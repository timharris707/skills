"""Executable preflight (design §7) — per-seat probes and the GO/NO-GO table
plus board guidance when fewer than two seats are usable."""
from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from typing import Optional

from _conductor.constants import (
    FAILURE_MODEL,
    FAILURE_NOOUTPUT,
    SMOKE_PROMPT,
)
from _conductor.registry import model_not_found
from _conductor.config import (
    RunConfig,
    SeatConfig,
)
from _conductor.spawn import (
    classify,
    spawn,
)
from _conductor.toolchain import propose_model

__all__ = [
    "SeatPreflight",
    "preflight_seat",
    "run_preflight",
    "render_preflight_table",
    "render_board_guidance",
]


@dataclass
class SeatPreflight:
    seat: str
    binary_ok: bool
    auth: str            # human-readable; never a token
    model_ok: bool
    smoke_status: str    # ran | degraded | dropped
    go: bool
    detail: str
    model_proposal: Optional[str] = None  # a resolvable fallback id when the pinned one 404s


def preflight_seat(seat: SeatConfig, *, network_on: bool, workdir: Optional[str] = None,
                   smoke_timeout: int = 60) -> SeatPreflight:
    adapter = seat.adapter

    version = spawn(adapter, adapter.version_argv(), timeout=15)
    binary_ok = version.exit_code == 0
    if not binary_ok:
        return SeatPreflight(seat.name, False, "n/a", False, "dropped", False,
                             f"binary not present / --version exit {version.exit_code}")

    prompt = SMOKE_PROMPT
    argv = adapter.build_argv(seat.model, prompt, reasoning=seat.reasoning,
                              workdir=workdir, network=network_on)
    smoke = spawn(adapter, argv, prompt=prompt, timeout=smoke_timeout, cwd=workdir)
    status, failure = classify(smoke, adapter)

    # A model-not-found signal must override classify(): claude prints the "model
    # may not exist" notice to stdout with exit 1, which would otherwise look like
    # "degraded-but-ran". This is a stale-CLI / renamed-id symptom, not auth — so
    # probe the seat's fallbacks for a resolvable id to PROPOSE (never auto-apply).
    proposal = None
    if model_not_found(smoke):
        proposal = propose_model(seat, network_on=network_on, workdir=workdir,
                                  smoke_timeout=smoke_timeout)
        detail = f"version ok; model '{seat.model}' did not resolve ({FAILURE_MODEL})"
        if proposal:
            detail += f"; fallback that resolves: {proposal}"
        return SeatPreflight(seat.name, binary_ok, "unknown (model id did not resolve)",
                             False, "dropped", False, detail, proposal)

    # The smoke ping proves model + transport end to end and that *some* auth is
    # live, but we do NOT run a separate session/whoami probe, so we report the
    # auth honestly as not independently verified (§16 licenses degrading here).
    # Never print tokens.
    if status == "dropped" and failure == FAILURE_NOOUTPUT:
        auth = "unknown (no smoke response)"
        model_ok = False
    elif status == "dropped":
        auth = "unknown (smoke timed out)"
        model_ok = False
    else:
        auth = "reachable (smoke-verified; not independently probed)"
        model_ok = True

    go = binary_ok and model_ok and status in ("ran", "degraded")
    detail = f"version ok; smoke {status}" + (f" ({failure})" if failure else "")
    return SeatPreflight(seat.name, binary_ok, auth, model_ok, status, go, detail)


def run_preflight(config: RunConfig) -> list:
    # Gate mode confines each seat to a scoped working directory (codex via -C,
    # claude/gemini via the subprocess cwd). The probe uses an EPHEMERAL temp dir,
    # not the run's out_dir — preflight is a read-only probe and a NO-GO board must
    # leave no artifacts behind (the M3 fan-out reuses out_dir once it spawns).
    workdir = tempfile.mkdtemp(prefix="advisory-board-preflight-") if config.fs_scoped else None
    try:
        return [preflight_seat(seat, network_on=config.network_on, workdir=workdir)
                for seat in config.board]
    finally:
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)


def render_preflight_table(results: list) -> str:
    rows = ["| Seat        | CLI | Auth                                          | Model | Smoke    | Verdict |",
            "| ----------- | --- | --------------------------------------------- | ----- | -------- | ------- |"]
    for r in results:
        cli = "yes" if r.binary_ok else "no"
        model = "yes" if r.model_ok else "no"
        verdict = "GO" if r.go else "NO-GO"
        rows.append(
            f"| {r.seat:<11} | {cli:<3} | {r.auth:<45} | {model:<5} "
            f"| {r.smoke_status:<8} | {verdict:<7} |"
        )
    go_count = sum(1 for r in results if r.go)
    rows.append("")
    rows.append(f"{go_count} of {len(results)} seats GO "
                f"({'proceed' if go_count >= 2 else 'STOP — a board needs >= 2 voices'}).")
    for r in results:
        if r.model_proposal:
            rows.append(f"  proposal ({r.seat}): pinned model did not resolve — "
                        f"`{r.model_proposal}` works; update the CLI or pass "
                        f"--model {r.seat}={r.model_proposal}")
    return "\n".join(rows)


def render_board_guidance(preflight: list, config: RunConfig) -> str:
    """When a board can't form (<2 usable seats), turn the dead-end into a path:
    separate not-installed seats (offer the install command) from installed-but-
    unusable ones (auth/model), then surface the documented fallbacks so a single-
    provider user is never stuck. Returns "" when the board CAN form."""
    go = [p for p in preflight if p.go]
    if len(go) >= 2:
        return ""

    by_name = {s.name: s for s in config.board}
    missing, unusable = [], []
    for p in preflight:
        if p.go:
            continue
        (missing if not p.binary_ok else unusable).append(p.seat)

    lines = [f"Only {len(go)} of {len(preflight)} seats are usable — a board needs at "
             "least 2 independent voices. Here's how to get there:"]

    if missing:
        lines.append("")
        lines.append("CLIs not installed (install ≠ account — you still need provider auth):")
        for name in missing:
            seat = by_name.get(name)
            adapter = seat.adapter if seat else None
            cmd = " ".join(adapter.install_argv()) if (adapter and adapter.install_argv) else "(no installer known)"
            line = f"  {name}: {cmd}"
            if adapter and adapter.auth_hint:
                line += f"  ·  then {adapter.auth_hint}"
            lines.append(line)
        lines.append("  (or let the skill do it: run_board.py toolchain --install)")

    if unusable:
        lines.append("")
        lines.append("Installed but not usable right now (check auth/login or model availability): "
                     + ", ".join(unusable))

    lines.append("")
    lines.append("Other ways to still run a board:")
    if go:
        lines.append(f"  • Same-provider, multi-lens board with what works ({', '.join(p.seat for p in go)}): "
                     "two seats on the same model with different lenses. Less independent — flag it in "
                     "provenance. See references/board-composition.md.")
    lines.append("  • Add a local-model seat — runnable now, no account or egress: "
                 "`brew install ollama`, pull a model (`ollama pull <model>`), then add it "
                 "with `--board " + (",".join(p.seat for p in go) + "," if go else "") +
                 "ollama --model ollama=<model>`. Or capture a human review as a seat. "
                 "See references/board-composition.md.")
    return "\n".join(lines)

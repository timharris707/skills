"""Setup doctor (roadmap v1.11 #7) — the preflight, proactively, for a brand-new
user. Sweeps EVERY registered provider (not just a chosen board), reusing the
toolchain currency probe (installed -> version vs latest, check_tool) and the
preflight seat probe (auth -> default model resolves -> smoke, preflight_seat)
verbatim — nothing here re-implements them. Output: a per-provider status block
with concrete fix-it steps, then a summary of which boards are viable today
(>= 2 seats GO) and a suggested first command. No user material egresses: the
probes are read-only and the smoke ping is the fixed one-word SMOKE_PROMPT."""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Optional

from _conductor.constants import FAILURE_MODEL
from _conductor.registry import REGISTRY
from _conductor.config import SeatConfig
from _conductor.toolchain import (
    ToolStatus,
    _tool_status_label,
    check_tool,
)
from _conductor.preflight import (
    SeatPreflight,
    preflight_seat,
)

__all__ = [
    "ProviderHealth",
    "probe_provider",
    "run_doctor",
    "fix_steps",
    "summarize_doctor",
    "render_doctor_header",
    "render_provider_block",
    "render_doctor_summary",
    "find_sample_source",
    "conductor_script_path",
]


@dataclass
class ProviderHealth:
    provider: str                     # registry key (claude / codex / gemini / antigravity / ollama)
    vendor: str                       # adapter.provider (Anthropic / OpenAI / Google / local)
    model: str                        # the default model the probe asked for
    tool: ToolStatus                  # installed -> version/currency (check_tool)
    probe: Optional[SeatPreflight]    # auth/model/smoke (preflight_seat); None when the CLI is absent
    install_cmd: str = ""             # how to install the CLI ("" when no installer is known)
    update_cmd: str = ""              # how to update it ("" when no updater is known)
    auth_hint: str = ""               # how to authenticate after install (never a secret)

    @property
    def installed(self) -> bool:
        return self.tool.present

    @property
    def go(self) -> bool:
        return bool(self.probe and self.probe.go)


def probe_provider(name: str, *, adapter=None, workdir: Optional[str] = None,
                   smoke_timeout: int = 60) -> ProviderHealth:
    """One provider's health, from the existing probes only: toolchain currency
    (check_tool) always, then — only when the CLI is installed — the standard
    preflight seat probe (auth/model/smoke) on the adapter's DEFAULT model.
    `adapter` is injectable for tests; it defaults to the REGISTRY entry."""
    adapter = adapter if adapter is not None else REGISTRY[name]
    tool = check_tool(adapter)
    probe = None
    if tool.present:
        seat = SeatConfig(id=name, name=name, adapter=adapter,
                          model=adapter.default_model, lens="",
                          reasoning=adapter.default_reasoning)
        # network_on=False mirrors the gate-mode preflight posture: the smoke ping
        # needs no web tools, so the doctor probes with the least reach.
        probe = preflight_seat(seat, network_on=False, workdir=workdir,
                               smoke_timeout=smoke_timeout)
    return ProviderHealth(
        provider=name,
        vendor=adapter.provider,
        model=adapter.default_model,
        tool=tool,
        probe=probe,
        install_cmd=" ".join(adapter.install_argv()) if adapter.install_argv else "",
        update_cmd=" ".join(adapter.update_argv()) if adapter.update_argv else "",
        auth_hint=adapter.auth_hint,
    )


def run_doctor(names=None, *, smoke_timeout: int = 60, on_result=None) -> list:
    """Probe every registered provider (or `names`) in registry order.

    Probes run in an EPHEMERAL scoped workdir (the run_preflight posture — a
    diagnostic must leave no artifacts behind). `on_result` (optional) is called
    with each ProviderHealth as it lands, so the CLI can stream status blocks
    instead of going silent for the whole sweep (a slow provider can take up to
    `smoke_timeout` seconds)."""
    names = list(names) if names is not None else list(REGISTRY)
    workdir = tempfile.mkdtemp(prefix="advisory-board-doctor-")
    try:
        healths = []
        for name in names:
            health = probe_provider(name, workdir=workdir, smoke_timeout=smoke_timeout)
            if on_result is not None:
                on_result(health)
            healths.append(health)
        return healths
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def fix_steps(health: ProviderHealth) -> list:
    """Concrete, ordered fix-it steps for one provider — pure (no probing).

    Ordered the way a new user unblocks a seat: install -> auth -> model
    fallback -> update. An empty list means nothing to do. A GO seat can still
    get the stale-CLI update nudge (non-blocking, but stale CLIs are the usual
    reason a freshly-renamed model id 404s)."""
    steps: list = []
    tool, probe = health.tool, health.probe
    if not tool.present:
        steps.append(f"install: {health.install_cmd or '(no installer known)'}")
        if health.auth_hint:
            steps.append(f"then auth: {health.auth_hint}")
        return steps
    if probe is not None and not probe.binary_ok:
        steps.append("the CLI is on PATH but `--version` fails — reinstall: "
                     + (health.install_cmd or "(no installer known)"))
        return steps
    model_missing = probe is not None and FAILURE_MODEL in probe.detail
    if model_missing:
        step = f"model '{health.model}' did not resolve — update the CLI"
        if health.update_cmd:
            step += f": {health.update_cmd}"
        steps.append(step)
        if probe.model_proposal:
            steps.append("or use the fallback that resolves today: "
                         f"--model {health.provider}={probe.model_proposal}")
    elif probe is not None and not probe.go:
        # Installed and the version reads, but the smoke never answered — auth
        # is the usual cause (installing a CLI never grants an account).
        if health.auth_hint:
            steps.append(f"auth/setup: {health.auth_hint}")
        else:
            steps.append("no smoke response — check the CLI's auth/login state")
    if tool.current is False and not model_missing and health.update_cmd:
        steps.append(f"update the stale CLI: {health.update_cmd} "
                     f"({tool.installed or '?'} -> {tool.latest or '?'})")
    return steps


_DEFAULT_TRIO = ("claude", "codex", "gemini")


def summarize_doctor(healths: list) -> dict:
    """Pure viable-board summary over a sweep: who is GO / not installed /
    installed-but-unusable, whether a board can convene today (>= 2 seats GO),
    and the --board value to suggest — None when no board is viable, or when the
    default trio is fully GO (the default run needs no flag)."""
    go = [h.provider for h in healths if h.go]
    missing = [h.provider for h in healths if not h.installed]
    unusable = [h.provider for h in healths if h.installed and not h.go]
    viable = len(go) >= 2
    default_trio_go = all(p in go for p in _DEFAULT_TRIO)
    board = None if (not viable or default_trio_go) else ",".join(go[:3])
    return {
        "go": go,
        "missing": missing,
        "unusable": unusable,
        "viable": viable,
        "total": len(healths),
        "board": board,
    }


def render_doctor_header(names: list) -> str:
    return "\n".join([
        "=== setup doctor ===",
        f"Sweeping every registered provider: {', '.join(names)}.",
        "No user material egresses in this sweep — read-only probes and smoke-pings only:",
        "each installed CLI gets one fixed one-word smoke prompt (never your files), and",
        "version currency asks your local package manager. A slow provider can take a minute.",
    ])


def render_provider_block(health: ProviderHealth) -> str:
    tool, probe = health.tool, health.probe
    lines = [f"## {health.provider} — {health.vendor} · {tool.pkg_label or health.provider}"]

    def row(label: str, text: str) -> None:
        lines.append(f"  {label:<8}{text}")

    if not tool.present:
        row("cli", "not installed")
        row("model", f"{health.model} — not probed (CLI absent)")
        row("verdict", "NO-GO")
    else:
        row("cli", f"installed {tool.installed or '(version unreadable)'}"
                   f" · latest {tool.latest or '?'} · {_tool_status_label(tool)}")
        if probe is not None:
            row("auth", probe.auth)
            if probe.model_ok:
                model_line = f"{health.model} — resolves (smoke {probe.smoke_status})"
            elif FAILURE_MODEL in probe.detail:
                model_line = f"{health.model} — did NOT resolve ({FAILURE_MODEL})"
            else:
                model_line = f"{health.model} — unconfirmed (smoke {probe.smoke_status})"
            row("model", model_line)
            row("verdict", "GO" if probe.go else "NO-GO")
        if tool.note:
            row("note", tool.note)
    for index, step in enumerate(fix_steps(health)):
        row("fix" if index == 0 else "", step)
    return "\n".join(lines)


def render_doctor_summary(summary: dict, *, sample_source: Optional[str] = None,
                          script_path: Optional[str] = None) -> str:
    """Render the viable-board summary + the suggested first command. Pure over
    its inputs; the caller resolves the real sample/script paths."""
    sample = sample_source or "<your-doc.md>"
    script = script_path or "scripts/run_board.py"
    go, total = summary["go"], summary["total"]
    lines = ["## Summary — which boards are viable today"]
    if summary["viable"]:
        lines.append(f"{len(go)} of {total} providers GO: {', '.join(go)} — a board can "
                     "convene with any two or more of them (>= 2 independent voices).")
        if summary["board"] is None:
            lines.append("The default board (claude,codex,gemini) is fully GO — no --board flag needed.")
    else:
        lines.append(f"Only {len(go)} of {total} providers GO"
                     + (f" ({', '.join(go)})" if go else "")
                     + " — NOT viable yet: a board needs at least 2 independent voices.")
    if summary["missing"]:
        lines.append(f"not installed: {', '.join(summary['missing'])}")
    if summary["unusable"]:
        lines.append(f"installed but not usable yet: {', '.join(summary['unusable'])}")
    if not summary["viable"]:
        lines.append("Get to two seats:")
        lines.append("  - fix a NO-GO provider above (each block lists its steps)")
        lines.append("  - add a local seat — no account, no egress: brew install ollama, "
                     "then `ollama pull <model>`")
        if go:
            lines.append(f"  - or run a same-provider, multi-lens board on {go[0]} alone "
                         "(less independent — flag it in provenance): "
                         f"--board a={go[0]},b={go[0]}  (see references/board-composition.md)")
        else:
            lines.append("  - see references/board-composition.md for minimal lineups")
    lines.append("")
    board_flag = f" --board {summary['board']}" if summary["board"] else ""
    lead = ("Suggested first command" if summary["viable"]
            else "Once two seats are GO, the first command")
    lines.append(f"{lead} — a full preview (config, egress plan, artifact tree; spawns nothing):")
    lines.append(f"  python3 {script} run --source {sample}{board_flag} --dry-run")
    return "\n".join(lines)


def conductor_script_path() -> str:
    """Absolute path to run_board.py (this package's parent scripts/ dir), so the
    suggested first command is copy-pasteable from any cwd."""
    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(scripts_dir, "run_board.py")


def find_sample_source() -> str:
    """The skill's bundled sample source (tests/fixtures/sample-plan.md) when it
    shipped with this install, else a placeholder — the suggested first command
    must never point at a file that doesn't exist."""
    scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cand = os.path.normpath(os.path.join(scripts_dir, os.pardir,
                                         "tests", "fixtures", "sample-plan.md"))
    return cand if os.path.isfile(cand) else "<your-doc.md>"

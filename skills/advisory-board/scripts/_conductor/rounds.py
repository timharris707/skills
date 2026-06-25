"""The round fan-out (design §11/§12/§13): run a round across the board, the
per-seat round runner, and the per-seat round artifacts/renderers."""
from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Optional

from _conductor.constants import (
    EXIT_EGRESS_BLOCKED,
    die,
)
from _conductor.config import (
    RunConfig,
    SeatConfig,
)
from _conductor.spawn import (
    RETRYABLE_FAILURES,
    classify_round1,
    spawn,
)
from _conductor.egress import (
    EgressApproval,
    packet_hash,
)
from _conductor.artifacts import _write

__all__ = [
    "SeatRoundResult",
    "_run_seat_round",
    "run_round",
    "run_round1",
    "_dropped_md",
    "render_raw_record",
    "write_round_artifacts",
    "write_round1_artifacts",
    "render_round_table",
    "render_round1_table",
    "_argv_preview",
]


@dataclass
class SeatRoundResult:
    seat: str
    provider: str
    round_no: int
    model_requested: str
    model_answered: Optional[str]
    status: str                 # ran | degraded | dropped
    failure_class: Optional[str]
    attempts: int
    elapsed_s: float
    exit_code: int
    timed_out: bool
    stdout: str
    stderr: str
    prompt_hash: str            # sha256 of the exact bytes THIS seat received
    source_hash: str            # sha256 of the source material (same across seats)
    round_packet_hash: str      # sha256 of THIS round's full packet (round 1 == approval hash)
    argv_preview: str           # the invocation, prompt elided (the black-box recorder)

    @property
    def usable(self) -> bool:
        return self.status in ("ran", "degraded")


def _run_seat_round(seat: SeatConfig, blob: "PacketBlob", config: RunConfig, *,
                    round_no: int, round_packet_hash: str,
                    workdir: Optional[str], timeout: Optional[int]) -> SeatRoundResult:
    """Spawn one seat on its packet blob, classify, retry once per §13.

    The prompt fed here is `blob.text` — the SAME canonical string used to compute
    the round's packet hash — so the bytes that actually leave (codex/gemini carry
    it in argv, claude on stdin) are exactly the recorded bytes. No re-templating
    happens between hashing and spawn.
    """
    adapter = seat.adapter
    seat_timeout = timeout if timeout is not None else adapter.timeout_s
    prompt = blob.text

    attempts = 0
    result = None
    status = failure = None
    last_argv: list = []
    for attempt in (1, 2):
        attempts = attempt
        last_argv = adapter.build_argv(seat.model, prompt, reasoning=seat.reasoning,
                                       workdir=workdir, network=config.network_on)
        result = spawn(adapter, last_argv, prompt=prompt, timeout=seat_timeout, cwd=workdir)
        status, failure = classify_round1(result, adapter)
        if status in ("ran", "degraded"):
            break
        if attempt == 1 and failure in RETRYABLE_FAILURES:
            continue   # the one allowed retry (Timeout | InvalidOutput)
        break

    answered = adapter.model_answered(result.stdout, result.stderr) if status in ("ran", "degraded") else None
    return SeatRoundResult(
        seat=seat.name,
        provider=seat.provider,
        round_no=round_no,
        model_requested=seat.model,
        model_answered=answered,
        status=status,
        failure_class=failure,
        attempts=attempts,
        elapsed_s=result.elapsed_s,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        stdout=result.stdout,
        stderr=result.stderr,
        prompt_hash=blob.sha256,
        source_hash=config.source.sha256,
        round_packet_hash=round_packet_hash,
        argv_preview=_argv_preview(last_argv),
    )


def run_round(config: RunConfig, blobs: list, approval: EgressApproval, *,
              round_no: int = 1, timeout: Optional[int] = None,
              parallel: bool = True) -> list:
    """Fan a round out across its seats. Returns SeatRoundResult in blob order.

    Round 1 re-asserts the egress hash one last time before the first spawn: the
    packet MUST still hash to exactly what consent was bound to, or nothing leaves
    the machine (the pre-spawn hard stop, restated at the point of no return).
    Round 2+ egresses only DERIVATIVES of already-approved source (the round-1
    reviews) to the SAME providers, under the multi-round plan the run-card
    disclosed — so it records its own packet hash for provenance but reuses the
    run's approval rather than re-prompting.
    """
    round_packet_hash = packet_hash(blobs)
    if round_no == 1 and round_packet_hash != approval.content_hash:
        die("egress hash drift: the packet no longer matches the approved content "
            "hash — refusing to spawn the board", EXIT_EGRESS_BLOCKED)
    by_seat = {b.seat: b for b in blobs}
    seats = [s for s in config.board if s.name in by_seat]   # round 2 drops failed seats

    # Gate mode confines each seat to a scoped, empty cwd (same posture preflight
    # used); advisory mode runs in the caller's cwd (your own material, by design).
    workdir = tempfile.mkdtemp(prefix=f"advisory-board-round{round_no}-") if config.fs_scoped else None
    try:
        def _one(seat: SeatConfig) -> SeatRoundResult:
            return _run_seat_round(seat, by_seat[seat.name], config, round_no=round_no,
                                   round_packet_hash=round_packet_hash,
                                   workdir=workdir, timeout=timeout)

        results: dict = {}
        if parallel and len(seats) > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=len(seats)) as pool:
                futures = {pool.submit(_one, s): s for s in seats}
                for fut, seat in futures.items():
                    results[seat.name] = fut.result()
        else:
            for seat in seats:
                results[seat.name] = _one(seat)
        return [results[s.name] for s in seats]
    finally:
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)


def run_round1(config: RunConfig, blobs: list, approval: EgressApproval, *,
               timeout: Optional[int] = None, parallel: bool = True) -> list:
    """Round-1 fan-out across the board (thin wrapper over run_round)."""
    return run_round(config, blobs, approval, round_no=1, timeout=timeout, parallel=parallel)


def _dropped_md(r: SeatRoundResult) -> str:
    return (f"# {r.seat} — round {r.round_no}: no usable review\n\n"
            f"Status: **{r.status}** · failure class: **{r.failure_class or '-'}** · "
            f"attempts: {r.attempts}.\n\n"
            f"This seat did not return a usable round-{r.round_no} review. See "
            f"`round-{r.round_no}/{r.seat}.raw` for the full invocation record and "
            f"`logs/{r.seat}-round-{r.round_no}.stderr` for its stderr.\n")


def render_raw_record(r: SeatRoundResult) -> str:
    """The Black-Box Recorder (§12): the verbatim invocation + the hashes that
    prove same-material independence and bind it to the round's packet. Honestly
    'falsifiable-by-inspection', not tamper-proof — it catches empty/lazy/drifted
    runs, not a determined forger using the same orchestrator."""
    if r.round_no == 1:
        packet_note = "(egress consent was bound to this)"
    else:
        packet_note = ("(round-2 packet; reuses the run's egress approval — "
                       "derivatives of already-approved source to the same providers)")
    lines = [
        f"# Black-box recorder — {r.seat} · round {r.round_no}",
        "",
        f"command         : {r.argv_preview}",
        f"prompt-source   : prompts/{r.seat}-round-{r.round_no}.prompt",
        f"source-hash     : sha256:{r.source_hash}   (identical across seats → same-material independence)",
        f"prompt-hash     : sha256:{r.prompt_hash}   (the exact bytes this seat received)",
        f"packet-hash     : sha256:{r.round_packet_hash}   {packet_note}",
        f"model-requested : {r.model_requested}",
        f"model-answered  : {r.model_answered or 'unknown (CLI reported none — not assumed)'}",
        f"exit-code       : {r.exit_code}",
        f"timed-out       : {'yes' if r.timed_out else 'no'}",
        f"elapsed-s       : {r.elapsed_s:.2f}",
        f"attempts        : {r.attempts}",
        f"status          : {r.status}",
        f"failure-class   : {r.failure_class or '-'}",
        "",
        "----------------8<---------------- STDOUT ----------------8<----------------",
        r.stdout.rstrip("\n"),
        "----------------8<---------------- STDERR ----------------8<----------------",
        r.stderr.rstrip("\n"),
        "",
    ]
    return "\n".join(lines) + "\n"


def write_round_artifacts(config: RunConfig, results: list, round_no: int) -> None:
    out = config.out_dir
    rdir = os.path.join(out, f"round-{round_no}")
    os.makedirs(rdir, exist_ok=True)
    os.makedirs(os.path.join(out, "logs"), exist_ok=True)
    for r in results:
        review_md = r.stdout if r.usable else _dropped_md(r)
        _write(os.path.join(rdir, f"{r.seat}.md"), review_md)
        _write(os.path.join(rdir, f"{r.seat}.raw"), render_raw_record(r))
        _write(os.path.join(out, "logs", f"{r.seat}-round-{round_no}.stderr"), r.stderr)


# Back-compat alias (M3 callers / tests).
def write_round1_artifacts(config: RunConfig, results: list,
                           approval: Optional[EgressApproval] = None) -> None:
    write_round_artifacts(config, results, 1)


def render_round_table(results: list, round_no: int) -> str:
    rows = ["| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |",
            "| ------ | -------- | -------------- | -------- | ------- | ------- |"]
    for r in results:
        answered = r.model_answered or "unknown"
        rows.append(
            f"| {r.seat:<6} | {r.status:<8} | {answered:<14} | {r.attempts:<8} "
            f"| {r.elapsed_s:>5.1f}s | {r.failure_class or '-'} |"
        )
    usable = sum(1 for r in results if r.usable)
    rows.append("")
    rows.append(f"{usable} of {len(results)} seats produced a usable round-{round_no} review.")
    return "\n".join(rows)


def render_round1_table(results: list) -> str:   # back-compat alias
    return render_round_table(results, 1)


def _argv_preview(argv: list) -> str:
    # Keep golden output readable: collapse a long inlined prompt to a sentinel.
    shown = []
    for token in argv:
        if len(token) > 60 and " " in token:
            shown.append("<prompt>")
        else:
            shown.append(token)
    return " ".join(shown)

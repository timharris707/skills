"""The subprocess spawn helper (process-group-killed on timeout) and the §13
failure protocol — classification, the round-1 success-shape check, and the
auth/retry signatures."""
from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from typing import Optional

from _conductor.constants import (
    FAILURE_AUTH,
    FAILURE_INVALID,
    FAILURE_MODEL,
    FAILURE_NOOUTPUT,
    FAILURE_TIMEOUT,
)
from _conductor.registry import (
    SeatAdapter,
    model_not_found,
)

__all__ = [
    "ROUND1_MIN_CHARS",
    "ROUND1_SECTION_CUES",
    "ROUND1_MIN_CUES",
    "check_round1_shape",
    "SpawnResult",
    "spawn",
    "_kill_group_and_collect",
    "_clock",
    "classify",
    "RETRYABLE_FAILURES",
    "_AUTH_FAILURE_SIGNALS",
    "auth_failed",
    "classify_round1",
    "classify_ask",
]


# Round-1 output success criteria (design §13 "the output artifact must contain
# the round's required sections — a shape/length check"). A genuine 7-section
# review is long and names several of its sections; a plan-mode summary or an "I
# saved the review to a file" reply is short and names few. This is the DETECTION
# half of the {{CLAUDE_OUTPUT_OVERRIDE}} fix (a short/plan-shaped Claude artifact
# fails here). Heuristic by design: lenient on any real review, strict on stubs.
ROUND1_MIN_CHARS = 200
ROUND1_SECTION_CUES = ("verdict", "objection", "execution", "invariant",
                       "risk", "evidence", "challenge", "guardrail", "assumption")
ROUND1_MIN_CUES = 3


def check_round1_shape(text: str) -> tuple:
    """(ok, reason). Does this look like a real round-1 review, not a stub?"""
    body = text.strip()
    if len(body) < ROUND1_MIN_CHARS:
        return False, f"too short ({len(body)} chars < {ROUND1_MIN_CHARS}) — plan-mode/stub reply"
    low = body.lower()
    hits = sorted({c for c in ROUND1_SECTION_CUES if c in low})
    if len(hits) < ROUND1_MIN_CUES:
        return False, (f"missing review sections (found {len(hits)}/{ROUND1_MIN_CUES} "
                       f"section cues: {', '.join(hits) or 'none'})")
    return True, ""


# Spawn helper (used by preflight now; reused by M3 fan-out)


@dataclass
class SpawnResult:
    exit_code: int
    stdout: str
    stderr: str
    elapsed_s: float
    timed_out: bool


def spawn(adapter: SeatAdapter, argv: list, *, prompt: Optional[str] = None,
          timeout: Optional[int] = None, cwd: Optional[str] = None) -> SpawnResult:
    """Run one seat CLI under a hard timeout, capturing stdout/stderr.

    The child is launched in its OWN session (start_new_session=True) so a real
    seat that forks worker subprocesses can be killed as a process GROUP on
    timeout — subprocess.run only kills the direct child and would orphan the
    workers (handoff M3 obligation; the mock `timeout` arm exec's sleep so it has
    none, but real CLIs do). On timeout we return exit 124 + whatever partial
    output was captured, never blocking forever on the dead child's pipes.
    """
    timeout = timeout if timeout is not None else adapter.timeout_s
    start = _clock()
    if adapter.prompt_on_stdin and prompt is not None:
        stdin_arg, input_data = subprocess.PIPE, prompt
    elif adapter.close_stdin:
        stdin_arg, input_data = subprocess.DEVNULL, None
    else:
        stdin_arg, input_data = None, None   # inherit (e.g. the --version probe)
    try:
        proc = subprocess.Popen(
            argv,
            stdin=stdin_arg,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        return SpawnResult(127, "", f"{argv[0]}: command not found", _clock() - start, False)
    try:
        out, err = proc.communicate(input=input_data, timeout=timeout)
        return SpawnResult(proc.returncode, out or "", err or "", _clock() - start, False)
    except subprocess.TimeoutExpired:
        out, err = _kill_group_and_collect(proc)
        return SpawnResult(124, out, err, _clock() - start, True)


def _kill_group_and_collect(proc: "subprocess.Popen") -> tuple:
    """Terminate the timed-out child's whole process group, then drain its pipes.

    SIGTERM the group, give it 5s to flush and exit; if it clings, SIGKILL the
    group. Returns (stdout, stderr) — possibly partial, never None.
    """
    def _killpg(sig: int) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError):
            try:
                proc.send_signal(sig)   # group gone/denied: fall back to the child
            except ProcessLookupError:
                pass

    _killpg(signal.SIGTERM)
    try:
        out, err = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        _killpg(signal.SIGKILL)
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out, err = "", ""
    return out or "", err or ""


def _clock() -> float:
    import time
    return time.monotonic()


def classify(result: SpawnResult, adapter: SeatAdapter) -> tuple:
    """Classify a spawn into (status, failure_class|None) — design §13.

    status is one of ran | degraded | dropped. Judge a seat by whether usable
    content came back, not by stderr noise alone (Gemini routinely prints router
    retries to stderr yet returns a valid review).
    """
    if result.timed_out:
        return "dropped", FAILURE_TIMEOUT
    if not result.stdout.strip():
        return "dropped", FAILURE_NOOUTPUT
    if result.exit_code != 0:
        # Usable content despite a non-zero exit (matches execution-harness.md:
        # "judge by whether the artifact is usable, not by stderr"). This is the
        # PREFLIGHT smoke classifier — a one-word "ready" is a valid smoke. The
        # round-1 fan-out adds the artifact-shape check via classify_round1 below.
        return "degraded", None
    return "ran", None


# Failure classes the protocol retries ONCE (design §13). Everything else
# (AuthFailure, NoOutput, ModelNotFound) is non-recoverable → immediate drop.
RETRYABLE_FAILURES = frozenset({FAILURE_TIMEOUT, FAILURE_INVALID})

# Auth-failure tells scanned ONLY on stderr (never the review on stdout, which may
# legitimately discuss auth/401s when the material under review is an auth system).
_AUTH_FAILURE_SIGNALS = (
    "not authenticated", "please log in", "please sign in", "authentication failed",
    "unauthorized", "401 ", "invalid api key", "no api key", "login required",
    "auth error", "session expired", "expired credentials",
)


def auth_failed(stderr: str) -> bool:
    blob = stderr.lower()
    return any(sig in blob for sig in _AUTH_FAILURE_SIGNALS)


def classify_round1(result: SpawnResult, adapter: SeatAdapter) -> tuple:
    """Classify a round-1 fan-out spawn into (status, failure_class|None) — §13.

    Stricter than the preflight classify(): the captured artifact must pass the
    shape/length check (check_round1_shape), which is how a short plan-mode reply
    or an "I saved it to a file" stub is caught (the {{CLAUDE_OUTPUT_OVERRIDE}}
    detection half). Ordering matters — timeout, then the SHAPE GATE, then (only
    when no usable review came back) the model-not-found / empty-auth split, then
    the usable-but-nonzero degrade.

    The shape gate comes BEFORE the model-not-found / auth screens on purpose. A
    genuine ModelNotFound or auth failure yields NO usable review — the model
    never answered. So a complete, well-formed review on stdout is itself proof
    the model resolved and ran; a model-not-found / auth SIGNAL on stderr is then
    echoed MATERIAL UNDER REVIEW, not a real failure. The acute case: a seat
    reviewing this skill's own source — codex's file-read trace echoes
    registry.py's literal `_MODEL_NOT_FOUND_SIGNALS` list to stderr, which would
    otherwise drop a healthy seat. (PR #27 stopped scanning stdout for exactly
    this; the same echo also lands on stderr — still scanned — so screening only
    when the review is absent/stub-shaped is what actually closes it.)
    """
    if result.timed_out:
        return "dropped", FAILURE_TIMEOUT
    shape_ok, _reason = check_round1_shape(result.stdout)
    if not shape_ok:
        # No usable review: NOW the stderr signals are trustworthy failure modes.
        if model_not_found(result):
            return "dropped", FAILURE_MODEL
        if not result.stdout.strip():
            # No usable stdout: distinguish an actionable auth failure (look only
            # at stderr) from a bare empty run.
            if auth_failed(result.stderr):
                return "dropped", FAILURE_AUTH
            return "dropped", FAILURE_NOOUTPUT
        return "dropped", FAILURE_INVALID   # retryable once
    if result.exit_code != 0:
        return "degraded", None             # usable review despite a non-zero exit
    return "ran", None


def classify_ask(result: SpawnResult, adapter: SeatAdapter) -> tuple:
    """Classify an `ask` cross-examination answer into (status, failure_class|None).

    Lighter than classify_round1: an answer to a follow-up question is free-form
    prose, NOT a 7-section review, so there is no shape/length gate (that would drop
    a perfectly good short answer). Non-empty stdout IS the usable artifact. Ordering
    mirrors classify_round1 — timeout, then (only when NO usable answer came back) the
    model-not-found / auth / empty split (stderr-only, the poisoning defense), then the
    usable-but-nonzero degrade."""
    if result.timed_out:
        return "dropped", FAILURE_TIMEOUT
    if not result.stdout.strip():
        if model_not_found(result):
            return "dropped", FAILURE_MODEL
        if auth_failed(result.stderr):
            return "dropped", FAILURE_AUTH
        return "dropped", FAILURE_NOOUTPUT
    if result.exit_code != 0:
        return "degraded", None             # usable answer despite a non-zero exit
    return "ran", None

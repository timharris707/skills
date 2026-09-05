"""Live progress view (v1.14 #10): a `status.json` in the run dir rewritten
atomically on every seat/round/stage transition, the terminal per-seat progress
lines drawn from the same events, and a self-refreshing `status.html` tracker.

Board runs block-buffer stdout, so a user watching a background run sees nothing
until a round completes — the run dir is the only live window. This makes that
window real: the moment a seat starts, finishes, drops, or retries, three things
happen from ONE `emit`:

  1. `status.json` is rewritten (write-temp + os.replace — a concurrent reader
     never sees a torn file);
  2. `status.html` is regenerated with the current state inlined (file:// JS
     can't fetch a sibling json in modern browsers, so we inline + <meta refresh>);
  3. a flushed one-liner is printed to stdout (block-buffering is the pain we fix).

Design constraints honored here:
  * status.json is the SINGLE source of truth — one JSON document, versioned
    `advisory-board/status@1`, run-level fields + an ordered `events[]` + a
    per-seat current-state map for cheap rendering;
  * writes are SERIALIZED with a lock (seat transitions fire from worker threads)
    and BEST-EFFORT — a status write failure warns once to stderr and never kills
    the run;
  * event timestamps use the repo's `now_stamp()` (deterministic under
    ADVISORY_BOARD_NOW_TS) but are kept OUT of any golden byte surface — the
    event-sequence golden asserts the ordered (stage, seat, round, state) tuples,
    the HTML render is a pure function of the status dict that omits stamps from
    its structural surface.

The tracker is a LIVE VIEW, not an artifact of record (its footer says so): the
verdict chain + run-metadata.md remain the authoritative outputs. status.json /
status.html persist after a run completes, reading as such (a `finished` stamp +
a terminal outcome).

RH-1 invariant: the tracker defers its first disk write until the run commits to
spawning (post-egress-approval). So a preflight NO-GO leaves no dir; an egress-refused
run writes only the refusal manifest (egress-manifest.md + sensitivity.json), never
status.* — the refusal record predates activate(), which the gate never reaches.
"""
from __future__ import annotations

import html
import json
import os
import threading
from typing import Optional

from _conductor.constants import now_stamp

__all__ = [
    "STATUS_SCHEMA",
    "STATUS_JSON_NAME",
    "STATUS_HTML_NAME",
    "OUTCOME_INTERRUPTED",
    "STATES",
    "STAGES",
    "StatusTracker",
    "NullTracker",
    "render_status_html",
    "event_tuples",
]

STATUS_SCHEMA = "advisory-board/status@1"
STATUS_JSON_NAME = "status.json"
STATUS_HTML_NAME = "status.html"

# Terminal outcome tokens that the run reached its intended end for — the tracker's
# HTML badge renders these green ("done"), everything else (a NO-GO, an egress
# block, a synthesizer/revision that didn't deliver) renders muted-red ("drop").
# `verdict-only` is green-adjacent (the verdict landed; only the optional revised
# draft didn't) but we surface it as an incomplete outcome so it reads as "look".
_SUCCESS_OUTCOMES = frozenset({"ok", "rounds-complete"})

# The terminal outcome stamped when the run ABORTS after activate() without reaching
# a normal finish() — a die() mid-fan-out (egress-hash / repo-scope drift), a
# KeyboardInterrupt, or an unhandled exception. cli._execute_run's finally stamps this
# so the persisted status.json reads `finished` and the status.html stops meta-refreshing
# over a dead run (the seats' last-known states stay as the honest queued/running
# snapshot). Renders muted-red ("drop"), like every other non-success outcome.
OUTCOME_INTERRUPTED = "interrupted"

# The per-transition state vocabulary. Stage transitions use started/done;
# seat transitions add running/dropped/retry.
STATES = ("started", "running", "done", "dropped", "retry", "skipped")
# `retry` and `skipped` are RESERVED in status@1: part of the documented vocabulary
# so consumers can rely on the enum, but no current conductor path emits them.
# The top-level stages a run moves through (each may fire started/done). `round`
# is per-round (carries a round number); the rest are once-per-run phases.
STAGES = ("preflight", "egress", "rubric", "round", "synthesis", "revision", "endorsement", "run")


def _atomic_write_text(path: str, text: str) -> None:
    """Write `text` to `path` atomically: a sibling temp file + os.replace, so a
    concurrent reader sees either the old complete file or the new complete file,
    never a torn write. The temp is removed on any Python-level failure so no `.tmp` litters
    the run dir. Fsync is deliberately skipped — this is a best-effort live view,
    not a durability-critical artifact, and the run dir already tolerates a crash
    mid-fan-out (the round artifacts are the record of what happened)."""
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".{os.path.basename(path)}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, path)   # atomic on POSIX and Windows
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class NullTracker:
    """A no-op tracker: every method is a silent pass. Used where a run wants the
    conductor's stage/seat hooks present but no live view written (tests that pin
    a run dir's exact contents, or a caller that opts out). Keeping the same shape
    as StatusTracker means the hook sites stay branch-free."""

    enabled = False

    def activate(self, *a, **k): pass
    def stage(self, *a, **k): pass
    def round_started(self, *a, **k): pass
    def round_done(self, *a, **k): pass
    def seat(self, *a, **k): pass
    def finish(self, *a, **k): pass
    def finish_if_unfinished(self, *a, **k): pass


class StatusTracker:
    """The live-progress recorder. One instance per run; its `emit` is the single
    choke point that (1) appends an event, (2) updates the per-seat/run state,
    (3) rewrites status.json atomically, (4) regenerates status.html, and (5)
    prints a flushed terminal line. Serialized with a lock because seat
    transitions fire from the round's worker threads.

    BEST-EFFORT throughout: a write failure is caught, warned ONCE to stderr, and
    the run continues (a live view must never take the run down). The in-memory
    document keeps advancing even if disk writes are failing, so a later
    recovering write still reflects the full history."""

    enabled = True

    def __init__(self, out_dir: str, *, title: str, rounds_planned, seats,
                 write_html: bool = True, stream=None, active: bool = False):
        import sys
        self.out_dir = out_dir
        self.write_html = write_html
        self.stream = stream if stream is not None else sys.stdout
        self._lock = threading.Lock()
        self._seq = 0
        self._warned = False
        # DISK writes are gated on `_active`. The tracker records events + prints
        # flushed terminal lines from the very first transition (preflight/egress),
        # but does NOT create the run dir until the run has COMMITTED to spawning —
        # i.e. `activate()` is called right after the egress gate approves and the
        # pre-spawn artifacts are written. This preserves the RH-1 invariant: a
        # preflight-NO-GO or egress-refused run leaves NO out dir (and no status.*).
        # Once active, the FULL in-memory history (including the pre-activation
        # preflight/egress events) is written on the first flush, so the persisted
        # status.json is complete. Tests may construct with active=True to write
        # from the first event.
        self._active = active
        seat_ids = [s.id for s in seats]
        self._doc = {
            "schema": STATUS_SCHEMA,
            "title": title,
            "started": now_stamp(),
            "finished": None,
            "outcome": None,
            "stage": None,
            "rounds_planned": rounds_planned,
            "rounds_done": 0,
            "seats": {sid: {"state": "waiting", "round": None, "detail": None}
                      for sid in seat_ids},
            "events": [],
        }
        # Record the run-started event (prints the line; writes to disk only if
        # already active — the default defers until activate()).
        self._flush("run", None, None, "started", "run started")

    def activate(self) -> None:
        """Commit the live view to disk. Called once the run has passed the egress
        gate and materialized its run dir (write_pre_spawn_artifacts) — the first
        moment writing status.* into the out dir is legitimate. Idempotent; flushes
        the full accumulated history so the persisted status.json is complete."""
        with self._lock:
            if self._active:
                return
            self._active = True
            self._write_files()

    # -- public transition helpers ---------------------------------------- #

    def stage(self, stage: str, state: str = "started", detail: Optional[str] = None) -> None:
        """A top-level phase transition (preflight/egress/synthesis/…)."""
        with self._lock:
            self._doc["stage"] = stage if state == "started" else self._doc["stage"]
            self._flush(stage, None, None, state, detail)

    def round_started(self, round_no: int, detail: Optional[str] = None) -> None:
        with self._lock:
            self._doc["stage"] = "round"
            for sid in self._doc["seats"]:
                # Only seats still in play advance to "queued" for this round; a
                # dropped seat stays dropped (round 2+ leaves it behind).
                if self._doc["seats"][sid]["state"] != "dropped":
                    self._set_seat(sid, "queued", round_no, None)
            self._flush("round", None, round_no, "started",
                        detail or f"round {round_no} fan-out")

    def round_done(self, round_no: int, detail: Optional[str] = None) -> None:
        with self._lock:
            self._doc["rounds_done"] = max(self._doc["rounds_done"], round_no)
            self._flush("round", None, round_no, "done",
                        detail or f"round {round_no} complete")

    def seat(self, seat_id: str, state: str, round_no: int,
             detail: Optional[str] = None) -> None:
        """A per-seat transition inside a round (fires from worker threads)."""
        with self._lock:
            self._set_seat(seat_id, state, round_no, detail)
            self._flush("round", seat_id, round_no, state, detail)

    def finish(self, outcome: str, detail: Optional[str] = None) -> None:
        """Terminal marker — stamps `finished` + a coarse outcome token so a
        completed run's status.json/status.html read as done."""
        with self._lock:
            self._doc["finished"] = now_stamp()
            self._doc["outcome"] = outcome
            self._doc["stage"] = "run"
            self._flush("run", None, None, "done", detail or outcome)

    def finish_if_unfinished(self, outcome: str, detail: Optional[str] = None) -> None:
        """Stamp a terminal outcome ONLY if the run hasn't already finished — the
        abort guard cli._execute_run's finally calls so any abnormal exit (a die()
        mid-fan-out, KeyboardInterrupt, an unhandled exception) leaves status.json
        `finished` and status.html STATIC, never meta-refreshing over a dead run. A
        no-op when finish() already ran on a normal path (so it never re-stamps a
        completed run), and idempotent under its own lock. The seats' last-known
        states are left untouched — the honest queued/running snapshot at the abort."""
        with self._lock:
            if self._doc["finished"] is not None:
                return
            self._doc["finished"] = now_stamp()
            self._doc["outcome"] = outcome
            self._doc["stage"] = "run"
            self._flush("run", None, None, "done", detail or outcome)

    # -- internals -------------------------------------------------------- #

    def _set_seat(self, seat_id: str, state: str, round_no, detail) -> None:
        s = self._doc["seats"].get(seat_id)
        if s is None:
            return
        s["state"] = state
        s["round"] = round_no
        s["detail"] = detail

    def _flush(self, stage, seat, round_no, state, detail) -> None:
        """Append the event, then rewrite both artifacts + print the line. Caller
        holds the lock. Every disk touch is best-effort."""
        self._seq += 1
        self._doc["events"].append({
            "seq": self._seq,
            "stage": stage,
            "seat": seat,
            "round": round_no,
            "state": state,
            "detail": detail,
            "at": now_stamp(),
        })
        self._print_line(stage, seat, round_no, state, detail)
        self._write_files()

    def _write_files(self) -> None:
        if not self._active:
            return   # deferred: no run dir yet (pre-egress-approval — RH-1)
        try:
            _atomic_write_text(os.path.join(self.out_dir, STATUS_JSON_NAME),
                               json.dumps(self._doc, indent=2, ensure_ascii=False) + "\n")
            if self.write_html:
                _atomic_write_text(os.path.join(self.out_dir, STATUS_HTML_NAME),
                                   render_status_html(self._doc))
        except Exception as exc:   # best-effort: never let a live-view write kill the run
            if not self._warned:
                self._warned = True
                import sys
                print(f"warning: live status view could not be written "
                      f"({type(exc).__name__}: {exc}); the run continues, artifacts "
                      "of record are unaffected", file=sys.stderr, flush=True)

    def _print_line(self, stage, seat, round_no, state, detail) -> None:
        line = terminal_line(stage, seat, round_no, state, detail)
        if line is None:
            return
        try:
            print(line, file=self.stream, flush=True)   # flush: the whole point
        except Exception:
            pass


# The per-state glyph for the flushed terminal line. Kept ASCII-plus-check so it
# renders in any terminal; the check/× are the two the pinned-elsewhere output
# never uses, so these lines only ADD, never collide.
_STATE_GLYPH = {
    "started": "…",
    "running": "…",
    "queued": "·",
    "done": "✓",
    "dropped": "✗",
    "retry": "↻",
    "skipped": "–",
}


def terminal_line(stage, seat, round_no, state, detail) -> Optional[str]:
    """The human one-liner for a transition, or None to print nothing.

    Per-seat, in-round lines are the point (e.g. `round 1 · codex … running`,
    `round 1 · codex ✓ 186s`). Stage started/done lines are terse phase markers.
    These are ADDITIVE — no existing pinned stdout line is touched — so they never
    need to match a golden; the round tables + `=== round N ===` banners the
    conductor already prints are unchanged."""
    glyph = _STATE_GLYPH.get(state, "·")
    if stage == "round" and seat is not None:
        head = f"round {round_no} · {seat}"
        if state == "running":
            return f"  {head} {glyph} running"
        if state == "done":
            return f"  {head} {glyph} {detail}" if detail else f"  {head} {glyph} done"
        if state == "dropped":
            return f"  {head} {glyph} dropped" + (f" ({detail})" if detail else "")
        if state == "retry":
            return f"  {head} {glyph} retry" + (f" ({detail})" if detail else "")
        return None   # queued: no line (the banner already announced the round)
    if stage == "round" and seat is None:
        return None   # round started/done: the conductor's own banner/table covers it
    if state == "started":
        return f"  · {stage} …"
    if state == "done" and stage not in ("run", "round"):
        return f"  · {stage} {glyph}"
    return None


def event_tuples(doc: dict) -> list:
    """The ordered (stage, seat, round, state) tuples of a status document — the
    stable surface the event-sequence golden asserts (never the timestamps).

    Defensive against a hand-authored/corrupted status.json: a non-dict `doc`, a
    non-list `events`, or a non-dict entry yields no tuples (rather than an
    AttributeError/KeyError), and a well-shaped entry missing a key reads it as
    None via `.get` — the same isinstance-guard discipline the verdict readers use."""
    if not isinstance(doc, dict):
        return []
    events = doc.get("events")
    if not isinstance(events, list):
        return []
    return [(e.get("stage"), e.get("seat"), e.get("round"), e.get("state"))
            for e in events if isinstance(e, dict)]


# --------------------------------------------------------------------------- #
# The self-refreshing HTML tracker — a PURE function of the status dict.
# --------------------------------------------------------------------------- #

_SEAT_STATE_CLASS = {
    "waiting": "st-wait",
    "queued": "st-queued",
    "running": "st-run",
    "done": "st-done",
    "dropped": "st-drop",
    "retry": "st-retry",
    "skipped": "st-skip",
}
_SEAT_STATE_LABEL = {
    "waiting": "waiting",
    "queued": "queued",
    "running": "running",
    "done": "done",
    "dropped": "dropped",
    "retry": "retrying",
    "skipped": "skipped",
}


def _esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def render_status_html(doc: dict) -> str:
    """Render the live tracker as a self-contained, deterministic HTML page from
    the status dict. Pure function (no clock, no I/O) — the ONLY nondeterminism is
    whatever stamps the doc already carries, and those are printed as opaque text,
    never computed here. Reuses the repo's dark/compact visual convention loosely;
    inline CSS only, no external fonts/CDNs/JS-src, renders offline.

    Self-refreshing via <meta http-equiv="refresh" content="2"> — file:// JS can't
    fetch a sibling json in modern browsers, so the state is inlined and the page
    reloads itself every 2s; the conductor regenerates this file on each event, so
    each reload shows the latest state. It is a LIVE VIEW, not an artifact of
    record (the footer says so).

    Defensive against a hand-authored/corrupted status.json (this reader has no CLI
    surface — it is only ever driven by the tracker's own well-formed doc and by
    tests — but a malformed dict must still render a MINIMAL valid page, never raise):
    the seats/events containers and every entry are isinstance-guarded and malformed
    entries are skipped, matching the verdict readers' guard style. A non-dict `doc`
    is normalized to an empty doc so the page is a valid 'no seats / no events' shell."""
    if not isinstance(doc, dict):
        doc = {}
    title = _esc(doc.get("title", "advisory board run"))
    finished = doc.get("finished")
    outcome = doc.get("outcome")
    stage = doc.get("stage")
    rounds_planned = doc.get("rounds_planned")
    rounds_done = doc.get("rounds_done", 0)
    seats = doc.get("seats")
    if not isinstance(seats, dict):
        seats = {}

    running = finished is None
    # Only self-refresh while the run is live; a completed run's page is static.
    meta_refresh = '<meta http-equiv="refresh" content="2">' if running else ""
    if running:
        status_word = "running"
        status_class = "run"
        stage_txt = f"stage: {_esc(stage)}" if stage else "starting…"
    else:
        status_word = _esc(outcome or "done")
        status_class = "done" if (outcome is None or outcome in _SUCCESS_OUTCOMES) else "drop"
        stage_txt = f"finished {_esc(finished)}"

    seat_rows = []
    for sid, s in seats.items():
        if not isinstance(s, dict):
            s = {}   # a corrupted seat entry renders as a bare "waiting" row, never raises
        st = s.get("state", "waiting")
        cls = _SEAT_STATE_CLASS.get(st, "st-wait")
        label = _SEAT_STATE_LABEL.get(st, st)
        rnd = s.get("round")
        rnd_txt = f"round {_esc(rnd)}" if rnd is not None else "—"
        detail = s.get("detail")
        detail_txt = _esc(detail) if detail else ""
        seat_rows.append(
            f'      <tr class="{cls}"><td class="seat">{_esc(sid)}</td>'
            f'<td class="state">{_esc(label)}</td>'
            f'<td class="round">{rnd_txt}</td>'
            f'<td class="detail">{detail_txt}</td></tr>'
        )
    seats_html = "\n".join(seat_rows) or (
        '      <tr><td class="seat" colspan="4">no seats yet</td></tr>')

    # The recent event log — newest last, capped so a long auto run stays compact.
    events = doc.get("events")
    if not isinstance(events, list):
        events = []
    tail = [e for e in events[-14:] if isinstance(e, dict)]
    ev_rows = []
    for e in tail:
        who = e.get("seat") or e.get("stage")
        rnd = e.get("round")
        where = f'r{_esc(rnd)}' if rnd is not None else "·"
        ev_rows.append(
            f'      <li><span class="ev-where">{where}</span>'
            f'<span class="ev-who">{_esc(who)}</span>'
            f'<span class="ev-state ev-{_esc(e.get("state"))}">{_esc(e.get("state"))}</span>'
            f'<span class="ev-detail">{_esc(e.get("detail") or "")}</span></li>'
        )
    events_html = "\n".join(ev_rows) or '      <li>(no events yet)</li>'

    rp = "?" if rounds_planned is None else _esc(rounds_planned)
    started = _esc(doc.get("started"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{meta_refresh}
<title>{title} — live status</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 1.4rem 1.2rem 2rem;
    background: #0b0e17; color: #e6e9f2;
    font: 14px/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }}
  header {{ display: flex; align-items: baseline; gap: .8rem; flex-wrap: wrap;
           border-bottom: 1px solid #1e2740; padding-bottom: .7rem; }}
  h1 {{ font-size: 1.05rem; margin: 0; font-weight: 600; letter-spacing: .01em; }}
  .badge {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
           padding: .18rem .5rem; border-radius: 999px; font-weight: 700; }}
  .badge.run {{ background: #12305c; color: #7fb2ff; }}
  .badge.done {{ background: #143a2a; color: #74e0a3; }}
  .badge.drop {{ background: #3a1a1e; color: #ff9aa6; }}
  .sub {{ color: #8b93a7; font-size: .82rem; }}
  .meta {{ color: #8b93a7; font-size: .8rem; margin: .55rem 0 1.1rem; }}
  h2 {{ font-size: .76rem; text-transform: uppercase; letter-spacing: .09em;
        color: #7a8199; margin: 1.3rem 0 .5rem; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 720px; }}
  td {{ padding: .34rem .6rem; border-bottom: 1px solid #161d31; }}
  td.seat {{ font-weight: 600; color: #cdd4e6; width: 8rem; }}
  td.round {{ color: #8b93a7; width: 6rem; }}
  td.detail {{ color: #8b93a7; }}
  tr.st-run td.state {{ color: #7fb2ff; }}
  tr.st-done td.state {{ color: #74e0a3; }}
  tr.st-drop td.state {{ color: #ff9aa6; }}
  tr.st-retry td.state {{ color: #e2b658; }}
  tr.st-queued td.state, tr.st-wait td.state {{ color: #8b93a7; }}
  ul.events {{ list-style: none; margin: 0; padding: 0; max-width: 720px; }}
  ul.events li {{ display: flex; gap: .7rem; padding: .2rem .1rem;
                  border-bottom: 1px solid #12182a; align-items: baseline; }}
  .ev-where {{ color: #6b768f; width: 2.4rem; }}
  .ev-who {{ color: #cdd4e6; width: 8rem; font-weight: 600; }}
  .ev-state {{ width: 5rem; }}
  .ev-running, .ev-started {{ color: #7fb2ff; }}
  .ev-done {{ color: #74e0a3; }}
  .ev-dropped {{ color: #ff9aa6; }}
  .ev-retry {{ color: #e2b658; }}
  .ev-detail {{ color: #8b93a7; }}
  footer {{ margin-top: 1.8rem; padding-top: .8rem; border-top: 1px solid #1e2740;
            color: #6b768f; font-size: .74rem; max-width: 720px; }}
</style>
</head>
<body>
  <header>
    <h1>{title}</h1>
    <span class="badge {status_class}">{status_word}</span>
    <span class="sub">{stage_txt}</span>
  </header>
  <div class="meta">started {started} · rounds {_esc(rounds_done)} / {rp}</div>

  <h2>Seats</h2>
  <table>
    <tbody>
{seats_html}
    </tbody>
  </table>

  <h2>Recent events</h2>
  <ul class="events">
{events_html}
  </ul>

  <footer>
    Live view — self-refreshing every 2s while the run is active. This is a
    progress tracker, <strong>not an artifact of record</strong>: the verdict
    chain (<code>verdict.json</code> → <code>final-consensus.md</code>) and
    <code>run-metadata.md</code> are the authoritative outputs. Advisory Board,
    powered by Panely.
  </footer>
</body>
</html>
"""

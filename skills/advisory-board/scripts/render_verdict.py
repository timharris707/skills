#!/usr/bin/env python3
"""Render the human-facing consensus FROM the canonical verdict.json.

The verdict.json is the source of truth (design section 9); the Markdown and HTML
are *views* of it. This renders:

  * final-consensus.md   - always; the decision, the blockers with their resolved
                           evidence, the preserved dissent, the couldn't-verify
                           bucket, the open questions, and the next actions.
  * handoff-data.json    - with --handoff-data; a derived input for render_handoff.py
                           so the HTML, too, renders FROM the verdict. Per-round prose
                           is pulled from a run dir's round-N/<seat>.md when --run is
                           given, else replaced with a pointer - never invented. The
                           narrative the JSON references stays in the artifacts; we do
                           not flatten it into the schema (section 9: don't over-flatten).
  * final-consensus.html - with --html; same mapping, rendered through render_handoff.py.

A third shape, `implementation-sequence`, renders the same verdict as a
sequence-first view — the ordered next actions (with owners where the verdict
names them) leading, backed by the blockers each step must clear with their
evidence trails. Markdown and HTML, both deterministic from verdict.json.

Usage:
  render_verdict.py verdict.json                              -> final-consensus.md
  render_verdict.py verdict.json -o consensus.md
  render_verdict.py verdict.json --check                      print to stdout, write nothing
  render_verdict.py verdict.json --handoff-data handoff-data.json [--run RUNDIR]
  render_verdict.py verdict.json --html final-consensus.html [--run RUNDIR]
  render_verdict.py verdict.json --shape implementation-sequence \
      --html implementation-sequence.html                     -> implementation-sequence.md + .html

Exit codes: 0 ok, 2 usage / data error.
Standard library only; no third-party dependencies.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _render_engine import die  # noqa: E402  shared with the other renderers
from board_verdict import effective_confidence  # noqa: E402  the ONE amended-confidence source (v1.12 P4)
from _verdict_labels import (  # noqa: E402  lens-aware label + framing (renderer-only)
    blockers_heading,
    human_label,
    lens_disclaimer,
    verdict_lead,
)
from _conductor.constants import (  # noqa: E402  v1.11 cost transparency (stdlib-only module)
    PRICING_AS_OF,
    price_band_usd,
)
from _conductor.delta import (  # noqa: E402  v1.12: mechanical cross-run delta (stdlib-only)
    DELTA_CONTAINERS,
    verdict_delta,
)
from _conductor.redline import (  # noqa: E402  v1.13 P3: prose redline rows (stdlib-only)
    REDLINE_MAX_LINES,
    build_redline,
)
from _conductor.revise import SOURCE_MATERIAL_FILENAME  # noqa: E402  the persisted source copy

STATUS_WORD = {"verified": "verified", "unverified": "unverified", "refuted": "REFUTED"}
EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")


def load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        die(f"{path}: not found")
    except json.JSONDecodeError as exc:
        die(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        die(f"{path}: top level must be a JSON object")
    if "verdict" not in data:
        die(f"{path}: missing required field 'verdict'")
    return data


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #


def _seats_line(data: dict) -> str:
    parts = []
    for seat in data.get("board", []):
        name = seat.get("seat", "?")
        lens = seat.get("lens")
        model = seat.get("model")
        tag = "/".join(x for x in (lens, model) if x)
        parts.append(f"{name} ({tag})" if tag else name)
    return " · ".join(parts)


def _stance(data: dict) -> str:
    if "unanimous" in data:
        return "unanimous" if data.get("unanimous") else "split board"
    ran = [s for s in data.get("board", []) if not s.get("dropped")]
    finals = {s["round_verdicts"][-1] for s in ran if s.get("round_verdicts")}
    return "unanimous" if finals == {data.get("verdict")} else "split board"


def _evidence_label(ev: dict) -> str:
    kind = ev.get("kind")
    if kind == "code":
        loc = f"{ev.get('path', '?')}:{ev['line']}" if "line" in ev else f"{ev.get('path', '?')}::{ev.get('symbol', '?')}"
        return f"`{loc}` (code)"
    if kind == "source":
        quote = ev.get("quote", "")
        snippet = quote if len(quote) <= 60 else quote[:57] + "..."
        return f"{ev.get('url', '?')} — “{snippet}” (source)"
    if kind == "command":
        return f"`{ev.get('command', '?')}` (command)"
    return f"judgment{(' — ' + ev['detail']) if ev.get('detail') else ''}"


def _evidence_trail(ev: dict) -> str:
    status = ev.get("status")
    badge = f" — {STATUS_WORD.get(status, status)}" if status else " — unchecked"
    if ev.get("kind") == "judgment":
        badge = ""  # judgment has no external referent to resolve
    return _evidence_label(ev) + badge


def _valid_snippet(snip) -> bool:
    """True when `snip` is a well-formed captured snippet: a dict with a non-empty
    `text` str and integer `from`/`to` (bool-guarded) with 1 ≤ from ≤ to. Anything
    malformed (missing from/to, text-only, bool line number, from>to, non-dict)
    renders the evidence line WITHOUT the snippet rather than crashing — the
    standalone `render_verdict.py verdict.json` path never runs the schema
    validator, so a hand-authored/fuzzed snippet must degrade, not traceback."""
    if not isinstance(snip, dict):
        return False
    text = snip.get("text")
    if not isinstance(text, str) or not text:
        return False
    frm, to = snip.get("from"), snip.get("to")
    if isinstance(frm, bool) or not isinstance(frm, int) or frm < 1:
        return False
    if isinstance(to, bool) or not isinstance(to, int) or to < frm:
        return False
    return True


def _snippet_fence(text: str) -> str:
    """A CommonMark-safe code fence for `text`: a backtick run STRICTLY LONGER than
    the longest backtick run inside the snippet (minimum 3). A captured source line
    containing ``` (7 files in this repo's scripts/ do) would close a hardcoded
    3-backtick fence early and derail the whole document; a longer fence can't be
    closed by any run the text contains."""
    longest = 0
    run = 0
    for ch in text:
        if ch == "`":
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    return "`" * max(3, longest + 1)


def _evidence_snippet_md_lines(ev: dict, indent: str = "     ") -> list:
    """The fenced snippet block for an evidence entry that carries one (v1.13 P3),
    or [] — so an entry without a snippet (or a malformed one) renders
    byte-identically to the pre-snippet output. Labeled `path:from-to`, the verbatim
    lines fenced with a backtick run longer than any inside them (so a snippet
    containing ``` can't break out): the handoff is self-contained without the repo.
    `indent` aligns it under the evidence bullet."""
    snip = ev.get("snippet")
    if not _valid_snippet(snip):
        return []
    text = str(snip["text"])
    fence = f"{indent}{_snippet_fence(text)}"
    label = f"{indent}{ev.get('path', '?')}:{snip['from']}-{snip['to']}:"
    lines = [label, fence]
    lines += [indent + line for line in text.split("\n")]
    lines.append(fence)
    return lines


def _iter_evidence(data: dict):
    for key in EVIDENCE_CONTAINERS:
        for item in (data.get(key) or []):
            if isinstance(item, dict):
                for ev in (item.get("evidence") or []):
                    if isinstance(ev, dict):
                        yield ev
    for ev in (data.get("evidence") or []):
        if isinstance(ev, dict):
            yield ev


# --------------------------------------------------------------------------- #
# Amendments (v1.12 P4): human-owned, append-only verdict tuning. Renderers show
# the EFFECTIVE value WITH provenance — never an amended value as the board's own.
# The verdict dict is NEVER mutated; every function here derives its display.
# --------------------------------------------------------------------------- #


def _flat(text) -> str:
    """Collapse every whitespace run (newlines included) in human-typed amendment
    text to a single space. Amendment strings (author, reason, caveat, severity
    note, `on`) land inside Markdown list items / headings, where a raw newline
    would let a crafted value inject a `## heading` or a new list. Applied at EVERY
    Markdown emission point for amendment-sourced text; the HTML path is separately
    escaped (html.escape), so it does not use this."""
    return " ".join(str(text).split())


def _confidence_clause(data: dict) -> str:
    """The `(… confidence[ — amended …])` parenthetical for a verdict heading, or "".

    Byte-identical to pre-v1.12 (`(high confidence)`) with no confidence amendment:
    a NO-amendments verdict is unchanged. With one, it shows the EFFECTIVE value and
    its provenance so an amended confidence never reads as the board's own call. When
    confidence is untracked (no board value AND no amendment) the clause drops."""
    value, entry = effective_confidence(data) if "confidence" in data else (None, None)
    if not value:
        return ""
    if entry is not None:
        return (f" ({value} confidence — amended from {_flat(entry['from'])} by "
                f"{_flat(entry['author'])}, {_flat(entry['timestamp'])})")
    return f" ({value} confidence)"


def _amendment_caveat_lines(data: dict) -> list:
    """Standing caveats added by a human amendment, each marked human-added with its
    author — so they read alongside the board's own caveats but never as the board's.
    [] with no caveat amendments, so the couldn't-verify bucket is byte-identical."""
    lines = []
    for entry in (data.get("amendments") or []):
        if isinstance(entry, dict) and "caveat" in entry:
            lines.append(f"{_flat(entry['caveat'])} — added by "
                         f"{_flat(entry.get('author', '?'))} (amendment)")
    return lines


def _severity_notes_for(data: dict, title: str) -> list:
    """Severity-note amendments scoped to a finding by an EXACT `on` title match.
    A note without `on` (or with an unmatched `on`) never attaches here — it lands
    in the Amendments section only. [] when nothing matches (findings unchanged)."""
    notes = []
    for entry in (data.get("amendments") or []):
        if (isinstance(entry, dict) and "severity_note" in entry
                and entry.get("on") == title):
            notes.append(entry)
    return notes


def _amendment_effect(entry: dict) -> str:
    """One-line human description of what an amendment did — for the Amendments trail.
    A zero-effect (provenance-only) entry has no effect to show and returns ""."""
    if entry.get("field") == "confidence":
        return f"Confidence: {entry.get('from', '?')} → {entry.get('to', '?')}"
    if "caveat" in entry:
        return f"Added caveat: {entry['caveat']}"
    if "severity_note" in entry:
        on = entry.get("on")
        scope = f' on "{on}"' if on else ""
        return f"Severity note{scope}: {entry['severity_note']}"
    return ""


def render_amendments_markdown(data: dict) -> list:
    """The '## Amendments' lines — the full human-owned trail (author, timestamp,
    reason, and the effect), one entry per amendment, IN ORDER. [] when there are no
    amendments, so a verdict without them renders byte-identically. A zero-effect
    entry renders as a provenance-only note (its reason, no effect line)."""
    amendments = data.get("amendments") or []
    if not amendments:
        return []
    out = ["## Amendments",
           "_Human-owned tuning applied after the board reported. "
           "The board's own words above are unchanged._"]
    for entry in amendments:
        if not isinstance(entry, dict):
            continue
        who = _flat(entry.get("author", "?"))
        when = _flat(entry.get("timestamp", "?"))
        out.append(f"- **{who}, {when}** — {_flat(entry.get('reason', ''))}")
        # _amendment_effect composes amendment text (caveat / note / from→to); flatten
        # the whole line so a newline in any part can't break out of the list item.
        effect = _flat(_amendment_effect(entry))
        if effect:
            out.append(f"  - {effect}")
    out.append("")
    return out


def _load_previous_verdict(data: dict):
    """(prior verdict dict, None) when `previous_run` points at a readable
    verdict.json that matches the recorded verdict_sha256 (when recorded);
    (None, reason) otherwise. Deterministic for a given filesystem state — the
    delta is DERIVED from the two verdicts at render time, never stored (D8:
    verdict.json carries lineage, not a rendering)."""
    prev = data.get("previous_run")
    if not isinstance(prev, dict) or not prev.get("run_dir"):
        return None, None
    path = os.path.join(os.path.expanduser(str(prev["run_dir"])), "verdict.json")
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
        prior = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, (f"prior run not reachable at {prev['run_dir']} — "
                      "delta not shown (lineage above still stands)")
    want = prev.get("verdict_sha256")
    if want and hashlib.sha256(raw).hexdigest() != want:
        return None, ("prior verdict.json no longer matches the recorded "
                      "verdict_sha256 — delta not shown (the prior run's "
                      "artifacts changed after this run revised them)")
    if not isinstance(prior, dict):
        return None, "prior verdict.json is not an object — delta not shown"
    return prior, None


_DELTA_BUCKETS = (("cleared", "Cleared"), ("still_open", "Still open"), ("new", "New"))


def _delta_item_title(entry) -> str:
    """The display title for a delta entry. still_open entries are
    {prior, current, matched_by} — show the CURRENT wording."""
    item = entry.get("current", entry) if isinstance(entry, dict) and "current" in entry else entry
    if isinstance(item, dict):
        return item.get("title") or "(untitled)"
    return str(item)


def _trajectory_labels(prior: dict, data: dict):
    frm, _ = human_label(prior.get("verdict"), prior.get("lens_preset"), prior.get("decision"))
    to, _ = human_label(data.get("verdict"), data.get("lens_preset"), data.get("decision"))
    return frm, to


def render_delta_markdown(data: dict) -> list:
    """The '## Delta vs the previous run' lines; [] when this verdict has no
    `previous_run` (so a non-revise consensus stays byte-identical)."""
    prev = data.get("previous_run")
    if not isinstance(prev, dict):
        return []
    out = ["## Delta vs the previous run"]
    when = f" ({prev['date']})" if isinstance(prev.get("date"), str) and prev["date"] else ""
    out.append(f"Revises: {prev.get('run_dir', '?')}{when}")
    prior, problem = _load_previous_verdict(data)
    if prior is None:
        out.append(f"_{problem or 'prior run reference incomplete — delta not shown'}_")
        out.append("")
        return out
    delta = verdict_delta(prior, data)
    frm, to = _trajectory_labels(prior, data)
    out.append(f"**Trajectory: {frm} → {to}**")
    for container in DELTA_CONTAINERS:
        buckets = delta[container]
        for key, label in _DELTA_BUCKETS:
            entries = buckets[key]
            if not entries:
                continue
            out.append(f"{label} {container} ({len(entries)}):")
            out += [f"- {_delta_item_title(entry)}" for entry in entries]
    out.append("")
    return out


def render_markdown(data: dict) -> str:
    out = ["# Advisory Board — Final Consensus"]
    if data.get("title"):
        out.append(data["title"])
    seats = _seats_line(data)
    rounds = data.get("rounds", "?")
    out.append(f"Board: {seats}. Rounds: {rounds}.")
    out.append("")

    label, note = human_label(data.get("verdict"), data.get("lens_preset"), data.get("decision"))
    # The confidence clause shows the EFFECTIVE value (amended value + provenance when a
    # human tuned it), or the board's own; it drops entirely when confidence is untracked —
    # matching the HTML handoff's clean-drop of the pill — never a literal "? confidence".
    conf_clause = _confidence_clause(data)
    out.append(f"## Verdict: {label} — {_stance(data)}{conf_clause}")
    # Lead with the plain should-I/shouldn't-I answer on a non-software lens. The heading
    # keeps the calibrated label (the machine-friendly anchor); this bold line answers
    # the reader's actual question. Suppressed when the board authored its own
    # `decision` (the heading already leads with it) and for a software lens.
    lead = verdict_lead(data.get("verdict"), data.get("lens_preset"), data.get("decision"))
    if lead and not data.get("decision"):
        out.append(f"**{lead}.**")
    # An explicit verdict_note (authored in the verdict.json) wins; else the plain
    # "what this means" line a non-software lens supplies.
    note = data.get("verdict_note") or note
    if note:
        out.append(note)
    out.append("")

    # --revise runs only (previous_run present): the cross-run delta, right under
    # the verdict so the trajectory reads first. Absent on every other verdict.
    out += render_delta_markdown(data)

    blockers = data.get("blockers", [])
    if blockers:
        out.append(f"## {blockers_heading(data.get('lens_preset'), 'md')}")
        for index, blocker in enumerate(blockers, 1):
            title = blocker.get("title", "blocker")
            body = blocker.get("body", "")
            out.append(f"{index}. {title}" + (f" — {body}" if body else ""))
            for ev in (blocker.get("evidence") or []):
                if isinstance(ev, dict):
                    out.append(f"   - evidence: {_evidence_trail(ev)}")
                    out += _evidence_snippet_md_lines(ev)
            # A human severity note scoped to THIS blocker (exact --on title match).
            for note in _severity_notes_for(data, title):
                out.append(f"   - severity note: {_flat(note['severity_note'])} "
                           f"— added by {_flat(note.get('author', '?'))} (amendment)")
        out.append("")

    dissent = data.get("dissent", [])
    if dissent:
        out.append("## Hard dissent (preserved)")
        for entry in dissent:
            who = entry.get("who", "-")
            out.append(f"- {who}: {entry.get('body', '')}")
        out.append("")

    couldnt = _couldnt_verify_lines(data)
    if couldnt:
        out.append("## What the board couldn't verify")
        out += [f"- {line}" for line in couldnt]
        out.append("")

    questions = data.get("open_questions", [])
    if questions:
        out.append("## Open questions")
        out += [f"- {q}" for q in questions]
        out.append("")

    actions = data.get("next_actions", [])
    if actions:
        out.append("## Next actions")
        out += [f"- {_action_line(a)}" for a in actions]
        out.append("")

    # The human-owned amendment trail (v1.12 P4). Empty on a verdict with no
    # amendments, so nothing changes for those.
    out += render_amendments_markdown(data)

    if any(True for _ in _iter_evidence(data)):
        out.append("---")
        out.append("_Evidence status is a resolution check — it confirms the cited line exists "
                   "or the quote is present in the captured material. It does not prove the "
                   "inference drawn from it is sound (design §9)._")
        out.append("")

    # A subtle, lens-aware professional-advice caveat in the footer. None for a
    # software lens (and the absent-preset default), so existing software runs are
    # unchanged. Separated by its own rule so it reads as a footnote, not the verdict.
    disclaimer = lens_disclaimer(data.get("lens_preset"))
    if disclaimer:
        out.append("---")
        out.append(f"_{disclaimer}_")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _couldnt_verify_lines(data: dict) -> list:
    """The honesty bucket: authored caveats plus any unverified/refuted citation, then
    any human-added caveat amendments (each marked human-added with its author). The
    amendment lines are appended, so with no caveat amendments the bucket is
    byte-identical to pre-v1.12."""
    lines = []
    for caveat in (data.get("caveats") or []):
        if isinstance(caveat, str):
            lines.append(caveat)
        elif isinstance(caveat, dict):
            claim = caveat.get("claim", "")
            impact = caveat.get("impact", "")
            lines.append(claim + (f" — {impact}" if impact else ""))
    for ev in _iter_evidence(data):
        if ev.get("status") in ("unverified", "refuted"):
            lines.append(f"{_evidence_label(ev)} {_resolution_verb(ev)}.")
    lines += _amendment_caveat_lines(data)
    return lines


def _resolution_verb(ev: dict) -> str:
    """A kind-aware verb for an unverified/refuted citation. A `command` that ran and
    contradicted its expectation is NOT 'not found' — surface the observed exit so the
    receipt reaches the consensus doc, not just verdict.json."""
    status = ev.get("status")
    is_command = ev.get("kind") == "command"
    observed = ev.get("observed") if isinstance(ev.get("observed"), dict) else {}
    if status == "unverified":
        if is_command:
            return "could not be re-executed (off-allowlist or not runnable)"
        return "could not be resolved"
    # refuted
    if is_command and "exit" in observed:
        detail = f"exit {observed['exit']}"
        if observed.get("expect_found") is False:
            detail += ", expected output absent"
        return f"was REFUTED on re-execution ({detail})"
    return "was REFUTED (cited line/quote not found in the material)"


# --------------------------------------------------------------------------- #
# implementation-sequence — the sequence-first shape (md; the HTML renders via
# render_handoff.py against references/implementation-sequence-template.html)
# --------------------------------------------------------------------------- #


def _action_fields(action) -> tuple:
    """Normalize a next_actions[] entry to (text, owner).

    The schema's next_actions are strings; an entry MAY instead be an object
    naming an owner — `{"action": "...", "owner": "..."}` (`title` accepted as
    the text fallback). Anything else degrades to its string form, never a crash."""
    if isinstance(action, dict):
        text = action.get("action") or action.get("title") or ""
        owner = action.get("owner") or ""
        return str(text), str(owner)
    return str(action), ""


def _action_line(action) -> str:
    """A next_actions[] entry as one display line — byte-identical for the plain
    string form; an owner-carrying object renders `text — owner: NAME`."""
    text, owner = _action_fields(action)
    return f"{text} — owner: {owner}" if owner else text


def render_sequence_markdown(data: dict) -> str:
    """The implementation-sequence view of the SAME verdict.json: the ordered next
    actions lead (with owners where the verdict names them), backed by the blockers
    the sequence must clear, each with its evidence trail. A deterministic VIEW —
    it reorders what the verdict already says and adds nothing."""
    out = ["# Advisory Board — Implementation Sequence"]
    if data.get("title"):
        out.append(data["title"])
    out.append(f"Board: {_seats_line(data)}. Rounds: {data.get('rounds', '?')}.")
    out.append("")

    # The verdict context stays on top — a sequence without the board's call would
    # misrepresent a block as a green light. Same labels/lead/note as the consensus.
    label, note = human_label(data.get("verdict"), data.get("lens_preset"), data.get("decision"))
    conf_clause = _confidence_clause(data)
    out.append(f"## Verdict: {label} — {_stance(data)}{conf_clause}")
    lead = verdict_lead(data.get("verdict"), data.get("lens_preset"), data.get("decision"))
    if lead and not data.get("decision"):
        out.append(f"**{lead}.**")
    note = data.get("verdict_note") or note
    if note:
        out.append(note)
    out.append("")

    out.append("## The sequence — in order")
    actions = data.get("next_actions", [])
    if actions:
        for index, action in enumerate(actions, 1):
            out.append(f"{index}. {_action_line(action)}")
    else:
        out.append("_The verdict lists no next actions — see the full handoff._")
    out.append("")

    blockers = data.get("blockers", [])
    if blockers:
        out.append("## What the sequence must clear")
        for index, blocker in enumerate(blockers, 1):
            title = blocker.get("title", "blocker")
            body = blocker.get("body", "")
            out.append(f"{index}. {title}" + (f" — {body}" if body else ""))
            for ev in (blocker.get("evidence") or []):
                if isinstance(ev, dict):
                    out.append(f"   - evidence: {_evidence_trail(ev)}")
                    out += _evidence_snippet_md_lines(ev)
            for note in _severity_notes_for(data, title):
                out.append(f"   - severity note: {_flat(note['severity_note'])} "
                           f"— added by {_flat(note.get('author', '?'))} (amendment)")
        out.append("")

    # The human-owned amendment trail (v1.12 P4). Empty without amendments.
    out += render_amendments_markdown(data)

    if any(isinstance(ev, dict) for b in blockers if isinstance(b, dict)
           for ev in (b.get("evidence") or [])):
        out.append("---")
        out.append("_Evidence status is a resolution check — it confirms the cited line exists "
                   "or the quote is present in the captured material. It does not prove the "
                   "inference drawn from it is sound (design §9)._")
        out.append("")

    disclaimer = lens_disclaimer(data.get("lens_preset"))
    if disclaimer:
        out.append("---")
        out.append(f"_{disclaimer}_")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


# --------------------------------------------------------------------------- #
# handoff-data.json (so render_handoff.py can produce the HTML from the verdict)
# --------------------------------------------------------------------------- #

_VERDICT_CLASS = {"ship": "ship", "caution": "caution", "block": "block"}


_ZW = "​"  # zero-width space


def _nb(text: str) -> str:
    """Neutralize render_handoff's `{{TOKEN}}` sentinel so literal braces in user content
    (a plan quoting a template, a Jinja/env snippet) can't survive into the HTML and trip
    its leftover-token guard (which dies — aborting --html). Inserting a zero-width space
    after each `{` breaks every brace adjacency; the visible text is unchanged. Works in
    both pass-through (RAW) and renderer-escaped (non-RAW) slots — the ZWSP survives
    html.escape, so the same string is safe either way."""
    return str(text).replace("{", "{" + _ZW)


def _raw(text: str) -> str:
    """For a render_handoff RAW (pass-through HTML) slot: HTML-escape, then neutralize braces."""
    return _nb(html.escape(text))


def _evidence_html(ev: dict) -> str:
    """An evidence trail line for a RAW HTML slot: the Markdown trail (_evidence_trail),
    HTML-escaped, its backtick spans upgraded to <code>, braces neutralized."""
    line = html.escape(_evidence_trail(ev))
    line = re.sub(r"`([^`]*)`", r"<code>\1</code>", line)
    return _nb(line)


def _plain(text: str) -> str:
    """For a render_handoff non-RAW slot (the renderer html-escapes it): neutralize braces only."""
    return _nb(text)


def _oneliner(text: str, limit: int = 180) -> str:
    """Collapse a blocker/dissent body to ONE plain-text line for the quick-verdict brief.

    Strips leading list markers and inline markdown (per-line leading "-"/"•" bullets, and
    the `* ` backtick `#` `>` characters), collapses all whitespace/newlines to single
    spaces, and trims. If the result is longer than `limit`, it is cut at the last word
    boundary <= limit and an ellipsis is appended. Returns "" for empty/whitespace input."""
    if not text or not str(text).strip():
        return ""
    lines = []
    for line in str(text).splitlines():
        # Drop a leading bullet marker ("-", "•", "*") and surrounding space per line.
        line = re.sub(r"^\s*[-•*]\s+", "", line)
        lines.append(line)
    joined = " ".join(lines)
    # Strip the remaining inline-markdown punctuation (emphasis, code, headings, quotes).
    joined = re.sub(r"[*`#>]", "", joined)
    collapsed = re.sub(r"\s+", " ", joined).strip()
    if len(collapsed) <= limit:
        return collapsed
    cut = collapsed[:limit]
    if " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip() + "…"


def _round_review(run_dir, seat_name: str, round_no: int, verdict: str) -> str:
    """The seat's round review as raw MARKDOWN. render_handoff.py owns the single
    Markdown->HTML conversion (its _md_review), so this must NOT pre-render HTML — a
    second conversion there would escape the tags into literal text. The full prose
    lives in the round-N/<seat>.md artifacts; when one is present we hand it back
    verbatim, else a Markdown pointer to it."""
    if run_dir:
        for candidate in glob.glob(os.path.join(run_dir, f"round-{round_no}", "*.md")):
            if os.path.splitext(os.path.basename(candidate))[0].lower() == seat_name.lower():
                try:
                    with open(candidate, encoding="utf-8", errors="replace") as handle:
                        return handle.read()
                except OSError:
                    break
    return (f"Round {round_no} verdict: **{verdict}**. "
            f"Full review in `round-{round_no}/{seat_name.lower()}.md`.")


def _seat_reported_token_totals(run_dir) -> "dict | None":
    """Best-effort token totals from the run's run-metadata.tsv (v1.11 #3a), or None.

    The conductor appends trailing token columns to run-metadata.tsv ONLY when a
    seat CLI actually reported usage. No run dir, no TSV, no token columns, or no
    known values → None, and the HTML footer stays byte-identical to the
    tokenless baseline. Column positions are resolved by header name, never by
    index, so this reads both TSV layouts.
    """
    if not run_dir:
        return None
    try:
        with open(os.path.join(run_dir, "run-metadata.tsv"), encoding="utf-8") as handle:
            lines = [ln for ln in handle.read().splitlines() if ln.strip()]
    except OSError:
        return None
    if not lines:
        return None
    header = lines[0].split("\t")
    if "tokens_total" not in header:
        return None
    idx = {name: i for i, name in enumerate(header)}

    def _cell_int(row: list, name: str):
        i = idx.get(name)
        if i is None or i >= len(row):
            return None
        raw = row[i].strip().replace(",", "")
        # isascii() guard: str.isdigit() accepts Unicode digit-class chars (e.g.
        # "²") that int() rejects — a malformed cell must degrade to None, not raise.
        return int(raw) if raw.isascii() and raw.isdigit() else None

    tokens = rows = known_rows = 0
    cost_low = cost_high = 0.0
    priced_any = False
    for ln in lines[1:]:
        row = ln.split("\t")
        rows += 1
        tin = _cell_int(row, "tokens_in")
        tout = _cell_int(row, "tokens_out")
        ttotal = _cell_int(row, "tokens_total")
        combined = ttotal if ttotal is not None else (
            tin + tout if tin is not None and tout is not None else None)
        if combined is None:
            continue
        known_rows += 1
        tokens += combined
        model_i = idx.get("model_requested")
        model = row[model_i] if model_i is not None and model_i < len(row) else ""
        band = price_band_usd(model, tin, tout, ttotal)
        if band is not None:
            cost_low += band[0]
            cost_high += band[1]
            priced_any = True
    if not known_rows:
        return None
    return {
        "tokens": tokens, "rows": rows, "known_rows": known_rows,
        "cost_low": cost_low if priced_any else None,
        "cost_high": cost_high if priced_any else None,
    }


def _token_totals_note(totals) -> str:
    """One footer segment for the seat-reported totals ("" when unknown)."""
    if not totals:
        return ""
    where_known = (" (where known — some seats reported no usage)"
                   if totals["known_rows"] < totals["rows"] else "")
    note = f"Seat-reported tokens{where_known}: {totals['tokens']:,}"
    if totals["cost_low"] is not None:
        if totals["cost_high"] - totals["cost_low"] < 0.005:
            band = f"~${totals['cost_low']:.2f}"
        else:
            band = f"~${totals['cost_low']:.2f}–${totals['cost_high']:.2f}"
        note += (f" · est. cost {band} at list prices dated {PRICING_AS_OF} "
                 "(an estimate, not a bill)")
    return note


# --------------------------------------------------------------------------- #
# Revision redline / patch (v1.13 P3, D12). A full-handoff-only VIEW of the
# board's revised draft, rendered ONLY when --run points at a sha-coherent
# revised-draft chain. The chain is verified end to end (verdict → changes →
# {source, revised}, PLUS source-material.txt ≡ changes.source.sha256) before any
# byte is diffed — any mismatch/missing artifact/malformed json degrades to the
# section being absent with one stderr warning (never a crash, never partial).
# --------------------------------------------------------------------------- #


def _redline_warn(reason: str) -> None:
    """One stderr warning when a present-but-incoherent revised chain drops the
    redline/patch section (revise.py's UNVERIFIED-posture precedent). Silent when
    there is simply no revision (the common case)."""
    print(f"note: revised-draft redline not rendered — {reason}", file=sys.stderr)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _confined_path(run_dir: str, artifact: str):
    """The `run_dir/artifact` path, realpath-confined to inside realpath(run_dir),
    or None when the artifact escapes it. Defense in depth INDEPENDENT of the
    validators (renderer robustness must not depend on validators having run): an
    absolute or `../escape` artifact — or one reached through a parent-dir symlink —
    resolves OUTSIDE run_dir and is refused here, so the renderer degrades to the
    section being absent rather than reading arbitrary bytes. The islink checks the
    callers already do catch a symlink AT the artifact path; this catches the
    absolute/parent-escape cases those miss."""
    root = os.path.realpath(run_dir)
    target = os.path.realpath(os.path.join(run_dir, artifact))
    root_prefix = root if root.endswith(os.sep) else root + os.sep
    if target == root or target.startswith(root_prefix):
        return target
    return None


def _load_revised_chain(data: dict, run_dir):
    """(source_text, revised_text, source_type, changes) when `data` carries a
    verdict→changes pointer AND the whole revised-draft chain is sha-coherent
    under `run_dir`; (None, reason) otherwise. Verifies, in order:

      * verdict.json.changes = {artifact, sha256} present and shaped;
      * changes.json bytes match verdict.changes.sha256;
      * changes.json validates (advisory-board/changes@1);
      * source-material.txt bytes hash to changes.source.sha256 (the equivalence
        the run persists but asserts NOWHERE — verified HERE, mirroring
        revise.prior_source_text: real file only, no symlink, sha compare);
      * revised-draft.<artifact> bytes match changes.revised.sha256.

    Returns None-reason (not raising) so the caller degrades to a dropped section.
    `run_dir` is required — the chain lives in files, and a verdict.json alone
    can't be trusted to still match its run's bytes."""
    changes_ptr = data.get("changes")
    if not isinstance(changes_ptr, dict):
        return None, None   # no revision on this verdict — silent, the common case
    if not run_dir:
        return None, ("the verdict points at a changes.json but no --run dir was "
                      "given to resolve it against")
    artifact = changes_ptr.get("artifact")
    want_changes_sha = changes_ptr.get("sha256")
    if (not isinstance(artifact, str) or not artifact
            or not isinstance(want_changes_sha, str)):
        return None, "verdict.changes pointer is malformed (need {artifact, sha256})"
    # 1. changes.json bytes ≡ verdict.changes.sha256.
    changes_path = _confined_path(run_dir, artifact)
    if changes_path is None:
        return None, (f"the verdict's changes pointer {artifact!r} resolves outside "
                      "the run dir — refused")
    if os.path.islink(os.path.join(run_dir, artifact)):
        return None, f"{artifact} is a symlink — refused"
    try:
        with open(changes_path, "rb") as handle:
            changes_raw = handle.read()
    except OSError as exc:
        return None, f"{artifact} not readable ({exc})"
    if _sha256_bytes(changes_raw) != want_changes_sha:
        return None, (f"{artifact} does not match the verdict's changes pointer "
                      "sha256 (the revision artifact changed after the pointer was written)")
    try:
        changes = json.loads(changes_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"{artifact} is not valid JSON ({exc})"
    # 2. changes.json validates against the @1 schema (loud beats garbage-in).
    try:
        import board_changes
    except ImportError as exc:
        return None, f"could not import board_changes to validate {artifact} ({exc})"
    import contextlib
    import io
    buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(buf):
            board_changes.validate(changes)
    except SystemExit:
        detail = buf.getvalue().strip() or "schema error"
        return None, f"{artifact} failed changes@1 validation ({detail})"
    source_pin = changes.get("source") or {}
    revised_pin = changes.get("revised") or {}
    want_source_sha = source_pin.get("sha256")
    revised_artifact = revised_pin.get("artifact")
    want_revised_sha = revised_pin.get("sha256")
    # 3. source-material.txt ≡ changes.source.sha256 — the equivalence the run
    #    persists but never asserts. The recorded sha is over the LF-normalized
    #    source TEXT (config.source.sha256), so hash the file's decoded text, not
    #    its raw bytes.
    src_path = os.path.join(run_dir, SOURCE_MATERIAL_FILENAME)
    if os.path.islink(src_path):
        return None, f"{SOURCE_MATERIAL_FILENAME} is a symlink — refused"
    try:
        with open(src_path, encoding="utf-8") as handle:
            source_text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"{SOURCE_MATERIAL_FILENAME} not readable ({exc})"
    if _sha256_bytes(source_text.encode("utf-8")) != want_source_sha:
        return None, (f"{SOURCE_MATERIAL_FILENAME} does not match changes.source.sha256 "
                      "(the persisted source is not the source the board reviewed)")
    # 4. revised-draft.<artifact> ≡ changes.revised.sha256.
    if not isinstance(revised_artifact, str) or not revised_artifact:
        return None, "changes.revised.artifact is missing"
    revised_path = _confined_path(run_dir, revised_artifact)
    if revised_path is None:
        return None, (f"changes.revised.artifact {revised_artifact!r} resolves "
                      "outside the run dir — refused")
    if os.path.islink(os.path.join(run_dir, revised_artifact)):
        return None, f"{revised_artifact} is a symlink — refused"
    try:
        with open(revised_path, "rb") as handle:
            revised_raw = handle.read()
    except OSError as exc:
        return None, f"{revised_artifact} not readable ({exc})"
    if _sha256_bytes(revised_raw) != want_revised_sha:
        return None, (f"{revised_artifact} does not match changes.revised.sha256 "
                      "(the revised draft on disk is not the one the board endorsed)")
    try:
        revised_text = revised_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, f"{revised_artifact} is not valid UTF-8 ({exc})"
    source_type = changes.get("source_type") or "prose"
    return source_text, revised_text, source_type, changes


def _redline_row_html(row: dict) -> str:
    """One redline row → a RAW HTML fragment (fully escaped + brace-neutralized).

    context/gap/delete/insert render the whole line; a replace row renders the
    original with `<del>` on its changed WORDS then the revised with `<ins>` on
    its changed words (D12: word-level within changed lines). Every text segment
    is html.escaped and brace-neutralized (`_nb`) before it lands in the fragment,
    so HTML-hostile source (`<script>`, `{{TOKEN}}`) can never survive into the
    handoff. A blank line renders a non-breaking space so the row keeps height."""
    kind = row["kind"]
    if kind in ("context", "gap", "delete", "insert"):
        cls = {"context": "rl-ctx", "gap": "rl-gap",
               "delete": "rl-del", "insert": "rl-ins"}[kind]
        text = _raw(row["text"]) or "&nbsp;"
        return f'<div class="rl-row {cls}">{text}</div>'
    # replace: two sub-rows (old with <del> spans, new with <ins> spans)
    del_html = _segment_html(row["del_segments"], "del") or "&nbsp;"
    ins_html = _segment_html(row["ins_segments"], "ins") or "&nbsp;"
    return (f'<div class="rl-row rl-del">{del_html}</div>'
            f'<div class="rl-row rl-ins">{ins_html}</div>')


def _segment_html(segments, tag: str) -> str:
    """Render `(changed, text)` segments: unchanged runs plain, changed runs
    wrapped in `<del>`/`<ins>`. Each run's text is escaped + brace-neutralized."""
    out = []
    for changed, text in segments:
        piece = _raw(text)
        out.append(f"<{tag}>{piece}</{tag}>" if changed and text else piece)
    return "".join(out)


def build_redline_rows(source_text: str, revised_text: str) -> "tuple":
    """(rows, truncated_note) for the prose redline block. `rows` is a list of
    {"redline_html": <RAW fragment>} for the template's REDLINE block; a non-empty
    `truncated_note` says how many rows were cut (with a pointer to the artifact)."""
    raw_rows, truncated, total = build_redline(source_text, revised_text)
    rows = [{"redline_html": _redline_row_html(r)} for r in raw_rows]
    note = ""
    if truncated:
        more = total - REDLINE_MAX_LINES
        note = (f"… {more} more changed line(s) — see revised-draft.md "
                f"(showing the first {REDLINE_MAX_LINES} of {total}).")
    return rows, note


def build_patch_html(source_text: str, revised_text: str, changes: dict) -> "tuple":
    """(patch_html, truncated_note) for the code fenced-patch block. The unified
    diff is rendered as one escaped `<pre>` (the template's existing code styling),
    capped at REDLINE_MAX_LINES diff lines with a pointer to the artifact. Built
    from the SAME pinned strings as revised-draft.patch — a rendering, no new trust
    surface."""
    from _conductor.revision import build_unified_patch
    name = (changes.get("source") or {}).get("name") or "source"
    patch = build_unified_patch(source_text, revised_text, name)
    lines = patch.splitlines()
    note = ""
    if len(lines) > REDLINE_MAX_LINES:
        more = len(lines) - REDLINE_MAX_LINES
        lines = lines[:REDLINE_MAX_LINES]
        note = (f"… {more} more patch line(s) — see revised-draft.patch "
                f"(showing the first {REDLINE_MAX_LINES}).")
    body = "\n".join(lines)
    return _raw(body), note


def _revision_handoff_fields(data: dict, run_dir, shape: str = "full-handoff") -> dict:
    """The redline/patch slots for the HTML handoff (v1.13 P3). All empty when
    there is no sha-coherent revised chain, so BOTH template sections drop and the
    page stays byte-identical to a non-revision run. At most ONE is populated: a
    prose chain fills the redline rows, a code chain fills the patch pre (D12 —
    two sibling sections, ins/del OR fenced patch, never both).

    The redline/patch view lives ONLY in the full-handoff template (Item 4): for
    the quick-verdict / implementation-sequence shapes the fields render nowhere, so
    we return them empty WITHOUT touching the revised-draft chain on disk — no
    changes.json / source-material / revised-draft reads, and NO spurious 'redline
    not rendered' warning when a --run points at a present-but-incoherent chain."""
    empty = {"redline_source_name": "", "redline_rows": [], "redline_note": "",
             "patch_pre": "", "patch_note": "", "endorsement_summary": ""}
    if shape != "full-handoff":
        return empty
    loaded = _load_revised_chain(data, run_dir)
    if loaded[0] is None:
        if loaded[1]:                    # present-but-incoherent chain: warn once
            _redline_warn(loaded[1])
        return empty
    source_text, revised_text, source_type, changes = loaded
    fields = dict(empty)
    name = (changes.get("source") or {}).get("name") or "source"
    if source_type == "code":
        patch_html, note = build_patch_html(source_text, revised_text, changes)
        fields["patch_pre"] = patch_html
        fields["patch_note"] = _plain(note) if note else ""
    else:
        rows, note = build_redline_rows(source_text, revised_text)
        fields["redline_rows"] = rows
        fields["redline_note"] = _plain(note) if note else ""
        fields["redline_source_name"] = _plain(name)
    # Endorsement outcomes (v1.13 P4, D13): a minimal per-edit position summary line
    # + any objection notes, surfaced in the redline/patch section header area. Empty
    # string when changes.json carries no endorsements — the {{ENDORSEMENT_SUMMARY}}
    # line then drops (drop_empty_optionals), keeping an endorsement-less run's HTML
    # byte-identical to a P2/P3 render.
    fields["endorsement_summary"] = build_endorsement_summary_html(changes)
    return fields


def _esc(text) -> str:
    """HTML-escape + brace-neutralize an untrusted string for a RAW slot we assemble
    ourselves (my structural tags pass through; only the interpolated model/seat text
    is escaped, so the fragment renders as HTML with the data escaped)."""
    return _nb(html.escape(str(text)))


def build_endorsement_summary_html(changes: dict) -> str:
    """A small RAW HTML block summarizing changes.json.endorsements (D13): one line
    per edit ("N endorse / M object / K abstain"), a line per unresolved conflict
    that drew votes, then any objection notes listed (seat + note). Returns "" when
    there are no endorsement rows — the template line drops and the page stays
    byte-identical to an endorsement-less render. Interpolated seat/note strings are
    HTML-escaped (`_esc`); the surrounding tags are ours and pass through."""
    rows = changes.get("endorsements") or []
    if not rows:
        return ""

    def _tally(target_field, n):
        counts = {"ENDORSE": 0, "OBJECT": 0, "ABSTAIN": 0}
        for r in rows:
            if r.get(target_field) == n and r.get("position") in counts:
                counts[r["position"]] += 1
        return counts

    def _counts_phrase(c) -> str:
        parts = []
        if c["ENDORSE"]:
            parts.append(f"{c['ENDORSE']} endorse")
        if c["OBJECT"]:
            parts.append(f"{c['OBJECT']} object")
        if c["ABSTAIN"]:
            parts.append(f"{c['ABSTAIN']} abstain")
        return " / ".join(parts)

    lines = ['<div class="endorse-summary">',
             '<p class="endorse-head">Board endorsement — the non-revision seats '
             'voted on each change:</p>', '<ul class="endorse-list">']
    for edit in changes.get("edits") or []:
        n = edit.get("n")
        c = _tally("edit_n", n)
        phrase = _counts_phrase(c)
        if phrase:
            lines.append(f'<li>edit {_esc(n)}: {phrase}</li>')
    for i in range(1, len(changes.get("unresolved") or []) + 1):
        c = _tally("unresolved_n", i)
        phrase = _counts_phrase(c)
        if phrase:
            lines.append(f'<li>unresolved conflict {_esc(i)}: {phrase}</li>')
    lines.append("</ul>")
    objections = [r for r in rows if r.get("position") == "OBJECT" and r.get("note")]
    if objections:
        lines.append('<p class="endorse-obj-head">Objections on the record:</p>')
        lines.append('<ul class="endorse-obj">')
        for r in objections:
            target = (f"edit {r['edit_n']}" if "edit_n" in r
                      else f"unresolved conflict {r['unresolved_n']}")
            # _flat collapses any whitespace run (an embedded newline included) to a
            # single space so a multi-line OBJECT note stays ONE <li> summary line —
            # the same discipline amendment text uses at every emission point (a raw
            # newline in the note would otherwise split the summary across lines and
            # feed the drop_empty_optionals blank-line regexes a shape they don't expect).
            lines.append(f'<li>{_esc(r.get("seat", "?"))} on {_esc(target)}: '
                         f'{_esc(_flat(r.get("note", "")))}</li>')
        lines.append("</ul>")
    lines.append("</div>")
    return "\n".join(lines)


def build_handoff_data(data: dict, run_dir=None, shape: str = "full-handoff") -> dict:
    verdict = data.get("verdict", "")
    lens_preset = data.get("lens_preset")
    label, note = human_label(verdict, lens_preset, data.get("decision"))
    # The banner headline leads with a plain should-I/shouldn't-I answer on a non-software
    # lens. `verdict_lead` is None for a software board, so its headline (and the whole
    # banner) is byte-identical to before. The stance rides on the headline for both
    # families; the banner color (verdict_class) stays keyed on the raw token.
    lead = verdict_lead(verdict, lens_preset, data.get("decision"))
    headline = f"{lead} · {_stance(data)}" if lead else f"{label} — {_stance(data)}"
    # An explicit verdict_note (authored) wins; else the plain lens note.
    verdict_note = data.get("verdict_note") or note
    # The subtle, lens-aware professional-advice caveat (None for a software lens and
    # the absent-preset default). Empty string when absent so the template slot resolves
    # to nothing and the footer line is dropped.
    disclaimer = lens_disclaimer(lens_preset)
    # The EFFECTIVE confidence, rendered as a small banner pill ("high confidence"). When
    # a human amended it, the pill shows the amended value with a terse "(amended)" marker —
    # the full provenance rides the dedicated Amendments section below, keeping the pill
    # small. Empty when absent so the pill is dropped. Same value feeds full + brief banners.
    conf_value, conf_entry = (effective_confidence(data) if "confidence" in data
                              else (None, None))
    confidence_str = (f"{conf_value} confidence" + (" (amended)" if conf_entry else "")
                      if conf_value else "")
    board_str = " · ".join(s.get("seat", "?") for s in data.get("board", []))
    rounds_str = str(data.get("rounds", ""))
    # The brief trims dissent to the first dissenter + a "+N more" pointer, and caps next
    # steps at the top 3 + a "…N more" pointer; the full handoff keeps the complete lists.
    dissent = data.get("dissent") or []
    actions = data.get("next_actions") or []
    # Footer provenance, in human terms — no internal file/script names. (The old
    # "Rendered from verdict.json by scripts/render_verdict.py" was a developer string
    # that leaked onto the page; same for the subtitle below.) The token/cost segment
    # (v1.11 #3a) is "" — and the footer byte-identical to before — unless the run's
    # TSV carries seat-reported usage; when present it is labeled an estimate.
    metadata = " · ".join(p for p in (
        f"Board: {board_str}" if board_str else "",
        f"{rounds_str} rounds" if rounds_str else "",
        data.get("date", ""),
        _token_totals_note(_seat_reported_token_totals(run_dir)),
    ) if p)
    hd = {
        # non-RAW slots (the renderer escapes them) -> _plain; RAW slots -> _raw.
        "title": _plain(data.get("title", "Advisory Board review")),
        # SUBTITLE describes WHAT was reviewed (shown in the masthead); an authored
        # subtitle wins, else a neutral default. Never a developer/render string.
        "subtitle": _raw(data.get("subtitle") or "An independent multi-model review."),
        "date": _plain(data.get("date", "")),
        "board": _raw(board_str),
        "rounds": rounds_str,
        "verdict": _plain(headline),
        "verdict_class": _VERDICT_CLASS.get(verdict, ""),
        "verdict_note": _raw(verdict_note) if verdict_note else "",
        "confidence": _plain(confidence_str),
        # Lens-aware section header for the consensus must-resolve items.
        "blockers_heading": _plain(blockers_heading(lens_preset, "html")),
        "disclaimer": _raw(disclaimer) if disclaimer else "",
        "plan": _raw(data.get("title", "")),
        "metadata": _raw(metadata),
        "dissent_flag": "Dissent on the record" if data.get("dissent") else "",
        "seats": [],
        # blocker_summary / dissent_summary are the one-line plain-text forms the
        # quick-verdict brief renders; the full handoff keeps using blocker_body /
        # dissent_body (the full prose). Both are non-RAW (the renderer escapes them).
        "blockers": [{"blocker_title": _plain(b.get("title", "blocker")),
                      "blocker_body": _raw(b.get("body", "")),
                      "blocker_summary": _plain(_oneliner(b.get("body", "")))}
                     for b in data.get("blockers", [])],
        "dissents": [{"dissent_who": _plain(d.get("who", "-")),
                      "dissent_body": _raw(d.get("body", "")),
                      "dissent_summary": _plain(_oneliner(d.get("body", "")))}
                     for d in data.get("dissent", [])],
        "caveats": [{"caveat_claim": _raw(line), "caveat_impact": ""}
                    for line in _couldnt_verify_lines(data)],
        "questions": [{"question": _raw(q)} for q in data.get("open_questions", [])],
        "actions": [{"action": _raw(_action_line(a))} for a in data.get("next_actions", [])],
        # Brief-only trims. The full handoff uses dissents[]/actions[] (complete); the
        # quick-verdict template uses these capped variants + their "more" pointers.
        "dissents_brief": ([{
            "dissent_who": _plain(dissent[0].get("who", "-")),
            "dissent_summary": _plain(_oneliner(dissent[0].get("body", ""))),
            "dissent_more": _plain(f"(+{len(dissent) - 1} more in the full handoff)")
                            if len(dissent) > 1 else "",
        }] if dissent else []),
        "actions_brief": [{"action": _raw(_action_line(a))} for a in actions[:3]],
        "actions_more": _plain(f"…{len(actions) - 3} more in the full handoff")
                        if len(actions) > 3 else "",
        # implementation-sequence slots (references/implementation-sequence-template.html):
        # the FULL ordered action list (never capped like the brief) with any owner split
        # out, and the blockers with their evidence trails. Additive — templates without
        # the SEQ blocks simply never read these keys.
        "sequence": [{"seq_action": _raw(_action_fields(a)[0]),
                      "seq_owner": _plain(_action_fields(a)[1])}
                     for a in actions],
        "seq_blockers": [{
            "seq_blocker_title": _plain(b.get("title", "blocker")),
            "seq_blocker_body": _raw(b.get("body", "")),
            "seq_evidence": [{"seq_evidence_line": _evidence_html(ev)}
                             for ev in (b.get("evidence") or []) if isinstance(ev, dict)],
        } for b in data.get("blockers", [])],
        # The human-owned amendment trail (v1.12 P4). Empty on a verdict with no
        # amendments, so the template's amendment section drops and the page is
        # byte-identical to before. Each row: who/when, the reason, and the effect.
        "amendments": [{
            "amend_who": _plain(entry.get("author", "?")),
            "amend_when": _plain(entry.get("timestamp", "?")),
            "amend_reason": _raw(entry.get("reason", "")),
            "amend_effect": _plain(_amendment_effect(entry)),
        } for entry in (data.get("amendments") or []) if isinstance(entry, dict)],
    }
    # Blocker severity notes: attach a human severity note to its matching blocker
    # (exact --on title match). Appended onto the already-built blocker rows so a
    # verdict with no severity notes leaves them untouched.
    for row, blocker in zip(hd["blockers"], data.get("blockers", [])):
        row["blocker_severity_notes"] = [
            {"blocker_severity_note": _raw(
                f"{note['severity_note']} — added by "
                f"{note.get('author', '?')} (amendment)")}
            for note in _severity_notes_for(data, blocker.get("title", ""))]
    for seat in data.get("board", []):
        name = seat.get("seat", "?")
        # Match the round artifact file on the machine id when present (a duplicate/aliased
        # seat writes round-N/<id>.md); fall back to the display label for a default board.
        seat_key = seat.get("id") or name
        rounds = []
        for round_no, rv in enumerate(seat.get("round_verdicts", []), 1):
            # Per-round pills follow the board-level lens family (the note is for the
            # headline only; a pill is just the short label). No `decision` here — a
            # round_verdict is always a raw ship/caution/block token.
            rv_label, _ = human_label(rv, lens_preset)
            rounds.append({
                "round_label": f"Round {round_no}",
                "round_verdict": _plain(rv_label),
                "round_verdict_class": _VERDICT_CLASS.get(rv, ""),
                "round_confidence": "",
                "round_review": _round_review(run_dir, seat_key, round_no, rv_label),
            })
        lens = seat.get("lens", "") or ""
        hd["seats"].append({
            "seat_name": _plain(name),
            "seat_lens": _plain(lens.capitalize() + (" lens" if lens else "")),
            "seat_model": _plain(seat.get("model", "")),
            "seat_status": "dropped" if seat.get("dropped") else "",
            "seat_status_class": "dropped" if seat.get("dropped") else "",
            "seat_highlight": "",
            "rounds": rounds,
        })
    hd.update(_delta_handoff_fields(data))
    # The revision redline/patch slots (v1.13 P3). Empty (both sections drop) on
    # any verdict without a sha-coherent revised-draft chain, so a non-revision
    # run stays byte-identical. Gated on the full-handoff shape (Item 4): the slim
    # shapes render no redline/patch, so they do NO revised-chain I/O and emit no
    # spurious redline warning.
    hd.update(_revision_handoff_fields(data, run_dir, shape))
    return hd


def _delta_handoff_fields(data: dict) -> dict:
    """The delta slots for the HTML handoff (v1.12 #1). All empty on a
    non-revise verdict, so the template's delta section drops entirely and the
    page stays byte-identical to before."""
    empty = {"delta_revises": "", "delta_trajectory": "", "delta_note": "",
             "delta_cleared": [], "delta_open": [], "delta_new": []}
    prev = data.get("previous_run")
    if not isinstance(prev, dict):
        return empty
    fields = dict(empty)
    when = f" ({prev['date']})" if isinstance(prev.get("date"), str) and prev["date"] else ""
    fields["delta_revises"] = _plain(f"Revises {prev.get('run_dir', '?')}{when}")
    prior, problem = _load_previous_verdict(data)
    if prior is None:
        fields["delta_note"] = _plain(
            problem or "prior run reference incomplete — delta not shown")
        return fields
    delta = verdict_delta(prior, data)
    frm, to = _trajectory_labels(prior, data)
    fields["delta_trajectory"] = _plain(f"{frm} → {to}")
    singular = {"blockers": "blocker", "concerns": "concern"}
    for container in DELTA_CONTAINERS:
        buckets = delta[container]
        for key, hd_key in (("cleared", "delta_cleared"),
                            ("still_open", "delta_open"), ("new", "delta_new")):
            fields[hd_key] += [
                {"delta_item": _plain(f"{_delta_item_title(entry)} "
                                      f"({singular[container]})")}
                for entry in buckets[key]]
    return fields


def _render_html(hd: dict, shape: str = "full-handoff") -> str:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import render_handoff  # sibling script
    # Same handoff-data dict feeds every view; only the template differs. The
    # quick-verdict template uses the slim subset of tokens/blocks (verdict banner,
    # one-line blockers, dissent line, actions) — no seats/rounds/caveats/questions.
    # The implementation-sequence template is the sequence-first view (the full
    # ordered action list with owners, then the blockers with evidence trails).
    if shape == "quick-verdict":
        template_path = render_handoff.quick_verdict_template()
    elif shape == "implementation-sequence":
        template_path = render_handoff.implementation_sequence_template()
    else:
        template_path = render_handoff.default_template()
    with open(template_path, encoding="utf-8") as handle:
        template = handle.read()
    return render_handoff.render(hd, template)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render final-consensus.md / handoff-data.json / HTML from verdict.json.")
    parser.add_argument("path", help="path to verdict.json")
    parser.add_argument("-o", "--out", default=None,
                        help="Markdown output path. Written when given, or — when no --html/--handoff-data is "
                             "requested — defaults to final-consensus.md. Pass --html alone to render only the HTML.")
    parser.add_argument("--check", action="store_true", help="print Markdown to stdout; write nothing")
    parser.add_argument("--handoff-data", dest="handoff_data", help="also write a derived handoff-data.json here")
    parser.add_argument("--html", help="also write final-consensus.html here (via render_handoff.py)")
    parser.add_argument("--shape", choices=("full-handoff", "quick-verdict", "implementation-sequence"),
                        default="full-handoff",
                        help="output shape: the full handoff (default), the slim quick-verdict "
                             "brief, or the sequence-first implementation-sequence view. "
                             "full-handoff/quick-verdict pick the --html template only; "
                             "implementation-sequence also switches the Markdown to the "
                             "sequence view (default filename implementation-sequence.md)")
    parser.add_argument("--run", dest="run_dir", help="a run dir; pulls per-round prose from its round-N/<seat>.md")
    args = parser.parse_args(argv)

    data = load(args.path)
    sequence_shape = args.shape == "implementation-sequence"
    markdown = render_sequence_markdown(data) if sequence_shape else render_markdown(data)

    # The Markdown is the implicit default deliverable: write it when --out is given, or
    # when no other output (--html / --handoff-data) was requested. Asking only for the
    # HTML brief (e.g. --html quick-verdict.html --shape quick-verdict) no longer litters
    # a stray final-consensus.md.
    if args.check:
        sys.stdout.write(markdown)
    elif args.out is not None or not (args.html or args.handoff_data):
        out_path = args.out or ("implementation-sequence.md" if sequence_shape
                                else "final-consensus.md")
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(markdown)
        print(f"wrote {out_path} ({len(markdown)} bytes)")

    if args.handoff_data or args.html:
        hd = build_handoff_data(data, run_dir=args.run_dir, shape=args.shape)
        if args.handoff_data:
            with open(args.handoff_data, "w", encoding="utf-8") as handle:
                json.dump(hd, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
            print(f"wrote {args.handoff_data}")
        if args.html:
            out_html = _render_html(hd, args.shape)
            with open(args.html, "w", encoding="utf-8") as handle:
                handle.write(out_html)
            print(f"wrote {args.html} ({len(out_html)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

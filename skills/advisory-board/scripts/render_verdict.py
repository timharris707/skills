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

Usage:
  render_verdict.py verdict.json                              -> final-consensus.md
  render_verdict.py verdict.json -o consensus.md
  render_verdict.py verdict.json --check                      print to stdout, write nothing
  render_verdict.py verdict.json --handoff-data handoff-data.json [--run RUNDIR]
  render_verdict.py verdict.json --html final-consensus.html [--run RUNDIR]

Exit codes: 0 ok, 2 usage / data error.
Standard library only; no third-party dependencies.
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _render_engine import die  # noqa: E402  shared with the other renderers
from _verdict_labels import (  # noqa: E402  lens-aware label + framing (renderer-only)
    blockers_heading,
    human_label,
    lens_disclaimer,
    verdict_lead,
)

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


def render_markdown(data: dict) -> str:
    out = ["# Advisory Board — Final Consensus"]
    if data.get("title"):
        out.append(data["title"])
    seats = _seats_line(data)
    rounds = data.get("rounds", "?")
    out.append(f"Board: {seats}. Rounds: {rounds}.")
    out.append("")

    label, note = human_label(data.get("verdict"), data.get("lens_preset"), data.get("decision"))
    # The confidence clause is dropped entirely when confidence is untracked — matching the
    # HTML handoff's clean-drop of the pill — rather than emitting a literal "? confidence".
    confidence = data.get("confidence")
    conf_clause = f" ({confidence} confidence)" if confidence else ""
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
        out += [f"- {a}" for a in actions]
        out.append("")

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
    """The honesty bucket: authored caveats plus any unverified/refuted citation."""
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


def build_handoff_data(data: dict, run_dir=None) -> dict:
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
    # The board's confidence, rendered as a small banner pill ("high confidence"). Empty
    # when absent so the pill is dropped. Same value feeds both the full and brief banners.
    confidence = data.get("confidence")
    confidence_str = f"{confidence} confidence" if confidence else ""
    board_str = " · ".join(s.get("seat", "?") for s in data.get("board", []))
    rounds_str = str(data.get("rounds", ""))
    # The brief trims dissent to the first dissenter + a "+N more" pointer, and caps next
    # steps at the top 3 + a "…N more" pointer; the full handoff keeps the complete lists.
    dissent = data.get("dissent") or []
    actions = data.get("next_actions") or []
    # Footer provenance, in human terms — no internal file/script names. (The old
    # "Rendered from verdict.json by scripts/render_verdict.py" was a developer string
    # that leaked onto the page; same for the subtitle below.)
    metadata = " · ".join(p for p in (
        f"Board: {board_str}" if board_str else "",
        f"{rounds_str} rounds" if rounds_str else "",
        data.get("date", ""),
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
        "actions": [{"action": _raw(a)} for a in data.get("next_actions", [])],
        # Brief-only trims. The full handoff uses dissents[]/actions[] (complete); the
        # quick-verdict template uses these capped variants + their "more" pointers.
        "dissents_brief": ([{
            "dissent_who": _plain(dissent[0].get("who", "-")),
            "dissent_summary": _plain(_oneliner(dissent[0].get("body", ""))),
            "dissent_more": _plain(f"(+{len(dissent) - 1} more in the full handoff)")
                            if len(dissent) > 1 else "",
        }] if dissent else []),
        "actions_brief": [{"action": _raw(a)} for a in actions[:3]],
        "actions_more": _plain(f"…{len(actions) - 3} more in the full handoff")
                        if len(actions) > 3 else "",
    }
    for seat in data.get("board", []):
        name = seat.get("seat", "?")
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
                "round_review": _round_review(run_dir, name, round_no, rv_label),
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
    return hd


def _render_html(hd: dict, shape: str = "full-handoff") -> str:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import render_handoff  # sibling script
    # Same handoff-data dict feeds both views; only the template differs. The
    # quick-verdict template uses the slim subset of tokens/blocks (verdict banner,
    # one-line blockers, dissent line, actions) — no seats/rounds/caveats/questions.
    template_path = (render_handoff.quick_verdict_template()
                     if shape == "quick-verdict"
                     else render_handoff.default_template())
    with open(template_path, encoding="utf-8") as handle:
        template = handle.read()
    return render_handoff.render(hd, template)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render final-consensus.md / handoff-data.json / HTML from verdict.json.")
    parser.add_argument("path", help="path to verdict.json")
    parser.add_argument("-o", "--out", default="final-consensus.md", help="Markdown output path (default: final-consensus.md)")
    parser.add_argument("--check", action="store_true", help="print Markdown to stdout; write nothing")
    parser.add_argument("--handoff-data", dest="handoff_data", help="also write a derived handoff-data.json here")
    parser.add_argument("--html", help="also write final-consensus.html here (via render_handoff.py)")
    parser.add_argument("--shape", choices=("full-handoff", "quick-verdict"), default="full-handoff",
                        help="HTML shape for --html: the full handoff (default) or the slim quick-verdict brief")
    parser.add_argument("--run", dest="run_dir", help="a run dir; pulls per-round prose from its round-N/<seat>.md")
    args = parser.parse_args(argv)

    data = load(args.path)
    markdown = render_markdown(data)

    if args.check:
        sys.stdout.write(markdown)
    else:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(markdown)
        print(f"wrote {args.out} ({len(markdown)} bytes)")

    if args.handoff_data or args.html:
        hd = build_handoff_data(data, run_dir=args.run_dir)
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

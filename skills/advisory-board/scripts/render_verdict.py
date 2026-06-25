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

LABEL = {"ship": "SHIP", "caution": "SHIP WITH CHANGES", "block": "DO NOT SHIP YET"}
STATUS_WORD = {"verified": "verified", "unverified": "unverified", "refuted": "REFUTED"}
EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


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

    label = data.get("decision") or LABEL.get(data.get("verdict"), str(data.get("verdict")))
    out.append(f"## Verdict: {label} — {_stance(data)} ({data.get('confidence', '?')} confidence)")
    if data.get("verdict_note"):
        out.append(data["verdict_note"])
    out.append("")

    blockers = data.get("blockers", [])
    if blockers:
        out.append("## Consensus blockers (must fix before ship)")
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
            verb = "could not be resolved" if ev["status"] == "unverified" else "was REFUTED (not found)"
            lines.append(f"{_evidence_label(ev)} {verb}.")
    return lines


# --------------------------------------------------------------------------- #
# handoff-data.json (so render_handoff.py can produce the HTML from the verdict)
# --------------------------------------------------------------------------- #

_VERDICT_CLASS = {"ship": "ship", "caution": "caution", "block": "block"}
_BACKTICK = re.compile(r"`([^`]+)`")


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


def _md_to_html(text: str) -> str:
    """Minimal, honest md->HTML: escape, turn `code` into <code>, paragraph-wrap on
    blank lines. We deliberately do NOT reconstruct rich structure the JSON never
    held - the full prose lives in the round-N/<seat>.md artifacts this points at."""
    blocks = re.split(r"\n\s*\n", text.strip())
    paras = []
    for block in blocks:
        escaped = _raw(block.strip())
        escaped = _BACKTICK.sub(lambda m: "<code>" + m.group(1) + "</code>", escaped)
        escaped = escaped.replace("\n", "<br>\n")
        if escaped:
            paras.append(f"<p>{escaped}</p>")
    return "\n".join(paras)


def _round_review(run_dir, seat_name: str, round_no: int, verdict: str) -> str:
    if run_dir:
        for candidate in glob.glob(os.path.join(run_dir, f"round-{round_no}", "*.md")):
            if os.path.splitext(os.path.basename(candidate))[0].lower() == seat_name.lower():
                try:
                    with open(candidate, encoding="utf-8", errors="replace") as handle:
                        return _md_to_html(handle.read())
                except OSError:
                    break
    pointer = _nb(f"round-{round_no}/{html.escape(seat_name.lower())}.md")
    return f"<p>Round {round_no} verdict: <strong>{_nb(html.escape(verdict))}</strong>. Full review in <code>{pointer}</code>.</p>"


def build_handoff_data(data: dict, run_dir=None) -> dict:
    verdict = data.get("verdict", "")
    label = data.get("decision") or LABEL.get(verdict, str(verdict))
    hd = {
        # non-RAW slots (the renderer escapes them) -> _plain; RAW slots -> _raw.
        "title": _plain(data.get("title", "Advisory Board review")),
        "subtitle": "Rendered from the canonical verdict.json.",
        "date": _plain(data.get("date", "")),
        "board": _raw(" · ".join(s.get("seat", "?") for s in data.get("board", []))),
        "rounds": str(data.get("rounds", "")),
        "verdict": _plain(f"{label} — {_stance(data)}"),
        "verdict_class": _VERDICT_CLASS.get(verdict, ""),
        "verdict_note": _raw(data["verdict_note"]) if data.get("verdict_note") else "",
        "plan": _raw(data.get("title", "")),
        "metadata": "Rendered from <code>verdict.json</code> by <code>scripts/render_verdict.py</code>.",
        "dissent_flag": "Dissent on the record" if data.get("dissent") else "",
        "seats": [],
        "blockers": [{"blocker_title": _plain(b.get("title", "blocker")),
                      "blocker_body": _raw(b.get("body", ""))} for b in data.get("blockers", [])],
        "dissents": [{"dissent_who": _plain(d.get("who", "-")),
                      "dissent_body": _raw(d.get("body", ""))} for d in data.get("dissent", [])],
        "caveats": [{"caveat_claim": _raw(line), "caveat_impact": ""}
                    for line in _couldnt_verify_lines(data)],
        "questions": [{"question": _raw(q)} for q in data.get("open_questions", [])],
        "actions": [{"action": _raw(a)} for a in data.get("next_actions", [])],
    }
    for seat in data.get("board", []):
        name = seat.get("seat", "?")
        rounds = []
        for round_no, rv in enumerate(seat.get("round_verdicts", []), 1):
            rounds.append({
                "round_label": f"Round {round_no}",
                "round_verdict": _plain(LABEL.get(rv, rv)),
                "round_verdict_class": _VERDICT_CLASS.get(rv, ""),
                "round_confidence": "",
                "round_review": _round_review(run_dir, name, round_no, LABEL.get(rv, rv)),
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


def _render_html(hd: dict) -> str:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import render_handoff  # sibling script
    with open(render_handoff.default_template(), encoding="utf-8") as handle:
        template = handle.read()
    return render_handoff.render(hd, template)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render final-consensus.md / handoff-data.json / HTML from verdict.json.")
    parser.add_argument("path", help="path to verdict.json")
    parser.add_argument("-o", "--out", default="final-consensus.md", help="Markdown output path (default: final-consensus.md)")
    parser.add_argument("--check", action="store_true", help="print Markdown to stdout; write nothing")
    parser.add_argument("--handoff-data", dest="handoff_data", help="also write a derived handoff-data.json here")
    parser.add_argument("--html", help="also write final-consensus.html here (via render_handoff.py)")
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
            out_html = _render_html(hd)
            with open(args.html, "w", encoding="utf-8") as handle:
                handle.write(out_html)
            print(f"wrote {args.html} ({len(out_html)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

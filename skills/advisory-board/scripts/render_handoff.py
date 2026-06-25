#!/usr/bin/env python3
"""Render final-consensus.html deterministically from a handoff-data.json.

The HTML handoff is a *view* of the board's result; hand-filling the template
drifts (leftover {{tokens}}, stray scaffolding comments, HTML that contradicts
the Markdown). This makes the HTML a pure function of structured data, and
fails loudly if any placeholder or authoring comment survives.

Usage:
  render_handoff.py handoff-data.json                       -> writes final-consensus.html
  render_handoff.py handoff-data.json -o out.html           -> writes out.html
  render_handoff.py handoff-data.json --template t.html     -> use a specific template
  render_handoff.py handoff-data.json --check               -> render in memory, verify, write nothing

Exit codes: 0 ok, 2 usage / data / unresolved-placeholder error.
Standard library only; no third-party dependencies.

handoff-data.json shape (keys mirror the template's {{TOKENS}}, lowercased):

  Top level (scalars):  title, subtitle, date, board, rounds, verdict,
                        verdict_class, verdict_note, plan, metadata, dissent_flag
  Lists of objects:     seats[], blockers[], dissents[], caveats[],
                        questions[], actions[]
    seats[]:   seat_name, seat_lens, seat_model, seat_status, seat_status_class,
               seat_highlight, rounds[]
      rounds[]: round_label, round_verdict, round_verdict_class,
                round_confidence, round_review
    blockers[]: blocker_title, blocker_body
    dissents[]: dissent_who, dissent_body
    caveats[]:  caveat_claim, caveat_impact
    questions[]: question      actions[]: action

Empty/omitted optional fields (seat_status, seat_highlight, round_confidence)
render to nothing — the pill/callout is dropped, not left blank.

Label/enum fields are HTML-escaped by the renderer. Prose/body fields are passed
through as HTML, so the data author must escape them and wrap inline code in
<code> (matching the template's output contract). RAW (pass-through) fields:
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys

# Block-comment name -> the data key holding its list of items.
BLOCK_KEYS = {
    "SEAT CARD": "seats",
    "ROUND": "rounds",
    "BLOCKER": "blockers",
    "DISSENT": "dissents",
    "CAVEAT": "caveats",
    "QUESTION": "questions",
    "ACTION": "actions",
}

# Tokens whose values are authored HTML fragments and pass through unescaped.
RAW_TOKENS = {
    "SUBTITLE", "BOARD", "VERDICT_NOTE", "PLAN", "METADATA", "SEAT_HIGHLIGHT",
    "ROUND_REVIEW", "BLOCKER_BODY", "DISSENT_BODY", "CAVEAT_CLAIM",
    "CAVEAT_IMPACT", "QUESTION", "ACTION",
}

TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
BEGIN_RE = re.compile(r"<!--\s*BEGIN ([A-Z][A-Z ]*?)\s*(?:\([^)]*\))?\s*-->")
MARKER_RE = re.compile(r"<!--\s*(BEGIN|END) ([A-Z][A-Z ]*?)\s*(?:\([^)]*\))?\s*-->")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
DIVIDER_RE = re.compile(r"^<!--\s*=+.*=+\s*-->$")


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def find_first_block(tpl: str):
    """Return (start, end, name, inner) for the first BEGIN..matching END block.

    Matching is depth-aware so a nested block (ROUND inside SEAT CARD) doesn't
    end the outer block early. Returns None when no block remains.
    """
    begin = BEGIN_RE.search(tpl)
    if not begin:
        return None
    name = begin.group(1).strip()
    inner_start = begin.end()
    depth = 0
    for marker in MARKER_RE.finditer(tpl, begin.start()):
        depth += 1 if marker.group(1) == "BEGIN" else -1
        if depth == 0:
            return begin.start(), marker.end(), name, tpl[inner_start:marker.start()]
    die(f"unterminated BEGIN {name}")


def substitute(tpl: str, ctx: dict) -> str:
    def repl(match: re.Match) -> str:
        token = match.group(1)
        key = token.lower()
        if key not in ctx or isinstance(ctx[key], list):
            return match.group(0)  # leave for the final unresolved-token check
        value = "" if ctx[key] is None else str(ctx[key])
        return value if token in RAW_TOKENS else html.escape(value, quote=True)

    return TOKEN_RE.sub(repl, tpl)


def render_item(tpl: str, ctx: dict) -> str:
    """Expand every repeatable block against ctx, then fill ctx's scalar tokens."""
    while True:
        block = find_first_block(tpl)
        if block is None:
            break
        start, end, name, inner = block
        key = BLOCK_KEYS.get(name)
        if key is None:
            die(f"unknown template block: {name!r}")
        items = ctx.get(key) or []
        if not isinstance(items, list):
            die(f"{key!r} must be a list; got {type(items).__name__}")
        rendered = "".join(render_item(inner, item) for item in items)
        tpl = tpl[:start] + rendered + tpl[end:]
    return substitute(tpl, ctx)


def drop_empty_optionals(out: str) -> str:
    """Remove the three optional elements when their token rendered empty."""
    out = re.sub(r'\s*<span class="seat-status\s*">\s*</span>', "", out)
    out = re.sub(r'\s*<div class="highlight">\s*</div>', "", out)
    out = re.sub(r'\s*<span class="conf">confidence:\s*</span>', "", out)
    return out


def strip_comments(out: str) -> str:
    """Drop authoring comments; keep single-line ===== section dividers."""
    def decide(match: re.Match) -> str:
        comment = match.group(0)
        if "\n" not in comment and DIVIDER_RE.match(comment.strip()):
            return comment
        return ""

    return COMMENT_RE.sub(decide, out)


def render(data: dict, template: str) -> str:
    out = render_item(template, data)
    out = drop_empty_optionals(out)
    out = strip_comments(out)
    out = re.sub(r"\n{3,}", "\n\n", out)

    leftover = sorted(set(TOKEN_RE.findall(out)))
    if leftover:
        die("unresolved placeholder(s): " + ", ".join("{{%s}}" % t for t in leftover))
    if "<!--" in out and not all(
        DIVIDER_RE.match(c.strip()) for c in COMMENT_RE.findall(out)
    ):
        die("authoring comment survived rendering")
    return out


def default_template() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "references", "handoff-template.html",
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render final-consensus.html from handoff-data.json.")
    parser.add_argument("data", help="path to handoff-data.json")
    parser.add_argument("-o", "--out", default="final-consensus.html", help="output path (default: final-consensus.html)")
    parser.add_argument("--template", default=None, help="template path (default: ../references/handoff-template.html)")
    parser.add_argument("--check", action="store_true", help="render and verify only; write nothing")
    args = parser.parse_args(argv)

    try:
        with open(args.data, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        die(f"{args.data}: not found")
    except json.JSONDecodeError as exc:
        die(f"{args.data}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        die(f"{args.data}: top level must be a JSON object")

    template_path = args.template or default_template()
    try:
        with open(template_path, encoding="utf-8") as handle:
            template = handle.read()
    except FileNotFoundError:
        die(f"{template_path}: template not found")

    out = render(data, template)

    if args.check:
        print(f"ok: rendered cleanly ({len(out)} bytes), no placeholders left")
        return 0

    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(out)
    print(f"wrote {args.out} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

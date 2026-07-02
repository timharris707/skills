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
                        verdict_class, verdict_note, blockers_heading, disclaimer,
                        plan, metadata, dissent_flag
  Lists of objects:     seats[], blockers[], dissents[], caveats[],
                        questions[], actions[], sequence[], seq_blockers[]
    seats[]:   seat_name, seat_lens, seat_model, seat_status, seat_status_class,
               seat_highlight, rounds[]
      rounds[]: round_label, round_verdict, round_verdict_class,
                round_confidence, round_review
    blockers[]: blocker_title, blocker_body
    dissents[]: dissent_who, dissent_body
    caveats[]:  caveat_claim, caveat_impact
    questions[]: question      actions[]: action
    sequence[]: seq_action, seq_owner        (implementation-sequence view)
    seq_blockers[]: seq_blocker_title, seq_blocker_body, seq_evidence[]
      seq_evidence[]: seq_evidence_line

Empty/omitted optional fields (seat_status, seat_highlight, round_confidence)
render to nothing — the pill/callout is dropped, not left blank.

Label/enum fields are HTML-escaped by the renderer. Prose/body fields are passed
through as HTML, so the data author must escape them and wrap inline code in
<code> (matching the template's output contract). RAW (pass-through) fields:

EXCEPTION — seat round reviews: each seat's `round_review` is authored as raw
Markdown (exactly what the model produced) and converted to HTML here by _md
(headings, bold/italic, lists, inline + fenced code). The data author does NOT
hand-build HTML for it — that is the fragile step that used to leave literal `##`
and `**` in the published handoff. Every other prose field stays authored HTML.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _render_engine import (  # noqa: E402  shared block / {{TOKEN}} engine
    assert_fully_resolved,
    die,
    render_item,
    strip_comments,
)
from _md import md_to_html  # noqa: E402  seat reviews are Markdown -> rendered to HTML here

# Block-comment name -> the data key holding its list of items.
BLOCK_KEYS = {
    "SEAT CARD": "seats",
    "ROUND": "rounds",
    "BLOCKER": "blockers",
    "DISSENT": "dissents",
    "DISSENT BRIEF": "dissents_brief",
    "CAVEAT": "caveats",
    "QUESTION": "questions",
    "ACTION": "actions",
    "ACTION BRIEF": "actions_brief",
    # implementation-sequence view (implementation-sequence-template.html): the full
    # ordered step list, and the blockers with a nested evidence-trail list.
    "SEQ STEP": "sequence",
    "SEQ BLOCKER": "seq_blockers",
    "SEQ EVIDENCE": "seq_evidence",
    # delta vs the previous run (v1.12 --revise; full handoff only). All three
    # lists are empty on a non-revise verdict — the whole section drops below.
    "DELTA CLEARED": "delta_cleared",
    "DELTA OPEN": "delta_open",
    "DELTA NEW": "delta_new",
}

# Tokens whose values are authored HTML fragments and pass through unescaped.
RAW_TOKENS = {
    "SUBTITLE", "BOARD", "VERDICT_NOTE", "DISCLAIMER", "PLAN", "METADATA",
    "SEAT_HIGHLIGHT", "ROUND_REVIEW", "BLOCKER_BODY", "DISSENT_BODY",
    "CAVEAT_CLAIM", "CAVEAT_IMPACT", "QUESTION", "ACTION",
    "SEQ_ACTION", "SEQ_BLOCKER_BODY", "SEQ_EVIDENCE_LINE",
}


def drop_empty_optionals(out: str) -> str:
    """Remove the optional elements when their token rendered empty."""
    # --- delta section (v1.12 --revise; delta-* classes exist only in the full
    #     handoff template — NO-OPS elsewhere). Whole-section drop FIRST: a
    #     non-revise verdict renders an empty delta-revises line, taking the
    #     entire section (heading included) with it. Then the per-piece drops
    #     for a revise verdict: empty trajectory/note lines, empty buckets. ---
    out = re.sub(
        r'\s*<section class="delta-sec">\s*<h2>[^<]*</h2>\s*'
        r'<p class="delta-revises">\s*</p>.*?</section>',
        "", out, flags=re.DOTALL)
    out = re.sub(r'\s*<p class="delta-traj">\s*</p>', "", out)
    out = re.sub(r'\s*<p class="delta-note">\s*</p>', "", out)
    out = re.sub(
        r'\s*<div class="delta-col">\s*<h4>[^<]*</h4>\s*'
        r'<ul class="delta-list">\s*</ul>\s*</div>',
        "", out)
    out = re.sub(r'\s*<span class="seat-status\s*">\s*</span>', "", out)
    out = re.sub(r'\s*<div class="highlight">\s*</div>', "", out)
    out = re.sub(r'\s*<span class="conf">confidence:\s*</span>', "", out)
    out = re.sub(r'\s*<span class="disclaimer">\s*</span>', "", out)
    # Drop the verdict-banner confidence pill when there's no confidence. Shared by both
    # the full handoff and the brief (same banner markup); no-op when the pill is filled.
    out = re.sub(r'<span class="conf-badge">\s*</span>', "", out)
    # --- quick-verdict (qv-*) drops. All scoped to qv-* classes, so they are NO-OPS
    #     for the full handoff template (which has no qv-* markup). After render_item,
    #     an empty repeatable block leaves its <ol>…</ol>/<span>…</span> empty — that
    #     is the shape these match. ---
    # Drop the brief's "+N more" / "…N more" pointers when they rendered empty. The
    # qv-more-li drop MUST run BEFORE the empty-actions-section drop below, so a zero-
    # action brief leaves a truly empty <ol> for that rule to match (and the whole
    # section drops). qv-more is the inline dissent pointer span.
    out = re.sub(r'\s*<li class="qv-more-li">\s*</li>', "", out)
    out = re.sub(r'\s*<span class="qv-more">\s*</span>', "", out)
    # Drop an empty dissent block: only an empty qv-dflag and no qv-d items left.
    out = re.sub(
        r'\s*<div class="qv-dissent">\s*<span class="qv-dflag">\s*</span>\s*</div>',
        "", out, flags=re.DOTALL)
    # Drop an empty blockers section (the qv-blockers <ol> rendered empty).
    out = re.sub(
        r'\s*<section class="qv-sec qv-blockers-sec">.*?<ol class="qv-blockers">\s*</ol>.*?</section>',
        "", out, flags=re.DOTALL)
    # Drop an empty actions section (the qv-actions <ol> rendered empty).
    out = re.sub(
        r'\s*<section class="qv-sec qv-actions-sec">.*?<ol class="qv-actions">\s*</ol>.*?</section>',
        "", out, flags=re.DOTALL)
    # --- implementation-sequence (seq-*) drops. Scoped to seq-* classes — NO-OPS for
    #     the other templates. An action with no owner leaves its owner span empty;
    #     a blocker with no evidence leaves its <ul> empty; a verdict with no
    #     next_actions / blockers leaves that whole section's list empty. ---
    out = re.sub(r'\s*<span class="seq-owner">\s*</span>', "", out)
    out = re.sub(r'\s*<ul class="seq-ev">\s*</ul>', "", out)
    out = re.sub(
        r'\s*<section class="seq-sec seq-steps-sec">.*?<ol class="seq-steps">\s*</ol>.*?</section>',
        "", out, flags=re.DOTALL)
    out = re.sub(
        r'\s*<section class="seq-sec seq-blockers-sec">.*?<ol class="seq-blockers">\s*</ol>.*?</section>',
        "", out, flags=re.DOTALL)
    return out


_ZW = "​"  # zero-width space


def _md_review(markdown: str) -> str:
    """Convert a seat review from Markdown to HTML, then break any `{{...}}` adjacency
    in the result (a review quoting a template) with a zero-width space, so it can't
    masquerade as an unfilled token and trip assert_fully_resolved. ROUND_REVIEW is a
    RAW pass-through slot, so this is the one place its braces get neutralized."""
    return md_to_html(markdown or "").replace("{", "{" + _ZW)


def markdownify_reviews(data: dict) -> dict:
    """Return a shallow copy of `data` with each seat round's `round_review` Markdown
    converted to HTML. Done on a copy so the original data is untouched (and a second
    render can't double-convert already-HTML)."""
    if not isinstance(data.get("seats"), list):
        return data
    data = dict(data)
    seats = []
    for seat in data["seats"]:
        if isinstance(seat, dict) and isinstance(seat.get("rounds"), list):
            seat = dict(seat)
            seat["rounds"] = [
                {**r, "round_review": _md_review(r.get("round_review", ""))}
                if isinstance(r, dict) else r
                for r in seat["rounds"]
            ]
        seats.append(seat)
    data["seats"] = seats
    return data


def render(data: dict, template: str) -> str:
    data = markdownify_reviews(data)
    # Pre-v1.12 handoff-data.json files carry no delta slots; default them so an
    # old data file still renders (the empty section drops below) instead of
    # dying on an unresolved {{DELTA_*}} token.
    for key in ("delta_revises", "delta_trajectory", "delta_note"):
        data.setdefault(key, "")
    for key in ("delta_cleared", "delta_open", "delta_new"):
        data.setdefault(key, [])
    out = render_item(template, data, BLOCK_KEYS, RAW_TOKENS)
    out = drop_empty_optionals(out)
    out = strip_comments(out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    assert_fully_resolved(out)
    return out


def default_template() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "references", "handoff-template.html",
    )


def quick_verdict_template() -> str:
    """The slim "quick-verdict" (skim-brief) template — same handoff-data, fewer slots."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "references", "quick-verdict-template.html",
    )


def implementation_sequence_template() -> str:
    """The sequence-first "implementation-sequence" template — same handoff-data;
    the full ordered next actions (with owners) lead, backed by the blockers each
    step must clear with their evidence trails."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "references", "implementation-sequence-template.html",
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

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
  Top level (v1.13 P3): redline_source_name, redline_note, patch_pre, patch_note
  Lists of objects:     seats[], blockers[], dissents[], caveats[],
                        questions[], actions[], sequence[], seq_blockers[],
                        amendments[], redline_rows[]
    redline_rows[]: redline_html   (a pre-escaped <del>/<ins> row fragment)
    seats[]:   seat_name, seat_lens, seat_model, seat_status, seat_status_class,
               seat_highlight, rounds[]
      rounds[]: round_label, round_verdict, round_verdict_class,
                round_confidence, round_review
    blockers[]: blocker_title, blocker_body, blocker_severity_notes[]
      blocker_severity_notes[]: blocker_severity_note   (human amendment, --on match)
    amendments[]: amend_who, amend_when, amend_reason, amend_effect  (v1.12 P4)
    dissents[]: dissent_who, dissent_body
    caveats[]:  caveat_claim, caveat_impact
    questions[]: question      actions[]: action
    sequence[]: seq_action, seq_owner        (implementation-sequence view)
    seq_blockers[]: seq_blocker_title, seq_blocker_body, seq_evidence[]
      seq_evidence[]: seq_evidence_line

Empty/omitted optional fields (seat_status, seat_highlight, round_confidence)
render to nothing — the pill/callout is dropped, not left blank.

Template-evolution invariant (settled v1.12 P4, extended v1.13 P3): a feature's
<head> CSS may evolve freely — the committed examples carry head-CSS drift — but
the rendered BODY must stay byte-identical for a run WITHOUT that feature. A new
section MUST whole-drop (heading, markup, and any preceding authoring comment) to
ZERO body bytes when its fields are empty, so it leaves no residue. The head-CSS
exemption is deliberate; the body byte-identity is enforced by test.

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
    # human-owned amendments (v1.12 P4; full handoff only). Empty on an un-amended
    # verdict — the whole section drops below. BLOCKER SEVERITY NOTE is a note nested
    # in a blocker (attached by an exact --on title match).
    "AMENDMENT": "amendments",
    "BLOCKER SEVERITY NOTE": "blocker_severity_notes",
    # delta vs the previous run (v1.12 --revise; full handoff only). All three
    # lists are empty on a non-revise verdict — the whole section drops below.
    "DELTA CLEARED": "delta_cleared",
    "DELTA OPEN": "delta_open",
    "DELTA NEW": "delta_new",
    # revision redline (v1.13 P3; prose sources, full handoff only). One row per
    # redline line (context/del/ins/replace, pre-rendered as RAW HTML). Empty when
    # there is no sha-coherent revised chain — the whole section drops below.
    "REDLINE": "redline_rows",
}

# Tokens whose values are authored HTML fragments and pass through unescaped.
RAW_TOKENS = {
    "SUBTITLE", "BOARD", "VERDICT_NOTE", "DISCLAIMER", "PLAN", "METADATA",
    "SEAT_HIGHLIGHT", "ROUND_REVIEW", "BLOCKER_BODY", "DISSENT_BODY",
    "CAVEAT_CLAIM", "CAVEAT_IMPACT", "QUESTION", "ACTION",
    "SEQ_ACTION", "SEQ_BLOCKER_BODY", "SEQ_EVIDENCE_LINE",
    "AMEND_REASON", "BLOCKER_SEVERITY_NOTE",
    # revision redline/patch (v1.13 P3): REDLINE_HTML is a per-row fragment the
    # data author already escaped (<del>/<ins> spans + escaped text); PATCH_PRE is
    # the escaped unified-diff body for the code fenced block.
    "REDLINE_HTML", "PATCH_PRE",
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
    # --- amendments (amend-*) drops (v1.12 P4). Scoped to amend-* classes — NO-OPS for
    #     the other templates. A blocker with no severity notes leaves its <ul> empty; a
    #     verdict with no amendments leaves the amend-list <ol> empty and the whole
    #     section (heading + intro) drops. Each optionally eats the immediately-preceding
    #     authoring comment + its whitespace, so the drop leaves no blank-line residue
    #     (the comment would otherwise strip to a stray whitespace-only line — the ONLY
    #     new blocks that carry such a comment; the pre-existing drops above don't). ---
    out = re.sub(
        r'\s*(?:<!--(?:(?!-->).)*?-->\s*)?<ul class="blocker-sev-notes">\s*</ul>',
        "", out, flags=re.DOTALL)
    # A zero-effect (provenance-only) amendment leaves its effect pill empty — drop it.
    out = re.sub(r'\s*<span class="amend-effect">\s*</span>', "", out)
    out = re.sub(
        r'\s*(?:<!--(?:(?!-->).)*?-->\s*)?'
        r'<section class="amend-sec">.*?<ol class="amend-list">\s*</ol>.*?</section>',
        "", out, flags=re.DOTALL)
    # --- revision redline / patch (v1.13 P3). Two SIBLING sections, at most one
    #     populated (prose → redline, code → patch); both drop on a non-revision
    #     run. Same tempered-comment form as amend-sec: the regex optionally eats
    #     the immediately-preceding authoring comment so no blank-line residue. ---
    # First the optional truncation notes (empty when the section wasn't capped).
    out = re.sub(r'\s*<p class="rl-note">\s*</p>', "", out)
    out = re.sub(r'\s*<p class="patch-note">\s*</p>', "", out)
    # Prose redline: the whole section drops when no rows rendered (the rl-body
    # <div> is empty). rl-* classes exist only in the full handoff → no-op elsewhere.
    out = re.sub(
        r'\s*(?:<!--(?:(?!-->).)*?-->\s*)?'
        r'<section class="redline-sec">.*?<div class="rl-body">\s*</div>.*?</section>',
        "", out, flags=re.DOTALL)
    # Code patch: the whole section drops when the <pre> body rendered empty.
    out = re.sub(
        r'\s*(?:<!--(?:(?!-->).)*?-->\s*)?'
        r'<section class="patch-sec">.*?<pre class="patch-pre">\s*</pre>.*?</section>',
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
    # Same pre-v1.12 backfill for the amendments block (v1.12 P4): an old
    # handoff-data.json has no `amendments` key, so default it to [] — the section
    # drops below rather than dying on an unresolved {{AMEND_*}} token. Each blocker
    # gets an empty severity-notes list for the same reason (an old blocker row has
    # no `blocker_severity_notes`).
    data.setdefault("amendments", [])
    # Same pre-v1.13 backfill for the revision redline/patch (v1.13 P3): an old
    # handoff-data.json has none of these keys, so default the scalars to "" and
    # the row list to [] — both sections drop below rather than dying on an
    # unresolved {{REDLINE_*}}/{{PATCH_*}} token.
    for key in ("redline_source_name", "redline_note", "patch_pre", "patch_note"):
        data.setdefault(key, "")
    data.setdefault("redline_rows", [])
    if isinstance(data.get("blockers"), list):
        # Copy each blocker row before defaulting its nested list, so an old
        # handoff-data.json passed in by the caller is never mutated.
        data["blockers"] = [
            {"blocker_severity_notes": [], **b} if isinstance(b, dict) else b
            for b in data["blockers"]]
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

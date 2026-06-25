#!/usr/bin/env python3
"""Render a planning document to a self-contained HTML view, FROM its markdown.

The markdown plan (e.g. design/run-board-v1x.md) is the source of truth; this
HTML is a deterministic *view* of it, regenerated whenever the markdown changes
so the two never drift (same discipline as verdict.json -> final-consensus.html).
Never hand-edit the HTML — run this.

Usage:
  render_plan.py plan.md                         -> writes plan.html (alongside)
  render_plan.py plan.md -o out.html
  render_plan.py plan.md --check                 -> render + verify, write nothing
  render_plan.py plan.md --template t.html       -> use a specific template
  render_plan.py plan.md --eyebrow "..."         -> override the masthead eyebrow

Exit codes: 0 ok, 2 usage / data / unresolved-placeholder error.
Standard library only; no third-party dependencies.

THE PLAN-MARKDOWN DIALECT
-------------------------
  # Plan title
  > One-line subtitle.                         (blockquote right after the H1)

  - **Updated:** 2026-06-25                     (top-level bullets before the
  - **Source:** design/run-board-conductor.md    first '##' -> header chips)

  ## Overview
  Editorial lede paragraphs.

  ## Milestone: Round 3 / `auto` stop-rule       (auto-numbered M1, M2, ...)
  status: wip                                    (optional; else derived)
  Short description of the milestone.

  ### Phase 1 — Design the stop-rule             (### -> a phase)
  status: done                                   (optional; else derived)
  - [x] a done task                              (ONE checklist item per line; marks:
  - [wip] an in-progress task                     [ ]=todo  [x]=done  [wip]=in progress
  - [ ] a todo task                               [f]=failed/blocked. An unknown mark
  - [f] a failed task                             is an error, never silently dropped.)
  Testing: how this phase is proven.             (optional)
  Gate: `python3 -m unittest ...`                (optional; the must-pass command)

  ## Decisions                                   (optional)
  - **D1** Title — rationale body.
  ## Risks                                        (optional)
  - **R1** Title — mitigation body.
  ## Dependency order                             (optional)
  ```svg
  <svg ...>...</svg>                              (diagram-as-code; only a ```svg fence is
  ```                                              inlined, verbatim except that <script>,
                                                   <foreignObject> and on* handlers are
                                                   scrubbed — author it as trusted markup.)

Progress (overall ring + per-milestone bar) and every status badge are COMPUTED
from the checklist states, not authored — so they cannot lie about the markdown.
"""
from __future__ import annotations

import argparse
import html
import math
import os
import re
import sys

# --- template engine -----------------------------------------------------------
# This block/{{TOKEN}} engine is a deliberate sibling of render_handoff.py (the
# canonical copy). Keep them in step; extracting a shared _render_engine.py is a
# tracked follow-up (it would also touch the released render_handoff/render_verdict).
BLOCK_KEYS = {
    "SUBTITLE": "subtitle", "META": "meta", "RAIL": "rail", "OVERVIEW": "overview",
    "MILESTONE": "milestones", "DESC": "desc", "PHASE": "phases", "TASK": "tasks",
    "TESTING": "testing", "GATE": "gate",
    "DECISIONS": "decisions", "DECISION": "decision",
    "RISKS": "risks", "RISK": "risk", "DIAGRAM": "diagram",
}
# Tokens whose values are already-HTML fragments and pass through unescaped.
RAW_TOKENS = {
    "FONTS", "SUBTITLE", "OVERVIEW", "MS_TITLE", "MS_DESC", "PH_TITLE", "TASK_TEXT",
    "PH_TESTING", "DEC_TITLE", "DEC_BODY", "RISK_TITLE", "RISK_BODY", "DIAGRAM",
    "METADATA",
}
TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
BEGIN_RE = re.compile(r"<!--\s*BEGIN ([A-Z][A-Z ]*?)\s*(?:\([^)]*\))?\s*-->")
MARKER_RE = re.compile(r"<!--\s*(BEGIN|END) ([A-Z][A-Z ]*?)\s*(?:\([^)]*\))?\s*-->")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
DIVIDER_RE = re.compile(r"^<!--\s*=+.*=+\s*-->$")
SENTINEL_RE = re.compile("\x00S(\\d+)\x00")

RING_R = 52.0
RING_CIRC = 2 * math.pi * RING_R

STATE_LABEL = {"done": "Done", "wip": "In progress", "todo": "To do", "blocked": "Blocked"}
TASK_GLYPH = {"done": "✓", "wip": "●", "todo": "", "blocked": "✕"}
STATUS_WORD = {
    "done": "done", "complete": "done", "completed": "done", "x": "done",
    "wip": "wip", "in progress": "wip", "in-progress": "wip", "started": "wip",
    "todo": "todo", "to do": "todo", "to-do": "todo", "pending": "todo", "planned": "todo",
    "blocked": "blocked", "failed": "blocked", "fail": "blocked", "at risk": "blocked",
    "f": "blocked",
}
CHECK_STATE = {" ": "todo", "": "todo", "x": "done", "X": "done", "wip": "wip", "f": "blocked", "~": "blocked"}


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


# --------------------------------------------------------------------------- #
#  Inline markdown -> HTML (escape first, then a small, safe subset)            #
# --------------------------------------------------------------------------- #
_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_EM_RE = re.compile(r"(?<![\w*])[*_]([^*_\n]+)[*_](?![\w*])")


_SAFE_LINK_SCHEMES = {"http", "https", "mailto"}


def _link_repl(m: re.Match) -> str:
    """[text](url) -> anchor for safe schemes only; otherwise inert text.

    Rejects javascript:/data:/vbscript:/file: so a markdown link cannot smuggle a
    clickable script sink into the view (the body fields are RAW/unescaped)."""
    label, url = m.group(1), m.group(2)            # url is already html-escaped
    head = url.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if ":" in head and head.split(":", 1)[0].lower() not in _SAFE_LINK_SCHEMES:
        return label                               # drop the unsafe href, keep the text
    return f'<a href="{url}">{label}</a>'


def inline(text: str) -> str:
    """Escape, then apply inline `code`, **bold**, *em*, and [links]."""
    text = html.escape(text.strip(), quote=True)
    stash: list[str] = []

    def keep_code(m: re.Match) -> str:
        stash.append(f"<code>{m.group(1)}</code>")
        return f"\x00{len(stash) - 1}\x00"

    text = _CODE_RE.sub(keep_code, text)               # protect code spans first
    text = _LINK_RE.sub(_link_repl, text)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _EM_RE.sub(r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], text)
    return text


def paragraphs(lines: list[str]) -> str:
    """Group lines into <p> blocks on blank-line boundaries."""
    out, buf = [], []
    for ln in lines:
        if ln.strip():
            buf.append(ln.strip())
        elif buf:
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
            buf = []
    if buf:
        out.append("<p>" + inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


def kv(key: str, value: str) -> list:
    """A 0/1-length list holding one {token: value} dict, so an optional block
    renders once when present and drops cleanly when the value is empty."""
    return [{key: value}] if value else []


# --------------------------------------------------------------------------- #
#  Parse the plan-markdown dialect into the render data model                   #
# --------------------------------------------------------------------------- #
CHECK_RE = re.compile(r"^\s*[-*]\s+\[(x|X|wip|f|~| )?\]\s+(.*)$")
STATUS_RE = re.compile(r"^\s*(?:\*\*)?status(?:\*\*)?\s*:\s*\*{0,2}\s*([A-Za-z ./-]+?)\s*\*{0,2}\s*$", re.I)
TESTING_RE = re.compile(r"^\s*(?:\*\*)?testing(?:\s+strategy)?(?:\*\*)?\s*:\s*(.*)$", re.I)
GATE_RE = re.compile(r"^\s*(?:\*\*)?(?:validation\s+)?gate(?:\*\*)?\s*:\s*(.*)$", re.I)
ENTRY_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*(.*)$")
META_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*\s*:?\s*(.*)$")
FENCE_RE = re.compile(r"^\s*```+\s*([A-Za-z0-9_-]*)\s*$")


def norm_status(word: str) -> str:
    return STATUS_WORD.get(word.strip().lower(), "")


def derive(states: list[str]) -> str:
    """Roll up child states into a parent state."""
    if not states:
        return "todo"
    if all(s == "done" for s in states):
        return "done"
    if any(s == "blocked" for s in states):
        return "blocked"
    if any(s in ("done", "wip") for s in states):
        return "wip"
    return "todo"


def split_title_body(rest: str):
    for sep in (" — ", " - ", ": "):
        if sep in rest:
            t, b = rest.split(sep, 1)
            return t.strip(), b.strip()
    return rest.strip(), ""


_SVG_SCRIPT_RE = re.compile(r"(?is)<script\b.*?</script\s*>")
_SVG_FOREIGN_RE = re.compile(r"(?is)<foreignobject\b.*?</foreignobject\s*>")
_SVG_ON_RE = re.compile(r"""(?i)\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""")


def scrub_svg(svg: str) -> str:
    """Strip active content from an inlined diagram — <script>, <foreignObject>, and
    on* event handlers. The diagram is the one verbatim (RAW) region, so it must not
    become a script sink; everything else in the view is already escaped."""
    svg = _SVG_SCRIPT_RE.sub("", svg)
    svg = _SVG_FOREIGN_RE.sub("", svg)
    svg = _SVG_ON_RE.sub("", svg)
    return svg


def parse_plan(text: str) -> dict:
    raw = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = raw.split("\n")

    title, subtitle = "", ""
    meta, overview, milestones, decisions, risks = [], [], [], [], []
    diagram = ""

    section = "preamble"          # preamble|overview|milestone|decisions|risks|deps
    cur_ms = cur_ph = None
    prose: list[str] = []         # buffer for the active prose region
    prose_target = None           # 'overview' | 'ms_desc' | 'testing' | None
    in_fence = False
    fence_lang = ""
    fence_buf: list[str] = []

    def flush_prose():
        nonlocal prose, prose_target
        if prose_target == "overview" and any(p.strip() for p in prose):
            overview.append(paragraphs(prose))
        elif prose_target == "ms_desc" and cur_ms is not None and any(p.strip() for p in prose):
            cur_ms["_desc"] = paragraphs(prose)
        elif prose_target == "testing" and cur_ph is not None and any(p.strip() for p in prose):
            cur_ph["_testing"] = paragraphs(prose)
        prose, prose_target = [], None

    def close_phase():
        # Flush unconditionally: before the first '###' the pending prose is the
        # milestone description (cur_ph is still None) — it must not be dropped.
        flush_prose()

    def close_milestone():
        nonlocal cur_ph
        flush_prose()
        cur_ph = None

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # fenced code blocks: capture verbatim (diagram), never parse inside.
        fence = FENCE_RE.match(line)
        if in_fence:
            if fence is not None:
                if section == "deps" and fence_lang == "svg" and not diagram:
                    diagram = scrub_svg("\n".join(fence_buf).strip())
                in_fence = False
                fence_lang = ""
                fence_buf = []
            else:
                fence_buf.append(line)
            i += 1
            continue
        if fence is not None:
            flush_prose()
            in_fence = True
            fence_lang = (fence.group(1) or "").lower()
            fence_buf = []
            i += 1
            continue

        h2 = re.match(r"^##\s+(.*)$", line)
        h3 = re.match(r"^###\s+(.*)$", line)
        h1 = re.match(r"^#\s+(.*)$", line)

        if h1 and not title:
            title = h1.group(1).strip()
            i += 1
            continue

        if h2:
            flush_prose()
            close_milestone()
            cur_ms = None
            head = h2.group(1).strip()
            low = head.lower()
            if low.startswith("milestone") and not low.startswith("milestones"):
                # Any '## Milestone …' IS a milestone — it is never silently
                # reclassified, so a typo'd separator (en-dash, missing colon) can't
                # drop the milestone and all its phases/tasks from the totals.
                name = re.sub(r"^Milestone\b[\s:–—-]*", "", head, flags=re.I).strip()
                if not name:
                    die(f"milestone heading has no title: '## {head}'")
                section = "milestone"
                cur_ms = {"title": name, "status": "", "_desc": "", "phases": []}
                milestones.append(cur_ms)
                prose_target = "ms_desc"
            elif low.startswith("overview"):
                section = "overview"
                prose_target = "overview"
            elif low.startswith("decision"):
                section = "decisions"
            elif low.startswith("risk"):
                section = "risks"
            elif low.startswith("depend"):
                section = "deps"
            else:
                section = "other"
            i += 1
            continue

        if h3:
            if section != "milestone" or cur_ms is None:
                die(f"phase heading '### {h3.group(1).strip()}' has no milestone — "
                    "every '###' phase must follow a '## Milestone:' heading")
            close_phase()
            cur_ph = {"title": h3.group(1).strip(), "status": "", "tasks": [],
                      "_testing": "", "_gate": ""}
            cur_ms["phases"].append(cur_ph)
            prose_target = None
            i += 1
            continue

        # subtitle: a blockquote in the preamble (right after the H1)
        if section == "preamble" and line.strip().startswith(">") and not subtitle:
            subtitle = line.strip()[1:].strip()
            i += 1
            continue

        # status: line (milestone or phase)
        sm = STATUS_RE.match(line)
        if sm and section == "milestone":
            st = norm_status(sm.group(1))
            if st:
                if cur_ph is not None:
                    cur_ph["status"] = st
                elif cur_ms is not None:
                    cur_ms["status"] = st
            i += 1
            continue

        # checklist item (within a phase)
        cm = CHECK_RE.match(line)
        if cm and cur_ph is not None:
            flush_prose()
            mark = cm.group(1) if cm.group(1) is not None else " "
            state = CHECK_STATE.get(mark, "todo")
            cur_ph["tasks"].append({"state": state, "text": cm.group(2).strip()})
            i += 1
            continue

        # A checklist-shaped bullet with an unrecognized mark must fail loud, not vanish.
        if cur_ph is not None:
            bad = re.match(r"^\s*[-*]\s+\[([^\]]*)\]\s+\S", line)
            if bad:
                die(f"unrecognized checklist mark '[{bad.group(1)}]' "
                    "(use '[ ]' todo, '[x]' done, '[wip]', or '[f]' failed/blocked)")

        # testing strategy (within a phase)
        tm = TESTING_RE.match(line)
        if tm and cur_ph is not None:
            flush_prose()
            first = tm.group(1).strip()
            prose = [first] if first else []
            prose_target = "testing"
            i += 1
            continue

        # validation gate (within a phase)
        gm = GATE_RE.match(line)
        if gm and cur_ph is not None:
            flush_prose()
            cmd = gm.group(1).strip().strip("*").strip()    # tolerate **Gate:** **`cmd`**
            if len(cmd) >= 2 and cmd[0] == "`" and cmd[-1] == "`":
                cmd = cmd[1:-1].strip()
            cur_ph["_gate"] = cmd
            i += 1
            continue

        # decisions / risks entries
        if section in ("decisions", "risks"):
            em = ENTRY_RE.match(line)
            if em:
                tag, rest = em.group(1).strip(), em.group(2).strip()
                ttl, body = split_title_body(rest)
                bucket = decisions if section == "decisions" else risks
                bucket.append({"tag": tag, "title": ttl, "body": body})
                i += 1
                continue

        # preamble meta bullets
        if section == "preamble":
            mm = META_RE.match(line)
            if mm:
                meta.append({"label": mm.group(1).strip().rstrip(":"), "value": mm.group(2).strip()})
                i += 1
                continue

        # otherwise: prose for the active region
        if prose_target in ("overview", "ms_desc", "testing"):
            prose.append(line)
        i += 1

    flush_prose()
    close_milestone()

    return _build_model(title, subtitle, meta, overview, milestones, decisions, risks, diagram)


# --------------------------------------------------------------------------- #
#  Build the template data model (computes all progress + status)              #
# --------------------------------------------------------------------------- #
def _build_model(title, subtitle, meta, overview, milestones, decisions, risks, diagram) -> dict:
    total = done = 0
    ms_items, rail = [], []
    for idx, ms in enumerate(milestones, 1):
        ph_items, ms_states = [], []
        ms_total = ms_done = 0
        for ph in ms["phases"]:
            t_states = [t["state"] for t in ph["tasks"]]
            ph_derived = derive(t_states)
            ph_state = ph["status"] or ph_derived
            if ph["status"] and t_states and ph["status"] != ph_derived:
                print(f"warning: phase '{ph['title']}' is marked status:{ph['status']} "
                      f"but its tasks imply '{ph_derived}' — the badge will not match the bar",
                      file=sys.stderr)
            ms_states.append(ph_state)
            ms_total += len(ph["tasks"])
            ms_done += sum(1 for s in t_states if s == "done")
            tasks = [{
                "task_state": t["state"],
                "task_glyph": TASK_GLYPH[t["state"]],
                "task_text": inline(t["text"]),
            } for t in ph["tasks"]]
            ph_items.append({
                "ph_state": ph_state,
                "ph_title": inline(ph["title"]),
                "ph_state_label": STATE_LABEL[ph_state],
                "tasks": tasks,
                "testing": kv("ph_testing", ph["_testing"]),
                "gate": kv("ph_gate", ph["_gate"]),
            })
        ms_derived = derive(ms_states)
        ms_state = ms["status"] or ms_derived
        if ms["status"] and ms_states and ms["status"] != ms_derived:
            print(f"warning: milestone '{ms['title']}' is marked status:{ms['status']} "
                  f"but its phases imply '{ms_derived}'", file=sys.stderr)
        total += ms_total
        done += ms_done
        pct = round(100 * ms_done / ms_total) if ms_total else 0
        ms_items.append({
            "ms_state": ms_state,
            "ms_num": idx,
            "ms_title": inline(ms["title"]),
            "ms_state_label": STATE_LABEL[ms_state],
            "ms_pct": pct,
            "ms_done": ms_done,
            "ms_total": ms_total,
            "desc": kv("ms_desc", ms["_desc"]),
            "phases": ph_items,
        })
        rail.append({"rail_state": ms_state, "rail_num": f"M{idx}"})

    overall = round(100 * done / total) if total else 0
    offset = RING_CIRC * (1 - overall / 100)

    decisions_data = [{"decision": [
        {"dec_tag": d["tag"], "dec_title": inline(d["title"]), "dec_body": inline(d["body"])}
        for d in decisions]}] if decisions else []
    risks_data = [{"risk": [
        {"risk_tag": r["tag"], "risk_title": inline(r["title"]), "risk_body": inline(r["body"])}
        for r in risks]}] if risks else []

    return {
        "title": title or "Untitled plan",
        "subtitle": kv("subtitle", inline(subtitle) if subtitle else ""),
        "meta": [{"meta_label": m["label"], "meta_value": m["value"]} for m in meta],
        "rail": rail,
        "overview": kv("overview", overview[0] if overview else ""),
        "progress_label": f"{overall}%",
        "ring_circ": f"{RING_CIRC:.1f}",
        "ring_offset": f"{offset:.1f}",
        "done_count": done,
        "total_count": total,
        "milestones": ms_items,
        "decisions": decisions_data,
        "risks": risks_data,
        "diagram": kv("diagram", diagram),
    }


# --------------------------------------------------------------------------- #
#  Template fill (BEGIN/END blocks + {{TOKEN}} substitution)                    #
# --------------------------------------------------------------------------- #
def find_first_block(tpl: str):
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


def substitute(tpl: str, ctx: dict, stash: list) -> str:
    def repl(match: re.Match) -> str:
        token = match.group(1)
        key = token.lower()
        if key not in ctx or isinstance(ctx[key], list):
            return match.group(0)              # a genuine unfilled template slot
        value = "" if ctx[key] is None else str(ctx[key])
        value = value if token in RAW_TOKENS else html.escape(value, quote=True)
        stash.append(value)                    # hide filled content behind a sentinel so
        return f"\x00S{len(stash) - 1}\x00"    # later scans see the template, not the data

    return TOKEN_RE.sub(repl, tpl)


def render_item(tpl: str, ctx: dict, stash: list) -> str:
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
        rendered = "".join(render_item(inner, it, stash) for it in items)
        tpl = tpl[:start] + rendered + tpl[end:]
    return substitute(tpl, ctx, stash)


def strip_comments(out: str) -> str:
    def decide(match: re.Match) -> str:
        comment = match.group(0)
        if "\n" not in comment and DIVIDER_RE.match(comment.strip()):
            return comment
        return ""
    return COMMENT_RE.sub(decide, out)


def render(data: dict, template: str, fonts: str) -> str:
    data = dict(data, fonts=fonts)
    stash: list = []
    out = render_item(template, data, stash)

    # Filled data/author content now sits behind \x00S..\x00 sentinels, so these passes
    # police ONLY the template: strip its authoring comments, then a surviving {{TOKEN}}
    # is a real unfilled slot and a surviving comment is a real leftover. Verbatim author
    # content (e.g. an SVG carrying comments or '{{...}}') is stashed and restored LAST,
    # so it is neither scanned nor mutated.
    out = strip_comments(out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    leftover = sorted(set(TOKEN_RE.findall(out)))
    if leftover:
        die("unresolved placeholder(s): " + ", ".join("{{%s}}" % t for t in leftover))
    if "<!--" in out and not all(DIVIDER_RE.match(c.strip()) for c in COMMENT_RE.findall(out)):
        die("authoring comment survived rendering")

    return SENTINEL_RE.sub(lambda m: stash[int(m.group(1))], out)   # restore verbatim, last


def here(*parts: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *parts)


def build_metadata(source: str, data: dict) -> str:
    src = html.escape(os.path.basename(source))
    return (
        f"Rendered from <code>{src}</code> &middot; "
        f"{len(data['milestones'])} milestones &middot; "
        f"{data['done_count']}/{data['total_count']} tasks complete. "
        "The markdown plan is the source of truth &mdash; regenerate with "
        "<code>render_plan.py</code>; never hand-edit this file."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render a planning markdown to a self-contained HTML view.")
    parser.add_argument("plan", help="path to the plan markdown")
    parser.add_argument("-o", "--out", default=None, help="output path (default: <plan>.html)")
    parser.add_argument("--template", default=None, help="template path (default: ../references/plan-template.html)")
    parser.add_argument("--fonts", default=None, help="embedded fonts CSS (default: ../references/plan-fonts.css)")
    parser.add_argument("--eyebrow", default="Advisory Board · Plan", help="masthead eyebrow text")
    parser.add_argument("--check", action="store_true", help="render and verify only; write nothing")
    args = parser.parse_args(argv)

    try:
        with open(args.plan, encoding="utf-8") as handle:
            text = handle.read()
    except FileNotFoundError:
        die(f"{args.plan}: not found")

    template_path = args.template or here("..", "references", "plan-template.html")
    try:
        with open(template_path, encoding="utf-8") as handle:
            template = handle.read()
    except FileNotFoundError:
        die(f"{template_path}: template not found")

    fonts_path = args.fonts or here("..", "references", "plan-fonts.css")
    try:
        with open(fonts_path, encoding="utf-8") as handle:
            fonts = handle.read()
    except FileNotFoundError:
        print(f"warning: {fonts_path}: fonts asset not found; falling back to system fonts",
              file=sys.stderr)
        fonts = "/* plan-fonts.css not found — using Arial/Georgia fallback */"

    data = parse_plan(text)
    data["eyebrow"] = args.eyebrow
    data["metadata"] = build_metadata(args.plan, data)

    out = render(data, template, fonts)

    if args.check:
        print(f"ok: rendered cleanly ({len(out)} bytes), no placeholders left; "
              f"{data['done_count']}/{data['total_count']} tasks, {data['progress_label']} complete")
        return 0

    out_path = args.out or os.path.splitext(args.plan)[0] + ".html"
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(out)
    print(f"wrote {out_path} ({len(out)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

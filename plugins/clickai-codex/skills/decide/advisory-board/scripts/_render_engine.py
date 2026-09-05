#!/usr/bin/env python3
"""Shared block / {{TOKEN}} template engine for the advisory-board renderers.

Each renderer produces an HTML (or Markdown) *view* of a source of truth, and
they all fill the same kind of template the same way — depth-aware expansion of
repeatable ``<!-- BEGIN X -->..<!-- END X -->`` blocks, ``{{TOKEN}}``
substitution, authoring-comment stripping, and the loud guards that refuse to
emit a half-filled template. That shared mechanism lives here, parameterized by
each caller's ``BLOCK_KEYS`` and ``RAW_TOKENS``; each renderer keeps its own
data-model builder, template, and CLI.

Callers:
  * render_handoff.py - final-consensus.html from handoff-data.json
  * render_verdict.py - final-consensus.md/html from verdict.json (HTML via render_handoff)
  * render_plan.py    - a plan's HTML view from its markdown (uses the stash; see below)

Each caller supplies:
  block_keys : {"BLOCK NAME": "ctx list key"}  -- repeatable blocks -> the ctx list to expand
  raw_tokens : {"TOKEN", ...}                  -- tokens whose values are already-HTML (pass-through)

THE SENTINEL STASH (opt-in via ``stash=``)
------------------------------------------
By default :func:`substitute` inlines each token's value straight into the
template, and the caller's post-processing (:func:`strip_comments`, then
:func:`assert_fully_resolved`) scans the whole output -- filled data included.
That is fine when the data never contains a literal ``{{...}}`` or ``<!--``, but
a renderer that inlines *verbatim* author content (an SVG diagram carrying its
own comments, a plan quoting a ``{{jinja}}`` snippet) needs that content held
out of those scans or the guards would mangle it or abort. Passing a ``stash``
list turns the protection on: each filled value is replaced by a
``\\x00S{n}\\x00`` sentinel and pushed onto ``stash``; the caller runs its
guards against the now data-free template, then calls :func:`restore_stash`
LAST to splice the verbatim values back in -- neither scanned nor mutated.

Standard library only; no third-party dependencies.
"""
from __future__ import annotations

import html
import re
import sys

# Marker / token grammar. Shared verbatim by every renderer so the templates
# speak one dialect.
TOKEN_RE = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
BEGIN_RE = re.compile(r"<!--\s*BEGIN ([A-Z][A-Z ]*?)\s*(?:\([^)]*\))?\s*-->")
MARKER_RE = re.compile(r"<!--\s*(BEGIN|END) ([A-Z][A-Z ]*?)\s*(?:\([^)]*\))?\s*-->")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
DIVIDER_RE = re.compile(r"^<!--\s*=+.*=+\s*-->$")
SENTINEL_RE = re.compile("\x00S(\\d+)\x00")


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def find_first_block(tpl: str):
    """Return (start, end, name, inner) for the first BEGIN..matching END block.

    Matching is depth-aware so a nested block (e.g. ROUND inside SEAT CARD)
    doesn't end the outer block early. Returns None when no block remains.
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


def substitute(tpl: str, ctx: dict, raw_tokens, stash=None) -> str:
    """Fill ``{{TOKEN}}`` scalars from ``ctx``.

    A token in ``raw_tokens`` passes through as authored HTML; any other is
    HTML-escaped. A token that is absent from ``ctx`` or maps to a list is left
    untouched, for the leftover-placeholder guard to catch. When ``stash`` is a
    list, the filled value is hidden behind a sentinel instead of inlined (see
    the module docstring).
    """
    def repl(match: re.Match) -> str:
        token = match.group(1)
        key = token.lower()
        if key not in ctx or isinstance(ctx[key], list):
            return match.group(0)  # leave for the final unresolved-token check
        value = "" if ctx[key] is None else str(ctx[key])
        value = value if token in raw_tokens else html.escape(value, quote=True)
        if stash is None:
            return value
        stash.append(value)
        return f"\x00S{len(stash) - 1}\x00"

    return TOKEN_RE.sub(repl, tpl)


def render_item(tpl: str, ctx: dict, block_keys, raw_tokens, stash=None) -> str:
    """Expand every repeatable block against ``ctx``, then fill its scalars."""
    while True:
        block = find_first_block(tpl)
        if block is None:
            break
        start, end, name, inner = block
        key = block_keys.get(name)
        if key is None:
            die(f"unknown template block: {name!r}")
        items = ctx.get(key) or []
        if not isinstance(items, list):
            die(f"{key!r} must be a list; got {type(items).__name__}")
        rendered = "".join(
            render_item(inner, item, block_keys, raw_tokens, stash) for item in items
        )
        tpl = tpl[:start] + rendered + tpl[end:]
    return substitute(tpl, ctx, raw_tokens, stash)


def strip_comments(out: str) -> str:
    """Drop authoring comments; keep single-line ``=====`` section dividers."""
    def decide(match: re.Match) -> str:
        comment = match.group(0)
        if "\n" not in comment and DIVIDER_RE.match(comment.strip()):
            return comment
        return ""

    return COMMENT_RE.sub(decide, out)


def assert_fully_resolved(out: str) -> None:
    """Fail loudly if a real template slot or authoring comment survived.

    Run this AFTER :func:`strip_comments`. When the stash is in use, run it
    while values are still stashed (before :func:`restore_stash`) so verbatim
    author content is never mistaken for a leftover placeholder or comment.
    """
    leftover = sorted(set(TOKEN_RE.findall(out)))
    if leftover:
        die("unresolved placeholder(s): " + ", ".join("{{%s}}" % t for t in leftover))
    if "<!--" in out and not all(
        DIVIDER_RE.match(c.strip()) for c in COMMENT_RE.findall(out)
    ):
        die("authoring comment survived rendering")


def restore_stash(out: str, stash) -> str:
    """Splice stashed verbatim values back in. Call LAST, after the guards."""
    def repl(match: re.Match) -> str:
        index = int(match.group(1))
        if index >= len(stash):  # a sentinel we never minted -> fail loudly, not IndexError
            die(f"dangling stash sentinel S{index} (stash holds {len(stash)})")
        return stash[index]

    return SENTINEL_RE.sub(repl, out)

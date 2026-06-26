#!/usr/bin/env python3
"""A small, deterministic Markdown -> HTML converter for the handoff renderer.

Seat reviews are raw Markdown (that is what the models emit). The handoff template
styles real HTML (`<p class="r-title">` sub-heads, `<strong>`, `<ul>/<li>`, `<code>`,
`<pre>`), so the renderer converts the Markdown to those elements rather than asking
the data author to hand-build HTML — the fragile step that previously left literal
`##` and `**` in the published artifact.

Scope is deliberately the subset models actually produce in a review: ATX headings,
bold/italic, inline code, fenced code, ordered/unordered lists, blockquotes, links,
and blank-line-separated paragraphs. Not a CommonMark engine; no nested lists, no
tables, no reference links. Standard library only.

Safety: all text is HTML-escaped BEFORE markup tags are inserted, so a review that
contains `<script>` or `&` renders as literal text, never live HTML. Inline code is
captured first so `*` / `_` inside a code span are not treated as emphasis.
"""
from __future__ import annotations

import html
import re

__all__ = ["md_to_html"]

# Private-use sentinels: a code span is lifted out before escaping/emphasis and
# restored last, so backticks protect their contents from every other rule.
_CODE_OPEN, _CODE_CLOSE = "", ""

_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
# A whole-line bold span (e.g. **2. Strongest Objections**) is a section heading in
# these reviews, equivalent to an ATX `## ...` heading — render it the same way.
_BOLD_HEADING = re.compile(r"^\*\*(.+?)\*\*$|^__(.+?)__$")
_BLOCKQUOTE = re.compile(r"^\s*>\s?")
_UL_ITEM = re.compile(r"^\s*[-*+]\s+")
# Bound the marker to 1-9 digits: a real ordered-list number never needs more, and an
# unbounded run would feed int() a 4300+-digit string (Python's int-from-str limit) and
# raise — a pathological line just falls through to a paragraph instead.
_OL_ITEM = re.compile(r"^\s*(\d{1,9})[.)]\s+")
# Link schemes that are safe in an href. Anything else (javascript:, data:, vbscript:,
# protocol-relative //host, …) collapses to '#' so a review cannot plant a
# code-execution or off-site-phishing link. A single leading '/' (site-relative) is
# allowed, but '//' is not.
_SAFE_URL = re.compile(r"(?i)^(?:https?:|mailto:|tel:|#|/(?!/)|\.{1,2}/)")


def _safe_href(escaped_url: str) -> str:
    """Make a captured (already &<>-escaped, quote=False) link URL safe for an href:
    allowlist the scheme, then neutralize the quotes escaping left — the
    attribute-breakout vector — without double-escaping the ampersands."""
    url = escaped_url.strip()
    # A code-span sentinel inside a URL means backticks were used in the link target
    # (nonsensical, and the restore would later splice raw bytes into the href AFTER
    # this sanitization) — collapse such a URL to '#'.
    if _CODE_OPEN in url or _CODE_CLOSE in url:
        return "#"
    if not _SAFE_URL.match(url):
        return "#"
    return url.replace('"', "&quot;").replace("'", "&#x27;")


def _inline(text: str) -> str:
    """Inline Markdown -> HTML on a single text run. Escapes first, then inserts tags."""
    # Drop any author copy of the code-span sentinels so a review cannot forge a
    # placeholder (which would otherwise crash the restore or inject a fake <code>).
    text = text.replace(_CODE_OPEN, "").replace(_CODE_CLOSE, "")
    spans: list = []

    def _stash_code(m):
        # quote=True so a restored <code> can NEVER re-introduce a raw " or ' — those
        # are spliced back in AFTER href sanitization, so an unescaped quote here would
        # break out of an href="..." (a code span embedded in a link URL). Inside the
        # rendered <code> a quote shows correctly as its entity.
        spans.append(html.escape(m.group(1), quote=True))
        return f"{_CODE_OPEN}{len(spans) - 1}{_CODE_CLOSE}"

    text = re.sub(r"`([^`]+)`", _stash_code, text)
    text = html.escape(text, quote=False)
    # links: label already escaped; href scheme-allowlisted + quote-neutralized. The
    # label class forbids '[' (as well as ']') so a long run of unclosed '[' can't drive
    # O(n^2) backtracking.
    text = re.sub(r"\[([^\][]+)\]\(([^)\s]+)\)",
                  lambda m: f'<a href="{_safe_href(m.group(2))}">{m.group(1)}</a>', text)
    # bold before italic so ** is consumed first
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    # italic: a single * or _ not adjacent to another marker / word char
    text = re.sub(r"(?<![\*\w])\*(?!\s)([^*\n]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<![_\w])_(?!\s)([^_\n]+?)_(?![_\w])", r"<em>\1</em>", text)
    # restore code spans (already escaped); a stray/out-of-range marker stays literal
    def _restore(m):
        idx = int(m.group(1))
        return f"<code>{spans[idx]}</code>" if 0 <= idx < len(spans) else m.group(0)

    text = re.sub(rf"{_CODE_OPEN}(\d+){_CODE_CLOSE}", _restore, text)
    return text


def _emit_list(lines, i, n, item_re, tag, out):
    """Collect a (possibly loose) list of one type into a single <ul>/<ol>, absorbing
    a single blank line between items so blank-separated points render as ONE list
    with correct numbering — and return the index past the list. For an ordered list
    the first item's number becomes `start=`, so a list that begins at N (or a lone
    "N. ..." line) never silently loses its number."""
    items: list = []
    start = None
    while i < n:
        m = item_re.match(lines[i])
        if m:
            if tag == "ol" and start is None:
                start = int(m.group(1))
            items.append(item_re.sub("", lines[i]).strip())
            i += 1
        elif lines[i].strip() == "" and i + 1 < n and item_re.match(lines[i + 1]):
            i += 1   # blank line between two items of the same kind — stay in the list
        else:
            break
    attr = f' start="{start}"' if (tag == "ol" and start not in (None, 1)) else ""
    out.append(f"<{tag}{attr}>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + f"</{tag}>")
    return i


def md_to_html(text: str) -> str:
    """Convert a Markdown review body to an HTML fragment for the handoff template."""
    if not text:
        return ""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list = []
    para: list = []
    n = len(lines)
    i = 0

    def flush_para():
        if para:
            out.append("<p>" + _inline(" ".join(para).strip()) + "</p>")
            para.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()

        fence = _FENCE.match(line)
        if fence:
            ch = fence.group(1)[0]
            close = re.compile(rf"^\s*{re.escape(ch)}{{3,}}\s*$")
            j = i + 1
            body: list = []
            while j < n and not close.match(lines[j]):
                body.append(lines[j])
                j += 1
            if j < n:
                # a real, CLOSED code block
                flush_para()
                out.append("<pre><code>" + html.escape("\n".join(body), quote=False) + "</code></pre>")
                i = j + 1
                continue
            # UNTERMINATED fence: don't swallow the rest of the review (incl. the
            # verdict) into a <pre>. Drop the stray opening fence and process the
            # remaining lines as normal Markdown.
            i += 1
            continue

        if not stripped:
            flush_para()
            i += 1
            continue

        heading = _HEADING.match(line)
        if heading:
            flush_para()
            out.append('<p class="r-title">' + _inline(heading.group(2).strip()) + "</p>")
            i += 1
            continue

        bold_head = _BOLD_HEADING.match(stripped)
        if bold_head:
            flush_para()
            out.append('<p class="r-title">' + _inline((bold_head.group(1) or bold_head.group(2)).strip()) + "</p>")
            i += 1
            continue

        if _BLOCKQUOTE.match(line):
            flush_para()
            quoted: list = []
            while i < n and _BLOCKQUOTE.match(lines[i]):
                quoted.append(_BLOCKQUOTE.sub("", lines[i]).strip())
                i += 1
            out.append("<blockquote>" + _inline(" ".join(quoted).strip()) + "</blockquote>")
            continue

        if _UL_ITEM.match(line):
            flush_para()
            i = _emit_list(lines, i, n, _UL_ITEM, "ul", out)
            continue

        if _OL_ITEM.match(line):
            flush_para()
            i = _emit_list(lines, i, n, _OL_ITEM, "ol", out)
            continue

        para.append(stripped)
        i += 1

    flush_para()
    return "\n".join(out)

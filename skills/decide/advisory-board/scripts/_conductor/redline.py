"""Prose redline (v1.13 P3, D12) — a word-level-within-changed-lines diff of the
ORIGINAL source against the board's revised draft, rendered as `<ins>`/`<del>`
HTML for the full-handoff view.

This is a pure, stdlib-only VIEW: given two strings (original + revised), it
produces a list of redline "rows" the renderer turns into HTML. No file I/O, no
model reasoning — the diff is `difflib.SequenceMatcher.get_opcodes()`, exactly
the mechanism the revision reconciliation (revision.py) already trusts to define
"a change". Line-level structure (context / delete / insert / replace), with a
word-level SECOND pass inside a replace pair so only the changed WORDS carry
`<del>`/`<ins>` spans (D12).

The renderer owns HTML escaping and the {{TOKEN}}-neutralizing (`_nb`) of the
row text; this module returns the STRUCTURE (row kind + the word-level segments)
and leaves every string un-escaped, so the escaping discipline stays in one
place (render_verdict._raw / _nb). See render_verdict.build_redline_rows.

Cap: at most REDLINE_MAX_LINES rendered rows (mirrors revise.DIFF_MAX_LINES=400);
over the cap the caller appends an explicit truncation pointer to the artifact.
"""
from __future__ import annotations

import difflib

__all__ = [
    "REDLINE_MAX_LINES",
    "REDLINE_CONTEXT_LINES",
    "build_redline",
]

# The rendered-row budget for the redline section. Mirrors revise.DIFF_MAX_LINES
# (the injected-diff cap) so the two "how much diff do we show" numbers share one
# rationale: orientation, not the material. Over the cap the section truncates
# with a pointer to revised-draft.md (which always carries the full revised text).
REDLINE_MAX_LINES = 400

# How many unchanged CONTEXT lines to keep on each side of a changed region — a
# line or two of orientation (D12: "unchanged context (a line or two)"), never
# the whole unchanged file.
REDLINE_CONTEXT_LINES = 2


def _word_segments(a_line: str, b_line: str):
    """Word-level diff of two CHANGED lines → (del_segments, ins_segments).

    Each segments list is `[(changed: bool, text: str), ...]` in order: a
    `del_segments` list reconstructs the ORIGINAL line (its changed runs are the
    words that were removed/replaced), an `ins_segments` list reconstructs the
    REVISED line (its changed runs are the words that were added/replaced). A
    reader renders the unchanged runs plain and wraps only the changed runs in
    `<del>` / `<ins>` (D12: word-level within changed lines).

    Tokenized on a word-plus-trailing-whitespace boundary so whitespace rides
    with its word and the reconstruction is byte-exact — ''.join of either
    segment list's texts equals the corresponding input line."""
    a_words = _split_words(a_line)
    b_words = _split_words(b_line)
    sm = difflib.SequenceMatcher(None, a_words, b_words, autojunk=False)
    del_segs = []
    ins_segs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        a_text = "".join(a_words[i1:i2])
        b_text = "".join(b_words[j1:j2])
        if tag == "equal":
            if a_text:
                del_segs.append((False, a_text))
            if b_text:
                ins_segs.append((False, b_text))
        else:  # replace | delete | insert — the changed runs
            if a_text:
                del_segs.append((True, a_text))
            if b_text:
                ins_segs.append((True, b_text))
    return del_segs, ins_segs


def _split_words(line: str):
    """Split a line into word-plus-trailing-whitespace tokens. Each token is a
    run of non-whitespace followed by its trailing whitespace run, so ''.join of
    the tokens is byte-identical to the input (no separator is dropped or added).
    A leading-whitespace run becomes its own token (empty word + the space)."""
    tokens = []
    i = 0
    n = len(line)
    while i < n:
        start = i
        # consume a non-whitespace run
        while i < n and not line[i].isspace():
            i += 1
        # consume the trailing whitespace run
        while i < n and line[i].isspace():
            i += 1
        tokens.append(line[start:i])
    return tokens


def _emit_context(rows, lines, lo, hi):
    """Append `context` rows for lines[lo:hi] (0-based, half-open)."""
    for text in lines[lo:hi]:
        rows.append({"kind": "context", "text": text})


def build_redline(original: str, revised: str):
    """Build the redline row list for the original→revised diff.

    Returns `(rows, truncated, total)`:
      * rows: a list of dicts, each one of —
          {"kind": "context", "text": <line>}
          {"kind": "delete",  "text": <line>}
          {"kind": "insert",  "text": <line>}
          {"kind": "replace", "del_segments": [...], "ins_segments": [...],
                              "del_text": <orig line>, "ins_text": <revised line>}
        (segments are `(changed, text)` tuples from _word_segments). Every string
        is UN-escaped — the renderer escapes.
      * truncated: True when the full row list exceeded REDLINE_MAX_LINES and
        `rows` was cut to the cap.
      * total: the full (pre-cap) row count, so the caller can say "… N more".

    Line-level structure via get_opcodes over splitlines() (no keepends — the
    redline is a human VIEW, not a byte-reconciliation; line terminators are
    framing, not content here). Only a line or two of unchanged CONTEXT is kept
    around each change; long unchanged runs collapse to REDLINE_CONTEXT_LINES on
    each side. A `replace` opcode pairs original lines with revised lines by
    position and runs the word-level second pass on each pair; unmatched tail
    lines in the longer side become plain delete/insert rows."""
    a = original.splitlines()
    b = revised.splitlines()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    opcodes = sm.get_opcodes()

    rows = []
    for idx, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if tag == "equal":
            # Keep only a little context: the tail of the run before the NEXT
            # change and the head of the run after the PREVIOUS change. A run at
            # the very top/bottom of the file with no adjacent change on one side
            # keeps context only on the side that touches a change.
            has_prev = idx > 0
            has_next = idx < len(opcodes) - 1
            span = i2 - i1
            if not has_prev and not has_next:
                # whole file unchanged — no redline to show (all context)
                _emit_context(rows, a, i1, i2)
                continue
            head = i1
            tail = i2
            if has_prev and has_next and span > 2 * REDLINE_CONTEXT_LINES:
                _emit_context(rows, a, i1, i1 + REDLINE_CONTEXT_LINES)
                rows.append({"kind": "gap",
                             "text": f"… {span - 2 * REDLINE_CONTEXT_LINES} unchanged line(s) …"})
                _emit_context(rows, a, i2 - REDLINE_CONTEXT_LINES, i2)
                continue
            if has_prev and not has_next:
                head = min(i2, i1 + REDLINE_CONTEXT_LINES) if span > REDLINE_CONTEXT_LINES else i1
                if head > i1:
                    _emit_context(rows, a, i1, head)
                    if head < i2:
                        rows.append({"kind": "gap",
                                     "text": f"… {i2 - head} unchanged line(s) …"})
                else:
                    _emit_context(rows, a, i1, i2)
                continue
            if has_next and not has_prev:
                tail = max(i1, i2 - REDLINE_CONTEXT_LINES) if span > REDLINE_CONTEXT_LINES else i2
                if tail < i2:
                    if tail > i1:
                        rows.append({"kind": "gap",
                                     "text": f"… {tail - i1} unchanged line(s) …"})
                    _emit_context(rows, a, tail, i2)
                else:
                    _emit_context(rows, a, i1, i2)
                continue
            _emit_context(rows, a, i1, i2)
        elif tag == "delete":
            for text in a[i1:i2]:
                rows.append({"kind": "delete", "text": text})
        elif tag == "insert":
            for text in b[j1:j2]:
                rows.append({"kind": "insert", "text": text})
        else:  # replace — pair lines by position, word-diff each pair
            a_lines = a[i1:i2]
            b_lines = b[j1:j2]
            paired = min(len(a_lines), len(b_lines))
            for k in range(paired):
                del_segs, ins_segs = _word_segments(a_lines[k], b_lines[k])
                rows.append({
                    "kind": "replace",
                    "del_segments": del_segs, "ins_segments": ins_segs,
                    "del_text": a_lines[k], "ins_text": b_lines[k],
                })
            # An unequal replace: the extra original lines are pure deletes, the
            # extra revised lines pure inserts.
            for text in a_lines[paired:]:
                rows.append({"kind": "delete", "text": text})
            for text in b_lines[paired:]:
                rows.append({"kind": "insert", "text": text})

    total = len(rows)
    truncated = total > REDLINE_MAX_LINES
    if truncated:
        rows = rows[:REDLINE_MAX_LINES]
    return rows, truncated, total

#!/usr/bin/env python3
"""Severity filtering for the verdict renderers (v1.14 P1, roadmap #8).

The verdict schema already separates severities — `blockers[]` / `dissent[]` /
`concerns[]` (verdict-moving, structured) and `caveats[]` (plain strings, the
couldn't-verify bucket). This module is the ONE place that decides, per filter,
which of those tiers a renderer shows — it is *exposure*, not new modeling.

`--filter` picks the depth:

  * ``all``              — every tier (the default; a renderer given ``all`` or no
                           filter at all must be byte-identical to today).
  * ``blockers+dissent`` — blockers and dissent; the couldn't-verify bucket
                           (caveats + any concern-derived evidence) is elided.
  * ``blockers``         — blockers only; dissent AND the couldn't-verify bucket
                           are elided.

Elision is **loud, never silent** (house style: honest artifacts). A renderer
that drops a section states what it dropped, with counts, via `elision_note()` —
which is a pure FORMATTER: the renderer computes the exact counts of what its
shape suppressed (dissent entries, couldn't-verify lines) and passes them, so the
note's count of a dropped bucket matches exactly what was dropped. The summary/
verdict banner and confidence are NEVER filtered — only the findings sections are.

Standard library only; no third-party dependencies.
"""
from __future__ import annotations

# Ordered loosest → strictest. `all` is first so it reads as the default in help.
FILTER_CHOICES = ("all", "blockers+dissent", "blockers")
DEFAULT_FILTER = "all"

# The severity TIERS each filter keeps. `blockers` is always kept (it is the whole
# point of a block); `dissent` is the middle tier; `concerns`/caveats — the
# couldn't-verify bucket — is the lowest. A renderer asks show_* below rather than
# reading this directly.
_KEPT = {
    "all": {"blockers", "dissent", "concerns"},
    "blockers+dissent": {"blockers", "dissent"},
    "blockers": {"blockers"},
}


def show_dissent(filt: str) -> bool:
    """True when this filter renders the dissent section."""
    return "dissent" in _KEPT.get(filt, _KEPT[DEFAULT_FILTER])


def show_concerns(filt: str) -> bool:
    """True when this filter renders the concern/caveat tier — the couldn't-verify
    bucket (authored caveats + unverified/refuted evidence, incl. concern
    evidence). Blockers are always shown; there is no `show_blockers`."""
    return "concerns" in _KEPT.get(filt, _KEPT[DEFAULT_FILTER])


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def elision_note(filt: str, *, dissent_dropped: int = 0,
                 couldnt_verify_dropped: int = 0) -> str:
    """Format the explicit "(filtered: … — --filter X)" line, or "" when nothing
    was actually dropped.

    This is a PURE FORMATTER: the RENDERER computes what its shape actually
    suppressed and passes the counts. `dissent_dropped` is the number of dissent
    entries the shape would have rendered but the filter hid; `couldnt_verify_
    dropped` is the number of couldn't-verify LINES the shape would have rendered
    (`render_verdict._couldnt_verify_lines` — caveats + unverified/refuted
    evidence + amendment caveats) but the filter hid. A shape that renders neither
    bucket passes 0 for it, so the note never names a section that shape never
    shows (e.g. concerns are never rendered as items in these shapes — the note
    must never claim a dropped "concern").

    The counts name the honest buckets — "dissent(s)" and "couldn't-verify
    line(s)" — so each clause is auditable against exactly what the filter
    removed. `all` (or an unknown filter) always returns "" (it elides nothing),
    and a bucket with a zero count is omitted; when nothing was dropped the whole
    note is "".
    """
    if filt == DEFAULT_FILTER or filt not in _KEPT:
        return ""
    parts = []
    if dissent_dropped > 0:
        parts.append(_plural(dissent_dropped, "dissent"))
    if couldnt_verify_dropped > 0:
        parts.append(_plural(couldnt_verify_dropped, "couldn't-verify line"))
    if not parts:
        return ""
    return f"(filtered: {', '.join(parts)} — --filter {filt})"

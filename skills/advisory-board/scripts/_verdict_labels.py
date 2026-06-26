#!/usr/bin/env python3
"""Lens-aware human label for a `verdict.json` token.

The machine token `verdict` (`ship` | `caution` | `block`) is the canonical gate
axis and stays byte-identical everywhere — downstream parsing depends on it. But
the *human-facing* label rendered to a reader should fit the board's lens. A
software-architecture board ships code, so "SHIP / SHIP WITH CHANGES / DO NOT SHIP
YET" reads naturally. A product, research, legal, business, or writing board does
not "ship" anything — that jargon confused a non-developer reader — so for every
non-software preset (and any unknown one) we render plain language plus a one-line
"what this means" note.

The three renderers (`render_verdict.py` Markdown + handoff data, `format_output.py`
share formats) all consumed their own copy of the legacy software map; they now call
:func:`human_label` here so the families live in one place and can't drift apart.

Precedence (unchanged): an explicit `decision` field — the board's native call when
the decision isn't software-shipping (`invest` / `hold` / `wind-down`) — always wins
over the token map; we return it verbatim with no note.

Standard library only; no third-party dependencies.
"""
from __future__ import annotations

from typing import Optional, Tuple

# The legacy software-shipping labels. Used only for the `software-architecture`
# preset (the historical default), so existing software boards read unchanged.
SOFTWARE_LABELS = {"ship": "SHIP", "caution": "SHIP WITH CHANGES", "block": "DO NOT SHIP YET"}

# Plain language for every other lens (and any unknown preset). No shipping metaphor.
PLAIN_LABELS = {"ship": "Go ahead", "caution": "Proceed with care", "block": "Stop and rethink"}

# A one-line "what this means" note for each plain verdict — the bit a non-developer
# reader actually wanted. Software boards keep their familiar label and get no note.
PLAIN_NOTES = {
    "ship": "The board sees no blocking concerns — proceed with confidence.",
    "caution": "Workable, but address the flagged concerns before you go ahead.",
    "block": "The board found serious problems — don't proceed as-is.",
}

# The one preset that keeps the software-shipping labels. Absent/unknown presets fall
# through to PLAIN — EXCEPT a wholly missing field, which defaults to software for
# backward compatibility (every pre-feature verdict.json was a software-lens run and
# carried no `lens_preset`; see `human_label`).
SOFTWARE_PRESET = "software-architecture"

# Lens-aware professional-advice caveat for the human-facing artifacts. A software-lens
# board (and the absent/None default, which maps to software) carries NO disclaimer, so
# existing software runs are unchanged. The legal preset gets the lawyer-specific line;
# every other non-software preset (and any unknown one) gets the universal one. These
# strings are approved wording — keep them VERBATIM.
LEGAL_DISCLAIMER = (
    "Directional review to help you focus a conversation with a qualified attorney "
    "— not legal advice."
)
UNIVERSAL_DISCLAIMER = (
    "An advisory board sharpens your judgment; it doesn't replace professional advice "
    "where your decision warrants it."
)


def is_software_lens(lens_preset: Optional[str]) -> bool:
    """True when the board-level preset is the software-architecture family.

    A wholly absent preset (``None`` — an old verdict.json written before this field
    existed) defaults to software: those runs were all software-lens, and defaulting
    to plain would silently relabel them. An explicit-but-unknown string is treated
    as plain (it isn't the one special case)."""
    if lens_preset is None:
        return True
    return lens_preset == SOFTWARE_PRESET


def human_label(token: str, lens_preset: Optional[str] = None,
                decision: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """Resolve a verdict token to a (label, note) pair for human display.

    * an explicit ``decision`` wins verbatim, with no note (it's already the board's
      own words for the call);
    * else a software-lens board gets the legacy SHIP/… label and no note;
    * else (every other preset, and any unknown one) the plain label plus its
      one-line "what this means" note.

    ``note`` is ``None`` whenever there's nothing to add (a decision, or a software
    label); callers render it only when present."""
    if decision:
        return decision, None
    if is_software_lens(lens_preset):
        return SOFTWARE_LABELS.get(token, str(token)), None
    return PLAIN_LABELS.get(token, str(token)), PLAIN_NOTES.get(token)


def lens_disclaimer(lens_preset: Optional[str]) -> Optional[str]:
    """The professional-advice caveat to render for a board's lens, or ``None``.

    * a software-lens board — ``software-architecture`` or the absent/``None`` default
      that :func:`is_software_lens` maps to software — carries no disclaimer (existing
      software runs are unchanged);
    * a ``legal-contract`` board gets the lawyer-specific line;
    * every other non-software preset (business-decision, product-strategy,
      research-paper, writing-editing, and any unknown non-software value) gets the
      universal one.

    Renderer-only: this never touches the verdict.json schema or the machine gate."""
    if is_software_lens(lens_preset):
        return None
    if lens_preset == "legal-contract":
        return LEGAL_DISCLAIMER
    return UNIVERSAL_DISCLAIMER

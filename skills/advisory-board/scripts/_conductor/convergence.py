"""The M1 convergence signal (design §15 / v1.x M1) — a PURE function over the
parsed `VERDICT:` token + the citation set of each seat's round artifacts.

Principle #1 ("models reason; the conductor plumbs") forbids the conductor from
inferring a verdict from the free-form prose of a round artifact. So each seat
emits a machine-readable `VERDICT: ship|caution|block` line, and this module only
DIFFS tokens and citation sets — it never reads meaning out of the prose. A seat
that rephrases its prose but keeps the same verdict token and the same concrete
citations reads as *no movement* (the rephrase-invariance property the
`--rounds auto` stop-rule depends on).

Movement between two rounds, per seat:
  * verdict-token shift  — the `VERDICT:` token changed (e.g. block -> caution); and
  * new-citation delta   — the seat brought ≥1 NEW concrete citation into round N.
A seat *moved* if either holds. Board-wide movement is the count of seats (present
and usable in BOTH rounds) that moved. `--rounds auto` keeps going while movement
is at or above the threshold and stops the moment it drops below.
"""
from __future__ import annotations

import re
from typing import Optional

__all__ = [
    "VERDICT_TOKENS",
    "DEFAULT_CONVERGE_THRESHOLD",
    "parse_verdict",
    "citations",
    "seat_movement",
    "board_movement",
    "movement_detail_line",
]


# The verdict vocabulary — identical to board_verdict.py's SEVERITY and the
# verdict@2 schema's per-seat `round_verdicts`, so M1's token feeds the existing
# verdict chain (and M2's synthesizer) without translation.
VERDICT_TOKENS = ("ship", "caution", "block")

# Sane default: keep going while AT LEAST ONE seat is still moving; stop the moment
# the board goes quiet (movement < 1, i.e. zero movers). Overridable in code; the
# hard ceiling is the conductor's `--max-rounds`.
DEFAULT_CONVERGE_THRESHOLD = 1


# A seat's machine-readable verdict line. We scan every line that carries a
# `VERDICT:` label and accept only the ones naming EXACTLY ONE of the three tokens:
#  * the instruction echo ("VERDICT: ship|caution|block", all three) is rejected;
#  * a hedged line ("VERDICT: not ship but block", two tokens) is rejected;
#  * `search` (not `match`) and the optional `[*_]*` tolerate real-world decoration
#    a model adds around the label — a list marker, a leading qualifier, or markdown
#    emphasis ("- VERDICT: block", "Final VERDICT: ship", "**VERDICT:** caution").
# The LAST qualifying line wins. The round templates instruct each seat to put its
# verdict "on the LAST line of your reply ... nothing after it", so the seat's own
# verdict is the final VERDICT line; an earlier QUOTED PEER verdict (from the
# cross-reading packet, named per "where you changed your mind") is correctly
# superseded by the seat's own closing token rather than overriding it.
_VERDICT_LINE = re.compile(r"\bVERDICT\b\s*[*_]*\s*:\s*(.+?)\s*$", re.IGNORECASE)
_WORD = {t: re.compile(rf"\b{t}\b", re.IGNORECASE) for t in VERDICT_TOKENS}
_FIRST_WORD = re.compile(r"[A-Za-z]+")


def _is_quoted_verdict_line(line: str, match: "re.Match") -> bool:
    """True if this VERDICT line is markdown-QUOTED rather than the seat's own flush-left
    token, so it must NOT count as the seat's verdict (R: a trailing blockquoted/indented/
    code-spanned 'VERDICT: ship' echoed from a poisoned repo file could otherwise override
    the seat's real verdict via 'last line wins'). A line is rejected when it is:
      * a markdown blockquote — leading whitespace then '>';
      * indented — a leading TAB or >= 4 leading spaces (a fenced/quoted code block);
      * code-span-wrapped — a backtick appears BEFORE the VERDICT label (e.g. '`VERDICT:
        ship`'). A backtick only on the VALUE side ('VERDICT: `ship`') is NOT rejected —
        that is the seat's own flush-left token with a decorated value.
    Plain list/emphasis decoration ('- VERDICT', '**VERDICT**', 'Final VERDICT') is the
    seat's own token and is intentionally NOT rejected."""
    leading = line[:len(line) - len(line.lstrip())]
    if "\t" in leading or len(leading) >= 4:
        return True
    stripped = line.lstrip()
    if stripped.startswith(">"):
        return True
    # A backtick anywhere before the matched VERDICT label means the label sits inside a
    # code span (`VERDICT: ship`); a backtick after the label is just a decorated value.
    if "`" in line[:match.start()]:
        return True
    return False


def parse_verdict(text: Optional[str]) -> Optional[str]:
    """The seat's overall verdict token (ship|caution|block), or None if it emitted no
    clean VERDICT line. The token must be the FIRST alphabetic word of the value (the
    bare-token contract `VERDICT: <token>`), so a prose label like `Verdict: REJECT / DO
    NOT SHIP` is NOT read as `ship`, while leading decoration that isn't a word — markdown
    (`**ship**`), a bullet (`- caution`), an arrow/emoji — is skipped. A line naming zero
    or more than one token (the echoed instruction, hedged prose) is ignored. The last
    clean line wins, matching the templates' 'verdict on the last line' contract."""
    found = None
    for line in (text or "").splitlines():
        m = _VERDICT_LINE.search(line)
        if not m:
            continue
        if _is_quoted_verdict_line(line, m):
            continue   # a blockquoted/indented/code-spanned VERDICT is not the seat's own
        rest = m.group(1)
        hits = [t for t in VERDICT_TOKENS if _WORD[t].search(rest)]
        if len(hits) != 1:
            continue   # zero tokens, or the 3-token echo / a hedge naming two
        first = _FIRST_WORD.search(rest)
        if first and first.group(0).lower() == hits[0]:   # the token leads the value
            found = hits[0]
    return found


# Concrete, rephrase-stable citation forms: an identifier/path-shaped inline-code
# span (`parse()`, `auth.py:42`, `some_symbol`) or a file-shaped slash path
# (src/auth.py:42, config/x.yaml). We deliberately do NOT count free quoted prose —
# it flickers on rewording and would keep `auto` from ever converging. So BOTH
# branches are shape-guarded: a code span counts only when it has no internal
# whitespace and carries a code-ish character (so a backticked PROSE phrase like
# `the retry path doubles charges` is not a citation), and a slash path counts only
# when it looks like a file (a dotted extension or a :line suffix), so a plain word
# like "and/or" is not a citation. Trailing sentence punctuation is stripped from a
# bare path so `lib/x.py.` (sentence end) and `lib/x.py` are the SAME citation.
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_SLASH_PATH = re.compile(r"(?<![\w./-])([\w.-]+(?:/[\w.-]+)+(?::\d+)?)")
_FILE_SHAPED = re.compile(r"\.[A-Za-z]|:\d")   # a LETTER-led extension (.py) or a :line suffix,
#                                                not a decimal ratio like p50/p99.9 or 3/4.5
_CODE_CHAR = re.compile(r"[./:_()\[\]=#-]")   # a code-ish punctuation (not plain prose)
_WS = re.compile(r"\s+")
_TRAILING_PUNCT = ".,;:!?"


def _normalize(token: str) -> str:
    return _WS.sub(" ", token.strip()).lower()


def citations(text: Optional[str]) -> frozenset:
    """The set of concrete citations in a review — identifier/path-shaped inline-code
    spans plus file-shaped slash paths, normalized. Deterministic and rephrase-stable:
    identical text yields an identical set, and reworded prose around the same refs
    does not change it."""
    body = text or ""
    out = set()
    for raw in _CODE_SPAN.findall(body):
        norm = _normalize(raw)
        if len(norm) >= 2 and " " not in norm and _CODE_CHAR.search(norm):
            out.add(norm)   # a backticked prose phrase (has spaces / no code char) is skipped
    for raw in _SLASH_PATH.findall(body):
        if not _FILE_SHAPED.search(raw):
            continue   # a slash word like "and/or" is not a file citation
        norm = _normalize(raw).rstrip(_TRAILING_PUNCT)
        if len(norm) >= 2:
            out.add(norm)
    return frozenset(out)


def seat_movement(prev_text: Optional[str], curr_text: Optional[str]) -> dict:
    """Per-seat movement between two consecutive rounds (pure over the parsed token
    + citation set). `moved` is True iff the verdict token shifted OR the seat
    introduced at least one new citation."""
    prev_v, curr_v = parse_verdict(prev_text), parse_verdict(curr_text)
    verdict_shift = prev_v != curr_v
    new_cites = citations(curr_text) - citations(prev_text)
    return {
        "verdict_from": prev_v,
        "verdict_to": curr_v,
        "verdict_shift": verdict_shift,
        "new_citations": len(new_cites),
        "moved": bool(verdict_shift or new_cites),
    }


def board_movement(prev_results: list, curr_results: list) -> dict:
    """Board-wide movement across one round transition. Only seats USABLE in BOTH
    rounds count (a dropped seat cannot 'move'); `considered` is that overlap.
    Returns the per-seat detail plus the mover count and the round numbers."""
    prev_by = {r.seat: r for r in prev_results if r.usable}
    seats: dict = {}
    moved = 0
    for r in curr_results:
        if not r.usable or r.seat not in prev_by:
            continue
        detail = seat_movement(prev_by[r.seat].stdout, r.stdout)
        seats[r.seat] = detail
        if detail["moved"]:
            moved += 1
    from_round = prev_results[0].round_no if prev_results else None
    to_round = curr_results[0].round_no if curr_results else None
    return {
        "from_round": from_round,
        "to_round": to_round,
        "moved": moved,
        "considered": len(seats),
        "seats": seats,
    }


def movement_detail_line(movement: dict) -> str:
    """A one-line human summary of a transition's per-seat movement, for provenance.
    e.g. 'claude block→caution; codex +1 cite; gemini —'."""
    parts = []
    for seat, d in movement["seats"].items():
        if d["verdict_shift"]:
            frm = d["verdict_from"] or "none"
            to = d["verdict_to"] or "none"
            parts.append(f"{seat} {frm}→{to}")
        elif d["new_citations"]:
            parts.append(f"{seat} +{d['new_citations']} cite{'s' if d['new_citations'] != 1 else ''}")
        else:
            parts.append(f"{seat} —")
    return "; ".join(parts) if parts else "(no overlapping seats)"

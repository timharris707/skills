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
  * verdict-token shift  — the `VERDICT:` token changed (e.g. block -> caution);
  * new-citation delta   — the seat brought ≥1 NEW concrete citation into round N; and
  * score change (v1.15) — on a --rubric run, any per-criterion `SCORE cN` the seat
    reported changed between the two rounds (integer 1–5, so any change is ≥1 and the
    epsilon question is moot). A criterion the seat scored in NEITHER round is
    non-movement; a criterion scored in exactly one round IS a change (D19).
A seat *moved* if any of these hold. Board-wide movement is the count of seats
(present and usable in BOTH rounds) that moved. `--rounds auto` keeps going while
movement is at or above the threshold and stops the moment it drops below.
"""
from __future__ import annotations

import re
from typing import Optional

__all__ = [
    "VERDICT_TOKENS",
    "BASIS_TOKENS",
    "SCORE_MIN",
    "SCORE_MAX",
    "DEFAULT_CONVERGE_THRESHOLD",
    "parse_verdict",
    "parse_basis",
    "parse_scores",
    "parse_rubric_note",
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


# The independence/basis vocabulary (v1.14 #9 — echo score). ROUND-2+ seats emit a
# machine-readable `BASIS:` line stating what their revised position rests on. It is a
# self-reported signal for the echo-score metric, NOT a verdict signal: it never gates
# and never overrides the one VERDICT token. Parsed with the SAME failure-tolerant
# discipline as parse_verdict — a line naming zero or >1 of the tokens is ignored, and
# a seat that omits the line yields None ("unknown"), never a guess.
BASIS_TOKENS = ("independent", "evidence", "deference")

_BASIS_LINE = re.compile(r"\bBASIS\b\s*[*_]*\s*:\s*(.+?)\s*$", re.IGNORECASE)
_BASIS_WORD = {t: re.compile(rf"\b{t}\b", re.IGNORECASE) for t in BASIS_TOKENS}


def parse_basis(text: Optional[str]) -> Optional[str]:
    """The seat's self-reported round-2+ basis token (independent|evidence|deference),
    or None if it emitted no clean BASIS line (v1.14 #9). Mirrors parse_verdict exactly:
    the token must be the FIRST alphabetic word of the value (so a prose line like
    `Basis: mostly my own evidence` is NOT read as `evidence`), a line naming zero or
    more than one token is ignored, a markdown-QUOTED/indented/code-spanned line is
    skipped (a peer's echoed BASIS cannot override the seat's own), and the last clean
    line wins. None means 'unknown' — the metric never guesses a basis a seat did not
    state. This token is self-reported: it flags the seat's OWN account of its
    independence, it does not verify it."""
    found = None
    for line in (text or "").splitlines():
        m = _BASIS_LINE.search(line)
        if not m:
            continue
        if _is_quoted_verdict_line(line, m):
            continue   # a blockquoted/indented/code-spanned BASIS is not the seat's own
        rest = m.group(1)
        hits = [t for t in BASIS_TOKENS if _BASIS_WORD[t].search(rest)]
        if len(hits) != 1:
            continue   # zero tokens, or a hedge naming two/all three
        first = _FIRST_WORD.search(rest)
        if first and first.group(0).lower() == hits[0]:   # the token leads the value
            found = hits[0]
    return found


# Per-criterion scores (v1.15 #P3 — D17). On a --rubric run each seat emits, above its
# BASIS/VERDICT tokens, one `SCORE cN: <1–5>` line per merged criterion (ids c1…cN,
# conductor-assigned at chair-merge time). Scores COEXIST with the VERDICT token and
# never gate (D17): seat usability stays defined by VERDICT, so a missing/invalid SCORE
# degrades to an ABSENT scorecard cell (rendered "—", never imputed), never an unusable
# seat. The scale is 1–5 INTEGERS (coarse, defensible — not 0–10/0–100 false precision).
SCORE_MIN = 1
SCORE_MAX = 5

# A seat's per-criterion score line, parsed with parse_verdict's discipline:
#  * `search` + optional `[*_]*` tolerate a list marker / leading qualifier / markdown
#    emphasis around the label ("- SCORE c3: 4", "**SCORE c3:** 4", "Final SCORE c3: 4");
#  * the criterion id (c<digits>) is captured case-insensitively, then lowercased;
#  * the VALUE must be a bare ASCII integer in [1,5], the ONLY number on the line — a
#    hedged range ("SCORE c3: 4 or 5", "4-5", "4/5"), a prose value ("SCORE c3: high"), or
#    a decimal ("3.5") is rejected, like a hedged VERDICT naming two tokens; a Unicode
#    digit ("٣", "３") and a signed value ("-3") are rejected too (ASCII [0-9], no leading
#    sign), and an out-of-range integer (0, 6, 12) is rejected. Markdown/emphasis/
#    punctuation decoration around the single integer ("**4**", "`4`", "4.", "→4") is
#    tolerated;
#  * a markdown-QUOTED/indented/code-spanned line is skipped (a peer's echoed SCORE from
#    the cross-reading packet cannot override the seat's own — _is_quoted_verdict_line);
#  * the LAST qualifying line PER ID wins (the templates put the seat's own scores at the
#    tail, above BASIS/VERDICT, so an earlier quoted peer score is superseded).
_SCORE_LINE = re.compile(r"\bSCORE\b\s*[*_]*\s*(c[0-9]+)\s*[*_]*\s*:\s*(.+?)\s*$", re.IGNORECASE)
# The value is ONE ASCII integer with only markdown/emphasis/punctuation decoration around
# it. The digit class is ASCII [0-9] ONLY — NOT `\d`, which also matches Unicode decimal
# digits (Arabic-Indic "٣", fullwidth "３"), so those are rejected rather than silently
# parsed as 3. The leading decoration class carries markdown emphasis / list-marker /
# blockquote / arrow (`→`) / bullet glyphs but deliberately EXCLUDES `-`: a leading `-`
# is a sign, so "SCORE c1: -3" must NOT parse as 3 (it falls out of the 1–5 band anyway,
# but the value must not swallow the minus). A leading `[*_`(\[>` and bullet/arrow, and a
# trailing `.,;:!?)*_\`` ], are allowed; a SECOND ASCII digit anywhere in the value (a
# range "4 or 5"/"4-5"/"4/5", a decimal "3.5") means the value is NOT a lone integer and
# the line is rejected (the hedge arm, mirroring parse_verdict's two-token rejection).
_SCORE_VALUE = re.compile(r"^[\s*_`(\[>→•·]*([0-9]+)[\s.,;:!?)*_`\]]*$")


def parse_scores(text: Optional[str],
                 criterion_ids: Optional["frozenset|set|list|tuple"] = None) -> dict:
    """The seat's per-criterion integer scores, `{criterion_id: score}` for every
    criterion it scored CLEANLY (an integer in [SCORE_MIN, SCORE_MAX] as the first token
    of the value). A criterion with no clean line is simply ABSENT from the dict — never
    imputed, never 0 (the scorecard renders it "—"). The last clean line per id wins.

    `criterion_ids`, when given, RESTRICTS parsing to the merged rubric's ids: a score
    for an id outside the rubric (a stray `SCORE c9` a seat invented) is ignored, so a
    seat can never conjure a criterion the chair did not merge. When None (tests), every
    `c<digits>` id the reply names is accepted. Pure; shares parse_verdict's line-level
    hardening — quoted/indented/code-spanned lines skipped, last clean line per id wins,
    §11 one-machine-token-per-line (never the prose). It DIFFERS in the value shape it
    accepts: parse_verdict reads an alphabetic token from a fixed vocabulary, this reads a
    LONE ASCII integer in [SCORE_MIN, SCORE_MAX]; a hedged range/decimal, a Unicode digit,
    a signed value, or an out-of-band integer is rejected (the hedge/out-of-range arm)."""
    allowed = None
    if criterion_ids is not None:
        # isinstance-guard before the membership check: a non-iterable would raise, and a
        # stray str would iterate CHARACTERS. Only a real collection restricts; anything
        # else falls back to "accept any c<digits> id" rather than crashing the round.
        if isinstance(criterion_ids, (set, frozenset, list, tuple)):
            allowed = {str(c).lower() for c in criterion_ids}
    found: dict = {}
    for line in (text or "").splitlines():
        m = _SCORE_LINE.search(line)
        if not m:
            continue
        if _is_quoted_verdict_line(line, m):
            continue   # a blockquoted/indented/code-spanned SCORE is not the seat's own
        cid = m.group(1).lower()
        if allowed is not None and cid not in allowed:
            continue   # not a merged-rubric criterion — a seat cannot invent one
        vm = _SCORE_VALUE.match(m.group(2))
        if not vm:
            continue   # value is not a LONE integer (hedged range / prose / decimal)
        value = int(vm.group(1))
        if not (SCORE_MIN <= value <= SCORE_MAX):
            continue   # out of the 1–5 band — rejected (a parse failure for this cell)
        found[cid] = value
    return found


# A seat's optional objection to the RUBRIC ITSELF (D17). One free-text `RUBRIC-NOTE:`
# line recording that the seat scored under the merged rubric but disagrees with it — a
# non-blocking dissent captured WITHOUT another fan-out (the scoring reply IS acceptance,
# D16). It carries no machine token and never gates; the scorecard records it verbatim.
_RUBRIC_NOTE_LINE = re.compile(r"\bRUBRIC-NOTE\b\s*[*_]*\s*:\s*(.+?)\s*$", re.IGNORECASE)


def parse_rubric_note(text: Optional[str]) -> Optional[str]:
    """The seat's `RUBRIC-NOTE:` objection line (its verbatim text), or None if it
    emitted none. The LAST such line wins (mirroring the one-token-per-line contract);
    a markdown-quoted/indented/code-spanned line is skipped so an echoed peer note cannot
    stand in for the seat's own. Pure; free text (not a machine token) — recorded, never
    parsed for meaning (§11)."""
    found = None
    for line in (text or "").splitlines():
        m = _RUBRIC_NOTE_LINE.search(line)
        if not m:
            continue
        if _is_quoted_verdict_line(line, m):
            continue
        note = m.group(1).strip()
        if note:
            found = note
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


def _score_changes(prev_text: Optional[str], curr_text: Optional[str],
                   criterion_ids) -> list:
    """The sorted list of criterion ids whose parsed score CHANGED between two rounds
    (D19). A criterion scored in NEITHER round is non-movement (absent from both dicts →
    not a change); a criterion scored in EXACTLY ONE round IS a change (the seat gained
    or dropped a cell); a criterion scored in both with a different integer IS a change.
    Pure over parse_scores — never over the prose."""
    prev_s = parse_scores(prev_text, criterion_ids)
    curr_s = parse_scores(curr_text, criterion_ids)
    changed = [cid for cid in (set(prev_s) | set(curr_s))
               if prev_s.get(cid) != curr_s.get(cid)]
    return sorted(changed)


def seat_movement(prev_text: Optional[str], curr_text: Optional[str],
                  *, criterion_ids=None) -> dict:
    """Per-seat movement between two consecutive rounds (pure over the parsed token +
    citation set + per-criterion scores). `moved` is True iff the verdict token shifted
    OR the seat introduced ≥1 new citation OR (on a --rubric run) any criterion score
    changed. `criterion_ids` (the merged rubric's c1…cN) enables the score arm — None on
    a non-rubric run, where the score arm is inert and the boolean is exactly as before
    (byte-for-byte the historical two-arm movement)."""
    prev_v, curr_v = parse_verdict(prev_text), parse_verdict(curr_text)
    verdict_shift = prev_v != curr_v
    new_cites = citations(curr_text) - citations(prev_text)
    score_changed = (_score_changes(prev_text, curr_text, criterion_ids)
                     if criterion_ids else [])
    return {
        "verdict_from": prev_v,
        "verdict_to": curr_v,
        "verdict_shift": verdict_shift,
        "new_citations": len(new_cites),
        "score_changes": score_changed,           # sorted criterion ids that moved
        "moved": bool(verdict_shift or new_cites or score_changed),
    }


def board_movement(prev_results: list, curr_results: list, *, criterion_ids=None) -> dict:
    """Board-wide movement across one round transition. Only seats USABLE in BOTH
    rounds count (a dropped seat cannot 'move'); `considered` is that overlap.
    Returns the per-seat detail plus the mover count and the round numbers.
    `criterion_ids` (the merged rubric's c1…cN) widens each seat's movement with the
    score arm (D19); None (non-rubric) leaves the two-arm behavior unchanged."""
    prev_by = {r.seat: r for r in prev_results if r.usable}
    seats: dict = {}
    moved = 0
    for r in curr_results:
        if not r.usable or r.seat not in prev_by:
            continue
        detail = seat_movement(prev_by[r.seat].stdout, r.stdout, criterion_ids=criterion_ids)
        seats[r.seat] = detail
        if detail["moved"]:
            moved += 1
    from_round = prev_results[0].round_no if prev_results else None
    to_round = curr_results[0].round_no if curr_results else None
    # The union of still-moving criterion ids across all considered seats (D19 — the
    # round-done detail names which criteria are still moving). Sorted; empty on a
    # non-rubric run (no seat carries score_changes there).
    moving_criteria = sorted({cid for d in seats.values()
                              for cid in d.get("score_changes", [])})
    return {
        "from_round": from_round,
        "to_round": to_round,
        "moved": moved,
        "considered": len(seats),
        "seats": seats,
        "moving_criteria": moving_criteria,
    }


def movement_detail_line(movement: dict) -> str:
    """A one-line human summary of a transition's per-seat movement, for provenance.
    e.g. 'claude block→caution; codex +1 cite; gemini c2,c4↕; delta —'. On a --rubric
    run a seat whose scores moved names the still-moving criterion ids (D19); the
    verdict/citation arms take precedence in the label when several arms fire (the
    verdict shift is the loudest signal)."""
    parts = []
    for seat, d in movement["seats"].items():
        score_moved = d.get("score_changes") or []
        if d["verdict_shift"]:
            frm = d["verdict_from"] or "none"
            to = d["verdict_to"] or "none"
            parts.append(f"{seat} {frm}→{to}")
        elif d["new_citations"]:
            parts.append(f"{seat} +{d['new_citations']} cite{'s' if d['new_citations'] != 1 else ''}")
        elif score_moved:
            parts.append(f"{seat} {','.join(score_moved)}↕")
        else:
            parts.append(f"{seat} —")
    return "; ".join(parts) if parts else "(no overlapping seats)"

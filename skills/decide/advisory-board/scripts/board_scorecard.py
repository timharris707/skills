#!/usr/bin/env python3
"""Validate an advisory-board scorecard.json — the post-rounds artifact of record (v1.15).

`scorecard.json` is the per-round SCORING trajectory of a `--rubric` run: every seat
scored every merged criterion `1–5` each opinion round, and this file records those
rows (the trajectory IS the convergence story), the seats' `RUBRIC-NOTE:` objections,
and the conductor's per-seat weighted totals + coarse bands. It is written AFTER the
opinion rounds (the rubric.json it scores against is written BEFORE them — the D18
two-artifact split). The verdict points at it (`verdict.json.scorecard = {artifact,
sha256}`, a P4 pointer, only present when synthesis runs); this file is the source of
truth for the scores.

Examples:
  board_scorecard.py scorecard.json          validate + print a summary
  board_scorecard.py scorecard.json --json     echo normalized JSON

Exit codes:
  0  ok
  2  usage or schema error

Schema: `advisory-board/scorecard@1`. EVERYTHING here is conductor-computed — the
scores are PARSED from the round replies (never a model-authored JSON field), the ids
mirror rubric.json's `c1`…`cN`, the weighted totals + bands are arithmetic over the
final round. The only content that traces to a model is the verbatim `RUBRIC-NOTE:`
prose in `rubric_notes[]`. This validator is strict — unknown top-level keys are
refused, field types are exact, and the two conductor invariants are RE-CHECKED here as
the last gate before any consumer (the renders) trusts the file:

  * SCORES-IN-RANGE (D17): every recorded `score` is an integer in [SCORE_MIN,
    SCORE_MAX] (1–5); a missing cell is ABSENT from `scores[]`, never a 0 or null (the
    render draws "—"). Every `criterion` names a criterion id present in `criteria[]`.
  * BANDS (D17): each per-seat `band` is one of the coarse thirds (`weak`/`mixed`/
    `strong`), reader-defensible over the 1–5 scale — never a false-precision number.
    The gate NEVER reads a band (the `confidence`/echo-score precedent: a gameable
    number must not move a gate); a token↔band contradiction is recorded loudly here
    and surfaced in the render, but it does NOT gate (Gemini's ABSTAIN-on-contradiction
    dissent is deferred, D17).

DERIVABLE-INVARIANT hardening (v1.15 P4 fix pass — the claude seat's scope, deliberately
NARROWER than a full recompute). Fields that are FULLY determined by other in-document
fields are re-derived and must match, so a hand-edited/fuzzed artifact that skews one
field alone is refused. This is NOT a recompute of `weighted_total` from
`criteria[]`/`scores[]` (codex's scope): two copies of the conductor's arithmetic would
invite drift, and verdict.json's `scorecard.sha256` already guards the in-run case.

  * band == band_for(weighted_total) — the band is fully derivable; band_for lives HERE
    (this validator is the SINGLE SOURCE OF TRUTH for the fixed-thirds boundaries, and
    _conductor.scorecard delegates to it), so the written band and the re-derived band
    can never drift.
  * partial == (criteria_scored < len(criteria)); criteria_scored <= len(criteria); and
    the null coherence: null weighted_total ⇔ null band ⇔ criteria_scored == 0.
  * contradictions[] ⇔ totals[]: each `totals[]` row carries the seat's final verdict
    token (`final_verdict` + `final_verdict_round`, REQUIRED on scorecard@1). The set of
    seats whose `(final_verdict, band)` trips the fixed token↔band rule (block/strong,
    ship/weak) must EXACTLY equal the set of seats in `contradictions[]`, and each
    recorded row's verdict/band must match its totals row. So contradictions[] is
    validatable STANDALONE — a missing or extra row is refused — WITHOUT any arithmetic
    recompute (derivable consistency, in claude's spirit). The pair is REQUIRED (not
    additive-optional): scorecard@1 is unreleased, so no legitimate artifact lacks it, and
    an optional field would only ever let a TAMPERED artifact strip the pair to dodge this
    cross-check (strip-to-evade) — so the check ALWAYS runs, with no skip branch.

The conductor runs `validate()` before writing `scorecard.json`; anything invalid takes
the refusal path (a warning + no scorecard.json — the rounds and verdict still stand,
because a scorecard hiccup must never discard the successful board, D14). Standard
library only.

isinstance guards precede every membership (`in`) check, deliberately: an unhashable
hand-authored value (a list/dict where a scalar belongs) would otherwise TypeError on
the `in` and escape die()'s clean schema exit 2 (the `board_verdict.py`
TypeError-on-unhashable idiom the roadmap's "Later" flags — NOT repeated here).
"""
from __future__ import annotations

import argparse
import json
import re
import sys

SCHEMA = "advisory-board/scorecard@1"

# The score scale (mirrors convergence.SCORE_MIN/SCORE_MAX — the same 1–5 integers the
# round parser accepts). Stated here so this validator stands alone (no _conductor
# import — board_scorecard.py is a standalone CLI like board_verdict/board_changes).
SCORE_MIN = 1
SCORE_MAX = 5

# The coarse bands (D17 — thirds of the 1–5 scale). Reader-defensible over the scale,
# NOT a tuned formula (the echo-score philosophy). `partial` marks a seat that did not
# score every criterion. A gate NEVER reads a band.
BANDS = ("weak", "mixed", "strong")

# Band thresholds = thirds of the 1–5 scale (span 4, so cut at 1+4/3 ≈ 2.333 and
# 1+8/3 ≈ 3.667). Reader-defensible: "bottom / middle / top third of the scale". A
# weighted mean in [1, 2.333) is `weak`, [2.333, 3.667) is `mixed`, [3.667, 5] is
# `strong`. THIS validator is the SINGLE SOURCE OF TRUTH for the boundaries: the
# builder (_conductor.scorecard) imports band_for from here, so the number the
# conductor writes and the number this validator re-derives can never drift (D17 fix
# pass — one place, not two copies of the arithmetic). Standalone-ness is preserved
# because the boundaries live in the standalone validator itself (no _conductor import).
_BAND_WEAK_MAX = SCORE_MIN + (SCORE_MAX - SCORE_MIN) / 3.0        # ≈ 2.3333
_BAND_MIXED_MAX = SCORE_MIN + 2 * (SCORE_MAX - SCORE_MIN) / 3.0   # ≈ 3.6667


def band_for(weighted_total):
    """The coarse band for a weighted mean on the 1–5 scale, or None when there is
    nothing to band (a seat that scored no criterion in its final round). Fixed thirds
    (D17): each cut point falls in the UPPER band because the test is `< max` — a value
    EXACTLY at `_BAND_MIXED_MAX` (≈ 3.6667) is not `< _BAND_MIXED_MAX`, so it lands in
    `strong`. So `weak` is [1, 2.3333), `mixed` is [2.3333, 3.6667), `strong` is
    [3.6667, 5]. This is the ONE definition; _conductor.scorecard delegates here."""
    if weighted_total is None:
        return None
    if weighted_total < _BAND_WEAK_MAX:
        return "weak"
    if weighted_total < _BAND_MIXED_MAX:
        return "mixed"
    return "strong"

# Strict key sets. Unknown keys are refused so a fabricated/fuzzed artifact can't
# smuggle fields past the validator (mirrors board_changes/board_rubric discipline —
# scorecard.json is conductor-born, so the whole document is strict).
TOP_LEVEL_KEYS = {
    "schema", "title", "chair_seat", "rubric_artifact",
    "criteria", "scores", "rubric_notes", "totals", "contradictions",
}
TOP_LEVEL_REQUIRED = (
    "schema", "title", "chair_seat", "rubric_artifact",
    "criteria", "scores", "rubric_notes", "totals", "contradictions",
)
CRITERION_KEYS = {"id", "title", "weight"}
SCORE_KEYS = {"seat", "round", "criterion", "score"}
NOTE_KEYS = {"seat", "round", "note"}
TOTAL_KEYS = {"seat", "weighted_total", "band", "partial", "criteria_scored",
              "final_verdict", "final_verdict_round"}
CONTRADICTION_KEYS = {"seat", "verdict", "band", "token_round", "score_round"}

# The verdict tokens a contradiction row may carry (mirrors board_verdict.SEVERITY).
VERDICT_TOKENS = ("ship", "caution", "block")

WEIGHT_SUM = 100

_CRITERION_ID = re.compile(r"^c[1-9][0-9]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

EXIT_OK = 0
EXIT_SCHEMA = 2


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(EXIT_SCHEMA)


def _is_severe_contradiction(token, band) -> bool:
    """The fixed token↔band contradiction rule (D17), mirrored from
    _conductor.scorecard._is_contradiction so contradictions[] can be re-derived from
    totals[] here: a `block` verdict over `strong` scores, or a `ship` verdict over
    `weak` scores. `caution`/`mixed` never contradict (they ARE the hedge); a null token
    or band never contradicts. Fixed and coarse — never a tuned threshold."""
    return ((token == "block" and band == "strong")
            or (token == "ship" and band == "weak"))


def _is_int(value) -> bool:
    """A real integer, not a bool (bool is an int subclass in Python)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _nonempty_str(value, where: str) -> None:
    if not isinstance(value, str) or not value.strip():
        die(f"{where} must be a non-empty string")


def _validate_criterion(crit, index: int) -> None:
    where = f"criteria[{index}]"
    if not isinstance(crit, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("id", "title", "weight") if k not in crit]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(crit) - CRITERION_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    # id: c1…cN (isinstance guard before the regex).
    if not isinstance(crit["id"], str) or not _CRITERION_ID.match(crit["id"]):
        die(f"{where}.id must match c<positive-int> (c1, c2, …); got {crit['id']!r}")
    _nonempty_str(crit["title"], f"{where}.title")
    if not _is_int(crit["weight"]) or crit["weight"] < 1:
        die(f"{where}.weight must be a positive integer percentage (>= 1); got {crit['weight']!r}")


def _validate_score_row(entry, index: int, valid_cids: set) -> None:
    where = f"scores[{index}]"
    if not isinstance(entry, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("seat", "round", "criterion", "score") if k not in entry]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(entry) - SCORE_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    _nonempty_str(entry["seat"], f"{where}.seat")
    if not _is_int(entry["round"]) or entry["round"] < 1:
        die(f"{where}.round must be a positive integer; got {entry['round']!r}")
    # criterion: an id present in criteria[] (isinstance guard before the membership
    # check — an unhashable value would TypeError on `in` and escape die()).
    cid = entry["criterion"]
    if not isinstance(cid, str) or cid not in valid_cids:
        die(f"{where}.criterion must name a criterion id in criteria[]; got {cid!r}")
    # score: an integer in [SCORE_MIN, SCORE_MAX]. A missing cell is ABSENT from
    # scores[] — never a 0/null row (D17: never imputed).
    if not _is_int(entry["score"]) or not (SCORE_MIN <= entry["score"] <= SCORE_MAX):
        die(f"{where}.score must be an integer in [{SCORE_MIN}, {SCORE_MAX}]; "
            f"got {entry['score']!r}")


def _validate_note(entry, index: int) -> None:
    where = f"rubric_notes[{index}]"
    if not isinstance(entry, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("seat", "round", "note") if k not in entry]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(entry) - NOTE_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    _nonempty_str(entry["seat"], f"{where}.seat")
    if not _is_int(entry["round"]) or entry["round"] < 1:
        die(f"{where}.round must be a positive integer; got {entry['round']!r}")
    _nonempty_str(entry["note"], f"{where}.note")


def _validate_total(entry, index: int, n_criteria: int) -> None:
    where = f"totals[{index}]"
    if not isinstance(entry, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("seat", "weighted_total", "band", "partial", "criteria_scored",
                           "final_verdict", "final_verdict_round")
               if k not in entry]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(entry) - TOTAL_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    _nonempty_str(entry["seat"], f"{where}.seat")
    # weighted_total: a finite number in [SCORE_MIN, SCORE_MAX], OR null for a seat that
    # scored NOTHING in the final round (a fully-partial cell — no total to compute).
    wt = entry["weighted_total"]
    if wt is not None:
        if isinstance(wt, bool) or not isinstance(wt, (int, float)):
            die(f"{where}.weighted_total must be a number or null; got {wt!r}")
        if wt != wt or wt in (float("inf"), float("-inf")):
            die(f"{where}.weighted_total must be a finite number; got {wt!r}")
        if not (SCORE_MIN <= wt <= SCORE_MAX):
            die(f"{where}.weighted_total must be in [{SCORE_MIN}, {SCORE_MAX}]; got {wt!r}")
    # band: one of the coarse thirds, OR null when weighted_total is null (nothing to
    # band). A band with no total, or a total with no band, is a conductor bug — refuse.
    band = entry["band"]
    if band is not None and (not isinstance(band, str) or band not in BANDS):
        die(f"{where}.band must be one of {', '.join(BANDS)} or null; got {band!r}")
    if (wt is None) != (band is None):
        die(f"{where}: weighted_total and band must both be null or both be set "
            f"(got weighted_total={wt!r}, band={band!r})")
    if not isinstance(entry["partial"], bool):
        die(f"{where}.partial must be a boolean; got {entry['partial']!r}")
    if not _is_int(entry["criteria_scored"]) or entry["criteria_scored"] < 0:
        die(f"{where}.criteria_scored must be a non-negative integer; "
            f"got {entry['criteria_scored']!r}")
    # final_verdict / final_verdict_round (D17 fix pass): the seat's final declared
    # verdict token + its round, carried so contradictions[] is validatable standalone
    # (the token↔band contradiction rule is re-derivable from totals[] alone). REQUIRED on
    # every scorecard@1 totals row (checked in the missing-keys list above) — scorecard@1 is
    # unreleased, so there is no legacy artifact lacking the pair; making it optional would
    # only ever benefit a TAMPERED artifact that strips the pair to dodge the
    # contradictions⇔totals cross-check below (strip-to-evade). Typed strictly: final_verdict
    # is a known token or null; the round is a positive integer, and is null EXACTLY when the
    # token is null (a seat that never declared a verdict has neither). A null token means
    # "no standing verdict".
    fv = entry["final_verdict"]
    if fv is not None and (not isinstance(fv, str) or fv not in VERDICT_TOKENS):
        die(f"{where}.final_verdict must be one of {', '.join(VERDICT_TOKENS)} or "
            f"null; got {fv!r}")
    fvr = entry["final_verdict_round"]
    if fvr is not None and (not _is_int(fvr) or fvr < 1):
        die(f"{where}.final_verdict_round must be a positive integer or null; "
            f"got {fvr!r}")
    if (fv is None) != (fvr is None):
        die(f"{where}: final_verdict and final_verdict_round must both be null or "
            f"both set (got final_verdict={fv!r}, final_verdict_round={fvr!r})")

    # --- DERIVABLE-INVARIANT checks (D17 fix pass, the claude seat's scope) --------- #
    # These re-derive fields that are FULLY determined by other in-document fields, so a
    # hand-edited/fuzzed scorecard that skews one field without the others is refused.
    # Deliberately NOT a full recompute of weighted_total from criteria[]/scores[]
    # (codex's scope): two copies of the conductor's arithmetic invite drift, and
    # verdict.json's scorecard.sha256 already guards the in-run case. band is the one
    # arithmetic-derivable field checked here — its input (weighted_total) is already in
    # the row, so band_for(weighted_total) is a re-derivation of the SAME single source
    # of truth (board_scorecard.band_for), not a second arithmetic path.
    if band != band_for(wt):
        die(f"{where}: band {band!r} is not band_for(weighted_total={wt!r}) "
            f"(expected {band_for(wt)!r}) — the band is fully derivable and must match")
    # partial ⇔ the seat did not score every criterion. criteria_scored can never exceed
    # the criteria count. And the null-total case is coherent: no total ⇔ no band ⇔
    # criteria_scored == 0 (a seat scored nothing).
    cs = entry["criteria_scored"]
    if cs > n_criteria:
        die(f"{where}.criteria_scored={cs} exceeds the {n_criteria} criteria "
            f"(a seat cannot score more criteria than exist)")
    if bool(entry["partial"]) != (cs < n_criteria):
        die(f"{where}.partial={entry['partial']!r} is inconsistent with "
            f"criteria_scored={cs} of {n_criteria} (partial ⇔ criteria_scored < "
            f"len(criteria))")
    if (wt is None) != (cs == 0):
        die(f"{where}: a null weighted_total ⇔ criteria_scored == 0 "
            f"(got weighted_total={wt!r}, criteria_scored={cs})")


def _validate_contradiction(entry, index: int) -> None:
    where = f"contradictions[{index}]"
    if not isinstance(entry, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("seat", "verdict", "band", "token_round", "score_round")
               if k not in entry]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(entry) - CONTRADICTION_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    _nonempty_str(entry["seat"], f"{where}.seat")
    # verdict: a valid token (isinstance guard before the membership check).
    v = entry["verdict"]
    if not isinstance(v, str) or v not in VERDICT_TOKENS:
        die(f"{where}.verdict must be one of {', '.join(VERDICT_TOKENS)}; got {v!r}")
    b = entry["band"]
    if not isinstance(b, str) or b not in BANDS:
        die(f"{where}.band must be one of {', '.join(BANDS)}; got {b!r}")
    # token_round / score_round: the two round numbers being compared (NIT 2). Both are
    # positive integers; they name the seat's final round of each kind — the verdict
    # token's round and the scored round — and MAY differ (a seat can score in a later
    # round than the one carrying its last verdict token). A reader uses the pair to see
    # when the compared positions come from different rounds.
    for field in ("token_round", "score_round"):
        rv = entry[field]
        if not _is_int(rv) or rv < 1:
            die(f"{where}.{field} must be a positive integer; got {rv!r}")


def validate(data: dict) -> None:
    """Strict schema check for a scorecard.json document. A malformed artifact of record
    must never quietly pass — the conductor refuses to write on any failure here."""
    if not isinstance(data, dict):
        die("top level must be a JSON object")
    unknown = set(data) - TOP_LEVEL_KEYS
    if unknown:
        die(f"unknown top-level key(s): {', '.join(sorted(unknown))}")
    missing = [k for k in TOP_LEVEL_REQUIRED if k not in data]
    if missing:
        die(f"missing required field(s): {', '.join(missing)}")

    if data["schema"] != SCHEMA:
        die(f"schema must be {SCHEMA!r}; got {data['schema']!r}")
    _nonempty_str(data["title"], "title")
    _nonempty_str(data["chair_seat"], "chair_seat")
    # rubric_artifact: a BARE filename pointing at the sibling rubric.json (the same
    # bare-filename discipline board_verdict enforces on changes.artifact — no path
    # separator, no `..`, not absolute; a render joins it onto the run dir).
    art = data["rubric_artifact"]
    if not isinstance(art, str) or not art.strip():
        die("rubric_artifact must be a non-empty string")
    import os
    if (os.sep in art or (os.altsep and os.altsep in art)
            or os.path.isabs(art) or ".." in art.replace("\\", "/").split("/")):
        die("rubric_artifact must be a bare filename (no path separator, no "
            f"'..', not absolute); got {art!r}")

    criteria = data["criteria"]
    if not isinstance(criteria, list) or not criteria:
        die("criteria must be a non-empty list")
    for index, crit in enumerate(criteria):
        _validate_criterion(crit, index)
    # Criterion ids must be a dense c1…cN sequence in order (mirrors rubric.json).
    cids = [c["id"] for c in criteria if isinstance(c, dict)]
    if cids != [f"c{n}" for n in range(1, len(criteria) + 1)]:
        die(f"criteria[].id must be a dense c1…cN sequence in order; got {cids}")
    # The criteria weights mirror rubric.json's merged criteria — re-check they sum to
    # 100 (the D18 weight-sum invariant travels with the copy; a hand-edited scorecard
    # that changed a weight to skew a weighted total must fail here).
    valid_cids = set(cids)
    weight_sum = sum(c["weight"] for c in criteria)
    if weight_sum != WEIGHT_SUM:
        die(f"the criteria weights sum to {weight_sum}, not {WEIGHT_SUM} — they mirror "
            f"rubric.json's merged criteria and must sum to EXACTLY {WEIGHT_SUM} (D18)")

    scores = data["scores"]
    if not isinstance(scores, list):
        die("scores must be a list")
    for index, entry in enumerate(scores):
        _validate_score_row(entry, index, valid_cids)

    notes = data["rubric_notes"]
    if not isinstance(notes, list):
        die("rubric_notes must be a list")
    for index, entry in enumerate(notes):
        _validate_note(entry, index)

    totals = data["totals"]
    if not isinstance(totals, list):
        die("totals must be a list")
    n_criteria = len(criteria)
    for index, entry in enumerate(totals):
        _validate_total(entry, index, n_criteria)
    # One total row per seat, no duplicates (the render keys the table on it).
    seats = [t["seat"] for t in totals if isinstance(t, dict)]
    if len(seats) != len(set(seats)):
        die("totals[] must carry exactly one row per seat (a duplicate seat is refused)")

    contradictions = data["contradictions"]
    if not isinstance(contradictions, list):
        die("contradictions must be a list")
    for index, entry in enumerate(contradictions):
        _validate_contradiction(entry, index)

    # --- contradictions[] ⇔ totals[] CONSISTENCY (D17 fix pass) --------------------- #
    # With per-seat final tokens now on totals[], contradictions[] is validatable
    # standalone: the set of seats whose (final_verdict, band) trips the fixed token↔band
    # rule (block/strong, ship/weak) must EXACTLY equal the set of seats in
    # contradictions[]. A missing row (a real contradiction the builder failed to record)
    # OR an extra row (a contradictions[] entry with no matching totals row) is refused.
    # This is derivable consistency (claude's spirit) — NOT an arithmetic recompute; it
    # reads only tokens and bands already in the document. final_verdict is REQUIRED on every
    # totals row (see _validate_total), so this check ALWAYS runs — there is no skip branch a
    # tampered artifact can trip by stripping the field (strip-to-evade closed; scorecard@1 is
    # unreleased, so no legitimate artifact lacks the field).
    expected = set()
    for t in totals:
        fv, band = t.get("final_verdict"), t.get("band")
        if _is_severe_contradiction(fv, band):
            expected.add(t["seat"])
    recorded = {c["seat"] for c in contradictions if isinstance(c, dict)}
    missing_rows = expected - recorded
    if missing_rows:
        die("contradictions[] is missing a row for seat(s) whose final_verdict"
            "↔band trips the rule: " + ", ".join(sorted(missing_rows)))
    extra_rows = recorded - expected
    if extra_rows:
        die("contradictions[] has a row for seat(s) whose totals final_verdict↔band "
            "does NOT trip the rule: " + ", ".join(sorted(extra_rows)))
    # Each recorded row's verdict + band must MATCH its totals row (a row that names a
    # real contradicting seat but with the wrong token/band is a tampered artifact).
    totals_by_seat = {t["seat"]: t for t in totals if isinstance(t, dict)}
    for index, c in enumerate(contradictions):
        if not isinstance(c, dict):
            continue
        t = totals_by_seat.get(c.get("seat"))
        if t is None:   # already refused above as an extra row, but be defensive
            continue
        if c.get("verdict") != t.get("final_verdict") or c.get("band") != t.get("band"):
            die(f"contradictions[{index}] (seat {c.get('seat')!r}) verdict/band "
                f"{c.get('verdict')!r}/{c.get('band')!r} does not match its totals "
                f"row {t.get('final_verdict')!r}/{t.get('band')!r}")


def load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        die(f"{path}: not found")
    except json.JSONDecodeError as exc:
        die(f"{path}: invalid JSON ({exc})")
    except OSError as exc:
        die(f"{path}: cannot read ({exc})")
    validate(data)
    return data


def summarize(data: dict) -> str:
    criteria = data.get("criteria") or []
    scores = data.get("scores") or []
    notes = data.get("rubric_notes") or []
    totals = data.get("totals") or []
    contradictions = data.get("contradictions") or []
    lines = [
        f"title          : {data.get('title', '(untitled)')}",
        f"chair seat     : {data.get('chair_seat', '?')}",
        f"criteria       : {len(criteria)}",
        f"score rows     : {len(scores)}",
        f"rubric notes   : {len(notes)}",
        f"contradictions : {len(contradictions)}",
        "",
        "Per-seat weighted totals (final round):",
    ]
    for t in totals:
        if not isinstance(t, dict):
            continue
        wt = t.get("weighted_total")
        wt_s = f"{wt:.2f}" if isinstance(wt, (int, float)) and not isinstance(wt, bool) else "—"
        band = t.get("band") or "—"
        partial = "  (partial)" if t.get("partial") else ""
        lines.append(f"  {t.get('seat')}: {wt_s} / 5  [{band}]{partial}")
    if contradictions:
        lines.append("")
        lines.append("Token↔band contradictions (informational — never gated, D17):")
        for c in contradictions:
            if isinstance(c, dict):
                tr, sr = c.get("token_round"), c.get("score_round")
                rounds = ""
                if isinstance(tr, int) and isinstance(sr, int) and tr != sr:
                    rounds = f" (verdict r{tr}, scores r{sr})"
                lines.append(f"  ⚠ {c.get('seat')}: VERDICT {c.get('verdict')} "
                             f"vs {c.get('band')} scores{rounds}")
    return "\n".join(lines)


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="board_scorecard.py",
        description="Validate an advisory-board scorecard.json (the post-rounds scoring artifact).")
    parser.add_argument("path", nargs="?", default="scorecard.json",
                        help="path to scorecard.json (default: scorecard.json)")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="echo normalized JSON and exit")
    args = parser.parse_args(argv)

    data = load(args.path)
    if args.as_json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return EXIT_OK
    print(summarize(data))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

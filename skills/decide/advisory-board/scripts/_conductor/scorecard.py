"""Build scorecard.json — the post-rounds scoring artifact of record (v1.15 P4, D17/D18).

The rubric (rubric.json) is written BEFORE the opinion rounds; the scorecard is written
AFTER them — the D18 two-artifact split by time. This module assembles the scorecard
purely from the conductor's own state: the merged rubric's criteria (ids/titles/weights)
and the per-round `SeatRoundResult`s (whose `.scores`/`.rubric_note` PARSE the round
replies — never a model-authored JSON field). Everything here is conductor-computed:

  * `scores[]` — one `{seat, round, criterion, score}` row per CLEANLY-scored cell across
    ALL rounds (the trajectory IS the convergence story, D18). A missing cell is simply
    ABSENT — never a 0/null row (D17: never imputed; the render draws "—").
  * `rubric_notes[]` — the seats' verbatim `RUBRIC-NOTE:` objections, per round.
  * `totals[]` — per-seat weighted total + coarse band over the seat's FINAL scored
    round. The total is a WEIGHTED MEAN on the 1–5 scale (Σ score·weight ÷ Σ weight over
    the criteria the seat scored) so a partial cell doesn't drag a seat toward 0; the
    band is a fixed third of the scale (D17 — reader-defensible, never a tuned formula,
    the echo-score philosophy). `partial` marks a seat that did not score every criterion.
  * `contradictions[]` — the loud token↔band self-contradictions (a `block` token over a
    `strong` band, or a `ship` token over a `weak` band). Recorded here and surfaced in
    the render, but NEVER gated (the `confidence`/echo precedent: a gameable number must
    not move a gate; Gemini's ABSTAIN-on-contradiction dissent is deferred, D17).

The assembled dict is validated by board_scorecard.validate before the conductor writes
it; a validation failure warns and writes nothing (the rounds + verdict still stand —
D14, a scorecard hiccup never discards the board). Standard library only.
"""
from __future__ import annotations

from typing import Optional

SCORECARD_SCHEMA = "advisory-board/scorecard@1"

# The score scale, kept in lockstep with board_scorecard (SCORE_MIN/MAX) and
# convergence (SCORE_MIN/MAX). Stated here rather than imported so the scale is a
# single, visible number in this file.
SCORE_MIN = 1
SCORE_MAX = 5

# Band thresholds live in ONE place — board_scorecard (the validator). This builder
# DELEGATES to board_scorecard.band_for so the band the conductor writes and the band
# the validator re-derives (band == band_for(weighted_total), the D17 fix-pass
# invariant) are computed by the SAME function — two copies of the arithmetic would
# invite drift (the claude seat's explicit warning). board_scorecard is a standalone
# CLI already imported lazily by validate_scorecard below; band_for is imported the same
# lazy way so this module's load never depends on scripts/ being on sys.path at import.


def band_for(weighted_total: Optional[float]) -> Optional[str]:
    """The coarse band for a weighted mean on the 1–5 scale — DELEGATES to the single
    source of truth, board_scorecard.band_for (D17 fix pass: one definition of the
    fixed-thirds boundaries, so the written band and the validator's re-derived band can
    never diverge). Fixed thirds: `weak` is [1, 2.3333), `mixed` is [2.3333, 3.6667),
    `strong` is [3.6667, 5]; None when there is nothing to band."""
    import board_scorecard
    return board_scorecard.band_for(weighted_total)


def _weighted_total(scores: dict, weight_of: dict) -> "tuple[Optional[float], int]":
    """(weighted_mean_on_1_5, criteria_scored) for one seat's `{cid: score}` dict. The
    mean is Σ score·weight ÷ Σ weight over ONLY the criteria the seat scored — so a
    partial cell doesn't drag the total toward zero, and the total stays on the 1–5
    scale. Returns (None, 0) when the seat scored nothing (no total to compute)."""
    num = 0.0
    den = 0
    n = 0
    for cid, score in scores.items():
        w = weight_of.get(cid)
        if w is None:
            continue   # a stray id (defensive — .scores already restricts to rubric ids)
        num += score * w
        den += w
        n += 1
    if den == 0:
        return None, 0
    return num / den, n


def _final_scored_round(seat: str, rounds_done: list) -> "tuple[dict, Optional[int]]":
    """(scores, round_no) for the seat's LAST round in which it produced any clean score
    (its final scored round — a seat that dropped before the last round is scored on its
    last usable round, never penalized to empty). Returns ({}, None) when the seat never
    scored anything. The round_no travels so the contradiction row can name it (NIT 2)."""
    latest: dict = {}
    latest_round: Optional[int] = None
    for round_results in rounds_done:
        for r in round_results:
            if r.seat == seat and r.scores:
                latest = r.scores
                latest_round = r.round_no
    return latest, latest_round


def build_scorecard(config, rubric: dict, rounds_done: list, *, chair_seat: str,
                    rubric_artifact: str = "rubric.json") -> dict:
    """Assemble scorecard.json (schema advisory-board/scorecard@1) from the merged rubric
    + the per-round results. Pure over the conductor's state — no model JSON is trusted;
    the scores are PARSED (SeatRoundResult.scores) and everything structural is computed
    here. The caller validates with board_scorecard before writing.

    CONTRADICTION SEMANTICS (NIT 2, the accepted design): a seat's contradiction compares
    its FINAL-of-each-kind — the token from its last round that declared a verdict vs the
    band of its last round that produced any clean score. These are resolved
    INDEPENDENTLY (`_final_verdict_token` vs `_final_scored_round`), so they can name
    DIFFERENT rounds: a seat can score in round 3 but decline to restate a verdict token
    there, leaving its final token in round 2. That is deliberate — each is the seat's
    last STANDING position of that kind — but a reader must be able to see when they
    diverge, so each contradiction row carries `token_round` and `score_round` (the two
    round numbers being compared; equal on the common path)."""
    criteria_in = rubric.get("criteria") or []
    criteria = [
        {"id": c["id"], "title": c["title"], "weight": c["weight"]}
        for c in criteria_in
        if isinstance(c, dict) and c.get("id") and c.get("title") is not None
    ]
    weight_of = {c["id"]: c["weight"] for c in criteria}
    criterion_ids = [c["id"] for c in criteria]

    # Every seat that appears in any round, in first-seen order (round-1 board order,
    # then any later joiner — there are none today, but the order is stable).
    seat_order: list = []
    seen_seats = set()
    for round_results in rounds_done:
        for r in round_results:
            if r.seat not in seen_seats:
                seen_seats.add(r.seat)
                seat_order.append(r.seat)

    # scores[] — one row per cleanly-scored cell across ALL rounds (the trajectory).
    scores: list = []
    notes: list = []
    for round_results in rounds_done:
        for r in round_results:
            seat_scores = r.scores   # {cid: 1–5}, already restricted to the rubric ids
            for cid in criterion_ids:
                if cid in seat_scores:
                    scores.append({
                        "seat": r.seat,
                        "round": r.round_no,
                        "criterion": cid,
                        "score": seat_scores[cid],
                    })
            note = r.rubric_note
            if note:
                notes.append({"seat": r.seat, "round": r.round_no, "note": note})

    # totals[] + contradictions[] — per-seat, over the seat's final scored round.
    totals: list = []
    contradictions: list = []
    for seat in seat_order:
        final_scores, score_round = _final_scored_round(seat, rounds_done)
        weighted_total, n_scored = _weighted_total(final_scores, weight_of)
        band = band_for(weighted_total)
        partial = n_scored < len(criterion_ids)
        # The seat's final declared VERDICT token (+ the round it came from), resolved
        # ONCE here and carried on the totals row so contradictions[] is validatable
        # standalone (D17 fix pass): the validator can now re-derive the token↔band
        # contradiction rule from totals[] alone — no arithmetic recompute, just the
        # derivable "a totals row whose token+band trips the rule MUST have a matching
        # contradictions[] row and vice versa" consistency check. `final_verdict` is a
        # known token (ship/caution/block) or null (a seat that never declared one).
        token, token_round = _final_verdict_token(seat, rounds_done)
        totals.append({
            "seat": seat,
            "weighted_total": round(weighted_total, 4) if weighted_total is not None else None,
            "band": band,
            "partial": partial,
            "criteria_scored": n_scored,
            "final_verdict": token,
            "final_verdict_round": token_round,
        })
        # A loud token↔band contradiction (D17): the seat's declared VERDICT token from
        # its final usable round vs its scores band. `block` over `strong` scores, or
        # `ship` over `weak` scores — the same self-contradiction class as "the declared
        # verdict clears a gate the seats trip". Recorded, surfaced in the render, NEVER
        # gated. Only a real band (a seat that actually scored) can contradict. The two
        # round numbers travel (NIT 2) so a reader can see when the compared token and
        # scores come from different rounds.
        if band is not None:
            if token is not None and _is_contradiction(token, band):
                contradictions.append({
                    "seat": seat,
                    "verdict": token,
                    "band": band,
                    "token_round": token_round,
                    "score_round": score_round,
                })

    return {
        "schema": SCORECARD_SCHEMA,
        "title": config.title,
        "chair_seat": chair_seat,
        "rubric_artifact": rubric_artifact,
        "criteria": criteria,
        "scores": scores,
        "rubric_notes": notes,
        "totals": totals,
        "contradictions": contradictions,
    }


def _final_verdict_token(seat: str, rounds_done: list) -> "tuple[Optional[str], Optional[int]]":
    """(token, round_no) for the seat's LAST round in which it was usable AND declared a
    verdict (its final declared verdict), or (None, None). Pure over
    SeatRoundResult.verdict (never the prose). The round_no travels so the contradiction
    row can name it (NIT 2)."""
    latest = None
    latest_round: Optional[int] = None
    for round_results in rounds_done:
        for r in round_results:
            if r.seat == seat and r.usable and r.verdict is not None:
                latest = r.verdict
                latest_round = r.round_no
    return latest, latest_round


def _is_contradiction(token: str, band: str) -> bool:
    """A SEVERE self-contradiction (D17): a `block` verdict over `strong` scores, or a
    `ship` verdict over `weak` scores. `caution`/`mixed` never contradict (they ARE the
    hedge). Fixed and coarse — never a tuned threshold."""
    return (token == "block" and band == "strong") or (token == "ship" and band == "weak")


def validate_scorecard(data: dict) -> Optional[str]:
    """Run board_scorecard.validate against the assembled scorecard.json. Returns an
    error string (captured from board_scorecard.die) if invalid, else None. Mirrors
    rubric.validate_rubric / revision.validate_changes' lazy-import + SystemExit-capture
    pattern (board_scorecard is a standalone CLI; the only in-process caller is here)."""
    import contextlib
    import io
    try:
        import board_scorecard
    except ImportError as exc:
        return f"could not import board_scorecard for schema validation: {exc}"
    buf = io.StringIO()
    try:
        with contextlib.redirect_stderr(buf):
            board_scorecard.validate(data)
    except SystemExit as exc:
        captured = buf.getvalue().strip()
        if captured.startswith("error:"):
            captured = captured[len("error:"):].strip()
        return f"scorecard schema validation failed: {captured or f'(exit {exc.code})'}"
    return None

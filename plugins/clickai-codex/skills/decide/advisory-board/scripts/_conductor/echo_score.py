"""The independence / echo score (v1.14 #9, roadmap M4 P2).

A multi-model board is only worth more than one model if the seats reach their
positions *independently*. Once they read each other, they can drift toward
agreement for social reasons — three voices that echoed into one read as authority
but carry one voice's information. This module scores that risk.

It is a PURE FUNCTION over signals the conductor already parses — nothing here
reads a seat's prose (principle #1 / §11). It reuses `convergence.parse_verdict`
(the one machine verdict token), `convergence.citations` (the concrete citation
set), and `convergence.parse_basis` (the self-reported BASIS line this milestone
adds to the round-2 template). Three explainable sub-signals over the FINAL round
transition (round N-1 → N — where echo would show, on the settled board):

  1. flip-toward-majority — of the seats that changed their verdict token in the
     final transition, how many moved TOWARD the round's emerging majority verdict.
     A seat flipping onto the majority is the echo fingerprint; a seat flipping AWAY
     (holding a real dissent) is its opposite.
  2. citation overlap — the mean pairwise Jaccard overlap of the final-round
     citation sets. High overlap means the seats lean on the same concrete evidence.
  3. deference count — how many seats' final-round BASIS token is `deference`
     (self-reported echo), how many are `evidence`/`independent`, how many `unknown`.

These roll up to a COARSE band — low / moderate / high echo risk — never a false-
precision 0-100 number. The one-line explanation always names the sub-signals that
drove the band, so a reader can audit the call.

**What this is NOT.** It FLAGS possible echo; it does not prove independence — and a
`high` band is not a verdict on the board. See `references/epistemics.md` for the
metric's stated limits and failure modes (honest convergence on strong evidence,
expected overlap on a small source, the self-reported deference token).

**The scored population.** Every sub-signal — AND the same-provider discount — reads
exactly ONE population: the seats usable in BOTH final rounds (the "overlap seats").
The discount is not derived from the full configured board: under a seat drop the two
diverge, so a same-provider proxy over the whole board would fire (or fail to fire) on
a population the metric never scored. Instead the discount is computed over the overlap
seats' own `.provider` values (`SeatRoundResult.provider`): the pair is same-provider
when `len({r.provider for r in overlap_seats}) < len(overlap_seats)`, i.e. at least two
SCORED seats share a provider. A seat whose `.provider` is missing/None counts as a
DISTINCT provider — an unknown never manufactures a same-provider discount.

**Honest degradation — the ONLY `not_computed` cases.** `not_computed` is reserved for
a run with no final transition to score: a single-round run (there is no round N-1 → N
transition, so the metric is never invoked and no sidecar is written at all), and a run
where fewer than two seats are usable in BOTH final rounds. Nothing else degrades to
`not_computed`. In particular: an OLD RUN DIR re-rendered has no `echo-score.json`, so
the pill/section are simply ABSENT — nothing is computed or claimed (not `not_computed`).
A PRE-P2 RECIPE replayed via `--from-recipe` runs with the CURRENT round-2 template
(which carries the `BASIS:` line), so it scores normally like any fresh run; if its
seats state no basis, it scores with an all-`unknown` BASIS tally — the deference
sub-signal contributes nothing and the explanation names how many seats did not state a
basis. It is a real, honest band, never a fabricated one.

Standard library only; no third-party dependencies.
"""
from __future__ import annotations

from typing import Optional

from _conductor.convergence import citations, parse_basis

__all__ = [
    "ECHO_BANDS",
    "NOT_COMPUTED",
    "echo_score",
]

# The three bands, ordered least → most concerning. `not_computed` is the honest
# degradation for a run without the signals to score (never a fabricated band).
ECHO_BANDS = ("low", "moderate", "high")
NOT_COMPUTED = "not_computed"

# Sub-signal thresholds. Deliberately coarse and explainable — the point is a band
# a reader can defend from the named sub-signals, not a tuned number. `high` overlap
# is a strong lean on shared evidence; `moderate` is a partial one.
_OVERLAP_HIGH = 0.60
_OVERLAP_MODERATE = 0.30


def _pairwise_overlap(cite_sets: list) -> Optional[float]:
    """Mean pairwise Jaccard overlap of a list of citation sets. None when there are
    fewer than two sets, or when EVERY pair is empty∪empty (no citations to compare —
    overlap is undefined, not zero). A pair where exactly one side is empty counts as
    0.0 (they share nothing); two identical non-empty sets count as 1.0."""
    sets = [set(c) for c in cite_sets]
    if len(sets) < 2:
        return None
    ratios = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            union = sets[i] | sets[j]
            if not union:
                continue   # both empty — undefined, skip (do not score as 1.0 or 0.0)
            ratios.append(len(sets[i] & sets[j]) / len(union))
    if not ratios:
        return None
    return sum(ratios) / len(ratios)


def _majority_verdict(verdicts: list) -> Optional[str]:
    """The strict-majority verdict token among the final-round verdicts, or None when
    there is no strict majority (a tie, or all None). `verdicts` may contain None
    (a seat with no clean token); those never form a majority."""
    counts: dict = {}
    for v in verdicts:
        if v is None:
            continue
        counts[v] = counts.get(v, 0) + 1
    if not counts:
        return None
    top = max(counts.values())
    leaders = [v for v, n in counts.items() if n == top]
    if len(leaders) != 1:
        return None   # tie — no single majority to flip toward
    # A strict majority needs more than half the seats that voted.
    voted = sum(counts.values())
    return leaders[0] if top * 2 > voted else None


def echo_score(prev_results: Optional[list], curr_results: Optional[list]) -> dict:
    """Score echo risk over the FINAL round transition. `prev_results`/`curr_results`
    are the last two rounds' `SeatRoundResult` lists (each item exposes `.usable`,
    `.verdict`, `.basis`, `.stdout`, `.seat`, `.provider`). Returns a dict:

        {"band": "low"|"moderate"|"high"|"not_computed",
         "explanation": str,                # one line naming the sub-signals
         "considered": int,                 # seats usable in BOTH final rounds
         "flippers": int,                   # of those, seats whose verdict shifted
         "flippers_toward_majority": int,   # of the flippers, ones onto the majority
         "majority": str|None,              # the final-round strict-majority verdict
         "overlap": float|None,             # mean pairwise citation Jaccard (0..1)
         "deference": int, "evidence": int, "independent": int, "unknown": int}

    Pure over parsed signals only. A run without a final transition, or with fewer
    than two seats usable in both final rounds, yields band `not_computed` — the
    metric never fabricates a score from signals it does not have.

    The same-provider honesty hook is read straight off the SCORED population: when
    two or more of the overlap seats share a `.provider` (e.g. `--board claude,claude`),
    high citation overlap is EXPECTED and does not by itself indicate echo — the
    explanation says so and the band does not treat overlap alone as high risk there.
    Provider identity is read from each `SeatRoundResult.provider`; a seat with a
    missing/None provider counts as DISTINCT (an unknown never manufactures a
    same-provider discount)."""
    prev = [r for r in (prev_results or []) if r.usable]
    curr = [r for r in (curr_results or []) if r.usable]
    prev_by = {r.seat: r for r in prev}
    overlap_seats = [r for r in curr if r.seat in prev_by]

    if len(overlap_seats) < 2:
        return {
            "band": NOT_COMPUTED,
            "explanation": ("Not computed — fewer than two seats were usable in both "
                            "final rounds, so there is no cross-seat movement to score."),
            "considered": len(overlap_seats),
            "flippers": 0, "flippers_toward_majority": 0, "majority": None,
            "overlap": None,
            "deference": 0, "evidence": 0, "independent": 0, "unknown": 0,
        }

    # Sub-signal 1: verdict flips toward the emerging majority (final round).
    final_verdicts = [r.verdict for r in overlap_seats]
    majority = _majority_verdict(final_verdicts)
    flippers = 0
    flippers_toward_majority = 0
    for r in overlap_seats:
        prev_v = prev_by[r.seat].verdict
        curr_v = r.verdict
        if prev_v is not None and curr_v is not None and prev_v != curr_v:
            flippers += 1
            if majority is not None and curr_v == majority and prev_v != majority:
                flippers_toward_majority += 1

    # Sub-signal 2: mean pairwise citation overlap (final round).
    overlap = _pairwise_overlap([citations(r.stdout) for r in overlap_seats])

    # Sub-signal 3: self-reported BASIS tally (final round).
    tally = {"deference": 0, "evidence": 0, "independent": 0, "unknown": 0}
    for r in overlap_seats:
        b = r.basis
        tally[b if b in tally else "unknown"] += 1

    # The same-provider discount reads the SCORED population itself: two or more
    # overlap seats sharing a provider. A missing/None provider counts as distinct.
    same_provider = _same_provider(overlap_seats)

    band = _band(flippers_toward_majority, len(overlap_seats), overlap,
                 tally["deference"], same_provider)
    explanation = _explain(band, len(overlap_seats), flippers,
                           flippers_toward_majority, majority, overlap, tally,
                           same_provider)
    return {
        "band": band,
        "explanation": explanation,
        "considered": len(overlap_seats),
        "flippers": flippers,
        "flippers_toward_majority": flippers_toward_majority,
        "majority": majority,
        "overlap": overlap,
        "deference": tally["deference"],
        "evidence": tally["evidence"],
        "independent": tally["independent"],
        "unknown": tally["unknown"],
    }


def _same_provider(overlap_seats: list) -> bool:
    """True when at least two of the SCORED (overlap) seats share a provider — read
    straight off each seat's `.provider`, the only population the metric scored. When
    the distinct providers among the overlap seats number fewer than the seats
    themselves, a scored pair shares a provider and high citation overlap is expected.

    A seat whose `.provider` is missing/None counts as a DISTINCT provider: unknowns
    are dropped before the duplicate check, so an unknown can never manufacture a
    same-provider discount — not even paired with another unknown. Only seats with a
    KNOWN, shared provider fire the discount."""
    providers = [getattr(r, "provider", None) for r in overlap_seats]
    known = [p for p in providers if p is not None]
    return len(set(known)) < len(known)


def _band(flippers_toward_majority: int, considered: int, overlap: Optional[float],
          deference: int, same_provider: bool) -> str:
    """The coarse band from the sub-signals. Explainable rules, not a tuned score.

    Two "echo" signals are recognized:
      * strong_flip — at least half of the considered seats flipped ONTO the emerging
                      majority verdict in the final round (the convergence fingerprint);
      * any_deference — at least one seat self-reported `deference` (self-reported echo).
    Citation overlap CORROBORATES those signals but never stands alone: high overlap
    with no flip and no deference can just be a small source everyone cites.

      * HIGH   — an echo signal (strong_flip OR any_deference) corroborated by high
                 citation overlap. On a SAME-PROVIDER board, overlap is expected and
                 does NOT corroborate, so HIGH there requires BOTH echo signals
                 (a flip onto the majority AND a self-reported deference).
      * MODERATE — one echo signal, or (on a mixed-provider board) moderate/high
                 overlap on its own.
      * LOW    — no flip onto a majority, no self-reported deference, and low overlap.
    """
    frac_flip = (flippers_toward_majority / considered) if considered else 0.0
    high_overlap = overlap is not None and overlap >= _OVERLAP_HIGH
    mod_overlap = overlap is not None and overlap >= _OVERLAP_MODERATE

    strong_flip = frac_flip >= 0.5
    any_deference = deference > 0
    echo_signal = strong_flip or any_deference

    if same_provider:
        # Overlap is expected here and never corroborates. HIGH needs both echo
        # signals; a single echo signal is MODERATE; no echo signal is LOW
        # (however high the overlap).
        if strong_flip and any_deference:
            return "high"
        if echo_signal:
            return "moderate"
        return "low"

    if echo_signal and high_overlap:
        return "high"
    if echo_signal or mod_overlap:
        return "moderate"
    return "low"


def _pct(x: Optional[float]) -> str:
    return "n/a" if x is None else f"{round(x * 100)}%"


def _explain(band: str, considered: int, flippers: int,
             flippers_toward_majority: int, majority: Optional[str],
             overlap: Optional[float], tally: dict,
             same_provider: bool) -> str:
    """One line that names the sub-signals behind the band (no pseudo-precision — it
    reports the coarse counts/percent that drove the call, e.g. '2/2 seats flipped
    toward the majority with 78% citation overlap and 1 deference declaration')."""
    parts = []
    if majority is not None and flippers_toward_majority:
        parts.append(f"{flippers_toward_majority}/{considered} seats flipped toward "
                     f"the majority ({majority})")
    elif flippers:
        parts.append(f"{flippers}/{considered} seats changed verdict "
                     f"(none onto a majority)")
    else:
        parts.append(f"0/{considered} seats changed verdict in the final round")
    parts.append(f"{_pct(overlap)} mean citation overlap")
    if tally["deference"]:
        parts.append(f"{tally['deference']} deference declaration"
                     + ("s" if tally["deference"] != 1 else ""))
    if tally["unknown"]:
        parts.append(f"{tally['unknown']} seat"
                     + ("s" if tally["unknown"] != 1 else "")
                     + " did not state a basis (unknown)")
    lead = {
        "high": "High echo risk",
        "moderate": "Moderate echo risk",
        "low": "Low echo risk",
    }[band]
    note = ""
    if same_provider:
        note = ("; this is a same-provider board, where high citation overlap is "
                "expected and is not counted as echo on its own")
    return f"{lead}: {', '.join(parts)}{note}. Flags possible echo — it does not prove independence."

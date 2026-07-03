**Verdict**
Overall: caution, confidence high. I would move to ship if the design explicitly adds unique-id chair selection, a pre-round `rubric.json` artifact, and reconciles the score-parse retry path with the “seat remains usable” failure posture.

**Q Rulings**
Q1: Ship. One proposal fan-out plus one chair merge is the right cost/control trade-off, with the >=2 usable proposal floor. Add one guardrail: the chair should not introduce criteria that cannot be traced to seat proposals.

Q2: Caution. Use revision-style unique seat-id selection, not synthesizer’s current provider-name lookup, so duplicate-provider boards work. Scoring as acceptance is fine; add criterion-scoped `RUBRIC-NOTE cN:` support.

Q3: Caution. Coexisting `SCORE cN: 1-5` lines plus the existing verdict token is right, but missing scores cannot reuse the normal invalid-output path unchanged, because Q9 wants the seat to remain usable after retry.

Q4: Ship. Keep scores out of the gate for v1.15. Render token/score-band contradictions loudly and record them in `scorecard.json`, but do not make numeric bands affect exit codes yet.

Q5: Caution. A separate scorecard is right, but the agreed rubric itself should be a pre-round strict `rubric.json` artifact. Final `scorecard.json` should pin or embed that exact rubric and add per-round scores, notes, totals, and bands.

Q6: Ship. Widen movement to include integer score changes, bounded by `--max-rounds`. Define missing-cell behavior explicitly: missing to present should count as movement; absent values are never imputed.

Q7: Ship. `--rubric` should stay orthogonal and should not require `--synthesize`. If no verdict pointer exists, run metadata should still record scorecard/rubric shas so standalone artifacts have provenance.

Q8: Ship. Implement stakeholder panel as a new lens preset only. Do not make it imply `--rubric`, board composition, or default criteria.

Q9: Caution. Refusing on chair failure is correct because no opinion rounds have been produced yet. Clarify exit code, write `rubric-rejected.*`, and define `--revise --rubric` when the prior run has no rubric.

**Strongest Objections**
- Chair selection must be id-axis. `SeatConfig.id` is the unique artifact key, while `choose_synthesizer_seat()` still keys preferred seats by provider name; `choose_revision_seat()` already fixed this with id-first lookup.
- The score parser/status model is underspecified. The design says invalid scores trigger retry, but also says the seat remains usable with missing cells after retry. That needs a distinct “usable review, partial scorecard” state.
- `scorecard.json` alone is not enough before opinion rounds. The merged rubric is injected into round prompts, so the exact injected object needs its own immutable artifact and sha before scores exist.
- Revision carry-forward needs edge-case rules: prior rubric exists, prior rubric missing, `--from-recipe`, and explicit `--rubric` on a non-rubric prior run.

**Recommended Execution Sequence**
1. Record D15+ decisions and rewrite the v1.15 phases before coding.
2. Add config/recipe/status/run-card/artifact-tree plumbing for `--rubric` and `--chair-seat`, with no default artifact byte drift.
3. Implement `_conductor/rubric.py`: proposal prompt/parser, chair prompt/parser, marker neutralization, raw records, `rubric.json`, and strict validation.
4. Thread the agreed rubric into round prompts and implement score extraction separately from verdict usability.
5. Extend convergence with score movement and criterion-level movement detail.
6. Add `board_scorecard.py`, scorecard writing, optional verdict pointer validation, and render sections.
7. Add revise carry-forward, mocks, golden tests, byte-identity tests, malformed-validator tests, and recipe replay tests.

**Invariants And Guardrails**
- No `--rubric`, no body-byte changes.
- No disk writes before consent; every rubric byte sent to seats is consent-hash covered.
- Models author criterion prose, notes, and scores only. Conductor owns ids, shas, totals, bands, completeness, and weight arithmetic.
- Gate reads only verdict tokens/evidence integrity, not scores.
- Criteria ids are stable `c1...cN`; weights are integer percentages summing exactly to 100.
- Missing scores remain missing, totals become partial, and no score is inferred.

**Risks And Evidence**
- Pipeline insertion is real structure: round 1 starts directly in `_run_after_activate()` at [cli.py](skills/advisory-board/scripts/_conductor/cli.py:421), and auto convergence consumes `board_movement()` at [cli.py](skills/advisory-board/scripts/_conductor/cli.py:509).
- Existing convergence is token/citation only: [convergence.py](skills/advisory-board/scripts/_conductor/convergence.py:197).
- Gate intentionally ignores gameable confidence and reads final verdict tokens: [board_verdict.py](skills/advisory-board/scripts/board_verdict.py:463).
- Recipe persistence distinguishes record artifacts from presentation flags: [recipe.py](skills/advisory-board/scripts/_conductor/recipe.py:232).
- Current status stages are a literal enum and must be extended deliberately: [status.py](skills/advisory-board/scripts/_conductor/status.py:81).
- The design itself notes no round 0, no multi-score parser, no numeric convergence path, and no seat-composition preset in [design brief](design/v1.15-rubric-first-design-brief.md:41).

**Ask Other Seats**
Challenge whether rendering-only score/token contradictions are honest enough for users, whether chair-without-source can merge criteria well enough, and whether two artifacts (`rubric.json` plus `scorecard.json`) are worth the extra schema surface.

VERDICT: caution

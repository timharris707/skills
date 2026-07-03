**1. Updated Verdict**
Caution, confidence high. The design is shippable only after D15+ records four changes: chair selection by canonical seat id, an explicit proposal-to-rubric partition, a standalone `rubric.json`/`scorecard.json` artifact chain, and a clarified score-parse retry path. What would change my verdict to ship: those become required invariants in the roadmap before Phase 2 code.

Q map: Q1 ship with merge-partition guardrails; Q2 caution on “reuse synthesizer verbatim”; Q3 ship with a separate scoring parser; Q4 ship only if score/token contradictions stay non-gating but loud; Q5 caution unless `rubric.json` is the pre-round artifact of record; Q6 ship; Q7 ship; Q8 ship; Q9 caution until retry/partial-score semantics are precise.

**2. Changed / Dissent**
Changed toward Claude on Q1: Claude’s “completeness check is unverifiable as worded” is stronger than my round-1 “no untraced criteria” guardrail. The chair must emit a conductor-checkable partition: every proposal id appears exactly once in either a merged criterion’s `subsumes[]` or a dropped entry with reason.

Still dissent from Gemini’s overall SHIP: the latency concern is real but opt-in; the blocking risk is structural ambiguity, not cost. The current code has duplicate-provider seat ids and strict artifact precedents that the strawmen do not fully incorporate.

**3. Strongest Remaining Objections**
The phrase “conductor cross-asserts completeness” is under-specified. Without proposal ids and chair-emitted mapping, the conductor can validate JSON shape but not completeness.

`--chair-seat` cannot mirror current synthesizer lookup verbatim. `choose_synthesizer_seat()` keys preferred seats by provider name, which collapses duplicate-provider boards; chair/revision must use canonical ids.

Q3 and Q9 conflict operationally. “Missing score triggers standard retry” plus “seat remains usable after retry” needs a purpose-built rubric round runner or classifier. Current retry machinery drops `InvalidOutput` after the second attempt.

`rubric.json` should be a first-class artifact, not just fields embedded in `scorecard.json`. The agreed rubric and proposal accounting are the record that later scoring depends on.

**4. Recommended Execution Sequence**
1. Add design decisions first: chair id semantics, merge partition, artifact chain, score retry/partial semantics, non-gating scores.
2. Build parsers/validators before orchestration: proposal parser, chair merge parser, `board_rubric.py` or rubric validation inside `board_scorecard.py`, then `board_scorecard.py`.
3. Add rubric proposal + chair module before round 1, inside the existing post-activate guard.
4. Add scoring parser and rubric-aware round runner, with tests for partial score cells after retry.
5. Add convergence score movement, recipe/from-recipe, live status stage, render sections, and byte-identity tests.
6. Add stakeholder-panel as a lens preset only.
7. Dogfood rubric runs before release, especially duplicate-provider boards and `--revise`.

**5. Invariants And Guardrails**
All ids are conductor-minted: proposal ids, criterion ids `c1..cN`, canonical chair seat id.

Merge partition: every proposal id appears exactly once across `subsumes[]` and `drops[]`; every merged criterion cites at least one proposal; every drop has a reason.

Weights are positive integer percentages and sum exactly 100 after chair merge. Invalid arithmetic retries the chair, then refuses.

`VERDICT:` remains canonical for gate and schema. Scores never derive or override verdict tokens in v1.15.

Score parser uses `parse_verdict`-style hardening per criterion id: quoted/indented/code-spanned score lines rejected, last qualifying line per id wins, no imputation.

Missing score cells after final retry are absent cells, not zeroes; totals are marked partial.

Non-rubric runs must keep rendered body byte identity. New rubric sections whole-drop to zero bytes.

`--from-recipe` replays rubric/chair templates and canonical chair id exactly. `--revise` mechanically carries the prior rubric.

**6. Risks / Missing Evidence**
No calibration data exists for score bands or token/score contradiction labels. Keep them descriptive, not gating.

The exact exit code for chair-merge refusal is still ambiguous: “preflight NO-GO-like” versus a new rubric integrity failure. Decide before implementation.

The chair prompt may still hallucinate valid-looking mappings. The partition invariant catches structural invention, not semantic bad merges.

Scorecard rendering could become noisy with per-round, per-seat, per-criterion rows. The artifact should keep full data; human render should summarize with drill-down style sections.

Stakeholder-panel as a lens preset satisfies the current machinery, but not the fuller “board composition preset” product vision. That should be documented as out of scope.

**7. Concrete Evidence**
`skills/advisory-board/scripts/_conductor/cli.py:421` defines `_run_after_activate`; round 1 begins immediately at `cli.py:435-437`, so rubric insertion is genuinely new pre-round structure.

`skills/advisory-board/scripts/_conductor/convergence.py:90-112` parses one `VERDICT:` token; `convergence.py:197-210` defines movement only as verdict shift or new citations.

`skills/advisory-board/scripts/_conductor/synthesizer.py:220-228` selects preferred synthesizer by `s.name`; `revision.py:274-288` explains canonical unique-id selection for duplicate boards.

`skills/advisory-board/scripts/_conductor/config.py:300-321` creates unique ids such as `provider#1`; this is why chair selection must not be provider-name only.

`skills/advisory-board/scripts/_conductor/spawn.py:188-222` classifies malformed round output as retryable `InvalidOutput`; `rounds.py:125-135` retries once, then stops. That does not implement “partial scores but usable seat” by itself.

`skills/advisory-board/scripts/board_verdict.py:180-217` validates `changes` as exactly `{artifact, sha256}`; `board_changes.py:294-301` refuses unknown top-level keys. This is the right precedent for scorecard/rubric artifacts.

`skills/advisory-board/scripts/render_handoff.py:45-50` states new sections must whole-drop to zero body bytes when empty.

`skills/advisory-board/scripts/_conductor/status.py:34-37` records RH-1, and `status.py:88` lists the current stage enum without `rubric`.

`skills/advisory-board/scripts/_conductor/recipe.py:240-267` persists record-shaping synth settings and template shas; `recipe.py:282-285` explicitly says live status is not persisted because it is not a record artifact.

BASIS: evidence
VERDICT: caution

# Advisory Board — Final Consensus
v1.13 p4 endorsement pass pr review
Board: Claude (Architecture & systems/claude-opus-4-8) · Codex (Implementation & testing/gpt-5.5). Rounds: 2.

## Verdict: SHIP WITH CHANGES — unanimous (high confidence)

## Delta vs the previous run
Revises: ~/.advisory-board/runs/v1-13-p4-endorsement-pass-pr-review-2026-07-02 (2026-07-02)
**Trajectory: DO NOT SHIP YET → SHIP WITH CHANGES**
Cleared blockers (5):
- Run-card endorsement count is name-axis and undercounts duplicate-provider boards
- Per-seat --timeout is not honored in the endorsement fan-out
- Egress disclosure overclaims — 'no new egress' / 'already egressed' misnames what is sent
- Revision-seat selection and recording are provider-name based (duplicate providers cannot be disambiguated)
- Renderer byte-identity for the no-endorse path is not proven (endorsement CSS is unconditional)
New blockers (1):
- Validator does not enforce the dropped-row contract
Cleared concerns (1):
- Re-validation-failure path leaves orphan endorsement/*.md with endorsements: []
New concerns (2):
- Endorsement artifacts written before re-validation (orphan-artifact edge)
- Default duplicate-board reviser is a last-name dict-collapse (note, not a bug)

## Consensus blockers (must fix before ship)
1. Validator does not enforce the dropped-row contract — Both seats (final round) converge on this as the one gating issue. `_validate_endorsement` only checks that `dropped` is not a value other than `True`; it never asserts `position == 'ABSTAIN'` when `dropped` is set and never requires a non-empty `note`. Codex verified directly that both `{position:'ENDORSE', dropped:true}` and `{position:'ABSTAIN', dropped:true}` with no note are accepted, contradicting the documented contract (changes-schema.md) and the conductor's own `dropped_rows`, which always emits ABSTAIN + dropped:true + a reason note. No pipeline path produces a violating row (the conductor builds the rows), but the validator's stated job — and this PR's own tightening theme — is to catch hand-authored/corrupted files. Downstream, the renderer's `_tally` counts by `position` and ignores `dropped`, so a hand-authored `{dropped:true, position:'ENDORSE'}` would be counted as an endorsement in the handoff summary. Both seats hold this against tagging v1.13.0; it is a ~3-line fix plus negative tests. Claude notes a recorded deferral to v1.13.1 with explicit rationale is an acceptable alternative to landing the fix now.
   - evidence: `scripts/board_changes.py:258` (code) — unchecked
   - evidence: `references/changes-schema.md:152` (code) — unchecked
   - evidence: `scripts/_conductor/endorsement.py:392` (code) — unchecked
   - evidence: `scripts/render_verdict.py::_tally` (code) — unchecked

## Hard dissent (preserved)
- Claude: Claude labels a residual dissent on 'stale egress/doc strings': it grepped every egress site (`artifacts.py:143-144` and `:157-158`, `cli.py:762`, `endorsement.py:253` and `:616`, `data-handling.md:48`) and found the converged round-2 framing everywhere — the revision seat sees only already-sent source, and the endorsement seat receives the board-generated revised draft framed as the same exposure class as round-2 review sharing. It could not reproduce any specific stale string and holds that, absent an exact file:line, that concern should be dropped rather than gate the tag. Codex's final-round review does treat the egress-category blocker as materially cleared.

## What the board couldn't verify
- The reported '1279 OK' test count is author-asserted; neither seat executed the suite (read-only). Both seats say to confirm green in CI before tagging.
- Codex could not run the full suite in the read-only sandbox (even shell here-docs failed to create temp files); it ran only a direct `python -c` validator probe for the dropped-row issue.
- Claude could not reproduce any specific stale egress string; it found the converged round-2 framing at all egress sites it checked.

## Open questions
- Land the dropped-row validator fix now, or record a conscious deferral to v1.13.1 with an explicit rationale that it is not a live pipeline path? Either flips Claude to ship.
- Is there any concrete 'stale egress string' site? Claude found none and asks for an exact file:line, otherwise the concern should be dropped.

## Next actions
- Tighten `_validate_endorsement` in `scripts/board_changes.py`: when `dropped` is true, require `position == 'ABSTAIN'` and a non-empty string `note`; die otherwise.
- Add negative tests to `TestEndorsementValidatorMatrix`: reject dropped+ENDORSE, reject dropped without note, and accept conductor-shaped dropped+ABSTAIN+note.
- (Non-gating) Add a one-line divergence note in the `cli.py` failure branch when endorsements are dropped from `changes.json` but per-seat `endorsement/` records remain on disk — or validate candidate rows before writing the endorsement artifacts.
- (Non-gating) Add one sentence to `references/changes-schema.md` noting the default reviser on a duplicate-provider board is the last same-name seat.
- Run the focused suite (`TestEndorsement*`, id-axis, exotic-note) fail-before/pass-after, then the full suite; confirm green in CI before tagging v1.13.0.
- Alternatively, record a conscious deferral of the validator fix to v1.13.1 with an explicit rationale.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

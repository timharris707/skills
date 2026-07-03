# Advisory Board — Final Consensus
v1.14 p2 echo score pr review
Board: Claude (Architecture & systems/claude-opus-4-8) · Codex (Implementation & testing/gpt-5.5). Rounds: 2.

## Verdict: SHIP WITH CHANGES — unanimous (high confidence)

## Delta vs the previous run
Revises: ~/.advisory-board/runs/v1-14-p2-echo-score-pr-review-2026-07-02 (2026-07-02)
**Trajectory: DO NOT SHIP YET → SHIP WITH CHANGES**
Cleared blockers (2):
- DECISION docs claim `not_computed` degradations the code never performs
- Pre-P2 `--from-recipe` replay is not byte-exact and the recorded template sha is never validated
Still open blockers (1):
- _same_provider() collapses two None providers, contradicting its own "None is distinct" contract
New blockers (1):
- Regression suite has no [None, None] case — the exact input that fires the bug
Cleared concerns (2):
- The mis-populated same-provider band is advisory-only
- Recipe provenance records only the round-1 template id
New concerns (3):
- Blocker-2 "pre-P2 recipe" doc reconciliation is incomplete
- CHANGELOG suite-count drift
- SKILL.md omits the <2 overlap seats not-computed case

## Consensus blockers (must fix before ship)
1. _same_provider() collapses two None providers, contradicting its own "None is distinct" contract — Both seats agree _same_provider() computes `len(set(providers)) < len(providers)`, and Python collapses `{None, None}` -> `{None}` (len 1 < 2), so two seats with a missing/None provider read as same-provider and fire the same-provider discount. This contradicts the rule stated in the same function and in the module/echo_score docstrings that a missing/None provider counts as a DISTINCT provider; the self-contradicting parenthetical documents the buggy behavior. The function is new in this fix pass, so it is the pass's new defect — Claude retracted its round-1 "no new defect" claim after verifying Codex's finding.
   - evidence: `scripts/_conductor/echo_score.py:219` (code) — unchecked
   - evidence: `scripts/_conductor/echo_score.py:214` (code) — unchecked
   - evidence: `scripts/_conductor/echo_score.py:215` (code) — unchecked
   - evidence: `scripts/_conductor/echo_score.py:40` (code) — unchecked
   - evidence: `scripts/_conductor/echo_score.py::_same_provider` (code) — unchecked
2. Regression suite has no [None, None] case — the exact input that fires the bug — The existing test only exercises one None seat (`{Anthropic, None}`), which stays distinct under set() and passes by accident; there is no `[None, None]` case, so the suite does not cover the defect. Both seats call adding this regression mandatory before ship — it is the test that would have caught the bug.
   - evidence: `tests/test_run_board.py:14084` (code) — unchecked
   - evidence: `tests/test_run_board.py::test_none_provider_counts_as_distinct_no_discount` (code) — unchecked

## Hard dissent (preserved)
- Claude: Dissents from Codex on severity/reachability. Claude argues the None-collapse cannot downgrade a real board: SeatRoundResult.provider is a non-optional str populated from self.adapter.provider, always a registry-supplied string, so .provider is never None outside hand-built fixtures and the live blast radius is nil. Claude agrees the defect must be fixed (it contradicts its own documented contract, is a latent bug, and leaves a test hole) but holds it is not currently reachable on a real run.
- Codex: Maintains the None-provider defect is real and material against Claude's round-1 "no substantive new defect" read (which Claude retracted in round 2). Codex verified a two-seat provider=None, high-overlap, both-flip, no-deference case returns `moderate` with a same-provider note when the contract says it should stay mixed/unknown and return `high`, framing it as an edge-path/API-contract issue that the PR explicitly documents and tests.

## What the board couldn't verify
- Neither seat re-ran the full suite (~1403 tests) on the exact staged tree; both reviewed staged files, not a live run.
- Claude did not independently reproduce the full HTML byte-identity golden on the exact staged tree.
- Codex ran the existing test_none_provider_counts_as_distinct_no_discount (it passes) but it does not cover the two-unknown-provider defect.
- Codex's git commands emitted sandbox temp/cache warnings but still returned status/stat output.

## Open questions
- Can any future adapter or partial-init path yield a None .provider at runtime? Claude flags that .provider is never None on a real run today, but if that assumption breaks the None-collapse defect becomes live rather than latent.

## Next actions
- Fix _same_provider() so each missing/None provider is treated as distinct — e.g. drop Nones before the duplicate check, or map each missing value to a unique sentinel (unknown, seat_id or index); delete the self-contradicting parenthetical at echo_score.py:215 and keep the docstring's "distinct" headline.
- Add a [None, None] regression (two None providers, strong flip, high overlap, no deference -> expect high band and no same-provider note) beside test_none_provider_counts_as_distinct_no_discount.
- Reconcile the stale "pre-P2 recipe" docs/comments (render_verdict.py:821 and :1282, render_handoff.py:158-164, references/handoff-template.html:456-459) to "old run dir / pre-P2 handoff-data with no sidecar," since a replayed pre-P2 recipe now scores normally.
- Correct CHANGELOG.md:23 to 1355 -> 1403 (or split implementation vs fix-pass counts) and re-scan that block for other count/version drift.
- Add the <2 overlap seats not-computed case to SKILL.md:115.
- Keep the fix confined to _same_provider — preserve the byte-identity goldens for old dirs, the overlap-seats scoping of the discount, and the advisory-only (non-gating) nature of the score.
- Re-run the targeted echo tests, the full suite, and the HTML byte-identity goldens on the exact staged tree; confirm green.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

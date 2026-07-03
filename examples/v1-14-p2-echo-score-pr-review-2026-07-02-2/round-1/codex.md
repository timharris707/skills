1. **Verdict: CAUTION, medium confidence.**  
What would change it: fix the `None` provider duplicate case, update the stale “pre-P2 recipe” comments/docstrings, add regression coverage, and rerun the suite.

2. **Strongest Objections**

- The same-provider fix is not fully correct for the stated `None` rule. The docs say missing/`None` provider counts as distinct, but `_same_provider()` uses `set(providers)`, so two `None` providers collapse into one provider and trigger the discount. That can downgrade a mixed/unknown-provider high-risk case to moderate.
- Some reconciliation comments still say pre-P2 recipes have no `echo-score.json`, which is now false for replayed pre-P2 recipes. Runtime behavior is okay, but the comments contradict the revised docs.

3. **Recommended Execution Sequence**

1. Change `_same_provider()` so each `None`/missing provider is unique, e.g. key unknown providers by seat id or object sentinel.
2. Add a regression: two overlap seats with `provider=None`, strong flip, high overlap, no deference should be `high` and should not include the same-provider note.
3. Update stale comments in `render_handoff.py` / `render_verdict.py` and recipe/template comments that still imply old byte-exact replay or no pre-P2 replay sidecar.
4. Rerun full suite.

4. **Invariants And Guardrails**

- Same-provider discount must read only overlap seats.
- Unknown provider identity must never create a discount.
- `not_computed` only for single-round/no final transition or fewer than two overlapping usable seats.
- `BASIS:` remains advisory and never gates.
- Old run dirs with no sidecar stay absent/byte-identical.

5. **Risks / Missing Evidence**

I did not rerun the full suite in this read-only review. I did run a tiny bytecode-disabled probe confirming `_same_provider([None, None])` returns `True`, and an echo-score probe showing the band downgrades to `moderate` with the same-provider note.

6. **Concrete Evidence**

- Population fix mostly landed: `cli.py` now calls `echo_score(rounds_done[-2], rounds_done[-1])` with no board proxy at [cli.py](skills/advisory-board/scripts/_conductor/cli.py:467).
- The contradictory implementation is here: providers are collected and collapsed with `set()` at [echo_score.py](skills/advisory-board/scripts/_conductor/echo_score.py:218), despite the doc saying `None` is distinct at [echo_score.py](skills/advisory-board/scripts/_conductor/echo_score.py:214).
- Existing test only covers one `None` plus one real provider, not two unknowns, at [test_run_board.py](skills/advisory-board/tests/test_run_board.py:14084).
- Stale pre-P2 recipe comments remain at [render_handoff.py](skills/advisory-board/scripts/render_handoff.py:158) and [render_verdict.py](skills/advisory-board/scripts/render_verdict.py:819).

7. **Ask Other Seats To Challenge**

- Whether `None` providers can ever occur in real persisted runs, or only hand-built tests/API callers.
- Whether the duplicate-provider discount should fire for “any pair shares provider” on a larger mixed board, or only when the scored population is provider-homogeneous.
- Whether stale comments are acceptable before merge, given this PR is specifically about provenance and doc/code exactness.

VERDICT: caution

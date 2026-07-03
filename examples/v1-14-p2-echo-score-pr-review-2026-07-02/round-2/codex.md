1. **Updated Verdict**  
**BLOCK**, confidence high. What would change it: enforce exact/non-scoring behavior for pre-P2 `--from-recipe` replay, align dropped-seat degradation, and fix or moot the same-provider population bug with tests.

2. **Changed Mind / Dissent**  
Changed: I give more weight to Claude’s same-provider objection, but I now see it as mostly downstream of the dropped-seat policy. If any dropped final-round seat makes echo `not_computed`, the population bug mostly disappears.

Still dissent with Claude’s CAUTION: recipe replay is not a caution-level edge. The contract says `--from-recipe` replay stays exact, and current code rebuilds current round-2 prompts.

3. **Strongest Objections**  
**Blocker: pre-P2 `--from-recipe` replay is not exact and is not non-scoring.** [config.py](skills/advisory-board/scripts/_conductor/config.py:505) loads recipe fields into `base`, but [egress.py](skills/advisory-board/scripts/_conductor/egress.py:53) always builds round-2 prompts from the current template, which now includes `BASIS:` at [prompts.py](skills/advisory-board/scripts/_conductor/prompts.py:439). [cli.py](skills/advisory-board/scripts/_conductor/cli.py:466) then writes `echo-score.json` for any two-round replay.

**Blocker/contract mismatch: dropped-seat degradation is not implemented as claimed.** `echo_score` filters to usable overlapping seats at [echo_score.py](skills/advisory-board/scripts/_conductor/echo_score.py:126) and computes a real band whenever two remain. [cli.py](skills/advisory-board/scripts/_conductor/cli.py:466) writes the sidecar regardless of whether another final-round seat dropped.

**Concern: same-provider discount uses full configured board, not scored seats.** [cli.py](skills/advisory-board/scripts/_conductor/cli.py:468) passes distinct providers from `config.board`; `_same_provider` compares that to considered seats at [echo_score.py](skills/advisory-board/scripts/_conductor/echo_score.py:184). A `claude,claude,codex` run with codex dropped scores two Claude seats as mixed-provider.

4. **Recommended Sequence**  
1. Add recipe provenance handling: preserve old prompt bytes by recorded template/sha, or refuse/scoring-disable pre-P2 recipes loudly.  
2. Decide dropped-seat policy. If claimed policy stands, any dropped final-transition seat should produce no sidecar/section or `not_computed` consistently.  
3. If scoring subsets remains allowed, compute same-provider from `SeatRoundResult.provider` among `overlap_seats`, not from `config.board`.  
4. Add regression tests for pre-P2 recipe replay, three-seat one-dropped final round, and duplicate-provider-with-dropped-other-provider.

5. **Invariants / Guardrails**  
Keep the metric pure over parsed verdict, parsed basis, and parsed citations only. Never infer missing `BASIS`. Do not emit a real band for a run whose prompt did not request the token. HTML pill remains optional and escaped.

6. **Risks / Missing Evidence**  
I did not rerun the full suite in this read-only review. The current tests miss the pre-P2 recipe replay and three-seat dropped-seat cases. There is also a provenance concern: [recipe.py](skills/advisory-board/scripts/_conductor/recipe.py:254) still records only the round-1 template id while the changed surface is round 2.

7. **Concrete Evidence**  
Trigger: replay an old two-round recipe with old `prompt_template_sha256`. Current code loads it, emits the new `BASIS:` round-2 prompt, and writes `echo-score.json`. Trigger: run three seats where one drops before the final round; current code scores the remaining two instead of degrading as claimed.

BASIS: independent
VERDICT: block

**Verdict**
Block, medium-high confidence. I would change this to caution/ship after the rubric proposal packet is made equivalent to the actual round-1 review context for `--revise` and `--repo`, with tests proving those composed paths.

**Strongest Objections**
- **BLOCKER: rubric proposals are not built from the same full source packet as round 1.** `cmd_run()` prepares repo grounding and revision context before `_execute_run()` ([cli.py](skills/advisory-board/scripts/_conductor/cli.py:252), [cli.py](skills/advisory-board/scripts/_conductor/cli.py:260)). Round 1 includes `{repo_grounding}` and `{revision_context}` ([prompts.py](skills/advisory-board/scripts/_conductor/prompts.py:188), [prompts.py](skills/advisory-board/scripts/_conductor/prompts.py:326)), but the rubric proposal prompt only embeds `config.source.text` ([rubric.py](skills/advisory-board/scripts/_conductor/rubric.py:771)). For `run --rubric --revise`, the rubric is proposed without the prior verdict/diff that the opinion round reviews. For `run --rubric --repo`, the proposal pass also uses an empty scoped tempdir ([cli.py](skills/advisory-board/scripts/_conductor/cli.py:735)) while round 1 uses the approved snapshot ([rounds.py](skills/advisory-board/scripts/_conductor/rounds.py:226)). That violates D15/D20 orthogonality and “full source packet” for composed runs.
- **CONCERN: duplicate-provider chair projection still leaks through the run card.** Execution defaults to the first `claude` seat in board order ([rubric.py](skills/advisory-board/scripts/_conductor/rubric.py:368)), but the run card computes `by_name = {s.name: s ...}` and can display the last duplicate provider ([artifacts.py](skills/advisory-board/scripts/_conductor/artifacts.py:170)). Failure: `--board claude,claude,codex --rubric --dry-run` can advertise a different chair than the real run uses.
- **CONCERN: `choose_chair_seat()` itself still accepts ambiguous provider names for direct callers.** The resolver rejects ambiguity ([config.py](skills/advisory-board/scripts/_conductor/config.py:453)), but `choose_chair_seat(..., preferred="claude")` falls back through a by-name dict ([rubric.py](skills/advisory-board/scripts/_conductor/rubric.py:358)). The contract names both resolver and chooser as id-first/refuse-ambiguous.
- **CONCERN: rubric template shas are recorded but not checked on recipe replay.** The recipe writes rubric proposal/chair shas ([recipe.py](skills/advisory-board/scripts/_conductor/recipe.py:330)), while replay drift warning checks only the main prompt template sha ([config.py](skills/advisory-board/scripts/_conductor/config.py:528)). A future rubric template edit would silently change replayed rubric bytes.

**Prior Blockers**
The original consent-hash blocker is cleared for the plain-source path: rubric proposal blobs join `egress_blobs` before approval ([cli.py](skills/advisory-board/scripts/_conductor/cli.py:288)), are passed to the gate, persisted, and reasserted ([cli.py](skills/advisory-board/scripts/_conductor/cli.py:406), [cli.py](skills/advisory-board/scripts/_conductor/cli.py:714)). The chair mechanical retry blocker is cleared: parse, build, partition, weight sum, and schema validation now run inside the two-attempt loop ([rubric.py](skills/advisory-board/scripts/_conductor/rubric.py:1105)).

**Recommended Execution Sequence**
1. Make `build_rubric_proposal_prompt()` include the same contextual review inputs as round 1: revision block, repo-grounding clause/evidence instructions, and the same neutralization posture.
2. Make `_run_rubric_step()` use the approved repo snapshot cwd when grounded, mirroring `run_round()`.
3. Fix chair projection by reusing `choose_chair_seat()` for run-card display, and make `choose_chair_seat()` reject ambiguous bare provider names even for direct callers.
4. Add recipe replay drift warnings/checks for both rubric template shas.
5. Add tests for `--rubric --revise`, `--rubric --repo`, duplicate-provider dry-run chair display, direct ambiguous `choose_chair_seat`, and actual recomputation of the printed combined egress hash.

**Invariants And Guardrails**
Keep the new proposal-blob consent invariant, the `approval.round1_hash` subhash, no artifacts before egress approval, chair-with-proposals-only, partition exactly-once, no empty subsumes, and integer weights summing exactly 100. Add a new invariant: “rubric proposal context equals the real round-1 review context except for the task-specific reply contract.”

**Risks And Missing Evidence**
I did not rerun the suite in this read-only review. The test suite has no visible `--rubric --revise` or `--rubric --repo` coverage. The egress test comment says the printed hash equals the combined hash, but the test only regexes a hash and checks files exist ([tests/test_run_board.py](skills/advisory-board/tests/test_run_board.py:15505)). The no-rubric byte-identity tests mostly assert absence of rubric strings/artifacts, not golden byte equality.

**Ask Other Seats To Challenge**
Ask Claude to decide whether “full source packet” contractually includes revision and repo-grounding context. Ask Gemini to challenge the user-facing consent/run-card mismatch and replay drift story. Ask both to inspect whether proposal prompts should also carry seat lens, since current rubric proposals are not seat-specialized.

VERDICT: block

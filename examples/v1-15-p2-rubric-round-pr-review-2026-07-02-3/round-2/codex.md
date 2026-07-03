**1. Updated Verdict**
Block, high confidence.

What would change it: make rubric proposal spawns receive the same composed data surface as round 1 for `--revise` and `--repo`, use the grounded snapshot cwd, and add composed-mode tests proving it.

**2. Changed / Dissent**
Changed toward Claude on the plain `--rubric` consent-hash fix: [cli.py](skills/advisory-board/scripts/_conductor/cli.py:288) now folds round-1 and rubric proposal blobs into the approved hash, and [cli.py](skills/advisory-board/scripts/_conductor/cli.py:714) reasserts it before rubric egress.

Still dissent from Claude’s SHIP: the fix binds the rubric prompt bytes, but those bytes are not the same composed packet as round 1 in repo-grounded and revise runs.

Still agree with Codex round-1 blocker: rubric proposals are built from `config.source.text` only, not the full round-1 packet surface.

**3. Strongest Remaining Objections**
Blocker: rubric proposals omit `--revise` context. Round 1 uses `config.revision.material` in [egress.py](skills/advisory-board/scripts/_conductor/egress.py:101) and injects it via [prompts.py](skills/advisory-board/scripts/_conductor/prompts.py:340). Rubric proposals use only `config.source.text` in [rubric.py](skills/advisory-board/scripts/_conductor/rubric.py:776). Failure scenario: a revised-draft run needs criteria about whether prior blockers were actually cleared; the rubric is minted without that prior verdict/diff context.

Blocker: rubric proposals do not get the repo-grounded execution surface. Round 1 adds the repo clause in [prompts.py](skills/advisory-board/scripts/_conductor/prompts.py:152) and runs seats from `config.grounding.snapshot_dir` in [rounds.py](skills/advisory-board/scripts/_conductor/rounds.py:235). Rubric uses a tempdir or `None` in [cli.py](skills/advisory-board/scripts/_conductor/cli.py:735), then spawns proposals with that workdir in [rubric.py](skills/advisory-board/scripts/_conductor/rubric.py:993). Failure scenario: a repo-grounded review asks seats to inspect code, but the pre-round rubric criteria are proposed without access to the frozen repo snapshot.

Concern: duplicate-chair display can lie in the run card. Actual default chair picks first `claude` in [rubric.py](skills/advisory-board/scripts/_conductor/rubric.py:368), but run-card projection uses a by-name dict in [artifacts.py](skills/advisory-board/scripts/_conductor/artifacts.py:170), which collapses duplicate providers to the last one.

**4. Recommended Execution Sequence**
1. Factor a shared “review context” builder used by both round 1 and rubric proposal prompts: source material plus repo-grounding clause plus revision context.
2. In `_run_rubric_step`, mirror `run_round` workdir selection for grounded runs: use `config.grounding.snapshot_dir`, not a fresh empty tempdir.
3. Add tests for `--rubric --revise` and `--rubric --repo` proving proposal prompts and spawn cwd match the round-1 context.
4. Fix run-card chair projection to call the same unique-id logic as execution, and add a duplicate-provider dry-run test.
5. Then rerun the full suite.

**5. Invariants And Guardrails**
Keep the already-good invariants: conductor-minted `pN`/`cN`, exact partition coverage, no phantom/double claim, non-empty subsumes, chair mechanical checks inside retry, and weights summing exactly 100.

Add this guardrail explicitly: rubric proposal fan-out must see the same data surface as round 1 for every composable mode, including `--repo` and `--revise`.

**6. Risks / Missing Evidence**
I did not run the full suite because this seat is read-only. I also found no composed rubric tests by search for rubric+repo or rubric+revise patterns in `tests/test_run_board.py`.

The reported 1499 OK is therefore unverified here, and even if true it does not cover the main composed-mode failure.

**7. Concrete Evidence**
`build_packet()` composes round-1 prompts with `revision_material` and `grounded=config.grounded`: [egress.py](skills/advisory-board/scripts/_conductor/egress.py:95).

`build_rubric_proposal_prompt()` only formats `source_material=neutralize_rubric_markers(config.source.text)`: [rubric.py](skills/advisory-board/scripts/_conductor/rubric.py:771).

Grounded round execution uses snapshot cwd: [rounds.py](skills/advisory-board/scripts/_conductor/rounds.py:226). Rubric proposal execution does not: [cli.py](skills/advisory-board/scripts/_conductor/cli.py:735).

BASIS: independent
VERDICT: block

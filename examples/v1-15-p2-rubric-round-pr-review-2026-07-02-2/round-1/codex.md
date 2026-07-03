**1. Verdict**

Block, high confidence. I would change this to caution once the rubric proposal prompts are hash-bound in the egress packet and chair mechanical invalid replies retry once before refusal.

**2. Strongest Objections**

- `scripts/_conductor/egress.py:95-111`, `scripts/_conductor/cli.py:287-288`, `scripts/_conductor/cli.py:673-688` — blocker: rubric proposal prompts are spawned outside the approved packet hash. `build_packet()` only builds round-1 prompts, the egress hash is computed from those blobs, then `_run_rubric_step()` builds and sends new full-source rubric prompts later. Failure scenario: a hash-bound non-public `--rubric` run sends `prompts/rubric-*.prompt` with full source to external providers even though the approved manifest/hash only covered `*-round-1.prompt`.

- `scripts/_conductor/rubric.py:1000-1036` — blocker: chair merge partition/weight failures are not retried. The loop retries JSON parse failures, then breaks before `build_rubric()` performs partition and weight validation. Failure scenario: chair first returns weights summing to 99 or misses `p7`; a second attempt could fix it, but the run refuses immediately, contrary to the contract’s reject-and-retry posture.

- `scripts/_conductor/recipe.py:330-336`, `scripts/_conductor/cli.py:708-713`, `scripts/_conductor/artifacts.py:728-729` — concern: default chair selection is not replay-exact. The recipe is written before proposals and records `chair_seat: null` when defaulted, but the actual default can depend on “first usable proposal.” Failure scenario: `--board codex,gemini --rubric` where codex drops and gemini chairs; replay may choose codex if codex is usable.

- `scripts/_conductor/rubric.py:328-339` — concern: `choose_chair_seat()` still has a by-name dict fallback that collapses duplicate providers. Normal CLI config resolves this earlier, but the exported function violates the D16 shape. Failure scenario: direct/programmatic `preferred="claude"` on `claude,claude,codex` silently picks the last claude instead of refusing ambiguity.

- `scripts/_conductor/config.py:528-565`, `scripts/_conductor/recipe.py:333-336` — concern: rubric template hashes are recorded but not checked for replay drift. Failure scenario: a later rubric template edit makes `--from-recipe` emit different proposal/chair prompts without the warning currently provided for main prompt templates.

**3. Recommended Execution Sequence**

1. Fix egress first: prebuild rubric proposal `PacketBlob`s before approval, list them in the manifest, include them in the approved hash discipline, write them before spawn, and reassert their hash at rubric spawn time.
2. Move chair `build_rubric()` and schema validation into the retry loop; treat model-authored partition/weight/schema rejection as `InvalidOutput` for attempt 1.
3. Persist the resolved chair seat for exact replay, or make the default chair deterministic before recipe write.
4. Remove by-name ambiguity from `choose_chair_seat()` itself.
5. Add tests that prove rubric prompts are in `egress-manifest.md`, the content hash changes with rubric prompt bytes, bad partition/weight attempts retry twice, and no-claude default-chair recipes replay the same chair.

**4. Invariants And Guardrails**

Every spawned prompt that can leave the machine must be in a consented packet hash. Rubric must run after egress approval and before round 1. No round artifacts or verdict may exist after rubric refusal. Proposal IDs stay conductor-minted, dense, and board-order deterministic. Chair selection must be on seat ID, never ambiguous provider name. Partition coverage and integer weights summing to exactly 100 remain hard gates. No stale `rubric.json` may coexist with `rubric-rejected.json`.

**5. Risks, Stale Assumptions, Missing Evidence**

The “no new consent category” claim is not enough for hash-bound consent; exact outbound bytes matter. The reported 1484 OK suite does not prove the egress invariant because tests check artifact existence, not approval packet membership. The mocks are deterministic and hide default-chair replay drift. I did not rerun tests in this read-only review.

**6. Concrete Evidence**

`write_pre_spawn_artifacts()` says it persists “the APPROVED packet” before spawn and writes only `blobs` at `scripts/_conductor/artifacts.py:716-744`; rubric prompt files are instead written after `run_rubric_proposals()` returns at `scripts/_conductor/cli.py:680-688`.

The chair loop states “mechanical checks are NOT retryable” at `scripts/_conductor/rubric.py:1019-1020`, while the contract says discrepancies should be invalid/retryable once.

The tests for bad chair weight and partition only assert refusal/no round at `tests/test_run_board.py:15168-15190`; only missing-fence asserts `attempts: 2` at `tests/test_run_board.py:15200-15210`.

**7. Ask Other Seats To Challenge**

Ask security to attack the egress hash model. Ask correctness to challenge retry classification for model-authored structural failures versus conductor internal errors. Ask test strategy to add non-deterministic/default-chair replay cases. Ask API/state-surface to decide whether recipe files may be updated after chair selection or need a separate resolved-run record.

VERDICT: block

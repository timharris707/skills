```json
{
  "verdict": "block",
  "confidence": "low",
  "blockers": [
    {
      "title": "Rubric proposals are not built from the same composed packet as round 1 under `--repo` / `--revise`",
      "body": "Both seats independently confirmed that rubric proposal prompts are formed from `config.source.text` only. Under `--repo`, round-1 seat prompts carry the repo-grounding clause and run from the frozen snapshot cwd (grounded=True), while the rubric proposal has no grounding placeholder, runs in an empty ephemeral tempdir, and never passes `grounded=`. Under `--revise`, round-1 embeds the prior-verdict digest and source diff; the rubric proposal embeds none. The board therefore proposes criteria against strictly less than it will review, it degrades silently rather than refusing, and no test exercises either composition. Codex holds this a block (the rubric is the foundation P3 will score against; a revised or repo-grounded review needs criteria informed by that context). Claude holds it a caution — inert in P2 (rubric.json is written but not injected or scored until P3/P4) and cheaply fixable — but agrees the composition fix is required before the change is sound.",
      "evidence": [
        { "kind": "code", "path": "scripts/_conductor/rubric.py", "line": 776 },
        { "kind": "code", "path": "scripts/_conductor/prompts.py", "line": 152 },
        { "kind": "code", "path": "scripts/_conductor/prompts.py", "line": 340 },
        { "kind": "code", "path": "scripts/_conductor/rounds.py", "line": 235 },
        { "kind": "code", "path": "scripts/_conductor/cli.py", "line": 735 },
        { "kind": "code", "path": "scripts/_conductor/rubric.py", "line": 993 },
        { "kind": "judgment", "detail": "No test exercises `--rubric --repo` or `--rubric --revise`; Codex found none by search, and Claude confirms TestRubricE2E (tests/test_run_board.py, ~15244-15460) covers no composed path." }
      ]
    }
  ],
  "dissent": [
    {
      "who": "Claude",
      "body": "Dissents from Codex's block on severity. The composition gap is inert in P2 — rubric.json is written but not injected into rounds or scored until P3/P4, so a thinner rubric has zero effect on a P2 run's rounds or verdict. It is a strict-subset egress (source text only, no snapshot access), the consent hash covers it, and it does not crash (round1_hash reconstruction verified sound). Block would discard a large, high-quality change over a bounded, currently-inert, cheaply-fixable gap; caution with a required composition fix is the proportionate call."
    },
    {
      "who": "Codex",
      "body": "Holds block against Claude's caution. The consent-hash fold binds the rubric prompt bytes, but those bytes are not the same composed packet as round 1 in repo-grounded and revise runs. Proposals are minted without the prior-verdict/diff context a revised-draft run needs, and without access to the frozen repo snapshot a grounded run reviews against, so the guardrail that rubric fan-out must see the same data surface as round 1 for every composable mode is not met."
    }
  ],
  "concerns": [
    {
      "title": "Code prose overclaims equivalence with the round-1 packet",
      "body": "The rubric.py module docstring and the cli.py:288-301 comment assert the proposal egresses the same content as the round-1 packet. This is true for the plain path but misleading under grounding/revision: the consent claim (subset egress) is fine, but the equivalence claim is not. Scope the wording to 'source text only; grounding/revision context is not carried into the rubric pass.'",
      "evidence": [
        { "kind": "source", "url": "scripts/_conductor/rubric.py", "quote": "the same content the round‑1 packet already egresses under the run's existing disclosure, so there is no new consent category" },
        { "kind": "code", "path": "scripts/_conductor/cli.py", "line": 288 }
      ]
    },
    {
      "title": "Run-card chair projection can display a different chair than execution uses",
      "body": "The actual default chair picks the first `claude` seat, but the run-card projection uses a by-name dict that collapses duplicate providers to the last one — so with duplicate providers the run card can show a chair that does not match execution.",
      "evidence": [
        { "kind": "code", "path": "scripts/_conductor/rubric.py", "line": 368 },
        { "kind": "code", "path": "scripts/_conductor/artifacts.py", "line": 170 }
      ]
    },
    {
      "title": "Partition invariant is implemented twice",
      "body": "The partition invariant lives in rubric.py reconcile_partition (write-time) and in an independent inline re-check in board_rubric.validate. Correct defense-in-depth for a standalone validator, but two paths that must stay in lockstep; a future edit to one and not the other silently weakens the last gate. Have the validator call reconcile_partition, or add a parity test.",
      "evidence": [
        { "kind": "code", "path": "scripts/_conductor/rubric.py", "symbol": "reconcile_partition" },
        { "kind": "code", "path": "scripts/board_rubric.py", "symbol": "validate" }
      ]
    },
    {
      "title": "Zero-weight merged criteria are accepted",
      "body": "_validate_chair_weight and board_rubric allow weight == 0 provided the sum is 100. A criterion the board weights at nothing is a soundness smell; require weight >= 1.",
      "evidence": [
        { "kind": "judgment", "detail": "_validate_chair_weight and board_rubric accept weight == 0 as long as weights sum to exactly 100; a zero-weighted merged criterion is a soundness smell." }
      ]
    },
    {
      "title": "Several validator tests assert only that the doc dies, not why",
      "body": "test_proposal_ids_must_be_dense_sequence concedes in its own comment that 'a phantom would trip first,' yet asserts only self._dies(d), so it would pass even if the dense-id check never ran. The unicode-confusable tests correctly pin 'phantom'; tighten the rest where a specific invariant is the point.",
      "evidence": [
        { "kind": "code", "path": "tests/test_run_board.py", "symbol": "test_proposal_ids_must_be_dense_sequence" },
        { "kind": "source", "url": "tests/test_run_board.py", "quote": "a phantom would trip first" }
      ]
    }
  ],
  "caveats": [
    "Neither seat executed the full test suite (both are read-only); the reported 1499-OK total is unverified. Claude confirmed the +73 new-test count statically, not by running the suite.",
    "Even if the suite passes, it does not cover the composed-mode failure — there are no `--rubric --repo` or `--rubric --revise` tests."
  ],
  "open_questions": [
    "Is source-only rubric proposal the intended P2 behavior — in which case grounding/revision context is deliberately excluded and must be documented and tested — or should `--rubric` refuse to compose with `--repo`/`--revise`/`--endorse` until it carries the same packet?"
  ],
  "next_actions": [
    "Decide the P2 composition policy before merge: either guard-and-refuse `--rubric` combined with `--repo`/`--revise`/`--endorse` (mirroring the existing `--chair-seat`=>`--rubric` guard in resolve_config) with a test asserting EXIT_USAGE, or treat source-only rubrics as intended and factor a shared 'review context' builder feeding both round 1 and rubric proposals.",
    "If source-only is not intended, mirror run_round workdir selection in _run_rubric_step for grounded runs — use config.grounding.snapshot_dir, not a fresh empty tempdir.",
    "Add composed-mode tests for `--rubric --repo` and `--rubric --revise` proving the proposal prompts and spawn cwd match the round-1 context (or, if source-only, that the rubric is source-derived).",
    "Rewrite the two overclaiming docstrings (rubric.py module docstring, cli.py:288-301 comment) to scope equivalence to source text only.",
    "Fix run-card chair projection (artifacts.py:170) to use the same unique-id logic as execution (rubric.py:368) and add a duplicate-provider dry-run test.",
    "Run the full suite on a clean checkout.",
    "Optional low-severity cleanups: require weight >= 1; collapse or parity-test the duplicated partition invariant; pin the death-only validator tests to their specific check."
  ]
}
```

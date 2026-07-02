**Updated Verdict**

CAUTION, high confidence. I would move to SHIP if the design adopts stable finding references, diff reconciliation, clean applyable draft artifacts, atomic `changes` pointer writes, and parallel endorsement fan-out.

**Changed / Still Dissent**

Changed because of Claude: truncation is now a blocking Q5 concern for me. A one-spawn full rewrite is acceptable only with source-size preflight, strict fence parsing, and a mechanical original-to-revised diff reconciliation that rejects unaccounted edits.

Changed because of Gemini: Q6 should not be a sequential endorsement loop. Keep endorsement ON by default, but fan out non-revision endorsement seats in parallel and record failed endorsement spawns as `ABSTAIN`/dropped rows.

Still dissent with Claude on Q2: I still prefer `changes.json` plus a tiny conductor-written `verdict.json.changes` pointer, because the current schema/docs explicitly reserved `changes` for this feature. But it must be written with the same lost-update discipline as `amend`; file-only is the fallback if that cannot be made race-safe.

Still dissent with the Q1 strawman: exact titles alone are too weak for machine provenance. Use conductor-assigned finding ids now, or at minimum `{list, index, title}` with duplicate-title rejection.

**Q Status**

Q1 CAUTION: no title-only mapping.  
Q2 SHIP with guardrails: file + pointer, atomically written, non-circular verdict pin in `changes.json`.  
Q3 CAUTION: schema shape is close, but `resolves` should target blockers/concerns only; line locators need diff-hunk reconciliation.  
Q4 SHIP: heuristic + explicit `--source-type`, with unknown/stdin requiring the flag.  
Q5 CAUTION: one spawn only with size/truncation/diff checks.  
Q6 SHIP if endorsement is ON by default and parallelized.  
Q7 SHIP: conflicts become `unresolved`, no content-based exit-code change.  
Q8 CAUTION: require `verdict.json`, but do not put metadata headers inside clean revised drafts.

**Strongest Remaining Objections**

1. Title-only edit identity can misbind edits when titles duplicate or drift.
2. A valid-looking partial rewrite could become the “fixed copy” unless diff reconciliation is mandatory.
3. The proposed `revised-draft.md` header makes the clean draft not clean; put run metadata in `changes.json`, HTML, or `revision/README.md`.
4. The brief’s `caveats` language does not match the implementation’s verdict-moving containers.
5. Sequential endorsements would make the default path slow enough that users will opt out, undercutting the “board-endorsed” claim.

**Recommended Execution Sequence**

1. Lock D9 decisions first: finding reference format, Q2 pointer semantics, actual `changes@1` containers, clean-draft rule, endorsement default.
2. Add CLI/config/recipe plumbing: `--output revised-draft`, `--source-type`, `--no-endorse`, and resolve-time refusal unless synthesis is available.
3. Build `changes@1` validator and revision spawn by generalizing synthesizer substrate.
4. Add diff reconciliation before writing accepted artifacts.
5. Write clean draft, patch/redline view, `changes.json`, and only then atomically add the `verdict.json.changes` pointer.
6. Add parallel endorsement fan-out and record per-edit positions.
7. Cover duplicate titles, conflicting findings, unknown source type, truncation, rejected revision output, stale artifact races, and no-flags byte identity in tests.

**Invariants And Guardrails**

No source file is ever modified. No metadata is inserted into the clean revised draft. Models never mint shas, ids, statuses, provenance, or verdict pointers. Every blocker is either resolved or listed in `unresolved`; concerns are best-effort; dissent and caveats are not editable findings. Every edit maps to a real finding reference and to a mechanical diff hunk or legal insertion anchor. Revision failure preserves successful rounds and exits 0 by default, with strict mode affecting only pipeline failure. Endorsement objections are recorded, not resolved by another model loop.

**Risks / Missing Evidence**

The design still needs a source-size/output-budget policy for full-file rewrites. URL wording should be tightened because URL sources are currently refused rather than fetched. Recipe validation will need new enum coverage for `output`/`source_type`. The redline renderer is genuinely new machinery, so golden tests need to include changed words, changed lines, insertions, deletions, HTML escaping, and unchanged large sections.

**Concrete Evidence**

- [board_verdict.py:45](skills/advisory-board/scripts/board_verdict.py:45) defines evidence containers as `blockers`, `dissent`, `concerns`; [board_verdict.py:525](skills/advisory-board/scripts/board_verdict.py:525) makes `amend --on` title-match only blockers/concerns.
- [board_verdict.py:142](skills/advisory-board/scripts/board_verdict.py:142) rejects any current `changes` key; [references/verdict-schema.md:138](skills/advisory-board/references/verdict-schema.md:138) reserves it for v1.13.
- [cli.py:705](skills/advisory-board/scripts/_conductor/cli.py:705) has only the three current `--output` choices; [config.py:427](skills/advisory-board/scripts/_conductor/config.py:427) merely stores the resolved value.
- [config.py:52](skills/advisory-board/scripts/_conductor/config.py:52) shows `SourceSpec.kind` is `path|url|stdin`; [config.py:155](skills/advisory-board/scripts/_conductor/config.py:155) refuses URL fetching.
- `rg` found no `get_opcodes`/`HtmlDiff`; current diff use is `SequenceMatcher` for verdict delta and `unified_diff` for revise context.
- [cli.py:576](skills/advisory-board/scripts/_conductor/cli.py:576) preserves rounds on synth failure; [tests/test_run_board.py:7531](skills/advisory-board/tests/test_run_board.py:7531) protects prior `verdict.json` from parse-failure reruns.

VERDICT: caution

# Advisory Board — Final Consensus
v1.13 fixit revision artifact design brief
Board: Claude (Architecture & systems/claude-opus-4-8) · Codex (Implementation & testing/gpt-5.5) · Gemini (Product & operations/gemini-3.5-flash). Rounds: 2.

## Verdict: SHIP WITH CHANGES — unanimous (high confidence)

## Consensus blockers (must fix before ship)
1. Title-only edit identity is ambiguous by construction (Q1) — All three seats moved off pure title matching for the revision's `resolves` join key. Unlike the human-in-the-loop `amend`, `changes.json` is machine provenance with no human to disambiguate, and there is no duplicate-title guard anywhere: `_finding_titles` appends every finding title unconditionally and covers only blockers+concerns. Two same-titled findings make an edit's `resolves` ambiguous with nothing to break the tie. Board minimum is a composite `{list, index, title}` with a conductor equality-assert / duplicate-title rejection (Claude, Codex); Gemini would go further to conductor-assigned sequential IDs.
   - evidence: `scripts/board_verdict.py:525` (code) — unverified
   - evidence: `scripts/board_verdict.py:528` (code) — unverified
   - evidence: judgment — No duplicate-title guard exists anywhere in the codebase, and changes.json (machine-authored) has no human to disambiguate a collision.
2. `caveats` is a phantom container the schema must be fixed against (Q3) — The brief and Q3 treat `caveats[]` as structured, resolvable findings (blockers/concerns/caveats), but the implementation's evidence containers are blockers/dissent/concerns, and caveats are plain string arrays with no titles or evidence — un-resolvable by construction. Every `resolves.list` enum, the completeness rule, and the best-effort carve-out inherit this error. The vocabulary must be reconciled (`caveats`→`dissent`) before any schema line is written, or the validator and the artifact disagree on day one. Codex and Gemini restrict resolvable findings to blockers+concerns; Claude's enum also admits dissent.
   - evidence: `scripts/board_verdict.py:45` (code) — unverified
   - evidence: `scripts/verify_evidence.py:107` (code) — unverified
   - evidence: references/verdict-schema.md — “Reviewed the plan, not the code...” (source) — verified
3. Silent truncation ships a corrupted "board-endorsed" copy (Q5) — Claude's highest-severity failure and a top objection for all three seats: a single-spawn full-file rewrite of a large source can truncate and produce a plausible-looking short reply that gets written as the "fixed copy." The retry set only catches timeout, not truncation. Defense must be layered: strict fence parsing (an opened DATA fence with no matching close ⇒ reject/retry), a mechanical original→revised diff reconciliation (every edit locator maps to a real diff hunk 1:1; status computed from the diff, never model-asserted), and a source-size preflight that refuses oversized `--output revised-draft` loudly rather than truncating. Gemini proposes emitting the JSON mapping first and the draft second so a missing closing fence is caught mechanically.
   - evidence: judgment — One-spawn full rewrite can silently truncate into a valid-looking partial; without size preflight + strict fence parsing + diff reconciliation the short output becomes the board-endorsed applied copy.
4. Metadata header inside the clean revised draft corrupts the applied artifact (Q8) — The strawman's `revised-draft.*` carries a header (run title, seat, unresolved count). But that artifact is the thing a human applies — a header prepends board metadata to the user's document, and for code produces a syntax-corrupt or semantically-wrong file the moment it is saved. All three seats agree the draft must be byte-clean; metadata belongs in `changes.json`, the HTML handoff, and the run card, never in the applied file. Its sha256 in `changes.json.revised` must match the file on disk exactly.
   - evidence: judgment — revised-draft.<ext> with a tool-authored header is not directly apply-able and, for code sources, is corrupt on save; metadata must live outside the applied bytes.
5. Sequential endorsement makes the default path slow and self-defeating (Q6) — The board converged on endorsement ON by default (otherwise "board-endorsed" becomes marketing and one seat's rewrite wears the whole board's name), but it MUST be dispatched concurrently. Gemini's round-1 "+40–60%" is a spawn/token-cost figure miscast as latency; the endorsement pass is a dependency-free per-seat fan-out — structurally a review round — and rounds already fan out concurrently, so reused its wall-clock cost is ~one extra round, not N sequential spawns. `--no-endorse` remains the opt-out for the genuine token-cost axis.
   - evidence: `scripts/_conductor/rounds.py:232` (code) — unverified

## Hard dissent (preserved)
- Gemini: On Q2, dissents from any design that reopens and appends `verdict.json` to add the `changes` pointer. Argues the run is a single-process pipeline, so the verdict should be held in memory and `verdict.json` written to disk once at the very end (after synthesis, revision, and parallel endorsements), never reopened — keeping it a self-contained, cryptographically verifiable index. Claude and Codex instead reuse `amend`'s atomic lost-update guard, noting `amend` already reopens verdict.json post-synthesis so write-once is already gone.
- Claude: On Q1, prefers the composite `{list, index, title}` locator with a conductor equality-assert and declines Codex's stronger option of minting a real `id` on verdict@2, calling it premature — a second schema evolution in two releases for a within-run consumer. Codex favors conductor-assigned finding IDs now (composite as the minimum fallback); Gemini favors conductor-assigned sequential string IDs (`blocker-1`, `concern-2`).
- Claude: On the scope of resolvable findings, Claude's changes@1 enum allows `resolves.list ∈ {blockers, dissent, concerns}`, treating dissent findings as resolvable, and acknowledges this goes beyond the amend precedent. Codex and Gemini restrict resolvable findings to blockers+concerns only — "dissent and caveats are not editable findings."

## What the board couldn't verify
- Claude did not audit amend's lost-update guard mechanism this round — whether it covers both the amend writer and the revision pointer-writer is a Phase-2 task, not yet verified.
- The claim that amend sets the join-key precedent is only 2/3 true: amend's _finding_titles covers blockers+concerns, not dissent — so resolving dissent findings would go beyond the amend precedent.
- `scripts/board_verdict.py:525` (code) could not be resolved.
- `scripts/board_verdict.py:528` (code) could not be resolved.
- `scripts/board_verdict.py:45` (code) could not be resolved.
- `scripts/verify_evidence.py:107` (code) could not be resolved.
- `scripts/_conductor/rounds.py:232` (code) could not be resolved.
- `scripts/_conductor/config.py:52` (code) could not be resolved.
- `scripts/_conductor/config.py:155` (code) could not be resolved.
- `rg 'get_opcodes|HtmlDiff'` (command) could not be re-executed (off-allowlist or not runnable).
- `scripts/_conductor/revise.py:259` (code) could not be resolved.
- `scripts/_conductor/delta.py:15` (code) could not be resolved.
- `scripts/board_verdict.py:142` (code) could not be resolved.
- `references/verdict-schema.md:138` (code) could not be resolved.
- `scripts/board_verdict.py:535` (code) could not be resolved.

## Open questions
- Q1 join-key format is unsettled: composite {list, index, title} with equality-assert vs conductor-assigned sequential IDs vs a real id on verdict@2.
- Q2 write-safety mechanism is unsettled: reuse amend's atomic lost-update guard (reopen/append) vs a late-write pipeline that writes verdict.json once at the end and never reopens it.
- Whether the revision step may resolve dissent findings, or only blockers+concerns.

## Next actions
- Pre-work (blocking, no code): reconcile `caveats`→`dissent` across the brief + schema, and lock the D9 decisions — Q1 join-key format, Q2 pointer/write semantics, changes@1 containers, clean-draft rule, and endorsement default — before authoring changes@1.
- Adopt a non-title edit identity: composite {list, index, title} with a conductor equality-assert / duplicate-title rejection (or conductor-assigned finding IDs).
- Restrict `resolves.list` to real evidence containers; drop caveats (plain string arrays) from the resolvable set.
- Build the advisory-board/changes@1 schema and its own strict validator (mirroring board_verdict.py); limit model-authored fields to summary/resolves/note, with the conductor computing n, status, shas, and validating locators.
- Generalize the synthesizer spawn path into _run_revision_step() after _run_synthesis_step(); single spawn with a DATA fence + neutralizer.
- Add a source-size preflight that loudly refuses oversized `--output revised-draft`, plus strict fence parsing (unclosed fence ⇒ reject/retry).
- Add mechanical original→revised diff reconciliation (INV-1): every edit locator maps 1:1 to a real diff hunk; status "applied" is conductor-computed from the diff, never model-asserted; reconciliation failure ⇒ reject path.
- Emit a byte-clean revised-draft.* with no metadata header; its sha256 in changes.json.revised must match the file on disk.
- Parallelize the endorsement pass on the rounds.py ThreadPoolExecutor; keep it ON by default with a `--no-endorse` opt-out; record per-edit ENDORSE/OBJECT/ABSTAIN (and treat `unresolved` entries as endorsement targets).
- Write the verdict.json.changes pointer atomically (amend's lost-update discipline or late-write) with an acyclic pin: verdict → changes → {source, revised}.
- Add CLI/config/recipe plumbing: `--output revised-draft`, `--source-type`, `--no-endorse`, resolve-time refusal unless synthesis is available, and new recipe enum coverage for output/source_type.
- Cover in tests: duplicate titles, conflicting findings, unknown source type, truncation, rejected revision output, stale-artifact races, no-flags byte identity, and redline golden files.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

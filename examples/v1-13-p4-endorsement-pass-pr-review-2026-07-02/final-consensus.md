# Advisory Board — Final Consensus
v1.13 p4 endorsement pass pr review
Board: Claude (Architecture & systems/claude-opus-4-8) · Codex (Implementation & testing/gpt-5.5). Rounds: 2.

## Verdict: DO NOT SHIP YET — split board (low confidence)

## Consensus blockers (must fix before ship)
1. Run-card endorsement count is name-axis and undercounts duplicate-provider boards — Both seats agree this is a real, in-scope defect. The run card projects the endorsement-seat count by provider name (`n_endorse = sum(1 for s in config.board if s.name != chosen)`, with `chosen` a name), while the pass itself excludes the reviser correctly by unique id (`s.id != revision_seat_id`). On `--board claude,claude,codex` the card shows 1 endorsement seat but the pass actually runs 2 (`claude#2` + `codex`). Claude calls it the one surface where the PR's own 'id-axis completeness' is incomplete; Codex lists it first. One-line fix.
   - evidence: `scripts/_conductor/artifacts.py:141` (code) — unchecked
   - evidence: `scripts/_conductor/artifacts.py:121` (code) — unchecked
   - evidence: `scripts/_conductor/endorsement.py:188` (code) — unchecked
2. Per-seat --timeout is not honored in the endorsement fan-out — Both seats agree (Claude adopted this from Codex, upgrading its CAUTION count to three). `cli.py._run_endorsement_pass` passes `timeout=revision_seat.timeout_s` to every endorsement spawn, and `endorsement.py.run_endorsement` resolves `timeout if timeout is not None else adapter.timeout_s`, never consulting each endorsement seat's own `seat.timeout_s`. This diverges from the round fan-out's correct precedence. A documented per-seat override like `--timeout gemini=600` is silently ignored during endorsement; the seat runs on the reviser's clock and can time out, drop, and lose its vote. The bug only bites with per-seat overrides — a bare `--timeout 300` coincidentally masks it, and the added tests don't cover per-seat timeout.
   - evidence: `scripts/_conductor/cli.py:767` (code) — unchecked
   - evidence: `scripts/_conductor/endorsement.py:498` (code) — unchecked
   - evidence: `scripts/_conductor/rounds.py:105` (code) — unchecked
   - evidence: `scripts/_conductor/config.py:375` (code) — unchecked
3. Egress disclosure overclaims — 'no new egress' / 'already egressed' misnames what is sent — Both seats agree the wording overclaims; they split on severity. Multiple surfaces (runtime print, raw recorder, run card, `build_endorsement_prompt` docstring) state the endorsement seats already received these bytes, but the endorsement prompt sends the original source, revised draft, edits table, and unresolved table — and the revised draft is a new artifact to the endorsement seats (it was egressed to the revision seat). Codex holds this as materially inaccurate disclosure (block-weight). Claude downgrades it to CAUTION, arguing the substance is sound (no new exposure class — every endorsement seat already received the source in rounds per data-handling.md, the revised draft is a board-derived edit) and that the accurate framing is 'no new exposure class — board-derived from source already disclosed to these providers.' See dissent.
   - evidence: `scripts/_conductor/endorsement.py:252` (code) — unchecked
   - evidence: `scripts/_conductor/endorsement.py:253` (code) — unchecked
   - evidence: `scripts/_conductor/artifacts.py:145` (code) — unchecked
   - evidence: scripts/_conductor/endorsement.py — “revision derivatives the run already egressed” (source) — unchecked
4. Revision-seat selection and recording are provider-name based (duplicate providers cannot be disambiguated) — Codex objection carrying the block; a facet Claude records but defers. `--revision-seat` validates against registry/provider names, not ids, and `revision.py` builds `by_name = {s.name: s ...}`, which collapses duplicate providers — so on `--board claude,claude,codex`, `--revision-seat claude` is ambiguous and `claude#1`/`claude#2` cannot be selected. Relatedly, `changes.revision_seat` is recorded name-axis (`revision_seat=seat.name`) while `endorsements[].seat` carries unique ids, so the reviser is ambiguous in the same file on a duplicate-provider board. Claude flags the recording facet as pre-existing and 'not a blocker for this PR'; Codex treats the selection ambiguity as load-bearing for BLOCK.
   - evidence: `scripts/_conductor/config.py:662` (code) — unchecked
   - evidence: `scripts/_conductor/revision.py:273` (code) — unchecked
   - evidence: `scripts/_conductor/revision.py:1001` (code) — unchecked
   - evidence: `scripts/_conductor/revision.py:788` (code) — unchecked
5. Renderer byte-identity for the no-endorse path is not proven (endorsement CSS is unconditional) — Codex-only objection, directly contested by Claude. The no-endorse path removes the summary element, but the handoff template adds endorsement CSS unconditionally, so a literal P3 byte-identity claim is false unless the invariant is narrowed. The existing renderer test checks absence of `<div class="endorse-summary">`, not byte identity against a P3 render. Claude, by contrast, verified byte-identity for endorsement-less runs as 'CLEAN & test-enforced' — see dissent.
   - evidence: `references/handoff-template.html:348` (code) — unchecked

## Hard dissent (preserved)
- Claude: Holds CAUTION, dissenting from Codex's BLOCK. The design core is sound: pointer sha ≡ on-disk changes.json bytes on every branch (the anti-smuggling guard runs before the pass, writes happen after it returns, the re-validation-failure path fails safe), plus row-order determinism, parse atomicity, thread-safety, and the validator shape-vs-bounds split all verified clean. The three in-scope defects (run-card count, per-seat timeout, egress wording) are isolated, fail gracefully, and none touch the sha-pin. On egress, Claude argues BLOCK is too strong: the wording overclaims but the substance is sound — no new exposure class egresses, mirroring the reasoning data-handling.md already blessed for source-material.txt. On the renderer, Claude verified byte-identity for endorsement-less runs as CLEAN & test-enforced. What would have flipped Claude to BLOCK — a new-exposure-class leak, or any path where changes.json diverges from the pinned pointer bytes — does not exist.
- Codex: Holds BLOCK, dissenting from Claude's CAUTION. The defects are not just cosmetic: timeout behavior can mis-drop seats, duplicate-provider revision selection is ambiguous, and 'no new egress' overstates what is sent. Codex additionally asserts the renderer byte-identity is not proven because the template adds endorsement CSS unconditionally, making the literal P3 byte-identity claim false. Codex requires a patch fixing the duplicate-provider id-axis surfaces, endorsement per-seat timeouts, egress wording/consent honesty, and the no-endorse HTML byte-identity test gap before the verdict changes. It softened one prior point (does not require a brand-new consent architecture if project policy treats generated-derivative fan-out like round 2) but insists the disclosed wording must accurately name the material sent.

## What the board couldn't verify
- Neither seat re-ran the suite this pass (read-only); the claimed 1262 OK is unverified — Claude relied on the stated count plus a line-level trace, Codex explicitly did not run it.
- Byte-determinism of an OBJECT endorsement note carrying non-ASCII (e.g. é) or an embedded newline is untested; the existing pointer-sha test pins on-disk bytes only with ASCII notes (Claude).
- Current tests cover duplicate-provider execution rows but not the run-card projection or unique revision-seat selection (Codex); the renderer test checks absence of the summary element, not byte identity against a P3 render.

## Open questions
- Does project policy treat generated-derivative fan-out (the revised draft sent to the endorsement seats) under the same disclosure category as round-2 source egress? Codex softened its consent objection conditional on this, but maintains the disclosed wording must still accurately name the material sent.

## Next actions
- Fix the per-seat endorsement timeout to mirror rounds.py precedence (call-level override → seat.timeout_s → adapter cap); drop `timeout=revision_seat.timeout_s` in `_run_endorsement_pass`; add a test where a per-seat `--timeout` forces exactly that endorsement seat to drop while others vote.
- Project the run-card endorsement count on the id axis (compute the reviser id, count `s.id != chosen_id`); assert `--board claude,claude,codex` prints '2 non-revision seat(s)'.
- Make `--revision-seat` selection and `changes.revision_seat` id-axis so duplicate providers (claude#1/claude#2) can be selected and recorded unambiguously; add tests for `--board claude,claude,codex` (also cover revision artifact/log names).
- Rewrite the egress language across the four sites (runtime print, raw recorder, run card, docstring) plus a data-handling.md sentence to say the endorsement pass sends source plus generated revision/change artifacts under the existing disclosure category — not that the exact bytes were already egressed.
- Make the no-endorse HTML byte-identity real: move endorsement CSS into the populated RAW block or add a true P3 baseline byte test and narrow/adjust the invariant.
- Document or reconcile the changes.revision_seat axis in changes-schema.md (or record a revision_seat_id); defer a schema change.
- Add a byte-determinism test for an OBJECT note carrying non-ASCII (é) and an embedded newline, re-asserting the pointer pin.
- Re-run the focused new tests (must fail before the fix, pass after), then the full suite, confirming the claimed 1262 OK.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

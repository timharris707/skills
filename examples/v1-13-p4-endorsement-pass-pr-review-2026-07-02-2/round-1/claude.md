All three verification agents are back, and combined with my direct reads I have what I need. One agent flagged a "sha divergence risk" that I need to evaluate critically rather than accept — so let me settle that one point, then deliver the review.

The claim is that `changes_sha` (cli.py:946-948) is computed from a re-serialization (`json.dumps`) rather than the on-disk bytes. I read that code directly: it's `json.dumps(rr.changes, indent=2, ensure_ascii=False)+"\n"` hashed, versus `json.dump(rr.changes, handle, indent=2, ensure_ascii=False)+"\n"` written to a `newline="" , encoding="utf-8"` handle — the **same dict, same encoder, same params, same process**. `json.dump` and `json.dumps` share one `iterencode`; they cannot diverge for this input, and two tests read the disk bytes back and assert equality (including the exotic é+newline note). That "risk" is not real. I'll record the rebuttal so it isn't re-litigated.

Here is my review as the Claude seat.

---

# Claude seat review — v1.13 P4 endorsement pass (revised)

## 1. Verdict

**SHIP — confidence: HIGH.**

All five of my prior blockers are genuinely resolved (verified against the working tree, not the diff narrative), both "couldn't-verify" gaps are now closed by real tests, and the independent-finder MINOR is a sound validator tightening. The one item that is *not* addressed is the prior board's lone **concern** (orphan `endorsement/*.md` on the re-validation-failure branch), but it sits on an unreachable-by-construction path and is forensic-cosmetic — it does not gate v1.13.0.

*What would flip this to caution/block:* the full suite not actually green on a clean checkout (I did **not** execute it — see §5), OR a demonstration that the endorsement re-validation-failure branch is reachable with conductor-built rows (by construction it is not), OR evidence that `json.dump`→file and `json.dumps` can diverge for these bytes (they cannot; test-pinned).

## 2. Strongest objections (all non-blocking)

- **The prior CONCERN is still open, and "every item is addressed" overstates it.** In `_run_endorsement_pass` (cli.py), each seat's `endorsement/<seat>.md`+`.raw` are written *before* `_validate_changes_doc(candidate)`. On the failure branch the function returns early leaving `rr.changes["endorsements"]` as `[]`, so `changes.json` would claim `endorsements: []` while the per-seat files exist on disk. It's unreachable (the conductor builds rows from `_expected_targets`, which satisfy every tightened validator rule by construction), so I don't gate on it — but it was flagged last round and remains. Cheap fix: write the per-seat artifacts *after* re-validation passes, or drop/annotate them on the failure branch.
- **Pre-empting a false blocker on the pointer sha.** `changes_sha` (cli.py:946-948) is a re-serialization, not a file read-back. I verified this is **byte-safe**: identical object + `indent=2, ensure_ascii=False` + one process ⇒ `json.dump` and `json.dumps` emit the same bytes; the file uses `newline="", encoding="utf-8"` so no translation; `test_pointer_sha_matches_endorsement_bearing_changes_bytes` and `test_exotic_object_note_round_trips_byte_for_byte` hash the on-disk bytes and assert equality. Not a defect. Optional symmetry hardening: hash the file back via `board_verdict._file_sha256` (as the verdict pointer path does at cli.py:680/712) so the two integrity anchors read identically — purely cosmetic.
- **Sibling wording inconsistency from the blocker-3 fix.** The endorsement egress language was corrected honestly at all five sites, but the adjacent **revision-seat** run-card line still reads `"never written (D6); no new egress" / "(the revision seat sees only source the run already sent)"` (artifacts.py:143-144). The revision seat also receives the board-generated verdict/findings, so this carries the exact imprecision blocker 3 corrected for endorsement. Harmonize it for consistency (out of P4's declared scope, but it's the same defect class you just fixed one line above).

## 3. Recommended execution sequence

1. On a clean checkout: run the new focused tests (`TestEndorsement*`, the id-axis and exotic-note cases) and confirm **fail-before / pass-after**, then the full suite green (author reports **1279 OK** — confirm in CI, since I verified statically, not by execution).
2. *(Optional, cheap, this PR or immediate follow-up)* reorder the per-seat endorsement writes to after re-validation (closes the residual concern); harmonize the revision-seat egress line.
3. Tag `advisory-board/v1.13.0` and cut the release — this is the P4 capstone the milestone was gating on.

## 4. Invariants & guardrails (confirmed holding)

- **Pointer-sha coherence:** endorsement rows merged in place (cli.py:930) *before* the single `changes.json` write (943-945); sha computed over the same bytes (946-948); pointer written once (966-967). Verified across on/off/all-dropped/partial-drop by the merge-then-write ordering.
- **Model authors tokens, never rows:** anti-smuggling guard *before* the pass (cli.py:904-909) + conductor-built rows + strict `board_changes` validation (exactly one of `edit_n`/`unresolved_n`, enum position, `dropped` true-only, upper-bound + `(seat,kind,n)` dedup).
- **Body-only byte-identity:** genuinely pre-existing — documented "settled v1.12 P4, extended v1.13 P3" in render_handoff.py:45-50 with a *deliberate* head-CSS exemption. Not goalpost-moving; the empty `{{ENDORSEMENT_SUMMARY}}` proven to contribute zero body bytes.
- **Single seat-identity axis (`id`):** exclusion (`endorsement_seats` by `s.id`), rows, artifacts, prompts, logs, `changes.revision_seat`, and `--revision-seat` selection all key on the unique id; `id == name` on non-duplicate boards keeps single-provider artifacts byte-identical.
- **Timeout precedence identical to the round fan-out** (endorsement.py:502-512 == rounds.py:102-110), and `_run_endorsement_pass` passes no call-level timeout, so the reviser's clock is never imposed on voters.
- **Failure posture:** the pass never fails the run, discards the revision, or moves exit codes; deterministic row order (seats × targets).

## 5. Risks, stale assumptions, missing evidence

- **Test count is author-asserted, not executed by me** (read-only review). I verified the logic and the presence/shape of every new test; recommend CI confirm the 1279 green before tag.
- **Run-card count is a projection.** It agrees with the runtime reviser on the default duplicate-`claude` path (both collapse `by_name` to `claude#2`). It can *theoretically* diverge only on the "first-usable-seat-in-last-round" fallback where `claude` isn't seated — and that affects the **cosmetic count only**, never the actual exclusion (which uses the real `revision_seat.id`). Acceptable; worth a one-line comment noting the projection's limit.
- **Orphan-artifact path** (§2) — unreachable-by-construction, minor.
- **Cosmetic:** the upper-bound error string renders "there are 1 edit target(s)" (`board_changes.py`) — trivial grammar.

## 6. Concrete evidence

- `cli.py:930` pass runs before writes · `:943-948` single write + sha over same bytes · `:966-967` pointer once · `:904-909` guard placement · `:781-799` orphan region, in-place set at `rr.changes["endorsements"] = rows` (799).
- `endorsement.py:180-189` `endorsement_seats` excludes by `s.id`; `:502-512` timeout precedence; `run_endorsement_pass(..., timeout=None)`; `build_endorsement_prompt` neutralizes source + revised draft + edit/finding/note splices.
- `rounds.py:102-110` matching timeout precedence.
- `config.py:291-313` id assignment (`provider#N`, `id==name` when unique); `:406-431` `resolve_revision_seat_id` (id → unique-name → ambiguous-refuse-listing-ids → off-board refuse).
- `revision.py:280-296` `choose_revision_seat` id-first; `:1014` records `seat.id`.
- `artifacts.py:130-158` id-axis endorsement count + honest egress line.
- `render_verdict.py:40/209/617/1020` (`html`, `_flat`, `_nb`, `_esc` all in scope); `_flat` flattens the multi-line OBJECT note into one `<li>`.
- `render_handoff.py:45-50` documented invariant · `:125` `RAW_TOKENS` · `:210-215` empty-token drop (both sections) · `:287` backfill.
- `recipe.py:291-305` `endorse` recorded only for revised-draft runs (normal recipes byte-identical); `:381-382` type-validated.

## 7. What I'd ask the other seats to challenge

- **Codex (blocked last round):** independently confirm the `json.dump`↔`json.dumps` equivalence at cli.py:946-948 so the sha path is *not* re-raised as a blocker — do you agree it's byte-guaranteed for this input, or can you construct a divergence?
- **Whoever owns data-handling/consent:** re-audit that the endorsement packet splices *only* neutralized, board-already-egressed-category material, and that no user-facing surface calls a `--no-endorse` (findings-mapped) run "board-endorsed" (D13's marketing constraint) — check SKILL.md, CHANGELOG, run card, and the redline/patch section header for that leak.
- **Any seat:** should the residual orphan-artifact concern gate v1.13.0 or defer to a tidy-up? I say defer; argue me out of it if the failure path is reachable.

VERDICT: ship

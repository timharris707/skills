All three integration agents report clean, and I've verified both blocker-fix sites in the actual tree. I now have everything needed to finalize. Here is my review.

---

# Claude seat review — v1.15 P2 rubric round + chair merge (`--revise` pass)

## 1. Verdict

**SHIP** — confidence: **high.**

Both prior blockers are genuinely resolved in the actual working tree (not just claimed in the diff), all four concerns are addressed, and every cross-cutting integration point I was worried about checks out against real code. The residual items below are non-blocking P3 refinements, not merge gates.

One line on what would change it: if the stated suite (1499 OK) does not actually pass on a clean checkout — I trusted the reported count rather than running it — or if a seat demonstrates that the "settled" default-chair rule can wedge a run that had ≥2 usable proposals (see §2.3). Neither is a P2-scope correctness defect.

## 2. Did the prior blockers/concerns actually get fixed?

I verified each against the real files, not the diff's self-description.

**BLOCKER 1 — proposal bytes not in the consent hash → RESOLVED.**
- `cli.py:299-301`: `rubric_blobs = build_rubric_proposal_blobs(config) if config.rubric else []` / `egress_blobs = blobs + rubric_blobs` / `content_hash = packet_hash(egress_blobs)`. Confirmed in the live file.
- `egress.py:324`: `enforce_egress_gate` sets `content_hash = packet_hash(blobs)` on the blobs it's handed, and `cli.py:407` hands it `egress_blobs`. So consent binds the exact outbound proposal bytes (round-1 ∪ rubric-proposal), not a source proxy.
- Whole-packet re-assertion at `cli.py:714` before any rubric egress; per-seat rebuild-drift re-assertion inside `run_rubric_proposal` (fail-closed to `EXIT_EGRESS_BLOCKED`).
- Round-1 byte-binding preserved: `EgressApproval` is `@dataclass` (**not frozen**, `egress.py:129`), so `approval.round1_hash = packet_hash(blobs)` (`cli.py:416`) is a valid mutation; `rounds.py:202-203` checks `approval.round1_hash or approval.content_hash` and round 1 is spawned with the round-1 `blobs` (`cli.py:500`), not `egress_blobs`. The `or content_hash` fallback keeps the non-rubric path identical.
- The chair prompt is **legitimately** left out of the initial consent hash: `build_round2` (`egress.py:38-65`) already embeds peer reviews that were never in the original hash, and the content-hash guard is explicitly round-1-only (`rounds.py:210` "round 2+ packets are legitimate derivatives"). The chair merely follows that established precedent — verified, not asserted. Prior Concern 4 ("pins source transitively") was flagged *optional*; the chair now carries only proposals (no source afresh), so the residual is minimal.
- Tests pin it, not the implementation back to itself: `TestRubricConsentHash.test_rubric_proposal_blobs_are_in_the_consent_hash` asserts `packet_hash(round1+proposals) != packet_hash(round1)` (the fail-if-absent guard), and the E2E variant asserts each `prompts/rubric-<seat>.prompt` appears in the persisted `egress-manifest.md`.

**BLOCKER 2 — mechanical checks don't retry → RESOLVED.**
- `rubric.py:1130-1143` (verified in the real file): `build_rubric(...)` + `validate_rubric(...)` run **inside** the `for attempt in (1, 2)` loop; a `RubricRejected`/schema failure sets `reject_error`, and `if attempt == 1: continue` (retry) else `break` (refuse). Retry-then-refuse, one policy.
- Tests assert `attempts == 2` on both arms: `bad_weight`/`bad_partition`/`phantom`/`missing_fence` → 2 then refuse; the new `retry_once_then_ok` mock (with a `$MOCK_CHAIR_COUNTER` file proving the CLI spawned twice) → 2 then success. This is the retry-then-**recover** path the prior board asked for, and it's genuinely exercised.

**Concern 1 (disclosure silent) → RESOLVED.** `disclosure_line` gains a `config.rubric` branch naming the pre-round pass; `test_rubric_disclosure_names_the_pre_round_pass` asserts "rubric"/"proposal"/"chair" present on, absent off, plus an E2E check of the printed gate. CHANGELOG no longer overclaims a "purpose mention."

**Concern 2 (no dropped-provenance cross-check) → RESOLVED.** `board_rubric.py` builds a `provenance = {proposal_id: (seat, title)}` map from `proposals[]` and dies if a `dropped[]` entry's seat/title disagrees; `test_dropped_provenance_seat_must_match_proposal` / `_title_must_match` / `_matching_passes` pin both the reject and the no-false-positive direction.

**Concern 3 (by-name chair collapse on duplicate board) → RESOLVED.** `choose_chair_seat` default iterates board order for the first `claude`-provider seat (unique-id axis), and `test_default_claude_on_duplicate_board_is_deterministic_unique_axis` asserts `seat.id == board[0].id == "claude#1"`.

**Exit-code decision (in-scope to judge) → AFFIRMED.** Reusing `EXIT_PREFLIGHT_NOGO` is precedented: `cli.py:518` already returns that code *after* round-1 has spawned (post-egress) for the "one voice is not a board" floor. A rubric refusal — pre-verdict, nothing-to-protect — is the same bucket. A new constant would splinter it. Sound.

**D5/R5 byte-identity → HOLDS.** Verified the three drift risks I flagged: (a) `STAGES` is a doc-only export; `render_status_html` renders the *current* stage, never a checklist over the tuple, so a non-rubric `status.json`/`.html` is byte-identical; (b) the estimator's always-present `"rubric"` dict key is never `json.dump`'d anywhere — only `render_estimate` reads it, gated on `est.get("rubric")`; (c) `config_to_recipe` adds rubric keys only inside `if config.rubric:`, and every written key is read back in `resolve_config`, so non-rubric recipes are byte-identical and rubric recipes round-trip.

## 3. Strongest objections (all non-blocking)

1. **The partition invariant is implemented twice** — `rubric.py:reconcile_partition` (write-time) and an inline re-check in `board_rubric.validate` (last-gate). They agree today, but they're independent code paths; a future edit to one can silently drift from the other. This is defensible defense-in-depth (the standalone validator must not import conductor internals, mirroring `board_changes.py`), but there's no test that fuzzes the *same* inputs through both. Add one, or a cross-reference comment. **Maintainability, not correctness.**

2. **A zero-weight merged criterion is accepted.** Both `_validate_chair_weight` and `board_rubric` allow `weight >= 0`; a criterion at weight 0 passes as long as the set sums to 100. A criterion the board will later score at 0% is inert — arguably it should be dropped, not merged. The chair prompt says "INTEGER PERCENTAGE" but never forbids 0. Invariants (partition, sum-to-100) still hold, so this is a rubric-*quality* gap, best tightened to `>= 1` for merged criteria when P3 makes a 0-weight criterion visibly pointless.

3. **The default chair is usability-blind and can pick a just-failed provider.** On `claude,claude,codex` where `claude#1` dropped its proposal (its CLI is broken) but `claude#2`+`codex` are usable, the default still selects `claude#1` (first claude in board order), whose chair spawn will likely also fail → retry → refuse — discarding a run that *had* ≥2 usable proposals. This is literally per-contract ("claude if seated → first usable → board[0]"), and `--chair-seat` is the escape hatch, so it's not a deviation — but it's a "risk the contract didn't anticipate": "claude-if-seated" could reasonably mean "first *usable* claude, else first claude." Raise with the board for P3; don't block P2.

4. **Estimate/run-card chair projection ≠ actual chair on a no-claude board.** The preflight calls `choose_chair_seat(preferred=config.chair_seat)` *without* `usable_seats`, projecting `board[0]`; the run passes `usable_seats` and may pick a different first-usable seat (different model). Documented as a projection and the estimate is explicitly never a gate — cosmetic, acceptable.

## 4. Recommended execution sequence

This is a review of a completed change, not a build plan, so the sequence is merge-hygiene:
1. **Run the full suite on a clean checkout** and confirm 1499 OK (I trusted the reported count; I did not execute it). This is the one gate I couldn't close myself.
2. Merge as-is. The four §3 items are P3 backlog, not pre-merge work.
3. File P3 follow-ups for §3.2 (weight ≥ 1) and §3.3 (usable-first default chair) so they're not lost — both become more visible once scoring lands.

## 5. Invariants & guardrails (all present and correctly placed)

- **Identity is conductor-owned** (§11): `mint_proposals` is the sole proposal-id source (board order, then within-seat); criterion ids `c1…cN` assigned in `build_rubric`; a model-supplied `id` is dropped at parse (`test_model_supplied_id_is_ignored`). ✔
- **Partition = exactly-once ∪ no-phantom ∪ no-empty-subsumes**, checked mechanically against the minted ground truth in both `reconcile_partition` and the validator; unicode-confusable/NFC look-alike ids are refused as phantoms (raw code-point compare, never normalized) — good, genuinely adversarial tests. ✔
- **Weight-sum-to-100** enforced on integer percentages, bool rejected (int-subclass trap handled via `_is_int`), non-finite proposal weights rejected. ✔
- **RH-1**: no `out_dir` write before `enforce_egress_gate` approves; proposal prompts land via `write_pre_spawn_artifacts` post-approval/pre-activation; `_write` does `os.makedirs`, so the pre-round `logs/`/`rubric/` writes are safe. ✔
- **Fence/injection**: neutralizer covers the full `_ALL_RUBRIC_MARKERS` alphabet, `_extract_fenced`'s containment guard rejects any reply carrying *any* rubric marker, and `_proposals_table` re-neutralizes model prose before it re-enters the chair prompt. A poisoned source cannot forge a fence or smuggle fake partition JSON — the conductor mints ids and reconciles against them. ✔
- **Thread-safety**: the `ThreadPoolExecutor` fan-out writes `results[seat.id]` only from the main thread (collecting `fut.result()`); `config`/blob map are read-only. The single shared workdir is **consistent** with the existing round and endorsement fan-outs (verified), so it introduces no new concurrency property.

## 6. Concrete evidence

- Consent-hash fold: `cli.py:299-301`, `egress.py:324`, re-assert `cli.py:714`, round-1 sub-hash `cli.py:416` + `rounds.py:202-203`.
- Round-2 precedent legitimizing the chair egress: `egress.py:38-65` (`build_round2` embeds `own_review`), guard round-1-only `rounds.py:203,210`.
- Chair retry-then-refuse: `rubric.py:1130-1143` (`build_rubric`/`validate_rubric` inside `for attempt in (1, 2)`, `continue` on attempt 1, `break` on attempt 2).
- Exit-code precedent post-egress: `cli.py:518` returns `EXIT_PREFLIGHT_NOGO` after round-1 spawn; `rubric.py` sets `RUBRIC_REFUSAL_EXIT = EXIT_PREFLIGHT_NOGO`.
- Byte-identity: `status.py:88` (STAGES is `__all__`-only), `constants.py:341` (`"rubric"` key never serialized), `recipe.py:330-336` gated add + `config.py:797-807` read-back.
- Zero-weight gap: `rubric.py` `_validate_chair_weight` (`value < 0` reject only) and `board_rubric.py` (`crit["weight"] < 0`).

## 7. What I'd ask the other seats to challenge

- **Codex (adversarial/systems):** Is the single shared workdir across the concurrent proposal fan-out actually safe for *real* CLIs (not just mocks) that may write scratch files into `cwd`? It's consistent with rounds/endorsement, but "consistent with a latent risk" isn't "safe" — is there any adapter that writes into `cwd`?
- **Codex:** The default chair is usability-blind (§3.3). Can you construct a board where a healthy run with ≥2 usable proposals is refused solely because the first-claude seat's CLI died? Is that acceptable per D16, or a contract gap?
- **Any seat on tests:** Two validator tests (`test_proposal_ids_must_be_dense_sequence`, `test_partition_missing_id_refused`) pass by tripping a check *earlier* than the one their name implies (dense-id fires before partition; a no-op `subsumes` reassignment). They pin *a* refusal but not cleanly the named one — do these need tightening so a future reorder of `validate()` doesn't silently move which guard fires?
- **Gemini (product/quality):** Should a merged criterion be allowed at weight 0, or is "merged but scored at 0%" a rubric smell we forbid now before P3 scoring makes it user-visible?

VERDICT: ship

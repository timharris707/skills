All three explorations are back. I have what I need to render a grounded verdict. Every load-bearing invariant checked out against the actual code; one corner of the PR's own stated scope (the id-axis fix) is incomplete. Here is my full review.

---

# Claude seat review — v1.13 P4, the endorsement pass (release gate)

**Role lens: architecture & systems — invariants, failure modes, adversarial review.**

I verified the claims that couldn't be settled from the diff alone against the real tree (`spawn.py`, `config.py`, `rounds.py`, `egress.py`, `revision.py`, `artifacts.py`, `board_changes.py`, `render_verdict.py`). The design is sound and the crux invariant holds. I found exactly one defect, and it sits squarely inside this PR's own acceptance criterion (id-axis completeness). It is cosmetic and one line to fix — but on a release capstone whose thesis is "we got the id/name axis right everywhere," it should not ship unaddressed.

## 1. Verdict

**CAUTION** — confidence **HIGH**.

Proceed once the run-card endorsement-seat projection is moved onto the id axis (it currently under-counts on duplicate-provider boards, the one surface where the id-axis fix is incomplete), and the inverted narrative comment on the flagship id-axis regression test is corrected. Neither touches a correctness or integrity invariant; both are trivial.

**What would change it:** fix the `artifacts.py` projection to exclude by seat `id` (mirroring `endorsement_seats`) → **SHIP**. Conversely, had the shared endorsement workdir diverged from how the round fan-out isolates seats, or had the pointer sha been computed from a stale copy, this would be **BLOCK** — I checked both; neither is the case.

## 2. Strongest objections

**O1 — The id-axis fix is complete everywhere *except* the run card, which is name-axis and under-counts (the one in-scope defect).** `artifacts.py:121-122` derives the projected reviser as a **name**: `chosen = config.revision_seat or ("claude" if any(s.name == "claude" …) else config.board[0].name)`, then `artifacts.py:141` projects `n_endorse = sum(1 for s in config.board if s.name != chosen)`. On `--board claude,claude,codex` this excludes **both** claude seats → prints "**1** non-revision seat(s) vote," while the actual pass (`endorsement.py:188`, `s.id != revision_seat_id`) excludes only the reviser → **2** seats vote (`claude#1` + codex, confirmed by `test_duplicate_provider_board_keys_seats_by_unique_id`). The scrutiny brief explicitly listed "the record when two seats share a provider" as a hard check; the run card is a pre-consent record the user reads, and it is the single place the id-axis story still breaks. It is also a (mild) egress-disclosure under-count — it states one spawn where two occur (both to already-approved providers, so no new-provider egress, but the fan-out count is wrong). The PR pre-emptively labels this "name-axis by documented convention" — but documenting a wrong number doesn't make it right, and the fix is one line: project the reviser's id (`{s.name: s for s in board}.get(chosen)` mirrors `choose_revision_seat`'s own last-of-name collapse) and exclude on `s.id`.

**O2 — The canonical id-axis regression test has an inverted comment.** `test_duplicate_provider_board_keys_seats_by_unique_id` comments "claude#1 revises and claude#2 + codex endorse," but `choose_revision_seat` (`revision.py:281-282`) returns `by_name["claude"]`, and `by_name = {s.name: s for s in config.board}` **collapses duplicate names to the last occurrence** — so `claude#2` revises and the assertion `{"claude#1", "codex"}` is what's actually correct. The code and assertion are right; the comment describing them is backwards. On the one test that exists to pin the id-vs-name axis, a misleading narrative is a real maintenance hazard — a future debugger will trust the comment over the dict semantics.

**O3 — The reviser-selection-on-duplicate-boards is correct but incidental, and undocumented as such.** That `by_name = {s.name: s for s in board}` makes "last seat of that name" the default reviser (`revision.py:280-282`) is a side effect of dict-key collapse, not an explicit choice. It's harmless (any same-provider seat may revise) and it's pre-existing P2 code this PR doesn't touch — but it's the root cause of O2's confusion, so a one-line note at the `by_name` construction ("duplicate names collapse to the last seat") would repay itself.

**O4 — Egress-honesty wording is slightly loose (accurate in substance).** `render_endorsement_raw` says the seat "sees only source + revision derivatives **the run already egressed**." On a duplicate-provider board, the *assembled* revised draft was produced by the reviser (`claude#2`) and was **not** literally egressed to codex before this pass. It is a derivative of already-approved source + board-authored edits, sent to an already-approved provider under the disclosed endorsement plan — which is exactly the round-2 cross-read category (`egress.py:46,54` embeds every seat's prior review into every seat's next prompt), so the "no new egress category" claim is substantively true. But "already egressed" overstates it; "a derivative of already-approved material, to an already-approved provider, under the disclosed plan" is the honest phrasing. Wording only — no gate is bypassed (the run-level round-1 approval covers derivatives; `rounds.py:178-181`).

## 3. Recommended execution sequence

1. **Fix O1** — `artifacts.py` `render_run_card`: project the reviser id and count endorsement seats on `s.id`, so the card matches `endorsement_seats`. Add a targeted assertion to `TestEndorsementE2E` (or the run-card test) that a `claude,claude,codex` dry-run card reads "2 non-revision seat(s)".
2. **Fix O2** — correct the comment in `test_duplicate_provider_board_keys_seats_by_unique_id` to "claude#2 revises; claude#1 + codex endorse," matching the (correct) assertion.
3. **Optional O3/O4** — one-line note at `by_name` in `choose_revision_seat`; tighten the `render_endorsement_raw` disclosure sentence.
4. **Re-run the suite** (expect 1262 still green; +1 if you add the card assertion) and re-render one duplicate-provider handoff to eyeball the summary.
5. Tag v1.13.0.

## 4. Invariants and guardrails (verified holding — keep them pinned)

- **Pointer sha ≡ on-disk `changes.json` bytes, under every branch.** Merge happens in place at `cli.py:923` (`_run_endorsement_pass`) **before** the write (`cli.py:936-938`) and before the sha (`cli.py:939-941`, re-serialized with identical `indent=2, ensure_ascii=False` + `"\n"`); `_write_verdict_changes_pointer` trusts the passed sha and re-guards the verdict optimistically. Byte-identity is enforced by `test_pointer_sha_matches_endorsement_bearing_changes_bytes`, which hashes the **file bytes**. No divergence across endorse-ON / `--no-endorse` (untouched `[]`) / all-dropped / re-validation-failure.
- **Anti-smuggling ordering.** The guard (refuse a non-empty `endorsements` pre-pass) runs *before* the conductor's own merge; the conductor's rows enter *after*. Correct — the guard cannot false-positive on legitimate rows.
- **Re-validation fail-safe.** `_validate_changes_doc` catches `board_changes.validate`'s `SystemExit(2)` (confirmed `board_changes.py:89-91,286`); on the impossible failure it leaves `endorsements: []` and writes a valid artifact rather than shipping an invalid one — via a shallow `dict(rr.changes)` candidate, so `rr.changes` is untouched on failure.
- **Determinism / thread-safety.** Workers only *read* `config`/`changes`/`revised_text`; each builds its own rows; results are collected post-join in `[results[s.id] for s in seats]` board order, rows appended in `_expected_targets` (edits→unresolved) order → byte-stable across identical replies. The shared workdir matches the round fan-out exactly (`rounds.py:220` creates one `mkdtemp` shared across concurrent seats; `spawn()` writes nothing into `cwd`) — **not** a new race.
- **Failure posture.** Dropped/unparseable seat → one ABSTAIN/`dropped:true` row per target; all-dropped → loud warning + rows; single-seat board → `[]` + note. The pass never fails the run, discards the revision, or moves exit codes.

## 5. Risks, stale assumptions, missing evidence

- **Parse robustness — clean.** `parse_endorsement_reply` refuses missing/duplicate/extra/unknown target, both/neither locator, non-int/bool/negative number, bad position, OBJECT-without-note, non-JSON, missing/echoed/duplicate fence (`_extract_fenced` enforces unique END + marker-free interior). Every malformed shape → `ValueError` → `InvalidOutput` (retryable, `RETRYABLE_FAILURES = {FAILURE_TIMEOUT, FAILURE_INVALID}`) → retry → dropped. **All-or-nothing per seat** — never a partial row set. Matrix well-covered by `TestEndorsementParseMatrix`.
- **Validator split — sound by precedent.** The standalone `board_changes.validate` checks shape (XOR target, positive int, enum, `dropped` strictly-`true`, unknown-key refusal) but **not** target bounds — a hand-authored `edit_n:99` passes standalone. This mirrors the existing finding-ref convention ("shape check here is bounds-independent; the conductor cross-asserts"), and conductor-built rows are always in range (`parse` rejects unknown targets). Defensible; a possible future hardening (the doc has `edits[]` in hand) but not a gate.
- **Renderer — escaping correct.** `_esc = _nb(html.escape(str(...)))` (both `html` and `_nb` present, `render_verdict.py:40,617-624`); `<script>` → `&lt;script&gt;` proven by `test_summary_builder_html_escapes_notes`; `RAW_TOKENS` includes `ENDORSEMENT_SUMMARY`; empty-drop regexes target the `rl-body`/`patch-pre` lookaheads only. Minor: `_esc` duplicates the existing `_raw` (only adding `str()` for the integer slots) — could reuse. Minor: byte-identity for endorsement-less runs is tested by **absence proxies** (no `endorse-summary` div, no `</p>\n    \n` residue), not a golden-file diff — adequate but weaker than a stored-baseline compare.
- **Unused param.** `_run_endorsement_pass(config, rr, revision_seat, args)` never uses `args`. Dead parameter — drop it or note why it's threaded.
- **Standing invariants — all hold.** No-flag default byte-identical (`endorse=False` off the revised-draft path; recipe key added only inside the revised-draft block); stdlib-only; no unseeded clocks; hand-authored artifacts exit 2 cleanly; P2/P3 empty-`endorsements` artifacts validate and render unchanged (backfilled `setdefault("endorsement_summary", "")` in both renderers).

## 6. Concrete evidence

- **Defect (O1):** `scripts/_conductor/artifacts.py:121-122` (`chosen` = a **name**) and `:141` (`n_endorse = sum(1 for s in config.board if s.name != chosen)`) — vs. the correct id-axis exclusion at `scripts/_conductor/endorsement.py:188` (`[s for s in config.board if s.id != revision_seat_id]`). On `claude,claude,codex`: card says 1, pass does 2.
- **Test-comment inversion (O2):** `tests/test_run_board.py`, `test_duplicate_provider_board_keys_seats_by_unique_id` — comment says "claude#1 revises"; `revision.py:281-282` + the `{s.name: s for s in config.board}` collapse make **claude#2** the reviser, which is why the assertion `{"claude#1", "codex"}` is correct.
- **Sha invariant holds:** `cli.py:923` (merge) precedes `:936-938` (write) precedes `:939-941` (sha over re-serialized `rr.changes`); `_write_verdict_changes_pointer` (`cli.py:668-726`) trusts the sha and re-guards. Enforced by `test_pointer_sha_matches_endorsement_bearing_changes_bytes` hashing file bytes.
- **Concurrency parity (not a defect):** `rounds.py:214-228` — one `mkdtemp` per round shared across all concurrently-spawned seats; `spawn()` (`spawn.py:99-107`) passes `cwd` to `Popen` and writes nothing itself. The endorsement pass (`endorsement.py:556-584`) replicates this exactly.
- **Egress category is pre-existing:** `rounds.py:178-181` gates only round 1 against `approval.content_hash`; `egress.py:46,54` already egresses every seat's review to every other seat next round — the revised-draft-to-endorsers egress is the same class.
- **No AttributeErrors:** `SeatConfig.timeout_s` (`config.py:77`), `RunConfig.fs_scoped`/`network_on`/`endorse` (`config.py:109-126`) all exist.

## 7. What I'd ask the other board seats to challenge

- **Codex (impl-risk / correctness):** Stress the `changes.json` byte-determinism claim beyond the happy path — does a note containing a non-ASCII character or an embedded newline round-trip byte-identically through `json.dump` (file) vs `json.dumps` (sha) given `ensure_ascii=False`? Both should, but it's the exact place a sha could silently diverge, and the test uses ASCII notes. Also: is there any real board where `choose_revision_seat`'s last-of-name default surprises a user who passed `--revision-seat` expecting the *first* same-named seat?
- **Gemini (rollout / observability):** Is the shared endorsement workdir genuinely safe when two **same-provider** CLIs (two `claude`) run concurrently and each may scribble provider state into `cwd`/`$HOME`? Rounds already do this so it's not new — but has anyone observed a real dup-provider concurrent run, or only the mock (which writes nothing)? If the CLIs ever cache to `cwd`, both rounds and endorsement inherit the same latent race; worth one real dup-provider smoke run before the tag.
- **Either seat:** Do you accept the standalone-validator/conductor **bounds-check split** for endorsement targets, or should `board_changes.py` bounds-check `edit_n`/`unresolved_n` against `edits[]`/`unresolved[]` length (it has both in hand) so a hand-authored artifact of record can't carry a dangling target that passes `validate`?

---

Net: architecturally this is a clean generalization of the revision spawn path — the write-order/sha spine, the never-fail failure posture, the parse contract, and the concurrency model are all correct and well-tested. The only thing standing between it and SHIP is one name-axis projection line that contradicts the PR's own id-axis mandate, plus a backwards test comment. Fix those two and tag it.

VERDICT: caution

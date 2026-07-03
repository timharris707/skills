I've verified all the disputed claims against the actual code. I have what I need to finalize my round-2 position. Producing the full review now (this is a review deliverable — text out, no files).

---

# Round 2 — Claude seat (Architecture & systems)

I verified the four load-bearing disputes against the tree (`artifacts.py`, `endorsement.py`, `cli.py`, `config.py`, `rounds.py`, `revision.py`, `data-handling.md`). Result: the **design core is sound and I confirm it clean** (write order, pointer sha, parse robustness, validator split, concurrency, row order, escaping). But Codex found a **second real defect I missed in round 1** (per-seat timeout), and its egress objection has a **real kernel** — just not a block-worthy one. I hold **CAUTION** and dissent from Codex's **BLOCK**.

## 1. Updated verdict

**CAUTION — confidence HIGH.** The endorsement pass is architecturally correct; the artifact-of-record integrity (the thing this release gate exists to protect) is intact under every branch I traced. Three concrete, in-scope, non-corrupting defects must be fixed first — all isolated, all with graceful failure, none touching the sha-pin.

**What flips it to SHIP:** the id-axis run-card count, the per-seat endorsement timeout, and the egress-disclosure wording are all fixed with regression tests. **What would have flipped it to BLOCK (and does not):** an actual new-exposure-class leak, or any path where `changes.json` on disk can diverge from the pinned pointer bytes — I checked both; neither exists.

## 2. Where I changed my mind / where I still dissent

**Changed my mind (credit: codex):** In round 1 I called the run-card the *"one in-scope defect."* That was wrong — there are (at least) two. **Codex's per-seat-timeout catch is correct and I missed it.** `cli.py._run_endorsement_pass` passes `timeout=revision_seat.timeout_s` to the whole fan-out, and `endorsement.py.run_endorsement` resolves `timeout if timeout is not None else adapter.timeout_s` — it **never consults each endorsement seat's own `seat.timeout_s`**. The round fan-out does it correctly (`rounds.py:105-110`). So a documented `--timeout gemini=600` is silently ignored during endorsement; gemini runs on the reviser's clock and can time-out → drop → lose its vote. Real, conditional on per-seat overrides, graceful. I upgrade my count to **three** CAUTION items.

**Partially agree with codex on egress:** the wording *does* overclaim. I adopt that as a CAUTION.

**Still dissent from codex — BLOCK is too strong.** Codex frames the egress packet as *"materially inaccurate disclosure."* The **wording** is imprecise; the **substance is sound**. Every endorsement seat is a board seat that **already received the source in rounds** (`data-handling.md:3` — the source goes to every seat's provider up front). The revised draft is a board-derived *edit* of that source; the edit tables are the board's own collective work product. **No provider receives anything without having already received the source, and no new information/exposure class egresses** — which is exactly the reasoning `data-handling.md:46` already blessed for `source-material.txt` (*"the same consent envelope… no new exposure class"*). That is a documentation fix, not a data-leak, and it does not corrupt the artifact of record. BLOCK implies the design is unsound; it isn't.

## 3. Strongest remaining objections

**O1 (mine, hold) — run-card endorsement count is name-axis and under-counts on duplicate-provider boards.** `artifacts.py:141` `n_endorse = sum(1 for s in config.board if s.name != chosen)` with `chosen` a **name** (`:121-122`). The pass itself excludes correctly by **id** (`endorsement.py` `endorsement_seats`: `s.id != revision_seat_id`). On `--board claude,claude,codex`, the card projects **1** endorsement seat; the pass runs **2** (`claude#2` + `codex`). This is the one surface where the PR's own "id-axis completeness" (scrutiny #3) is incomplete. One-line fix.

**O2 (codex's, adopted) — per-seat `--timeout` not honored in the endorsement fan-out.** `cli.py._run_endorsement_pass` → `run_endorsement_pass(..., timeout=revision_seat.timeout_s, ...)`; `endorsement.py.run_endorsement` uses `timeout … else adapter.timeout_s`, never `seat.timeout_s`. Diverges from `rounds.py:105-110`. Silently drops a slow-but-valid seat's vote. Fix: make `run_endorsement` mirror the rounds precedence and pass `timeout=None` from `_run_endorsement_pass`.

**O3 (codex's kernel, downgraded to CAUTION) — egress disclosure overclaims.** The runtime print (*"each sees only source + revision derivatives the run already egressed"*), the raw recorder, the run card (*"no new egress"*), and `build_endorsement_prompt`'s docstring say the endorsement seats *already* received these bytes. They didn't — the revised draft is a **new artifact** to them (it was egressed to the *revision* seat). Accurate framing: *"no new exposure class — board-derived from source already disclosed to these providers in rounds."* Tighten the four sites + add one `data-handling.md` sentence (as §46 does for `source-material.txt`).

**O4 (codex's question, note-only) — `changes.revision_seat` is name-axis while `endorsements[].seat` is id-axis, in the same file.** `revision.py:1001` `revision_seat=seat.name`. On a duplicate-provider board `changes.revision_seat == "claude"` is ambiguous, while endorsement rows carry `claude#2`/`codex`. Pre-existing P2 field, not introduced here, and it doesn't break the sha-pin — but it's newly relevant. Document that the reviser is identifiable by *absence* from the id-axis rows, or record a `revision_seat_id`. Not a blocker for this PR.

## 4. Recommended execution sequence

1. **O2 (timeout) — highest correctness value.** In `endorsement.py.run_endorsement`, resolve `timeout → seat.timeout_s → adapter.timeout_s` (copy `rounds.py:105-110`); drop `timeout=revision_seat.timeout_s` in `cli.py._run_endorsement_pass`. Add a test: `--timeout <endorsement-seat>=<small>` forces exactly that seat to drop while others vote.
2. **O1 (run card) — project on the id axis.** Compute the projected reviser id and `sum(1 for s in config.board if s.id != chosen_id)`; keep it in lockstep with the revision-seat projection. Assert in `TestEndorsementE2E` that `claude,claude,codex` prints "2 non-revision seat(s)".
3. **O3 (egress wording) — the four sites + `data-handling.md`.** Replace "already egressed / no new egress" with the exposure-class framing; state the endorsement egress posture in the contract explicitly.
4. **O4 (revision_seat axis) — document or reconcile** in `changes-schema.md`; defer a schema change.
5. Re-run the suite (currently **1262 OK**); confirm the new tests fail before the fix and pass after.

## 5. Invariants and guardrails (verified this round)

- **Pointer sha ≡ on-disk `changes.json` bytes, every branch — CLEAN.** The anti-smuggling guard runs *before* `_run_endorsement_pass` (checks `endorsements == []` pre-merge); the conductor merges rows **in place**; draft → `changes.json` (`json.dump`, `newline=""`) → pointer are all written **after** the pass returns, from the same dict. On the re-validation-failure path, `rr.changes["endorsements"]` stays `[]` and the pointer pins *those* bytes — fails safe. `--no-endorse` and all-dropped paths preserve it. Do not reorder these writes.
- **Row order determinism — CLEAN.** `run_endorsement_pass` collects into a dict and returns `[results[s.id] for s in seats]`; rows are `board-order × target-order`. Byte-stable across identical replies. Preserve it.
- **Byte-identity for endorsement-less runs — CLEAN & test-enforced.** `--no-endorse` keeps `endorsements: []` (build_changes shape); the renderer drops `{{ENDORSEMENT_SUMMARY}}` with no blank residue.
- **Parse atomicity — CLEAN.** Any malformed reply raises → whole seat → `dropped_rows` (one ABSTAIN/dropped per target). Never a partial row set. Keep the all-or-nothing contract.
- **Thread-safety — CLEAN.** Workers touch only their own `EndorsementResult`; rows/flags assembled after the pool joins.
- **Validator shape-vs-bounds split — SOUND.** Standalone validator checks shape (XOR target, positive int, enum, `dropped` strict-true, unknown keys); the conductor bounds edit_n/unresolved_n via `_expected_targets` + `parse_endorsement_reply`. Consistent with the existing `resolves[].index` precedent.

## 6. Risks, stale assumptions, missing evidence

- **O2's blast radius is masked in the common case.** A bare `--timeout 300` folds into every seat's `timeout_s` (`config.py:375`), so `revision_seat.timeout_s` coincidentally equals theirs — the bug only bites with **per-seat** overrides. That's exactly the documented use case ("a slow local seat shouldn't set the whole board's clock"), so don't let the green suite hide it: the added tests don't cover per-seat timeout at all (codex's point stands).
- **Byte-determinism of an OBJECT note with non-ASCII / embedded newline is untested.** `json.dump(ensure_ascii=False)` + `newline=""` is deterministic (control chars escaped, UTF-8 emitted raw), and `test_pointer_sha_matches_endorsement_bearing_changes_bytes` pins on-disk bytes — but only with ASCII notes. Add a note carrying `é` and `\n` and re-assert the pin. Low risk, closes the last gap codex challenged.
- **Re-validation-failure path leaves orphan `endorsement/*.md` with `endorsements: []`.** Defensive, should-never-fire, warns loudly, fails safe — acceptable, worth a one-line note.
- **Not independently re-run here** (read-only). I relied on the stated 1262 OK + my own line-level trace; the three fixes need their own regressions before I'd call it SHIP.

## 7. Concrete evidence

- **O1:** `scripts/_conductor/artifacts.py:121-122` (`chosen = config.revision_seat or ("claude" if … else config.board[0].name)` — a **name**) and `:141` (`n_endorse = sum(1 for s in config.board if s.name != chosen)`) vs. the correct id-axis exclusion in `scripts/_conductor/endorsement.py` `endorsement_seats` (`return [s for s in config.board if s.id != revision_seat_id]`).
- **O2:** `scripts/_conductor/cli.py` `_run_endorsement_pass`: `run_endorsement_pass(config, rr.changes, rr.revised_text or "", seats, timeout=revision_seat.timeout_s, workdir=workdir)`; `scripts/_conductor/endorsement.py` `run_endorsement`: `seat_timeout = timeout if timeout is not None else adapter.timeout_s`. Correct precedent: `scripts/_conductor/rounds.py:105-110` (`if timeout is not None … elif seat.timeout_s is not None … else adapter.timeout_s`). Per-seat store: `scripts/_conductor/config.py:375` (`timeout_s=timeout_overrides.get(sid, timeout_default)`).
- **O3:** `scripts/_conductor/endorsement.py` runtime/raw/docstring ("…revision derivatives the run already egressed", "no new egress"); `artifacts.py:145` ("no new egress"). Contract: `references/data-handling.md:3` (source → every provider) and `:46` (`source-material.txt` = "no new exposure class") — the precedent that makes the *substance* fine and the *wording* wrong.
- **O4:** `scripts/_conductor/revision.py:788` (`"revision_seat": revision_seat`) and `:1001` (`revision_seat=seat.name`) — name-axis, vs. `endorsements[].seat` = unique id.
- **Write order (clean):** `cli.py._run_revision_step` — smuggling guard (`(rr.changes.get("endorsements") or []) != []` → reject) precedes `_run_endorsement_pass(config, rr, seat, args)`, which precedes the draft/`changes.json`/pointer writes; `_run_endorsement_pass` re-validates via `_validate_changes_doc` before assigning `rr.changes["endorsements"] = rows`.

VERDICT: caution

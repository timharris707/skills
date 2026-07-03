Verified against the working tree. Both contested points reproduce, and I checked the egress sites and the duplicate-board projection myself. Here is my round-2 review.

---

# Claude seat — round 2 (Architecture & systems)

## 1. Updated verdict

**CAUTION — confidence: high.** The five original blockers are genuinely cleared (I re-verified, not from the diff narrative), the two "couldn't-verify" gaps are closed by real tests, and the design is sound end-to-end. I am moving off my round-1 SHIP for one narrow, in-theme reason: the `changes@1` validator does not enforce the dropped-row contract it documents, and this is a release **tag** whose own headline this round was validator strictness. That is a ~3-line fix plus negative tests.

**What would flip it to ship:** tighten `_validate_endorsement` so `dropped: true` requires `position == "ABSTAIN"` **and** a non-empty `note` (with fail-before/pass-after tests) — *or* a recorded decision to defer that to v1.13.1 with an explicit rationale that it's not a live pipeline path. Either one flips me to ship. Nothing else gates.

## 2. Where I changed my mind, where I still dissent

- **Changed my mind (converging with codex):** codex's `board_changes.py` dropped-row point is correct and I confirmed it — `scripts/board_changes.py:258-262` accepts `{"seat":"x","edit_n":1,"position":"ENDORSE","dropped":true}` and a dropped row with no `note`. My round-1 "every item is addressed / SHIP HIGH" overstated: the dropped-row validator semantics were **not** in the addressed set, and this same PR tightened sibling gaps (upper-bounds + duplicate rows at `board_changes.py:330-352`). Stopping short of the dropped-row contract is an incomplete tightening on the artifact of record. That's enough to hold the tag.

- **Still dissent from codex — "stale egress/doc strings":** I grepped the egress sites (`artifacts.py:143-144` revision line, `artifacts.py:157-158` endorsement line, `cli.py:762`, `endorsement.py:253` and `:616`, `data-handling.md:48`). All carry the converged round-2 framing: the *revision* seat sees only already-sent source (no new egress); the *endorsement* seat receives the board-**generated** revised draft, framed as "same category as round-2 review sharing, no new exposure class," with the honesty clause that it's freshly generated. I could not reproduce a specific stale string. If codex is holding on this, it needs an exact `file:line` — on my read the wording is settled and not blocking.

- **Dissent on severity of my own round-1 concern:** the artifact-before-validation ordering (`cli.py:776-799`) is real but I no longer treat it as a blocker — see §3. It's a minor coherence note, not a gate.

## 3. Strongest remaining objections

1. **Validator doesn't enforce the dropped-row contract (gating).** `_validate_endorsement` (`board_changes.py:258-262`) only checks `dropped is not True`. It never asserts `position == "ABSTAIN"` when `dropped` is set, and never requires a `note`. The conductor's `dropped_rows` always emits `ABSTAIN` + a non-empty `note`, so **no pipeline path** produces a violating row — but this validator's stated job (and this PR's own tightening theme) is to catch hand-authored/corrupted files. Concrete downstream consequence: the renderer's tally (`render_verdict.py` `_tally`) counts by `position` and ignores `dropped`, so a hand-authored `{dropped:true, position:"ENDORSE"}` would be counted as an endorsement in the handoff summary. Small blast radius, but it's the artifact of record.

2. **Endorsement artifacts written before re-validation (minor, non-gating).** `cli.py:776-787` writes `endorsement/<seat>.md`+`.raw`+prompt+stderr, then `cli.py:794` re-validates the merged candidate and, on failure, returns with `changes.json` carrying `endorsements: []` (`:795-798`). The `endorsement/<seat>.md` on disk then shows votes while `changes.json` shows none. This is an internal-error-only path (conductor-built rows should never fail re-validation), and it's defensible as the system's existing "black-box always recorded, certified artifact gated" posture (mirrors a dropped revision writing `revision/<seat>.raw` alongside `changes-rejected.json`). But the failure-branch print doesn't point the reader at the divergence. A one-line note in that branch ("per-seat endorsement/ records are on disk though endorsements were dropped from changes.json") would close it. Not a tag gate.

3. **Default duplicate-board reviser is a last-name-collapse (note, not a bug).** On `--board claude,claude,codex` with no `--revision-seat`, the default reviser is `claude#2` — `choose_revision_seat` returns `by_name["claude"]` (`revision.py:290-291`), and the dict-collapse picks the last same-name seat. I confirmed the run-card projection agrees: `artifacts.py:130-133` reproduces the same `by_name` collapse → `chosen_id = claude#2`, so the card's "2 non-revision seat(s)" matches the seat that actually revises. This is the correct fix for item 1; I only flag that "which claude revises by default" is decided by dict-last-wins and deserves a one-line doc mention.

## 4. Recommended execution sequence

1. **Tighten the dropped-row validator** (the one gate): in `_validate_endorsement`, add `if entry.get("dropped") is True and entry["position"] != "ABSTAIN": die(...)` and `... and (not isinstance(entry.get("note"), str) or not entry["note"].strip()): die(...)`. Add negative tests to `TestEndorsementValidatorMatrix` (dropped+ENDORSE refused; dropped+no-note refused; dropped+ABSTAIN+note accepted — the last already implicitly covered by `test_dropped_row_validates`).
2. **(Optional, non-gating)** add the one-line divergence note in `cli.py:795-798`'s failure branch.
3. **(Optional, non-gating)** one sentence in `changes-schema.md` that the default reviser on a duplicate-provider board is the last same-name seat.
4. Run the focused suite (`TestEndorsement*`, id-axis, exotic-note) fail-before/pass-after, then the full **1279 OK** in CI — the count is author-asserted; I verified logic and test shape only (read-only).
5. If steps 2-3 are deferred, they don't block the tag; only step 1 (or a recorded waiver of it) does.

## 5. Invariants and guardrails

- **Pointer-sha coherence (holds):** rows merge in place at `cli.py:799` **before** the single `changes.json` write (`:939-944`), sha computed over those exact bytes, pointer written once. `verdict.json.changes.sha256` pins the endorsement-bearing bytes — `test_pointer_sha_matches_endorsement_bearing_changes_bytes` and `test_exotic_object_note_round_trips_byte_for_byte` cover it.
- **Conductor-built rows only (holds):** the write-path guard (`cli.py:904-909`) still refuses any non-empty `endorsements` reaching the write path *before* the conductor's own merge — the model authors tokens, never rows.
- **Never-fail-the-run (holds):** dropped/all-dropped/single-seat/`--no-endorse` all exit 0 with rows-or-empty + a note; verified by the E2E matrix.
- **Id-axis keying (holds):** exclusion, row `seat`, and per-seat artifact paths all key on the unique `id` (`endorsement.py` `endorsement_seats` + `run_endorsement`; `revision.py:947,1024` now record `seat.id`), so duplicate-provider seats stay distinguishable and their black-box records don't collide.
- **New guardrail to add:** `dropped ⟹ ABSTAIN + non-empty note` at the validator, matching the conductor's own `dropped_rows` output — the missing invariant.

## 6. Risks, stale assumptions, missing evidence

- **Test count author-asserted.** 1279 OK is not executed by me (read-only). Confirm green in CI before tag.
- **codex's "stale egress strings" unlocated.** I found none; either codex cites the exact site or it should be dropped as a gate.
- **Tally conflates dropped-ABSTAIN with genuine ABSTAIN** in the handoff summary (pre-existing D13 choice; the `dropped` marker and objection notes remain in `changes.json`). Not new, not raising as a gate — noting for product awareness.
- **`--no-endorse` byte-identity** to a P2-shape `changes.json` is asserted and tested (`test_no_endorse_changes_json_matches_a_p2_shape_endorsements`); I did not re-run it.

## 7. Concrete evidence

- Validator gap: `scripts/board_changes.py:258-262` — only `if "dropped" in entry and entry["dropped"] is not True: die(...)`; no ABSTAIN/note coupling. Contrast the conductor's `dropped_rows` (endorsement.py) which always sets `position="ABSTAIN"`, `dropped=True`, `note=f"endorsement seat dropped: {reason}"`.
- Sibling tightening this PR *did* land: `scripts/board_changes.py:330-352` (upper-bound + duplicate `(seat, kind, n)`).
- Artifact-before-validate ordering: `scripts/_conductor/cli.py:776-787` (writes) precede `:794` (`_validate_changes_doc`) and the `:795-798` empty-endorsements return; in-place set at `:799`.
- Single-write + sha coherence: `scripts/_conductor/cli.py:939-944` write, pointer once after.
- Duplicate-board projection agrees with runtime pick: `artifacts.py:130-133` mirrors `revision.py:280-291` `by_name` collapse (`claude#2`).
- Egress framing verified converged: `artifacts.py:143-144` / `:157-158`, `cli.py:762`, `endorsement.py:253` / `:616`, `references/data-handling.md:48`.

Bottom line: the design is sound and the blockers are cleared — this is a good feature. Close the one documented-but-unenforced validator invariant (or record a conscious deferral), and it's a clean v1.13.0 tag.

VERDICT: caution

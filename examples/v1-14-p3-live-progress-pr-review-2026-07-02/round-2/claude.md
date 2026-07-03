Both round-1 objections are now confirmed against the actual source, and I've found corroborating evidence that sharpens the first one. I have what I need to finalize my round-2 position. Producing the review as text (this is a read-only review task — no files written, no plan-mode summary, per the board instruction).

---

# Claude seat — round 2 (Architecture & systems)

## 1. Updated verdict

**CAUTION — confidence: high.** I hold my round-1 position. The load-bearing architecture is sound under scrutiny: the lock discipline serializes every mutation, the atomic writer never tears, RH-1 correctly defers all `status.*` writes until after hash-bound egress approval, and the zero-drift claim holds for every *artifact of record*. But two named defects remain, both now verified against the tree, not just the diff. **What would change it to SHIP:** gate the `render_artifact_tree` status line on config (with the missing `assertNotIn` test), and reconcile the "egress-refused leaves no out dir" prose with the code that actually writes `egress-manifest.md` + `sensitivity.json` on refusal.

## 2. Where I changed my mind / where I still dissent

- **I HELD my prior view (caution), on my own re-verified evidence.** My round-1 O1 (the unconditional artifact-tree line) is not just a convention smell — I confirmed it is a *lie in the dry-run preview*: `render_artifact_tree` is printed at `cli.py:285-286` under `=== artifact tree it WOULD create ===`, so `run --dry-run --no-live-status` promises `status.json status.html` that the real run will never write. And I found the smoking gun for "violates the repo's own convention": `tests/test_run_board.py:7259` (`test_artifact_tree_shows_synthesizer_when_on`) is an *existing, passing* test asserting the tree is config-conditional (`assertNotIn("synthesizer/", off)`). The status line was added with no parallel `assertNotIn`.
- **I adopted one fact codex surfaced — but verified it myself, so it did not flip my verdict.** Codex (objection 1) named that the egress-refused path writes an out dir before the tracker is active (`cli.py:377-387`). I confirmed it: `os.makedirs(config.out_dir)` + two `_write` calls at `cli.py:381-385`. This makes the CHANGELOG/SKILL "egress-refused run leaves no out dir" prose false. My verdict was already caution on independent grounds (O1), so this is a corroborating second defect, not the basis of my position.
- **I do NOT dissent from codex on anything material.** We converge on caution. Where I'd push back on *emphasis*: codex frames RH-1 as "internally inconsistent" — I want to be precise that the **code is correct** on the invariant that actually matters (no `status.*` before consent); only the **prose** overreaches by conflating "no `status.*`" with "no dir." That distinction changes the fix from "code change" to "one-line doc change," and it should not read as a safety hole.

## 3. Strongest remaining objections

**O1 [primary] — the artifact tree advertises `status.*` unconditionally, breaking the file's own truthful-tree convention and lying in the dry-run preview.** `artifacts.py:309-316` appends the status line with no `config` guard. Every sibling optional slot in the *same function* is gated: grounding (`:268 if config.grounding is not None`), echo-score (`:276 if packet_rounds`), synthesizer (`:282 if config.synthesize`), revised-draft (`:287 if config.output == "revised-draft"`), endorsement (`:304 if config.endorse`). The comment at `:302-303` states the governing principle outright — "*so the tree stays truthful about what a --no-endorse run writes*" — and the status line violates exactly that. Impact is real (the dry-run preview at `cli.py:285` shows files a `--no-live-status` run won't create) but bounded (no byte-pinned golden of the full tree exists, so the suite stays green — this is an output-honesty bug, not a red test). **Fix:** add `live_status: bool` to `RunConfig` (set from `not args.no_live_status` in `resolve_config`, mirroring `endorse`), gate the line on `config.live_status`, and add `test_artifact_tree_omits_status_when_no_live_status` alongside `:7259`. `RunConfig` currently has **no** such field — the only signal is `args.no_live_status` at `cli.py:328`, which `render_artifact_tree(config)` can't see.

**O2 — the "egress-refused leaves no out dir" claim is contradicted by pre-existing code.** `cli.py:381-385` creates `config.out_dir` and writes `egress-manifest.md` + `sensitivity.json` on refusal (this predates the PR; only the `tracker.finish()` at `:386` is new). The status behavior is correct — `tracker.finish()` fires while inactive (`activate()` is at `:396`, only on the approved path), so `_write_files` early-returns on `not self._active` and no `status.*` lands. But `CHANGELOG.md:28` and `SKILL.md:145` say a refused run "leaves no out dir — and no `status.*`." Only the second half is true. **Fix:** reword to "no `status.*`" (preflight NO-GO leaves no dir; egress-refused writes the refusal manifest as it always has).

**O3 [minor] — no finalizer stamps an interrupted run.** Every *enumerated* exit calls `tracker.finish(...)` (preflight NO-GO `:359`, egress block `:386`, round-1 collapse, board collapse `:537`, synthesis/revision success + failure). But an uncaught exception / KeyboardInterrupt / OOM *after* `activate()` leaves `status.json` with `finished=None`, so `status.html` self-refreshes forever on a dead process. Prior reviewers called this "honest" and I agree it's defensible (the process genuinely didn't finish) — but there is no `try/finally` or `atexit` to stamp `outcome="interrupted"`. I keep this as cosmetic, not gating.

## 4. Recommended execution sequence

1. **Thread `live_status` onto `RunConfig`.** Add the field; set it in `resolve_config` from `not getattr(args, "no_live_status", False)`; keep `cli.py:328` reading the same source (or switch it to `config.live_status` for a single source of truth).
2. **Gate `artifacts.py:309-316`** — wrap the status line in `if config.live_status:`. Add `test_artifact_tree_omits_status_when_no_live_status` mirroring `:7259` (`assertIn` on default, `assertNotIn("status.json", off_tree)`).
3. **Reconcile the RH-1 prose** in `CHANGELOG.md:28`, `SKILL.md:145`, and the `status.py` module docstring: precise wording is "no `status.*` before egress approval," and (separately) "preflight NO-GO leaves no dir; egress-refused writes only the refusal manifest, never `status.*`." Add an E2E `test_egress_refused_leaves_no_status` (dir may exist with the manifest; assert `status.json`/`status.html` absent) — the suite currently tests only the preflight NO-GO case (`test_no_go_preflight_leaves_no_status`).
4. **(Optional, O3)** wrap the post-`activate()` run body so any abnormal exit stamps `finished` + `outcome="interrupted"`, then re-renders the now-static HTML.
5. Re-run `-k Status` and the full suite; confirm 1419→1421 (two new tests) and the live-vs-opt-out artifact diff stays clean.

## 5. Invariants and guardrails

- **One lock, every mutation under it.** `stage`/`round_started`/`round_done`/`seat`/`finish`/`activate` all acquire `self._lock`; `_flush` (seq++, `events.append`, `_set_seat`, `_print_line`, `_write_files`) runs inside a locked caller. The JSON snapshot `json.dumps(self._doc)` executes under the lock in `_write_files`, so **the serialized snapshot can never tear** — this is the invariant that matters and it holds. **Keep it:** any future off-lock caller of `_write_files`/`_flush` breaks it.
- **Fixed tempfile name is safe *because* writes are serialized.** `_atomic_write_text` uses `.{basename}.tmp` (not unique per write). No collision is possible only because the lock guarantees non-overlapping writes. This is a latent contract — if `_write_files` is ever called concurrently, two writers race the same tmp. Worth a one-line comment pinning "safe only under the lock."
- **`os.replace` is atomic on macOS and the CI linux runner** (sibling tmp, same volume → `rename(2)`); a reader sees old-or-new, never partial. status.json and status.html are *individually* atomic but not *jointly* — acceptable for a live view (not an artifact of record).
- **RH-1: no `status.*` before hash-bound consent.** `_write_files` early-returns on `not self._active`; `activate()` is called only at `cli.py:396`, strictly after `write_pre_spawn_artifacts`. Preserve the ordering: `activate()` must never move above the approval branch.
- **Best-effort writes never take the run down** — warn once (`_warned` flag under the lock), keep advancing the in-memory doc. Verified by `test_write_failure_never_kills_the_run`.
- **`--no-live-status` ⇒ byte-identical artifacts of record.** After the O1 fix this becomes fully true (the artifact-tree line will also disappear on opt-out).

## 6. Risks, stale assumptions, missing evidence

- **`elapsed_s` is wall-clock** (`rounds.py`), flowing into the `done` event `detail` and the terminal line (`round 1 · codex ✓ 186s`). It is confined to non-pinned surfaces today — the event-sequence golden asserts `event_tuples` (stage/seat/round/state), never `detail`; the terminal-format tests use fixed strings. **Latent risk:** the moment anyone byte-goldens `status.json`'s `detail` or the full terminal transcript, this becomes nondeterministic. Keep `detail` out of any future golden.
- **Missing tests (both cheap):** no `assertNotIn("status.json", off_tree)` for the artifact tree; no egress-refused `status.*`-absence E2E. The PR's own claim ("live-vs-opt-out artifact diff clean") is asserted, not test-encoded for these two surfaces.
- **Terminal-line interleaving is fine as written** — during fan-out only worker threads print (serialized by the tracker lock); the main thread is blocked in `run_round` and prints the round table only after it returns, so tracker lines never garble the conductor's own multi-line blocks. Do not move any main-thread `print` into the fan-out window.
- **Not independently verifiable from the material:** the 1419-OK count and the clean artifact diff (the state note says both were independently run; I did not re-run the suite here — I verified the *code* claims).

## 7. Concrete evidence

- `artifacts.py:309-316` — unconditional status line; contrast the conditional slots at `:268` (grounding), `:276-281` (echo-score), `:282` (synthesizer), `:287` (revised-draft), `:304` (endorsement). Governing comment: `:302-303` ("*so the tree stays truthful*").
- `cli.py:285-286` — `render_artifact_tree(config)` inside the dry-run preview (`=== artifact tree it WOULD create ===`) → the tree lies on `--dry-run --no-live-status`.
- `tests/test_run_board.py:7259-7265` — `test_artifact_tree_shows_synthesizer_when_on`: existing test proving the tree is config-conditional (`assertNotIn("synthesizer/", off)`); no `status.json` analogue was added.
- `cli.py:328` / `cli.py:1235` — the only `no_live_status` signal lives on `args`; `RunConfig` has no `live_status` field (grep-confirmed), so `render_artifact_tree(config)` cannot currently gate the line.
- `cli.py:377-387` — egress-refused path: `os.makedirs(config.out_dir)` + `_write(... "egress-manifest.md")` + `_write(... "sensitivity.json")`, then `tracker.finish("egress-blocked", ...)` while inactive. Contradicts `CHANGELOG.md:28` / `SKILL.md:145` ("leaves no out dir"); the `status.*`-absence half is correct (`status.py` `_write_files` returns on `not self._active`; `activate()` at `cli.py:396`).
- `status.py` `_atomic_write_text` — `.{basename}.tmp` + `os.replace`; `unlink` on failure; fsync deliberately skipped (documented best-effort). Safe under the lock; fixed tmp name is the one fragility to comment.

BASIS: independent
VERDICT: caution

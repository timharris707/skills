I've verified the claims against the actual staged files. My verification is complete — findings below.

---

# Claude seat review — v1.14 P3 live progress view (REVISED)

**Role lens: architecture & systems — invariants, failure modes, adversarial review.**

I checked each prior blocker against the real files in the worktree, not the diff's narration. All four items land. The most substantive new code — the abort guard and the `_execute_run` → `_run_after_activate` split — is correctly designed, and I traced the one failure mode that would sink it (a normal completion path that skips `finish()` and gets falsely stamped `interrupted`). It doesn't exist: every terminal path stamps first.

## 1. Verdict

**SHIP** — high confidence on the blocker resolutions (verified against source, not the diff), medium-high overall.

**What would change it:** I did not execute the suite (read-only/plan constraint), so the "1426 green" claim rests on the authors' run plus my static trace. If a targeted `-k Status` run showed *either* a false `interrupted` stamp on a clean `--synthesize`/`--output revised-draft` completion *or* a `NameError` from the `_run_after_activate` extraction, that flips me to caution. Both are directly covered by E2E tests I read and judge sound, so I don't expect it — but that run is the one unclosed loop.

## 2. Strongest objections (all minor; none blocks)

- **The `retry` state is advertised but never emitted.** It's in `STATES`, `_STATE_GLYPH`, `_SEAT_STATE_CLASS/LABEL`, the CHANGELOG vocabulary, and the terminal-line formatter — but `rounds.py:261` only ever emits `"done"`/`"dropped"` (`event = "done" if result.usable else "dropped"`), with an honest deferral comment at `rounds.py:257-260`. This was a prior *concern*, and it remains: the schema surface claims a transition the emitter cannot produce. Shipping with the comment is defensible, but the vocabulary is writing a check the code doesn't cash. Cheapest honest fix is a one-word doc note that `retry` is reserved-not-yet-emitted.
- **`content_hash` is a dead parameter** of `_run_after_activate` (`cli.py:421`) — passed at the call site, never read in the body. Harmless, but it's exactly the kind of vestige a reader trips on when reasoning about what the round loop still depends on. Drop it.
- **`--from-recipe` silently re-enables the live view.** `live_status` is deliberately not recipe-persisted (`recipe.py` comment + `config.py:112` default `True`), so replaying a recipe captured from a `--no-live-status` run will now write `status.*`. This matches the stated `--strict-exit`/`--digest-format` convention and touches no record artifact, so it's *consistent* — but it means a recipe cannot faithfully reproduce a `--no-live-status` run's exact dir contents. One sentence of acknowledgement is enough; not worth persisting.
- **`interrupted` conflates a hostile drift-abort with a Ctrl-C.** The egress-hash / repo-scope `die()` inside `run_round` is a *security* abort, not an interruption, yet it stamps `outcome: interrupted`. Because `status.*` is explicitly not an artifact of record and the exit code + `die()` message are preserved untouched, this is acceptable — but flagging it so no one later keys a security audit off `outcome`.

## 3. Recommended execution sequence

This is mergeable as-is. Ordering for the merge + optional cleanup:

1. **Before merge (required):** run `-k Status` plus one live-vs-`--no-live-status` artifact diff, and confirm the count moves to 1426. This is the only verification I couldn't perform.
2. **Merge.** The v1.14.0 release follows one phase later, per the roadmap gate — hold the tag for Tim's go.
3. **Optional, same PR or a trailer:** drop the dead `content_hash` param; add the one-line `retry`-is-reserved doc note; add a one-line comment on the `events[]`-order caveat (below) so a future test author doesn't write a flaky ordered assertion.

## 4. Invariants and guardrails (verified)

- **RH-1 (no `status.*` before egress approval): HOLDS.** `activate()` is reached only at `cli.py:397`, *after* the egress gate and `write_pre_spawn_artifacts`. The refusal path (`cli.py:378-388`) calls `tracker.finish("egress-blocked")` on a not-yet-active tracker, and `_write_files` early-returns on `if not self._active` (`status.py:275`) — so the refusal writes only `egress-manifest.md` + `sensitivity.json`, never `status.*`. This matches the corrected docs exactly.
- **Zero byte-drift on record artifacts: HOLDS.** `render_artifact_tree` has exactly one caller — `cli.py:287`, inside the `--dry-run` branch. It is console-preview-only; it is *not* baked into the run-card or any persisted file. So defaulting `live_status` on adds a preview line but changes no record artifact. `status.*` are new files, explicitly excluded.
- **Best-effort writes: HOLDS.** `_write_files` swallows all exceptions and warns once (`status.py:283-289`); the finally's `finish_if_unfinished` is itself wrapped `try/except pass` (`cli.py:413-418`) so a failing stamp can never mask the original exception.
- **Thread-safety: HOLDS.** Every mutation (`_seq`, `events.append`, seat map, `_warned`) is under the single lock; `json.dumps(self._doc)` runs *inside* the lock, so the serialized snapshot is never torn. `on_seat` fires from workers → `tracker.seat()` acquires the lock; and `run_round._notify` additionally wraps the callback in `try/except pass` (`rounds.py:247-250`) so a bad callback can't break the fan-out.
- **Exit-code preservation: HOLDS.** The `finally` contains no `return`, so the try's return value / re-raised `SystemExit` propagates unchanged.

## 5. Risks, stale assumptions, missing evidence

- **Latent, un-guardrailed: `events[]` order is nondeterministic under the real parallel executor.** Across seats, the `running`/`done` interleaving depends on thread scheduling. Today's tests dodge this correctly — the golden (`test_event_sequence_golden…`) drives the tracker with in-order *direct* calls, and the E2E uses `assertIn`, never ordered equality. But nothing *documents* the sharp edge. A future contributor who asserts `event_tuples(real_run_doc) == [...]` will get a flake. Add a one-line caveat at the golden or in `event_tuples`.
- **`status.json` is inherently nondeterministic** (`detail` carries `f"{result.elapsed_s:.0f}s"`, wall-clock). Correctly kept out of every byte-pin; just note it can never become a golden fixture without stripping `detail`. No invariant violated.
- **Missing evidence I'd want:** the real-executor Ctrl-C path is proven only via a synchronous mock (`test_keyboard_interrupt…` patches `run_round` to raise directly). The guard logic is origin-independent so this is a fair proxy, but note that `ThreadPoolExecutor.__exit__` waits for in-flight seat subprocesses before the KI propagates — a pre-existing behavior, not introduced here, but it means Ctrl-C during a fan-out isn't instantaneous. The guard stamps correctly once it does propagate.
- **Count arithmetic:** +7 (1419→1426) is internally consistent with the ~7 blocker-fix test methods the revision adds (artifact-tree omission, dry-run opt-out, egress-refused, mid-fan-out die, KeyboardInterrupt, and the 2-test reader-hardening class). I did not re-run to confirm.

## 6. Concrete evidence

- **Blocker 1 cleared** — `config.py:112` `live_status: bool = True`; `config.py` `resolve_config` sets `live_status=not getattr(args, "no_live_status", False)`; `artifacts.py:319` `if config.live_status:` gates the status line; `cli.py:329` `if not config.live_status:` selects `NullTracker` from the *same* field. Single source of truth, exactly as prescribed. Tests: `test_artifact_tree_omits_status_when_no_live_status`, `test_dry_run_no_live_status_omits_status_from_preview`.
- **Blocker 2 cleared** — `status.py:34-37` docstring now reads "an egress-refused run writes only the refusal manifest (egress-manifest.md + sensitivity.json), never status.*". Code proof: `cli.py:382-388` writes the two refusal files then `finish(...)` on the inactive tracker then `die()`; `activate()` never reached. Test: `test_egress_refused_writes_manifest_but_no_status`.
- **Codex ship-gate cleared** — `event_tuples` (`status.py:352-358`) guards `doc`, `events`, and each entry via `isinstance`; `render_status_html` (`status.py:408-468`) normalizes a non-dict `doc` to `{}`, guards `seats`/`events` containers and every entry. Test: `TestStatusReaderHardening`. The note that no CLI subcommand reads `status.json` checks out — the only readers are the tracker itself and tests, so "harden to never raise" (not "exit 2") is the correct resolution.
- **O3 cleared, correctly** — `cli.py:408-418` try/finally; `finish_if_unfinished` (`status.py:232-246`) is idempotent under the lock (`if self._doc["finished"] is not None: return`). I traced **every** normal return path calling `finish()`/`tk.finish()` first: `cli.py:449` (round-1 insufficient), `:571` (collapse), `:596` (no-synthesize), `:704` (synth ok), `:732` (no-verdict), `:1094` (revision ok), `:1125` (verdict-only); the synth-with-revision branch (`:698-703`) delegates to revision, which always finishes. So the finally is a proven no-op on all clean completions and only stamps `interrupted` on a genuine abnormal exit. Extraction free-variable check: all of `config/args/tracker/blobs/approval/preflight/digest_json/_seat_cb/_write` are parameters; the rest are module-level or locals created inside. No `NameError`.

## 7. What I'd ask the other seats to challenge

- **Codex (correctness/security):** Re-run `-k Status` and, ideally, a full pass to confirm 1426 and — the single highest-value check — that no clean `--synthesize` or `--output revised-draft` run comes back stamped `interrupted`. That's the one regression the static trace can't fully close.
- **Codex:** Does `main()` catch `KeyboardInterrupt` anywhere upstream of `_execute_run`? `test_keyboard_interrupt…` asserts it propagates through `rb.main(...)`; confirm nothing swallows `BaseException` between the guard and the test.
- **Any seat:** Contest my "not a blocker" call on the advertised-but-unemitted `retry` state — is a documented-but-dead schema token acceptable to ship, or does the vocabulary need to shrink to what's emitted?
- **Any seat:** Push on the `interrupted` label for the egress-hash-drift `die()` — is coarse "interrupted" fine for a security abort given `status.*` is non-record, or should a distinct `aborted-security` token exist so the two are never conflated?

Every prior blocker is genuinely resolved, the Codex ship-gate and the optional O3 are both properly addressed, and the abort guard is the right shape (idempotent, best-effort, exit-code-preserving, complete `finish()` coverage). The residuals are cosmetic or documented-and-acknowledged. Ship, with the pre-merge `-k Status` run as the one gate.

VERDICT: ship

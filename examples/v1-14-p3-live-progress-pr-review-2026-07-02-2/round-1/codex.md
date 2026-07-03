**Verdict**
Ship, high confidence. I would change this if a focused E2E showed `--no-live-status` still advertises or writes `status.*`, or if a normal post-activate return path reaches the new `finally` without first calling `finish()`.

**Strongest Objections**
The only meaningful objection left is structural: `_execute_run()` now relies on every normal return path in `_run_after_activate()` and its synthesis/revision callees stamping a terminal status before returning. I checked the visible paths and they do, but future returns could regress this easily. Keep the abort-guard tests.

The docs still slightly overstate “no `.tmp` is ever left behind”; `_atomic_write_text()` cleans up on Python exceptions, but SIGKILL/process death can leave a temp file. Not merge-blocking for a best-effort live view.

`retry` remains in the status vocabulary but is not emitted by `run_round()`; the code explicitly defers retry hooks. This is acceptable, but the schema/docs should not imply retry events are currently observable.

**Recommended Execution Sequence**
1. Merge this P3 fix as-is.
2. Before release, run the focused status suite plus the full suite in a writable environment.
3. Add a small future guard test for any new normal return path after `activate()`: completed status must not be `interrupted`.
4. Consider a docs-only follow-up to soften the `.tmp` claim and clarify retry is reserved.

**Invariants And Guardrails**
`config.live_status` must remain the single source for both CLI tracker wiring and artifact-tree preview.

No `status.*` writes before `tracker.activate()`.

Every post-activate path must end with `finish()` or be stamped by `finish_if_unfinished()`.

`--no-live-status` must suppress both files and additive terminal progress lines.

Status read/render paths must tolerate malformed input without raw tracebacks.

**Risks / Missing Evidence**
I could not run the test suite in this read-only sandbox because temp-file creation is blocked; an import-level sanity check passed. The claimed “1426 OK” still needs trust in the independent writable run.

The best-effort writer is serialized through `StatusTracker`, but `_atomic_write_text()` itself is not safe as a general concurrent helper with its fixed temp name. Keep it private.

**Concrete Evidence**
Prior blocker #1 is cleared: [config.py](skills/advisory-board/scripts/_conductor/config.py:119) adds `live_status`, [config.py](skills/advisory-board/scripts/_conductor/config.py:797) resolves it from `not args.no_live_status`, and [artifacts.py](skills/advisory-board/scripts/_conductor/artifacts.py:319) gates the `status.*` artifact-tree line.

Prior blocker #2 is cleared: [cli.py](skills/advisory-board/scripts/_conductor/cli.py:382) still writes refusal manifest files, while [status.py](skills/advisory-board/scripts/_conductor/status.py:34) and [SKILL.md](skills/advisory-board/SKILL.md:145) now describe the true invariant.

Abort refresh is addressed: [cli.py](skills/advisory-board/scripts/_conductor/cli.py:408) wraps post-activate execution, and [status.py](skills/advisory-board/scripts/_conductor/status.py:232) stamps only unfinished runs.

Malformed readers are hardened: [status.py](skills/advisory-board/scripts/_conductor/status.py:352) guards `event_tuples()`, and [status.py](skills/advisory-board/scripts/_conductor/status.py:408) normalizes non-dict render input.

**Ask Other Seats**
Challenge whether the broad `finally` can mislabel any successful future path as `interrupted`.

Challenge the RH-1 wording around run-dir creation versus status writes.

Challenge whether the status schema should include `waiting`/`queued` or reserve `STATES` for events only.

VERDICT: ship

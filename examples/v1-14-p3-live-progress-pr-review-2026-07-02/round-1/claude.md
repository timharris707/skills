I've verified the load-bearing claims against the actual repo. Here is my review.

---

# Claude seat review — v1.14 P3 live progress view

**Role lens: architecture & systems — invariants, failure modes, adversarial.**

I traced the diff against the real tree (`render_artifact_tree` call site + convention, `now_stamp` determinism, the existing exact-match goldens, the egress-block path). The core engineering is careful and the load-bearing invariants hold. I found one concrete deviation from the codebase's *own explicit convention* that the prior reviewers' summary did not flag, plus a security-relevant documentation overclaim. Both are cheap. Neither breaks correctness.

## 1. Verdict

**CAUTION — confidence: high.** The concurrency model, RH-1 gating, atomic writer, and zero-drift-on-existing-artifacts claims all survive scrutiny. But the new `status.json status.html` line in `render_artifact_tree` is **unconditional**, which contradicts the tree's established "stay truthful about what a `--no-X` run writes" convention (proven three blocks up for `--no-endorse`), and the CHANGELOG/SKILL/docstring claim that an "egress-refused run leaves no dir" is contradicted by the code and an existing test. Fold in those two truthfulness fixes and it ships.

*What would change it to SHIP:* gate the tree's status line on live-status-enabled (mirroring `config.endorse` at `artifacts.py:304`) and correct the "egress-refused leaves no dir" wording to "leaves no `status.*`." *What would change it to BLOCK:* evidence that the `on_seat` callback or the lock is bypassed under the real executor (I found no such path by inspection, but see §7).

## 2. Strongest objections

**O1 — The artifact tree lies to a `--no-live-status` run (violates the repo's own stated convention). [primary]**
`render_artifact_tree` unconditionally appends the status line (`artifacts.py:309–315`). But every other optional artifact in that same function is gated on config, and the endorsement block carries an explicit comment stating the principle:

> `artifacts.py:301–303` — *"Listed only when the pass runs (ON by default; `--no-endorse` drops these lines so the tree stays truthful about what a `--no-endorse` run writes)."*

`--no-live-status` is the exact analog of `--no-endorse` (on-by-default, opt-out flag), yet its files are listed unconditionally with only a parenthetical hedge instead of being dropped. Test `test_artifact_tree_shows_synthesizer_when_on` (`test_run_board.py:7259–7265`) proves the tree is *supposed* to be conditional (`assertNotIn("synthesizer/", off)`). The fix is well-precedented but needs plumbing: `no_live_status` lives on `args` (`cli.py:328,1235`), **not** on `RunConfig` (grep of `config.py` is empty), so a `live_status` bool must be added to the config exactly as `synthesize`/`endorse`/`output` are, then the line gated on it. `test_no_live_status_opts_out` (`test_run_board.py`) checks only that the *files* are absent — it never asserts the stdout tree omits them, so this ships untested.

**O2 — "Egress-refused run leaves no dir" is false. [security-relevant docs]**
Stated in three places (CHANGELOG: *"A preflight-NO-GO or egress-refused run leaves no out dir — and no `status.*`"*; SKILL.md: *"a preflight-NO-GO / egress-refused run still leaves no dir"*; `status.py` docstring: *"a preflight-NO-GO or egress-refused run leaves NO out dir"*). The egress-block path in `cli.py` writes `egress-manifest.md` + `sensitivity.json` into `config.out_dir` **before** `die()`, and the existing test `test_run_blocks_redacted_without_yes` (`test_run_board.py:795–799`) asserts *"manifest is written for review."* So an egress refusal **does** leave a dir. What's actually true — and what matters for RH-1 — is that it leaves **no `status.*`** (because `activate()` hasn't run) and **no packet egresses**. The code is correct; the prose overstates a consent-gate guarantee, which is the kind of inaccuracy you least want in the invariant docs of a security-sensitive tool. Only the preflight-NO-GO case genuinely leaves no dir (`test_no_go_preflight_leaves_no_status`), and only that case is tested.

**O3 — An uncaught exception / SIGINT after `activate()` leaves a forever-refreshing "running/queued" page. [robustness]**
Every *controlled* exit calls `tracker.finish(...)` before `die()` (verified: NO-GO, egress-block, <2 usable r1, collapse, synthesis, revision, no-synth all stamp `finished`), so `status.html` goes static (`meta_refresh` is gated on `finished is None`, `status.py`). But there is **no `try/finally`** around the post-`activate()` run body. If `run_round` raises or the process is interrupted mid-fan-out, `finish()` never fires, the last-written page keeps `finished=None`, and the browser reloads a dead run showing `queued`/`running` forever. The PR flags the seat-map half of this as "cosmetic/honest"; I'd sharpen it: a page that *looks live* for a *dead* run is mildly misleading, and the fix is a small `try/except` that stamps `finish("interrupted", …)` on unexpected exit. Low severity, not a blocker, but worth the ~6 lines.

## 3. Recommended execution sequence

1. Add `live_status: bool` to `RunConfig` (set from `args.no_live_status` in `resolve_config`), mirroring `endorse`. Gate the `artifacts.py:309–315` status line on it. Add a `test_artifact_tree_omits_status_when_no_live_status` assertion (`assertNotIn("status.json", tree_off)`) to lock the convention.
2. Correct the "egress-refused leaves no dir" wording in CHANGELOG, SKILL.md, and the `status.py` docstring → "leaves no `status.*` (and nothing egresses); the egress-manifest is still written locally for review." Optionally add an E2E assertion that an egress-block leaves no `status.json`.
3. (Recommended, not required) Wrap the post-`activate()` body of `_execute_run` in `try/except` that calls `tracker.finish("interrupted", …)` on unexpected exit, so the tracker page is guaranteed static on every terminal path.
4. Re-run the full suite; confirm 1419 → 1420+ with the new assertions and no regression on the pinned-line / dry-run-determinism tests.

## 4. Invariants and guardrails (verified holding)

- **Thread-safety:** one `threading.Lock`; every mutating public method (`stage`/`round_started`/`round_done`/`seat`/`finish`/`activate`) acquires it, and `_flush` (seq++, events.append, `_set_seat`, print, `_write_files`) runs under the caller's lock. `json.dumps(self._doc)` executes **inside** the lock → the serialized snapshot cannot tear. The fixed temp name (`.status.json.tmp`) is safe **because** writes are serialized. The `_warned` flag is set under the lock → no double-warn race. ✔
- **No stdout garbling:** worker-thread tracker prints are serialized by the lock; the main thread does not print during a round (it blocks inside `run_round` until all seats return, then prints the round table). So tracker lines and conductor lines are never concurrent. ✔
- **RH-1 (for `status.*`):** `_write_files` early-returns while `not self._active`; `activate()` is called only after `write_pre_spawn_artifacts`, which is only reached post-approval (the `if not approval.approved: die()` guard precedes it). First disk write of `status.*` is post-consent. ✔
- **Atomic writes / torn reads:** sibling temp + `os.replace` on the same filesystem → atomic on APFS (macOS) and ext4/tmpfs (CI linux); reader sees old-or-new inode, never partial. `.tmp` unlinked on failure. ✔
- **Zero drift on existing artifacts:** the tracker writes only `status.json`/`status.html`; `render_artifact_tree` is **stdout-only** (`cli.py:286` `print(...)`), never persisted to a file, so no existing artifact file changes bytes; existing tree tests are substring-based (`7263–7265`, `12391`); the only exact `listdir` golden is on `endorsement/` (`test_run_board.py:11723`), not the top-level dir. ✔
- **Determinism of pinned surfaces:** `now_stamp` (`constants.py:326`) obeys `ADVISORY_BOARD_NOW_TS`; the event-sequence golden uses `event_tuples` = `(stage, seat, round, state)` only — `seq`, `detail`, and timestamps are excluded; the HTML render omits event `at` (`test_render_omits_no_timestamp_in_structural_golden`); the sole full-stdout determinism test is `--dry-run` (`test_run_board.py:778–793`), which prints only the *static* tree line, not the wall-clock terminal lines. ✔

## 5. Risks, stale assumptions, missing evidence

- **`elapsed_s` is wall-clock** (`rounds.py:56`) and flows into the `done` terminal line (`{result.elapsed_s:.0f}s`) and the status.json `detail`. Confined to non-pinned surfaces today (the only exact-equality stdout test is dry-run, which never reaches a real spawn). *Risk:* if anyone later adds a full-stdout golden for a real run, or asserts an exact `detail`, it will flake. Guardrail is implicit, not enforced — worth a one-line comment at the format site.
- **Dead state vocabulary:** `STATES` includes `retry`/`skipped`, and `_STATE_GLYPH`/`_SEAT_STATE_LABEL` render them, but the wiring (`_seat_cb`, `run_round._notify`) only ever emits `running`/`done`/`dropped`. `rounds.py` explicitly defers the retry hook. Harmless, but the HTML/CSS carries unreachable branches — flag as intentional-dead or drop.
- **Synthesis/revision/endorsement are stage-granular, not per-seat.** Those phases spawn seats without an `on_seat` bridge, so the live view shows them as coarse `started/done` stages. Reasonable scope, but the tracker page will show the seat *map* frozen at round-N states while a synthesis seat runs — mildly confusing on a long synthesis. Acceptable; note it.
- **Cross-file skew:** `_write_files` replaces `status.json` then `status.html` as two separate atomic ops; a reader between them sees new-json/old-html. Self-heals on the next event and the html regenerates from the json's data anyway. Cosmetic.
- **Lock held across disk + stdout I/O** in worker threads. At a handful of transitions per round this is negligible, but it does mean a slow/full disk serializes the fan-out's callbacks. Best-effort semantics make this acceptable; worth being conscious of if seat counts grow.
- **Missing evidence:** no test asserts (a) the opt-out stdout omits the status line (O1), (b) an egress-refusal leaves no `status.*` (O2), or (c) the page goes static on an uncaught crash (O3). The "1419 OK, independently verified" claim is credible but I did not run it; my thread-safety conclusion is by inspection, not runtime stress.

## 6. Concrete evidence

- `artifacts.py:309–315` — unconditional status line, vs. the conditional convention at `:268–269` (grounding), `:276–281` (echo-score), `:282–286` (synthesizer), `:287–308` (revised-draft/endorsement). The governing comment is `:301–303`.
- `test_run_board.py:7259–7265` — proves the tree is expected to be config-conditional (`assertNotIn("synthesizer/", off)`).
- `cli.py:328` `getattr(args, "no_live_status", False)` and `cli.py:1235` (the flag def); grep of `config.py` for `live_status` is **empty** → the flag is not on `RunConfig`, so the O1 fix needs config plumbing.
- `test_run_board.py:795–799` `test_run_blocks_redacted_without_yes` — *"manifest is written for review"* → egress-refusal **does** leave a dir, contradicting the CHANGELOG/SKILL/docstring "leaves no dir."
- `cli.py` egress-block path: writes `egress-manifest.md` + `sensitivity.json`, then `tracker.finish("egress-blocked", …)` (pre-`activate()` → no `status.*`), then `die(…)`.
- `status.py` `_write_files`: `if not self._active: return` — the RH-1 gate. `activate()` called at `cli.py` immediately after `write_pre_spawn_artifacts`.
- `status.py` `render_status_html`: `meta_refresh = '<meta http-equiv="refresh" content="2">' if running else ""` where `running = finished is None` — the static-once-finished mechanism, which depends on `finish()` being called (no `try/finally` guarantees it on crash).
- `constants.py:326` `def now_stamp()`; unit test pins `doc["started"] == "2026-06-25T12:00:00"` via `ADVISORY_BOARD_NOW_TS`.
- `test_run_board.py:778–793` — the only exact full-stdout determinism test is `--dry-run`; unaffected by the real-run terminal lines.

## 7. What I'd ask the other seats to challenge

- **Codex (execution/behavior):** run the real suite with `-k Status` under `-j` parallelism and, ideally, `pytest-randomly` + a repeat flag, to stress the lock empirically — does the event-tuple golden ever tear, or a `.tmp` ever linger, under true thread interleaving? Confirm my "main thread never prints during a round" claim by inspecting `run_round`'s executor join.
- **Gemini (breadth/consistency):** grep the whole suite for any *full-buffer* stdout equality on a real `run` (not substring), and for any committed `examples/` transcript that could capture the tree — my claim that none exist rests on the suite being green, not on an exhaustive scan.
- **Whoever owns egress/consent:** is writing `egress-manifest.md` on refusal in tension with *any* reading of RH-1, and does the "leaves no dir" prose appear elsewhere (SECURITY notes, D5 text) where the inaccuracy would compound?
- **Any seat:** contest my downgrade of the "seats queued forever" gap from "cosmetic" to "mildly misleading" — is a forever-refreshing dead-run page acceptable as-is, or does D-something require the tracker to self-terminate its refresh?

VERDICT: caution

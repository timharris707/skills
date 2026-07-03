# Board packet — round 2 (cross-reading: summaries — structured digest)

## Where the board stands after round 1

Verdicts: claude=caution · codex=caution
Agreement: unanimous: caution
Shared evidence (raised by ≥2 seats): `--no-live-status`, `activate()`, `config.out_dir`, `die()`, `egress-manifest.md`, `sensitivity.json`, `status.html`, `status.json`, `status.py`

## By topic

### Verdict

- **claude:** **CAUTION — confidence: high.** The concurrency model, RH-1 gating, atomic writer, and zero-drift-on-existing-artifacts claims all survive scrutiny. But the new `status.json status.html` line in `render_artifact_tree` is **unconditional**, …
- **codex:** CAUTION, high confidence. I would change this to SHIP if the RH-1 wording/code/tests are reconciled, `status.json` schema handling is made robust to malformed inputs, and the opt-out dry-run preview is made truthful.

### Strongest objections

- **claude:** **O1 — The artifact tree lies to a `--no-live-status` run (violates the repo's own stated convention). [primary]** `render_artifact_tree` unconditionally appends the status line (`artifacts.py:309–315`). But every other optional artifact …
- **codex:** 1. RH-1 is internally inconsistent. The PR says egress-refused runs leave no out dir, but the refused path creates it and writes refusal artifacts before the tracker is active: `scripts/_conductor/cli.py:377-387`. Existing tests also …

### Recommended execution sequence

- **claude:** 1. Add `live_status: bool` to `RunConfig` (set from `args.no_live_status` in `resolve_config`), mirroring `endorse`. Gate the `artifacts.py:309–315` status line on it. Add a `test_artifact_tree_omits_status_when_no_live_status` assertion …
- **codex:** 1. Decide the RH-1 contract precisely: “no status writes before approval” vs “no run-dir writes before approval.” Update `CHANGELOG.md`, `SKILL.md`, `status.py` comments, and add an egress-refused test. 2. Amend the schema docs/tests so …

### Invariants & guardrails

- **claude:** - **Thread-safety:** one `threading.Lock`; every mutating public method (`stage`/`round_started`/`round_done`/`seat`/`finish`/`activate`) acquires it, and `_flush` (seq++, events.append, `_set_seat`, print, `_write_files`) runs under the …
- **codex:** Keep tracker mutation under `StatusTracker._lock`; keep `activate()` after `write_pre_spawn_artifacts()`; status write failures must warn once and never affect verdict; `--no-live-status` must suppress files and progress lines; status …

### Risks, stale assumptions & missing evidence

- **claude:** - **`elapsed_s` is wall-clock** (`rounds.py:56`) and flows into the `done` terminal line (`{result.elapsed_s:.0f}s`) and the status.json `detail`. Confined to non-pinned surfaces today (the only exact-equality stdout test is dry-run, which …
- **codex:** The claimed full suite and artifact diff are not independently verifiable from the material alone. There is no test for egress-refused status absence, corrupt status rendering, concurrent writer temp collision, or dry-run with …

### Concrete evidence

- **claude:** - `artifacts.py:309–315` — unconditional status line, vs. the conditional convention at `:268–269` (grounding), `:276–281` (echo-score), `:282–286` (synthesizer), `:287–308` (revised-draft/endorsement). The governing comment is `:301–303`. …
- **codex:** `cli.py:381-386` creates `config.out_dir`, writes `egress-manifest.md` and `sensitivity.json`, then calls `tracker.finish()` while inactive. `CHANGELOG.md:28` and `SKILL.md:145` say egress-refused leaves no dir. `status.py:157` emits …

### Challenges to the board

- **claude:** - **Codex (execution/behavior):** run the real suite with `-k Status` under `-j` parallelism and, ideally, `pytest-randomly` + a repeat flag, to stress the lock empirically — does the event-tuple golden ever tear, or a `.tmp` ever linger, …
- **codex:** Ask whether egress-refused manifest writing is an accepted existing exception to RH-1, whether dry-run stdout is a D5-pinned surface, and whether a post-activation abort should finalize `status.html` or remain live as an honest crash …

# Conductor tests

Tests for `scripts/run_board.py` (the M1–M5 conductor; implemented as the
`scripts/_conductor/` package behind a thin `run_board` façade) and the sibling
scripts it calls (`board_verdict.py`, `verify_evidence.py`, `render_verdict.py`).
Python 3 standard library only; they run the whole pipeline — including the real
round-1 and round-2 fan-outs — against **mock CLIs** on `PATH`, so no provider
tokens are spent and nothing leaves the machine.

## Run

```
# from skills/advisory-board/
python3 -m unittest discover -s tests -p 'test_*.py'

# verbose
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The suite prepends `tests/mocks/` to `PATH` itself and pins the clock via
`ADVISORY_BOARD_NOW` / `ADVISORY_BOARD_NOW_TS` for deterministic output — no setup
needed beyond a Python 3 interpreter.

## What's here

| Path | Purpose |
| ---- | ------- |
| `test_run_board.py` | the suite (registry, YAML codec, config, packet, preflight, egress gate, end-to-end run flow, **round-1 fan-out: shape check, failure classifier, model-answered parser, retry/timeout, hash binding, process-group kill**, **round 2: cross-reading packets (full/summaries/none), dropped-seat exclusion, distinct per-round packet hashes, `run-metadata.tsv`, `--rounds`/`--cross-reading` behavior**, `--from-recipe`, delegation, toolchain currency + model self-heal, setup doctor, **persistent runs root + `history`** (v1.11 #5: the `<slug>-<date>` default dir, `$ADVISORY_BOARD_RUNS_ROOT`/`--runs-root`/`--ephemeral` precedence + contradictions, collision suffix, and the history table's graceful `incomplete` degradation)) |
| `mocks/{claude,codex,gemini,agy,ollama}` | banner-accurate CLI stubs; behavior switched by `MOCK_<SEAT>_MODE` (`go`/`nogo_version`/`nogo_smoke`/`empty`/`degraded`/`timeout`/`model_not_found`/`stub`; gemini also `model_proposal`) and argv captured to `MOCK_ARGV_LOG`. The smoke ping returns `ready`; a round-1 prompt returns a full multi-section review (with a `model:` banner on stderr) so a single test exercises preflight **and** the fan-out — `stub` returns a short plan-style reply (the §13 shape-check failure). `claude`/`codex`/`agy` also mock `update` (force failure with `MOCK_<SEAT>_UPDATE_FAIL=1`); `agy` also mocks `models`. (`agy` is the Antigravity seat — `MOCK_AGY_VERSION` sets its reported version. `ollama` is the local seat — prompt on stdin, no `model_not_found`/`update` arms; `MOCK_OLLAMA_VERSION` sets its reported version, default `0.5.0`) |
| `mocks/{npm,brew}` | package-manager stubs for the toolchain check/update: latest version is env-controlled (`MOCK_NPM_CLAUDE`/`MOCK_NPM_CODEX`, `MOCK_BREW_GEMINI`/`MOCK_BREW_OLLAMA` formulae, `MOCK_BREW_CASK` for the antigravity cask; default `9.9.9` → stale); `brew upgrade` fails with `MOCK_BREW_UPGRADE_FAIL=1` |
| `fixtures/sample-plan.md` | a small, stable source for deterministic runs |
| `fixtures/{verdict-m5.json, src/charges.py, packet.txt}` | M5 evidence-resolution fixtures — a `@2` verdict exercising every kind/status, a 15-line source file (`charge_idempotent`), and a captured packet a `source` quote resolves against |

The M5 canonical-verdict layer (`TestSchemaV2Validation`, `TestGateAbstain`,
`TestEvidenceResolution`, `TestRenderVerdict`, `TestM5ChainDelegation`) tests the
schema `@2` validation, the abstain gate, evidence resolution/stamping, and the
`verify` → `consensus` → `validate` chain (see "the M5 invariants" below).

## The safety properties the suite locks

These are the M2 invariants — if any regresses, a test fails:

- **The egress gate blocks non-public material without approval** (`TestEgressGate`,
  `TestRunFlow.test_run_blocks_redacted_without_yes`) — and on a block, no prompt
  is materialized (the pre-spawn hard stop).
- **Preflight gates before egress** (`test_preflight_gates_before_egress`) — a
  NO-GO board never writes an egress manifest.
- **Gate-mode isolation flags reach the real argv** (`TestIsolationReachesArgv`) —
  asserted both at the registry (`build_argv`) and end-to-end via `MOCK_ARGV_LOG`.
- **Consent is tiered by sensitivity** — public proceeds after disclosure, redacted
  blocks for hash-bound approval, local-only refuses external egress outright.
- **The run-recipe round-trips** through the restricted YAML codec
  (`TestYamlCodec`).
- **Toolchain updates are consent-gated and model ids stay pinned**
  (`TestToolchainUpdate`, `TestModelProposal`) — a missing package manager reads
  "unknown" not "stale" (never a spurious update), a non-TTY without `--yes` is a
  no-op, and an unresolvable pinned id yields a *proposed* fallback, not a silent
  swap.
- **Graceful degradation for partial setups** (`TestGracefulDegradation`) — an
  absent CLI reads `missing` (not `unknown`) and prints its install command;
  `--install` is consent-gated and never implies an account; and when fewer than
  two seats are usable, preflight/run emit actionable guidance (install vs auth,
  same-provider / local-seat fallbacks) instead of dead-ending.

The M3 round-1 fan-out adds its own invariants:

- **The egress hash is re-asserted at the point of no return**
  (`TestRound1FanOut.test_hash_drift_refuses_to_spawn`) — if the packet no longer
  matches the approved content hash, nothing spawns; each seat is fed the exact
  approved blob, so the bytes that leave equal what consent was bound to.
- **The §13 failure protocol** (`TestClassifyRound1`, `TestRound1FanOut`) — a
  short/plan-shaped reply fails the shape check (`InvalidOutput`, the
  {{CLAUDE_OUTPUT_OVERRIDE}} detection); `Timeout`/`InvalidOutput` retry once,
  every other class drops immediately; auth is judged on stderr only so a review
  that *discusses* 401s is not misread as an auth failure.
- **Honest provenance** (`TestModelAnsweredParser`) — the answering model is parsed
  from stderr (never mined from the review prose) and is `None` ("unknown") when
  unreported; antigravity is structurally `None` (it silently substitutes models).
- **Hung seats are reaped as a process group**
  (`TestSpawnProcessGroupKill`) — a timed-out child's backgrounded grandchildren
  are killed, not orphaned (the gap `subprocess.run(timeout=)` alone would leave).

The M4 round-2 layer adds:

- **Round 2 cross-reads correctly** (`TestRound2Builders`, `TestRound2FanOut`) —
  `full`/`summaries`/`none` build the right packet; only *usable* round-1 seats
  continue; the source is re-supplied (each spawn is stateless) and peers are
  wrapped as data-under-review.
- **Each round is its own egress with its own hash** (`TestRound2RunLevel`) —
  `run-metadata.tsv` carries one row per seat per round; round-1 and round-2 rows
  carry distinct packet hashes; the round-2 `.raw` records that it reuses the run's
  approval rather than a fresh hash-bound consent.
- **`--rounds`/`--cross-reading` honored** — `--rounds 1` skips round 2; `none`
  skips the board packet; `--rounds 3`/`auto` caps at round 2 with a v1.x note;
  `<2` usable round-1 reviews skips round 2 but still records what was captured.

The M5 canonical-verdict layer adds:

- **The schema `@2` validates strictly** (`TestSchemaV2Validation`) — `@1` files
  still pass; a bad evidence kind/status, a `code` citation missing `path` or
  `line`/`symbol`, or a `source` citation missing its `quote` is rejected with the
  schema exit code; a `judgment` citation needs no referent.
- **Evidence resolution respects quarantine** (`TestEvidenceResolution`) — `code`
  `path:line`/`symbol` resolves against the source (in-range → verified, out-of-range
  / absent-symbol → refuted, missing-file / no-source → unverified); `source` quotes
  resolve against the **captured packet only** (present → verified, absent → refuted,
  no-packet → unverified — it never reaches the URL); `command` is unverified by
  default (re-execution is opt-in), and resolves against re-execution under
  `--allow-program NAME` (exit matches `expect_exit` and `expect` substring present
  → verified, mismatch → refuted); `judgment` is left unstamped.
- **The gate abstains in the torn regime** (`TestGateAbstain`, `TestGateReconcileVerdictVsBoard`,
  `TestGateRefutedAnywhere`) — `--gate` returns exit `3` ("human required") when the seats that
  ran straddle the `--fail-on` line with no strict majority, when the declared `verdict` clears
  the gate while a majority of seats trip it (a verdict that contradicts its board — the
  injected-"ship" case), or when any citation is refuted. Synthesis *escalation* (a declared
  verdict that trips the gate) still fails decisively; the decision reads observed
  `round_verdicts`, never the gameable `confidence`.
- **md + HTML render FROM the verdict** (`TestRenderVerdict`) — `final-consensus.md`
  carries the decision, the evidence trail with stamps, and the couldn't-verify
  bucket; the derived `handoff-data.json` round-trips cleanly through
  `render_handoff.py`; per-round prose is pulled from `round-N/<seat>.md` when a run
  dir is given, never invented.
- **The chain wires through the conductor** (`TestM5ChainDelegation`) — `verify` /
  `consensus` / `validate` delegate to the sibling scripts, the abstain exit
  propagates, and `run` prints the synthesis-then-chain guidance.

# Conductor tests

Tests for `scripts/run_board.py` (the M1+M2 conductor). Python 3 standard library
only; they run the whole pipeline against **mock CLIs** on `PATH`, so no provider
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
| `test_run_board.py` | the suite (registry, YAML codec, config, packet, preflight, egress gate, end-to-end run flow, `--from-recipe`, delegation, toolchain currency + model self-heal) |
| `mocks/{claude,codex,gemini,agy,ollama}` | banner-accurate CLI stubs; behavior switched by `MOCK_<SEAT>_MODE` (`go`/`nogo_version`/`nogo_smoke`/`empty`/`degraded`/`timeout`/`model_not_found`; gemini also `model_proposal`) and argv captured to `MOCK_ARGV_LOG`. `claude`/`codex`/`agy` also mock `update` (force failure with `MOCK_<SEAT>_UPDATE_FAIL=1`); `agy` also mocks `models`. (`agy` is the Antigravity seat — `MOCK_AGY_VERSION` sets its reported version. `ollama` is the local seat — prompt on stdin, no `model_not_found`/`update` arms; `MOCK_OLLAMA_VERSION` sets its reported version, default `0.5.0`) |
| `mocks/{npm,brew}` | package-manager stubs for the toolchain check/update: latest version is env-controlled (`MOCK_NPM_CLAUDE`/`MOCK_NPM_CODEX`, `MOCK_BREW_GEMINI`/`MOCK_BREW_OLLAMA` formulae, `MOCK_BREW_CASK` for the antigravity cask; default `9.9.9` → stale); `brew upgrade` fails with `MOCK_BREW_UPGRADE_FAIL=1` |
| `fixtures/sample-plan.md` | a small, stable source for deterministic runs |

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

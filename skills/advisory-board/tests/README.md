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
| `test_run_board.py` | the suite (registry, YAML codec, config, packet, preflight, egress gate, end-to-end run flow, `--from-recipe`, delegation) |
| `mocks/{claude,codex,gemini}` | banner-accurate CLI stubs; behavior switched by `MOCK_<SEAT>_MODE` (`go`/`nogo_version`/`nogo_smoke`/`empty`/`degraded`/`timeout`) and argv captured to `MOCK_ARGV_LOG` |
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

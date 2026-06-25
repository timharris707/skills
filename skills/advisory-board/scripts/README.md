# Advisory Board Scripts

`run_board.py` is the conductor that drives a board run; the others are optional helpers that wire a board's `verdict.json` into CI and tooling (gating, formatting, deterministic HTML rendering). Python 3 standard library only; no install step.

| Script | Does | Reference |
| ------ | ---- | --------- |
| `run_board.py` | The **conductor** (M1–M4): deterministic seat-adapter registry, `--dry-run`, toolchain currency (`toolchain` — check/update stale CLIs, propose fallback model ids), executable preflight (GO/NO-GO), a hash-bound egress/quarantine gate before any provider call, the **round-1 fan-out** (real spawn, §13 failure protocol, per-seat `round-1/` artifacts), and **round 2** (cross-reading `board-packet-round-2.md`, debate fan-out, `run-metadata.tsv`). Calls the scripts below; never reimplements them. Implemented as the [`_conductor/`](#package-layout) package — `run_board.py` is a thin façade (re-exports the API + the CLI entry). | `design/run-board-conductor.md` |
| `board_verdict.py` | Validate `verdict.json`; gate CI on the verdict (`--gate`). | `references/verdict-schema.md` |
| `format_output.py` | Render `verdict.json` as a TL;DR, PR comment, Slack message, or normalized JSON. | `references/output-formats.md` |
| `render_handoff.py` | Render `final-consensus.html` from a `handoff-data.json` — deterministic, fails on any leftover placeholder. | `references/handoff-template.html` |

## Package layout

The conductor's implementation lives in the `_conductor/` package; `run_board.py`
is a thin façade that re-exports the entire public API (so `import run_board`
keeps working) and stays the CLI entry point. The modules are layered as a
dependency DAG — each imports only from those above it:

| Module | Holds |
| ------ | ----- |
| `constants.py` | Exit codes, schema ids, `PROVIDERS`, lens presets, failure classes, and the `die`/`now_date`/`now_stamp` primitives. |
| `registry.py` | The seat-adapter registry (design §6): `SeatAdapter`, the per-seat `*_argv`/version/update/install builders, the model-answered + model-not-found parsers, semver helpers, and `REGISTRY`. |
| `config.py` | `SourceSpec`/`SeatConfig`/`RunConfig` and everything that turns CLI args (or a recipe) into a `RunConfig`. |
| `spawn.py` | The subprocess spawn helper (process-group-killed on timeout) and the §13 failure protocol — classification, the round-1 shape check, auth/retry signatures. |
| `prompts.py` | The round-1/round-2 prompt templates and the pure string builders (delimit-and-neutralize). |
| `toolchain.py` | Toolchain currency (design §7a): check/update/install CLIs on consent and propose a fallback model id. |
| `egress.py` | The egress packet + gate (design §8, §12): packet assembly (both rounds), the content hash, tiered consent, the manifest, and the pre-spawn hard stop. |
| `preflight.py` | Executable preflight (design §7): per-seat probes, the GO/NO-GO table, and board guidance. |
| `recipe.py` | The restricted-YAML codec for `run-recipe.yaml` plus recipe↔config conversion/validation. |
| `artifacts.py` | Renderers/writers for the pre-spawn artifacts: run-card, `sensitivity.json`, the artifact tree, and the run-metadata stamp (md + tsv). |
| `rounds.py` | The round fan-out (design §11/§12/§13): `run_round`/`_run_seat_round` and the per-seat round artifacts/renderers. |
| `cli.py` | The argparse front end: the `cmd_*` handlers, the delegation shim, and `main()`. |

The split is behavior-preserving — the test suite (`tests/`) imports `run_board`
exactly as before and exercises the same public surface.

## Quick start

```
# check each seat CLI vs its latest release (read-only): current / STALE / missing / unknown
python3 scripts/run_board.py toolchain

# update stale CLIs and/or install absent ones (consent-gated; --yes approves unattended)
python3 scripts/run_board.py toolchain --update
python3 scripts/run_board.py toolchain --install   # installs absent CLIs (account/auth still required)

# preview a run — config, run-card, preflight plan, egress manifest, artifact tree (no spawn)
python3 scripts/run_board.py run --source plan.md --dry-run

# probe the seats (GO/NO-GO); exits non-zero if fewer than two are GO
python3 scripts/run_board.py preflight --source plan.md

# full run: preflight + egress gate + round 1 + round 2 (cross-reading debate)
# -> round-{1,2}/<seat>.md + .raw, board-packet-round-2.md, run-metadata.tsv
# (stops at the last round's boundary; synthesis -> verdict.json is M5)
python3 scripts/run_board.py run --source plan.md --sensitivity public --rounds 2 --cross-reading summaries

# validate and summarize
python3 scripts/board_verdict.py path/to/verdict.json

# gate a merge: non-zero exit when the board says "block"
python3 scripts/board_verdict.py path/to/verdict.json --gate

# turn the verdict into a PR comment
python3 scripts/format_output.py path/to/verdict.json --format pr

# render the HTML handoff deterministically from structured data
python3 scripts/render_handoff.py path/to/handoff-data.json -o final-consensus.html
```

> Paths above are relative to the **skill directory** — `skills/advisory-board/` in this repo, or the installed skill root (e.g. `~/.codex/skills/advisory-board/`) — the same convention as every `references/…` path in the skill. Run the scripts from there, or prefix them with that directory; `scripts/board_verdict.py` won't resolve from the repo root.

`board_verdict.py` and `format_output.py` read the `verdict.json` a *completed* run emits next to `final-consensus.md` (produced once the conductor reaches synthesis — M5). `run_board.py` currently stops at the **last round's boundary**: it spawns the board for round 1 and (by default) a cross-reading round 2, capturing each seat's review under `round-1/` and `round-2/`, but does not yet synthesize a `verdict.json` (M5). See the repo-root `examples/payments-idempotency-review/verdict.json` for a filled-in sample, and `references/verdict-schema.md` for the schema.

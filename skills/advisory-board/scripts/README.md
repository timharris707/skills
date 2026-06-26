# Advisory Board Scripts

`run_board.py` is the conductor that drives a board run; the others are optional helpers that wire a board's `verdict.json` into CI and tooling (gating, formatting, deterministic HTML rendering). Python 3 standard library only; no install step.

| Script | Does | Reference |
| ------ | ---- | --------- |
| `run_board.py` | The **conductor** (M1–M5): deterministic seat-adapter registry, `--dry-run`, toolchain currency (`toolchain` — check/update stale CLIs, propose fallback model ids), executable preflight (GO/NO-GO), a hash-bound egress/quarantine gate before any provider call, the **round-1 fan-out** (real spawn, §13 failure protocol, per-seat `round-1/` artifacts), **rounds 2…N** (cross-reading `board-packet-round-N.md`, debate fan-out, the `--rounds auto` convergence stop-rule, `run-metadata.tsv`), and the **canonical-verdict chain** (`verify` → `consensus` → `validate`). Calls the scripts below; never reimplements them. Implemented as the [`_conductor/`](#package-layout) package — `run_board.py` is a thin façade (re-exports the API + the CLI entry). | `design/run-board-conductor.md` |
| `board_verdict.py` | Validate `verdict.json` (`@1`/`@2`); gate CI on the verdict (`--gate`) — pass `0` / fail `1` / schema `2` / **abstain `3`** when the board is torn, the declared verdict contradicts the observed board, or a citation is refuted. | `references/verdict-schema.md` |
| `verify_evidence.py` | Resolve a verdict's typed `evidence[]` and stamp each `verified`/`unverified`/`refuted` — `code` `path:line`/`symbol` against the source, `source` quotes against the **captured packet** (never a live fetch), and (M3, opt-in via `--allow-program NAME`) `command` citations by **program-pinned, no-shell re-execution** in an isolated cwd with a structural exit/`expect` match. | `references/verdict-schema.md` |
| `render_verdict.py` | Render `final-consensus.md` **from** the canonical `verdict.json` (evidence trail + couldn't-verify bucket); `--handoff-data`/`--html` derive the HTML via `render_handoff.py`. | `references/verdict-schema.md` |
| `format_output.py` | Render `verdict.json` as a TL;DR, PR comment, Slack message, or normalized JSON. | `references/output-formats.md` |
| `render_handoff.py` | Render `final-consensus.html` from a `handoff-data.json` — deterministic, fails on any leftover placeholder. | `references/handoff-template.html` |
| `render_plan.py` | Render a **planning-document HTML view** deterministically **from** its markdown (`design/<plan>.md`) — milestones / phases / checklists / per-phase testing + validation gate, a computed progress ring and milestone status rail, decisions/risks, and an inlined SVG diagram. The markdown is the source of truth; never hand-edit the HTML — regenerate it. Self-contained (Claude brand fonts embedded). Fails on any leftover placeholder. | `references/plan-template.html` (+ `plan-fonts.css`) |
| `_render_engine.py` | The shared block / `{{TOKEN}}` template engine the renderers reuse (depth-aware block expansion, substitution, comment stripping, the leftover guards, and the opt-in SENTINEL stash for verbatim author content). Imported by `render_handoff.py`/`render_verdict.py`/`render_plan.py`; parameterized by each caller's `BLOCK_KEYS`/`RAW_TOKENS`. | — |

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
| `convergence.py` | The M1 stop-rule signal: `parse_verdict` + `citations` + `board_movement` — a pure function over each seat's `VERDICT:` token and citation set (never the prose) that drives `--rounds auto`. |
| `digest.py` | The M4 structured cross-reading digest (the `summaries` packet): regroups each review by its own section headers + a verdict/citation agreement header. §11-safe — organizes by structure + M1 tokens, never clusters claims by meaning. Builds on `convergence.py`. |
| `prompts.py` | The round-1/round-N prompt templates (each ends with the `VERDICT:` line) and the pure string builders (delimit-and-neutralize); routes the `summaries` packet through `digest.py`. |
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
# (stops at the last round's boundary; synthesis -> verdict.json is the agent's job, §11)
python3 scripts/run_board.py run --source plan.md --sensitivity public --rounds 2 --cross-reading summaries

# --- the canonical-verdict chain (after the agent fills verdict.json,
#     or `run --synthesize` drafts it via the neutral synthesizer seat — M2) ---
# 1. resolve + stamp each typed citation verified/unverified/refuted.
#    add --allow-program NAME (+ optional --allow-command 'REGEX' to pin args) to ALSO
#    re-execute command citations whose argv[0] is NAME (M3; opt-in, program-pinned,
#    no-shell, isolated cwd, curated PATH, scrubbed env, process-group timeout —
#    allowlist only read-only programs you trust; a re-run's output is persisted)
python3 scripts/run_board.py verify <out>/verdict.json --source ./src --run <out>
# 2. render final-consensus.md FROM the verdict (+ --html for the HTML)
python3 scripts/run_board.py consensus <out>/verdict.json --run <out> -o <out>/final-consensus.md
# 3. gate: 0 pass / 1 block / 2 schema / 3 ABSTAIN (board torn or a citation refuted)
python3 scripts/run_board.py validate <out>/verdict.json --gate

# turn the verdict into a PR comment
python3 scripts/format_output.py path/to/verdict.json --format pr

# render the HTML handoff deterministically from structured data
python3 scripts/render_handoff.py path/to/handoff-data.json -o final-consensus.html

# render a PLAN view from its markdown (regenerate whenever the markdown changes)
python3 scripts/render_plan.py ../../design/run-board-v1x.md     # -> run-board-v1x.html
python3 scripts/render_plan.py ../../design/run-board-v1x.md --check   # verify only
```

> Paths above are relative to the **skill directory** — `skills/advisory-board/` in this repo, or the installed skill root (e.g. `~/.codex/skills/advisory-board/`) — the same convention as every `references/…` path in the skill. Run the scripts from there, or prefix them with that directory; `scripts/board_verdict.py` won't resolve from the repo root.

`board_verdict.py`, `verify_evidence.py`, `render_verdict.py`, and `format_output.py` all read the canonical `verdict.json`. `run_board.py run` stops at the **last round's boundary** and prints the synthesis chain: the agent (or one neutral seat) reads `round-N/*.md` and writes `verdict.json` (synthesis stays a reasoning task — §11; the conductor does **not** generate the verdict in code), then `verify` → `consensus` → `validate` run deterministically. See the repo-root `examples/payments-idempotency-review/verdict.json` for a filled-in sample (still `@1`; regenerated via the conductor in M6), and `references/verdict-schema.md` for the `@2` schema with typed evidence and the `abstain` gate.

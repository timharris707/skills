# Advisory Board Scripts

`run_board.py` is the conductor that drives a board run; the others are optional helpers that wire a board's `verdict.json` into CI and tooling (gating, formatting, deterministic HTML rendering). Python 3 standard library only; no install step.

| Script | Does | Reference |
| ------ | ---- | --------- |
| `run_board.py` | The **conductor** (M1–M5): deterministic seat-adapter registry, `--dry-run`, toolchain currency (`toolchain` — check/update stale CLIs, propose fallback model ids), executable preflight (GO/NO-GO), a hash-bound egress/quarantine gate before any provider call, the **round-1 fan-out** (real spawn, §13 failure protocol, per-seat `round-1/` artifacts), **rounds 2…N** (cross-reading `board-packet-round-N.md`, debate fan-out, the `--rounds auto` convergence stop-rule, `run-metadata.tsv`), and the **canonical-verdict chain** (`verify` → `consensus` → `validate`). Runs **persist by default** under `~/.advisory-board/runs/<slug>-<date>/` (override: `$ADVISORY_BOARD_RUNS_ROOT` / `--runs-root`; exact dir: `--out`; throwaway `/tmp`: `--ephemeral`) and `history` lists them. Optionally **repo-grounds** the board: `--repo PATH` (with `--repo-include`/`--repo-exclude` globs) hands every seat a read-only, `.gitignore`-respecting, secret-denylisted **snapshot** of the repository so findings cite real `path:line`; consent binds to the scope hash and `repo-scope-manifest.json` records the scope, and in gate mode it enforces read-XOR-network (refuses an un-isolatable seat — see `references/data-handling.md`). Calls the scripts below; never reimplements them. Implemented as the [`_conductor/`](#package-layout) package — `run_board.py` is a thin façade (re-exports the API + the CLI entry). | `design/run-board-conductor.md` |
| `board_verdict.py` | Validate `verdict.json` (`@1`/`@2`); gate CI on the verdict (`--gate`) — pass `0` / fail `1` / schema `2` / **abstain `3`** when the board is torn, the declared verdict contradicts the observed board, or a citation is refuted. | `references/verdict-schema.md` |
| `verify_evidence.py` | Resolve a verdict's typed `evidence[]` and stamp each `verified`/`unverified`/`refuted` — `code` `path:line`/`symbol` against the source, `source` quotes against the **captured packet** (never a live fetch), and (M3, opt-in via `--allow-program NAME`) `command` citations by **program-pinned, no-shell re-execution** in an isolated cwd with a structural exit/`expect` match. | `references/verdict-schema.md` |
| `render_verdict.py` | Render `final-consensus.md` **from** the canonical `verdict.json` (evidence trail + couldn't-verify bucket); `--handoff-data`/`--html` derive the HTML via `render_handoff.py`. `--shape` picks the view: `full-handoff` (default), `quick-verdict` (skim brief), or `implementation-sequence` (sequence-first — every next action in order with owners where the verdict names them, backed by the blockers and their evidence trails; md + HTML). | `references/verdict-schema.md`, `references/output-formats.md` |
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
| `doctor.py` | Setup doctor (`doctor`): sweeps **every** registered provider via `check_tool` + `preflight_seat` (never re-implements the probes), renders per-provider fix-it steps and the viable-board summary (≥ 2 seats GO) + a suggested first command. No user material egresses. |
| `recipe.py` | The restricted-YAML codec for `run-recipe.yaml` plus recipe↔config conversion/validation. |
| `history.py` | The run-history listing (v1.11 #5): scan the persistent runs root and render the `history` table from each run's `verdict.json` (degrading to `run-recipe.yaml` / `incomplete` for partial or legacy runs — never crashing the listing). |
| `artifacts.py` | Renderers/writers for the pre-spawn artifacts: run-card, `sensitivity.json`, the artifact tree, and the run-metadata stamp (md + tsv). |
| `rounds.py` | The round fan-out (design §11/§12/§13): `run_round`/`_run_seat_round` (pluggable classifier) and the per-seat round artifacts/renderers. |
| `delta.py` | The pure cross-run verdict delta (v1.12 #1): matches blockers/concerns across two runs (exact title > shared citations > guarded similarity) into cleared / still-open / new + trajectory. |
| `revise.py` | `--revise` (v1.12 #1): load a prior run, recover its source (sha-verified), and build the injected prior-verdict digest + source diff (with the sensitivity-escalation gate). |
| `ask.py` | `ask` (v1.12 #4): post-verdict cross-examination — reconstruct the run's board from its recipe, build a run-context packet from that run's own artifacts, re-consent, one-round fan-out, and write `addendum-N.md` + the addenda index / handoff refresh. |
| `cli.py` | The argparse front end: the `cmd_*` handlers, the delegation shim, and `main()`. |

The split is behavior-preserving — the test suite (`tests/`) imports `run_board`
exactly as before and exercises the same public surface.

## Quick start

```
# first run on a new machine? sweep EVERY provider (installed -> version -> auth -> model),
# get per-provider fix-it steps + which boards are viable today (probes/smoke-pings only)
python3 scripts/run_board.py doctor

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
# artifacts land under the persistent runs root by default: ~/.advisory-board/runs/<slug>-<date>/
# ($ADVISORY_BOARD_RUNS_ROOT or --runs-root DIR relocate the root; --out DIR names an exact
#  dir; --ephemeral opts back into a throwaway /tmp/advisory-board-<ts>)
python3 scripts/run_board.py run --source plan.md --sensitivity public --rounds 2 --cross-reading summaries

# per-seat timeouts + a typed digest: a bare --timeout caps every seat, SEAT=SECONDS caps one
# (targeted by id like --model/--lens; unknown ids fail loudly). --digest-format json ALSO
# writes each round's structured digest as board-packet-round-N.json next to the .md —
# the same parsed signals (verdict tokens, agreement, shared citations, per-topic takes).
python3 scripts/run_board.py run --source plan.md --timeout 600 --timeout ollama=1200 --digest-format json
# list past runs from the persistent runs root (date, title, verdict, confidence,
# unanimous, seats, run dir — read from each run's verdict.json; a partial/legacy run
# without one lists as `incomplete`). Local disk read only; respects --runs-root / the
# env root. NOTE: `run --from-recipe` reuses the recipe's recorded dir (rewriting that
# run's artifacts in place) unless --out/--runs-root/--ephemeral name somewhere fresh.
python3 scripts/run_board.py history

# repo-grounded run: seats read a read-only snapshot of ./myrepo and cite real path:line.
# gate mode enforces read-XOR-network — drop any un-isolatable seat (gemini/antigravity).
# -> repo-scope-manifest.json (the scope consent bound to) + grounded round artifacts
python3 scripts/run_board.py run --source plan.md --repo ./myrepo --board claude,codex --mode gate --out <out> --yes
# then verify the grounded run so real path:line citations resolve (a fabricated
# citation stamps `refuted` -> the gate abstains). The snapshot is a temp dir cleaned
# up at run end, so re-verification points --source at the LIVE repo (recorded in
# run-metadata.md): a citation real at approval can refute later if the tree drifted.
python3 scripts/run_board.py verify <out>/verdict.json --source ./myrepo --run <out>

# post-verdict cross-examination: put a follow-up question to a COMPLETED run's board.
# context packet is built ONLY from <out>'s own artifacts (reviewed material + a
# mechanical verdict digest + each addressed seat's own prior review); re-consents the
# new bytes (public discloses; non-public needs --yes); --seat targets one seat.
# -> addendum-N.md + addendum-N/ (prompts + manifest) + addenda.json + a refreshed
#    "Post-verdict addenda" block in final-consensus.md.
python3 scripts/run_board.py ask "Does the dedup blocker still hold if we shard?" --run <out> --yes

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

`board_verdict.py`, `verify_evidence.py`, `render_verdict.py`, and `format_output.py` all read the canonical `verdict.json`. `run_board.py run` stops at the **last round's boundary** and prints the synthesis chain: the agent (or one neutral seat) reads `round-N/*.md` and writes `verdict.json` (synthesis stays a reasoning task — §11; the conductor does **not** generate the verdict in code), then `verify` → `consensus` → `validate` run deterministically. See the repo-root `examples/payments-idempotency-review/verdict.json` for a filled-in sample, and `references/verdict-schema.md` for the `@2` schema with typed evidence and the `abstain` gate.

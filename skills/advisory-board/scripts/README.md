# Advisory Board Scripts

`run_board.py` is the conductor that drives a board run; the others are optional helpers that wire a board's `verdict.json` into CI and tooling (gating, formatting, deterministic HTML rendering). Python 3 standard library only; no install step.

| Script | Does | Reference |
| ------ | ---- | --------- |
| `run_board.py` | The **conductor** (M1–M5): deterministic seat-adapter registry, `--dry-run`, toolchain currency (`toolchain` — check/update stale CLIs, propose fallback model ids), executable preflight (GO/NO-GO), a hash-bound egress/quarantine gate before any provider call, the **round-1 fan-out** (real spawn, §13 failure protocol, per-seat `round-1/` artifacts), **rounds 2…N** (cross-reading `board-packet-round-N.md`, debate fan-out, the `--rounds auto` convergence stop-rule, `run-metadata.tsv`), and the **canonical-verdict chain** (`verify` → `consensus` → `validate`). Runs **persist by default** under `~/.advisory-board/runs/<slug>-<date>/` (override: `$ADVISORY_BOARD_RUNS_ROOT` / `--runs-root`; exact dir: `--out`; throwaway `/tmp`: `--ephemeral`) and `history` lists them. Optionally **repo-grounds** the board: `--repo PATH` (with `--repo-include`/`--repo-exclude` globs) hands every seat a read-only, `.gitignore`-respecting, secret-denylisted **snapshot** of the repository so findings cite real `path:line`; consent binds to the scope hash and `repo-scope-manifest.json` records the scope, and in gate mode it enforces read-XOR-network (refuses an un-isolatable seat — see `references/data-handling.md`). Calls the scripts below; never reimplements them. Implemented as the [`_conductor/`](#package-layout) package — `run_board.py` is a thin façade (re-exports the API + the CLI entry). | `design/run-board-conductor.md` |
| `board_verdict.py` | Validate `verdict.json` (`@1`/`@2`); gate CI on the verdict (`--gate`) — pass `0` / fail `1` / schema `2` / **abstain `3`** when the board is torn, the declared verdict contradicts the observed board, or a citation is refuted. **`--min-severity blocker\|concern`** (v1.14) composes with `--fail-on` to narrow a fail (a fail must ALSO rest on a finding at/above that tier — see below). The `amend` subcommand (v1.12) appends append-only human tuning (a confidence change, caveat, or severity note, each with provenance) without rewriting the board's own words. Validates the v1.13 `changes` pointer (exactly `{artifact, sha256}`) strict-when-present. | `references/verdict-schema.md` |
| `board_changes.py` | Validate `changes.json` — the v1.13 revision artifact of record (`advisory-board/changes@1`; the edit → finding mapping of `run --output revised-draft`, plus the per-edit board `endorsements`). Strict schema check (locator shapes, `resolves`-list enum {blockers, concerns}, dense `n`, conductor-computed `status`; endorsement rows: exactly one of `edit_n`/`unresolved_n`, `position ∈ {ENDORSE,OBJECT,ABSTAIN}`, optional `note`, optional `dropped: true`) — schema `2` on a violation. Importable `validate()` + a small CLI. | `references/changes-schema.md` |
| `verify_evidence.py` | Resolve a verdict's typed `evidence[]` and stamp each `verified`/`unverified`/`refuted` — `code` `path:line`/`symbol` against the source, `source` quotes against the **captured packet** (never a live fetch), and (M3, opt-in via `--allow-program NAME`) `command` citations by **program-pinned, no-shell re-execution** in an isolated cwd with a structural exit/`expect` match. A `code` citation that RESOLVES also **captures a snippet** onto the evidence entry (v1.13 P3, #12) — the cited lines, so the handoff is self-contained; gated by `repo-scope-manifest.json`'s sha when the run is grounded (see below). | `references/verdict-schema.md` |
| `render_verdict.py` | Render `final-consensus.md` **from** the canonical `verdict.json` (evidence trail + couldn't-verify bucket, now with fenced `path:from-to` snippet blocks where captured — v1.13 P3); `--handoff-data`/`--html` derive the HTML via `render_handoff.py`. `--shape` picks the view: `full-handoff` (default), `quick-verdict` (skim brief), or `implementation-sequence` (sequence-first — every next action in order with owners where the verdict names them, backed by the blockers and their evidence trails; md + HTML). **`--filter blockers\|blockers+dissent\|all`** (v1.14) trims the findings by severity (see below). The full-handoff HTML also carries the revised-draft **redline/patch view** (v1.13 P3) when `--run` resolves a sha-coherent revised chain — and, above it, a small **endorsement summary** (v1.13 P4: the per-edit ENDORSE/OBJECT/ABSTAIN tally + any objection notes) when `changes.json` carries endorsement rows (absent + byte-identical otherwise). See below. | `references/verdict-schema.md`, `references/output-formats.md` |
| `format_output.py` | Render `verdict.json` as a TL;DR, PR comment, Slack message, or normalized JSON. **`--filter blockers\|blockers+dissent\|all`** (v1.14) trims the findings by severity (only the `pr` shape renders dissent; **refused with `--format json`** — see below). | `references/output-formats.md` |
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
| `revision.py` | The revision seat (v1.13 #2, `run --output revised-draft`): generalizes the synthesizer spawn path to produce a board-derived, findings-mapped revised copy of the source (the endorsement pass then votes on it — see `endorsement.py`). Enumerates the verdict's resolvable findings, spawns one board seat (mapping first, revised draft second), then MECHANICALLY cross-asserts every `{list, index, title}` finding ref against the verdict, reconciles each edit locator against the `difflib` diff (INV-1), enforces completeness, and builds `changes.json` (schema `advisory-board/changes@1`). Also holds `build_unified_patch` (v1.13 P3, D12) — a stdlib `difflib.unified_diff` `a/`/`b/`-headered, LF-terminated patch builder shared by the `revised-draft.patch` artifact and the HTML handoff's code patch section. |
| `endorsement.py` | The endorsement pass (v1.13 #2 / P4, D13, `run --output revised-draft` unless `--no-endorse`): generalizes the revision spawn path — same template-sha discipline, DATA-fence + neutralizer, two-attempt retry set (`Timeout \| InvalidOutput`), raw black-box record. After the revision SUCCEEDS, fans the NON-revision seats out CONCURRENTLY (the round `ThreadPoolExecutor`; ≈ one extra round) for a per-target `ENDORSE`/`OBJECT`/`ABSTAIN` token on every edit AND every unresolved conflict; the conductor BUILDS the `{seat, edit_n\|unresolved_n, position, note?, dropped?}` rows (the model authors tokens, never rows). A failed/unparseable spawn records that seat as `ABSTAIN`/`dropped` rows — the pass NEVER fails the run, discards the revision, or moves exit codes; all-dropped is a loud warning + rows. Writes `endorsement/<seat>.md`+`.raw`. |
| `redline.py` | The prose redline VIEW (v1.13 P3, D12), pure and stdlib-only: `build_redline(original, revised)` runs `difflib.SequenceMatcher.get_opcodes()` line-level, then a second word-level pass inside each `replace` pair so only the changed WORDS carry `<ins>`/`<del>` spans. Returns un-escaped row structures — `render_verdict.py` owns HTML-escaping and `{{TOKEN}}`-neutralizing. Caps at `REDLINE_MAX_LINES` (400) rendered rows, with the full pre-cap count returned so the caller can say "N more"; collapses long unchanged runs to `REDLINE_CONTEXT_LINES` (2) of context on each side of a change plus a gap row, rather than echoing the whole file. |
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

# tune a completed verdict by hand — append-only, one effect per call, with provenance.
# never rewrites the board's own confidence/blockers; renderers show the effective value
# marked "(amended)"; a no-amendments verdict is unchanged.
python3 scripts/board_verdict.py amend --run <out> --author tim --reason "overstated" --confidence medium

# board-ENDORSED FIXED COPY (v1.13): after synthesis, spawn a revision seat to produce a revised
# copy of the source, each edit mapped by the model to the finding it resolves, mechanically
# validated (coverage reconciliation + index/title cross-assert). Then, unless --no-endorse, the
# ENDORSEMENT PASS (P4, D13) runs: once the revision succeeds, every NON-revision seat is fanned
# out CONCURRENTLY (~ one extra round) to vote ENDORSE/OBJECT/ABSTAIN on each edit AND each
# unresolved conflict, recorded as changes.json.endorsements rows. Objections are RECORDED, never
# resolved (a human reads them, D6). Requires a verdict path (--synthesize). --source-type
# prose|code selects the redline format (else the extension heuristic decides; unknown ext / stdin
# must pass the flag). --revision-seat picks which board seat revises. The source file is NEVER
# written (D6) — applying the revised draft is your act.
# -> revised-draft.md (or .<orig-ext>, byte-clean) + changes.json (advisory-board/changes@1, now
#    carrying endorsements) + revision/<seat>.md+.raw + endorsement/<seat>.md+.raw; verdict.json
#    gains a {artifact, sha256} changes pointer (sha-pins the endorsement-bearing bytes).
python3 scripts/run_board.py run --source plan.md --out <out> --yes --synthesize --output revised-draft
# --no-endorse skips the endorsement pass (the token-cost opt-out): the draft is findings-mapped,
# not board-endorsed, and changes.json keeps endorsements: [] (byte-identical to the revision's build).
python3 scripts/run_board.py run --source plan.md --out <out> --yes --synthesize --output revised-draft --no-endorse
# validate the revision artifact of record (strict schema check; exit 2 on a violation)
python3 scripts/board_changes.py <out>/changes.json

# revised-draft flag / failure decision table:
#   flag / condition                 -> effect
#   --output revised-draft (alone)   -> refused (needs --synthesize; the conductor owns the skeleton)
#   --source-type / --revision-seat  -> only with --output revised-draft (else refused)
#   --no-endorse                     -> only with --output revised-draft (else refused); endorsements: []
#   revision fails a mechanical check-> changes-rejected.json + revised-draft-rejected.* + exit 0
#                                       (--strict-exit -> 4); NO endorsement pass runs
#   endorsement seat drops/unparsed  -> that seat -> ABSTAIN/dropped rows; run still exits 0
#   ALL endorsement seats drop       -> rows still written + one loud warning; run still exits 0
#   single-seat board (no non-rev.)  -> endorsements: [] + a note (not a crash)
# a CODE source (--source-type code) additionally writes revised-draft.patch (a/ b/ headers,
# git-apply-able: `git apply -p1 revised-draft.patch`); a PROSE source writes no patch — its
# redline instead renders as a <ins>/<del> section in the full-handoff HTML below (v1.13 P3, D12).

# render the redline/patch view: --run must point at THIS run's dir (renderer walks
# verdict.changes -> changes.json -> {source-material.txt, revised-draft.*}, re-verifying
# every hop's sha256 before diffing a byte; any mismatch drops the section + one stderr
# warning, never a crash). Only the full-handoff shape (the default) carries it.
python3 scripts/render_verdict.py <out>/verdict.json --run <out> --html <out>/final-consensus.html

# --- the canonical-verdict chain (after the agent fills verdict.json,
#     or `run --synthesize` drafts it via the neutral synthesizer seat — M2) ---
# 1. resolve + stamp each typed citation verified/unverified/refuted.
#    add --allow-program NAME (+ optional --allow-command 'REGEX' to pin args) to ALSO
#    re-execute command citations whose argv[0] is NAME (M3; opt-in, program-pinned,
#    no-shell, isolated cwd, curated PATH, scrubbed env, process-group timeout —
#    allowlist only read-only programs you trust; a re-run's output is persisted)
#    A resolved `code` citation ALSO captures a snippet (v1.13 P3, #12) — the cited lines,
#    onto evidence[].snippet — so the handoff is self-contained even after the run's repo
#    snapshot is cleaned up. Snippet CONTENT capture is hard-gated (status is never
#    affected): the cited file (and every intermediate dir) must be a real path, not a
#    symlink, and must realpath-resolve INSIDE --source — an in-tree symlink pointing out
#    of the root gets its normal badge but NO snippet, so it can't exfiltrate out-of-tree
#    bytes into the handoff. Then the manifest gate, keyed on --run <out>:
#      * run dir HAS repo-scope-manifest.json (grounded) → WHITELIST-ONLY: capture only a
#        manifest-listed path whose LIVE sha still matches; an unlisted OR changed file
#        keeps its verified/refuted badge but gets NO snippet;
#      * manifest PRESENT but unusable (malformed / unreadable / symlinked) → NO snippets
#        at all + one warning (fail closed — a grounded run's whitelist must be trustworthy);
#      * run dir has NO manifest (ungrounded verify) → capture freely under the read gate
#        above (verify's existing trust model: the human supplied --source).
#    The console line reports how many snippets were captured.
python3 scripts/run_board.py verify <out>/verdict.json --source ./src --run <out>
# 2. render final-consensus.md FROM the verdict (+ --html for the HTML)
python3 scripts/run_board.py consensus <out>/verdict.json --run <out> -o <out>/final-consensus.md
# 3. gate: 0 pass / 1 block / 2 schema / 3 ABSTAIN (board torn or a citation refuted)
python3 scripts/run_board.py validate <out>/verdict.json --gate
# gate, but only fail when a fail rests on a real blocker (v1.14): a caution/block
# verdict whose only findings are concerns/dissent passes; abstain is unaffected.
python3 scripts/run_board.py validate <out>/verdict.json --gate --min-severity blocker

# render, trimmed by severity (v1.14): blockers-only md, with a loud elision line
# stating what was dropped. --filter all (the default) is byte-identical to no flag.
python3 scripts/render_verdict.py <out>/verdict.json --filter blockers -o blockers-only.md

# turn the verdict into a PR comment, blockers only (the pr shape renders dissent,
# so --filter blockers drops it — with a loud "(filtered: …)" note)
python3 scripts/format_output.py path/to/verdict.json --format pr --filter blockers

# render the HTML handoff deterministically from structured data
python3 scripts/render_handoff.py path/to/handoff-data.json -o final-consensus.html

# render a PLAN view from its markdown (regenerate whenever the markdown changes)
python3 scripts/render_plan.py ../../design/run-board-v1x.md     # -> run-board-v1x.html
python3 scripts/render_plan.py ../../design/run-board-v1x.md --check   # verify only
```

> Paths above are relative to the **skill directory** — `skills/advisory-board/` in this repo, or the installed skill root (e.g. `~/.codex/skills/advisory-board/`) — the same convention as every `references/…` path in the skill. Run the scripts from there, or prefix them with that directory; `scripts/board_verdict.py` won't resolve from the repo root.

`board_verdict.py`, `verify_evidence.py`, `render_verdict.py`, and `format_output.py` all read the canonical `verdict.json`. `run_board.py run` stops at the **last round's boundary** and prints the synthesis chain: the agent (or one neutral seat) reads `round-N/*.md` and writes `verdict.json` (synthesis stays a reasoning task — §11; the conductor does **not** generate the verdict in code), then `verify` → `consensus` → `validate` run deterministically. See the repo-root `examples/payments-idempotency-review/verdict.json` for a filled-in sample, and `references/verdict-schema.md` for the `@2` schema with typed evidence and the `abstain` gate.

### Severity filters (v1.14, #8)

The verdict schema already separates severities — `blockers[]` (top), `dissent[]`, `concerns[]`, and the plain-string `caveats[]` (the couldn't-verify bucket). Two flags **expose** that structure; they add no new modeling.

**`--filter blockers|blockers+dissent|all`** on `render_verdict.py` and `format_output.py` trims the **findings** sections (the verdict banner and confidence are never filtered):

| value | shows | elides |
| ----- | ----- | ------ |
| `all` (default) | everything | nothing — **byte-identical to no flag** |
| `blockers+dissent` | blockers + dissent | the couldn't-verify bucket (concerns' unverified/refuted evidence + caveats) |
| `blockers` | blockers only | dissent **and** the couldn't-verify bucket |

A dropped section is **stated with counts**, never truncated silently — e.g. `(filtered: 2 dissents, 4 couldn't-verify lines — --filter blockers)`. The **renderer** computes the counts and the helper only formats them, so the note names the honest buckets *that shape renders* — dissent **entries** and couldn't-verify **lines** (caveats + unverified/refuted evidence, the exact lines the couldn't-verify section would have shown). It is never a raw `len(concerns)`/`len(caveats)`; concerns are not rendered as items here, so the note never claims a dropped "concern". Each count equals exactly what the filter suppressed, auditable against the verdict:

- **consensus md** (`render_verdict.py`, default shape) — dissent + couldn't-verify are both filterable; the elision line follows the last kept section.
- **quick-verdict / full-handoff HTML** — same tiers; on the filtered render a suppressed section drops **whole — heading included** (`render_handoff.drop_empty_optionals`; never a hollow shell), and the `{{FILTER_NOTE}}` line carries the count. The quick-verdict template renders no couldn't-verify bucket, so its note reports only dropped dissent.
- **implementation-sequence** (md + HTML) — renders only next actions + blockers, so **no filter setting changes it** — its rendered output *and* its `handoff-data.json` — and it never carries an elision line.
- **`format_output.py` `pr`** — renders dissent, so `blockers` drops it (with a note); `tldr`/`slack` render neither dissent nor caveats, so every filter is a **no-op** for them.

A filtered `--handoff-data` file is a shape-specific **view** feeding the HTML render, never a machine echo (that stays `format_output.py --format json`, which refuses `--filter`). Its thinning is **shape-owned**: a slot is emptied only when that shape renders the bucket, and the `filter_note` inside the file counts exactly what was emptied — a bucket the shape never renders keeps its full list, so the artifact never silently loses content.
- **`format_output.py --format json`** — **`--filter` (non-`all`) is refused with a clean exit `2`.** The JSON output is the faithful, unfiltered machine echo of the verdict (a gate reads it); filtering it would silently drop verdict content, and annotating it would break the faithful-mirror contract. Filter the human formats instead.

**`--min-severity blocker|concern`** on `board_verdict.py --gate` (also `run_board.py validate`) **composes with `--fail-on`**: after the verdict token clears the fail threshold, a **fail** additionally requires a finding at or above the named tier (ranked `blocker` > `concern`; **dissent is a minority view, not a finding tier, and never counts**). So a caution/block verdict whose only findings are concerns/dissent **passes** under `--min-severity blocker` instead of failing. It can only **narrow a fail to a pass** — it never escalates a pass, and it never touches the **abstain** integrity checks (a refuted citation, a torn board, or a verdict-vs-board contradiction all still abstain regardless). Absent = today's behavior (the verdict token alone drives the gate). Unknown values are refused (exit `2`).

Both flags flow through the `run_board.py` delegate subcommands (`consensus`, `validate`) unchanged — those forward every argument verbatim to the underlying script.

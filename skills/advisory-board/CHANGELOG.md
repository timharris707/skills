# Changelog — advisory-board

All notable changes to the `advisory-board` skill are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases are
cut as **skill-scoped semver tags** `advisory-board/vX.Y.Z` (see [`RELEASING.md`](../../RELEASING.md)).
Pre-1.0 the minor tracks the conductor milestone (M5 → `v0.5.0`, M6 → `v0.6.0`); `v1.0.0` is
reserved for an explicit production-ready call. The verdict-JSON schema is versioned separately
(`advisory-board/verdict@N`) and is not the same axis as the release version.

## [Unreleased]

## [v1.12.0] - 2026-07-02 — The decision loop

### Changed
- **Claude seat: Opus 4.8 registered as the one sanctioned fallback.** The seat's default
  stays `claude-fable-5` at `--effort max` (the depth flagship); `fallback_models` now names
  `claude-opus-4-8` — probe-and-propose only when Fable 404s, never auto-applied — and
  SKILL.md documents it as the sanctioned per-run downgrade when Claude usage matters more
  than Fable-tier depth (`--model claude=claude-opus-4-8`; Opus 4.8 accepts the same
  `--effort max`, grounded live 2026-07-02 on CLI 2.1.191). SKILL.md also notes the
  zero-Claude-usage posture: seat a board without the Claude seat (`--board codex,gemini`) —
  every seat bills its own subscription.

### Added
- **`board_verdict.py amend --run <dir> --author … --reason … <effect>` (v1.12 #5) —
  human-owned, append-only verdict tuning.** Tune a completed verdict without touching the
  board's words: `amend` **appends** an `amendments[]` entry and never rewrites `confidence`,
  blockers, or concerns. Exactly **one effect per invocation** — `--confidence {low,medium,high}`
  (records `field: confidence` with `from` = the effective value *before* this amendment and
  `to` = the new one; a no-op is refused), `--caveat TEXT`, or `--severity-note TEXT` optionally
  scoped by `--on "<finding title>"` (a **strict** match against an existing blocker/concern
  title — a mismatch dies listing the available titles). Provenance (`author`/`reason`/
  `timestamp`) is required; the timestamp honors `$ADVISORY_BOARD_NOW_TS` for reproducible runs,
  else the local ISO-8601 now. The file is re-validated and **atomically** rewritten. A new
  module-level `effective_confidence(data)` (the last confidence amendment wins, else the board's
  own value) is the single source renderers read; `summarize()` now shows the effective
  confidence **with** its provenance and an `amendments:` breakdown line — but **only when
  amendments exist**, so an un-amended verdict prints byte-identically. `_validate_lifecycle`
  now checks the effect fields strictly **when present** (additive; a zero-effect entry from P1
  still validates). The gate is untouched — an amendment never moves a gate outcome. **All
  renderers now display amended values WITH provenance and never as the board's own:** the
  consensus Markdown (and the implementation-sequence view) show the effective confidence with an
  "amended from … by …" clause, mark caveat amendments as human-added alongside the board's own
  caveats, attach a severity note to its matching blocker (exact `--on` title match — unmatched /
  `on`-less notes land only in the trail), and carry a new **Amendments** section with the full
  ordered trail (author, timestamp, reason, effect; a zero-effect entry renders as a
  provenance-only note); the HTML handoff gains a visually distinct (gold-edged, human-owned)
  Amendments section plus an effective-confidence pill marked `(amended)`, both wired through the
  pre-v1.12 backfill so a new token never breaks an old template and vice versa; and `tldr` / `pr`
  / `slack` append a terse `(amended)` marker to the effective confidence (`--format json` still
  echoes the verdict verbatim). A verdict with **no** amendments renders byte-identically to
  before in the consensus Markdown, the implementation-sequence Markdown, and the `tldr`/`pr`/
  `slack` short formats; the HTML handoff's rendered body is likewise byte-identical (the only
  change is additive, inert CSS for the amendment styling — the dropped optional blocks leave no
  whitespace residue) — all test-enforced.
- **`ask "<question>" --run <dir> [--seat <id>]` (v1.12 #4) — post-verdict cross-examination.**
  Put a follow-up question to a COMPLETED run's board without a full re-review. `ask` loads the
  run's recorded board from its `run-recipe.yaml`, builds a context packet **bounded to that run's
  own artifacts** — the reviewed material (recovered from `source-material.txt`, sha-verified, or
  degraded loudly), a MECHANICAL digest of the prior verdict (reused from `--revise`; tokens /
  titles / citations, never a summary, §11), and **each addressed seat's own last USABLE review**
  for continuity (a dropped-round `no usable review` placeholder is skipped in favor of the seat's
  last real position — adversarial correctness fix) — then fans ONE round out to the addressed
  seat(s) (`--seat <id>` targets one; the default is every seat). It writes `addendum-N.md` (the
  Q&A + falsifiable per-seat prompt/packet hashes), an `addendum-N/` egress record (manifest +
  `sensitivity.json` + the exact per-seat prompts), a machine `addenda.json` index, and refreshes
  a managed **Post-verdict addenda** block in `final-consensus.md` (idempotent, rebuilt from the
  index; block content is sentinel-neutralized and the splice only honors an ordered BEGIN→END
  pair, so a marker-bearing question or a hand-corrupted file can never cascade corruption —
  adversarial security fix). **Consent re-decides for the new
  bytes**: the ask packet gets its own content hash through the SAME egress gate a fresh run uses
  (public discloses and proceeds; non-public requires hash-bound `--yes`/interactive approval and
  refuses non-interactively), and the effective sensitivity is the **strictest of the recipe's
  value, the run's `sensitivity.json`, and an operator `--sensitivity` floor (tighten-only)** —
  an ask never egresses under a looser posture than the material was handled with, a local-only
  run with external seats is refused, and (from the adversarial security review) a run with **no
  readable `sensitivity.json` never floats down to public**: its original posture is unknown, so
  public floors to redacted, loudly, with the flooring recorded on the consent record — the disk
  values live inside a (shareable, tamperable) run dir, so the posture cannot rest on them alone.
  Grounding is forced OFF
  (a grounded run's `ask` still egresses only artifacts, never a live repo read). The injected
  run-context is **byte-neutralized** against fence-marker echoes (a new `PRIOR RUN CONTEXT` fence
  family, since it embeds prior MODEL output), the question rides OUTSIDE that data fence as the
  operator's instruction, and every recovered file is a **bounded read** (symlinked or out-of-tree
  artifacts refused). The one-round fan-out reuses the round runner with a lighter classifier
  (`classify_ask`) — an answer is free-form prose, not a 7-section review. Own template family +
  sha (`advisory-board/ask@1`), recorded on the addendum's egress record.
- **`--revise <prior run dir | verdict.json>` (v1.12 #1) — re-review a revised draft with the
  prior verdict as context.** `--source` is the revised draft; the round-1 prompts additionally
  carry a fenced, neutralized block holding a MECHANICAL digest of the prior verdict (tokens,
  titles, citations — never a summary, §11) plus the unified diff from the previously reviewed
  draft to the current material (capped at 400 lines, loudly). The injected bytes live inside
  the packet blobs, so the egress **consent hash covers them with no new machinery**, the
  run card / dry-run disclose them, and the template-sha discipline holds: the version records
  a `+revise@1` suffix (`advisory-board/round1@2+revise@1`, composing with grounded `@3`) while
  a non-revise run's prompts, template sha, and recipe stay byte-identical. To make the diff
  possible every run now persists `source-material.txt` (an exact source copy, post-approval —
  the same bytes the persisted prompts already embed; `references/data-handling.md` notes it);
  revising a pre-v1.12 run recovers the prior source from a persisted round-1 prompt,
  **sha-verified against the recipe**, and degrades loudly to digest-only when unrecoverable.
  The conductor pins `previous_run` lineage (run dir, prior verdict token, verdict sha256) into
  the synthesizer skeleton — the one path lifecycle fields can enter a synthesized verdict —
  and a revise run's recipe records `revise_of`, so `--from-recipe` replays the same lineage
  (the flag pair itself is refused as contradictory). **Consent-surface hardening** (from the
  adversarial security review): the pre-approval disclosure line, the egress manifest (its own
  section, mirroring grounding's scope disclosure), and `sensitivity.json` all name the
  injection and its provenance; a prior run with a **stricter declared sensitivity** (e.g.
  `local-only`) refuses to revise under a looser run — material never silently escalates; the
  injected material is **byte-neutralized** against fence-marker echoes (the round-2 defense,
  whose marker family now covers the revise fence); recovery is labeled **sha-verified vs
  UNVERIFIED** on every surface, symlinked prior artifacts are refused, and marker-parsing
  prompt extraction is only trusted when the recipe records a `source_sha256` to verify
  against (a prior source containing the marker line can never yield a silently truncated
  diff).
- **Cross-run delta in the consensus (v1.12 #1).** New pure `_conductor/delta.py` classifies
  blockers/concerns across the two runs — cleared / still-open / new — by exact normalized
  title, then shared concrete citations, then guarded stdlib title similarity (mechanical
  only; a reworded finding with nothing shared honestly shows as cleared+new). Matching runs
  as **global tier passes** (an exact title always beats an earlier item's fuzzy pairing), a
  bare file path counts as a citation only when the evidence carries no line/symbol (a
  single-file review must not collapse into all-still-open), and the similarity tier requires
  a shared substantive token on top of the ratio floor. `final-consensus.md`
  and the full-handoff HTML lead with a **trajectory banner** (prior → new verdict, lens-aware
  labels) and the three buckets, derived at render time from `previous_run` (nothing new is
  stored in verdict.json — D8 holds): the prior verdict.json is re-read and checked against
  the recorded `verdict_sha256`, and the section degrades to an honest one-liner when the
  prior run moved or its artifacts changed. Non-revise verdicts render byte-identically, and
  pre-v1.12 `handoff-data.json` files still render.
- **Verdict-lifecycle schema fields (v1.12 Phase 1)** — ONE additive evolution of
  `advisory-board/verdict@2` (the version string does not change; a verdict without the new
  fields is byte-for-byte the same schema as before): optional `previous_run` lineage (object;
  required non-empty `run_dir`, optional `title`/`date`/`verdict`/`verdict_sha256` — the sha
  binds lineage to the prior verdict's *content*, not a movable path) and optional append-only
  `amendments[]` (each entry requires the provenance trio `author`/`timestamp`/`reason`; effect
  fields arrive with the `amend` tooling). Both are validated strictly WHEN PRESENT — like
  evidence, identically under either schema id (`@1` included) — and are invisible when
  absent; the gate never reads them. Every renderer reads named fields only, so
  a lifecycle-carrying verdict renders identically — test-proven for the consensus markdown,
  the implementation-sequence shape, the handoff data (the HTML's input), and the
  tldr/pr/slack formats (`--format json` deliberately echoes the whole verdict, lifecycle
  fields included). The top-level
  `changes` key is RESERVED for the v1.13 revision artifact and refused loudly while undefined.
  Lifecycle fields are tool/human-authored, never model reasoning: the synthesizer merge now
  strips them (new `LIFECYCLE_KEYS`, alongside the protected skeleton keys) so a model reply
  cannot fabricate an amendment trail or a prior-run link. This is the single schema evolution
  v1.12's `--revise` / `ask` / `amend` build on — no further ad-hoc bumps.

## [v1.11.0] - 2026-07-01 — Transparency & foundations

Know before you convene, and keep what you ran. A board run now tells you its **cost and
time up front** (`--dry-run` estimate) and records what each seat actually spent where the
CLI reports it; one flag — **`--tier quick|standard|deep`** — sets the whole cost/depth
posture; run artifacts land in a **persistent runs root** with a `history` listing instead
of evaporating from `/tmp`; a **setup doctor** walks a brand-new machine to its first
viable board; and the round-2+ structured digest is available as **typed JSON** for
tooling, alongside per-seat `--timeout` and a real `implementation-sequence` render. A
default run — no new flags, tokens unreported — stays byte-identical to v1.10.0 artifacts
except the (loudly documented, opt-out) runs-root move.

### Added
- **`--tier quick|standard|deep` (v1.11 #3b)** — one flag for the run's whole cost/depth
  posture, applied as a BASE beneath explicit flags: `quick` = 1 round, `summaries`
  cross-reading, reduced per-seat reasoning (claude `high`, codex `medium`); `standard` =
  today's defaults (a deliberate no-op); `deep` = 3 rounds, `full` cross-reading at the
  registry's max-tier reasoning (codex stays at `xhigh`, its hard API ceiling —
  test-guarded). Model ids are deliberately NOT a tier knob (no unverified "budget" id may
  404 the board); reasoning is keyed by provider so duplicate/aliased seats move together,
  and seats without an effort knob (gemini/antigravity/ollama) are untouched at every tier.
  `--rounds`/`--cross-reading` always win over the tier; `run-metadata.md` gets a one-line
  tier provenance note only when the flag was given (a no-tier run stays byte-identical);
  `run-recipe.yaml` records the RESOLVED values, never the tier name, so `--from-recipe`
  replays exactly — the pair is refused as contradictory.
- **`--digest-format markdown|json`** on `run` (default `markdown` — existing behavior untouched):
  with `json`, each round-2+ structured digest is ALSO written as typed JSON —
  `board-packet-round-N.json` (`advisory-board/board-packet-digest@1`) next to the `.md` — carrying
  the same parsed signals the markdown digest already computes: per-seat `VERDICT` tokens + the
  agreement summary, the shared (≥2-seat) citation set, every canonical topic with each seat's
  head-excerpted take, and the unparsed-review fallbacks. A serialization of what exists, not new
  reasoning (§11); requires `--cross-reading summaries` (refused loudly otherwise). Golden-file
  tested against the committed payments example.
- **Per-seat `--timeout`**: `--timeout SECONDS | SEAT=SECONDS`, repeatable. A bare value applies to
  every seat (the old single-value syntax keeps working unchanged); `SEAT=SECONDS` overrides one
  seat, targeted by id exactly like `--model`/`--lens` — an unknown id fails loudly. The resolved
  value threads config → rounds → spawn (tested at the spawn call), and the synthesizer honors its
  seat's value. Run-only; deliberately not recipe-persisted.
- **`--output implementation-sequence` is now a real, distinct render** (previously it fell back to
  the full handoff). `render_verdict.py --shape implementation-sequence` renders a sequence-first
  view of the same `verdict.json`: the ordered `next_actions[]` lead — the full list, with the
  owner named where the verdict carries one — backed by the blockers each step must clear with
  their evidence trails. Emits `implementation-sequence.md` plus a matching self-contained HTML
  shape (`references/implementation-sequence-template.html`, same template machinery and brand as
  the other shapes), deterministic from `verdict.json` like every render. `next_actions[]` entries
  may now be `{action, owner}` objects; plain strings render byte-identically everywhere.
- **Setup doctor** (`run_board.py doctor`, #7) — guided onboarding for a brand-new machine: sweeps
  **every** registered provider (claude, codex, gemini, antigravity, ollama), not just a chosen
  board, reusing the toolchain currency probe (installed → version vs latest) and the preflight
  seat probe (auth → default model resolves → smoke) per provider. Prints a per-provider status
  block with concrete fix-it steps (install command, auth command, model fallback, stale-CLI
  update), then a viable-board summary (≥ 2 seats GO) with a suggested first command (a `--dry-run`
  on the bundled sample source). No user material egresses — probes and smoke-pings only, and the
  output says so. Exits non-zero when no board is viable, so scripts can branch on it.
  (`scripts/_conductor/doctor.py`; probe logic stays in `preflight.py`/`toolchain.py`.)
- **Per-seat token capture (v1.11 #3a).** `SeatRoundResult` gains nullable
  `tokens_in`/`tokens_out`/`tokens_total`, filled by per-adapter `parse_usage`
  parsers in `registry.py` that read ONLY what each CLI unambiguously reports
  about its own usage (grounded live 2026-07-01): codex's trailing
  `tokens used` stderr footer (a combined total — no in/out split), and
  claude's `--output-format json` result envelope (plain `-p` text mode — the
  board's argv today — prints no usage, so the seat honestly reports unknown).
  gemini / antigravity / ollama print nothing and stay unknown. Never guessed.
- **Preflight cost/time estimate.** A dated list-price table
  (`constants.MODEL_PRICING_USD_PER_MTOK`) plus a pure `estimate_run()`
  (source bytes × seats × rounds × cross-reading → token band, cost band,
  rough minutes), surfaced as an `=== estimate ===` block in `run --dry-run`
  and pointed at by SKILL.md's flag-a-large-run guidance. Best-effort and
  labeled an ESTIMATE — never a gate; unverified prices render as unknown,
  not $0.
- **"If known" cost/time rendering.** When any seat CLI reported usage:
  per-seat token lines and a `## Cost & time (best effort)` section in
  `run-metadata.md`, three trailing token columns in `run-metadata.tsv`, and a
  seat-reported totals segment in the `final-consensus.html` footer (read from
  the run dir's TSV). With no usage reported — every mocked/default run today —
  all three artifacts stay **byte-identical** to the pre-feature baseline
  (guarded by tests).
- **`run_board.py history`** — a table of past runs (date, title, verdict, confidence,
  unanimous, seats, run dir) read from each run's `verdict.json` under the runs root, with the
  same lens-aware human verdict labels the consensus artifacts use. Partial/legacy runs (missing
  or malformed `verdict.json`) degrade to `run-recipe.yaml` and list as `incomplete` — the
  listing never crashes. Local disk read only; honors `--runs-root` / `$ADVISORY_BOARD_RUNS_ROOT`.
  New `scripts/_conductor/history.py` module.

### Changed
- **Persistent runs root (v1.11 #5) — runs stop evaporating.** Default run artifacts now land
  under `~/.advisory-board/runs/<slug>-<date>/` (slug from the run's resolved title, date from
  the deterministic run date; a same-day collision gets a `-2` suffix, never an overwrite)
  instead of a throwaway `/tmp/advisory-board-<ts>` folder. Overrides: `$ADVISORY_BOARD_RUNS_ROOT`
  (env) and `--runs-root DIR` (flag, wins over env) relocate the root; `--out DIR` still names an
  exact dir; `--ephemeral` opts back into the pre-v1.11 `/tmp` behavior. Contradictory
  combinations (`--ephemeral` + `--out`, etc.) are refused loudly. Every real run now announces
  where its artifacts land on its first output line. A `--from-recipe` re-run keeps today's
  semantics — it reuses the recipe's *recorded* dir (now persistent, so replaying rewrites that
  run's artifacts in place; the notice says so) unless `--out`/`--runs-root`/`--ephemeral` point
  it somewhere fresh. Artifact *content* is unchanged —
  persistence is a disk-location move only, and persisted artifacts inherit the run's
  sensitivity handling (`references/data-handling.md` gets a "Persisted run artifacts" section).

### Fixed
- **Snapshot leak checks are now process-local (test-only).** Three tests asserted a
  before/after glob of the machine-wide tempdir for `advisory-board-repo-*`, so any
  concurrent suite (sibling worktree, parallel CI) creating or removing its own snapshots
  flaked them. A `_private_tempdir` helper now redirects `TMPDIR` to a fresh per-test dir
  for the run, and the tests assert *that* dir holds no snapshot afterward; the
  failure-path test additionally probes mid-prepare that the snapshot really landed there,
  so the check can't pass vacuously.

## [v1.10.0] - 2026-07-01 — Claude seat on Fable 5 at max effort

The Claude seat now defaults to **Fable 5** (`claude-fable-5`), Anthropic's most capable model,
and runs it at **max reasoning**. The seat's effort is now forwarded to the CLI via `--effort max`
— previously the seat computed a reasoning value but never passed it, so it ran at the CLI's own
default. Max effort is scoped to the Claude seat (the only CLI that exposes a `max` level): Codex
stays at `xhigh` (its ceiling — `model_reasoning_effort=max` returns a 400), and
Gemini/Antigravity/Ollama expose no effort knob.

### Changed
- **`scripts/_conductor/registry.py`** — Claude seat `default_model` `claude-opus-4-8` →
  `claude-fable-5`; `default_reasoning` `xhigh` → `max`; `claude_argv()` now forwards
  `--effort <reasoning>`; `flags_verified_version` → `2.1.191`.
- **`SKILL.md`, `references/run-metadata-template.md`, `references/verdict-schema.md`** — model
  lineup, the Claude CLI template, and examples updated to Fable 5 / `--effort max`, with a
  premium-tier cost note and the `--model claude=<id>` override.

### Fixed
- **`--from-recipe` now reproduces per-seat reasoning.** Recipe replay restored model and lens but
  re-pulled reasoning from the live registry, so a recipe recorded at `xhigh` would have silently
  replayed at the new `max` default. `resolve_board` takes reasoning overrides and the replay path
  restores recorded reasoning; guarded by a new round-trip test.

Also since v1.9.0: the **relocation gallery example** and its README "See It In Action" lead
(#45), and the seat-composition plan marked SHIPPED (#46, docs-only).

## [v1.9.0] - 2026-06-28 — Flexible seat composition

Seat the **same provider more than once** (`2 Opus + 1 Codex`, `3 Opus`) with a unique `seat.id`
and per-seat lenses. `--board` entries are `provider` or `alias=provider` (bare repeats
auto-number `claude#1`/`#2`; aliases read cleaner); `--lens` is repeatable (bare = the board
preset, `id=value` overrides one seat's focus). `--model`/`--lens` target seats by id. Duplicate
seats no longer silently collapse — that is now a loud failure — and a run stays reproducible via
`--from-recipe`. A default `claude,codex,gemini` board is byte-identical to before (the regression
guard).

### Added
- **Flexible seat composition** (#44) — `seat.id`, alias/auto-numbering, and per-seat lenses,
  re-keyed across the conductor onto `seat.id`; `TestSeatComposition` plus duplicate/alias E2E.
  Gated by three parallel adversarial skeptics (identity-collision, egress/consent, byte-identical
  + recipe) → zero confirmed defects.

### Fixed
- **`--shape` documented** and the quick-verdict render no longer leaves a stray
  `final-consensus.md` (`--out` defaults to none) (#43).
- **Untracked confidence renders cleanly** in Markdown and the short formats — the clause is
  dropped (matching the HTML pill), so no more literal `(? confidence)` (#42).

## [v1.8.0] - 2026-06-27 — Quick-verdict skim-brief shape + confidence pill

### Added
- A **quick-verdict (skim-brief) output shape** that leads with the verdict for fast skimming,
  plus a **confidence pill** in the artifact banner (#40).

## [v1.7.2] - 2026-06-27 — Lens-aware consensus artifact

### Changed
- The **consensus artifact leads with the plain-language, lens-aware verdict** — a plain verdict
  lead plus a matching section heading — carrying the v1.6.0 plain-language label into the
  consensus surface (#39).

## [v1.7.1] - 2026-06-27 — Artifact lockup: "Advisory Board, powered by Panely"

The artifact masthead and footer now lead with **Advisory Board** as the product, with
**powered by Panely** as a maker attribution beneath it — previously the lockup bundled
"Panely Advisory Board". This keeps the skill and the Panely app cleanly distinct, while
still crediting the maker. Template-only: no behavior, renderer, or schema change.

## [v1.7.0] - 2026-06-26 — Panely Advisory Board brand

The human-facing artifact is now a branded **Panely Advisory Board** deliverable — the
review's strongest marketing surface. The body stays light and readable, bookended by
dark masthead and footer bands carrying the Panely "decision core" mark, the *Panely
Advisory Board* lockup, the "use your own subscriptions to Claude, Codex, and Gemini"
line, and a **panely.ai** call-to-action. The verdict-JSON contract, the section
structure, the honesty sections, and the lens-aware label/disclaimer are all unchanged.

### Changed
- **`references/handoff-template.html`** — re-skinned into the Panely identity: a dual
  theme (light "Boardroom" body + dark "Signal" masthead/footer bands), cobalt `#2347FF`
  signature accent, gold `#E2B658` lead-seat secondary, muted verdict colors, Signal
  font stacks, and an inline self-contained glowing avatar in the masthead with a flat
  favicon in the footer. Every `{{TOKEN}}`/block and the renderer-contract shapes (the
  `verdict {{VERDICT_CLASS}}` class, the `disclaimer`/`seat-status`/`highlight`/`conf`
  spans, the `.review-body` list-indent rule) are preserved — the suite stays green.

### Fixed
- **Two developer strings no longer leak onto the page** (`scripts/render_verdict.py`):
  the masthead **subtitle** now describes what was reviewed (was "Rendered from the
  canonical verdict.json."), and the footer **provenance** reads in human terms —
  "Board: … · N rounds · date" (was "Rendered from verdict.json by
  scripts/render_verdict.py.").

## [v1.6.0] - 2026-06-26 — Plain-language, lens-aware verdict label

The machine token `verdict: ship|caution|block` stays byte-identical (the gate
axis is untouched), but the **human-facing label** is now lens-aware. A
`software-architecture` board keeps the familiar `SHIP` / `SHIP WITH CHANGES` /
`DO NOT SHIP YET`; every other lens preset (product, research, legal, business,
writing — and any unknown one) renders plain language — `Go ahead` / `Proceed
with care` / `Stop and rethink` — plus a one-line "what this means" note, so a
non-developer reader isn't handed shipping jargon. An explicit `decision` field
still wins verbatim.

### Added
- **`lens_preset` in `verdict.json`** — the conductor writes the run's board-level
  lens preset name into the canonical verdict so the renderers (which read it
  standalone) can pick the right label family. Type-checked (optional string) by
  `board_verdict.py`; documented in `references/verdict-schema.md`. A wholly
  absent field defaults to the software family (backward compatible: every
  pre-feature verdict.json was a software-lens run).
- **Shared `scripts/_verdict_labels.py`** — one `human_label(token, lens_preset,
  decision)` source of truth so the three renderers stop diverging (they each
  carried their own, already-drifted, label map).

### Changed
- `render_verdict.py` (Markdown headline, handoff `verdict`/`verdict_note`,
  per-round pills) and `format_output.py` (`verdict_line`) now resolve labels
  through `_verdict_labels.human_label`. The handoff banner color
  (`verdict_class`) stays keyed on the **raw** token, not the label. Plain labels
  keep their natural case (no shouted "STOP AND RETHINK").
- The M2 synthesizer prompt gains a light `decision` optional-field nudge
  (template version `synthesizer@1` → `@2`).

## [v1.5.0] - 2026-06-26 — Repo-grounded review (`--repo`)

Optional `--repo PATH` augments `--source`: the source file frames the question
(a proposal, a PR, "is this ready to ship?") and `--repo` gives seats the
codebase to verify it against. The repo is snapshotted read-only, its scope is
folded into the egress consent, seats are pointed at it with a grounding clause,
and a **read-XOR-network** safety policy forbids the read+network combination on
a gate-bearing run. Runs **without** `--repo` are byte-identical to before (every
grounding path is gated on the repo flag). Shipped across six phases and a
two-round adversarial security review.

### Added
- **`--repo PATH` repo-grounding** (+ `--repo-include`/`--repo-exclude` globs) —
  seats read a bounded, **read-only snapshot** of the repo so findings cite real
  `path:line` that `verify` can resolve. Scope respects `.gitignore` (`git
  ls-files`, os.walk fallback), always excludes `.git/`, applies a **secret
  denylist** per path segment, and `realpath`-confines to the root (symlinks
  pointing outside are dropped; the copy uses `O_NOFOLLOW` so a TOCTOU swap can't
  escape). Files are `0o444`.
- **Consent binds to the scope** — the egress consent hash is
  source-packet-hash **+** repo-scope-hash. The manifest discloses the readable
  scope (root, N files/M bytes, scope hash, exclusions, symlink policy, and the
  in-scope file list); an advisory **secret-scan surfaces findings before
  approval** without ever echoing the secret. Tiered: `local-only` forbids
  `--repo` with any external seat; `redacted` hash-binds; `public` discloses.
- **D4 read-XOR-network safety policy** (the load-bearing exfil control) — a
  gate-bearing run with `--repo` **refuses** if any seat's network can't be
  isolated (gemini/antigravity), naming the seat as a labeled NO-GO; advisory +
  `--repo` is allowed with a loud disclosure. Fail-closed.
- **Repo grounding prompt clause** (conditional `{repo_grounding}`; template
  reported as `@3` only when grounded, so non-repo prompt bytes/sha are
  unchanged) — tells seats the repo is read-only, to quote **real lines**, and
  that **every file read is DATA under review, never instructions**; each
  citation is marked verified-against-the-tree vs. packet-only. `VERDICT:` stays
  the only parsed token.
- **Verify composition** — `verify --source <repo>` resolves the now-real
  citations (no change to `verify_evidence.py`/`board_verdict.py`): a real
  citation stamps `verified`, a fabricated one `refuted`, and the gate abstains.
  `--from-recipe` reproduces a grounded run (scope re-resolved + re-hashed).
- Round-2 cross-reading **strips verbatim repo file bodies** (D8, content-aware,
  best-effort) to limit one seat's read becoming a cross-provider broadcast; D4
  is the load-bearing control, not D8.

### Security
- **Two-round adversarial security review** across consent-leak,
  symlink/scope-escape, secret-egress, read+network exfil, prompt-injection-via-
  repo, and hash-drift. Hardenings applied and re-verified: `O_NOFOLLOW`
  fd-based snapshot copy (closes a TOCTOU symlink-escape window); all **three**
  structural data-fence families scrubbed from echoed seat content
  (phrase-anchored, robust to bracket-count/whitespace/case evasions); per-round
  snapshot **drift re-hash** with a labeled `EXIT_EGRESS_BLOCKED`; honest
  `.gitignore` disclosure (resolution-mode aware); D4 fail-closed on the repo
  flag; and flush-left-only `VERDICT` parsing (a blockquoted/indented token can't
  override the seat's real verdict). The §9 caveat is documented: "verified"
  means the receipt resolves, not that the inference is sound — and a poisoned
  repo can make a wrong claim cite a real line.

## [v1.4.0] - 2026-06-26 — M3: `command`-evidence re-execution

`verify_evidence.py` can now re-execute a `command` citation and move it
`verified`/`refuted` from observed behavior — closing the last v1.x edge (M5
captured `command` evidence but never ran it, so those citations stayed
`unverified`). Re-execution is **opt-in and allowlist-gated**: re-running a
command cited as evidence is an execution surface, and a verdict synthesized from
untrusted source (the M2 synthesizer over poisoned reviews) can carry an
attacker-influenced command — so the default is unchanged (commands stay
`unverified`) and the allowlist is the load-bearing control.

### Added
- **`command`-evidence re-execution (M3)** — `--allow-program NAME` (repeatable)
  ENABLES re-execution for commands whose **argv[0] is exactly that bare program
  name**; everything else stays `unverified` with a recorded `status_reason`. The
  **program allowlist is the load-bearing control** — argv[0] is pinned to a program
  you name, never a path (`./x`, `/bin/sh`, `../x` are refused) and never chosen by
  a regex. `--allow-command REGEX` (repeatable, optional) further requires the full
  command to `re.fullmatch` a pattern — for pinning **args**, not the program; it
  refines, never widens, the program allowlist and cannot enable re-execution on
  its own.
- **Layered containment** (hardened after a security review found 3 RCE paths):
  **no shell** (`shlex.split` + `shell=False` → `;`/`|`/`>`/`$()`/globs are inert
  literal args); a **curated PATH** (inherited PATH minus `.`/empty/relative
  entries) + a **resolves-inside-cwd guard** so a `pytest` planted in the reviewed
  source can't shadow the real one; an **isolated throwaway cwd by default** (NOT
  the source tree — `--rerun-cwd DIR` opts into a real tree) with **HOME pointed at
  it** so `~/.aws`/`~/.ssh` aren't reachable; a **scrubbed env** (no inherited
  `PATH`/`HOME`/secrets; only locale vars); stdin closed; and a **process-group-
  killed** hard timeout (`--rerun-timeout`, default 30s).
- **Structural match only** (design §11 / principle #1): `verified` iff exit ==
  `expect_exit` (default 0) AND any verbatim `expect` substring is present —
  decided over the FULL output, never a reading of its meaning. `observed` carries
  the exit, a **head+tail** excerpt (so a runner's tail summary survives
  truncation), a `truncated` flag, and an explicit `expect_found` so the receipt
  asserts the match even when it falls in an elided region.
- **Asymmetric stamping (honest, like `code`)** — a command that COULDN'T be run
  (off-allowlist, path argv[0], executable absent or resolving inside cwd, timed
  out, unparseable) is `unverified` (an inability, not a contradiction); a command
  that RAN and contradicted its expectation is `refuted` (a positive contradiction).
  `render_verdict.py`'s couldn't-verify bucket is now **kind-aware** — a refuted
  command reports its observed exit, not the code/quote "not found" wording.
- **Schema (additive, stays `advisory-board/verdict@2`)** — `command` evidence may
  carry optional `expect_exit` (int) and `expect` (verbatim substring); both are
  validated by `board_verdict.py` when present. Bare `{kind, command}` citations
  and older verdicts are unaffected.

### Honest limits
- A subprocess is **not a kernel sandbox** (acknowledged the same way the egress
  scanner is in design §8). The program allowlist + the containments above stop
  *planted-code* and *secret-env* paths, but a program you allowlist can still
  READ files its uid can read and **persist them into `verdict.json`'s
  `observed.output`** — so do NOT allowlist programs that read secrets (`cat`,
  `env`, `printenv`). Allowlist only programs you trust to be read-only over public
  material.

Hardened by **two security-focused adversarial-review rounds**: the first found 3 RCE
paths (relative argv[0] running a planted script, a dirty-PATH bare-name hijack, a
too-broad regex choosing argv[0]) plus exfil/timeout/renderer issues — all fixed by the
program-pinning + curated-PATH + isolated-cwd design above; the second confirmed the RCE
rewrite held (no shipping blocker) and caught two fail-safe fix-introduced issues (a bare
command that exits non-zero with no expectation pinned was mislabeled `refuted` → now
`unverified`, so an env-shaped failure isn't defamed as a fabricated receipt; and HOME is
now a SEPARATE throwaway, never the `--rerun-cwd` tree).

This completes the v1.x line of `design/run-board-v1x.md` (M1, M2, M3, M4 all done).
**Suite: 430 tests** (up from 386: +44 M3 tests).

## [v1.3.0] - 2026-06-25 — M2: neutral synthesizer seat

`run --synthesize` now spawns a single **no-lens synthesizer seat** that drafts
`verdict.json` from the final-round reviews. The conductor still does NOT generate the
verdict in code (§11); the synthesizer is a **reasoning seat**, briefed only on the round
artifacts + the conductor-extracted `VERDICT:` tokens — its output is **merged into an
authoritative skeleton** (schema/title/date/rounds/board are conductor-owned) and
**schema-validated against `advisory-board/verdict@2` before any write**. The human still
gates ship/abstain (`board_verdict.py --gate`).

### Added
- **Neutral synthesizer seat (M2)** — new pure module `scripts/_conductor/synthesizer.py`
  with `SYNTHESIZER_TEMPLATE` (versioned `advisory-board/synthesizer@1`, sha256 recorded
  in the recipe + the synth raw record), `build_skeleton` (per-seat `round_verdicts`
  pulled from `parse_verdict` over each round artifact — never the prose), `extract_json_object`
  (handles ```` ```json ```` fences, bare ``` fences, prose-prefixed replies, and
  bare brace-balanced objects; the LAST match wins; nested `}` inside JSON strings are
  brace-balanced safely), `merge_synthesizer_content` (drops `PROTECTED_SKELETON_KEYS` =
  `{schema, title, date, rounds, board}` so a model reply cannot rewrite the structural
  shell; recomputes `unanimous` from the final-round tokens vs. the merged verdict so a
  model-asserted flag cannot contradict the observed board), and `run_synthesizer` (one
  retry on Timeout|InvalidOutput per §13; persists a Black-Box Recorder `.raw` alongside
  the seat reply; refuses synthesis if any usable seat lacks a `VERDICT` token, with
  `failure_class="missing-verdict-token"` — the conductor must not invent a token to
  satisfy the schema).
- **CLI surface** — new flags `--synthesize` and `--synthesizer-seat SEAT` on both `init`
  and `run`. `--synthesizer-seat` must name a board seat (the synthesizer egresses to that
  seat's already-disclosed provider — a fresh provider would need its own disclosure);
  default order is `claude` → first usable seat. Both flags persist in the recipe so
  `--from-recipe` reproduces a synthesized run.
- **Provenance** — when `--synthesize` is on, the run dir adds
  `prompts/synthesizer.prompt` (the exact bytes the synthesizer received),
  `synthesizer/<seat>.md` (the verbatim reply), `synthesizer/<seat>.raw` (the
  Black-Box Recorder: argv, prompt + packet sha256, model-answered, parse/schema
  errors, accepted yes/no), `logs/synthesizer-<seat>.stderr`, and a new
  **`## Synthesizer`** section in `run-metadata.md`. A run that failed validation
  drops the merged-but-rejected JSON to `verdict-rejected.json` so the human can
  hand-fix from there. The run-card and artifact tree show the synthesizer when on.
- **Recipe schema** — new fields `synthesize` (bool), `synthesizer_seat` (string|null),
  `synthesizer_template` (`advisory-board/synthesizer@1` when on), and
  `synthesizer_template_sha256` (drift-detection across the egressed bytes).

### Honest limits
- The synthesizer is opt-in by design (decision D3) — synthesis is a reasoning task and
  the human still gates ship/abstain at the `validate --gate` step. The conductor calls
  no gate automatically on a synthesized verdict.
- Validation reuses `board_verdict.validate` (the same gate the user runs); on failure
  the conductor writes `verdict-rejected.json` + a loud warning, **never** a `verdict.json`
  that didn't validate, and exits 0 (the rounds succeeded — synthesis is a value-add).

## [v1.2.0] - 2026-06-25 — M4: smarter cross-reading digest

Round 2's `summaries` packet is no longer each round-1 review head-truncated to a char
budget (which silently dropped every section past the first). It is now a **structured
digest**: a verdict/citation **agreement header** over the board, then **every seat's take
on each topic side by side** — a sharper signal for round 2 (and the `auto` stop-rule) to
debate against.

### Added
- **Structured cross-reading digest (M4)** — a new pure module `scripts/_conductor/digest.py`
  replaces the head-excerpt `summaries` packet. It is §11-safe (principle #1: the conductor
  plumbs, the models reason) — it does NOT cluster claims semantically. It regroups each review
  **by the review's own section headers** (matching section *labels*, not claim content, to a
  fixed canonical taxonomy: Verdict / Objections / Sequence / Invariants / Risks / Evidence /
  Challenges) and surfaces agreement/conflict **only through M1's machine signals**: the parsed
  `VERDICT:` tokens (`unanimous` vs `split — 2×caution, 1×block`) and citations raised by ≥2 seats.
  Handles markdown headings (`## 1. Verdict`), numbered-bold headers (`**1. Verdict**`), lettered
  and roman sub-points (`### A. …`, `### II. …` stay inside their parent section), and code fences
  (a `#` line inside a ``` block is not a header); reviews with no parseable headers degrade
  gracefully to a head excerpt. `full` and `none` are unchanged. Golden-file test over the committed
  example's three real reviews + an end-to-end `--cross-reading summaries` run. Hardened by an
  adversarial review (16 findings — two parser content-loss bugs, code-fence awareness, the
  `parse_verdict` decoration handling, and a round-N debate-section bucket — all fixed). 343 tests.

### Changed
- **`parse_verdict` precision (M1 primitive, shared with M4)** — the verdict token must now be the
  FIRST word of the value (the bare-token contract `VERDICT: <token>`), so a prose label like
  `Verdict: REJECT / DO NOT SHIP` is no longer misread as `ship`. Compliant M1 reviews (a clean
  trailing `VERDICT:` line) are unaffected.
- **Retired the old head-excerpt `_digest`** (and `ROUND2_SUMMARY_BUDGET`) — superseded by the
  structured digest; `summaries` now routes through `build_structured_digest`.

## [v1.1.0] - 2026-06-25 — M1: Round 3 / `auto` stop-rule

The board no longer always runs a fixed two rounds. `--rounds auto` keeps debating
**while the board is still moving** and stops the moment it goes quiet; `--rounds 3`
now runs a real third round (the old clamp-to-2 note is gone).

### Added
- **Round 3 / `auto` stop-rule (M1)** — each seat now ends its review with a machine-readable
  `VERDICT: ship|caution|block` line, and a new pure module `scripts/_conductor/convergence.py`
  measures **movement** between consecutive rounds as a function over *only* the parsed token and
  the seat's concrete citation set (inline-code spans + file-shaped paths) — never the prose
  (principle #1 / §11: the model reasons, the conductor diffs tokens). A seat *moved* if its
  verdict token shifted or it brought a new citation; `--rounds auto` loops rounds 2…N while
  board-wide movement stays at/above the threshold and stops at `converged` (or the `--max-rounds`
  ceiling, default 3). The per-transition movement and the stop reason are recorded in a new
  **`## Convergence`** section of `run-metadata.md`, and each seat's parsed verdict token is a new
  `verdict` column in `run-metadata.tsv`. New flag `--max-rounds N` (persisted in the recipe, so an
  `auto` run reproduces its ceiling). The suite is **325 tests** (up from 287), including the
  adversarial rephrase property (same token + same citations ⇒ *no movement*, exercised end-to-end),
  the citation-delta movement arm, and the mid-debate-collapse guard (a board that drops below two
  voices in round 2+ is never handed off for synthesis). Hardened by two rounds of adversarial review.

### Added (workflow tooling — shipped with this release)
- **Plan view** — `scripts/render_plan.py` renders a self-contained HTML view of a planning
  document deterministically **from** its markdown (`design/<plan>.md` is the source of truth),
  the same render-from-source discipline as `verdict.json → final-consensus.html`. It parses a
  small markdown dialect — milestones / phases / `[ ]/[wip]/[x]/[f]` checklists, per-phase testing
  strategy and a named validation gate, decisions, risks, and an inlined SVG diagram — and computes
  every progress ring, status rail, and badge from the checklist states (they can't lie about the
  markdown). Claude brand styling (Poppins + Lora embedded as base64, the clay palette, WCAG-AA
  text) via `references/plan-template.html` + `references/plan-fonts.css` (regenerated by
  `scripts/_embed_fonts.py`). Malformed structure fails loud rather than dropping content; markdown
  links and inlined SVG are sanitized. 39 tests, including a drift guard that fails if a committed
  plan HTML falls out of sync with its markdown.
- `design/run-board-v1x.md` (+ rendered `design/run-board-v1x.html`) — the v1.x conductor feature
  plan, authored in the new dialect as the first real plan view (a reviewable starting draft).

### Changed
- **Prompt templates bumped to `round1@2` / `round2@2`** — the `VERDICT:` line is appended to both
  round templates and the round-2 template is generalized to any round N (it keeps the same structure
  and markers — `This is round 2`, `BOARD ROUND-1 REVIEWS` — for round 2, with the VERDICT line
  appended and a minor intro rewording). This changes the egressed bytes, so `prompt_template_sha` and
  the template versions bump (the recorded sha is the tamper-evident record of the change). The
  committed `examples/payments-idempotency-review/` is left untouched — it faithfully records a
  historical `round2@1` run.
- **Shared template engine** — the block / `{{TOKEN}}` machinery that `render_handoff.py`,
  `render_verdict.py`, and `render_plan.py` each carried (separately, and re-copied by
  `render_plan`) is extracted into `scripts/_render_engine.py`, parameterized by each caller's
  `BLOCK_KEYS`/`RAW_TOKENS`. `render_plan`'s SENTINEL stash (which holds verbatim author content —
  an inlined SVG, a quoted `{{…}}` snippet — out of the comment-strip and leftover-placeholder
  guards) now lives in the shared engine as an opt-in. Pure refactor: every renderer's output is
  byte-identical to before (verified against the committed example and plan view). +20 engine tests.

## [v1.0.0] - 2026-06-25 — v1: production-ready

The conductor's v1 scope (milestones M1–M6) is complete and has been exercised end-to-end
against real models. Declaring the line **stable**. No code change from `v0.6.0` — this is the
deliberate production-ready call the pre-1.0 scheme reserved.

### What v1 is
- **Engine** — a seat-adapter registry (claude / codex / gemini, plus antigravity and a local
  ollama seat), an executable preflight (GO/NO-GO), and round-1 + round-2 cross-reading fan-out
  with the §13 failure protocol (timeout / retry / classification, honest `model_answered`).
- **Safety** — a hash-bound egress/quarantine gate with tiered consent and a pre-spawn hard stop,
  capability-removal isolation in gate mode, and the evidence gate.
- **Verdict** — the canonical `advisory-board/verdict@2` with typed, resolved evidence
  (`verify_evidence.py`), Markdown/HTML rendered *from* the verdict (`render_verdict.py`), and the
  observed-agreement `abstain` gate (`board_verdict.py`).
- **Proven** — the first real, token-spending board run is the committed
  `examples/payments-idempotency-review/` (self-verifying).

### The v1 contract (stable)
- The `advisory-board/verdict@2` schema, the `run-recipe@1` format, the CLI subcommand surface,
  and `board_verdict.py` exit codes (`0` pass / `1` block / `2` schema / `3` abstain).
- Future work (Round 3 / `auto`, a spawned neutral synthesizer, `command`-evidence execution) is
  additive v1.x — see `design/run-board-conductor.md` §15.

## [v0.6.0] - 2026-06-25 — M6: docs/drift + the real proof-of-life run

The first token-spending board run: the conductor drove three subscription CLIs through
the full pipeline (preflight → egress gate → round-1/2 fan-out → synthesis → verify →
consensus → validate), end to end, against real models.

### Added
- **`examples/payments-idempotency-review/` regenerated via the conductor** as the real
  proof-of-life run (`claude-opus-4-8` · `gpt-5.5` · `gemini-3.5-flash`, 2 rounds, `full`
  cross-reading). The example is now an `advisory-board/verdict@2` with resolved evidence
  (8 `source` quotes verified against the captured packet), the rendered `final-consensus.md`/
  `.html`, and the run's provenance/consent summary (`run-recipe.yaml`, `run-metadata.{md,tsv}`,
  `egress-manifest.md`, `sensitivity.json`). All three seats independently converged on a
  unanimous `block`.

### Fixed
- **`parse_model_answered` no longer mines the echoed cross-reading packet.** A CLI like codex
  echoes its prompt to stderr; in a `--cross-reading full` round 2 that packet can carry a
  `"model": "…"` line (e.g. a quoted CLI example), which was being reported as the answering
  model — a false provenance value that violated the "never assume, unknown means unknown"
  rule. The parser now bounds its scan to the banner region before the `MATERIAL UNDER REVIEW`
  delimiter. Surfaced by the proof-of-life run itself.

### Changed
- **`SKILL.md`**: the conductor (`scripts/run_board.py`) is now documented as the canonical run
  driver; the `CLI Execution Notes` point at the seat-adapter **registry** as the canonical,
  self-healing source for execution mechanics, with the manual per-CLI templates reframed as
  the portable, script-free fallback (design §12 drift-resolution).

## [v0.5.0] - 2026-06-25 — M5: canonical verdict + resolved evidence

`verdict.json` becomes the source of truth for the board's decision; the Markdown and HTML
render from it. Synthesis stays a reasoning task (design §11) — the conductor produces clean
per-round packets and the agent fills `verdict.json`; it does not generate the verdict in code.

### Added
- **Schema `advisory-board/verdict@2`** — typed `evidence[]` (kinds `code`/`source`/`command`/`judgment`)
  with an optional `status` (`verified`/`unverified`/`refuted`) on blockers, dissent, and concerns.
  `board_verdict.py` validates both `@1` and `@2`.
- **`scripts/verify_evidence.py`** — resolves `code` `path:line`/`symbol` against `--source` and
  `source` quotes against the captured packet (`--packet`/`--run`), never a live URL fetch
  (respects quarantine); stamps each citation. `command` is deferred (`unverified`); `judgment`
  is left unstamped. Path-safe (rejects absolute/`..` paths and basename collisions).
- **`scripts/render_verdict.py`** — renders `final-consensus.md` from the canonical `verdict.json`
  (evidence trail + couldn't-verify bucket); `--handoff-data`/`--html` derive the HTML via the
  existing `render_handoff.py`. Per-round prose is pulled from `round-N/<seat>.md`, never invented.
- **`board_verdict.py --gate` abstain** — a neutral exit `3` ("human required"), driven by observed
  cross-seat agreement (`round_verdicts`), never the gameable `confidence`. Fires when the board is
  torn across the threshold with no majority, when the declared verdict clears the gate while a
  majority of seats trip it (the injected-"ship" case), or when any citation is refuted.
- **`run_board.py` subcommands `verify` and `consensus`**; `run` now prints the
  synthesis → verify → consensus → validate chain at the end of a run.

### Changed
- `references/verdict-schema.md`, `scripts/README.md`, `tests/README.md`, and the `SKILL.md`
  helper list updated for the verdict chain and the `@2` schema.

### Notes
- The shipped `examples/payments-idempotency-review/verdict.json` stays `@1` (regenerated via the
  conductor in M6).
- Verification: 227 standard-library tests; live preflight 3/3 GO; CLI byte-identical. Shipped in
  [#11](https://github.com/timharris707/skills/pull/11), reviewed by a 5-agent adversarial pass.

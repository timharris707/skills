# Changelog — advisory-board

All notable changes to the `advisory-board` skill are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases are
cut as **skill-scoped semver tags** `advisory-board/vX.Y.Z` (see [`RELEASING.md`](../../RELEASING.md)).
Pre-1.0 the minor tracks the conductor milestone (M5 → `v0.5.0`, M6 → `v0.6.0`); `v1.0.0` is
reserved for an explicit production-ready call. The verdict-JSON schema is versioned separately
(`advisory-board/verdict@N`) and is not the same axis as the release version.

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

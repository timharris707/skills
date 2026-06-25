# Changelog — advisory-board

All notable changes to the `advisory-board` skill are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases are
cut as **skill-scoped semver tags** `advisory-board/vX.Y.Z` (see [`RELEASING.md`](../../RELEASING.md)).
Pre-1.0 the minor tracks the conductor milestone (M5 → `v0.5.0`, M6 → `v0.6.0`); `v1.0.0` is
reserved for an explicit production-ready call. The verdict-JSON schema is versioned separately
(`advisory-board/verdict@N`) and is not the same axis as the release version.

## [Unreleased]

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

# Changelog — advisory-board

All notable changes to the `advisory-board` skill are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases are
cut as **skill-scoped semver tags** `advisory-board/vX.Y.Z` (see [`RELEASING.md`](../../RELEASING.md)).
Pre-1.0 the minor tracks the conductor milestone (M5 → `v0.5.0`, M6 → `v0.6.0`); `v1.0.0` is
reserved for an explicit production-ready call. The verdict-JSON schema is versioned separately
(`advisory-board/verdict@N`) and is not the same axis as the release version.

## [Unreleased]

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

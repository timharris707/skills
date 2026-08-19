# Changelog: show-me-your-work

All notable changes to the **show-me-your-work** skill. Unpromoted (lives in
`in-progress/`); versioning starts when it moves to a promoted bucket. This
file is the source for its eventual release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Initial draft: a reviewable decision trail for long-running or unattended
  work. One canonical append-only TSV (`ts, phase, decision, why, evidence,
  result`), one row per decision, local by default and committed only when a
  reviewer needs the trail to trust the result, with a closing self-audit
  against the session's own record and an optional cross-model review gate
  routed through advisory-board's CLI-seat runners (same-family subagent
  fallback, stated as weaker). Adapted from Lauren Tan's pstack
  `show-me-your-work` (github.com/cursor/plugins, MIT), keeping its `log.sh`
  spreadsheet-formula-injection hardening; positions itself as a per-run audit
  ledger, distinct from handoff (resume pointer) and domain-memory
  (institutional why).

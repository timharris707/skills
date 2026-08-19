# Changelog — blast-radius

All notable changes to the **blast-radius** skill. Versioned as a standalone
plugin (`blast-radius/vX.Y.Z`); this file is the source for its release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [v1.0.0] - 2026-08-19 — promoted to run/

### Changed

- **Promotion** (#250): moved from `in-progress/` to `run/` and claimed as a
  standalone plugin. Sibling links updated for the new path, and the prose-pass
  line now points straight at plainspoken, which shipped v1.0.0 in #240 (the
  old "once that skill is in reach" hedge no longer held).
- **Em-dash sweep** (#226): the Done-when heading's em dash became a colon, the
  file's only occurrence. Guarded by `scripts/check_emdash_density.py` in CI.

### Added

- Initial release: adapted from Lauren Tan's pstack `blast-radius`
  (github.com/cursor/plugins, MIT): pre/mid-change impact analysis with the
  5-rung evidence ladder and the one-fact-it-is-safe-because-of discipline.
  Sibling references remapped to this catalog (adversarial-review for
  escalation, plainspoken for the prose pass), agent-invoked instead of
  user-only, house-idiom body with a checkable Done-when.

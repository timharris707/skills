# Changelog — blast-radius

All notable changes to the **blast-radius** skill. Unpromoted for now; on promotion
it versions as a standalone plugin (`blast-radius/vX.Y.Z`) and this file becomes the
source for its release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- **Em-dash sweep** (#226): the Done-when heading's em dash became a colon, the
  file's only occurrence. Guarded by `scripts/check_emdash_density.py` in CI.

### Added

- Initial adaptation from Lauren Tan's pstack `blast-radius` (github.com/cursor/plugins,
  MIT): pre/mid-change impact analysis with the 5-rung evidence ladder and the
  one-fact-it-is-safe-because-of discipline. Sibling references remapped to this
  catalog (adversarial-review for escalation, plainspoken for the prose pass),
  agent-invoked instead of user-only, house-idiom body with a checkable Done-when.

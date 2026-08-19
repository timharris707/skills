# Changelog — huh

All notable changes to the **huh** skill. Versioned as a standalone plugin
(`huh/vX.Y.Z`); this file is the source for its release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- **Em-dash sweep** (#226): SKILL.md's em-dash constructions rewrote into periods,
  commas, and colons, meaning-preserving; the description's trigger wording is
  unchanged. Part of the catalog-wide sweep guarded by
  `scripts/check_emdash_density.py` in CI.

## [v1.0.0] - 2026-08-16

### Added

- Initial release: decode a message that didn't land. Four moves — restate in
  plain sentences, expand invented shorthand, split report from request, flag
  claims stated without evidence — over either the agent's own last message or
  pasted output from another session, with a checkable exit. Shares only its
  trigger moment with Matt Pocock's `wait-what`; the body is original to this
  catalog.

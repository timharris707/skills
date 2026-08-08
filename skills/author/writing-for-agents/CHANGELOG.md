# Changelog — writing-for-agents

All notable changes to the **writing-for-agents** skill. Versioned as a
standalone plugin (`writing-for-agents/vX.Y.Z`); this file is the source for
its release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **Fidelity audit follow-up** (#122). The Attribution section now says what is
  actually true: the body is a lightly edited adaptation of Matt Pocock's
  [`writing-for-agents`](https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents)
  (MIT) — section by section, much of it near-verbatim — not merely shared
  vocabulary. The "When to split" section his original carries (by sequence /
  by invocation) is restored; the remaining text leaned on it.

## [v1.0.0] - 2026-08-05

### Added

- Initial release: the reference for writing and pruning documents an agent
  consumes — a SKILL.md, an AGENTS.md or CLAUDE.md, a reference reached by a
  pointer. Context pointers, the two loads (always-loaded vs reached-for), the
  information hierarchy, leading words, and the no-op test. Shipped in PR #97
  as the standard the rest of this catalog is written against.

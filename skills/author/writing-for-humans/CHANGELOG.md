# Changelog — writing-for-humans

All notable changes to the **writing-for-humans** skill. Versioned as a
standalone plugin (`writing-for-humans/vX.Y.Z`); this file is the source for
its release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [v1.1.0] - 2026-08-08

### Added

- Dash budget, from the skill's first real application (#150): in human-facing
  copy dashes are the exception, roughly a handful per page, each one earning
  its place. The only fix is restructuring (split the sentence, subordinate
  with a comma, or cut the aside); a mechanical in-place swap of a dash for
  any other mark, comma, semicolon, colon, or parentheses, is named as the
  anti-pattern because it preserves the AI rhythm the rule exists to break.
  New standing voice rule and done-when line in SKILL.md.
- The last-mile scrub now treats em-dash density as a primary tell: a new
  first row in the cluster table that fires on frequency alone, consistent
  with blader/humanizer's treatment of the em dash as one of the most
  reliable AI tells.

### Changed

- The skill's own prose was brought under the dash budget. SKILL.md and the
  scrub reference were reworked: SKILL.md from 30 em dashes to
  five (four in the page body, one in the frontmatter description), the scrub
  from eight to one.

## [v1.0.0] - 2026-08-08

### Added

- Initial release: the human-facing counterpart to writing-for-agents — how to
  write pages, READMEs, and launch posts a stranger will read. Guide structure
  over catalog structure, the warmth moves, three named failure modes
  (agent-register bleed, process bleed, clean nothing), the standing voice
  rules, and a last-mile AI-tell scrub with its guardrails. Shipped from #141.

# Changelog — writing-for-humans

All notable changes to the **writing-for-humans** skill. Versioned as a
standalone plugin (`writing-for-humans/vX.Y.Z`); this file is the source for
its release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **Em-dash sweep** (#226): SKILL.md and `references/last-mile-scrub.md` rewrote
  their em-dash constructions into periods, commas, and colons, meaning-preserving.
  The shipped-page dash *budget* this skill teaches is unchanged; the sweep governs
  the skill's own source prose. Guarded by `scripts/check_emdash_density.py` in CI.

- The last-mile scrub no longer carries its own tell table. The repo's single
  merged AI-tell catalog now lives in the `plainspoken` skill (decision record
  0004: two catalogs drift), and the scrub defers to it, keeping only its
  artifact-specific additions: the voice-sample-outranks-rules and
  no-fabrication guardrails, the dash budget that replaces the catalog's
  outright em-dash ban for shipped pages, the pass steps, and the exit
  checklist.

## [v1.2.0] - 2026-08-13

### Added

- An "It's working if" section: qualities of the finished page judged by reading
  it cold, following the outcome-test shape of Matt Pocock's skill docs pages
  (his `wait-what` docs page is the model). It carries the over-correction
  guard his pattern makes explicit: the final page must be scrubbed but not
  silenced — a page that is only cleaner is clean nothing.
  Done-when gains a line requiring each "It's working if" line be checked
  against the final text, not assumed.

### Changed

- The body was pruned line by line against writing-for-agents' no-op test
  ("does this change behavior versus the default?"), 1,496 words to 1,264
  while adding the new section. Cut: expository openers, in-body attribution
  duplicating the Attribution section (the mattpocock/skills and forint573
  parentheticals), the empathy sentence duplicated between Guide structure
  and Warmth moves, and the positioning rule's rationale prose (the
  third-person-descriptor discussion). The canonical positioning lines, the
  two-legs rule, and the PLAN.md canon pointer survive verbatim.
- Done-when was split against the new section: result qualities moved to
  "It's working if", process checks stayed in Done-when, so no line appears
  in both.

## [v1.1.0] - 2026-08-08

### Added

- Dash budget, from the skill's first real application (#150): in human-facing
  copy dashes are the exception, roughly a handful per page, each one earning
  its place. The only fix is restructuring (split the sentence, subordinate
  with a comma, or cut the aside); a mechanical in-place swap of a dash for
  any other mark (comma, semicolon, colon, or parentheses) is named as the
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

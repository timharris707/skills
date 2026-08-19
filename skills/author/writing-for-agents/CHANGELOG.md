# Changelog — writing-for-agents

All notable changes to the **writing-for-agents** skill. Versioned as a
standalone plugin (`writing-for-agents/vX.Y.Z`); this file is the source for
its release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Punctuation rule** (#226): a compact section stating that skill prose carries
  no em dashes (periods, commas, colons instead), because the em dash is a top AI
  tell and the style of prose an agent reads leaks into what it writes; rationale
  pointed at plainspoken's tell catalog, pattern 13. A matching Done-when bullet
  ("No em dash appears outside a code block") makes it checkable.

### Changed
- **Em-dash sweep** (#226): SKILL.md and `references/skill-mechanics.md` rewrote
  their em-dash constructions into periods, commas, and colons, meaning-preserving;
  the frontmatter description's trigger wording is unchanged. The description-shape
  example in skill-mechanics now demonstrates the swept form. Part of the
  catalog-wide sweep guarded by `scripts/check_emdash_density.py` in CI.

## [v1.0.1] - 2026-08-13 — fidelity and invariant corrections

### Changed

- **Done-when invariant claim corrected** (the catalog audit): the completion-criteria
  section claimed the `## Done when (checkable)` section is one "every skill carries";
  advisory-board, router, and orchestrate legitimately lack one (a gated artifact chain,
  a menu, a standing role). The sentence now scopes the invariant to task-shaped skills
  and names the exemption as a deliberate call. (The audit also added the missing
  Done-when to handoff, the one task-shaped skill without one.)

- **Terminology: agent-invoked / user-invoked** (#144). The skill-mechanics
  reference now says who actually triggers a skill: the invocation-mode section
  and its table say "agent-invoked" and "user-invoked" instead of the old
  model-/human-centred phrasings. The literal frontmatter key
  `disable-model-invocation` is the harness's name and stays quoted as-is.

- Cross-link to the new sibling skill **writing-for-humans** (#141): the intro
  now names when the other register applies — a document a human reads goes to
  the counterpart, not through these levers.

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

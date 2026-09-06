# Click AI for Codex changelog

## [Unreleased]

## [v1.1.0] - 2026-09-05

- Carry the team-workflow v1.7.0 positioning: orchestrate is described as the seat a
  non-engineer works from, setup asks the working-mode question (read the code, or lead
  from outside it) and records the answer in the binding doc, and the router sends a
  `lead` repo's new task to the orchestrator seat. Protocols are unchanged.

## [v1.0.0] - 2026-09-04

- Ship all 23 Click AI skills as a separate native Codex desktop plugin, tuned
  for Astra at medium and extra high while respecting the user's model settings.
- Adapt orchestration to native subagents, explicit workspace ownership, current
  question tools, bounded monitoring, and evidence-based review.
- Keep task ownership through compaction with a portable checkpoint resolver and
  recovery instructions. No automatic hooks or global configuration changes.
- Preserve the existing Claude packages and legacy Codex plugin. Include complete
  generated resources, a reproducible release ZIP, and SHA-256 verification.
- Publish matching Codex skill pages and agent Markdown at Clickai.dev, with clear
  edition selection and installation instructions.

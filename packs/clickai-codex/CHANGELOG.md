# Click AI for Codex changelog

## [Unreleased]

## [v1.1.1] - 2026-09-05

- Restore distinct invocation branches across all 23 descriptions, with positive
  and negative review cases and offline branch-preservation checks. These checks
  do not claim measured model activation or Astra performance improvements.
- Make decision-maker source and conflict safeguards, review completion, independent
  review of substantive corrections, and checkpoint secret inspection explicit.
- Distinguish unverified, GO, and NO-GO provider candidates; validate the actual
  model route under authorization and launch only approved, verified seats.
- Label documented capabilities, desktop observations, and workflow policy, with
  live-schema fallbacks. Describe the edition as adapted for Codex and Astra.
- Preserve proportional tests, required regression checks, pending report decisions,
  selected project voice, and same-task recovery; correct stale explanations.
- Adopt the shared mixed ticket/non-ticket blocker fix from team-workflow v1.7.2.

- The nine advisory-board fixes and the wizard write_env fix that shipped only in this
  edition (#286) are now in the shared source (advisory-board v1.18.3, team-workflow v1.7.1);
  their patch hunks are gone. No Codex-facing change.

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

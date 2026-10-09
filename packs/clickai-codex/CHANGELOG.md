# Click AI for Codex changelog

## [Unreleased]

- Carry team-workflow's announce toggle rename (#194): orchestrate and the binding-doc
  template name the toggle `announce extras: on/off`. orchestrate also names the former
  name, `announce model/effort`, so a binding doc still using it keeps working, and setup's
  audit reports that line as drift. Identity announcing is unchanged.
- Carry orchestrate's integration-branch rule (#310): before closing a spec item at a
  lane's close-out, the orchestrator gives its open dependents outside the spec the
  `blocked` label until the spec's final PR reaches the default branch, and takes it off at
  that PR's close-out unless another non-ticket blocker still applies. The reference is
  shared unchanged with this edition.
- Carry team-workflow's two show-me-your-work fixes (#283, #284). The bundled `log.sh`
  stops with an error, instead of finishing the row, when the log's unterminated last row
  has fewer than six fields or an empty last field; a row cut inside a nonempty last field
  still cannot be told apart from a short one. In a
  loop run, an iteration with no fork, verified unit, pivot, blocker, or gate fix gets no
  row. The Done-when asks for one row for each fork, pivot, and abandoned approach listed
  from the run's record. This edition's append-a-correction audit wording is unchanged.
- Carry team-workflow's git guardrail fix (#309): the bundled, unwired
  `setup/scripts/git_guardrails.py` reads a `git tag` listing filter such as `--merged` as
  listing, never as creating a tag, and skips a `--sort` or `--format` value so it is
  never read as the tag name or as a mode option.
- Carry setup's new audit check (#306): where a binding doc records the git guardrail as
  seeded, as a repo shared with Claude Code can, the audit reports a script that is missing
  or git-ignored, and names the fix as restoring the bundled script or un-ignoring it. This
  edition records the guardrail as a gap on Codex, which produces no finding. Setup's
  un-ignore guidance for the guardrail's settings file (#311) sits in the part this edition
  replaces, so it changes nothing here.
- Carry team-workflow's two new labels (#305): setup's reference vocabulary, the tracker
  reference, and the binding-doc template add `needs-info` and `wontfix`. A project bound
  earlier keeps working without them.
- Ship team-workflow's new handoff hook reference (#320), `setup/references/handoff-hook.md`,
  unwired: it is the Claude Code session-start entry, and setup's Codex continuity step now
  says to leave it unwired, as it does for the git guardrail script. Codex continuity still
  uses the task checkpoint resolver; the handoff adaptation is unchanged.
- Carry team-workflow's explicit skill loading (#302) in Codex's own words: each step that
  must load another skill now says "open and read the `<name>` skill's SKILL.md
  completely", the way Codex's skill instructions say to use an installed skill, since
  Codex has no Skill tool for skills installed as files. Sixteen steps changed, the same
  ones as the Claude edition except two: the successor prompt, which this edition's
  orchestrate does not have, and grilling's research step, which stays a mention because
  Codex bars handing skill reading to a subagent. show-me-your-work's cross-model gate
  links advisory-board's runner reference, where installed. Orchestrate drops two
  restated phrases with team-workflow (the "rule-based" label and "setup may offer wiring
  it") and keeps its titling section's retired-marker clause, the only place this edition
  defines that marker. writing-for-agents' mechanics reference records the convention
  with this wording.

## [v1.3.0] - 2026-10-06 — adopts team-workflow v1.9.0

- Carry team-workflow's pr-writing promotion (#300): the PR-writing guide is now its own
  `pr-writing` skill, so the package ships 24 skills. The Codex adaptation moves with it:
  the skill reads every unresolved review finding whatever its age, instead of acting only
  on comments newer than the latest push, and its Done-when list says the same. Setup's
  conduct pointer, orchestrate, the lane-brief template, and the router point at the skill.

## [v1.2.0] - 2026-10-06 — adopts team-workflow v1.8.0

- Carry the team-workflow PR-writing change (#298): every agent-filed PR shows before-and-after
  evidence that something ran, says whether a revert fully undoes it and how much could break,
  and may add a small diagram for reviewers. The Codex review-feedback adaptation is unchanged.
- Carry team-workflow's catch-up rule and optional per-spec integration branch (#299):
  workers bring their work up to date with the merge target and re-run verification
  before reporting. A worker that may not commit carries its preserved working diff onto
  the target instead. If the target moves again before the merge, the orchestrator updates
  the work itself where that applies cleanly; only a conflict goes back to the worker.
- Adopt the four shared changes from team-workflow's #297: the wizard no longer shows a time
  estimate, diagnose gains the redaction rule, to-tickets attaches each ticket to its source
  issue as a sub-issue (the tracker reference carries the recipe), and domain-memory's
  attribution links point at the renamed `GLOSSARY-FORMAT.md`.
- Setup records the team-workflow git guardrail hook as a gap: Codex hooks cannot return
  an ask decision yet, and the guardrail asks rather than blocks. The binding-doc template
  carries the gap line. The hook script ships in the package unwired.
- Correct two stale lines shipped in v1.1.1: setup's glossary-edit and conduct-pointer
  steps now point at Configuration ownership instead of a sync-managed section this
  edition does not have, and the PR-writing attribution no longer credits Theo Browne
  with the newer-than-latest-push rule, which this edition replaces.

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

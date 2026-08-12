# Team workflow — repo bindings

<!-- Seeded by the team-workflow pack's setup skill. This doc is the single place the pack's
     skills read repo-specific facts from; keep it current via a setup re-run (idempotent
     refresh), not hand-drift. -->

_Pack version: v1.4.0 (this repo is the pack source; main may run ahead of the release tag) · Last confirmed: 2026-08-12_

## Tracker binding

- **Tracker**: GitHub Issues on `timharris707/skills`
- **Claim recipe**: the pack's tracker-discipline recipes as written (`gh`-based)
- **Frontier query**: `gh issue list --repo timharris707/skills --state open --label ready-for-agent --json number,title,labels` — dual-read against the `blocked` label and blocking edges in issue bodies
- **Blocking**: `blocked` label + "Blocked by #N" lines in issue bodies (dual-read; either alone is insufficient)
- **Label vocabulary**: pack defaults, created at setup on 2026-08-12 (`needs-triage`, `ready-for-agent`, `ready-for-human`, `blocked`, `slice`, `gate-decision`, `process`; `bug` pre-existed)

## Verify commands

<!-- The exact commands that constitute "verified" here — the CI suite, runnable locally. -->

```bash
python3 scripts/check_router_freshness.py
python3 scripts/check_invocation_freshness.py
python3 scripts/check_site_disclosure.py
python -m compileall -q skills/decide/advisory-board/scripts
```

Doc-only changes additionally verify that every changed file's relative markdown links resolve. The advisory-board mock validation in `ci.yml` runs when that skill's scripts change.

## The decider

- **Decider**: Tim Harris (@timharris707)

Every pack skill says "the decider"; this line is where the role resolves. Sessions brief decisions with recommendations and evidence; the decider answers them on the record.

## Docs home

- **Binding doc home**: `docs/agents/team-workflow.md` (this file)
- **Decision maps**: `docs/agents/<scope>-decision-map.md`
- **Research findings**: `docs/agents/research/`
- **Domain/context docs agents should load**: `CONTRIBUTING.md`, `RELEASING.md`, and — for skill-authoring lanes — `skills/write/writing-for-agents/SKILL.md`

## Precedence & exemptions

How the pack composes with this repo's resident rule systems. Resident rules win unless an exemption below says otherwise.

- **Prototype test-exemption**: code on `prototype/<name>` branches is exempt from the repo's test-first / coverage rules — prototype branches are throwaway by contract and never merge; the exemption ends the moment the winner's real implementation starts.
- **This repo is the pack source**: the pack skills under `skills/` are the live, authoritative copies — a lane editing a skill is editing the protocol every consuming repo installs. Skill-doc changes conform to `writing-for-agents` and carry a pack CHANGELOG entry per `CONTRIBUTING.md`.
- **Merge rule (CLAUDE.md)**: an agent may merge a PR once checks are green and CodeRabbit is dispositioned (every finding verified and replied to on its thread — fixed or declined with a reason). Branch protection additionally requires the branch up to date with `main` and all review threads resolved.

## Templates

- Issue/work-item spec: adopted in place — this repo is the pack source; the authoritative template is `skills/orient/setup/references/templates/issue-slice-spec.md` (no `.github/ISSUE_TEMPLATE` copy seeded)
- Lane brief: adopted in place — `skills/orient/setup/references/templates/lane-brief.md`

## Domain memory

- **Memory home**: `docs/agents/memory/` — `decisions/` directory + `terms.md`, git-tracked (in-repo by the decider's explicit choice, 2026-08-12: bindings and institutional memory live per-project, never per-profile)
- **Size bound**: 30 records — past it, sessions offer a consolidation pass, dispositioned by the decider
- **Backfill**: not requested

## Handoff

- **Handoff location**: `.claude/handoff.md`, untracked
- **Ignore entry**: already present (`.gitignore` ignores `.claude/*` except `settings.json`)
- **Session-start auto-load hook**: seeded in `.claude/settings.json` (git-tracked, repo-owned — not sync-managed) on 2026-08-12

## Adversarial review

- **Defect-class file**: none seeded — this repo's changes are skill docs, not application code; the review bar is the rule-preservation and writing-for-agents disciplines. Revisit at re-run if code-bearing skills grow.
- **Layers**: floor + orchestrator close-out. Close-out layer is mandatory (not CodeRabbit alone) for changes to pack-skill protocol files when the item's spec says so — the decider's standing word for critically important skills (e.g. orchestrate).
- **Mandatory lenses**: rule-preservation on any compaction/restructure of a skill doc (every normative rule present, none weakened — inventory-checked)
- **Live-probe policy**: no live probes
- **Substantiality rules**: any change to a pack skill's SKILL.md is substantial

## Orchestration

- **Lane launch**: default in-process Claude Agent subagent in an isolated worktree (`Agent` tool, `isolation: worktree`); background-task chip session for lanes expecting mid-flight approvals, long-lived work, or decider-watching (per orchestrate §4's shape rule). Claim posted as a `Lane-start` comment on the issue before launch, stamping runner, model/effort source, and workspace. Titling: launcher titles; subagent lanes have no picker entry — the launch report carries identity. Chip-launched sessions are pre-titled by the chip label (title protocol outranks the chip's imperative-label convention). Native auto-archive on PR close: no — the notification path per orchestrate §5 step 6.
- **Announce model/effort**: on
- **Runner inventory**: Claude (Agent tool subagents; background-task chips; `claude` CLI for detached sessions). No launcher script — launches are tool-call-native; this section is the recipe doc.
- **Runner policy**: Claude only, orchestrator's choice of vehicle (decider-set 2026-08-12). Fallbacks loud per orchestrate §4.
- **Workspace provisioning**: git worktrees under `.claude/worktrees/` (harness-provisioned per lane); no per-lane resources beyond the worktree and branch — prune both at close-out.
- **Monitoring**: inline `gh` polling (filtered, count-shaped) on a ~4-minute background-sleep metronome while lanes are live, re-armed each wake; subagent completion notifications for lane liveness.
- **Verification executor**: delegated verifier subagent in the lane's workspace for anything non-trivial; inline for one-command checks. Per-command exit codes, zero skipped checks.
- **Review-tier policy** (decider-set 2026-08-12, canonical shape):
  - Mechanical verification re-runs: Haiku (or session model) at low effort · floor: never the adversarial pass itself
  - Adversarial review (finders, skeptics, re-probes): session model at high effort on pack-skill changes · floor: no low-effort skeptics on pack-skill protocol changes
  - Max tier: decider-named cases only — never a default
- **Merge flow**: lane branch → PR → CI checks + CodeRabbit disposition per the merge rule above → squash-merge by the orchestrator → issue close-out comment → prune worktree/branch.

## Accepted drift (written by setup's audit mode)

<!-- Drift findings the decider accepted as this repo's recorded choice instead of updating
     the binding. The next audit reads this list and does not re-flag an entry here. -->

_None yet._

## Friction log (optional)

- Pack friction gets filed as `process`-labeled issues on the tracker.

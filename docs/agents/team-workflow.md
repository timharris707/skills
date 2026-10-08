# Team workflow: repo bindings

<!-- Seeded by the team-workflow pack's setup skill. This doc is the single place the pack's
     skills read repo-specific facts from; keep it current via a setup re-run (idempotent
     refresh), not hand-drift. -->

_Pack version: v1.9.0 (this repo is the pack source; main carries unreleased changes ahead of the tag) · Last confirmed: 2026-10-07_

## Tracker binding

- **Tracker**: GitHub Issues on `timharris707/skills`
- **Claim recipe**: the pack's tracker-discipline recipes as written (`gh`-based)
- **Frontier query**: the pack's frontier recipe (dual-read) with this repo written in, from `skills/orient/setup/references/tracker-discipline.md`, "Frontier recipe (dual-read)". The command lists every open issue with its labels, assignees, and count of open blockers; the rule below picks out the grabbable ones.

  ```bash
  gh api 'repos/timharris707/skills/issues?state=open&per_page=100' --paginate --jq '.[]
    | select(has("pull_request") | not)
    | {number, title,
       labels: [.labels[].name],
       assignees: [.assignees[].login],
       blockedBy: (.issue_dependencies_summary.blocked_by // 0)}'
  ```

  Grabbable = has the `ready-for-agent` label AND `assignees == []` AND `blockedBy == 0` AND no `blocked` label. When the frontier is empty, report why (all claimed, triage stalled, or everything blocked).
- **Blocking**: dual-read; either alone is insufficient. A blocker that is itself a ticket is a native GitHub dependency edge, wired with the `blocked_by` command in the tracker-discipline reference; an item held only by edges does not also carry the `blocked` label. A blocker that is not a ticket (a vendor, a date, a pending decision) is the `blocked` label. An older issue whose text says "Blocked by #N" still counts while #N is open: the query cannot see that text, so read it.
- **Label vocabulary**: pack defaults, created at setup on 2026-08-12 (`needs-triage`, `ready-for-agent`, `ready-for-human`, `blocked`, `slice`, `gate-decision`, `process`; `bug` pre-existed)

## Verify commands

<!-- The exact commands that constitute "verified" here: the CI suite, runnable locally. All use `python3`: CI's `python` comes from its setup step, and a Mac has only `python3`. -->

```bash
python3 scripts/check_router_freshness.py
python3 scripts/check_invocation_freshness.py
python3 scripts/check_skill_frontmatter.py
python3 scripts/check_emdash_density.py
python3 scripts/check_site_disclosure.py
python3 scripts/check_positioning.py
python3 scripts/check_lineage_counts.py
python3 -m unittest discover -s tests/gate -p 'test*.py'
python3 -m unittest discover -s tests/hooks -p 'test*.py'
python3 -m unittest discover -s tests/site -p 'test*.py'
python3 scripts/build_codex_plugin.py --check
python3 scripts/check_codex_publication.py
python3 -m unittest discover -s tests/codex -p 'test*.py'
python3 -m compileall -q skills/decide/advisory-board/scripts
python3 -m unittest discover -s skills/decide/advisory-board/tests -p 'test*.py'
python3 -m compileall -q skills/investigate/ingest/scripts
python3 -m unittest discover -s skills/investigate/ingest/tests -t skills/investigate/ingest/tests -p 'test*.py'
python3 -m compileall -q skills/in-progress/retro/scripts
python3 -m unittest discover -s skills/in-progress/retro/tests -t skills/in-progress/retro/tests -p 'test*.py'
```

Four further CI checks run against the built site. The first three need its server up: in `site/`, run `npm ci && npm run build`, start the server in the background or a second terminal (`npm run start &`), then, still from `site/`, run `python3 ../scripts/check_skill_og_cards.py`, `python3 ../scripts/check_skill_md_twins.py`, and `python3 ../scripts/check_site_font_coverage.py` (each retries until the server responds). The fourth checks that the build asks Google Fonts for no font: stop the server, then from `site/` run `rm -rf .next && NEXT_FONT_GOOGLE_MOCKED_RESPONSES="$PWD/../tests/site/google-fonts-mock.cjs" npm run build`. CI additionally greps skill docs for unqualified `gh` commands (every one carries `--repo`), runs `git diff --check` for whitespace, and syntax-checks the advisory-board shell mocks (`bash -n`) on every pull request, whatever files changed.

Doc-only changes keep the reviewer-run gate: every changed file's relative Markdown links resolve, checked at close-out review; no script exists yet (revisit at next setup re-run).

## The decider

- **Decider**: Tim Harris (@timharris707)

Every pack skill says "the decider"; this line is where the role resolves. Sessions brief decisions with recommendations and evidence; the decider answers them on the record.

## Working mode

- **Working mode**: `lead`. The decider does not read code; new sessions in this repo open by invoking orchestrate and following its startup checklist. Recorded 2026-09-05 with decision 0005.

## Docs home

- **Binding doc home**: `docs/agents/team-workflow.md` (this file)
- **Decision maps**: `docs/agents/<scope>-decision-map.md`
- **Research findings**: `docs/agents/research/`
- **Domain/context docs agents should load**: `CONTRIBUTING.md`, `RELEASING.md`, and, for skill-authoring lanes, `skills/author/writing-for-agents/SKILL.md`

## Precedence & exemptions

How the pack composes with this repo's resident rule systems. Resident rules win unless an exemption below says otherwise.

- **Prototype test-exemption**: code on `prototype/<name>` branches is exempt from the repo's test-first / coverage rules: prototype branches are throwaway by contract and never merge; the exemption ends the moment the winner's real implementation starts.
- **This repo is the pack source**: the pack skills under `skills/` are the live, authoritative copies: a lane editing a skill is editing the protocol every consuming repo installs. Skill-doc changes conform to `writing-for-agents` and carry a pack CHANGELOG entry per `CONTRIBUTING.md`.
- **Merge rule (CLAUDE.md)**: an agent may merge a PR once checks are green and CodeRabbit is dispositioned (every finding verified and replied to on its thread, fixed or declined with a reason). The review-settled check enforces the reply: it stays red while any thread CodeRabbit opened has no non-bot reply. Branch protection additionally requires the branch up to date with `main` and all review threads resolved.

## Templates

- Issue/work-item spec: adopted in place. This repo is the pack source; the authoritative template is `skills/orient/setup/references/templates/issue-slice-spec.md` (no `.github/ISSUE_TEMPLATE` copy seeded)
- Lane brief: adopted in place, `skills/orient/setup/references/templates/lane-brief.md`

## Domain memory

- **Memory home**: `docs/agents/memory/`, a `decisions/` directory plus `terms.md`, git-tracked (in-repo by the decider's explicit choice, 2026-08-12: bindings and institutional memory live per-project, never per-profile)
- **Size bound**: 30 records; past it, sessions offer a consolidation pass, dispositioned by the decider
- **Backfill**: not requested

## Handoff

- **Handoff location**: `.claude/handoff.md`, untracked
- **Ignore entry**: already present (`.gitignore` ignores `.claude/*` except `settings.json` and `hooks/`)
- **Session-start auto-load hook**: seeded in `.claude/settings.json` (git-tracked, repo-owned, not sync-managed) on 2026-08-12

## Git guardrail

- **Git guardrail hook**: seeded 2026-10-07: `.claude/hooks/git_guardrails.py` wired as a `PreToolUse` hook (matcher `Bash`) in `.claude/settings.json`, with `!.claude/hooks/` in `.gitignore` so the script is tracked. It asks before force-push, pushing tags, creating, editing, or deleting a release, deleting a remote branch, `git reset --hard`, `git clean -f`, and `git branch -D`; ordinary pushes, commits, PRs, and merges pass silently. To remove it, delete the settings entry first, then the script.

## Adversarial review

- **Defect-class file**: none seeded: this repo's changes are skill docs, not application code; the review bar is the rule-preservation and writing-for-agents disciplines. Revisit at re-run if code-bearing skills grow.
- **Layers**: floor + orchestrator close-out. Close-out layer is mandatory (not CodeRabbit alone) for changes to pack-skill protocol files when the item's spec says so, the decider's standing word for critically important skills (e.g. orchestrate).
- **Mandatory lenses**: rule-preservation on any compaction/restructure of a skill doc (every normative rule present, none weakened, inventory-checked)
- **Live-probe policy**: no live probes
- **Substantiality rules**: any change to a pack skill's SKILL.md is substantial

## Orchestration

- **Lane launch**: default in-process Claude Agent subagent in an isolated worktree (`Agent` tool, `isolation: worktree`); background-task chip session for lanes expecting mid-flight approvals, long-lived work, or decider-watching (per orchestrate §4's shape rule). Claim posted as a `Lane-start` comment on the issue before launch, stamping runner, model/effort source, and workspace. Titling: launcher titles; subagent lanes have no picker entry; the launch report carries identity. Chip-launched sessions are pre-titled by the chip label (title protocol outranks the chip's imperative-label convention). Native auto-archive on PR close: no; the notification path per orchestrate §5 step 6.
- **Announce model/effort**: on
- **Runner inventory**: Claude (Agent tool subagents; background-task chips; `claude` CLI for detached sessions). No launcher script: launches are tool-call-native; this section is the recipe doc.
- **Runner policy**: Claude only, orchestrator's choice of vehicle (decider-set 2026-08-12). Fallbacks loud per orchestrate §4.
- **Workspace provisioning**: git worktrees under `.claude/worktrees/` (harness-provisioned per lane); no per-lane resources beyond the worktree and branch; prune both at close-out.
- **Monitoring**: inline `gh` polling (filtered, count-shaped) on a ~4-minute background-sleep metronome while lanes are live, re-armed each wake; subagent completion notifications for lane liveness.
- **Verification executor**: delegated verifier subagent in the lane's workspace for anything non-trivial; inline for one-command checks. Per-command exit codes, zero skipped checks.
- **Review-tier policy** (decider-set 2026-08-12, canonical shape):
  - Mechanical verification re-runs: Haiku (or session model) at low effort · floor: never the adversarial pass itself
  - Adversarial review (finders, skeptics, re-probes): session model at high effort on pack-skill changes · floor: no low-effort skeptics on pack-skill protocol changes
  - Max tier: decider-named cases only, never a default
- **Merge flow**: lane branch → PR → CI checks + CodeRabbit disposition per the merge rule above → squash-merge by the orchestrator → issue close-out comment → prune worktree/branch.

## Accepted drift (written by setup's audit mode)

<!-- Drift findings the decider accepted as this repo's recorded choice instead of updating
     the binding. The next audit reads this list and does not re-flag an entry here. -->

_None yet._

## Friction log (optional)

- Pack friction gets filed as `process`-labeled issues on the tracker.

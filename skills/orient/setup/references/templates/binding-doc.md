# Team workflow: repo bindings

<!-- Seeded by the team-workflow pack's setup skill. Default home: docs/agents/team-workflow.md
     (the home is confirmed at setup, never assumed). This doc is the single place the pack's
     skills read repo-specific facts from; keep it current via a setup re-run (idempotent
     refresh), not hand-drift. -->

_Pack version: <pack version installed> · Last confirmed: <date>_

## Tracker binding

- **Tracker**: <e.g. GitHub Issues on `<owner>/<repo>`, or `none yet: <why>; revisit at next setup re-run`>
- **Claim recipe**: <e.g. "the pack's tracker-discipline recipes as written", or the repo's mapping of them onto its tracker; `dormant until a tracker is bound` when the tracker is `none yet`>
- **Frontier query**: <the exact command/query that lists grabbable items>
- **Blocking**: <native dependency edges + `blocked` label, or the repo's equivalent dual-read>
- **Label vocabulary**: <`pack defaults, created at setup on <date>` | repo labels ↔ pack vocabulary: needs-triage / ready-for-agent / ready-for-human / blocked + type labels (slice / bug / gate-decision / process) | the creation instruction, for trackers setup cannot drive>
- **Implicit-repo check** (GitHub trackers): <`match` | the mismatch found, e.g. `gh here resolves to <other-repo> (fork); recipes' --repo scoping applies` | `unresolved: <why gh repo view returned nothing usable>`; never blank>

## Verify commands

<!-- The exact commands that constitute "verified" here. Briefs and templates name these
     instead of guessing. Tier them if the repo distinguishes blast radii.
     A repo with no toolchain yet records the explicit none-yet form below instead of the
     command block, never a guessed command. The setup re-run revisits it. -->

```bash
<typecheck command>
<lint command>
<test command>
<build command>
```

<!-- Or, on a brand-new repo:
- **Verify commands**: none yet (no toolchain as of <date>); revisit at next setup re-run.
-->

## The decider

- **Decider**: <name/role: who adjudicates decisions in this repo>

Every pack skill says "the decider"; this line is where the role resolves. Sessions brief decisions with recommendations and evidence; the decider answers them on the record.

## Docs home

- **Binding doc home**: <this file's confirmed location>
- **Decision maps**: <where map docs live, e.g. `docs/<scope>-decision-map.md`>
- **Research findings**: <where findings files live, e.g. `docs/research/`>
- **Domain/context docs agents should load** (optional): <paths>

## Precedence & exemptions

How the pack composes with this repo's resident rule systems. Resident rules win unless an exemption below says otherwise.

- **Prototype test-exemption**: code on `prototype/<name>` branches is exempt from the repo's test-first / coverage rules: prototype branches are throwaway by contract and never merge; the exemption ends the moment the winner's real implementation starts.
- <other resident rules and how the pack defers to or composes with them>

## Templates

- Issue/work-item spec: <adopted repo's own | seeded at `<path>` | declined>
- Lane brief: <adopted | seeded at `<path>` | declined>

## Handoff

- **Handoff location**: <where the handoff skill writes, e.g. `.claude/handoff.md`, untracked>
- **Ignore entry**: <seeded in `.gitignore` | already present | declined; the entry that keeps the handoff file untracked>
- **Session-start auto-load hook**: <seeded in `<settings file>` (created fresh if the repo had none) | pending as a snippet with the settings owner (sync-managed settings) | declined>

## Adversarial review (optional; repos running the adversarial-review skill)

<!-- The adversarial-review skill's binding slots. Omit this section if the repo has not
     bound the skill; the floor layer plus an empty defect-class file is the minimal binding. -->

- **Defect-class file**: <path: seeded from the pack template | adopted: the repo's existing review-standards doc, unchanged>
- **Layers**: <floor only | floor + orchestrator close-out>
- **Mandatory lenses**: <path patterns that pin a lens, e.g. "`payments/` always runs the money lens", or none>
- **Live-probe policy**: <where proofs may/must touch real services or seeded data, and what is off-limits, or "no live probes">
- **Substantiality rules**: <changes that are always substantial regardless of implementer judgment, or none pinned>

## Codebase review (optional; repos running the codebase-review skill)

<!-- The codebase-review skill's binding slots. Omit this section if the repo has not
     bound the skill. Rejection memory must survive across runs: reruns read it before
     proposing, so a rejected candidate reopens on new evidence, never on repetition. -->

- **Report destination**: <the tracker item each run posts its report to and closes: a standing item, or the rule that creates one per run; must be writable and closable, never a read-only query>
- **Lane-count threshold (N)**: <merged lanes since the last review that trigger a run>
- **Rejection memory**: <where rejected candidates and their load-bearing reasons live>
- **Executor mechanics**: <how the read-only review lane is launched, claimed, and tracked; in orchestrated repos, usually the lane-launch machinery below>

## Domain memory (optional; repos running the domain-memory skill)

<!-- The domain-memory skill's binding slots. Omit this section if the repo has not
     bound the skill. Where codebase-review is also bound, its rejection-memory slot
     above points at this memory home: one store, never two. -->

- **Memory home**: <where the store lives, e.g. `docs/decisions/` + `docs/terms.md`, a decisions directory plus a terms file the repo tracks>
- **Size bound**: <the store size past which sessions offer a consolidation pass, e.g. 30 records; dispositioned by the decider, never run unprompted>
- **Backfill**: <not requested | requested on <date>: the one-time lane that drafts records from closed PRs/issues/handoffs for card-by-card disposition>

## Orchestration (optional; repos running an orchestrator)

<!-- The orchestrate skill's binding slots. Omit this section if no session orchestrates. -->

- **Lane launch**: <how a working session starts; what gets stamped on the tracker item; the titling mechanism and actor (session-title tool / terminal title / …; launcher titles (default) / orchestrator retitles / self-title only where the harness supports it; or `no titling surface`, launch reports and handoffs carry identity instead); title content is protocol with per-repo refinement, see the orchestrate skill §8>; native auto-archive on PR close: <yes / no; yes only if it cannot preempt close-out order>
- **Announce model/effort**: <on (default) / off: whether launch and review hand-off announcements carry the reasoning-effort line and the hand-off repeat (the per-round repeats and the close-out cost line included) per the orchestrate skill §4–§5 (the launch report's identity list, model included, holds in every state); this recorded line is the only valid off-switch, so audit mode can check it>
- **Runner inventory**: <the runners available for lanes (e.g. Claude Code, Codex CLI, human) and the launch mechanism for each: a launcher script/recipe per the orchestrate skill's runner-parity reference, or `manual`; where a launcher recipe doc lives in-repo>
- **Runner policy**: <the decider's preference policy, e.g. "prefer Codex for implementation lanes" / "orchestrator's choice"; followed at every launch, never habit; launch failures diagnose first, and fallbacks are loud (`runner fallback: X→Y, reason` on the launch report and the tracker item), per the orchestrate skill §4>
- **Workspace provisioning**: <how a fresh per-lane workspace is created; per-lane resources that must be pruned with it>
- **Monitoring**: <how the orchestrator watches PRs / tracker activity / lane liveness between turns>
- **Verification executor**: <who re-runs a lane's verification at close-out, and how>
- **Review-tier policy** (decider-set: close-out machinery runs at these tiers, never by habit; each tier carries a floor, what it may NOT be used for, so cost-saving never silently weakens the review bar; deviation is loud in both directions per the orchestrate skill §4; canonical shape below, adapted per repo):
  - Mechanical verification re-runs: <model + effort, e.g. cheaper model, low effort (they follow a script; exit codes don't need the frontier model)> · floor: <what this tier may NOT cover, e.g. never the adversarial pass itself>
  - Adversarial review (finders, skeptics, re-probes): <model + effort: high on real code or release-arming changes> · floor: <e.g. no low-effort skeptics on release-arming diffs>
  - Max tier: <the decider-named cases that run at max; never a default>
- **Merge flow**: <integration mechanics; who may push what where>

## Accepted drift (written by setup's audit mode)

<!-- Drift findings the decider accepted as this repo's recorded choice instead of updating
     the binding. The next audit reads this list and does not re-flag an entry here.
     Repos bound to domain-memory may keep acceptances as decision records at the memory
     home instead; record the pointer here so the audit knows where to read. -->

- <date> · pack <version at acceptance> · <the drift, one line> · accepted: <the load-bearing reason>

## Friction log (optional)

- <where pack friction gets recorded, e.g. a dedicated tracker item>

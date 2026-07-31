# Team workflow — repo bindings

<!-- Seeded by the team-workflow pack's setup skill. Default home: docs/agents/team-workflow.md
     (the home is confirmed at setup, never assumed). This doc is the single place the pack's
     skills read repo-specific facts from; keep it current via a setup re-run (idempotent
     refresh), not hand-drift. -->

_Pack version: <pack version installed> · Last confirmed: <date>_

## Tracker binding

- **Tracker**: <e.g. GitHub Issues on `<owner>/<repo>`>
- **Claim recipe**: <e.g. "the pack's tracker-discipline recipes as written" — or the repo's mapping of them onto its tracker>
- **Frontier query**: <the exact command/query that lists grabbable items>
- **Blocking**: <native dependency edges + `blocked` label, or the repo's equivalent dual-read>
- **Label mapping** (optional): <repo labels ↔ pack vocabulary: needs-triage / ready-for-agent / ready-for-human / blocked + type labels>

## Verify commands

<!-- The exact commands that constitute "verified" here. Briefs and templates name these
     instead of guessing. Tier them if the repo distinguishes blast radii. -->

```bash
<typecheck command>
<lint command>
<test command>
<build command>
```

## The decider

- **Decider**: <name/role — who adjudicates decisions in this repo>

Every pack skill says "the decider"; this line is where the role resolves. Sessions brief decisions with recommendations and evidence; the decider answers them on the record.

## Docs home

- **Binding doc home**: <this file's confirmed location>
- **Decision maps**: <where map docs live, e.g. `docs/<scope>-decision-map.md`>
- **Research findings**: <where findings files live, e.g. `docs/research/`>
- **Domain/context docs agents should load** (optional): <paths>

## Precedence & exemptions

How the pack composes with this repo's resident rule systems. Resident rules win unless an exemption below says otherwise.

- **Prototype test-exemption**: code on `prototype/<name>` branches is exempt from the repo's test-first / coverage rules — prototype branches are throwaway by contract and never merge; the exemption ends the moment the winner's real implementation starts.
- <other resident rules and how the pack defers to or composes with them>

## Templates

- Issue/work-item spec: <adopted repo's own | seeded at `<path>` | declined>
- Lane brief: <adopted | seeded at `<path>` | declined>
- Handoff: <adopted | seeded at `<path>` | declined>

## Friction log (optional)

- <where pack friction gets recorded, e.g. a dedicated tracker item>

# Tracker discipline: the portable recipes

The pack's collision defenses, written GitHub-Issues-first (`gh` commands throughout). The tracker itself is a **named binding**: a repo on a different tracker maps these same recipes (machine-readable claims, dependency edges, a frontier query, issue-as-spec) onto its own tool in its binding doc; the recipes' logic is the export, not the tool.

**Every command names the bound repo.** `<owner>/<repo>` throughout these recipes is the tracker binding's repo, carried explicitly: `--repo <owner>/<repo>` on every `gh issue`/`gh label` command, the literal repo in every `gh api` path. Unqualified `gh` resolves the repo implicitly from the working directory's remotes: in a fork that is typically the **upstream** repo, not the bound tracker, so tracker-state reads go quietly wrong and writes land in a repo that never bound the pack. `gh api`'s `{owner}/{repo}` placeholders resolve the same implicit way; they are not scoping. Nor is `gh repo set-default`: it is per-clone state the next worktree or machine doesn't have. Command-level scoping is the defense.

The core discipline: **one session per work item, and the claim is legible to machines.** Two agents (or an agent and a human) silently building the same item is the failure class every recipe below exists to prevent: an assignee field alone cannot distinguish two sessions sharing one account, so claims are carried in comment markers a scanner can read.

## Issue-as-spec

The work item's body IS the spec: destination, acceptance criteria, out-of-scope, written once, on the tracker, before any code. The implementing brief adds standing constraints and mechanics, never a second copy of the requirements; the implementing PR carries `Closes #N`; the work summary posts back to the item as a comment, making the tracker the durable record. Discovered-but-unplanned work gets filed as a new item, not smuggled into the current one.

## Claim recipe (read-before-write)

Claiming is a read-modify-write with the read mandatory:

1. **Read the item's comments first.** A claim is LIVE when the latest comment matching
   `Lane-start: workspace=<name> branch=<branch>`
   has no later `Lane-start-retracted: workspace=<same-name>` marker after it (a later `Lane-start` supersedes an earlier one; takeover chains post a new one).
2. **A live claim refuses your claim.** No external pointer ever overrides a live Lane-start: not a handoff note, a stale to-do list, or a plan doc. Those pointers go stale the moment anyone else claims; the tracker comment is the truth.
3. **On clear: claim atomically.** Set yourself assignee AND post the marker in one pass:

   ```bash
   gh issue edit <N> --repo <owner>/<repo> --add-assignee "@me"
   gh issue comment <N> --repo <owner>/<repo> --body "Lane-start: workspace=<name> branch=<branch>"
   ```

   `<name>` is a machine-matchable token identifying your working copy (worktree, clone, or machine+dir); the retraction scanner matches on it literally, so pick something unique and reuse it exactly.
4. **Releasing your OWN claim** posts the machine-recognized marker and unassigns:

   ```bash
   gh issue comment <N> --repo <owner>/<repo> --body "Lane-start-retracted: workspace=<name>"
   gh issue edit <N> --repo <owner>/<repo> --remove-assignee "@me"
   ```

   Prose retractions ("I'm dropping this one") are invisible to a scanner unless they contain the literal workspace token; always post the marker.
5. **Taking over a DEAD lane** requires recorded evidence of death, and death is hard to prove: an agent session can be alive but between turns, invisible to every process probe, so "no processes running + no commits" is NOT death evidence. Before a takeover: read the item's recent comments for liveness (progress notes, a summary in flight), check for active sessions on the machines involved, and wait out quiet phases. Only then post a superseding claim that records the takeover:

   ```bash
   gh issue comment <N> --repo <owner>/<repo> --body "Lane-start: workspace=<name> branch=<branch> (takeover: <evidence the prior lane is dead>; prior workspace=<old-name>)"
   ```
6. **Suspect claims**: an assignee with no live Lane-start comment is a suspect claim; check for running sessions before treating the item as free.

Also on the claimer, before any of the above: check for other active sessions already working the same surface: a running session beats an unclaimed item. After claiming, make the session/workspace carry the item number (a fresh, item-named working copy; a recycled name makes session lists lie to the next reader).

## Frontier recipe (dual-read)

The frontier is the set of grabbable items: ready-labeled, unassigned, and **not blocked, read blocking two ways**: native dependency edges OR a `blocked` label. A query that checks only the label misses edge-blocked items; one that checks only edges misses non-ticket blockers.

```bash
# One JSON object per open issue, with the dependency summary the plain issue list omits.
# <owner>/<repo> is the bound tracker repo, written literally — {owner}/{repo} would
# resolve implicitly and mis-target in forks:
gh api 'repos/<owner>/<repo>/issues?state=open&per_page=100' --paginate --jq '.[]
  | select(has("pull_request") | not)
  | {number, title,
     labels: [.labels[].name],
     assignees: [.assignees[].login],
     blockedBy: (.issue_dependencies_summary.blocked_by // 0)}'
```

Grabbable = has the ready label (per your label binding) AND `assignees == []` AND `blockedBy == 0` AND no `blocked` label. When the frontier is empty, report WHY (all claimed vs. triage stalled vs. everything blocked); an empty answer with no breakdown sends people guessing.

## Blocking edges

Wire blocked-on-a-ticket work as a **native dependency edge** so the frontier un-blocks itself the moment the blocker closes:

```bash
# -F issue_id takes the blocker's DATABASE id — not its #number, not its node_id:
gh api repos/<owner>/<repo>/issues/<blocker-number> --jq .id
gh api repos/<owner>/<repo>/issues/<child-number>/dependencies/blocked_by -F issue_id=<that-id>
```

Division of labor: **edges are authoritative wherever the blocker is a tracker item** (no label flip needed when it closes); the **`blocked` label** is the human-readable mirror and the only expressible form for non-ticket blockers (vendor gates, scheduling, pending adjudications). A purely edge-backed item does NOT also carry the label: a stale label would hold it blocked after its edges clear. The label rides while any non-ticket blocker remains and comes off only when all such blockers resolve. An item with both kinds carries both markers: closing its ticket dependency does not clear the non-ticket label, and removing that label does not clear an unfinished dependency.

## State and type labels (the vocabulary binding maps these)

The pack's reference vocabulary follows; map your repo's existing labels onto it in the binding doc rather than renaming your labels: state = `needs-triage` (all inbound; verify/reproduce before promoting) → `ready-for-agent` / `ready-for-human`, plus `blocked`; type labels tag the kind of work (build slice, bug, decision, process) and can drive per-type verification tiers if the repo wants them.

These labels must actually exist on the tracker before any recipe above can match them: a frontier query against labels nobody created returns empty forever, and nothing downstream creates them as a side effect. On a fresh tracker the setup interview creates the vocabulary (or records the creation instruction) as part of the tracker binding; if your frontier is inexplicably empty on a new repo, check the labels exist before debugging the query.

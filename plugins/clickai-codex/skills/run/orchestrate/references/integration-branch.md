# Integration branch: landing a spec whole

For a spec the decider wants landed whole, its lanes merge into one **integration branch** instead of the default branch, and the default branch gets a single PR at the end, reviewed as a whole. It is opt-in per spec, on the decider's word, and never the default: a spec with no recorded integration branch lands lane by lane.

## What the binding records

The merge-flow binding slot ([SKILL.md](../SKILL.md) §7) records each opted-in spec before the spec's first lane launches, naming:

- the spec and the branch name;
- who creates the branch;
- who may merge into it;
- when the final PR to the default branch opens.

## While its lanes run

- Each lane branches off the integration branch, and the integration branch is the merge target it catches up with before handing back (§4).
- Each lane still closes out per §5, merged into the integration branch.
- A lane PR into the integration branch does not close its item: GitHub honors `Closes #N` only on PRs into the default branch. The orchestrator closes the item at that lane's close-out, with a comment naming the integration branch and the merge commit, so dependent items reach the frontier.

## The final PR

1. Before the final PR opens, the integration branch catches up with the default branch by the same rule as a lane (§4): updated from the default branch, any conflict resolved, verification re-run, and the default-branch commit it caught up to named in the PR.
2. The final PR gets the whole-spec close-out review: §5 again, scoped to the whole spec.
3. The final PR to the default branch lists the spec's items for the record.

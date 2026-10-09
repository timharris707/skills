# Integration branch: landing a spec whole

For a spec the decider wants landed whole, its lanes merge into one **integration branch** instead of the default branch, and the default branch gets a single PR at the end, reviewed as a whole. It is opt-in per spec, on the decider's word, and never the default: a spec with no recorded integration branch lands lane by lane.

The spec's items are the items the spec records, for example its sub-issues. Any other item is outside the spec, even one that depends on a spec item.

## What the binding records

The merge-flow binding slot ([SKILL.md](../SKILL.md) §7) records each opted-in spec before the spec's first lane launches, naming:

- the spec and the branch name;
- who creates the branch;
- who may merge into it;
- when the final PR to the default branch opens.

## While its lanes run

- Each lane branches off the integration branch, and the integration branch is the merge target it catches up with before handing back (§4).
- Each lane still closes out per §5, merged into the integration branch.
- A lane PR into the integration branch does not close its item: GitHub honors `Closes #N` only on PRs into the default branch. The orchestrator closes the item at that lane's close-out, with a comment naming the integration branch and the merge commit, so dependent items inside the spec reach the frontier.
- A dependent outside the spec stays blocked until the final PR merges: it would branch off the default branch, which lacks the item's code until then. Before closing the item, find its open dependents (the items whose native blocked-by edges point at it) that are outside the spec, and give each the `blocked` label with a comment naming the integration branch and saying the item waits for the spec's final PR to reach the default branch. This is a non-ticket blocker in [tracker discipline's](../../../orient/setup/references/tracker-discipline.md) terms. A dependent in another repo is out of the bound tracker's reach: name it in the closing comment instead of labeling it.

  ```bash
  # Open items that <N> blocks; <owner>/<repo> is the bound tracker repo, written literally:
  gh api 'repos/<owner>/<repo>/issues/<N>/dependencies/blocking?per_page=100' --jq '.[] | select(.state == "open" and .repository_url == "https://api.github.com/repos/<owner>/<repo>") | .number'
  gh issue edit <dependent> --repo <owner>/<repo> --add-label blocked
  gh issue comment <dependent> --repo <owner>/<repo> --body "Blocked until <spec>'s final PR reaches <default-branch>: #<N> is merged into <integration-branch> only."
  ```

## The final PR

1. Before the final PR opens, the integration branch catches up with the default branch by the same rule as a lane (§4): updated from the default branch, any conflict resolved, verification re-run, and the default-branch commit it caught up to named in the PR.
2. The final PR gets the whole-spec close-out review: §5 again, scoped to the whole spec.
3. The final PR to the default branch lists the spec's items for the record.
4. At the final PR's close-out, after it merges into the default branch, rerun the lookup on each spec item. Take the `blocked` label off each open dependent outside the spec, unless another non-ticket blocker still applies, and comment on each that the code is on the default branch.

   ```bash
   gh issue edit <dependent> --repo <owner>/<repo> --remove-label blocked
   gh issue comment <dependent> --repo <owner>/<repo> --body "Unblocked: <spec>'s final PR is merged into <default-branch>."
   ```

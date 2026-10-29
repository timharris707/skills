---
name: review-loop
description: "Have a second model review a branch on this machine before its pull request opens, fix what holds up, and repeat until a round comes back clean or three rounds pass. Use when about to open a pull request or push a fix to one, when the user says review loop or asks for a second opinion before the PR, or when a repo's instructions name the review loop."
---

# Review loop

A pull request should reach the review bot already clean. The bot then reviews once, and the PR merges on that one pass instead of collecting a fix push per finding. The review loop is that cleaning: a **second model** reads the branch's diff in a fresh context, the author fixes what holds up, and the loop repeats, at most three rounds.

The reviewer is Codex through `codex review`, on the Codex subscription the machine already signs in with. It costs one Codex review per round and no API spend. A repo whose instructions name a different reviewer, or a heavier pre-PR review such as [adversarial-review](../../run/adversarial-review/SKILL.md), keeps its own; the loop is the light pass for every other PR.

## Steps

1. **Ready the branch.** Commit the work and run the checks the repo requires before a PR. Fetch the base branch the PR will target. Done when the working tree is clean and `git log origin/<base>..HEAD` lists exactly the work for this PR.

2. **Run a round.** One review of the whole branch against its base. `codex review` refuses `--base` together with instructions, so the base goes inside the instructions:

   ```bash
   # Set run once, at the loop's first round, so a later loop keeps this one's records.
   run="$(git rev-parse --git-dir)/review-loop/$(git branch --show-current | tr / -)-$(date +%Y%m%d-%H%M%S)"
   out="$run/round-<n>.md"
   mkdir -p "$run"
   codex review "Review the changes on this branch against origin/<base> (git diff origin/<base>...HEAD). <goal of the driving item, one sentence>. Report only defects: wrong behavior, missing or broken tests for changed behavior, security problems, and breaks of this repo's written rules. Skip style." > "$out" 2>&1
   ```

   A round takes from under a minute to several. Run it with your command tool's timeout set to 15 minutes (macOS has no `timeout` command). A nonzero exit is a failed round, not a review: read the error at the end of the file, fix the cause, and rerun the round. A `401 Unauthorized` means Codex ran without a sign-in; set `CODEX_HOME` to the profile the machine's Codex agents use. On a zero exit, the findings are the block after the last line that reads `codex`; everything above it is the session log. Done when the command exited 0 and that block holds findings or says it found none.

3. **Settle every finding.** For each one, read the code it points at and decide:
   - **Fix** it when it is real and inside the driving item's goal, with the smallest change that answers it.
   - **Decline** it, with a one-line reason, when it is wrong or asks for work beyond the item. Scope creep is a decline even when the idea is good; file real outside work as its own tracked item.

   Append each finding's disposition (fixed, or declined and why) to the end of the round's file, then commit the fixes and rerun the repo's checks. Done when every finding in the round has its disposition in the round file.

4. **Repeat or stop.** Stop on whichever comes first:
   - **Clean:** the round reports no findings.
   - **Settled:** you declined every finding in the round. Rerunning would return the same ones.
   - **Round 3 done:** findings you fixed in it stay unreviewed and go into the PR as such, and any still open are named there.

   Otherwise run the next round on the updated branch. Done when the loop has stopped on one of those three conditions.

5. **Record it in the PR.** The PR description carries one line the reviewer and the decider can read at a glance:

   ```markdown
   **Review loop:** 2 rounds (Codex). Fixed 3, declined 1 (out of scope: <reason>). Final round clean.
   ```

   A settled stop says "final round settled (all declined)", never clean. On a stop after round 3, name each finding still open. A fix pushed to an open PR runs the loop again on the new commits before the push, and updates this line.

## Done when (checkable: verify each line before reporting complete)

- Every round reviewed the diff against the PR's actual base branch, and its file under the git dir ends in findings or a clean verdict, never an error.
- Every finding has its disposition and reason in its round file; no finding was skipped.
- The loop stopped clean, settled, or after round 3, never earlier with fixed findings unreviewed.
- The repo's required checks pass on the final commit.
- The PR description carries the review-loop line, and any finding left open is named there.

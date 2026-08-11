# How agent-filed PRs read

A PR is read by the decider and by reviewers long before anyone reads it in git history — and in a repo run through this pack, the decider may be a non-engineer whose merge decision rests entirely on the description. Every rule here exists because its violation shipped; the examples are real agent-filed PRs from consuming repos, identifiers removed and content lightly paraphrased.

## Before filing

- Check whether a PR for this branch already exists — update it rather than filing a twin.
- Review the actual diff against the default branch before writing anything: the description describes what the diff does, not what the lane meant to do, and a diff that doesn't match the driving item's goal is a finding to report, not to describe around.
- File a real PR, not a draft — review bots skip drafts, and the pack's review discipline depends on them running. A repo whose recorded policy wants drafts overrides this.

## Title

The title says **why the change matters**, in plain language — and since squash-merge makes it the commit subject, it follows the repo's title conventions (read a few recently merged PRs first).

- Bad (real): *"Refactor task detail run summaries"* — pure mechanism; says what was touched, not what was wrong or why anyone should care.
- Good (real): *"Defuse seeded demo-account password time bomb"* — names the problem and the stakes in one line.

## Description

**Open with a plain-language statement of the problem, drawn from the driving item or the user's original words. Then the solution in a sentence or two.** Implementation detail comes after that, if at all — never first.

The anti-pattern is the **implementation inventory**: a bullet list of internal changes with no stated problem. It reads as thorough and communicates nothing.

- Bad (real): *"— extract duplicated latest-run and active-run mapping into a typed shared helper — keep the response shape and query behavior unchanged — update the hygiene roadmap…"* No reader can say what the point of this PR was.
- Good (real): *"The status icons next to the provider column headers did nothing on hover, and nothing said they were clickable. Hovering now shows the same health-detail popover that clicking does; click behavior is unchanged."* The problem in the user's own terms, then the fix.

Close the description with a **provenance blurb** naming the model and harness that did the work (*"Filed by \<model\> via \<harness\>"*) — read from a recorded source, never guessed, per the pack's announce discipline. `Closes #N` links the driving item; issue bookkeeping never substitutes for the problem statement.

## Responding to review feedback

Where the repo has a resident review-response system (a disposition rule, a review wiki), that system is the authority and its precedent store stays the only one — these are the floor beneath it:

- **Never let review feedback expand the PR beyond the driving item's goal.** Address real shortcomings; everything else is filed as a new tracked item — tracker discipline's "discovered work gets its own item" applied to review comments.
- Act only on checks and comments **newer than the latest push** — everything older is already answered by the code.
- Verify every bot finding against the source before changing code. A false positive gets a reply with a written reason, then the thread resolved — never a silent dismissal, never an unverified fix.
- A comment an agent writes on a human's behalf says so: *"\<model\> responding on behalf of \<name\>: …"* — nobody should mistake an agent's reply for the human's.

## Attribution

The problem-first description rule, the implementation-inventory anti-pattern, the no-drafts default, the provenance blurb, the scope-creep guard, and the newer-than-latest-push rule follow Theo Browne's file-PR and babysit-PR skill lessons (described in his video work; the skills themselves are unpublished). The examples, the tracker-discipline composition, and the resident-review-response deference are this pack's.

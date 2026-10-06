# How agent-filed PRs read

A PR is read by the decider and by reviewers long before anyone reads it in git history; and in a repo run through this pack, the decider may be a non-engineer whose merge decision rests entirely on the description. Most rules here exist because their violation shipped; the rest come from reviewed prior art named in Attribution. The examples are real agent-filed PRs from consuming repos, identifiers removed and content lightly paraphrased.

## Before filing

- Check whether a PR for this branch already exists; update it rather than filing a twin.
- Review the actual diff against the PR's base branch before writing anything: the description describes what the diff does, not what the lane meant to do, and a diff that doesn't match the driving item's goal is a finding to report, not to describe around.
- File a real PR, not a draft: review bots skip drafts, and the pack's review discipline depends on them running. A repo whose recorded policy wants drafts overrides this.

## Title

The title says **why the change matters**, in plain language, and since squash-merge makes it the commit subject, it follows the repo's title conventions (read a few recently merged PRs first).

- Bad (real): *"Refactor task detail run summaries"*: pure mechanism; says what was touched, not what was wrong or why anyone should care.
- Good (real): *"Defuse seeded demo-account password time bomb"*: names the problem and the stakes in one line.

## Description

A description runs in this order: the problem, the solution, the evidence, the can-we-undo call, then any optional detail. The provenance blurb closes it.

### Problem, then solution

**Open with a plain-language statement of the problem, drawn from the driving item or the user's original words. Then the solution in a sentence or two.** Implementation detail comes after that, if at all, never first.

The anti-pattern is the **implementation inventory**: a bullet list of internal changes with no stated problem. It reads as thorough and communicates nothing.

- Bad (real): *"— extract duplicated latest-run and active-run mapping into a typed shared helper — keep the response shape and query behavior unchanged — update the hygiene roadmap…"* No reader can say what the point of this PR was.
- Good (real): *"The status icons next to the provider column headers did nothing on hover, and nothing said they were clickable. Hovering now shows the same health-detail popover that clicking does; click behavior is unchanged."* The problem in the user's own terms, then the fix.

### Evidence: before and after

**Every change carries evidence that it works, shown before and after.** Evidence is something that ran (a test, a command, the running app), never "the code reads right".

- **A user-visible change carries visual evidence**: a screenshot, or a short recording for interaction, of the before and the after. Reviewers and a non-engineer decider judge what they can see, and one image outweighs a paragraph of description.
- **Every other change** carries the exact test or command and its output, before the change and after it: a test that failed and now passes, or output that changed the way the problem statement says it should. A change meant to alter no behavior, such as a refactor, shows the same tests passing on both sides.

Where the environment provides an upload capability (a file-host skill, a recorded binding), use it and embed the link; externally hosted video does not inline-play on GitHub, so link it plainly, optionally under a small GIF preview. **Review every frame before uploading**: hosted evidence is public to anyone holding the link, so no credentials, tokens, or customer data on screen: re-capture with safe data rather than annotating around a leak, and where the surface cannot be captured safely, fall back to the no-capability path. No capability, no invention: note "demo available on request" instead of improvising hosting. Pasted command output gets the same review before it goes in the description.

### Can we undo this?

**Every description says whether a revert fully undoes the change, and how much could break**, as two short lines in plain words:

```markdown
**Can we undo this?** Yes, a revert fully undoes it. | No: <what a revert leaves done>.
**What could break:** <small | medium | large>. <One sentence naming what.>
```

- **Can we undo this?** Yes when the change lives only in the code, so reverting the PR puts everything back: a **two-way door**, one you can walk back through. No when merging or deploying does something a revert leaves done: it deletes or migrates data, sends messages, publishes something, spends money, or changes a third party. That is a **one-way door**, and the line names which of those it does.
- **What could break:** one word for how much, then one sentence naming what. When the answer is medium or large, run the [blast-radius](../../blast-radius/SKILL.md) skill where it is installed, and write that sentence from what it finds.

### Optional detail

Optional detail follows the undo call and is written for reviewers: a diagram, and any implementation detail a reviewer needs.

**A diagram for reviewers.** When a developer reviewing the PR would see the change faster in a picture, add the smallest view that makes it clear: pseudocode for logic, a call tree for runtime flow, a file tree for a layout change or a broad refactor, a Mermaid diagram for how parts interact or where data flows, or a diff sketch for what changes in a shape that already exists. It sits here, after the plain-language problem and solution, and never stands in for them. Keep only the calls, files, and states the point needs; one view is usually enough. Leave it out when the prose already makes the change clear.

### Closing lines

Close the description with a **provenance blurb** naming the model and harness that did the work (*"Filed by \<model\> via \<harness\>"*), read from a recorded source, never guessed, per the pack's announce discipline. `Closes #N` links the driving item; issue bookkeeping never substitutes for the problem statement.

## Responding to review feedback

Where the repo has a resident review-response system (a disposition rule, a review wiki), that system is the authority and its precedent store stays the only one; these are the floor beneath it:

- **Never let review feedback expand the PR beyond the driving item's goal.** Address real shortcomings; everything else is filed as a new tracked item: tracker discipline's "discovered work gets its own item" applied to review comments.
- Read every unresolved finding regardless of its age and verify its disposition against current code. Use CI results for the current commit. A push does not automatically answer an older comment.
- Verify every bot finding against the source before changing code. A false positive gets a reply with a written reason, then the thread resolved, never a silent dismissal, never an unverified fix.
- A comment an agent writes on a human's behalf says so: *"\<model\> responding on behalf of \<name\>:"*; nobody should mistake an agent's reply for the human's. The attribution line stands alone on its own line, a blank line follows, and the body starts as its own paragraph: the reader sees who is speaking before anything else. Paragraphs run roughly 2–3 sentences: the decider reads these on a phone, and a wall of prose hides the verdict. Lists do the enumerating, and long comma-chains split. Both rules hold for any tracker-visible comment written on a human's behalf (PR comments, review-thread replies, issue close-outs), not just PR bodies.

## Attribution

The problem-first description rule, the implementation-inventory anti-pattern, the no-drafts default, the provenance blurb, the scope-creep guard, and the newer-than-latest-push rule follow Theo Browne's file-PR and babysit-PR skill lessons (described in his video work; the skills themselves are unpublished). The before-and-after evidence rule, the can-we-undo call with its two-way and one-way doors, the rating of how much could break, and the optional reviewer diagram follow Matt Pocock's [`pr`](https://github.com/mattpocock/skills/tree/main/skills/engineering/pr) skill (MIT). The diagram menu (pseudocode, call tree, file tree, Mermaid, diff sketch) reached `pr` from Dex Horthy's [`show-me`](https://github.com/humanlayer/skills/blob/main/plugins/show-me/skills/show-me/SKILL.md), which `pr` credits. What changed here: evidence must be something that ran (a screenshot or recording for a user-visible change, the exact command and output for anything else), never a reading of the code; the undo call and the rating are plain yes-or-no and small, medium, or large lines a non-engineer decider can act on, the blast-radius pointer is new, and the diagram moved from the top of the PR to optional detail after the plain-language problem and solution. The examples, the tracker-discipline composition, and the resident-review-response deference are this pack's.

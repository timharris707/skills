---
name: to-tickets
description: Turn a plan, a spec, a closed decision map, or a pressure-tested conversation into tracer-bullet work items on the repo's tracker, each an issue-as-spec with its blocking edges wired. Use when asked to file tickets, break work down, or move from "we've decided" to "it's on the board".
---

# To Tickets

The pack's bridge from **decided** to **takeable**. [decision-map](../../decide/decision-map/SKILL.md) produces decisions; [orchestrate](../orchestrate/SKILL.md) routes tracked items into lanes. This skill is what stands between them: it turns settled intent into work items a lane can claim without asking anyone what was meant.

Read the team-workflow binding doc first — it names the tracker, the label vocabulary, the verify commands, and the decider. The [tracker discipline](../../orient/setup/references/tracker-discipline.md) governs everything filed here.

## Tracer bullets

Slice by **tracer bullet**: a thin path that goes all the way through, end to end, rather than a horizontal layer that goes nowhere alone. "Wire the read path from route to store, one field" is a tracer bullet. "Build the data layer" is a layer — it cannot be verified, cannot be demoed, and its acceptance criteria are always someone else's.

Three tests, all of which must pass:

1. **Verifiable alone.** The item names how you would know it worked, using the repo's verify commands.
2. **PR-sized.** One session, one branch, one review. An item nobody can finish in a sitting is a plan wearing a ticket's clothes.
3. **Ordered by what it unblocks**, not by architectural tidiness. The first bullet should retire the most risk.

## The two passes

Items need ids before they can reference each other, so filing is always two passes. Doing it in one produces edges pointing at numbers that do not exist yet.

**Pass 1 — file the bodies.** Each item's body IS the spec, per the [work-item spec template](../../orient/setup/references/templates/issue-slice-spec.md) that setup seeds: destination, plan source, acceptance criteria, verification, out of scope. The **plan source** line is not optional — it links the primary source (the decision-map entry, the grilling verdict, the research findings) so review never relitigates a settled question.

**Pass 2 — wire the edges.** Add native dependency edges for every blocker that is itself a tracker item, using the recipe's database-id form:

```bash
gh api repos/{owner}/{repo}/issues/<blocker-number> --jq .id
gh api repos/{owner}/{repo}/issues/<child-number>/dependencies/blocked_by -F issue_id=<that-id>
```

Edges are authoritative wherever the blocker is a tracker item, so the frontier unblocks itself when the blocker closes. The `blocked` label is only for **non-ticket** blockers — a vendor gate, a scheduling constraint, a pending adjudication. An item blocked purely by edges must not also carry the label, or a stale label holds it blocked after its edges clear.

## Labels and readiness

Apply the state and type labels the binding doc maps. An item is labeled ready **only when its body could be handed to a stranger** — every acceptance criterion checkable, every dependency wired, no "we'll figure this out in the ticket". Anything short of that is `needs-triage`, and saying so is more useful than a ready label that lies.

Confirm the labels exist on the tracker before filing. A frontier query against labels nobody created returns empty forever, and nothing downstream creates them as a side effect.

## What this skill does not do

- **It does not claim.** Filing an item and starting it are separate acts by separate sessions. Run the claim recipe when work begins; a filer who claims their own batch has locked the board against every other lane.
- **It does not decide.** Anything genuinely open when you reach it goes back to the decider as a question, or becomes a [decision-map](../../decide/decision-map/SKILL.md) ticket if the open questions gate each other. Filing a build slice over an undecided question buries the decision where nobody will see it until a lane hits it.
- **It does not spec what nobody pressure-tested.** If the source is a conversation rather than a recorded decision, run [grilling](../../decide/grilling/SKILL.md) first. A ticket set derived from unexamined agreement inherits every silent assumption and multiplies it by the number of items.

## Done when (checkable — verify each line before reporting complete)

- Every filed item passes all three tracer-bullet tests: verifiable alone, PR-sized, ordered by what it unblocks.
- Every item body carries destination, plan source link, checkable acceptance criteria, named verification, and out-of-scope.
- Pass 2 ran: every ticket-blocker is a native edge, every non-ticket blocker is the `blocked` label, and no item carries both.
- Every item is labeled, and every ready-labeled item could be handed to a stranger as-is.
- The frontier query returns the items you expect to be takeable now — run it and read the result rather than assuming.
- Nothing filed is claimed, and every question that surfaced while slicing is recorded for the decider rather than resolved by you.

---
name: implement
description: How a working lane builds an item: seam-scoped test-first, tracer-first sequencing, a green checkpoint per slice, and file-don't-fix scope discipline. Use when a build-shaped lane brief points here, when implementing a spec or tracked item, or when mid-build discoveries tempt a lane beyond its brief.
---

# Implement

How a working lane builds an item. The item's body is the spec, the brief's verification set defines done, and this skill is the discipline between those two points, not a lane type of its own, and deliberately without binding slots: everything repo-specific (verify commands, constraints, the tracker) already arrived in the lane's brief.

## Tracer first

**The first commit proves the thinnest end-to-end slice**: the path that goes all the way through, one field wide, before anything widens. Widening follows, slice by slice, each responding to what the last one taught. This pairs with [to-tickets](../to-tickets/SKILL.md)' slicing: tickets sliced tracer-style are built tracer-style. An item with no thin end-to-end slice in it is a slicing problem: report it back through the orchestrator rather than building horizontal layers and calling the stack a tracer.

## Seam-scoped test-first

A **seam** is a public boundary where behavior is observed without reaching inside, and the seams under test are the ones **the item's verification set names**, agreed upstream when the ticket was filed, not invented mid-lane. Two bars, by whether a seam is named:

- **At every named seam: red before code.** The failing test is written first, watched failing, and stays in the suite after it goes green. One seam, one test, one minimal implementation per cycle.
- **Code at no named seam ships WITH its tests, in the same commit**: tests still travel with the code, just not necessarily before it.

Tests verify behavior through the seam, never internal structure: a test that breaks under refactor while behavior held was testing the wrong thing.

## Green checkpoints

**Each slice commits when green**: the verification relevant to the seams touched so far passing at the moment of commit. The point is survival: orchestrate's relaunch-fresh rule assumes a stopped or dead lane's completed work sits at a known-good point in the lane's workspace, and the checkpoint cadence is what makes that true. A green slice left uncommitted while the next one starts is work the next interruption deletes.

## File, don't fix

Building surfaces adjacent work: a bug next door, dead code, a stale doc, a refactor begging to happen. **All of it goes to the tracker**, a comment on the driving ticket or a suggested new ticket for disposition, and the lane's diff stays inside its brief. The lane never silently expands its own scope; the tracker entry is how the discovery survives without the brief growing.

## What the close-out audit checks

Enforcement is **artifacts, not forensics**: the orchestrator's close-out audit checks three things the finished lane either shows or does not:

1. **Tests exist and pass at every seam the verification set names.**
2. **The tracer slice is identifiable**: the first commit demonstrably proves a thin end-to-end path.
3. **The diff contains no out-of-scope files.**

No commit-by-commit reconstruction of red-before-green: the kept tests, the visible tracer, and the clean diff are the evidence.

## Interlocks

Four situations route out of this skill, each to a named place:

1. **A bug surfaces mid-build** → [diagnose](../diagnose/SKILL.md). The named-cause test binds before the lane resumes building: no fix ships without a cause stated in one plain sentence, with evidence.
2. **The structure fights the lane**: a change that should have been local sprawls, a test only writable past an interface → fix nothing structural; report it as **friction** in the close-out summary, [codebase-review](../../investigate/codebase-review/SKILL.md)'s third entry gate.
3. **The spec is ambiguous** → back through the orchestrator to the decider, and build waits on the answer for anything the ambiguity gates. A lane that resolves ambiguity silently has made a decision that was never its to make.
4. **A step only a human can take** → generate a [wizard](../wizard/SKILL.md) and put the `blocked` label on the driving item until the human clears it.

## Done when (checkable: verify each line before reporting complete)

- The first commit proves the thinnest end-to-end slice, and every later commit widens it; no commit stacks a horizontal layer that goes nowhere alone.
- Every seam the item's verification set names has a test that was written red before its code, passes now, and stays in the suite; all other code shipped with its tests in the same commit.
- Every slice sits at a green checkpoint commit, and nothing green is uncommitted.
- The diff contains only in-scope files, and every adjacent discovery is on the tracker rather than in the diff.
- Every mid-build bug carries diagnose's closing artifacts; structural friction is reported in the close-out summary; every spec ambiguity went to the decider through the orchestrator; every human-only step rides a wizard with the `blocked` label on the driving item, or none of these arose.
- The close-out summary points at the three audit artifacts: the seam tests, the tracer commit, and the diff's scope.

## Attribution

Adapted from Matt Pocock's [`implement`](https://github.com/mattpocock/skills/tree/main/skills/engineering/implement) and [`tdd`](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd) (MIT). The implement-session shape is his: a session that builds from the spec or tickets, tests as it goes, and ends in review. So is the red–green loop by vertical slice: red before green, one seam, one test, one minimal implementation per cycle, each test a tracer bullet responding to what the last cycle taught (his terms), testing only at pre-agreed seams rather than everywhere, and behavior-through-public-interfaces as what a good test is.

What this pack changes: the seam agreement moves upstream (the item's verification set names the seams at filing time, instead of a mid-session ask) and the seam-scoped bar lets code at no named seam ship with its tests in the same commit; the tracer-first mandate on the first commit; the green-checkpoint cadence orchestrate's relaunch-fresh rule leans on; the file-don't-fix scope rule; enforcement by close-out artifacts rather than commit forensics; and the four named interlocks into diagnose, codebase-review, the decider, and wizard.

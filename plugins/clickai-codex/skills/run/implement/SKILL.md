---
name: implement
description: "For a build brief, implementing a spec or tracked item, or mid-build discoveries tempting scope expansion, build thin verified slices with test-first checks at named boundaries, proportional validation elsewhere, and respect for scope and commit instructions."
---

# Implement

Read the [Codex desktop binding](../../../CODEX.md) when this workflow needs harness mechanics, model routing, or recovery.

How a working lane builds an item. The item's body is the spec, the brief's verification set defines done, and this skill is the discipline between those two points. It is not a lane type of its own, and it deliberately has no binding slots: everything repo-specific (verify commands, constraints, the tracker) already arrived in the lane's brief.

## Tracer first

**The first verified checkpoint proves the thinnest end-to-end slice**: the path that goes all the way through, one field wide, before anything widens. Widening follows, slice by slice, each responding to what the last one taught. This pairs with [to-tickets](../to-tickets/SKILL.md)' slicing: tickets sliced tracer-style are built tracer-style. An item with no thin end-to-end slice in it is a slicing problem: report it back through the orchestrator rather than building horizontal layers and calling the stack a tracer.

## Seam-scoped test-first

A **seam** is a public boundary where behavior is observed without reaching inside, and the seams under test are the ones **the item's verification set names**, agreed upstream when the ticket was filed, not invented mid-lane. Two bars, by whether a seam is named:

- **At every named seam: red before code.** The failing test is written first, watched failing, and stays in the suite after it goes green. One seam, one test, one minimal implementation per cycle.
- **Outside named seams, validate the actual risk.** Use relevant existing checks for small reversible edits. Add behavioral tests when they establish new behavior or catch a reported regression; do not write tests that merely mirror implementation.

Proportional validation never waives required project tests or a regression check
for a reported bug. Required tests accompany the delivered change and pass for its
current revision, whether committed or left as a diff under a no-commit instruction.

Tests verify behavior through the seam, never internal structure: a test that breaks under refactor while behavior held was testing the wrong thing.

## Green checkpoints

**Save green checkpoints within the user's commit instructions.** Commit coherent slices when commits are authorized. A no-commit instruction instead preserves the working diff and its verification in the checkpoint. An interrupted Codex turn does not erase uncommitted files; inspect the workspace before recovery.

## File, don't fix

Building surfaces adjacent work: a bug next door, dead code, a stale doc, a refactor begging to happen. **All of it goes to the tracker**, a comment on the driving ticket or a suggested new ticket for disposition, and the lane's diff stays inside its brief. The lane never silently expands its own scope; the tracker entry is how the discovery survives without the brief growing.

## What the close-out audit checks

Enforcement is **artifacts, not forensics**: the orchestrator's close-out audit checks three things the finished lane either shows or does not:

1. **Tests exist and pass at every seam the verification set names.**
2. **The tracer slice is identifiable**: the first verified checkpoint demonstrably proves a thin end-to-end path.
3. **The diff contains no out-of-scope files.**

No commit-by-commit reconstruction of red-before-green: the kept tests, the visible tracer, and the clean diff are the evidence.

## Interlocks

Four situations route out of this skill, each to a named place:

1. **A bug surfaces mid-build** → [diagnose](../diagnose/SKILL.md). The named-cause test binds before the lane resumes building: no fix ships without a cause stated in one plain sentence, with evidence.
2. **The structure fights the lane**: a change that should have been local sprawls, a test only writable past an interface → fix nothing structural; report it as **friction** in the close-out summary, [codebase-review](../../investigate/codebase-review/SKILL.md)'s third entry gate.
3. **The spec has a material unresolved decision** → ask the decider through the coordinator and pause only dependent work. Resolve routine implementation choices from evidence and recorded decisions; do not re-ask settled questions.
4. **A step only a human can take** → generate a [wizard](../wizard/SKILL.md) and put the `blocked` label on the driving item until the human clears it.

## Done when (checkable: verify each line before reporting complete)

- The first verified checkpoint proves the thinnest end-to-end slice, and later checkpoints widen it; no step stacks a horizontal layer that goes nowhere alone.
- Every seam the item's verification set names has a test that was written red before its code, passes now, and stays in the suite; other changes have validation proportional to their behavior and risk.
- Coherent work is checkpointed with its verification; commits follow the user's authorization and explicit no-commit restrictions.
- The diff contains only in-scope files, and every adjacent discovery is on the tracker rather than in the diff.
- Every mid-build bug carries diagnose's closing artifacts; structural friction is reported in the close-out summary; every material unresolved decision was raised while routine choices used available evidence; every human-only step rides a wizard with the `blocked` label on the driving item, or none of these arose.
- The close-out summary points at the three audit artifacts: the seam tests, the tracer checkpoint, and the diff's scope.

## Attribution

Adapted from Matt Pocock's [`implement`](https://github.com/mattpocock/skills/tree/main/skills/engineering/implement) and [`tdd`](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd) (MIT). The implement-session shape is his: a session that builds from the spec or tickets, tests as it goes, and ends in review. So is the red–green loop by vertical slice: red before green, one seam, one test, one minimal implementation per cycle, each test a tracer bullet responding to what the last cycle taught (his terms), testing only at pre-agreed seams rather than everywhere, and behavior-through-public-interfaces as what a good test is.

What this pack changes: the seam agreement moves upstream (the item's verification set names the seams at filing time, instead of a mid-session ask) and validation outside named seams follows actual risk while preserving required tests and regression checks; the tracer-first mandate on the first verified checkpoint; verified checkpoints support same-task recovery within the user's commit instructions; the file-don't-fix scope rule; enforcement by close-out artifacts rather than commit forensics; and the four named interlocks into diagnose, codebase-review, the decider, and wizard.

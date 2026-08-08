---
name: codebase-review
description: Run a state review of the codebase — the counterpart to adversarial-review's change review — lens-named finders hunting structural friction, a built-in skeptic that kills unproven candidates, and a disposition loop where the decider adopts, rejects, or defers every survivor. Use before building against an upcoming spec (make the change easy first), when lanes merged since the last review cross the repo's threshold, or when lanes or the orchestrator report the code fighting them.
---

# Codebase review

A review of what the codebase **is**, where [adversarial-review](../../run/adversarial-review/SKILL.md) reviews what a diff changes. It hunts **deepening opportunities** — places where structure taxes every change that passes through — and ends only when the decider has dispositioned every surviving candidate. This skill is the portable protocol: an entry gate, a read-only review lane of lens-named finders, a skeptic pass that kills candidates before the report exists, and the disposition loop. Everything repo-specific — where reports land, the trigger threshold, where rejections are remembered, how the lane is run — lives in **binding slots** the team-workflow setup interview fills.

Read the team-workflow binding doc first. Full domain-modeling discipline (CONTEXT.md glossaries, ADR upkeep) is deliberately not part of this skill — it wants a skill of its own.

## 1. Triggers: an entry gate, never a calendar

The review runs when one of three gates opens — a scheduled run reviews whatever the calendar happens to land on, and produces findings to match.

1. **Pre-feature** — a spec is about to land in an area; review that area first, in the spirit of "make the change easy, then make the easy change."
2. **Lane-count threshold** — N lanes have merged since the last review (N is a per-repo binding slot). Merged work is the pressure that degrades structure; the count measures the pressure.
3. **Reported friction** — a lane or the orchestrator reports the code fought them: a change that should have been local sprawled, a test that could only be written past an interface.

**Scope follows the trigger.** Pre-feature reviews the spec's blast radius. Lane-count and friction reviews cover the areas churned since the last review, weighted by git history — recently-changed code is where deepening pays, because it is where the next change lands. A full sweep runs exactly once: a repo's first-ever review.

## 2. Execution: a read-only lane

The review runs as a **delegated lane**, claimed and tracked like any work item — how it is launched and tracked is the executor binding slot. Its contract is read-only: it changes no code and files no tickets; its deliverable is the report, and ticket filing belongs to the disposition loop (§5).

**Before any finder runs, the lane reads the repo's rejection memory** (binding slot): a candidate the decider rejected reopens on new evidence, never on repetition. A rerun that re-proposes a recorded rejection without new evidence has ignored the decider once and the memory twice.

Finder agents run in parallel, each holding **one named lens** from the menu, stated in the report:

- **shallow modules / seams** — interfaces nearly as complex as the implementations behind them; seams placed where nothing varies, or missing where something does.
- **duplicated concepts** — one concept implemented in several places, so one change must be made N times and is made N−1.
- **dead code** — code the deletion test clears for removal: delete it and no complexity reappears anywhere.
- **boundaries-vs-reality** — the declared module layout versus how change actually flows: imports that cross seams, layers honored in the diagram and bypassed in the code.
- **test-pain** — code that can only be tested past its interface, and the setup-heavy tests that prove it.

Finders and the skeptic speak the shared design vocabulary — depth, seams, locality, the deletion test — defined in [references/design-vocabulary.md](references/design-vocabulary.md); every claim in the report is phrased in those terms, in the codebase's own domain names.

## 3. The skeptic

A finder's candidate is a hypothesis. **Every candidate goes to a built-in skeptic whose brief is to kill it before the report exists** — re-read the code, find the second caller that makes the "duplicate" a real seam, the constraint that explains the "shallow" wrapper, the test that already covers the pain. Only candidates the skeptic fails to kill reach the report.

Survival is the only grade. A finder ranking its own findings — strong, worth exploring, speculative — is grading its own homework; the skeptic's failed kill is evidence, a badge is a mood.

## 4. The report

Plain markdown, posted on the tracker item the binding names. It carries:

- **Deferred candidates from the previous run, at the top** — deferral means carried forward, not quietly dropped.
- **Each survivor**: the claim, the evidence (files and lines), the skeptic's attempted kill and why it failed, the estimated cost, and the payoff in locality and leverage terms.
- **Zero survivors is a verdict, stated as a success**: "the codebase is fine" — the finders looked, the skeptic held the bar, and nothing survived. A review that must produce findings to feel finished manufactures them.

## 5. The disposition loop

The run is **not finished at report time** — an undispositioned report is a review that changed nothing. The orchestrator (or whoever ran the review) presents every survivor to the decider as a structured question card, [grilling](../../decide/grilling/SKILL.md)-style: the claim, the skeptic's verdict, cost and payoff, with the recommendation marked on an option — numbered-text fallback where no card tool exists. The decider dispositions each:

- **Adopt** — becomes a tracker ticket ([to-tickets](../../run/to-tickets/SKILL.md) where bound) and rides normal lane flow.
- **Reject** — recorded in rejection memory with the load-bearing reason. The reason is the record's value: a future run needs to know *why*, so it can tell new evidence from repetition.
- **Defer** — carried at the top of the next run's report, and named in session handoffs so it survives the context boundary.

The run's tracker item closes only when nothing is undispositioned.

## 6. Binding slots (the setup interview fills these per-repo)

- **Report destination** — the tracker item or query where run reports and close-outs land.
- **Lane-count threshold (N)** — merged lanes since the last review that open gate 2.
- **Rejection memory** — where rejected candidates and their load-bearing reasons live.
- **Executor mechanics** — how the review lane is launched, claimed, and tracked (in repos running the [orchestrate](../../run/orchestrate/SKILL.md) skill, its lane-launch machinery is the natural answer).

## Done when (checkable)

- The triggering gate is named in the report, and the scope matches it (blast radius, churn-weighted, or first-ever full sweep).
- Rejection memory was read before any finder ran; nothing proposed re-litigates a recorded rejection without new evidence.
- Every finder's lens is stated, and every candidate went through the skeptic — the report contains survivors only.
- Every survivor carries claim, file/line evidence, the attempted kill and why it failed, cost, and payoff; a zero-survivor run states the "codebase is fine" verdict.
- Deferred candidates from the previous run appear at the top, each re-dispositioned or re-deferred.
- Every survivor is dispositioned — adopted to a ticket, rejected into memory with its reason, or deferred — and the run's tracker item is closed.
- The lane changed no code and filed no tickets itself.

## Attribution

This skill is adapted from Matt Pocock's [`improve-codebase-architecture`](https://github.com/mattpocock/skills) (MIT). The core model is his: the hunt for deepening opportunities as the unit of review, weighting attention toward recently-changed code, per-candidate cards carrying problem/cost/payoff, respecting recorded rejections so reviews don't re-suggest settled ground, and grounding every suggestion in the shared design vocabulary of his [`codebase-design`](https://github.com/mattpocock/skills) (MIT), which the [references doc](references/design-vocabulary.md) adapts.

What this repo changes: event triggers replace on-demand invocation, the review runs as a read-only tracked lane, finders take named lenses in parallel, a skeptic pass replaces self-graded recommendation-strength badges, the report is plain markdown on a tracker item rather than an HTML artifact, zero survivors is an explicit success verdict, and the disposition loop — adopt / reject-into-memory / defer-and-carry, closing only when nothing is undispositioned — replaces the pick-one grilling loop.

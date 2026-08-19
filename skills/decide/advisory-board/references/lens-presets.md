# Advisory Board Lens Presets

A seat's lens is a **role assignment, not a model**. Any provider can sit in any seat: the lens just steers what that seat watches for, so the board covers more ground than undifferentiated reviewers would.

Every seat still answers the full brief. The lens reduces blind spots; it doesn't narrow responsibility.

Two seats may share a lens **when they sit on different providers**: that's a cross-model comparison on one axis, and often the point of a bigger board. The same provider carrying the same lens twice adds nothing; give each duplicate-provider seat its own lens.

## How to use

1. Choose the preset closest to the material (default: `software-architecture`), or compose your own lenses.
2. Assign each lens to a seat. With the default Claude / Codex / Gemini / Grok lineup, map by fit; with a different lineup or seat count, assign however the lenses land.
3. Drop the lens into the Round 1 seat prompt's "Role emphasis" slot (see `prompt-templates.md`).

Running via `run_board.py`, the board preset is `--lens <preset>` (it sets the verdict's vocabulary *and* the default per-seat focus set). Give one seat its own focus with a repeated `--lens <seat-id>=<value>`, where `<value>` is a free-form focus string or a preset name (which uses that preset's primary focus). Seats you don't override keep the positional default, so a same-provider board gets distinct lenses without any extra flags. See `references/board-composition.md` for seat ids and targeting.

## Presets

### `software-architecture` (default)
- **Architecture & systems.** Design soundness, invariants, failure modes, adversarial review.
- **Implementation & testing.** Repo-grounded execution, migration, test strategy, edge cases.
- **Product & operations.** Rollout, latency, observability, evaluation, user-workflow risk.
- **Contrarian synthesis.** Challenge the other frames, surface hidden assumptions, reconcile tradeoffs.

### `product-strategy`
- **Market & user value.** Positioning, demand, differentiation, jobs-to-be-done.
- **Execution & GTM.** Feasibility, resourcing, sequencing, go-to-market mechanics.
- **Second-order & risk.** Competitive response, cannibalization, downside and stakeholder risk.
- **Strategic red team.** Attack the thesis, test alternative explanations, identify decisive evidence.

### `research-paper`
- **Methodology & validity.** Design, statistics, threats to validity, confounds.
- **Novelty & positioning.** Contribution, related work, what is actually new.
- **Reproducibility & impact.** Can it be reproduced, stated limitations, who it helps and how.
- **Adversarial synthesis.** Reconcile conflicting evidence, probe generalization, test the strongest counterclaim.

### `legal-contract`
- **Risk allocation.** Liability, indemnity, limitation of liability, termination, IP.
- **Enforceability & compliance.** Governing law, regulatory fit, ambiguity, gaps.
- **Commercial practicality.** Operational burden, counterparty reality, negotiation leverage.
- **Adversarial interpretation.** Find exploitable ambiguity, conflicting duties, hard negotiation tradeoffs.
- _Directional review to focus a human lawyer, not legal advice._

### `business-decision`
- **First principles & economics.** Does the core logic and the math hold up.
- **Execution & feasibility.** Can this org actually do it, with what and by when.
- **Second-order & downside.** Stakeholders, incentives, what breaks if it works.
- **Contrarian synthesis.** Challenge consensus, compare alternatives, name the decision-changing evidence.

### `writing-editing`
- **Argument & structure.** Thesis, logic, evidence, what is load-bearing.
- **Clarity & style.** Concision, flow, precision, tone for the audience.
- **Audience & impact.** Does it land, what is missing, what a skeptic seizes on.
- **Adversarial editor.** Test the argument against hostile readings and synthesize the strongest revision.

### `red-team`
Every seat is hostile by assignment: the preset for stress-testing an artifact (a skill, spec, plan, or document) before you stake something on it. Pair with `--repo` when the artifact lives in a codebase so attacks cite `path:line`.
- **Correctness attacker.** Find the input, state, or sequence that makes it wrong; construct the failing case, don't gesture at it.
- **Ambiguity attacker.** Read it the way a reasonable executor would get it wrong: instructions two readers would follow differently, contradictions, undefined edge behavior.
- **Security & data-handling attacker.** What leaks, what escalates, what a malicious input or poisoned dependency reaches; secrets, PII, and consent paths first.
- **Unimagined-failure hunter.** The failure class the author's framing excludes: wrong assumptions about the environment, scale, users, or time.

### `stakeholder-panel`
"The room this decision would face": three distinct stakeholder archetypes, one per seat, in a fixed **seat-order binding**:
- **The decision owner.** The executive who must answer for the outcome: does it deliver, at what cost, what do we tell the board.
- **The end user.** The person this lands on: does it actually help them, what friction or harm does it create, would they choose it.
- **The compliance & risk reviewer.** The gatekeeper who signs off: what rule, obligation, or downside does this trip, and can we defend it.
- **The independent challenger.** The outsider who questions the room's shared assumptions and forces a defensible synthesis.

The lens string **is** the persona (there is no separate structured-persona object). The seat-order binding is positional; a **2-seat** board takes the first two archetypes. It pairs naturally with weighted-rubric scoring: `--rubric --lens stakeholder-panel` convenes the room *and* scores the decision against criteria the panel itself agrees. But the two flags are **orthogonal**: `--lens stakeholder-panel` never implies `--rubric`, and `--rubric` never implies a lens. Combine them explicitly.

## Custom lenses

No preset fits? Write lenses that triangulate the subject: first-principles soundness, execution and feasibility, second-order consequences and stakeholder risk, plus an independent challenger when a fourth seat is present. Keep them distinct enough that two seats won't return the same review.

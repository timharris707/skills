# Advisory Board Lens Presets

A seat's lens is a **role assignment, not a model**. Any provider can sit in any seat — the lens just steers what that seat watches for, so the board covers more ground than undifferentiated reviewers would.

Every seat still answers the full brief. The lens reduces blind spots; it doesn't narrow responsibility.

## How to use

1. Choose the preset closest to the material (default: `software-architecture`), or compose your own lenses.
2. Assign each lens to a seat. With the default Claude / Codex / Gemini / Grok lineup, map by fit; with a different lineup or seat count, assign however the lenses land.
3. Drop the lens into the Round 1 seat prompt's "Role emphasis" slot (see `prompt-templates.md`).

Running via `run_board.py`, the board preset is `--lens <preset>` (it sets the verdict's vocabulary *and* the default per-seat focus set). Give one seat its own focus with a repeated `--lens <seat-id>=<value>`, where `<value>` is a free-form focus string or a preset name (which uses that preset's primary focus). Seats you don't override keep the positional default — so a same-provider board gets distinct lenses without any extra flags. See `references/board-composition.md` for seat ids and targeting.

## Presets

### `software-architecture` (default)
- **Architecture & systems** — design soundness, invariants, failure modes, adversarial review.
- **Implementation & testing** — repo-grounded execution, migration, test strategy, edge cases.
- **Product & operations** — rollout, latency, observability, evaluation, user-workflow risk.
- **Contrarian synthesis** — challenge the other frames, surface hidden assumptions, reconcile tradeoffs.

### `product-strategy`
- **Market & user value** — positioning, demand, differentiation, jobs-to-be-done.
- **Execution & GTM** — feasibility, resourcing, sequencing, go-to-market mechanics.
- **Second-order & risk** — competitive response, cannibalization, downside and stakeholder risk.
- **Strategic red team** — attack the thesis, test alternative explanations, identify decisive evidence.

### `research-paper`
- **Methodology & validity** — design, statistics, threats to validity, confounds.
- **Novelty & positioning** — contribution, related work, what is actually new.
- **Reproducibility & impact** — can it be reproduced, stated limitations, who it helps and how.
- **Adversarial synthesis** — reconcile conflicting evidence, probe generalization, test the strongest counterclaim.

### `legal-contract`
- **Risk allocation** — liability, indemnity, limitation of liability, termination, IP.
- **Enforceability & compliance** — governing law, regulatory fit, ambiguity, gaps.
- **Commercial practicality** — operational burden, counterparty reality, negotiation leverage.
- **Adversarial interpretation** — find exploitable ambiguity, conflicting duties, hard negotiation tradeoffs.
- _Directional review to focus a human lawyer — not legal advice._

### `business-decision`
- **First principles & economics** — does the core logic and the math hold up.
- **Execution & feasibility** — can this org actually do it, with what and by when.
- **Second-order & downside** — stakeholders, incentives, what breaks if it works.
- **Contrarian synthesis** — challenge consensus, compare alternatives, name the decision-changing evidence.

### `writing-editing`
- **Argument & structure** — thesis, logic, evidence, what is load-bearing.
- **Clarity & style** — concision, flow, precision, tone for the audience.
- **Audience & impact** — does it land, what is missing, what a skeptic seizes on.
- **Adversarial editor** — test the argument against hostile readings and synthesize the strongest revision.

### `stakeholder-panel`
"The room this decision would face" — three distinct stakeholder archetypes, one per seat, in a fixed **seat-order binding**:
- **The decision owner** — the executive who must answer for the outcome: does it deliver, at what cost, what do we tell the board.
- **The end user** — the person this lands on: does it actually help them, what friction or harm does it create, would they choose it.
- **The compliance & risk reviewer** — the gatekeeper who signs off: what rule, obligation, or downside does this trip, and can we defend it.
- **The independent challenger** — the outsider who questions the room's shared assumptions and forces a defensible synthesis.

The lens string **is** the persona (there is no separate structured-persona object). The seat-order binding is positional; a **2-seat** board takes the first two archetypes. It pairs naturally with weighted-rubric scoring — `--rubric --lens stakeholder-panel` convenes the room *and* scores the decision against criteria the panel itself agrees — but the two flags are **orthogonal**: `--lens stakeholder-panel` never implies `--rubric`, and `--rubric` never implies a lens. Combine them explicitly.

## Custom lenses

No preset fits? Write lenses that triangulate the subject: first-principles soundness, execution and feasibility, second-order consequences and stakeholder risk, plus an independent challenger when a fourth seat is present. Keep them distinct enough that two seats won't return the same review.

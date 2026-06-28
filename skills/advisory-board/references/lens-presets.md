# Advisory Board Lens Presets

A seat's lens is a **role assignment, not a model**. Any provider can sit in any seat — the lens just steers what that seat watches for, so the board covers more ground than three general reviewers would.

Every seat still answers the full brief. The lens reduces blind spots; it doesn't narrow responsibility.

## How to use

1. Choose the preset closest to the material (default: `software-architecture`), or compose your own three lenses.
2. Assign each lens to a seat. With the default Claude / Codex / Gemini lineup, map by fit; with a different lineup or a different seat count, assign however the lenses land.
3. Drop the lens into the Round 1 seat prompt's "Role emphasis" slot (see `prompt-templates.md`).

Running via `run_board.py`, the board preset is `--lens <preset>` (it sets the verdict's vocabulary *and* the default per-seat focus trio). Give one seat its own focus with a repeated `--lens <seat-id>=<value>`, where `<value>` is a free-form focus string or a preset name (which uses that preset's primary focus). Seats you don't override keep the positional default — so a same-provider board gets distinct lenses without any extra flags. See `references/board-composition.md` for seat ids and targeting.

## Presets

### `software-architecture` (default)
- **Architecture & systems** — design soundness, invariants, failure modes, adversarial review.
- **Implementation & testing** — repo-grounded execution, migration, test strategy, edge cases.
- **Product & operations** — rollout, latency, observability, evaluation, user-workflow risk.

### `product-strategy`
- **Market & user value** — positioning, demand, differentiation, jobs-to-be-done.
- **Execution & GTM** — feasibility, resourcing, sequencing, go-to-market mechanics.
- **Second-order & risk** — competitive response, cannibalization, downside and stakeholder risk.

### `research-paper`
- **Methodology & validity** — design, statistics, threats to validity, confounds.
- **Novelty & positioning** — contribution, related work, what is actually new.
- **Reproducibility & impact** — can it be reproduced, stated limitations, who it helps and how.

### `legal-contract`
- **Risk allocation** — liability, indemnity, limitation of liability, termination, IP.
- **Enforceability & compliance** — governing law, regulatory fit, ambiguity, gaps.
- **Commercial practicality** — operational burden, counterparty reality, negotiation leverage.
- _Directional review to focus a human lawyer — not legal advice._

### `business-decision`
- **First principles & economics** — does the core logic and the math hold up.
- **Execution & feasibility** — can this org actually do it, with what and by when.
- **Second-order & downside** — stakeholders, incentives, what breaks if it works.

### `writing-editing`
- **Argument & structure** — thesis, logic, evidence, what is load-bearing.
- **Clarity & style** — concision, flow, precision, tone for the audience.
- **Audience & impact** — does it land, what is missing, what a skeptic seizes on.

## Custom lenses

No preset fits? Write three lenses that triangulate the subject: one on first-principles soundness, one on execution and feasibility, one on second-order consequences and stakeholder risk. Keep them distinct enough that two seats won't return the same review.

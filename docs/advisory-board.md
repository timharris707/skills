---
title: Advisory Board
---

# Advisory Board

`advisory-board` is a reusable workflow for getting an idea, plan, or decision reviewed by several high-reasoning models before you commit to it.

Bring the board any material worth more than one expert opinion — a plan, design, architecture, document, decision, or goal. Each model reviews it independently, then reads a packet of the first-round findings and responds to the strongest objections, missed details, and points of disagreement. A final synthesis turns the debate into a single working handoff.

## What It Is For

- Adversarial review of a plan, design, or architecture before a build.
- Pressure-testing a decision, strategy, or proposal.
- Implementation sequencing.
- Surfacing risks, stale assumptions, and missing evidence.
- Letting several models debate and sharpen each other's thinking.
- Turning multiple model opinions into a single takeaway.

## Default Workflow

1. **Round 1** — each model reviews independently, with no view of the others.
2. **Round 2** — each model reads the other seats' findings and responds: what it missed, what changed its mind, what it still disputes.
3. **Final synthesis** — the chair writes a handoff with consensus, dissent, risks, guardrails, and next actions.

Two rounds is the default: enough for the board to challenge itself without turning every review into a long-running process.

## Seats

Each seat gets a distinct lens, matched to the subject. For software and technical work:

- **Claude** — architecture, systems, and adversarial design review.
- **Codex** — repo-grounded implementation, migration, testing, and execution.
- **Gemini** — product, operations, rollout, latency, evaluation, and user-workflow risk.

For non-software subjects the seats take comparable lenses — first-principles soundness, execution and feasibility, and second-order consequences. Every seat still reviews the whole brief; the lens reduces blind spots, it doesn't narrow responsibility.

## Safety Defaults

- Read-only unless edits are explicitly requested.
- Subscription-backed CLIs where available.
- Highest available reasoning settings, verified at run time.
- No secrets stored in artifacts.

## Outputs

A run saves:

- per-seat Round 1 notes;
- per-seat Round 2 rebuttals;
- a board packet between rounds;
- a final consensus handoff;
- optional run metadata (no secrets).

## Source Files

- [`SKILL.md`](../skills/advisory-board/SKILL.md)
- [`prompt-templates.md`](../skills/advisory-board/references/prompt-templates.md)
- [`openai.yaml`](../skills/advisory-board/agents/openai.yaml)

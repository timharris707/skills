---
title: Advisory Board Review
---

# Advisory Board Review

`advisory-board-review` is a reusable workflow for getting a plan reviewed by several high-reasoning model seats before implementation begins.

The intended use is simple: give the board a plan, architecture document, repo, or goal. Each model reviews the same material independently, then reads a board packet from the first round and responds to the strongest objections, missed details, and points of disagreement. A final synthesis turns the discussion into a single working handoff.

## What It Is For

- Architectural review before a build.
- Adversarial plan review.
- Implementation sequence design.
- Risk and assumption discovery.
- Turning multiple model opinions into a single consensus document.

## Default Workflow

1. Round 1: each model reviews independently.
2. Round 2: each model reads the summarized findings from the other seats and responds.
3. Final synthesis: the chair creates a handoff with consensus, dissent, risks, guardrails, and next actions.

The default is two rounds because it gives the board enough time to challenge itself without turning every review into a long-running process.

## Default Seats

- Claude seat: architecture, systems, and adversarial design review.
- Codex seat: repo-grounded implementation, migration, testing, and execution review.
- Gemini seat: product, operations, rollout, latency, evaluation, and user-workflow risk.

Each seat still reviews the full plan. The seat emphasis is there to reduce blind spots, not to narrow responsibility.

## Safety Defaults

- Read-only unless edits are explicitly requested.
- No OpenClaw dependency.
- Subscription-backed CLI usage where available.
- Highest available reasoning settings verified at run time.
- No secrets stored in artifacts.

## Outputs

The skill is designed to save:

- per-seat Round 1 notes;
- per-seat Round 2 rebuttals;
- a board packet between rounds;
- a final consensus handoff;
- optional run metadata without secrets.

## Source Files

- [`SKILL.md`](../skills/advisory-board-review/SKILL.md)
- [`prompt-templates.md`](../skills/advisory-board-review/references/prompt-templates.md)
- [`openai.yaml`](../skills/advisory-board-review/agents/openai.yaml)

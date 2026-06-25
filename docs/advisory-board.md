---
title: Advisory Board
---

# Advisory Board

`advisory-board` is a reusable workflow for getting an idea, plan, or decision reviewed by several high-reasoning models before you commit to it.

Bring the board any material worth more than one expert opinion — a plan, design, architecture, document, decision, or goal. Each model reviews it independently, then reads a packet of the first-round findings and responds to the strongest objections, missed details, and points of disagreement. A final synthesis turns the debate into a single working handoff.

**See a sample:** [a rendered handoff](./sample-handoff.html) from a payments idempotency review — self-contained HTML that opens offline.

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

Two rounds is the default: enough for the board to challenge itself without turning every review into a long-running process. Set rounds to `auto` to stop early on convergence or add a round when real disagreement remains.

## Seats

Each seat gets a distinct lens, matched to the subject — ready-made lens sets for software, product, research, legal, business, and writing live in [`lens-presets.md`](../skills/advisory-board/references/lens-presets.md). For software and technical work:

- **Claude** — architecture, systems, and adversarial design review.
- **Codex** — repo-grounded implementation, migration, testing, and execution.
- **Gemini** — product, operations, rollout, latency, evaluation, and user-workflow risk.

For non-software subjects the seats take comparable lenses — first-principles soundness, execution and feasibility, and second-order consequences. Every seat still reviews the whole brief; the lens reduces blind spots, it doesn't narrow responsibility.

## Safety Defaults

- A preflight go/no-go check (CLI, auth, model, smoke ping) gates every run — a board needs at least two healthy seats.
- Sensitive material is disclosed before it leaves the machine, with redaction or a local-only board as options.
- Read-only unless edits are explicitly requested.
- Subscription-backed CLIs where available.
- Highest available reasoning settings, verified at run time.
- No secrets stored in artifacts.

## Outputs

A run saves:

- per-seat Round 1 notes;
- per-seat Round 2 rebuttals;
- a board packet between rounds;
- a final consensus handoff (Markdown + self-contained HTML);
- `verdict.json` — a machine-readable verdict you can gate CI on or reshape into a PR comment, Slack message, or TL;DR;
- run metadata: provenance, per-seat status, and timings (no secrets).

## Source Files

- [`SKILL.md`](../skills/advisory-board/SKILL.md)
- [`prompt-templates.md`](../skills/advisory-board/references/prompt-templates.md)
- [`lens-presets.md`](../skills/advisory-board/references/lens-presets.md)
- [`preflight.md`](../skills/advisory-board/references/preflight.md)
- [`board-composition.md`](../skills/advisory-board/references/board-composition.md)
- [`data-handling.md`](../skills/advisory-board/references/data-handling.md)
- [`epistemics.md`](../skills/advisory-board/references/epistemics.md)
- [`run-metadata-template.md`](../skills/advisory-board/references/run-metadata-template.md)
- [`verdict-schema.md`](../skills/advisory-board/references/verdict-schema.md)
- [`output-formats.md`](../skills/advisory-board/references/output-formats.md)
- [`intake-interview.md`](../skills/advisory-board/references/intake-interview.md)
- [`handoff-template.html`](../skills/advisory-board/references/handoff-template.html)
- [`scripts/`](../skills/advisory-board/scripts/) — `board_verdict.py`, `format_output.py`
- [`openai.yaml`](../skills/advisory-board/agents/openai.yaml)

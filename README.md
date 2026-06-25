# Skills

Reusable AI workflow skills for planning, review, orchestration, and execution support.

This repository is provider-agnostic: a skill may ship adapter metadata for a specific runtime, but the source of truth in `SKILL.md` stays readable, portable, and easy to adapt.

## Current Skills

| Skill | Purpose |
| --- | --- |
| [Advisory Board](./skills/advisory-board/SKILL.md) | A multi-model round table that reviews the same material, debates across rounds, and produces a single working handoff. |

## Advisory Board

Bring an idea, problem, plan, or architecture to a board of frontier models sitting in different roles. `advisory-board` runs Claude, Codex, and Gemini through their subscription CLIs as separate seats: each reviews the same source independently, then reads a packet of the others' findings and answers the strongest objections, before a final synthesis turns the debate into one working handoff. You leave with the best conclusion the board can reach together — not three disconnected opinions.

Default behavior:

- two rounds of review and rebuttal;
- read-only unless edits are explicitly requested;
- cross-reading via summaries;
- subscription-backed CLIs where available;
- the highest available reasoning setting for each provider, verified at run time.

Use it to:

- pressure-test a plan, design, or architecture before you build;
- stress a decision, strategy, or proposal from several angles at once;
- surface risks, stale assumptions, and missing evidence;
- let strong models debate and sharpen each other's thinking;
- collapse several model opinions into a single, clean takeaway;
- review non-software work too — product, research, legal, business, and writing — via built-in lens presets.

## See It In Action

Every run ends in a single, self-contained HTML handoff — verdict, the round-by-round debate, consensus blockers, preserved dissent, and next actions — that opens offline in any browser with no dependencies.

- **View a live sample:** [rendered handoff for a payments idempotency review](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/payments-idempotency-review/final-consensus.html)
- **Browse the full run:** [`examples/payments-idempotency-review/`](./examples/payments-idempotency-review/) — per-seat round notes, the board packet, and both the Markdown and HTML handoffs.
- **Gate on it:** every run also emits a machine-readable [`verdict.json`](./examples/payments-idempotency-review/verdict.json); `scripts/board_verdict.py --gate` turns the board's `ship | caution | block` call into a CI exit code, and `scripts/format_output.py` reshapes it into a PR comment, Slack message, or TL;DR.

The look comes from one template, [`handoff-template.html`](./skills/advisory-board/references/handoff-template.html), so any agent that installs the skill renders the same clean output.

## Repository Layout

```text
skills/
  advisory-board/
    SKILL.md
    agents/
      openai.yaml
    references/
      prompt-templates.md
      lens-presets.md
      preflight.md
      board-composition.md
      data-handling.md
      epistemics.md
      run-metadata-template.md
      verdict-schema.md
      output-formats.md
      intake-interview.md
      handoff-template.html
    scripts/
      board_verdict.py
      format_output.py
      README.md
docs/
  index.md
  advisory-board.md
  sample-handoff.html
```

## Using A Skill

Each skill lives in `skills/<skill-name>/`.

For Codex-compatible runtimes, copy or sync a skill directory into your local skills folder (`agents/openai.yaml` is the only runtime adapter so far). Other agent runtimes can read `SKILL.md` directly and adapt the templates in `references/`.

## Public Docs

GitHub Pages-ready documentation lives in [`docs/`](./docs/) — the Advisory Board page covers what the workflow does and how it is meant to be used.

## License

Released under the [MIT License](./LICENSE.md) — free to use, copy, modify, and adapt with attribution.

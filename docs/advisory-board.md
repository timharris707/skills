---
title: Advisory Board
---

# Advisory Board

**Get a room full of expert advisors for any big decision — before you commit.**

Several leading AI advisors each examine the same thing — your plan, your decision, your draft, your design — then debate it out loud and converge on one clear recommendation. Think of it as the smartest meeting you'll ever call: everyone did the reading, no one's afraid to disagree, and you get a clean summary at the end. It works for software, but also for product, research, legal, business, and writing decisions.

## Who It's For

Founders weighing a big bet. Writers who want a hard read before they hit send. Product managers stress-testing a launch plan. Researchers checking a method. People comparing two real-life options. And yes — it goes deep for engineers too, citing exact `path:line` evidence in your codebase. If it's a decision worth getting right, it's worth bringing to the board.

## Ask the Board

- **Ask the board:** "I got a job offer — better pay, but I'd leave a team I love. Should I take it?"
- **Ask the board:** "Here's my apartment lease / freelance contract — anything I should worry about before I sign?" *(A sharp first read to bring to a professional — not legal advice.)*
- **Ask the board:** "We're thinking of raising prices 20%. Smart, or are we about to lose half our customers?"
- **Ask the board:** "I wrote a hard email to my boss — read it before I hit send."
- **Ask the board:** "Read my cover letter / wedding speech / pitch and make it land."
- **Ask the board:** "I'm choosing between two health-insurance plans for my family — walk me through the trade-offs." *(Helps you think it through; not medical or financial advice.)*
- **Ask the board:** "Here's our launch plan. What are we missing?"
- **Ask the board:** "Review this system design / architecture — find the flaw now, not in production." *(Point it at the real codebase and advisors cite exact `path:line` evidence.)*

## See What Comes Back

Here's a real board, debating a real decision — *"Should I go full-time on my side project?"*

> ### Verdict: Proceed with care — unanimous, high confidence
>
> *Workable, but address the flagged concerns before you go ahead.*
>
> **The blocker the board converged on:** *"Income case never closes: $12k MRR ≠ replacing a $165k salary."* All three advisors agreed the financial model was the gating item — once health insurance, self-employment tax, and lost benefits are stripped out, the target income is closer to half of current total comp. They didn't say "don't do it." They said *here's exactly what has to be true first*, and handed back the next steps to get there.

**[Read the full handoff →](./sample-handoff.html)** — a self-contained page that opens offline: the verdict, the round-by-round debate, the blockers they agreed on, the dissent they preserved, and the concrete next actions.

## How It Works, in 3 Steps

1. **Bring your thing.** Point it at whatever you're deciding — an idea, a document, a plan, a contract, a draft.
2. **The board reviews and debates.** Several top models review independently, then read each other's takes and push back — catching the blind spots a single opinion would miss.
3. **You get one clear answer.** A short, plain-English write-up: the bottom line (go ahead / proceed with care / stop and rethink), where they agree, where they don't, the risks, and your next steps.

The board is **leading models from Anthropic, OpenAI, and Google** — Claude, GPT-5.5, and Gemini — each in a different seat. Two rounds of back-and-forth by default: enough to genuinely stress-test your thinking without dragging on.

## Your Data, Your Call

**Independent first, together second.** Each advisor reviews your material on its own, with no idea what the others said — so they catch each other's blind spots instead of nodding along.

**You approve what leaves your computer.** You see exactly what would be sent to each provider and approve it before anything leaves your machine — redact what's sensitive, or run a fully local board where nothing is sent at all.

**It looks before it acts.** The board only reads, and never changes your work unless you explicitly ask. No surprises, no stored secrets.

A preflight check confirms at least two advisors are healthy before any run begins — a board needs a quorum.

## What You Walk Away With

A run hands you a single, plain-English handoff you can read like a memo, plus the full record behind it:

- **The bottom line** — go ahead, proceed with care, or stop and rethink, with the confidence level.
- **Where they agreed** — the blockers worth fixing before you commit.
- **Where they disagreed** — preserved, not flattened, so you can weigh it yourself.
- **What they couldn't verify** and the open questions still worth answering.
- **Your next steps** — concrete actions, not vague advice.
- **The full debate** — every advisor's first-round notes and second-round rebuttals, so you can check their work.

## Start Here

1. Pick what you're deciding — a plan, a draft, a contract, a design, a real-life choice.
2. Hand it to the board and let it run (two rounds, a few minutes).
3. Read the handoff, act on the next steps.

Curious what a finished run looks like first? **[Open the sample handoff →](./sample-handoff.html)**

---

## Also Built for Engineers

Under the warm summary is a workflow built for technical rigor — and a machine-readable verdict you can wire into a pipeline.

### Repo-grounded review

Point the board at a real codebase with `--repo` and advisors cite exact `path:line` evidence, working from a captured snapshot rather than guesswork. Ready-made lens sets for software, product, research, legal, business, and writing live in [`lens-presets.md`](../skills/advisory-board/references/lens-presets.md). For software and technical work the seats take distinct lenses:

- **Claude** (`claude-opus-4-8`) — architecture, systems, and adversarial design review.
- **Codex** (`gpt-5.5`) — repo-grounded implementation, migration, testing, and execution.
- **Gemini** (`gemini-3-pro-preview`) — product, operations, rollout, latency, evaluation, and user-workflow risk.

Every seat still reviews the whole brief; the lens reduces blind spots, it doesn't narrow responsibility.

### Default workflow

1. **Round 1** — each model reviews independently, with no view of the others.
2. **Round 2** — each model reads the other seats' findings and responds: what it missed, what changed its mind, what it still disputes.
3. **Final synthesis** — the chair writes a handoff with consensus, dissent, risks, guardrails, and next actions.

Two rounds is the default. Set rounds to `auto` to stop early on convergence or add a round when real disagreement remains.

### Gate CI on the verdict

Every run also emits `verdict.json` — a machine-readable call (`ship | caution | block`) you can gate CI on or reshape into a PR comment, Slack message, or TL;DR. `scripts/board_verdict.py --gate` turns the board's call into a CI exit code; `scripts/format_output.py` reshapes it for wherever your team reads it.

> **What "verified" means here:** each cited line carries a resolution check that confirms the quote exists in the captured material — it does *not* prove the inference drawn from it is correct. The board sharpens your judgment; it doesn't replace it.

### Outputs

A run saves:

- per-seat Round 1 notes;
- per-seat Round 2 rebuttals;
- a board packet between rounds;
- a final consensus handoff (Markdown + self-contained HTML);
- `verdict.json` — the machine-readable verdict described above;
- run metadata: provenance, per-seat status, and timings (no secrets).

### A technical example

Prefer to see the board on code? The [payments idempotency review](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/payments-idempotency-review/final-consensus.html) walks a real architecture decision end to end, with `path:line` evidence and a unanimous `block` verdict. Browse the full run in [`examples/payments-idempotency-review/`](https://github.com/timharris707/skills/tree/main/examples/payments-idempotency-review).

### Source Files

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

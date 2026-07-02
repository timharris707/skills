# Skills

**A panel of expert advisors for any hard decision.** Reusable AI workflow skills for the moments where one opinion isn't enough — reviewing, deciding, and pressure-testing the calls worth getting right before you commit.

This repository is provider-agnostic: a skill may ship adapter metadata for a specific runtime, but the source of truth in `SKILL.md` stays readable, portable, and easy to adapt.

## Current Skills

| Skill | Purpose |
| --- | --- |
| [Advisory Board](./skills/advisory-board/SKILL.md) | Convene a board of leading AI models to review the same decision, debate across rounds, and hand back one clear recommendation. |

## Advisory Board

**Get a room full of expert advisors for any big decision — before you commit.** Bring the board whatever you're weighing — a plan, a draft, a contract, a design, a real-life choice — and several leading AI models each examine it independently, then read each other's notes, argue out the disagreements, and hand you back one clear answer: what's solid, what's risky, and what to do next. You read it like a memo, not a config file. It works for software, but also for product, research, legal, business, and writing decisions.

The board is **leading models from Anthropic, OpenAI, and Google** — Claude, Codex/GPT-5.5, and Gemini — each sitting in a different seat. Each reviews the same source on its own, then reads a packet of the others' findings and answers the strongest objections, before a final synthesis turns the debate into one working handoff. You leave with the best conclusion the board can reach together — not three disconnected opinions.

Use it to:

- weigh a big personal or business decision — a job offer, a price change, going full-time on a side project;
- get a sharp first read on a draft, a pitch, a cover letter, or a hard email before you send it;
- pressure-test a plan, design, or architecture before you build;
- surface risks, stale assumptions, and missing evidence a single opinion would miss;
- collapse several strong opinions into one clean, plain-English takeaway.

Default behavior: two rounds of review and rebuttal; read-only unless edits are explicitly requested; you see exactly what would be sent to each provider and approve it before anything leaves your machine — redact what's sensitive, or run a fully local board where nothing is sent at all.

**Run it your way.** Advisory Board is a provider-agnostic agent skill — convene the board through Claude Code, Codex, or whatever harness you prefer.

> **Prefer a polished app instead?** [Panely](https://github.com/timharris707/panely) is a sibling product built around the same idea — a local-first advisory room. Advisory Board is the open agent skill; Panely is the app. Same maker.

## See It In Action

Here's a real board debating a real decision — *"Should we relocate our family across the country for this job offer?"* The offer looks great on paper: a **+37.5% raise**. The board's job was to check whether the headline survives contact with the math.

> **Verdict: Go ahead, with conditions — unanimous, high confidence.** The reveal all three advisors converged on: the raise is *consumed almost entirely by rent*, quietly collapsing monthly savings from **$2,750 to $537**; the $20k "covers the move" sign-on is gross and nets ~$11–13k against an ~$18k move; and the "take-home rises" headline **inverts** at a realistic tax rate. They didn't say "don't" — they said exactly what to resolve first, and handed back the next steps.

**Read it two ways — start with the skim:**

- **The 30-second brief:** [quick-verdict for the relocation decision](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/should-we-relocate-our-family-across-the-country-for-this-job-offer/quick-verdict.html) — the verdict, the must-resolve blockers as one-liners, the top next steps. The teaser you'd forward.
- **The full handoff:** [the complete record](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/should-we-relocate-our-family-across-the-country-for-this-job-offer/final-consensus.html) — the round-by-round debate, every consensus blocker, and preserved cross-model dissent (Gemini: *"you're shorting your marital operating system"*).
- **See the input, too:** [the decision brief](./examples/should-we-relocate-our-family-across-the-country-for-this-job-offer/decision.md) the board reviewed — good input in, good output out.

Every run ends in a single, self-contained HTML handoff that opens offline in any browser with no dependencies.

**Also built for engineers:** point the board at a real codebase and advisors cite exact `path:line` evidence. Every run also emits a machine-readable [`verdict.json`](./examples/payments-idempotency-review/verdict.json); `scripts/board_verdict.py --gate` turns the board's `ship | caution | block` call into a CI exit code, and `scripts/format_output.py` reshapes it into a PR comment, Slack message, or TL;DR. See the technical [payments idempotency review](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/payments-idempotency-review/final-consensus.html) for a code-grounded run.

**More runs to browse:** the [side-project go-full-time decision](./examples/side-project-go-full-time-review/), the [API rate-limiter readiness review](./examples/ratelimiter-readiness-review/), and the board [dogfooding the design of its own next feature](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/dogfood-fixit-design-roundtable/final-consensus.html) — a 3-seat design roundtable with preserved cross-model dissent.

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

## Releases

Each skill is versioned independently and published as a GitHub release from a skill-scoped tag
(`<skill>/vX.Y.Z`). Per-skill changes are tracked in that skill's `CHANGELOG.md` (e.g.
[`skills/advisory-board/CHANGELOG.md`](./skills/advisory-board/CHANGELOG.md)); see
[`RELEASING.md`](./RELEASING.md) for how releases are cut.

## License

Released under the [MIT License](./LICENSE.md) — free to use, copy, modify, and adapt with attribution.

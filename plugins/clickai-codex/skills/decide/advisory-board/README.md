# Advisory Board

**Get a room full of expert advisors for any big decision — before you commit.** Bring the board whatever you're weighing — a plan, a draft, a contract, a design, a real-life choice — and several leading AI models each examine it independently, then read each other's notes, argue out the disagreements, and hand you back one clear answer: what's solid, what's risky, and what to do next. You read it like a memo, not a config file. It works for software, but also for product, research, legal, business, and writing decisions.

The default board uses frontier models from **Anthropic, OpenAI, Google, and xAI** — Claude, Codex, Gemini, and Grok — each sitting in a different seat. Provider-maintained aliases/defaults select the strongest current model at run time, while explicit model overrides remain pinned. Each seat reviews the same source on its own, then reads a packet of the others' findings and answers the strongest objections before a final synthesis turns the debate into one working handoff.

Use it to:

- weigh a big personal or business decision — a job offer, a price change, going full-time on a side project;
- get a sharp first read on a draft, a pitch, a cover letter, or a hard email before you send it;
- pressure-test a plan, design, or architecture before you build;
- surface risks, stale assumptions, and missing evidence a single opinion would miss;
- collapse several strong opinions into one clean, plain-English takeaway.

Default behavior: two rounds of review and rebuttal; read-only unless edits are explicitly requested; you see exactly what would be sent to each provider and approve it before anything leaves your machine — redact what's sensitive, or run a fully local board where nothing is sent at all.

**Run it your way.** Advisory Board is a provider-agnostic agent skill — convene the board through Claude Code, Codex, or whatever harness you prefer. Install it from the [repo root](../../../README.md#install-claude-code), or read [`SKILL.md`](./SKILL.md) directly.

> **Prefer a polished app instead?** [Panely](https://github.com/timharris707/panely) is a sibling product built around the same idea — a local-first advisory room. Advisory Board is the open agent skill; Panely is the app. Same maker.

## See It In Action

Here's a real board debating a real decision — *"Should we relocate our family across the country for this job offer?"* The offer looks great on paper: a **+37.5% raise**. The board's job was to check whether the headline survives contact with the math.

> **Verdict: Go ahead, with conditions — unanimous, high confidence.** (A three-seat board sat for this run.) The reveal all three advisors converged on: the raise is *consumed almost entirely by rent*, quietly collapsing monthly savings from **$2,750 to $537**; the $20k "covers the move" sign-on is gross and nets ~$11–13k against an ~$18k move; and the "take-home rises" headline **inverts** at a realistic tax rate. They didn't say "don't" — they said exactly what to resolve first, and handed back the next steps.

**Read it two ways — start with the skim:**

- **The 30-second brief:** [quick-verdict for the relocation decision](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/should-we-relocate-our-family-across-the-country-for-this-job-offer/quick-verdict.html) — the verdict, the must-resolve blockers as one-liners, the top next steps. The teaser you'd forward.
- **The full handoff:** [the complete record](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/should-we-relocate-our-family-across-the-country-for-this-job-offer/final-consensus.html) — the round-by-round debate, every consensus blocker, and preserved cross-model dissent (Gemini: *"you're shorting your marital operating system"*).
- **See the input, too:** [the decision brief](https://github.com/timharris707/skills/tree/main/examples/should-we-relocate-our-family-across-the-country-for-this-job-offer/decision.md) the board reviewed — good input in, good output out.

Every run ends in a single, self-contained HTML handoff that opens offline in any browser with no dependencies.

**Also built for engineers:** point the board at a real codebase and advisors cite exact `path:line` evidence. Every run also emits a machine-readable [`verdict.json`](https://github.com/timharris707/skills/tree/main/examples/payments-idempotency-review/verdict.json); [`scripts/board_verdict.py`](./scripts/board_verdict.py) `--gate` turns the board's `ship | caution | block` call into a CI exit code, and [`scripts/format_output.py`](./scripts/format_output.py) reshapes it into a PR comment, Slack message, or TL;DR. See the technical [payments idempotency review](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/payments-idempotency-review/final-consensus.html) for a code-grounded run.

**More runs to browse:** the [side-project go-full-time decision](https://github.com/timharris707/skills/tree/main/examples/side-project-go-full-time-review/), the [API rate-limiter readiness review](https://github.com/timharris707/skills/tree/main/examples/ratelimiter-readiness-review/), and the board [dogfooding the design of its own next feature](https://htmlpreview.github.io/?https://github.com/timharris707/skills/blob/main/examples/dogfood-fixit-design-roundtable/final-consensus.html) — a 3-seat design roundtable with preserved cross-model dissent.

**The board reviewing its own PRs:** during the v1.13→v1.15 release train, every substantial PR got a 2-seat board review (Claude Opus + Codex gpt-5.5) on a frozen review packet, then a `--revise` re-review of the fixes — each pair linked by directory suffix (the revise run appends the next numeric suffix to the original run's directory name). Browse the committed rulings: the [endorsement-pass review](https://github.com/timharris707/skills/tree/main/examples/v1-13-p4-endorsement-pass-pr-review-2026-07-02/) (`block` → `caution` across the revise pass), the [echo-score review](https://github.com/timharris707/skills/tree/main/examples/v1-14-p2-echo-score-pr-review-2026-07-02/) (the board ruled `block` where a solo review agent had said ship — divergence with recorded dissent), the [live-progress review](https://github.com/timharris707/skills/tree/main/examples/v1-14-p3-live-progress-pr-review-2026-07-02/) (`caution` → a clean `ship`), and the [rubric-round review](https://github.com/timharris707/skills/tree/main/examples/v1-15-p2-rubric-round-pr-review-2026-07-02-2/) (a split `block` with preserved cross-seat dissent; [the revise pass](https://github.com/timharris707/skills/tree/main/examples/v1-15-p2-rubric-round-pr-review-2026-07-02-3/) confirmed both blockers fixed and surfaced a new one). There's also a second design roundtable: the [rubric-first deliberation brief](https://github.com/timharris707/skills/tree/main/examples/v1-15-rubric-first-design-brief-2026-07-02/) — 3 seats, unanimous `caution`, three preserved dissents.

The look comes from one template, [`handoff-template.html`](./references/handoff-template.html), so any agent that installs the skill renders the same clean output.

## Going Deeper

- **[The GitHub Pages guide](https://timharris707.github.io/skills/advisory-board)** — the friendly walkthrough: who it's for, how a run works, what you walk away with, and the engineer-grade features (repo grounding, lens presets, CI gating).
- **[`SKILL.md`](./SKILL.md)** — the skill itself: the full workflow contract any agent runs.
- **[`references/`](./references/)** — prompt templates, lens presets, preflight, board composition, data handling, epistemics, verdict schema, output formats, and the handoff/quick-verdict HTML templates.
- **[`scripts/`](./scripts/)** — `board_verdict.py` (CI gate) and `format_output.py` (PR comment / Slack / TL;DR reshaping).
- **[`CHANGELOG.md`](./CHANGELOG.md)** — versioned history; releases tag as `advisory-board/vX.Y.Z`.

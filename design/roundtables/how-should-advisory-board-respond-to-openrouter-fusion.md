# How should Advisory Board respond to OpenRouter Fusion?

## The decision

OpenRouter shipped **Fusion** (June 2026): a server-side multi-model deliberation behind one model id. It is, structurally, the **same core idea as this `advisory-board` skill**, built by a different team. We need the board's verdict on **how advisory-board should respond**: which candidate features to adopt, in what order, and — just as important — what to deliberately **NOT** do. Be specific, opinionated, and rank. A non-answer ("it depends") is a failure; commit to a recommendation and say what would change it.

You are reviewing your **own** skill. A read-only snapshot of `skills/advisory-board/` is in scope — verify claims about what we already do against the real code (`SKILL.md`, `scripts/_conductor/registry.py`, `references/data-handling.md`) rather than trusting this brief.

## What Fusion is (verified from primary sources)

- One API call to `openrouter/fusion` fans out to a **panel of 1–8 models in parallel** (default `claude-opus-latest`, `gpt-latest`, `gemini-pro-latest`), each with web search + fetch on.
- A **judge model** *compares* (explicitly "does not merge") the panel into structured JSON: `consensus`, `contradictions`, `partial_coverage`, `unique_insights`, `blind_spots`, plus raw per-model responses. A final model writes the answer.
- **Pass-through priced** (~4–5× a single completion; ~2–7× latency). Streams; OpenAI/Anthropic-API-compatible; has a chat UI.
- Can be attached as a **server tool** so a coding agent **escalates to it selectively** (most control). Positioned as "overkill for short prompts — for when the cost of being wrong outweighs a few extra completions." Server-tool layer is **beta**.
- Benchmark (DRACO, 100 deep-research tasks): a fused panel beats every individual frontier model. Notably **fusing Opus with itself** (2× Opus, Opus judge) = **+6.7 pts** over solo Opus — suggesting much of the lift is the **synthesis / test-time-compute step**, not model diversity alone.

## What advisory-board is today (contrast — verify against the snapshot)

- **Subscription CLIs, ~$0 marginal** (not metered API keys). Multi-round **debate** with cross-reading (seats read each other and revise), **distinct role lenses** per seat, a **neutral synthesizer + minority report**.
- A machine-readable **`verdict.json`** (ship/caution/block) with a CI **gate** that **abstains** when the board is torn or a citation is **refuted**; **repo-grounding** + a **verify** chain that stamps citations verified/unverified/refuted.
- **read-XOR-network** safety, redaction, and a **local-only board** option for sensitive material. Durable artifact bundle + provenance.
- Seats are **full agentic CLIs run read-only** (bigger tool surface than Fusion's panel; the constraint is posture, not arsenal).

## Candidate features — evaluate each: ADOPT NOW / DEFER / REJECT, with why

1. **Inline / embeddable escalation mode** — a lightweight single-question "one-shot board" callable like a tool (e.g. an MCP server / server-tool another agent escalates to), distinct from the full multi-round run. This is our biggest capability gap vs Fusion. Worth it, or a distraction from our strengths?
2. **Sandboxed execution-grounded seats** — let seats run code/tests in a sandbox to ground claims (Fusion's benchmark gave `bash`). (Being deep-dived in a separate run — here, just rank it against the others.)
3. **MCP / domain-tool pass-through** to seats (DB, internal API, browser) for domain-specific boards.
4. **Crisper structured output** — adopt Fusion's `partial_coverage` / `unique_insights` as explicit `verdict.json` fields alongside our evidence/judgment/couldn't-verify buckets.
5. **A published benchmark** — DRACO-style, to substantiate "debate beats solo" with a number.
6. **Positioning / differentiation** — make debate + economics (subscription, ~$0 marginal) + privacy/local + verifiability the explicit moat; frame the board as a "deliberation workflow with a gateable verdict," not "an inline model."

## What should we deliberately NOT become?

Name the moves that would be a mistake — e.g. chasing a metered inline API and forfeiting the subscription / local / verifiable advantages, or adding cost/complexity that dilutes the gate.

## What the board must deliver

For **each** candidate: a verdict (adopt-now / defer / reject), a one-line rationale, the main risk, and what evidence would change the call. Then:
- The **single highest-leverage move** for the next milestone.
- The **one thing to refuse**.
- Where each load-bearing claim is **grounded in the repo** vs a **judgment call** vs **couldn't-verify**.

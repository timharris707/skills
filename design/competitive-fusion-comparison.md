# OpenRouter Fusion vs. Advisory Board — competitive comparison

> Fusion is the same core idea as the advisory board, built independently — strong validation of the thesis, and a useful map of where we differ and what's worth borrowing.

- **Subject:** OpenRouter "Fusion" (launched ~June 13, 2026) vs. the `advisory-board` skill
- **Date:** 2026-06-26
- **Sources:** OpenRouter model page, plugin/router/server-tool docs, launch blog ("Surpassing Frontier Performance with Fusion"), HN #48537641; our `skills/advisory-board/SKILL.md` + `scripts/_conductor/registry.py`
- **Confidence:** Fusion facts from primary sources (a few flagged unverified at the end); our facts from the skill source.

## Headline

Fusion is, structurally, **the same core idea as the advisory board, built independently.** Both make the same wager: *several frontier models from different providers, grounded with web search, with a judge that surfaces consensus and disagreement, beats any single model on high-stakes reasoning.* They even land on the **same default lineup** — Claude Opus + OpenAI GPT + Google Gemini.

They diverge on three things that matter: **whether the models actually debate, what it costs to run, and where the thing lives.** OpenRouter shipping this is encouraging external validation of our core bet — and a clear map of our moat and the few things worth borrowing.

## What Fusion is

A server-side orchestration behind a single model alias (`openrouter/fusion`). One call fans a prompt out to a panel of **1–8 models in parallel** (default: `claude-opus-latest`, `gpt-latest`, `gemini-pro-latest`), each with web search + fetch on. A **judge model** then *compares* the panel answers (explicitly "does not merge") into structured JSON — `consensus`, `contradictions`, `partial_coverage`, `unique_insights`, `blind_spots` — and a final model writes the answer. Pass-through priced (~4–5× a single completion, ~2–7× latency), streams, OpenAI/Anthropic-API-compatible, attachable as a **server tool** so a coding agent escalates to it selectively. Positioned explicitly as "overkill for short prompts — for when the cost of being wrong outweighs a few extra completions." Server-tool layer is labeled **beta**.

## Side by side

| Dimension | **Fusion** | **Advisory Board** |
|---|---|---|
| Topology | Fan-out → judge → final writer. **One pass.** | Fan-out → **debate across 2–3 rounds** → neutral synthesizer |
| Do models see each other? | **No** — panel answers in parallel, blind to each other; only the judge reads all | **Yes** — seats read each other's findings each round, revise, and dissent |
| Model diversity | Cross-provider (Opus/GPT/Gemini), 1–8 configurable | Cross-provider (Opus/GPT/Gemini), 2–5 seats |
| Role differentiation | None — every panelist gets the same prompt | **Distinct lenses per seat** (architecture / implementation / product-ops…) |
| Auth & cost | OpenRouter **API key, metered**, ~4–5× single completion | **Subscription CLIs, ~$0 marginal** (uses your Claude/ChatGPT/Gemini plans) |
| Latency | ~2–3× (HN reports ~7×) a single call | Minutes — multi-round, high reasoning |
| Web grounding | Exa/Parallel search+fetch, on by default | Seats web-search; **plus optional repo-grounding** with read-only snapshot |
| Citation integrity | Inline citations; no verification layer | **`verify` chain** stamps each citation verified/unverified/**refuted**; fabrication fails the gate |
| Output | Structured JSON inline (+ raw responses) | Artifact bundle: per-round files, packets, `final-consensus.md`/`.html`, `verdict.json`, `run-metadata` |
| Decision / gating | Analysis, not a verdict | **CI-gateable** ship/caution/block, **abstains** when torn or a citation is refuted |
| Epistemic honesty | `blind_spots` section | `blind_spots` **+ confidence levels + evidence/judgment/couldn't-verify buckets + minority report** |
| Privacy | Cloud-only; data → OpenRouter + panel providers + Exa | **Data-handling consent, redaction, local-only board option**, read-XOR-network gate safety |
| Where it lives | Inline API / server tool / chat UI — **embeddable** | Local skill/CLI workflow — **not embeddable inline** |
| Setup | Zero — one model id | Install + auth 2–3 CLIs |
| Orchestration control | Server-side, opaque | **You own the conductor**; deterministic packets & convergence |

## The crux: debate vs. one-shot

The single most important difference. **Fusion's panel never talks to each other** — models answer the same question in isolation, and a judge reports where they happened to agree. Our seats **read each other's work and argue across rounds**, changing or defending positions, with the conductor measuring movement until they converge. Fusion gives a *snapshot of independent opinions, compared.* The board gives a *deliberation that has been pressure-tested.*

OpenRouter's own benchmark hints this is where the value lives: **fusing Opus 4.8 with itself** (2× Opus, Opus judge) jumped **+6.7 points** over solo Opus — i.e. much of the lift came from the **synthesis / test-time-compute step, not model diversity per se.** That's a direct argument that the board's extra rounds of deliberation buy something real, and it validates the board's "same provider in two seats" fallback config.

## Tool surface & "taking action" (the axis that's easy to misread)

A natural first read is "Fusion's agents take action; are ours under-armed?" On tool *surface*, it's the reverse:

- **Fusion's panel** gets `web_search` + `web_fetch` (Exa), plus `bash` in the DRACO benchmark. Its "action" is **web research + sandboxed computation** — it does not mutate your environment.
- **Our seats are full agentic CLIs** held read-only by design (`registry.py`): Claude `--permission-mode plan` (read-only bash + web), **Codex `--sandbox read-only` which *can* execute commands** (no writes/network), Gemini `--approval-mode plan` (executes **no** tools), plus optional repo-grounding.

So on raw arsenal we arm seats *at least* as much as Fusion. The difference is **posture**, not tooling — and the read-only posture is load-bearing: the board's whole safety guarantee is **read XOR network** (a seat that can both read your repo and reach the net is the exfiltration channel the gate exists to break). Fusion carries no such guarantee (cloud-only; your data's already at OpenRouter + Exa).

**The one genuine gap** the "take action" framing points at is **execution-grounded reasoning**: the Fusion benchmark let models *run* things to check claims; our default leans read-and-reason, and Gemini can't execute at all. For "does this reproduce / what does the benchmark say / does this query return what they claim," a read-only seat is genuinely weaker. That gap, and its safe envelope, is scoped separately in `design/run-board-executable-evidence.md`.

## What Fusion validates about the board

Built independently, Fusion converged on: multi-provider panel → judge → structured output, web grounding on by default, "consensus / contradictions / blind spots" as the output shape, the model-diversity thesis, and "escalation primitive, not a default" positioning. **Every one is a load-bearing choice in the advisory board.** A serious infra company shipping the same design is a signal the core bet is right.

## Pros & cons

**Fusion**
- ✅ Inline, one API call, embeddable in any app/agent; server-tool lets a coding agent self-escalate
- ✅ Zero setup, managed, streaming, auto-decides whether deliberation is even needed
- ✅ Lower latency for a single query; a published benchmark (DRACO) showing it beats frontier solo
- ❌ No real debate — parallel-and-compare, not deliberate-and-converge
- ❌ Metered ~4–5× cost; cloud-only (no privacy/local mode); opaque orchestration
- ❌ Analysis, not a gateable decision; no citation-verification/fabrication guard; no role/lens differentiation

**Advisory Board**
- ✅ Genuine multi-round debate with role lenses; neutral synthesis + minority report
- ✅ **~$0 marginal** on existing subscriptions; runs local/redacted with consent gates for sensitive material
- ✅ Repo-grounding + citation verification that **refutes fabrications**; CI-gateable verdict; durable, human-readable artifact bundle with full provenance
- ✅ You own and can audit the whole orchestration
- ❌ Heavyweight: install/auth several CLIs, minutes per run
- ❌ **Not embeddable inline** — a workflow you run, not a model you call
- ❌ No managed option, no published benchmark, no "auto-skip when overkill" gating; weaker execution-grounding

## Strategic takeaways

1. **Different lanes, not direct rivals.** Fusion is an *inline escalation model*; the board is a *deliberation workflow with a durable, gateable verdict.* We don't need to out-API Fusion.
2. **Our moat is debate + economics + verifiability + privacy.** Lean into those in positioning — none are things Fusion does.
3. **Worth borrowing:** (a) Fusion's crisp `partial_coverage` / `unique_insights` sections complement our evidence buckets; (b) the **server-tool "escalate selectively" pattern** — we have no lightweight single-question mode, only the full run, so a "one-shot board" lane is worth a design note; (c) a DRACO-style **published benchmark** to substantiate "debate beats solo."
4. **The self-fusion +6.7 result is ammunition** for the board's deliberation-heavy design and its same-provider-multi-seat fallback.
5. **Execution-grounding** is the real capability gap — scoped in `design/run-board-executable-evidence.md`.

## Board verdicts (dogfooded)

Both strategic questions below were run **through the advisory board itself** — grounded, 3-seat (Claude·Codex·Gemini) cross-provider boards debating across rounds — so the response is the product's own deliberation, not a single author's take. (Doing so also surfaced and fixed a real self-review bug in the conductor; see [skills#32](https://github.com/timharris707/skills/pull/32).)

**"How should advisory-board respond to Fusion?"** → *Proceed with care — high confidence, unanimous* (`design/roundtables/fusion-response-run/`). The board:
- **Adopt now:** rewrite positioning as a *local, gateable, abstaining deliberation workflow at ~$0 marginal* (not an inline model); **ship a local one-shot escalation surface** (`advisory-board ask` / an MCP tool) as a thin wrapper over `run_board.py` — the embeddability gap vs Fusion, but exposing the *real* board (debate + gate intact), never a degraded one-shot; add `partial_coverage`/`unique_insights`/`blind_spots` as **informational, never gate-bearing** schema fields.
- **Defer:** a published benchmark (until the integration exists; then measure gate precision/recall, not raw accuracy); execution-grounded seats (own deep-dive, below).
- **Reject:** MCP/domain-tool pass-through on the gate+repo path (collides with read-XOR-network) — allowed only on local-only/advisory profiles.

**"Should we add a sandboxed-execution seat mode, and what's the safe envelope?"** → *Build-with-constraints — high confidence, unanimous*, 3 rounds (`design/roundtables/executable-evidence-run/`). Reframed the feature as a **declared-command broker** (not seat bash), gated on proving execution output isn't an ungated egress channel. Full build plan: `design/run-board-executable-evidence.md`.

## Unverified / honest caveats

- Fusion's model-page metadata shows **"$0 / $0 per-million-tokens"** — almost certainly a placeholder (it bills the underlying models pass-through). **Not a free tier.**
- The full "9 models in this router" list and all preset slugs beyond `general-high` / `general-budget` weren't reachable (a `/labs/fusion` page 404s). Default production search provider ("Exa or Parallel") isn't pinned beyond the benchmark using Exa.
- Server-tool layer is **beta**; behavior may change.

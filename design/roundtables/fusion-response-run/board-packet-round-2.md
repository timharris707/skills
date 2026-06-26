# Board packet — round 2 (cross-reading: summaries — structured digest)

## Where the board stands after round 1

Verdicts: claude=caution · codex=caution · gemini=caution
Agreement: unanimous: caution
Shared evidence (raised by ≥2 seats): `isolates_network=false`, `partial_coverage`, `scripts/board_verdict.py`, `skill.md:23`, `unique_insights`, `verdict.json`

## By topic

### Verdict

- **claude:** **CAUTION — proceed, but only with the reframing below.** Confidence: **medium-high.** The plan's instincts are mostly right, but its headline framing is wrong in a way that matters commercially. Candidate #1 ("inline escalation mode") is …
- **gemini:** **Verdict:** `caution` (proceed only with the changes and positioning revisions below) **Confidence:** High *What would change this:* This verdict would shift to `block` if the board attempted to compete directly with OpenRouter on …

### Strongest objections

- **claude:** **A. "Biggest capability gap" is a category error.** Fusion's inline model id is the *commodified* version of this idea — pass-through priced, one team owns the gateway. If we ship a metered inline API to match it, we compete on their …
- **gemini:** * **Objection 1: The CLI Background Execution DX Disaster (Feature 1 — Inline Escalation Mode)** Our seat adapters run on subscription-backed local CLIs (such as `antigravity-cli`, `@openai/codex`, and `claude`) that require interactive …

### Recommended execution sequence

- **claude:** Ranked by leverage-per-cost for the next milestone: 1. **#6 Positioning — ADOPT NOW (week 1, near-zero cost).** Rewrite the one-liner: "a deliberation *workflow* with a gateable, abstaining verdict — runs on your subscriptions at ~$0 …
- **gemini:** We must avoid playing on OpenRouter's home turf (server-side, fast-answering, high-volume API completions) and instead double down on our structural moats: **deliberate multi-round debate, verifiability, privacy, and zero marginal cost**. …

### Invariants & guardrails

- **claude:** - **The gate stays uncontaminated.** `board_verdict.py:68-69` already enforces "**The gate never reads** [confidence]." Any #4 field (`partial_coverage`, `unique_insights`) must be **informational only** — never a gate input. The abstain …
- **gemini:** * **Invariant 1 (Read XOR Network):** No seat with repository read access (`--repo`) shall ever be passed domain tools with network-enabled capabilities (browser, external API) or write permissions. * **Invariant 2 (Deterministic …

### Risks, stale assumptions & missing evidence

- **claude:** - **Missing: any proof debate > compare.** Fusion's judge *explicitly does not merge* (packet) and still wins benchmarks; the 2×Opus result says synthesis-compute is most of the lift. **We have no evidence our cross-reading-and-revise loop …
- **gemini:** * **Stale Assumption: Google CLI/Auth Longevity:** As grounded in `registry.py:L455` and `board-composition.md`, Google sunset consumer tiers for `gemini-cli` on 2026-06-18, leaving only enterprise/API, and requiring migration to the newer …

### Concrete evidence

- **gemini:** * **`SKILL.md:L17-21` [verified]:** Core hard rules: *"Never write files or make edits... Never present a degraded or dropped seat as a full board... a board needs at least two seats that actually ran."* * …

### Challenges to the board

- **claude:** - **Codex (execution/repo lens):** Can the existing conductor (`run_board.py`) be wrapped as a local MCP/server-tool with *no* new metered path and *no* weakening of D4's read-XOR-network gate? If the inline mode can't preserve the gate …
- **gemini:** * **To Claude (Architecture & Adversarial Seat):** Challenge the security boundaries of passing tools to seats. Could local-only, de-networked DB tools still be abused via prompt injection to leak sensitive database schemas into the final …

### codex — review (no section headers found; head excerpt)

**Verdict** Caution, high confidence. Proceed, but narrow the response to one milestone: ship an inline/local escalation mode plus clearer structured output and positioning. What would change my view: credible user evidence that customers care more about domain-tool pass-through or a public benchmark than about invoking the board from their existing agent workflow. **Candidate Calls** | Candidate | Call | Rationale | Main Risk | Would Change If | |---|---:|---|---|---| | 1. Inline / embeddable escalation | ADOPT NOW, rank 1 | Biggest GTM gap versus Fusion. Build as a thin local tool/CLI/MCP wrapper over existing conductor, not a new hosted API. | Bypassing egress, provenance, or gate rules to feel …

# Round 2 Advisory Board Review: Gemini Seat
**Role Emphasis:** Second-order & risk — competitive response, cannibalization, downside, and stakeholder risk

---

### 1. Updated Verdict & Confidence

*   **Verdict:** `caution`
*   **Confidence:** High
*   **What would change it:** Solid, production-validated evidence showing that an inline, background tool-escalation mode can run on subscription-backed CLIs without hitting interactive authentication prompts, causing shell hangs, violating provider Terms of Service, or bypassing our strict `read XOR network` security boundary.

---

### 2. Changed Mind & Dissent

*   **Where we CHANGED OUR MIND:**
    *   **With respect to Codex (Candidate 1):** In Round 1, Codex strongly advocated for adopting Candidate 1 (Inline Escalation Mode) immediately as its top priority. We originally opposed this outright as a developer experience disaster due to background authentication hangs. However, after reviewing the seat adapters (`scripts/_conductor/registry.py:L395-510` [verified]) and the execution harness (`references/execution-harness.md` [verified]), we change our mind to **conditionally support a local-only CLI/MCP bridge** in a subsequent milestone. If scoped strictly as a local-only tool running on already-authenticated user-owned CLIs, it bridges the capability gap without adopting a risky hosted/metered architecture.
    *   **With respect to Claude (Candidate 1):** Claude argued that Candidate 1 is a "category error." We agree with Claude's positioning moat but change our mind on a complete rejection or long deferral; we can prototype a local CLI/MCP bridge once positioning and structured outputs are stabilized.

*   **Where we STILL DISSENT:**
    *   **Dissent from Codex's Rank 1 Priority for Candidate 1:** We still dissent from making Candidate 1 the immediate priority. Doing so severely underestimates the high operational risks: (a) developer frustration with high-latency multi-round local runs in active IDE loops (`SKILL.md:L42` [verified] warns that runs can take minutes), and (b) background authentication hangs where non-interactive subprocesses block on credential entry or stdin reads (`scripts/_conductor/registry.py:L480` [verified]; `references/execution-harness.md:L63` [verified]). Candidate 6 (Positioning) and Candidate 4 (Crisper Structured Output) must precede it.
    *   **Dissent from any metered, hosted gateway or server-side API:** We completely dissent from entering the metered, server-side API market. Doing so cannibalizes our core **subscription-backed, ~$0 marginal cost moat** (`SKILL.md:L35` [verified]), exposes us to high liability regarding repository code egress to third-party endpoints without the local, hash-bound explicit consent flow (`references/data-handling.md:L29` [verified]), and pits us directly against OpenRouter's core competency.

---

### 3. Strongest Remaining Objections

*   **Objection 1: The High-Latency / Blocked Developer Loop Risk (Second-Order/UX):** Active coding agents expect tool calls to return in single-digit seconds. Convening a 2-round multi-model board with local CLIs takes *minutes* due to slow subprocess spawns and deep reasoning times (`SKILL.md:L42` [verified]). Exposing this inline as a background tool will lead to frequent agent timeouts and severe developer frustration unless the calling agent is explicitly designed for asynchronous, high-latency deliberation.
*   **Objection 2: Non-Interactive Stdin/Auth Hangs:** In an automated IDE or server-tool loop, there is no active TTY. If a seat's subscription credentials expire, or if the subprocess reads stdin to EOF, it will hang or crash. As verified in `scripts/_conductor/registry.py:L480` [verified] (`agy` verified to hang without `DEVNULL`) and `references/execution-harness.md:L63` [verified] (`codex` always closed), non-interactive execution is incredibly fragile.
*   **Objection 3: Tool Pass-through (Candidate 3) Prompt-Injection Exfiltration Risk:** Passing active database, API, or system tools to seats (even if de-networked) is an unacceptable second-order risk. An adversarial repository under review could contain prompt-injection payloads that trick the seat into querying sensitive database schemas, then writing those schemas into its review output—which is then transmitted and fanned out to other external providers in Round 2 (`SKILL.md:L99` [verified]; `references/data-handling.md:L29` [verified]).

---

### 4. Recommended Execution Sequence

1.  **Milestone 1: Candidate #6 (Positioning & Differentiation) — ADOPT NOW.**
    *   *Rationale:* Near-zero cost; immediately solidifies our branding as a high-integrity, high-deliberation *workflow* with a gateable, abstaining verdict, rather than a fast inline model.
    *   *Main Risk:* No technical barriers built, leaving the GTM gap open briefly.
2.  **Milestone 1.5: Candidate #4 (Crisper Structured Output) — ADOPT NOW.**
    *   *Rationale:* Add optional fields (`partial_coverage`, `unique_insights`) to `verdict.json` and render them.
    *   *Main Risk:* Diluting the focus of the report if not strictly segregated.
    *   *Guardrail:* These fields must be purely informational and must **never** feed the deterministic gating logic in `board_verdict.py` (`references/verdict-schema.md:L68-69` [verified]).
3.  **Milestone 2: Candidate #1 (Local CLI/MCP Escalation Bridge) — DEFER / PROTOTYPE.**
    *   *Rationale:* Build a local, CLI-driven wrapper that exposes `run_board.py` as a tool, enforcing strict timeouts, preflight checks, and a loud warning regarding subscription auth and latency.
    *   *Main Risk:* Background auth hangs and high-latency timeouts in developer IDEs.
4.  **Milestone 3: Candidate #2 (Sandboxed Execution-Grounded Seats) — DEFER.**
    *   *Rationale:* Highly complex; sandbox environments must prevent local disk escapes and exfiltration before we allow seats to execute code.
5.  **Milestone 4: Candidate #3 (MCP/Domain Tool Pass-through) & Candidate #5 (Published Benchmark) — REJECT.**
    *   *Rationale:* Tool pass-through is rejected due to prompt-injection and exfiltration risks. Benchmark is rejected due to rate-limiting, slow execution, and terms-of-service/suspension risks on subscription CLIs.

---

### 5. Invariants and Guardrails

*   **Invariant 1: The Deterministic Gate remains untouched by "Soft" Fields:** The gating logic in `scripts/board_verdict.py:L217-251` [verified] must only evaluate verified `round_verdicts` and verified citations. Soft fields like `partial_coverage` or `unique_insights` are purely informational and must not influence gate outcomes.
*   **Invariant 2: Read XOR Network Security Boundary:** Any seat with repository read access (`--repo`) must be network-isolated. If a seat cannot be network-isolated (such as `gemini` or `antigravity`), the run must refuse in gate mode (`scripts/_conductor/config.py:L110` [verified]; `references/data-handling.md:L39` [verified]). No tool-use or escalation mode can bypass this quarantine.
*   **Invariant 3: Zero-Metered Egress / Subscription Moat:** We must never build a hosted, metered API gateway. All seat interactions must be driven through local CLI adapters owned and authenticated by the user (`SKILL.md:L35` [verified]).

---

### 6. Risks, Stale Assumptions, and Missing Evidence

*   **Risk: Account Ban/Rate-Limiting on Subscription CLIs:** Driving subscription CLIs via automated, tight background loops (such as active IDE extension tool calls) violates terms of service, leading to rate-limiting or account bans.
*   **Stale Assumption: Gemini CLI Consumer Auth Viability:** The consumer tiers of `gemini-cli` were sunset on 2026-06-18 (`scripts/_conductor/registry.py:L455` [verified], `references/board-composition.md:L17` [verified]). Believing we can continue to rely on consumer-tier `gemini-cli` is stale. We must transition users to `antigravity` (Google's agent-first `agy` CLI successor) or paid API keys.
*   **Missing Evidence: Deliberate Debate vs Single-Shot Compare:** There is no hard evidence in the repository that a multi-round debate with cross-reading is significantly superior to a single-shot "compare" by a strong judge. We need internal evaluation metrics, but compiling them is hampered by rate limits on subscription CLIs.

---

### 7. Concrete Evidence

*   **`SKILL.md:L17-21` [verified]:** Core hard rules: `"Never write files or make edits... Never present a degraded or dropped seat as a full board... a board needs at least two seats that actually ran."`
*   **`SKILL.md:L35` [verified]:** Core Defaults: `"Use subscription CLIs by default, not provider API keys."`
*   **`references/data-handling.md:L39` [verified]:** `"Gate mode requires read XOR network (D4)... Gate + --repo therefore requires every seat to be network-isolatable; a seat that can't be de-networked (today gemini, antigravity) makes the run refuse..."`
*   **`references/verdict-schema.md:L68-69` [verified]:** `"confidence — low | medium | high. A self-reported number; informational. The gate never reads it — a gameable confidence must not move a gate."`
*   **`scripts/_conductor/registry.py:L455` [verified]:** Gemini auth hint: `"run gemini once and authenticate (Google account; consumer tiers sunset 2026-06-18 — enterprise/API only)"`
*   **`scripts/_conductor/registry.py:L480` [verified]:** Antigravity adapter detail: `"agy reads stdin to EOF — verified to hang without DEVNULL"`
*   **`scripts/board_verdict.py:L238` [verified]:** Gate decision logic: `"The decision reads each seat's final-round verdict, never the gameable confidence."`
*   **`references/execution-harness.md:L63` [verified]:** Stdin execution caveat: `"codex always takes its prompt as an argument with stdin closed."`
*   **`scripts/_conductor/config.py:L110` [verified]:** Unenforced network seats: `"return [s.name for s in self.board if not s.adapter.isolates_network]"`
*   **`scripts/run_board.py:L53-54` [verified]:** Gating logic basis: `"driven by OBSERVED cross-seat agreement, never self-reported confidence."`

---

VERDICT: caution

# Advisory Board Strategic Review: Response to OpenRouter Fusion

**Seat:** Gemini  
**Role Emphasis:** Second-order & risk — competitive response, cannibalization, downside and stakeholder risk

---

### 1. Verdict & Confidence Level

**Verdict:** `caution` (proceed only with the changes and positioning revisions below)  
**Confidence:** High  
*What would change this:* This verdict would shift to `block` if the board attempted to compete directly with OpenRouter on low-latency, inline, metered API completions, or if we compromised our core "Read XOR Network" safety boundary.

---

### 2. Strongest Objections (Risk & Cannibalization Analysis)

*   **Objection 1: The CLI Background Execution DX Disaster (Feature 1 — Inline Escalation Mode)**  
    Our seat adapters run on subscription-backed local CLIs (such as `antigravity-cli`, `@openai/codex`, and `claude`) that require interactive browser/OAuth logins, regular version upgrades, and local session caches (as verified in `registry.py:L429`, `L455`, `L481`). Packaging this as a low-latency background inline tool (e.g., an MCP server) in another agent's loop is a developer experience trap. The moment a subscriber’s session expires or a CLI version drifts, the parent agent's loop will block or fail silently.
*   **Objection 2: Breach of the "Read XOR Network" Invariant (Feature 3 — MCP / Domain-Tool Pass-through)**  
    Under `references/data-handling.md:L35-41`, our repo-grounded safety depends on the **Read XOR Network** policy. A seat with read access to local code (`--repo`) must never have network access. If we pass domain-specific tools (DB, internal APIs, browser) to seats while they are reviewing code, we create an immediate exfiltration vector. A malicious repository file with an embedded prompt injection could instruct a seat to query the database and exfiltrate credentials or code via the browser/network tool.
*   **Objection 3: Sandboxing Complexity & Latency Penalties (Feature 2 — Sandbox Execution)**  
    Executing code on the local host to ground claims introduces severe security risks. As grounded in `references/data-handling.md:L41-45`, Codex's `--sandbox read-only` does **not** confine physical reads to the working directory. Building secure, local, multi-platform container sandboxes (e.g., Docker or WASM) within a Python/CLI tool adds massive operational footprint and maintenance overhead, turning a lightweight, highly-portable skill into heavy, brittle infrastructure.

---

### 3. Recommended Execution Sequence

We must avoid playing on OpenRouter's home turf (server-side, fast-answering, high-volume API completions) and instead double down on our structural moats: **deliberate multi-round debate, verifiability, privacy, and zero marginal cost**.

| Rank | Candidate | Action | Technical Rationale & Mitigation |
| :--- | :--- | :--- | :--- |
| **1** | **6. Positioning / Differentiation** | **ADOPT NOW** | Position the board as a **deliberate decision-making workflow and gatekeeping engine** for high-stakes PRs/commits, not an inline model. Frame our subscription/local architecture as the privacy-respecting, zero-marginal-cost choice. |
| **2** | **4. Crisper Structured Output** | **ADOPT NOW (Modified)** | Do **NOT** modify the `verdict.json` schema (which must remain lean and gate-centric). Instead, update the synthesizer prompt (`_conductor/synthesizer.py`) and Markdown/HTML templates to render "Unique Insights" and "Partial Coverage" as explicit sections in human-facing views. |
| **3** | **5. Published Benchmark** | **DEFER** | Creating a DRACO benchmark is costly and drifts as models update. Instead, curate a portfolio of reproducible **qualitative case studies** (like `examples/payments-idempotency-review/verdict.json`) where our multi-round, grounded debate catches bugs that solo models ship. |
| **4** | **2. Sandboxed Execution** | **DEFER** | Postpone general sandboxed execution until secure, zero-config local WASM runners can be embedded directly into target provider CLIs without introducing local host vulnerabilities. |
| **5** | **1. Inline Escalation Mode** | **REJECT** | Avoid this. Headless background execution of subscription CLIs in agent loops is extremely fragile and prone to silent credential expiration timeouts. |
| **6** | **3. MCP / Domain-Tool Pass-through** | **REJECT** | Permanently reject domain-tool pass-through for grounded seats. It fundamentally violates the "Read XOR Network" safety policy. |

---

### 4. Invariants & Guardrails

*   **Invariant 1 (Read XOR Network):** No seat with repository read access (`--repo`) shall ever be passed domain tools with network-enabled capabilities (browser, external API) or write permissions.
*   **Invariant 2 (Deterministic Gating):** The CI/PR gate (`board_verdict.py`) must remain driven by deterministic token checks and validated citations. We must never transition to a heuristic, LLM-based comparison step for gate validation.
*   **Invariant 3 (Subscription & Local Economics):** Keep local-first (`ollama`) and subscription CLIs as first-class citizens. We must not transition to a metered, API-key-only architecture that forfeits our privacy and cost advantages.

---

### 5. Risks, Stale Assumptions, and Missing Evidence

*   **Stale Assumption: Google CLI/Auth Longevity:** As grounded in `registry.py:L455` and `board-composition.md`, Google sunset consumer tiers for `gemini-cli` on 2026-06-18, leaving only enterprise/API, and requiring migration to the newer agent-first `antigravity` CLI (`agy`). Our strategy must assume that paid consumer tiers are rapidly shifting, making local-first (`ollama`) models and enterprise API fallbacks increasingly vital.
*   **Latency & Timeout Risks:** Multi-seat, multi-round debates are inherently slow (default timeout cap is 15 minutes, `registry.py:L70`). This makes running them inline inside other agent loops highly vulnerable to timing out.
*   **Missing Evidence:** We lack data proving developers actually want an inline, fast-answering "micro-board," or if they prefer keeping the board as a high-stakes PR gate.

---

### 6. Concrete Evidence from the Source Material

*   **`SKILL.md:L17-21` [verified]:** Core hard rules: *"Never write files or make edits... Never present a degraded or dropped seat as a full board... a board needs at least two seats that actually ran."*
*   **`references/data-handling.md:L35-45` [verified]:** The "Read XOR Network" (D4) policy, and the honest limitation that Codex's read-only sandbox does **not** physically confine reads to the working directory (R9).
*   **`scripts/_conductor/registry.py:L194-200` [verified]:** The fact that the Gemini CLI adapter cannot disable GoogleSearch grounding (`isolates_network=False`), making it a NO-GO in gate mode.
*   **`scripts/_conductor/registry.py:L214-224` [verified]:** Google consumer tier sunset details (2026-06-18) and Antigravity CLI (`agy`) quirks (silent substitution of unknown model names and stdin hanging issues).
*   **`scripts/board_verdict.py:L223-239` [verified]:** The exact implementation of how the `abstain` exit (code 3) is computed based on observed cross-seat agreement and refuted citations.

---

### 7. What to Ask the Other Board Seats to Challenge

*   **To Claude (Architecture & Adversarial Seat):** Challenge the security boundaries of passing tools to seats. Could local-only, de-networked DB tools still be abused via prompt injection to leak sensitive database schemas into the final consensus markdown?
*   **To Codex (Implementation & Execution Seat):** Challenge the execution path of safe sandboxing. Can we isolate execution entirely inside a lightweight, zero-network WASM shell, and what is the development effort/bundle size penalty?

---

VERDICT: caution

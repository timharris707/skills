chat_summary_placeholderHere is the design review of the v1.13 "Transform: the board hands back a fixed copy" proposal from the Gemini seat (Product & Operations).

### 1. Verdict & Rationale
**Verdict: CAUTION**
**Confidence: HIGH**
*Change Factor:* This verdict would improve to **SHIP** if the latency-heavy sequential endorsement loop proposed in Q6 is optimized to be off-by-default or parallelized to avoid stalling the main user loop.

---

### 2. Strongest Objections & Operational Risks
* **The Sequential Endorsement Bottleneck (Q6):** Spawning additional review runs sequentially across all non-revision seats adds immense execution latency (up to 40-60% longer runs in a standard 3-seat board). This is highly disruptive to active CLI developer workflows.
* **Post-Synthesis Write-Path Reopening (Q2):** Modifying `verdict.json` *after* the synthesizer has finalized it violates transactional single-write guarantees. This exposes the file to dirty writes if concurrent actions (like human `amend` or CI validation gates) run simultaneously.
* **Line-Range Locator Drift (Q3):** Relying solely on line-range numbers without original context blocks means patches will break silently if a human makes minor local file modifications before applying the board's proposed changes.

---

### 3. Rulings on the Eight Questions (Q1–Q8)

#### Q1 — Edit Identity: Finding `id`s or exact titles?
* **Ruling:** **(a) Key by exact finding title.**
* **Rationale:** Titles are fully functional in the codebase today, as seen in `amend --on` and `--revise` delta matching. A complete schema evolution to `@3` just to support unique IDs is unnecessary overhead and causes backward compatibility churn. Finding titles are stable during the short minutes between synthesis and revision.

#### Q2 — Where does the mapping live: `changes.json` file vs. the reserved `changes` key?
* **Ruling:** **(a) Separate `changes.json` artifact only.** *(Dissenting from Strawman (b))*
* **Rationale:** Once `verdict.json` is written by the synthesizer and verified, the write path should be closed. We must avoid reopening `verdict.json` post-synthesis. A sovereign, self-contained `changes.json` maintains pipeline isolation and protects the integrity of the canonical verdict.

#### Q3 — `changes.json` Shape & Locator Mechanics
* **Ruling:** **Include line ranges + strict before/after context snippets.** *(Dissenting from line-only)*
* **Rationale:** Pure line-range locators are too fragile. Including short `before`/`after` blocks allows safety checks to confirm structural context matches before applying mutations. A complete validation check must be enforced: every blocker in the verdict must either map to an applied edit or be declared in the `unresolved` conflict array.

#### Q4 — Prose vs. Code: What decides redline vs. patch?
* **Ruling:** **(c) Heuristic default + flag override.**
* **Rationale:** Fully automatic detection fails on ambiguous extensions, and fully manual flags add friction. Heuristic detection for common extensions, combined with mandatory `--source-type` flags for stdin/URLs, recorded in the recipe, balances exact CLI ergonomics with reproducible replays.

#### Q5 — One spawn or two: How does the revision seat return text + mapping?
* **Ruling:** **(a) One spawn with two fenced sections.**
* **Rationale:** A single spawn guarantees transactional consistency. Splicing text and JSON metadata in a single response prevents text-mapping drift and avoids doubling input token volume, operational latency, and API costs.

#### Q6 — Endorsement pass: Shape and default
* **Ruling:** **(ii) OFF by default, opt-in via `--endorse`.** *(Dissenting from Strawman (i))*
* **Rationale:** Running an endorsement pass on every revision run introduces substantial latency overhead. Given that applying the revision is always a human decision under D6, the feature's primary integrity is preserved without forcing a mandatory multi-seat consensus loop. The endorsement pass must be an explicit, optional opt-in.

#### Q7 — Failure posture when findings conflict
* **Ruling:** **(c) Apply non-conflicting edits; surface conflicts in `unresolved`.**
* **Rationale:** Graceful degradation is a core operational standard. If the board produces conflicting recommendations, the revision seat should resolve what it can and log conflicts in `unresolved` rather than failing the run or choosing a side silently. It should not affect the final exit code.

#### Q8 — Redline artifacts: Exactly what does P3 render?
* **Ruling:** **Ship as specified by the strawman.**
* **Rationale:** Outputting clean draft files alongside unified `.patch` files (via standard `difflib`) and word-level HTML rendering is clean and idiomatic. Non-standard markdown formats (like CriticMarkup) add unnecessary rendering and parsing complexity.

---

### 4. Recommended Execution Sequence
1. **Phase 1 (CLI & Configuration):** Add parsing and validation for `--output revised-draft` and `--source-type`.
2. **Phase 2 (Draft Generation):** Build single-spawn prompts, fence parsers, and validation rules for `changes.json`.
3. **Phase 3 (Diff Engine):** Wire `difflib` to generate unified patches for code and inline word-level HTML renders for prose.
4. **Phase 4 (Endorsement Pass):** Add the optional, concurrent endorsement step, recording responses in `changes.json`.

---

### 5. Invariants and Guardrails
* **D5/D6 Compliance:** Source files must never be modified by the CLI. The revision remains an opt-in artifact.
* **Fail-Safe Exit:** Revision/endorsement failures must never discard successful round reviews or delete valid synthesized `verdict.json` files.
* **Egress Bounds:** Operation must utilize existing egress consent hashes; no new external data categories may be introduced.

---

### 6. Risks, Stale Assumptions, & Missing Evidence
* **Complex Mapping Failure:** Models struggle to reliably map multi-point edits back to a structured JSON schema when edits cross-cut files. We need high-complexity integration test fixtures to ensure JSON-to-text formatting doesn't truncate.
* **Target Workspace State:** Developers may modify local files between running a review and applying a patch, causing standard patch tools to fail.

---

### 7. Other Seats to Challenge
* **The Claude Seat:** Challenge whether full-file rewrites in single-spawns lead to high truncation rates, and if line-by-line patch instructions should be returned instead.
* **The Codex/Gemini Seats:** Challenge whether title-based matching in `changes.json` is robust enough for downstream CI systems.

VERDICT: caution

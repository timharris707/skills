# Board packet — round 2 (cross-reading: summaries — structured digest)

## Where the board stands after round 1

Verdicts: claude=caution · codex=caution · gemini=caution
Agreement: unanimous: caution
Shared evidence (raised by ≥2 seats): `--no-endorse`, `--output`, `--source-type`, `.patch`, `<ins>/<del>`, `changes.json`, `revised-draft.*`, `revised-draft.md`, `verdict.json`

## By topic

### Verdict

- **claude:** **CAUTION — proceed only with the changes below.** Confidence: **high** (both fact-checks returned; every objection is code-backed with citations, not judgment calls). *What would flip it to SHIP:* adopt **Q2(a) file-only** (don't reopen …
- **gemini:** **Verdict: CAUTION** **Confidence: HIGH** *Change Factor:* This verdict would improve to **SHIP** if the latency-heavy sequential endorsement loop proposed in Q6 is optimized to be off-by-default or parallelized to avoid stalling the main …

### Strongest objections

- **claude:** 1. **Silent truncation ships a corrupted "board-endorsed" copy (Q5).** The single highest-severity failure. Mitigation is the diff-reconciliation invariant + size preflight; without them the feature's flagship artifact can be a …
- **gemini:** * **The Sequential Endorsement Bottleneck (Q6):** Spawning additional review runs sequentially across all non-revision seats adds immense execution latency (up to 40-60% longer runs in a standard 3-seat board). This is highly disruptive to …

### Recommended execution sequence

- **claude:** Fold these into the roadmap's D9+ / Phase 2–4 gating: 1. **Pre-work (blocking):** decide Q2 (recommend file-only) and reconcile the `caveats`→`dissent` naming; both change the `changes@1` schema before a line is written. 2. **Phase 2a — …
- **gemini:** 1. **Phase 1 (CLI & Configuration):** Add parsing and validation for `--output revised-draft` and `--source-type`. 2. **Phase 2 (Draft Generation):** Build single-spawn prompts, fence parsers, and validation rules for `changes.json`. 3. …

### Invariants & guardrails

- **claude:** - **INV-1 (integrity spine):** `changes.json.edits[]` must reconcile 1:1-or-better with the mechanical `original→revised` diff. Every diff hunk ↔ ≥1 edit; every locator ⊂ a hunk. Reconciliation failure ⇒ reject path (retry, then …
- **gemini:** * **D5/D6 Compliance:** Source files must never be modified by the CLI. The revision remains an opt-in artifact. * **Fail-Safe Exit:** Revision/endorsement failures must never discard successful round reviews or delete valid synthesized …

### Risks, stale assumptions & missing evidence

- **claude:** - **Stale/incorrect assumption — `caveats[]`:** the brief's product-context and Q3 name a container that isn't in the schema. Confirm against `board_verdict.py:45` before schema work; likely narrows `resolves` scope to blockers+concerns. - …
- **gemini:** * **Complex Mapping Failure:** Models struggle to reliably map multi-point edits back to a structured JSON schema when edits cross-cut files. We need high-complexity integration test fixtures to ensure JSON-to-text formatting doesn't …

### Concrete evidence

- **claude:** - Container error: `scripts/board_verdict.py:45` — `EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")`; no `caveats[]` list; `amend` joins blocker/concern only (`_finding_titles()` `:525-532`). - Title non-uniqueness: …

### Challenges to the board

- **claude:** - **To the pragmatist/product seat:** is Q2(b)'s "provenance from `verdict.json` alone" a real user need, or am I over-weighting write-once purity? If a concrete sharing workflow needs it, my (a) recommendation weakens. - **To whoever owns …
- **gemini:** * **The Claude Seat:** Challenge whether full-file rewrites in single-spawns lead to high truncation rates, and if line-by-line patch instructions should be returned instead. * **The Codex/Gemini Seats:** Challenge whether title-based …

### codex — review (no section headers found; head excerpt)

**Verdict** Caution, high confidence. I would move to ship if Q1/Q3/Q8 are tightened: stable edit identity, diff-hunk anchoring, no metadata header inside the clean revised draft, and explicit endorsement semantics. **Q Rulings** Q1: CAUTION. Do not key only by exact title. Titles are usable for `amend` because a human is in the loop, but `changes.json` is machine provenance. Use conductor-assigned optional finding ids now, or at minimum `{list, index, title}` with duplicate-title detection. Q2: SHIP with guardrails. File plus `verdict.json.changes` pointer is right, but write it atomically with the same lost-update discipline as `amend`, and include a non-circular verdict pin in `changes.json`, such as …

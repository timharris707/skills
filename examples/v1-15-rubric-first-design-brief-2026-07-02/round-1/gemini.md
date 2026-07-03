# Advisory Board Design Review: v1.15 "Rubric-First Deliberation"

## Rulings on Q1–Q9

### Q1 — Pipeline shape: what exactly does `--rubric` insert?
**RULING: CAUTION**
* **Rationale**: The proposal fan-out and sequential chair-merge pipeline is democratically robust, preventing single-seat dominance while strictly adhering to the §11 "models reason, conductor plumbs" mandate. However, adding two sequential LLM steps before opinion rounds double the pre-deliberation latency. To mitigate this severe operational/latency penalty in repetitive or time-sensitive user workflows, we must support a short-circuit bypass flag, `--rubric-file <path>`, allowing users to provide pre-defined criteria directly. When the dynamic pipeline is used, the proposed preflight floor of $\ge 2$ usable proposals is an essential guardrail to prevent single-seat monopoly.

### Q2 — The chair: who is it, and how is it chosen?
**RULING: SHIP**
* **Rationale**: Reusing the synthesizer-selection rules verbatim via `--chair-seat` (defaulting to Claude if seated, else first usable) is highly idiomatic and avoids egress disclosure boundaries since it re-spawns an approved provider. Crucially, treating scoring under the rubric itself as the acceptance act—while capturing objections asynchronously via a `RUBRIC-NOTE:` reply line—avoids a third sequential setup round (like an endorse check), which would otherwise introduce prohibitive latency.

### Q3 — Scores and the VERDICT token: replace, coexist, or derive?
**RULING: SHIP**
* **Rationale**: Coexistence of per-criterion scores with the canonical `VERDICT: ship|caution|block` token is the only operationally viable path. It maintains backward compatibility with the existing gate, convergence, and renderer architectures without duplicating or branching the codebase. The 1–5 integer scale perfectly embodies our "coarse over precise" design philosophy, and conductor-assigned IDs (`c1`–`cN`) protect against the model-minted identity collision bugs previously seen in the revision-seat findings.

### Q4 — How do scores map to ship/caution/block?
**RULING: CAUTION**
* **Rationale**: While we agree that gameable numbers must not move a gate directly (upholding the `confidence` precedent), leaving severe contradictions (e.g., a seat scoring all criteria 1/5 but declaring a `ship` token) purely as a rendered warning is a major user-workflow risk. We should map severe score-to-token contradictions—where a seat's computed score band and its declared token are in direct opposition—to the existing `ABSTAIN` gate outcome (exit 3). This forces a safe, human-in-the-loop review for self-contradictory seats without introducing arbitrary or gameable gate thresholds.

### Q5 — Schema: where does the scorecard live?
**RULING: SHIP**
* **Rationale**: Storing the scorecard in a separate `scorecard.json` artifact (schema `advisory-board/scorecard@1`) and linking to it via a tool-authored `{artifact, sha256}` pointer in `verdict.json` is a robust, proven pattern that mirrors the successful `changes.json` design. Tracking scores per-round provides excellent observability of convergence trajectories, and housing the chair's drop-with-reason records inside the scorecard prevents file sprawl.

### Q6 — Convergence under `--rounds auto`
**RULING: SHIP**
* **Rationale**: Extending the existing binary `moved` check to trigger when any criterion score changes by $\ge 1$ is simple, robust, and avoids introducing complex epsilon mathematics. Bounding potential score oscillation with the existing `--max-rounds` ceiling is a strong, pre-calibrated backstop. Surfacing which criteria are still moving in the round-done status string dramatically improves real-time pipeline observability.

### Q7 — What exactly does `--rubric` opt into, and how does it compose?
**RULING: SHIP**
* **Rationale**: Keeping `--rubric` orthogonal to other flags keeps the CLI clean. Storing resolved template versions and shas in the recipe is vital for exact replayability (`--from-recipe`). For non-synthesized runs where `verdict.json` is not written, the scorecard is unpinned; we recommend writing the `scorecard.json` sha256 straight to `run-metadata` to protect the unpinned artifact from silent disk tampering.

### Q8 — The audience/stakeholder panel preset
**RULING: SHIP**
* **Rationale**: Implementing the stakeholder panel purely as a `LENS_PRESETS` prose-string bundle (`stakeholder-panel`) is highly pragmatic. It avoids the complexity of introducing a brand-new "board composition preset" axis, ships rapidly, and leverages the entire existing lens-aware plain-language rendering pipeline out of the box.

### Q9 — Failure and degrade posture
**RULING: SHIP**
* **Rationale**: The proposed failure postures are exceptionally robust. Refusing and stopping on a chair-merge failure is the correct choice; silent degradation to a non-rubric run violates explicit user intent, while saving `rubric-rejected.json` ensures clean observability. Resilient handling of missing scores (using "—" and marking totals partial) avoids discarding expensive, successful opinion rounds. Carrying the agreed rubric forward mechanically in `--revise` is a textbook application of §11 that preserves evaluation integrity across revisions.

---

## 1. Verdict & Confidence
* **Verdict**: `caution` (Proceed only with the changes/recommendations detailed above and below).
* **Confidence**: `high`.
* **Change Catalyst**: A production benchmark proving that the 2 sequential rounds of startup latency (proposal + chair merge) cannot be bypassed using cached/user-provided rubrics, or a demonstration that self-contradicting seats (extreme low scores but a "ship" token) do not trip the gating pipeline.

## 2. Strongest Objections
* **Pre-Round-1 Latency Penalty (Q1):** The proposed pipeline introduces two sequential LLM calls (Proposal Fan-Out and Chair Merge) *before* the first opinion round. In a fast-moving developer workflow, this doubling of startup latency is a significant penalty. We must allow users to short-circuit this by providing a pre-defined rubric file (e.g. via `--rubric-file <path>`).
* **Gate Blindness to Contradictory Seats (Q4):** If a seat scores every criterion 1/5 but declares `VERDICT: ship`, the gate should not silently pass. Such self-contradiction is a logical refutation of the seat's own basis. The gate must map extreme score-token discrepancies to the existing `ABSTAIN` (human-in-the-loop, exit 3) outcome.
* **Tampering Risk of Unpinned Scorecards (Q7):** When `--synthesize` is omitted, `scorecard.json` stands alone. To protect its integrity as an audit trail, its sha256 must be recorded in `run-metadata`.

## 3. Recommended Execution Sequence
1. **Phase 1: Schema & Validator Core:** Establish the `advisory-board/scorecard@1` schema and the strict validator `board_scorecard.py` (unknown keys refused, strict type checking, and integer weight-sum verification to exactly 100).
2. **Phase 2: Rubric Setup Module:** Implement `scripts/_conductor/rubric.py` matching the seven-part "spawn a seat" pattern. Wire the pre-round-1 proposal/merge loop inside `_run_after_activate()`'s guard.
3. **Phase 3: Scoring Reply Parser:** Update the round reply parser to extract `SCORE cX: N` lines. Handle missing/invalid scores resiliently by marking them partial in the scorecard without failing the run.
4. **Phase 4: Convergence & Echo Score Integration:** Update `convergence.py` to count score shifts $\ge 1$ as movement. Update `status.py` to add the `"rubric"` stage and track active moving criteria.
5. **Phase 5: Gate & Renderers:** Update `board_verdict.py`'s gate logic to check for extreme score/verdict contradictions and trigger `ABSTAIN` when detected. Update HTML/markdown renderers to whole-drop the scorecard section to zero body bytes when `--rubric` is absent (preserving the D5 byte-identity invariant).

## 4. Invariants and Guardrails
* **D5 Body Byte-Identity:** The rendered body of `final-consensus.html`/`.md` must remain byte-identical for non-rubric runs. Rubric HTML blocks must drop to exactly zero bytes when empty (`scripts/render_handoff.py:45-50`).
* **§11 Separation of Concerns:** Conductor code must never perform semantic merging or reasoning (this is the spawned chair's job). Conversely, the chair must never be trusted to compute weights arithmetic or assign ID schemas; the conductor must assert weight sums of exactly 100% and map proposed criteria to strict `c1`–`cN` indices.
* **Egress & Disclosure Sanity:** The chair seat must be selected from existing board seats to ensure it stays within the run's egress consent boundaries.

## 5. Risks, Stale Assumptions, and Missing Evidence
* **Stale Assumption in the Brief:** The design brief claims "the changes is reserved for the revision artifact... and not yet defined." In reality, `changes` is fully implemented and validated in `board_verdict.py:189-216`. Our proposed `scorecard` pointer must mirror this *active* precedent, not the outdated "reserved" concept.
* **Validator Membership Crashes:** Many membership (`in`) checks in `board_verdict.py` still lack `isinstance` guards, risking raw `TypeError` crashes on hand-authored unhashable inputs. The new `board_scorecard.py` validator must strictly enforce type guards.
* **Oscillation in Auto Rounds:** Under `--rounds auto`, seats might flap criteria scores between rounds (e.g. alternating $3 \leftrightarrow 4$). Bounding this via `DEFAULT_MAX_ROUNDS` protects execution but can still result in higher-than-expected token consumption; we need clear metrics tracking score-induced round count expansions.

## 6. Concrete Evidence from Source
* **Rounds Hook Point:** `scripts/_conductor/cli.py:435-437` shows round-1 starting immediately after setup. The pre-round-1 rubric loop must hook inside `_run_after_activate`'s `try` guard (cli.py:421) to benefit from the abnormal-exit safety net.
* **The Seat Spawning Precedent:** `scripts/_conductor/endorsement.py:12-17` documents the generalized 7-part seat spawning architecture, which `rubric.py` must replicate for the proposal and chair-merge passes.
* **The Lens-aware Human Label Precedent:** `scripts/_verdict_labels.py` shows how non-software lenses map machine tokens (`ship|caution|block`) to human-friendly text like "Go ahead" or "Proceed with care". The scorecard renderer must leverage this same lens-aware labeling.

## 7. Seat Challenges (What to ask other seats)
* **To the Claude/Synthesizer Seat:** "Can you guarantee that the chair prompt shape reliably deduplicates and drops criteria while maintaining a strict JSON format with explicit drop-reasons, without introducing hallucinated criteria IDs?"
* **To the Codex/Software-Architecture Seat:** "How should we handle criteria weighting when seats propose conflicting weights (e.g., security-oriented seats weighting a safety criterion at 50% while product-oriented seats weight it at 10%)? Does the chair's merge formula reliably balance these perspectives?"

VERDICT: caution

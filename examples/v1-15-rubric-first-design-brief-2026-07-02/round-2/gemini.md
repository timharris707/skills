### 1. Updated Verdict
- **Verdict**: `CAUTION`
- **Confidence**: `high`
- **What would change it**: I would move to `SHIP` if we explicitly mandate conductor-minted proposal IDs for structural completeness checks, enforce unique seat-ID selection for the chair, and provide a programmatic `--rubric-file <path>` option to bypass pre-round LLM latency.

---

### 2. Changed My Mind & Still Dissent
- **Where I CHANGED MY MIND (aligning with Claude and Codex)**:
  - **With Claude on Q1 (Completeness & Partition Integrity)**: I previously accepted the strawman's unmechanized completeness check. Claude's objection regarding §11 is absolutely correct: without structural constraints, we are blindly trusting the chair's reasoning to not drop ideas or hallucinate criteria. I now agree that the conductor must assign sequential unique proposal IDs (e.g., `p1_seat_id`) during the proposal pass, and require the chair seat's JSON merge output to explicitly partition *every single* proposal ID into a `subsumed` or `dropped` array. The conductor must validate this partition structurally, refusing empty subsumptions or untraced criteria.
  - **With Codex on Q2 (Chair Selection on Unique-ID Axis)**: I previously accepted the synthesizer-style seat lookup. Codex's point that a name-collapsible lookup fails on duplicate-provider boards (e.g., two `claude` seats with different focuses) is a severe regression. The `--chair-seat` selection must resolve against unique seat IDs (e.g., `claude#2`), following `choose_revision_seat`'s robust `by_id` dictionary check.
  - **With Codex on Q1/Q5 (Independent Pre-Round `rubric.json`)**: I now support writing an intermediate `rubric.json` artifact of record immediately after the chair merge step. This decouples rubric definition from execution, allows the rubric state to be audited before the opinion rounds start, and supports resuming from crash/interruption.

- **Where I STILL DISSENT**:
  - **With Claude on Execution Sequence**: Claude proposes writing M5's phases so the parser/proposal validation lands *first* (Phase 2a/2b) and schema validation core (Phase 1) is deferred. I still assert that **Phase 1 must be the Schema & Validator Core** (`board_scorecard.py` and `advisory-board/scorecard@1` validation). Establishing the rigid, validated target contracts for artifacts up-front acts as a regression-guard and prevents "contract drift" during speculative prompt/pipeline engineering.
  - **With the Strawman on Q4 (Gate Integration of Score-Token Contradictions)**: The strawman suggests leaving score-token contradictions purely as a rendered warning (Q4(a)). I dissent: while we must not gate on gameable scores themselves, we must treat severe seat self-contradictions (e.g., top-third weighted score with a `block` token, or bottom-third with `ship`) as a structural anomaly that trips the gate's `ABSTAIN` (exit code 3) path in `--strict` mode. Ignoring this degrades the gate's integrity.
  - **With the Strawman on Q1's Pre-Round Latency**: A two-step sequential LLM pass (Proposal + Chair Merge) before Round 1 begins creates a significant 10–20 second developer-experience bottleneck. To mitigate this, we should support `--rubric-file <path>` as a direct option, allowing developers to supply their own static criteria and completely bypass the pre-round LLM proposal and chair-merge latency.

---

### 3. Strongest Remaining Objections
1. **The §11 "Conductor Plumbs, Models Reason" Boundary Violation in Q1/Q3**: The design must strictly prevent models from inventing numeric parameters or structural definitions. The models propose prose and drop reasons, but the conductor must compute IDs, apply weights arithmetic, and check completeness.
2. **Name-Collapsing Seat Selection in Synthesizer vs. Chair (Q2)**: If we reuse synthesizer seat selection, a multi-model board with duplicate providers will break. We must enforce unique-ID resolution.
3. **The Unmitigated Pre-Round Latency Penalty**: A sequential LLM start-up block of two calls will hurt adoption. We must provide a programmatic `--rubric-file` escape hatch.
4. **Weak Gate integration of scorecard contradictions**: A seat that says "Excellent" (score 5/5) but votes "BLOCK" (or vice versa) is a serious pipeline contradiction. It must escalate to `ABSTAIN` (exit 3) rather than just rendering a silent warning.

---

### 4. Recommended Execution Sequence
1. **Phase 1: Schema & Validator Core**: Author `advisory-board/scorecard@1` and its strict validator `board_scorecard.py` (preventing unknown keys, enforcing that weights sum to exactly 100, and ensuring integer 1–5 scale boundaries).
2. **Phase 2: Proposal Parse & Conductor Partition Checking**: Implement proposal parsing and Claude's "merge partition" verification logic, using conductor-minted proposal IDs.
3. **Phase 3: Pre-Round-1 Pipeline Hooks & `rubric.json` Artifact**: Integrate the rubric proposal/merge loop into `_run_after_activate` (inside the `try` guard of `cli.py`), writing a standalone `rubric.json` post-merge.
4. **Phase 4: Scoring Rounds & Parser Upgrades**: Extend `rounds.py` and `parse_verdict` to parse per-criterion scores (`SCORE cN: [1-5]`) and `RUBRIC-NOTE cN:`.
5. **Phase 5: Gate Integration & Renderers**: Update `board_verdict.py`'s validator (verdict-to-scorecard pinning) and `render_handoff.py` (enforcing D5 byte-identity for non-rubric runs).

---

### 5. Invariants and Guardrails
- **D5 Body Byte-Identity**: The rendered body of `final-consensus.html`/`.md` must remain byte-identical down to zero bytes when `--rubric` is omitted (`scripts/render_handoff.py:45-50`).
- **Sum-to-100 Invariant**: The scorecard validator must strictly verify that the criteria weights are integers that sum to exactly 100.
- **Merge Partition Integrity**: The conductor must verify that the set of proposal IDs minted is partition-identical to the set of IDs listed in the chair's `subsumes` and `drops` outputs.
- **Seat Retries on Invalid Scores**: If a seat fails to output a valid score line (or repeats a score, or outputs an out-of-range integer) for any active criterion, the conductor must trigger the standard two-attempt retry before marking the cell as absent (`—`).

---

### 6. Risks, Stale Assumptions, and Missing Evidence
- **Stale Assumption on `changes`**: The design brief claimed `changes` is reserved for the revision artifact "and not yet defined in the gate validator". However, our reading of `board_verdict.py:180-225` shows that `changes` is *already fully implemented and strictly validated* inside `board_verdict.py`. We must mirror this exact `{artifact, sha256}` pointing style for `scorecard`.
- **Latency of Small Boards**: On a fast-tier, 3-seat board, a developer expects feedback in seconds. Adding proposal and chair-merge calls triples the turnaround time. A static rubric override is vital.
- **Scale Resolution Risk**: Standardizing 1-5 scale allows simple bounding, but we must protect against model drift where seats default to "3" (neutrality bias). We must explicitly define a 5-point rubric anchor prompt for the seats.

---

### 7. Concrete Evidence
- **`board_verdict.py:180-205`**: Shows that the `{artifact, sha256}` pointer style is already robustly established for `changes`.
- **`revision.py:266-285`**: Defines how `choose_revision_seat` performs unique seat-ID matching first, matching on `by_id = {s.id: s for s in config.board}` rather than collapsible provider names.
- **`cli.py:421-435`**: Confirms that `_run_after_activate` starts immediately after setup within the abort guard. The proposal and chair-merge loop must be hooked inside this function to ensure abort/interruption cleanup works.
- **`render_handoff.py:45-50`**: Enforces the strict "zero body bytes when its fields are empty" template-evolution invariant, which must be upheld for the scorecard html sections.

BASIS: evidence
VERDICT: caution

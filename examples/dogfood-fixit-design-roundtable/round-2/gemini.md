# Round 2 Board Review — Gemini (Product & Operations)

## 1. Updated Verdict
* **Verdict:** **CAUTION**
* **Confidence:** **HIGH**
* **What would change it:** Committing to an architecture that parallelizes the endorsement pass, assigns post-synthesis sequential string IDs to findings to act as robust join keys, and guarantees that the clean revised drafts contain no tool-authored metadata headers.

---

## 2. Changed Mind & Dissent

* **Where we CHANGED OUR MIND:**
  * **Q1 (Edit identity — Agreed with Codex):** We change our mind to support Codex's caution against **Q1(a) (pure exact-title matching)**. While human-driven `amend --on` uses titles, machine-driven revision provenance is too fragile under exact title matching. We propose a hybrid/refined solution: The conductor should assign sequential string IDs (e.g., `"blocker-1"`, `"concern-2"`) to blockers and concerns at merge time (post-synthesis). The revision seat then keys its `changes.json` to these IDs. This avoids a heavy `@3` schema evolution while delivering absolute machine precision.
  * **Q6 (Endorsement Pass Default — Agreed with Parallelization):** We change our mind regarding the default posture of the endorsement pass. To protect the integrity of a truly "board-endorsed" revision (solving the marketing risk R4), we agree it must be **ON by default, but executed in parallel, with a `--no-endorse` flag to opt-out**. In Round 1, we flagged the immense latency penalty of sequential spawns; parallelizing the spawns cuts this latency to a single round's duration, satisfying both speed and quality standards.

* **Where we STILL DISSENT:**
  * **Q2 (Pointer Location — Dissented from Claude):** We still dissent from Claude's push for **Q2(a) (file-only)** and maintain that **Q2(b) (file + pointer inside `verdict.json`) is correct**. Claude fears that reopening `verdict.json` violates the write-once feel and invites concurrency issues. However, the entire execution is a single-process pipeline. By holding the synthesized verdict in memory and writing `verdict.json` to disk *once* at the very end of the run (after synthesis, revision, and parallel endorsements are done), we completely avoid "reopening" a file while ensuring `verdict.json` remains a self-contained, cryptographically verifiable index of the run.

---

## 3. Strongest Remaining Objections

* **Silent Truncation and Lack of Structural Validation (Q5):** Full-file rewrites of large sources in a single spawn are prone to token limits. If the CLI silently writes a truncated file as "board-endorsed," it corrupts user work (R4). We must enforce **strict validation of closed fences**. Putting the JSON mapping *first* and the revised draft *second* ensures that if the draft is truncated, the missing closing fence is caught mechanically, failing the run safely.
* **Header Pollution in Clean Drafts (Q8):** Placing tool-authored metadata headers inside `revised-draft.md` or `revised-draft.<ext>` introduces unnecessary user friction when copy-pasting or applying the files. The clean drafts must be completely clean and immediately apply-able, leaving metadata to `changes.json` and the HTML handoff.
* **The Caveat Schema Inconsistency:** The brief and Q3 treat `caveats[]` as structured findings that can be resolved. As proven by the code, caveats are simple string arrays with no titles or evidence, making them un-resolvable. The revision step must strictly limit its focus to resolving `blockers` and `concerns`.

---

## 4. Recommended Execution Sequence

1. **Phase 1: Foundation & Pre-Work (Blocking)**
   - Update `board_verdict.py` and `_conductor/synthesizer.py` to assign standard sequential IDs (`blocker-1`, `concern-1`) to `blockers` and `concerns` post-synthesis.
   - Refine the validator to allow the `changes` key in `verdict.json` only when `--output revised-draft` is active.
2. **Phase 2: Revision Step (Single Spawn & Reconciliation)**
   - Implement `_run_revision_step()`.
   - Use a single spawn with a strict block order: [JSON Mapping First, Clean Revised Draft Second].
   - Build a parser that strictly validates closed fences for both blocks.
   - Implement Claude's INV-1 diff-reconciliation invariant (`difflib` over original vs revised must match the locator map 1:1).
3. **Phase 3: Parallel Endorsement Pass**
   - Spawn parallel non-revision seat reviews to collect endorsements in one concurrent step, appending results to `changes.json`.
4. **Phase 4: Rendering & Local Artifacts**
   - Implement line/word-level `<ins>/<del>` redline generation using `difflib.SequenceMatcher` for the HTML handoff.
   - Write clean, header-free `revised-draft` files and `.patch` diffs.

---

## 5. Invariants and Guardrails

* **Fenced-Block Integrity:** An unclosed data fence for either the JSON or the draft must trigger a parse rejection, preventing silent truncations.
* **INV-1 Reconciliation:** The mechanical diff must map 1:1 to the edit locators. Any discrepancy must reject the revision draft.
* **Size Preflight Barrier:** Set an upper limit on source file size (e.g., 800 lines or 4000 tokens) for revision generation. If exceeded, refuse revision with a clear error or warning, preventing guaranteed truncation.
* **Late-Write Pipeline:** Defer writing `verdict.json` to the filesystem until the entire pipeline is finalized, preventing file reopening.

---

## 6. Risks, Stale Assumptions, and Missing Evidence

* **Stale Assumption: Caveats as findings:** As proven by `scripts/board_verdict.py:45` and `references/verdict-schema.md`, `caveats` are simple lists of strings and not structured findings. They cannot be resolved or mapped.
* **Truncation Vulnerability:** Single-spawn execution for full-file generation on larger code files is highly risky. 
* **Concurrency Risk in Manual Amendments:** If a user runs `amend` after a revision is generated, the `changes` pointer in `verdict.json` must be preserved. We must ensure `amend`'s optimistic file locking does not strip the `changes` field.

---

## 7. Concrete Evidence

* **EVIDENCE_CONTAINERS error:** `scripts/board_verdict.py:45` and `scripts/verify_evidence.py:107` both define `EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")`. There is no `caveats` container.
* **Caveat array structure:** `references/verdict-schema.md` shows `"caveats": ["Reviewed the plan, not the code..."]`.
* **Finding Titles limited to blockers/concerns:** `scripts/board_verdict.py:527` uses `for key in ("blockers", "concerns")` to extract titles, confirming caveats are completely out of scope for matching.
* **Changes reservation error:** `scripts/board_verdict.py:142` checks `if "changes" in data: die(...)`, which confirms the reserved key is blocked.

VERDICT: caution

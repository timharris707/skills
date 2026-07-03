All three verification agents are back and they resolve my uncertain findings decisively. I have what I need — no further round-trips required. Here is my review.

---

# Claude seat review — v1.15 P2 rubric round + chair merge

**Role: architecture & systems — invariants, failure modes, adversarial review.** I verified the load-bearing claims against the actual codebase (three read-only agents over `egress.py`, `revision.py`, `synthesizer.py`, `constants.py`, `cli.py`, `status.py`, the tracker, and `EnvMixin`), so the findings below are grounded, not inferred from the diff alone.

## 1. Verdict

**CAUTION — proceed only with the egress and schema-hygiene fixes below.** Confidence: **high.**

The settled design (D15/D16/D18/D20) is faithfully and, in most places, impressively implemented: the mechanical partition reconciliation, the weight-sum invariant, conductor-owned id minting, the strict validator with `isinstance`-before-membership guards, the D16 by-id chair axis, the exit-code reuse, and the byte-identity of the no-flag path are all correct and verified. But the implementation deviates from the contract — and from its own CHANGELOG — in exactly the area this project treats as sacred: **egress consent.** Two consent-surface gaps plus a schema-id collision are enough to hold merge until fixed.

**One line on what would flip it:** if the team confirms the pre-round egress needs no disclosure mention *and* the missing approved-hash re-assertion is accepted as covered by source immutability (with the CHANGELOG corrected and `rubric-rejected.json` given its own schema id), this goes to **ship**.

## 2. Strongest objections

**① Undisclosed pre-round egress (concern — consent surface).** The `--rubric` pass egresses the **full source to every board seat before round 1**, but the disclosure the user approves is not updated to say so. Confirmed by inspection: `egress.disclosure_line()` contains no "rubric"/"proposal" mention. Yet the CHANGELOG asserts twice that *"the disclosure text gains a purpose mention only"* and *"no new consent category (the disclosure text gains a purpose mention only)."* No disclosure-rendering code is touched anywhere in the diff. So the PR under-delivers on its own stated design, on the one surface where "zero artifacts before egress approval" is the north star. Same bytes/same providers mitigates the *data* exposure, but the user consents to an egress whose pre-round rubric leg is never named.

**② The rubric fan-out skips the approved-hash re-assertion round-1 performs (concern — D15 "same egress discipline").** The diff's own step-4 comment states round-1 *"re-asserts the egress hash one last time, then feeds each seat its approved blob verbatim (so the bytes that actually leave equal what consent was bound to)."* The rubric path does not: `run_rubric_proposal` (rubric.py) re-renders `config.source.text` into a fresh prompt, wraps `PacketBlob(...)`, and computes `packet_hash([blob])` **for its own record** — it never compares the embedded source against the run's approved content hash. Agent-confirmed. Today `config.source.text` is immutable in-process so exploitability is low, but this is precisely the defense-in-depth round-1 bothers to do, and D15 says the proposal fan-out must run under the *"same packet-hash/egress discipline."* A future refactor (lazy/streamed source, a repo-grounding snapshot) could silently egress drifted bytes through the rubric leg while round-1 still catches it.

**③ `rubric-rejected.json` reuses the accepted schema id (concern — schema hygiene).** `_refuse_rubric` writes `{"schema": "advisory-board/rubric@1", "rejected": true, ...}` — the **same** schema string as a valid rubric.json, but a shape `board_rubric.validate()` would reject (unknown key `rejected`, missing `criteria`/`proposals`). Any consumer that dispatches on `schema == "advisory-board/rubric@1"` and then trusts the shape breaks on the refusal record. P4 wires a verdict pointer at this artifact family — give the refusal its own id (`advisory-board/rubric-rejected@1`) before that lands.

**④ The retry posture is documented two contradictory ways (concern — binding-decision accuracy).** The module docstring and CHANGELOG say a weight-sum/partition discrepancy is *"retryable once, then the refusal path"* (D15/D18). The code does **not** retry mechanical rejects — `build_rubric` (reconcile + weight-sum) runs *after* the two-attempt loop; only parse-level `invalid` retries. This is actually **correct house style** — I verified `revision.py` does exactly the same (mechanical `reconcile`/`build_changes` sits after the loop at lines 1007–1021, with the identical *"the mechanical checks are NOT retryable"* comment at 997–998). So the **code is right and consistent**; the **module docstring and CHANGELOG are wrong** to call mechanical discrepancies retryable. Fix the prose to: parse failures retry once; a well-formed-but-mechanically-invalid merge is a single-shot reject. (This is also a genuine design fork worth a seat vote — see §7.)

**⑤ The feature's central happy path is untested (concern — tests).** Every end-to-end rubric test uses the default mock that folds **all** proposals into **one** criterion at weight 100 with **nothing dropped**. No test drives a realistic **multi-criterion merge with a non-empty `dropped[]`** through the real `run_rubric_chair → build_rubric → reconcile_partition`. The `two_criteria` chair mock built for exactly this is **dead — no test references it**, and `build_rubric`'s dropped-provenance assembly (`seat_of.get`, `title_of.get`) is never exercised. The multi-criterion+dropped shape is only ever fed to the *validator* via the `_rubric_doc()` fixture, never *produced by the conductor*. The tests pin the invariants (§4 lens) well in isolation, but the integration they most need to cover is the one they skip.

## 3. Recommended execution sequence

1. **Egress first (①②).** Add the rubric purpose mention to `disclosure_line()`; add an approved-content-hash re-assertion to the rubric fan-out mirroring round-1. Re-run the consent/egress tests; add one asserting the disclosure names the rubric leg when `--rubric`.
2. **Schema id (③).** Mint `advisory-board/rubric-rejected@1` for the refusal record; leave `rubric.json` on `@1`.
3. **Reconcile the retry docs (④).** Correct the module docstring + CHANGELOG to match the code (and `run_rubric_chair`'s already-correct local docstring). Optionally pin it: assert `attempts == 1` for a `bad_weight`/`bad_partition`/`phantom` chair, the way `missing_fence` pins `attempts: 2`.
4. **Cover the real merge (⑤).** Wire the `two_criteria` mock into an E2E that yields ≥2 criteria + a dropped proposal with a reason; assert the written `rubric.json` partitions correctly and validates.
5. **Nits (§5).** Rename/repair `test_estimator_default_has_no_rubric_key`; symmetric env cleanup.

Then merge.

## 4. Invariants and guardrails (must hold)

- **Consent precedes every egress, and the disclosure names every egress purpose.** The rubric leg is a new egress *event* (N seats, pre-round) even at the same byte/provider category — the consent UX must reflect it, and each egress packet must re-assert the approved content hash (round-1 parity).
- **§11 conductor-owns-structure.** Ids, criterion ids, the partition, and the arithmetic are conductor-computed; the model authors prose only; every structural claim is mechanically re-checked before `rubric.json` is written. *Verified intact* — and notably injection-resistant: the chair never sees the raw source (only the neutralized, conductor-minted proposal table), and subsumes/dropped ids are cross-checked against ground truth, so a poisoned source cannot smuggle a phantom id the conductor honors.
- **Weight-sum = 100 integer partition, reject-on-violation, checked twice** (build + standalone validator). *Verified* (bool rejected as int subclass; `!= 100` refuses).
- **Byte-identity of the no-flag path.** *Verified* across recipe/run-card/artifact-tree/status. The estimator's rendered output is byte-identical (gated on `est.get("rubric")`); the extra in-memory `"rubric": False` key never reaches a persisted artifact (est dict is stdout-only). Keep it that way — if any future code serializes the est dict, gate the key.
- **Schema id ↔ conformant shape is 1:1.** A document tagged `advisory-board/rubric@1` must pass `board_rubric.validate`. (Currently violated by the refusal record.)

## 5. Risks, stale assumptions, missing evidence

- **Stale assumption:** "same source, same providers ⇒ no disclosure needed." The PR's own CHANGELOG contradicts it (it intended a purpose mention). Resolve the policy, then make code match.
- **Stale assumption:** "source is immutable between consent and rubric spawn." True today; the missing re-assertion makes it a latent trap under any future lazy/snapshot source.
- **Missing evidence:** no test proves the conductor can produce the partitioned, multi-criterion, some-dropped rubric the feature exists to produce (§2⑤).
- **Untested named invariant:** D5/R5 "status events" byte-identity has no guard (only `"rubric" in STAGES` is asserted). *Safe by construction* — the HTML/status renderer is event-driven and does not enumerate `STAGES`, so a non-rubric run emits no rubric event — but the named invariant rides on that implementation detail with no test fencing it.
- **Robustness (contract-specified, flag anyway):** `choose_chair_seat` defaults to claude-if-seated **regardless of whether claude's own proposal was usable**. On a claude-seated board where claude is the flaky seat, a run with 2 usable *non-claude* proposals still routes the chair to the failing claude and can refuse — a salvageable run lost. Matches the contract's stated default order, but the default may be worth revisiting.
- **Low-severity:** `run_rubric_chair` uses 2-level timeout precedence (caller-compensated) vs. `run_rubric_proposal`'s 3-level — a future direct caller passing `timeout=None` would skip the seat's `--timeout`. Estimator prices the chair on `models[0]`, not the claude-if-seated projection the comment claims to match (estimate-only, never gates). A zero-weight merged criterion is legal (neither dropped-with-reason nor scoring-relevant) — a small semantic hole.

## 6. Concrete evidence

- **CHANGELOG overclaim (①):** `CHANGELOG.md` (diff) — *"no new consent category (the disclosure text gains a purpose mention only)."* No disclosure code appears anywhere in the diff; `egress.disclosure_line()` has no rubric mention (verified).
- **Round-1 re-asserts, rubric doesn't (②):** `cli.py` `_run_after_activate` step-4 comment (diff): *"run_round re-asserts the egress hash one last time, then feeds each seat its approved blob verbatim."* vs. `rubric.py` `run_rubric_proposal`: `blob = PacketBlob(... text=prompt); pkt_hash = packet_hash([blob])` — no comparison to the approved hash.
- **Schema collision (③):** `cli.py` `_refuse_rubric`: `"schema": "advisory-board/rubric@1", "rejected": True` — vs. `board_rubric.TOP_LEVEL_REQUIRED` requiring `criteria`/`proposals` and refusing unknown keys.
- **Retry contradiction (④):** `rubric.py` module docstring — *"Any discrepancy → the reply is invalid (retryable once, then the refusal path)"* — vs. `run_rubric_chair` local docstring — *"A well-formed reply that fails a mechanical check is a genuine reject (NOT retryable)"* — and the code (`build_rubric` outside the `for attempt in (1, 2)` loop). Confirmed to mirror `revision.py:997-1021`.
- **Dead mock / coverage gap (⑤):** `tests/mocks/claude` defines `two_criteria)`; no occurrence of `two_criteria` in `test_run_board.py`. `TestRubricBuildWeightSum.test_weight_sum_100_passes` builds a single-criterion rubric; the E2E uses default `ok` mode.
- **Verified-correct:** `EXIT_PREFLIGHT_NOGO = 1`, `EXIT_NO_VERDICT = 4` (constants.py:52-59) → exit-code reuse is right. `_run_after_activate` is inside the `try/finally` that calls `tracker.finish_if_unfinished(OUTCOME_INTERRUPTED, ...)` (cli.py:425-436), so a rubric-pass abort still stamps terminal. `EnvMixin.tearDown` does `os.environ.clear(); os.environ.update(self._env)` (test:94-95) → the asymmetric `MOCK_GEMINI_MODE` in `test_proposal_floor_refuses_before_rounds` cannot leak.

## 7. What I'd ask the other seats to challenge

- **Codex (systems/egress):** Is a pre-round full-source egress genuinely covered by the existing run disclosure, or must `disclosure_line()` name it? This is a consent-policy call, not a code call — I want a second opinion before we treat ①/② as blocking vs. cosmetic.
- **gpt-5.5 (adversarial):** Challenge the retry fork head-on. D15 says "reject+retry"; the code single-shots mechanical rejects (matching revision). A fresh stochastic chair spawn *could* fix a bad partition — is one retry the more resilient reading of D15, or is "a coherent-but-wrong partition is a genuine reject, don't burn a second spawn" correct? Whichever wins, the docs must say it.
- **Any seat:** Should `claude`-if-seated remain the chair default when claude's own proposal failed, given it can turn a salvageable 2-usable-proposal run into a refusal? And should a zero-weight merged criterion be legal?

Bottom line: the engine is sound and the mechanical core is genuinely well-built — this is a caution about consent-surface fidelity and schema hygiene, not about the design. Fix the two egress items and the schema id, correct the retry docs, cover the real merge, and it ships.

VERDICT: caution

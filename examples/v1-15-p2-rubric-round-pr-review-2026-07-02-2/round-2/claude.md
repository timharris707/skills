All three verifications are in, and I read `cli.py` directly to resolve the key discrepancy. The critical finding: **the frozen diff I was handed no longer matches the live working tree.** The live tree (uncommitted `MM cli.py`) already contains an egress re-assertion at `cli.py:682` and a chair-aware estimator — fixes that the frozen diff lacks and that directly answer codex's round-1 block. Codex was right about the diff; the tree has since moved. That divergence is itself a first-class finding. Here is my round-2 review.

---

# Round 2 — Claude seat (Architecture & systems)

## 1. Updated verdict

**CAUTION — proceed only with the changes below. Confidence: high.**

One line to change it: **→ ship** once the disclosure/CHANGELOG mismatch (D3) and the chair-retry contradiction (D5) are resolved *and* the live-tree egress re-assertion (`cli.py:682`) is confirmed part of what commits; **→ block** if that re-assertion is dropped and the code reverts to the frozen diff's egress gap.

I verified the decisive claims against the real code rather than deferring: I read `cli.py:445–717` myself and ran three independent checks (egress binding, chair retry, byte-identity/correctness).

## 2. Where I changed my mind / where I still dissent

- **I did NOT adopt codex's BLOCK, and I raise my own confidence — on my own evidence.** Codex's blocker ("rubric proposal prompts are spawned outside the approved packet hash") is **valid against the frozen diff** — the diff's `_run_rubric_step(config, *, tracker=None, _write=None)` (call site `_run_rubric_step(config, tracker=tracker, _write=_write)`) has no hash re-assertion. But the **live working tree already fixes it**: `cli.py:651` is now `_run_rubric_step(config, blobs, approval, ...)` and `cli.py:682–684` runs `if packet_hash(blobs) != approval.content_hash: die(..., EXIT_EGRESS_BLOCKED)` — the exact hard-stop `run_round` uses (`cli.py:469–470`). That gives the rubric pass **parity** with round-1's egress discipline. So "do not proceed" now overstates a substantially-resolved issue. This is not deference — I read the fix and it closes the asymmetry codex named.

- **I STILL DISSENT from codex (block) on two exact points.** (a) The egress asymmetry is closed by `cli.py:682`; block is no longer warranted. (b) Codex's "chair mechanical-invalid replies must retry once before refusal" is a legitimate concern (I corroborate it below), but the *current* behavior — refuse on first mechanical failure — satisfies the overriding contract rule "never a shipped bad rubric" (D15). Failing safe doesn't reach block.

- **I HOLD my round-1 CAUTION and my objection ① (undisclosed egress).** It survives even the live tree: `egress.disclosure_line()` (egress.py:248–278) still names round-1, grounding, revision, ask — **never the rubric pass** — while the CHANGELOG claims "the disclosure text gains a purpose mention." That claim is false against both the diff and the tree.

## 3. Strongest remaining objections

**D3 — Disclosure text never names the rubric egress; CHANGELOG overclaims it did (concern, stands in the live tree).** `disclosure_line()` has no rubric branch. *Failure scenario:* a privacy-sensitive user approves a `--rubric` run believing egress = the round-1 packet; in fact the source egresses as **N additional proposal spawns + 1 chair spawn** to the same providers — real egress *events* the consent surface never enumerates. Same bytes, same providers, but the consent UX under-represents the count and purpose. Fix: add the purpose mention to `disclosure_line()` (make code match the CHANGELOG), or correct the CHANGELOG.

**D5 — Chair mechanical-check failures do not retry, but three docs + the CHANGELOG say they do (concern, stands in both).** In `rubric.py`, `run_rubric_chair`'s `for attempt in (1,2)` loop `break`s on a *clean parse*; `build_rubric`/`reconcile_partition`/`validate_rubric` run **after** the loop, so a weight-sum≠100 or partition miss refuses on the first occurrence. Yet the module docstring ("Any discrepancy → … retryable once, then the refusal path"), `build_rubric`'s own inline comment ("refused (retryable once, then the refusal path)"), and the CHANGELOG all promise a retry — while `run_rubric_chair`'s docstring correctly says "NOT retryable." *Failure scenario:* a seat slips a `weight:99` on attempt 1 (exactly the transient prompt-following miss D15's "prompt unreliability degrades to reject+retry" anticipates); the run refuses (exit 1) and discards the already-paid-for proposal fan-out, when a cheap retry would likely have succeeded. Compounding: **no test pins the retry** — the `bad_weight`/`bad_partition`/`phantom` mocks emit identical failing output on both attempts, so a retry is behaviorally invisible; only the parse-failure test (`missing_fence`) asserts `attempts == 2`. Fix: decide the policy, make code + all three docstrings + CHANGELOG agree, and add a fail-once-then-succeed chair mock so a test can prove it. (My recommendation: actually retry once — it matches D15's stated intent and is nearly free.)

**D4 — The egress fix pins the source, not the rubric's exact outbound bytes (concern / optional hardening).** `cli.py:682` re-asserts `packet_hash(blobs)` — the **round-1** packet — as a proxy: the rubric prompt's only sensitive input is `config.source.text`, which the round-1 packet embeds, so pinning that pins the source. Defensible, because the rubric prompt = `static sha-recorded template` + `neutralize(source)` (deterministic). But the exact rubric bytes are pinned only *transitively*, and the template-sha lives in the recipe, not the egress gate. *Failure scenario:* a future edit to `build_rubric_proposal_prompt` that splices in any non-source content egresses it without tripping the gate. The strict form of codex's ask — prebuild the proposal + chair `PacketBlob`s, list them in the manifest, fold them into the approved hash — makes the "consent binds exact outbound bytes" property direct instead of transitive. Not blocking; worth doing.

## 4. Recommended execution sequence

1. **Confirm the live-tree egress re-assertion (`cli.py:682`) is in the commit that ships.** This is the load-bearing fix. If it is dropped, everything below is moot and the verdict is block.
2. **D3 — disclosure parity.** Add a rubric purpose-mention to `disclosure_line()`; add a test asserting a `--rubric` disclosure names the pre-round pass. Reconcile the CHANGELOG to the code either way.
3. **D5 — retry policy + doc coherence.** Move the mechanical checks inside the retry loop (retry once on `RubricRejected`), classify it `_INVALID` on attempt 1; make the module docstring, `build_rubric` comment, `run_rubric_chair` docstring, and CHANGELOG say one thing; add a fail-once-then-succeed `MOCK_*_CHAIR_MODE` and a test asserting `attempts == 2` then success.
4. **D4 — optional hardening.** Prebuild rubric blobs into the manifest + approved hash for direct byte-binding; otherwise document explicitly why source-pinning is sufficient.
5. **Re-freeze the diff.** Re-run the suite and regenerate the review artifact from the *current* tree so reviewers sign off on the bytes that ship (see D1 below).

## 5. Invariants and guardrails

- **Every egress runs inside the approved-hash hard-stop.** The rubric pass must re-assert `approval.content_hash` before it spawns — now satisfied at `cli.py:682`, at parity with `run_round`. Guardrail: a test that fails the run with `EXIT_EGRESS_BLOCKED` if the approved packet is mutated before the rubric spawn (mirroring the round-1 drift test).
- **The disclosure enumerates every egress purpose,** even when bytes/providers are unchanged. A new egress *event* is a disclosure event.
- **Prompt unreliability degrades to reject+retry, never a shipped bad rubric (D15).** The "reject" half holds; the "retry" half is the D5 gap.
- **Conductor owns identity + arithmetic (§11).** Verified intact: `mint_proposals` is the sole id source; `reconcile_partition` + the sum-to-100 check are mechanical and re-checked in `board_rubric.py`; the model authors prose only. This is the strongest part of the change.
- **Injection containment.** `neutralize_rubric_markers` scrubs all eight markers from spliced source *and* proposal titles/descriptions (`_proposals_table`), and `_extract_fenced` rejects extracted content containing reply markers — a poisoned source or poisoned prior proposal can't forge a fence or smuggle a fake partition. Verified solid; keep it.

## 6. Risks, stale assumptions, missing evidence

- **D1 — the artifact under review is stale (process risk).** The frozen diff ≠ the live tree: the tree already carries the egress re-assertion (`cli.py:465/651/673–694`) *and* a `chair_model`-aware estimator (agent C found `estimate_run(..., chair_model=...)` synchronized via `choose_chair_seat` at the preflight), whereas the frozen diff prices the chair on `models[0]` — a real projection mismatch with the run-card's claude-if-seated. **A reviewer approving the frozen diff is not approving the code that ships.** Resolve by re-freezing before merge.
- **Stale assumption: "same source, same providers ⇒ no disclosure needed."** The change's own CHANGELOG contradicts it (it intended a purpose mention). Pick the policy; make code and CHANGELOG agree.
- **Missing evidence: the retry claim is untested.** The 58 new tests pin the invariants well (partition phantom/double-claim/missing/empty, weight-sum≠100, bool/float/unhashable weight, dense-id sequences, byte-identity, chair-seat id axis) — but the "retryable once" mechanical-failure path is asserted nowhere and is unfalsifiable with the current mocks. Suite-green does not prove that behavior.
- **Not a gap (correct by design):** verdict pointers, round-prompt injection, scoring, renders are P3/P4. Their absence is right.

## 7. Concrete evidence

- **Live-tree egress fix (resolves codex's block):** `cli.py:651` `def _run_rubric_step(config, blobs, approval, *, tracker=None, _write=None)`; `cli.py:682–684` `if packet_hash(blobs) != approval.content_hash: die("egress hash drift: … refusing to spawn the rubric pass", EXIT_EGRESS_BLOCKED)`; `cli.py:685–694` also re-hashes the grounding snapshot. Compare the **frozen diff**, whose `_run_rubric_step(config, *, tracker=None, _write=None)` and call `_run_rubric_step(config, tracker=tracker, _write=_write)` contain neither `blobs`/`approval` nor any re-assertion.
- **D3:** `egress.disclosure_line()` (egress.py:248–278) has branches for providers/grounding/revision/ask, none for rubric. CHANGELOG (diff): *"no new consent category (the disclosure text gains a purpose mention only)"* — no such code exists.
- **D5:** `rubric.py` `run_rubric_chair` loop `break`s after a clean `parse_chair_reply`; `build_rubric`/`validate_rubric` run *outside* the loop (`if parse_error is None and status in ("ran","degraded"): … except RubricRejected`). Module docstring: *"Any discrepancy → the reply is invalid (retryable once, then the refusal path)."* `run_rubric_chair` docstring: *"a genuine reject (NOT retryable)."* CHANGELOG: *"retryable once, then the refusal path."* Mocks `tests/mocks/claude` `bad_weight`/`bad_partition`/`phantom` emit identical output every call; only `test_chair_retries_then_refuses_on_missing_fence` asserts `attempts == 2`.
- **Verified clean:** `EXIT_PREFLIGHT_NOGO = 1`, `RUBRIC_REFUSAL_EXIT = EXIT_PREFLIGHT_NOGO` (correct bucket, not `EXIT_NO_VERDICT=4`); byte-identity gated everywhere (`STAGES` is never index-serialized, so inserting `"rubric"` is safe); `mint_proposals` monotonic ids, weight check rejects bool/float, isinstance-before-membership guards in `board_rubric.py`; proposal fan-out threads are independent (results keyed by `seat.id` post-join).

Net: the design (D15/D16/D18/D20) is faithfully and, on the §11/injection/partition axes, impressively implemented. Codex's block was correct against the frozen diff and is substantially resolved in the live tree; what remains is disclosure honesty (D3), a self-contradicting retry contract (D5), and an optional byte-binding hardening (D4) — all "proceed with changes," none disqualifying.

BASIS: independent
VERDICT: caution

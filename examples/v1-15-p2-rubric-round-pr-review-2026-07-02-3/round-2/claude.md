All three agents are back and the picture is complete and consistent. I have what I need to reconsider. Here is my full round-2 review.

---

# Claude seat — round 2 review (Architecture & systems)

## 1. Updated verdict

**CAUTION — confidence: high.** The core rubric machinery is sound and both prior blockers are genuinely fixed, but Codex surfaced a real defect I under-weighted in round 1, and I have now independently confirmed it against the working tree: **the rubric proposal packet is not equivalent to the round‑1 review context under `--repo` or `--revise`, it silently degrades rather than refusing, and no test exercises either composition.**

One line on what would change it: fold the fix into this PR — either **guard the composition** (`--rubric` refuses to combine with `--repo`/`--revise`/`--endorse` in P2) or **document the source‑only decision and add `--rubric --repo` + `--rubric --revise` tests** — and I move to ship. Leave it unresolved and I hold caution; if evidence emerged that the composition also corrupts a run (it does not — see §6), I would go to block.

## 2. Where I changed my mind / where I still dissent

**Changed my mind (ship → caution) — seat: codex.** His round‑1 blocker was: "rubric proposals are not built from the same full source packet as round 1… `cmd_run()` prepares repo grounding and revision context before `_execute_run()`." In round 1 I treated the consent‑hash fold (BLOCKER 1) as fully closing the packet question. It closes *egress/consent*, but not *context equivalence*. I verified Codex's factual claim end‑to‑end against the real tree:
- Under **`--repo`**, a round‑1 seat prompt carries the `REPO_GROUNDING_CLAUSE` + evidence‑ask (`prompts.py:152‑162, 170‑174, 265‑268`) **and** runs with `cwd = grounding.snapshot_dir` + `grounded=True` (`rounds.py:235‑240, 128‑129`). The rubric proposal prompt has **no** grounding placeholder (`rubric.py build_rubric_proposal_prompt`), runs in an **empty ephemeral tempdir** (`cli.py:735`), and **never passes `grounded=`** to `build_argv` (`rubric.py:993‑994`).
- Under **`--revise`**, round‑1 embeds `REVISION_CONTEXT_BLOCK` (prior‑verdict digest + source diff, `prompts.py:215‑227, 340‑343`); the rubric proposal embeds none.
- **Zero tests** combine `--rubric` with `--repo`, `--revise`, or `--endorse` (`tests/test_run_board.py` TestRubricE2E 15244‑15460).

That is a specific, confirmed fact he raised, so this is evidence-driven, not deference.

**Still dissent — seat: codex — on severity (his BLOCK).** I do not agree this is "do not proceed." The gap is **inert in P2**: rubric.json is written but not injected into rounds or scored until P3/P4, so a thinner rubric has **zero effect on a P2 run's rounds or verdict**. It is **not an egress/safety issue** — the proposal egresses a strict subset of what round 1 egresses (source text only, no snapshot access), the consent hash correctly covers it, and the scope re‑hash still guards (`cli.py` `_run_rubric_step`). And it **does not crash** — the `round1_hash` reconstruction is sound (verified, §5). Block would discard a large, high‑quality change over a bounded, currently‑inert, cheaply‑fixable gap. Caution with a required composition fix is the proportionate call.

**Also retiring my own round‑1 challenge to Codex (shared workdir):** I asked whether the single shared workdir across the concurrent proposal fan‑out was safe for real CLIs. Verified: the **round path shares one workdir across concurrent seats too** (`rounds.py:244‑256`), identically to the rubric path (`cli.py:735` → `rubric.py:1051`). It is consistent with today's behavior, not a new risk — I withdraw it as a rubric‑specific objection.

## 3. Strongest remaining objections

1. **[Required for caution] `--rubric` × `--repo`/`--revise` composition is silently degraded and untested.** Proposals are formed blind to the repo and to revision context, so under grounding/revision the board proposes criteria against strictly less than it will review. No guard refuses the combination (`config.py resolve_config` ~789‑835 sets `rubric` orthogonally; the only guard is `--chair-seat`⇒requires‑`--rubric` at ~801‑807). Inert in P2, but this is the *foundation* P3 scores against — the mis‑scoping surfaces the instant P3 injects the rubric. Cheapest to decide now.
2. **[Concern] The code's own prose overclaims equivalence.** `rubric.py`'s module docstring — "the same content the round‑1 packet already egresses under the run's existing disclosure, so there is no new consent category" — and the `cli.py:288‑301` comment are true for the plain path but **misleading under grounding/revision**. The consent claim is fine (subset egress); the *equivalence* claim is not. Scope the wording to "source text only; grounding/revision context is not carried into the rubric pass."
3. **[Low] The partition invariant is implemented twice** — `rubric.py:reconcile_partition` (write‑time) and an independent inline re‑check in `board_rubric.validate`. Correct defense‑in‑depth for a standalone validator, but two code paths that must stay in lockstep; a future edit to one and not the other silently weakens the last gate. Consider having the validator call `reconcile_partition`, or add a parity test.
4. **[Low] Zero‑weight merged criteria are accepted.** `_validate_chair_weight` and `board_rubric` allow `weight == 0` provided the sum is 100. A criterion the board weights at nothing is a soundness smell; require `weight ≥ 1`.
5. **[Low, tests / lens 4] Several validator tests assert only that the doc dies, not *why*.** E.g. `test_proposal_ids_must_be_dense_sequence` — its own comment concedes "a phantom would trip first," yet it asserts only `self._dies(d)`, so it would pass even if the dense‑id check never ran. The unicode‑confusable tests correctly pin `"phantom"`; tighten the rest where a specific invariant is the point.

## 4. Recommended execution sequence

This reviews a completed change, so the sequence is merge‑hygiene, not a build plan:
1. **Decide the P2 composition policy before merge.** Recommended (smallest, preserves byte‑identity): **guard and refuse** `--rubric` with `--repo`/`--revise`/`--endorse`, mirroring the existing `--chair-seat`⇒`--rubric` guard in `resolve_config`, and add a test asserting `EXIT_USAGE`. Alternative (if source‑only rubrics are genuinely intended): **rewrite the two misleading docstrings** to scope the equivalence to source text, and add `--rubric --repo` + `--rubric --revise` E2E tests proving the run completes and the rubric is source‑derived.
2. **Run the full suite on a clean checkout.** I verified the +73 count statically (exactly 73 new `def test_*`), not by execution; the 1499 total is unverified by me.
3. **Optional low‑severity cleanups** (§3.3‑3.5): weight ≥ 1; collapse or parity‑test the double partition; pin the death‑only validator tests to their specific check.

## 5. Invariants and guardrails

Verified holding:
- **Identity conductor‑owned (§11):** `mint_proposals` is the sole p‑id source (board order, then within‑seat); `c1…cN` assigned in `build_rubric`; a model‑supplied `id` is dropped at parse.
- **Partition reconciliation:** coverage / no‑phantom / no‑double‑claim / no‑empty‑subsumes against conductor ground‑truth; unicode & NFC/NFKC id spoofs are rejected as phantoms because the check compares raw code points with no normalization.
- **Weight‑sum:** exactly 100, integer, `bool` rejected, enforced at *both* write (`build_rubric`) and validate (`board_rubric`).
- **Consent‑hash fold (BLOCKER 1):** proposal blobs prebuilt pre‑approval, in the manifest + content hash; whole‑packet re‑assertion in `_run_rubric_step` plus per‑seat rebuild‑drift check; round‑1 sub‑hash recorded and checked — verified sound (`cli.py:415‑416` set before `write_pre_spawn`/`activate`; `rounds.py:202‑205` guard; `blobs` never mutated, `cli.py:705` copies).
- **Retry state machine (BLOCKER 2):** mechanical checks live inside the two‑attempt loop; `retry_once_then_ok` proves recover, `bad_weight`/`bad_partition`/`phantom` prove refuse‑after‑2 (`attempts == 2`).
- **Byte‑identity (D5/R5):** recipe/run‑card/tree/estimator/status all gated on `config.rubric`; tested; estimator callers safe (new params defaulted).
- **RH‑1 / refusal posture:** floor refusal writes `rubric-rejected.json`, no chair artifacts, no round/verdict; `EXIT_PREFLIGHT_NOGO` reuse is well‑argued and correct.

**The one missing guardrail:** nothing enforces that `--rubric` runs only where its packet actually equals the review context. That is objection 1.

## 6. Risks, stale assumptions, missing evidence

- **Stale assumption baked into the code:** the "same source as round 1" framing is stale the moment grounding or revision is on.
- **Missing evidence:** no composed‑path tests (`--rubric --repo` / `--rubric --revise` / `--rubric --endorse`); I did not execute the suite (count verified statically, not by run).
- **Deferred risk:** a source‑only rubric will drive P3 scoring against criteria that ignore the repo the board actually reviewed — the defect is invisible now and load‑bearing later.
- **Not a risk (cleared this round):** the composition does **not** crash (round1_hash logic verified), does **not** leak (subset egress), and the shared workdir is consistent with the existing round path.

## 7. Concrete evidence

- Non‑equivalence under `--repo`: `prompts.py:152‑162, 170‑174, 265‑268` (grounding clause in round‑1) + `rounds.py:235‑240, 128‑129` (snapshot cwd + `grounded=True`) vs `rubric.py build_rubric_proposal_prompt` (no grounding placeholder), `cli.py:735` (empty tempdir), `rubric.py:993‑994` (no `grounded=`).
- Non‑equivalence under `--revise`: `prompts.py:215‑227, 340‑343` (revision block in round‑1) vs no revision context in the proposal prompt.
- No composition guard: `config.py resolve_config` ~789‑835; sole guard at ~801‑807.
- No composition tests: `tests/test_run_board.py` TestRubricE2E 15244‑15460.
- round1_hash correctness (not a bug): `cli.py:415‑416`, `cli.py:437/442`, `cli.py:705`, `rounds.py:197, 202‑205`.
- Overclaiming prose: `rubric.py` module docstring "the same content the round‑1 packet already egresses… no new consent category"; `cli.py:288‑301` comment.

BASIS: evidence
VERDICT: caution

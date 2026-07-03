# Advisory Board — Claude seat review

**Role: Architecture & systems (design soundness, invariants, failure modes).** I am ruling on the v1.15 rubric-first design brief as a self-contained document. My rulings rest on the brief's own stated invariants (§11, D8, D14, R5/D5, the echo-score philosophy) and the precedents it cites (synthesizer/revision/endorsement, `changes.json`, the `confidence` gate rule).

---

## 1. Verdict

**CAUTION — proceed, but fold the changes below into D15+ before any Phase 2 code.** Confidence: **high**.

The design is directionally right and unusually well-precedented — every strawman reaches for an existing pattern rather than inventing one, and the two genuinely risky axes (the gate and byte-identity) are handled conservatively. But at least two strawmen are **not sound as literally specified**: Q1's completeness check is unverifiable as worded (it lets the chair invent criteria and provides no mechanism to check the merge — a §11 correctness gap), and Q4's informational-scorecard is misleading unless it explicitly says it didn't gate. Those are specific, load-bearing changes, not "concerns to note" — which is the definition of CAUTION rather than SHIP.

**One line on what would change it:** if the chair-merge already emits a conductor-checkable proposal→criterion partition (closing the completeness gap) and per-seat lensing already exists (Q8), most of my cautions soften and this moves to SHIP.

---

## 2. Per-question rulings

**Q1 — SHIP the shape, CAUTION the completeness mechanism.** Single-shot proposal→merge is the right cost/value point: the opinion rounds already provide the iterative deliberation (on *scores*), so a debate round buys marginal quality for a full extra fan-out — leave it documented as the escalation if real rubrics come out incoherent. The ≥2-proposal floor is correct ("one voice is not a board"). **But "cross-asserts completeness (every proposal accounted for)" is under-specified in a way that violates §11 if built as-worded:** it is unidirectional (catches silently-dropped proposals, not chair-*invented* criteria) and names no mechanism. The trade-off I'm weighing is chair-output complexity vs. an auditable merge — and §11 ("completeness checks are conductor-computed and never model-trusted") forces the latter. Fix: conductor mints proposal ids at parse time; the chair emits, per merged criterion, the source-proposal-ids it subsumes and, per drop, the proposal-id + reason; the conductor verifies a **total, disjoint partition** (every proposal id appears exactly once across subsumed-sets ∪ drops; any merged criterion with an empty subsumed-set is rejected as invented). The conductor never judges whether a subsumption is *semantically* right (that's the chair's reasoning) — only that the partition is total and disjoint. Also specify proposal-weight semantics (each seat's weights sum to 100, conductor-validated at proposal parse) so the chair reconciles comparable inputs.

**Q2 — SHIP (a) for chair selection; CAUTION "scoring is pure acceptance with a free-text note."** Reusing the synthesizer/revision selection rules verbatim is right; (c)'s "least-invested" rule correctly rejected because it smuggles merge-quality incentives into seat selection where nothing else does. The trade-off on acceptance is faithfulness-to-R4 vs. an extra fan-out. I don't want the extra endorsement round (an OBJECT verdict has no clean mechanical consequence here without reintroducing the debate-round cost Q1 rejected) — but the brief applies the R4 precedent ("the objection that made endorsement default-on") only to Q1's no-proposal alternative and **misses that it also bites here**: the chair's merged rubric is one seat's reconciliation product that becomes the board's scoring standard, and statelessness means the *scoring* spawn of seat A never ratified what the *proposing* spawn of seat A suggested. A free-text, uncounted `RUBRIC-NOTE` is below this codebase's own auditability bar. Fix without a fan-out: structure the channel into a countable line (`RUBRIC-OBJECT c3: <reason>` / `RUBRIC-OBJECT rubric: <reason>`) the conductor tallies and renders; a majority objection to a criterion becomes a loud scorecard signal. That honors R4 without the extra round.

**Q3 — SHIP (b), 1–5 integers, conductor-assigned ids.** (b) is unambiguously correct: (a) forks the gate/parser/convergence/schema/renderers and destroys cross-run comparability; (c) violates §11 (conductor generating a verdict) and the false-precision rule. 1–5 integers are the echo-score philosophy applied ("coarse over precise") and — the trade-off with 0–10/0–100 — they also dissolve fact 3's oscillation concern, since any movement is a discrete ≥1 step. Conductor-minted `c1…cN` is consistent with §11 and with the D9-for-findings reasoning (criteria are a new object with no legacy). **One required addition:** a bare 1–5 is only comparable across seats/rounds if the scale has fixed named anchors ("1 = criterion badly unmet … 5 = fully met") injected with the rubric and shown in the render — otherwise seat A's 4 and seat B's 4 aren't the same thing and the board-mean is noise. Also state retry granularity crisply: one retry on any missing/out-of-range line, then accept partial (dovetails with Q9).

**Q4 — SHIP the strawman (a-for-gate, b-as-recorded-extension, ⚠ row) with a REQUIRED honesty guardrail.** This is the crux, and the conservative choice is right. The decisive argument against wiring the gate now (option b) isn't only §11 — it's that the bands are **uncalibrated** (zero real scored runs exist; nobody yet knows whether a 2.4/5 weighted mean is "block-band"), and routing model-asserted scores into the gate — even toward the safe ABSTAIN direction — erodes the clean, defensible "gate reads only tokens" invariant (the `confidence` precedent). The trade-off is teeth-now vs. a calibrated gate later; deferral wins because the scorecard still has teeth without gating (it localizes disagreement, drives convergence, and renders the ⚠ token/band contradiction for a human). **But rendered-but-not-gating is honest *only if the artifact says so*:** the scorecard must carry a plain-language note that scores are informational and did not move the gate (exactly how `confidence` is shown-but-labeled-self-reported). Without that note, showing scores next to a verdict implies they gated it. Fix the bands as coarse thirds, name them in the render, and have the ⚠ row name the seat and direction.

**Q5 — SHIP the two-artifact-of-record pattern (b); CAUTION the single-artifact shape — split it.** (b) over (a) is clearly right: (a) bloats the judgment record and forces the synthesizer to transcribe scores it didn't produce. The weights-sum-to-100 invariant is correctly flagged as the first numeric-sum invariant — **validate at merge and refuse on mismatch; do not silently normalize** (normalization hides a chair that can't follow the weight instruction and is a "conductor invents numbers" smell). Per-round over final-only is right — the trajectory *is* the convergence story. **My refinement, on a failure-mode/lifetime argument:** the strawman's single `scorecard.json` conflates two artifacts with *different lifetimes* — the merged rubric must be written, hashed, and injected **before round 1**, while scores accumulate through the final round. Embedding both forces either a write-twice (breaks black-box write-once) or "criteria live in memory until run-end" (an interrupted mid-scoring run then has no validated record of the rubric it was scoring against). Split into `rubric.json` (`advisory-board/rubric@1`, written at merge, interruption-safe, injected; validated by `board_rubric.py` — ids, partition, weights-sum-100) + `scorecard.json` (`advisory-board/scorecard@1`, written at end, pins the rubric by `{artifact, sha256}`, carries per-round scores + conductor-computed totals/bands). `verdict.json` pins both. Drop-with-reason is chair prose → the bounded model-authored "notes" category → lives in `rubric.json`, not a third artifact.

**Q6 — SHIP (a).** Widening the existing OR-boolean with "any criterion score changed" is minimal and correct; (b) is rejected for the reason the brief half-states and I'll sharpen: it converges on the **non-gating axis** — a board can agree every number while still flipping tokens, so score-convergence could stop the run while the gate-relevant axis is unstable. (a) keeps *both* token and score movement in the OR, so the run continues while either the gating axis or the deliberation axis is live — which is correct. The trade-off is a real cost characteristic: rubric+`auto` will tend toward `--max-rounds`, because integer scores are twitchier than tokens (a 4→3 nudge counts). That's bounded by the ceiling and arguably desirable (a still-moving score *is* live deliberation), so ship it — but make it self-diagnosing via the strawman's round-done "which criteria still moving" detail; if runs show pathological single-criterion flapping, the dampening move (movement = weighted-total *band* crossed, not any single cell) is the documented fallback.

**Q7 — SHIP the orthogonal boolean and "no hard `--synthesize` requirement."** Orthogonality to tier/lens/synthesize/output is right and axis-consistent; "quick tier still does proposal+merge first" is correct (skipping the rubric under quick would make `--rubric` mean different things at different tiers — the silent-implication trap). Recording in the recipe (not treating it as a presentation flag) is the right precedent since it changes artifact shape. On the unpinned-scorecard tampering attack: the trade-off is a synthesizer spawn on every rubric run vs. a weaker integrity anchor. Requiring `--synthesize` is disproportionate (the round artifacts are *already* unpinned on every non-synthesize run today, and the codebase accepts that). **But strengthen the integrity story rather than leaving it at "stands alone like round artifacts":** the scorecard is a *derived* conclusion-bearing summary (unlike a raw round reply), so state that it is **deterministically re-derivable from the raw, consent-hashed round records** — tampering is detectable by re-parsing the rounds; the `verdict.json` pointer is an *additional* bind when synthesis runs, not the sole anchor. That defuses the tampering claim without coupling the features.

**Q8 — SHIP (c).** (b) is self-defeating and the brief is right to flag it: criteria-defaults would pre-empt the proposal pass, which is the heart of the feature; plus board-composition presets don't exist and it's a third preset axis to maintain. (c) rides the entire existing lens + plain-language-verdict machinery for prose cost. Keep it orthogonal and document `--rubric --lens stakeholder-panel`. **Two flags.** (i) Factual dependency: (c) is "an afternoon" *only if per-seat lensing already exists* — the brief is internally ambiguous (product-context says "the seat's Role emphasis," singular; fact 5 says "per-position focus strings," plural). Distinct archetypes on distinct seats need per-seat assignment; if lensing is uniform, that's a small prerequisite, not free. (ii) Design-consequence: a stakeholder panel is a **designed-divergence** run (a CFO and an end-user rationally disagree forever) — it will lean on `--max-rounds` and rarely reach unanimity, so convergence/rendering must frame persistent persona-divergence as the *product*, not a failed convergence.

**Q9 — SHIP all three postures; the chair-merge refuse is right, but on a better rationale than "nothing valuable produced."** Proposal-pass refuse-before-rounds is correct and correctly distinguished from the synthesizer (which fails after expensive work). The scoring-line soft-degrade (usable seat, "—" for missing cells, partial totals, never impute) is exactly D14/§11-correct — imputing a score would be the conductor inventing model content. On the hard one: I attacked the strawman and it survives, but its stated reason is slightly wrong. "Nothing valuable has been produced yet" is overstated — the proposal fan-out *is* real recorded model work (it's preserved on refuse, not discarded). The **actual** distinguishing principle is: **chair-merge is an upstream *precondition* for the requested deliberation shape, not a downstream *post-process*.** The synthesizer/revision/endorsement soft-fails all preserve a *successful core* and drop a trimming; a failed chair merge means the requested core (rubric'd rounds) can't happen at all, so degrading to plain rounds *substitutes a different core the user didn't ask for* — the preflight-refuse posture, not the synthesizer posture. That principle also predicts the proposal-floor refusal and the scoring-line degrade, so record *it* as the rule. **Guardrail:** the refusal exit code must be a pipeline-integrity code (preflight-NO-GO family), never a content-gate code — a chair failure exiting like "block" would conflate pipeline-broke with board-said-block. Q9b (mechanically carry the prior rubric forward on `--revise`) is right and elegant (comparability across revisions); just confirm the objection channel is available on revision runs so a seat can flag a criterion the revision made moot.

---

## 3. Strongest objections (ranked)

1. **The completeness check is unverifiable as worded (Q1/§11).** "Every proposal accounted for" with no chair-emitted mapping and no invention-direction check means the chair is *trusted* to merge honestly — the exact thing §11 says the conductor must mechanize. This is the one gap that, unfixed, makes the merge un-auditable. Fix = the total-disjoint partition check above.
2. **An informational scorecard that doesn't say it's informational is misleading (Q4).** The feature's promise is "auditable against stated standards"; a reader who sees scores beside a verdict will assume the scores constrained it. The honesty note is mandatory, not cosmetic.
3. **The rubric objection channel is below the codebase's own auditability bar (Q2).** Free-text `RUBRIC-NOTE` in a codebase that counts ENDORSE/OBJECT/ABSTAIN is out of character and quietly overrides the R4 precedent. Structure and count it.
4. **The scorecard's single-artifact shape fights black-box write-once and interruption-safety (Q5).** Two lifetimes → two artifacts.
5. **Chair-merge refuse is defended by the wrong reason (Q9).** Right call, fragile rationale; the precondition-vs-post-process framing is what makes it robust and generalizable.

---

## 4. Recommended execution sequence

Rewrite M5's phases so the **linchpin and the regression guard land first**:

- **Phase 2a** — proposal parse + conductor-minted proposal ids + per-seat weight validation (comparable inputs).
- **Phase 2b (build first, it's the §11 anchor)** — chair merge emitting the proposal→criterion partition + drops; conductor total-disjoint partition check + weights-sum-100 (refuse, don't normalize); `rubric.json` (`advisory-board/rubric@1`) + `board_rubric.py`; injection into round prompts.
- **Phase 2c** — proposal-floor + chair-merge refusal postures with exit-code hygiene (preflight-NO-GO family), written alongside the happy path.
- **Phase 3a** — score-line format + per-line parser reusing `parse_verdict` hardening + fixed anchor legend injection.
- **Phase 3b** — score-movement OR-disjunct in convergence + round-done moving-criteria detail (the self-diagnostic).
- **Phase 3c** — scoring-line soft-degrade (partial totals, "—").
- **Phase 4a** — `scorecard.json` (`@1`) + `board_scorecard.py`; `verdict.json` pointers for both artifacts (strict-when-present, invisible-when-absent).
- **Phase 4b** — renderers (scorecard, ⚠ row + honesty note, anchor legend, **weighted *and* unweighted totals**) **and the byte-identity golden test first in this sub-phase** — a non-rubric run diffed byte-for-byte on `verdict.json` and rendered body.
- **Phase 4c** — recipe recording + `--from-recipe` replay + STAGES token + RH-1.
- **Independent/late** — `--revise` carry-forward (Q9b) and the `stakeholder-panel` lens preset (Q8), each landable on its own.

Front-load 2b and the 4b golden test — both are expensive to retrofit if wrong.

---

## 5. Invariants and guardrails

- **Merge partition:** every proposal id appears exactly once across (subsumed-sets ∪ drops); every merged criterion cites ≥1 proposal; empty-subsumption criteria rejected. Conductor checks structure, never semantics.
- **All ids conductor-minted** (proposals + criteria); models never mint identity.
- **Weights:** integer %, conductor-validated `== 100` at merge, *before* injection; refuse on mismatch, never normalize.
- **Gate reads only tokens + token-derived structural contradictions** — never scores/totals/bands (D8, `confidence` precedent). Scorecard states this in plain language.
- **Scores never imputed:** missing = "—", totals marked partial; **content never moves exit codes** (D14).
- **Refusals (proposal-floor, chair-merge) exit in the preflight/pipeline family**, never a content-gate code.
- **Byte-identity (R5/D5):** non-rubric run → byte-identical `verdict.json` (no pointers) + zero-body render sections. Golden test.
- **Egress:** everything injected inside the consent-hashed packet; purpose mention only, no new category.
- **Artifacts:** `rubric.json` written before round 1 (interruption-safe), injected verbatim, re-derivable-from-raw; `scorecard.json` at end, pins rubric.
- **Scale:** fixed named 5-point anchors, injected + rendered. **Bands:** fixed coarse thirds, named in render.
- **Objection channel:** structured + counted, not free-text.

---

## 6. Risks, stale assumptions, missing evidence

- **Stale/ambiguous fact:** per-seat vs. uniform lensing (Q8) — "the seat's Role emphasis" (singular) vs. "per-position focus strings" (plural). Resolve before scoping stakeholder-panel.
- **No calibration data exists:** the 1–5 scale's *discriminating power* is unproven — models may cluster at 3–4 and make the scorecard feel mushy. This both justifies deferring the Q4 gate integration *and* argues for a real dogfood scored run early in Phase 3 to check spread before committing to the render.
- **Unverifiable chair weighting (cross-cut):** weights are chair judgment (sum-to-100 is the only mechanical check) yet they drive the totals feeding the ⚠ row — another reason scores must stay non-gating, and the reason to render weighted *and* unweighted totals so a reader can see whether a contradiction is weighting-driven.
- **Cost:** rubric+`auto` tends to `--max-rounds`; bounded but real — keep it transparent via STAGES (a Tim value: conserve usage).
- **Framing honesty (statelessness):** "the seats agreed the criteria" is aspirational — they *proposed*, the chair *merged*, they *score-under*. The structured objection channel is the mitigation; don't overclaim in render.
- **Unconfirmed assumption:** that the existing fan-out/retry machinery cleanly hosts a pass returning a *non-VERDICT* reply shape (criteria block). Fact 1 calls it a new module — confirm the executor is reply-shape-agnostic or needs a parametrized parser hook.
- **Partial totals** must not be silently ranked/compared against full totals, and the ⚠ row should note partiality rather than fire a confident band off a subset.

---

## 7. Concrete evidence from the brief

- §11: *"everything structural (ids, weights arithmetic, **completeness checks**) is conductor-computed and never model-trusted"* — directly indicts Q1's unmechanized "cross-asserts completeness."
- Q1: *"The conductor cross-asserts completeness (every proposal accounted for)"* — the exact phrase that is unidirectional and mechanism-free.
- Q1 alternative: *"the same R4-style objection that made endorsement default-on in v1.13"* — the brief raises R4 against the no-proposal option but not against Q2's "scoring is acceptance," where it also applies.
- D8: *"the gate never reads a gameable number (the `confidence` precedent)"* — grounds Q4 non-gating.
- Q4: *"is a rendered-but-not-gating contradiction honest enough…?"* — answered by the mandatory informational note.
- Q5: *"conductor-validated to sum to exactly 100 — the first numeric-sum invariant in the codebase, so state it loudly"* — grounds refuse-not-normalize.
- Q9 chair-merge: *"nothing valuable has been produced yet to protect. Attack this hard"* — attacked: the proposals *are* produced/preserved; the durable reason is precondition-vs-post-process.
- Fact 3: *"a continuous epsilon rule risks a board that oscillates forever near the boundary"* — grounds 1–5-integers-dissolve-epsilon (Q6).
- Fact 5 vs. product context — the per-seat/uniform lens ambiguity (Q8).

---

## 8. What I'd ask the other seats to challenge

- **Codex (implementation lens):** Does the existing fan-out/parse machinery genuinely host a proposal pass with a non-VERDICT reply shape, or is fact-1's "new module" underestimating a parser refactor? And is there *any* always-written run-level manifest that could anchor the scorecard sha without `--synthesize`, making my re-derivability argument unnecessary?
- **Product/strategy seat:** Is 1–5 enough discrimination for a non-developer stakeholder panel to trust the scores, or will everything cluster and feel mushy — i.e., is the calibration risk bad enough to run a dogfood scored board *before* finalizing the render?
- **Plain-language/honesty lens:** Does showing scores beside a gate-ignored verdict confuse a non-developer even *with* the informational note — is there a clearer framing than a ⚠ row?
- **Challenge to my own strongest claim:** I want the chair to *self-report* the proposal→criterion mapping and have the conductor verify only the partition (total + disjoint), on the theory that the partition check is exact regardless of match quality. The alternative is the conductor computing the mapping itself by text-matching (no trust, but fuzzy and unreliable). Is trust-then-verify-the-partition actually §11-clean, or does accepting a chair-asserted mapping at all reintroduce the model-trust §11 forbids? I believe the partition check is exact and mechanical, but I want it stress-tested.

VERDICT: caution

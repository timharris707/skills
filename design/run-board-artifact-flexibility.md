# Output-Artifact Flexibility
> Make the board's artifacts as good as its deliberation — adapt what it hands back to who is asking and why.

- **Updated:** 2026-06-26
- **Source:** Two dogfood roundtables (2-seat + full 3-seat) on artifact strategy; Panely reference; Tim direction
- **Owner:** Tim
- **Baseline:** v1.6.0 — plain-language lens-aware verdict shipped (`5d07b89`); classifier FP fixed (`bd975bb`); GitHub-grounding in flight
- **Status:** PLANNED

## Overview

**Thesis:** the skill is only as good as the artifacts it produces. The deliberation is already strong; the value is lost if what lands in the user's hands is shaped for the wrong reader — developer jargon for a founder, a scattered transcript for someone who wanted a one-page call. Artifacts should feel *authored for the person who asked*.

**Provenance.** This plan is grounded in two real advisory-board runs on this exact question (the run dirs and a side-by-side are archived). The board's verdict both times: **caution / high / unanimous** — back the direction, but not as originally drawn. Its loudest *unanimous* point is a caution: **there is no demand signal** — no data on which artifact is the "hero" or whether `verdict.json` is parsed downstream. That single fact shapes the sequencing below: **build the differentiator, ship a strong default, instrument real use, and let evidence — not a debate — choose how far to flex.**

**Proposed path (the spine of this plan):**
1. **Foundations & honesty** — one deterministic render source-of-truth so artifacts can't drift; disclose provider egress in every serious artifact.
2. **Build the discussion-atlas first** — the single full-discussion artifact. It is the proven gap (today the full per-seat text is scattered across `round-N/<seat>.md`), the hard requirement, and the board's named differentiator ("a single-model query cannot produce this").
3. **One universal baseline bundle** — a small, opinionated, *zero-choice* set of artifacts rendered as deterministic views of the source-of-truth. No audience knobs yet.
4. **Instrument, then decide the flex axis from data** — capture which artifacts get used across ~10–15 real non-developer runs before adding any second dimension. Audience adaptation, if warranted, is deterministic template-selection, not generative re-voicing.

**Explicitly out of scope (shelved, may revisit):** *transformational* artifacts — the board writing/applying a fixed copy of the user's code. The board named this the "Actionability Trap" (a consensus board is optimized for critique, not precision editing; a non-expert over-trusts a "board-approved" patch), and Tim removed it from scope. The board may still *diagnose* and *output* code as advice (a diff to review), but never apply it. See **D3**.

## Decisions

- **D1** Keep `verdict.json` as the machine contract — Every human artifact is a downstream projection of this one schema-validated file (`advisory-board/verdict@2`). Flexibility lives in rendering, never in the source of truth.
- **D2** Plain-language, lens-aware human verdict — SHIPPED in v1.6.0. Software lens keeps "SHIP / SHIP WITH CHANGES / DO NOT SHIP YET"; other lenses render "Go ahead / Proceed with care / Stop and rethink" + a one-line note. This plan builds on it.
- **D3** Transformational / apply-the-fix artifacts are OUT OF SCOPE for this milestone — Board "Actionability Trap" objection + Tim's call. Code may be *shown* (diff to review), never *applied*. The board split on how hard to foreclose this: Gemini wanted transform permanently ruled out (a read-only-advisor invariant), while Claude wanted to leave a narrow gated path open for a later milestone. The "revisit later" framing below reflects Claude's side, to be re-decided if/when revisited. Revisit as a possible gated, copy-never-original, developer-only feature in a later milestone — not here.
- **D4** `handoff-data.json` is the derived semantic intermediate, not a second source of truth — `verdict.json` stays the one canonical source (D1). `handoff-data.json` is a normalized semantic intermediate *derived from* `verdict.json` in code (`build_handoff_data()` builds it from the verdict), and every human renderer consumes that intermediate so artifacts are "not separately authored documents that can drift" (Codex). The derivation direction is one-way (`verdict.json` → `handoff-data.json` → human artifacts); the intermediate is explicitly NOT a rival canonical source. This is the anti-drift backbone that makes multiple artifacts safe.
- **D5** Zero user choices at invocation on the default path — The guardrail binds on *choices-at-invocation ≈ 0*, NOT on artifact count (Claude's round-2 correction). A good default bundle is fine; forced configuration is the hazard. The default brief reads as an objective briefing forwardable to someone who never ran the board — voiced for a third-party reader, NOT for the prompter. (Format forwardability — Slack/email/PDF — is a separate concern, covered by Phase 7 / R6; this clause is about *voice*.) This brief is the hero-candidate to validate in Phase 8. A future Phase-9 audience-persona choice must NOT silently re-voice the default away from third-party-objective — a forwardability guard pins the default voice (see Phase 9).
- **D6** Build the discussion-atlas first — The full-discussion artifact is the differentiator, the hard requirement, and the proven gap. It is sequenced ahead of the baseline bundle.
- **D7** Deterministic template-selection over generative re-voicing for v1 — Cheaper, testable with golden files, no per-variant model call, no drift. Generative re-voicing is an open question (OD2), not a v1 commitment.
- **D8** Egress honesty in every serious artifact — Artifacts must not imply fully-local deliberation; they disclose that material was sent to external providers (which providers saw what). Corroborated independently by the board and by the in-flight marketing fix.
- **D9** Provisional artifact names now, refine after seeing outputs (Tim, 2026-06-26) — Initial names (`decision-brief`, `decision-record`, `discussion-atlas`, `verdict.json`, `run-metadata`) are placeholders; "too formal / too generic" is a cheap post-hoc change once real outputs exist. Don't block the build on naming.
- **D10** Reading level = lens-aware default + optional override (Tim, 2026-06-26) — Default derives from the lens/topic: general-audience lenses render at ~8th-grade; technical and high-stakes lenses (software-architecture, legal-contract) keep precision / a higher level rather than being dumbed down. A user may set an explicit reading level at invocation (`--reading-level`); the default path requires no choice (consistent with D5). This is a property of the baseline, NOT the deferred flex axis — it ships early.
- **D11** Dissent, blockers, and confidence are PROMINENT in every artifact tier — Both runs unanimously require the minority report, blockers, and the confidence level to render prominently in *every* artifact tier — the skim brief and the comprehensive record included, not only the atlas/transcript — and to survive the plain-language/reading-level layer (D2/D10) without being smoothed away. This is an invariant: the same dissent/blockers/confidence appear regardless of audience or reading level. Enforced by the golden test in Phase 6.

## Open decisions

- **OD1 — RESOLVED (defer to data; Tim, 2026-06-26):** Primary flex axis — the board split three ways: **audience persona** (Claude), **decision-context / lens** (Codex: "the artifact must often persuade stakeholders beyond the prompter"), or **no adaptation — one universal professional baseline** (Gemini). Decision: do NOT pick now; resolve from instrumentation (Phase 9). Start from one universal baseline.
- **OD2 — open (leaning deterministic):** Whether audience adaptation is ever generative (re-voiced) vs. always deterministic template-selection — Default to deterministic (D7); revisit only if Phase 8 data shows template-selection is insufficient.
- **OD3 — RESOLVED → D9:** provisional names now, refined after real outputs exist.
- **OD4 — RESOLVED → D10:** lens-aware reading-level default (~8th-grade for general; precision preserved for technical/high-stakes) + optional user override; no forced choice on the default path.

## Milestone: Foundations & honesty

### Phase 1 — Plain-language verdict (shipped)
status: done
- [x] Lens-aware human label decoupled from the machine token; `lens_preset` threaded into `verdict.json`.
- [x] All three renderers route through one shared label module; 579 tests green.
Testing: shipped in PR #26; `TestVerdictLabels` + smuggle-guard regression tests.
Gate: `merged to main (5d07b89)`

### Phase 2 — Single render source-of-truth (`handoff-data.json`)
status: todo
- [ ] DECISION: every human artifact renders from the `handoff-data.json` intermediate, which is itself derived one-way from `verdict.json` — no artifact authored independently of it (D4). Derivation direction: `verdict.json` → `handoff-data.json` → all human artifacts.
- [ ] Note: `build_handoff_data()` (`scripts/render_verdict.py`) already derives the intermediate from `verdict.json`; this phase converges the renderers onto it, it does not introduce a new source.
- [ ] Audit current renderers (`render_verdict.py`, `format_output.py`, the handoff template) and converge them onto the single derived intermediate.
- [ ] Add a drift guard: a test that two artifacts built from the same `verdict.json` agree on shared fields (verdict, blockers, seats).
Testing: golden-file render of a fixed `verdict.json` → `build_handoff_data()` → byte-stable across artifacts.
Gate: `python3 -m unittest discover -s tests -t tests`

### Phase 3 — Egress honesty in every serious artifact
status: todo
- [ ] DECISION: each non-trivial artifact carries a short provenance/egress line (which providers received the material) — D8.
- [ ] Render the egress disclosure from the existing run manifest / `sensitivity.json` (no new data collection).
- [ ] Honesty about board composition: every serious artifact renders dropped/degraded seats visibly (from the per-seat `dropped` field in `verdict.json`), never only in run-metadata — a board that degraded 3→2 must never render as a clean unanimous board.
- [ ] Reconcile wording with the marketing data-confinement fix so the product and the docs say the same thing.
Testing: artifact contains an accurate egress line for a public run and a local-only run; and the dropped seat in the ragged run surfaces in the artifact body, not just run-metadata. Concrete check: assert the egress line substring is present for the public-run fixture and absent for the local-only fixture, and that the rendered artifact text contains the dropped seat's name flagged as dropped.
Gate: `python3 scripts/render_verdict.py over scratchpad/roundtable-run-3seat (public) and scratchpad/roundtable-run (ragged) → egress line correct; dropped codex seat visible in artifact body`

## Milestone: The discussion-atlas (full-discussion artifact)

### Phase 4 — Atlas data model
status: todo
- [ ] DECISION: one artifact captures the ENTIRE roundtable as a single readable thing (hard requirement) — consolidating the scattered `round-N/<seat>.md` files.
- [ ] Define the atlas structure over the run dir: per-seat turns across rounds, verdict-movement, citations, points of contention.
- [ ] Handle jagged matrices: seats that dropped mid-deliberation or have missing round files (e.g. a seat present in round 1 but absent in round 2) must be representable — the atlas data model carries a per-seat presence/`dropped` status per round rather than assuming a full N-seats × M-rounds rectangle.
- [ ] Preserve verbatim turns (no summarization of the discussion itself).
Testing: atlas data assembled from BOTH archived run dirs round-trips every present seat/round; the dropped seat in the ragged run is carried as dropped, not silently omitted. Concrete check: assert `set(atlas.seats) == set(seat dirs on disk)` and that each present `round-N/<seat>.md` maps to exactly one atlas turn, for both fixtures.
Gate: `atlas builder over scratchpad/roundtable-run-3seat → 3 seats × 2 rounds present; AND over scratchpad/roundtable-run (2-seat, codex dropped after round 1) → codex carried as dropped, no round-2/codex.md required`

### Phase 5 — Atlas render (guided layer over verbatim)
status: todo
- [ ] Guided layer so it is inviting, not a 10k-word wall (R2): timeline, contention map, verdict-movement, per-seat cards, collapsible long turns (progressive disclosure).
- [ ] Verbatim turns remain one click away and unmodified.
- [ ] Dropped/degraded seats render visibly on their own seat card (from the per-seat `dropped` status) — a seat that left after round 1 shows as dropped on the card, never silently absent or implicitly unanimous.
- [ ] DECISION (OD-adjacent): the guided layer is deterministic/structural, not a generative rewrite of the discussion.
Testing: render BOTH archived runs; confirm dissent (the three-way flex-axis split) is visible and not flattened, and that the dropped seat in the ragged run shows as dropped on its card. Verbatim check is concrete: byte-equality of each extracted atlas turn against its source `round-N/<seat>.md` file (idiomatic — `tests/test_render_engine.py` already does byte-equality verbatim checks).
Gate: `render atlas → HTML + markdown; assert byte-equality of extracted turns vs round-N/<seat>.md for both fixtures`

## Milestone: Universal baseline bundle (zero-choice)

### Phase 6 — Core artifacts as deterministic views
status: todo
- [ ] DECISION: ship a small zero-choice default set — a skim brief + a comprehensive record + the atlas + `verdict.json` + run-metadata (names per OD3) — all rendered from `handoff-data.json`.
- [ ] No audience knobs in this milestone; one well-crafted universal voice (Gemini's baseline).
- [ ] Carry the plain-language verdict (D2) and egress line (D8) into the brief and record.
- [ ] The brief and the record render blockers + minority dissent PROMINENTLY (D11) — never confined to the atlas/transcript, never smoothed away by the plain-language/reading-level layer (D2/D10).
- [ ] Every serious artifact renders dropped/degraded seats visibly (from the per-seat `dropped` field) — a 3→2 board never renders as a clean unanimous board.
Testing: golden renders of all core artifacts from one fixture. Golden assertion that dissent, blockers, and confidence are INVARIANT (D11) — the same minority report, blockers, and confidence string appear in the brief and the record across every audience and reading level, not merely present in one of them; and that the dropped seat in the ragged fixture surfaces in the brief and record bodies.
  - PARTIAL (2026-06-27): the **confidence** half of this invariant has landed for the artifacts that exist today — the board confidence now renders as a verdict-banner pill in the HTML record (`build_handoff_data` → `references/handoff-template.html` `.vconf`), and `TestConfidenceIsProminentInEveryTier` (tests/test_run_board.py) pins it across lenses + the Markdown record + the short formats (tldr/pr/slack). The skim-brief / quick-verdict tier does NOT exist yet, so this box stays open: when that tier is built it MUST carry the same confidence/dissent/blockers golden assertion (the test note flags this).
Gate: `python3 -m unittest discover -s tests -t tests`

### Phase 7 — Derived share formats (after the core)
status: todo
- [ ] Slack / email / PR / PDF as derived projections, sequenced AFTER the core (R6: HTML alone is less shareable for non-devs).
- [ ] Each derived format is a transform of the same source-of-truth (no new content).
Testing: each share format renders from the fixture and matches the core on shared fields.
Gate: `format_output round-trip tests`

## Milestone: Instrument, then decide the flex axis

### Phase 8 — Instrument artifact usage
status: todo
- [ ] Lightweight, local, consent-respecting signal: which artifacts get opened/used across real runs (no external telemetry) — answers "which artifact is the hero" (R1). The one-page brief is the HERO CANDIDATE to validate here (D5).
- [ ] Capture a DISCRIMINATING signal that separates the OD1 forks (not just open/use, which only finds the hero): who the artifact gets forwarded to — the recipient's role vs. the prompter's role. This is the signal that tests Codex's claim that "the artifact must persuade stakeholders beyond the prompter," and it is what lets Phase 9 choose between audience-persona, decision-context/lens, and stay-universal rather than just naming the hero.
- [ ] Gather ~10–15 real non-developer runs (the demand signal the board says is missing — R1).
Testing: an instrumented run records which artifacts were produced and surfaced, AND records a forwarding/recipient-role signal (prompter vs. third party) where one occurs. Concrete check: over a sample run, assert the instrumentation log contains both an open/use event and a recipient-role field, and that the brief is tagged as the hero candidate.
Gate: `instrumentation present on a sample run; open/use + recipient-role captured; privacy-safe`

### Phase 9 — Resolve the flex axis from data (OD1)
status: todo
- [ ] DECISION (OD1): pick the primary flex dimension — audience / decision-context-lens / stay-universal — using Phase 8 evidence, against a pre-stated DECISION RULE, not a priori. OD1 is *deferred to this pre-specified experiment*, not "look at the data later."
- [ ] DECISION RULE (evidence → axis), stated now so Phase 8 is a real experiment: predominant forwarding to third parties / non-prompter roles ⇒ favor decision-context/lens or a stand-alone universal (the artifact must persuade beyond the prompter); usage clustering by prompter type with low forwarding ⇒ favor audience-persona; a single universal bundle satisfying most runs ⇒ stay universal.
- [ ] If adaptation is warranted: deterministic template-selection (D7), ≤1 override on the default path (D5), with single-step selection-input resolution (audience or lens — under the lens branch the lens is already known and needs no acquisition) that fails safe to the universal baseline when ambiguous.
- [ ] Forwardability guard: whatever axis is chosen, the default brief stays third-party-objective in voice (D5) — an audience-persona branch may add a re-voiced variant but must NOT silently re-voice the default away from forwardable/objective.
- [ ] Honor the reading-level floor for high-stakes lenses (OD4) and the "directional review, not advice" label for legal/contract (R4).
Testing: golden renders per selected dimension; the default path still asks ≤1 question; the default brief's voice is unchanged from the Phase-6 third-party-objective baseline (forwardability guard).
Gate: `python3 -m unittest discover -s tests -t tests`

## Risks

- **R1** No demand signal — Building artifacts ahead of evidence. Mitigation: MVP is one universal baseline; instrument before adding any flex dimension (Phases 8–9).
- **R2** Discussion-atlas becomes an ignored wall of text — Both seats warned of a "10,000-word wall … ultimately ignored." Mitigation: guided layer + progressive disclosure (Phase 5); verbatim is one click away, not the front door.
- **R3** Scope creep / configuration matrix — A `persona × decision × mode × format` matrix is "a combinatorial explosion" and "an unmaintainable testing matrix." Mitigation: zero choices at invocation (D5); one axis at most, chosen from data (OD1).
- **R4** Legal/contract artifacts read as legal advice — Mitigation: every artifact in a legal/contract lens is labeled directional review, not advice.
- **R5** Generative variants cost/latency/drift — Each re-voiced variant is a model call. Mitigation: deterministic template-selection for v1 (D7); golden tests.
- **R6** Self-contained HTML is less shareable than email/PDF/Docs — Mitigation: derived share formats sequenced after the core (Phase 7).
- **R7** Plain-language / reading-level simplification smooths dissent away — The D2/D10 reading-level layer could soften or drop the minority report, blockers, or confidence in the brief/record, leaving a falsely tidy result. Mitigation: D11 (dissent/blockers/confidence prominent and invariant in every tier) + the Phase 6 golden test asserting they are invariant across audiences and reading levels.

## Dependency order

```svg
<svg viewBox="0 0 720 240" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" font-size="13">
  <rect x="16" y="96" width="150" height="48" rx="8" fill="none" stroke="#788c5d" stroke-width="2"/>
  <text x="91" y="116" text-anchor="middle" fill="#141413">Foundations</text>
  <text x="91" y="133" text-anchor="middle" fill="#b0aea5">source-of-truth + egress</text>

  <rect x="206" y="24" width="160" height="48" rx="8" fill="none" stroke="#d97757" stroke-width="2"/>
  <text x="286" y="44" text-anchor="middle" fill="#141413">Discussion-atlas</text>
  <text x="286" y="61" text-anchor="middle" fill="#b0aea5">build first</text>

  <rect x="206" y="120" width="160" height="48" rx="8" fill="none" stroke="#141413" stroke-width="2"/>
  <text x="286" y="140" text-anchor="middle" fill="#141413">Universal bundle</text>
  <text x="286" y="157" text-anchor="middle" fill="#b0aea5">zero-choice</text>

  <rect x="406" y="120" width="150" height="48" rx="8" fill="none" stroke="#141413" stroke-width="2"/>
  <text x="481" y="140" text-anchor="middle" fill="#141413">Instrument</text>
  <text x="481" y="157" text-anchor="middle" fill="#b0aea5">~10–15 real runs</text>

  <rect x="586" y="120" width="120" height="48" rx="8" fill="none" stroke="#141413" stroke-width="2"/>
  <text x="646" y="140" text-anchor="middle" fill="#141413">Flex axis</text>
  <text x="646" y="157" text-anchor="middle" fill="#b0aea5">decide from data</text>

  <line x1="166" y1="120" x2="206" y2="48" stroke="#b0aea5" stroke-width="1.5" marker-end="url(#a)"/>
  <line x1="166" y1="120" x2="206" y2="144" stroke="#b0aea5" stroke-width="1.5" marker-end="url(#a)"/>
  <line x1="366" y1="144" x2="406" y2="144" stroke="#b0aea5" stroke-width="1.5" marker-end="url(#a)"/>
  <line x1="556" y1="144" x2="586" y2="144" stroke="#b0aea5" stroke-width="1.5" marker-end="url(#a)"/>
  <defs>
    <marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#b0aea5"/>
    </marker>
  </defs>
</svg>
```

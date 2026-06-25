# Advisory Board — v1.x Plan
> The next four features for the `run_board.py` conductor, after the production-ready v1.0.0.

- **Updated:** 2026-06-25
- **Source:** design/run-board-conductor.md §15 + the 2026-06-25 handoff (scope)
- **Owner:** Tim
- **Baseline:** advisory-board/v1.0.0 + plan view · **M1 shipped (v1.1.0)** · 313 tests green

## Overview
v1.0.0 shipped the full board: **preflight → egress gate → round-1 fan-out → round-2 cross-reading → canonical verdict chain**. The v1.x line sharpens four edges that the M6 proof-of-life run exposed: the board always runs a fixed number of rounds, the verdict is still an agent hand-off rather than one command, `command`-evidence is captured but never re-executed, and the cross-reading digest is coarse.

This cut takes §15's Round-3/`auto` and neutral-synthesizer items, adds `command`-evidence re-execution (deferred to v1.x by §9 / Decision 3) and the smarter cross-reading digest, and defers smart-intake auto-inference and Context Gap Radar to a later v1.x.

This plan is the **source of truth** for that work. Each milestone is its own PR and its own `advisory-board/v1.x` release; the markdown is reviewed line-by-line and this HTML view is rendered from it so the two never drift. **Every milestone gets an adversarial review before merge** — and this plan itself gets one before any code is written.

## Milestone: Round 3 / `auto` stop-rule
status: done
Today the board runs a fixed two rounds. A third round only helps when seats are still *moving* — when round 2 changed minds. `--rounds auto` keeps going while a measurable convergence signal says the debate is live, and stops the moment it goes quiet (or hits a hard ceiling), so we never pay for a round that just restates round 2.

### Phase 1 — Define the convergence signal
The round artifacts (`round-N/<seat>.md`) are the seat's free-form prose, so the conductor must **not** infer a verdict from them — that would be reasoning (§11 / principle 1). The seat emits a machine-parseable token the conductor can diff.
- [x] DECISION: the round template emits one literal `VERDICT: ship|caution|block` line per seat — the model reasons, the conductor only reads the token (this changes the egressed prompt, so `prompt_template_sha` and the prompt version bump)
- [x] DECISION: movement = verdict-token shift + new-citation delta between a seat's round N-1 and N; board-wide movement `< threshold` (or `--max-rounds`) stops
- [x] Add the `VERDICT:` line to the ROUND1/ROUND2 templates and bump the prompt version (`round1@2`/`round2@2`)
- [x] Implement the metric as a pure function over the parsed token + citation set (no prose inference) — `_conductor/convergence.py`
- [x] Decide sane defaults for the threshold and the ceiling — converge when 0 seats move (threshold 1 mover to continue); ceiling `--max-rounds`, default 3
Testing: unit tests on hand-built two-round fixtures (moved / unchanged / mixed); a property test that movement is zero when round N == round N-1; an adversarial fixture where a seat rephrases its prose but the `VERDICT` token is unchanged (must read as *no move*).
Gate: `python3 -m unittest discover -s tests -t tests`

### Phase 2 — Wire `--rounds auto` through the conductor
status: done
- [x] Replace the clamp-to-2 deferral note (`auto`/`3` already parse — `cli.py`/`config.py`/`recipe.py`) with the real round loop
- [x] Loop rounds (the `cmd_run` orchestration calls `run_round` per round) until the stop predicate fires
- [x] Record the per-round movement + stop reason in provenance (`run-metadata.md` `## Convergence` + the tsv `verdict` column)
- [x] A mock run that converges in 2 and one that needs 3 (`moving` mock mode), both deterministic
Testing: end-to-end mock-CLI runs asserting the stop reason and round count; provenance has the movement trace.
Gate: `PATH="$PWD/tests/mocks:$PATH" python3 scripts/run_board.py run --source tests/fixtures/sample-plan.md --rounds auto --out "$(mktemp -d)" --yes`

## Milestone: Neutral synthesizer seat
status: todo
The verdict chain (`verify → consensus → validate`) runs *after* an agent fills `verdict.json` by hand from the round artifacts (§11: synthesis stays a reasoning task). A spawned **neutral synthesizer seat** — a model with no prior round, briefed only on the artifacts — can draft that `verdict.json`, turning the hand-off into one command while keeping a human gate.

### Phase 1 — Synthesizer prompt + seat
status: todo
- [ ] Author the neutral-synthesis prompt (artifacts in, `verdict@2` JSON out, no new opinions)
- [ ] Spawn it as a no-lens seat that reads `round-N/*.md` only
- [ ] Validate its output against the `verdict@2` schema before accepting
Testing: feed the committed example's rounds to the synthesizer mock; assert schema-valid `verdict@2` and that evidence ids resolve.
Gate: `python3 scripts/run_board.py verify /tmp/v.json --run ../../examples/payments-idempotency-review --check`

### Phase 2 — Make it optional + auditable
status: todo
- [ ] `--synthesize` opt-in flag; default stays manual (§11 preserved)
- [ ] Persist the synthesizer's seat artifact + provenance alongside the others
- [ ] Document that the human still gates the abstain/ship call
Testing: a run with and without `--synthesize` produce the same artifact tree shape; the synthesized verdict still passes `--gate`.
Gate: `python3 -m unittest discover -s tests -t tests`

## Milestone: `command`-evidence re-execution
status: todo
`verdict@2` already types `command` evidence, but M5 deferred actually *running* it — those citations stay `unverified`. This milestone lets `verify_evidence.py` re-execute a whitelisted command in the captured run dir and compare output to the claim, moving the citation to `verified`/`refuted`.

### Phase 1 — Safe re-execution
status: todo
- [ ] Allowlist of re-runnable commands (no network, no writes outside the run dir)
- [ ] Capture stdout/exit and diff against the cited expectation
- [ ] Mark the citation `verified` / `refuted` with the observed output attached
Testing: a fixture command that passes and one that fails; assert status transitions and that a non-allowlisted command stays `unverified` with a reason.
Gate: `python3 -m unittest discover -s tests -t tests`

## Milestone: Smarter cross-reading digest
status: todo
Round 2 hands each seat a round-2 packet of the others' round-1 reviews, assembled by `prompts.build_round2_packet`. Under `cross_reading=summaries` each review is head-truncated to a char budget by `prompts._digest`; under `full` the reviews are concatenated verbatim. A structured digest — grouped by claim, with agreements and conflicts surfaced — would replace this, giving round 2 (and the `auto` stop-rule) a sharper signal to debate against.

### Phase 1 — Structure the digest
status: todo
- [ ] Decide scope: does the structured digest replace the `summaries` path only, or `full` too
- [ ] Extract per-seat claims and cluster the overlapping ones
- [ ] Render agreements vs. conflicts, not a raw dump
- [ ] Keep it within the token budget the seats already assume
Testing: golden-file test of the digest for the committed example's round 1; assert conflicts are surfaced and the budget holds.
Gate: `python3 -m unittest discover -s tests -t tests`

## Decisions
- **D1** Markdown stays the source of truth — the HTML view is rendered from it by `render_plan.py` and is never hand-edited, the same rule as `verdict.json → final-consensus.html`.
- **D2** Embed the Claude brand fonts (Poppins + Lora) as base64 in the view — so a plan opens identically offline, with no CDN and no licensing risk (both OFL).
- **D3** The synthesizer seat is opt-in — §11 ("synthesis is a reasoning task") holds by default; `--synthesize` only drafts the verdict, the human still gates ship/abstain.
- **D4** Ship milestone-by-milestone — each feature is its own PR + `advisory-board/v1.x` minor release, each adversarially reviewed before merge.

## Risks
- **R1** Auto-rounds runaway — a board that never converges burns tokens; the `--max-rounds` ceiling and a flagged-large-run prompt are the backstop.
- **R2** Synthesizer smuggles in new opinion — mitigated by schema validation, the no-lens briefing, and keeping the human gate on the final call.
- **R3** Command re-execution side effects — mitigated by the allowlist plus the existing egress/quarantine gate; anything off-list stays `unverified`, never silently trusted.
- **R4** The convergence signal must not make the conductor reason over prose — the round artifacts are free-form, so M1 has each seat emit a machine-parseable `VERDICT:` token and the conductor only diffs tokens + citations (§11 / principle 1). A seat that moves its mind without changing the token is the residual risk; the adversarial-rephrasing fixture in M1 Phase 1 covers it.

## Dependency order
```svg
<svg viewBox="0 0 720 250" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Milestone dependency order: the smarter digest (M4) sharpens the debate signal the auto stop-rule (M1) measures (a soft dependency, shown dashed); M1 then feeds the neutral synthesizer (M2); command re-execution (M3) is independent and can ship any time." font-family="'Poppins',-apple-system,sans-serif">
  <title>Milestone dependency order</title>
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="#b0aea5"/>
    </marker>
  </defs>
  <line x1="222" y1="76" x2="258" y2="76" stroke="#b0aea5" stroke-width="2" stroke-dasharray="4 3" marker-end="url(#arr)"/>
  <line x1="462" y1="76" x2="498" y2="76" stroke="#b0aea5" stroke-width="2" marker-end="url(#arr)"/>

  <g>
    <rect x="42" y="48" width="180" height="56" rx="13" fill="#ffffff" stroke="#d9d7cc" stroke-width="1.5"/>
    <circle cx="60" cy="68" r="4" fill="#b0aea5"/>
    <text x="72" y="72" font-size="13" font-weight="700" fill="#141413">M4</text>
    <text x="58" y="90" font-size="11" fill="#6f6d64">Smarter digest</text>
  </g>
  <g>
    <rect x="282" y="48" width="180" height="56" rx="13" fill="#ffffff" stroke="#d97757" stroke-width="2"/>
    <circle cx="300" cy="68" r="4" fill="#d97757"/>
    <text x="312" y="72" font-size="13" font-weight="700" fill="#141413">M1</text>
    <text x="298" y="90" font-size="11" fill="#6f6d64">Auto stop-rule</text>
  </g>
  <g>
    <rect x="522" y="48" width="180" height="56" rx="13" fill="#ffffff" stroke="#d9d7cc" stroke-width="1.5"/>
    <circle cx="540" cy="68" r="4" fill="#b0aea5"/>
    <text x="552" y="72" font-size="13" font-weight="700" fill="#141413">M2</text>
    <text x="538" y="90" font-size="11" fill="#6f6d64">Neutral synthesizer</text>
  </g>
  <g>
    <rect x="282" y="158" width="180" height="56" rx="13" fill="#ffffff" stroke="#d9d7cc" stroke-width="1.5"/>
    <circle cx="300" cy="178" r="4" fill="#b0aea5"/>
    <text x="312" y="182" font-size="13" font-weight="700" fill="#141413">M3</text>
    <text x="298" y="200" font-size="11" fill="#6f6d64">Command re-exec</text>
  </g>
  <text x="372" y="234" font-size="10.5" fill="#9b988d" text-anchor="middle" font-style="italic">M3 is independent — ships any time</text>
</svg>
```

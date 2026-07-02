# Advisory Board — Roadmap v1.11 → v1.15
> Fourteen features in five releases: transparency first, then the decision loop, the transform artifact, signal quality, and rubric-first deliberation.

- **Updated:** 2026-07-02
- **Source:** 2026-07-01 four-agent review (feature surface · conductor architecture · artifacts/examples · market scan) + Tim's selection of items 1–14 from the ranked slate
- **Owner:** Tim
- **Baseline:** advisory-board/v1.10.0 · `main` @ `be4c9b2` · 676 tests green
- **Status:** M1 SHIPPED (`advisory-board/v1.11.0`, 2026-07-01) · M2 SHIPPED (`advisory-board/v1.12.0`, 2026-07-02) · M3 SHIPPED (`advisory-board/v1.13.0`, 2026-07-02 — P1 D9–D14 · P2 PR #67 · P3 PR #68 · P4 PR #69) · M4 (v1.14) next — severity filters first

## Overview

The 2026-07-01 review found the board strong where the market is weak — genuine multi-vendor independence, multi-round debate with convergence detection, minority reports, evidence verification, polished self-contained HTML — and weak *around* the run: every run is one-shot (no follow-up, no re-review, no history; artifacts default to `/tmp`), the verdict only informs (never hands back a fixed copy), and a 10–20-minute premium-model run is a black box on cost and time. The market scan grounds each fix: cost anxiety and setup friction are the loudest complaints against llm-council-style tools; one-click "apply the review" is the proven adoption lever next door in code review; and no council tool does document transformation at all.

This roadmap ships the fourteen chosen items as five milestone releases, batched by dependency rather than by rank: **v1.11** lays substrates (persistent runs, structured digest) and the transparency story; **v1.12** turns one-shot verdicts into a decision loop (`--revise`, `ask`, amendments) behind a single additive schema evolution; **v1.13** crosses inform→transform (board-endorsed revision); **v1.14** is signal quality and run experience; **v1.15** is rubric-first deliberation, deliberately last because it touches every pipeline stage.

This markdown is the **source of truth**; the HTML view is rendered from it by `render_plan.py` and never hand-edited. Each phase is one PR-sized unit: implemented with tests, adversarially reviewed before commit, merged, and logged under `## [Unreleased]` in the skill CHANGELOG. Each milestone ends with a human-gated release (changelog section on `main` **before** the tag). The `/goal` skill (user-level, this machine) drives the loop: it picks the next unchecked item here, runs the pipeline, updates this plan + the HTML + the handoff, and stops at release gates.

**Standing invariants (every milestone).** (1) A default run — no new flags, tokens unreported — stays **byte-identical** to baseline artifacts; every feature here is opt-in or additive. (2) The consent/egress surface never loosens: new packet content (prior verdicts, follow-up questions, revision drafts) is hash-bound and disclosed like any other egress. (3) §11 holds — the conductor plumbs, the models reason; anything that merges meaning (rubric merge, revision drafting) is a seat's job, not code. (4) The suite stays green at every gate; frontier model ids stay inline.

## Milestone: v1.11 — Transparency & foundations

Know before you convene: what a run will cost and how long it takes, plus the substrates later milestones need (persistent runs for lineage, structured digest for tooling) and the small gap-fills. All items are Small and independent; PRs may land in any order but merge sequentially.

### Phase 1 — Cost & time capture + preflight estimate (#3a)
Capture what each seat actually spent and predict it before launch — always best-effort, never a gate.
- [x] Per-seat token capture: `tokens_in`/`tokens_out` (nullable) on `SeatRoundResult`; per-adapter output parsers in `registry.py` (claude first; codex/gemini/antigravity/ollama best-effort, else unknown — never guess) _(PR #53)_
- [x] Pricing table in `constants.py` keyed by model id (frontier ids inline, dated) + a pure `estimate_run()` (source bytes × seats × rounds × cross-reading) surfaced by `--dry-run` and the existing large-run warning _(PR #53)_
- [x] Render: per-seat tokens/cost columns in `run-metadata.tsv`, a cost/time line in `run-metadata.md` and the `final-consensus.html` footer, all with explicit "if known / estimate" wording _(PR #53)_
Testing: parser fixtures per CLI; estimator pure-function tests; unknown-tokens run renders byte-identical to baseline.
Gate: `cd skills/advisory-board && python3 -m unittest discover -s tests -t tests`

### Phase 2 — `--tier quick|standard|deep` presets (#3b)
One flag that sets the whole cost/depth posture.
- [x] Tier presets resolved in `config.py` **before** per-flag overrides (quick: 1 round, `summaries`, reduced per-seat reasoning — claude `high`, codex `medium`; standard: today's defaults; deep: 3 rounds, `full`, registry max-tier reasoning, codex capped at `xhigh`); explicit flags always win; `run-recipe.yaml` records the **resolved values**, never the tier name, so replay stays exact. _Deviation (per D7): quick dials reasoning, NOT "budget models" — model ids stay pinned; an unverified budget id could 404 the board._ _(PR #57)_
- [x] Docs: SKILL.md cost-posture bullet + cost guidance; tier shown in run-metadata provenance (+ template note; the `--digest-format json` refusal names the tier when the tier caused it) _(PR #57)_
Testing: precedence matrix (tier vs explicit flags vs recipe replay); no-tier runs unchanged.
Gate: full suite.

### Phase 3 — Run history & persistent runs root (#5)
Runs stop evaporating.
- [x] Persistent default runs root (`~/.advisory-board/runs/<slug>-<date>/`), opt-out flag/env; `data-handling.md` notes that persisted artifacts inherit the run's sensitivity handling _(PR #52)_
- [x] `run_board.py history` — table (title, date, verdict, confidence, unanimous, seats) read from each run's `verdict.json` + `run-metadata`; degrades gracefully on partial/legacy runs _(PR #52)_
Testing: history over fixture runs incl. a partial one; root override honored end-to-end.
Gate: full suite.

### Phase 4 — Setup doctor (#7)
The preflight, proactively, for a brand-new user.
- [x] `run_board.py doctor` sweeps **every** REGISTRY provider (installed → version/currency → auth → model resolves), prints per-provider fix-it steps (reusing preflight/toolchain probes) + a suggested first command; summarizes which boards are viable today (≥2 GO) _(PR #50)_
Testing: mocked probes cover GO / NO-GO / not-installed / stale-CLI paths.
Gate: full suite.

### Phase 5 — Structured digest + gap-fills (#13, #14)
- [x] `--digest-format markdown|json`: emit the round-2+ board packet's sections/agreement/citations as typed JSON alongside the markdown (same parsed signals, no new reasoning) _(PR #51)_
- [x] `--timeout id=SECONDS` per-seat override threading through to spawn _(PR #51)_
- [x] Make `--output implementation-sequence` a real distinct render (sequence-first view from `next_actions[]`/blockers), not an alias of full-handoff _(PR #51)_
Testing: digest JSON golden file; timeout reaches the spawn call; new output-shape snapshot.
Gate: full suite.

### Phase 6 — Reconcile & release v1.11
- [x] CHANGELOG `v1.11.0` section reconciled and landed on `main` before tagging (runs-root re-homed to Changed, `history` to Added) _(PR #58)_
- [x] Tag `advisory-board/v1.11.0` on Tim's **explicit go** (given 2026-07-01) → `release.yml` green, release published as Latest, body = changelog section
Gate: `gh release view advisory-board/v1.11.0` shows Latest + full suite green.

## Milestone: v1.12 — The decision loop

One-shot verdicts become an ongoing advisory relationship: re-review a revised draft with a verdict delta, ask the board follow-ups, and amend a verdict with recorded human provenance. All three touch the verdict lifecycle, so the milestone opens with a single additive schema evolution instead of three ad-hoc bumps.

### Phase 1 — Verdict-lifecycle schema design
- [x] DECISION: one additive evolution of `advisory-board/verdict@2` — optional `previous_run` lineage, optional `amendments[]` (append-only; author/timestamp/reason), and a reserved pointer for v1.13's `changes` — with a compatibility test proving existing verdicts still validate and gate identically. _Recorded as D8: fields live inside `@2` (no version bump); tool/human-authored — the synthesizer merge strips them; `changes` refused loudly until v1.13._ _(PR #61)_
- [x] `references/verdict-schema.md` + `board_verdict.py` validation extended; no renderer breaks on absent fields — byte-identity test-proven on present fields too (consensus md, sequence, handoff data, tldr/pr/slack) _(PR #61)_
Testing: old fixture verdicts validate unchanged; new-field round-trip.
Gate: full suite.

### Phase 2 — `--revise`: re-review with a verdict delta (#1)
- [x] `--revise <prior run dir|verdict.json>` loads the prior recipe + verdict, replays board/lenses/models, and injects a **prior-verdict digest + source diff** into the round-1 packet (consent hash covers every added byte; disclosure on the consent line, manifest, and sensitivity.json; stricter-prior-sensitivity refused; material byte-neutralized; recovery sha-verified with `source-material.txt` now persisted per run) _(PR #63)_
- [x] `delta.py`: pure matching of blockers/concerns across runs (citations, title similarity — mechanical only, global tier passes) → cleared / still-open / new + verdict trajectory _(PR #63)_
- [x] Delta section in `final-consensus.md`/`.html` (trajectory banner: e.g. BLOCK → SHIP, lens-aware labels) + `previous_run` recorded by the conductor _(PR #63)_
Testing: delta pure-function matrix; end-to-end revise on a fixture pair; consent-hash coverage test.
Gate: full suite.

### Phase 3 — `ask`: post-verdict cross-examination (#4)
- [x] `run_board.py ask "<question>" --run <dir> [--seat <id>]` — context packet built from the run's own artifacts, egress re-consent for the new bytes, one-round fan-out to the addressed seat(s), `addendum-N.md` + handoff refresh. _Hardened per the adversarial review: never-loosen sensitivity floor (strictest of recipe / sensitivity.json / tighten-only `--sensitivity`; missing sensitivity.json never floats down to public), dropped-placeholder skip for seat continuity, sentinel-injection-proof handoff block, bounded reads (symlink/out-of-tree refused)._ _(PR #65)_
Testing: packet content bounded to the named run; seat targeting; re-consent required on sensitive runs.
Gate: full suite.

### Phase 4 — Amendments: human-owned verdict tuning (#11)
- [x] `board_verdict.py amend --run <dir>` appends to `amendments[]` (confidence change, added caveat, severity note) — never edits board fields in place; gate and renderers show amended values **with** provenance. _Hardened per adversarial review — parallel finder subagents plus a dogfooded two-seat board run (gpt-5.5 xhigh + Opus 4.8, unanimous caution), all findings fixed: markdown newline injection collapsed, defensive `effective_confidence`, symlink-preserving unique-tmp atomic write + sha256 concurrency guard, chain-consistency validation (hand-edited false provenance refused), full-handoff HTML byte-identity restored._ _(PR #66)_
Testing: amend round-trip; gate reflects amendment; render marks human provenance.
Gate: full suite.

### Phase 5 — Docs, review, release v1.12
- [x] SKILL.md + references updated (revise/ask/amend); CHANGELOG section on `main`; adversarial-review debts closed _(docs verified covering all three features; every must-fix finding from the P2/P3/P4 reviews fixed in-phase; LOW leftovers parked in ## Later by design; `## [v1.12.0]` landed on main `10b6969` before the tag)_
- [x] Tag `advisory-board/v1.12.0` on Tim's explicit go → release green _(go given 2026-07-02; release published + Latest, workflow green, suite 980 OK)_
Gate: release Latest + full suite green.

## Milestone: v1.13 — Transform: the board hands back a fixed copy

Inform → transform. A revision seat produces a board-endorsed revised copy of the source — redline for documents, patch for code — each edit annotated with the finding it resolves. Artifact-only: the user's source file is never written. Per the artifact-features convention, design decisions are settled by a dogfood roundtable before code.

### Phase 1 — Dogfood design roundtable
- [x] Run the advisory board on the fix-it design brief; record decisions: redline format per source type, `changes.json` shape (edit → finding mapping), endorsement-pass shape and default, failure posture when findings conflict _Recorded as D9–D14. Roundtable 2026-07-02: 3 seats (claude-opus-4-8 · gpt-5.5 · gemini-3.5-flash), 2 rounds + claude synthesizer — unanimous SHIP WITH CHANGES @ high confidence, 5 blockers, all folded into the decisions; brief at `design/v1.13-fixit-revision-artifact-design-brief.md`, fact sheet at `design/v1.13-fixit-design-inputs.md`._
Testing: n/a (design phase); decisions land in this plan + Decisions below.
Gate: decisions recorded here before Phase 2 starts.

### Phase 2 — Revision seat + `changes.json` (#2)
- [x] `--output revised-draft`: after synthesis, spawn a revision seat (generalizing the synthesizer spawn path) with source + `verdict.json`; emits the `changes` mapping first, revised text second, in one spawn (D11) — `changes.json` keyed by composite `{list, index, title}` finding locators (D9; the roundtable struck the "blocker/concern ids" phrasing — no ids exist and none are introduced) _Reviewed by 2 finder agents + a 2-seat dogfood board AND its `--revise` re-review (first real use of the v1.12 loop): 4 board blockers fixed, 1 re-review blocker (byte-clean vs LF-normalization) fixed per the board's prescribed option. Suite 980 → 1118._ _(PR #67)_
Testing: revision honors verdict scope; changes.json schema round-trip; source file untouched.
Gate: full suite.

### Phase 3 — Redline rendering + inline citation snippets (#2, #12)
- [x] Redline view: stdlib `difflib` opcodes → ins/del spans in the HTML engine for prose sources; unified `.patch` artifact for code sources _Sha-verified chain (pointer → changes → draft + source-material equivalence), word-level spans, git-marker-correct patches (`git apply` result-byte tested), body byte-identity enforced._ _(PR #68)_
- [x] Grounded runs: embed cited lines as fenced snippets in `final-consensus.md` so the handoff is self-contained (#12) _Captured at verify time (repo bytes don't survive a run — self-contained AFTER verify); content read gate (symlink refusal + realpath containment) + whitelist-only manifest gate, fail-closed on unusable manifests. Board review: 2 finders + 2-seat board + `--revise` re-review (3 blockers cleared, 1 fail-open caught in the fix and closed). Suite 1118 → 1209._ _(PR #68)_
Testing: redline golden files (prose + code); snippet embedding on a grounded fixture.
Gate: full suite.

### Phase 4 — Endorsement pass, docs, review, release v1.13
- [x] One-shot endorse/object pass by non-revision seats — ON by default for `--output revised-draft`, parallel fan-out, `--no-endorse` opt-out (D13) — recorded per seat in `changes.json` _Per-edit AND per-unresolved votes, conductor-built rows, id-axis seat identity (duplicate-provider boards disambiguated), honest egress wording, dropped-row contract validator-enforced. Board review → `--revise` re-review: 5 blockers cleared → unanimous SHIP WITH CHANGES @ high confidence. Suite 1209 → 1282._ _(PR #69)_
- [x] Docs + CHANGELOG on `main`; tag `advisory-board/v1.13.0` under Tim's standing release go (2026-07-02, v1.13–v1.15) → release green _CHANGELOG `## [v1.13.0] - 2026-07-02 — Transform: the board hands back a fixed copy` landed on main (`367928e`) before the annotated tag; release workflow verified green._
Gate: release Latest + full suite green.

## Milestone: v1.14 — Signal quality & run experience

Noise controls, a quantified independence story, and something to watch during a 15-minute run.

### Phase 1 — Severity filters (#8)
- [ ] `--filter blockers|blockers+dissent|all` on `render_verdict.py`/`format_output.py`; `--min-severity` option on the `board_verdict.py --gate` path (schema already separates blockers/concerns/caveats — this is exposure, not new modeling)
Testing: filter matrix over a rich fixture verdict; gate threshold behavior.
Gate: full suite.

### Phase 2 — Independence / echo score (#9)
- [ ] Add a parseable evidence-vs-deference token to the round-2 template (the independence check `epistemics.md` documents; prompt-template version bump); pure metric over parsed signals only (verdict-flip correlation, citation overlap, deference count) → score + one-line explanation in `run-metadata.md` + an HTML pill
- [ ] DECISION in-phase: metric definition published in `epistemics.md` with its limits (no pseudo-precision; it flags echo, it doesn't prove independence)
Testing: metric pure-function matrix incl. adversarial same-provider boards.
Gate: full suite.

### Phase 3 — Live progress view (#10)
- [ ] Status events (seat × round state transitions) written to a `status.json` in the run dir as they happen; terminal per-seat progress lines from it; optional self-refreshing HTML tracker page reading the same file
Testing: event sequence golden on a mocked run; tracker renders from fixture status.
Gate: full suite.

### Phase 4 — Docs, review, release v1.14
- [ ] Docs + CHANGELOG on `main`; tag `advisory-board/v1.14.0` on Tim's explicit go → release green
Gate: release Latest + full suite green.

## Milestone: v1.15 — Rubric-first deliberation

Seats agree weighted criteria before opining, score per criterion, and converge on scores — with an optional audience/stakeholder panel preset. Deliberately last: it touches prompts, rounds, convergence, schema, gate, and render. **The checklists below are intentionally coarse — Phase 1 rewrites this milestone in place before any code.**

### Phase 1 — Full design pass
- [ ] Grilling + dogfood roundtable on the rubric design: who proposes criteria, who merges (a chair seat — merging is reasoning, §11), how scores map to ship/caution/block, what `--rubric` opts into, schema scorecard shape; rewrite M5 phases from the outcome
Gate: this milestone's phases re-authored and reviewed before implementation.

### Phase 2 — Rubric round + chair merge
- [ ] Placeholder (defined by Phase 1)
### Phase 3 — Scoring rounds + score-based convergence
- [ ] Placeholder (defined by Phase 1)
### Phase 4 — Schema, gate, scorecard render
- [ ] Placeholder (defined by Phase 1)
### Phase 5 — Docs, review, release v1.15
- [ ] Docs + CHANGELOG on `main`; tag `advisory-board/v1.15.0` on Tim's explicit go → release green
Gate: release Latest + full suite green.

## Decisions
- **D1** Markdown is the source of truth — this file drives the HTML via `render_plan.py`; checkbox state computes every badge; the plan is updated in the same PR as the work it describes.
- **D2** One verdict-schema evolution, additive-only — v1.12 Phase 1 designs `previous_run` + `amendments[]` (+ a reserved `changes` pointer for v1.13) together; existing `verdict@2` consumers keep validating; append-only amendments mean no silent edits ever.
- **D3** Ship milestone-per-release, phase-per-PR — every code PR is adversarially reviewed before merge (`REVIEWED=1` commits), logs under `## [Unreleased]`, and the changelog section lands on `main` **before** the tag (release.yml hard-fails otherwise). Releases are outward-facing: every tag waits for Tim's explicit go.
- **D4** Cost is best-effort, never a gate — token parsers are per-CLI and may return unknown; estimates are labeled estimates; pricing lives in one dated table with frontier model ids inline.
- **D5** Everything is opt-in or additive — the no-flags default run stays byte-identical to v1.10.0 artifacts (the regression guard for the whole roadmap), except the runs root moving out of `/tmp`, which is loudly documented and opt-out.
- **D6** Transform never touches the source — `--output revised-draft` writes new artifacts only; applying the revision is the human's act.
- **D7** Estimates date from the 2026-07-01 architecture review — each milestone re-scopes in its first phase; drift is corrected in this file, not in heads.
- **D8** Verdict-lifecycle fields live inside `@2`, not a new `@3` — `previous_run` + `amendments[]` are optional, validated strictly only when present, and invisible when absent, so every existing consumer and file is untouched; `@3` stays reserved for a genuinely structural break. The fields are tool/human-authored: the synthesizer merge strips them (a model must not fabricate provenance), the gate never reads them, and the reserved `changes` key is refused loudly until v1.13 defines it.
- **D9** Edits are keyed by composite locator, and only real findings are resolvable — `changes.json` references findings as `{list, index, title}` with a conductor equality-assert (an index/title mismatch, or a duplicate title among resolvable findings, is refused at revision time), after the roundtable unanimously rejected title-only joins for machine provenance: unlike `amend --on` there is no human at hand to disambiguate a collision, and no duplicate-title guard exists anywhere. No `id` field enters `@2` — Codex's preference for conductor-assigned ids and Gemini's sequential-string variant (`blocker-1`) are recorded dissents; the composite is the board's agreed minimum, and a second schema evolution in two releases was ruled premature. `resolves.list` covers `blockers` and `concerns` only: `caveats[]` is a plain-strings bucket with no titles or evidence (the brief's structured-caveats framing was a vocabulary error the board caught against `EVIDENCE_CONTAINERS`), and dissent entries are not editable findings (Claude's dissent-inclusive enum declined 2–1). _(v1.13 P1 roundtable, 2026-07-02)_
- **D10** `changes.json` is the artifact of record; `verdict.json` carries only a tool-authored pointer — schema `advisory-board/changes@1` gets its own strict validator (mirroring `board_verdict.py` discipline): model-authored fields are limited to `summary`/`resolves`/`note`; the conductor computes `n`, statuses, and shas, and enforces completeness (every blocker either resolved by an edit or listed in `unresolved`; concerns best-effort). Edit locators reconcile 1:1 against the mechanical original→revised diff (INV-1: every locator falls inside a real hunk or a legal insertion anchor, every hunk is claimed by ≥1 edit, `status: "applied"` is conductor-computed from the diff and never model-asserted; reconciliation failure takes the reject path). The reserved `changes` key is consumed as `{artifact, sha256}` — an acyclic pin (verdict→changes→{source, revised}, never mutual) written with `amend`'s lost-update discipline; Gemini's late-write alternative (hold the verdict in memory, write `verdict.json` once at pipeline end, never reopen) is a recorded dissent, and file-only is the fallback if the pointer write can't be made race-safe. _(v1.13 P1 roundtable, 2026-07-02)_
- **D11** The revision seat is one spawn, generalized from the synthesizer, and refuses loudly rather than truncating silently — `--output revised-draft` builds its own dispatch (`_run_revision_step()` after synthesis; `--output` was decorative before v1.13) and **requires** a verdict path at resolve time (`--synthesize` or a synthesized recipe re-run) — a revision seat improvising findings from raw reviews would put a model where the conductor's skeleton belongs. The single spawn returns the `changes` mapping FIRST and the revised draft second (a truncated reply then fails mechanically on the missing closing fence), behind the synthesizer's fence/neutralize machinery and retry set — an unclosed DATA fence classifies `invalid` and retries. A source-size preflight refuses oversized revisions loudly (threshold fixed in P2): better a loud refusal at resolve time than a silently short board-endorsed copy. Failure mirrors the synthesizer exactly: `revised-draft-rejected.*` + `changes-rejected.json`, loud warning, exit 0 (`--strict-exit` → 4). _(v1.13 P1 roundtable, 2026-07-02)_
- **D12** Redline by source type; the applied file is byte-clean — prose vs code resolves by extension heuristic with `--source-type prose|code` override, the resolved value recorded in the recipe and printed on the run card; unknown extensions and stdin refuse without the flag (URL sources are already refused at load, so the brief's url clause was moot). Prose: `revised-draft.md` plus a word-level-within-changed-lines `<ins>/<del>` redline in the HTML handoff via stdlib `get_opcodes()`; code: `revised-draft.<orig-ext>` plus an apply-able unified `.patch`; no text-format redline artifact (no seat wanted one). The board unanimously struck the strawman's metadata header from the drafts: `revised-draft.*` contains the revised source bytes and nothing else — a header corrupts code the moment it is saved — the `changes.json.revised` sha256 must match the file on disk exactly, and run metadata lives in `changes.json`, the HTML handoff, and the run card instead. _(v1.13 P1 roundtable, 2026-07-02)_
- **D13** Endorsement is ON by default and concurrent — un-endorsed, "board-endorsed" is marketing and R4 bites, so every `--output revised-draft` run fans the non-revision seats out in parallel (the existing rounds `ThreadPoolExecutor`; wall-clock ≈ one extra round — the round-1 "+40–60%" objection was a token-cost figure miscast as latency, and its author reversed) for a one-shot per-edit `ENDORSE`/`OBJECT`/`ABSTAIN` with optional note, recorded as `{seat, edit_n, position, note}` rows in `changes.json.endorsements`; failed endorsement spawns record as ABSTAIN/dropped rows, `unresolved` entries are endorsement targets too (a seat may object to how a conflict was characterized), and objections are recorded, never resolved by another model loop — the human reads them and decides (D6). `--no-endorse` is the opt-out for the genuine token-cost axis. _(v1.13 P1 roundtable, 2026-07-02)_
- **D14** Conflicting findings degrade loudly, never silently and never fatally — the revision seat applies the non-conflicting edits and surfaces each conflict as an `unresolved` entry naming the findings involved and its one-paragraph reason; the run card, consensus render, and HTML handoff all state the unresolved count. Content never moves exit codes (they stay about pipeline integrity; `--strict-exit` unchanged). Refusing to revise on any conflict and silently picking a side were both rejected — the first is useless on rich verdicts, the second launders an editorial choice as board consensus. _(v1.13 P1 roundtable, 2026-07-02)_

## Risks
- **R1** CLI-wiring merge conflicts across parallel v1.11 PRs — the five phases are file-disjoint except arg parsing; mitigation: sequential merges, each later branch rebases before merge.
- **R2** Token parsers rot as CLIs update — best-effort fields default to unknown; `flags_verified_version` discipline extends to output formats; a parser miss degrades to "cost unknown", never a wrong number.
- **R3** `--revise` packet growth (source + diff + prior verdict) — mitigation: quick-verdict-sized prior digest, not the full handoff; token budget checked like any round-2 packet.
- **R4** Fix-it reads as the board rewriting your work — artifact-only output, explicit opt-in flag, endorsement recorded per seat, and the human applies changes themselves (D6).
- **R5** Rubric-first destabilizes the default path — strictly opt-in behind `--rubric`; the byte-identical default-run guard (D5) is the regression net; own design phase before code.
- **R6** Fourteen items invite scope creep — anything discovered mid-milestone goes to a "later" note in this file, not into the current phase; the roadmap only grows by PR.

## Later
Discovered mid-milestone (R6), deliberately not folded into the phase that found it:
- `--rounds 1` (incl. via `--tier quick`) + `--digest-format json` is a silent no-op — structured digests only exist for round 2+, so the run succeeds with zero JSON digests written. Pre-existing (#13); decide whether to refuse loudly or document. _(found during #3b adversarial review, 2026-07-01)_
- `board_verdict.py` membership checks on hand-authored files crash with a raw TypeError (exit 1, not the clean schema exit 2) when a token field holds an unhashable value — e.g. top-level `"verdict": []`, `round_verdicts` entries, evidence `kind`/`status`. Pre-existing idiom across the file (the new lifecycle checks guard against it); sweep the remaining membership checks with isinstance guards in one pass. _(found during v1.12 P1 adversarial review, 2026-07-01)_
- Delta-render trust: `previous_run.run_dir` in a verdict.json is an arbitrary local path the renderer reads at render time (sha-gated when `verdict_sha256` is recorded, but the field is optional) — a hostile shared verdict could point it anywhere for a spoofed/cosmetic delta or a file-exists oracle. Consider requiring the sha for delta rendering, or a run_dir sanity check. _(v1.12 P2 security review, LOW, 2026-07-01)_
- Delta similarity tier can still pair parallel-but-different titles ("Add index on users" / "Add index on orders" share a token + high ratio). Mechanical limit, honestly rendered (both lists shown); revisit only if real runs mis-pair. _(v1.12 P2 correctness review, LOW, 2026-07-01)_
- `revise.py` shares three hardening gaps whose `ask`-side twins were fixed in P3: `_prior_sensitivity` crashes (raw AttributeError) on a non-object `sensitivity.json`; `_load_prior_verdict` crashes (raw TypeError) on a scalar-JSON verdict; `prior_source_text`'s prompt extraction checks `islink` per file but not a symlinked `prompts/` PARENT dir (sha-gated, so not exploitable today — the attacker would already need the exact bytes). Sweep all three with the ask-side patterns (isinstance guards + realpath containment) in one pass. _(v1.12 P3 adversarial review, LOW, 2026-07-02)_
- `board_verdict.py load()` catches only FileNotFoundError/JSONDecodeError — a path through a non-directory (NotADirectoryError), an unreadable file (PermissionError), etc. still crash legacy invocations with a raw traceback instead of the clean exit 2 (`amend` now pre-checks its own `--run`; the legacy positional path does not). Widen to OSError in the same sweep as the membership-check note above. _(v1.12 P4 adversarial review, LOW, 2026-07-02)_
- `render_handoff.py drop_empty_optionals`: the PRE-existing optional-block drops (seat-status / highlight / conf) leave a whitespace-only line behind because their regexes don't consume the preceding template authoring comment — the P4 blocks got the tempered-comment fix; old vs new output is identical (both carry the artifact), so this is cosmetic template-engine debt only. _(v1.12 P4 compat review, LOW, 2026-07-02)_
- An extensionless code source (e.g. `Makefile`) under `--source-type code` falls back to `revised-draft.txt`, losing the original name — consider preserving the source basename for the revised artifact. _(v1.13 P2 board re-review, LOW, 2026-07-02)_
- Exotic Unicode line separators (` `, `\f`) could desync a model's line numbering from `splitlines()`'s — the locator convention is documented against `splitlines()`; revisit only if real runs mis-anchor. _(v1.13 P2 board re-review, LOW, 2026-07-02)_
- The revision path's duplicate-title refusal is arguably vestigial now that refs carry `index` (the cross-assert disambiguates); a verdict with two same-titled blockers currently can't be revised at all — consider relaxing to a warning. _(v1.13 P2 board re-review, LOW, 2026-07-02)_
- Byte-exact (non-LF-normalized) source support for `revised-draft`: CR/CRLF sources are refused loudly today because the pipeline reads the source and captures seat replies with universal-newline translation end to end; add a byte-exact path only if demand shows. _(v1.13 P2 board re-review, LOW, 2026-07-02)_

## Dependency order
```svg
<svg viewBox="0 0 880 170" xmlns="http://www.w3.org/2000/svg" font-family="sans-serif" font-size="12">
  <defs>
    <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#8b95a7"/>
    </marker>
  </defs>
  <g fill="none" stroke="#8b95a7" stroke-width="1.5">
    <line x1="168" y1="60" x2="196" y2="60" marker-end="url(#arr)"/>
    <line x1="344" y1="60" x2="372" y2="60" marker-end="url(#arr)"/>
    <line x1="520" y1="60" x2="548" y2="60" marker-end="url(#arr)"/>
    <line x1="696" y1="60" x2="724" y2="60" marker-end="url(#arr)"/>
    <path d="M 96 84 C 96 130, 250 130, 262 84" stroke-dasharray="4 3" marker-end="url(#arr)"/>
    <path d="M 120 84 C 120 150, 600 150, 616 84" stroke-dasharray="4 3" marker-end="url(#arr)"/>
  </g>
  <g>
    <rect x="20" y="36" width="148" height="48" rx="9" fill="#eef1f6" stroke="#8b95a7"/>
    <text x="94" y="56" text-anchor="middle" font-weight="bold">M1 · v1.11</text>
    <text x="94" y="72" text-anchor="middle">cost · history · doctor</text>
    <rect x="196" y="36" width="148" height="48" rx="9" fill="#eef1f6" stroke="#8b95a7"/>
    <text x="270" y="56" text-anchor="middle" font-weight="bold">M2 · v1.12</text>
    <text x="270" y="72" text-anchor="middle">revise · ask · amend</text>
    <rect x="372" y="36" width="148" height="48" rx="9" fill="#eef1f6" stroke="#8b95a7"/>
    <text x="446" y="56" text-anchor="middle" font-weight="bold">M3 · v1.13</text>
    <text x="446" y="72" text-anchor="middle">fix-it · redline</text>
    <rect x="548" y="36" width="148" height="48" rx="9" fill="#eef1f6" stroke="#8b95a7"/>
    <text x="622" y="56" text-anchor="middle" font-weight="bold">M4 · v1.14</text>
    <text x="622" y="72" text-anchor="middle">filters · echo · live</text>
    <rect x="724" y="36" width="136" height="48" rx="9" fill="#eef1f6" stroke="#8b95a7"/>
    <text x="792" y="56" text-anchor="middle" font-weight="bold">M5 · v1.15</text>
    <text x="792" y="72" text-anchor="middle">rubric-first</text>
    <text x="200" y="128" fill="#5b6472">runs root (#5) → revise/ask lineage</text>
    <text x="330" y="152" fill="#5b6472">json digest (#13) → live progress (#10)</text>
  </g>
</svg>
```

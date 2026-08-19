# Changelog — advisory-board

All notable changes to the `advisory-board` skill are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Releases are
cut as **skill-scoped semver tags** `advisory-board/vX.Y.Z` (see [`RELEASING.md`](../../../RELEASING.md)).
The skill follows SemVer; its artifact schemas (for example `advisory-board/verdict@N`) are
versioned separately and do not replace the skill release version.

## [Unreleased]

### Security
- **`verify_evidence.py` re-execution now pins arguments, not just the program** (#243,
  surfaced by CodeRabbit on PR #242): `--allow-program NAME` alone used to re-run a
  `command` citation with whatever arguments it carried, and the command text is
  model-authored, so an untrusted seat could smuggle hostile arguments to an allowed
  program (`pytest --rootdir=... -p plugin`, `git -c core.pager=...`). Now
  `--allow-program` alone permits only the bare program with no arguments; a command
  carrying any argument must also `re.fullmatch` an `--allow-command` pattern. A refused
  command stays `unverified` with a `status_reason` naming the missing pattern.
  Regression tests cover the hostile-argv case at the `command_allowed`, `resolve_command`,
  and `main()` layers (nothing executes, no `observed` receipt).

### Fixed
- **`use defaults` no longer reads as a way past the doctor preflight** (#244, surfaced by
  CodeRabbit on PR #242): `intake-interview.md` and SKILL.md said the fast path "jumps
  straight" to the step-6 confirm card, which let a run launch with an unconfirmed or
  unavailable seat. Both now state that `use defaults` resolves steps 2-5 to defaults only
  after step 1 completes and its findings are applied to the card; a seat that is not GO is
  never offered as a default. Doc-only: the conductor scripts have no intake path and never
  encoded the jump.

### Changed
- **Readability pass on the opening paragraph** (#227): the single dense mode sentence is
  now one plain sentence per mode; every fact (mode names, the default, the intake
  reference, the per-mode shapes) is unchanged. Frontmatter description untouched.
- **Em-dash sweep** (#226): SKILL.md and all thirteen references rewrote their
  em-dash constructions into periods, commas, colons, or restructured sentences,
  meaning-preserving: every Must-Not and schema rule keeps its exact force, and
  bold-label list separators became "**X**: explanation" per file. Untouched by
  design: code blocks, the CLI prompt templates (their bytes must keep matching
  the conductor's shipped templates and `prompt_template_sha256`), and literal
  output strings such as the severity filter's elision line (the `— --filter`
  form `_severity_filter.py` actually emits). Guarded by
  `scripts/check_emdash_density.py` in CI.

### Added
- **Competitive mode: optional graft-and-verify close** (`references/modes.md` §Competitive),
  off by default and opted into at intake with its extra cost named on the card. After
  Pitch → Critique → Vote, the conductor reads the shape of the field first (convergence
  means ship the consensus with no graft; wild divergence means the brief was
  under-specified, so reframe and re-run), then takes the winning pitch as base, grafts
  the strongest separable ideas from the losing pitches (each graft a discrete,
  attributable change put to the non-winning seats for a per-graft
  `ENDORSE`/`OBJECT`/`ABSTAIN` vote, per the revised-draft convention), records grafts,
  sources, and above all the rejection notes, and re-verifies the synthesis under the same
  scrutiny as any seat output; winning the tournament earns no pass. New artifact:
  `synthesis.md`. The tally, `results.md`, and the no-`verdict.json` rule are unchanged,
  and the intake wizard (`references/intake-interview.md` step 5) now offers the close on
  Competitive runs. Adapted from phases E and F of Lauren Tan's `arena`
  (github.com/cursor/plugins, `pstack/`, MIT); attribution recorded beside the phase.

## [v1.18.1] - 2026-08-13 — audit prune, lean description, signed-out preflight fix

### Changed
- **SKILL.md pruned to the lines that steer the agent** (the writing-for-agents audit, following
  writing-for-humans v1.2.0): 6,558 → 4,547 words with no protocol change. Version-history
  narration (v1.x / D-number / R-number tags, retired-alias archaeology) removed — the
  CHANGELOG owns history. Conductor feature detail, script flag semantics, and per-tier
  effort values now live only where the environment and references already state them
  (`scripts/README.md`, the registry, `references/*`); SKILL.md keeps the protocol, the
  guardrails, and a run-controls index with pointers. Two passages relocated rather than
  cut: the approval-time / poisoned-repo / snapshot-drift caveat on `verified` stamps moved
  into `references/data-handling.md` §Repo-grounded review, and the illustrative Gemini
  thinking-level config into `references/execution-harness.md`. Every Must-Not, default,
  protocol step, and artifact contract survives verbatim or compressed in place.
- **Description trimmed to identity + triggers.** The frontmatter description is loaded
  into every session, so the per-mode explanations and the intake-process summary moved
  out of it (the skill body already carries both). Trigger phrases are consolidated —
  synonym runs collapsed, the provider cross-check folded into "cross-provider review" —
  with no trigger situation dropped.

### Fixed
- **Preflight no longer passes a signed-out CLI as GO.** The claude CLI answers any prompt with `Not logged in · Please run /login` on **stdout** and exits **0**, so every mechanical signal the classifier reads — exit code, non-empty output, clean stderr — looked healthy. A real run took consent, spent three other seats' tokens, and lost the claude seat at round 1 with `InvalidOutput`. Preflight now screens the smoke reply's text for signed-out tells and returns a labelled NO-GO carrying the adapter's auth hint. Scanning stdout is confined to the smoke path (a fixed `SMOKE_PROMPT`, so it cannot be poisoned by material under review) — the round classifiers still read stderr only, and only when no usable review came back.

## [v1.18.0] - 2026-08-07 — A handoff a human can read

The deliverable was written expert-to-expert and rendered as a wall of pills and card
boxes; the person it was for had to ask what the outcome was. This release makes the
handoff lead with a plain-language bottom line and redesigns the HTML as an editorial
document.

### Added
- **The write-for-a-human contract** (synthesizer prompt `@3`, mirrored in `SKILL.md`
  § Final synthesis and `references/prompt-templates.md`): every prose field must read as
  plain English on the first pass — short sentences, no coined compound labels
  ("harden-before-relying-on-as-evidence"), no unexplained jargon; a finding's title is a
  complete sentence naming what can go wrong, and mechanism detail lives in the evidence
  citations. The contract binds hand-authored verdicts (the degraded-synthesizer path) too.
- **`summary` — the bottom line** (required of the synthesizer; optional in the schema):
  3–6 plain sentences saying what was reviewed, what the board decided, why, and what
  happens next. Leads `final-consensus.md`, both HTML shapes (inside the verdict banner),
  and the `tldr`/`pr` short formats. `reviewed` (what the material *is*) now feeds the
  "What was reviewed" block — previously an echo of the run title — and `verdict_note` is
  required whenever a native `decision` label is set, so a domain verdict always carries
  its plain-language translation. All type-checked by `board_verdict.py` when present.
- **"How the board voted"** — a compact per-seat table (seat, lens, model, per-round vote
  trajectory, dropped status) in the full handoff, replacing five near-empty seat cards as
  the at-a-glance seat record.
- **Per-finding receipts in the HTML**: each finding's evidence trail renders as a
  collapsed `<details>` block ("Receipts — N citations") under its prose, so the
  `path:line` record is present without drowning the finding.
- `run_board.py run --effort SEAT=LEVEL` (repeatable): per-seat reasoning-effort override in each CLI's own vocabulary, targeted by seat id exactly like `--model` (unknown ids fail loudly). Wins over `--tier`'s per-provider base; recorded in the recipe like every resolved per-seat value. Closes the gap where the guided intake promised per-seat effort overrides the conductor couldn't deliver.

### Changed
- **Full-handoff + quick-verdict HTML redesigned as an editorial document**: one colored
  moment (the verdict banner), typographic section headings, hairline rules, numbered
  findings as prose instead of card boxes with circle counters, dissent and amendments as
  set-off prose with a colored edge instead of tinted boxes, a plain-text masthead meta
  line instead of chip pills, and a text-link footer CTA. Seat prose (when the run dir
  carries round files) moves to an appendix — "each seat in its own words" — after the
  consensus record.
- **Empty sections now whole-drop on every render**: no more hollow "Dissent & minority
  report" shells, dangling "— " separators after couldn't-verify items, or vacuous
  "Round 1 verdict: … full review in `round-1/amb.md`" stub cards when round prose isn't
  available (the vote table is the record; a filter-emptied section is still accounted for
  by the loud elision line).

### Fixed
- A `decision`-carrying verdict rendered with no explanation of what the label meant; the
  synthesizer contract now demands the note, and the banner renders it.

## [v1.17.0] - 2026-08-07 — Modes, guided intake, and the Fable seat

### Added
- **Modes** (`references/modes.md`): the board's interaction topology is now a named, user-chosen axis, sharing vocabulary with panely.ai — **Formal Board Review** (the existing Round Protocol, now named; the default and the only conductor-driven mode), **Roundtable** (collaborative, shared transcript, optional moderator), and **Competitive** (pitch → critique → blind vote). The two new topologies ship as hand-runnable protocols with prompt skeletons and artifact sets; `run_board.py --mode` support is a tracked follow-up. Neither produces a `verdict.json` or feeds a gate.
- **`red-team` lens preset** — every seat hostile by assignment (correctness attacker, ambiguity attacker, security & data-handling attacker, unimagined-failure hunter), for stress-testing artifacts before staking something on them; pairs with `--repo` for `path:line` attacks. Mirrored in `references/lens-presets.md` and the conductor's `LENS_PRESETS`.

### Changed
- **The intake is now a mandatory guided wizard** (`references/intake-interview.md`, rewritten): doctor probes every seat first and broken seats get an explicit fix-now (consent-gated) / continue-without / abort choice; the user's stated goal drives a mode recommendation the user confirms; seats (2–10 of the GO providers, "latest frontier of each" shortcut), reasoning depth, rounds, and output are all chosen on the record. "Use defaults" collapses to a single confirm-summary card — never to zero questions — and data-handling consent remains separate and unwaivable. A new Must Not line makes launching an unconfirmed run a violation.
- **Claude seat targets `fable`** — Anthropic's maintained alias for Fable 5 (Mythos-class, above Opus), at `--effort max`; `opus` is the ordered fallback preflight proposes (never silently applies) where `fable` doesn't resolve.
- **Board ceiling raised from ~5 to 10 seats**, with the lens rule refined: the same lens on two different providers is a valid cross-model pairing; only same-provider-same-lens wastes a seat. Past a preset's lens count the intake proposes distinct additional lenses for confirmation, and big/deep boards get a cost warning up front.

### Fixed
- Grok seat now works against current Grok CLI releases. xAI removed `--no-auto-update` (by 0.2.111) and retired the `grok-build` alias, so every Grok run failed on an unknown flag and an unresolvable model. The adapter drops the flag and selects `grok-4.5`, which `grok models` reports as the only model and the CLI default. All other flags the seat depends on — `-p`, `--effort`, `--output-format`, `--permission-mode plan`, `--sandbox read-only`, `--no-memory`, `--no-subagents` — re-verified against CLI 0.2.117 on 2026-08-05.

## [v1.16.0] - 2026-07-15 — Four-provider frontier board

### Added
- Added xAI's official Grok CLI as the fourth default frontier seat, using the provider-maintained `grok-build` selector (Grok 4.5 at release time) with high reasoning effort, read-only sandboxing, web-search isolation in gate mode, doctor/toolchain support, and full mock coverage.

### Changed
- Default model selection now floats on each provider's maintained frontier selector: Claude `opus`, Codex's recommended model (`auto`), Gemini `pro`, and Grok `grok-build`. Explicit `--model seat=id` overrides remain pinned, and run provenance records both the requested selector and the model reported by the CLI.
- Expanded the default board, disclosures, per-seat lens presets, dry-run estimates, and setup guidance from three providers to Claude, Codex, Gemini, and Grok.

## [v1.15.0] - 2026-07-03 — Rubric-first deliberation

### Added
- **Rubric-first deliberation — the proposal + chair-merge pass (v1.15 #P2 / D15, D16, D18, D20).** Behind a new opt-in `--rubric` flag, the board agrees its weighted criteria *before* it opines: a parallel proposal fan-out plus a single, mechanically-reconciled chair merge, run **before round 1**. `rubric.json` becomes the pre-round artifact of record. This is the substrate for the scoring rounds and scorecard that later phases build on; **P2 stops at `rubric.json`** — injecting the rubric into the round prompts and per-criterion scoring is not in this change.
  - **Proposal fan-out (new stdlib-only module `scripts/_conductor/rubric.py`).** Every board seat is spawned in parallel (the same `ThreadPoolExecutor` shape as a round) and asked to propose **3–7 weighted criteria** `{title, description, weight}` in a fenced structured block. The proposal packet embeds the **source text** — a **subset** of what a plain round-1 packet already egresses under the run's existing disclosure, so there is **no new consent category**. It is **source-only in this phase**: `--repo` grounding context and `--revise`/revised-draft context (the prior-verdict digest + source diff) are **not** carried into the rubric pass, so those composed modes are **refused** (see the composed-mode guard below) rather than proposing a rubric against strictly less than the rounds review. The proposal prompts are **deterministic pre-run, so they are prebuilt into the egress manifest and folded into the consent content hash** alongside the round-1 prompts (`build_rubric_proposal_blobs`); the rubric pass then spawns from those **exact** approved bytes (re-asserted per seat + whole-packet before egress) — consent binds the exact outbound proposal bytes, not a source proxy. The pre-approval disclosure line **names the rubric pass** (the extra proposal spawns + the chair spawn — same bytes, same providers). The **conductor mints the proposal ids** (`p1`…`pN`, seat order then within-seat order) at parse time — a model never mints identity (§11). A **floor of ≥2 usable proposals** or the run **refuses loudly before any opinion round spends a token**. Own template `advisory-board/rubric-proposal@1` + sha, fence markers + neutralizer, two-attempt retry (timeout|invalid), and a raw black-box record per seat under `rubric/` + `prompts/rubric-<seat>.prompt` (mirroring the revision/endorsement artifact layout).
  - **Chair merge on the unique-seat-id axis (D16).** `--chair-seat` resolves via `resolve_chair_seat_id` + an id-first `choose_chair_seat` that **refuses an ambiguous provider name on a duplicate-provider board** (mirroring the revision path, *not* the synthesizer's by-name lookup which would silently collapse a `claude,claude` board). The chair must be a board seat (the egress rule) and defaults independently of the synthesizer choice — on the **unique-id axis** (the **first `claude`-provider seat in board order**, e.g. `claude#1` on a `claude,claude,codex` board — a deterministic, output-surfaced choice, *not* a by-name dict that would silently collapse the duplicate) → first seat with a usable proposal → `board[0]`. The chair receives **all usable proposals** (not the source afresh) and returns the merged rubric plus an **explicit partition** — each merged criterion lists the proposal-id(s) it subsumes; each dropped proposal-id gets a reason. Own template `advisory-board/rubric-chair@1` + sha, fence markers, neutralizer, retry set, raw record.
  - **Mechanical reconciliation (§11).** The conductor verifies the partition **mechanically** (D15): every minted proposal-id appears **exactly once** across (∪ subsumed) ∪ dropped — no phantom id, no double-claim, no merged criterion with an empty subsumes list. And the **weight-sum invariant (D18): merged criterion weights are integer percentages summing to EXACTLY 100** — the codebase's **first numeric-sum invariant**, conductor-validated, reject-on-violation. Any discrepancy — a partition miss, a weight-sum≠100, or a schema failure — **retries once, then the refusal path**: the mechanical checks run **inside `run_rubric_chair`'s two-attempt loop** (alongside parse-invalid and timeout), so a first-attempt slip gets a cheap retry before the already-paid-for proposal fan-out is discarded; only a **second** mechanical failure refuses. The model authors only the prose (titles, descriptions, reasons); everything structural (proposal ids, criterion ids `c1`…`cN`, the partition, the arithmetic, the provenance) is conductor-computed.
  - **`rubric.json` artifact + strict validator.** Schema `advisory-board/rubric@1`, written at chair-merge time (post-consent per RH-1; pre-rounds; survives a later failure): conductor-computed `criteria[]` (id, title, description, weight, subsumes), `dropped[]` (proposal_id, seat, title, reason), `proposals[]` provenance, chair seat id, and both template versions + shas. New standalone validator **`scripts/board_rubric.py`** mirrors `board_changes.py` discipline byte-for-byte — unknown top-level keys refused, exact type checks, an `isinstance` guard *before* every membership check (so an unhashable hand-authored value dies with the clean schema exit 2, never a raw `TypeError`), dense `c1…cN` / `p1…pN` id sequences, the partition re-checked, and the weight-sum-to-100 invariant re-checked. Each **dropped entry's provenance (`seat`/`title`) is cross-checked against the proposal it names** — a hand-edited rubric that misattributes a dropped proposal fails validation, not just a type check. It has a `validate`-consistent CLI (summary / `--json`).
  - **Failure posture — refuse the run (D20).** The proposal floor and a chair-merge final failure **refuse the run**: `rubric-rejected.json` + the failed raw records are written for the post-mortem, a loud message prints, and the run exits **non-zero**. This is intentionally **not** the synthesizer's never-fail-the-run posture — the refusal lands before any opinion round has produced value to protect. **Exit code: `EXIT_PREFLIGHT_NOGO` (1)**, reused (not newly minted) because a rubric refusal is the same pre-round, pre-verdict hard-stop bucket the round-1/round-N "one voice is not a board" refusals already own; `EXIT_NO_VERDICT` (4) is the opposite (a value-*protecting* code for a post-rounds synth/revision hiccup), so a new code would splinter a bucket that already carries the right meaning. The reasoning is documented in the module docstring and at the constant's definition.
  - **Wiring.** `--rubric` + `--chair-seat` are shared run-options, recorded in the recipe (with the rubric-proposal + rubric-chair template versions/shas — the `synthesize`/`endorse` precedent, since the pass changes record-artifact shape) so `--from-recipe` replays exactly. A `rubric` stage token joins `STAGES` in the live view (RH-1 respected). The run card gains a conditional rubric block and the artifact tree lists the rubric prompts/records/`rubric.json` — both gated on `config.rubric`. `estimate_run()`/`--dry-run` account honestly for the extra proposal fan-out + chair spawn (nothing modeled a pre-round pass before). Every mock (`claude`/`codex`/`gemini`/`agy`/`ollama`) sniffs the `You are proposing RUBRIC criteria` / `You are the CHAIR` markers, with `MOCK_*_RUBRIC_MODE`/`MOCK_*_CHAIR_MODE` switches for the bad-weight / bad-partition / phantom / too-few / missing-fence paths, plus a `retry_once_then_ok` chair path (attempt 1 rejects on weight-sum, attempt 2 succeeds — via a `$MOCK_CHAIR_COUNTER` file) that proves the mechanical-check **retry-then-recover** behavior.
  - **Composed-mode guard (P2 policy — *lifted in P3*, see the composed-context item below).** Because the P2 proposal pass was **source-only**, `resolve_config` **refused `--rubric` combined with `--repo`, `--revise`, or `--output revised-draft`** — a loud, pre-spawn `EXIT_USAGE` refusal naming the offending flag, mirroring the `--chair-seat` guard idiom. Round 1 under those modes carried context the source-only rubric proposal did not (the repo-grounding clause + frozen snapshot cwd; the prior-verdict digest + source diff), so composing them would have let the board propose criteria against strictly **less** than it reviews. This guard shipped in P2 as the sound posture until the shared composed-context builder landed; **P3 lands that builder and lifts the guard** — those combinations now compose correctly.
  - **Weight-floor + run-card chair fixes.** A merged criterion must now carry **weight ≥ 1** — a zero-weight criterion (accepted before as long as the weights summed to 100) is a soundness smell, refused at both the chair-side write check and the standalone validator. The **`--dry-run` run card** now projects the chair via the **same `choose_chair_seat` selector execution uses** (the unique-id axis), so on a duplicate-provider board (`claude,claude,codex`) it names the seat the run would actually pick (`claude#1`) rather than a by-name-collapsed `claude#2`. The partition invariant (implemented independently at write time in `reconcile_partition` and read time in `board_rubric.validate`, deliberately **not** collapsed — different trust boundaries) gains a **parity test** pinning both to reject the same violating docs and accept the same valid one.
  - **Byte-identity guard (D5/R5).** A run **without** `--rubric` is byte-identical to before everywhere — recipe, run card, artifact tree, status events, estimator output — enforced by explicit tests.
- **Composed rubric context — the shared review-context builder (v1.15 #P3, unit 1).** `--rubric` now **composes from the same surface round 1 sees**, not the bare source, so the board proposes criteria against exactly what it reviews. A single shared builder (`prompts.build_composed_review_context` / `composed_review_context_for`) produces the context both the round-1 packet and the rubric proposal prompt splice in beyond the source: under **`--repo`** the repo-grounding clause (and the proposal seats now spawn from the **frozen snapshot cwd, grounded** — the exact read-only tree consent bound to, mirroring `run_round`, not a fresh empty tempdir); under **`--revise`** the mechanical prior-verdict digest + source diff (`config.revision`, prepared pre-round only from `config.revise_of` — a `revised-draft` run without `--revise` revises **after** synthesis and adds no pre-round revision context, so its rubric pass is source-only unless it is also a `--revise` run). Round 1 is a **pure refactor** — it now calls the shared builder but its rendered bytes are **byte-identical** (golden tests hold), because the composed splices are empty on an ungrounded, non-revise run. The rubric proposal template gains a conditional `{composed_context}` splice: `advisory-board/rubric-proposal@1` when source-only (byte-identical to before), **`@2`** when the composed context renders — the recipe, banner, and black-box record the composed-aware version + sha, so provenance names the true egressed surface. The composed context is **deterministic pre-approval** (`config.grounded` is resolved and `config.revision.material` is built before the packet), so `build_rubric_proposal_blobs` **prebuilds it into the egress manifest and consent content hash** — consent binds the true outbound composed bytes, not a source proxy (extended consent-hash test proves a composed prebuild hashes differently from a source-only one). The **P2 composed-mode guard is lifted**: `resolve_config` no longer refuses `--rubric` with `--repo`/`--revise`/`--output revised-draft`; the former guard tests become **parity tests** proving the proposal prompt carries the `--repo` grounding clause / the `--revise` prior-verdict digest + diff, that each piece is byte-identical to round 1's, and that plain `--rubric` — and a `revised-draft` run without `--revise` — still composes source-only. The **chair prompt is unchanged** (it embeds seat-derived proposals under the round-2 derived-content precedent — no source or grounding added).
  - **Union-alphabet fence scrubbing of the composed splices (injection hardening).** The revision block's fence (`PRIOR VERDICT + SOURCE DIFF`) is a **round-family** marker whatever template splices it, but the rubric caller's own neutralizer (`neutralize_rubric_markers`) does **not** cover it — so on a `--rubric --revise` run a poisoned prior-verdict/diff line carrying a literal `<<<<<<<< END PRIOR VERDICT + SOURCE DIFF >>>>>>>>` would have passed through verbatim and let attacker text escape the fence. `build_composed_review_context` now scrubs the revision material against the **union** of the round-family alphabet **and** the caller's own (new `prompts.scrub_composed_splice`) — the round scrub **always** runs, the caller's neutralizer runs on top; on the round-1 path (whose caller *is* `neutralize_round_markers`) the union collapses to a single application, so round-1 bytes stay **byte-identical to `@2`** (golden tests hold). The same root cause is closed at the **other splice site**: the rubric **SOURCE** splice is now scrubbed against the union too, so a source echoing round-family fences can't fabricate a fake round-family block inside a rubric prompt.
  - **Grounded flag keyed to the snapshot-workdir predicate (honest grounding).** The rubric spawn's effective `grounded` flag now follows the **same** predicate that selects the frozen-snapshot workdir (`grounded ∧ grounding ∧ snapshot_dir`) — `config.grounded` alone (a `--repo` run whose snapshot never materialized) no longer spawns a proposal seat *claiming* grounding without the snapshot cwd. `_run_rubric_step` derives `grounded=bool(grounded_snapshot)` and threads it through `run_rubric_proposals` → `run_rubric_proposal` (defaulting to `config.grounded` for direct/test callers). The shared snapshot the seats read is **not owned** by the rubric step — its `finally` only rmtree's the ephemeral tempdir it created (`own_workdir`, `None` under `--repo`), so the snapshot survives to the single `cmd_run` cleanup.
- **Scoring rounds + score-based convergence (v1.15 #P3, unit 2 / D17, D19).** With a rubric agreed, `--rubric` now **injects the merged rubric into every opinion round's prompt and each seat scores every criterion 1–5**, and the `--rounds auto` stop-rule is **widened** to include score movement. This lands the scores in seat-review parsing so a later phase's `scorecard.json` can consume them; **this change stops at parsing + convergence — it does not build `scorecard.json`.**
  - **Rubric injection into the round prompts (the `{revision_context}` precedent).** A new conditional `{rubric_scoring}` placeholder in **both** round templates (`prompts.RUBRIC_SCORING_BLOCK`) carries the merged criteria (their conductor-assigned ids `c1`…`cN`, titles, descriptions, weights) and instructs each seat to emit one `SCORE cN: <1-5>` line per criterion, plus an **optional `RUBRIC-NOTE:`** objection to the rubric itself (recorded, never debated — scoring under the rubric *is* accepting it, D16). The block sits **above** the `BASIS`/`VERDICT` tokens so the verdict stays genuinely last, and the chair-authored criterion prose (model output) is **fence-scrubbed with the union alphabet** (`scrub_composed_splice`) before it is spliced — a poisoned criterion can't forge an early round-fence END. The placeholder is **empty on a non-rubric run**, so a plain run's round bytes — and the combined `prompt_template_sha256` — are **byte-identical to before** (the whole-roadmap D5/D6 regression guard). It is a **version suffix** (`+rubric@1`) on the round-1 *and* round-2 template ids, composing after `+revise@1`; the recipe records it. The **template sha follows unit 1's one-sha-per-shape policy**: the `{rubric_scoring}` fill is pre-substituted with the RAW block (its inner `{rubric_criteria}` unfilled) so the sha pins the *shape* of a scored round, not any run's criteria. The **pre-approval egress disclosure and the `--dry-run` run card now name the full pass** — they no longer stop at "the chair merges the proposals": both state that the merged rubric is **injected back into every opinion-round prompt for per-criterion scoring** (post-approval, conductor-**derived** content — no new source egress), so the consent surface enumerates the injection, not just the merge.
  - **`SCORE cN` parser with `parse_verdict`-style hardening.** New `convergence.parse_scores(text, criterion_ids)` scans every line for a `SCORE c<n>:` label and accepts only a **lone ASCII integer in 1–5** as the value: the **last qualifying line per id wins**; a markdown-**quoted / indented / code-spanned** line is skipped (a peer's echoed score can't override the seat's own); a **hedged range/decimal/prose** value (`4 or 5`, `4-5`, `3.5`, `high`) and an **out-of-range** integer (`0`, `6`) are rejected. The value class is **ASCII `[0-9]` only (not `\d`)** — a Unicode decimal digit (Arabic-Indic `٣`, fullwidth `３`) is **rejected**, not silently parsed as 3 — and the leading decoration class **excludes `-`**, so a **signed value** (`-3`) is rejected rather than parsed as its magnitude (while an arrow/bullet lead like `→4` stays tolerated decoration). A score for an id **outside the merged rubric** (a seat inventing a criterion) is ignored. A criterion with no clean line is **absent — never imputed** (the scorecard will render it "—"). A sibling `parse_rubric_note` parses the objection line. Both are pure and mirror `parse_verdict`/`parse_basis` exactly. An `isinstance` guard runs before the id-membership check.
  - **Rubric-aware round runner — seat usability unchanged; a bad score degrades to a partial cell.** `SeatRoundResult` gains the round's `criterion_ids` and exposes `.scores` / `.rubric_note` (empty/None on a non-rubric round). **Seat usability stays defined by the `VERDICT` token** (the classifier is untouched): a missing/invalid SCORE line does **not** make a seat unusable — it degrades to a **partial scorecard cell** (that criterion absent → rendered "—", the seat's total marked partial), exactly per D19's classifier note (a valid-review seat is never dropped over a bad number; the "standard two-attempt retry" is the seat's own retry, which fires only when the *review* is retryable, not on a bad SCORE line alone). The console prints a per-round per-seat score line and the tracker's round-done detail carries a `scored N/M cells` coverage note (the status-event surface a later scorecard reads the trajectory from).
  - **Convergence widened, one boolean (D19).** `moved = verdict_shift OR new_cites OR any criterion score changed`. `seat_movement`/`board_movement` take an optional `criterion_ids`: a **criterion scored in neither round is non-movement**; one scored in exactly one round **is** a change; integer 1–5 makes the epsilon question moot. `--max-rounds` stays the hard ceiling, and the round-done detail **names the still-moving criteria** (`board_movement(...)["moving_criteria"]`, e.g. `criteria still moving: c1`) — **board movement is now computed *before* `tracker.round_done` for round 2+ so the still-moving criteria ride into the round-done `status.json` event**, letting status consumers (a later `scorecard.json`) recover the trajectory from the event, not just the console. The convergence artifact prose (`render_convergence_section`) now explains movement as verdict-token / citation / **per-criterion score** change (a score-only mover renders `cN↕`), not verdict + citations only. `criterion_ids=None` (non-rubric) leaves the two-arm movement **byte-for-byte** as before.
  - **Consent / provenance — the round-1 tension resolved on the round-2 precedent, not `--revise`.** The round-1 packet is **prebuilt before egress approval**, but the merged rubric does **not exist** then — the chair merges **after** approval. So the rubric-scored round-1 prompt **cannot** be part of the consent-hashed round-1 blobs. It is resolved as **derived content**: the injected rubric is derived **entirely from already-approved material** (the proposal fan-out — whose prompts *are* in the consent hash — plus the chair merge, itself covered by the disclosed rubric plan), exactly like a round-2 cross-reading packet. So `_run_rubric_step` hands the merged rubric back, the round-1 packet is **rebuilt** with the scoring block, and `run_round`'s round-1 hash re-assert is **narrowed into a two-link chain of custody** for a scored round 1 — **not skipped**. The scored packet as a whole can't equal the round-1 sub-hash (the rubric is post-consent), so the guard binds the **actual outbound blobs** to consent in two links, each dying `EXIT_EGRESS_BLOCKED` on mismatch exactly like the hard path: **Link A (blobs → config)** re-asserts the outbound packet hash equals a fresh `packet_hash(build_packet(config, rubric_criteria=rubric_criteria))` — `build_packet` is deterministic over the config *and* the merged rubric, so the outbound bytes are exactly what THIS config re-produces WITH the rubric, proving nothing was injected between build and spawn; **Link B (config → consent)** re-asserts the **rubric-STRIPPED** rebuild (`rubric_criteria=None`, byte-identical to the pre-approval build) equals the recorded `approval.round1_hash` anchor. Chained, A ∘ B binds the outbound **base** (source + grounding + revision bytes) **byte-for-byte** back to consent — the earlier stripped-base-only assertion checked the config against consent but never touched the outbound blobs; Link A closes that gap. Only the rubric **delta** rides on the disclosed-plan derivation, and Link A pins even that to the config's own injection. `run_round` now threads `rubric_criteria` through (cli.py passes it) so it can rebuild the scored packet for Link A. The scored-round predicate is derived from **one signal** (`round_no == 1 AND config.rubric`) so the relaxation and the rubric injection can never disagree. The round records its own packet hash for provenance and reuses the run's approval, like round 2+; the **repo-scope guard still fires on every grounded round**. The black-box record labels a scored round-1 packet honestly ("rubric-scored round-1 packet; … a derivative of already-approved source"). This is documented in the `RUBRIC_SCORING_BLOCK` note in `prompts.py` and in `run_round`'s docstring.
  - **`--tier quick` composition + wiring.** `--rubric` is orthogonal to `--tier` — the rubric pass **always runs** (never silently skipped) and the single quick round still injects + scores. Every review-emitting mock (`claude`/`codex`/`gemini`) sniffs the injected scoring block and emits `SCORE cN` lines, with `MOCK_*_SCORE_MODE` switches (`default` / `moving` / `oscillating` / `partial` / `partial_after_first` / `invalid` / `note`) exercising the score-parse hardening, the partial-cell degradation, and score-driven auto stop. New tests: score-parse fixtures, score movement (incl. absent-in-both non-movement), prompt injection + byte-identity, partial/invalid degradation with the seat staying usable, `--rounds auto` continuing then stopping on a **score-only** mover, `--tier quick` still runs the rubric + scores, the scored-round-1 derived-content provenance, `--max-rounds` capping a never-converging score oscillation, and the RUBRIC-NOTE surfacing. Adversarial-review catch fixed in-phase: `config._warn_on_template_drift` now recomputes the current sha with the SAME **rubric** posture the recipe encodes (`recipe["rubric"]`), so a fresh `--rubric` recipe replayed via `--from-recipe` no longer fires a false prompt-template-drift warning. **Board-review fixes (P3 round 2):** the scored round-1 consent re-assert was **narrowed rather than skipped** (rubric-stripped base re-bound to `approval.round1_hash`), reviving the previously-orphaned anchor; board movement is computed before `round_done` so the still-moving criteria reach `status.json`; the convergence artifact prose names score movement; and the score properties bind `r.scores` once instead of re-parsing stdout per access. New review-driven tests: a **tampered scored round-1 base dies `EXIT_EGRESS_BLOCKED`** (with the happy-path stripped-base = anchor equality asserted, and the non-rubric round 1 still hard-asserting), the `round_done` status event surfaces both `scored N/M cells` and the still-moving criteria, a `--from-recipe` **scored replay** re-injects the scoring block and re-parses `SCORE` outputs, and the convergence artifact prose renders the `cN↕` score mover. **Board re-review fixes (P3 round 3):** the chain of custody was **completed** — the re-assert now also binds the **actual outbound blobs** to the config via **Link A** (`round_packet_hash == packet_hash(build_packet(config, rubric_criteria=rubric_criteria))`), so the "byte-for-byte" claim is true of the real egressed bytes (the stripped-base-only check bound the config to consent but never the outbound blobs); `run_round` threads `rubric_criteria` through and cli.py passes it. New tests: a **tampered outbound blob** (config untouched) dies `EXIT_EGRESS_BLOCKED` via Link A, plus **grounded** and **`--revise`** variants of the base-reassert (happy-path equality + tamper→blocked each) and a **`--rubric --revise` E2E** driven through the round-1 two-link re-assert to a verdict. Nit: `_SCORE_LINE`'s id capture tightened `c\d+` → `c[0-9]+`. Suite 1523 → 1577.
- **Scorecard, schema pointers, renders (v1.15 #P4 / D17, D18, D20).** The rubric feature's last code phase: a **`scorecard.json`** artifact of record, **tool-authored `rubric`/`scorecard` pointers** in `verdict.json`, and **scorecard renders** in `final-consensus.md` + the HTML handoff — with a `stakeholder-panel` lens preset and `--revise` carrying the prior rubric forward. Scores are **informational only — the gate never reads them** (D17; Gemini's ABSTAIN-on-contradiction dissent stays deferred until real scored runs calibrate the bands).
  - **`scorecard.json` (schema `advisory-board/scorecard@1`) + strict validator `scripts/board_scorecard.py`.** Written **after** the opinion rounds (the rubric.json it scores against is written **before** them — the D18 two-artifact split by time), from the conductor's own state: per-round `scores[]` rows across **all** rounds (the trajectory **is** the convergence story), `rubric_notes[]`, per-seat conductor-computed **weighted totals + coarse bands**, and `contradictions[]`. Everything is conductor-computed — the scores are **parsed** from the round replies (`SeatRoundResult.scores`), never a model JSON field; the only model-traced content is the verbatim `RUBRIC-NOTE:` prose. The validator mirrors `board_rubric`/`board_changes` discipline **byte-for-byte** — unknown top-level keys refused, exact types, an `isinstance` guard *before* every membership check (an unhashable hand-authored value dies with the clean schema exit 2, never a raw `TypeError`), dense `c1…cN` ids, scores re-checked in-range `[1,5]`, the criteria weight-sum re-checked to 100 (D18 travels with the copy), bands re-checked to `weak`/`mixed`/`strong`, and `weighted_total`/`band` required to be both-null-or-both-set. It has a `validate`-consistent CLI (summary / `--json`). It is written on **any** round count (even a single scored round carries a trajectory) and **stands alone** — `--synthesize` is not required. A validation failure **warns and writes nothing** — the rounds and verdict still stand (D14, a scorecard hiccup never discards the board).
  - **Band computation policy (D17 — the echo-score philosophy).** The per-seat weighted total is a **weighted mean on the 1–5 scale** (Σ score·weight ÷ Σ weight over **only** the criteria the seat scored, so a partial cell doesn't drag the total toward zero and the total stays on-scale), over the seat's **final scored round** (a seat that dropped before the last round is scored on its last usable round, never penalized to empty). The **coarse band** is a fixed third of the scale — `weak` `[1, 2.333)`, `mixed` `[2.333, 3.667)`, `strong` `[3.667, 5]` — reader-defensible over the scale, **never a tuned formula**. `partial` marks a seat that did not score every criterion; a seat that scored nothing has a `null` total and band.
  - **Token↔band contradiction, surfaced LOUDLY, never gated (D17).** A **severe** self-contradiction — a `block` verdict over a `strong` band, or a `ship` verdict over a `weak` band (`caution`/`mixed` never contradict — they *are* the hedge) — is recorded in `contradictions[]` and surfaced in **both** the primary verdict summary (a `⚠ Scores contradict the verdict for: …` line) and the scorecard section. It **does not** move the verdict or the gate (the `confidence`/echo precedent: a gameable number must not move a gate).
  - **`verdict.json` gains tool-authored `rubric` + `scorecard` `{artifact, sha256}` pointers.** They follow the shipped **`changes`-pointer precedent byte-for-byte** — validated strictly when present, **invisible when absent** (a non-rubric verdict is byte-identical), stripped from synthesizer merges (added to `synthesizer.LIFECYCLE_KEYS`, so a model can never author them — the conductor pins them **after** the merge), and **never read by the gate** (added to `board_verdict.LIFECYCLE_FIELDS`; the `changes` validation block was refactored into a shared `_validate_artifact_pointer` reused for all three pointers). The conductor pins them with **amend's full write discipline** (`_write_verdict_pointer` — realpath through symlinks, optimistic sha guard re-checked before the swap, mkstemp + `os.replace`, mode preservation, byte-exact `newline=""`); each write **chains the baseline sha forward** so the second pointer guards the first pointer's bytes, and the revision step's `changes` pointer sha-guards the **latest** bytes. **`--synthesize` is not required** — the artifacts stand alone; the pointers appear **only when synthesis runs** (there's no verdict.json to pin to otherwise). A pointer-write failure is **loud but never fatal** — the artifact still stands on its own.
  - **Renders — scorecard table in `final-consensus.md` + the HTML handoff (D20).** The consensus markdown gains a `## Rubric scorecard` section (criteria weights, per-seat weighted totals + bands + a `History` trajectory column recomputed per round from the `scores[]` rows, coverage/partial marks, recorded `RUBRIC-NOTE` objections, and the chair's dropped-criteria provenance read from the sibling rubric.json). The HTML handoff gains a matching `scorecard-sec` section that **whole-drops to ZERO body bytes on a non-rubric run** (the sc-intro renders empty → the whole section + its authoring comment drop, per the byte-identity invariant `render_handoff.py:45-50`; a body-byte-identity test proves the drop leaves no residue). Labels are **lens-aware** (routed through the software-vs-plain split like the verdict labels). Both renders read `scorecard.json` **best-effort** — realpath-confined + symlink-refused, exactly like the echo-score/revised-chain reads — so a missing/malformed artifact drops the section rather than dying.
  - **`history` scorecard column.** The `history` table gains a **`Rubric`** column: `yes` when a run's `verdict.json` pins a scorecard pointer (a synthesized rubric run), else `—`.
  - **`stakeholder-panel` lens preset (D20).** A new `LENS_PRESETS` entry — three **distinct stakeholder archetypes**, one per seat, in a documented **seat-order binding**: seat 1 the **decision owner**, seat 2 the **end user**, seat 3 the **compliance & risk reviewer**. The lens string **is** the persona (structured personas are out of scope for v1.15); it rides the entire existing lens machinery including plain-language verdict rendering. `resolve_board`'s positional-slot default carries the binding — a 4th seat **repeats** the reviewer voice, a 2-seat board **drops** the third archetype. It pairs with `--rubric` (`--rubric --lens stakeholder-panel`) but never **implies** it — the axes stay orthogonal; the combination is documented, not bundled.
  - **`--revise` carries the prior rubric forward mechanically (D20).** On a `--revise --rubric` run whose prior run carried a valid rubric, the prior rubric is **carried forward mechanically** — **no** fresh proposal + chair pass, **re-agreement is not offered** (the §11 no-re-reasoning precedent; scores stay comparable across revisions). Because the prior rubric is **deterministic pre-approval** (read + strict-validated from the prior run dir in `prepare_revision` → `RevisionContext.carried_rubric`), its scoring block is built into the **round-1 packet before consent**, so it lands **inside the consent-hashed packet** (unlike P3's post-approval chair merge). `run_round`'s scored-round-1 two-link chain is bypassed for a carried run (`rubric_pre_consent=True`) because the whole scored packet **is** what consent bound — it takes the normal whole-packet assertion. The disclosure line and the `--dry-run` estimate are carried-aware (they name the carry + skip the proposal/chair spawn cost). The carried rubric.json is written into the new run dir so the run is self-contained.
  - **Mocks.** The three review mocks gain `low`/`high` `MOCK_*_SCORE_MODE` switches (a flat weak/strong band) so the E2E band + token↔band-contradiction tests can exercise a `block`-over-`strong` (gemini) contradiction end to end.
  - **Byte-identity guard (D5/R5).** A run **without** `--rubric` is byte-identical everywhere — the scorecard render whole-drops, the verdict pointers are absent, `verdict.json`/`board_verdict`/`synthesizer` are untouched — enforced by explicit tests. Suite 1577 → 1631.
  - **Fix pass (adversarial review, SHIP-WITH-CHANGES).** Two findings folded in: **(1)** the markdown scorecard's criteria table emitted the chair-authored criterion **title** into a `| … |` cell through `_flat` (which collapses newlines but leaves a `|` intact) — a title like `Cost | Risk tradeoff` would inject an extra column and corrupt the table (board_rubric imposes no char constraint; the fence-scrub preserves pipes). A new `render_verdict._md_cell` backslash-escapes every `|` (and a leading `#`/`-`/`+`/`>`) and is applied to the title; the HTML path was already safe (html.escaped via `_plain`). **(2)** the token↔band contradiction compares the seat's **final-of-each-kind** — its last round that declared a verdict token vs its last round that produced any clean score — which can resolve to **different rounds**. That accepted semantic is now documented precisely in `build_scorecard`'s docstring, and each `contradictions[]` row carries the two round numbers as **additive schema fields `token_round` / `score_round`** (both positive integers, strictly validated by `board_scorecard`) so a reader can see when the compared positions diverge; the md render and the CLI summary print a `(verdict from round N, scores from round M)` clause **only when the rounds differ**. New tests: validator refusals for `inf`/`-inf`/`NaN`/negative `weighted_total`; a null-total/null-band seat renders `—` in both the md and HTML paths without crashing; a hostile criterion title (a `|` and a leading `#`) renders a non-corrupted md table (stable column count per row); the **carried** `--revise --rubric` path drives the whole-packet hard assert (a tampered outbound blob dies `EXIT_EGRESS_BLOCKED`); and a `--from-recipe` replay of a carried run reproduces byte-identical round-1 prompt bytes (locking the carry re-derivation). Suite 1631 → 1640.
  - **Board-review fix pass (2-seat board review — validator hardening + validate-or-drop).** Three findings folded in, each in the claude seat's *derivable-invariant* scope (deliberately **not** a full arithmetic recompute — two copies of the conductor's arithmetic invite drift, and `verdict.json`'s `scorecard.sha256` already guards the in-run case). **(1) `board_scorecard.validate` now re-derives every in-document invariant:** `band == band_for(weighted_total)` (with `band_for` + the fixed-thirds boundaries moved to `board_scorecard` as the **single source of truth** — `_conductor.scorecard` now delegates to it, so the written band and the re-derived band can never diverge), `partial == (criteria_scored < len(criteria))`, `criteria_scored <= len(criteria)`, and the null coherence `null weighted_total ⇔ null band ⇔ criteria_scored == 0`. **(2) Per-seat final verdict tokens in the schema.** Each `totals[]` row gains additive `final_verdict` (a known token or null) + `final_verdict_round`, so `contradictions[]` is now validatable **standalone**: the set of seats whose `(final_verdict, band)` trips the fixed token↔band rule (block/strong, ship/weak) must **exactly** equal the seats in `contradictions[]`, and each recorded row's verdict/band must match its totals row — a **missing or extra** contradiction row is refused (derivable consistency, no recompute). **(3) Render validate-or-drop.** `render_verdict._read_scorecard` now runs `board_scorecard.validate` on the payload and **drops the scorecard section** (renders it absent) on any failure instead of raising — a malformed scorecard (e.g. a string `weight`, which crashed `_scorecard_seat_history` with a `TypeError`, or a band⇔total mismatch) degrades gracefully in both the md and HTML handoff paths (the only file-reading render path). New tests: band⇔total-inconsistent (`4.5`/`weak`) refused; `partial`/`criteria_scored`/null-coherence refusals; `final_verdict` token/pairing refusals; missing/extra/mismatched contradiction rows refused; string-weight and band⇔total-inconsistent scorecards degrade to section-drop without crashing (md + HTML); a `{{TOKEN}}` in a criterion title stays inert (literal in md, defanged in HTML). The carried-rubric consent path is untouched (both seats verified it sound). Suite 1640 → 1655.
  - **Board re-review fix pass (2-seat board re-review — pointer enforcement + escape/strip hardening).** Four findings folded in. **(1) The render now enforces the pinned scorecard/rubric sha.** `render_verdict._read_scorecard`/`_read_rubric_dropped` thread the verdict `data`, and when it carries a `verdict.json.scorecard`/`rubric` `{artifact, sha256}` pointer they **hash the on-disk artifact and require equality with the pinned sha BEFORE validate/render** (new `_pointer_sha_ok`, mirroring `_load_revised_chain`), dropping the section on any mismatch — a swapped-in but schema-valid `scorecard@1` (flipped band, dropped contradiction) no longer renders forged values into `final-consensus.md` or the HTML handoff (both paths go through the one file-reading choke point). The pointer's whole purpose — binding the verdict to the exact artifact bytes — is now enforced by the consumer that holds both halves, closing the gap the sibling `changes` chain already guarded. The **fixed-name path is the no-pointer fallback only** (an artifact stands alone without `--synthesize`, so a pointerless run is legitimate). **(2) `_md_cell` under-escaped backslashes.** It now **doubles `\` to `\\` before** escaping `|` → `\|`, so a criterion title containing a backslash-then-pipe (`\|`) can no longer inject a column (the escaping backslash was being consumed by the literal one). **(3) `final_verdict`/`final_verdict_round` are now REQUIRED on every `scorecard@1` totals row** (was additive-optional). `scorecard@1` is unreleased, so no legitimate artifact lacks the pair; making it optional only ever benefited a **tampered** artifact that stripped the pair to dodge the contradictions⇔totals cross-check (strip-to-evade). The cross-check's all-rows-present skip branch is removed — it **always runs**. The conductor's builder already emits both, so no builder change. **(4) Nit:** `history._rubric_cell`'s docstring now matches its `''` return. New tests: a swapped valid `scorecard@1` (different band) drops the section in **both** md and HTML under a matching pointer while the same bytes render with no pointer; a backslash-pipe criterion title yields a stable per-row column count at the **parser** level (split on unescaped pipes); a rule-tripping `(final_verdict, band)` with `final_verdict` stripped is **refused**; a totals row missing the pair is refused.

## [v1.14.0] - 2026-07-02 — Signal quality & run experience

### Added
- **Severity filters (v1.14 #8 / P1) — trim what a render shows, and what the gate fails on, by finding severity.** The verdict schema already separates severities (`blockers[]` / `dissent[]` / `concerns[]` / plain-string `caveats[]`); this is **exposure, not new modeling**.
  - **`--filter blockers|blockers+dissent|all` on `render_verdict.py` and `format_output.py`.** `all` (the default) is today's full output — **byte-identical to no flag everywhere** (D5). `blockers` renders blockers only; `blockers+dissent` adds dissent. Every dropped section is stated with counts — a **loud elision line**, e.g. `(filtered: 2 dissents, 4 couldn't-verify lines — --filter blockers)` — never a silent truncation; the renderer computes the counts (the helper only formats), naming the honest buckets that shape renders (dissent entries + couldn't-verify lines), so each count equals exactly what the filter dropped and is auditable against the verdict. The **verdict banner and confidence are never filtered.** Per shape: the consensus md and full-handoff HTML filter their dissent + couldn't-verify sections (on the filtered render a suppressed HTML section drops **whole — heading included**, never a hollow shell, and the new optional `{{FILTER_NOTE}}` line carries the count); the quick-verdict HTML and `format_output`'s `pr` shape render dissent but no couldn't-verify bucket, so they filter dissent only; the **implementation-sequence** shape renders only actions + blockers, so `--filter` never changes it; `tldr`/`slack` render no dissent/caveats and are unaffected.
  - **`format_output.py --format json` refuses `--filter` (non-`all`) with a clean exit `2`.** The JSON output is the faithful, unfiltered machine echo a gate reads; silently thinning it — or annotating the canonical echo with a non-schema `filter` key — would defeat exactly the honesty this feature exists for. `--filter all` (the no-op default) still echoes the whole verdict.
  - **`--min-severity blocker|concern` on the `board_verdict.py --gate` path** (also via `run_board.py validate`). It **composes with `--fail-on`**: after the verdict token clears the threshold, a **fail** additionally requires a finding at or above the named tier (`blocker` > `concern`; dissent is a minority view, not a finding tier, and never counts). A caution/block verdict whose only findings are concerns/dissent then **passes** under `--min-severity blocker` instead of failing. It can only narrow a fail to a pass — it never escalates a pass, and it never touches the **abstain** integrity checks (a refuted citation, a torn board, or a verdict-vs-board contradiction still abstain regardless). Absent = today's behavior unchanged; unknown values are refused (exit `2`).
  - Both render/gate flags flow through the `run_board.py` delegate subcommands (`consensus`, `validate`) unchanged — they forward every argument verbatim. New shared, stdlib-only helper `scripts/_severity_filter.py` (imported by both renderers). A `handoff-data.json` written under a filter is a shape-specific **view** feeding the HTML render (the JSON echo from `format_output.py` stays the only machine mirror), and its thinning is **shape-owned**: a slot is emptied only when that shape renders the bucket and the loud `filter_note` counts it — a bucket a shape never renders stays intact in its data, so the artifact never silently loses content and `implementation-sequence` handoff-data never varies with `--filter` at all. Docs: SKILL.md, `scripts/README.md` (flag tables, examples, and a per-shape semantics section). Suite 1286 → 1355.
- **Independence / echo score (v1.14 #9 / P2) — a quantified, honest flag for whether the board's convergence was earned or social.** A multi-model board only beats one model when the seats reach their positions *independently*; once they read each other they can drift into agreement for social reasons. This scores that risk.
  - **A parseable `BASIS:` line added to the round-2+ template** makes the `epistemics.md` independence check machine-readable: each seat states, on the second-to-last line (above `VERDICT:`), whether its revised position rests on `independent` (its own evidence, or it held its prior view), `evidence` (it changed toward another seat because of a specific argument/file/fact *they* surfaced), or `deference` (it changed only because the others agreed). It is a **second parsed token but self-reported and advisory** — it feeds the metric only, never gates, and never overrides the one `VERDICT:` token; parsed with the same failure-tolerance (a line naming zero or >1 token is ignored, an omitted line is *unknown*, never guessed). Added **unconditionally** (round 2+, every run), so it **bumps the round-2 template**: base `round2@2` → `round2@3`, grounded `round2@3` → `round2@4`. Round 1 is untouched (`round1@2`/`@3`) — there is nothing there to have changed from. The recipe's `prompt_template_sha256` (a combined round1+round2 hash) moves accordingly; a fresh run legitimately records the new bytes. **`--from-recipe` reproduces the resolved *config* exactly, but prompts are always built from the *current* template code — not recorded bytes** (there is one round-2 template, and it now carries `BASIS:`), so a **pre-P2 recipe replayed post-P2 egresses the new round-2 bytes and a new sha**. That drift is now surfaced loudly: on load, a recorded `prompt_template_sha256` that differs from the current combined sha — or a recipe predating the field — prints a stderr warning naming both shas; the replay still proceeds (its prompts are consented at the egress gate), and the id+sha the new run records make the drift visible. The recipe also now records the **round-2 template id + sha** (`round2_template` / `round2_template_sha256`, additive keys) so the surface P2 actually changed is named, not only the round-1 id.
  - **A pure metric (new stdlib-only module `scripts/_conductor/echo_score.py`)** over the **final** round transition's already-parsed signals — verdict flips *toward the emerging majority*, mean pairwise citation-set overlap (the same convergence citations), and the `BASIS:` deference count. It rolls up to a **coarse band — low / moderate / high echo risk**, never a false-precision 0–100 number, with a **one-line explanation that names the sub-signals that drove it** (e.g. "2/2 seats flipped toward the majority with 78% citation overlap and 1 deference declaration"). On a **same-provider board** (`--board claude,claude`) high citation overlap is *expected* and is **not** counted as echo on its own — the band and the explanation say so. It **flags possible echo; it does not prove independence**, and a `high` band is not a verdict on the board.
  - **Surfaced in `run-metadata.md`** as an "Independence / echo" subsection inside Convergence (it scores the same cross-round signals), and as an **optional pill in the full-handoff HTML** (band-tinted). Both follow the D5 optional-slot discipline. **`not computed`** is reserved for a run with no final transition to score: a **single-round run** and a run with **fewer than two seats usable in both final rounds**. An **old run dir** re-rendered has no `echo-score.json`, so the pill/section are simply **absent** (nothing computed or claimed — not `not computed`), and re-rendering such a run stays **byte-identical** (verified). A **pre-P2 recipe replayed** runs with the current `BASIS:`-bearing round-2 template, so it **scores normally** — a run whose seats state no basis scores with an all-`unknown` BASIS tally (the deference sub-signal contributes nothing; the explanation names how many seats did not state a basis). The conductor writes a small machine-readable `echo-score.json` sidecar on any ≥2-round run, which the HTML renderer reads best-effort (realpath-confined, symlink-refused).
  - **DECISION recorded in-phase** in `references/epistemics.md`: the metric definition, the `BASIS:` token grammar, the band, and — explicitly — the limits and failure modes (honest convergence on strong evidence, expected overlap on a small source, the self-reported deference token, final-transition-only + parsed-only scope). Docs: `references/prompt-templates.md` (the `BASIS:` line + version bumps), SKILL.md, `scripts/README.md`. Suite 1355 → 1404.
- **Live progress view (v1.14 #10 / P3) — something to watch during a 15-minute run.** Board runs block-buffer stdout, so a user watching a background run sees nothing until a round completes; the run dir was the only live window. This makes that window real: a `status.json` in the run dir, rewritten atomically on every seat/round/stage transition, drives flushed terminal progress lines and a self-refreshing HTML tracker from ONE event stream. **On by default** — it's pure value; `--no-live-status` opts out for a byte-exact run dir.
  - **`status.json` is the single source of truth (new stdlib-only module `scripts/_conductor/status.py`)** — one JSON document, schema `advisory-board/status@1`: run-level fields (title, `started`/`finished` stamps, current `stage`, `rounds_planned`/`rounds_done`, coarse `outcome`) + an ordered `events[]` (monotonic `seq`, `stage`/`seat`/`round`, `state`, `detail`, `at`) + a per-seat current-state map for cheap rendering. It is **rewritten atomically on every event** (write-temp + `os.replace`), so a concurrent reader never sees a torn file and no `.tmp` is left behind on any Python-level failure. Seat transitions fire from the round's worker threads, so writes are **serialized with a lock**; a status-write failure is **best-effort** — caught, warned **once** to stderr, and the run continues (a live view must never take the run down). The `state` vocabulary is `started`/`running`/`done`/`dropped`/`retry`/`skipped` (`retry` and `skipped` are reserved in `status@1` — no current path emits them); the `stage` vocabulary is `preflight`/`egress`/`round`/`synthesis`/`revision`/`endorsement`/`run`.
  - **Flushed terminal per-seat progress lines** drawn from the same events — `round 1 · codex … running`, `round 1 · codex ✓ 186s`, `round 1 · gemini ✗ dropped (Timeout)` — each `print(…, flush=True)` so a background run streams instead of going dark until a round returns. These lines are **purely additive**: no existing pinned stdout line is touched (the `=== round N ===` banners and round tables the conductor already prints are byte-identical), so they need no golden.
  - **A self-refreshing `status.html` tracker**, regenerated on each event by a **pure function** of the status dict (`render_status_html`, deterministic and golden-tested from a fixture). `file://` JS can't fetch a sibling json in modern browsers, so the state is **inlined** and the page carries `<meta http-equiv="refresh" content="2">` while the run is live (a completed run's page is static — no refresh). Dark/compact, fully **self-contained** (inline CSS only; no external fonts/CDNs/JS/`<script src>`/`<link>` — renders offline), HTML-escaping every injected string. Its footer says, in as many words, that it is a **live view, not an artifact of record** — the verdict chain + `run-metadata.md` remain the authoritative outputs.
  - **RH-1 preserved:** the live view **defers its first disk write until the run has committed to spawning** (post-egress-approval, when `write_pre_spawn_artifacts` materializes the run dir), then flushes the full accumulated pre-spawn history (preflight + egress events) at once. A **preflight NO-GO leaves no dir; an egress-refused run writes only the refusal manifest (`egress-manifest.md` + `sensitivity.json`), never `status.*`** — exactly as before; the terminal lines for those phases still print (they don't touch disk). **Zero impact when opted out or on old runs:** `--no-live-status` writes no status files and every artifact of record is byte-identical; a completed run's `status.json`/`status.html` persist and read as done (a `finished` stamp + a terminal `outcome`). Wired into `cli.py` at the preflight/egress/round/synthesis/revision/endorsement transitions and into `rounds.run_round` via an optional, best-effort `on_seat` callback (back-compatible — every existing call site is behavior-identical). Docs: SKILL.md (`## How A Run Executes`), `scripts/README.md` (run-dir contents + the package-layout row). Suite 1404 → 1426.

### Fixed
- **`format_output.py` crashed on owner-carrying `next_actions[]` entries.** The schema says a
  `next_actions[]` entry is a string *or* `{action, owner}` and every renderer accepts both
  forms — `render_verdict.py` did, but `--format slack` raised `TypeError` on the join and
  `--format pr` printed the raw dict repr. Both short formats now render the same one-line
  form the implementation-sequence shape uses (`text — owner: NAME`), via the one normalizer
  in `render_verdict.py`; plain-string entries stay byte-identical.

## [v1.13.0] - 2026-07-02 — Transform: the board hands back a fixed copy

### Added
- **The endorsement pass (v1.13 #2 / P4, D13) — the board votes on the fixed copy.** A
  `run --output revised-draft` run is now **board-endorsed** by default, not merely
  findings-mapped: after the revision seat SUCCEEDS (all mechanical checks pass), every
  NON-revision board seat is spawned ONCE, all fanned out **concurrently** (the round
  `ThreadPoolExecutor` — wall-clock ≈ one extra round), to vote `ENDORSE` / `OBJECT` / `ABSTAIN`
  on **every edit and every unresolved conflict**. Each seat emits parseable per-target tokens
  (an `OBJECT` carries a short note — D13: a seat may object to how a conflict was
  characterized); the **conductor builds** the rows into `changes.json.endorsements`
  (`{seat, edit_n|unresolved_n, position, note?, dropped?}`) — the model authors tokens, never
  rows. **Objections are recorded, never resolved** — no discussion round, no revision loop; the
  human reads them and decides (D6). New `--no-endorse` opts out (the token-cost axis): that run
  is findings-mapped and `endorsements` stays `[]` (byte-identical to the revision seat's own
  build). New module `scripts/_conductor/endorsement.py` generalizes the revision spawn path
  (versioned template `advisory-board/endorsement@1` + sha, DATA-fence + neutralizer, two-attempt
  retry on `timeout|invalid`, black-box `endorsement/<seat>.raw`). **Failure posture:** a
  failed/unparseable endorsement spawn records that seat as one `ABSTAIN` row per target with
  `dropped: true`; the pass NEVER fails the run, discards the revision, or moves the exit code.
  If ALL endorsement seats drop, `changes.json` still writes those rows with one loud warning. A
  single-seat board (no non-revision seat) leaves `endorsements: []` with a note, not a crash.
  Write order: endorsement rows are merged into the changes dict BEFORE `changes.json` is written
  and BEFORE the pointer write, so `verdict.json.changes` sha-pins the endorsement-bearing bytes.
  Artifacts: `endorsement/<seat>.md`+`.raw` + `prompts/endorsement-<seat>.prompt` (mirrors
  `revision/`); the full-handoff HTML gains a small endorsement summary (per-edit tally +
  objection notes) in the redline/patch section — absent + byte-identical on a `--no-endorse`
  run. The recipe records the resolved `endorse` boolean + (when on) the endorsement template
  version/sha, so `--from-recipe` replays the same posture. On a **duplicate-provider board**
  (e.g. `--board claude,claude,codex`) the pass excludes only the seat that actually revised by
  its **unique id** — the other same-provider seat stays a full voting member — and every
  endorsement row + `changes.revision_seat` is keyed on that same id axis (`claude#2`), the same
  ids `--model`/`--timeout` use; `--revision-seat` selects on it too (an ambiguous bare provider
  name is refused, listing the candidate ids). On a non-duplicate board id == provider name, so
  `changes.json` and every artifact path stay byte-identical.
- **`run --output revised-draft` (v1.13 #2) — the revision seat + `changes.json`.** After
  synthesis produces a validated `verdict.json`, a board seat is spawned to produce a
  **board-derived, findings-mapped revised copy of the source**, each edit mapped by the model
  to the finding it resolves, mechanically validated (coverage reconciliation + index/title
  cross-assert). (The non-revision seats then vote on it — see the endorsement pass above.) The revision seat generalizes the synthesizer spawn path (versioned template
  `advisory-board/revision@1` + sha, DATA-fence + neutralizer, board-seat choice, two-attempt
  retry on timeout|invalid, black-box `revision/<seat>.raw`, rejected-artifact-plus-exit-0
  posture). The single spawn returns the **edit→finding mapping first and the revised source
  second**, so a truncated reply fails mechanically on the missing closing fence. §11 holds:
  the conductor **enumerates** the verdict's resolvable findings (blockers + concerns, by
  composite `{list, index, title}` locator) and hands them to the model; the model reasons the
  edits and the revised text; the conductor then **mechanically** cross-asserts every
  `resolves`/`findings` ref against the verdict (the `{list, index, title}` composite —
  index bounds-checked and `verdict[list][index].title == title`, D9), reconciles each edit
  locator 1:1 against the
  `difflib` diff (INV-1: every diff hunk claimed, every locator overlaps a real hunk),
  enforces completeness (every blocker resolved-or-`unresolved`; concerns best-effort), and
  computes `n`/`status`/the shas itself — never trusting a model assertion. Artifacts (gated on
  revised-draft; nothing else changes): `revised-draft.md` (prose) or `revised-draft.<orig-ext>`
  (code), **byte-clean — the revised source bytes and nothing else, no metadata header** (a
  header corrupts code on save); `changes.json` (schema `advisory-board/changes@1`, the artifact
  of record); and `revision/<seat>.md`+`.raw`. `verdict.json` gains a tool-authored
  `changes = {artifact, sha256}` pointer (written with `amend`'s re-read + sha-guard + atomic
  discipline; acyclic verdict → changes → {source, revised}). Conflicting findings degrade
  loudly as `unresolved` entries (surfaced on the run card, never fatal, never move the exit
  code — D14). A revision failure never discards the completed rounds/verdict:
  `revised-draft-rejected.*` + `changes-rejected.json` + a loud warning + exit 0 (`--strict-exit`
  → exit 4, the synthesizer's code).
- **`--output revised-draft` resolve-time contract.** Requires a verdict path (`--synthesize`,
  or a `--from-recipe` replay of a synthesized revised-draft recipe) — refused at resolve time
  otherwise (exit 2). New `--source-type prose|code` (accepted only with revised-draft) selects
  the redline format downstream; the resolved value comes from `--source-type` or a conservative
  extension heuristic (prose: `.md/.markdown/.txt/.rst/.adoc`; code: a known-extension list) —
  an unknown extension or a stdin source without the flag is refused. New `--revision-seat SEAT`
  mirrors `--synthesizer-seat` (must be a board seat). A source over **65536 bytes** (env override
  `ADVISORY_BOARD_REVISION_MAX_BYTES`) is refused loudly — better a loud refusal than a silently
  short board-derived copy. The resolved `source_type` and revision seat/template are recorded
  in `run-recipe.yaml` so a `--from-recipe` replay reproduces exactly.
- **`scripts/board_changes.py` — the `advisory-board/changes@1` validator.** An importable
  `validate()` plus a small CLI (validate a `changes.json`), stdlib-only, mirroring
  `board_verdict.py` discipline (clean `die()`, exit 2 on schema violation, strict — unknown
  top-level keys refused, exact field types, locator shape checks, `resolves`-list enum
  {blockers, concerns}). The conductor validates every `changes.json` with it before write; a
  failure takes the reject path.
- **Prose redline in the full-handoff HTML (v1.13 P3, D12).** A `run --output revised-draft`
  against a **prose** source now renders a word-level-within-changed-lines redline of the
  original vs. the board's revised draft as a new section in `final-consensus.html`
  (`--shape full-handoff` only). New `scripts/_conductor/redline.py`: a pure, stdlib-only view —
  `difflib.SequenceMatcher.get_opcodes()` line-level (context/delete/insert/replace, long
  unchanged runs collapsed to `REDLINE_CONTEXT_LINES` (2) on each side of a change plus a gap
  row), then a second word-level `SequenceMatcher` pass inside each `replace` pair so only the
  changed WORDS carry `<ins>`/`<del>` spans, not the whole line. Capped at `REDLINE_MAX_LINES`
  (400) rendered rows, with a truncation row pointing at `revised-draft.md` for the rest.
  `render_verdict.py` walks the **sha trust chain** before rendering a byte: `verdict.changes`
  pointer → `changes.json` (sha-checked) → `source-material.txt` (hashed against
  `changes.source.sha256` — the equivalence the run persists but never elsewhere asserts) and
  `revised-draft.*` (sha-checked against `changes.revised.sha256`); any mismatch, missing
  artifact, or malformed pointer **degrades to the section being absent** with one stderr
  warning, never a crash and never a partial render. `references/handoff-template.html` gains
  the `redline-sec` section (RAW token `REDLINE_HTML`, one row per redline line) behind the same
  tempered-comment drop discipline as the delta/amendment sections — absent on any
  non-revision run, byte-identical to before.
- **Code patch artifact + HTML patch section (v1.13 P3, D12).** A `run --output revised-draft`
  against a **code** source now also writes `revised-draft.patch` — a git-apply-able unified
  diff (`a/<name>`/`b/<name>` headers, `git apply -p1`) built by the new
  `_conductor/revision.build_unified_patch` from the **same sha-pinned strings** `changes.json`
  already certifies (source over the original, revised over the byte-clean draft) — a redundant,
  human-apply-able *rendering* of the change, not a new trust surface. It's the code sibling of
  the prose redline: the full-handoff HTML gets a `patch-sec` section (RAW token `PATCH_PRE`)
  instead of `redline-sec` for a code source — at most one of the two ever renders. A stale
  `.patch` from a prior code run is cleaned up when a later run on the same `--out` is prose.
  `run-card`/artifact-tree output (`_conductor/artifacts.py`) lists the patch for code runs.
- **Grounded citation snippets (v1.13 P3, #12).** `verify_evidence.py` now captures the cited
  lines onto a resolved `code` citation's evidence entry (`snippet: {from, to, text}`) so
  `final-consensus.md` (both the full-handoff and implementation-sequence renders) embeds the
  receipt itself as a fenced `path:from-to` code block, not just its coordinates — the handoff
  stays self-contained even after a grounded run's repo snapshot is cleaned up. A `{path, line}`
  citation captures the cited line ± `SNIPPET_CONTEXT_LINES` (2, clamped at file edges); a
  `{path, symbol}` citation captures the first `SNIPPET_SYMBOL_LINES` (8) of the resolved region
  from the symbol's first match. Capped at `SNIPPET_CHAR_LIMIT` (4000) chars, marked
  `…[truncated]` on a cap hit. **Sha-gated on a grounded run:** when the run dir carries
  `repo-scope-manifest.json` (new `verify_evidence.load_scope_manifest`), a manifest-listed file
  captures a snippet only if its **live** sha256 still matches the manifest's — a file that
  changed since the board reviewed it keeps its `verified`/`refuted` badge but gets **no**
  snippet (never embed lines the board didn't see). An ungrounded `--source` (no manifest)
  captures freely, matching `verify`'s existing trust model. A re-verify always drops any prior
  `snippet` before re-resolving, so a stale capture from an earlier pass can never survive. The
  console summary reports how many snippets were captured (and whether sha-gated).

### Changed
- **`verdict.json`'s reserved `changes` key is now defined (v1.13).** `board_verdict.py`
  accepts `changes`, when present, as **exactly** `{artifact: <non-empty str>, sha256: <64-char
  lowercase hex>}` — strict-when-present, unknown keys refused (replacing the blanket "reserved"
  refusal). It is tool-authored: the synthesizer merge still strips a model-supplied `changes`
  (a model must not fabricate revision provenance). `references/verdict-schema.md` documents the
  pointer shape; the new `references/changes-schema.md` documents the full `changes@1` schema.
- **Evidence gains an optional `snippet` field (v1.13 P3, #12).** `board_verdict.py` now
  validates a `snippet` on any `evidence[]` item, strict-when-present: exactly `{from: <int ≥
  1>, to: <int ≥ from>, text: <non-empty string>}`, unknown keys and bool-as-int both rejected.
  It's tool-authored — written by `verify_evidence.py` at stamping time, the same discipline as
  `status` — and absent means invisible: a verdict with no `snippet` fields validates and
  renders byte-for-byte as before. `references/verdict-schema.md` documents the shape and who
  writes it.

## [v1.12.0] - 2026-07-02 — The decision loop

### Changed
- **Claude seat: Opus 4.8 registered as the one sanctioned fallback.** The seat's default
  stays `claude-fable-5` at `--effort max` (the depth flagship); `fallback_models` now names
  `claude-opus-4-8` — probe-and-propose only when Fable 404s, never auto-applied — and
  SKILL.md documents it as the sanctioned per-run downgrade when Claude usage matters more
  than Fable-tier depth (`--model claude=claude-opus-4-8`; Opus 4.8 accepts the same
  `--effort max`, grounded live 2026-07-02 on CLI 2.1.191). SKILL.md also notes the
  zero-Claude-usage posture: seat a board without the Claude seat (`--board codex,gemini`) —
  every seat bills its own subscription.

### Added
- **`board_verdict.py amend --run <dir> --author … --reason … <effect>` (v1.12 #5) —
  human-owned, append-only verdict tuning.** Tune a completed verdict without touching the
  board's words: `amend` **appends** an `amendments[]` entry and never rewrites `confidence`,
  blockers, or concerns. Exactly **one effect per invocation** — `--confidence {low,medium,high}`
  (records `field: confidence` with `from` = the effective value *before* this amendment and
  `to` = the new one; a no-op is refused), `--caveat TEXT`, or `--severity-note TEXT` optionally
  scoped by `--on "<finding title>"` (a **strict** match against an existing blocker/concern
  title — a mismatch dies listing the available titles). Provenance (`author`/`reason`/
  `timestamp`) is required; the timestamp honors `$ADVISORY_BOARD_NOW_TS` for reproducible runs,
  else the local ISO-8601 now. The file is re-validated and **atomically** rewritten. A new
  module-level `effective_confidence(data)` (the last confidence amendment wins, else the board's
  own value) is the single source renderers read; `summarize()` now shows the effective
  confidence **with** its provenance and an `amendments:` breakdown line — but **only when
  amendments exist**, so an un-amended verdict prints byte-identically. `_validate_lifecycle`
  now checks the effect fields strictly **when present** (additive; a zero-effect entry from P1
  still validates). The gate is untouched — an amendment never moves a gate outcome. **All
  renderers now display amended values WITH provenance and never as the board's own:** the
  consensus Markdown (and the implementation-sequence view) show the effective confidence with an
  "amended from … by …" clause, mark caveat amendments as human-added alongside the board's own
  caveats, attach a severity note to its matching blocker (exact `--on` title match — unmatched /
  `on`-less notes land only in the trail), and carry a new **Amendments** section with the full
  ordered trail (author, timestamp, reason, effect; a zero-effect entry renders as a
  provenance-only note); the HTML handoff gains a visually distinct (gold-edged, human-owned)
  Amendments section plus an effective-confidence pill marked `(amended)`, both wired through the
  pre-v1.12 backfill so a new token never breaks an old template and vice versa; and `tldr` / `pr`
  / `slack` append a terse `(amended)` marker to the effective confidence (`--format json` still
  echoes the verdict verbatim). A verdict with **no** amendments renders byte-identically to
  before in the consensus Markdown, the implementation-sequence Markdown, and the `tldr`/`pr`/
  `slack` short formats; the HTML handoff's rendered body is likewise byte-identical (the only
  change is additive, inert CSS for the amendment styling — the dropped optional blocks leave no
  whitespace residue) — all test-enforced.
- **`ask "<question>" --run <dir> [--seat <id>]` (v1.12 #4) — post-verdict cross-examination.**
  Put a follow-up question to a COMPLETED run's board without a full re-review. `ask` loads the
  run's recorded board from its `run-recipe.yaml`, builds a context packet **bounded to that run's
  own artifacts** — the reviewed material (recovered from `source-material.txt`, sha-verified, or
  degraded loudly), a MECHANICAL digest of the prior verdict (reused from `--revise`; tokens /
  titles / citations, never a summary, §11), and **each addressed seat's own last USABLE review**
  for continuity (a dropped-round `no usable review` placeholder is skipped in favor of the seat's
  last real position — adversarial correctness fix) — then fans ONE round out to the addressed
  seat(s) (`--seat <id>` targets one; the default is every seat). It writes `addendum-N.md` (the
  Q&A + falsifiable per-seat prompt/packet hashes), an `addendum-N/` egress record (manifest +
  `sensitivity.json` + the exact per-seat prompts), a machine `addenda.json` index, and refreshes
  a managed **Post-verdict addenda** block in `final-consensus.md` (idempotent, rebuilt from the
  index; block content is sentinel-neutralized and the splice only honors an ordered BEGIN→END
  pair, so a marker-bearing question or a hand-corrupted file can never cascade corruption —
  adversarial security fix). **Consent re-decides for the new
  bytes**: the ask packet gets its own content hash through the SAME egress gate a fresh run uses
  (public discloses and proceeds; non-public requires hash-bound `--yes`/interactive approval and
  refuses non-interactively), and the effective sensitivity is the **strictest of the recipe's
  value, the run's `sensitivity.json`, and an operator `--sensitivity` floor (tighten-only)** —
  an ask never egresses under a looser posture than the material was handled with, a local-only
  run with external seats is refused, and (from the adversarial security review) a run with **no
  readable `sensitivity.json` never floats down to public**: its original posture is unknown, so
  public floors to redacted, loudly, with the flooring recorded on the consent record — the disk
  values live inside a (shareable, tamperable) run dir, so the posture cannot rest on them alone.
  Grounding is forced OFF
  (a grounded run's `ask` still egresses only artifacts, never a live repo read). The injected
  run-context is **byte-neutralized** against fence-marker echoes (a new `PRIOR RUN CONTEXT` fence
  family, since it embeds prior MODEL output), the question rides OUTSIDE that data fence as the
  operator's instruction, and every recovered file is a **bounded read** (symlinked or out-of-tree
  artifacts refused). The one-round fan-out reuses the round runner with a lighter classifier
  (`classify_ask`) — an answer is free-form prose, not a 7-section review. Own template family +
  sha (`advisory-board/ask@1`), recorded on the addendum's egress record.
- **`--revise <prior run dir | verdict.json>` (v1.12 #1) — re-review a revised draft with the
  prior verdict as context.** `--source` is the revised draft; the round-1 prompts additionally
  carry a fenced, neutralized block holding a MECHANICAL digest of the prior verdict (tokens,
  titles, citations — never a summary, §11) plus the unified diff from the previously reviewed
  draft to the current material (capped at 400 lines, loudly). The injected bytes live inside
  the packet blobs, so the egress **consent hash covers them with no new machinery**, the
  run card / dry-run disclose them, and the template-sha discipline holds: the version records
  a `+revise@1` suffix (`advisory-board/round1@2+revise@1`, composing with grounded `@3`) while
  a non-revise run's prompts, template sha, and recipe stay byte-identical. To make the diff
  possible every run now persists `source-material.txt` (an exact source copy, post-approval —
  the same bytes the persisted prompts already embed; `references/data-handling.md` notes it);
  revising a pre-v1.12 run recovers the prior source from a persisted round-1 prompt,
  **sha-verified against the recipe**, and degrades loudly to digest-only when unrecoverable.
  The conductor pins `previous_run` lineage (run dir, prior verdict token, verdict sha256) into
  the synthesizer skeleton — the one path lifecycle fields can enter a synthesized verdict —
  and a revise run's recipe records `revise_of`, so `--from-recipe` replays the same lineage
  (the flag pair itself is refused as contradictory). **Consent-surface hardening** (from the
  adversarial security review): the pre-approval disclosure line, the egress manifest (its own
  section, mirroring grounding's scope disclosure), and `sensitivity.json` all name the
  injection and its provenance; a prior run with a **stricter declared sensitivity** (e.g.
  `local-only`) refuses to revise under a looser run — material never silently escalates; the
  injected material is **byte-neutralized** against fence-marker echoes (the round-2 defense,
  whose marker family now covers the revise fence); recovery is labeled **sha-verified vs
  UNVERIFIED** on every surface, symlinked prior artifacts are refused, and marker-parsing
  prompt extraction is only trusted when the recipe records a `source_sha256` to verify
  against (a prior source containing the marker line can never yield a silently truncated
  diff).
- **Cross-run delta in the consensus (v1.12 #1).** New pure `_conductor/delta.py` classifies
  blockers/concerns across the two runs — cleared / still-open / new — by exact normalized
  title, then shared concrete citations, then guarded stdlib title similarity (mechanical
  only; a reworded finding with nothing shared honestly shows as cleared+new). Matching runs
  as **global tier passes** (an exact title always beats an earlier item's fuzzy pairing), a
  bare file path counts as a citation only when the evidence carries no line/symbol (a
  single-file review must not collapse into all-still-open), and the similarity tier requires
  a shared substantive token on top of the ratio floor. `final-consensus.md`
  and the full-handoff HTML lead with a **trajectory banner** (prior → new verdict, lens-aware
  labels) and the three buckets, derived at render time from `previous_run` (nothing new is
  stored in verdict.json — D8 holds): the prior verdict.json is re-read and checked against
  the recorded `verdict_sha256`, and the section degrades to an honest one-liner when the
  prior run moved or its artifacts changed. Non-revise verdicts render byte-identically, and
  pre-v1.12 `handoff-data.json` files still render.
- **Verdict-lifecycle schema fields (v1.12 Phase 1)** — ONE additive evolution of
  `advisory-board/verdict@2` (the version string does not change; a verdict without the new
  fields is byte-for-byte the same schema as before): optional `previous_run` lineage (object;
  required non-empty `run_dir`, optional `title`/`date`/`verdict`/`verdict_sha256` — the sha
  binds lineage to the prior verdict's *content*, not a movable path) and optional append-only
  `amendments[]` (each entry requires the provenance trio `author`/`timestamp`/`reason`; effect
  fields arrive with the `amend` tooling). Both are validated strictly WHEN PRESENT — like
  evidence, identically under either schema id (`@1` included) — and are invisible when
  absent; the gate never reads them. Every renderer reads named fields only, so
  a lifecycle-carrying verdict renders identically — test-proven for the consensus markdown,
  the implementation-sequence shape, the handoff data (the HTML's input), and the
  tldr/pr/slack formats (`--format json` deliberately echoes the whole verdict, lifecycle
  fields included). The top-level
  `changes` key is RESERVED for the v1.13 revision artifact and refused loudly while undefined.
  Lifecycle fields are tool/human-authored, never model reasoning: the synthesizer merge now
  strips them (new `LIFECYCLE_KEYS`, alongside the protected skeleton keys) so a model reply
  cannot fabricate an amendment trail or a prior-run link. This is the single schema evolution
  v1.12's `--revise` / `ask` / `amend` build on — no further ad-hoc bumps.

## [v1.11.0] - 2026-07-01 — Transparency & foundations

Know before you convene, and keep what you ran. A board run now tells you its **cost and
time up front** (`--dry-run` estimate) and records what each seat actually spent where the
CLI reports it; one flag — **`--tier quick|standard|deep`** — sets the whole cost/depth
posture; run artifacts land in a **persistent runs root** with a `history` listing instead
of evaporating from `/tmp`; a **setup doctor** walks a brand-new machine to its first
viable board; and the round-2+ structured digest is available as **typed JSON** for
tooling, alongside per-seat `--timeout` and a real `implementation-sequence` render. A
default run — no new flags, tokens unreported — stays byte-identical to v1.10.0 artifacts
except the (loudly documented, opt-out) runs-root move.

### Added
- **`--tier quick|standard|deep` (v1.11 #3b)** — one flag for the run's whole cost/depth
  posture, applied as a BASE beneath explicit flags: `quick` = 1 round, `summaries`
  cross-reading, reduced per-seat reasoning (claude `high`, codex `medium`); `standard` =
  today's defaults (a deliberate no-op); `deep` = 3 rounds, `full` cross-reading at the
  registry's max-tier reasoning (codex stays at `xhigh`, its hard API ceiling —
  test-guarded). Model ids are deliberately NOT a tier knob (no unverified "budget" id may
  404 the board); reasoning is keyed by provider so duplicate/aliased seats move together,
  and seats without an effort knob (gemini/antigravity/ollama) are untouched at every tier.
  `--rounds`/`--cross-reading` always win over the tier; `run-metadata.md` gets a one-line
  tier provenance note only when the flag was given (a no-tier run stays byte-identical);
  `run-recipe.yaml` records the RESOLVED values, never the tier name, so `--from-recipe`
  replays exactly — the pair is refused as contradictory.
- **`--digest-format markdown|json`** on `run` (default `markdown` — existing behavior untouched):
  with `json`, each round-2+ structured digest is ALSO written as typed JSON —
  `board-packet-round-N.json` (`advisory-board/board-packet-digest@1`) next to the `.md` — carrying
  the same parsed signals the markdown digest already computes: per-seat `VERDICT` tokens + the
  agreement summary, the shared (≥2-seat) citation set, every canonical topic with each seat's
  head-excerpted take, and the unparsed-review fallbacks. A serialization of what exists, not new
  reasoning (§11); requires `--cross-reading summaries` (refused loudly otherwise). Golden-file
  tested against the committed payments example.
- **Per-seat `--timeout`**: `--timeout SECONDS | SEAT=SECONDS`, repeatable. A bare value applies to
  every seat (the old single-value syntax keeps working unchanged); `SEAT=SECONDS` overrides one
  seat, targeted by id exactly like `--model`/`--lens` — an unknown id fails loudly. The resolved
  value threads config → rounds → spawn (tested at the spawn call), and the synthesizer honors its
  seat's value. Run-only; deliberately not recipe-persisted.
- **`--output implementation-sequence` is now a real, distinct render** (previously it fell back to
  the full handoff). `render_verdict.py --shape implementation-sequence` renders a sequence-first
  view of the same `verdict.json`: the ordered `next_actions[]` lead — the full list, with the
  owner named where the verdict carries one — backed by the blockers each step must clear with
  their evidence trails. Emits `implementation-sequence.md` plus a matching self-contained HTML
  shape (`references/implementation-sequence-template.html`, same template machinery and brand as
  the other shapes), deterministic from `verdict.json` like every render. `next_actions[]` entries
  may now be `{action, owner}` objects; plain strings render byte-identically everywhere.
- **Setup doctor** (`run_board.py doctor`, #7) — guided onboarding for a brand-new machine: sweeps
  **every** registered provider (claude, codex, gemini, antigravity, ollama), not just a chosen
  board, reusing the toolchain currency probe (installed → version vs latest) and the preflight
  seat probe (auth → default model resolves → smoke) per provider. Prints a per-provider status
  block with concrete fix-it steps (install command, auth command, model fallback, stale-CLI
  update), then a viable-board summary (≥ 2 seats GO) with a suggested first command (a `--dry-run`
  on the bundled sample source). No user material egresses — probes and smoke-pings only, and the
  output says so. Exits non-zero when no board is viable, so scripts can branch on it.
  (`scripts/_conductor/doctor.py`; probe logic stays in `preflight.py`/`toolchain.py`.)
- **Per-seat token capture (v1.11 #3a).** `SeatRoundResult` gains nullable
  `tokens_in`/`tokens_out`/`tokens_total`, filled by per-adapter `parse_usage`
  parsers in `registry.py` that read ONLY what each CLI unambiguously reports
  about its own usage (grounded live 2026-07-01): codex's trailing
  `tokens used` stderr footer (a combined total — no in/out split), and
  claude's `--output-format json` result envelope (plain `-p` text mode — the
  board's argv today — prints no usage, so the seat honestly reports unknown).
  gemini / antigravity / ollama print nothing and stay unknown. Never guessed.
- **Preflight cost/time estimate.** A dated list-price table
  (`constants.MODEL_PRICING_USD_PER_MTOK`) plus a pure `estimate_run()`
  (source bytes × seats × rounds × cross-reading → token band, cost band,
  rough minutes), surfaced as an `=== estimate ===` block in `run --dry-run`
  and pointed at by SKILL.md's flag-a-large-run guidance. Best-effort and
  labeled an ESTIMATE — never a gate; unverified prices render as unknown,
  not $0.
- **"If known" cost/time rendering.** When any seat CLI reported usage:
  per-seat token lines and a `## Cost & time (best effort)` section in
  `run-metadata.md`, three trailing token columns in `run-metadata.tsv`, and a
  seat-reported totals segment in the `final-consensus.html` footer (read from
  the run dir's TSV). With no usage reported — every mocked/default run today —
  all three artifacts stay **byte-identical** to the pre-feature baseline
  (guarded by tests).
- **`run_board.py history`** — a table of past runs (date, title, verdict, confidence,
  unanimous, seats, run dir) read from each run's `verdict.json` under the runs root, with the
  same lens-aware human verdict labels the consensus artifacts use. Partial/legacy runs (missing
  or malformed `verdict.json`) degrade to `run-recipe.yaml` and list as `incomplete` — the
  listing never crashes. Local disk read only; honors `--runs-root` / `$ADVISORY_BOARD_RUNS_ROOT`.
  New `scripts/_conductor/history.py` module.

### Changed
- **Persistent runs root (v1.11 #5) — runs stop evaporating.** Default run artifacts now land
  under `~/.advisory-board/runs/<slug>-<date>/` (slug from the run's resolved title, date from
  the deterministic run date; a same-day collision gets a `-2` suffix, never an overwrite)
  instead of a throwaway `/tmp/advisory-board-<ts>` folder. Overrides: `$ADVISORY_BOARD_RUNS_ROOT`
  (env) and `--runs-root DIR` (flag, wins over env) relocate the root; `--out DIR` still names an
  exact dir; `--ephemeral` opts back into the pre-v1.11 `/tmp` behavior. Contradictory
  combinations (`--ephemeral` + `--out`, etc.) are refused loudly. Every real run now announces
  where its artifacts land on its first output line. A `--from-recipe` re-run keeps today's
  semantics — it reuses the recipe's *recorded* dir (now persistent, so replaying rewrites that
  run's artifacts in place; the notice says so) unless `--out`/`--runs-root`/`--ephemeral` point
  it somewhere fresh. Artifact *content* is unchanged —
  persistence is a disk-location move only, and persisted artifacts inherit the run's
  sensitivity handling (`references/data-handling.md` gets a "Persisted run artifacts" section).

### Fixed
- **Snapshot leak checks are now process-local (test-only).** Three tests asserted a
  before/after glob of the machine-wide tempdir for `advisory-board-repo-*`, so any
  concurrent suite (sibling worktree, parallel CI) creating or removing its own snapshots
  flaked them. A `_private_tempdir` helper now redirects `TMPDIR` to a fresh per-test dir
  for the run, and the tests assert *that* dir holds no snapshot afterward; the
  failure-path test additionally probes mid-prepare that the snapshot really landed there,
  so the check can't pass vacuously.

## [v1.10.0] - 2026-07-01 — Claude seat on Fable 5 at max effort

The Claude seat now defaults to **Fable 5** (`claude-fable-5`), Anthropic's most capable model,
and runs it at **max reasoning**. The seat's effort is now forwarded to the CLI via `--effort max`
— previously the seat computed a reasoning value but never passed it, so it ran at the CLI's own
default. Max effort is scoped to the Claude seat (the only CLI that exposes a `max` level): Codex
stays at `xhigh` (its ceiling — `model_reasoning_effort=max` returns a 400), and
Gemini/Antigravity/Ollama expose no effort knob.

### Changed
- **`scripts/_conductor/registry.py`** — Claude seat `default_model` `claude-opus-4-8` →
  `claude-fable-5`; `default_reasoning` `xhigh` → `max`; `claude_argv()` now forwards
  `--effort <reasoning>`; `flags_verified_version` → `2.1.191`.
- **`SKILL.md`, `references/run-metadata-template.md`, `references/verdict-schema.md`** — model
  lineup, the Claude CLI template, and examples updated to Fable 5 / `--effort max`, with a
  premium-tier cost note and the `--model claude=<id>` override.

### Fixed
- **`--from-recipe` now reproduces per-seat reasoning.** Recipe replay restored model and lens but
  re-pulled reasoning from the live registry, so a recipe recorded at `xhigh` would have silently
  replayed at the new `max` default. `resolve_board` takes reasoning overrides and the replay path
  restores recorded reasoning; guarded by a new round-trip test.

Also since v1.9.0: the **relocation gallery example** and its README "See It In Action" lead
(#45), and the seat-composition plan marked SHIPPED (#46, docs-only).

## [v1.9.0] - 2026-06-28 — Flexible seat composition

Seat the **same provider more than once** (`2 Opus + 1 Codex`, `3 Opus`) with a unique `seat.id`
and per-seat lenses. `--board` entries are `provider` or `alias=provider` (bare repeats
auto-number `claude#1`/`#2`; aliases read cleaner); `--lens` is repeatable (bare = the board
preset, `id=value` overrides one seat's focus). `--model`/`--lens` target seats by id. Duplicate
seats no longer silently collapse — that is now a loud failure — and a run stays reproducible via
`--from-recipe`. A default `claude,codex,gemini` board is byte-identical to before (the regression
guard).

### Added
- **Flexible seat composition** (#44) — `seat.id`, alias/auto-numbering, and per-seat lenses,
  re-keyed across the conductor onto `seat.id`; `TestSeatComposition` plus duplicate/alias E2E.
  Gated by three parallel adversarial skeptics (identity-collision, egress/consent, byte-identical
  + recipe) → zero confirmed defects.

### Fixed
- **`--shape` documented** and the quick-verdict render no longer leaves a stray
  `final-consensus.md` (`--out` defaults to none) (#43).
- **Untracked confidence renders cleanly** in Markdown and the short formats — the clause is
  dropped (matching the HTML pill), so no more literal `(? confidence)` (#42).

## [v1.8.0] - 2026-06-27 — Quick-verdict skim-brief shape + confidence pill

### Added
- A **quick-verdict (skim-brief) output shape** that leads with the verdict for fast skimming,
  plus a **confidence pill** in the artifact banner (#40).

## [v1.7.2] - 2026-06-27 — Lens-aware consensus artifact

### Changed
- The **consensus artifact leads with the plain-language, lens-aware verdict** — a plain verdict
  lead plus a matching section heading — carrying the v1.6.0 plain-language label into the
  consensus surface (#39).

## [v1.7.1] - 2026-06-27 — Artifact lockup: "Advisory Board, powered by Panely"

The artifact masthead and footer now lead with **Advisory Board** as the product, with
**powered by Panely** as a maker attribution beneath it — previously the lockup bundled
"Panely Advisory Board". This keeps the skill and the Panely app cleanly distinct, while
still crediting the maker. Template-only: no behavior, renderer, or schema change.

## [v1.7.0] - 2026-06-26 — Panely Advisory Board brand

The human-facing artifact is now a branded **Panely Advisory Board** deliverable — the
review's strongest marketing surface. The body stays light and readable, bookended by
dark masthead and footer bands carrying the Panely "decision core" mark, the *Panely
Advisory Board* lockup, the "use your own subscriptions to Claude, Codex, and Gemini"
line, and a **panely.ai** call-to-action. The verdict-JSON contract, the section
structure, the honesty sections, and the lens-aware label/disclaimer are all unchanged.

### Changed
- **`references/handoff-template.html`** — re-skinned into the Panely identity: a dual
  theme (light "Boardroom" body + dark "Signal" masthead/footer bands), cobalt `#2347FF`
  signature accent, gold `#E2B658` lead-seat secondary, muted verdict colors, Signal
  font stacks, and an inline self-contained glowing avatar in the masthead with a flat
  favicon in the footer. Every `{{TOKEN}}`/block and the renderer-contract shapes (the
  `verdict {{VERDICT_CLASS}}` class, the `disclaimer`/`seat-status`/`highlight`/`conf`
  spans, the `.review-body` list-indent rule) are preserved — the suite stays green.

### Fixed
- **Two developer strings no longer leak onto the page** (`scripts/render_verdict.py`):
  the masthead **subtitle** now describes what was reviewed (was "Rendered from the
  canonical verdict.json."), and the footer **provenance** reads in human terms —
  "Board: … · N rounds · date" (was "Rendered from verdict.json by
  scripts/render_verdict.py.").

## [v1.6.0] - 2026-06-26 — Plain-language, lens-aware verdict label

The machine token `verdict: ship|caution|block` stays byte-identical (the gate
axis is untouched), but the **human-facing label** is now lens-aware. A
`software-architecture` board keeps the familiar `SHIP` / `SHIP WITH CHANGES` /
`DO NOT SHIP YET`; every other lens preset (product, research, legal, business,
writing — and any unknown one) renders plain language — `Go ahead` / `Proceed
with care` / `Stop and rethink` — plus a one-line "what this means" note, so a
non-developer reader isn't handed shipping jargon. An explicit `decision` field
still wins verbatim.

### Added
- **`lens_preset` in `verdict.json`** — the conductor writes the run's board-level
  lens preset name into the canonical verdict so the renderers (which read it
  standalone) can pick the right label family. Type-checked (optional string) by
  `board_verdict.py`; documented in `references/verdict-schema.md`. A wholly
  absent field defaults to the software family (backward compatible: every
  pre-feature verdict.json was a software-lens run).
- **Shared `scripts/_verdict_labels.py`** — one `human_label(token, lens_preset,
  decision)` source of truth so the three renderers stop diverging (they each
  carried their own, already-drifted, label map).

### Changed
- `render_verdict.py` (Markdown headline, handoff `verdict`/`verdict_note`,
  per-round pills) and `format_output.py` (`verdict_line`) now resolve labels
  through `_verdict_labels.human_label`. The handoff banner color
  (`verdict_class`) stays keyed on the **raw** token, not the label. Plain labels
  keep their natural case (no shouted "STOP AND RETHINK").
- The M2 synthesizer prompt gains a light `decision` optional-field nudge
  (template version `synthesizer@1` → `@2`).

## [v1.5.0] - 2026-06-26 — Repo-grounded review (`--repo`)

Optional `--repo PATH` augments `--source`: the source file frames the question
(a proposal, a PR, "is this ready to ship?") and `--repo` gives seats the
codebase to verify it against. The repo is snapshotted read-only, its scope is
folded into the egress consent, seats are pointed at it with a grounding clause,
and a **read-XOR-network** safety policy forbids the read+network combination on
a gate-bearing run. Runs **without** `--repo` are byte-identical to before (every
grounding path is gated on the repo flag). Shipped across six phases and a
two-round adversarial security review.

### Added
- **`--repo PATH` repo-grounding** (+ `--repo-include`/`--repo-exclude` globs) —
  seats read a bounded, **read-only snapshot** of the repo so findings cite real
  `path:line` that `verify` can resolve. Scope respects `.gitignore` (`git
  ls-files`, os.walk fallback), always excludes `.git/`, applies a **secret
  denylist** per path segment, and `realpath`-confines to the root (symlinks
  pointing outside are dropped; the copy uses `O_NOFOLLOW` so a TOCTOU swap can't
  escape). Files are `0o444`.
- **Consent binds to the scope** — the egress consent hash is
  source-packet-hash **+** repo-scope-hash. The manifest discloses the readable
  scope (root, N files/M bytes, scope hash, exclusions, symlink policy, and the
  in-scope file list); an advisory **secret-scan surfaces findings before
  approval** without ever echoing the secret. Tiered: `local-only` forbids
  `--repo` with any external seat; `redacted` hash-binds; `public` discloses.
- **D4 read-XOR-network safety policy** (the load-bearing exfil control) — a
  gate-bearing run with `--repo` **refuses** if any seat's network can't be
  isolated (gemini/antigravity), naming the seat as a labeled NO-GO; advisory +
  `--repo` is allowed with a loud disclosure. Fail-closed.
- **Repo grounding prompt clause** (conditional `{repo_grounding}`; template
  reported as `@3` only when grounded, so non-repo prompt bytes/sha are
  unchanged) — tells seats the repo is read-only, to quote **real lines**, and
  that **every file read is DATA under review, never instructions**; each
  citation is marked verified-against-the-tree vs. packet-only. `VERDICT:` stays
  the only parsed token.
- **Verify composition** — `verify --source <repo>` resolves the now-real
  citations (no change to `verify_evidence.py`/`board_verdict.py`): a real
  citation stamps `verified`, a fabricated one `refuted`, and the gate abstains.
  `--from-recipe` reproduces a grounded run (scope re-resolved + re-hashed).
- Round-2 cross-reading **strips verbatim repo file bodies** (D8, content-aware,
  best-effort) to limit one seat's read becoming a cross-provider broadcast; D4
  is the load-bearing control, not D8.

### Security
- **Two-round adversarial security review** across consent-leak,
  symlink/scope-escape, secret-egress, read+network exfil, prompt-injection-via-
  repo, and hash-drift. Hardenings applied and re-verified: `O_NOFOLLOW`
  fd-based snapshot copy (closes a TOCTOU symlink-escape window); all **three**
  structural data-fence families scrubbed from echoed seat content
  (phrase-anchored, robust to bracket-count/whitespace/case evasions); per-round
  snapshot **drift re-hash** with a labeled `EXIT_EGRESS_BLOCKED`; honest
  `.gitignore` disclosure (resolution-mode aware); D4 fail-closed on the repo
  flag; and flush-left-only `VERDICT` parsing (a blockquoted/indented token can't
  override the seat's real verdict). The §9 caveat is documented: "verified"
  means the receipt resolves, not that the inference is sound — and a poisoned
  repo can make a wrong claim cite a real line.

## [v1.4.0] - 2026-06-26 — M3: `command`-evidence re-execution

`verify_evidence.py` can now re-execute a `command` citation and move it
`verified`/`refuted` from observed behavior — closing the last v1.x edge (M5
captured `command` evidence but never ran it, so those citations stayed
`unverified`). Re-execution is **opt-in and allowlist-gated**: re-running a
command cited as evidence is an execution surface, and a verdict synthesized from
untrusted source (the M2 synthesizer over poisoned reviews) can carry an
attacker-influenced command — so the default is unchanged (commands stay
`unverified`) and the allowlist is the load-bearing control.

### Added
- **`command`-evidence re-execution (M3)** — `--allow-program NAME` (repeatable)
  ENABLES re-execution for commands whose **argv[0] is exactly that bare program
  name**; everything else stays `unverified` with a recorded `status_reason`. The
  **program allowlist is the load-bearing control** — argv[0] is pinned to a program
  you name, never a path (`./x`, `/bin/sh`, `../x` are refused) and never chosen by
  a regex. `--allow-command REGEX` (repeatable, optional) further requires the full
  command to `re.fullmatch` a pattern — for pinning **args**, not the program; it
  refines, never widens, the program allowlist and cannot enable re-execution on
  its own.
- **Layered containment** (hardened after a security review found 3 RCE paths):
  **no shell** (`shlex.split` + `shell=False` → `;`/`|`/`>`/`$()`/globs are inert
  literal args); a **curated PATH** (inherited PATH minus `.`/empty/relative
  entries) + a **resolves-inside-cwd guard** so a `pytest` planted in the reviewed
  source can't shadow the real one; an **isolated throwaway cwd by default** (NOT
  the source tree — `--rerun-cwd DIR` opts into a real tree) with **HOME pointed at
  it** so `~/.aws`/`~/.ssh` aren't reachable; a **scrubbed env** (no inherited
  `PATH`/`HOME`/secrets; only locale vars); stdin closed; and a **process-group-
  killed** hard timeout (`--rerun-timeout`, default 30s).
- **Structural match only** (design §11 / principle #1): `verified` iff exit ==
  `expect_exit` (default 0) AND any verbatim `expect` substring is present —
  decided over the FULL output, never a reading of its meaning. `observed` carries
  the exit, a **head+tail** excerpt (so a runner's tail summary survives
  truncation), a `truncated` flag, and an explicit `expect_found` so the receipt
  asserts the match even when it falls in an elided region.
- **Asymmetric stamping (honest, like `code`)** — a command that COULDN'T be run
  (off-allowlist, path argv[0], executable absent or resolving inside cwd, timed
  out, unparseable) is `unverified` (an inability, not a contradiction); a command
  that RAN and contradicted its expectation is `refuted` (a positive contradiction).
  `render_verdict.py`'s couldn't-verify bucket is now **kind-aware** — a refuted
  command reports its observed exit, not the code/quote "not found" wording.
- **Schema (additive, stays `advisory-board/verdict@2`)** — `command` evidence may
  carry optional `expect_exit` (int) and `expect` (verbatim substring); both are
  validated by `board_verdict.py` when present. Bare `{kind, command}` citations
  and older verdicts are unaffected.

### Honest limits
- A subprocess is **not a kernel sandbox** (acknowledged the same way the egress
  scanner is in design §8). The program allowlist + the containments above stop
  *planted-code* and *secret-env* paths, but a program you allowlist can still
  READ files its uid can read and **persist them into `verdict.json`'s
  `observed.output`** — so do NOT allowlist programs that read secrets (`cat`,
  `env`, `printenv`). Allowlist only programs you trust to be read-only over public
  material.

Hardened by **two security-focused adversarial-review rounds**: the first found 3 RCE
paths (relative argv[0] running a planted script, a dirty-PATH bare-name hijack, a
too-broad regex choosing argv[0]) plus exfil/timeout/renderer issues — all fixed by the
program-pinning + curated-PATH + isolated-cwd design above; the second confirmed the RCE
rewrite held (no shipping blocker) and caught two fail-safe fix-introduced issues (a bare
command that exits non-zero with no expectation pinned was mislabeled `refuted` → now
`unverified`, so an env-shaped failure isn't defamed as a fabricated receipt; and HOME is
now a SEPARATE throwaway, never the `--rerun-cwd` tree).

This completes the v1.x line of `design/run-board-v1x.md` (M1, M2, M3, M4 all done).
**Suite: 430 tests** (up from 386: +44 M3 tests).

## [v1.3.0] - 2026-06-25 — M2: neutral synthesizer seat

`run --synthesize` now spawns a single **no-lens synthesizer seat** that drafts
`verdict.json` from the final-round reviews. The conductor still does NOT generate the
verdict in code (§11); the synthesizer is a **reasoning seat**, briefed only on the round
artifacts + the conductor-extracted `VERDICT:` tokens — its output is **merged into an
authoritative skeleton** (schema/title/date/rounds/board are conductor-owned) and
**schema-validated against `advisory-board/verdict@2` before any write**. The human still
gates ship/abstain (`board_verdict.py --gate`).

### Added
- **Neutral synthesizer seat (M2)** — new pure module `scripts/_conductor/synthesizer.py`
  with `SYNTHESIZER_TEMPLATE` (versioned `advisory-board/synthesizer@1`, sha256 recorded
  in the recipe + the synth raw record), `build_skeleton` (per-seat `round_verdicts`
  pulled from `parse_verdict` over each round artifact — never the prose), `extract_json_object`
  (handles ```` ```json ```` fences, bare ``` fences, prose-prefixed replies, and
  bare brace-balanced objects; the LAST match wins; nested `}` inside JSON strings are
  brace-balanced safely), `merge_synthesizer_content` (drops `PROTECTED_SKELETON_KEYS` =
  `{schema, title, date, rounds, board}` so a model reply cannot rewrite the structural
  shell; recomputes `unanimous` from the final-round tokens vs. the merged verdict so a
  model-asserted flag cannot contradict the observed board), and `run_synthesizer` (one
  retry on Timeout|InvalidOutput per §13; persists a Black-Box Recorder `.raw` alongside
  the seat reply; refuses synthesis if any usable seat lacks a `VERDICT` token, with
  `failure_class="missing-verdict-token"` — the conductor must not invent a token to
  satisfy the schema).
- **CLI surface** — new flags `--synthesize` and `--synthesizer-seat SEAT` on both `init`
  and `run`. `--synthesizer-seat` must name a board seat (the synthesizer egresses to that
  seat's already-disclosed provider — a fresh provider would need its own disclosure);
  default order is `claude` → first usable seat. Both flags persist in the recipe so
  `--from-recipe` reproduces a synthesized run.
- **Provenance** — when `--synthesize` is on, the run dir adds
  `prompts/synthesizer.prompt` (the exact bytes the synthesizer received),
  `synthesizer/<seat>.md` (the verbatim reply), `synthesizer/<seat>.raw` (the
  Black-Box Recorder: argv, prompt + packet sha256, model-answered, parse/schema
  errors, accepted yes/no), `logs/synthesizer-<seat>.stderr`, and a new
  **`## Synthesizer`** section in `run-metadata.md`. A run that failed validation
  drops the merged-but-rejected JSON to `verdict-rejected.json` so the human can
  hand-fix from there. The run-card and artifact tree show the synthesizer when on.
- **Recipe schema** — new fields `synthesize` (bool), `synthesizer_seat` (string|null),
  `synthesizer_template` (`advisory-board/synthesizer@1` when on), and
  `synthesizer_template_sha256` (drift-detection across the egressed bytes).

### Honest limits
- The synthesizer is opt-in by design (decision D3) — synthesis is a reasoning task and
  the human still gates ship/abstain at the `validate --gate` step. The conductor calls
  no gate automatically on a synthesized verdict.
- Validation reuses `board_verdict.validate` (the same gate the user runs); on failure
  the conductor writes `verdict-rejected.json` + a loud warning, **never** a `verdict.json`
  that didn't validate, and exits 0 (the rounds succeeded — synthesis is a value-add).

## [v1.2.0] - 2026-06-25 — M4: smarter cross-reading digest

Round 2's `summaries` packet is no longer each round-1 review head-truncated to a char
budget (which silently dropped every section past the first). It is now a **structured
digest**: a verdict/citation **agreement header** over the board, then **every seat's take
on each topic side by side** — a sharper signal for round 2 (and the `auto` stop-rule) to
debate against.

### Added
- **Structured cross-reading digest (M4)** — a new pure module `scripts/_conductor/digest.py`
  replaces the head-excerpt `summaries` packet. It is §11-safe (principle #1: the conductor
  plumbs, the models reason) — it does NOT cluster claims semantically. It regroups each review
  **by the review's own section headers** (matching section *labels*, not claim content, to a
  fixed canonical taxonomy: Verdict / Objections / Sequence / Invariants / Risks / Evidence /
  Challenges) and surfaces agreement/conflict **only through M1's machine signals**: the parsed
  `VERDICT:` tokens (`unanimous` vs `split — 2×caution, 1×block`) and citations raised by ≥2 seats.
  Handles markdown headings (`## 1. Verdict`), numbered-bold headers (`**1. Verdict**`), lettered
  and roman sub-points (`### A. …`, `### II. …` stay inside their parent section), and code fences
  (a `#` line inside a ``` block is not a header); reviews with no parseable headers degrade
  gracefully to a head excerpt. `full` and `none` are unchanged. Golden-file test over the committed
  example's three real reviews + an end-to-end `--cross-reading summaries` run. Hardened by an
  adversarial review (16 findings — two parser content-loss bugs, code-fence awareness, the
  `parse_verdict` decoration handling, and a round-N debate-section bucket — all fixed). 343 tests.

### Changed
- **`parse_verdict` precision (M1 primitive, shared with M4)** — the verdict token must now be the
  FIRST word of the value (the bare-token contract `VERDICT: <token>`), so a prose label like
  `Verdict: REJECT / DO NOT SHIP` is no longer misread as `ship`. Compliant M1 reviews (a clean
  trailing `VERDICT:` line) are unaffected.
- **Retired the old head-excerpt `_digest`** (and `ROUND2_SUMMARY_BUDGET`) — superseded by the
  structured digest; `summaries` now routes through `build_structured_digest`.

## [v1.1.0] - 2026-06-25 — M1: Round 3 / `auto` stop-rule

The board no longer always runs a fixed two rounds. `--rounds auto` keeps debating
**while the board is still moving** and stops the moment it goes quiet; `--rounds 3`
now runs a real third round (the old clamp-to-2 note is gone).

### Added
- **Round 3 / `auto` stop-rule (M1)** — each seat now ends its review with a machine-readable
  `VERDICT: ship|caution|block` line, and a new pure module `scripts/_conductor/convergence.py`
  measures **movement** between consecutive rounds as a function over *only* the parsed token and
  the seat's concrete citation set (inline-code spans + file-shaped paths) — never the prose
  (principle #1 / §11: the model reasons, the conductor diffs tokens). A seat *moved* if its
  verdict token shifted or it brought a new citation; `--rounds auto` loops rounds 2…N while
  board-wide movement stays at/above the threshold and stops at `converged` (or the `--max-rounds`
  ceiling, default 3). The per-transition movement and the stop reason are recorded in a new
  **`## Convergence`** section of `run-metadata.md`, and each seat's parsed verdict token is a new
  `verdict` column in `run-metadata.tsv`. New flag `--max-rounds N` (persisted in the recipe, so an
  `auto` run reproduces its ceiling). The suite is **325 tests** (up from 287), including the
  adversarial rephrase property (same token + same citations ⇒ *no movement*, exercised end-to-end),
  the citation-delta movement arm, and the mid-debate-collapse guard (a board that drops below two
  voices in round 2+ is never handed off for synthesis). Hardened by two rounds of adversarial review.

### Added (workflow tooling — shipped with this release)
- **Plan view** — `scripts/render_plan.py` renders a self-contained HTML view of a planning
  document deterministically **from** its markdown (`design/<plan>.md` is the source of truth),
  the same render-from-source discipline as `verdict.json → final-consensus.html`. It parses a
  small markdown dialect — milestones / phases / `[ ]/[wip]/[x]/[f]` checklists, per-phase testing
  strategy and a named validation gate, decisions, risks, and an inlined SVG diagram — and computes
  every progress ring, status rail, and badge from the checklist states (they can't lie about the
  markdown). Claude brand styling (Poppins + Lora embedded as base64, the clay palette, WCAG-AA
  text) via `references/plan-template.html` + `references/plan-fonts.css` (regenerated by
  `scripts/_embed_fonts.py`). Malformed structure fails loud rather than dropping content; markdown
  links and inlined SVG are sanitized. 39 tests, including a drift guard that fails if a committed
  plan HTML falls out of sync with its markdown.
- `design/run-board-v1x.md` (+ rendered `design/run-board-v1x.html`) — the v1.x conductor feature
  plan, authored in the new dialect as the first real plan view (a reviewable starting draft).

### Changed
- **Prompt templates bumped to `round1@2` / `round2@2`** — the `VERDICT:` line is appended to both
  round templates and the round-2 template is generalized to any round N (it keeps the same structure
  and markers — `This is round 2`, `BOARD ROUND-1 REVIEWS` — for round 2, with the VERDICT line
  appended and a minor intro rewording). This changes the egressed bytes, so `prompt_template_sha` and
  the template versions bump (the recorded sha is the tamper-evident record of the change). The
  committed `examples/payments-idempotency-review/` is left untouched — it faithfully records a
  historical `round2@1` run.
- **Shared template engine** — the block / `{{TOKEN}}` machinery that `render_handoff.py`,
  `render_verdict.py`, and `render_plan.py` each carried (separately, and re-copied by
  `render_plan`) is extracted into `scripts/_render_engine.py`, parameterized by each caller's
  `BLOCK_KEYS`/`RAW_TOKENS`. `render_plan`'s SENTINEL stash (which holds verbatim author content —
  an inlined SVG, a quoted `{{…}}` snippet — out of the comment-strip and leftover-placeholder
  guards) now lives in the shared engine as an opt-in. Pure refactor: every renderer's output is
  byte-identical to before (verified against the committed example and plan view). +20 engine tests.

## [v1.0.0] - 2026-06-25 — v1: production-ready

The conductor's v1 scope (milestones M1–M6) is complete and has been exercised end-to-end
against real models. Declaring the line **stable**. No code change from `v0.6.0` — this is the
deliberate production-ready call the pre-1.0 scheme reserved.

### What v1 is
- **Engine** — a seat-adapter registry (claude / codex / gemini, plus antigravity and a local
  ollama seat), an executable preflight (GO/NO-GO), and round-1 + round-2 cross-reading fan-out
  with the §13 failure protocol (timeout / retry / classification, honest `model_answered`).
- **Safety** — a hash-bound egress/quarantine gate with tiered consent and a pre-spawn hard stop,
  capability-removal isolation in gate mode, and the evidence gate.
- **Verdict** — the canonical `advisory-board/verdict@2` with typed, resolved evidence
  (`verify_evidence.py`), Markdown/HTML rendered *from* the verdict (`render_verdict.py`), and the
  observed-agreement `abstain` gate (`board_verdict.py`).
- **Proven** — the first real, token-spending board run is the committed
  `examples/payments-idempotency-review/` (self-verifying).

### The v1 contract (stable)
- The `advisory-board/verdict@2` schema, the `run-recipe@1` format, the CLI subcommand surface,
  and `board_verdict.py` exit codes (`0` pass / `1` block / `2` schema / `3` abstain).
- Future work (Round 3 / `auto`, a spawned neutral synthesizer, `command`-evidence execution) is
  additive v1.x — see `design/run-board-conductor.md` §15.

## [v0.6.0] - 2026-06-25 — M6: docs/drift + the real proof-of-life run

The first token-spending board run: the conductor drove three subscription CLIs through
the full pipeline (preflight → egress gate → round-1/2 fan-out → synthesis → verify →
consensus → validate), end to end, against real models.

### Added
- **`examples/payments-idempotency-review/` regenerated via the conductor** as the real
  proof-of-life run (`claude-opus-4-8` · `gpt-5.5` · `gemini-3.5-flash`, 2 rounds, `full`
  cross-reading). The example is now an `advisory-board/verdict@2` with resolved evidence
  (8 `source` quotes verified against the captured packet), the rendered `final-consensus.md`/
  `.html`, and the run's provenance/consent summary (`run-recipe.yaml`, `run-metadata.{md,tsv}`,
  `egress-manifest.md`, `sensitivity.json`). All three seats independently converged on a
  unanimous `block`.

### Fixed
- **`parse_model_answered` no longer mines the echoed cross-reading packet.** A CLI like codex
  echoes its prompt to stderr; in a `--cross-reading full` round 2 that packet can carry a
  `"model": "…"` line (e.g. a quoted CLI example), which was being reported as the answering
  model — a false provenance value that violated the "never assume, unknown means unknown"
  rule. The parser now bounds its scan to the banner region before the `MATERIAL UNDER REVIEW`
  delimiter. Surfaced by the proof-of-life run itself.

### Changed
- **`SKILL.md`**: the conductor (`scripts/run_board.py`) is now documented as the canonical run
  driver; the `CLI Execution Notes` point at the seat-adapter **registry** as the canonical,
  self-healing source for execution mechanics, with the manual per-CLI templates reframed as
  the portable, script-free fallback (design §12 drift-resolution).

## [v0.5.0] - 2026-06-25 — M5: canonical verdict + resolved evidence

`verdict.json` becomes the source of truth for the board's decision; the Markdown and HTML
render from it. Synthesis stays a reasoning task (design §11) — the conductor produces clean
per-round packets and the agent fills `verdict.json`; it does not generate the verdict in code.

### Added
- **Schema `advisory-board/verdict@2`** — typed `evidence[]` (kinds `code`/`source`/`command`/`judgment`)
  with an optional `status` (`verified`/`unverified`/`refuted`) on blockers, dissent, and concerns.
  `board_verdict.py` validates both `@1` and `@2`.
- **`scripts/verify_evidence.py`** — resolves `code` `path:line`/`symbol` against `--source` and
  `source` quotes against the captured packet (`--packet`/`--run`), never a live URL fetch
  (respects quarantine); stamps each citation. `command` is deferred (`unverified`); `judgment`
  is left unstamped. Path-safe (rejects absolute/`..` paths and basename collisions).
- **`scripts/render_verdict.py`** — renders `final-consensus.md` from the canonical `verdict.json`
  (evidence trail + couldn't-verify bucket); `--handoff-data`/`--html` derive the HTML via the
  existing `render_handoff.py`. Per-round prose is pulled from `round-N/<seat>.md`, never invented.
- **`board_verdict.py --gate` abstain** — a neutral exit `3` ("human required"), driven by observed
  cross-seat agreement (`round_verdicts`), never the gameable `confidence`. Fires when the board is
  torn across the threshold with no majority, when the declared verdict clears the gate while a
  majority of seats trip it (the injected-"ship" case), or when any citation is refuted.
- **`run_board.py` subcommands `verify` and `consensus`**; `run` now prints the
  synthesis → verify → consensus → validate chain at the end of a run.

### Changed
- `references/verdict-schema.md`, `scripts/README.md`, `tests/README.md`, and the `SKILL.md`
  helper list updated for the verdict chain and the `@2` schema.

### Notes
- The shipped `examples/payments-idempotency-review/verdict.json` stays `@1` (regenerated via the
  conductor in M6).
- Verification: 227 standard-library tests; live preflight 3/3 GO; CLI byte-identical. Shipped in
  [#11](https://github.com/timharris707/skills/pull/11), reviewed by a 5-agent adversarial pass.

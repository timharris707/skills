---
name: advisory-board
description: Convene a multi-model advisory board where subscription-backed Claude, Codex, Gemini, and Grok CLIs review the same material in one of three modes — Formal Board Review (independent first round, rebuttal, structured verdict), Roundtable (collaborative judgment and synthesis), or Competitive (rival proposals, critique, and voting) — opening with a mandatory guided intake that settles mode, seats, lenses, and effort with the user before anything runs. Use when the user asks for an advisory board, round table, panel, or idea tournament; a multi-model or multi-provider review; a skilled debate among models; an adversarial review or red-team of a plan, design, architecture, skill, document, decision, or strategy; an Anthropic/OpenAI/Google/xAI cross-check; or a consensus handoff from several frontier models.
---

# Advisory Board

Bring an idea, problem, plan, or architecture to a board of frontier models sitting in different roles. The board runs in one of three **modes** — the interaction topology chosen with the user at intake (`references/modes.md`): **Formal Board Review** (the default: independent first round, rebuttal, structured verdict — the protocol this document defines), **Roundtable** (collaborative, shared transcript, optional moderator), or **Competitive** (pitch → critique → blind vote). Whatever the mode, you leave with the strongest conclusion the board can reach together and a clean takeaway — not disconnected opinions.

## Must Not

Hard rules, collected here so they are never missed (each is elaborated in context below). Violating one invalidates the run.

- **Never write files or make edits** unless the user explicitly asked for edits — the board is read-only by default.
- **Never write artifacts into a tracked git tree** without naming the location first; default to the persistent runs root (`~/.advisory-board/runs/<slug>-<date>/`), or a throwaway `/tmp/advisory-board-*` folder with `--ephemeral`.
- **Never substitute a model silently** — if a requested model is unavailable, use the nearest same-provider frontier model and say so.
- **Never skip the data-handling disclosure** for non-public material — not even when the user says "use defaults." Disclose what leaves the machine and to whom, and get a go-ahead, before any external seat runs (`references/data-handling.md`).
- **Never present a degraded or dropped seat as a full board** — label it on the seat card and in `verdict.json` (`dropped: true`) on a Formal Board Review run; Roundtable and Competitive, which emit no `verdict.json`, record it in `run-metadata.md` and name it in `synthesis.md`/`results.md` (`references/modes.md`). A board needs at least two seats that actually ran.
- **Never print or store secrets** — keys, tokens, cookies, or private environment values — in prompts, packets, artifacts, logs, or metadata.
- **Never launch a run the user hasn't confirmed.** The guided intake (`references/intake-interview.md`) is mandatory: mode, seats, lenses, effort, rounds, and output are the user's choices, made on the record. "Use defaults" collapses the intake to a single confirm-summary card — never to zero questions.

## Core Defaults

- Use subscription CLIs by default, not provider API keys.
- Run read-only unless the user explicitly asks for edits.
- Rounds: 2. Cross-reading: summaries. Final artifact: full handoff (Markdown plus a self-contained HTML view).
- Write run artifacts to the **persistent runs root** by default — `~/.advisory-board/runs/<slug>-<date>/` (slug from the run title, date from the run date; a same-day rerun gets a `-2` suffix, never an overwrite) — so runs stop evaporating and `run_board.py history` can list them. Override the root with `$ADVISORY_BOARD_RUNS_ROOT` or `--runs-root DIR`; name an exact dir with `--out DIR`; or opt back into a throwaway timestamped `/tmp/advisory-board-*` folder with `--ephemeral`. Every real run announces where its artifacts land on its first output line (a `--from-recipe` re-run reuses — and rewrites — the recipe's recorded dir unless you point it somewhere fresh). Persistence changes only the disk location — artifacts inherit the run's sensitivity handling (`references/data-handling.md`).
- Writing artifacts into the reviewed project is itself a write, even on a read-only review: do that only when the user asks or agrees, prefer a dedicated `advisory-board/<timestamp>/` (or `docs/advisory-board/<timestamp>/`) folder, and never write into a tracked git tree without naming the location first.
- One flag sets the whole cost/depth posture: **`--tier quick|standard|deep`**. `quick` — 1 round, `summaries` cross-reading, reduced per-seat reasoning (claude `high`, codex/grok `medium`; model selectors never change, and seats without an effort knob are untouched). `standard` — today's defaults, a deliberate no-op. `deep` — 3 rounds, `full` cross-reading at the registry's max-tier reasoning (codex stays at `xhigh`; grok stays `high`). The tier is a **base**: explicit flags (`--rounds`, `--cross-reading`) always override it, and `run-recipe.yaml` records the resolved selectors and effort values. Provider-maintained aliases/defaults deliberately re-resolve on a later run; `--model seat=id` is the exact-pin escape hatch. Four frontier models at high reasoning across several rounds can take minutes and meaningful tokens — flag a large run before launching it; `run_board.py run … --dry-run` prints a best-effort estimate. After the run, `run-metadata.md` records what each seat CLI actually reported, where known.

## Modes

The three topologies, their mechanics, hand-runnable protocols for the two the conductor doesn't drive yet, and the intent→mode recommendation table live in `references/modes.md`. In brief: **Formal Board Review** is this document's Round Protocol and everything the conductor, verdict chain, and gate support — the default. **Roundtable** and **Competitive** run by hand via the portable fallback, produce their own artifact sets, and never feed `verdict.json` or a gate. The mode is settled at intake, with the user.

## Guided Intake (mandatory)

Every run opens with the wizard in `references/intake-interview.md` — presented as selection cards like the `grilling` skill's rounds, recommendation first. The sequence, in order:

1. **Doctor first** — probe every registered seat (`run_board.py doctor`); report per-seat GO/NO-GO in plain terms; for each broken seat offer fix-now (installs/updates only with an explicit yes; auth is always the user's hands), continue-without, or abort. Never offer a seat you haven't confirmed.
2. **Goal → mode** — hear the goal in the user's words, recommend a mode (and lens preset) from `references/modes.md` §Choosing a mode, and let the user pick from all three.
3. **Seats** — any 2–10 of the GO providers ("latest frontier of each" is the shortcut); show the seat→provider→lens table before launch; warn on cost for big or deep boards.
4. **Reasoning depth** — Highest available (default) / Standard / Quick via `--tier`; per-seat overrides on request.
5. **Rounds and output** — with defaults marked.
6. **Confirm-summary** — the resolved plan as one card; nothing launches without this yes.

"Use defaults" jumps straight to step 6 with everything resolved to defaults — it never skips the confirmation, and it never waives data-handling consent: if the material isn't clearly public, still disclose which providers will receive it and get an explicit go-ahead before launching any external seat (`references/data-handling.md`).

## Model Lineup

Target the strongest reasoning model each provider offers **at run time**. Defaults use provider-maintained selectors so new frontier releases do not require a skill edit; explicit `--model seat=id` overrides pin exact IDs.

- Claude seat: Anthropic's maintained `fable` alias (Fable 5 — the Mythos-class tier above Opus, the strongest generally available Anthropic model) at `--effort max`. Where `fable` doesn't resolve (older CLI or account), preflight proposes the `opus` fallback — never applies it silently.
- Codex seat: the Codex CLI's recommended model (no exact model pin) with `model_reasoning_effort="xhigh"`.
- Gemini seat: Google's maintained `pro` alias (latest highest-reasoning Pro model) with the CLI's highest available thinking level.
- Grok seat: `grok-4.5` through the official `grok` CLI at `--effort high`, the highest Grok 4.5 level. xAI retired the `grok-build` alias; `grok models` lists `grok-4.5` alone (verified on CLI 0.2.117, 2026-08-05).

The selector (`fable`, `pro`, `grok-4.5`, or Codex `auto`) and the model that actually answered are separate provenance fields. If a CLI cannot report the resolved ID, record `unknown` rather than pretending. Use an exact `--model` override for an eval or replay that must not float.

Preflight — run `references/preflight.md` before launching: for each seat, check the CLI is present, auth is active (subscription-backed where possible), the requested model resolves, and a one-token smoke ping returns. Proceed only with at least two seats GO; label any degraded or dropped seat in the handoff. In summary:

- **First run? `run_board.py doctor`** — a guided setup check that sweeps **every** registered provider (installed → version currency → auth → default model resolves), prints per-provider fix-it steps (install command, auth command, model fallback), and summarizes which boards are viable today (≥ 2 seats GO) plus a suggested first command. Probes and smoke-pings only — it never reads or sends your material.
- **Toolchain currency first** — `run_board.py toolchain` checks each CLI against its latest release and (`--update`, consent-gated) upgrades stale ones; `--install` installs absent ones (account/auth still required). Fresh CLIs keep provider-maintained frontier selectors current. Explicit `--model` pins remain exact; if one stops resolving, preflight proposes a fallback rather than silently rewriting it.
- **Graceful degradation** — if fewer than two seats are usable (a downloaded skill on a machine with only one provider's CLI/account), preflight doesn't dead-end: it distinguishes *not installed* (prints the install command) from *installed-but-unauthed*, and points to the fallbacks — a same-provider multi-lens board or a local/human seat (`references/board-composition.md`). You never need all four providers to get value.
- Confirm Claude subscription auth is active.
- Confirm Codex is on ChatGPT/subscription auth, not API-key-only, when possible.
- Confirm Gemini auth and model/config support.
- Confirm Grok login (OAuth/device auth or `XAI_API_KEY`) and that its frontier default resolves.
- Never print secrets, tokens, cookies, or private environment values.

## Seats

Give each seat its own angle so the board covers more ground than any single reviewer, and match the lenses to the subject. Pick a ready-made lens set from `references/lens-presets.md` — `software-architecture` (default), `product-strategy`, `research-paper`, `legal-contract`, `business-decision`, `writing-editing`, `red-team` (every seat hostile — the stress-test preset), `stakeholder-panel` (convene "the room this decision would face") — or compose your own. The same lens on two different providers is a valid cross-model pairing; only same-provider-same-lens wastes a seat. For software and technical work, the default split:

- Claude: architecture, systems, and adversarial design review.
- Codex: repo-grounded implementation, migration, testing, and execution.
- Gemini: product, operations, rollout, latency, evaluation, and user-workflow risk.
- Grok: contrarian synthesis, hidden assumptions, alternatives, and decision-changing evidence.

For non-software subjects (strategy, research, writing, business, policy), assign comparable lenses — e.g. one seat on first-principles soundness, one on execution and feasibility, one on second-order consequences and stakeholder or user risk.

Every seat still answers the full brief; the lens reduces blind spots, it doesn't narrow responsibility.

The board defaults to four seats but isn't fixed at four — for sizing (2–10), the same provider in multiple seats (`--board claude,claude,codex` auto-numbers, or `--board econ=claude,risk=claude` aliases — each seat takes its own lens via a repeated `--lens id=…`), a human or local-model seat, an **Antigravity** seat, and minimal "works with what you have" lineups, see `references/board-composition.md`.

## Data Handling

A board sends the same source material to every seat's provider. Before the first call, if the material isn't already public, tell the user what will leave the machine and to whom, and get a go-ahead. For sensitive material, redact the shared source packet; for must-not-leave material, run a local-only board or don't run it. Full guidance: `references/data-handling.md`.

### Repo-grounding & verification

By default a board reviews the **text you hand it** and is blind to the codebase that text is about — so findings come back "conditional on the cited factual base," none confirmed by a seat that read the code. The optional `--repo PATH` closes that gap: it augments `--source` (the source file still frames the question; the repo is the evidence base) by handing every seat a **read-only snapshot** of the repository so they verify claims against real code and cite real `path:line` instead of critiquing prose. The snapshot is `.gitignore`-respecting, `.git`-excluded, secret-denylisted, and symlink-confined; consent binds to its **scope hash** alongside the source-packet hash, and `repo-scope-manifest.json` records exactly what was in scope at approval. Repo-grounding details and the egress story: `references/data-handling.md`.

Grounding then makes the verdict chain trustworthy on **code**, not just prose: once seats cite real lines, `verify --source <repo> --run <out>` resolves those citations against the tree and stamps each `verified`/`unverified`/`refuted` — a fabricated citation stamps `refuted` and `validate --gate` abstains. No change to `verify_evidence.py`/`board_verdict.py`; the feature is entirely upstream (D7).

In **gate mode** (`--repo` on a gate-bearing run), the safety policy is **read XOR network**: every seat must be network-isolatable, because a grounded seat that is also networked can read a secret and exfiltrate it (or be driven to by an injected repo file). Seats that can't be de-networked (today **gemini**, **antigravity**) make a gate+`--repo` run **refuse** — the offending seat is named as a labeled NO-GO, never silently dropped (D4). **Advisory + `--repo`** is the home for casual self-review of your own repo (network on, you own the risk) with a loud disclosure; a gate-bearing run never silently falls back to advisory.

**Caveat — what "verified against the repo" does and doesn't mean (§9).** A `verified` stamp means the **receipt resolves** — the cited `path:line` exists and the quoted text is there — **not** that the inference drawn from it is sound. The gate catches fabrication, not grounded-but-wrong reasoning. Two limits follow and must be stated honestly: (1) a **poisoned repo** can make a wrong claim cite a real line, so `verified` on an attacker-controlled tree is not trust; and (2) because the snapshot is **cleaned up after the run**, later re-verification points `--source` at the **live repo**, so a citation that was real at approval can refute later if the tree drifted — `verified` is a statement about the snapshot at approval time, not a standing guarantee. This system also does **not** physically confine a seat's reads to the snapshot — codex's read-only sandbox can read files outside its working directory (R9) — so the snapshot bounds what is **consented to / hashed / verified against**, not what a seat can read; exfil is blocked by D4's network isolation, not by read-confinement.

## Round Protocol

This section defines **Formal Board Review** — the default mode and the only one the conductor drives end-to-end. Roundtable and Competitive replace it with their own phase structures (`references/modes.md`).

**Rubric-first scoring (`--rubric`, optional — v1.15).** Before round 1, the board can agree its own weighted criteria and then score every round against them, so the verdict is backed by a comparable number as well as prose. Two mechanically-checked passes run first:

1. **Proposal fan-out** — every seat is spawned in parallel and proposes 3–7 weighted criteria (`{title, description, weight}`) from the same source packet round 1 sees; the conductor mints the proposal ids (`p1`…`pN`) — a model never mints identity. Fewer than two usable proposals **refuses the run before any opinion round spends a token**.
2. **Chair merge** — one board seat, the **CHAIR** (`--chair-seat SEAT`, default: the first `claude`-provider seat, else the first seat with a usable proposal, else `board[0]`; resolved on the same **unique seat-id axis** as `--model`/`--revision-seat`, so it refuses an ambiguous provider name on a duplicate-provider board rather than silently collapsing it), merges every usable proposal into one weighted rubric with an explicit **partition** — each merged criterion names the proposal-id(s) it subsumes, each dropped proposal-id gets a reason. The conductor **mechanically** reconciles the partition (every proposal-id exactly once across subsumed ∪ dropped, no phantoms, no empty subsumptions) and the **weight-sum invariant** (integer percentages summing to exactly 100). A mechanical failure retries once, then refuses the run.

`rubric.json` is the pre-round artifact of record, written at chair-merge time (post-consent, pre-rounds — it survives a later scoring failure). A refusal (too few proposals, or a chair merge that can't be reconciled after retry) writes `rubric-rejected.json` instead and exits non-zero (`EXIT_PREFLIGHT_NOGO`) — the one place in the whole skill where a pass refuses the run outright rather than degrading, because it lands before any opinion round has produced value worth protecting.

Once the rubric is agreed, it is injected into **every** opinion round's prompt: each seat emits one `SCORE cN: <1-5>` line per criterion (parsed with the same line-hardening as `VERDICT:`; a bad or missing line degrades that cell to absent — "—", never imputed — it does **not** make the seat unusable) plus an optional `RUBRIC-NOTE:` objection to the rubric itself (recorded, never debated — scoring under the rubric *is* accepting it). `--rounds auto` convergence widens to include score movement (`moved = verdict_shift OR new_cites OR any criterion score changed`); the round-done detail names the still-moving criteria.

`--rubric` composes with `--repo` and `--revise`/`--output revised-draft` — the rubric pass sees the same composed context (repo-grounding clause, prior-verdict digest + diff) that round 1 does, never strictly less. On a `--revise --rubric` run whose prior run carried a valid rubric, the prior rubric is **carried forward mechanically** — no fresh proposal/chair pass, no re-agreement offered — so scores stay comparable across revisions. `--rubric` is orthogonal to `--tier`/`--lens` (it always runs when set, never silently skipped) and to `--output`/`--synthesize`; it's recorded in the recipe so `--from-recipe` replays it exactly. See `references/prompt-templates.md` for the injected block and token grammar, and `references/verdict-schema.md` for the `rubric`/`scorecard` verdict pointers.

**Round 1 — independent.**

- Give each seat the same source packet and its role lens, nothing else.
- No other seat's opinions.
- Require: verdict (with a confidence level — low/medium/high), strongest objections, revised sequence, invariants, risks, and concrete evidence.

**Round 2 — rebuttal (default).**

- Build a board packet from Round 1: a structured digest (`summaries`, the default) that puts every seat's take on each topic side by side under a verdict/citation agreement header — where the board agrees and where it splits — or the full prior responses when the token budget allows (`full`). `run_board.py` builds this deterministically from each review's own section structure plus the `VERDICT:` tokens; it never clusters claims by meaning (principle #1). Add `--digest-format json` to also write each round's digest as typed JSON (`board-packet-round-N.json` — the same parsed signals, machine-readable) next to the markdown.
- Ask each seat: what another seat caught that you missed, what changed your view (and whether the change is driven by evidence or mere deference — see `references/epistemics.md`), what you still dispute, what should become consensus, and what stays unresolved.

**Round 3 — convergence (optional).**

- Give each seat the Round 2 packet.
- Ask for the final position, hard dissent, and the smallest viable plan.

**Adaptive rounds (`auto`).**

- Stop early when the board has converged — a shared verdict, high confidence, and no material dissent after a round — rather than spending a round to rubber-stamp.
- Add a round when material dissent or low confidence remains and another exchange could plausibly resolve it, up to the `--max-rounds` ceiling (default 3).
- `run_board.py --rounds auto` makes this concrete: each seat ends its review with a `VERDICT: ship|caution|block` line, and the conductor measures **movement** between rounds as a pure function over that token plus the seat's concrete citations — never the prose (the model reasons; the conductor diffs tokens). It keeps going while the board is still moving and stops the moment it goes quiet; the per-round movement and the stop reason are recorded in `run-metadata.md` (`## Convergence`).
- **Independence / echo score (v1.14):** convergence can be *earned* (the seats independently reached the same answer) or *social* (they read each other and drifted into agreement). Round 2+ seats add a self-reported `BASIS: independent|evidence|deference` line (the machine form of the independence check — see `references/epistemics.md`), and the conductor scores echo risk over the final round's parsed signals — verdict flips toward the majority, citation-set overlap, and the deference count — as a coarse **low / moderate / high** band with a one-line explanation naming the sub-signals. It appears in `run-metadata.md` (inside `## Convergence`) and as an optional pill in the HTML handoff. It **flags** possible echo; it does not prove independence (high overlap can be an honest read of a small source, and a same-provider board's overlap is expected). It degrades to *not computed* on a single-round run or when fewer than two seats were usable in both final rounds.

**Final synthesis.**

- After the last round, write the handoff: consensus, dissent (and why it matters), revised plan, risks, invariants, evidence, and next actions.
- **Write the handoff for a human who was not in the room.** Lead with the bottom line — `summary` in `verdict.json`: 3–6 plain sentences saying what was reviewed, what the board decided, why, and what happens next. Every prose field (headline, notes, finding titles and bodies) must read as plain English on the first pass: short sentences, no coined compound labels, no unexplained jargon; a finding's title is a complete sentence naming what can go wrong, and mechanism detail (function names, flags, line-level behavior) lives in the evidence citations, not the prose. This contract binds a hand-authored verdict (the degraded-synthesizer path) exactly as it binds the synthesizer seat.
- Prefer a neutral synthesizer — a seat that didn't debate, or a blind merge — so the chair doesn't grade its own work (`references/epistemics.md`). If the board is unanimous, include a minority report: the strongest case against the verdict.
- Label model and round provenance (the model that actually answered, not just the one requested), and split the findings into three explicit buckets: **evidence-backed** (tied to a file, fact, run, or citation), **judgment calls** (reasoned but unproven here), and **couldn't-verify** (claims the board leaned on but didn't check, plus the shared blind spots no seat could see). For each load-bearing conclusion, note what would change it. The couldn't-verify bucket is the main guard against a confident, unanimous, *wrong* call — three models can converge on the same missing fact (`references/epistemics.md`).
- Emit `verdict.json` alongside the prose (`references/verdict-schema.md`) so the result can drive a gate or other tooling.

## Artifact Standard

Write:

- `round-1/<seat>.md` (and `round-2/`, `round-3/` as rounds run)
- `board-packet-round-2.md` (and `board-packet-round-3.md` when needed)
- `final-consensus.md` — the handoff in Markdown
- `final-consensus.html` — a self-contained, human-readable view of the handoff. Render it deterministically with `scripts/render_handoff.py` from a `handoff-data.json` (recommended — guarantees no leftover placeholders or template drift), or fill `references/handoff-template.html` by hand. Choose the **shape** with `scripts/render_verdict.py --html … --shape full-handoff` (default — the complete record), `--shape quick-verdict` (a slim skim brief to lead with), or `--shape implementation-sequence` (the sequence-first view for whoever executes: every next action in order with owners where named, backed by the blockers and their evidence — md + HTML); see `references/output-formats.md`. Trim by severity with **`--filter blockers|blockers+dissent|all`** (v1.14) on `render_verdict.py`/`format_output.py`: `all` is the full record (default, unchanged); `blockers` shows blockers only; `blockers+dissent` adds dissent. A dropped section is stated with counts (loud elision — never silent), the verdict banner/confidence are never filtered, and `--filter` is refused with `format_output.py --format json` (the JSON stays a faithful, unfiltered echo).
- `verdict.json` — the machine-readable verdict (`references/verdict-schema.md`); gate or reformat it with `scripts/`
- `changes.json` + `revised-draft.md`/`.<orig-ext>` — **only with `run --output revised-draft`** (v1.13): a board-derived, **board-endorsed** **revised copy** of the source, each edit mapped by the model to the board finding it resolves, mechanically validated (coverage reconciliation + index/title cross-assert), then voted on by the board — the per-edit **endorsement pass** (v1.13 P4, D13) runs by default: after the revision succeeds, each non-revision seat is fanned out concurrently to record `ENDORSE`/`OBJECT`/`ABSTAIN` on every edit and unresolved conflict in `changes.json.endorsements` (objections are recorded, never resolved — a human reads them). `--no-endorse` opts out (the token-cost axis); such a run is *findings-mapped*, not board-endorsed, and `endorsements` stays empty. The draft is **byte-clean** (the revised source bytes and nothing else — no header, so saved code stays valid) and **LF-normalized UTF-8** (the whole revision pipeline is LF-normalized end to end, so a CR/CRLF source is refused up front rather than silently re-terminated); `changes.json` (`advisory-board/changes@1`, `references/changes-schema.md`) is the edit→finding mapping (plus endorsements) of record and `verdict.json` gains a `{artifact, sha256}` pointer to it. The source file is **never written** — applying the revision is your act. Conflicting findings are surfaced as `unresolved` entries, never silently reconciled. A **code** source also gets a git-apply-able `revised-draft.patch` (`git apply -p1`); a **prose** source instead gets a word-level `<ins>`/`<del>` **redline** section in the full-handoff HTML (v1.13 P3, D12) — the two are siblings, at most one renders. Both are pure *views*, derived from the same sha-pinned strings `changes.json` already certifies (no new trust surface): the renderer walks verdict → `changes.json` → `{source-material.txt, revised-draft.*}`, re-verifying every hop's sha256 before diffing a byte, and drops the section with one stderr warning on any mismatch rather than showing something unverified.
- **Grounded citation snippets (v1.13 P3, #12).** When a `verify --repo`/`--source`-grounded run resolves a `code` citation, it captures the cited lines onto the evidence entry (`snippet: {from, to, text}`) so `final-consensus.md` and the sequence view embed the receipt as a fenced `path:from-to` block — the handoff is self-contained even though a grounded run's repo snapshot is cleaned up afterward. A citation that only resolved (no snippet) still renders as before.
- `rubric.json` + `scorecard.json` — **only with `--rubric`** (v1.15): `rubric.json` (schema `advisory-board/rubric@1`) is the pre-round artifact of record — the merged, weighted criteria plus the chair's partition and full proposal provenance, written before the opinion rounds; `scorecard.json` (schema `advisory-board/scorecard@1`) is written **after** the rounds — per-round `scores[]` rows (the trajectory is the convergence story), `rubric_notes[]`, and conductor-computed per-seat weighted totals + a coarse `weak`/`mixed`/`strong` band (a fixed third of the 1–5 scale, never a tuned formula). Both are conductor-computed and strictly validated (`scripts/board_rubric.py`, `scripts/board_scorecard.py`); a validation failure warns and writes nothing rather than corrupting the record — the rounds and verdict still stand. **Scores are informational only — the gate never reads them.** A severe token↔band contradiction (a `block` verdict over a `strong` band, or `ship` over `weak`) is recorded in `scorecard.json.contradictions[]` and surfaced loudly in the verdict summary, but never moves the verdict or the gate. `verdict.json` gains tool-authored `rubric`/`scorecard` `{artifact, sha256}` pointers (present only when `--synthesize` ran — the artifacts stand alone otherwise), following the `changes` pointer precedent exactly (strict when present, invisible when absent, model-forbidden). The consensus Markdown and full-handoff HTML render a `## Rubric scorecard` section (criteria, weights, per-seat totals/bands/history, coverage, recorded `RUBRIC-NOTE` objections, dropped-criteria provenance) that whole-drops to zero bytes on a non-rubric run. `run_board.py history` gains a `Rubric` column (`yes` on a synthesized rubric run, else `—`).
- `run-metadata.md` — provenance: commands, the model that actually answered per seat, auth mode (no secrets), per-seat status (ran / degraded / dropped), timings, and source paths. Use `references/run-metadata-template.md`. When a seat CLI reports its own token usage, the conductor also records per-seat tokens and a best-effort cost/time line ("if known" — most CLIs report nothing, and nothing is ever guessed).

When a seat is degraded or dropped, show it on its HTML seat card (status pill) and in `verdict.json` (`dropped: true`) — never let a smaller board look like a full one. Derive lighter shares (TL;DR, PR comment, Slack, print/PDF) per `references/output-formats.md`.

**Output contract for the HTML.** It is a *view* of `final-consensus.md`, not a second source of truth — the two must not disagree. The rendered file must contain no leftover `{{tokens}}` and no template scaffolding comments, and must stay self-contained (inline CSS only; no external fonts, CDNs, scripts, or remote `<link>`/`<script src>`) so it opens offline on a double-click. Follow the template's two-placeholder convention: replace each single `{{TOKEN}}` in place, and duplicate each `BEGIN`/`END` block once per item (delete the sample block if there are none).

Never store secrets. Redact keys, tokens, cookies, and private environment values.

## How A Run Executes

**The conductor — `scripts/run_board.py` — is the canonical way to drive a board.** It owns the load-bearing mechanics in code: a seat-adapter **registry** (the one place that knows each CLI's flags, isolation, and model-id self-heal), an executable **preflight** (GO/NO-GO), a hash-bound **egress/quarantine gate** before any byte leaves, the **round-1 + round-2 fan-out** with the failure protocol, the **verdict chain** (`verify` evidence → `consensus` md/html → `validate`/gate), and the **run history** (`history` — a table of past runs read from each run's `verdict.json` under the persistent runs root; a partial or legacy run lists as `incomplete`). Run `scripts/run_board.py run …` (see `scripts/README.md`); a real run is in the repo-root `examples/payments-idempotency-review/`. Useful run controls: `--timeout SECONDS` caps every seat and `--timeout SEAT=SECONDS` caps one (ids as in `--model`/`--lens`; a slow local seat shouldn't set the whole board's clock), repeatable `--effort SEAT=LEVEL` overrides seats' reasoning effort in each CLI's own vocabulary (`SEAT` is the exact seat id, as in `--model` — an ambiguous provider name on a duplicate-provider board is refused; wins over `--tier`'s base; recorded in the recipe; a non-default level on a seat whose CLI has no effort knob is refused loudly, while the adapter's own default passes so a `--from-recipe` replay stays valid), and `--digest-format json` also emits each round's structured digest as typed JSON. **Re-review a revised draft with `--revise <prior run dir>`** (v1.12): `--source` is the revised draft, and the round-1 prompts additionally carry a mechanical digest of the prior verdict plus the diff from the previously reviewed draft (recovered from the prior run dir, sha-verified; omitted loudly when unrecoverable) — every injected byte inside the consent packet hash. The new verdict records `previous_run` lineage, and the consensus render leads with the cleared / still-open / new delta and the verdict trajectory. **Ask a follow-up after the verdict with `ask "<question>" --run <dir> [--seat <id>]`** (v1.12): post-verdict cross-examination — the board answers a follow-up in one round, from a context packet built ONLY from that run's own artifacts (the reviewed material, a mechanical verdict digest, and each addressed seat's own prior review), bounded to the run and re-consented like any egress (public discloses; non-public needs `--yes`/approval; the sensitivity floor is the strictest of the recipe, the run's `sensitivity.json`, and a tighten-only `--sensitivity` flag — never looser, and a run missing its `sensitivity.json` never floats down to public); it writes `addendum-N.md` and refreshes the handoff. **Tune a completed verdict by hand with `board_verdict.py amend --run <dir> --author … --reason … <effect>`** (v1.12): append-only human tuning that never rewrites the board's own words — one effect per call (`--confidence`, `--caveat`, or `--severity-note [--on "<finding>"]`), recorded with provenance; renderers then show the effective value marked as amended, and a no-amendments verdict is unchanged. **Get a board-endorsed fixed copy with `run --output revised-draft`** (v1.13): after synthesis, a revision seat produces a revised copy of the source (each edit mapped by the model to the finding it resolves, mechanically validated — coverage reconciliation + index/title cross-assert) plus `changes.json` — the edit→finding mapping of record. Then the **endorsement pass** (v1.13 P4, D13) runs by default: once the revision succeeds, every non-revision seat is fanned out concurrently (≈ one extra round) to vote `ENDORSE`/`OBJECT`/`ABSTAIN` on each edit and unresolved conflict, recorded as `changes.json.endorsements` rows — objections are recorded, never resolved by another model loop (a human reads them, D6). `--no-endorse` opts out (the token-cost axis; that run is findings-mapped, not board-endorsed); a failed endorsement spawn records that seat as `ABSTAIN`/`dropped` and never fails the run or moves the exit code. It **requires** a verdict (`--synthesize`), takes `--source-type prose|code` to pick the redline format (the extension heuristic decides otherwise; a stdin or unknown-extension source must pass the flag) and `--revision-seat`; the revised draft is **byte-clean** with no header, the source file is **never written** (applying it is your act), conflicts surface as `unresolved` entries (never fatal), and a revision failure leaves the verdict/rounds intact (`changes-rejected.json` + exit 0, `--strict-exit` → 4). A code source additionally gets a `revised-draft.patch`; a prose source instead gets a redline section in the full-handoff HTML — see Artifact Standard above (v1.13 P3). Synthesis stays your reasoning task — the conductor stops at clean per-round packets and hands them to you (or one neutral seat) to fill `verdict.json`, then you call the chain. **Watch a long run live (v1.14):** a board run is 10–15 minutes and stdout block-buffers a backgrounded run, so on by default the conductor writes a `status.json` into the run dir — rewritten atomically on every seat/round/stage transition — and drives from it (a) flushed per-seat terminal lines (`round 1 · codex … running` → `round 1 · codex ✓ 186s`) that stream instead of going dark, and (b) a self-refreshing `status.html` tracker you can open in a browser (dark, compact, `<meta refresh>` every 2s while live; static once done). Both are a **live view, not an artifact of record** — the verdict chain and `run-metadata.md` stay authoritative — and the run dir is byte-identical to before apart from the two `status.*` files; `--no-live-status` drops even those. Writing the view is best-effort: a failure warns once and never touches the run, and a preflight NO-GO leaves no dir — an egress-refused run writes only the refusal manifest (`egress-manifest.md` + `sensitivity.json`), never `status.*` (the view defers its first write until the run commits to spawning).

The rest of this section and the **CLI Execution Notes** below are the **portable, script-free fallback** — the same protocol an agent runs by hand where the conductor isn't available. The principles hold either way:

- Run every seat as its own CLI subprocess — including the Claude seat as a separate `claude` process — so each reviews the source independently rather than reusing the orchestrator's context. That independence is what makes Round 1 worth anything.
- Keep the orchestrator and the chair neutral: assemble packets and synthesize, but don't also count yourself as a debating seat. If you must, say so in the handoff and use a minority report to check chair bias (`references/epistemics.md`).
- When the source is a repo or local files, decide once how seats reach it and record it in `run-metadata.md`: either every CLI reads the same shared path, or you build one source packet and hand identical bytes to each seat. Use one method for all seats so they review the same thing.
- Seats are agentic — they may web-search and read their working directory, which usually *helps* (live grounding). When you need a clean outside view or isolation, control the working directory and network and hand each seat one neutral source packet. (Running seats from a non-git folder also requires Codex's `--skip-git-repo-check`.)

For a concrete, copy-pasteable capture pattern — prompts written to files, stdout/stderr/exit-code/timeout capture, and `ran` / `degraded` / `dropped` classification folded into `run-metadata.md` — use `references/execution-harness.md`.

## CLI Execution Notes

> The conductor's seat-adapter **registry** (`scripts/_conductor/registry.py`) is the **canonical, self-healing** source for these mechanics — exact flags, gate-mode isolation, stdin handling, and model-id self-heal — kept current and asserted by tests. When a flag drifts, fix it there, in one place. The templates below are the **portable fallback** for running a seat by hand without the conductor; they are illustrative and not guaranteed current.

Prefer read-only modes. Confirm every flag against the installed CLI (`<cli> --help`) before a large run — or just use the conductor, which does.

Claude seat:

```
claude -p "<seat prompt>" --model fable --effort max --permission-mode plan
```

`-p` runs non-interactively; `--permission-mode plan` keeps it read-only. `--effort max` requests the deepest reasoning the installed build exposes. On long analytic prompts, plan mode can make the seat return a plan-style *summary* (and even claim it wrote a file) instead of the full review — so append the `{{CLAUDE_OUTPUT_OVERRIDE}}` block from `references/prompt-templates.md` verbatim to the Claude seat's prompt, and treat a short or plan-shaped artifact as a degraded seat to re-run.

Codex seat:

```
codex exec --sandbox read-only --skip-git-repo-check \
  --config model_reasoning_effort="xhigh" \
  "<seat prompt>" </dev/null
```

`codex exec` is the non-interactive form; `--sandbox read-only` blocks edits. Close stdin with `</dev/null`: `codex exec` reads stdin until EOF, so without it the call hangs when orchestrated in the background or any non-interactive pipeline. Pass `--skip-git-repo-check` so the run doesn't abort with "Not inside a trusted directory" when a seat runs from a neutral, non-git source folder.

Gemini seat:

```
gemini -p "<seat prompt>" -m pro
```

Run in a read-only / non-auto-approval mode so the seat can't make edits, and select the highest available thinking level. The Gemini CLI may print internal errors to stderr (e.g. model-router retries) yet still return a valid review — judge a seat by whether usable content came back, not by stderr noise or a non-zero exit; treat that as a degraded-but-ran seat, not a failure.

Grok seat:

```
grok -p "<seat prompt>" --model grok-4.5 --effort high \
  --output-format plain --permission-mode plan --sandbox read-only \
  --no-subagents --no-memory --disable-web-search \
  --disallowed-tools WebFetch
```

The conductor passes `--model grok-4.5`, the only model the CLI now lists. Override it only to pin a different exact model ID. `--no-auto-update` was removed upstream, so it is no longer passed. `--sandbox read-only` and plan mode block edits; the web flags remove search/fetch in gate mode.

### Gemini thinking level

Prefer a CLI flag or environment variable if the installed Gemini CLI exposes one. Edit settings files only as a last resort — and if you do, back up the existing file first and restore it in a cleanup step that runs even on failure, so a crash can't leave the user's config mutated. Verify the schema against the current Gemini CLI configuration reference first; the shape below is illustrative, not guaranteed current:

```json
{
  "modelConfigs": {
    "customAliases": {
      "<alias>": {
        "modelConfig": {
          "model": "pro",
          "generateContentConfig": {
            "thinkingConfig": { "thinkingLevel": "HIGH" }
          }
        }
      }
    }
  }
}
```

## Prompt Templates

Load `references/prompt-templates.md` when running a board. Use the templates as a starting point, then adapt them to the source material, output type, and project constraints.

## Scripts

Optional helpers in `scripts/` (Python 3 stdlib, no install): `board_verdict.py` validates `verdict.json` and gates CI on the verdict (`--gate`; exit `1` block / `3` abstain when the board is torn or a citation is refuted; **`--min-severity blocker|concern`** (v1.14) narrows a fail — it composes with `--fail-on` so a fail must ALSO rest on a finding at/above that tier, e.g. a caution whose only findings are concerns/dissent passes under `blocker` — never affecting abstain), and appends append-only human tuning with `board_verdict.py amend` (a confidence change, caveat, or severity note, each with provenance — the board's own words stay untouched); `board_changes.py` validates a `changes.json` (the v1.13 `run --output revised-draft` artifact of record — the edit→finding mapping plus the per-edit board `endorsements` — `references/changes-schema.md`); `board_rubric.py` validates a `rubric.json` (the v1.15 `--rubric` pre-round artifact — merged criteria, weight-sum-to-100, and the chair's partition); `board_scorecard.py` validates a `scorecard.json` (the v1.15 post-rounds scoring artifact — per-round score trajectory, weighted totals, bands, and token↔band contradictions); `verify_evidence.py` resolves a verdict's typed evidence and stamps each `verified`/`unverified`/`refuted` (incl. opt-in, program-pinned re-execution of `command` citations via `--allow-program`); `render_verdict.py` renders `final-consensus.md` from the verdict; `format_output.py` renders it as a TL;DR, PR comment, Slack message, or JSON; `render_handoff.py` renders `final-consensus.html` deterministically from a `handoff-data.json`; and `render_plan.py` renders a **planning-document HTML view** deterministically from its markdown (`design/<plan>.md` is the source of truth — the HTML is regenerated, never hand-edited), the same render-from-source discipline, for following along as a multi-milestone plan is built. The skill runs fine without them — they're for wiring a board into CI and other tooling. See `scripts/README.md`.

## When To Stop

Stop and ask or report if:

- no source material is given and none is inferable from an obvious file or repo;
- fewer than two seats can authenticate or run — a board needs at least two voices;
- a step would need write access but the user asked for review only;
- full cross-reading would blow the context budget — fall back to summaries and say so;
- the material is too sensitive to send to external providers and no local-only board is available (`references/data-handling.md`).

If a provider is unavailable, or fails partway through, but at least two seats remain, continue as a smaller board and label the missing seat (and the round it dropped out) in the handoff rather than silently omitting it.

---
name: advisory-board
description: Convene a multi-model advisory board — subscription-backed Claude, Codex, Gemini, and Grok CLIs reviewing the same material in formal, roundtable, or competitive mode. Use when the user asks for an advisory board, roundtable, panel, or idea tournament; a multi-model or cross-provider review or debate; a red-team of a plan, design, decision, or document by several models; or a consensus handoff from several frontier models.
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
- Write run artifacts to the **persistent runs root** — `~/.advisory-board/runs/<slug>-<date>/` (a same-day rerun gets a `-2` suffix, never an overwrite) — so runs stop evaporating and `run_board.py history` can list them. `--runs-root`/`--out` redirect; `--ephemeral` opts back into a throwaway `/tmp/advisory-board-*` folder. Every real run announces where its artifacts land on its first output line. Persistence changes only the disk location — artifacts inherit the run's sensitivity handling (`references/data-handling.md`).
- Writing artifacts into the reviewed project is itself a write, even on a read-only review: do that only when the user asks or agrees, prefer a dedicated `advisory-board/<timestamp>/` (or `docs/advisory-board/<timestamp>/`) folder, and never write into a tracked git tree without naming the location first.
- One flag sets the whole cost/depth posture: **`--tier quick|standard|deep`** — rounds, cross-reading, and per-seat reasoning together (`standard` is today's defaults, a deliberate no-op; exact per-tier values live in the registry and `scripts/README.md`). The tier is a **base**: explicit flags (`--rounds`, `--cross-reading`, per-seat `--effort`) always override it, and `run-recipe.yaml` records the resolved selectors and effort values. Provider-maintained aliases deliberately re-resolve on a later run; `--model seat=id` is the exact-pin escape hatch. Four frontier models at high reasoning across several rounds can take minutes and meaningful tokens — flag a large run before launching it; `run_board.py run … --dry-run` prints a best-effort estimate.

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

- Claude seat: Anthropic's maintained `fable` alias at `--effort max`. Where `fable` doesn't resolve (older CLI or account), preflight proposes the `opus` fallback — never applies it silently.
- Codex seat: the Codex CLI's recommended model (no exact model pin) with `model_reasoning_effort="xhigh"`.
- Gemini seat: Google's maintained `pro` alias (latest highest-reasoning Pro model) with the CLI's highest available thinking level.
- Grok seat: `grok-4.5` through the official `grok` CLI at `--effort high` — the only model the CLI currently lists.

The selector (`fable`, `pro`, `grok-4.5`, or Codex `auto`) and the model that actually answered are separate provenance fields. If a CLI cannot report the resolved ID, record `unknown` rather than pretending. Use an exact `--model` override for an eval or replay that must not float.

**Preflight** — run `references/preflight.md` before launching: for each seat, check the CLI is present, auth is active (subscription-backed where possible), the requested model resolves, and a one-token smoke ping returns. First run or new machine: `run_board.py doctor` sweeps **every** registered provider with per-provider fix-it steps and a viable-board summary — probes and smoke-pings only, it never reads or sends your material; `run_board.py toolchain` checks CLI currency and (consent-gated) updates or installs. Proceed only with at least two seats GO; fewer isn't a dead end — preflight distinguishes *not installed* from *installed-but-unauthed* and names the fallbacks: a same-provider multi-lens board or a local/human seat (`references/board-composition.md`). Label any degraded or dropped seat in the handoff.

## Seats

Give each seat its own angle so the board covers more ground than any single reviewer, and match the lenses to the subject. Pick a ready-made lens set from `references/lens-presets.md` — `software-architecture` (default), `product-strategy`, `research-paper`, `legal-contract`, `business-decision`, `writing-editing`, `red-team` (every seat hostile — the stress-test preset), `stakeholder-panel` (convene "the room this decision would face") — or compose your own. The same lens on two different providers is a valid cross-model pairing; only same-provider-same-lens wastes a seat. For software and technical work, the default split:

- Claude: architecture, systems, and adversarial design review.
- Codex: repo-grounded implementation, migration, testing, and execution.
- Gemini: product, operations, rollout, latency, evaluation, and user-workflow risk.
- Grok: contrarian synthesis, hidden assumptions, alternatives, and decision-changing evidence.

For non-software subjects (strategy, research, writing, business, policy), assign comparable lenses — e.g. one seat on first-principles soundness, one on execution and feasibility, one on second-order consequences and stakeholder or user risk.

Every seat still answers the full brief; the lens reduces blind spots, it doesn't narrow responsibility.

The board defaults to four seats but isn't fixed at four — for sizing (2–10), the same provider in multiple seats (each duplicate taking its own lens), a human or local-model seat, an **Antigravity** seat, and minimal "works with what you have" lineups, see `references/board-composition.md`.

## Data Handling

A board sends the same source material to every seat's provider. Before the first call, if the material isn't already public, tell the user what will leave the machine and to whom, and get a go-ahead. For sensitive material, redact the shared source packet; for must-not-leave material, run a local-only board or don't run it. Full guidance: `references/data-handling.md`.

### Repo-grounding & verification

By default a board reviews the **text you hand it** and is blind to the codebase that text is about — so findings come back conditional on the cited factual base, none confirmed by a seat that read the code. `--repo PATH` closes that gap: it augments `--source` (the source file still frames the question; the repo is the evidence base) by handing every seat a **read-only snapshot** of the repository — `.gitignore`-respecting, `.git`-excluded, secret-denylisted, symlink-confined — so seats verify claims against real code and cite real `path:line`. Consent binds to the snapshot's **scope hash** alongside the source-packet hash, and `repo-scope-manifest.json` records exactly what was in scope at approval.

Grounding then makes the verdict chain trustworthy on **code**, not just prose: `verify --source <repo> --run <out>` resolves those citations against the tree and stamps each `verified`/`unverified`/`refuted` — a fabricated citation stamps `refuted` and `validate --gate` abstains.

In **gate mode** (`--repo` on a gate-bearing run), the safety policy is **read XOR network**: every seat must be network-isolatable, because a grounded seat that is also networked can read a secret and exfiltrate it. Seats that can't be de-networked (today **gemini**, **antigravity**) make a gate+`--repo` run **refuse** — the offending seat named as a labeled NO-GO, never silently dropped — and a gate-bearing run never silently falls back to advisory. **Advisory + `--repo`** is the home for casual self-review of your own repo (network on, you own the risk) with a loud disclosure.

Be honest about the limits when reporting: a `verified` stamp means the receipt resolves, not that the inference drawn from it is sound, and it is a statement about the snapshot at approval time — the poisoned-repo and snapshot-drift caveats, and why the snapshot bounds consent rather than physical reads, are in `references/data-handling.md` §Repo-grounded review.

## Round Protocol

This section defines **Formal Board Review** — the default mode and the only one the conductor drives end-to-end. Roundtable and Competitive replace it with their own phase structures (`references/modes.md`).

**Rubric-first scoring (`--rubric`, optional).** Before round 1 the board can agree its own weighted criteria and then score every round against them, so the verdict is backed by a comparable number as well as prose. Two mechanically-checked passes run first: a **proposal fan-out** (every seat proposes 3–7 weighted criteria from the same source packet round 1 sees; the conductor mints the proposal ids — a model never mints identity) and a **chair merge** (one board seat merges every usable proposal into one weighted rubric with an explicit partition; the conductor mechanically reconciles the partition and the weights-sum-to-100 invariant, retries once, then refuses). Too few proposals or an unreconcilable merge **refuses the run before any opinion round spends a token** — the one place in the whole skill that refuses outright rather than degrading — writing `rubric-rejected.json`; success writes `rubric.json` post-consent, pre-rounds, so it survives a later scoring failure. The agreed rubric is injected into **every** opinion round: each seat emits one `SCORE cN: <1-5>` line per criterion (a bad or missing line degrades that cell to absent — never imputed, and never making the seat unusable) plus an optional `RUBRIC-NOTE:` objection (recorded, never debated — scoring under the rubric *is* accepting it). `--rounds auto` convergence widens to include score movement. On a `--revise --rubric` run the prior rubric is carried forward mechanically, so scores stay comparable across revisions. **Scores are informational only — the gate never reads them.** Injected block and token grammar: `references/prompt-templates.md`; artifacts and chair-seat resolution: `references/verdict-schema.md`, `scripts/README.md`.

**Round 1 — independent.**

- Give each seat the same source packet and its role lens, nothing else.
- No other seat's opinions.
- Require: verdict (with a confidence level — low/medium/high), strongest objections, revised sequence, invariants, risks, and concrete evidence.

**Round 2 — rebuttal (default).**

- Build a board packet from Round 1: a structured digest (`summaries`, the default) that puts every seat's take on each topic side by side under a verdict/citation agreement header — where the board agrees and where it splits — or the full prior responses when the token budget allows (`full`). `run_board.py` builds this deterministically from each review's own section structure plus the `VERDICT:` tokens; it never clusters claims by meaning. `--digest-format json` also writes each round's digest as typed JSON.
- Ask each seat: what another seat caught that you missed, what changed your view (and whether the change is driven by evidence or mere deference — see `references/epistemics.md`), what you still dispute, what should become consensus, and what stays unresolved.

**Round 3 — convergence (optional).**

- Give each seat the Round 2 packet.
- Ask for the final position, hard dissent, and the smallest viable plan.

**Adaptive rounds (`auto`).**

- Stop early when the board has converged — a shared verdict, high confidence, and no material dissent after a round — rather than spending a round to rubber-stamp.
- Add a round when material dissent or low confidence remains and another exchange could plausibly resolve it, up to the `--max-rounds` ceiling (default 3).
- `run_board.py --rounds auto` makes this concrete: each seat ends its review with a `VERDICT: ship|caution|block` line, and the conductor measures **movement** between rounds as a pure function over that token plus the seat's concrete citations — never the prose (the model reasons; the conductor diffs tokens). It keeps going while the board is still moving and stops the moment it goes quiet; the per-round movement and the stop reason are recorded in `run-metadata.md` (`## Convergence`).
- **Independence / echo score:** convergence can be *earned* (the seats independently reached the same answer) or *social* (they read each other and drifted into agreement). Round 2+ seats self-report a `BASIS: independent|evidence|deference` line, and the conductor scores echo risk over the final round's parsed signals as a coarse **low / moderate / high** band with a one-line explanation, recorded in `run-metadata.md`. It **flags** possible echo; it does not prove independence (`references/epistemics.md`).

**Final synthesis.**

- After the last round, write the handoff: consensus, dissent (and why it matters), revised plan, risks, invariants, evidence, and next actions.
- **Write the handoff for a human who was not in the room.** Lead with the bottom line — `summary` in `verdict.json`: 3–6 plain sentences saying what was reviewed, what the board decided, why, and what happens next. Every prose field must read as plain English on the first pass: short sentences, no coined compound labels, no unexplained jargon; a finding's title is a complete sentence naming what can go wrong, and mechanism detail lives in the evidence citations, not the prose. This contract binds a hand-authored verdict (the degraded-synthesizer path) exactly as it binds the synthesizer seat.
- Prefer a neutral synthesizer — a seat that didn't debate, or a blind merge — so the chair doesn't grade its own work (`references/epistemics.md`). If the board is unanimous, include a minority report: the strongest case against the verdict.
- Label model and round provenance (the model that actually answered, not just the one requested), and split the findings into three explicit buckets: **evidence-backed** (tied to a file, fact, run, or citation), **judgment calls** (reasoned but unproven here), and **couldn't-verify** (claims the board leaned on but didn't check, plus the shared blind spots no seat could see). For each load-bearing conclusion, note what would change it. The couldn't-verify bucket is the main guard against a confident, unanimous, *wrong* call — three models can converge on the same missing fact (`references/epistemics.md`).
- Emit `verdict.json` alongside the prose (`references/verdict-schema.md`) so the result can drive a gate or other tooling.

## Artifact Standard

Write:

- `round-1/<seat>.md` (and `round-2/`, `round-3/` as rounds run)
- `board-packet-round-2.md` (and `board-packet-round-3.md` when needed)
- `final-consensus.md` — the handoff in Markdown
- `final-consensus.html` — a self-contained, human-readable view of the handoff. Render it deterministically with `scripts/render_handoff.py` from a `handoff-data.json` (recommended — guarantees no leftover placeholders or template drift), or fill `references/handoff-template.html` by hand. `render_verdict.py --shape` chooses the view (full handoff, quick verdict, or implementation sequence) and `--filter` trims by severity — a dropped section is stated with counts, never silently elided; see `references/output-formats.md`.
- `verdict.json` — the machine-readable verdict (`references/verdict-schema.md`); gate or reformat it with `scripts/`
- `changes.json` + `revised-draft.*` — **only with `run --output revised-draft`**: a board-derived revised copy of the source, each edit mapped to the board finding it resolves and mechanically validated, then voted on per edit by the non-revision seats in the **endorsement pass** (`ENDORSE`/`OBJECT`/`ABSTAIN`; objections are recorded for a human to read, never resolved by another model loop; `--no-endorse` opts out, leaving a *findings-mapped*, not board-endorsed, run). The draft is **byte-clean** (the revised source bytes and nothing else) and the source file is **never written** — applying the revision is your act. Conflicting findings surface as `unresolved` entries, never silently reconciled. A **code** source also gets a git-apply-able `revised-draft.patch`; a **prose** source instead gets a word-level redline section in the full-handoff HTML — both pure views, sha-verified against `changes.json` before a byte is diffed. Schema and validation: `references/changes-schema.md`.
- **Grounded citation snippets.** When a grounded run resolves a `code` citation, the cited lines are captured onto the evidence entry so the handoff embeds the receipt itself — self-contained even though the repo snapshot is cleaned up after the run (`references/verdict-schema.md`).
- `rubric.json` + `scorecard.json` — **only with `--rubric`**: the pre-round merged rubric (criteria, weights, chair partition, proposal provenance) and the post-rounds score trajectory with conductor-computed per-seat totals and coarse bands. Both strictly validated; a validation failure warns and writes nothing — the rounds and verdict still stand. Scores never move the verdict or the gate; a severe token↔band contradiction is recorded and surfaced loudly in the verdict summary. Schemas: `references/verdict-schema.md`, `scripts/README.md`.
- `run-metadata.md` — provenance: commands, the model that actually answered per seat, auth mode (no secrets), per-seat status (ran / degraded / dropped), timings, and source paths. Use `references/run-metadata-template.md`. When a seat CLI reports its own token usage, record per-seat tokens and a best-effort cost/time line — nothing is ever guessed.

When a seat is degraded or dropped, show it on its HTML seat card (status pill) and in `verdict.json` (`dropped: true`) — never let a smaller board look like a full one. Derive lighter shares (TL;DR, PR comment, Slack, print/PDF) per `references/output-formats.md`.

**Output contract for the HTML.** It is a *view* of `final-consensus.md`, not a second source of truth — the two must not disagree. The rendered file must contain no leftover `{{tokens}}` and no template scaffolding comments, and must stay self-contained (inline CSS only; no external fonts, CDNs, scripts, or remote `<link>`/`<script src>`) so it opens offline on a double-click. Follow the template's two-placeholder convention: replace each single `{{TOKEN}}` in place, and duplicate each `BEGIN`/`END` block once per item (delete the sample block if there are none).

## How A Run Executes

**The conductor — `scripts/run_board.py` — is the canonical way to drive a board.** It owns the load-bearing mechanics in code: the seat-adapter **registry** (the one place that knows each CLI's flags, isolation, and model-id self-heal), the executable **preflight** (GO/NO-GO), the hash-bound **egress/quarantine gate** before any byte leaves, the **round fan-outs** with the failure protocol, the **verdict chain** (`verify` evidence → `consensus` md/html → `validate`/gate), and the **run history**. Synthesis stays your reasoning task — the conductor stops at clean per-round packets and hands them to you (or one neutral seat) to fill `verdict.json`, then you call the chain. Run `scripts/run_board.py run …`; a real run is in the repo-root `examples/payments-idempotency-review/`.

Beyond `run`, know these run controls exist — exact flags, semantics, and edge rules in `scripts/README.md` and `--help`:

- Per-seat `--timeout` and `--effort` overrides (seat ids as in `--model`; an ambiguous provider name on a duplicate-provider board is refused, never silently collapsed).
- `--revise <prior run dir>` — re-review a revised draft: round-1 prompts carry a mechanical digest of the prior verdict plus the diff from the previously reviewed draft (sha-verified; omitted loudly when unrecoverable), every injected byte inside the consent packet hash; the new verdict records lineage and the consensus leads with cleared / still-open / new.
- `ask "<question>" --run <dir>` — one-round post-verdict cross-examination, from a context packet built only from that run's own artifacts, bounded to the run and re-consented like any egress (the sensitivity floor only ever tightens); writes `addendum-N.md`.
- `board_verdict.py amend` — append-only human tuning of a completed verdict (a confidence change, caveat, or severity note, each with provenance) that never rewrites the board's own words.
- `run --output revised-draft` — the board-endorsed revision (see Artifact Standard); requires a verdict, takes `--source-type prose|code` and `--revision-seat`; a revision failure leaves the verdict and rounds intact.
- A live `status.json`/`status.html` view of a long run (10–15 minutes is normal), rewritten atomically on every transition — a **view, not an artifact of record**; `--no-live-status` drops it, and writing it is best-effort, never able to fail the run.

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

Run in a read-only / non-auto-approval mode so the seat can't make edits, and select the highest available thinking level — prefer a CLI flag or environment variable if the installed CLI exposes one; a settings-file edit is the last resort, with backup and restore-on-failure (`references/execution-harness.md` §Gemini thinking level). The Gemini CLI may print internal errors to stderr (e.g. model-router retries) yet still return a valid review — judge a seat by whether usable content came back, not by stderr noise or a non-zero exit; treat that as a degraded-but-ran seat, not a failure.

Grok seat:

```
grok -p "<seat prompt>" --model grok-4.5 --effort high \
  --output-format plain --permission-mode plan --sandbox read-only \
  --no-subagents --no-memory --disable-web-search \
  --disallowed-tools WebFetch
```

`--sandbox read-only` and plan mode block edits; the web flags remove search/fetch in gate mode. Override `--model` only to pin a different exact model ID.

## Prompt Templates

Load `references/prompt-templates.md` when running a board. Use the templates as a starting point, then adapt them to the source material, output type, and project constraints.

## Scripts

Optional helpers in `scripts/` (Python 3 stdlib, no install): `board_verdict.py` validates `verdict.json`, gates CI on the verdict (`--gate`), and appends human tuning (`amend`); `verify_evidence.py` resolves a verdict's typed evidence and stamps each citation `verified`/`unverified`/`refuted`; `render_verdict.py`/`render_handoff.py` render the consensus Markdown and HTML deterministically; `format_output.py` derives the TL;DR / PR comment / Slack / JSON shares; `board_changes.py`, `board_rubric.py`, and `board_scorecard.py` validate their artifacts; `render_plan.py` renders a planning-document HTML view from its markdown. The skill runs fine without them — they're for wiring a board into CI and other tooling. Flags, exit codes, and composition rules: `scripts/README.md`.

## When To Stop

Stop and ask or report if:

- no source material is given and none is inferable from an obvious file or repo;
- fewer than two seats can authenticate or run — a board needs at least two voices;
- a step would need write access but the user asked for review only;
- full cross-reading would blow the context budget — fall back to summaries and say so;
- the material is too sensitive to send to external providers and no local-only board is available (`references/data-handling.md`).

If a provider is unavailable, or fails partway through, but at least two seats remain, continue as a smaller board and label the missing seat (and the round it dropped out) in the handoff rather than silently omitting it.

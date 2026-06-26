---
name: advisory-board
description: Convene a multi-model advisory board (a round table) where subscription-backed Claude, Codex, and Gemini CLIs each review the same material independently, debate across rounds by reading one another's findings, and converge on a single working handoff. Use when the user asks for an advisory board, round table, or panel; a multi-model or multi-provider review; a skilled debate among models; an adversarial review of a plan, design, architecture, document, decision, or strategy; an Opus/GPT/Gemini cross-check; or a consensus handoff from several frontier models.
---

# Advisory Board

Bring an idea, problem, plan, or architecture to a board of frontier models sitting in different roles. Each reviews it independently, then they read and challenge each other across one or more rounds, and you leave with the strongest conclusion the board can reach together and a clean takeaway — not three disconnected opinions.

## Must Not

Hard rules, collected here so they are never missed (each is elaborated in context below). Violating one invalidates the run.

- **Never write files or make edits** unless the user explicitly asked for edits — the board is read-only by default.
- **Never write artifacts into a tracked git tree** without naming the location first; default to a `/tmp/advisory-board-*` folder.
- **Never substitute a model silently** — if a requested model is unavailable, use the nearest same-provider frontier model and say so.
- **Never skip the data-handling disclosure** for non-public material — not even when the user says "use defaults." Disclose what leaves the machine and to whom, and get a go-ahead, before any external seat runs (`references/data-handling.md`).
- **Never present a degraded or dropped seat as a full board** — label it on the seat card and in `verdict.json` (`dropped: true`); a board needs at least two seats that actually ran.
- **Never print or store secrets** — keys, tokens, cookies, or private environment values — in prompts, packets, artifacts, logs, or metadata.

## Core Defaults

- Use subscription CLIs by default, not provider API keys.
- Run read-only unless the user explicitly asks for edits.
- Rounds: 2. Cross-reading: summaries. Final artifact: full handoff (Markdown plus a self-contained HTML view).
- Write run artifacts to a timestamped `/tmp/advisory-board-*` folder by default. Writing them into the reviewed project is itself a write, even on a read-only review: do that only when the user asks or agrees, prefer a dedicated `advisory-board/<timestamp>/` (or `docs/advisory-board/<timestamp>/`) folder, and never write into a tracked git tree without naming the location first.
- Quick pass: 1 round with `summaries`. High-stakes: 3 rounds with `full` cross-reading. Three frontier models at high reasoning across several rounds can take minutes and meaningful tokens — flag a large run to the user before launching it.

## Upfront Choices

Optionally open with the intake interview (`references/intake-interview.md`) — a short structured Q&A, using the `grilling` or `grill-with-docs` skills as the engine when available — to settle the run. Otherwise ask only for whatever the user hasn't already given:

1. Source material: file(s), repo, URL, or goal to review.
2. Rounds: `1`, `2`, `3`, or `auto` (default `2`; `auto` adapts — see Round Protocol).
3. Cross-reading: `none`, `summaries`, or `full` (default `summaries`).
4. Output: `quick verdict`, `full handoff`, or `implementation sequence` (default `full handoff`).
5. Lens preset: the seat lineup's focus, from `references/lens-presets.md` (default: inferred from the material, falling back to `software-architecture`).
6. Sensitivity: can the material go to external providers? (`references/data-handling.md` — may force a local-only board.)
7. Board: seats and size, from `references/board-composition.md` (default: three seats — Claude, Codex, Gemini).

If the user says "use defaults", stop asking the *optional* setup questions and run with the defaults — with one exception. The data-handling check (choice 6) is mandatory: if the material isn't clearly public, still disclose which providers will receive it and get an explicit go-ahead before launching any external seat (`references/data-handling.md`). "Use defaults" settles the optional choices; it never waives that consent.

## Model Lineup

Target the strongest reasoning model each provider offers:

- Claude seat: `claude-opus-4-8` at the highest available reasoning/effort.
- Codex seat: `gpt-5.5` with `model_reasoning_effort="xhigh"` (or the highest Codex reasoning setting available).
- Gemini seat: Google's latest frontier reasoning model via the Gemini CLI (currently Gemini 3.1 Pro) with `thinkingLevel: HIGH` (or the highest available).

Model names and flags move fast — verify them against the installed CLIs or official docs before a large run. If a named model is unavailable, use the nearest same-provider frontier model and say so; never substitute silently.

Preflight — run `references/preflight.md` before launching: for each seat, check the CLI is present, auth is active (subscription-backed where possible), the requested model resolves, and a one-token smoke ping returns. Proceed only with at least two seats GO; label any degraded or dropped seat in the handoff. In summary:

- **Toolchain currency first** — `run_board.py toolchain` checks each CLI against its latest release and (`--update`, consent-gated) upgrades stale ones; `--install` installs absent ones (account/auth still required). A stale CLI is the usual reason a freshly-renamed frontier model id 404s; updating first keeps the board from half-failing. Model ids stay pinned — if one still won't resolve, preflight *proposes* a working fallback rather than swapping silently.
- **Graceful degradation** — if fewer than two seats are usable (a downloaded skill on a machine with only one provider's CLI/account), preflight doesn't dead-end: it distinguishes *not installed* (prints the install command) from *installed-but-unauthed*, and points to the fallbacks — a same-provider multi-lens board or a local/human seat (`references/board-composition.md`). You never need all three providers to get value.
- Confirm Claude subscription auth is active.
- Confirm Codex is on ChatGPT/subscription auth, not API-key-only, when possible.
- Confirm Gemini auth and model/config support.
- Never print secrets, tokens, cookies, or private environment values.

## Seats

Give each seat a distinct lens so the board covers more ground than any single reviewer, and match the lenses to the subject. Pick a ready-made lens set from `references/lens-presets.md` — `software-architecture` (default), `product-strategy`, `research-paper`, `legal-contract`, `business-decision`, `writing-editing` — or compose your own. For software and technical work, the default split:

- Claude: architecture, systems, and adversarial design review.
- Codex: repo-grounded implementation, migration, testing, and execution.
- Gemini: product, operations, rollout, latency, evaluation, and user-workflow risk.

For non-software subjects (strategy, research, writing, business, policy), assign comparable lenses — e.g. one seat on first-principles soundness, one on execution and feasibility, one on second-order consequences and stakeholder or user risk.

Every seat still answers the full brief; the lens reduces blind spots, it doesn't narrow responsibility.

The board defaults to three seats but isn't fixed at three — for sizing (2–5), the same provider in two seats, a human or local-model seat, an **Antigravity** seat (Google's `agy` CLI, the successor to the sunset gemini-cli), and minimal "works with what you have" lineups, see `references/board-composition.md`.

## Data Handling

A board sends the same source material to every seat's provider. Before the first call, if the material isn't already public, tell the user what will leave the machine and to whom, and get a go-ahead. For sensitive material, redact the shared source packet; for must-not-leave material, run a local-only board or don't run it. Full guidance: `references/data-handling.md`.

## Round Protocol

**Round 1 — independent.**

- Give each seat the same source packet and its role lens, nothing else.
- No other seat's opinions.
- Require: verdict (with a confidence level — low/medium/high), strongest objections, revised sequence, invariants, risks, and concrete evidence.

**Round 2 — rebuttal (default).**

- Build a board packet from Round 1: a structured digest (`summaries`, the default) that puts every seat's take on each topic side by side under a verdict/citation agreement header — where the board agrees and where it splits — or the full prior responses when the token budget allows (`full`). `run_board.py` builds this deterministically from each review's own section structure plus the `VERDICT:` tokens; it never clusters claims by meaning (principle #1).
- Ask each seat: what another seat caught that you missed, what changed your view (and whether the change is driven by evidence or mere deference — see `references/epistemics.md`), what you still dispute, what should become consensus, and what stays unresolved.

**Round 3 — convergence (optional).**

- Give each seat the Round 2 packet.
- Ask for the final position, hard dissent, and the smallest viable plan.

**Adaptive rounds (`auto`).**

- Stop early when the board has converged — a shared verdict, high confidence, and no material dissent after a round — rather than spending a round to rubber-stamp.
- Add a round when material dissent or low confidence remains and another exchange could plausibly resolve it, up to the `--max-rounds` ceiling (default 3).
- `run_board.py --rounds auto` makes this concrete: each seat ends its review with a `VERDICT: ship|caution|block` line, and the conductor measures **movement** between rounds as a pure function over that token plus the seat's concrete citations — never the prose (the model reasons; the conductor diffs tokens). It keeps going while the board is still moving and stops the moment it goes quiet; the per-round movement and the stop reason are recorded in `run-metadata.md` (`## Convergence`).

**Final synthesis.**

- After the last round, write the handoff: consensus, dissent (and why it matters), revised plan, risks, invariants, evidence, and next actions.
- Prefer a neutral synthesizer — a seat that didn't debate, or a blind merge — so the chair doesn't grade its own work (`references/epistemics.md`). If the board is unanimous, include a minority report: the strongest case against the verdict.
- Label model and round provenance (the model that actually answered, not just the one requested), and split the findings into three explicit buckets: **evidence-backed** (tied to a file, fact, run, or citation), **judgment calls** (reasoned but unproven here), and **couldn't-verify** (claims the board leaned on but didn't check, plus the shared blind spots no seat could see). For each load-bearing conclusion, note what would change it. The couldn't-verify bucket is the main guard against a confident, unanimous, *wrong* call — three models can converge on the same missing fact (`references/epistemics.md`).
- Emit `verdict.json` alongside the prose (`references/verdict-schema.md`) so the result can drive a gate or other tooling.

## Artifact Standard

Write:

- `round-1/<seat>.md` (and `round-2/`, `round-3/` as rounds run)
- `board-packet-round-2.md` (and `board-packet-round-3.md` when needed)
- `final-consensus.md` — the handoff in Markdown
- `final-consensus.html` — a self-contained, human-readable view of the handoff. Render it deterministically with `scripts/render_handoff.py` from a `handoff-data.json` (recommended — guarantees no leftover placeholders or template drift), or fill `references/handoff-template.html` by hand
- `verdict.json` — the machine-readable verdict (`references/verdict-schema.md`); gate or reformat it with `scripts/`
- `run-metadata.md` — provenance: commands, the model that actually answered per seat, auth mode (no secrets), per-seat status (ran / degraded / dropped), timings, and source paths. Use `references/run-metadata-template.md`.

When a seat is degraded or dropped, show it on its HTML seat card (status pill) and in `verdict.json` (`dropped: true`) — never let a smaller board look like a full one. Derive lighter shares (TL;DR, PR comment, Slack, print/PDF) per `references/output-formats.md`.

**Output contract for the HTML.** It is a *view* of `final-consensus.md`, not a second source of truth — the two must not disagree. The rendered file must contain no leftover `{{tokens}}` and no template scaffolding comments, and must stay self-contained (inline CSS only; no external fonts, CDNs, scripts, or remote `<link>`/`<script src>`) so it opens offline on a double-click. Follow the template's two-placeholder convention: replace each single `{{TOKEN}}` in place, and duplicate each `BEGIN`/`END` block once per item (delete the sample block if there are none).

Never store secrets. Redact keys, tokens, cookies, and private environment values.

## How A Run Executes

**The conductor — `scripts/run_board.py` — is the canonical way to drive a board.** It owns the load-bearing mechanics in code: a seat-adapter **registry** (the one place that knows each CLI's flags, isolation, and model-id self-heal), an executable **preflight** (GO/NO-GO), a hash-bound **egress/quarantine gate** before any byte leaves, the **round-1 + round-2 fan-out** with the failure protocol, and the **verdict chain** (`verify` evidence → `consensus` md/html → `validate`/gate). Run `scripts/run_board.py run …` (see `scripts/README.md`); a real run is in the repo-root `examples/payments-idempotency-review/`. Synthesis stays your reasoning task — the conductor stops at clean per-round packets and hands them to you (or one neutral seat) to fill `verdict.json`, then you call the chain.

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
claude -p "<seat prompt>" --model claude-opus-4-8 --permission-mode plan
```

`-p` runs non-interactively; `--permission-mode plan` keeps it read-only. Use the strongest reasoning/effort the build exposes (Claude Code defaults to `xhigh`). On long analytic prompts, `--permission-mode plan` can make the seat return a plan-style *summary* (and even claim it wrote a file) instead of the full review — so append the `{{CLAUDE_OUTPUT_OVERRIDE}}` block from `references/prompt-templates.md` verbatim to the Claude seat's prompt, and treat a short or plan-shaped artifact as a degraded seat to re-run.

Codex seat:

```
codex exec --sandbox read-only --skip-git-repo-check \
  --config model="gpt-5.5" \
  --config model_reasoning_effort="xhigh" \
  "<seat prompt>" </dev/null
```

`codex exec` is the non-interactive form; `--sandbox read-only` blocks edits. Close stdin with `</dev/null`: `codex exec` reads stdin until EOF, so without it the call hangs when orchestrated in the background or any non-interactive pipeline. Pass `--skip-git-repo-check` so the run doesn't abort with "Not inside a trusted directory" when a seat runs from a neutral, non-git source folder.

Gemini seat:

```
gemini -p "<seat prompt>" -m "<latest-frontier-gemini-model>"
```

Run in a read-only / non-auto-approval mode so the seat can't make edits, and select the highest available thinking level. The Gemini CLI may print internal errors to stderr (e.g. model-router retries) yet still return a valid review — judge a seat by whether usable content came back, not by stderr noise or a non-zero exit; treat that as a degraded-but-ran seat, not a failure.

### Gemini thinking level

Prefer a CLI flag or environment variable if the installed Gemini CLI exposes one. Edit settings files only as a last resort — and if you do, back up the existing file first and restore it in a cleanup step that runs even on failure, so a crash can't leave the user's config mutated. Verify the schema against the current Gemini CLI configuration reference first; the shape below is illustrative, not guaranteed current:

```json
{
  "modelConfigs": {
    "customAliases": {
      "<alias>": {
        "modelConfig": {
          "model": "<latest-frontier-gemini-model>",
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

Optional helpers in `scripts/` (Python 3 stdlib, no install): `board_verdict.py` validates `verdict.json` and gates CI on the verdict (`--gate`; exit `1` block / `3` abstain when the board is torn or a citation is refuted); `verify_evidence.py` resolves a verdict's typed evidence and stamps each `verified`/`unverified`/`refuted` (incl. opt-in, program-pinned re-execution of `command` citations via `--allow-program`); `render_verdict.py` renders `final-consensus.md` from the verdict; `format_output.py` renders it as a TL;DR, PR comment, Slack message, or JSON; `render_handoff.py` renders `final-consensus.html` deterministically from a `handoff-data.json`; and `render_plan.py` renders a **planning-document HTML view** deterministically from its markdown (`design/<plan>.md` is the source of truth — the HTML is regenerated, never hand-edited), the same render-from-source discipline, for following along as a multi-milestone plan is built. The skill runs fine without them — they're for wiring a board into CI and other tooling. See `scripts/README.md`.

## When To Stop

Stop and ask or report if:

- no source material is given and none is inferable from an obvious file or repo;
- fewer than two seats can authenticate or run — a board needs at least two voices;
- a step would need write access but the user asked for review only;
- full cross-reading would blow the context budget — fall back to summaries and say so;
- the material is too sensitive to send to external providers and no local-only board is available (`references/data-handling.md`).

If a provider is unavailable, or fails partway through, but at least two seats remain, continue as a smaller board and label the missing seat (and the round it dropped out) in the handoff rather than silently omitting it.

---
name: advisory-board
description: Convene a multi-model advisory board (a round table) where subscription-backed Claude, Codex, and Gemini CLIs each review the same material independently, debate across rounds by reading one another's findings, and converge on a single working handoff. Use when the user asks for an advisory board, round table, or panel; a multi-model or multi-provider review; a skilled debate among models; an adversarial review of a plan, design, architecture, document, decision, or strategy; an Opus/GPT/Gemini cross-check; or a consensus handoff from several frontier models.
---

# Advisory Board

Bring an idea, problem, plan, or architecture to a board of frontier models sitting in different roles. Each reviews it independently, then they read and challenge each other across one or more rounds, and you leave with the strongest conclusion the board can reach together and a clean takeaway — not three disconnected opinions.

## Core Defaults

- Use subscription CLIs by default, not provider API keys.
- Run read-only unless the user explicitly asks for edits.
- Rounds: 2. Cross-reading: summaries. Final artifact: full handoff (Markdown plus a self-contained HTML view).
- Save artifacts in a timestamped folder near the reviewed material, or in `/tmp/advisory-board-*` if there is no obvious project folder.
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

If the user says "use defaults", stop asking and run.

## Model Lineup

Target the strongest reasoning model each provider offers:

- Claude seat: `claude-opus-4-8` at the highest available reasoning/effort.
- Codex seat: `gpt-5.5` with `model_reasoning_effort="xhigh"` (or the highest Codex reasoning setting available).
- Gemini seat: Google's latest frontier reasoning model via the Gemini CLI (currently Gemini 3.1 Pro) with `thinkingLevel: HIGH` (or the highest available).

Model names and flags move fast — verify them against the installed CLIs or official docs before a large run. If a named model is unavailable, use the nearest same-provider frontier model and say so; never substitute silently.

Preflight — run `references/preflight.md` before launching: for each seat, check the CLI is present, auth is active (subscription-backed where possible), the requested model resolves, and a one-token smoke ping returns. Proceed only with at least two seats GO; label any degraded or dropped seat in the handoff. In summary:

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

The board defaults to three seats but isn't fixed at three — for sizing (2–5), the same provider in two seats, a human or local-model seat, and minimal "works with what you have" lineups, see `references/board-composition.md`.

## Data Handling

A board sends the same source material to every seat's provider. Before the first call, if the material isn't already public, tell the user what will leave the machine and to whom, and get a go-ahead. For sensitive material, redact the shared source packet; for must-not-leave material, run a local-only board or don't run it. Full guidance: `references/data-handling.md`.

## Round Protocol

**Round 1 — independent.**

- Give each seat the same source packet and its role lens, nothing else.
- No other seat's opinions.
- Require: verdict (with a confidence level — low/medium/high), strongest objections, revised sequence, invariants, risks, and concrete evidence.

**Round 2 — rebuttal (default).**

- Build a board packet from Round 1: summaries with links/paths to the full artifacts (`summaries`), or full prior responses when the token budget allows (`full`).
- Ask each seat: what another seat caught that you missed, what changed your view (and whether the change is driven by evidence or mere deference — see `references/epistemics.md`), what you still dispute, what should become consensus, and what stays unresolved.

**Round 3 — convergence (optional).**

- Give each seat the Round 2 packet.
- Ask for the final position, hard dissent, and the smallest viable plan.

**Adaptive rounds (`auto`).**

- Stop early when the board has converged — a shared verdict, high confidence, and no material dissent after a round — rather than spending a round to rubber-stamp.
- Add a round (up to 3) when material dissent or low confidence remains and another exchange could plausibly resolve it.

**Final synthesis.**

- After the last round, write the handoff: consensus, dissent (and why it matters), revised plan, risks, invariants, evidence, and next actions.
- Prefer a neutral synthesizer — a seat that didn't debate, or a blind merge — so the chair doesn't grade its own work (`references/epistemics.md`). If the board is unanimous, include a minority report: the strongest case against the verdict.
- Label model and round provenance (the model that actually answered, not just the one requested), and keep evidence-backed conclusions separate from judgment calls.
- Emit `verdict.json` alongside the prose (`references/verdict-schema.md`) so the result can drive a gate or other tooling.

## Artifact Standard

Write:

- `round-1/<seat>.md` (and `round-2/`, `round-3/` as rounds run)
- `board-packet-round-2.md` (and `board-packet-round-3.md` when needed)
- `final-consensus.md` — the handoff in Markdown
- `final-consensus.html` — a self-contained, human-readable view of the handoff, rendered from `references/handoff-template.html`
- `verdict.json` — the machine-readable verdict (`references/verdict-schema.md`); gate or reformat it with `scripts/`
- `run-metadata.md` — provenance: commands, the model that actually answered per seat, auth mode (no secrets), per-seat status (ran / degraded / dropped), timings, and source paths. Use `references/run-metadata-template.md`.

When a seat is degraded or dropped, show it on its HTML seat card (status pill) and in `verdict.json` (`dropped: true`) — never let a smaller board look like a full one. Derive lighter shares (TL;DR, PR comment, Slack, print/PDF) per `references/output-formats.md`.

**Output contract for the HTML.** It is a *view* of `final-consensus.md`, not a second source of truth — the two must not disagree. The rendered file must contain no leftover `{{tokens}}` and no template scaffolding comments, and must stay self-contained (inline CSS only; no external fonts, CDNs, scripts, or remote `<link>`/`<script src>`) so it opens offline on a double-click. Follow the template's two-placeholder convention: replace each single `{{TOKEN}}` in place, and duplicate each `BEGIN`/`END` block once per item (delete the sample block if there are none).

Never store secrets. Redact keys, tokens, cookies, and private environment values.

## How A Run Executes

You (the orchestrating agent) drive the board by shelling out to each provider's CLI and collecting its written artifact:

- Run every seat as its own CLI subprocess — including the Claude seat as a separate `claude` process — so each reviews the source independently rather than reusing the orchestrator's context. That independence is what makes Round 1 worth anything.
- Keep the orchestrator and the chair neutral: assemble packets and synthesize, but don't also count yourself as a debating seat. If you must, say so in the handoff and use a minority report to check chair bias (`references/epistemics.md`).
- When the source is a repo or local files, decide once how seats reach it and record it in `run-metadata.md`: either every CLI reads the same shared path, or you build one source packet and hand identical bytes to each seat. Use one method for all seats so they review the same thing.
- Seats are agentic — they may web-search and read their working directory, which usually *helps* (live grounding). When you need a clean outside view or isolation, control the working directory and network and hand each seat one neutral source packet. (Running seats from a non-git folder also requires Codex's `--skip-git-repo-check`.)

## CLI Execution Notes

Prefer read-only modes. The commands below are starting templates — confirm every flag against the installed CLI (`<cli> --help`) before a large run, because CLI syntax changes between versions and these are not guaranteed current.

Claude seat:

```
claude -p "<seat prompt>" --model claude-opus-4-8 --permission-mode plan
```

`-p` runs non-interactively; `--permission-mode plan` keeps it read-only. Use the strongest reasoning/effort the build exposes (Claude Code defaults to `xhigh`). On long analytic prompts, `--permission-mode plan` can make the seat return a plan-style *summary* (and even claim it wrote a file) instead of the full review — so tell the seat to output its complete review as its reply and not write any files.

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

Optional helpers in `scripts/` (Python 3 stdlib, no install): `board_verdict.py` validates `verdict.json` and gates CI on the verdict (`--gate`); `format_output.py` renders it as a TL;DR, PR comment, Slack message, or JSON. The skill runs fine without them — they're for wiring a board into CI and other tooling. See `scripts/README.md`.

## When To Stop

Stop and ask or report if:

- no source material is given and none is inferable from an obvious file or repo;
- fewer than two seats can authenticate or run — a board needs at least two voices;
- a step would need write access but the user asked for review only;
- full cross-reading would blow the context budget — fall back to summaries and say so;
- the material is too sensitive to send to external providers and no local-only board is available (`references/data-handling.md`).

If a provider is unavailable, or fails partway through, but at least two seats remain, continue as a smaller board and label the missing seat (and the round it dropped out) in the handoff rather than silently omitting it.

---
name: advisory-board
description: Convene a multi-model advisory board (a round table) where subscription-backed Claude, Codex, and Gemini CLIs each review the same material independently, debate across rounds by reading one another's findings, and converge on a single working handoff. Use when the user asks for an advisory board, round table, or panel; a multi-model or multi-provider review; a skilled debate among models; an adversarial review of a plan, design, architecture, document, decision, or strategy; an Opus/GPT/Gemini cross-check; or a consensus handoff from several frontier models.
---

# Advisory Board

Bring an idea, problem, plan, or architecture to a board of frontier models sitting in different roles. Each reviews it independently, then they read and challenge each other across one or more rounds, and you leave with the strongest conclusion the board can reach together and a clean takeaway — not three disconnected opinions.

## Core Defaults

- Use subscription CLIs by default, not provider API keys.
- Run read-only unless the user explicitly asks for edits.
- Rounds: 2. Cross-reading: summaries. Final artifact: full handoff.
- Save artifacts in a timestamped folder near the reviewed material, or in `/tmp/advisory-board-*` if there is no obvious project folder.
- Quick pass: 1 round with `summaries`. High-stakes: 3 rounds with `full` cross-reading. Three frontier models at high reasoning across several rounds can take minutes and meaningful tokens — flag a large run to the user before launching it.

## Upfront Choices

Ask only for whatever the user hasn't already given:

1. Source material: file(s), repo, URL, or goal to review.
2. Rounds: `1`, `2`, or `3` (default `2`).
3. Cross-reading: `none`, `summaries`, or `full` (default `summaries`).
4. Output: `quick verdict`, `full handoff`, or `implementation sequence` (default `full handoff`).

If the user says "use defaults", stop asking and run.

## Model Lineup

Target the strongest reasoning model each provider offers:

- Claude seat: `claude-opus-4-8` at the highest available reasoning/effort.
- Codex seat: `gpt-5.5` with `model_reasoning_effort="xhigh"` (or the highest Codex reasoning setting available).
- Gemini seat: Google's latest frontier reasoning model via the Gemini CLI (currently Gemini 3.1 Pro) with `thinkingLevel: HIGH` (or the highest available).

Model names and flags move fast — verify them against the installed CLIs or official docs before a large run. If a named model is unavailable, use the nearest same-provider frontier model and say so; never substitute silently.

Preflight:

- Confirm Claude subscription auth is active.
- Confirm Codex is on ChatGPT/subscription auth, not API-key-only, when possible.
- Confirm Gemini auth and model/config support.
- Never print secrets, tokens, cookies, or private environment values.

## Seats

Give each seat a distinct lens so the board covers more ground than any single reviewer, and match the lenses to the subject. For software and technical work, a strong default split:

- Claude: architecture, systems, and adversarial design review.
- Codex: repo-grounded implementation, migration, testing, and execution.
- Gemini: product, operations, rollout, latency, evaluation, and user-workflow risk.

For non-software subjects (strategy, research, writing, business, policy), assign comparable lenses — e.g. one seat on first-principles soundness, one on execution and feasibility, one on second-order consequences and stakeholder or user risk.

Every seat still answers the full brief; the lens reduces blind spots, it doesn't narrow responsibility.

## Round Protocol

**Round 1 — independent.**

- Give each seat the same source packet and its role lens, nothing else.
- No other seat's opinions.
- Require: verdict, strongest objections, revised sequence, invariants, risks, and concrete evidence.

**Round 2 — rebuttal (default).**

- Build a board packet from Round 1: summaries with links/paths to the full artifacts (`summaries`), or full prior responses when the token budget allows (`full`).
- Ask each seat: what another seat caught that you missed, what changed your view, what you still dispute, what should become consensus, and what stays unresolved.

**Round 3 — convergence (optional).**

- Give each seat the Round 2 packet.
- Ask for the final position, hard dissent, and the smallest viable plan.

**Final synthesis.**

- After the last round, write the handoff: consensus, dissent (and why it matters), revised plan, risks, invariants, evidence, and next actions.
- Label model and round provenance, and keep evidence-backed conclusions separate from judgment calls.

## Artifact Standard

Write:

- `round-1/<seat>.md` (and `round-2/`, `round-3/` as rounds run)
- `board-packet-round-2.md` (and `board-packet-round-3.md` when needed)
- `final-consensus.md`
- optional `run-metadata.md`: commands, model names, auth/account status (no secrets), timestamps, and source paths

Never store secrets. Redact keys, tokens, cookies, and private environment values.

## How A Run Executes

You (the orchestrating agent) drive the board by shelling out to each provider's CLI and collecting its written artifact:

- Run every seat as its own CLI subprocess — including the Claude seat as a separate `claude` process — so each reviews the source independently rather than reusing the orchestrator's context. That independence is what makes Round 1 worth anything.
- Keep the orchestrator and the chair neutral: assemble packets and synthesize, but don't also count yourself as a debating seat. If you must, say so in the handoff.
- When the source is a repo or local files, decide once how seats reach it and record it in `run-metadata.md`: either every CLI reads the same shared path, or you build one source packet and hand identical bytes to each seat. Use one method for all seats so they review the same thing.

## CLI Execution Notes

Prefer read-only modes. The commands below are starting templates — confirm every flag against the installed CLI (`<cli> --help`) before a large run, because CLI syntax changes between versions and these are not guaranteed current.

Claude seat:

```
claude -p "<seat prompt>" --model claude-opus-4-8 --permission-mode plan
```

`-p` runs non-interactively; `--permission-mode plan` keeps it read-only. Use the strongest reasoning/effort the build exposes (Claude Code defaults to `xhigh`).

Codex seat:

```
codex exec --sandbox read-only \
  --config model="gpt-5.5" \
  --config model_reasoning_effort="xhigh" \
  "<seat prompt>"
```

`codex exec` is the non-interactive form; `--sandbox read-only` blocks edits.

Gemini seat:

```
gemini -p "<seat prompt>" -m "<latest-frontier-gemini-model>"
```

Run in a read-only / non-auto-approval mode so the seat can't make edits, and select the highest available thinking level.

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

## When To Stop

Stop and ask or report if:

- no source material is given and none is inferable from an obvious file or repo;
- fewer than two seats can authenticate or run — a board needs at least two voices;
- a step would need write access but the user asked for review only;
- full cross-reading would blow the context budget — fall back to summaries and say so.

If a provider is unavailable, or fails partway through, but at least two seats remain, continue as a smaller board and label the missing seat (and the round it dropped out) in the handoff rather than silently omitting it.

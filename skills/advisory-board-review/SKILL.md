---
name: advisory-board-review
description: Run a reusable multi-model advisory board review using subscription-backed Claude Code, Codex, and Gemini CLIs. Use when the user asks for an advisory board, round table, Panely-style review, multi-provider adversarial plan review, architectural review before execution, Opus/GPT/Gemini review, or a consensus handoff from several frontier models.
---

# Advisory Board Review

## Core Defaults

- Use subscription CLIs by default, not provider API keys.
- Do not use OpenClaw.
- Run read-only unless the user explicitly asks for edits.
- Default rounds: 2.
- Default discussion: yes, cross-read summaries.
- Default final artifact: full handoff doc.
- Save artifacts in a timestamped output folder near the reviewed material when possible, or in `/tmp/advisory-board-review-*` if no project folder is clear.

## Upfront Choices

Before running, ask only for missing choices:

1. Source material: file(s), repo, URL, or goal to review.
2. Rounds: `1`, `2`, or `3`; default `2`.
3. Cross-reading: `none`, `summaries`, or `full`; default `summaries`.
4. Output: `quick verdict`, `full handoff`, or `implementation sequence`; default `full handoff`.

If the user says "use defaults", do not ask further.

## Model Lineup

Default target lineup:

- Claude seat: `claude-opus-4-8`, highest available reasoning or effort setting.
- Codex seat: `gpt-5.5`, `model_reasoning_effort="xhigh"` or the highest available Codex reasoning setting.
- Gemini seat: Google's latest frontier reasoning model available through the Gemini CLI, with `thinkingLevel: HIGH` or the highest available thinking setting.

At run time, verify the exact model names and reasoning flags with the installed CLIs or official docs before launching a large run. If a requested model is unavailable, report it and use the nearest available same-provider frontier/reasoning model only with a user-visible note.

Preflight:

- Verify Claude subscription auth is active.
- Verify Codex is using ChatGPT/subscription auth when available, not API-key-only auth.
- Verify Gemini auth and available model/config support.
- Do not print secrets, tokens, cookies, or private environment values.

## Seats

Default role emphasis:

- Claude: architecture, systems, and adversarial design review.
- Codex: repo-grounded implementation, migration, testing, and execution review.
- Gemini: product, operations, rollout, latency, evaluation, and user-workflow risk.

Each seat must still answer the full review brief, not only its emphasis.

## Round Protocol

Round 1 independent:

- Give each model the same source packet and role emphasis.
- Do not include other model opinions.
- Require verdict, strongest objections, revised sequence, invariants, risks, and evidence.

Round 2 rebuttal, default:

- Build a board packet from Round 1.
- If cross-reading is `summaries`, summarize each response with links or paths to full artifacts.
- If cross-reading is `full`, include full prior responses when token budget allows.
- Ask each model what others caught that it missed, what changed its view, what it still disputes, what should become consensus, and what remains unresolved.

Round 3 convergence, optional:

- Give each model the Round 2 packet.
- Ask for final consensus, hard dissent, and the smallest viable execution plan.

Final synthesis:

- Create the final answer or handoff after all rounds.
- Include consensus, dissent, revised plan, risks, invariants, evidence, and next actions.
- Clearly label model and round provenance.

## Artifact Standard

Create:

- `round-1/<seat>.md`
- `round-2/<seat>.md` when rounds >= 2
- `round-3/<seat>.md` when rounds >= 3
- `board-packet-round-2.md`
- `board-packet-round-3.md` when needed
- `final-consensus.md`
- optional `run-metadata.md` with commands, model names, auth/account status without secrets, timestamps, and source paths

Never store secrets. Redact keys, tokens, cookies, and private environment values.

## CLI Execution Notes

Prefer read-only modes and verify local CLI syntax before launching:

- Claude Code: use the installed CLI's strongest reasoning/effort setting and a read-only or plan-like permission mode when available.
- Codex: use `codex exec` with read-only sandboxing when available, and set reasoning effort to the highest supported value.
- Gemini: use a plan/read-only approval mode when available, and configure the latest frontier model with the highest supported thinking level.

For Gemini high thinking, prefer a temporary settings alias equivalent to:

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

Delete temporary settings after the run.

## Prompt Templates

Load `references/prompt-templates.md` when running a board review. Use the templates as the starting point, then adapt them to the user's source material, output type, and project constraints.

## When To Stop

Stop and ask or report if:

- the user has not provided source material and no obvious file or repo is inferable;
- a requested model or provider cannot authenticate;
- a command would need write access but the user requested review only;
- full cross-reading would exceed context, in which case fall back to summaries and say so.

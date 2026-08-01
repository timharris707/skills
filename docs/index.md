---
title: Skills
---

# Skills

A catalog of portable skills for AI agents. Each skill is a self-contained playbook — a `SKILL.md` any agent can read, plus the templates and scripts it needs — that turns a workflow you'd otherwise re-explain every session into something you install once and invoke by name.

The repository doubles as a Claude Code plugin marketplace, but nothing is locked to one runtime: provider-specific adapters live beside each skill, and the core instructions stay portable.

## The Catalog

| Skill | What it's for | Ships as |
| --- | --- | --- |
| [advisory-board](./advisory-board) | Convene a board of frontier AI models — Claude, Codex, Gemini, and Grok — that each review the same decision independently, debate across rounds, and hand back one clear recommendation. | Standalone plugin |
| [router](https://github.com/timharris707/skills/blob/main/skills/router/SKILL.md) | The team-workflow pack's entry point: names every pack skill and when to reach for it. | team-workflow pack |
| [setup](https://github.com/timharris707/skills/blob/main/skills/setup/SKILL.md) | Once-per-repo interview that binds the pack to your project — tracker, verify commands, who decides — and seeds the binding doc and templates. | team-workflow pack |
| [decision-map](https://github.com/timharris707/skills/blob/main/skills/decision-map/SKILL.md) | Chart genuinely foggy work — where open questions gate each other — as a decision map before anyone writes a build spec. | team-workflow pack |
| [prototype](https://github.com/timharris707/skills/blob/main/skills/prototype/SKILL.md) | Throwaway prototype code that answers a design question you can't settle by discussion; the verdict is the deliverable. | team-workflow pack |
| [research](https://github.com/timharris707/skills/blob/main/skills/research/SKILL.md) | Fire-and-report investigation against primary sources, ending in a cited findings file. | team-workflow pack |
| [handoff](https://github.com/timharris707/skills/blob/main/skills/handoff/SKILL.md) | Write a structured session handoff — at wrap-up or when context fills — so a fresh session resumes losslessly. | team-workflow pack |
| [orchestrate](https://github.com/timharris707/skills/blob/main/skills/orchestrate/SKILL.md) | Run one session as the orchestrator of parallel working lanes: route tracked items, audit results, own integration. | team-workflow pack |

## Advisory Board

**Get a room full of expert advisors for any big decision — before you commit.** Frontier models from Anthropic, OpenAI, Google, and xAI each examine the same thing — your plan, your draft, your decision — then debate it out loud and hand you one clear recommendation: what's solid, what's risky, and what to do next. Works for software, but also product, research, legal, business, and writing.

[**Read the full guide →**](./advisory-board) — or jump straight to [a real finished handoff](./sample-handoff.html) from another real run, *"Should I go full-time on my side project?"* (verdict: proceed with care, unanimous).

## Team-Workflow Pack

**A workflow for teams building with agents — without the collisions.** Seven skills that ship and version together: decide before you build (decision-map), prototype what discussion can't settle (prototype), investigate what sources can answer (research), hand sessions off losslessly (handoff), coordinate parallel lanes from one seat (orchestrate), bind it all to your repo once (setup), and orient any session with the router. Everything repo-specific lives in one binding doc; every skill defers judgment calls to **the decider** — the role your repo names, not a person the pack assumes.

Start with the [router](https://github.com/timharris707/skills/blob/main/skills/router/SKILL.md) to see the whole pack at a glance.

## Install

In Claude Code:

```text
/plugin marketplace add timharris707/skills
/plugin install advisory-board@skills
/plugin install team-workflow@skills
```

Or clone [the repository](https://github.com/timharris707/skills) and copy or symlink skill directories into wherever your runtime discovers skills — the README covers both paths.

## Repository Principles

- Keep skills readable and portable.
- Keep provider-specific configuration separate from the core skill.
- Avoid secrets and private account details.
- Make defaults explicit.
- Save reusable prompts and templates near the skill that uses them.

## Source

The source files live in the [`skills/`](https://github.com/timharris707/skills/tree/main/skills) directory of the repository.

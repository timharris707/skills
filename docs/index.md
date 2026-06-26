---
title: Skills
---

# Skills

Reusable AI workflow skills for the moments where one opinion isn't enough — reviewing, deciding, and pressure-testing the hard calls before you commit.

This repository is provider-agnostic. Individual skills may include runtime-specific adapter files, but the main skill instructions are written to stay portable.

## Available Skills

### [Advisory Board](./advisory-board)

**Get a room full of expert advisors for any big decision — before you commit.** Several leading AI models from Anthropic, OpenAI, and Google each examine the same thing — your plan, your draft, your decision — then debate it out loud and hand you one clear recommendation: what's solid, what's risky, and what to do next. Works for software, but also product, research, legal, business, and writing.

[**See a real board in action →**](./sample-handoff.html) — a finished handoff on *"Should I go full-time on my side project?"* (verdict: proceed with care, unanimous), or [read the full page](./advisory-board).

## Repository Principles

- Keep skills readable and portable.
- Keep provider-specific configuration separate from the core skill.
- Avoid secrets and private account details.
- Make defaults explicit.
- Save reusable prompts and templates near the skill that uses them.

## Source

The source files live in the [`skills/`](../skills/) directory.

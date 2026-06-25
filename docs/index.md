---
title: Skills
---

# Skills

Reusable AI workflow skills for planning, review, orchestration, and execution support.

This repository is provider-agnostic. Individual skills may include runtime-specific adapter files, but the main skill instructions are written to stay portable.

## Available Skills

### [Advisory Board Review](./advisory-board-review)

A multi-model adversarial review workflow for strengthening plans before execution. It is designed for architecture reviews, implementation sequencing, risk discovery, and consensus handoff creation.

## Repository Principles

- Keep skills readable and portable.
- Keep provider-specific configuration separate from the core skill.
- Avoid secrets and private account details.
- Make defaults explicit.
- Save reusable prompts and templates near the skill that uses them.

## Source

The source files live in the [`skills/`](../skills/) directory.

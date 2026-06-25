# Contributing

This is a personal skills repository. Keep additions portable and provider-agnostic unless a runtime adapter file is explicitly needed.

## Skill Structure

Use one directory per skill:

```text
skills/<skill-name>/
  SKILL.md
  references/
  agents/
```

`SKILL.md` should contain the core behavior and should be understandable without a specific provider runtime. Put longer reusable prompts, examples, or reference material in `references/`.

## Quality Bar

- Keep instructions concise and operational.
- Avoid storing secrets, account details, tokens, cookies, or private environment values.
- Prefer clear defaults over vague configuration.
- Document what the skill should do, when to use it, and when to stop.
- Keep provider-specific metadata in adapter files such as `agents/openai.yaml`.

## Validation

When a skill is Codex-compatible, validate it with the local skill validator before publishing changes.

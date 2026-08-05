# Skill mechanics — frontmatter, invocation, and catalog invariants

The packaging layer that sits under [SKILL.md](../SKILL.md)'s writing levers. Read this when the document you're writing is a **skill** in this catalog.

## Frontmatter

Two fields carry the whole contract:

```yaml
---
name: <kebab-case, matches the directory name>
description: <what it does — then when to reach for it>
---
```

`description` **is** the context pointer, and it is the only part of a skill loaded into every session. Everything in SKILL.md's "Context pointers" section applies to it with full force. The house shape is one sentence of identity followed by the branches:

> Write and prune documents an agent consumes — a SKILL.md, an AGENTS.md or CLAUDE.md, a reference file reached by a pointer. **Use when** authoring or revising a skill, editing standing agent instructions, or diagnosing why a document fires unreliably.

The `Use when` clause is where the branches live. One trigger per branch; a run of synonyms is one branch written three times.

Optional fields, used sparingly:

- `disable-model-invocation: true` — the skill fires only when a human names it. Correct for skills whose whole value is a deliberate human act (a live interview, a wrap-up). Wrong for skills the agent should notice it needs.
- `argument-hint` — the placeholder shown after the skill name for human-invoked skills.

## Choosing the invocation mode

| The skill should fire… | Mode |
| --- | --- |
| whenever the agent recognizes the situation | model-invocable (default) — spend the description on branch triggers |
| only when a human decides it is time | `disable-model-invocation: true` — the description is a menu entry, and can be short |
| both, through a thin human-facing alias | two skills: the reference skill model-invocable, plus a one-line invoker |

The third row is a real pattern, not a workaround: a reference skill holds the process and a short human-invoked skill exists purely so a person can name it. Keep the process in exactly one of them — the alias points, it does not restate.

## Directory shape

```text
skills/<skill-name>/
  SKILL.md          the process and the top of the ladder
  references/       disclosed reference, reached by pointers from SKILL.md
  scripts/          optional helpers — Python 3 standard library only
  agents/           provider adapters, e.g. openai.yaml
```

A skill must work with `scripts/` absent. Helpers accelerate; they never gate.

## Catalog invariants (CI enforces these)

`scripts/check_router_freshness.py` runs on every PR and fails the build unless all four hold. Adding a skill means touching more than its own directory:

1. **`.claude-plugin/marketplace.json` claims the directory.** Every `skills/<name>` is claimed by exactly one plugin, and every claimed path contains a `SKILL.md`. A skill claimed twice fails; a skill claimed zero times fails.
2. **`skills/team-workflow/` is the one exception** — it is the pack's changelog home and deliberately carries no `SKILL.md`.
3. **The router names every pack skill.** A skill in the `team-workflow` plugin must appear in [`skills/router/SKILL.md`](../../router/SKILL.md) as a `../<name>/` link. The router itself is exempt.
4. **Every relative `.md` link in the router resolves.**

Run it locally before pushing:

```bash
python3 scripts/check_router_freshness.py
```

The invariants exist because routers rot exactly when skills are added or renamed. They are structural checks, not style checks — a fresh router is enforced, a good one is still your job.

## Pack membership

Landing a skill in the `team-workflow` pack is a scoping claim: the pack covers **tracked, multi-session, agent-assisted development** — planning, research, prototyping, handoff, orchestration, tracker hygiene. It deliberately ships no review checklist and no build-stage discipline.

A skill outside that territory ships as its own plugin instead, the way `advisory-board` and `writing-for-agents` do. Independent installability is the test: if someone would sensibly want this skill without the pack, it is its own plugin.

## Versioning

Pack skills version together under the `team-workflow/vX.Y.Z` tag; standalone plugins carry their own. Bump the version in `marketplace.json` in the same PR that adds the skill, and keep the plugin `description` honest about what it now contains — a pack description that still says "seven skills" after the eighth lands is stale documentation shipped to every installer.

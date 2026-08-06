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

## Buckets

Every skill lives in a **bucket** — a directory under `skills/`, declared in [`skills/buckets.json`](../../../buckets.json). The bucket does two jobs at once: it says what the skill is *for*, and whether it *ships*.

```text
skills/
  buckets.json      the declaration — id, display name, promoted, blurb
  orient/           promoted ─┐
  decide/           promoted  │  ships in the marketplace,
  investigate/      promoted  │  and appears on clickai.dev
  run/              promoted  │
  author/           promoted ─┘
  in-progress/      unpromoted ─┐
  misc/             unpromoted  │  ships nowhere, shows nowhere
  deprecated/       unpromoted ─┘

skills/<bucket>/<skill-name>/
  SKILL.md          the process and the top of the ladder
  references/       disclosed reference, reached by pointers from SKILL.md
  scripts/          optional helpers — Python 3 standard library only
  agents/           provider adapters, e.g. openai.yaml
```

A skill must work with `scripts/` absent. Helpers accelerate; they never gate.

**Promotion is the point.** A half-built skill goes in `in-progress/`, where it is neither installable nor listed — no half-wired entry in the marketplace, no placeholder on the site, and nothing deleted. `git mv` it into a promoted bucket when it earns its place. The promoted buckets are also the site's regions, read straight from `buckets.json`, so a skill's category is simply the directory it sits in.

Cross-skill links follow from the layout: same bucket is `../<name>/SKILL.md`, a different bucket is `../../<bucket>/<name>/SKILL.md`.

## Running on Codex as well as Claude

A skill is a `SKILL.md`, and both runtimes read it directly — so the *instructions* are already portable. What differs is packaging, and it takes two files plus one per skill:

| | Claude Code | Codex |
| --- | --- | --- |
| Marketplace | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` |
| Plugin manifest | in the marketplace entry | `.codex-plugin/plugin.json` |
| Per-skill metadata | frontmatter only | frontmatter **plus** `agents/openai.yaml` |
| Plugins per repo | many | **one per plugin root** |

The **one-plugin-per-root** rule is the only real asymmetry: a Codex plugin root is the directory holding `.codex-plugin/`, and skill paths are relative to it, so a repo root can host exactly one Codex plugin. This catalog therefore ships three Claude plugins (`advisory-board`, `team-workflow`, `writing-for-agents`) and one Codex plugin (`clickai-skills`) containing the same twelve skills. Different shape, identical contents — and CI enforces the "identical contents" half.

**`skills` in `.codex-plugin/plugin.json` accepts an array of paths, and Codex exposes only those paths.** This is worth stating plainly because the widely-cited constraint says otherwise — that Codex accepts only a single path string and discovers `SKILL.md` recursively beneath it, which would make a curated subset impossible in a bucketed repo. Verified against **Codex CLI 0.146.0** with a control: a scratch plugin containing one promoted and one unpromoted skill, both carrying the same marker string.

| `skills` in the manifest | Codex exposed |
| --- | --- |
| `["./skills/decide/alpha"]` | `probe:alpha` only |
| `["./skills/in-progress/draft"]` | `probe:draft` only |

Inverting the manifest inverted the result, so the array is authoritative rather than incidental. The unlisted skill is still *copied* into the plugin cache — it is simply never surfaced. Re-run that probe before trusting this on a newer CLI; provider manifests move.

The per-skill adapter is small, and the short description is what a human reads in Codex's picker:

```yaml
interface:
  display_name: "Grilling"
  short_description: "Stress-test a plan one round of questions at a time"
```

## Catalog invariants (CI enforces these)

`scripts/check_router_freshness.py` runs on every PR and fails the build unless all six hold. Adding a skill means touching more than its own directory:

1. **Every directory under `skills/` is a declared bucket**, and every declared bucket exists.
2. **`.claude-plugin/marketplace.json` claims the directory.** Every claimed `skills/<bucket>/<name>` contains a `SKILL.md`, and no path is claimed by two plugins.
3. **Promotion holds both ways.** Every skill in a promoted bucket is claimed by exactly one plugin; no skill in an unpromoted bucket is claimed by any. This is what makes parking a skill a single `git mv` plus an unclaim — CI names both edits if you forget one.
4. **Claude and Codex ship the same set.** `.codex-plugin/plugin.json` lists exactly what the Claude marketplace claims, and every promoted skill has an `agents/openai.yaml` carrying `display_name` and `short_description`. A skill that exists on one runtime and silently doesn't on the other is the failure this prevents.
5. **The router names every pack skill.** A skill in the `team-workflow` plugin must appear in [`skills/orient/router/SKILL.md`](../../../orient/router/SKILL.md). The router itself is exempt.
6. **Every relative `.md` link in the router resolves.**

Run it locally before pushing:

```bash
python3 scripts/check_router_freshness.py
```

The invariants exist because the catalog rots exactly when skills are added, renamed, or moved between buckets. They are structural checks, not style checks — a fresh router is enforced, a good one is still your job.

## Pack membership

Landing a skill in the `team-workflow` pack is a scoping claim: the pack covers **tracked, multi-session, agent-assisted development** — planning, research, prototyping, handoff, orchestration, tracker hygiene. It deliberately ships no review checklist and no build-stage discipline.

A skill outside that territory ships as its own plugin instead, the way `advisory-board` and `writing-for-agents` do. Independent installability is the test: if someone would sensibly want this skill without the pack, it is its own plugin.

## Versioning

Pack skills version together under the `team-workflow/vX.Y.Z` tag; standalone plugins carry their own. Bump the version in `marketplace.json` in the same PR that adds the skill, and keep the plugin `description` honest about what it now contains — a pack description that still says "seven skills" after the eighth lands is stale documentation shipped to every installer.

A tag's release notes come from that name's `CHANGELOG.md`, resolved rather than hard-coded: `skills/<bucket>/<skill>/CHANGELOG.md` for a standalone skill, `packs/<pack>/CHANGELOG.md` for a pack. Moving a skill between buckets therefore never breaks its release, and pack changelogs live outside `skills/` because a pack is not a skill.

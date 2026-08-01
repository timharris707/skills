# Skills

**Portable skills for AI agents.** Each skill is a self-contained playbook — a `SKILL.md` any agent can read, plus the templates and scripts it needs — that turns a workflow you'd otherwise re-explain every session into something you install once and invoke by name.

This repo is a [Claude Code plugin marketplace](./.claude-plugin/marketplace.json), but nothing here is locked to one runtime: provider-specific adapters live beside each skill, and the core instructions stay readable and portable.

## The Catalog

| Skill | What it's for | Ships as |
| --- | --- | --- |
| [advisory-board](./skills/advisory-board/) | Convene a board of frontier AI models — Claude, Codex, Gemini, and Grok — that each review the same decision independently, debate across rounds, and hand back one clear recommendation. | Standalone plugin |
| [router](./skills/router/SKILL.md) | The team-workflow pack's entry point: names every pack skill and when to reach for it. Start here to orient a new session or repo. | team-workflow pack |
| [setup](./skills/setup/SKILL.md) | Once-per-repo interview that binds the pack to your project — tracker, verify commands, who decides — and seeds the binding doc and templates. | team-workflow pack |
| [decision-map](./skills/decision-map/SKILL.md) | Chart genuinely foggy work — where open questions gate each other — as a decision map before anyone writes a build spec. | team-workflow pack |
| [prototype](./skills/prototype/SKILL.md) | Throwaway prototype code that answers a design question you can't settle by discussion; the verdict is the deliverable, and the winner gets rebuilt properly. | team-workflow pack |
| [research](./skills/research/SKILL.md) | Fire-and-report investigation against primary sources, ending in a cited findings file — and a questionnaire when the missing facts are human-held. | team-workflow pack |

The five **team-workflow** skills ship and version together as one pack — install them as a set and they cover the full loop of tracked, multi-session, agent-assisted development. **advisory-board** stands alone and works anywhere a hard decision does.

## Install (Claude Code)

Add the marketplace once, then install whichever plugins you want:

```text
/plugin marketplace add timharris707/skills
/plugin install advisory-board@skills    # the multi-model advisory board
/plugin install team-workflow@skills     # all five pack skills as one plugin
```

### Install without the plugin system

Clone the repo and copy or symlink skill directories into wherever your runtime discovers skills — for Claude Code, the personal skills folder:

```bash
git clone https://github.com/timharris707/skills.git agent-skills
for s in advisory-board router setup decision-map prototype research; do
  ln -s "$(pwd)/agent-skills/skills/$s" ~/.claude/skills/$s
done
```

Symlinks track updates on `git pull`; copies pin what you have. Other agent runtimes can read each `SKILL.md` directly — advisory-board also ships a Codex adapter ([`agents/openai.yaml`](./skills/advisory-board/agents/openai.yaml)).

## The Skills, Briefly

### Advisory Board

Bring the board whatever you're weighing — a plan, a draft, a contract, a design, a real-life choice — and several leading AI models each examine it independently, then read each other's notes, argue out the disagreements, and hand you back one clear answer you read like a memo. Read-only by default; you approve exactly what leaves your machine, or run a fully local board. Point it at a codebase and advisors cite `path:line` evidence; every run also emits a machine-readable `verdict.json` you can gate CI on.

**[Full tour, real example runs, and engineer features →](./skills/advisory-board/README.md)** · [GitHub Pages guide](https://timharris707.github.io/skills/advisory-board)

### Team-Workflow Pack

A portable discipline for teams building with agents — without the collisions. Decide before you build (`decision-map`), prototype what discussion can't settle (`prototype`), investigate what sources can answer (`research`), and keep parallel sessions from stepping on each other with the tracker recipes `setup` binds to your repo. Everything repo-specific lives in one binding doc; every skill defers judgment calls to **the decider** — the role your repo names, not a person the pack assumes.

First run in a repo: install the pack, then run `setup`. When unsure which skill applies, the [router](./skills/router/SKILL.md) is the map.

The pack versions **as one unit**: a single tag `team-workflow/vX.Y.Z`, a single [changelog](./skills/team-workflow/CHANGELOG.md), and a matching plugin version — consuming repos pin one pack version and upgrade deliberately.

## Repository Layout

```text
skills/
  advisory-board/    # standalone: SKILL.md, references/, scripts/, tests/, agents/
  router/            # team-workflow pack: entry point
  setup/             # team-workflow pack: binding interview + seeded templates
  decision-map/      # team-workflow pack
  prototype/         # team-workflow pack
  research/          # team-workflow pack
  team-workflow/     # the pack's single CHANGELOG.md (pack-scoped tags resolve here)
.claude-plugin/
  marketplace.json   # plugin marketplace: advisory-board + team-workflow
scripts/
  check_router_freshness.py   # CI: router roster and marketplace stay in sync with skills/
docs/                # GitHub Pages site
examples/            # real advisory-board runs you can browse
```

Skill directories are stable, versioned paths — releases, the marketplace manifest, and CI all key off `skills/<skill-name>/`.

## Docs, Releases, Contributing

- **Docs:** the GitHub Pages site at [timharris707.github.io/skills](https://timharris707.github.io/skills) covers the catalog; each skill's `SKILL.md` is the source of truth.
- **Releases:** standalone skills tag as `<skill>/vX.Y.Z`, the pack as `team-workflow/vX.Y.Z`; each release's notes come from the relevant `CHANGELOG.md`. See [`RELEASING.md`](./RELEASING.md).
- **Contributing:** structure, quality bar, and validation in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## License

Released under the [MIT License](./LICENSE.md) — free to use, copy, modify, and adapt with attribution.

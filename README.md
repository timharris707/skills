# Skills

**Portable skills for AI agents.** Each skill is a self-contained playbook — a `SKILL.md` any agent can read, plus the templates and scripts it needs — that turns a workflow you'd otherwise re-explain every session into something you install once and invoke by name.

**Runs natively on Claude Code and Codex** — the same `SKILL.md`, installed one line either way, with no port and no second-class path. This repo is both a [Claude Code plugin marketplace](./.claude-plugin/marketplace.json) and a [Codex plugin](./.codex-plugin/plugin.json); CI fails the build if the two would ship a different set of skills. Any other harness can read each `SKILL.md` directly.

## The Catalog

| Skill | What it's for | Ships as |
| --- | --- | --- |
| [advisory-board](./skills/decide/advisory-board/) | Convene a board of frontier AI models — Claude, Codex, Gemini, and Grok — that each review the same decision independently, debate across rounds, and hand back one clear recommendation. | Standalone plugin |
| [router](./skills/orient/router/SKILL.md) | The team-workflow pack's entry point: names every pack skill and when to reach for it. Start here to orient a new session or repo. | team-workflow pack |
| [setup](./skills/orient/setup/SKILL.md) | Once-per-repo interview that binds the pack to your project — tracker, verify commands, who decides — and seeds the binding doc and templates. | team-workflow pack |
| [grilling](./skills/decide/grilling/SKILL.md) | Interview the decider relentlessly over a design tree, in rounds, until nothing load-bearing is still assumed. Facts are the agent's job; decisions are the decider's. | team-workflow pack |
| [decision-map](./skills/decide/decision-map/SKILL.md) | Chart genuinely foggy work — where open questions gate each other — as a decision map before anyone writes a build spec. | team-workflow pack |
| [prototype](./skills/investigate/prototype/SKILL.md) | Throwaway prototype code that answers a design question you can't settle by discussion; the verdict is the deliverable, and the winner gets rebuilt properly. | team-workflow pack |
| [research](./skills/investigate/research/SKILL.md) | Fire-and-report investigation against primary sources, ending in a cited findings file — and a questionnaire when the missing facts are human-held. | team-workflow pack |
| [to-tickets](./skills/run/to-tickets/SKILL.md) | Turn a plan, a closed map, or a pressure-tested conversation into tracer-bullet work items with their blocking edges wired. Files and labels; never claims, never decides. | team-workflow pack |
| [wizard](./skills/run/wizard/SKILL.md) | Generate an interactive bash wizard for the steps only a human can take — vendor dashboards, DNS panels, credentials that must not enter an agent's context. | team-workflow pack |
| [handoff](./skills/run/handoff/SKILL.md) | Write a structured session handoff — at wrap-up or when context fills — so a fresh session resumes losslessly. | team-workflow pack |
| [orchestrate](./skills/run/orchestrate/SKILL.md) | Run one session as the orchestrator of parallel working lanes: route tracked items, audit results, own integration — never implement. | team-workflow pack |
| [writing-for-agents](./skills/author/writing-for-agents/SKILL.md) | Write and prune documents an agent consumes — context pointers, the two loads, the information hierarchy, leading words, and the no-op test. | Standalone plugin |

The ten **team-workflow** skills ship and version together as one pack — install them as a set and they cover the full loop of tracked, multi-session, agent-assisted development. **advisory-board** stands alone and works anywhere a hard decision does; **writing-for-agents** stands alone as the standard the rest of this catalog is written against.

## Install

Add the marketplace once, then install whichever plugins you want.

### Claude Code

```text
/plugin marketplace add timharris707/skills
/plugin install advisory-board@skills      # the multi-model advisory board
/plugin install team-workflow@skills       # all ten pack skills as one plugin
/plugin install writing-for-agents@skills  # the skill-authoring reference
```

### Codex

The same twelve skills, native. Codex allows one plugin per repository root, so the
whole catalog arrives as a single plugin rather than three:

```bash
codex plugin marketplace add timharris707/skills
codex plugin add clickai-skills@clickai
```

Each skill carries a Codex adapter at `agents/openai.yaml` supplying the display
name and one-line description Codex shows in its picker. CI enforces that Claude
and Codex ship exactly the same set, so a skill can never exist on one runtime
and silently not on the other.

### Any other runtime

Clone the repo and copy or symlink skill directories into wherever your runtime discovers skills — for Claude Code, the personal skills folder:

```bash
git clone https://github.com/timharris707/skills.git agent-skills
# Skills live in buckets; this links every skill in a promoted bucket by name.
for d in agent-skills/skills/*/*/; do
  [ -f "$d/SKILL.md" ] || continue
  ln -s "$(pwd)/$d" ~/.claude/skills/"$(basename "$d")"
done
```

Symlinks track updates on `git pull`; copies pin what you have. Other agent runtimes can read each `SKILL.md` directly — the instructions are the portable part, and every skill also ships a Codex adapter at `agents/openai.yaml`.

## The Skills, Briefly

### Advisory Board

Bring the board whatever you're weighing — a plan, a draft, a contract, a design, a real-life choice — and several leading AI models each examine it independently, then read each other's notes, argue out the disagreements, and hand you back one clear answer you read like a memo. Read-only by default; you approve exactly what leaves your machine, or run a fully local board. Point it at a codebase and advisors cite `path:line` evidence; every run also emits a machine-readable `verdict.json` you can gate CI on.

**[Full tour, real example runs, and engineer features →](./skills/decide/advisory-board/README.md)** · [GitHub Pages guide](https://timharris707.github.io/skills/advisory-board)

### Team-Workflow Pack

A portable discipline for teams building with agents — without the collisions. Decide before you build (`decision-map`), prototype what discussion can't settle (`prototype`), investigate what sources can answer (`research`), hand sessions off losslessly (`handoff`), coordinate parallel lanes from one seat (`orchestrate`), and keep sessions from stepping on each other with the tracker recipes `setup` binds to your repo. Everything repo-specific lives in one binding doc; every skill defers judgment calls to **the decider** — the role your repo names, not a person the pack assumes.

The pack deliberately covers the stages **upstream and around** building: planning, research, prototyping, handoff, orchestration, tracker hygiene. It ships no review-response system — repos that already run one (a review skill with its own decision wiki) keep it, and the pack defers to it entirely.

First run in a repo: install the pack, then run `setup`. When unsure which skill applies, the [router](./skills/orient/router/SKILL.md) is the map.

The pack versions **as one unit**: a single tag `team-workflow/vX.Y.Z`, a single [changelog](./packs/team-workflow/CHANGELOG.md), and a matching plugin version — consuming repos pin one pack version and upgrade deliberately.

## Repository Layout

Every skill lives in a **bucket** — a directory under `skills/` declared in [`skills/buckets.json`](./skills/buckets.json). A bucket says both what a skill is *for* and whether it *ships*.

```text
skills/
  buckets.json       # the declaration: id, name, promoted, blurb
  orient/            # PROMOTED  router, setup
  decide/            # PROMOTED  grilling, decision-map, advisory-board
  investigate/       # PROMOTED  research, prototype
  run/               # PROMOTED  to-tickets, wizard, orchestrate, handoff
  author/            # PROMOTED  writing-for-agents
  in-progress/       # unpromoted: half-built, kept but not shipped
  misc/              # unpromoted: one-offs too repo-specific to publish
  deprecated/        # unpromoted: superseded, kept until nothing points at them
packs/
  team-workflow/     # the pack's single CHANGELOG.md (pack-scoped tags resolve here)
.claude-plugin/
  marketplace.json   # plugin marketplace: advisory-board + team-workflow + writing-for-agents
scripts/
  check_router_freshness.py   # CI: buckets, promotion, marketplace, and router stay in sync
site/                # the clickai.dev catalog, generated from these SKILL.md files
docs/                # GitHub Pages site
examples/            # real advisory-board runs you can browse
```

**Only promoted buckets ship.** Nothing in `in-progress/`, `misc/`, or `deprecated/` appears in the marketplace or on the site — so parking a half-finished skill is one `git mv` and an unclaim, with nothing deleted and no placeholder left in the catalog. CI enforces the boundary in both directions: a skill in a promoted bucket must be claimed by exactly one plugin, and a skill in an unpromoted bucket must be claimed by none.

The promoted buckets are also the site's regions, read straight from `buckets.json` — a skill's category is just the directory it sits in.

## Docs, Releases, Contributing

- **Docs:** the GitHub Pages site at [timharris707.github.io/skills](https://timharris707.github.io/skills) covers the catalog; each skill's `SKILL.md` is the source of truth.
- **Releases:** standalone skills tag as `<skill>/vX.Y.Z`, the pack as `team-workflow/vX.Y.Z`; each release's notes come from the relevant `CHANGELOG.md`. See [`RELEASING.md`](./RELEASING.md).
- **Contributing:** structure, quality bar, and validation in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## License

Released under the [MIT License](./LICENSE.md) — free to use, copy, modify, and adapt with attribution.

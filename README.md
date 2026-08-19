# Skills

I don't write code. I direct agents. This repo is the method: every workflow I used to re-explain to an agent each session, written down once as a `SKILL.md` (a plain-markdown playbook the agent reads on its own), installed in one line and versioned like software.

If you just want to install something, jump to [Installation](#installation-30-second-setup). If you want to know why any of this exists, read on; it's short.

## Why these skills exist

Every skill here started the same way: an agent failed me in a pattern, twice, and I got tired of re-explaining the fix. These are the four failures that cost me the most.

### The agent built the wrong thing

Nobody describes what they want completely, me included. I'd ask for a change, the agent would fill every unstated gap with a guess, and I'd find the guesses three files deep in the diff.

The fix is [grilling](./skills/decide/grilling/SKILL.md): the agent interviews me about the plan, in rounds, until nothing load-bearing is still assumed. Facts are the agent's job to go fetch; decisions stay mine. I run it before any change big enough to argue about, which turns out to be most of them.

### A hard decision got one model's opinion

Some calls are expensive to get wrong: an architecture, a contract, a launch plan. Settling one with whichever model happened to be in the chair that session never sat right with me.

The fix is [advisory-board](./skills/decide/advisory-board/): Claude, Codex, Gemini, and Grok each review the same decision independently, read each other's notes, argue out the disagreements, and hand back one recommendation you read like a memo. It's read-only by default and you approve exactly what leaves your machine, or you run a fully local board. Point it at a codebase and the advisors cite `path:line` evidence; every run also emits a machine-readable `verdict.json` you can gate CI on. There's a [full tour with real example runs](./skills/decide/advisory-board/README.md), and the runs themselves are in [examples/](./examples/).

### Everything the agent writes sounds like AI

The em dashes. The "not just X, but Y". The victory lap at the end of every reply. Read enough agent prose in a day and the tells start to grate.

The fix is [plainspoken](./skills/author/plainspoken/SKILL.md), which is always on once installed: plain words, concrete claims, no tells, in everything the agent emits, commit messages included. For pages a stranger will read, [writing-for-humans](./skills/author/writing-for-humans/SKILL.md) adds what clean prose alone can't: structure, warmth, an admitted limit or two. And when a message has already failed to land, [huh](./skills/author/huh/SKILL.md) translates it.

### The work outgrew one session

Context fills mid-task and the next session rebuilds understanding from scratch. Or two sessions touch the same repo at once and collide.

The fix is the **team-workflow** pack: [handoff](./skills/run/handoff/SKILL.md) writes a snapshot a fresh session resumes from losslessly, [orchestrate](./skills/run/orchestrate/SKILL.md) runs one session as the coordinator of parallel lanes, and [setup](./skills/orient/setup/SKILL.md) binds the whole discipline to your repo in one interview. More on who the pack fits, and who it doesn't, in [Start with these](#start-with-these).

## Installation (30-second setup)

One marketplace, native on two harnesses. The same `SKILL.md` runs on Claude Code and Codex with no port and no second-class path: this repo is both a [Claude Code plugin marketplace](./.claude-plugin/marketplace.json) and a [Codex plugin](./.codex-plugin/plugin.json), and CI fails the build if the two would ship a different set of skills.

<details>
<summary><strong>Claude Code</strong></summary>

Add the marketplace once, then install whichever plugins you want:

```text
/plugin marketplace add timharris707/skills
/plugin install advisory-board@skills      # the multi-model advisory board
/plugin install team-workflow@skills       # every pack skill as one plugin
/plugin install ingest@skills              # media → evidence packet + routing
/plugin install writing-for-agents@skills  # the skill-authoring reference
/plugin install writing-for-humans@skills  # the human-facing copy reference
/plugin install plainspoken@skills         # the always-on plain-writing voice rule
/plugin install huh@skills                 # decode a message that didn't land
/plugin install blast-radius@skills        # prove a change safe before it merges
```

You don't need all of them. [Start with these](#start-with-these) is my short list; [the catalog](#the-catalog) is the full menu.

</details>

<details>
<summary><strong>Codex</strong></summary>

Every skill in the catalog below, native. Codex allows one plugin per repository
root, so the whole catalog arrives as a single plugin rather than one per skill:

```bash
codex plugin marketplace add timharris707/skills
codex plugin add clickai-skills@clickai
```

Each skill carries a Codex adapter at `agents/openai.yaml` supplying the display
name and one-line description Codex shows in its picker. CI enforces that Claude
and Codex ship exactly the same set, so a skill can never exist on one runtime
and silently not on the other.

</details>

<details>
<summary><strong>Any other runtime, or tinkerers</strong></summary>

Clone the repo and copy or symlink skill directories into wherever your runtime discovers skills. For Claude Code, that's the personal skills folder:

```bash
git clone https://github.com/timharris707/skills.git agent-skills
# Skills live in buckets; this links every skill in a promoted bucket by name.
python3 -c "import json; [print(b['id']) for b in json.load(open('agent-skills/skills/buckets.json'))['buckets'] if b['promoted']]" |
while read -r bucket; do
  for d in agent-skills/skills/"$bucket"/*/; do
    [ -f "$d/SKILL.md" ] || continue
    ln -s "$(pwd)/$d" ~/.claude/skills/"$(basename "$d")"
  done
done
```

Symlinks track updates on `git pull`; copies pin what you have, and they're yours to edit. The instructions are the portable part: any runtime that can read markdown can read a `SKILL.md`, and every skill also ships a Codex adapter at `agents/openai.yaml`.

</details>

## Start with these

Four entry points, in the order I'd try them:

- **[grilling](./skills/decide/grilling/SKILL.md)**, before your next change big enough to argue about. Alignment first is the cheapest fix in this repo.
- **[advisory-board](./skills/decide/advisory-board/)**, the next time a decision is expensive to get wrong. It stands alone and works anywhere a hard decision does; there's also a [GitHub Pages guide](https://timharris707.github.io/skills/advisory-board).
- **[plainspoken](./skills/author/plainspoken/SKILL.md)**, installed once and left on. You stop noticing it, which is the point.
- **The team-workflow pack**, when you want the whole discipline rather than single skills.

The pack is built for a solo engineer or founder orchestrating agent-assisted work end to end: deciding before building ([decision-map](./skills/decide/decision-map/SKILL.md)), prototyping what discussion can't settle ([prototype](./skills/investigate/prototype/SKILL.md)), investigating what sources can answer ([research](./skills/investigate/research/SKILL.md)), handing sessions off, coordinating parallel lanes from one seat, and keeping sessions out of each other's way with the tracker recipes [setup](./skills/orient/setup/SKILL.md) binds to your repo. Teams with their own established process may prefer the standalone skills. Everything repo-specific lives in one binding doc, and every skill defers judgment calls to **the decider**: the role your repo names at setup, not a person the pack assumes.

The pack deliberately covers the stages upstream and around building: planning, research, prototyping, handoff, orchestration, tracker hygiene. It ships no review-response system; repos that already run one keep it, and the pack defers to it entirely.

First run in a repo: install the pack, then run `setup`. When you're unsure which skill applies, the [router](./skills/orient/router/SKILL.md) is the map. The pack versions as one unit: a single tag `team-workflow/vX.Y.Z`, a single [changelog](./packs/team-workflow/CHANGELOG.md), and a matching plugin version, so consuming repos pin one pack version and upgrade deliberately.

## The catalog

Every promoted skill, one section per bucket (a bucket is the directory a skill lives in; see [Repository layout](#repository-layout)). "Ships as" says whether a skill arrives with the team-workflow pack or as its own plugin. "Invocation" says who triggers it: every skill here currently fires itself, meaning the agent reaches for it when the task fits, and you can always ask for one by name.

### Orient

Bind the discipline to a repo, and find your way around it.

| Skill | What it's for | Ships as | Invocation |
| --- | --- | --- | --- |
| [router](./skills/orient/router/SKILL.md) | The pack's entry point: names every pack skill and when to reach for it. | team-workflow pack | fires itself |
| [setup](./skills/orient/setup/SKILL.md) | Once-per-repo interview that binds the pack to your project and seeds the binding doc. | team-workflow pack | fires itself |
| [domain-memory](./skills/orient/domain-memory/SKILL.md) | Per-repo glossary and decision records, written as side effects and read at session start. | team-workflow pack | fires itself |

### Decide

Settle what is still open before anyone writes a line of it.

| Skill | What it's for | Ships as | Invocation |
| --- | --- | --- | --- |
| [grilling](./skills/decide/grilling/SKILL.md) | Interviews the decider in rounds until nothing load-bearing is still assumed. | team-workflow pack | fires itself |
| [decision-map](./skills/decide/decision-map/SKILL.md) | Charts genuinely foggy work as a map of gating questions before anyone writes a build spec. | team-workflow pack | fires itself |
| [advisory-board](./skills/decide/advisory-board/) | Puts one decision to Claude, Codex, Gemini, and Grok; they debate and return one recommendation. | Standalone plugin | fires itself |

### Investigate

Answer what discussion cannot, from sources or from running code.

| Skill | What it's for | Ships as | Invocation |
| --- | --- | --- | --- |
| [research](./skills/investigate/research/SKILL.md) | Fire-and-report investigation of primary sources, ending in a cited findings file. | team-workflow pack | fires itself |
| [prototype](./skills/investigate/prototype/SKILL.md) | Throwaway code that settles a design question; the verdict is the deliverable. | team-workflow pack | fires itself |
| [codebase-review](./skills/investigate/codebase-review/SKILL.md) | Lens-named finders hunt structural friction; a skeptic kills unproven candidates. | team-workflow pack | fires itself |
| [ingest](./skills/investigate/ingest/SKILL.md) | Turns a video, recording, or media URL into an evidence packet: transcript, frames, manifest. | Standalone plugin | fires itself |

### Run

Get decided work onto the board, through the lanes, and handed on.

| Skill | What it's for | Ships as | Invocation |
| --- | --- | --- | --- |
| [to-tickets](./skills/run/to-tickets/SKILL.md) | Turns a plan or closed map into tracer-bullet work items with blocking edges wired. | team-workflow pack | fires itself |
| [wizard](./skills/run/wizard/SKILL.md) | Generates an interactive bash wizard for the steps only a human can take. | team-workflow pack | fires itself |
| [handoff](./skills/run/handoff/SKILL.md) | Writes a structured session handoff so a fresh session resumes losslessly. | team-workflow pack | fires itself |
| [orchestrate](./skills/run/orchestrate/SKILL.md) | Runs one session as the orchestrator of parallel lanes: route, audit, integrate, never implement. | team-workflow pack | fires itself |
| [adversarial-review](./skills/run/adversarial-review/SKILL.md) | Breaks the change before it ships: isolated finders, a skeptic pass, a gate only confirmed blockers hold. | team-workflow pack | fires itself |
| [diagnose](./skills/run/diagnose/SKILL.md) | The disciplined bug loop; no fix ships without its cause named in one plain sentence, with evidence. | team-workflow pack | fires itself |
| [implement](./skills/run/implement/SKILL.md) | How a lane builds an item: seam-scoped test-first, a green checkpoint commit per slice. | team-workflow pack | fires itself |
| [blast-radius](./skills/run/blast-radius/SKILL.md) | Finds what a change breaks somewhere else, past where grep stops, and proves the safety claim by running real code. | Standalone plugin | fires itself |

### Author

Standards for writing: documents agents consume, and pages humans read.

| Skill | What it's for | Ships as | Invocation |
| --- | --- | --- | --- |
| [writing-for-agents](./skills/author/writing-for-agents/SKILL.md) | The standard for documents agents consume: pointers, the two loads, the no-op test. | Standalone plugin | fires itself |
| [writing-for-humans](./skills/author/writing-for-humans/SKILL.md) | The standard for pages humans read: guide structure, warmth moves, the AI-tell scrub. | Standalone plugin | fires itself |
| [plainspoken](./skills/author/plainspoken/SKILL.md) | Plain words and no AI tells in everything the agent emits, commit messages included. | Standalone plugin | fires itself |
| [huh](./skills/author/huh/SKILL.md) | Decodes a message that didn't land: plain restatement, shorthand expanded, claims flagged. | Standalone plugin | fires itself |

## Repository layout

Every skill lives in a **bucket**, a directory under `skills/` declared in [`skills/buckets.json`](./skills/buckets.json). A bucket says both what a skill is *for* and whether it *ships*.

```text
skills/
  buckets.json       # the declaration: id, name, promoted, blurb
  orient/            # PROMOTED  router, setup, domain-memory
  decide/            # PROMOTED  grilling, decision-map, advisory-board
  investigate/       # PROMOTED  research, prototype, codebase-review, ingest
  run/               # PROMOTED  to-tickets, wizard, handoff, orchestrate, adversarial-review, diagnose, implement, blast-radius
  author/            # PROMOTED  writing-for-agents, writing-for-humans, plainspoken, huh
  in-progress/       # unpromoted: half-built, kept but not shipped
  misc/              # unpromoted: one-offs too repo-specific to publish
  deprecated/        # unpromoted: superseded, kept until nothing points at them
packs/
  team-workflow/     # the pack's single CHANGELOG.md (pack-scoped tags resolve here)
.claude-plugin/
  marketplace.json   # plugin marketplace: one entry per plugin, the pack plus each standalone skill
scripts/
  check_router_freshness.py       # CI: buckets, promotion, marketplace, and router stay in sync
  check_invocation_freshness.py   # CI: the catalog tables above and the site's invocation map stay in sync
site/                # the clickai.dev catalog, generated from these SKILL.md files
docs/                # GitHub Pages site
examples/            # real advisory-board runs you can browse
```

**Only promoted buckets ship.** Nothing in `in-progress/`, `misc/`, or `deprecated/` appears in the marketplace or on the site, so parking a half-finished skill is one `git mv` and an unclaim, with nothing deleted and no placeholder left in the catalog. CI enforces the boundary in both directions: a skill in a promoted bucket must be claimed by exactly one plugin, and a skill in an unpromoted bucket must be claimed by none.

The promoted buckets are also the site's regions, read straight from `buckets.json`; a skill's category is just the directory it sits in.

## Docs, releases, contributing

- **Docs:** the GitHub Pages site at [timharris707.github.io/skills](https://timharris707.github.io/skills) covers the catalog; each skill's `SKILL.md` is the source of truth.
- **Releases:** standalone skills tag as `<skill>/vX.Y.Z`, the pack as `team-workflow/vX.Y.Z`; each release's notes come from the relevant `CHANGELOG.md`. See [`RELEASING.md`](./RELEASING.md).
- **Contributing:** structure, quality bar, and validation in [`CONTRIBUTING.md`](./CONTRIBUTING.md).

## Acknowledgements

Much of this catalog is adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT), and this README's shape (problem first, fix second, reference last) is modeled on his. Every adapted skill names what it took and what it added in its own Attribution section; that section, not any list here, is the record. [grilling](./skills/decide/grilling/SKILL.md) and [writing-for-agents](./skills/author/writing-for-agents/SKILL.md) follow their originals most closely.

## License

Released under the [MIT License](./LICENSE.md): free to use, copy, modify, and adapt with attribution.

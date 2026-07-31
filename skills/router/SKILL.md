---
name: router
description: Entry point for the team-workflow pack — names every pack skill and when to reach for it. Use when unsure which team-workflow skill applies, or to orient a new session/repo on what the pack offers.
---

# Team-workflow router

One entry point for the **team-workflow** pack: a portable discipline for running tracked, multi-session, agent-assisted development — decision-making before building, throwaway prototyping, autonomous research, and tracker hygiene that keeps parallel sessions from colliding. Everything repo-specific lives in one binding doc seeded by the setup skill; every skill defers decisions to **the decider**, the role that doc names.

**First run in a repo? Run `setup` before anything else.** The other skills read the bindings it seeds.

## The skills

| Skill | Reach for it when |
| --- | --- |
| [setup](../setup/SKILL.md) | Installing the pack into a repo, or refreshing its bindings. Once-per-repo interview: confirms the tracker, verify commands, the decider, and the binding-doc home; seeds the binding doc and templates; re-runs are idempotent diffs, never overwrites. |
| [decision-map](../decision-map/SKILL.md) | The work is genuinely foggy — open questions gate each other and nobody can spec it in one sitting. Charts a map (destination, clusters, two ledgers), files gate-decision tickets, and runs briefed decision rounds with the decider. Not for work you could already spec: a map with nothing undecided is overhead. |
| [prototype](../prototype/SKILL.md) | The question is "how should this look / behave / feel in action" and discussion or static artifacts can't settle it. Throwaway code on a `prototype/<name>` branch — UI variants on the live route, or a terminal UI over a pure logic module; the verdict is the deliverable and the winner is re-implemented properly. |
| [research](../research/SKILL.md) | A question is answerable from primary sources and should run fire-and-report. Autonomous investigation ending in a cited findings file — and a questionnaire when the missing facts are human-held. |

## Not skills, but in the pack

- **Tracker discipline** — the claim / frontier / blocking recipes and the issue-as-spec shape live in [setup's references](../setup/references/tracker-discipline.md) and get bound to the repo via the binding doc. There is nothing to invoke; sessions follow the recipes.
- **Templates** — work-item spec, lane brief, and session handoff are templates the setup skill seeds into the consuming repo (handoff is deliberately a template, not a skill — repos often have their own wrap-up convention).

## Review discipline: the meta-rule

The pack ships no review checklist, on purpose. The rule that travels: **derive your own defect classes from your own defect history, and admit a class to the checklist only via a live reproduction** — a checklist imported from someone else's war record checks for their bugs, not yours. Start the repo's own list the first time a real defect escapes, and grow it only from evidence.

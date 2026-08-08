---
name: router
description: Entry point for the team-workflow pack — names every pack skill and when to reach for it. Use when unsure which team-workflow skill applies, or to orient a new session/repo on what the pack offers.
---

# Team-workflow router

One entry point for the **team-workflow** pack: a portable discipline for running tracked, multi-session, agent-assisted development — pressure-testing and decision-making before building, throwaway prototyping, autonomous research, filing the work that comes out of it, wizards for the steps only a human can take, adversarial review before changes ship, state review of the codebase between changes, session handoffs, orchestration of parallel lanes, and tracker hygiene that keeps parallel sessions from colliding. Everything repo-specific lives in one binding doc seeded by the setup skill; every skill defers decisions to **the decider**, the role that doc names.

**First run in a repo? Run `setup` before anything else.** The other skills read the bindings it seeds.

## The main flow

Most work travels one route: **idea → grill → map → tickets → lanes → review → merge.** An idea is pressure-tested in [grilling](../../decide/grilling/SKILL.md); when real fog surfaces, [decision-map](../../decide/decision-map/SKILL.md) charts and works it until nothing gating is undecided (no fog means skipping the map entirely); [to-tickets](../../run/to-tickets/SKILL.md) turns what was decided into tracer-bullet items; [orchestrate](../../run/orchestrate/SKILL.md) routes those items into parallel lanes; [adversarial-review](../../run/adversarial-review/SKILL.md) tries to break each change before it merges. [prototype](../../investigate/prototype/SKILL.md) and [research](../../investigate/research/SKILL.md) are detours off any point of the route — taken when a question needs seeing or reading rather than deciding — and [handoff](../../run/handoff/SKILL.md) carries state across every session boundary along it.

**On-ramps** merge onto that route rather than starting a new one: [ingest](../../investigate/ingest/SKILL.md) turns a recording or media URL into evidence plus a recommendation for where it enters the flow (tickets, a grilling session, strategy for the decider); [research](../../investigate/research/SKILL.md) findings and returned questionnaires feed the grilling that follows them; [wizard](../../run/wizard/SKILL.md) clears the human-only steps a lane stalls on and hands the flow back.

## The skills

| Skill | Reach for it when |
| --- | --- |
| [setup](../setup/SKILL.md) | Installing the pack into a repo, or refreshing its bindings. Once-per-repo interview: confirms the tracker, verify commands, the decider, and the binding-doc home; seeds the binding doc, templates, and the session-start handoff hook; re-runs are idempotent diffs, never overwrites. |
| [grilling](../../decide/grilling/SKILL.md) | An idea or plan is half-formed and nobody has pressure-tested it. Interviews the decider in rounds over a design tree — the frontier is every decision whose prerequisites are settled — until nothing load-bearing is still assumed. Facts are the agent's job; decisions are the decider's. Run it before charting a map or writing a spec off a conversation. |
| [decision-map](../../decide/decision-map/SKILL.md) | The work is genuinely foggy — open questions gate each other and nobody can spec it in one sitting. Charts a map (destination, clusters, two ledgers), files gate-decision tickets, and runs briefed decision rounds with the decider. Not for work you could already spec: a map with nothing undecided is overhead. |
| [prototype](../../investigate/prototype/SKILL.md) | The question is "how should this look / behave / feel in action" and discussion or static artifacts can't settle it. Throwaway code on a `prototype/<name>` branch — UI variants on the live route, or a terminal UI over a pure logic module; the verdict is the deliverable and the winner is re-implemented properly. |
| [research](../../investigate/research/SKILL.md) | A question is answerable from primary sources and should run fire-and-report. Autonomous investigation ending in a cited findings file — and a questionnaire when the missing facts are human-held. |
| [codebase-review](../../investigate/codebase-review/SKILL.md) | The codebase itself needs review — a spec is about to land in an area, enough lanes have merged since the last look, or lanes report the code fighting them. A read-only lane: lens-named finders, a built-in skeptic that kills unproven candidates, a plain-markdown report on the tracker, and a disposition loop where the decider adopts, rejects into rejection memory, or defers every survivor. Zero survivors is a success verdict, not a failure. |
| [to-tickets](../../run/to-tickets/SKILL.md) | The decision is made and the work needs to be on the board. Turns a plan, a closed decision map, or a pressure-tested conversation into tracer-bullet items — issue-as-spec bodies filed in one pass, blocking edges wired in a second. Files and labels; never claims, never decides. |
| [wizard](../../run/wizard/SKILL.md) | The next step is one only a human can take — a vendor dashboard, a registrar's DNS panel, a credential that must not enter an agent's context. Generates an interactive bash wizard that opens each URL, says what to click, captures the values, verifies what it can, and reports what still needs doing by hand. |
| [handoff](../../run/handoff/SKILL.md) | Context is filling (around half the window), the session is wrapping up, or someone says "checkpoint" / "save state". Writes the structured session handoff — overwrite-don't-append, pointer-not-transcript, NEXT points at the tracker query — so a fresh session resumes losslessly. |
| [orchestrate](../../run/orchestrate/SKILL.md) | One session should coordinate several — routing tracked items into parallel working lanes, auditing results, owning integration — instead of implementing. Principles plus per-repo binding slots; the single-orchestrator rule applies. |
| [adversarial-review](../../run/adversarial-review/SKILL.md) | A substantial change is about to be committed, a lane is at close-out, or someone asks to break a diff before it ships. Three isolated finders (correctness, a fitting lens, a spec axis), a skeptic pass that kills unproven findings, a gate only confirmed blockers may hold — run before external reviewers see the change. |
| [ingest](../../investigate/ingest/SKILL.md) | A recording, voice memo, or media URL arrives with a goal. Converts it into an evidence packet — transcript, timestamped frames, manifest — and ends with a routing recommendation into the flow: what looks like tickets, what needs a grilling session, what is strategy for the decider. Ships as its own plugin, installed beside the pack. |

## Not skills, but in the pack

- **Tracker discipline** — the claim / frontier / blocking recipes and the issue-as-spec shape live in [setup's references](../setup/references/tracker-discipline.md) and get bound to the repo via the binding doc. There is nothing to invoke; sessions follow the recipes.
- **Templates** — work-item spec and lane brief are templates the setup skill seeds into the consuming repo; the session-handoff template ships inside the handoff skill.

## Review discipline: the meta-rule

The pack ships a review **protocol** — the [adversarial-review](../../run/adversarial-review/SKILL.md) skill — but still no review checklist, on purpose. The rule that travels: **derive your own defect classes from your own defect history, and admit a class to the checklist only via a live reproduction** — a checklist imported from someone else's war record checks for their bugs, not yours. That rule now lives as the skill's defect-class binding slot: each repo's checklist starts empty (or adopts the repo's existing review-standards document) and grows only from evidence.

A sibling of the same meta-rule: **institutional review memory** — review verdicts recorded as per-repo decision entries that later reviews (human and automated) consult before commenting, so settled decisions reopen on new evidence, not on repetition. Repos that already run such a system — a review-response skill with a decision wiki — have the review-RESPONSE stage covered, and this pack deliberately stays out of it: planning, research, prototyping, handoff, and orchestration are the pack's territory; review response belongs to the resident system, and pack outputs should cite that repo's precedent store rather than create a second one.

## Attribution

The main-flow-with-on-ramps framing is adapted from Matt Pocock's [`ask-matt`](https://github.com/mattpocock/skills/tree/main/skills/engineering/ask-matt) (MIT); the flow itself, the table, and the meta-rules are this pack's.

---
title: Graph engineering
kind: survey
date: 2026-08-05
checked: 2026-08-05
standfirst: An eighteen-day-old name for patterns Anthropic documented in December 2024, sharing a word with an unrelated body of peer-reviewed work that never uses it. Here is what survives, and how much of this catalog it actually describes.
---

Two different communities landed on the same phrase, and only one of them has evidence. Sorting that out first makes the rest of this readable.

**Task-graph orchestration.** Decompose a goal into a dependency graph, run the independent nodes concurrently, gate downstream integration behind completed prerequisites. Every mainstream source uses the phrase this way. [Aident](https://aident.ai/blog/claude-code-graph-engineering-agent-teams) states the shape without decoration — "Graph engineering is a workflow pattern, not a Claude Code command" and "A graph coordinates several bounded loops" — and prescribes one lead, two or three workers, and a separate verification node.

**Code knowledge graphs.** Index a repository as symbols and relationships — call edges, imports, inheritance, tests — so an agent traverses dependencies instead of matching strings. This one has a peer-reviewed lineage going back to 2024, and it does not call itself graph engineering.

The two have nothing to do with each other. [MarkTechPost](https://www.marktechpost.com/2026/07/29/prompt-engineering-vs-loop-engineering-vs-graph-engineering/) is the only mainstream source to notice, observing that the term "collides with an older knowledge-graph usage of the same word." Exactly one source treats them as a single discipline: a [GitHub repository](https://github.com/codejunkie99/graph-engineering) defining graph engineering as "The discipline of designing the structures AI agents work through — not the prompts." The GitHub API reports it created at 2026-07-23T14:10:49Z and last pushed at 14:10:53Z. One commit, four seconds after creation, never touched since. Thirty-six kilobytes. That is the entire basis for the unified reading.

Treat the halves separately or you will be wrong about both.

## What survives

Five rules hold up against everything below.

1. **Use a graph only when two tasks can advance without consuming each other's unfinished output.** This is the one genuinely falsifiable rule in the whole corpus — aident's gating test. Same-file, schema, lockfile and migration work stays sequential, which is also Anthropic's own guidance about when *not* to run a team.
2. **Carry evidence on every edge.** Node, outcome, changed files, validation command, exit code, artifacts, known risks. Downstream verifies the artifact; it does not trust the word "done."
3. **Deterministic gates over model judges.** A validator proves a field is missing. A model argues its work is complete.
4. **Manufacture disjoint work before you draw the topology.** Carlini's sixteen agents did not fail on coordination — they failed because they were all standing on the same bug. An oracle that split the territory fixed it. A prettier graph would not have.
5. **Define done and correct before you define the shape.** Drawing a topology without that is, in the advocacy literature's own words, "a prettier way to fail."

Rule 4 is the one people skip, and it is the one with the best evidence behind it.

## What the evidence actually says

**The largest documented parallel run rejected orchestration entirely.** Nicholas Carlini [ran 16 agents to build a C compiler](https://www.anthropic.com/engineering/building-c-compiler) (5 February 2026): roughly 2,000 sessions, 2 billion input tokens, about $20,000, some 100,000 lines of Rust that builds a bootable Linux 6.9. His coordination was text files in a `current_tasks/` directory, arbitrated by git — "If two agents try to claim the same task, git's synchronization forces the second agent to pick a different one." He is explicit: "I don't use an orchestration agent."

His failure data is better than anyone else's success data. On a monolithic goal, "Every agent would hit the same bug, fix that bug, and then overwrite each other's changes," and "Having 16 agents running didn't help because each was stuck solving the same task." The fix was not a better topology. It was manufacturing disjoint work by using GCC as an oracle so agents bisected into separate bug territory. And he names the binding constraint, which is not topology at all: a weak verifier means "Claude will solve the wrong problem."

**The vendor whose tooling implements this never uses the term.** Anthropic's [agent teams documentation](https://code.claude.com/docs/en/agent-teams) describes the prescribed mechanics precisely — a shared task list where "a pending task with unresolved dependencies cannot be claimed until those dependencies are completed," file locking on claims, per-agent mailboxes, and task and idle hooks as quality gates. The phrase "graph engineering" appears nowhere in it. The capability is real; the label is bolted on from outside.

**That same documentation contradicts the maximalist pitch.** "Start with 3-5 teammates." "Three focused teammates often outperform five scattered ones." Token costs scale linearly per teammate. And agent teams are named as the wrong tool for "sequential tasks, same-file edits, or work with many dependencies" — which is precisely the dependency-heavy work a task graph is marketed at.

**There is no benchmark.** [SmartScope's evidence review](https://smartscope.blog/en/blog/graph-engineering-loop-engineering-logic-review/) rates reliability gains "Insufficient evidence" because no comparative benchmark was found. Aident gives no performance numbers. Neither does eigent.ai. The one figure in circulation — "~92% of solo quality at ~63% cost on SWE-bench Pro" — carries no citation and no reproducible setup.

**A graph without grounding is worse than a loop without one.** [Carlos Perez](https://medium.com/intuitionmachine/from-loop-engineering-to-graph-engineering-d3ebeb08511c) makes the sharpest structural criticism: a fully-connected graph of loops becomes "an elaborate network of mutual confirmation in which everything is consistent and nothing is verified," failing "later and more expensively, with far more green lights on the way down." His conclusion — "The topology bought sophistication. It did not buy contact with reality" — and his read that the durable axis was never loops versus graphs at all, but ungrounded versus grounded. Eigent lands in the same place independently: "a graph without anchors is just a more elaborate echo chamber."

**The word is new; the practice is not, and the advocates say so.** Anthropic's [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (19 December 2024) already documented prompt chaining, routing, parallelization, orchestrator-workers and evaluator-optimizer, defining orchestrator-workers as "a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes their results." That document never uses the word "graph," and contains no DAG, node or edge vocabulary. The patterns predate the label by nineteen months. The pro-graph [AI Builder Club guide](https://www.aibuilderclub.com/blog/graph-engineering-vs-loop-engineering) concedes it verbatim: "The word is new. The practice is not." / "Calling the practice 'graph engineering' is a naming event, not a technical one."

A graph contains loops, so succession is the wrong relation — SmartScope's version is that it "resembles saying that shapes replace circles" — and agent graphs are state machines, which is why the most-cited reply was "Congrats, you reinvented LangGraph." David Khourshid, who created the XState state-machine library, put it bluntly: "First it was loops. Now it's graphs. Next month it'll be something else."

## The half nobody is tweeting about is the half with the evidence

Code knowledge graphs have benchmarks, ablations and peer review. [RepoGraph](https://arxiv.org/abs/2410.14684) (ICLR 2025) is a plug-in module managing repository structure at line-level granularity. [CodexGraph](https://aclanthology.org/2025.naacl-long.7/) (NAACL 2025) integrates agents with a graph database over MODULE/CLASS/FUNCTION nodes and CONTAINS/INHERITS/USES edges. [LARGER](https://arxiv.org/abs/2605.16352) (May 2026) reports file-level Acc@5 up 13.9 points on LocBench over the strongest baseline — and, more interestingly, drops into existing CLI coding agents without requiring an external graph database. That constraint is the actual engineering insight: the win came from folding structure into the agent's existing search loop, not from bolting a graph database onto the side.

[Code Isn't Memory](https://arxiv.org/abs/2606.22417) (June 2026) runs the best-controlled comparison — three arms, model held fixed, three seeds, SWE-PolyBench Verified and SWE-bench Pro — and reports the honest result: a large within-harness localisation gain and a separated resolve gain at lower cost per solve, but against agentic grep only that the index "does not regress."

The single most practically important finding is behavioural. [CodeCompass](https://arxiv.org/abs/2602.20048) (February 2026, 258 trials over 30 tasks) reports 99.4% completion on hidden-dependency tasks against 76.2% vanilla — and also that **58% of trials with graph access made zero tool calls**, with agents requiring explicit prompt engineering to adopt the tool at all. Its diagnosis: "the bottleneck is not tool availability but behavioral alignment." Building the graph is the easy half. Getting the agent to prefer structure over grep is the hard half.

One correction while we are here, because every secondary source blurs it: [Is Grep All You Need?](https://arxiv.org/abs/2605.15184v1) is not evidence against code graphs. It tests *vector* retrieval, and it tests it on conversational memory, not on a code corpus. Do not cite it in this argument.

## How much of this catalog it describes

The flattering claim is that this catalog is a graph-engineering toolkit and the homepage already draws the graph. It does not survive the files, so here is the checkable version.

**Three of twelve skills build a dependency graph.** [to-tickets](/skills/to-tickets) is the one whose job is literally wiring edges, and it explains why in graph terms: items need ids before they can reference each other, so filing is always two passes, and doing it in one "produces edges pointing at numbers that do not exist yet." [decision-map](/skills/decision-map) charts what gates what before anything is specced. [grilling](/skills/grilling) grows a decision tree at interview time and sweeps its frontier breadth-first.

**Three more depend on a graph without building one.** [orchestrate](/skills/orchestrate) starts by running the frontier query and never wires an edge. [handoff](/skills/handoff) defers to the graph rather than snapshotting it. [setup](/skills/setup) binds what "the frontier query" means per repo.

**The other six do not touch the concept.** `research`, `prototype`, `wizard`, `advisory-board`, `writing-for-agents` and `router` contain no dependency-graph idea at all.

And the graph on this site's homepage is not a task graph. Twelve nodes, thirteen edges, acyclic — it draws which skill hands off to which. That is an *org* graph, not a work graph. The work graph is the thing `to-tickets` files on your tracker, and it never appears on this site at all.

No priority is claimed here. Anthropic published the patterns in December 2024, and LangGraph shipped StateGraph before that.

Worth separating two dates that are easy to conflate, though, because I conflated them myself while writing this. These skills reached this repository on 31 July and 5 August 2026, after the term was coined — that is when they were *published*. The practice they encode is older: worktree-isolated agent lanes are dated 29 March 2026 in my own repositories, a routing handoff document 3 April, an `AGENTS.md` 22 May, a `.handoffs/` directory 4 June. Those repositories are private, so take that as stated rather than shown; the publication dates are the ones you can check.

Which is the same shape as everything above, in miniature. The work came first and the word arrived later, and a commit date measures when someone got around to sharing it.

## Provenance

The dates are short enough to state plainly.

**7 June 2026** — Addy Osmani names loop engineering: "replacing yourself as the person who prompts the agent. You design the system that does it instead." His essay already flags weak verification — the agent claims done without proof — as the core risk. The same failure mode graph engineering would later claim to fix.

**18 July 2026, 00:34 UTC** — Peter Steinberger posts one line: "Are we still talking loops or did we shift to graphs yet?" No definition. No design principles. SmartScope's review rules the claim that he published a methodology **False**, calling him "the catalyst for this discussion than the formal author of a method."

**About four and a half hours later** — an article titled "Loop Engineering Is Dead. Enter Graph Engineering" appears. [Alexey Grigorev, who tracked the timeline](https://alexeyondata.substack.com/p/ai-native-development-specifications), reports the body was a "stop it" GIF. It was mockery of the hype cycle — an obituary for a term six weeks old — and it has been cited as sincere ever since.

**23 July 2026** — the only repository fusing both halves is created and abandoned in the same second.

**3 August 2026** — the term reaches a much larger audience than the literature ever did, through a 26-minute video titled ["Why Graph Engineering will 10x your Claude/Codex"](https://www.youtube.com/watch?v=JWhICz1QR8M) (71,346 views two days after publication). It is worth reading the body against the title, because the two disagree.

The string "10x" does not occur anywhere in the 4,058-word transcript. Neither does "benchmark", nor "percent", nor any measurement or comparison at all. The single use of "faster" runs the other way: *"if the manual version doesn't produce way better work, automating it, honestly, will just produce mediocre work way faster."* "Claude" is said twice in twenty-six minutes and "Codex" is not said once; the coding-agent segment runs seventy-two seconds, four and a half percent of a video named for two coding agents. It is really about founder and operator workflows.

It also declines every error in circulation. It makes no origin claim beyond having seen the term go viral, never cites the obituary, never says loop engineering is dead, and cites no benchmark — correctly, because there is none. It warns against its own genre: *"more agents don't automatically mean better output. Sometimes actually more agents mean more noise."* It tells viewers to run the workflow by hand before touching a framework. It opens by asking whether the term is real or whether the field "just invent[ed] another phrase to make everyone feel behind."

So the honest verdict is not that the video is wrong. Its substance is sound. What it does not do is attribute: the planner, the parallel workers, the separate checker, the synthesiser and the human gate are Anthropic's December 2024 patterns, and the video says "Anthropic" zero times and "OpenAI" zero times while crediting LangGraph five. **The overclaim is in the packaging. The body is more careful than its own title, and better evidence for how this term travels than any takedown would be.**

Two disclosures. The view count is a snapshot taken 5 August 2026 and will drift. And the transcript is YouTube's auto-generated captioning, so quoted wording is approximate at the word level — it renders "Codex" as "code acts" — while the substance is reliable.

Within a fortnight the term had a for-and-against literature, an obituary, and a repository; a fortnight after that it had a video with seventy thousand views. That is the whole basis for calling it settled; the traffic figures that would substantiate more than that are irreconcilable across sources.

## What I could not check

The origin post and the four-and-a-half-hour obituary were not read directly. Both are characterised here through independent secondary accounts that agree on substance and timing, and the origin post's engagement numbers are irreconcilable across sources, so none is quoted. RepoGraph's most-cited improvement figure is omitted because the abstract states only qualitative claims and the number circulates via secondary summaries. Star and commit facts for the fused repository came from the GitHub API and will drift.

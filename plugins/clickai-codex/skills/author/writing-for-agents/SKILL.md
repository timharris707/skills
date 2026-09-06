---
name: writing-for-agents
description: "For skills, standing agent instructions, recorded rules, or documents agents skip, write and prune reliable triggers and checkable steps. Use to author or revise SKILL.md, AGENTS.md, CLAUDE.md, rules and references, or diagnose unreliable invocation and skimming."
---

# Writing for Agents

Read the [Codex desktop binding](../../../CODEX.md) when this workflow needs harness mechanics, model routing, or recovery.

Every document an agent reads is a **behavior lever**, not prose. The packaging differs across a skill, a standing instruction file, and a reference reached by a pointer, but the writing does not: the same levers make each one predictable. Predictable means the agent takes the same *process* every run. It does not mean the agent produces the same output.

This skill is reference, not a sequence: consult the rung that matches what you're writing. For frontmatter, invocation modes, and this repo's catalog invariants, read [references/skill-mechanics.md](references/skill-mechanics.md). When the reader is a human, as on a landing page, a README's front half, or a launch post, these levers read cold; use [writing-for-humans](../writing-for-humans/SKILL.md) instead.

## Context pointers

An agent often holds a short line that points at material it has not loaded: a skill's `description`, or a line in `AGENTS.md` naming a doc. That line is a **context pointer**: a reference the agent already holds that names material it does not, plus the condition for going and getting it.

The pointer's **wording**, not its target, decides whether the agent reaches the material. A must-have target behind a weakly worded pointer is a variance bug: the material is right and the firing is a coin flip. Sharpen the wording first; inline the material only when sharpening has already failed.

A pointer does two jobs: say what the material is, and name the **branches** that should trigger reaching it. A branch is a distinct case the document handles: different runs take different paths through it. Because an always-loaded pointer costs on every turn, it earns harder pruning than the body:

- **Front-load the trigger.** The pointer's opening words are where it does its work.
- **One trigger per branch.** Synonyms that rename a single branch are one branch written twice.
- **Cut identity the body already carries.** The pointer says when to come, not who you are.

## The two budgets

Every document and every pointer spends one of two budgets:

- **Context load.** Always-loaded material occupying the window: a skill description, an `AGENTS.md` line, anything present every turn whether or not it fires. Paid in tokens and in attention.
- **Cognitive load.** The cost on the human: knowing which documents exist and when to reach for each. The human is the index.

Cognitive load is not a cost to minimize. It is the price of human agency: spend it where human judgment matters, remove it where it does not. Material behind a pointer escapes context load at the price of the pointer's own line; material with no pointer rides entirely on cognitive load.

## The information hierarchy

A document mixes two content types: **steps** (ordered actions the agent performs) and **reference** (definitions, rules, and facts consulted on demand). A document may be all steps, all reference, or both. The decision that matters is where each piece sits on a ladder ranked by how immediately the agent needs it:

1. **In-file step.** The primary tier: what the agent does, in order.
2. **In-file reference.** Consulted on demand. Often a legitimately flat peer-set (every rule of a review on one rung). That is an arrangement, not a smell.
3. **Disclosed reference.** Pushed into a separate file behind a pointer, loaded only when the pointer fires. Ranges from a sibling in `references/` to material any document can point at.

Push too little down and the top bloats; push too much and you hide what the agent actually needs. That tension is the whole decision.

**Progressive disclosure** is the move down the ladder. It is not primarily a token optimization. It is how the top stays legible. The cleanest test is branching: inline what every branch needs, disclose what only some branches reach. When a document has steps, undisclosed in-file reference buries them, and attending to them becomes a coin flip.

**Co-location** is the within-file companion. The ladder decides how far down a piece sits; co-location decides what sits beside it once there. Keep a concept's definition, rules, and caveats under one heading so reading one part brings its neighbors along. Scattering fragments one meaning across many places; duplication, a distinct failure, repeats one meaning in two.

**Sprawl** is the failure mode: a document simply too long, even when every line is live and unique. Attention thins across the excess. The cure is the ladder: disclose reference behind pointers, and split by branch or sequence so each path carries only what it needs.

## Completion criteria

Every step ends on a **completion criterion**, the condition telling the agent the work is done. Two properties make it a lever:

- **Clarity.** Can the agent tell done from not-done? A vague bound ("understanding reached") invites **premature completion**: ending early as attention slips toward *being done*. Visible later steps supply the pull; the criterion's clarity is the resistance. Sharpen the bound first; it is local and cheap. Only when a bound is irreducibly fuzzy *and* you observe the rush should you hide later steps by splitting the sequence, and hiding works only across a real context boundary (a handoff, a subagent dispatch). An inline call leaves the later steps in context and clears nothing.
- **Demand.** How much the criterion requires. "Every modified model accounted for" forces thorough work where "produce a change list" does not. Demand drives the digging the agent does inside the work, and it is not step-bound: "every rule applied" binds a body of flat reference exactly as "every step done" binds a sequence. That is how an all-reference document still carries an exhaustiveness bar.

The strongest criteria are both checkable and exhaustive. In this catalog they surface as the **`## Done when (checkable)`** section every task-shaped skill carries; a skill with no discrete run to complete (a menu, a standing role) is exempt, and the exemption is a deliberate call, not an omission.

## When to split

Splitting one document into two spends one of the two budgets, so split only when the cut earns it:

- **By sequence.** Hide later steps whose visibility tempts the agent to rush the one in front of it, only under the completion-criteria conditions above. Beware the reverse: merging sequences exposes each step to what follows it, inviting premature completion.
- **By invocation.** Skill-specific: when different triggers should reach different material, each invocation path becomes its own skill. The mechanics live in [references/skill-mechanics.md](references/skill-mechanics.md).

## Leading words

A **leading word** is a compact concept already living in the model's pretraining that the agent thinks with while running the document: *frontier*, *fog*, *tracer bullet*, *lane*. Repeated as a token and never as a sentence, it accumulates a distributed definition and anchors a whole region of behavior in the fewest tokens, by recruiting priors the model already holds.

It anchors twice. In the body it anchors **execution**: the agent reaches for the same behavior every time the word appears. In a pointer it anchors **invocation**: when the same word lives in your prompts, your docs, and your codebase, the agent links that shared language to the material and reaches it more reliably.

Coining your own works if you define it clearly, but a made-up word recruits no priors: you pay in definition tokens what a pretrained word gives free. Reach for an existing word first. Hunt for passages begging to collapse into one token: "fast, deterministic, low-overhead" becomes *tight*; "a loop you believe in" becomes *red*, turning a fuzzy gate into a binary observable state.

**Negation** is the failure mode beside this lever. Steering by prohibition drags the forbidden behavior into context and makes it *more* available. The ban half-reads as an instruction to do the thing, because a negation is a weak modifier that the strongly-activated concept overruns. **Prompt the positive**: state the target behavior so the banned one is never spoken. A prohibition earns its place only as a hard guardrail you cannot phrase positively, and even then it pairs with the positive target.

## Punctuation

The em dash never appears in skill prose: it is a top AI tell, and the prose an agent reads leaks into the prose it writes (plainspoken's tell catalog, pattern 13). Separate thoughts with periods, commas, and colons instead.

## Pruning

- **Single source of truth.** Keep each meaning in exactly one authoritative place, so changing the behavior is a one-place edit. **Duplication** costs maintenance and tokens, and inflates a meaning's rank on the ladder past its real one. It is the accidental inverse of a leading word, which repeats a token on purpose and never the meaning.
- **The environment is a source of truth too.** `package.json` scripts, config files, directory layout, `--help` output. A document restating it is a **cache**, and a cache earns its load only when the lookup is expensive. Cache what the agent cannot find by looking: the unwritten convention, the reason behind a choice, the gotcha no config confesses. Leave one-command lookups to the environment, where they cannot go stale.
- **Relevance.** A line loses it by never bearing on the task (exposition, or a branch that should be disclosed) or by going stale as the world it describes changes. Without a pruning discipline the default fate is **sediment**: stale layers that settle because adding feels safe and removing feels risky.
- **No-ops.** An instruction the model already obeys by default pays load to say nothing. The test is whether the line changes behavior versus the default, and it is model-relative, not reader-relative. Two people disagreeing about a no-op disagree about the default, and settle it by running the document, not by debating. When a sentence fails, delete the whole sentence rather than trimming words from it. The test also grades leading words: a word too weak to beat the default (*be thorough*, when the agent is already thorough-ish) is a no-op, and the fix is a stronger word (*relentless*), not a different technique.

## Done when (checkable: verify each line before reporting complete)

- Every pointer names its branches, front-loads its trigger, and carries no identity the body repeats.
- Every piece of content sits on a deliberate rung: inlined because every branch needs it, or disclosed because only some branches reach it.
- Every step ends on a criterion you can evaluate as done or not-done, and the document carries an exhaustiveness bar.
- No meaning appears in two places, and nothing restates a lookup the environment answers in one command.
- Every prohibition either states a positive target beside it or is a hard guardrail that cannot be phrased positively.
- No em dash appears outside a code block or inline code span.
- The no-op test has been run sentence by sentence, and what failed was deleted rather than trimmed.

## Attribution

This skill is a lightly edited adaptation of Matt Pocock's [`writing-for-agents`](https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents) (MIT). Not just the vocabulary but the body: context pointers, the two budgets, the information hierarchy, completion criteria, when to split, leading words, and pruning follow his text section by section, much of it near-verbatim. What this repo adds: the checkable Done-when list, the punctuation rule, and the mechanics reference with its catalog invariants.

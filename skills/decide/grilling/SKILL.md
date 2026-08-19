---
name: grilling
description: Interview the decider relentlessly to turn a half-formed plan, design, or idea into shared understanding: a design tree worked in rounds until nothing is silently assumed. Use when asked to grill, stress-test, or pressure-test thinking, and before charting a decision map or writing a spec off a conversation nobody has pressure-tested.
---

# Grilling

A grilling session converts a half-formed idea into **shared understanding** by interviewing the decider until nothing load-bearing is still assumed. It is the pack's live, single-session instrument: no tickets, no map doc, no branch: the deliverable is agreement, reached out loud and then written down (see the closing record below).

Map the work as a **design tree**: every decision branches into the decisions that hang off it. You do not know the tree in advance; each answer grows it.

## Rounds and the frontier

The **frontier** is every decision whose prerequisites are already settled: the questions askable *now* without guessing at answers you have not heard. Ask the whole frontier in one round, then wait. Where the repo binds [domain-memory](../../orient/domain-memory/SKILL.md), read the relevant decision records before composing the first round; a recorded decision is settled, not frontier, and reopens on new evidence, never on repetition.

The word means the same thing here as it does on the tracker, the edge of what is takeable, where [decision-map](../decision-map/SKILL.md) works a frontier of gated tickets. A question whose answer depends on another question still open in this round belongs to a *later* round. Putting it in this round forces the decider to answer twice: once on a guess, once for real.

Each answer reshapes the tree. Settled decisions push the frontier outward and unblock what depended on them. Recompute and ask the next round.

## How to ask a round

Two presentations, chosen per question rather than per session.

**Choice-shaped questions go to the harness's structured question tool** where one exists. In Claude Code that is `AskUserQuestion`, which renders each question as selectable cards. Put your recommendation first and mark its label `(Recommended)`. Give each question two to four real options, keep the header under twelve characters, and set multi-select only where the choices genuinely combine. The tool always appends an "Other" escape, so the card format never costs the decider the ability to answer in their own words.

That tool takes at most four questions per call. **A wide frontier is split across consecutive calls, never deferred to the next round.** Frontier questions are mutually independent by construction, which is what being on the frontier means, so answering four of them cannot change what the remaining three should be. The tree reshapes when the frontier is answered, not between calls.

**Open questions stay in text.** "Which failure mode worries you most" has no option list that is not an invention, and inventing one narrows the answer to whatever you happened to think of. Ask those so a round stays scannable and answerable by number:

```text
❓ **Q1** — **<short title>**: <the question, with options where options exist>

➡️ <your recommended answer, and the one-line reason>
```

One round may mix both presentations, and usually will. Where the harness offers no structured tool, every question uses the text block and the round is no different for it.

Always give the recommendation, in either presentation. A question without one makes the decider do your thinking as well as their own; a wrong recommendation is *more* useful than none, because disagreeing with a concrete claim is faster than composing an answer from nothing.

## Facts are yours, decisions are theirs

**Finding facts is your job, never the decider's.** When a frontier question needs something the environment already knows, go find it: what the code does, what the config says, what the vendor documents. Dispatch a subagent for anything that takes real digging, and follow the research skill's contract when the answer wants a durable citation.

Do not block on it. A running investigation is an unsettled prerequisite, so only the questions *downstream* of it wait. Ask the rest of the frontier now and fold the finding in when it lands.

The **decisions** are the decider's. Put each one to them and wait. A grilling agent that answers its own questions has produced nothing but a transcript of itself.

## Where it sits in the pack

- **Before a decision map.** Charting needs a destination and a first read on the fog; grilling produces both. Reach for [decision-map](../decision-map/SKILL.md) when the answer is "this is too big for one sitting and the open questions gate each other"; grilling is the engine that surfaces that, not a replacement for it.
- **Before a spec.** A conversation nobody pressure-tested makes a spec full of silent assumptions. Grill first, then write.
- **Beside prototype and research.** When a question turns out to be "I need to see it in action," that is a [prototype](../../investigate/prototype/SKILL.md); when it is "somebody documented this already," that is [research](../../investigate/research/SKILL.md). Hand off and keep grilling the rest of the frontier.
- **Not the advisory board.** [advisory-board](../advisory-board/SKILL.md) puts a finished artifact in front of several models for independent review. Grilling is one agent interviewing one human about something that is not finished yet. Grill to reach a position; convene the board to test one you already hold.

## Close with a record

Agreement that lives only in the transcript evaporates with the session. Once the decider confirms shared understanding, write it down somewhere durable: a comment on the driving ticket where one exists, otherwise a dated summary in the repo's docs home (the binding doc names it). The record is short and it is not the interview: it enumerates the settled decisions, the design tree as visited, and marks each recommendation accepted or overridden. It is what a later spec or ticket names as its plan source, so [to-tickets](../../run/to-tickets/SKILL.md) links a citable decision instead of a conversation nobody can reopen. Where the repo binds [domain-memory](../../orient/domain-memory/SKILL.md), the close-record also mints memory: each settled decision becomes a decision record at the memory home and new or sharpened terms enter the glossary, the same store the pre-round read consults so a settled question is never re-asked.

## Done when (checkable: verify each line before reporting complete)

- The frontier is empty, and the closing record enumerates the settled decisions: the visited tree is readable from the record, with nothing load-bearing left assumed.
- Every question that needed a fact got one you found, not a fact the decider was asked to supply.
- Every recommendation you made is marked accepted or overridden in the closing record, none left silently unanswered.
- The decider has explicitly confirmed shared understanding. Their last answer is not the confirmation; ask for it.
- The confirmed understanding is written to its durable record, a ticket comment or dated summary, not left in the transcript.
- Anything that surfaced as a prototype, research, or map-sized question is named as such, with the skill that owns it.
- Where the repo binds domain-memory: the relevant decision records were read before the first round, and the close-record's settled decisions and new or sharpened terms are minted into the store.

## Hard guardrails

- **Do not act on the understanding.** Grilling produces agreement, not changes: no code, no specs, no new tickets filed off the session. The writes are the closing record and, where the repo binds domain-memory, the records that closing mints and the glossary updates it makes; an existing driving ticket may, and per the closing step should, receive the record as a comment. Building, speccing, and filing happen after the decider confirms, as their own moves.
- **One round at a time.** Asking the next round before the current one is answered collapses the tree into a questionnaire and loses the reshaping that makes the rounds worth running. Splitting a single frontier across consecutive structured-question calls is still one round; asking anything whose prerequisite is unanswered is not, however it is presented.
- **Relentless means relentless.** Stopping at the first coherent answer is the failure mode this skill exists to prevent. An unasked question is a decision made silently, by you.

## Attribution

This skill is adapted from Matt Pocock's [`grilling`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grilling) (MIT), and follows it closely. The core model is his: the design tree, working it in rounds, the frontier as the set of decisions whose prerequisites are settled, deferring dependent questions to a later round, the ❓/➡️ question format, finding facts yourself while leaving decisions to the human, and not acting until shared understanding is confirmed.

What this repo adds: the presentation split between structured questions and text, the placement against the rest of the pack, the durable closing record, the checkable Done-when list, the hard guardrails, and the argument for why a recommendation is mandatory.

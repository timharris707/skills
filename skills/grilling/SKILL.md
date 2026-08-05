---
name: grilling
description: Interview the decider relentlessly to turn a half-formed plan, design, or idea into shared understanding — a design tree worked in rounds until nothing is silently assumed. Use when asked to grill, stress-test, or pressure-test thinking, and before charting a decision map or writing a spec off a conversation nobody has pressure-tested.
---

# Grilling

A grilling session converts a half-formed idea into **shared understanding** by interviewing the decider until nothing load-bearing is still assumed. It is the pack's live, single-session instrument: no tickets, no map doc, no branch — the deliverable is agreement, and agreement is reached out loud.

Map the work as a **design tree**: every decision branches into the decisions that hang off it. You do not know the tree in advance; each answer grows it.

## Rounds and the frontier

The **frontier** is every decision whose prerequisites are already settled — the questions askable *now* without guessing at answers you have not heard. Ask the whole frontier in one round, then wait.

The word is the pack's, and it means the same thing here as it does on the tracker: the edge of what is takeable. A question whose answer depends on another question still open in this round belongs to a *later* round. Putting it in this round forces the decider to answer twice — once on a guess, once for real.

Each answer reshapes the tree. Settled decisions push the frontier outward and unblock what depended on them. Recompute and ask the next round.

Format every question so a round is scannable and answerable by number:

```text
❓ **Q1** — **<short title>**: <the question, with options where options exist>

➡️ <your recommended answer, and the one-line reason>
```

Always give the recommendation. A question without one makes the decider do your thinking as well as their own; a wrong recommendation is *more* useful than none, because disagreeing with a concrete claim is faster than composing an answer from nothing.

## Facts are yours, decisions are theirs

**Finding facts is your job, never the decider's.** When a frontier question needs something the environment already knows — what the code does, what the config says, what the vendor documents — go find it. Dispatch a subagent for anything that takes real digging, and follow the research skill's contract when the answer wants a durable citation.

Do not block on it. A running investigation is an unsettled prerequisite, so only the questions *downstream* of it wait — ask the rest of the frontier now and fold the finding in when it lands.

The **decisions** are the decider's. Put each one to them and wait. A grilling agent that answers its own questions has produced nothing but a transcript of itself.

## Where it sits in the pack

- **Before a decision map.** Charting needs a destination and a first read on the fog; grilling produces both. Reach for [decision-map](../decision-map/SKILL.md) when the answer is "this is too big for one sitting and the open questions gate each other" — grilling is the engine that surfaces that, not a replacement for it.
- **Before a spec.** A conversation nobody pressure-tested makes a spec full of silent assumptions. Grill first, then write.
- **Beside prototype and research.** When a question turns out to be "I need to see it in action," that is a [prototype](../prototype/SKILL.md); when it is "somebody documented this already," that is [research](../research/SKILL.md). Hand off and keep grilling the rest of the frontier.
- **Not the advisory board.** [advisory-board](../advisory-board/SKILL.md) puts a finished artifact in front of several models for independent review. Grilling is one agent interviewing one human about something that is not finished yet. Grill to reach a position; convene the board to test one you already hold.

## Done when (checkable — verify each line before reporting complete)

- The frontier is empty: every branch of the design tree visited, nothing load-bearing left assumed.
- Every question that needed a fact got one you found, not a fact the decider was asked to supply.
- Every recommendation you made was either accepted or overridden on the record — none left silently unanswered.
- The decider has explicitly confirmed shared understanding. Their last answer is not the confirmation; ask for it.
- Anything that surfaced as a prototype, research, or map-sized question is named as such, with the skill that owns it.

## Hard guardrails

- **Do not act on the understanding.** Grilling produces agreement, not changes. Building, speccing, or filing tickets off the session happens after the decider confirms, as its own move.
- **One round at a time.** Asking the next round before the current one is answered collapses the tree into a questionnaire and loses the reshaping that makes the rounds worth running.
- **Relentless means relentless.** Stopping at the first coherent answer is the failure mode this skill exists to prevent. An unasked question is a decision made silently, by you.

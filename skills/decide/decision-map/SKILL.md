---
name: decision-map
description: Chart or work a decision map for genuinely foggy work — a new primitive, a milestone charter, an integration nobody can spec in one sitting — before any build slice is written. Use when asked to chart a decision map, work a map ticket, or plan a decision-heavy effort whose open questions gate each other.
---

# Decision Map

You are running a decision-map session. The protocol authority is [references/protocol.md](references/protocol.md) — read it first, whole; this skill only sequences the session. If the consuming repo has a domain-vocabulary or context doc (see its team-workflow binding doc, seeded by the setup skill), load that too and use its terms.

A decision map exists to turn fog into recorded decisions. It produces decisions, not deliverables: when the map's frontier is empty, the scope specs and builds as ordinary tracked work.

## Mode 1 — charting a new map (invoked with a scope or destination)

1. Write the destination paragraph first — one paragraph on what "decided" looks like for this scope — then survey the fog against the current code and docs per the protocol's charting section.
2. Choose the weight by fog density (deep → child gate-decision tickets, resolved most-gating-first; shallow → single-sitting adjudication) and say which you chose and why. When the survey finds no fog, take the early exit: write a normal work-item spec instead and say so.
3. Write the map doc, tracked, at `docs/<scope>-decision-map.md` (or the docs home your binding doc names) with both ledgers (Not yet specified / Out of scope) present, even when empty.
4. Deep weight: file the child tickets on the repo's tracker, wire blocking edges between dependent tickets per the protocol's recipe, and post the suggested resolution order (most-gating-first) on the parent ticket.
5. Brief the decider on the map and the first frontier round.

## Mode 2 — working a ticket (invoked with a map ticket)

1. Claim the ticket per the repo's claim recipe (the tracker-discipline binding applies unchanged).
2. Run the ticket by its type per the protocol's ticket-type table (prototype tickets invoke the prototype skill; research tickets follow the research skill).
3. Record the outcome on the ticket, write the one-line verdict back into the map doc, and name any newly unblocked tickets (the frontier moved).

## Done when (checkable — verify each line before reporting complete)

- Charting: the map doc exists tracked in the repo with a destination paragraph, both ledgers, and every surveyed question either ticketed, listed under Not yet specified, or ruled Out of scope with its ruling — no question left unplaced.
- Working: the ticket carries its recorded outcome, the map doc carries the check-off pointer, and blocking edges/labels reflect the new frontier.
- Map close: the protocol's map-done condition holds, verified against both ledgers → parent ticket closed, build work filed normally.

## Hard guardrails

- Sessions brief decisions; the decider decides. On reaching a decision point, record the recommendation and stop there — the round brief is the deliverable, never the answer.
- Deviations from a recorded decision go back to the decider; carry them as questions in the next round brief, never as reinterpretations inside a build brief.

## Attribution

This skill and its [protocol](references/protocol.md) are adapted from Matt Pocock's [`wayfinder`](https://github.com/mattpocock/skills/tree/main/skills/engineering/wayfinder) (MIT), and follow it closely. The core model is his: the destination named before anything is surveyed, the map as an index whose decisions live on their tickets, decision tickets that produce decisions rather than deliverables, the four ticket types, the fog of war with the Not-yet-specified and Out-of-scope ledgers, the fog-or-ticket test, refer-by-name, the no-fog early exit, native blocking edges rendering the frontier, one ticket per session, and create-then-wire filing.

What this repo adds: the weight choice by fog density (deep child tickets vs single-sitting shallow adjudication), the coupling to the binding doc and the named decider, the `gate-decision` label riding the pack's tracker discipline, the edge-vs-`blocked`-label division of labor, and the map-done condition checked against both ledgers.

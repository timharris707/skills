# Decision-map protocol

How a team charts genuinely foggy work — a new primitive, a milestone charter, an integration whose shape nobody can spec in one sitting — before any build slice is written. The core bet: a wrong guess made silently inside a build brief is far more expensive than a decision recorded on a ticket before building starts.

Vocabulary and repo bindings come from the consuming repo's team-workflow binding doc (seeded by the setup skill): the tracker, the claim recipe, the frontier query, and above all **the decider** — the named role that adjudicates decisions in this repo. Sessions brief decisions; the decider decides.

## Standing invariants (every map, every weight)

- **The map doc lives tracked in the repo's docs** (`docs/<scope>-decision-map.md`, or the docs home the binding doc names), so it is reviewable like any other source-of-truth doc.
- **Child tickets ride the existing tracker machinery**: a `gate-decision` type label, the repo's claim recipe, one session per ticket. A map invents no parallel tracker.
- **Adjudication authority is unchanged: sessions brief the decision, the decider decides.** A session that reaches a decision point records its recommendation on the ticket and waits — a grilling ticket is answered by the decider, on the record, before anything downstream builds on it.
- **A map produces decisions, not deliverables.** When the map's frontier is empty, the scope specs and builds normally; deviations from a recorded decision go back to the decider, never into a build brief.

## Charting a map (destination first)

1. **State the destination** before surveying anything: one paragraph on what "decided" looks like for this scope (a speccable milestone, a buildable primitive, an adjudicated slate). The destination bounds every later out-of-scope call.
2. **Survey the fog against current code**: every open question gets a cluster section with the question, why it is foggy, code pins (file:line evidence of what exists today), options with costs, and what it gates.
3. **Choose the weight by fog density**:
   - **Deep fog** (the questions gate each other; a wrong guess reshapes schemas, interfaces, or writer sets): each cluster becomes a child `gate-decision` ticket ("<SCOPE> DECISION: …", body mirroring its map section), resolved **one per session** in most-gating-first order. Child tickets are claimed via the repo's claim recipe like any work item.
   - **Shallow fog** (questions are independent and briefing-sized): adjudicate the whole map **single-sitting** with the decider, verdicts inlined directly in the map doc.
4. **No-fog early exit**: when the survey finds every question answerable from existing decisions, code, or evidence, stop — write a normal work-item spec and file it on the tracker. A map with nothing undecided is overhead, not planning.

## The map doc carries two ledgers (never merged)

- **Not yet specified** — in-scope fog: questions inside the destination that are not yet ticket-shaped (usually because an open decision must land first). Entries here **graduate into tickets** as the frontier advances; an empty section means every known unknown has a ticket.
- **Out of scope** — ruled past the destination by an explicit decision, with the ruling recorded. Entries here **never graduate**; reopening one is a new adjudication with the decider, not a ticket.

Every decided ticket writes back to the map: check the cluster off with a one-line verdict plus a pointer to the ticket (the ticket holds the full record — the map holds the index). The map is done when its frontier is empty AND the Not-yet-specified ledger is empty — every open decision has a ticket or an explicit out-of-scope line.

## Ticket types (four; each human-in-the-loop or autonomous)

| Type | Mode | What it is |
|---|---|---|
| **grilling** (default) | human-in-the-loop | A briefed decision round with the decider (below). The agent looks up **facts** (codebase, docs, evidence archives — never asked of the decider); the decider answers **decisions**. |
| **research** | autonomous | An investigation against primary sources ending in a cited findings file — the research skill's contract. Fire-and-report; multiple research tickets may run in parallel. |
| **prototype** | human-in-the-loop | Throwaway code answering a "how should it look / behave / feel" question via the prototype skill; its bindings live in that skill. |
| **task** | either | Real-world work that unblocks a decision (provision something, run an errand-shaped step, coordinate with a vendor). Rides normal lane discipline when it touches the repo. |

Reach-for guidance between grilling and prototype: simple frames resolve in discussion; questions answerable from existing screenshots or artifacts resolve from those. The moment the question is "I need to see/feel this in action," it is a prototype ticket.

## Grilling runs in frontier rounds

A grilling ticket defaults to **rounds, not one question at a time**: each round briefs the decider with the **entire settled frontier** of open decisions — numbered, each with a recommended answer and the evidence behind it. Sequencing rules:

- A question whose answer depends on another question still open **this round** waits for a later round.
- A background fact-lookup blocks only its own downstream questions — the rest of the round proceeds.
- The ticket is done when the frontier is empty: **nothing left silently assumed.** Any question the session answered for itself is a fact (with a source), never a decision.

Rounds are briefed to the decider; sessions never self-answer a decision.

## Research tickets

A research ticket runs autonomously against primary sources and ends in a cited findings file linked from the ticket. The full contract — source discipline, findings-file shape, and the questionnaire terminal move for facts only an external human holds — is the research skill's; a map's research tickets follow it unchanged.

## Blocking edges (map tickets AND build slices)

Blocked-on-a-ticket work carries a **native tracker dependency edge**, so the frontier un-blocks itself the moment the blocker closes. On GitHub Issues (the pack's reference tracker — see the tracker binding):

```bash
# NOTE: -F issue_id takes the blocker's DATABASE id — not its #number, not its node_id.
# Fetch it with: gh api repos/{owner}/{repo}/issues/<blocker-number> --jq .id
gh api repos/{owner}/{repo}/issues/<child-number>/dependencies/blocked_by -F issue_id=<blocker-database-id>
```

The frontier query dual-reads: a ticket is blocked when it carries dependency edges **or** a `blocked` label (recipe: the setup skill's tracker-discipline reference). The division of labor: **edges are authoritative wherever the blocker is a tracker ticket** (wire the edge; closing the blocker un-blocks the child with no label flip); **the `blocked` label** is the human-readable mirror and the only expressible form for non-ticket blockers — vendor gates, scheduling gates, pending adjudications. A purely edge-backed ticket does **not** carry the mirror label — a stale label would hold it blocked after its edges clear, defeating the self-unblocking; the label rides only while a non-ticket blocker exists and comes off when that blocker resolves.

## Map maintenance and close

- Each decided ticket: record the decision on the ticket, check it off in the map with a one-line pointer, and let the decision reshape the still-open clusters.
- At the map-done condition (§The map doc carries two ledgers): close the parent ticket, and spec/file the build work normally — the map's decisions are the primary sources the build specs link back to.

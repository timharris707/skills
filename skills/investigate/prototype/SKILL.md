---
name: prototype
description: Build throwaway prototype code that answers a design question — UI variants on a live route, or a terminal UI or single shareable HTML file over a pure logic module. Use when a question is "how should this look / behave / feel in action" and discussion or static artifacts cannot settle it.
---

# Prototype

A prototype is throwaway code that answers a question. It is the expensive-fidelity tool: simple frames resolve in discussion, and questions answerable from existing screenshots or artifacts resolve from those — reach for a prototype the moment the question is "I need to see/feel this in action." It runs two ways: as the engine of a `prototype` ticket inside a decision map (see the decision-map skill), and standalone for UI-heavy or state-model-heavy work outside any map.

## Pick the branch

- "How should it **look / behave on screen**?" → [references/UI.md](references/UI.md) — three structurally different variants mounted on the live route.
- "Does this **logic / state model feel right**?" → [references/LOGIC.md](references/LOGIC.md) — a pure candidate module behind a disposable shell: a lightweight terminal UI, or a single shareable HTML file when the demo must travel.

## Bindings (both branches)

- **All prototype code lives on a throwaway `prototype/<name>` branch** cut from the default branch — variants, switcher, terminal or HTML shell, everything. It never merges; the branch is the reference artifact, kept until the winner has shipped.
- **The verdict is the deliverable**: record on the driving ticket which variant won / what the logic answer was, and **why** — that comment is the primary-source pointer the implementing spec links back to, with the branch name for the code.
- **The winner is re-implemented through a normal change** (tests plus whatever verification discipline the repo's binding doc names), using the prototype branch as reference. Promoting prototype code as-is skips the discipline the real change exists for — start fresh and copy judiciously.
- **Prototype branches are exempt from the repo's test-first or coverage rules** — that is the point of a throwaway branch, and the exemption is named in the binding doc's precedence section so agents never deadlock between this skill and a resident test law. The exemption ends the moment re-implementation starts.
- Iterate where the decider is. In-session: react to each variant/run, give concrete feedback, let the next variant encode it. In a lane with no decider in-session, the driving ticket is the iteration channel: post what each round showed and the question it raises, and let the decider's reply drive the next round. Either way, the richness of the recorded design decisions is the point, not the first render.

## Done when (checkable)

- The driving ticket carries the verdict comment (winner + why + `prototype/<name>` branch name).
- The prototype branch holds the final iteration, pushed.
- The working branch you return to is clean of prototype code (`git status` shows none of it outside the prototype branch).
- A follow-on implementation path exists: either the implementing work item is named on the ticket, or the verdict states why none is filed yet.

## Attribution

This skill is adapted from Matt Pocock's [`prototype`](https://github.com/mattpocock/skills/tree/main/skills/engineering/prototype) (MIT), and follows it closely. The core model is his: throwaway code that answers a question, the two branches — UI variants switchable by URL param on a live route, and a pure logic module driven through the paper-hard cases (including the single shareable HTML file) — the `prototype/<name>` branch kept out of main as the primary source, and the verdict captured on the driving issue.

What this repo adds: the decision-map coupling, the re-implementation-through-a-normal-change rule, the test-exemption named in the binding doc, the lane-mode iteration channel, and the checkable Done-when list.

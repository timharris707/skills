---
name: handoff
description: Write a structured session handoff so a fresh session resumes losslessly. Use when context is filling up (around half the window), when wrapping a work session, or when the user says "handoff", "checkpoint", "wrap up", or "save state".
---

# Handoff

Capture where the work stands into one small file so the next session — or a fresh one after a context reset — resumes with zero re-explanation. The handoff is a **pointer, not a transcript**: it says where things are and where the durable records live; it never becomes a running log or a second copy of the plan.

## When to write one

**At roughly half the context window, write the handoff — don't wait for the window to fill.** A context window is the fixed amount of conversation an agent session can hold; as it fills, the oldest details fall away and the quality of long-chain reasoning degrades before the hard limit is ever hit. Writing the handoff at the halfway point captures state while the session can still summarize it accurately, and makes the succession clean instead of a scramble.

Also write one at any natural wrap-up: end of a work session, before a deliberate context reset, or whenever the user asks for a checkpoint.

## Where it goes

The repo's confirmed handoff location — recorded in the team-workflow binding doc at setup time. Default: `.claude/handoff.md` at the project root, untracked, with a session-start hook auto-loading it into fresh sessions (the setup skill seeds that wiring). Never write the handoff under a directory owned by a config-sync pipeline (a synced `.ai/` tree, a distributed settings stub) or inside another tool's preserved output home (a review-decision wiki such as `docs/review-wiki/`) — those locations are spoken for, and sync pipelines can silently overwrite or orphan what you put there.

In repos with an approval-before-edit guardrail: invoking this skill **is** the approval. The skill declares exactly one write — the handoff file at the confirmed location — and an explicit user invocation constitutes approval for that write and nothing else.

## The rules

1. **Overwrite, don't append.** The handoff always represents "where we are right now". Version control and the tracker hold history; an appended handoff decays into a transcript nobody reads.
2. **Pointer, not transcript.** Two to four sentences of state, links into the durable records (the tracker, the plan doc, the changed files) — never pasted code blocks, never a recap of the conversation. If the repo has a living plan or status doc, that stays the durable record; the handoff is the short "resume here" pointer into it.
3. **The stale-NEXT rule.** NEXT points at the tracker query, never enumerates work items. The queue lives on the tracker; a handoff that lists item numbers goes stale the moment any other session claims one, and a session starting from that stale list collides with the claimer. Corollary: **reading a handoff never authorizes starting an item** — the claim recipe always runs first.
4. **GOTCHAS carry the expensive lessons.** Traps, dead ends already ruled out, environment facts that look wrong but aren't — the things a fresh session would otherwise re-pay for.
5. **No secrets, ever.** The session-start hook replays the handoff into every fresh session, so a captured credential replays forever — into every future session's context. Name where a secret lives (the env var, the secret-store path, the wizard stage that produces it), never its value; scan the composed handoff for anything that looks like a token, key, or password and replace it with its pointer *before* the write, then confirm the saved file carries pointers, not values.

## Steps

1. Resolve the target path from the binding doc (default `.claude/handoff.md`; create the directory if needed).
2. Fill the [reference template](references/template.md) — STATE / DONE / NEXT / GOTCHAS — overwriting any existing handoff.
3. Keep it tight and high-signal; apply the five rules above.
4. Tell the user it's saved and that a fresh session (or a context reset) is now safe.

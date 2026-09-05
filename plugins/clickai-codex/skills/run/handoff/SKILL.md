---
name: handoff
description: "Save or recover the current Codex task at a checkpoint, compaction boundary, or requested handoff."
---

# Handoff

Read the [Codex desktop binding](../../../CODEX.md) when this workflow needs harness mechanics, model routing, or recovery.

Save a compact, task-owned checkpoint that lets Codex recover the current work
with its authorization and worker ownership intact. Checkpointing and replacing
the task are separate actions. Continue in the same task through automatic
compaction unless the user requests a transfer.

## Resolve the checkpoint

Read [checkpoint recovery](../../../runtime/CONTINUITY.md). Resolve the bundled
helper from this installed skill's directory. Pass the current project directory
and actual task ID, available as `CODEX_THREAD_ID` when the harness exposes it:

```sh
python3 "<installed-plugin>/runtime/checkpoint.py" --project "$PWD" --task "$CODEX_THREAD_ID"
```

Replace `<installed-plugin>` with the real plugin root, three levels above this
SKILL.md. The helper prints JSON with the canonical project root, task ID, and
checkpoint path. It creates no files. Use the returned path; only its owning task
writes it. A worker returns its own evidence to its parent. If the task ID is not
exposed, obtain it from the current task's app metadata or ask for a dedicated
location. Never guess another task's ID or overwrite a coordinator's checkpoint.

Existing project handoffs, including `.claude/handoff.md`, may provide background
on startup. Leave them unchanged. Loading one never authorizes stale NEXT work.

## When and what to save

Save at meaningful milestones, before an explicit transfer, when the user asks,
and when the harness reports impending compaction. Use active
context usage rather than cumulative usage. Finish the current atomic step, save
and verify, then continue. Do not wait for a manual restart after compaction.

Use [the template](references/template.md). Keep a pointer to the recorded
agreement and current state rather than a transcript. Preserve:

- The current objective, accepted decisions, authorization, and hard stop points.
- Branch/worktree and any uncommitted work; respect no-commit instructions.
- Worker/task IDs and owned process IDs, with status and the check that proves it.
- Completed work and verification evidence for its current revision.
- Pending questions, blockers, and the immediate next step on the current task.
- The tracker query for discovering new work, only when new work is authorized.
- Expensive lessons and pointers to durable decisions.

Overwrite this task's checkpoint. Never append a conversation recap or capture
secret values. Keep the ownership and authorization fields even when trimming.

## Recover and verify

Re-read the saved file and confirm paths and evidence resolve. Check live git,
worker, tracker, and process state before continuing; a saved status is not a
current liveness check. A fork's inherited checkpoint is background until the
new task's authority and ownership are established.

Report the saved path and what was verified. Do not promise lossless recovery:
an unresolved worker, stale evidence, or missing record remains explicitly
unverified. No checkpoint alone permits creating a successor task or archiving
the current one.

## Done when (checkable)

- The resolved task-owned file exists and was re-read after writing.
- Objective, authorization, stop points, ownership, state, next step, verification,
  and pending questions are preserved, with explicit none values where applicable.
- Evidence and paths were checked; stale or unavailable state is labeled.
- Secret values and transcripts are absent; Claude handoffs were not overwritten.
- The user received the path and verification result; current authorized work
  continues unless they requested a stop or transfer.

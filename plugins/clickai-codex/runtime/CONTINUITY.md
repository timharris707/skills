# Checkpoint recovery in Codex

Keep the current task through automatic compaction. Save a compact checkpoint at
meaningful milestones, on request, and when the harness signals impending
compaction. Active context usage matters; lifetime token totals and advertised
model windows do not establish when this task needs a checkpoint.

Resolve `checkpoint.py` beside this document and run it with Python 3:

```sh
python3 "<installed-plugin>/runtime/checkpoint.py" --project "$PWD" --task "$CODEX_THREAD_ID"
```

Use the actual installed path and task ID. The resolver is read-only and returns
JSON. Create the returned parent directory when saving, then write and re-read
the checkpoint. Its location is outside the project and shared across local
account profiles using the same operating-system user. Worktrees of the same
Git repository resolve to the same project identity; task IDs keep writers apart.
If the harness provides a task-owned checkpoint policy already, follow that
policy instead of keeping a second record. Keep a pointer to the saved path in
the current task so it survives ordinary summarization.

Preserve STATE, AUTHORIZATION, OWNERSHIP, DONE, NEXT, PENDING, VERIFY, and GOTCHAS
from [the handoff template](../skills/run/handoff/references/template.md). Record
only facts needed to resume: current agreement and stop points, files and branch,
worker IDs and owned processes, pending answers, evidence, and the next step.
Keep credentials and transcripts out. A subagent returns evidence to its parent;
it writes only its own checkpoint if its identity is independently available.

On resumption, read the checkpoint and project instructions, then verify current
Git, worker, tracker, and process state. A checkpoint records prior state and
adds no authorization. Recover the unfinished task before considering new work.
A project handoff from another harness is background; leave it unchanged.

This package installs no automatic hooks, changes no context limits, and replaces
no global agent file. Its checkpoint workflow works without hook trust or a
custom profile installer. Saving and recovery remain explicit skill steps; it
does not promise automatic or lossless recovery. Add automation only through the
current client's supported, user-approved hook mechanism if a project needs it.

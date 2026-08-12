# Announce-enforcement hook (recipe)

The §4/§5 announce rules are behavioral, and behavior decays over a long session: real orchestrators followed the rule at launch and compressed the per-round repeats away hours in. Where the harness supports tool-call hooks, move the reminder into machinery — the harness fires it on every spawn, and nothing decays.

## Claude Code shape

A `PostToolUse` hook on both spawn surfaces — the subagent tool and the background-task chip tool (`Agent|Task|mcp__ccd_session__spawn_task` matcher) — that injects a reminder into the model's context after every spawn. A matcher of `Agent|Task` alone lets chip launches fire no reminder: the decay class the hook exists to prevent walks around it through the other launch surface. Script (shared location, referenced from settings):

```bash
#!/bin/bash
# Fires after every spawn — subagent (Agent/Task) or background-task chip (spawn_task); reminds the orchestrator to announce.
cat > /dev/null  # consume stdin
printf '%s' '{"suppressOutput":true,"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"[announce-hook] A lane was just launched — subagent or background-task chip. If this session orchestrates (orchestrate skill §4–§5): your next user-visible message must announce this spawn'\''s runner, item, and workspace. Subagent (Agent/Task): model and reasoning effort read from a recorded source — \"session-inherited\" only after confirming nothing was explicitly set. Chip (spawn_task): the spawned session'\''s model/effort are set by session defaults at click time and are not launcher-readable — announce exactly that, never a specific model. Review hand-offs and every re-review round get the same announcement. Not orchestrating? Ignore."}}'
```

Settings entry (user-level settings.json covers every project that profile opens — once per profile, not per repo; a repo-level `.claude/settings.json` entry covers one workspace for all profiles):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Agent|Task|mcp__ccd_session__spawn_task",
        "hooks": [{ "type": "command", "command": "<path>/announce-subagent.sh", "timeout": 10 }]
      }
    ]
  }
}
```

## Composition

- The hook **prevents** the miss; §5's close-out line (`rounds announced: N of N`, alongside the cost line) **proves** compliance after the fact — keep both; neither substitutes for the other.
- Launcher-emitted announce lines (the §7 lane-launch slot's manifest pattern) compose: a conforming launcher prints the ready-made line and the orchestrator relays it; the hook still fires as the backstop for harness-direct spawns.
- The reminder is scoped ("if this session orchestrates") so non-orchestrating sessions in the same profile pay only the injected sentence, not false announcements.
- Setup may offer wiring this per-repo where the harness is Claude Code; the recorded binding line is what audit mode checks. An installed matcher missing the chip tool is an audit finding — half the launch surface is unenforced.

# Announce-enforcement hook (recipe)

The §4/§5 announce rules are behavioral, and behavior decays over a long session: real orchestrators followed the rule at launch and compressed the per-round repeats away hours in. Where the harness supports tool-call hooks, move the reminder into machinery — the harness fires it on every spawn, and nothing decays.

## Claude Code shape

A `PostToolUse` hook on the subagent tool (`Agent|Task` matcher) that injects a reminder into the model's context after every spawn. Script (shared location, referenced from settings):

```bash
#!/bin/bash
# Fires after every Agent/Task spawn; reminds the orchestrator to announce.
cat > /dev/null  # consume stdin
printf '%s' '{"suppressOutput":true,"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"[announce-hook] A subagent was just launched. If this session orchestrates (orchestrate skill §4–§5): your next user-visible message must announce this spawn'\''s runner, model, and reasoning effort, read from a recorded source — \"session-inherited\" only after confirming nothing was explicitly set. Review hand-offs and every re-review round get the same announcement. Not orchestrating? Ignore."}}'
```

Settings entry (user-level settings.json covers every project that profile opens — once per profile, not per repo; a repo-level `.claude/settings.json` entry covers one workspace for all profiles):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Agent|Task",
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
- Setup may offer wiring this per-repo where the harness is Claude Code; the recorded binding line is what audit mode checks.

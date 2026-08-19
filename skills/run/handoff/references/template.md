# Session handoff template

<!-- The handoff skill's reference template. Written at session wrap-up to the repo's
     confirmed handoff location (conventionally an untracked, auto-loaded file like
     .claude/handoff.md; the binding doc names it) so a fresh session resumes without
     re-explanation. Overwrite on each wrap-up; it is "where we are right now", never
     a running log. The tracker and the repo's tracked docs remain the durable record;
     the handoff is only the hot pointer. -->

# Handoff: <short task name>
_Updated: <date> · Branch: <branch>_

## STATE

<2–4 sentences: exactly where things stand right now.>

## DONE (this session)

- <what actually shipped/changed, with file paths>

## NEXT

<!-- THE STALE-NEXT RULE: NEXT points at the tracker query, never enumerates items.
     The work queue lives on the tracker; a handoff that lists specific item numbers
     goes stale the moment any other session claims one, and a session that starts
     from that stale list collides with the claimer. Reading a handoff never
     authorizes starting an item; the claim recipe always runs. -->

1. Run the frontier query (see the team-workflow binding doc) and claim from it.

## GOTCHAS / DON'T-REPEAT

- <traps, dead ends already ruled out, things that look right but aren't>

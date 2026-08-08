# Lane brief template

How a tracked work item becomes a working brief for the session (human or agent) implementing it. The item is the spec — the brief adds only standing constraints and lane mechanics, **never a second copy of the requirements**. A brief that paraphrases the spec creates two sources of truth that drift; a brief that pastes it verbatim cannot.

## Before generating the brief

1. Pick the item from the frontier (the binding doc's frontier query — it dual-reads dependency edges and the `blocked` label).
2. Claim it per the claim recipe (read-before-write; a live `Lane-start` refuses you).
3. Branch off the default branch; note anything the lane must pin at start (sequence numbers, environment facts) so parallel lanes can't collide on them.
4. Decide the verification set from the binding doc's verify commands (and the repo's tiering, if any) — name it in the brief so "done" is defined before work starts.

## The brief

```markdown
# Lane brief — item #<N>: <title>

## Spec
The spec is item #<N> (body pasted below verbatim — do not reinterpret; deviations go in
the summary's "Deviations" section, and deviations from a recorded decision go back to
the decider, never silently into the work).
<item body, verbatim>

## Required reading (load before writing code)
- <the repo's domain/context docs, per the binding doc>
- <the domain-memory home — glossary + recent decision records — where the repo binds it>
- <the team-workflow binding doc itself>

## Standing constraints (every lane)
- Verification: <the named verify commands for this item>.
- Check every verification command's own exit code — piped or filtered output is not
  evidence (a pipeline reports the last command's status, so `<cmd> | tail` reads green
  whenever `tail` does).
- Commit discipline: checkpoint commits on the lane branch, short imperative subjects;
  merging is the reviewer/integrator's move, not the lane's.
- <the repo's own standing constraints, from the binding doc's precedence section>

## Output contract
Write a summary containing:
1. What landed (by file).
2. Verification you ran (commands + results verbatim).
3. Deviations from the spec + open questions.
The summary posts back to item #<N> as a comment — write it for that audience; the
tracker comment is the durable record.
```

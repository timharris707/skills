# Lane brief template

How a tracked work item becomes a working brief for the session (human or agent) implementing it. The item is the spec — the brief adds only standing constraints and lane mechanics, **never a second copy of the requirements**. A brief that paraphrases the spec creates two sources of truth that drift; a brief that pastes it verbatim cannot.

**Runner-agnostic by construction**: the same brief must work whichever runner the launch policy names — Claude, Codex, or a human. Beside the verbatim paste, cite the spec by issue reference (the item id plus the tracker command that fetches it, e.g. `gh issue view <N> --comments`) so any runner can re-pull the authoritative text, and keep the brief free of harness-specific assumptions — one harness's tool names or session mechanics. The orchestrate skill's runner-parity reference names the full standard a launcher meets.

## Before generating the brief

1. Pick the item from the frontier (the binding doc's frontier query — it dual-reads dependency edges and the `blocked` label).
2. Claim it per the claim recipe (read-before-write; a live `Lane-start` refuses you).
3. Branch off the default branch; note anything the lane must pin at start (sequence numbers, environment facts) so parallel lanes can't collide on them.
4. Decide the verification set from the binding doc's verify commands (and the repo's tiering, if any) — name it in the brief so "done" is defined before work starts.

## The brief

```markdown
# Lane brief — item #<N>: <title>

## Spec
The spec is item #<N>, fetchable via `<the tracker command that shows it, e.g. gh issue view <N> --comments>`
(body pasted below verbatim — do not reinterpret; deviations go in
the summary's "Deviations" section, and deviations from a recorded decision go back to
the decider, never silently into the work).
<item body, verbatim>

## Required reading (load before writing code)
- <the repo's domain/context docs, per the binding doc>
- <the domain-memory home — glossary + recent decision records — where the repo binds it>
- <for bug-shaped items: the diagnose skill — no fix ships without a named cause>
- <for build-shaped items: the implement skill — seam-scoped test-first, tracer-first, file-don't-fix>
- <the team-workflow binding doc itself>

## Standing constraints (every lane)
- Verification: <the named verify commands for this item>.
- Check every verification command's own exit code — piped or filtered output is not
  evidence (a pipeline reports the last command's status, so `<cmd> | tail` reads green
  whenever `tail` does).
- Commit discipline: checkpoint commits on the lane branch, short imperative subjects;
  merging is the reviewer/integrator's move, not the lane's.
- Where this lane itself files a PR (e.g. a cross-repo lane): it must follow the orchestrate
  skill's pr-writing reference — problem-first description, no implementation inventory,
  no draft unless repo policy says otherwise, provenance blurb.
- <the repo's own standing constraints, from the binding doc's precedence section>

## Output contract
Write a compact summary containing:
1. What landed (by file), with the diff stat.
2. Verification you ran (each command with its own exit code), ending with `Skipped checks: none` — or every skipped check named, with why.
3. Deviations from the spec + open questions.
Quote only the load-bearing hunks or sentences — never the full diff or transcript;
the orchestrator audits the diff in your workspace, and everything it ingests it
re-pays on every later wake.
The summary posts back to item #<N> as a comment — write it for that audience; the
tracker comment is the durable record.
```

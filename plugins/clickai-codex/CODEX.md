# Codex desktop workflow

These are the Codex desktop bindings for this edition. Apply them to
desktop execution; keep the repository's domain rules, verification requirements,
decision records, and integration permissions. An old Claude runner, chip, hook,
or handoff recipe in a binding document describes that harness, not a requirement
to launch Claude from Codex. Current user instructions and the actual tool schemas
take precedence over this reference.

## Task scope and decisions

Answer a question read-only. Continue authorized work when a side question or
correction arrives; incorporate the update without discarding the original goal.
Reuse recorded approvals and settled decisions. Ask about material unresolved
choices, not routine implementation details the evidence already settles. A
skill's optional procedure does not create a new approval requirement.

For a bounded answer or review, deliver in the current task without creating a
tracker item, branch, or setup interview. For tracked development, use the bound
tracker and claim discipline. Explicit instructions to build, file, or publish
define the permitted work; reading a skill, handoff, or tracker item adds no scope.

## Model and effort

Use the user's selected model and effort. This edition is tuned for Astra at
medium and extra high; that is workflow guidance, not a benchmark claim or a
model requirement. Extra high is appropriate for difficult design, diagnosis, and important
reviews when selected or allowed by the task's recorded review policy. A skill
does not silently change the running model or effort.

For delegated work, read the live spawn schema. Full-history forks inherit model
and effort and cannot take overrides in this harness. Fresh, bounded briefs can
select a supported model and effort when authorized. Mechanical checks usually
need a shell command, not another model. Independent reviewers receive fresh
contexts and raw evidence, without the implementer's conclusions. State the
number of model calls and rough usage before a review or evaluation batch.

The model catalog, active runtime context, and configured ceiling can differ.
Use reported active-context usage for checkpoints, never cumulative lifetime
tokens. Respect the active account and client settings; do not infer a desktop limit from an API catalog.
Medium versus extra high is an effort choice, not a reason to hand off the task.

## Delegation and workspace ownership

Use `collaboration.spawn_agent` for a concrete independent subtask when the user
or the applied skill authorizes delegation. Inspect `collaboration.list_agents`
before assuming capacity or ownership. Reserve slots for required reviewers and
run independent passes in separate batches if necessary. Sequential passes in
one context are not isolated reviewers.

Subagents share the filesystem and initial working directory. Provision a
separate worktree explicitly for each concurrent writer and put its absolute path
in the brief. Read-only reviewers can share the reviewed workspace. Respect
project-specific worktree placement.
Record each worker's agent ID, worktree, branch, permitted writes, and owned
process IDs. The coordinator integrates one result at a time.

An interrupted agent remains available for `followup_task`; inspect its state
before resuming or replacing it. A completed shell process and a stopped model
turn are different states. An interruption does not erase uncommitted files.
Checkpoints should preserve useful work within the user's commit instructions.

Use app `create_thread` only when the user explicitly requests a separate task. Other
task tools can inspect or coordinate existing tasks as authorized. A user-owned
task can be resumed by `send_message_to_thread`. `handoff_thread` moves another
task and its Git state between a checkout and worktree, or to a supported host;
it is not a context reset or a transfer of orchestrator ownership.
A fork copies completed history and retains its context cost. It does not copy
the unfinished turn or transfer active workers.

## Waiting and user input

Stay in the active task while work is authorized. Codex accepts mid-turn steering;
ending the turn merely to receive messages is unnecessary. Answer incoming user
messages promptly, then continue dependent and independent work as appropriate.

Wait for actual state changes through the available agent or task tools. For
desktop tasks, use `wait_threads` with cursors and bounded waits. For subagents,
use their completion notifications and `wait_agent`; check liveness when an
interrupt or timeout makes it uncertain. Bound blocking waits to 60 seconds so
you can remain responsive. If watching external PR/CI state, state a cadence
appropriate to its latency, normally 2-4 minutes, and actually poll on it. A wait
notification does not prove that external CI or review state was checked.

Show meaningful progress with concrete counts. Quiet unchanged monitoring does
not need a status line on each poll. A later wakeup requires an actual app
automation when the user requests continuing later; a shell sleep does not schedule
a new model turn. Choose polling for task health, not an assumed five-minute
cache expiry. Provider cache retention is checked in current documentation.

Use the question tool actually available in this mode. In Default mode,
`request_user_input_async` can collect preferences or missing facts while useful
independent work continues. Do not use a Plan-only tool outside Plan mode. Honor
the current schema's limits rather than Claude's four-card convention. Pending
required answers stay pending: elapsed time or a preselected option is not consent.

## Checkpoints and recovery

Read [checkpoint recovery](runtime/CONTINUITY.md) when saving or resuming work.
The bundled resolver gives each task a stable checkpoint outside the repository.
Save at meaningful boundaries and when the harness reports impending compaction;
then continue in the same task through native compaction. A new task is a
user-requested change of ownership, not a half-window ritual. This package does
not install global hooks or modify context settings. Recovery depends on saving
the checkpoint and following these instructions; it is not a lossless guarantee.

Only the owning task writes its checkpoint. Workers report through their own
artifacts and IDs. Preserve the latest authorization, stop points, accepted
decisions, worktree/branch, worker and process ownership, pending questions,
verification, and the immediate next step. The tracker query is for discovering
new work; it must not replace the unfinished current task. Read old project
handoffs as background, and never overwrite Claude's handoff from this workflow.

After compaction, re-read the task checkpoint, project instructions and relevant
decisions, then verify live worker, git, tracker, and process state before acting.
Do not automatically replay old NEXT items or duplicate a running worker.

## Resources and validation

Resolve the real installed `SKILL.md` path before following relative references
or running its scripts. Helpers belong to that skill directory, not the project
working directory. Keep script outputs outside the shared skill deployment.

Run the checks that establish the requested behavior and the repository's
mandatory gates. Once the same revision has passed them, broaden or repeat only
for a changed revision, a failure, or an unresolved concern. Small reversible
edits need appropriate validation, not tests that duplicate implementation.
Reported bugs retain a regression check that would catch recurrence.

Read every unresolved review finding regardless of its timestamp. A push does
not answer a finding; verify its disposition against current code. Use current
commit results for CI, with per-command exit codes. The review report distinguishes
actual independent review from a single agent's multiple perspectives.

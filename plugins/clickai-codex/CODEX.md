# Codex desktop workflow

These are the Codex desktop bindings for this edition. Apply them to
desktop execution; keep the repository's domain rules, verification requirements,
decision records, and integration permissions. An old Claude runner, chip, hook,
or handoff recipe in a binding document describes that harness, not a requirement
to launch Claude from Codex. Current user instructions and the actual tool schemas
take precedence over this reference.

## Capability evidence and portability

This reference separates three sources of guidance. Check the current client and
live tool schemas before applying a desktop-specific recipe in another harness.

| Kind | Evidence and scope | What to recheck |
| --- | --- | --- |
| Documented skills | [Build skills](https://learn.chatgpt.com/docs/build-skills) describes skill discovery and front-loading use cases and trigger words in budgeted descriptions. | Installed paths and the current discovery list; concise descriptions must preserve distinct use cases. |
| Documented model identifier | [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) documents `gpt-6-astra`. | The selected account, CLI/provider route, supported effort, and actual model resolution. A catalog entry does not grant access. |
| Documented hooks | [Hooks](https://learn.chatgpt.com/docs/hooks) describes Codex hooks and their trust review. | Installed and approved hooks in the user's client. This package installs none; that is a packaging choice, not a capability limit. |
| Desktop-observed tools | `collaboration.*`, `request_user_input_async`, and app task tools such as `handoff_thread` have been exposed by desktop tool schemas. These observations are not a universal CLI contract or public API guarantee. | Discover the actual tools, arguments, mode restrictions, workspace ownership, and supported models in this task. |
| Edition workflow policy | Preserve task ownership through compaction, use scoped independent review, and respect the selected model and project rules. | Current user authorization and project requirements, which take precedence over this reference. These are chosen procedures, not measured model-performance claims. |

If delegation tools are absent, perform authorized work locally when the required
independence permits it; if independent review is required, report that gate as
pending rather than pretending multiple perspectives in one context are separate
reviewers. If an app task-movement tool is absent, save a checkpoint and provide
manual recovery instructions when a transfer is requested. Do not invent a tool
name, invoke a CLI imitation, or create a new task to bypass a missing capability.

For any provider-backed model route, verify the installed command and account
configuration, and establish requested-model resolution with authorized preflight
before calling it launch-ready. Never silently substitute a model. An unknown
route stays unverified; a rejected selection is a failed check. A smoke call
consumes model usage and needs the applicable provider authorization.

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

Use the user's selected model and effort. This edition is adapted for Codex
desktop and Astra workflows at medium and extra high; this describes workflow
policy, not a benchmark result or a model requirement. Extra high is appropriate for difficult design, diagnosis, and important
reviews when selected or allowed by the task's recorded review policy. A skill
does not silently change the running model or effort.

For delegated work, read the live spawn schema. In the observed desktop contract,
full-history forks inherit model and effort and cannot take overrides. Fresh, bounded briefs can
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

In the observed desktop contract, subagents share the filesystem and initial
working directory. Verify the current worker workspace contract before writing. Provision a
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

Use a question tool only when its live schema exposes it in the current mode.
Some desktop tasks expose `request_user_input_async` for collecting preferences
or missing facts while independent work continues; other tasks do not. A
Plan-only tool must stay in Plan mode. If no compatible tool is available, ask a
concise plain-text question in the permitted user-facing channel and pause
dependent work while required input is pending. Honor the current schema's limits.
Elapsed time or a preselected option is not consent.

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

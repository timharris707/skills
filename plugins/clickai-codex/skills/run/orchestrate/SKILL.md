---
name: orchestrate
description: "Play the lead developer of an agent team in Codex: delegate, monitor, verify, and integrate tracked work while the human brings the decisions."
---

# Orchestrate

Read the [Codex desktop binding](../../../CODEX.md) when this workflow needs harness mechanics, model routing, or recovery.

This is the seat a non-engineer sits in. Everything else in the pack is something a developer does; this skill is how one session plays the lead that decides which of those happens next and runs it. The human brings the idea and the decisions; the seat brings the team. The rules below are strict because a lead that drifts costs the human their afternoon.

One session coordinates many. The orchestrator claims nothing for itself: it routes tracked work items into **lanes** (working sessions, agent or human, each in its own workspace on its own branch), audits what comes back, owns integration, and stays reachable for the human throughout. This skill is the portable protocol: principles, plus **binding slots** (§7) for the machinery every repo does differently. It is rule-based: do every step, every time, because memory-only protocols drift.

Read the team-workflow binding doc first. The tracker discipline (claims, frontier, blocking; [setup's references](../../orient/setup/references/tracker-discipline.md)) is assumed throughout. Measurements behind the cost-shaped rules: [references/evidence.md](references/evidence.md).

## 1. The orchestrator is a router, not a worker

1. **Turn discipline.** Stay in the active Codex task while authorized work continues. User messages can arrive mid-turn. Keep waits bounded and use the live agent/task tools to stay responsive; a final answer is not a wake timer.
2. **Delegate execution, keep judgment.** Long verification and mechanical fixes go to delegated sessions; you read their reports, spot-check the load-bearing claims, and own routing, adjudication-surfacing, and the merge. Delegation moves the **executor**, never the **standard**.
3. **Respond first.** On any re-invocation, answer a waiting user message before resuming queued work.
4. **Preserve context.** Delegate substantial independent execution when useful, and hold judgments and compact state rather than full logs. A duration alone does not force a new worker or an early final answer.
5. **Monitor actual state.** State a polling cadence for external PR/CI state, normally 2-4 minutes, and perform it while work is live. Agent completion notifications and task waits handle worker events. Bound blocking waits to 60 seconds and report meaningful changes. Use current provider evidence for cache economics; no fixed five-minute expiry or keep-warm model call is required. Continuing after the active turn needs a supported automation when the user requests it.

## 2. The single-orchestrator rule

**Exactly one live orchestrator at a time.** Check for other active sessions before claiming or launching anything: a running session beats an unclaimed item; an existing orchestrator beats a new one. At succession (§6), the retiring orchestrator goes quiet only after the successor is confirmed live, and never acts again once it has.

## 3. Startup checklist

1. Read the current task-owned checkpoint first, then verify its agreement and live ownership. A previous project handoff is read-only background, never authorization for old work. Run the claim recipe when taking new tracked work. Where a domain-memory home is bound, read the glossary and relevant active decisions.
2. Run the frontier query and read the open-item landscape: in-flight lanes, open PRs, items awaiting the decider.
3. Check for other active sessions (§2).
4. **Title the session**, after the §2 check unless §8's pre-titling carve-out applies; a session that must stand down never wears the title.
5. Start the repo's standing watches; the **monitoring binding slot** (§7) names what they cover. Confirm the watch runs rather than asserting it; investigate any event it raises immediately, after any waiting user message (§1).

## 4. Launching lanes

- **Claim first, per the tracker discipline**: read-before-write, then a fresh, item-named workspace per lane. Start and record the lane per the **lane-launch binding slot** (§7).
- **Pick the runner from recorded policy (§7), never habit**: before the claim, which stamps the runner. Launcher standard: [references/runner-parity.md](references/runner-parity.md).
- **A failed launch is a launch defect**: diagnose per the repo's launch tooling and retry on the policy-named runner; only then fall back, LOUD, never silent: launch report AND tracker item carry `runner fallback: X→Y, reason`.
- **Brief from the lane-brief template** ([setup's templates](../../orient/setup/references/templates/lane-brief.md)): spec verbatim, named verification set, standing constraints, and the integration rule: workers save verified results within the user's commit instructions and stop; the orchestrator owns review and merge. Everything else travels by context pointer, to the item, notes, and prior commits, never duplicating what a pointer reaches. It points at a bound [domain-memory](../../orient/domain-memory/SKILL.md) home; bug-shaped briefs also at [diagnose](../diagnose/SKILL.md), build-shaped at [implement](../implement/SKILL.md). A lane expected to run unattended keeps a decision trail per [show-me-your-work](../show-me-your-work/SKILL.md), named in the brief, so the close-out audit and the human read a decision table, not a recap.
- **Launch reports are for the human: read, never guessed.** Every launch and lane mention names runner/model/session, item, and workspace, legibly enough to tell lanes apart. Unless the toggle (§7) records `off`, add the reasoning-effort level; the toggle governs only the additions (effort line, §5 repeats, close-out cost line), never identity. Every announced value comes from a recorded source (policy table, launch manifest/config, an explicit setting); "session-inherited" only after those were read and set nothing; a plausible guess is a protocol violation. A chip launch's model/effort are session defaults at click time, unreadable to the launcher: announce exactly that, never a specific guess. Compliance decays over long sessions ([evidence](references/evidence.md)); where tool-call hooks exist, enforce the reminder in machinery per [references/announce-hook.md](references/announce-hook.md), which also carries the launcher-manifest pattern; setup may offer wiring it.
- **Every picker-visible lane session is titled with its item at launch** (§8).
- **Honor the selected model and effort.** Use the current task selection. Fresh workers may use a policy-approved model and effort supported by the spawn tool. Full-history forks inherit both. The user can change effort in the same task; that is not succession. Do not switch models merely to run a shell check or to refresh context.
- **Lane count is a cost dial**: every lane pays a first-write of its whole brief and startup context. Where the tracker discipline allows, trivially-related small items ride one lane serially, or continue an existing lane by message where resuming is supported. The dial never overrides isolation where items conflict.
- **Subagent or separate task.** Use a subagent for a bounded delegated work item. Create a sidebar task only when the user explicitly asks for one; otherwise keep ownership in the current task. A separate user-owned task can be coordinated through the available task tools. Read the actual permission and lifecycle support before choosing a vehicle. All concurrent writers receive explicitly provisioned worktrees because Codex subagents share the filesystem and starting directory.
- **After an interrupt, check liveness and intent.** Inspect worker state, files, and owned processes. An interrupted Codex agent may resume through `followup_task`; an existing desktop task may resume through its message tool. Replace only a worker that cannot continue, carrying its completed work and current authorization forward. Respect a user stop before restarting anything.

## 5. Close-outs (one lane at a time; never two merges racing)

When a lane enters close-out review, announce the hand-off per §4's announce discipline (identity unconditional, the model/effort repeat as the toggle-governed addition), naming the reviewing agent or session, never merely a review type. Every re-review round is announced the same way.

1. **Audit the lane's summary against its verification contract; never trust self-reported greens.** Verify the results against the current revision in the worker's workspace. Re-run checks when the revision changed, evidence is incomplete, or a specific concern remains; a complete current CI result can satisfy its named check. Use the recorded executor policy for independent verification. Require per-command exit codes, zero skipped checks; piped or filtered output is not evidence. Spot-check the verifier's load-bearing claims yourself before merging. Read the diff **in the lane's workspace at the item's scope**: compact inventory first (`git diff --stat`/`--name-status`), then targeted hunks, never wholesale into your own context (§1 item 5; no-filter binds exit-code capture). A too-large diff goes to the delegated verifier to read in full and report compactly. A bug fix shows [diagnose](../diagnose/SKILL.md)'s two closing artifacts: the cause in one plain sentence, and the regression test or its flagged manual-repro fallback; an unnamed cause is not done. A build item shows [implement](../implement/SKILL.md)'s three: tests passing at every named seam, an identifiable tracer slice, no out-of-scope files, never commit-by-commit forensics.
2. **Where the repo binds the [adversarial-review skill's](../adversarial-review/SKILL.md) close-out layer, run it here**: against the lane's branch, before merge. The implementer never has the last word; a confirmed blocker gates the merge and only the decider may waive it.
3. **Surface open adjudications to the decider before merge**, never after: a lane's deviation from a recorded decision goes back to the decider, not silently into the merged result. Use the decider's recorded guidance when its source and scope are verifiable. An unsupported agent paraphrase is context; verify the original before attributing or expanding permission.
4. Merge per the repo's **merge-flow binding slot**; any PR filed follows [references/pr-writing.md](references/pr-writing.md). Post the close-out on the tracker item. Unless the toggle records `off`, it carries the cost line, build vs total review tokens across all rounds, with round count (`review: 3 rounds, ~175k tokens`), read from per-agent spend reports or stated "not readable in this harness", never an estimate. Report a missed external monitoring interval when it delayed attention; do not infer cache charges from elapsed time alone. And the announce-compliance line: `rounds announced: N of N`; N counts the launch plus every review round.
5. **Prune the lane**: workspace, branch, per-lane resources. Check for uncommitted work and surface it before pruning. Verify its processes are dead yourself before tearing down shared resources: a "servers down" claim is not evidence.
6. **Last of all, hand the dead lane's session to the human for archiving.** Only after merge, tracker close-out, and pruning, tell the human, naming the session **verbatim as the picker shows it**, that the lane is safe to archive; they archive on their own time. Never call an archive surface yourself; retitle the finished lane first if useful (no confirmation needed). Archive, never delete; name only the closed-out lane's session, never a human's working session. Archiving trails everything: an unanswered notification gates no work. Native auto-archive on PR close fires at merge time: use it for PR-linked lanes only where the lane has stopped, the workspace is done with, and the tracker close-out doesn't need the session live; otherwise record `no` and notify. Subagent lanes have nothing to archive.

## 6. Checkpoint, continue, or transfer ownership

1. At the measured context checkpoint or a meaningful milestone, finish the atomic step and write the task-owned checkpoint through [handoff](../handoff/SKILL.md). Preserve authorization, stop points, workers, processes, workspaces, evidence, and the current next step.
2. Continue in the same task through native compaction. Re-read the checkpoint, project instructions, relevant decisions, and live state afterward. Half a context window does not retire the coordinator.
3. A fresh task requires the user's request. On an explicit ownership transfer, give the successor the verified checkpoint and the current worker inventory. Start no competing integration while the transfer is pending.
4. Confirm the successor completed the startup checks and accepted ownership before retiring the old coordinator. Stop only watches owned by the retiring coordinator, update its title when supported, and record the transfer. A fork or checkout handoff alone transfers no live ownership.

## 7. Binding slots (the setup interview fills these per-repo)

The pack ships **no orchestration machinery**: launcher scripts, monitor daemons, provisioning tooling, verification-tier tables all encode a repo's blast radius and belong to it. The binding doc's orchestration section names, per-repo:

- **Lane launch**: how a working session starts; what is stamped on the tracker item (runner, model, workspace, branch); titling mechanism/actor and which surfaces pre-title (§8 governs the rest; the slot never opts a repo out of titling the harness supports); the decider's **runner policy**: available runners, launch mechanism for each, preference policy (launchers built to [references/runner-parity.md](references/runner-parity.md)); whether native auto-archive on PR close is safe per §5 step 6 (`yes`/`no`; no slot puts an archive surface in the orchestrator's hands); and the **announce toggle** (`announce model/effort: on/off`, default on) with §4's scope; only the recorded line is a valid off-switch, so audit mode can check it.
- **Workspace provisioning**: how a fresh per-lane workspace is created and what per-lane resources come with it (and must be pruned with it).
- **Monitoring**: how the orchestrator watches open PRs, inbound tracker activity, and lane liveness between turns, and how it confirms the watch is armed; the interval follows the observed system latency and §1 item 5.
- **Verification executor**: who re-runs verification at close-out (delegated verifier, CI, inline) and where per-command results land; plus the decider's **review-tier policy**: a table mapping close-out machinery (mechanical re-runs, finders and skeptics, re-probes) to model + effort. Canonical shape: mechanical verification cheap at low effort; adversarial review on real code or release-arming changes high; max only for decider-named cases, never a default. Each tier records a **floor** as well as a ceiling, what it may NOT be used for, so cost-saving never silently weakens the review bar. Tier deviation is loud in both directions, announced per §4.
- **Merge flow**: the repo's integration mechanics and who may push what where.

A repo that has not filled these slots can still run the principles, but fill them before scaling up.

## 8. Titling

Titles keep picker, tracker, and workspace speaking one name, and the §2 check working by eye. That titling happens, and what a title carries, is protocol; mechanism and actor are the lane-launch slot's (§7).

- **Orchestrator title**: default `Orchestrator — <repo>`, after the §2 check clears, the session telling its launcher once it does (§3 step 4). A binding may refine the shape so long as it says *orchestrator* and tells siblings apart; retirement adds the retired marker (§6 step 4).
- **Lane title**: default `#<N> — <short item name>` in the repo's own item notation, at launch, carrying the item id the claim and workspace already carry; a binding may refine the shape so long as the id survives. In-process subagents have no picker entry; the launch report carries the name.
- **Actor**: whoever launched the session titles it; self-titling only where the harness supports it: a session that cannot rename itself never attempts it. A retitle the harness can't self-perform (§6's retirement marker) falls to the successor or the human.
- **A role change retitles**: a lane adopted mid-flight or a session promoted to orchestrator is retitled the moment the role changes, same actor rule.
- **The carve-out: pre-titling surfaces.** Some launch surfaces fix the title at spawn from their own label: the launcher is the titling actor then, and the title protocol outranks the surface's label convention: a chip-arranged successor gets the orchestrator shape, never a generic imperative task label. Pre-titling precedes the §2 check (the only ordering exception); one that stands down is retitled by whoever archives it.
- **Degrade**: no titling surface at all → the launch report carries the name, and retirement is recorded in the handoff and final report.

---
name: setup
description: "For a new TeamWorkflow installation, binding refresh, or drift audit after a pack release, inspect and bind the project workflow. Reuse explicit recorded decisions with their sources; ask about missing, conflicting, or changed authority and bindings."
---

# Setup

Read the [Codex desktop binding](../../../CODEX.md) when this workflow needs harness mechanics, model routing, or recovery.

This skill binds the team-workflow pack to a specific repo, once, through an interview, and refreshes that binding on re-run. Everything the other pack skills call "the binding doc" is what this skill seeds. Nothing here rewrites the repo's CI or processes; it records how the pack composes with what is already there.

**Posture: inspect first, reuse decisions.** Scan the tracker, verification commands, instruction files, templates, installed skill paths, and configuration ownership. Reuse explicit recorded bindings and prior answers under the safeguards below. Ask only about a new binding, material drift, or an unresolved choice. A read-only installation audit needs no setup interview or tracker write.

## The five mandatory bindings

1. **Tracker.** The repo + tracker in use, and the mapping onto the pack's tracker discipline: how claims are posted, how blocking is expressed, what the frontier query is. The pack is GitHub-Issues-first (the recipes in [references/tracker-discipline.md](references/tracker-discipline.md) use `gh`), but the tracker is a **named binding**, not an assumption baked into the skills: a repo on a different tracker writes a different tracker section in its binding doc, mapping the same discipline (machine-readable claims, dependency edges, a frontier query) onto its own tool. The skills stay unchanged.

   **Implicit-repo check (GitHub trackers):** at binding time, compare gh's implicit repo resolution in the working directory (`gh repo view`) against the bound repo. A fork or multi-remote clone commonly resolves to the *upstream* repo, and every recipe run unqualified would then read and write tracker state there, not on the bound tracker. On mismatch, warn and record it in the tracker binding. The recipes scope `gh issue` and `gh label` with `--repo <owner>/<repo>` and write the bound repo literally into every `gh api` path (see tracker-discipline), precisely so this mismatch stays harmless; do not lean on `gh repo set-default`, which is per-clone state the next worktree or machine doesn't have.

   **A repo with no tracker yet** is a normal starting state, not a setup failure. Offer two honest paths and record whichever the human picks: (a) **bind one now**: on a GitHub remote that usually means the repo's own GitHub Issues, ready immediately; (b) **record `none yet`** as the tracker binding, with the consequence stated in the doc: the claim, frontier, and blocking recipes stay dormant until a tracker is bound. Never invent a tracker the team doesn't use, and never leave the field blank.

   **Label vocabulary on a fresh tracker:** the pack's recipes assume the labels they query already exist: a frontier query against labels nobody created returns empty forever, and nothing downstream ever creates them. When binding a tracker that lacks them, setup enumerates the pack's reference vocabulary (state: `needs-triage`, `ready-for-agent`, `ready-for-human`, `blocked`; type: `slice`, `bug`, `gate-decision`, `process`) and, on confirmation, creates the missing ones (on GitHub: `gh label create "<label>" --repo <owner>/<repo>`, one per missing label, a declared write) or records the creation instruction in the binding doc for trackers setup cannot drive. A repo with existing labels maps them instead via the optional label-vocabulary binding; nothing gets renamed.
2. **Verify commands.** The exact commands that constitute "verified" in this repo (typecheck, lint, test, build, whatever the repo runs), recorded so every brief and template can name them instead of guessing. A repo with no toolchain yet records an explicit **`none yet`**, never a guessed or aspirational command that would let briefs claim a verification nobody can run.
3. **The decider.** Who adjudicates decisions in this repo. Reuse only an explicit recorded decision-maker binding and cite its file or decision-record source. Ask when that binding is missing, conflicting, or there is evidence it changed; never infer authority from Git authorship, an account, or a remembered name. Current user instructions take precedence over a recorded role. Until resolved, pause only work that depends on that authority. Every pack skill says "the decider"; this binding is where that role gets a name. A repo without a clear answer here is not ready for the pack's decision discipline; surface that honestly.
4. **The binding-doc home.** Where the anchor binding doc lives. Default: `docs/agents/team-workflow.md`. Reuse the confirmed home, and ask only when it is new or changing: repos with config-distribution pipelines can make the default location wrong in ways only a human knows.

   The home must be **git-tracked and outside anything a sync pipeline manages**, stated so a config-pipeline owner can sign off from reading alone: (a) bindings are shared, per-repo team decisions, so they belong in version control where edits are reviewed and history survives, not in per-machine synced files; (b) sync pipelines republish and checksum what they manage, so a binding doc inside a synced tree is either clobbered on the next sync or turns every team edit into a fight with the pipeline.

5. **Working mode.** Ask, in these words or close to them: "Will you read the code your agents write, or lead from outside it?" Asked on first bind and never inferred from the repo; a re-run reuses the recorded answer unless it is missing or the human changes it. `lead` records that the human works from the orchestrator seat: new sessions in this repo open by invoking [orchestrate](../../run/orchestrate/SKILL.md) and following its startup checklist, and the other pack skills are what that seat runs, not a menu the human navigates. `read` records that the human reads and picks skills directly, the way an engineer would. Either answer is one line in the binding doc; a `lead` answer also makes orchestrate's binding slots (in the optional bindings that follow) worth offering in the same interview, since that repo will run an orchestrator from day one.

**Optional bindings** (offer them; skip freely): label-vocabulary mapping, domain-doc pointers (context docs agents should load), adopt-repo-templates vs seed-pack-templates (below), a friction-log location, and the per-skill binding slots that [adversarial-review](../../run/adversarial-review/SKILL.md), [codebase-review](../../investigate/codebase-review/SKILL.md), [domain-memory](../domain-memory/SKILL.md), and, for repos running an orchestrator, [orchestrate](../../run/orchestrate/SKILL.md) each define in their own SKILL.md; open the target skill for its slot list when the human takes one up. Where both codebase-review and domain-memory are bound, codebase-review's rejection-memory slot points at the memory home (the transition rule is in this skill's Done-when below). Two optional bindings get their own sections below because they write outside the binding doc: the glossary + non-negotiables binding, and the session-scope conduct pointer.

## What gets seeded

- **One anchor binding doc** at the confirmed home, from [references/templates/binding-doc.md](references/templates/binding-doc.md). It carries the five mandatory bindings, any confirmed optional ones, and a **precedence/exemptions section** stating how the pack composes with resident rule systems, explicitly including the prototype skill's test-exemption (prototype branches are exempt from test-first/coverage law) so agents never deadlock between pack rules and repo rules. Resident rules win unless the exemptions section says otherwise.
- **Templates**, seeded into the consuming repo's own convention locations **only on confirmation**, and only where the repo doesn't already have an equivalent it prefers to keep (the adopt-vs-seed optional binding):
  - Issue/work-item spec: [references/templates/issue-slice-spec.md](references/templates/issue-slice-spec.md) (on GitHub: `.github/ISSUE_TEMPLATE/`).
  - Lane brief shape: [references/templates/lane-brief.md](references/templates/lane-brief.md).
  - Defect-class checklist for the adversarial-review skill: [references/templates/defect-classes.md](references/templates/defect-classes.md): seeded only when the repo has no equivalent; a repo with an existing review-standards document adopts it as the binding unchanged.
  - Session handoffs are the [handoff skill's](../../run/handoff/SKILL.md) job (its reference template ships with it); setup records the bundled checkpoint resolver or an existing harness-owned checkpoint policy.
- **Codex continuity.** Use the task-owned checkpoint instructions in the desktop reference. Verify that the bundled resolver runs with the actual project and task ID, or verify the existing harness-owned policy if present. This package requires no hooks. Do not create `.claude/settings.json` or alter another harness's handoff. New hook definitions require the runtime's actual trust process; never forge trust state.
- **Checkpoint storage.** Codex task checkpoints live outside the repository at the path returned by the checkpoint resolver. No project ignore entry or Claude handoff relocation is needed. If the user explicitly chooses a project-owned checkpoint, record and ignore that exact path.

## Configuration ownership

Inspect configuration ownership before proposing changes. Existing hooks and
master instructions belong to their current owners; this plugin supplies neither.
Project setup records an existing checkpoint policy when one is present. Other tools' settings
and preserved output homes stay unchanged. Seed project bindings and templates
only in locations the project owns.

An instruction to configure this project authorizes the requested binding doc,
selected templates, agreed tracker labels, and agreed project-instruction edits.
Reuse recorded confirmations for that same scope. Ask only about new or changed
bindings that remain material; an audit request is read-only. Codex continuity
requires no `.claude/settings.json`, Claude handoff, or project ignore write.

## Glossary and non-negotiables (optional binding)

Two per-repo sections for the file every session already loads: the repo's agent-context file (CLAUDE.md or AGENTS.md), never the binding doc, which only loads when a skill reads it:

- **A domain glossary**: the repo's words defined the team's way, as much so agents *describe things back* in the team's vocabulary as so they understand it.
- **A never-compromise list**: the handful of properties a change must not break, so an agent knows what it is not allowed to trade away without the decider's sign-off.

**Harvest, never template.** Both sections are built from what the repo already says (docs, README, tracker vocabulary, existing agent-context files), proposed as candidates with inferred definitions and confirmed or corrected by the decider term by term. Setup ships no boilerplate terms: a seeded generic glossary is worse than none. For candidates written directly into the agent-context glossary, every disposition, `accepted`, `corrected`, or `declined`, is recorded in the binding doc so a re-run diffs against decided ground instead of re-proposing declined terms; where domain-memory is bound, dispositions live with the cards (next paragraph) and the binding doc records the routing and backfill status instead. Declining a whole section, or recording `none yet`, is a recorded binding revisited on re-run.

**Composition with domain-memory.** Where the repo binds [domain-memory](../domain-memory/SKILL.md), the glossary already has a home (the terms file at the memory home) and a disposition mechanism (backfill drafts, card by card): setup's harvest routes through that (setup only drafts the candidate cards; the terms-file write belongs to domain-memory's own disposition process, so setup's declared writes stay unchanged), and the agent-context file gets a **pointer line** to the memory home, never a second glossary. Only a repo without domain-memory gets the glossary written into the agent-context file directly. The never-compromise list is not domain memory: it goes in the agent-context file either way.

The agent-context edit is a declared, confirmed setup write; an agent-context file owned by a config-distribution pipeline follows the sync-managed rule above.

## Session-scope conduct pointer (optional binding)

The pack's PR conduct, the [pr-writing reference](../../run/orchestrate/references/pr-writing.md), binds every session writing on the decider's behalf, not just lanes the pack machinery launched; an ad-hoc session loads only the agent-context file, so conduct recorded in the binding doc alone never reaches it. Setup (interview and re-run alike) offers a short pointer section for the agent-context file: where the binding doc lives, plus "before writing any PR description or comment, read the pack's pr-writing reference." Pointer-only: the reference stays the single evolving authority, never copied. The write follows the same declared-write and sync-managed rules as the glossary edit above; a decline is recorded in the binding doc, revisited on re-run.

## Re-run semantics: idempotent refresh

Re-running setup **re-scans the repo, diffs against the existing binding doc, and proposes changes for confirmation**: never a blind overwrite, never a one-shot refusal. Bindings that still match are left untouched; drift (a changed verify command, a new tracker, a moved docs home) is presented as a diff for the human to accept or reject, one binding at a time. Recorded absences are first-class drift candidates: a `none yet` tracker or verify binding is exactly what a re-run exists to upgrade once the repo has grown the real thing, so the re-scan checks each one against what now exists.

## Audit mode: report drift, don't assume absence

A re-run can instead run as an **audit**: it audits a consuming repo's bindings against reality and reports drift, rather than interviewing toward a refreshed binding. Run it after each pack release, and on demand; there is no calendar floor. Five checks, exactly:

1. **Binding-doc currency.** The pack version the doc claims against the pack version actually installed, and, the common gap, sections missing for skills added since the doc was seeded: a repo bound before a release has no section to fill for the skills that release added, and nothing downstream ever creates one. Where the repo runs an orchestrator, currency includes the runner-policy binding: the orchestration section carries the runner inventory and runner-policy lines, the policy still names the runners the repo actually launches with, and the launcher recipe doc the inventory names still exists and still matches the launcher it describes (the check the [runner-parity reference](../../run/orchestrate/references/runner-parity.md) assigns to setup re-runs).
2. **Local forks.** Overrides in the repo's own skills directory (e.g. `.claude/skills/`) that shadow pack skills: report where the fork and the pack now disagree. Report only: the fork's authority stays the repo's recorded choice, and the audit never rewrites or retires one.
3. **Recorded grants and rules.** The grants, precedence rules, and exemptions the pack skills assume are actually present in the repo's canonical doc; nothing running on the memory of a confirmation the doc never recorded.
4. **Machine portability.** The workflow artifacts the binding governs (the binding doc itself, helper scripts it names, seeded docs and templates, contract validators and their tests and fixtures) must not hard-code one machine's filesystem: an absolute home path works for the author and walls out the first contributor on a second machine. The boundary is what the binding governs: application code and repo-local ignored files are out of scope. Report each occurrence as drift, proposing the portable derivation in the artifact's own mechanism (`$HOME` in shell, the home/repo-root resolution its language provides elsewhere).
5. **Session-scope conduct reachability.** A binding doc that pins the pack's pr-writing reference while the agent-context file carries no pointer to it: conduct the decider intends as universal is reachable only from sessions the pack machinery launched; an ad-hoc session never sees it. Report as drift, proposing the conduct-pointer section above.

Also verify the installed checkpoint resolver or existing harness policy and actual checkpoint location. A configured name alone is not evidence that saving and loading reach the same file.

Execution follows the house pattern: a lane per consuming repo produces the drift report; the orchestrator presents each finding to the decider as a disposition card: **update the binding** (a normal re-run confirms the change), **accept the drift** as a recorded choice, or **defer**. Accepted drifts are recorded, in the binding doc's Accepted drift section or as a decision record where the repo binds domain-memory (with a pointer from the Accepted drift section so the audit knows where to read), and the next audit reads the record and does not re-flag them.

## Done when (checkable)

All bullets except the last govern install and refresh runs; an audit run satisfies the audit bullet alone.

- The binding doc exists at the confirmed home with all five mandatory bindings filled and the precedence/exemptions section present. **A recorded explicit absence counts as filled**: `none yet` for the tracker or verify commands is a satisfiable answer on a brand-new repo, provided the doc carries the revisit-at-re-run note; a blank or guessed value is not.
- On a freshly bound tracker, the pack's label vocabulary exists (created by setup) or its creation instruction is recorded in the binding doc: the frontier query has labels to match.
- On a GitHub tracker: the implicit-repo check ran, and any mismatch between `gh repo view`'s resolution and the bound repo is recorded in the tracker binding (a match needs no record).
- Confirmed templates are seeded at their confirmed locations; declined ones are recorded as declined in the binding doc (so a re-run doesn't re-ask from scratch).
- The checkpoint resolver or existing harness policy was verified, or the missing capability was reported. Checkpoints resolve outside the project unless an explicit project-owned location was selected.
- Every new or materially changed binding was confirmed or authorized in the current request; unchanged recorded answers were reused. The decision-maker binding is explicit and its source cited; missing, conflicting, or apparently changed authority was raised, and current user instructions retained precedence.
- Where the domain-memory binding repoints an existing rejection-memory path at the memory home: the old records were moved into the store (as decision records, provenance noted) or the old path is recorded as read-until-migrated; the binding is accepted only when the old store is empty or its path is recorded.
- Where the glossary + non-negotiables binding was accepted: the agent-context file carries the confirmed never-compromise section, or a sync-managed agent-context file has the approved snippet recorded as pending with the settings owner (or the binding doc records its decline); the glossary is the confirmed agent-context section, or, where domain-memory is bound, the memory-home pointer with the harvested candidates drafted as backfill cards, or on a sync-managed agent-context file the approved snippet recorded as pending with the settings owner (the snippet carries the confirmed glossary, or, where domain-memory is bound, only the memory-home pointer, never a second glossary), or a recorded decline; and every harvested candidate's disposition (`accepted`/`corrected`/`declined`) is in the binding doc for a directly-written glossary, or with the backfill cards where domain-memory is bound (the binding doc recording the routing).
- Where the session-scope conduct pointer was accepted: the agent-context file carries the pointer section (binding-doc location plus the pr-writing read-before-writing line), or a sync-managed agent-context file has the approved snippet recorded as pending with the settings owner; otherwise the binding doc records the decline.
- On an audit run: all five checks ran against the repo, every drift finding was reported with a recommendation; any decisions the decider has made are recorded, and remaining decisions are explicitly pending. Reporting the audit does not require manufacturing a decision. Zero drift is an explicit "bindings current" verdict in the report, never a silent finish.

## Attribution

The interview shape here (scan the repo first, present findings, confirm each answer before writing) and the pattern of recording the tracker and label vocabulary as per-repo bindings the other skills read are adapted from Matt Pocock's [`setup-matt-pocock-skills`](https://github.com/mattpocock/skills/tree/main/skills/engineering/setup-matt-pocock-skills) (MIT). The five mandatory bindings, the empty-repo branches, the sync-managed-settings rules, the seeded templates and handoff hook, and the idempotent re-run are this repo's.

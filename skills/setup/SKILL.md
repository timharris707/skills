---
name: setup
description: Once-per-repo binding interview for the team-workflow pack — scan the repo, confirm the mandatory bindings (tracker, verify commands, decider, binding-doc home), seed the anchor binding doc and templates, and refresh idempotently on re-run. Use when installing the pack into a repo or updating an existing installation.
---

# Setup

This skill binds the team-workflow pack to a specific repo, once, through an interview — and refreshes that binding on re-run. Everything the other pack skills call "the binding doc" is what this skill seeds. Nothing here rewrites the repo's CI or processes; it records how the pack composes with what is already there.

**Posture: infer first, confirm everything.** Scan the repo before asking anything — the tracker in use, CI config, verify/test commands, existing agent-context files (CLAUDE.md, AGENTS.md, docs conventions), existing templates, and any config-distribution pipeline that syncs or ignores dotfiles. Present every inferred binding for confirmation; never silently assume one. Exactly two bindings always require a live human answer regardless of what the scan finds: **the decider** and **the binding-doc home**.

## The four mandatory bindings

1. **Tracker** — the repo + tracker in use, and the mapping onto the pack's tracker discipline: how claims are posted, how blocking is expressed, what the frontier query is. The pack is GitHub-Issues-first — the recipes in [references/tracker-discipline.md](references/tracker-discipline.md) use `gh` — but the tracker is a **named binding**, not an assumption baked into the skills: a repo on a different tracker writes a different tracker section in its binding doc, mapping the same discipline (machine-readable claims, dependency edges, a frontier query) onto its own tool. The skills stay unchanged.
2. **Verify commands** — the exact commands that constitute "verified" in this repo (typecheck, lint, test, build, whatever the repo runs), recorded so every brief and template can name them instead of guessing.
3. **The decider** — who adjudicates decisions in this repo. Always asked, never inferred. Every pack skill says "the decider"; this binding is where that role gets a name. A repo without a clear answer here is not ready for the pack's decision discipline — surface that honestly.
4. **The binding-doc home** — where the anchor binding doc lives. Default: `docs/agents/team-workflow.md`. The home is **confirmed in the interview, never assumed**: repos with config-distribution pipelines (synced or git-ignored dotfile directories) can make the default location wrong in ways only a human knows — the binding doc must land somewhere tracked, un-synced, and visible to agents.

**Optional bindings** (offer them; skip freely): label-vocabulary mapping (the repo's existing labels onto the pack's state/type vocabulary), domain-doc pointers (context docs agents should load), adopt-repo-templates vs seed-pack-templates (below), and a friction-log location.

## What gets seeded

- **One anchor binding doc** at the confirmed home, from [references/templates/binding-doc.md](references/templates/binding-doc.md). It carries the four mandatory bindings, any confirmed optional ones, and a **precedence/exemptions section** stating how the pack composes with resident rule systems — explicitly including the prototype skill's test-exemption (prototype branches are exempt from test-first/coverage law) so agents never deadlock between pack rules and repo rules. Resident rules win unless the exemptions section says otherwise.
- **Templates**, seeded into the consuming repo's own convention locations **only on confirmation** — and only where the repo doesn't already have an equivalent it prefers to keep (the adopt-vs-seed optional binding):
  - Issue/work-item spec: [references/templates/issue-slice-spec.md](references/templates/issue-slice-spec.md) (on GitHub: `.github/ISSUE_TEMPLATE/`).
  - Lane brief shape: [references/templates/lane-brief.md](references/templates/lane-brief.md).
  - Session handoff: [references/templates/handoff.md](references/templates/handoff.md) — a seeded template, not a skill; repos may already have their own handoff convention.

## Re-run semantics: idempotent refresh

Re-running setup **re-scans the repo, diffs against the existing binding doc, and proposes changes for confirmation** — never a blind overwrite, never a one-shot refusal. Bindings that still match are left untouched; drift (a changed verify command, a new tracker, a moved docs home) is presented as a diff for the human to accept or reject, one binding at a time.

## Done when (checkable)

- The binding doc exists at the confirmed home with all four mandatory bindings filled and the precedence/exemptions section present.
- Confirmed templates are seeded at their confirmed locations; declined ones are recorded as declined in the binding doc (so a re-run doesn't re-ask from scratch).
- The human confirmed every binding — including the inferred ones — and answered decider + home directly.

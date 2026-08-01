# Changelog — team-workflow (pack)

All notable changes to the **team-workflow pack** are documented here. The pack versions as a
unit — **one pack = one version**: a single pack-scoped tag `team-workflow/vX.Y.Z` covers all
pack skills together (see [`RELEASING.md`](../../RELEASING.md)), and the plugin version in
[`.claude-plugin/marketplace.json`](../../.claude-plugin/marketplace.json) mirrors the latest
pack tag. Individual pack skills do not carry their own changelogs or tags.

This file lives at `skills/team-workflow/CHANGELOG.md` deliberately: the release workflow
derives the changelog path from the tag prefix, so a `team-workflow/vX.Y.Z` tag resolves here
with no workflow changes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [v1.1.0] - 2026-08-01 — handoff + orchestrate siblings

### Added

- **handoff** — the sixth pack skill (promoted from a seeded template): write a structured
  session handoff at wrap-up or at roughly half the context window, with a plain-English
  context-window primer, overwrite-don't-append, pointer-not-transcript, the
  STATE/DONE/NEXT/GOTCHAS reference template, and the stale-NEXT rule (NEXT points at the
  tracker query, never enumerates items). The handoff template now ships inside this skill.
- **orchestrate** — the seventh pack skill: the portable protocol for one session
  coordinating parallel working lanes — router-not-worker turn discipline, delegation as
  context preservation, the single-orchestrator rule, claim-legible lane launches,
  never-trust-self-reported-greens close-outs, and half-window wrap-up with clean
  succession. Ships as principles plus named **binding slots** (lane launch, workspace
  provisioning, monitoring, verification executor, merge flow) that the setup interview
  fills per-repo; the pack deliberately ships no orchestration machinery.
- **setup: session-start handoff hook seeding**, on by default and documented as removable —
  wiring that auto-loads the repo's handoff file into fresh sessions. Setup now **detects
  sync-managed settings files** (republished by a config-distribution pipeline) and NEVER
  writes them directly: sync-managed repos get the hook as a ready-to-paste snippet routed
  through the settings owner's pipeline; default-on seeding applies only where settings are
  not sync-managed.
- **Write boundaries and approval reconciliation, stated explicitly**: pack skills never
  write into sync-owned directories (e.g. a synced `.ai/` tree) or other tools' preserved
  homes (e.g. a review-decision wiki at `docs/review-wiki/`); in approval-before-edit repos,
  explicit invocation of a file-writing pack skill constitutes approval for its declared
  writes only. The setup skill's binding-doc-home prose now self-justifies tracked-and-
  un-synced placement in config-pipeline-owner terms.
- **Empty-project support in the setup interview**: a brand-new repo is a first-class
  consumer — the tracker binding gains a no-tracker-yet branch (bind one now, or record an
  explicit `none yet` with the recipes dormant), verify commands allow a recorded `none yet`
  that the idempotent re-run revisits, setup creates the pack's label vocabulary on a
  freshly bound tracker so the frontier query isn't forever-empty, seeds the handoff-file
  `.gitignore` entry alongside the hook, and creates the conventional agent-settings file
  when none exists (non-sync-managed repos only); "Done when" counts a recorded absence as
  a filled binding.
- **Review-response boundary in the router**: institutional review memory noted as a sibling
  of the derive-your-classes-from-history meta-rule, and the pack's territory stated
  explicitly — planning, research, prototyping, handoff, and orchestration; the
  review-response stage belongs to a repo's resident system and pack outputs cite that
  precedent store rather than create a second one.

### Changed

- Binding-doc template: the seeded-handoff-template line is replaced by a Handoff section
  (handoff location + hook status) and an optional Orchestration section carrying the
  orchestrate skill's binding slots.
- Marketplace plugin version mirrors the pack tag (1.1.0); the plugin now carries seven
  skills.

## [v1.0.0] - 2026-07-31 — v1 pack

### Added

- Initial release of the **team-workflow** pack: a portable discipline for tracked,
  multi-session, agent-assisted development, shipped as five skills that travel together.
  - **router** — the pack's single entry point: names every pack skill and when to reach
    for it, plus the review meta-rule (derive your own defect classes from your own defect
    history; admit a class only via live reproduction).
  - **setup** — once-per-repo binding interview: confirms the tracker, verify commands,
    the decider, and the binding-doc home; seeds the anchor binding doc and templates;
    re-runs are idempotent diffs, never overwrites.
  - **decision-map** — chart and work decision maps for genuinely foggy efforts:
    destination-first, gate-decision tickets, four ticket types, two ledgers, and briefed
    decision rounds adjudicated by the decider (full protocol in `references/protocol.md`).
  - **prototype** — throwaway prototype code that answers a design question: UI variants on
    a live route, or a terminal UI over a pure logic module; the verdict is the deliverable
    and the winner is re-implemented properly.
  - **research** — autonomous fire-and-report investigation against primary sources, ending
    in a cited findings file — and a questionnaire when the missing facts are human-held.
- Tracker discipline as portable recipes (claim, frontier, blocking edges, issue-as-spec)
  in the setup skill's references, bound per-repo through the seeded binding doc.
- Seeded templates: binding doc, work-item spec, lane brief, and session handoff.
- Distribution: the repo's `.claude-plugin/marketplace.json` hosts the pack as one plugin
  carrying all five skills; a clone/symlink path is documented in the repo README for
  non-plugin consumers.
- CI freshness check: every skill directory is claimed in the router/marketplace roster and
  every router entry resolves, so the router cannot silently rot as skills are added.

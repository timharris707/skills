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

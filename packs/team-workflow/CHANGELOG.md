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

### Added

- **codebase-review** — the twelfth pack skill (#120): a state review of the codebase, the
  counterpart to adversarial-review's change review, adapted from Matt Pocock's
  [`improve-codebase-architecture`](https://github.com/mattpocock/skills) (MIT). Three entry
  gates and no calendar runs: pre-feature ("make the change easy" against an upcoming spec's
  blast radius), a lane-count threshold since the last review (N is a per-repo binding), and
  reported friction from lanes or the orchestrator; scope follows the trigger — churn-weighted
  areas for lane-count/friction runs, a full sweep only on a repo's first-ever run. Executes as
  a delegated read-only lane, claimed and tracked like any work item — changes no code, files no
  tickets. Finder agents each take a named lens (shallow modules/seams, duplicated concepts,
  dead code, boundaries-vs-reality, test-pain), speak the shared design vocabulary
  (`references/design-vocabulary.md`, adapted from his `codebase-design`, MIT), and read the
  repo's rejection memory before proposing anything. A built-in skeptic tries to kill every
  candidate before the report exists — survival is the only grade, no self-graded strength
  badges. The report is plain markdown on a tracker item: survivors only, each with claim,
  file/line evidence, the skeptic's attempted kill and why it failed, cost, and payoff; zero
  survivors is an explicit "codebase is fine" verdict stated as a success. The run ends in a
  disposition loop — every survivor presented to the decider as a grilling-style question card:
  Adopt (tracker ticket, normal lane flow), Reject (into rejection memory with the load-bearing
  reason), or Defer (carried at the top of the next run's report and named in handoffs) — and
  the run's tracker item closes only when nothing is undispositioned. Binding slots: report
  destination, lane-count threshold N, rejection-memory location, executor mechanics.
- **setup:** the interview's optional bindings now offer the codebase-review slots, and the
  binding-doc template gains a matching optional Codebase review section.

### Changed

- **router:** roster and intro now cover codebase-review — where adversarial-review breaks
  the change, codebase-review reviews the codebase the changes accumulate in.
- **Fidelity audit follow-up: attribution squared with the record, plus the upstream rules
  worth keeping** (#122). An audit against [mattpocock/skills](https://github.com/mattpocock/skills)
  (MIT) — the pack's main upstream — found overdue or inaccurate attributions and a handful of
  his rules the adaptations had dropped. Attribution: **decision-map** (wayfinder), **research**
  (research + to-questionnaire + wayfinder, including his phrase "grill the send, not the
  subject"), **prototype**, and **setup** gain honest Attribution sections in grilling's
  his-vs-ours style; **to-tickets** stops claiming the two-pass filing order as this repo's
  (it is wayfinder's); the **router** notes its main-flow-with-on-ramps framing comes from
  ask-matt. Adopted upstream rules and fixes: **decision-map** takes the fog-or-ticket test
  (ticket when the question can be stated precisely now) and refer-by-name (names, never
  bare issue numbers, in anything the human reads); **to-tickets** restores the
  wide-refactor expand–contract exception and gains a decider sign-off gate on the slice
  list before Pass 1 files anything; **prototype** regains the single-shareable-HTML shape
  for logic prototypes beside the
  terminal UI, and its iteration rule now covers lane mode (the driving ticket as the
  iteration channel when the decider is not in-session). Pack-native strengthening from the
  same audit: **grilling** closes with a durable record of the confirmed understanding, so
  to-tickets links a citable plan source instead of a transcript; **handoff** adds a
  no-secrets rule (the session-start hook replays a captured credential into every future
  session — point at where a secret lives, never its value); **wizard** mirrors pending
  manual steps as the driving ticket's `blocked` label until the human clears them;
  **research** gains claim/title discipline for standalone lanes, a skeptic pass over
  findings that will drive a build decision (optional otherwise), and the
  verify-each-line Done-when suffix its siblings carry; **adversarial-review**'s lens menu
  adds a conventions/standards lens — additive, active only where the repo documents its
  own standards, reading the repo's documents and never an imported checklist; the
  **router** gains "The main flow" — the named route (idea → grill → map → tickets →
  lanes → review → merge), with prototype and research as detours and ingest, research
  findings, and wizard as on-ramps — plus the ingest row in its table. The same audit's
  **writing-for-agents** changes (attribution reworded to own its near-verbatim body;
  "When to split" restored) ship separately, logged in that plugin's own changelog.
- **orchestrate: session titling is now protocol, not folklore** (#118). The startup
  checklist titles the session (after the existing-sessions check, so a session that must
  stand down never wears the title) — default `Orchestrator — <repo>`; every
  picker-visible lane session is titled with its item at launch — default
  `#<N> — <short item name>`, in the repo's own item notation, carrying the item id the
  claim and workspace already carry; role changes retitle, and a retiring orchestrator
  sheds the title at succession so the picker shows exactly one live orchestrator. The
  formats are defaults a repo binding may refine; the titling *mechanism and actor*
  (self-title where the harness allows, launcher/orchestrator where sessions cannot
  self-rename, launch-report-only where no titling surface exists) live in the
  lane-launch binding slot — that titling happens is protocol, and the slot never opts a
  repo out. In-process subagent lanes have no picker entry; the launch report carries the
  name. Generalizes a rule LoanMeld pioneered locally (its stricter orchestrator-owned
  variant remains a compliant refinement) and other repos ran on habit; the binding-doc
  template's lane-launch line is reworded to match.
- **orchestrate: titling's default actor flips to the launcher, and close-out ends by
  handing the dead lane to the human for archiving** (#123). The titling protocol above now
  defaults to *whoever launched the session titles it* — normally the orchestrator for
  lanes — with self-titling the exception, available only where a harness genuinely
  supports it (in most, a session cannot rename itself); the retirement retitle likewise
  falls to the successor or the human where self-rename is unsupported, and the existing
  degrade rules (launch report / handoff carrying identity where no titling surface exists)
  are unchanged. Close-out gains a final, trailing step: after merge, tracker close-out,
  and pruning, the orchestrator notifies the human — naming the session verbatim as the
  picker shows it — that the lane is complete and safe to archive, and the human archives
  on their own time; the orchestrator never calls an archive surface, so an unanswered
  notification gates nothing. Archive, never delete; only the closed-out lane's own session
  is ever named; native auto-archive-on-PR-close is the zero-touch path where the harness
  offers it (recorded in the lane-launch slot — `yes` only where it cannot preempt the
  close-out order, since it fires at merge time); in-process subagent lanes have nothing to
  archive; a retired orchestrator's session is archived by the human, never automatically
  and never by the orchestrator.

## [v1.3.0] - 2026-08-07 — adversarial-review joins the pack

### Added

- **adversarial-review** — the eleventh pack skill: reviewers whose job is to break a change
  before it ships, run before external reviewers ever see it. Two layers bound per repo (the
  floor — the implementing session reviews its own substantial change before committing — and
  the orchestrator close-out layer, where the implementer never has the last word on its own
  work). Three isolated finders: a correctness finder, a fitting lens picked from a shipped
  menu (security, compatibility/migration, money/ledger, concurrency, performance,
  UI/accessibility), and a spec axis that checks the diff against the originating ticket and
  reports a missing spec as a finding rather than inventing requirements. Finders read code
  and run proofs but modify nothing. Every finding above a NIT passes an independent skeptic
  trying to kill it; BLOCKER rank requires a skeptic-confirmed runnable reproduction. Reports
  land on the driving ticket/PR with ranked cited findings, the stated composition, and a
  clean bill of what was checked and found correct; axes are never blended into one verdict.
  Confirmed blockers gate the commit/merge and only the decider may waive one, on the record.
  Binding slots: the defect-class file (grown only via live reproduction, proposed in the
  fixing PR, removed only by extinction sweep), layers, mandatory lenses, live-probe policy,
  and substantiality rules. Spec axis, finder isolation, and the no-blended-verdict rule
  adapted from [mattpocock/skills](https://github.com/mattpocock/skills) (MIT).
- **setup: defect-class checklist template** (`references/templates/defect-classes.md`),
  seeded only where the repo has no equivalent — a repo with an existing review-standards
  document adopts it as the binding unchanged. The binding-doc template gains an optional
  Adversarial review section carrying the skill's binding slots, and the interview offers
  them as an optional binding.
- **grilling:** a presentation split for asking a round. Choice-shaped questions go to the
  harness's structured question tool (`AskUserQuestion` in Claude Code) as selectable cards with
  the recommendation marked; open questions keep the ❓/➡️ text block. A frontier wider than the
  tool's four-question limit splits across consecutive calls rather than deferring to the next
  round — frontier questions are independent by construction, so the split is sound. Harnesses
  without such a tool use the text block throughout.

### Changed

- **router:** the review meta-rule section now points at the adversarial-review skill — the
  pack ships a review *protocol* but still no review checklist; derive-your-own-classes-via-
  live-repro lives on as the skill's defect-class binding slot.
- **orchestrate:** close-outs gain an explicit step — where the repo binds the
  adversarial-review close-out layer, the review runs against the lane's branch before merge.
- **grilling, to-tickets:** added Attribution sections naming [mattpocock/skills](https://github.com/mattpocock/skills)
  (MIT) as the source, matching what `wizard` and `writing-for-agents` already carried. Both were
  adapted from it and neither said so. `grilling` follows its original closely enough that the
  section states which parts are his.
- Marketplace plugin version mirrors the pack tag (1.3.0); the plugin now carries eleven skills.

## [v1.2.0] - 2026-08-05 — grilling, to-tickets, wizard join the pack

_Recorded retroactively: the 1.2.0 plugin-version bump shipped in PR #97 without a matching
changelog section or pack tag; the tag was cut after the fact on the #97 merge commit._

### Added

- **grilling** — the eighth pack skill: interview the decider relentlessly over a design tree,
  in rounds, until nothing load-bearing is still assumed. The frontier is every decision whose
  prerequisites are settled; facts are the agent's job, decisions are the decider's.
- **to-tickets** — the ninth pack skill: turn a plan, a closed decision map, or a
  pressure-tested conversation into tracer-bullet work items — issue-as-spec bodies filed in
  one pass, blocking edges wired in a second. Files and labels; never claims, never decides.
- **wizard** — the tenth pack skill: generate an interactive bash wizard for procedures only a
  human can perform — third-party dashboards, credentials, DNS records, CI secrets.

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

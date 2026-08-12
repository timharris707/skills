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

- **setup** — session-scope conduct pointer (#168). PR conduct pinned in a binding doc was
  structurally scoped to orchestrated sessions: an ad-hoc session loads only the agent-context
  file, and setup wrote nothing there pointing at the pr-writing reference. The interview and
  re-run now offer an optional agent-context pointer section — binding-doc location plus
  "before writing any PR description or comment, read the pack's pr-writing reference" —
  pointer-only, so the reference stays the single evolving authority. Audit mode gains the
  matching fifth check: a binding doc pinning pr-writing with no agent-context pointer to it
  reports as drift.

- **codebase-review** — five refinements from the insight-chat pilot (#129), the skill's
  first real run: the lane shapes candidates before the skeptic — convergent findings merge
  into one candidate with the convergence recorded as evidence, bundled claims split, one
  claim per candidate stated explicitly, one skeptic per candidate; partial kills fold the
  skeptic's corrections into the survivor's write-up so the decider reads skeptic-hardened
  claims; the skeptic reproduces the claimed behavior read-only where possible; and a
  first-run-without-bindings degrade — the executor creates the tracker item itself and the
  report names the unbound slots.

- **orchestrate** — on-behalf comment formatting (#179). Tim's formatting request, promoted
  from one repo's local preference to the pack: any tracker-visible comment an agent writes
  on a human's behalf (PR comments, review-thread replies, issue close-outs — not just PR
  bodies) opens with the attribution line alone on its own line, a blank line, then the body
  as its own paragraph; paragraphs run roughly 2–3 sentences — the decider reads these on a
  phone, and a wall of prose hides the verdict — with lists doing the enumerating and long
  comma-chains split. Lives in `references/pr-writing.md`, loaded at the moment of writing.

- **orchestrate** — subagent-vs-session lane choice rule (#178). From the 2026-08-12
  chips-vs-subagents discussion: the choice between an in-process subagent and a separate
  session (background-task chip) was recorded only in one consuming repo's binding — every
  other orchestrator chose by habit. §4 now records the default: subagent for lanes that
  fit standing permission grants, need no human input mid-flight, and are short-lived (the
  orchestrator pays only brief-out and report-in; launch needs no human click); a separate
  session, where the harness offers one, for lanes with expected mid-flight approvals — the
  strongest single discriminator, since a subagent hitting a permission wall fails where a
  session can prompt — long-lived build work, work that must survive the orchestrator, or
  work the decider wants to watch (a full session boot as its own first-write, but all lane
  traffic stays out of the orchestrator's context; babysitting is one click at launch). The
  lane-launch slot (§7) refines or overrides this default with recorded policy; the rule is
  the fallback where the slot is silent. Harnesses without separate-session launches are
  unaffected.

- **orchestrate** — lean wakes (#176). Companion to #175, same burn-comparison source: even
  with the sub-TTL metronome (#169), every wake re-reads the entire accumulated context at
  cache-read price, so what a wake ingests is paid again on every later wake. §1 item 5 now
  defines a metronome wake as a minimal turn — re-arm, one small filtered check (count-shaped
  or `-q` queries, never broad listings), a one-line status — with broad ingestion (full
  listings, whole comment bodies, unfiltered logs) waiting for an event that needs it. The
  metronome keeps the cache warm; lean wakes keep the thing being cached from growing.

- **orchestrate, setup** — compact lane-report contract (#175). From the 2026-08-12 burn
  comparison: post-#169 the biggest remaining ramp is orchestrator context accumulation
  mid/late run — everything the orchestrator ingests it re-pays on every later wake. Two
  layers: §5's close-out audit reads the lane's diff in the lane's workspace at the scope
  the item names (targeted hunks, filtered queries), never wholesale into orchestrator
  context, with a too-large diff going to a delegated verifier per the verification-executor
  slot (§7); and the lane-brief template's output contract now asks for a compact report —
  diff stat, per-command exit codes, only the load-bearing hunks or sentences quoted — never
  the full diff or transcript.

- **orchestrate** — announce enforcement moves from prose to machinery. A live orchestrator
  followed the recorded announce rule at launch and compressed the per-round repeats away
  hours into the session — behavioral decay, not a stale rule. Three-part response:
  `references/announce-hook.md` (new) ships the recipe for a harness-level PostToolUse hook
  on the subagent tool that injects the reminder on every spawn (once per profile or per
  workspace — the harness fires it, nothing decays); §4's launcher guidance now has a
  conforming launcher print the ready-made announce line for the orchestrator to relay; and
  §5's close-out gains the announce-compliance line (`rounds announced: N of N`) beside the
  cost line — prevention, burden-removal, and detection respectively. Setup may offer the
  hook wiring per repo where the harness supports it.

- **orchestrate** — cache economics become protocol, from a measured usage audit of a real
  orchestration run (2026-08-11: cold full-context re-caching from 7–13-minute idle gaps was
  88% of the orchestrator's cache-write bill — the largest avoidable cost of the session,
  ahead of everything its 22 lanes spent). Four additions: §1 gains item 5 — while lanes are
  live, the between-turn wake cadence stays under the prompt-cache TTL (~5 minutes; poll at
  most every ~4), pricing the existing "monitoring means polling" discipline; §4 — a session's
  model is fixed at launch (the cache is per-model; different-model work goes to a subagent,
  never a mid-flight switch); §4 — lane count is a cost dial (each lane pays its own
  full-context first-write; trivially-related small items ride one lane serially, including
  continuing an existing lane by message where the harness supports it — its cached context
  is already paid for); §5's
  close-out cost line gains the cadence tripwire — where wake times are readable, the
  longest between-wake gap while lanes were live is named, and a gap past the TTL is
  reported as a cadence miss, never silently absorbed. The monitoring binding slot (§7) may
  set a faster interval, never a slower one.

- **setup** — audit mode gains a fourth check, machine portability: workflow artifacts the
  binding governs (helper scripts, seeded docs, contract validators and tests) must not
  hard-code one machine's filesystem — an absolute home path works for the author and walls
  out the first contributor on a second machine. Occurrences are reported as drift with the
  portable derivation (`$HOME`, repo root) as the proposed fix. Motivated by a real onboarding
  failure: a consuming repo's worktree helper pinned the author's absolute path and refused to
  run on the second contributor's machine.

- **setup** — glossary + non-negotiables optional binding: the interview can harvest a
  domain glossary and a "what we never compromise on" list into the repo's agent-context
  file (CLAUDE.md/AGENTS.md) — the file every session loads, deliberately not the binding
  doc, which only skills read. Harvest-never-template: candidates are proposed from the
  repo's own docs and vocabulary and confirmed term by term by the decider; setup ships no
  boilerplate. Where domain-memory is bound, term drafts route through its backfill cards
  into the existing terms file and the agent-context file gets a pointer line — never a
  second glossary; the never-compromise list goes in the agent-context file either way.
  The edit is a declared, confirmed setup write; sync-managed agent-context files follow
  the existing never-write rule. (From the decider's review of Theo Browne's agents-file
  lessons, 2026-08-11.)

- **orchestrate** — PR-writing reference (`references/pr-writing.md`), wired into §5's
  merge-flow step and the lane-brief template's standing constraints: agent-filed PR
  titles say why the change matters; descriptions open with the problem in plain language
  (from the driving item or the user's words), then the solution — never an
  implementation inventory; no draft PRs (review bots skip them) unless repo policy says
  otherwise; a provenance blurb names the model and harness, read never guessed. Review
  response gets a floor that defers to resident review-response systems: no scope creep
  beyond the driving item's goal, act only on comments newer than the latest push, verify
  bot findings against source before changing code, reply-with-reason on false positives,
  and agent-written comments on a human's behalf say so. Carries real bad/good example
  pairs (identifiers removed) from consuming repos' agent-filed PRs. Follows Theo
  Browne's file-PR/babysit-PR lessons; attribution in the reference.

- **orchestrate** — pr-writing amendment: a user-visible change carries visual evidence
  (screenshot, or short recording for interaction) embedded via whatever upload
  capability the environment provides — a file-host skill or a recorded binding; the
  reference stays portable by naming the capability class, not any host. Externally
  hosted video doesn't inline-play on GitHub (plain link, optional GIF preview), and
  with no capability present the PR notes "demo available on request" rather than
  improvising hosting. Hosted evidence is public-by-URL, so every frame is reviewed
  before upload — no credentials, tokens, or customer data on screen; unsafe surfaces
  fall back to the no-capability path. (Trigger: the first real PR that needed an embedded demo,
  2026-08-11.)

### Changed

- **orchestrate** — CodeRabbit follow-ups from the compaction review (#184). Four ambiguity
  fixes and one decider-approved rule, at the same 2,500-word bound (`wc -w` = 2,500, offsetting
  trims all entailment/dedup): §1 item 5 states the polling cadence as two explicit bounds
  (wake gaps stay under the ~5-minute TTL; an eventless poll waits at least ~4 minutes since
  the last); §5's close-out cost line defines what `rounds announced: N of N` counts (the
  lane's launch plus every review round); §5's hand-off announcement now matches §4's toggle
  scope — identity unconditional, the model/effort repeat as the toggle-governed addition;
  §7 drops the number-shaped "a lane or two" (decider's call: no fake precision, not an exact
  bound); and §5 step 5 gains the decider-approved prune guard — check a lane's workspace for
  uncommitted work before pruning it. `references/runner-parity.md` makes the launcher's
  titling duty conditional on a title surface existing, with the binding-doc template's
  `no titling surface` option carrying identity in launch reports and handoffs instead.

- **adversarial-review** — finder execution shape follows where the review runs (#154).
  Observed twice in one overnight session: a close-out review delegated to a subagent
  spawned its isolated finder subagents and stalled waiting for them — nested subagents'
  completions do not re-invoke a parent subagent in that harness shape. §2 now records the
  rule: a reviewer in the harness's main loop launches finders as parallel subagents; a
  review that itself runs as a delegated subagent runs the finder passes sequentially in
  one context, keeping isolation between passes (fresh perspective per pass, no shared
  candidate list until the skeptic) rather than between processes.

- **orchestrate** — compaction pass (#180). Tim's verdict after the size check: SKILL.md had
  grown to 4,151 words — second-largest skill in the repo, 2.5× the pack median — with titling
  rules spread across §3/§4/§6/§7 and roughly a third of the word count being measured-incident
  rationale rather than protocol. Three moves, zero rules dropped or weakened (a 95-rule
  inventory was produced before editing and checked line-by-line after, then re-probed by the
  adversarial close-out layer): the protocol spine stays in SKILL.md at Tim's 2,500-word bound
  (`wc -w` = 2,500), keeping reasons only where they aren't entailed by a rule's own wording or
  carried by a reference; the measured evidence and relocated rationale (idle-gap cache
  economics, mid-flight model-flip costs, announce-compliance decay, the permission-wall
  mechanism) move to a new `references/evidence.md`, with the launcher-manifest pattern's
  definition landing in `references/announce-hook.md` beside the hook it composes with; and the
  titling rules consolidate into one section (§8) with a single carve-out for pre-titling launch
  surfaces — §3/§4/§6/§7 and the setup binding-doc template now point there, as does
  `references/runner-parity.md`. §1–§7 keep their numbers so external §-references (including
  installed announce hooks) stay valid.

- **orchestrate** — announce hook covers chip launches; chip announcements get a
  read-don't-guess form (#173). Observed live: an orchestrator launched two lanes as
  background-task chips and announced neither — the hook recipe's `Agent|Task` matcher
  never fires on the chip tool (`mcp__ccd_session__spawn_task`), so the decay class the
  hook exists to prevent walked around it through the other launch surface. The recipe's
  matcher now includes the chip tool, the reminder covers both spawn shapes, and an
  installed matcher missing the chip tool is an audit finding. Protocol half: a
  chip-spawned session's model/effort are set by the session defaults at click time — the
  launcher can neither set nor read them — so §4 names the compliant chip announcement:
  identity list as always, model/effort stated as "set by session defaults at click
  time — not launcher-readable", never a specific model guess.
- **orchestrate** — title protocol outranks a launch surface's label convention (#162).
  Observed live: a background-task chip's title is required by the chip tool's schema to be
  an imperative action phrase AND becomes the spawned session's title, so a chip-arranged
  successor arrived titled like a task instead of an orchestrator — and in harnesses without
  self-rename the wrong title sticks. §6 step 3 names the collision and settles precedence
  (a chip-arranged successor's chip title is written in the orchestrator title shape, never
  a generic imperative task label) and states the general form — any launch surface that
  fixes the title at spawn time makes the launcher the titling actor at that moment. §3
  step 4 gains the carve-out: chip-launched successors arrive pre-titled by the retiring
  orchestrator, and one that stands down under §2 is retitled by whoever archives it. The
  lane-launch binding slot (§7) now records which launch surfaces pre-title sessions, under
  the same precedence rule.
- **setup, codebase-review, research** — description trims: the frontmatter description
  is the only part of a skill loaded into every session, so it carries identity plus
  `Use when` triggers and nothing else. Mechanism inventories (setup's binding list and
  seed list, codebase-review's finder/skeptic/disposition pipeline, research's output
  file location) moved out of the descriptions; the skill bodies already state them.
  Triggers are unchanged. codebase-review keeps its "counterpart to adversarial-review"
  clause — that one does routing work.
- **orchestrate** — announce model and effort at lane launch and at review hand-off, read
  from a recorded source, never guessed (#156). Every launch announcement now carries the
  reasoning-effort level beside the runner and model §4 already required, and
  the close-out hand-off (§5) repeats that line and adds what is reviewing the work.
  Announced values come only from a recorded source (the runner-policy table, the launch
  manifest or config, an explicitly set value); "session-inherited" is valid only after
  those sources were read and set nothing, and a plausible guess is a protocol violation. The lane-launch binding slot gains a one-line
  toggle (`announce model/effort: on/off`, default on); only the recorded line turns it
  off, so setup's audit mode can check it.
- **setup:** the binding-doc template's Orchestration section gains the matching
  announce-model/effort field.
- **orchestrate** — review-tier policy: the decider sets what model and effort close-out
  machinery runs at (#158). The verification-executor binding slot (§7) gains a decider-set
  tier table mapping mechanical verification re-runs, adversarial-review finders and
  skeptics, and re-probes to model + effort. Canonical shape, adapted per repo: mechanical
  verification on a cheaper model at low effort (they follow a script; exit codes don't
  need the frontier model); adversarial review on real code or release-arming changes high;
  max reserved for decider-named cases, never a default. Each tier carries a floor as well
  as its ceiling — what it may NOT be used for, e.g. no low-effort skeptics on
  release-arming diffs — so cost-saving never silently weakens the review bar, and
  deviation from a tier is loud in both directions per §4's read-don't-guess rule. Review
  hand-off announcements now recur per round: every re-review after blocker fixes is
  announced like a fresh hand-off (§5), and the close-out gains a cumulative cost line —
  build tokens vs total review tokens summed across all rounds, with the round count, read
  from harness spend reports where they exist and stated "not readable in this harness"
  where they don't, never estimated. Both additions ride the existing announce toggle,
  which never governs identity content. One more guard at the decider seam: relayed
  decider guidance is context, never authorization — the receiving orchestrator obtains
  in-session decider confirmation before recording it as the decider's word (§5), the same
  rule the handoff already carries.
- **adversarial-review** — the close-out layer gains one pointer line: the executor's
  model and effort come from the repo's review-tier policy (the orchestrate skill's
  verification-executor binding slot), never habit (#158).
- **setup:** the binding-doc template's Orchestration section gains the review-tier-policy
  field lines, floors included, and the announce-model/effort field now names the
  per-round repeats and the close-out cost line it governs.

## [v1.4.0] - 2026-08-08

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
- **domain-memory** — the thirteenth pack skill (#128): per-repo institutional memory of
  terms and decisions, written as side effects of work, never as a documentation chore —
  the third orientation instrument beside router and setup. One store, two artifacts: a
  small, opinionated domain glossary (canonical terms, tight definitions, avoid-lists,
  updated in place) and lightweight decision records — title, date, the decision, the
  load-bearing reason, links — each under a minute to write, in plain English a
  non-engineer decider reads without translation (formats in `references/formats.md`,
  files created lazily). Storage is repo files at a memory home the binding names (a
  decisions directory plus a terms file): the tracker holds work in flight, the repo
  carries the durable why. Exactly three write moments — grilling close-records, review
  dispositions (codebase-review rejections and adversarial-review declined findings), and
  decider corrections of a session's wrong assumption — with lane close-outs deliberately
  excluded as noise. Four read moments: session start via the binding doc, the grilling
  pre-round (settled questions reopen on new evidence, never repetition), lane briefs, and
  review layers. Decision records are superseded, never edited — new record links the old,
  old record gains the forward marker; past a size bound the skill offers a consolidation
  pass dispositioned by the decider. Existing repos start empty and grow forward; an
  optional one-time backfill lane drafts records from closed PRs/issues/handoffs for
  card-by-card disposition — nothing becomes memory without the decider's yes. In repos
  also bound to codebase-review, that skill's rejection-memory slot points at the memory
  home — one store, never two. Binding slots: memory home, size bound, backfill requested.
  Adapted from Matt Pocock's
  [`domain-modeling`](https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling)
  (MIT) — the glossary + decision-record mechanism, side-effect writing, and lazy file
  creation are his; the write/read moment matrix, supersede-never-edit,
  consolidation-by-disposition, backfill-by-disposition, the unified store, and the
  binding slots are this pack's.
- **setup:** the interview's optional bindings now offer the domain-memory slots, and the
  binding-doc template gains a matching optional Domain memory section.
- **diagnose** — the fourteenth pack skill (#130): the disciplined bug-fixing loop a
  working lane follows inline — a fix may not ship without a **named cause**, one plain
  sentence with evidence a non-engineer decider reads without translation. The named-cause
  test is the binding trigger on every fix, not just hard bugs: if the cause is already
  nameable with evidence the loop is satisfied; if not, it runs — the first fix attempt is
  where the vibes-fix ships. Six steps: reproduce red (a failing automated test written
  before any fix attempt, kept as the regression test after; where test infra genuinely
  cannot reach the bug, a documented manual repro with exact steps is the recorded
  fallback, flagged at close-out), minimize proportionately (until the repro is tight —
  fast and deterministic enough to iterate against — and no further), hypothesize
  falsifiably (ranked hypotheses, each stating the prediction that could kill it),
  instrument before fixing (probes map to predictions, one variable at a time, tagged for
  one-grep cleanup), fix only against the confirmed hypothesis, and regression-test (the
  original repro re-run, the test kept, the probes gone). The closing artifact is the
  named cause plus the regression test, and the orchestrator's close-out audit checks
  both — an unnamed cause is not done. Structural causes (the bug as symptom of a missing
  seam or duplicated rule) are fixed at the instance and reported as friction toward
  codebase-review's entry gate, never as scope expansion on the diagnosing lane; a root
  cause that overturns a standing assumption is offered to domain-memory as a fact record.
  Deliberately not hooked into handoff GOTCHAS — the domain-memory record is the durable
  copy. No binding slots: everything repo-specific arrives in the lane's brief. Adapted
  from Matt Pocock's
  [`diagnosing-bugs`](https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnosing-bugs)
  (MIT) — the six-step spine, tight loops, falsifiable predictions, tagged probes, and the
  architectural post-mortem handoff are his; the named-cause binding test, the
  red-test-first bar with its recorded fallback, proportionate minimize, the close-out
  audit artifacts, the domain-memory feed, and the friction-gate escalation are this
  pack's.
- **implement** — the fifteenth pack skill (#131): how a working lane builds an item —
  seam-scoped test-first, tracer-first sequencing, green checkpoints, and file-don't-fix
  scope discipline. Testing is seam-scoped: at every seam the item's verification set
  names (agreed upstream at filing time, not invented mid-lane), red before code — the
  failing test is written first and stays in the suite; code at no named seam ships WITH
  its tests in the same commit, not necessarily before. Sequencing is tracer-first,
  mandated: the first commit proves the thinnest end-to-end slice and widening follows,
  pairing with to-tickets' tracer-bullet slicing. Cadence is a green checkpoint per
  slice — each slice commits when green, so a stopped or dead lane's completed work
  survives at a known-good point, which is exactly what orchestrate's relaunch-fresh rule
  assumes. Scope is file-don't-fix: adjacent discoveries go to the tracker (a comment on
  the driving ticket or a suggested new ticket), and the lane never silently expands its
  brief. Enforcement is artifacts, not forensics: the orchestrator's close-out audit
  checks that tests exist and pass at every named seam, the tracer slice is identifiable,
  and the diff contains no out-of-scope files — no commit-by-commit red-before-green
  reconstruction. Four named interlocks: a bug mid-build routes to diagnose (the
  named-cause test binds), structure fighting the lane becomes a friction report at
  close-out (codebase-review's entry gate), spec ambiguity goes back through the
  orchestrator to the decider (never silently resolved), and human-only steps get a
  wizard plus the `blocked` label. No binding slots: everything repo-specific arrives in
  the lane's brief. Adapted from Matt Pocock's
  [`implement`](https://github.com/mattpocock/skills/tree/main/skills/engineering/implement)
  and [`tdd`](https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd)
  (MIT) — the implement-session shape and the red–green loop by vertical slice (red
  before green, one seam/test/minimal implementation per cycle, tracer-bullet tests,
  pre-agreed seams, behavior-through-public-interfaces) are his; the seam-scoped bar with
  its upstream agreement, the tracer-first mandate, the checkpoint cadence, the
  file-don't-fix rule, the artifact-audit enforcement, and the four interlocks are this
  pack's.

### Changed

- **router:** roster and intro now cover codebase-review — where adversarial-review breaks
  the change, codebase-review reviews the codebase the changes accumulate in.
- **router:** roster and intro now cover domain-memory — institutional memory written as a
  side effect of the work.
- **router:** roster and intro now cover diagnose — the disciplined diagnosis loop for the
  bugs lanes fix inline.
- **router:** roster, intro, and main flow now cover implement — the build discipline of
  seam-scoped test-first tracer slices the lanes follow.
- **orchestrate, to-tickets, diagnose, wizard: implement hook lines** (#131). Orchestrate's
  lane briefs point build-shaped items at implement, and its close-out audit checks
  implement's three artifacts — seam tests present and passing, an identifiable tracer
  slice, no out-of-scope files in the diff. To-tickets states the downstream half of its
  own slicing rule: tickets sliced tracer-style are built tracer-style, and the seams a
  ticket's verification names are where implement's test-first bar lands. Diagnose names
  the mid-build route in (implement sends bugs there before the lane resumes building),
  and wizard names the human-only-step route in (the wizard carries the steps, the
  `blocked` label carries the wait). The lane-brief template gains the matching
  required-reading line for build-shaped items.
- **orchestrate, domain-memory, codebase-review: diagnose hook lines** (#130). Orchestrate's
  lane briefs point bug-shaped items at diagnose, and its close-out audit checks the two
  closing artifacts on bug fixes — the named cause and the regression test (or its flagged
  fallback). Domain-memory's decider-correction write moment also carries a diagnose root
  cause that overturns a standing assumption — the same correction class with reality as
  the corrector, riding moment three rather than adding a fourth. Codebase-review's
  reported-friction gate names diagnose as a feeder: the lane fixes the instance, the
  structural cause arrives as friction. The lane-brief template gains the matching
  required-reading line for bug-shaped items.
- **grilling, adversarial-review, codebase-review, orchestrate: domain-memory hook lines**
  (#128). Grilling's close-record also mints memory where the repo binds domain-memory —
  settled decisions become records, new terms enter the glossary, and the pre-round read
  consults the same store. Adversarial-review's declined findings land as decision records
  with their reasons. Codebase-review's rejection-memory slot points at the memory home
  where both are bound (one store, never two), and its intro now points at domain-memory
  as the skill the deferred domain-modeling discipline grew into. Orchestrate's startup
  reads the glossary and skims recent records beside the handoff, and lane briefs point at
  the memory home.
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
- **orchestrate, setup: runner policy is a binding, launch fallbacks are loud, and the
  runner-parity reference lands** (#134). The lane-launch slot now records the repo's
  runner inventory and the decider's preference policy — the available runners (Claude,
  Codex, human), the launch mechanism for each, and who is preferred for what (e.g.
  "prefer Codex for implementation lanes") — and the orchestrator launches on the runner
  that policy names, never on habit. A failed lane launch is a launch defect first: diagnose
  per the repo's launch tooling and retry before reaching for another runner; falling back
  is permitted after that but never silent — the launch report AND the tracker item carry
  `runner fallback: X→Y, reason`, and silent runner substitution is a protocol violation.
  A new `references/runner-parity.md` (guidance, not machinery — repos build their own
  launcher scripts against it; the pack ships none) names what a conforming lane launcher
  owes any runner: the launch chain in order (eligibility gates → claim preview→apply with
  proof → conforming workspace and branch → environment → generated prompt with the claim
  authority baked in), the claim stamped on the tracker, the session titled by the
  launcher, an issue-as-spec brief with no harness-specific assumptions, the
  environment/sandbox provisioned — with the sandbox rule proven in practice: diagnose a
  sandbox violation to its mechanism and fix the runner invocation first (macOS counts
  sockets as network, so an internal IPC socket fails "network" for checks that touch no
  network); relax last and surgically — preflight of the lane's verification commands
  before handover, every launcher failure mode loud with its fix printed, and an in-repo
  recipe doc so the launcher knowledge stops living in session memory. Setup's binding-doc
  template gains the matching runner inventory + policy fields, and the lane-brief
  template gains the runner-agnostic note: spec cited by issue reference beside the
  verbatim paste, no harness-specific assumptions.
- **setup: audit mode — detect binding drift in consuming repos** (#133). A setup re-run
  can now run as an audit that checks a consuming repo's bindings against reality and
  reports drift, instead of assuming absence. Exactly three checks: binding-doc currency —
  the claimed pack version vs the installed one, sections missing for skills added since
  the doc was seeded, and (where the repo runs an orchestrator) the runner-policy
  binding's currency, including that the launcher recipe doc still exists and matches the
  launcher it describes; local forks — repo-side overrides shadowing pack skills, reported
  where fork and pack now disagree (report only, the fork's authority stays the repo's
  recorded choice); and recorded grants and rules present in the repo's canonical doc.
  Hook-target existence is deliberately not checked. Triggers: after each pack release and
  on demand, no calendar floor. Execution follows the house pattern — a lane per consuming
  repo produces the drift report, and the orchestrator presents each finding as a
  disposition card (update the binding / accept the drift as a recorded choice / defer);
  accepted drifts are recorded in the binding doc's new Accepted drift section, or as
  domain-memory decision records where bound, so the next audit does not re-flag them.
  The binding-doc template gains the matching Accepted drift section. Closes the last
  open item on the #121 gap map.

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

# Rule inventory — orchestrate SKILL.md before the #180 compaction

> **Review artifact for item #180 — dropped before merge.** Numbered inventory of every
> normative rule in `SKILL.md` as of commit 1bb0de8 (pre-compaction). Close-out review checks
> this list line-by-line against the compacted doc: every rule present, none weakened.
> Section references (§) are to the PRE-compaction document.

## Preamble

1. The orchestrator claims nothing for itself: routes tracked items into lanes, audits what comes back, owns integration, stays reachable for the human throughout.
2. Rule-based: do every step, every time — protocols that live only in memory drift between sessions.
3. Read the team-workflow binding doc first.
4. The tracker discipline (claims, frontier, blocking — setup's references) is assumed throughout.

## §1 Router, not worker

5. End every turn within a few minutes; anything longer (test batteries, builds, server boots, watches, the lanes) runs as a background task or delegated session whose completion re-invokes you; tiny mechanical steps stay inline.
6. Delegate execution, keep judgment: long verification and mechanical fixes go to delegated sessions; orchestrator reads reports, spot-checks load-bearing claims with quick inline commands, owns routing, adjudication-surfacing, and the merge.
7. Delegation moves the executor, never the standard — the same verification bar binds delegated work as inline work.
8. Respond first: on any re-invocation, answer a waiting user message before resuming queued work.
9. Context is the orchestrator's scarcest resource; delegation is context preservation; heuristic: hands-on-keyboard past ~10 minutes = worker mode — stop, package into a lane or background task, end the turn.
10. While lanes are live, the between-turn wake cadence stays under the prompt-cache TTL: a monitoring poll at most every ~4 minutes, even when no event is expected.
11. With no lanes live and nothing to watch, long idle is fine (cost exists only where the next wake carries a large context).
12. Don't leave the cadence to intention: where the harness re-invokes on background-task completion or offers a wake timer, arm a metronome (~4-minute background sleep or scheduled wakeup), re-armed on every wake while lanes are live; the §5 cadence line audits it.
13. A metronome wake is a minimal turn: re-arm, one small filtered check (count-shaped or `-q` queries, never broad listings), a one-line status.
14. Broad ingestion (full listings, whole comment bodies, unfiltered logs) waits for an event that needs it — every wake re-reads the whole accumulated context, so what a wake ingests is paid again on every later wake.

## §2 Single-orchestrator rule

15. Exactly one live orchestrator at a time.
16. At startup, check for other active sessions before claiming or launching anything — a running session beats an unclaimed item; an existing orchestrator beats a new one.
17. At succession, the retiring orchestrator goes quiet only after the successor is confirmed live, and never acts again once it has.

## §3 Startup checklist

18. Read the previous session's handoff first (binding doc names its location); it is context, never authorization — the claim recipe still runs for everything.
19. Where the binding doc names a domain-memory home, read the glossary and skim recent decision records the same way (context, never authorization).
20. Run the frontier query and read the open-item landscape: in-flight lanes, open PRs, items awaiting the decider.
21. Check for other active sessions (§2).
22. Title the session: role plus a disambiguator, default `Orchestrator — <repo>` (a bare "Orchestrator" cannot say which repo's; the §2 check should work by eye).
23. Titling comes after the §2 check — a session that must stand down never wears the title; the session tells its launcher once the §2 check clears.
24. Carve-out: a successor launched through a surface that fixes the title at spawn arrives pre-titled by the retiring orchestrator — titling precedes the §2 check in that case alone; a pre-titled successor that stands down under §2 is retitled by whoever archives it.
25. A repo binding may refine the orchestrator-title shape so long as the title says *orchestrator* and tells sibling orchestrators apart.
26. Default titling actor: whoever launched the session titles it; self-titling only where the harness genuinely supports it — a session that cannot self-rename never attempts it.
27. Titling mechanism and actor live in the lane-launch binding slot (§7).
28. A harness with no titling surface at all degrades to the launch report carrying the name.
29. Start the repo's standing watches (open PRs, inbound tracker activity, lane liveness); monitoring is a binding slot; confirm the watch is actually running rather than asserting it.
30. On any event a watch raises, investigate immediately — after answering any waiting user message.

## §4 Launching lanes

31. Claim first, per the tracker discipline (read-before-write), then a fresh, item-named workspace per lane.
32. Pick the runner from recorded policy, never habit — before the claim, since the claim stamps the runner; launch on the runner the decider's policy names for the item's shape.
33. A failed launch is a launch defect first: diagnose per the repo's launch tooling and retry on the policy-named runner; fallback to a different runner is permitted after that and never silent — launch report AND tracker item carry `runner fallback: X→Y, reason`; silent substitution is a protocol violation.
34. Brief from the lane-brief template: spec verbatim, the named verification set, standing constraints, and the integration rule — lanes commit on their own branch and stop; the orchestrator owns review and merge.
35. Where the repo binds domain-memory, the brief points at the memory home.
36. A bug-shaped item's brief points at diagnose (no fix without a named cause); a build-shaped item's brief points at implement (seam-scoped test-first, tracer-first, file-don't-fix).
37. Every launch and every lane mention names what is running where — runner/model/session, item, workspace — legibly enough to tell lanes apart at a glance; this identity list holds in every announce-toggle state.
38. Unless the announce toggle records `off`, the launch announcement also carries the reasoning-effort level; the toggle governs only the additions (effort line, §5 hand-off repeats, close-out cost line), never the identity list.
39. Every announced value — model included — comes from a recorded source (runner-policy table, launch manifest/config, explicitly set value); "session-inherited" is valid only after those sources were read and set nothing; a plausible guess is a protocol violation.
40. A background-task chip launch announces model/effort as "set by session defaults at click time — not launcher-readable" — never a specific model guess; the identity list still holds.
41. The working manifest pattern: a launcher records model and effort per lane in a manifest; the recipe doc names the manifest (not itself) as the authority; a conforming launcher prints the ready-made announce line for the orchestrator to relay.
42. Where the harness supports tool-call hooks, the announce reminder moves into machinery (announce-hook.md); setup may offer wiring it per repo or profile.
43. Every picker-visible lane session is titled with its item at launch — default `#<N> — <short item name>`, in the repo's item notation, carrying the item id the claim and workspace already carry (picker, tracker, workspace speak one name).
44. A repo binding may refine the lane-title shape so long as the item id survives.
45. Default actor: whoever launched the lane titles it (normally the orchestrator); self-titling only where genuinely supported; subagent lanes have no picker entry — the launch report carries the name.
46. A role change retitles: a lane adopted mid-flight or a session promoted to orchestrator is retitled the moment the role changes, by the same actor rule.
47. Titling mechanism and actor are the binding slot's business; that titling happens, and what a title must carry, is protocol.
48. A session's model is fixed at launch — never switched mid-flight (the prompt cache is per-model); work needing a different model goes to a fresh subagent or lane launched at that model, announced per §4.
49. Lane count is a cost dial: where the tracker discipline allows, trivially-related small items ride one lane serially — including continuing an existing lane by message where the harness supports resuming; the dial never overrides isolation where items genuinely conflict.
50. Subagent vs separate session chosen by shape, not habit: default in-process subagent (fits standing permission grants, no human input mid-flight, short-lived); a separate session takes expected mid-flight approvals (strongest discriminator), long-lived build work, work that must survive the orchestrator, or work the decider wants to watch; the lane-launch slot refines/overrides; harnesses without separate-session launches unaffected.
51. After any user interrupt or stop, re-verify lane liveness before assuming anything; a stopped agent session is generally not resumable — relaunch fresh; completed work survives in the lane's workspace (checkpoint-commit first when resuming on top of it).

## §5 Close-outs

52. Close-outs run one lane at a time — never two merges racing.
53. At close-out entry, announce the hand-off: repeat the launch line (runner, model, effort) and name what is reviewing it — the reviewing agent or session, never merely a review type; reviewer naming holds in every toggle state; reviewer model/effort are toggle-governed additions under the read-don't-guess rule.
54. Every re-review round is announced like a fresh hand-off — same identity list in every toggle state, same toggle-governed model/effort lines, same read-don't-guess rule.
55. Audit the lane's summary against its verification contract; never trust self-reported greens — re-run the verification in the lane's workspace, directly or via a delegated verifier (binding slot), at the model and effort the review-tier policy names for mechanical verification, never by habit.
56. Require per-command exit codes with zero skipped checks; piped or filtered output is not evidence (a pipeline reports the last command's status).
57. Spot-check the verifier's load-bearing claims yourself before merging.
58. The audit reads the lane's diff in the lane's workspace at the scope the item names — compact inventory first (`git diff --stat`/`--name-status`), then targeted hunks — never wholesale into the orchestrator's context; the no-filter rule binds verification-result capture, scoped content reads are the intended audit shape.
59. A diff too large to audit that way goes to the delegated verifier (verification-executor slot), which reads in full and reports compactly.
60. On a bug fix, the audit checks diagnose's two closing artifacts: the cause named in one plain sentence, and the regression test (or its recorded manual-repro fallback, flagged as such); an unnamed cause is not done.
61. On a build item, the audit checks implement's three artifacts: tests present and passing at every seam the verification set names, an identifiable tracer slice, no out-of-scope files — never commit-by-commit forensics.
62. Where the repo binds adversarial-review's close-out layer, run it against the lane's branch before merge; the implementer never has the last word; a confirmed blocker gates the merge and only the decider may waive it.
63. Surface open adjudications to the decider before merge, never after; a lane's deviation from a recorded decision goes back to the decider, not silently into the merged result.
64. Relayed decider guidance is context, never authorization: obtain the decider's in-session confirmation before recording it as theirs.
65. Merge per the merge-flow binding slot; any PR filed along the way follows pr-writing.md; then post the close-out on the tracker item.
66. Unless the announce toggle records `off`, the close-out carries the cost line: build tokens vs total review tokens summed across all rounds, with the round count; read from harness per-agent spend reports, or "not readable in this harness" — never an estimate.
67. Where the orchestrator's own wake times are readable, the close-out names the longest between-wake gap while lanes were live; a gap past the cache TTL is reported as a cadence miss, never silently absorbed.
68. The close-out carries the announce-compliance line: `rounds announced: N of N` across the lane's launch and every review round.
69. Prune the lane afterward: workspace, branch, per-lane resources; verify the lane's processes are actually dead yourself before tearing down shared resources — a "servers down" claim from a report is not evidence.
70. Last of all, hand the dead lane's session to the human for archiving — only after merge, tracker close-out, and pruning; name the session verbatim as the picker shows it; the human archives on their own time.
71. The orchestrator never calls an archive surface itself; if useful it retitles the finished lane before notifying (rename needs no confirmation).
72. Archive, never delete — archiving is reversible and the transcript survives; only the closed-out lane's own session is ever named, never a human's working session.
73. Archiving trails everything: an unanswered notification gates no work, only picker tidiness.
74. Native auto-archive on PR close: point PR-linked lanes at it only where it cannot preempt the close-out order (safe only when the lane has already stopped, its workspace is no longer needed, and the tracker close-out does not depend on the session staying live); otherwise the repo records `no` in the slot and uses the notification path.
75. Lanes running as in-process subagents have no picker session and nothing to archive.

## §6 Wrap-up and succession

76. At roughly half the context window, wrap up — finish the current step cleanly and start no new large work past the line.
77. Write the handoff via the handoff skill: state, shipped record, the tracker query as NEXT (never an enumerated item list), expensive lessons in GOTCHAS.
78. Arrange the successor per the lane-launch slot with a prompt that says "invoke orchestrate and follow its startup checklist" plus only what is unique to this moment; never restate the protocol in the prompt.
79. The title protocol outranks a launch surface's label convention: a chip-arranged successor's chip title is written in the orchestrator title shape, never a generic imperative task label; general form — any surface that fixes the title at spawn makes the launcher the titling actor at that moment.
80. Once the successor is confirmed live — evidence of its startup checklist completing (title switch is part of that evidence; a pre-titled successor's evidence is the rest of the checklist), not merely a first message — stop your own watches, shed the orchestrator title (retired marker, e.g. `Orchestrator (retired) — <repo>`), go quiet, stay quiet.
81. Where the harness does not support self-rename, the retirement retitle falls to the successor or the human; where no title surface exists, record the retirement in the handoff and final report.
82. A retired orchestrator's session is archived by the human when they see fit — never automatically, and never by the orchestrator.

## §7 Binding slots

83. The pack ships no orchestration machinery; the binding doc's orchestration section names per-repo: lane launch, workspace provisioning, monitoring, verification executor, merge flow.
84. Lane-launch slot records: launch mechanism; what is stamped on the tracker item (runner, model, workspace, branch); titling mechanism and actor (launcher-titles default, self-title only where genuinely supported).
85. Lane-launch slot records the runner policy, set by the decider: available runners, launch mechanism for each, preference policy — followed per §4, fallbacks loud per §4; repos build launchers against runner-parity.md.
86. The slot never opts a repo out of titling where the harness supports it.
87. The slot records which launch surfaces pre-title sessions; a pre-titling surface follows the title-protocol precedence.
88. The slot records whether the harness offers native auto-archive on PR close — `yes` only where it cannot preempt the close-out order; no slot puts an archive surface in the orchestrator's hands.
89. The slot carries the announce toggle (`announce model/effort: on/off`, default on) governing the model/effort additions, never either announcement's identity content; only the recorded line is a valid off-switch — a conversational "turn it off for now" is not — so audit mode can check it.
90. Monitoring slot: how watches run and how the orchestrator confirms the watch is armed; the polling interval is the slot's to set, but while lanes are live it stays under the prompt-cache TTL — a slot may poll faster, never slower.
91. Verification-executor slot: who re-runs a lane's verification and where per-command results land; records the review-tier policy set by the decider (table mapping close-out machinery to model + effort); canonical shape — mechanical verification on a cheaper model at low effort, adversarial review on real code or release-arming changes high, max reserved for decider-named cases, never a default.
92. Each tier records a floor as well as its ceiling — what it may NOT be used for — so cost-saving never silently weakens the review bar.
93. Deviation from a tier is loud in both directions, announced per the read-don't-guess rule; the §4/§5 announcements make actuals visible against the policy.
94. Merge-flow slot: the repo's integration mechanics and who may push what where.
95. A repo that has not filled the slots can still run the principles (inline watches, manual launches), but fills the slots before scaling past a lane or two.

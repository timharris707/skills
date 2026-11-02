# 0010: Easy helper work runs on faster Claude models, a one-week trial in this repo

- Date: 2026-11-01
- Links: [#368](https://github.com/timharris707/skills/issues/368); the decider's ruling in session; the Helper tiers entry under [Orchestration in the binding doc](../../team-workflow.md#orchestration)

Sessions in this repo hand easy work to helpers whose model is fixed in their definition
file under `.claude/agents/`. `scout` answers look-ups by reading and `Explore` searches
code, both on Haiku 5.5 at low effort and read-only. `mechanic` runs mechanical steps whose
request names a pass/fail check, on Sonnet 5.5 at medium effort. Work that takes judgment
(design, building a feature, review, any decision) stays on the session's own model. When a
mechanical step's check fails twice, or finishing it needs a call the request did not make,
the mechanic hands it back and the session's model redoes the step; work moves up from a
helper, never down. Helpers never run adversarial review,
skeptic passes, design, or decisions, and the review-tier policy is unchanged. The ruling
covers this repo only, and it is the decider's OK for these two models, which the decider's
standing rules otherwise make ask-first beyond the session's own model.

The trial runs from merge to 2026-11-09, about a week. Then the decider keeps, changes, or
drops it. Keep if, over the week: `scout` and `Explore` ran at least 10 times between them
and `mechanic` at least 3 times; five helper tasks from the week, the first three look-ups
or searches and the first two `mechanic` runs in the logs, replayed on the session's model
give the same answers and together take at least 20% longer there; at most 1 in 5 `mechanic` runs handed its step back, for either reason (its report
opens with `Handed back:`); and no close-out or review names a helper's mistake. Fewer runs than that
extends the trial a week instead of deciding it. The measurement reads session logs outside
the repo. A run counts as a helper run only when its agent type is `scout`, `Explore`, or
`mechanic` and its transcript shows that helper's pinned model, so a delegated verifier on
Haiku is not counted. No script for it lives here. A Claude Code session already running when a checkout first
gains `.claude/agents/` does not load the helpers until it restarts: until then `scout` and
`mechanic` are unknown to it, and `Explore` is still the built-in on the session's model.

The reason: on one machine over the 10 days before the ruling, every session and helper ran
Opus 5.5, and the model's own thinking and writing took 55% of a lead session's active time
and 46% of a helper's; the rest was commands running. Published output speeds put Opus 5.5
at about 80-96 tokens a second, Sonnet 5.5 at about 110-139, and Haiku 5.5 at about
137-235. So the best case is roughly 15% less working time on a Sonnet step and 25% on a
Haiku look-up, and only when the smaller model takes no extra steps and needs no redo. The
decider chose a measured trial in one repo over turning it on in every project at once, or
keeping everything on the session's model. Model rules are set per project, so other repos
are untouched. The keep bar's numbers are the orchestrator's proposal; the decider rules on
the result. An earlier draft of the bar, in the first version of #368, compared the share
of a helper's time spent in the model against a 46% baseline; it was dropped because that
share depends on the mix of tasks: Opus helpers measured on the day of the ruling spent 85%. Three
points were design calls made while building it, not the decider's:
helpers cannot start helpers of their own; sessions spawn them with no model or effort
parameter, since a per-call value overrides the pinned one; and the two read-only helpers
start without the CLAUDE.md files, as the built-in Explore does, so they start faster.

# 0007: Retro reads past sessions and routes labeled fixes

- Date: 2026-10-06
- Links: [#205 closing record](https://github.com/timharris707/skills/issues/205#issuecomment-6024724295), #304

The friction-to-protocol loop is a skill named **retro**, adapted from Matt Pocock's
`retro`, starting in `skills/in-progress/`. It reads a recent sample from one repo,
Claude Code and Codex, up to 8 sessions weighted toward rough ones unless the user names
sessions; a script trims each log, cheap readers (Sonnet) go through the trimmed logs,
the main model judges, and a cost estimate shows before the run. It returns a short
ranked list in plain words. Each finding names one owner of its fix (the project's own
setup, any skill from this skills repo, or the user's conduct rules) and one of four
labels by fixed rules: Critical, Highly recommended, Recommended, Worth considering. The
user picks: project and pack picks become tracker issues, conduct-rule picks are drafted
by retro and added to the user's conduct-rules file (the one their global CLAUDE.md or
AGENTS.md loads, plus any mirror it names) and committed, and nothing else is fixed in
the retro session. Every pack issue describes the pattern only, since this repo's
tracker is public; fixes for repos the user marks confidential go to the user rather
than being filed there; and secrets are redacted in anything quoted. It runs on request;
a wrap-up offer after a rough session lands with promotion. It joins the team-workflow
pack once two test runs on two of the decider's private product repos, each on a known recent
episode (a run of repeated fix PRs to one component; a batch where most parallel work
items came back with problems), each name the problem already known and the decider judges
their top-labeled findings real.

The reason: the decider's standing conduct rules came from one hand-run audit of past session
transcripts, and the same friction keeps recurring across projects, so the loop is worth
running on request with a human choosing every fix, which is also why it never applies a
fix the user did not pick: Matt found that automating it sends the agent chasing false positives.

# 0009: Triage works the backlog in batches the decider approves in one pass

- Date: 2026-10-06
- Links: [#206 closing record](https://github.com/timharris707/skills/issues/206#issuecomment-6024835875), #305

Tracker triage is a skill named **triage**, adapted from Matt Pocock's `triage`, starting
in `skills/in-progress/`. It covers the needs-triage backlog in the decider's own repos,
and issues and pull requests from outside contributors on public repos; trackers a team
runs are out. It works in batches of about 15, oldest first. Every item gets a cheap check
against the current code for duplicates and already-fixed work, and one proposed move with
a one-line reason; the decider approves or changes the whole batch in one pass, and then
triage applies it. A bug is reproduced only before it is proposed as ready-for-agent, and a
ready-for-agent item meets the pack's work-item spec template: triage rewrites the body
when it does not, or when another account filed it, keeping the original text quoted below
the spec. An outside pull request is an issue with code attached: the same states except
ready-for-agent, since agents usually cannot push to a contributor's fork, plus a check
that the code does what it claims, and never merged without the normal review. The pack's
label vocabulary gains `needs-info` and `wontfix`; the existing labels stay, `bug`
included, and no type label is required. A declined request becomes a decision record in
this store rather than an `.out-of-scope/` folder. Triage runs on request, and comments
carry the pack's "responding on behalf of" attribution line instead of Matt's disclaimer.
When it is promoted, a lead session's startup notes the pile in one line when a repo has
more than 20 issues waiting. It joins the team-workflow pack once its first 15-issue batch
on the largest pile in the decider's repos has the decider approving most proposals as they
are, with every "already fixed" call checking out.

The reason: in the decider's own repos nearly every issue is filed under the decider's
account, mostly by agents, and each active product repo has a needs-triage pile of dozens,
so a batch the decider settles in one pass moves the pile where one issue at a time does
not. A team-run tracker is filed by the team and its tools, so its triage is the team's.
Declines go in this store because reviews and grillings already read it, so a declined
request is not proposed again and there is one memory instead of two. Four points were the
orchestrator's design calls rather than questions put to the decider, who may override
them: the spec-template bar for ready-for-agent, a pull request taking every state except
ready for an agent, the attribution line, and the startup note landing in orchestrate at
promotion.

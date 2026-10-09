---
name: retro
description: "Read a sample of one repo's past agent sessions, Claude Code and Codex, find the friction the agents hit, and return a short ranked list of fixes in plain words, each labeled and routed to whoever owns the fix. Use when the user asks for a retro or retrospective on agent work, asks what keeps going wrong in a repo's agent sessions, or names past sessions to mine for friction."
---

# Retro

A retro reads how agents actually worked in one repo and proposes changes to their **environment**, never to the code they wrote: a check that would have caught a mistake, a pointer that would have saved a search, a pack step that caused rework, a rule the user keeps restating by hand. Its raw material is **friction**: errors, retries, interruptions, compactions, and the moments the human had to step in.

The output is a short ranked list the user picks from. The retro session fixes nothing: picked fixes leave as tracker issues and run as normal work, except a conduct rule, which is added on the pick.

## Fix destinations

Every finding names exactly one owner of its fix:

- **Project**: the repo's own setup: its checks (a lint rule, a hook, a CI job), its CLAUDE.md or AGENTS.md, its docs, its tools.
- **Pack**: any skill from this skills repo, the team-workflow pack or a standalone one, when that skill's process caused the friction.
- **Conduct rules**: the user's standing conduct rules, when the friction is agent behavior the user corrects by hand and no rule covers.

## Labels

Check these in order; the first that fits is the finding's label.

1. **Critical**: an unsafe or irreversible action, or a leaked secret, even once.
2. **Highly recommended**: it recurred in two or more sessions, or it cost a review round or hours.
3. **Recommended**: seen once, with a cheap, clear fix.
4. **Worth considering**: a judgment call.

The list runs in label order. Within a label, a finding that hits what the repo's team-workflow binding doc says matters most ranks up (where the repo has no binding doc, its CLAUDE.md or AGENTS.md stands in), then costlier findings come before cheaper ones.

## Privacy

- Every quote is redacted: secrets become `<REDACTED>`. The trim script redacts what it writes, including any unquoted value of eight or more characters right after a secret flag (`--token`, `--api-key`), digit or not (a bare `$NAME` or `${NAME}` variable reference is kept), so an ordinary word there is hidden too: open the raw log when a hidden word looks harmless. Recheck each quote before it leaves the session, since no pattern list catches every secret.
- The pack's tracker is public. Every pack issue describes the pattern only, whichever repo the run is in: no customer data, code, people, or internal details.
- A project fix for a repo the user marks confidential goes to the user as text, never filed into that repo.

## What to look for

Each category names the friction to look for and the usual shape of its fix.

- **Navigation**: the agent was slow to find a file or a fact, or tripped on a hidden link between files. The fix is usually a **navigation pointer**: one line, in a file the agent already reads, saying where the thing lives.
- **Automated checks**: the agent made a mistake a check could have caught. Read the repo's own check commands first (its package scripts, its CI workflow): a check that exists but sits unwired or silently broken is the finding, not a new check. A repo with no **guardrail** (no pre-commit hook and no CI job running its lint, type check, or tests) is a finding in itself.
- **Coding standards**: the reviewer let a mistake through. Classify it first. A **mechanical** violation (a fixed pattern, a banned call, an import shape, a file-location rule) gets a check, in the repo's own linter, a hook, or a CI job, whichever is cheapest there. Only a real **judgment call** becomes a line in the reviewer's standards file.
- **Steering-file size**: a CLAUDE.md or AGENTS.md, in the repo or the user's global scope, has grown large with instructions that belong in a check or in the reviewer's standards.
- **Tool economy**: the agent made expensive tool calls that could be cheaper, or a custom tool spends tokens badly.
- **No-ops**: steering lines that do not change what the agent does.
- **Information access**: a fact the agent needed was out of its reach (server logs, read-only access to a service).
- **Pack friction**: a step in one of this repo's skills caused rework, was skipped or misread, or clashed with the repo's own setup.
- **Conduct-rule gaps**: the user corrected an agent behavior by hand that no standing rule covers.

### Choosing a fix's form

- The implementing agent works under the most context pressure: it explores, writes, and debugs. The reviewer receives a diff. Standards belong with the reviewer.
- CLAUDE.md and AGENTS.md load into every session: keep what a fix adds there to navigation pointers.
- The reviewer's standards file is read at review, not while implementing.
- Docs are reference reached by pointers: extend an existing doc before writing a new one.
- Steering text a fix proposes (a pointer line, a standards entry, a conduct rule) follows [writing-for-agents](../../author/writing-for-agents/SKILL.md).

## Steps

1. **Settle the scope.**
   - **Repo**: exactly one: the one the user names, else the current one.
   - **Sessions**: sessions the user names override the sample. Otherwise the sample is recent sessions from that repo, Claude Code and Codex both, up to 8, weighted toward rough ones.
   - **Log folders**: the defaults come from the environment and are always read. A user running several accounts keeps logs in several config folders; ask which other folders hold theirs.
   - **Confidentiality**: whether the repo is confidential, from the user's standing instructions where they say, else asked once.

   Done when repo, sessions, log folders, and confidentiality are settled.

2. **Trim the logs.** Run [scripts/trim_sessions.py](scripts/trim_sessions.py):

   ```bash
   python3 <this skill's folder>/scripts/trim_sessions.py --repo <repo path>
   ```

   Add `--session <id or path>` once per named session (a subagent's own transcript, named by path, counts as a session) and `--claude-dir` or `--codex-home` once per extra log folder (the default folders are read either way); `--help` lists the rest, and the script's header says how it scores roughness. It writes one trimmed log per session to a private temp folder and prints a table: each session's raw and trimmed size, trimmed tokens, and reader-cost guess (step 3). A trimmed log keeps the human's messages, tool errors, interruptions, compactions, and repeated calls, each line tagged `L<n>` with its line number in the raw log. A session's subagents, Claude Code and Codex alike, fold into it: their trimmed logs follow the parent's in the same file, and their errors count toward its roughness. A subagent log named by path without its parent, or one whose chain of parents ends outside the logs found, stands as a session of its own. A worktree outside the repo folder that has since been removed leaves sessions that no longer match the repo; when recent logs were skipped for that reason, the script warns on stderr with their count. Tell the user, and if they want those sessions read, name each log by path: Claude Code's sit in `projects/` folders whose names start with the repo path written with every non-alphanumeric character as `-`, and a Codex log records the repo's git remote in its first line. Without the script, read the logs directly, keep only those signals, and mark every size in the estimate as a guess. Done when every selected session has a trimmed log and its sizes are in hand.

3. **Estimate the cost, then wait.** Before any reader starts, show the user: the sessions and their dates; raw and trimmed sizes and the trimmed token total, from the script's table; the reader cost beside that total, since the trimmed total alone is not what readers spend; the plan, one reader per session on a cheap model (Sonnet or the harness's equivalent) and one judging pass on the main model; and a rough cost.

   The reader cost is the table's READER_EST total. Each reader costs about 75,000 tokens plus 1.6 times its log's trimmed tokens: the first number is the reader's startup, the multiple covers the log and the conversation re-sent on each read call. Say plainly that this is a calibrated guess, fitted to one run (16 readers spent about 1.91M tokens against the 460K first estimated), and may be refined. Without the script, apply the same formula to each log by hand. When the main session reads the logs itself, no reader starts up: leave the startup figure out, show the trimmed token total, and mark it as a guess.

   Price the tokens at the models' current rates, looked up rather than recalled; on a subscription with no per-call bill, give the token total and say so. If the user stops the run here, delete the folder of trimmed logs. Done when the user has seen the reader cost, or the trimmed token total where the main session reads, marked as a guess, and has said go, narrowed the run, or stopped it.

4. **Read.** One **reader** per trimmed log, on the cheap model where the harness can dispatch subagents; without subagents, the main session reads each log itself. Brief each reader with the categories above and this return shape, one entry per candidate: the category; what happened, in plain words; the `L<n>` lines that show it; the shortest quote that proves it; and what it cost, as far as the log shows (rework, a review round, time, a correction from the human). Brief each reader to read its trimmed log in one call where the harness's read limit allows, otherwise in the fewest, largest pieces that fit, each part once: no re-reading a part and no small slices, since every extra read re-sends the whole conversation. The main session reads the same way when it reads the logs itself. Readers propose; labels and destinations belong to the judge. Done when every log has a reader's list, an empty list stated as empty, and every reader was briefed to read its log in as few large pieces as the harness allows.

5. **Judge.** On the main model, for every candidate:
   - Verify it against its `L<n>` lines, opening the raw log where a quote needs context. Drop what the log does not show.
   - Merge the same pattern across sessions, and count the sessions it appeared in.
   - Check the repo as it stands now: a fix that already landed retires the finding.
   - Name its destination, give it the label its rules produce, and rank it.
   - Draft the fix: for a project or pack finding, an issue title and a few sentences; for a conduct-rule finding, the exact rule text.

   Done when every candidate is either a finding with verified evidence, one destination, a label, and a drafted fix, or dropped for a reason the judge can state.

6. **Report.** Deliver the list in the shape below. Done when it is delivered.

7. **Act on the picks.** The user picks by number; unpicked findings are dropped. Before filing an issue on a public tracker (the pack's always is), show the user its exact title and body, and file it only on their go. Pass every issue body as a file (`--body-file`), never inline in a shell command, so nothing in it runs. Each pick goes by its destination:
   - **Project**: file an issue on the tracker the repo's binding doc names, else the repo's GitHub issues, so the fix runs as normal work. For a repo the user marks confidential, hand the user the issue text instead.
   - **Pack**: write the body to a file with the file-writing tool, not the shell, then run `gh issue create --repo timharris707/skills --label process --title '<title>' --body-file <body file>`, with no backticks or single quotes in the title. Title and body follow the privacy rules above.
   - **Conduct rules**: add the drafted rule to the user's conduct-rules file (the rules file their global CLAUDE.md or AGENTS.md loads; ask when it is unclear), update every mirror the file says to keep in step, and commit where the file is under version control. No issue.

   The retro session changes nothing else: code, checks, docs, and settings change later, as each issue's normal work. Delete the folder of trimmed logs last. Done when every pick is filed, handed over, or added, the user has each link, and the trimmed logs are gone.

## The report

Write the report for someone who does not read code: plain sentences; a technical term the user will meet again gets a plain definition the first time it appears. Category names stay out of the report: they are the judge's tool, not the user's.

```text
Retro: <repo>, <N> sessions, <first date> to <last date>

1. Critical · Project
   What happened: <what went wrong, when, how often>
   What it cost: <rework, a review round, hours, risk>
   Fix: <the change, in plain words>
   Evidence: <session date, lines of its log>

2. Highly recommended · Your conduct rules
   What happened: ...
   What it cost: ...
   Rule to add: "<the exact rule text>"
   Evidence: ...
```

Close with one line on what was read (sessions, and any skipped with the reason) and the ask: pick the numbers to act on; project and pack picks become tracker issues, and conduct-rule picks are added to the user's rules file.

## Done when (checkable: verify each line before reporting complete)

- Repo, sessions, log folders, and confidentiality were settled before the trim ran.
- The user saw the cost estimate (sessions, raw and trimmed sizes, trimmed tokens, the reader cost marked as a guess, the reader plan, a rough cost) and said go before any reader started.
- Every trimmed log had a reader, every reader was briefed to read its log in as few large pieces as the harness allows, and every reader's list was judged.
- Every finding cites a session and log lines the judge verified; none rests on a reader's word alone.
- Every finding names one destination and carries the label its rules give, and the list runs in label order.
- No quote carries a secret, every pack issue describes the pattern only, and no issue was filed into a repo the user marks confidential.
- Every issue for a public tracker was shown to the user, exact title and body, and filed only on their go.
- The retro session changed nothing beyond picked conduct rules: every other pick is a filed issue, or issue text in the user's hands.
- Every conduct-rule pick is in the rules file and each of its mirrors, committed where the file is versioned.
- The folder of trimmed logs is deleted.

## Attribution

Adapted from Matt Pocock's [`retro`](https://github.com/mattpocock/skills/tree/main/skills/engineering/retro) (MIT, v1.3.0). His: the retro as a look at the agent's environment rather than its code; the categories navigation, automated checks, coding standards, steering-file size, tool economy, no-ops, and information access, with the signals that point to each; reading the repo's own check commands before proposing a check, and counting a repo with no guardrail as a finding; the mechanical-versus-judgment split that sends mechanical violations to a check; the implementation-versus-review reasoning and file guidance behind "Choosing a fix's form"; and the human in the loop, with candidates presented for the user to act on.

Ours, from the grilling recorded on [#205](https://github.com/timharris707/skills/issues/205#issuecomment-6024724295): a sample of up to eight recent sessions from one repo across Claude Code and Codex in place of one session; the trim script, and the cost estimate shown before the run; cheap readers with a main-model judge; the three fix destinations; the four labels and their rules; findings that leave as tracker issues with nothing fixed in the session; drafted conduct rules added on the pick; the privacy rules; the pack-friction and conduct-rule-gap categories; and a report written for someone who does not read code.

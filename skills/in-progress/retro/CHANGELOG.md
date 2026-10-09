# Changelog: retro

All notable changes to the **retro** skill. Unversioned while in
`skills/in-progress/`; it joins the team-workflow pack, and its changelog, at promotion.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Codex subagents fold into their parent session** (#315), the way Claude Code
  subagents do. A Codex subagent's own log names its parent thread in its session
  header; the script indexes those headers, so a parent's trimmed file holds its own
  log and then each subagent's, and the subagents' errors and raw size count toward
  the parent's roughness and size. A subagent that a session in the sample folds in,
  at any depth, is not also a separate session, and a subagent named alongside its
  parent counts once; one named alone, or whose chain of parents ends outside the
  sample, stands as its own. A subagent is folded once per session id even when
  several Codex folders hold a copy of it. A subagent's user messages show as PROMPT
  lines, not human messages. Only a log's first session header counts, and a subagent
  forked from its parent leaves out the copy of the parent's history its log opens
  with, so the parent's compactions, interruptions, and errors are not counted twice.
  The copy ends at the log's `subagent_history_start_ordinal` where it has one, else
  just before the first `inter_agent_communication_metadata` row; a forked log with
  neither is counted whole.
- **A warning when sessions may be missing** (#315). Recent logs skipped only
  because their recorded working folder no longer exists (a removed worktree outside
  the repo folder) are counted when they otherwise look like the repo's: a Claude Code
  log whose project folder name starts with the repo path's, or a Codex log whose
  header records the repo's git remote. The script prints one line on stderr with the
  count and the `--session` hint, also when no session matched at all.
- **Initial skill** (#304), built to the grilling closing record on #205 and adapted
  from Matt Pocock's `retro` (MIT). Reads a sample of one repo's past agent sessions,
  Claude Code and Codex, up to 8 by default and weighted toward rough ones, or the
  sessions the user names. Shows a cost estimate before any reading starts; cheap
  readers go through the trimmed logs and the main model judges. Returns a short
  ranked list in plain words, each finding labeled Critical, Highly recommended,
  Recommended, or Worth considering by fixed rules, and routed to one owner: the
  project, any skill from this repo, or the user's conduct rules. The user picks;
  project and pack picks become tracker issues, conduct-rule picks are added to the
  user's rules file, and nothing else is fixed in the retro session. Privacy rules:
  secrets redacted in every quote, pattern-only pack issues, public issues shown to
  the user before filing, and no filing into a repo the user marks confidential.
- `scripts/trim_sessions.py`: finds a repo's recent Claude Code logs, with each
  session's subagent logs folded in, and Codex logs, filtered to the repo and its
  worktrees. It reads the default folders (`CLAUDE_CONFIG_DIR` or `~/.claude`,
  `CODEX_HOME` or `~/.codex`) plus each `--claude-dir` or `--codex-home`. It trims
  each log to the human's messages, tool errors, interruptions, compactions, and
  repeated calls with common secret shapes redacted, writes one file per session named
  by its full id, and reports each session's size before and after trimming. Standard
  library only, with unit tests on synthetic fixtures run in CI.

### Changed
- **A secret flag's unquoted value is redacted even without a digit** (#315). After
  `--api-key`, `--token`, `--secret`, and the rest of that flag list, an unquoted value
  of eight or more characters is now hidden whether or not it holds a digit, so a
  lowercase passphrase no longer passes through. The cost, written into the pattern's
  comment and the skill's Privacy section: an ordinary word of eight or more characters
  right after such a flag in prose is hidden too. Quoted values, values under eight
  characters, and flags that only contain a secret word (`--max-tokens`) are as before,
  and so is a value that is only an environment-variable reference (`$API_KEY` or
  `${GITHUB_TOKEN}`), which names a secret without holding one.

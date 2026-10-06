# Changelog: retro

All notable changes to the **retro** skill. Unversioned while in
`skills/in-progress/`; it joins the team-workflow pack, and its changelog, at promotion.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
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

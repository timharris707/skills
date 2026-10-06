# Changelog: triage

All notable changes to the **triage** skill. Unversioned while in
`skills/in-progress/`; it joins the team-workflow pack, and its changelog, at promotion.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Initial skill** (#305), built to the grilling closing record on #206 (decision 0009)
  and adapted from Matt Pocock's `triage` (MIT). Works a repo's needs-triage backlog, and
  outside contributors' issues and pull requests, in batches of about 15, oldest first.
  Each item gets a cheap reading check for duplicates, already-fixed work, and requests
  declined before, then one proposed move with a reason in plain words. The decider
  approves or changes the whole batch in one reply, and only then does triage label,
  comment, and close. A bug is reproduced only before it goes to an agent, running only
  the repo's own code, and a ready-for-agent item meets the pack's work-item spec
  template. An outside pull request takes the same moves except ready for an agent, plus
  a check of its diff against its claim; triage never merges one or runs its code.
  Declines become domain-memory decision records. Runs on request; the lead-session
  startup note for a pile over 20 lands at promotion.

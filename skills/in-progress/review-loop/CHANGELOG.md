# Changelog: review-loop

All notable changes to the **review-loop** skill. Unversioned while in
`skills/in-progress/`; it gets a version and release tags at promotion.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Initial skill.** Before a pull request opens, Codex reviews the branch against its base
  with `codex review`, the author fixes what holds up or declines it with a reason, and the
  loop repeats until a round is clean or three rounds have run. The PR description records
  the rounds and the verdict. Adapted from the pre-PR review loop Theo Browne describes in
  his videos (his skill is unpublished); built so the PR review bot can review each PR once.

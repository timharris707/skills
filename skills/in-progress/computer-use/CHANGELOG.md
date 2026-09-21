# Changelog — computer-use

All notable changes to the **computer-use** skill. Parked in `in-progress/` until the
promotion gates are met; versioned as `computer-use/vX.Y.Z` once promoted.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- First cut (2026-09-20). Runner `scripts/computer_use.py` with `preflight [--live]`,
  `resolve-app`, `approvals inspect|add`, `run`, `resume`, `prune-runs`. Profile-aware
  (`CODEX_HOME`), open-ended app targeting, fail-closed audit of the Codex event stream,
  evidence provenance and validation, private run directory with retention. Design
  follows Astra's review of the 2026-09-20 brief (`~/Desktop/computer-use-skill-proposal/`).
- Adversarial review before the first commit (two finders, findings reproduced against
  the code) closed: risky recorded actions now block unless the user's pre-approval names
  them; evidence must come from this run (helper screenshot folder or the event stream),
  be a real image, under a size cap, not a symlink; `prune-runs` deletes only directories
  the runner made; Sky calls with non-literal arguments or inside loops are recorded and
  block; actions outside Sky block; helper errors anywhere in the stream fail; unknown
  privacy status is a problem, not a pass; `approvals add` preserves other keys, writes
  atomically, and never overwrites a backup; resume parses only the new bytes of the
  event stream and launches nothing unless the answer is an unqualified yes.

- `approvals plan` (read-only inventory of installed apps vs the approval file, with the
  exact `add` command), `routing` in preflight (which provider and base URL a live call
  would bill through, or direct), Finder added to the inventory (it lives in CoreServices).

- Second adversarial review (the evening's additions) closed: `routing` now uses the
  standard-library TOML parser on top-level keys only, so a `[profiles.*]` provider can no
  longer read as the live route; single-quoted strings, quoted provider keys, inline
  tables, and comments parse; an unresolvable provider or unreadable config is a
  `parse_error`, and preflight treats a direct-billing config or an unknown route as a
  problem (`--allow-direct` to override). The inventory includes apps one vendor folder
  deep, reports what it skipped and why, and survives odd Info.plist files; `approvals
  plan` reports an unreadable approval file instead of proposing to add everything; a
  bundle ID can no longer start with `-`.

### Verified live, 2026-09-20 evening

- End to end on all four of the user's Codex profiles: live preflight and a read-only
  Chrome run, `done`, screenshots opened and matched. Calculator and Spotify by bundle ID,
  `done`, screenshots matched. Finder refused at preflight (not approved): the expected
  boundary, no model call. Approval file grew 1 to 77 IDs with backup; the helper honoured
  the change without any restart. All calls routed through the local proxy.

### Not yet verified

- Any state-changing action, the live `needs_confirmation` and `resume` path, apps beyond
  the three tested, other Macs.

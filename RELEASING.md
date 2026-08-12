# Releasing

This repo ships its skills as **GitHub releases** cut from **skill-scoped, annotated git tags**.

**The normal path is automatic.** When a PR that bumps a plugin `version` in
[`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) merges to `main`,
[`.github/workflows/auto-release.yml`](.github/workflows/auto-release.yml) cuts the missing
`<name>/vX.Y.Z` annotated tag at the merge commit and publishes the release from the changelog
section — the version bump in the reviewed PR *is* the release decision. Changelog sections are
validated **before** anything is tagged: a bumped version with a missing/empty section fails the
run red with nothing tagged, so fixing the changelog and re-triggering retries cleanly. The
workflow can also be **dispatched by hand** (Actions → auto-release → Run workflow) to reconcile:
it scans every plugin for a missing tag *or* a missing release and heals both. (This exists
because the manual tag-after-merge step was missed four times in one day — see #115.)

Pushing a version tag by hand still works and triggers
[`.github/workflows/release.yml`](.github/workflows/release.yml); both paths run the same
[`release-core.yml`](.github/workflows/release-core.yml). You never run `gh release create` by hand.

## Conventions

- **Tag format:** `<skill>/vMAJOR.MINOR.PATCH` — e.g. `advisory-board/v0.5.0`. Skill-scoped so each
  skill in the repo versions independently and tags never collide.
- **Scheme:** use SemVer for each skill's documented behavior. Increment **major** for an
  incompatible CLI, recipe, or workflow-contract change; **minor** for backward-compatible
  capabilities and deliberate default expansions whose old behavior remains available through
  explicit flags; and **patch** for backward-compatible fixes. Model and artifact schema versions
  such as `advisory-board/verdict@N` are separate axes and do not replace the skill version.
- **Packs:** skills that ship and version **together** release under one **pack-scoped tag**
  instead of per-skill tags. The `team-workflow` pack releases as `team-workflow/vX.Y.Z` with one
  changelog at [`packs/team-workflow/CHANGELOG.md`](packs/team-workflow/CHANGELOG.md).
  A pack is not a skill, so its changelog lives outside `skills/`. Individual pack skills never get
  their own tags. The pack's plugin `version` in
  [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) mirrors the latest pack tag;
  bump it in the release commit. Standalone skills (e.g. advisory-board) keep per-skill tags.
- **Cadence:** cut a release **when a milestone PR merges to `main`** — not on every PR. Infra-only,
  CI-only, and docs-only PRs do **not** get a tag or release (no tag → the workflow never fires).
- **Notes source:** each releasable name keeps a
  [`CHANGELOG.md`](skills/decide/advisory-board/CHANGELOG.md) (Keep a Changelog). The release body
  is its non-empty `## [vX.Y.Z]` section. A missing section fails the workflow; releases never
  silently fall back to generated notes.
- **Changelog resolution:** the workflow *searches* for the tag name's changelog rather than
  hard-coding a path — `skills/<bucket>/<skill>/CHANGELOG.md` for a standalone skill,
  `packs/<pack>/CHANGELOG.md` for a pack. Moving a skill between buckets therefore never breaks its
  release. Exactly one match is required: zero or two both fail the workflow rather than guess.

## Per-PR habit

A milestone PR carries its own changelog entry so the release is ready the moment it merges:

1. Add your changes under `## [Unreleased]` in `skills/<skill>/CHANGELOG.md` as you work.
2. As part of the release commit, rename `## [Unreleased]` → `## [vX.Y.Z] - YYYY-MM-DD — <milestone>`
   and add a fresh empty `## [Unreleased]` above it.

## Cutting a release

**Normally: nothing to do.** Merge the milestone PR with its version bump and changelog section;
`auto-release` cuts the tag and publishes within a minute or two. Confirm on the **Releases** page.

**Manually** (a retroactive tag on an older commit, or a repo state auto-release can't infer) —
after the milestone PR has **merged to `main`**:

```bash
git fetch origin
git checkout main && git pull            # or: branch from origin/main

# 1. Make sure skills/<skill>/CHANGELOG.md has a "## [vX.Y.Z] - DATE" section on main
#    (this normally lands with the milestone PR). If not, add it via a small PR first.

# 2. Annotated, skill-scoped tag on the release commit on main (which includes the
#    milestone's code AND its changelog section). The workflow refuses tags that
#    do not point to commits reachable from origin/main:
git tag -a advisory-board/v0.5.0 -m "advisory-board v0.5.0 — M5: canonical verdict + resolved evidence"

# 3. Push the tag — this is what triggers the release workflow:
git push origin advisory-board/v0.5.0
```

The `release` workflow then publishes a GitHub release titled `advisory-board v0.5.0` with the
changelog section as its body. Confirm it on the repo's **Releases** page (or `gh release view
advisory-board/v0.5.0`).

Pull requests must pass the repository CI workflow before merge. Perform the project's required
review before committing or merging; tag only the reviewed release commit.

## Fixing a release

```bash
gh release delete advisory-board/v0.5.0 --yes        # remove the release
git push origin --delete advisory-board/v0.5.0       # remove the remote tag
git tag -d advisory-board/v0.5.0                      # remove the local tag
# re-tag the corrected commit and push again
```

## Mechanism

The release logic lives once, in
[`.github/workflows/release-core.yml`](.github/workflows/release-core.yml) (`workflow_call`): it
validates the tag shape, requires an annotated tag reachable from `origin/main`, reads the
mandatory changelog section, and calls `gh release create` with `contents: write` permission (the
only scope it needs). Two callers:

- [`release.yml`](.github/workflows/release.yml) — any manually pushed tag matching `*/v*.*.*`.
- [`auto-release.yml`](.github/workflows/auto-release.yml) — pushes to `main` touching the
  marketplace manifest, plus manual dispatch (main only): scans every plugin's `version` for a
  missing tag *or* missing release, validates each needed changelog section via the shared script
  **before** cutting anything, then cuts missing annotated tags at the current commit and calls
  the core per tag. Tags it pushes use `GITHUB_TOKEN`, whose pushes fire no tag-push workflows —
  that is why it calls the core directly (a concurrent manual push of the same tag is safe: the
  tag job skips existing tags, and the core accepts an existing release only on a byte-exact
  title/body match). A retroactive tag on an old commit whose changelog lacks the section will
  fail the core; create that release manually from the current changelog section
  (`gh release create <tag> --notes-file …`), or delete the tag and let a dispatch re-cut it at
  current main.

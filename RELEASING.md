# Releasing

This repo ships its skills as **GitHub releases** cut from **skill-scoped, annotated git tags**.
Pushing a version tag triggers [`.github/workflows/release.yml`](.github/workflows/release.yml),
which publishes the release automatically — you never run `gh release create` by hand.

## Conventions

- **Tag format:** `<skill>/vMAJOR.MINOR.PATCH` — e.g. `advisory-board/v0.5.0`. Skill-scoped so each
  skill in the repo versions independently and tags never collide.
- **Scheme (semver), pre-1.0:** the **minor** tracks the conductor milestone — M5 → `v0.5.0`,
  M6 → `v0.6.0` — and **`v1.0.0` is reserved for an explicit "production-ready" call**, not an
  automatic milestone bump. Use the **patch** for follow-up fixes within a released milestone
  (`v0.5.1`). This is a separate axis from the verdict-JSON schema version (`advisory-board/verdict@N`).
- **Cadence:** cut a release **when a milestone PR merges to `main`** — not on every PR. Infra-only,
  CI-only, and docs-only PRs do **not** get a tag or release (no tag → the workflow never fires).
- **Notes source:** each skill keeps a [`CHANGELOG.md`](skills/advisory-board/CHANGELOG.md)
  (Keep a Changelog). The release body is that skill's `## [vX.Y.Z]` section; if it's missing the
  workflow falls back to GitHub's auto-generated notes.

## Per-PR habit

A milestone PR carries its own changelog entry so the release is ready the moment it merges:

1. Add your changes under `## [Unreleased]` in `skills/<skill>/CHANGELOG.md` as you work.
2. As part of the release commit, rename `## [Unreleased]` → `## [vX.Y.Z] - YYYY-MM-DD — <milestone>`
   and add a fresh empty `## [Unreleased]` above it.

## Cutting a release

After the milestone PR has **merged to `main`**:

```bash
git fetch origin
git checkout main && git pull            # or: branch from origin/main

# 1. Make sure skills/<skill>/CHANGELOG.md has a "## [vX.Y.Z] - DATE" section on main
#    (this normally lands with the milestone PR). If not, add it via a small PR first.

# 2. Annotated, skill-scoped tag on the current tip of main (which now includes the
#    milestone's code AND its changelog section):
git tag -a advisory-board/v0.5.0 -m "advisory-board v0.5.0 — M5: canonical verdict + resolved evidence"

# 3. Push the tag — this is what triggers the release workflow:
git push origin advisory-board/v0.5.0
```

The `release` workflow then publishes a GitHub release titled `advisory-board v0.5.0` with the
changelog section as its body. Confirm it on the repo's **Releases** page (or `gh release view
advisory-board/v0.5.0`).

> **Commit gate:** the skills repo blocks a bare `git commit` (see the project's review-before-commit
> hook). A changelog/release commit is trivial — use `SKIP_REVIEW=1 git commit …`. Tagging and
> pushing a tag are not commits and are not gated.

## Fixing a release

```bash
gh release delete advisory-board/v0.5.0 --yes        # remove the release
git push origin --delete advisory-board/v0.5.0       # remove the remote tag
git tag -d advisory-board/v0.5.0                      # remove the local tag
# re-tag the corrected commit and push again
```

## Mechanism

[`.github/workflows/release.yml`](.github/workflows/release.yml) runs on any pushed tag matching
`*/v*.*.*`. It splits the tag into `<skill>` and `vX.Y.Z`, reads `skills/<skill>/CHANGELOG.md` for
the matching section, and calls `gh release create` with `contents: write` permission (the only
scope it needs). [`.github/release.yml`](.github/release.yml) categorizes the auto-generated
fallback notes by PR label.

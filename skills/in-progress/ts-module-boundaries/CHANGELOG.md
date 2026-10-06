# Changelog — ts-module-boundaries

All notable changes to the **ts-module-boundaries** skill. Unversioned while in
`skills/in-progress/`; versioning starts at promotion.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Initial skill** (#303): enforced module boundaries for TypeScript repos,
  adapted from Matt Pocock's in-progress `setup-ts-deep-modules` (MIT). A package
  is reachable only through its entry-point files, checked by dependency-cruiser
  in a merge-gating CI job and proven to bite with a deliberate bad import.
  Seven steps (read the ground, settle the shape with the decider, install and
  configure, wire into CI, settle existing violations, prove it bites, put the
  rule where agents meet it), a checkable Done-when, and a parameterized config
  at `references/dependency-cruiser.config.cjs`, plus a TypeScript guard at
  `references/check-typescript-support.mjs`.
- Changes from upstream, each found by running the config against fixture repos
  and a private npm-workspaces monorepo: entry-point shape is a setting (one
  file per package, named files, or every root file) so workspace packages with
  a single `src/index.ts` fit, and a non-code export such as a stylesheet can be
  listed as an entry; the tests rule is opt-in; type-only and unused imports are
  counted (upstream's config let a deep `import type`, and its own example probe,
  an unused deep import, pass silently); the check's scope is every importer
  directory, not the packages root; a TypeScript version outside
  dependency-cruiser's range skips every `.ts` file and exits 0, so
  `lint:boundaries` runs a guard first that fails when the linter cannot read
  TypeScript, and the proof puts each probe in a `.ts` file instead of trusting
  a module count (a stray `.mjs` makes the count nonzero while every `.ts` file
  is skipped); existing violations are fixed or baselined with tickets; the shape
  decision is the decider's and is recorded through domain-memory; the new check
  reaches the binding doc through a setup re-run.

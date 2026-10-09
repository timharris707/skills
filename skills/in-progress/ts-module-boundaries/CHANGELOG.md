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
  an unused deep import, pass silently); the resolver tries every TypeScript and
  JavaScript extension (upstream's list left out `.d.ts`, `.mts`, `.cts`, `.mjs`,
  and `.cjs`, so an extensionless deep import of such a file stayed unresolved,
  matched no rule, and passed); the check's scope is every importer
  directory, not the packages root; a TypeScript version outside
  dependency-cruiser's range skips every `.ts` file and exits 0, so
  `lint:boundaries` runs a guard first that fails when the linter cannot read
  TypeScript, and the proof puts each probe in a `.ts` file instead of trusting
  a module count (a stray `.mjs` makes the count nonzero while every `.ts` file
  is skipped); existing violations are fixed or baselined with tickets; the shape
  decision is the decider's and is recorded through domain-memory; the new check
  reaches the binding doc through a setup re-run.
- **Unresolved imports fail the check** (#316): the config gains a fifth rule,
  `not-to-unresolvable`, that fails any import dependency-cruiser could not
  resolve. Before, such an import kept its raw text, matched no rule, and passed,
  so any resolution gap not already closed by the extension list would have let
  a deep import through. The rule needs package `exports` resolution to keep a
  legitimate second entry such as `@pkg/billing/testing` passing, so the config
  also turns on `exportsFields` and `conditionNames` (`import`, `require`,
  `node`, `default`, `types`, the set dependency-cruiser's own init template
  uses). That changes how every package-name import resolves: a deep
  package-name import into a package with an `exports` map now fails as
  unresolved rather than as a boundary breach, and a repo's first run may
  surface new failures, which go to the decider in step 5. The skill lists five
  rules, step 3 says what the exports setting changes, and step 6 names the new
  rule's probe.
- **A permanent test for the guard and the config** (#314): the repo's first
  Node test job. A fixture repo at `tests/ts-module-boundaries/` (an npm
  workspace with three packages, code outside them, and one probe per rule) runs
  the shipped guard and the shipped config, with the config's three constants
  set by the test. The guard must exit 0 on the pinned TypeScript 6.0.3 and
  exit 1 on TypeScript 7.0.2, outside dependency-cruiser 18.5.0's supported
  range. The clean fixture must pass, and each probe must fail naming exactly
  its own rule, once. A rule added to the config without a probe fails the
  test. The job is its own workflow file, runs only when the skill, the
  fixture, or the workflow changes, and pins Node 22.23.3 exactly, with
  dependency-cruiser and TypeScript pinned by a lockfile per fixture.

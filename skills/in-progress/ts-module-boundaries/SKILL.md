---
name: ts-module-boundaries
description: "Make each package in a TypeScript repo reachable only through its entry-point files, enforced by a dependency-linter check in CI and proven to bite with a deliberate bad import. Use when the decider asks for enforced module boundaries or deep modules, when a codebase-review boundaries-vs-reality finding is adopted for a TypeScript repo, or when code keeps importing past a package's entry points."
---

# TypeScript module boundaries

A package is a module, and its **entry points** (the one or few files other code may import from it) are where its interface lives. Everything behind them is implementation. This skill installs the check that makes that true: a dependency linter (a tool that reads every import and fails the build on one that breaks a rule), run in CI, that fails any import reaching past an entry point, then proves the check fails when it should.

Terms follow the [design vocabulary](../../investigate/codebase-review/references/design-vocabulary.md): module, interface, seam, depth. The entry points are the package's seam, and the check keeps imports from crossing anywhere else. It is the enforcement half of [codebase-review](../../investigate/codebase-review/SKILL.md)'s boundaries-vs-reality lens: the lens finds where change bypasses the declared layout, and this skill makes the declared layout hold. Layering (which package may depend on which) is a different concern and stays out.

Read the team-workflow binding doc first: its verify commands, memory home, and agent-context docs are what this skill writes to. A repo with no binding doc runs on its own scripts, and the hand-back names the unbound slots.

## The rules the check enforces

All `error`:

1. **From outside.** Code outside every package (apps, scripts, root tests) imports a package only through its entry points.
2. **Across packages.** A package's own files import each other freely and reach another package only through its entry points.
3. **Tests (opt-in).** For repos where each package keeps its tests in a private `tests/` folder: tests import any package's entry points and their own `tests/` fixtures, never any package's internals (not even their own), and nothing outside a `tests/` folder imports one. The interface is the test surface.
4. **No runtime cycles.** Type-only imports do not count.

Entry points come in three shapes, set by the config's `ENTRY_POINTS` constant: one file per package (`src/index.ts`, for a workspace package whose `main` points there), several named files, or every file at the package root with the code in subfolders. A non-code export, such as a stylesheet, is listed by name with its extension (`styles\\.css`). Prefer several small entry points to a barrel that re-exports a whole subtree: a barrel makes the interface nearly as wide as the implementation, which is what shallow means.

## Steps

### 1. Read the ground

Detect from the repo, with file evidence for each:

- **Package manager**: the lockfile.
- **Packages and their entry points**: workspace globs (`workspaces` in `package.json`, `pnpm-workspace.yaml`), each package's `main` and `exports` (a non-code export such as a stylesheet is an entry point too); failing that, folders shaped `<root>/<name>/index.ts`.
- **Importer directories**: every directory holding code that imports a package (apps, scripts, root tests). This is the check's scope.
- **Alias tsconfig**: the tsconfig that holds the `paths` aliases.
- **Existing boundary tooling**: a dependency-cruiser config, `eslint-plugin-boundaries` or `no-restricted-imports` rules, Fallow `boundaries`, Nx, Sheriff, Steiger, a `lint:boundaries` script. Put it to the decider: extend it, or replace it with this skill's config. One rule never runs under two linters.
- **TypeScript version**: dependency-cruiser supports a bounded range, and a version outside it skips every `.ts` file and still exits 0 (the linter's own warning names the range). Outside the range, stop and report to the decider; do not downgrade TypeScript or swap tools unasked. Step 3 installs a guard so a later bump fails the check instead of passing it.

**Done when:** each item is written down with its evidence, the existing-tooling question is answered (or the repo has none), and the TypeScript version is inside the linter's range.

### 2. Settle the shape with the decider

Brief the decider in plain words, with a recommendation and the step 1 evidence for each:

- **Entry-point shape**: one file per package, several named files, or every root file.
- **Tests**: beside the code they test (the opt-in rule stays off), or in a private `tests/` folder per package (it goes on).

A repo with no package yet has nothing to enforce. The decider names the areas that become packages, with [codebase-review](../../investigate/codebase-review/SKILL.md)'s shallow-modules lens as the source of candidates, or approves the scaffold in step 6.

**Done when:** the shape and tests answers are the decider's, recorded as a decision record with its load-bearing reason where the binding names a [domain-memory](../../orient/domain-memory/SKILL.md) home, otherwise in the PR description.

### 3. Install and configure

- Install `dependency-cruiser` as a devDependency with the detected package manager.
- Copy [references/dependency-cruiser.config.cjs](references/dependency-cruiser.config.cjs) to `.dependency-cruiser.cjs` (`.cjs` so it loads in a `"type": "module"` repo). Set its three constants to the step 2 answers and `tsConfig.fileName` to the alias tsconfig.
- Copy [references/check-typescript-support.mjs](references/check-typescript-support.mjs) to `scripts/check-typescript-support.mjs` (or the repo's equivalent scripts folder). It exits 1 when dependency-cruiser cannot read TypeScript, which step 4 puts in front of every run.
- Merge into an existing `.dependency-cruiser.*` and report what was added; the existing file is never overwritten.
- Leave `tsconfig` and the repo's path aliases as they are.

**Done when:** `.dependency-cruiser.cjs` exists with constants matching the decided shape, `depcruise` runs, and the guard exits 0.

### 4. Wire it into CI

- Add a `lint:boundaries` script: `node scripts/check-typescript-support.mjs && depcruise <every importer directory from step 1>`. A scope narrower than the importers sees no outside code, so rule 1 never fires. The guard comes first because dependency-cruiser warns about an unsupported TypeScript and still exits 0: without it, a later TypeScript bump turns the merge gate into a pass.
- Fold it into the umbrella check that already runs typecheck, where one exists.
- Add the same command as a step in a CI job that gates merge, or make its job a required check. CI runs the `lint:boundaries` script, never bare `depcruise`, so the guard stays in the path. A check outside the merge gate advises and enforces nothing.

**Done when:** a CI workflow runs `lint:boundaries` in a gating job, and the hand-back names the file and job.

### 5. Settle the violations already there

Run `lint:boundaries` once. A repo that never had the check usually fails it. Take each violation to the decider as fix or baseline:

- **Fix**: route the import through an entry point, by exporting from the entry or by opening a second entry named for its audience (`testing`, `server`).
- **Baseline**: record it as known with `node scripts/check-typescript-support.mjs && depcruise <dirs> --baseline` (writes `.dependency-cruiser-known-violations.json`), put `--ignore-known` in the `lint:boundaries` script, file a ticket per cluster ([to-tickets](../../run/to-tickets/SKILL.md)), and ratchet with `--baseline-mode shrink-only` as fixes land.

The rules, scope, and `pathNot` entries stay as step 2 decided; a violation is fixed or baselined, never excluded.

**Done when:** `lint:boundaries` exits 0 and every violation that was present is fixed or in the committed baseline with a ticket.

### 6. Prove it bites

Observe each outcome; assume none.

1. Run `lint:boundaries`: it passes.
2. Add a deliberate deep import in a real importer file, once per enabled rule and once per import style the repo uses (relative path, alias, package name). Write each probe in a `.ts` or `.tsx` file: a module count proves nothing about TypeScript, because dependency-cruiser counts plain `.js` and `.mjs` files while skipping every `.ts` file it cannot read, so only a probe that fails in a TypeScript file shows TypeScript is being read. Each run fails naming the rule: `entrypoint-boundary-from-outside`, `entrypoint-boundary-across-packages`, `tests-through-entrypoints`, `tests-folder-is-private` (probe it from a package's own non-test file importing its own `tests/` folder; an outside file would also trip `entrypoint-boundary-from-outside` and prove less), and, for a two-file import loop, `no-circular`.
3. Revert every probe and run again: it passes, and `git diff` shows no trace of them.

A repo with no package yet scaffolds `<packages-root>/example/` in the decided shape: an entry file exporting a function that delegates to an internal file in a subfolder, and, with the tests rule on, a test importing only the entry. It is the copy-me template and the probe target, and nothing else in the repo is enforced until code lives in packages; say so plainly.

**Done when:** you have seen a pass, a named fail for every probe (each in a TypeScript file), and a pass again. A probe that does not fail means the check is not wired: fix it before finishing.

### 7. Put the rule where agents meet it

- Write `README.md` in the packages folder: the layout, one sentence per enabled rule, how to run `lint:boundaries`, and the barrel preference.
- Add one context-pointer line to the repo's agent-instructions file (`CLAUDE.md`, else `AGENTS.md`, created if neither exists) naming that README, so an agent finds the rule before it trips on it.
- The new check is a changed verify command. Tell the decider to re-run [setup](../../orient/setup/SKILL.md), whose diff of the binding doc's verify commands picks it up and puts it into every brief's verification set.

**Done when:** the README exists and states the barrel preference, the pointer is in the agent-instructions file, and the decider has been told to re-run setup.

## When structure blocks the rules

A package whose code is one flat folder has nothing to hide, and an entry point over it hides nothing. Report that as a shallow-modules candidate to [codebase-review](../../investigate/codebase-review/SKILL.md) rather than restructuring inside this lane's diff ([implement](../../run/implement/SKILL.md)'s file-don't-fix rule).

## Done when (checkable: verify each line before reporting complete)

- Every step 1 item has file evidence, and the TypeScript version is inside the linter's range (or the run stopped there with a report).
- The entry-point shape and the tests answer are the decider's, on record.
- `.dependency-cruiser.cjs` carries constants matching those answers and an alias tsconfig that resolves the repo's aliased imports.
- `lint:boundaries` covers every importer directory, starts with the TypeScript guard, and runs in a CI job that gates merge; the file and job are named.
- `lint:boundaries` exits 0, and every pre-existing violation is fixed or in the committed baseline with a ticket.
- A pass, then a named fail for each probe (every enabled rule, every import style in use, each probe in a TypeScript file), then a pass, were all observed; the working tree holds no probe.
- The README and the context pointer exist, and the decider was told to re-run setup.
- The diff holds the config, the guard, the script, the CI step, the docs, and the dependency-cruiser devDependency with its lockfile change, plus the baseline if step 5 baselined any violation, the decider-approved import fixes if step 5 fixed any, and the `<packages-root>/example/` scaffold if the repo had no package, and nothing else.

## Attribution

Adapted from Matt Pocock's [`setup-ts-deep-modules`](https://github.com/mattpocock/skills/tree/main/skills/in-progress/setup-ts-deep-modules) (MIT, in progress upstream). The model is his: a package as a deep module whose entry points are its public surface and whose subfolders are private, enforced with dependency-cruiser group back-references so a package reaches its own internals while outsiders cannot, tests held to the entry points, several small entry points over a barrel, a deliberate bad import as the completion criterion, and a README plus a context pointer so agents find the rule.

What this repo changes: existing repos come first (the entry-point shape and the tests rule are settings read from the repo and confirmed by the decider, not a fixed `src/packages/<name>/{lib,tests}` layout, and the scaffold is only for a repo with no packages); an existing boundary tool and an unsupported TypeScript version are checked before anything is installed, and a guard keeps a later TypeScript bump from turning the check into a pass; the check's scope is every importer directory and it runs in a merge-gating CI job; violations already present are fixed or baselined with tickets; the proof runs once per rule and import style, each probe in a TypeScript file; type-only and unused imports are counted, because upstream's config let both pass (its own example probe, an unused deep import, never fails); the decision is recorded through domain-memory; the new check reaches the binding doc through a setup re-run; the vocabulary and the structural handoff come from codebase-review; and the rules are listed once, where upstream's text says four and its config holds five.

// @ts-check
// Module boundaries for dependency-cruiser: each package is reachable from
// outside only through its entry points, and everything else in it is private.
// Edit only the three constants below, plus tsConfig.fileName in options.
//
// Packages are flat: one tier of immediate children under PACKAGES_ROOT. A
// package's internals may nest as deep as they like; a package may not contain
// another package. The $1 back-reference in the rules ties a package to its own
// files, which is what lets it reach its internals while outsiders cannot: keep
// it, and do not flatten the rules into per-package copies.

/** Where packages live: one immediate child directory per package. */
const PACKAGES_ROOT = "packages";

/**
 * A package's entry points: the files outsiders may import. A regex relative
 * to the package directory. A code entry leaves its extension off (any JS/TS
 * extension matches); a non-code entry names its own.
 *   "src/index"                    one entry file (workspace packages whose main is src/index.ts)
 *   "src/(?:index|testing)"        several named entry files
 *   "src/(?:index|styles\\.css)"   a code entry plus an exported stylesheet
 *   "[^/]+"                        every file at the package root (code or not), with the code in subfolders
 */
const ENTRY_POINTS = "src/index";

/**
 * A private tests folder inside each package (e.g. "tests"), or null when tests sit beside the code.
 * @type {string | null}
 */
const TESTS_DIR = null;

// --- derived patterns (no need to edit) -------------------------------------
const R = PACKAGES_ROOT;
const EXT = "\\.[cm]?[jt]sx?";
const ANY_PACKAGE_FILE = `^${R}/[^/]+/`;
// The extension is optional via an empty alternative, not a "?" on the group:
// dependency-cruiser rejects a quantified group that holds quantifiers.
const ENTRY = `^${R}/[^/]+/(?:${ENTRY_POINTS})(?:${EXT}|)$`;
const ANY_TESTS = `^${R}/[^/]+/${TESTS_DIR}/`;
const OWN_TESTS = `^${R}/$1/${TESTS_DIR}/`;

/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "entrypoint-boundary-from-outside",
      comment: "Code outside every package may import a package's entry points, never its internals.",
      severity: "error",
      from: { pathNot: `^${R}/` },
      to: { path: ANY_PACKAGE_FILE, pathNot: ENTRY },
    },
    {
      name: "entrypoint-boundary-across-packages",
      comment: "A package's own files import each other freely, but reach another package only through its entry points.",
      severity: "error",
      from: { path: `^${R}/([^/]+)/`, ...(TESTS_DIR === null ? {} : { pathNot: ANY_TESTS }) },
      to: { path: ANY_PACKAGE_FILE, pathNot: [ENTRY, `^${R}/$1/`] },
    },
    ...(TESTS_DIR === null
      ? []
      : [
          {
            name: "tests-through-entrypoints",
            comment: "A package's tests use it through its entry points like everyone else: any package's entry points and their own tests folder, never any package's internals, not even their own.",
            severity: "error",
            from: { path: `^${R}/([^/]+)/${TESTS_DIR}/` },
            to: { path: ANY_PACKAGE_FILE, pathNot: [ENTRY, OWN_TESTS] },
          },
          {
            name: "tests-folder-is-private",
            comment: "A tests folder is reachable only from tests: nothing else imports fixtures.",
            severity: "error",
            from: { pathNot: ANY_TESTS },
            to: { path: ANY_TESTS },
          },
        ]),
    {
      name: "no-circular",
      comment: "No runtime dependency cycles. Imports that exist only before compilation (type-only) are not counted.",
      severity: "error",
      from: {},
      to: { circular: true, viaOnly: { dependencyTypesNot: ["pre-compilation-only"] } },
    },

    // Layering (optional, off by default). The rules above control HOW a package is
    // imported; layering controls WHICH packages may depend on which. Add your own, e.g.:
    // { name: "ui-may-not-depend-on-billing", severity: "error",
    //   from: { path: `^${R}/ui/` }, to: { path: `^${R}/billing/` } },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    // Count type-only and unused imports too ("specify" tags them, so no-circular can skip
    // them); without this a deep `import type` slips past the boundary rules.
    tsPreCompilationDeps: "specify",
    // The tsconfig that holds the repo's path aliases, so aliased imports resolve.
    tsConfig: { fileName: "tsconfig.json" },
    enhancedResolveOptions: { extensions: [".ts", ".tsx", ".js", ".jsx", ".json"] },
  },
};

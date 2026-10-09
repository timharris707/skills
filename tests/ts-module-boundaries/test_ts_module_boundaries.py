"""Tests for the ts-module-boundaries skill's two shipped support files (#314, #316).

The skill ships a TypeScript support guard and a dependency-cruiser boundary
config. Both are exercised here exactly as shipped: each test copies the
fixture repo into a scratch folder, copies the shipped guard to
scripts/check-typescript-support.mjs and the shipped config to
.dependency-cruiser.cjs (setting only the config's three constants, as the skill's
step 3 tells a reader to), then runs the real tools. An edit to either shipped
file is what gets tested; the fixture holds no copy of them.

Needs Node and the fixture installs: run `npm ci` in `fixture/` and in
`out-of-range-typescript/` first (CI does). A missing install fails the test
loudly instead of skipping it.

  * Guard: exits 0 with the pinned TypeScript, and exits 1 with its own message
    with a TypeScript outside dependency-cruiser's supported range.
  * Config: the clean fixture passes, and every rule the config holds fails on
    its own probe, once, naming that rule. The fixture runs with the tests
    folder turned on so both tests-folder rules are live.
"""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Any bucket, so promoting the skill out of in-progress/ breaks nothing here.
_SKILL_DIRS = list((HERE.parents[1] / "skills").glob("*/ts-module-boundaries/references"))
assert len(_SKILL_DIRS) == 1, f"expected one skills/<bucket>/ts-module-boundaries/references, found {_SKILL_DIRS}"
REFERENCES = _SKILL_DIRS[0]
GUARD = REFERENCES / "check-typescript-support.mjs"
CONFIG = REFERENCES / "dependency-cruiser.config.cjs"
FIXTURE = HERE / "fixture"
OUT_OF_RANGE = HERE / "out-of-range-typescript"

# The three constants the skill's step 3 tells a reader to set.
CONSTANTS = {
    "PACKAGES_ROOT": '"packages"',
    "ENTRY_POINTS": '"src/(?:index|testing)"',
    "TESTS_DIR": '"tests"',
}

# Directories the skill's step 4 passes to depcruise: every importer directory.
SCOPE = ["packages", "apps"]

ERROR_LINE = re.compile(r"^\s*error ([\w-]+): ", re.M)

# One probe per rule (two for the unresolved-import rule: a missing file and a
# missing package). Each probe is a TypeScript file: a plain JavaScript probe
# proves nothing about TypeScript (the skill's step 6).
PROBES = [
    ("entrypoint-boundary-from-outside", {
        "apps/web/probe.ts": 'import { record } from "../../packages/billing/src/internal/ledger";\nexport const p = record;\n',
    }),
    ("entrypoint-boundary-across-packages", {
        "packages/ui/src/probe.ts": 'import { record } from "../../billing/src/internal/ledger";\nexport const p = record;\n',
    }),
    ("tests-through-entrypoints", {
        "packages/ui/tests/probe.ts": 'import { label } from "../src/internal/button";\nexport const p = label;\n',
    }),
    ("tests-folder-is-private", {
        "packages/billing/src/probe.ts": 'import { sampleCents } from "../tests/fixtures";\nexport const p = sampleCents;\n',
    }),
    # A type-only deep import is still a deep import: it needs tsPreCompilationDeps.
    ("entrypoint-boundary-from-outside", {
        "apps/web/probe.ts": 'import type { record } from "../../packages/billing/src/internal/ledger";\nexport type P = typeof record;\n',
    }),
    ("no-circular", {
        "packages/ui/src/probe-a.ts": 'import { b } from "./probe-b";\nexport const a = () => b;\n',
        "packages/ui/src/probe-b.ts": 'import { a } from "./probe-a";\nexport const b = () => a;\n',
    }),
    ("not-to-unresolvable", {
        "apps/web/probe.ts": 'import { gone } from "./does-not-exist";\nexport const p = gone;\n',
    }),
    ("not-to-unresolvable", {
        "apps/web/probe.ts": 'import gone from "no-such-package";\nexport const p = gone;\n',
    }),
]


def run(args, cwd):
    """Run a command in cwd and return the finished process, output as text."""
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=180)


def scratch_copy(source: Path, parent: Path) -> Path:
    """Copy an installed fixture (relative symlinks kept) into parent."""
    if not (source / "node_modules").is_dir():
        raise AssertionError(f"{source.name}/node_modules is missing: run `npm ci` in {source} first")
    return Path(shutil.copytree(source, parent / source.name, symlinks=True))


def install_guard(root: Path) -> None:
    """Place the shipped guard where the skill's step 3 puts it."""
    (root / "scripts").mkdir(exist_ok=True)
    shutil.copy(GUARD, root / "scripts" / "check-typescript-support.mjs")


def install_config(root: Path) -> None:
    """Place the shipped config with its three constants set; a reshaped constant fails loudly."""
    text = CONFIG.read_text()
    for name, value in CONSTANTS.items():
        text, count = re.subn(rf"^const {name} = .*;$", lambda _: f"const {name} = {value};", text, flags=re.M)
        if count != 1:
            raise AssertionError(f"expected one `const {name} = ...;` line in the shipped config, found {count}")
    (root / ".dependency-cruiser.cjs").write_text(text)


def depcruise(root: Path, *extra):
    """Run the check the way `lint:boundaries` does (default reporter: nonzero exit on an error)."""
    return run([str(root / "node_modules" / ".bin" / "depcruise"), *SCOPE, *extra], root)


def rules_fired(result) -> list:
    """Names of the error rules in a depcruise run, one entry per violation."""
    return ERROR_LINE.findall(result.stdout)


class ConfigTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.root = scratch_copy(FIXTURE, Path(tmp.name))
        install_config(cls.root)

    def test_clean_fixture_passes(self):
        result = depcruise(self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_clean_fixture_resolves_each_kind_of_import(self):
        """Every kind of import the fixture uses resolves, each pinning one setting of the shipped config.

        A built-in and an installed package; a workspace main entry; an exports map of plain
        strings; an exports map keyed only by "import" and one keyed only by "types" (so the
        condition list must hold both); and an extensionless import that lands on a .d.ts (so
        the extension list must hold it).
        """
        result = depcruise(self.root, "-T", "json")
        modules = {m["source"]: m for m in json.loads(result.stdout)["modules"]}
        resolved = {d["module"]: d["resolved"] for d in modules["apps/web/main.ts"]["dependencies"]}
        self.assertEqual(resolved, {
            "fs": "fs",
            "typescript": "node_modules/typescript/lib/typescript.js",
            "@fixture/billing": "packages/billing/src/index.ts",
            "@fixture/billing/testing": "packages/billing/src/testing.ts",
            "@fixture/catalog": "packages/catalog/src/index.ts",
            "@fixture/catalog/testing": "packages/catalog/src/testing.ts",
            "@fixture/ui": "packages/ui/src/index.ts",
            "../../packages/ui/src/index": "packages/ui/src/index.ts",
            "./legacy-types": "apps/web/legacy-types.d.ts",
        })

    def test_every_rule_in_the_config_has_a_probe(self):
        loaded = run(["node", "-e", "console.log(JSON.stringify(require('./.dependency-cruiser.cjs').forbidden.map(r => r.name)))"], self.root)
        self.assertEqual(loaded.returncode, 0, loaded.stderr)
        self.assertEqual(sorted(json.loads(loaded.stdout)), sorted({rule for rule, _ in PROBES}))

    def probe(self, files):
        """Write the probe files, run the check, remove the files, return the run."""
        try:
            for name, content in files.items():
                (self.root / name).write_text(content)
            return depcruise(self.root)
        finally:
            for name in files:
                (self.root / name).unlink(missing_ok=True)

    def test_each_probe_fails_naming_exactly_its_own_rule_once(self):
        for rule, files in PROBES:
            with self.subTest(rule=rule, probe=sorted(files)):
                result = self.probe(files)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(rules_fired(result), [rule], result.stdout)

    def test_deep_package_name_import_fails_by_what_the_package_exposes(self):
        """Exports resolution changes which rule names a deep package-name import (the skill's step 6 says so)."""
        cases = [
            # A package with an `exports` map: a path the map does not list cannot be resolved.
            ("@fixture/billing/src/internal/ledger", "record", "not-to-unresolvable"),
            # A package with only `main`: the deep path resolves to a file, and the boundary rule sees it.
            ("@fixture/ui/src/internal/button", "label", "entrypoint-boundary-from-outside"),
        ]
        for specifier, name, rule in cases:
            with self.subTest(specifier=specifier):
                result = self.probe({"apps/web/probe.ts": f'import {{ {name} }} from "{specifier}";\nexport const p = {name};\n'})
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertEqual(rules_fired(result), [rule], result.stdout)


class GuardTest(unittest.TestCase):
    def guard(self, source: Path):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = scratch_copy(source, Path(tmp.name))
        install_guard(root)
        return run(["node", "scripts/check-typescript-support.mjs"], root)

    def test_exits_0_with_the_pinned_typescript(self):
        result = self.guard(FIXTURE)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exits_1_with_typescript_outside_the_supported_range(self):
        result = self.guard(OUT_OF_RANGE)
        self.assertEqual(result.returncode, 1, result.stderr)
        # A broken install also exits 1; the guard's own message tells the two apart.
        self.assertIn("dependency-cruiser cannot read TypeScript", result.stderr)


if __name__ == "__main__":
    unittest.main()

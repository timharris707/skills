"""Retained proofs for the publication review's functional findings."""
import ast
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_codex_plugin as builder
import check_codex_publication as publication
import verify_codex_install as installation

PACKAGE = ROOT / 'plugins/clickai-codex'


class ReviewRegressionTests(unittest.TestCase):
    def test_historical_incident_sources_require_sanitized_replacements(self):
        denied = set((ROOT / 'editions/codex/disclosure-denylist.txt').read_text().splitlines())
        for relative in ['skills/investigate/ingest/CHANGELOG.md', 'skills/investigate/ingest/scripts/ingest.py']:
            with self.subTest(source=relative):
                self.assertTrue(publication.private_findings((ROOT / relative).read_text(), denied))
                self.assertFalse(publication.private_findings((PACKAGE / relative).read_text(), denied))
        relative = 'skills/investigate/ingest/scripts/ingest.py'
        for root, should_reject in [(ROOT, True), (PACKAGE, False)]:
            tree = ast.parse((root / relative).read_text())
            function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'wedged_spans')
            self.assertEqual(should_reject, bool(publication.private_findings(ast.get_docstring(function), denied)))

    def test_empty_and_incomplete_adaptation_hashes_fail_before_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            edition = Path(tmp) / 'edition'
            shutil.copytree(builder.EDITION, edition)
            hashes = json.loads((edition / 'upstream.json').read_text())
            incomplete = dict(hashes); incomplete.pop(next(iter(incomplete)))
            for value in [{}, incomplete]:
                (edition / 'upstream.json').write_text(json.dumps(value))
                with patch.object(builder, 'EDITION', edition), self.assertRaisesRegex(ValueError, 'every adapted source'):
                    builder.build(Path(tmp) / 'output')

    def test_empty_matching_rosters_do_not_pass_checks(self):
        manifests = [ROOT / '.codex-plugin/plugin.json', PACKAGE / '.codex-plugin/plugin.json']
        read = Path.read_text
        def empty_manifest(path, *args, **kwargs):
            text = read(path, *args, **kwargs)
            if path in manifests:
                data = json.loads(text); data['skills'] = []; return json.dumps(data)
            return text
        with patch.object(Path, 'read_text', empty_manifest):
            self.assertTrue(publication.check())
            with self.assertRaisesRegex(ValueError, 'nonempty skill roster'):
                installation.verify('unused', 1)

    def test_recipe_list_scalars_roundtrip_without_becoming_mappings(self):
        scripts = PACKAGE / 'skills/decide/advisory-board/scripts'
        code = '''from _conductor.recipe import dump_recipe, load_recipe
from _conductor.constants import price_band_usd, die
from typing import get_type_hints
get_type_hints(price_band_usd)
get_type_hints(die)
for value in ["foo:bar", "https://example.invalid/path", "a: b", "plain"]:
    recipe = {"repo_include": [value], "seats": [{"id": "codex", "model": "auto"}]}
    assert load_recipe(dump_recipe(recipe)) == recipe, value
'''
        subprocess.run([sys.executable, '-c', code], env={**os.environ, 'PYTHONPATH': str(scripts)}, check=True)

    def test_manual_board_gate_requires_distinct_seats(self):
        source = (PACKAGE / 'skills/decide/advisory-board/references/execution-harness.md').read_text()
        gate = re.search(r'ran=\$\(awk.*?\n\[.*?\n', source, re.S).group(0)
        with tempfile.TemporaryDirectory() as tmp:
            metadata = Path(tmp) / 'run-metadata.tsv'
            metadata.write_text('codex\t1\tran\n' + 'codex\t2\tran\n' + 'gemini\t1\tdropped\n')
            self.assertNotEqual(0, subprocess.run(['bash', '-c', gate], cwd=tmp, capture_output=True).returncode)
            metadata.write_text(metadata.read_text() + 'gemini\t2\tdegraded (exit 1)\n')
            self.assertEqual(0, subprocess.run(['bash', '-c', gate], cwd=tmp, capture_output=True).returncode)

    def test_wizard_preserves_existing_config_on_read_failure(self):
        source = (PACKAGE / 'skills/run/wizard/template.sh').read_text()
        function = re.search(r'^write_env\(\) \{.*?^}', source, re.M | re.S).group(0)
        with tempfile.TemporaryDirectory() as tmp:
            envfile = Path(tmp) / '.env'; envfile.write_text('PRESERVE=old\n')
            script = 'bad() { :; }; ok() { :; }; grep() { return 2; }; WROTE_ENV=();\n' + function + '\nwrite_env NEW value\n'
            result = subprocess.run(['bash', '-c', script], env={**os.environ, 'ENV_FILE': str(envfile)}, capture_output=True)
            self.assertEqual(2, result.returncode)
            self.assertEqual('PRESERVE=old\n', envfile.read_text())

    def test_release_asset_lookup_drains_producer_before_matching(self):
        workflow = (ROOT / '.github/workflows/release-core.yml').read_text()
        body = workflow.split('      - name: Build and attach the complete Codex plugin', 1)[1].split('        run: |\n', 1)[1]
        script = textwrap.dedent(body)
        stub = '''python3() { :; }
gh() {
  case "$2" in
    view) printf '%s\\n' 'clickai-codex-v1.0.0.zip'; sleep 0.05; printf '%s\\n' 'clickai-codex-v1.0.0.zip.sha256';;
    download) cp "dist/$5" "existing-assets/$5";;
    upload) echo 'unexpected upload' >&2; return 2;;
    *) return 3;;
  esac
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp) / 'dist'; dist.mkdir()
            (dist / 'clickai-codex-v1.0.0.zip').write_bytes(b'fixture archive')
            (dist / 'clickai-codex-v1.0.0.zip.sha256').write_text('fixture checksum\n')
            run = subprocess.run(['bash', '-c', stub + script], cwd=tmp, env={**os.environ, 'TAG': 'clickai-codex/v1.0.0', 'VERSION': 'v1.0.0'}, capture_output=True, text=True)
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertEqual(2, len(list((Path(tmp) / 'existing-assets').iterdir())))


if __name__ == '__main__':
    unittest.main()

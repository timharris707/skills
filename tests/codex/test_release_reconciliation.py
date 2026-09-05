"""Execute the workflow's actual scan to catch incomplete-release recovery failures."""
import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import textwrap
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class ReconciliationTests(unittest.TestCase):
    def scan(self, assets):
        workflow = (ROOT / '.github/workflows/auto-release.yml').read_text()
        scan = re.search(r"python3 - <<'PY' > work.json\n(.*?)\n          PY", workflow, re.S).group(1)
        manifests = {
            '.claude-plugin/marketplace.json': {'plugins': [{'name': 'team-workflow', 'version': '1.6.0'}]},
            'plugins/clickai-codex/.codex-plugin/plugin.json': {'name': 'clickai-codex', 'version': '1.0.0'},
        }
        def open_fixture(path, *args, **kwargs):
            if path == 'released.txt': return io.StringIO('team-workflow/v1.6.0\nclickai-codex/v1.0.0\n')
            return io.StringIO(json.dumps(manifests[path]))
        def run_fixture(argv, **kwargs):
            if argv[0] == 'git': return subprocess.CompletedProcess(argv, 0)
            self.assertEqual(['python3', 'scripts/changelog_section.py'], argv[:2])
            return subprocess.CompletedProcess(argv, 0, stdout='Release notes\n')
        output = io.StringIO()
        with patch('builtins.open', side_effect=open_fixture), patch('subprocess.run', side_effect=run_fixture), patch('subprocess.check_output', return_value=json.dumps({'assets': [{'name': a} for a in assets]})), contextlib.redirect_stdout(output):
            exec(compile(textwrap.dedent(scan), 'auto-release scan', 'exec'), {})
        return json.loads(output.getvalue())

    def test_missing_archive_or_checksum_is_reconciled(self):
        for assets in [[], ['clickai-codex-v1.0.0.zip'], ['clickai-codex-v1.0.0.zip.sha256']]:
            with self.subTest(assets=assets):
                self.assertEqual(['clickai-codex/v1.0.0'], self.scan(assets))

    def test_complete_release_and_existing_claude_release_are_skipped(self):
        self.assertEqual([], self.scan(['clickai-codex-v1.0.0.zip', 'clickai-codex-v1.0.0.zip.sha256']))


if __name__ == '__main__':
    unittest.main()

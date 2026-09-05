"""Portable checkpoint and distribution regression checks; no provider calls."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_codex_plugin import archive, build, differences
from check_codex_publication import private_findings
from check_site_disclosure import digest

spec = importlib.util.spec_from_file_location('checkpoint', ROOT / 'editions/codex/runtime/checkpoint.py')
checkpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)


class PublicationTests(unittest.TestCase):
    def test_resolver_is_read_only_and_profile_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); project = root / 'project'; project.mkdir()
            before = list(root.rglob('*'))
            first = checkpoint.resolve(project, 'task-a', root)
            self.assertEqual(before, list(root.rglob('*')))
            self.assertEqual(first, checkpoint.resolve(project, 'task-a', root))
            self.assertNotEqual(first['checkpoint'], checkpoint.resolve(project, 'task-b', root)['checkpoint'])
            self.assertNotEqual(first['checkpoint'], checkpoint.resolve(root, 'task-a', root)['checkpoint'])

    def test_checkpoint_survives_worktree_moves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); project = root / 'project'; project.mkdir()
            subprocess.run(['git', 'init', '-q', str(project)], check=True)
            subprocess.run(['git', '-C', str(project), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
            worktree = root / 'worktree'
            subprocess.run(['git', '-C', str(project), 'worktree', 'add', '-qb', 'worker', str(worktree)], check=True)
            self.assertEqual(checkpoint.resolve(project, 'task-a', root), checkpoint.resolve(worktree, 'task-a', root))

    def test_task_ids_cannot_escape_or_claim_a_shared_file(self):
        for task in ['', '..', '../other', '/other', 'a/b', 'a\\b', 'a.b', 'x' * 129]:
            with self.subTest(task=task), self.assertRaises(ValueError):
                checkpoint.resolve(ROOT, task)

    def test_private_paths_credentials_and_confidential_phrases_are_rejected(self):
        for value in ['/Users/example/private', '/home/example/private', '.codex-profiles/example', 'ghp_' + 'x' * 30, 'PRIVATE CLIENT']:
            self.assertTrue(private_findings(value, {digest('private client')}))
        self.assertFalse(private_findings('Public attribution: Tim Harris. https://clickai.dev', set()))

    def test_archive_is_reproducible_complete_and_contains_no_local_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); candidate = root / 'package'; candidate.mkdir()
            build(candidate)
            self.assertEqual([], differences(candidate, ROOT / 'plugins/clickai-codex'))
            a, b = root / 'a.zip', root / 'b.zip'
            archive(candidate, a); archive(candidate, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as z:
                self.assertEqual(23, sum(n.endswith('/SKILL.md') for n in z.namelist()))
                self.assertTrue(all(n.startswith('clickai-codex/') and '..' not in n.split('/') for n in z.namelist()))
                self.assertIn('clickai-codex/runtime/checkpoint.py', z.namelist())
                metadata = json.loads(z.read('clickai-codex/.codex-plugin/plugin.json'))
                self.assertEqual('clickai-codex', metadata['name'])
                self.assertEqual(0o755, (z.getinfo('clickai-codex/skills/run/show-me-your-work/scripts/log.sh').external_attr >> 16) & 0o777)


if __name__ == '__main__':
    unittest.main()

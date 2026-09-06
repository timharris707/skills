"""Offline protocol regression checks; no activation benchmark or provider calls.

The invocation cases are review inputs. These tests detect lost written branches,
not whether any particular model chooses a skill for a prompt.
"""
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'plugins/clickai-codex'
CASES = json.loads((Path(__file__).parent / 'fixtures/invocation-cases.json').read_text())['cases']


def missing_branches(description, case):
    return [branch['description_concept'] for branch in case['branches']
            if branch['description_concept'].casefold() not in description.casefold()]


def skill(relative):
    return (PACKAGE / 'skills' / relative / 'SKILL.md').read_text()


class SafeguardTests(unittest.TestCase):
    def test_all_catalog_descriptions_preserve_reviewed_invocation_branches(self):
        roster = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())['skills']
        self.assertEqual({str(Path(p) / 'SKILL.md') for p in roster}, {c['source'] for c in CASES})
        self.assertEqual(len(roster), len(CASES))
        for case in CASES:
            with self.subTest(skill=case['skill']):
                description = json.loads(re.search(r'^description: (.+)$',
                                         (PACKAGE / case['source']).read_text(), re.M)[1])
                self.assertEqual([], missing_branches(description, case))
                self.assertLess(description.casefold().find(case['branches'][0]['description_concept'].casefold()), 100)
                self.assertTrue(case['negative_prompt'])
                for branch in case['branches']:
                    self.assertTrue(branch['positive_prompt'])
                    self.assertNotEqual(branch['positive_prompt'], case['negative_prompt'])
                    # Prove deleting any branch from the actual description is detected.
                    shortened = description.replace(branch['description_concept'], '')
                    self.assertIn(branch['description_concept'], missing_branches(shortened, case))
                self.assertTrue(missing_branches(description[:35], case), 'Opening-only compression must lose a reviewed branch')

    def test_decision_maker_reuse_requires_explicit_sourced_nonconflicting_authority(self):
        text = skill('orient/setup')
        for safeguard in ['explicit recorded decision-maker binding', 'cite its file or decision-record source',
                          'missing, conflicting', 'evidence it changed', 'Current user instructions take precedence',
                          'never infer authority from Git authorship']:
            self.assertIn(safeguard, text)

    def test_review_completion_keeps_correction_independence_and_current_checks(self):
        text = skill('run/adversarial-review')
        done = text.split('## Done when', 1)[1].split('## Attribution', 1)[0]
        for condition in ['independent finder and skeptic', 'recorded reason', 'affected behavior is verified',
                          'substantive corrections have independent review', 'checks pass for the delivered revision',
                          'keeps review incomplete']:
            self.assertIn(condition, done)
        self.assertIn('do not rerun an unchanged diff', text)
        self.assertIn('an instruction obligation', text)

    def test_handoff_inspects_before_save_and_after_save_without_leaking_values(self):
        text = skill('run/handoff')
        before = text.index('Before saving, inspect')
        replace = text.index('Replace any such value with a safe location pointer')
        write = text.index("Overwrite only this task's checkpoint")
        reread = text.index('Re-read the saved file, inspect it again')
        self.assertLess(before, replace)
        self.assertLess(replace, write)
        self.assertLess(write, reread)
        self.assertIn('Do not echo suspected secrets', text)
        self.assertIn('pattern\nscanner may supplement inspection', text)

    def test_retained_policies_are_explicit_and_attribution_is_current(self):
        implementation = skill('run/implement')
        self.assertIn('never waives required project tests or a regression check', implementation)
        self.assertIn('Required tests accompany the delivered change', implementation)
        self.assertNotIn('relaunch-fresh', implementation)
        self.assertNotIn('tests in the same commit', implementation)
        report = skill('investigate/codebase-review')
        self.assertIn('Keep the tracker item open', report)
        voice = skill('author/writing-for-humans')
        self.assertIn('when explicitly selected', voice)
        self.assertIn('Rewrite whole sentences', voice)
        self.assertNotIn('dash budget is a softer cousin', voice)

    def test_preflight_distinguishes_untested_candidates_and_verified_launch_seats(self):
        root = PACKAGE / 'skills/decide/advisory-board'
        preflight = (root / 'references/preflight.md').read_text()
        for condition in ['**Unverified**', '**GO**', '**NO-GO**', 'Registration or installation alone never establishes GO',
                          'Unknown resolution stays unverified', 'rejected pin is NO-GO', 'approved, verified selection',
                          'failed versus unperformed checks separately']:
            self.assertIn(condition, preflight)
        for relative in ['SKILL.md', 'references/intake-interview.md']:
            text = (root / relative).read_text()
            self.assertIn('unverified', text)
            self.assertNotIn('doctor still runs', text)
        self.assertIn('a full doctor is optional', (root / 'SKILL.md').read_text())

    def test_capability_evidence_and_missing_tool_fallbacks_are_explicit(self):
        text = (ROOT / 'editions/codex/CODEX.md').read_text()
        for condition in ['Documented skills', 'Documented model identifier', 'Documented hooks', 'Desktop-observed tools',
                          'Edition workflow policy', 'https://learn.chatgpt.com/docs/build-skills',
                          'https://developers.openai.com/api/docs/models/gpt-6-astra',
                          'https://learn.chatgpt.com/docs/hooks', 'If no compatible tool is available',
                          'If delegation tools are absent', 'Never silently substitute a model']:
            self.assertIn(condition, text)

    def test_mixed_blocker_query_preserves_both_states_until_each_clears(self):
        # Execute each edition's actual jq projection against mock API responses,
        # then apply the written frontier predicate. No network or tracker writes.
        states = [(1, True, False), (0, True, False), (1, False, False), (0, False, True)]
        for base in [ROOT, PACKAGE]:
            text = (base / 'skills/orient/setup/references/tracker-discipline.md').read_text()
            self.assertIn('comes off only when all such blockers resolve', text)
            self.assertIn('closing its ticket dependency does not clear the non-ticket label', text)
            ticket_text = (base / 'skills/run/to-tickets/SKILL.md').read_text()
            self.assertNotIn('no item carries both', ticket_text)
            self.assertIn('carries both until the respective blockers clear', ticket_text)
            query_block = text.split('## Frontier recipe', 1)[1].split('```bash', 1)[1].split('```', 1)[0]
            projection = re.search(r"--jq '(.*?)'", query_block, re.S)[1]
            for count, labelled, available in states:
                with self.subTest(edition=base.name, dependency=count, non_ticket=labelled):
                    labels = [{'name': 'ready-for-agent'}] + ([{'name': 'blocked'}] if labelled else [])
                    if base == ROOT:
                        data = [{'number': 1, 'title': 'fixture', 'labels': labels, 'assignees': [],
                                 'issue_dependencies_summary': {'blocked_by': count}}]
                    else:
                        data = {'data': {'repository': {'issues': {'nodes': [
                            {'number': 1, 'title': 'fixture', 'labels': {'nodes': labels},
                             'assignees': {'nodes': []}, 'issueDependenciesSummary': {'blockedBy': count}}]}}}}
                    result = subprocess.run(['jq', '-c', projection], input=json.dumps(data), text=True,
                                            capture_output=True, check=True)
                    row = json.loads(result.stdout)
                    grabbable = ('ready-for-agent' in row['labels'] and not row['assignees']
                                 and row['blockedBy'] == 0 and 'blocked' not in row['labels'])
                    self.assertEqual(available, grabbable)

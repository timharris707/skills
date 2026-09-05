#!/usr/bin/env python3
"""Check the generated edition's identity, resources, and publication privacy."""
import hashlib
import json
from pathlib import Path
import re
import sys

from check_site_disclosure import digest, load_denylist, ngrams

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/clickai-codex'
# Catch private installation material, not public authorship or generic CLI examples.
PRIVATE_PATH = re.compile(r'/Users/[^/\s]+/|/home/[^/\s]+/|\.codex-profiles/|\.codex-shared/|\.claude-shared/')
SECRET = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_]{20,}')


def private_findings(text, denied):
    findings = []
    for line, value in enumerate(text.splitlines(), 1):
        if PRIVATE_PATH.search(value) or SECRET.search(value):
            findings.append(f'{line}: private path or credential pattern')
    for line, phrase in ngrams(text):
        if digest(phrase) in denied:
            findings.append(f'{line}: confidential phrase (value withheld)')
    return sorted(set(findings))


def check():
    failures = []
    legacy = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())['skills']
    plugin = json.loads((PACKAGE / '.codex-plugin/plugin.json').read_text())
    if plugin['skills'] != legacy:
        failures.append('Codex catalog identity differs from the original catalog')
    if not legacy or len(legacy) != len(set(legacy)):
        failures.append('Original catalog must contain a nonempty set of unique skill paths')
    promoted = {f'./skills/{b["id"]}/{p.name}'
                for b in json.loads((ROOT / 'skills/buckets.json').read_text())['buckets'] if b['promoted']
                for p in (ROOT / 'skills' / b['id']).iterdir() if (p / 'SKILL.md').is_file()}
    if set(plugin['skills']) != promoted:
        failures.append('Codex catalog must contain every promoted skill directory')
    source_meta = json.loads((ROOT / 'editions/codex/plugin.json').read_text())
    if plugin['version'] != source_meta['version'] or plugin['name'] != 'clickai-codex':
        failures.append('Codex release identity differs from its source')
    denied = load_denylist() | {line.strip() for line in (ROOT / 'editions/codex/disclosure-denylist.txt').read_text().splitlines()
                                if line.strip() and not line.startswith('#')}
    for p in sorted(set((ROOT / 'editions/codex').rglob('*')) | set(PACKAGE.rglob('*'))):
        if not p.is_file() or '__pycache__' in p.parts or p.suffix == '.pyc': continue
        rel = p.relative_to(ROOT)
        if p.is_symlink(): failures.append(f'{rel}: symlink in publication inputs')
        try: text = p.read_text()
        except UnicodeDecodeError: continue
        failures.extend(f'{rel}:{finding}' for finding in private_findings(text, denied))
    for rel in plugin['skills']:
        directory = PACKAGE / rel
        text = (directory / 'SKILL.md').read_text()
        for href in re.findall(r'\]\(([^)]+)\)', text):
            if re.match(r'https?:|#|mailto:', href): continue
            if not (directory / href.split('#')[0]).exists():
                failures.append(f'{rel}: missing resource {href}')
        if '../../../CODEX.md' not in text:
            failures.append(f'{rel}: missing desktop binding')
        if not (directory / 'agents/openai.yaml').is_file():
            failures.append(f'{rel}: missing Codex metadata')
    # No executable install mechanism may silently change user configuration.
    for name in ['AGENTS.md', 'hooks/hooks.json', 'config.toml', 'manage.py']:
        if (PACKAGE / name).exists(): failures.append(f'Unexpected global installation payload: {name}')
    receipt = json.loads((PACKAGE / 'BUILD.json').read_text())['files']
    for rel, recorded in receipt.items():
        if hashlib.sha256((PACKAGE / rel).read_bytes()).hexdigest() != recorded['sha256']:
            failures.append(f'Build receipt differs: {rel}')
    return failures


if __name__ == '__main__':
    failures = check()
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        raise SystemExit(1)
    count = len(json.loads((PACKAGE / '.codex-plugin/plugin.json').read_text())['skills'])
    print(f'Codex publication: {count} skills, resource links, metadata, receipt, and privacy checks pass')

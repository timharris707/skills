#!/usr/bin/env python3
"""Build or check the complete Codex edition from common sources and reviewed edits."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EDITION = ROOT / 'editions/codex'
DEST = ROOT / 'plugins/clickai-codex'


def files(root):
    return {p.relative_to(root).as_posix(): p for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def build(target):
    """Fail on upstream drift; copy only public, tracked resources."""
    upstream = json.loads((EDITION / 'upstream.json').read_text())
    overrides = files(EDITION / 'overrides')
    patched = set(re.findall(r'^--- a/(.+)$', (EDITION / 'skills.patch').read_text(), re.M))
    adapted = patched | overrides.keys()
    if not upstream or set(upstream) != adapted:
        raise ValueError('Upstream hashes must cover every adapted source, with no empty or missing entries')
    for relative, expected in upstream.items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Review Codex adaptation after upstream change: {relative}')
    roster = json.loads((ROOT / '.codex-plugin/plugin.json').read_text())['skills']
    prefixes = tuple(p.removeprefix('./').rstrip('/') + '/' for p in roster)
    tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', 'skills'], cwd=ROOT).decode().split('\0')
    for rel in tracked:
        if not rel.startswith(prefixes) or 'tests' in Path(rel).parts:
            continue
        source = ROOT / rel
        if source.is_symlink():
            raise ValueError(f'Package sources must be regular files: {rel}')
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    shutil.copy2(ROOT / 'skills/buckets.json', target / 'skills/buckets.json')
    # An empty temporary repository prevents git apply from discovering the caller's checkout.
    subprocess.run(['git', 'init', '-q', str(target)], check=True)
    try:
        subprocess.run(['git', 'apply', '--check', str(EDITION / 'skills.patch')], cwd=target, check=True)
        subprocess.run(['git', 'apply', str(EDITION / 'skills.patch')], cwd=target, check=True)
    finally:
        shutil.rmtree(target / '.git')
    for relative, source in overrides.items():
        if not relative.startswith('skills/') or not (target / relative).is_file():
            raise ValueError(f'Override must replace an existing skill resource: {relative}')
        shutil.copy2(source, target / relative)
    for name in ['CODEX.md', 'README.md']:
        shutil.copy2(EDITION / name, target / name)
    shutil.copy2(ROOT / 'LICENSE.md', target / 'LICENSE.md')
    shutil.copytree(EDITION / 'runtime', target / 'runtime', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (target / '.codex-plugin').mkdir()
    metadata = json.loads((EDITION / 'plugin.json').read_text())
    metadata['skills'] = roster
    (target / '.codex-plugin/plugin.json').write_text(json.dumps(metadata, indent=2) + '\n')
    receipt = {rel: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                     'executable': bool(p.stat().st_mode & 0o111)} for rel, p in sorted(files(target).items())}
    (target / 'BUILD.json').write_text(json.dumps({'format': 1, 'files': receipt}, indent=2) + '\n')


def differences(expected, actual):
    a, b = files(expected), files(actual)
    changed = sorted(a.keys() ^ b.keys())
    for rel in a.keys() & b.keys():
        if a[rel].read_bytes() != b[rel].read_bytes() or bool(a[rel].stat().st_mode & 0o111) != bool(b[rel].stat().st_mode & 0o111):
            changed.append(rel)
    return sorted(changed)


def archive(package, output):
    """Write a reproducible archive with portable permissions and no local paths."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel, p in sorted(files(package).items()):
            info = zipfile.ZipInfo(f'clickai-codex/{rel}', (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if p.stat().st_mode & 0o111 else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes())
    output.with_suffix(output.suffix + '.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest() + '  ' + output.name + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--archive', type=Path, help='also write a deterministic release ZIP and SHA-256')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='clickai-build-') as tmp:
        candidate = Path(tmp)
        build(candidate)
        if args.check:
            changed = differences(candidate, DEST)
            if changed:
                raise SystemExit('Generated package differs; run scripts/build_codex_plugin.py:\n' + '\n'.join(changed))
        else:
            if DEST.exists():
                shutil.rmtree(DEST)
            shutil.copytree(candidate, DEST)
        if args.archive:
            archive(candidate, args.archive)
        print(f'Codex package {"verified" if args.check else "built"}: {len(files(candidate))} files')


if __name__ == '__main__':
    main()

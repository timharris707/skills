#!/usr/bin/env python3
"""Resolve a task-owned checkpoint without creating or changing files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def resolve(project, task, home=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', task):
        raise ValueError('Provide the actual task ID; it must be a safe single path component')
    project = Path(project).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError('Project must be a directory')
    try:
        # All linked worktrees use the primary checkout identity, including moves.
        result = subprocess.run(['git', '-C', str(project), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            common = Path(result.stdout.strip()).resolve()
            project = common.parent if common.name == '.git' else common
    except FileNotFoundError:
        pass  # A non-Git project still has a stable canonical directory identity.
    key = hashlib.sha256(str(project).encode()).hexdigest()[:24]
    base = Path(home) if home is not None else Path.home()
    checkpoint = base / '.local/share/clickai-codex/checkpoints' / key / (task + '.md')
    return {'project': str(project), 'task': task, 'checkpoint': str(checkpoint)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--task', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(resolve(args.project, args.task), indent=2))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f'Checkpoint resolution failed: {error}\n')


if __name__ == '__main__':
    main()

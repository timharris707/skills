#!/usr/bin/env python3
"""Verify native Codex installation in temporary profiles, without model calls."""
import argparse
import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def query(env, cwd, method, params):
    process = subprocess.Popen(['codex', 'app-server', '--listen', 'stdio://'], cwd=cwd, env=env,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    pending = b''

    def send(value):
        process.stdin.write((json.dumps(value) + '\n').encode())
        process.stdin.flush()

    def receive(request):
        nonlocal pending
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                message = json.loads(line)
                if message.get('id') == request:
                    if 'error' in message:
                        raise RuntimeError(f'{method} failed with code {message["error"].get("code")}')
                    return message['result']
            if selector.select(max(0, deadline - time.monotonic())):
                data = os.read(process.stdout.fileno(), 65536)
                if not data: raise RuntimeError('Codex app-server exited during discovery')
                pending += data
        raise TimeoutError(f'Timed out reading {method}')

    try:
        send({'id': 0, 'method': 'initialize', 'params': {'clientInfo': {
            'name': 'clickai_install_check', 'title': 'Click AI installation verification', 'version': '1.0'},
            'capabilities': {'experimentalApi': True}}})
        receive(0)
        send({'method': 'initialized', 'params': {}})
        send({'id': 1, 'method': method, 'params': params})
        return receive(1)
    finally:
        selector.close()
        process.stdin.close()
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
        process.stdout.close()


def verify(marketplace, profiles):
    expected = {'clickai-codex:' + Path(p).name for p in json.loads((ROOT / '.codex-plugin/plugin.json').read_text())['skills']}
    with tempfile.TemporaryDirectory(prefix='clickai-install-') as tmp:
        home = Path(tmp); project = home / 'project'; project.mkdir()
        (project / 'AGENTS.md').write_text('Fixture project rules remain unchanged.\n')
        results = []
        for n in range(profiles):
            profile = home / f'profile-{n + 1}'; profile.mkdir()
            config = profile / 'config.toml'
            config.write_text('model = "fixture-selected-model"\nmodel_reasoning_effort = "high"\n')
            master = profile / 'AGENTS.md'; master.write_text('Fixture global rules remain unchanged.\n')
            env = {**os.environ, 'HOME': str(home), 'CODEX_HOME': str(profile)}
            for command in [['codex', 'plugin', 'marketplace', 'add', marketplace],
                            ['codex', 'plugin', 'add', 'clickai-codex@clickai']]:
                run = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, timeout=60)
                if run.returncode:
                    raise RuntimeError(f'Native installation failed: {run.stderr}')
            result = query(env, project, 'skills/list', {'cwds': [str(project)], 'forceReload': True})['data'][0]
            selected = [s for s in result['skills'] if '/clickai-codex/' in s['path'] and s['enabled']]
            names = {s['name'] for s in selected}
            if names != expected or len(selected) != len(expected):
                raise ValueError(f'Native discovery differs: expected {len(expected)}, found {len(selected)}; names {sorted(names)}')
            if any('clickai-codex' in e['path'] for e in result['errors']):
                raise ValueError('Codex reported plugin parser errors')
            if 'model = "fixture-selected-model"' not in config.read_text() or 'model_reasoning_effort = "high"' not in config.read_text():
                raise ValueError('Installation changed selected model/effort')
            if master.read_text() != 'Fixture global rules remain unchanged.\n':
                raise ValueError('Installation changed global rules')
            if (project / 'AGENTS.md').read_text() != 'Fixture project rules remain unchanged.\n':
                raise ValueError('Installation changed project rules')
            if (home / '.claude').exists() or (profile / 'hooks.json').exists():
                raise ValueError('Unexpected Claude configuration or global hook writes')
            results.append({'profile': n + 1, 'enabled_skills': len(selected), 'parser_errors': 0, 'settings_preserved': True})
        return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--marketplace', default=str(ROOT))
    parser.add_argument('--profiles', type=int, default=3)
    args = parser.parse_args()
    if args.profiles < 1: parser.error('--profiles must be positive')
    print(json.dumps({'profiles': verify(args.marketplace, args.profiles), 'model_calls': 0}, indent=2))

#!/usr/bin/env python3
"""Tripwire for the Markdown twins (PR #216 close-out).

Every promoted skill's `/skills/<name>.md` route must serve the SKILL.md an
agent would install. This fetches each twin from a running site build and
asserts, so a serving regression fails CI instead of shipping silently:

  1. The body — everything between the frontmatter and the #213 install
     trailer — is byte-identical to the source SKILL.md body (the route
     strips leading whitespace, so the comparison allows only that).
  2. The regenerated frontmatter carries the source's name and description
     verbatim, modulo the unquoting the site's parser applies and the
     JSON-style requoting the route emits to keep the twin strict YAML. That
     regeneration and the appended install trailer are the only sanctioned
     differences.

Standard library only. Expects `next start` to be listening; retries until
the server is up. Usage:

  python3 scripts/check_skill_md_twins.py [--base http://localhost:3000]
                                          [--slug adversarial-review]
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAILER = "\n\n---\n\nShips in: "


def fetch(url: str, timeout: float = 15.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def fetch_when_up(url: str, deadline: float = 60.0) -> bytes:
    """Retry until the dev/prod server answers — it starts in parallel."""
    start = time.monotonic()
    while True:
        try:
            return fetch(url)
        except (urllib.error.URLError, ConnectionError, OSError) as error:
            if time.monotonic() - start > deadline:
                raise SystemExit(f"server never answered at {url}: {error}")
            time.sleep(1)


def promoted_skill_files() -> list[tuple[str, Path]]:
    """(slug, SKILL.md path) for every skill the site publishes."""
    buckets = json.loads((REPO_ROOT / "skills" / "buckets.json").read_text())["buckets"]
    out = []
    for bucket in buckets:
        if not bucket["promoted"]:
            continue
        bucket_dir = REPO_ROOT / "skills" / bucket["id"]
        if not bucket_dir.is_dir():
            continue
        for skill_file in sorted(bucket_dir.glob("*/SKILL.md")):
            out.append((skill_file.parent.name, skill_file))
    if not out:
        raise SystemExit("no promoted skills discovered — a green run would check nothing")
    return out


def split_source(raw: str) -> tuple[dict[str, str], str]:
    """Frontmatter fields and body of a source SKILL.md.

    The value transform (strip, then unquote) mirrors the site's parser —
    that transform is the sanctioned frontmatter difference being allowed,
    so it is replicated rather than trusted.
    """
    lines = raw.split("\n")
    if lines[0] != "---":
        raise SystemExit(f"source has no frontmatter: {raw[:40]!r}")
    close = lines.index("---", 1)
    fields = {}
    for line in lines[1:close]:
        match = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if not match:
            continue
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = re.sub(r'\\(["\\])', r"\1", value[1:-1])
        elif len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1]
        fields[match.group(1)] = value
    body = "\n".join(lines[close + 1 :])
    return fields, body


def check_twin(slug: str, skill_file: Path, base: str) -> list[str]:
    fields, source_body = split_source(skill_file.read_text(encoding="utf-8"))
    served = fetch_when_up(f"{base}/skills/{slug}.md").decode("utf-8")

    head, sep, rest = served.partition("\n---\n\n")
    if not sep:
        return [f"{slug}: served twin has no frontmatter block"]

    failures = []
    # The route emits the description JSON-quoted so the twin's frontmatter
    # stays strict YAML; json.dumps mirrors JSON.stringify for these strings.
    expected_head = [
        "---",
        f"name: {fields.get('name', '')}",
        f"description: {json.dumps(fields.get('description', ''), ensure_ascii=False)}",
    ]
    if head.split("\n") != expected_head:
        failures.append(f"{slug}: regenerated frontmatter does not match the source's name/description")

    cut = rest.rfind(TRAILER)
    if cut == -1:
        return failures + [f"{slug}: served twin has no install trailer (#213)"]
    served_body = rest[:cut]

    # The route serves body.trimStart(); beyond that, byte-identical.
    if served_body != source_body.lstrip():
        want, got = source_body.lstrip(), served_body
        at = next((i for i, (a, b) in enumerate(zip(want, got)) if a != b), min(len(want), len(got)))
        line = want.count("\n", 0, at) + 1
        failures.append(
            f"{slug}: served body diverges from {skill_file.relative_to(REPO_ROOT)} "
            f"around body line {line} (want {want[at:at + 40]!r}, got {got[at:at + 40]!r})"
        )
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:3000")
    parser.add_argument("--slug", help="check a single skill instead of all promoted ones")
    args = parser.parse_args()

    skills = promoted_skill_files()
    if args.slug:
        skills = [s for s in skills if s[0] == args.slug]
        if not skills:
            raise SystemExit(f"no promoted skill named {args.slug!r}")

    failures = []
    for slug, skill_file in skills:
        failures.extend(check_twin(slug, skill_file, args.base))

    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)
    print(f"markdown twins byte-identical for all {len(skills)} promoted skills")


if __name__ == "__main__":
    main()

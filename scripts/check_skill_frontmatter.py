#!/usr/bin/env python3
"""Fail the build when any tracked SKILL.md frontmatter is not strict YAML.

GitHub, gray-matter-based harnesses, and anything else standards-shaped parse
the leading `---` block with a real YAML parser. An unquoted `: ` inside a
description reads as a nested mapping and the whole block fails to parse:
GitHub shows an error banner instead of the frontmatter table, and a strict
loader drops or rejects the skill. Sixteen catalog descriptions shipped that
way before this check existed.

For every SKILL.md git tracks, this requires that:
  - a `---` frontmatter block opens the file,
  - the block parses under yaml.safe_load (PyYAML mirrors the strict parsers
    that matter; the CI step installs it, which is a no-op on GitHub runners),
  - it parses to a mapping with non-empty string `name` and `description`.

Each violation prints one line; any violation exits non-zero. An empty file
list fails too — an empty check is not a green check.
"""

import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("check_skill_frontmatter: PyYAML is required (pip install PyYAML)",
          file=sys.stderr)
    sys.exit(1)


def main() -> None:
    files = subprocess.run(
        ["git", "ls-files", "*SKILL.md"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    if not files:
        print("ERROR: no tracked SKILL.md files found — an empty check is "
              "not a green check")
        sys.exit(1)

    errors = []
    for path in files:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.S)
        if not match:
            errors.append(f"{path}: no leading --- frontmatter block")
            continue
        try:
            data = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            first = str(exc).replace("\n", " ").strip()
            errors.append(f"{path}: frontmatter is not strict YAML ({first})")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path}: frontmatter parses to {type(data).__name__}, "
                          "not a mapping")
            continue
        for key in ("name", "description"):
            value = data.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{path}: frontmatter lacks a non-empty string "
                              f"'{key}'")

    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"\n{len(errors)} frontmatter problem(s). Quote descriptions "
              "that contain ': ' (JSON-style double quotes are valid YAML).")
        sys.exit(1)
    print(f"OK: {len(files)} SKILL.md frontmatter blocks parse as strict YAML")


if __name__ == "__main__":
    main()

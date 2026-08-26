#!/usr/bin/env python3
"""Fail the build when any tracked SKILL.md frontmatter is not strict YAML.

GitHub, gray-matter-based harnesses, and anything else standards-shaped parse
the leading `---` block with a real YAML parser. An unquoted `: ` inside a
description reads as a nested mapping and the whole block fails to parse:
GitHub shows an error banner instead of the frontmatter table, and a strict
loader drops or rejects the skill. Sixteen catalog descriptions shipped that
way before this check existed.

Standard library only, so no YAML engine: instead this enforces a flat
`key: value` subset that every strict YAML parser agrees on. A value must be
one of:

  - a JSON string (double-quoted, validated with json.loads — JSON strings
    are a subset of YAML double-quoted scalars),
  - a single-quoted YAML scalar ('' is the only escape),
  - a plain scalar with no `: `, no trailing `:`, no ` #`, and no leading
    YAML indicator character.

Anything outside the subset fails, including nested or multi-line
frontmatter: keep SKILL.md frontmatter flat, and quote descriptions that
contain `: ` (JSON-style double quotes). On top of the form, `name` must be
a slug and `description` a non-empty string. Each violation prints one line;
any violation exits non-zero. An empty file list fails too — an empty check
is not a green check.
"""

import json
import re
import subprocess
import sys

KEY_LINE = re.compile(r"^([A-Za-z][\w-]*):(?: (.*))?$")
JSON_STRING = re.compile(r'^"(?:[^"\\]|\\.)*"$')
SINGLE_QUOTED = re.compile(r"^'(?:[^']|'')*'$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
# Leading characters YAML reserves or that start non-scalar nodes.
PLAIN_UNSAFE_LEAD = set("#&*!|>%@`\"'{}[],?:- ")


def value_error(value: str) -> str | None:
    """Why this value falls outside the strict-YAML-safe subset, or None."""
    if JSON_STRING.match(value):
        try:
            json.loads(value)
            return None
        except ValueError:
            return "double-quoted value is not a valid JSON string"
    if value.startswith('"'):
        return "unterminated or malformed double-quoted value"
    if SINGLE_QUOTED.match(value):
        return None
    if value.startswith("'"):
        return "unterminated single-quoted value ('' is the only escape)"
    if ": " in value or value.endswith(":"):
        return "unquoted ': ' reads as a nested mapping — quote the value"
    if " #" in value:
        return "unquoted ' #' starts a YAML comment — quote the value"
    if value and value[0] in PLAIN_UNSAFE_LEAD:
        return f"leading {value[0]!r} is not safe in a plain scalar — quote the value"
    return None


def decoded(value: str):
    """The value a YAML parser would produce for a subset-valid token."""
    if value.startswith('"'):
        return json.loads(value)
    if value.startswith("'"):
        return value[1:-1].replace("''", "'")
    lowered = value.lower()
    if lowered in ("", "~", "null"):
        return None
    if lowered in ("true", "false"):
        return lowered == "true"
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", value):
        return float(value) if "." in value else int(value)
    return value


def check_file(path: str) -> list:
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.S)
    if not match:
        return [f"{path}: no leading --- frontmatter block"]

    errors = []
    fields = {}
    for line in match.group(1).split("\n"):
        if not line.strip():
            continue
        key_match = KEY_LINE.match(line)
        if not key_match:
            errors.append(f"{path}: line {line!r} is not flat 'key: value' — "
                          "keep SKILL.md frontmatter flat")
            continue
        key, value = key_match.group(1), (key_match.group(2) or "").strip()
        if key in fields:
            errors.append(f"{path}: duplicate frontmatter key '{key}'")
            continue
        problem = value_error(value)
        if problem:
            errors.append(f"{path}: '{key}': {problem}")
            continue
        fields[key] = decoded(value)

    name = fields.get("name")
    if not isinstance(name, str) or not SLUG.match(name):
        errors.append(f"{path}: frontmatter 'name' {name!r} is not a slug")
    description = fields.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append(f"{path}: frontmatter lacks a non-empty string "
                      "'description'")
    return errors


def main() -> None:
    files = subprocess.run(
        ["git", "ls-files", "*SKILL.md"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    if not files:
        print("ERROR: no tracked SKILL.md files found — an empty check is "
              "not a green check")
        sys.exit(1)

    errors = [error for path in files for error in check_file(path)]
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"\n{len(errors)} frontmatter problem(s). Quote descriptions "
              "that contain ': ' (JSON-style double quotes are valid YAML).")
        sys.exit(1)
    print(f"OK: {len(files)} SKILL.md frontmatter blocks are strict-YAML safe")


if __name__ == "__main__":
    main()

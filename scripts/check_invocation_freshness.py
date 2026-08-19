#!/usr/bin/env python3
"""Invocation classification check (CI).

`site/src/lib/catalog.ts` carries a hand-maintained INVOCATION map — for every
promoted skill, who triggers it (`invokedBy`) and the slash command for the
user path (`command`). The skills' frontmatter is the source of truth, so this
check derives the expected values from each SKILL.md and fails when the map
disagrees — the same posture as `check_router_freshness.py`: site and skills
can never drift apart.

Derivation, per promoted skill:

  1. `disable-model-invocation: true` in its frontmatter → `invokedBy: "user"`,
     `command: "/<plugin>:<slug>"` (the plugin that claims it in
     `.claude-plugin/marketplace.json`).
  2. No flag, but some user-invoked promoted skill's SKILL.md links to this
     skill's SKILL.md (the thin-alias pattern: a user-invoked invoker pointing
     at an agent-invoked reference skill) → `invokedBy: "either"`, `command`
     is the alias's slash command.
  3. Otherwise → `invokedBy: "agent"`, `command: null`.

The map must list exactly the promoted skills — a missing or phantom entry is
an error, as is any value disagreement. The checker parses the INVOCATION
block line by line, so each entry stays on one line (catalog.ts says so too).

README.md's catalog (one table per bucket section) carries the same
classification as its Invocation column, one tag per state: "you call it" (user), "fires itself" (agent),
"both" (either), with the slash command in backticks when one exists. This
check derives each row's expected cell from the same frontmatter derivation
and fails on any disagreement, a row for a skill that is not promoted, or a
row missing the cell, so the README marking cannot silently drift either.
The table must also be complete: every promoted skill has a row, so a
promotion cannot skip the README and pass CI silently (#248).

Standard library only. Exit 0 = in agreement; exit 1 = drift, one line per
problem.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
BUCKETS = SKILLS_DIR / "buckets.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CATALOG = ROOT / "site" / "src" / "lib" / "catalog.ts"
README = ROOT / "README.md"

ENTRY_RE = re.compile(
    r'^\s*(?:"(?P<qslug>[\w-]+)"|(?P<slug>[\w-]+)):\s*'
    r'\{\s*invokedBy:\s*"(?P<invoked>user|agent|either)",\s*'
    r'command:\s*(?:null|"(?P<command>[^"]*)")\s*\},?\s*$'
)

errors = []


def frontmatter(skill_md: Path) -> dict:
    """The flat `key: value` pairs of the leading `---` block."""
    lines = skill_md.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    if not any(line.strip() == "---" for line in lines[1:]):
        return {}  # unclosed frontmatter: treat as none rather than swallow the body
    data = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if match:
            data[match.group(1)] = match.group(2).strip().strip("\"'")
    return data


def promoted_skills() -> dict:
    """slug -> skill directory, for every skill in a promoted bucket."""
    buckets = json.loads(BUCKETS.read_text())["buckets"]
    out = {}
    for bucket in buckets:
        if not bucket["promoted"]:
            continue
        bucket_dir = SKILLS_DIR / bucket["id"]
        if not bucket_dir.is_dir():
            print(f"ERROR: promoted bucket '{bucket['id']}' has no skills/{bucket['id']} "
                  "directory; a skipped bucket is not a green check")
            sys.exit(1)
        for entry in sorted(bucket_dir.iterdir()):
            if entry.is_dir() and (entry / "SKILL.md").is_file():
                out[entry.name] = entry
    if not out:
        print("ERROR: no promoted skills found — an empty check is not a green check")
        sys.exit(1)
    return out


def plugin_owners() -> dict:
    """slug -> claiming plugin name, from the Claude marketplace."""
    marketplace = json.loads(MARKETPLACE.read_text())
    owners = {}
    for plugin in marketplace.get("plugins", []):
        for raw in plugin.get("skills", []):
            rel = (raw[2:] if raw.startswith("./") else raw).rstrip("/")
            owners[rel.rsplit("/", 1)[-1]] = plugin.get("name", "<unnamed>")
    return owners


def derive_expected(skills: dict, owners: dict) -> dict:
    """slug -> (invokedBy, command), from frontmatter plus the alias pattern."""
    user_invoked = {}
    for slug, skill_dir in skills.items():
        data = frontmatter(skill_dir / "SKILL.md")
        if data.get("disable-model-invocation", "").lower() == "true":
            user_invoked[slug] = f"/{owners.get(slug, '?')}:{slug}"

    # The alias pattern: a user-invoked skill whose SKILL.md links to another
    # promoted skill's SKILL.md marks that reference skill "either" — invocable
    # by the agent directly and by the user through the alias's command.
    aliased = {}  # reference slug -> alias command
    for slug, command in user_invoked.items():
        body = (skills[slug] / "SKILL.md").read_text()
        for link in re.findall(r"\]\((\.\.?/[^)#\s]+SKILL\.md)(?:#[^)\s]*)?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\)", body):
            target = ((skills[slug] / link).resolve())
            for ref_slug, ref_dir in skills.items():
                if ref_slug != slug and target == (ref_dir / "SKILL.md").resolve():
                    aliased[ref_slug] = command

    expected = {}
    for slug in skills:
        if slug in user_invoked:
            expected[slug] = ("user", user_invoked[slug])
        elif slug in aliased:
            expected[slug] = ("either", aliased[slug])
        else:
            expected[slug] = ("agent", None)
    return expected


def parse_catalog() -> dict:
    """slug -> (invokedBy, command) as written in catalog.ts's INVOCATION map."""
    text = CATALOG.read_text()
    match = re.search(r"export const INVOCATION[^{]*\{(.*?)\n\};", text, re.DOTALL)
    if match is None:
        errors.append("site/src/lib/catalog.ts has no INVOCATION map")
        return {}
    found = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.strip().startswith(("//", "/*", "*")):
            continue
        entry = ENTRY_RE.match(line)
        if entry is None:
            errors.append(f"catalog.ts INVOCATION line not parseable: {line.strip()}")
            continue
        slug = entry.group("qslug") or entry.group("slug")
        found[slug] = (entry.group("invoked"), entry.group("command"))
    return found


def readme_mark(invoked_by: str, command) -> str:
    """The exact Invocation cell the README's catalog table must carry.

    Same three tags the site renders (invocationLabel in catalog.ts), plus the
    slash command in backticks when the state has one.
    """
    label = {"user": "you call it", "agent": "fires itself", "either": "both"}[invoked_by]
    return f"{label} (`{command}`)" if command else label


# A catalog-table row: a linked slug, then the remaining cells.
README_ROW_RE = re.compile(r"^\|\s*\[(?P<slug>[\w-]+)\]\([^)]*\)\s*\|(?P<rest>.*)\|\s*$")
README_HEADER_RE = re.compile(r"^\|\s*Skill\s*\|.*\|\s*Invocation\s*\|\s*$")


def check_readme(expected: dict):
    """Every skill row in README.md's catalog table carries the derived mark."""
    lines = README.read_text().splitlines()
    # Scope validation to the catalog tables themselves: each contiguous
    # pipe-row block that follows an Invocation header (the catalog is one
    # table per bucket section). Linked rows in unrelated tables must not
    # count toward `rows`, or a gutted catalog could pass.
    table = []
    headers = 0
    i = 0
    while i < len(lines):
        if README_HEADER_RE.match(lines[i]):
            headers += 1
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                table.append((i + 1, lines[i]))
                i += 1
        else:
            i += 1
    if headers == 0:
        errors.append("README.md catalog table has no 'Invocation' column header")

    rows = 0
    listed = set()
    for lineno, line in table:
        row = README_ROW_RE.match(line)
        if row is None:
            continue
        rows += 1
        slug = row.group("slug")
        listed.add(slug)
        if slug not in expected:
            errors.append(
                f"README.md:{lineno}: '{slug}' is in the catalog table but is not a promoted skill"
            )
            continue
        want = readme_mark(*expected[slug])
        cells = [c.strip() for c in row.group("rest").split("|")]
        # Cells after the link: what it's for, ships as, invocation.
        if len(cells) < 3 or not cells[2]:
            errors.append(f"README.md:{lineno}: '{slug}' row has no Invocation cell; expected '{want}'")
        elif cells[2] != want:
            errors.append(
                f"README.md:{lineno}: '{slug}' is marked '{cells[2]}', "
                f"but frontmatter derives '{want}'"
            )
    if rows == 0:
        errors.append("README.md has no catalog-table skill rows; an empty check is not a green check")
    for slug in sorted(set(expected) - listed):
        errors.append(
            f"'{slug}' is promoted but has no row in README.md's catalog table; "
            f"add one with the Invocation cell '{readme_mark(*expected[slug])}'"
        )


def main():
    skills = promoted_skills()
    expected = derive_expected(skills, plugin_owners())
    actual = parse_catalog()
    check_readme(expected)

    for slug in sorted(set(expected) - set(actual)):
        errors.append(
            f"'{slug}' is promoted but has no INVOCATION entry in catalog.ts — "
            f"expected invokedBy '{expected[slug][0]}'"
        )
    for slug in sorted(set(actual) - set(expected)):
        errors.append(
            f"'{slug}' is in catalog.ts INVOCATION but is not a promoted skill — remove it"
        )
    for slug in sorted(set(expected) & set(actual)):
        if expected[slug] != actual[slug]:
            exp_by, exp_cmd = expected[slug]
            act_by, act_cmd = actual[slug]
            errors.append(
                f"'{slug}': catalog.ts says invokedBy '{act_by}' command {act_cmd!r}, "
                f"but frontmatter derives invokedBy '{exp_by}' command {exp_cmd!r}"
            )

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"invocation freshness: {len(errors)} problem(s)")
        return 1

    counts = {}
    for invoked_by, _ in expected.values():
        counts[invoked_by] = counts.get(invoked_by, 0) + 1
    summary = ", ".join(f"{k}:{n}" for k, n in sorted(counts.items()))
    print(f"invocation freshness: OK ({len(expected)} skills — {summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

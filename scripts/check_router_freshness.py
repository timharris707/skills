#!/usr/bin/env python3
"""Router / catalog freshness check (CI).

Routers rot exactly when skills are added or renamed, so CI enforces the
structural invariants instead of convention:

  1. `.claude-plugin/marketplace.json` is valid JSON, and every skill path a
     plugin claims resolves to a directory containing `SKILL.md`.
  2. Every directory under `skills/` is accounted for: it is claimed by exactly
     one marketplace plugin, or it is the pack's changelog home
     (`skills/team-workflow/`, which deliberately carries no SKILL.md — the
     release workflow derives that path from the pack tag).
  3. Every skill in the team-workflow plugin appears in the router's roster
     (`skills/router/SKILL.md`), except the router itself.
  4. Every relative `.md` link in the router resolves to an existing file.

Standard library only. Exit 0 = fresh; exit 1 = stale, with one line per problem.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
ROUTER = SKILLS_DIR / "router" / "SKILL.md"
PACK_PLUGIN = "team-workflow"
# Non-skill directories under skills/ that are allowed to exist.
NON_SKILL_DIRS = {"team-workflow"}  # pack changelog home (skills/<tag-prefix>/CHANGELOG.md)

errors = []


def claim_paths(plugin):
    """A plugin's claimed skill dirs as skills/<name> strings."""
    out = []
    for raw in plugin.get("skills", []):
        rel = raw[2:] if raw.startswith("./") else raw
        out.append(rel.rstrip("/"))
    return out


def main():
    # 1. Marketplace parses; claimed paths resolve.
    try:
        marketplace = json.loads(MARKETPLACE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {MARKETPLACE.relative_to(ROOT)}: {exc}")
        return 1

    claimed = {}  # skills/<name> -> [plugin names]
    for plugin in marketplace.get("plugins", []):
        for rel in claim_paths(plugin):
            claimed.setdefault(rel, []).append(plugin.get("name", "<unnamed>"))
            path = ROOT / rel
            if not (path / "SKILL.md").is_file():
                errors.append(
                    f"marketplace plugin '{plugin.get('name')}' claims '{rel}' "
                    "but there is no SKILL.md there"
                )

    for rel, owners in claimed.items():
        if len(owners) > 1:
            errors.append(f"'{rel}' is claimed by more than one plugin: {', '.join(owners)}")

    # 2. Every skills/ directory is accounted for.
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        rel = f"skills/{entry.name}"
        has_skill_md = (entry / "SKILL.md").is_file()
        if entry.name in NON_SKILL_DIRS:
            if has_skill_md:
                errors.append(f"'{rel}' is the pack changelog home but now carries a SKILL.md")
            continue
        if not has_skill_md:
            errors.append(f"'{rel}' has no SKILL.md and is not a known non-skill directory")
            continue
        if rel not in claimed:
            errors.append(f"'{rel}' is not claimed by any plugin in marketplace.json")

    # 3 + 4. Router roster covers the pack; router links resolve.
    try:
        router_text = ROUTER.read_text()
    except OSError as exc:
        print(f"ERROR: cannot read {ROUTER.relative_to(ROOT)}: {exc}")
        return 1

    pack = next(
        (p for p in marketplace.get("plugins", []) if p.get("name") == PACK_PLUGIN), None
    )
    if pack is None:
        errors.append(f"marketplace.json has no '{PACK_PLUGIN}' plugin entry")
    else:
        for rel in claim_paths(pack):
            name = rel.rsplit("/", 1)[-1]
            if name == "router":
                continue
            if f"../{name}/" not in router_text:
                errors.append(f"pack skill '{name}' does not appear in the router roster")

    for link in re.findall(r"\]\((\.\.?/[^)#]+\.md)\)", router_text):
        if not (ROUTER.parent / link).resolve().is_file():
            errors.append(f"router links to '{link}' which does not exist")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"router freshness: {len(errors)} problem(s)")
        return 1
    print("router freshness: OK (marketplace, skills/ catalog, and router roster agree)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

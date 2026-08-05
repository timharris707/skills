#!/usr/bin/env python3
"""Catalog freshness check (CI).

The catalog rots exactly when skills are added, renamed, or moved between
buckets, so CI enforces the structural invariants instead of trusting
convention.

**Buckets.** A directory under `skills/` IS a bucket, declared in
`skills/buckets.json`. Everything inside a bucket is a skill. A bucket is either
*promoted* (it ships and appears on the site) or not — which is what makes
`in-progress/` useful: moving a half-built skill there removes it from the
marketplace and the site in one `git mv`, without deleting it.

Invariants:

  1. `skills/buckets.json` is valid, every directory under `skills/` is a
     declared bucket, and every declared bucket exists.
  2. `.claude-plugin/marketplace.json` is valid JSON, and every skill path a
     plugin claims resolves to a directory containing `SKILL.md`.
  3. Promotion holds both ways: every skill in a *promoted* bucket is claimed by
     exactly one plugin, and no skill in an *unpromoted* bucket is claimed by
     any.
  4. Every skill in the team-workflow plugin appears in the router's roster
     (`skills/orient/router/SKILL.md`), except the router itself.
  5. Every relative `.md` link in the router resolves to an existing file.

Standard library only. Exit 0 = fresh; exit 1 = stale, with one line per problem.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
BUCKETS = SKILLS_DIR / "buckets.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
ROUTER = SKILLS_DIR / "orient" / "router" / "SKILL.md"
PACK_PLUGIN = "team-workflow"

errors = []


def claim_paths(plugin):
    """A plugin's claimed skill dirs as `skills/<bucket>/<name>` strings."""
    out = []
    for raw in plugin.get("skills", []):
        rel = raw[2:] if raw.startswith("./") else raw
        out.append(rel.rstrip("/"))
    return out


def main():
    # 1. Buckets declare the shape of skills/.
    try:
        declared = json.loads(BUCKETS.read_text())["buckets"]
        promoted = {b["id"]: b["promoted"] for b in declared}
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {BUCKETS.relative_to(ROOT)}: {exc}")
        return 1

    on_disk = {e.name for e in SKILLS_DIR.iterdir() if e.is_dir()}
    for undeclared in sorted(on_disk - set(promoted)):
        errors.append(
            f"'skills/{undeclared}' is not a declared bucket — add it to skills/buckets.json, "
            "or move it inside an existing bucket"
        )
    for missing in sorted(set(promoted) - on_disk):
        errors.append(
            f"bucket '{missing}' is declared in buckets.json but skills/{missing}/ does not exist"
        )

    # Every skill on disk, with the bucket it sits in.
    skills = {}  # skills/<bucket>/<name> -> bucket id
    for bucket in sorted(on_disk & set(promoted)):
        for entry in sorted((SKILLS_DIR / bucket).iterdir()):
            if not entry.is_dir():
                continue
            rel = f"skills/{bucket}/{entry.name}"
            if not (entry / "SKILL.md").is_file():
                errors.append(f"'{rel}' sits in a bucket but has no SKILL.md")
                continue
            skills[rel] = bucket

    # 2. Marketplace parses; claimed paths resolve.
    try:
        marketplace = json.loads(MARKETPLACE.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read {MARKETPLACE.relative_to(ROOT)}: {exc}")
        return 1

    claimed = {}  # skills/<bucket>/<name> -> [plugin names]
    for plugin in marketplace.get("plugins", []):
        for rel in claim_paths(plugin):
            claimed.setdefault(rel, []).append(plugin.get("name", "<unnamed>"))
            if not (ROOT / rel / "SKILL.md").is_file():
                errors.append(
                    f"marketplace plugin '{plugin.get('name')}' claims '{rel}' "
                    "but there is no SKILL.md there"
                )

    for rel, owners in claimed.items():
        if len(owners) > 1:
            errors.append(f"'{rel}' is claimed by more than one plugin: {', '.join(owners)}")

    # 3. Promotion holds in both directions.
    for rel, bucket in sorted(skills.items()):
        if promoted[bucket] and rel not in claimed:
            errors.append(
                f"'{rel}' is in promoted bucket '{bucket}' but no plugin claims it — "
                "claim it in marketplace.json, or move it to an unpromoted bucket"
            )
        if not promoted[bucket] and rel in claimed:
            errors.append(
                f"'{rel}' is in unpromoted bucket '{bucket}' but plugin "
                f"'{claimed[rel][0]}' claims it — unpromoted skills must not ship"
            )

    # 4 + 5. Router roster covers the pack; router links resolve.
    try:
        router_text = ROUTER.read_text()
    except OSError as exc:
        print(f"ERROR: cannot read {ROUTER.relative_to(ROOT)}: {exc}")
        return 1

    pack = next((p for p in marketplace.get("plugins", []) if p.get("name") == PACK_PLUGIN), None)
    if pack is None:
        errors.append(f"marketplace.json has no '{PACK_PLUGIN}' plugin entry")
    else:
        for rel in claim_paths(pack):
            name = rel.rsplit("/", 1)[-1]
            if name == "router":
                continue
            # Same-bucket skills are linked ../<name>/; cross-bucket ../../<bucket>/<name>/.
            # Matching on /<name>/ covers both without hard-coding the bucket.
            if f"/{name}/" not in router_text:
                errors.append(f"pack skill '{name}' does not appear in the router roster")

    for link in re.findall(r"\]\((\.\.?/[^)#]+\.md)\)", router_text):
        if not (ROUTER.parent / link).resolve().is_file():
            errors.append(f"router links to '{link}' which does not exist")

    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        print(f"catalog freshness: {len(errors)} problem(s)")
        return 1

    counts = {}
    for bucket in skills.values():
        counts[bucket] = counts.get(bucket, 0) + 1
    summary = ", ".join(f"{b}:{n}" for b, n in sorted(counts.items()))
    print(f"catalog freshness: OK ({len(skills)} skills — {summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

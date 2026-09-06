#!/usr/bin/env python3
"""Positioning tripwire (CI), from decision 0005.

Decision 0005 (docs/agents/memory/decisions/0005-skills-for-real-non-engineers.md)
retired several lines from every public surface and recorded that no existing
check would catch them coming back: the adversarial review of that change found
one skill still mandating the retired hook verbatim, with all seven verify
commands green. This fails the build when any retired phrase reappears in the
surfaces a reader or an evaluating agent sees: README.md, the site source, the
skills, the packs, and the plugin manifests.

Exempt on purpose: the decision record itself (it names what it bans), the
changelogs (history), tests, tmp/, and the phrase "vibe coding" inside the
legend, where it is a defined term about someone else's framing. Standard
library only. Exit 0 = clean; exit 1 = one line per hit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RETIRED = [
    "I direct agents",
    "directing AI agents",
    "directing AI coding agents",
    "method that let a non-coder",
    "can't read the code",
    "vibe coding",
]

ROOTS = ["README.md", "site/src", "skills", "packs", ".claude-plugin", ".codex-plugin", "editions"]
SKIP_PARTS = {"node_modules", ".next", "tmp", "tests", "__pycache__"}
SUFFIXES = {".md", ".ts", ".tsx", ".json", ".txt", ".patch"}
EXEMPT = {
    Path("skills/investigate/prototype/references/UI.md"),
}


def exempt(rel: Path, phrase: str, line: str) -> bool:
    if rel.name == "CHANGELOG.md":
        return True
    if rel == Path("site/src/lib/legend.ts") and phrase == "vibe coding":
        return True
    if rel == Path("site/src/lib/human.ts") and phrase == "can't read the code":
        return True  # a first-person aside about review honesty, kept by decider call
    return rel in EXEMPT


def main() -> int:
    hits: list[str] = []
    for root in ROOTS:
        base = ROOT / root
        paths = [base] if base.is_file() else [p for p in base.rglob("*") if p.is_file()]
        for p in paths:
            rel = p.relative_to(ROOT)
            if SKIP_PARTS & set(rel.parts) or p.suffix not in SUFFIXES:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                for phrase in RETIRED:
                    if re.search(re.escape(phrase), line, re.IGNORECASE) and not exempt(rel, phrase, line):
                        hits.append(f"{rel}:{n}: retired positioning line {phrase!r} (decision 0005)")
    if hits:
        print("\n".join(hits), file=sys.stderr)
        print(f"\n{len(hits)} retired positioning phrase(s) found; see decision 0005.", file=sys.stderr)
        return 1
    print(f"positioning OK: none of {len(RETIRED)} retired phrases found")
    return 0


if __name__ == "__main__":
    sys.exit(main())

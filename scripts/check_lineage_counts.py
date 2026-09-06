#!/usr/bin/env python3
"""Lineage-count check (CI).

The hero's second paragraph counts where the shipped skills came from
("Sixteen are adapted from Matt Pocock's ..., three from Lauren Tan, four are
mine"). The site derives those numbers at build time from each skill's
Attribution section (site/src/lib/lineage.ts); README.md carries the same
sentence as static text. This derives the counts the same way and fails when
the README's sentence disagrees, so adding or moving a skill cannot leave the
README claiming a stale count. Same posture as check_invocation_freshness.py.

Rule, per promoted skill: an explicit `<!-- lineage: matt|tan|own -->` marker in
the Attribution section wins (for a skill that mentions a source without
deriving from it); otherwise a section linking github.com/mattpocock is
Matt's; one linking cursor/plugins or naming Lauren Tan without Matt is hers;
anything else is the maker's own. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
README = ROOT / "README.md"

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
         "eighteen", "nineteen", "twenty"]


def attribution(text: str) -> str:
    m = re.search(r"^## Attribution\s*$", text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def lineage(text: str) -> str:
    a = attribution(text)
    declared = re.search(r"<!--\s*lineage:\s*(matt|tan|own)\s*-->", a)
    if declared:
        return declared.group(1)
    if "github.com/mattpocock" in a:
        return "matt"
    if re.search(r"github\.com/cursor/plugins|Lauren Tan", a):
        return "tan"
    return "own"


def counts() -> dict[str, int]:
    promoted = {b["id"] for b in json.loads((SKILLS / "buckets.json").read_text())["buckets"] if b["promoted"]}
    out = {"matt": 0, "tan": 0, "own": 0}
    for bucket in sorted(promoted):
        for skill in sorted((SKILLS / bucket).glob("*/SKILL.md")):
            out[lineage(skill.read_text(encoding="utf-8"))] += 1
    return out


def word(n: int, capital: bool = False) -> str:
    w = WORDS[n] if n < len(WORDS) else str(n)
    return w.capitalize() if capital else w


def main() -> int:
    c = counts()
    if sum(c.values()) == 0:
        print("lineage check found no promoted skills; buckets or layout are wrong", file=sys.stderr)
        return 1
    expected = (f"{word(c['matt'], True)} are adapted from Matt Pocock's [Skills For Real Engineers]"
                f"(https://github.com/mattpocock/skills), {word(c['tan'])} from [Lauren Tan]"
                f"(https://github.com/cursor/plugins/tree/main/pstack), {word(c['own'])} are mine.")
    readme = README.read_text(encoding="utf-8")
    if expected not in readme:
        print("README.md lineage sentence disagrees with the skills' Attribution sections.", file=sys.stderr)
        print(f"expected: {expected}", file=sys.stderr)
        found = re.search(r"^[^\n]*adapted from Matt Pocock's \[Skills For Real Engineers\][^\n]*$", readme, re.M)
        print(f"found:    {found.group(0) if found else '(no lineage sentence)'}", file=sys.stderr)
        return 1
    print(f"lineage counts OK: matt={c['matt']} tan={c['tan']} own={c['own']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

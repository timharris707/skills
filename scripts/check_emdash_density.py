#!/usr/bin/env python3
"""Em-dash density tripwire (CI), from the #226 sweep.

The em dash is one of the most reliable AI tells (plainspoken's tell catalog,
pattern 13), and skill prose style leaks into model output, so the catalog's
skill texts were swept to zero em dashes outside code (#226). This check keeps
that from regressing: it counts em dashes per file, outside fenced code blocks
and inline code spans, and fails when any guarded file exceeds the threshold.

Guarded set (the files the sweep normalized):

  * every `SKILL.md` under `skills/` (all buckets, in-progress included)
  * every `*.md` under a `references/` directory beneath `skills/`

Deliberately not guarded: `CHANGELOG.md` (the release headline format requires
"— " separators per RELEASING.md), `README.md`, and files under `tests/` or
`scripts/`; none were in the sweep's scope.

Threshold: 8 em dashes outside code per file. Post-sweep the worst legitimate
survivor is 3 (a verbatim quoted anti-pattern example in orchestrate's
pr-writing reference), so 8 leaves generous headroom for quoted material while
any file written in the pre-sweep style (setup carried 69, advisory-board 102)
fails immediately. On failure the worst offenders are printed with counts.

Pure Python, standard library only, deliberately independent of grep flavors
(a local `grep` may be ugrep; exit-code semantics differ). Exit 0 = within
threshold; exit 1 = regression, one line per offending file.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
THRESHOLD = 8

FENCED_CODE = re.compile(r"^(?: {0,3})(```|~~~).*?^(?: {0,3})\1[^\n]*$", re.M | re.S)
INLINE_CODE = re.compile(r"`[^`\n]+`")


def emdash_count_outside_code(text: str) -> int:
    """Em dashes in prose: fenced code blocks and inline code spans exempt."""
    text = FENCED_CODE.sub("", text)
    text = INLINE_CODE.sub("", text)
    return text.count("—")


def guarded_files() -> list[Path]:
    out = []
    for path in sorted(SKILLS_DIR.rglob("*.md")):
        rel_parts = path.relative_to(SKILLS_DIR).parts
        if "tests" in rel_parts or "scripts" in rel_parts:
            continue
        if path.name == "SKILL.md" or "references" in rel_parts:
            out.append(path)
    if not out:
        raise SystemExit("no guarded files found under skills/; a green run would check nothing")
    return out


def main() -> int:
    counts = {p: emdash_count_outside_code(p.read_text(encoding="utf-8")) for p in guarded_files()}
    offenders = {p: n for p, n in counts.items() if n > THRESHOLD}
    if offenders:
        print(f"em-dash density regression: threshold is {THRESHOLD} per file outside code", file=sys.stderr)
        for p, n in sorted(offenders.items(), key=lambda kv: -kv[1]):
            print(f"  {n:4d}  {p.relative_to(ROOT)}", file=sys.stderr)
        print(
            "Rewrite the em-dash constructions (periods, commas, colons, or restructure; "
            "never an in-place swap); see plainspoken's tell catalog, pattern 13, and #226.",
            file=sys.stderr,
        )
        return 1
    worst = max(counts.values(), default=0)
    print(f"em-dash density OK: {len(counts)} guarded files, worst {worst}, threshold {THRESHOLD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

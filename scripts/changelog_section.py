#!/usr/bin/env python3
"""Resolve a skill's changelog and print one version's release-notes section.

The single implementation shared by the release workflows: auto-release's
detect job validates sections with it BEFORE any tag is cut, and
release-core extracts the release body with it. One copy, so what detect
approves is exactly what the release publishes — two drifting copies would
re-create the tag-first-validate-later wedge this exists to prevent (#115).

Usage: changelog_section.py <skill> <vX.Y.Z>

Rules (each violation exits non-zero with one line on stderr):
  - exactly one changelog dir may match: skills/<bucket>/<skill>/CHANGELOG.md
    or packs/<skill>/CHANGELOG.md — zero or two+ both fail rather than guess
  - the "## [vX.Y.Z]" heading must appear exactly once — a duplicated heading
    would silently merge or truncate sections, so it fails instead
  - the section body must be non-empty

Prints the section body to stdout on success. Standard library only.
"""

import re
import sys
from pathlib import Path


def die(msg: str) -> None:
    print(f"changelog_section: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 3:
        die("usage: changelog_section.py <skill> <vX.Y.Z>")
    skill, version = sys.argv[1], sys.argv[2]
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", skill):
        die(f"unexpected skill segment {skill!r}")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", version):
        die(f"version {version!r} is not vMAJOR.MINOR.PATCH")

    root = Path(__file__).resolve().parent.parent
    candidates = sorted(
        p
        for pattern in (f"skills/*/{skill}/CHANGELOG.md", f"packs/{skill}/CHANGELOG.md")
        for p in root.glob(pattern)
    )
    if not candidates:
        die(f"no CHANGELOG.md found for '{skill}' under skills/*/ or packs/")
    if len(candidates) > 1:
        die(f"'{skill}' has more than one CHANGELOG.md: {[str(p) for p in candidates]}")
    changelog = candidates[0]

    heading = f"## [{version}]"
    lines = changelog.read_text(encoding="utf-8").splitlines()
    starts = [
        i
        for i, line in enumerate(lines)
        if line.rstrip("\r") == heading or line.rstrip("\r").startswith(heading + " ")
    ]
    if not starts:
        die(f"missing '## [{version}]' section in {changelog}")
    if len(starts) > 1:
        die(f"'## [{version}]' appears {len(starts)} times in {changelog}")

    # Body = every line after the heading up to the next section heading,
    # kept verbatim (matching the release bodies published to date) so the
    # already-exists verification in release-core stays byte-exact.
    body: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if line.rstrip("\r").startswith("## ["):
            break
        body.append(line.rstrip("\r"))
    section = "\n".join(body)
    if not section.strip():
        die(f"empty '## [{version}]' section in {changelog}")
    print(section)


if __name__ == "__main__":
    main()

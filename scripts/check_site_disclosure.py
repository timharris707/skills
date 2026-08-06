#!/usr/bin/env python3
"""Fail the build if the public site names something it must not.

The site at ``site/`` is written from a private context repository. Most of what
lives there — customers, counterparties, colleagues, internal product names,
infrastructure — must never reach a public page. Care is not an invariant, so
this is the invariant.

The forbidden terms are themselves confidential, which is why this file carries
no plaintext list. ``scripts/disclosure_denylist.txt`` holds salted SHA-256
digests of lowercased one-, two-, and three-word phrases; the checker hashes the
site's own n-grams the same way and looks for collisions. A leak is caught, a
reader of this repository learns nothing, and adding a term never publishes it.

Run ``--add "some phrase"`` to append a term. Exit status 1 means something is
disclosed; the message says where, never what.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE_SRC = REPO / "site" / "src"
DENYLIST = Path(__file__).resolve().parent / "disclosure_denylist.txt"

# Fixed and public on purpose: this is domain separation so the digests cannot be
# checked against a generic rainbow table, not a secret. Anyone able to guess a
# phrase can confirm it either way; the point is that the list does not read as a
# customer roster to someone browsing the repo.
SALT = b"clickai-disclosure-v1:"

WORD = re.compile(r"[a-z0-9][a-z0-9.'-]*")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
MAX_NGRAM = 3


def digest(phrase: str) -> str:
    normalized = " ".join(phrase.lower().split())
    return hashlib.sha256(SALT + normalized.encode("utf-8")).hexdigest()


def load_denylist() -> set[str]:
    if not DENYLIST.exists():
        return set()
    out = set()
    for line in DENYLIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def site_files() -> list[Path]:
    return sorted(
        p
        for p in SITE_SRC.rglob("*")
        if p.is_file() and p.suffix in {".ts", ".tsx", ".css", ".js", ".jsx", ".md", ".json"}
    )


def ngrams(text: str):
    """Every 1-, 2-, and 3-word lowercase phrase, with the line it sits on."""
    for lineno, line in enumerate(text.splitlines(), start=1):
        words = WORD.findall(line.lower())
        for size in range(1, MAX_NGRAM + 1):
            for i in range(len(words) - size + 1):
                yield lineno, " ".join(words[i : i + size])


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--add":
        phrase = sys.argv[2]
        existing = load_denylist()
        h = digest(phrase)
        if h in existing:
            print("already present")
            return 0
        with DENYLIST.open("a", encoding="utf-8") as fh:
            fh.write(h + "\n")
        print(f"added ({len(existing) + 1} terms)")
        return 0

    denied = load_denylist()
    if not denied:
        print("site disclosure: no denylist found — nothing enforced", file=sys.stderr)
        return 1

    failures: list[str] = []

    for path in site_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(REPO)

        for match in EMAIL.finditer(text):
            lineno = text[: match.start()].count("\n") + 1
            failures.append(f"{rel}:{lineno}: an email address must not appear on the site")

        seen: set[tuple[int, str]] = set()
        for lineno, phrase in ngrams(text):
            if digest(phrase) in denied and (lineno, phrase) not in seen:
                seen.add((lineno, phrase))
                failures.append(
                    f"{rel}:{lineno}: a denylisted phrase appears here "
                    f"({len(phrase.split())}-word). It is confidential — remove it."
                )

    if failures:
        print("site disclosure check FAILED\n", file=sys.stderr)
        for line in failures:
            print(f"  {line}", file=sys.stderr)
        print(
            "\nThe phrase is deliberately not printed. Read the flagged line.",
            file=sys.stderr,
        )
        return 1

    print(f"site disclosure: OK ({len(site_files())} files, {len(denied)} terms enforced)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

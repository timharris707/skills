#!/usr/bin/env python3
"""Tripwire for the site's font subsets (#319).

The site's fonts are subsets cut by scripts/build_site_fonts.py, which keeps
only the characters recorded in site/src/fonts/fonts.json. A page that starts
using a character outside that set would render it in a fallback font. This
fetches every page in the sitemap from a running site build, plus the
Markdown twin its agent view shows and the stylesheets they load, and fails
when the server-rendered text, the Markdown twins, or any CSS `content` value
uses a character outside the recorded set. Text that client code renders only
after load (hover notes, fetch messages) is not seen. It also fails when a
font file no longer matches the hash recorded beside that set. A green run
means the fonts were cut with every character those sources use; a character
none of the source fonts draws still falls back.

The fix for a failure is to rerun the generator against a running build, so
the new characters are kept:

  python3 scripts/build_site_fonts.py --from-site http://localhost:3000

Standard library only. Expects `next start` to be listening; retries until
the server is up. Usage:

  python3 scripts/check_site_font_coverage.py [--base http://localhost:3000]
"""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "site" / "src" / "fonts"
MANIFEST = FONTS_DIR / "fonts.json"


def fetch(url: str, deadline: float = 60.0) -> str:
    """GET a URL as text, retrying until the server is up."""
    start = time.monotonic()
    while True:
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, ConnectionError, OSError) as error:
            if time.monotonic() - start > deadline:
                raise SystemExit(f"server never answered at {url}: {error}")
            time.sleep(1)


def twin_for(path: str) -> str | None:
    """The Markdown the agent view shows; mirrors twinFor in AgentFlip.tsx."""
    if path == "/":
        return "/llms.txt"
    if path in ("/work", "/legend", "/instruments"):
        return f"{path}.md"
    if re.fullmatch(r"/codex/skills/[^/]+|/(skills|legend|notes)/[^/]+", path):
        return f"{path}.md"
    return None


class PageText(HTMLParser):
    """Collects the text a page renders, skipping scripts and styles."""

    SKIP = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.text.append(data)


def site_characters(base: str) -> dict[str, str]:
    """Every character the site renders, mapped to one page that renders it."""
    sitemap = fetch(f"{base}/sitemap.xml")
    paths = [re.sub(r"^https?://[^/]+", "", loc) or "/" for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap)]
    if not paths:
        raise SystemExit("the sitemap listed no pages; a green run would check nothing")
    seen: dict[str, str] = {}
    stylesheets: set[str] = set()
    for path in paths:
        html = fetch(f"{base}{path}")
        parser = PageText()
        parser.feed(html)
        texts = ["".join(parser.text)]
        stylesheets.update(re.findall(r'<link rel="stylesheet" href="([^"]+)"', html))
        twin = twin_for(path)
        if twin:
            texts.append(fetch(f"{base}{twin}"))
        for text in texts:
            for char in text:
                if char >= " ":
                    seen.setdefault(char, path)
    # Generated content (CSS `content: "..."`) is rendered text too.
    for sheet in sorted(stylesheets):
        for value in re.findall(r'content:\s*"([^"]*)"', fetch(f"{base}{sheet}")):
            for char in css_unescape(value):
                if char >= " ":
                    seen.setdefault(char, sheet)
    return seen


def css_unescape(value: str) -> str:
    r"""Decode a CSS string's escapes: '\2606' is U+2606, '\"' is '"'."""
    return re.sub(r"\\(?:([0-9a-fA-F]{1,6})\s?|(.))",
                  lambda m: chr(int(m.group(1), 16)) if m.group(1) else m.group(2), value)


def parse_unicodes(ranges: str) -> set[int]:
    """'U+0000-00FF,U+2190' -> the set of code points it names."""
    points: set[int] = set()
    for part in ranges.split(","):
        first, _, last = part.strip().removeprefix("U+").partition("-")
        points.update(range(int(first, 16), int(last or first, 16) + 1))
    return points


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="http://localhost:3000")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    problems = []
    for name, digest in manifest["files"].items():
        actual = hashlib.sha256((FONTS_DIR / name).read_bytes()).hexdigest()
        if actual != digest:
            problems.append(f"{name} does not match the hash in fonts.json; regenerate it with the script.")

    kept = parse_unicodes(manifest["unicodes"])
    used = site_characters(args.base.rstrip("/"))
    missing = sorted((char, where) for char, where in used.items() if ord(char) not in kept)
    for char, where in missing:
        problems.append(f"U+{ord(char):04X} {char!r} is used (e.g. {where}) but the fonts were cut without it.")

    if problems:
        print("\n".join(problems), file=sys.stderr)
        print("Rerun: python3 scripts/build_site_fonts.py --from-site <running site URL>", file=sys.stderr)
        return 1
    print(f"the fonts were cut with all {len(used)} characters the site renders; "
          f"{len(manifest['files'])} font files match their hashes in fonts.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

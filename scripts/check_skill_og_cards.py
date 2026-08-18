#!/usr/bin/env python3
"""Tripwire for the per-skill link-preview cards (PR #214).

Fetches a skill page from a running site build and asserts the three
properties that PR shipped, so a metadata regression fails CI instead of
silently shipping a homepage card to every timeline:

  1. og:url names the page's own path, not the bare origin.
  2. og:image and twitter:image each name their per-skill image route
     (/skills/<slug>/opengraph-image, .../twitter-image) exactly, not the
     site-wide fallback.
  3. Each image route serves a real 1200x630 PNG (dimensions read from
     the IHDR chunk, content sniffed from the PNG signature).

Standard library only; HTML is matched with attribute-order-tolerant
regexes rather than shelling out, so the check behaves the same in CI and
on any developer machine. Expects `next start` to be listening; retries
until the server is up. Usage:

  python3 scripts/check_skill_og_cards.py [--base http://localhost:3000]
                                          [--slug adversarial-review]
"""

import argparse
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SITE_ORIGIN = "https://clickai.dev"


def fetch(url: str, timeout: float = 15.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def fetch_when_up(url: str, deadline: float = 60.0) -> bytes:
    """Retry until the dev/prod server answers — it starts in parallel."""
    start = time.monotonic()
    while True:
        try:
            return fetch(url)
        except (urllib.error.URLError, ConnectionError, OSError) as error:
            if time.monotonic() - start > deadline:
                raise SystemExit(f"server never answered at {url}: {error}")
            time.sleep(1)


def meta_content(html: str, attr: str, key: str) -> str:
    """The content= of a <meta> tag, tolerating either attribute order."""
    for pattern in (
        rf'<meta\s+{attr}="{re.escape(key)}"\s+content="([^"]*)"',
        rf'<meta\s+content="([^"]*)"\s+{attr}="{re.escape(key)}"',
    ):
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    raise SystemExit(f'no <meta {attr}="{key}"> tag found')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:3000")
    parser.add_argument("--slug", default="adversarial-review")
    args = parser.parse_args()

    page_path = f"/skills/{args.slug}"
    html = fetch_when_up(args.base + page_path).decode("utf-8")
    failures = []

    # 1. og:url claims this page, not the homepage (the pre-#214 bug).
    og_url = meta_content(html, "property", "og:url")
    if og_url != SITE_ORIGIN + page_path:
        failures.append(f"og:url is {og_url!r}, want {SITE_ORIGIN + page_path!r}")

    # 2 and 3. Each card image is the per-skill image route — exactly, not
    # merely somewhere under the skill path — and that route serves a
    # 1200x630 PNG. The emitted URL is absolute against the production origin
    # (with a cache-busting query); refetch its path from the server under
    # test.
    for tag_attr, key, route in (
        ("property", "og:image", "opengraph-image"),
        ("name", "twitter:image", "twitter-image"),
    ):
        url = meta_content(html, tag_attr, key)
        parsed = urllib.parse.urlsplit(url)
        expected = urllib.parse.urlsplit(f"{SITE_ORIGIN}{page_path}/{route}")
        if (parsed.scheme, parsed.netloc, parsed.path) != (
            expected.scheme,
            expected.netloc,
            expected.path,
        ):
            failures.append(f"{key} is {url!r}, want {expected.geturl()!r}")
            continue
        png = fetch_when_up(args.base + parsed.path)
        if png[:8] != b"\x89PNG\r\n\x1a\n":
            failures.append(f"{key} route did not return a PNG")
        else:
            width, height = struct.unpack(">II", png[16:24])
            if (width, height) != (1200, 630):
                failures.append(f"{key} is {width}x{height}, want 1200x630")

    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)
    print(f"link-preview card checks passed for {page_path}")


if __name__ == "__main__":
    main()

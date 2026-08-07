#!/usr/bin/env python3
"""Notify IndexNow that clickai.dev pages changed.

IndexNow is a push protocol: instead of waiting to be crawled, the site tells
participating engines what changed. Bing, Yandex, Seznam and Naver consume it.
Google has tested it and does not use it for indexing — so this speeds up the
Bing family only, which matters here mainly because Bing's index is what
ChatGPT's browsing reads.

Usage:
    python3 scripts/indexnow.py                    # every URL in the sitemap
    python3 scripts/indexnow.py /notes/some-note   # only these paths
    python3 scripts/indexnow.py --dry-run

Ownership is proved by a key file served at the host root; the route lives at
site/src/app/<KEY>.txt/route.ts and its directory name is the key. If the key
is rotated, change KEY here to match — the two must agree or every submission
is rejected as unverified.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request

HOST = "clickai.dev"
KEY = "4eb60288aa9dc50afb120dd731317477"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
SITEMAP = f"https://{HOST}/sitemap.xml"
ENDPOINT = "https://api.indexnow.org/indexnow"

# The protocol caps a batch at 10,000; the site is nowhere near it, but a cap
# that is never checked is a cap that fails the first time it matters.
MAX_BATCH = 10_000


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"user-agent": f"{HOST} indexnow"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def sitemap_urls() -> list[str]:
    return re.findall(r"<loc>(.*?)</loc>", fetch(SITEMAP))


def verify_key() -> bool:
    """The submission is rejected silently if the key file is not live yet."""
    try:
        return fetch(KEY_LOCATION).strip() == KEY
    except urllib.error.HTTPError as exc:
        print(f"key file returned HTTP {exc.code} at {KEY_LOCATION}")
        return False
    except Exception as exc:  # noqa: BLE001 — any failure means "not verifiable"
        print(f"could not fetch key file: {exc}")
        return False


def submit(urls: list[str]) -> int:
    payload = json.dumps(
        {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
    ).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={"content-type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv

    urls = (
        [f"https://{HOST}{p}" if p.startswith("/") else p for p in args]
        if args
        else sitemap_urls()
    )
    if not urls:
        print("no URLs to submit")
        return 1
    if len(urls) > MAX_BATCH:
        print(f"{len(urls)} URLs exceeds the {MAX_BATCH} batch cap")
        return 1

    print(f"{len(urls)} URL(s); first: {urls[0]}")
    if dry:
        return 0

    if not verify_key():
        print("\nKey file is not live. Merge and deploy first, then re-run.")
        return 1

    status = submit(urls)
    # 200 and 202 both mean accepted; the protocol returns no per-URL detail.
    print(f"IndexNow returned HTTP {status}")
    return 0 if status in (200, 202) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Tests for the character scan in scripts/check_site_font_coverage.py (#319).

In CI the scan runs only against a built site, so these feed it a stub site
instead: a sitemap, one page with its Markdown twin, and one stylesheet.
Next's minifier keeps CSS escapes as written (`content:"\\2606"`), so the scan
must decode them, or it reads the escape's digits instead of the character
the page shows.
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_site_font_coverage as coverage  # noqa: E402

BASE = "http://site.test"
SITE = {
    f"{BASE}/sitemap.xml": f"<urlset><url><loc>{BASE}/work</loc></url></urlset>",
    f"{BASE}/work": '<html><head><link rel="stylesheet" href="/app.css"></head>'
                    "<body><p>Plain text</p><script>ignored ✧</script></body></html>",
    f"{BASE}/work.md": "# Work",
    f"{BASE}/app.css": r'.a::before{content:"\2606"}.b::after{content:"\27A1 x"}',
}


class SiteCharactersTest(unittest.TestCase):
    def scan(self) -> dict[str, str]:
        with mock.patch.object(coverage, "fetch", side_effect=SITE.__getitem__):
            return coverage.site_characters(BASE)

    def test_css_escapes_are_read_as_the_characters_they_name(self):
        used = self.scan()
        self.assertEqual(used.get("☆"), "/app.css")
        self.assertEqual(used.get("➡"), "/app.css")
        self.assertNotIn("\\", used)

    def test_page_and_twin_text_is_read_and_scripts_are_skipped(self):
        used = self.scan()
        self.assertEqual(used.get("P"), "/work")
        self.assertEqual(used.get("#"), "/work")
        self.assertNotIn("✧", used)

    def test_css_unescape(self):
        self.assertEqual(coverage.css_unescape(r"\2606 x\"\\"), '☆x"\\')


if __name__ == "__main__":
    unittest.main()

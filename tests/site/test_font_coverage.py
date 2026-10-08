"""Tests for scripts/check_site_font_coverage.py (#319).

In CI the check runs only against a built site, so these feed its character
scan a stub site instead (a sitemap, one page with its Markdown twin, and one
stylesheet) and its file check a temporary font directory. Next's minifier
keeps CSS escapes as written (`content:"\\2606"`), so the scan must decode
them, or it reads the escape's digits instead of the character the page shows.
"""

import hashlib
import shutil
import sys
import tempfile
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


def scan(**changes: str) -> dict[str, str]:
    """Run the character scan over the stub site, with some URLs replaced."""
    site = {**SITE, **{f"{BASE}{path}": body for path, body in changes.items()}}
    with mock.patch.object(coverage, "fetch", side_effect=site.__getitem__):
        return coverage.site_characters(BASE)


class SiteCharactersTest(unittest.TestCase):
    def test_css_escapes_are_read_as_the_characters_they_name(self):
        used = scan()
        self.assertEqual(used.get("☆"), "/app.css")
        self.assertEqual(used.get("➡"), "/app.css")
        self.assertNotIn("\\", used)

    def test_page_and_twin_text_is_read_and_scripts_are_skipped(self):
        used = scan()
        self.assertEqual(used.get("P"), "/work")
        self.assertEqual(used.get("#"), "/work")
        self.assertNotIn("✧", used)

    def test_css_unescape(self):
        self.assertEqual(coverage.css_unescape(r"\2606 x\"\\"), '☆x"\\')

    def test_stylesheet_links_are_found_in_any_attribute_order(self):
        used = scan(**{"/work": '<link href="/app.css" precedence="next" rel="stylesheet">'})
        self.assertEqual(used.get("☆"), "/app.css")

    def test_pages_without_a_stylesheet_fail(self):
        with self.assertRaises(SystemExit):
            scan(**{"/work": "<p>No styles</p>"})

    def test_single_quoted_content_is_read(self):
        used = scan(**{"/app.css": r".a::before{content:'\2605 it\'s'}"})
        self.assertEqual(used.get("★"), "/app.css")
        self.assertEqual(used.get("'"), "/app.css")


class FileProblemsTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)
        (self.dir / "a").mkdir()
        self.files = {}
        for name in ("a/One.woff2", "Two.woff2"):
            (self.dir / name).write_bytes(name.encode())
            self.files[name] = hashlib.sha256(name.encode()).hexdigest()
        (self.dir / "Card.ttf").write_bytes(b"not a web font")

    def test_matching_manifest_passes(self):
        self.assertEqual(coverage.file_problems(self.files, self.dir), [])

    def test_empty_manifest_fails(self):
        self.assertTrue(coverage.file_problems({}, self.dir))

    def test_partial_manifest_fails(self):
        problems = coverage.file_problems({"Two.woff2": self.files["Two.woff2"]}, self.dir)
        self.assertEqual(problems, ["a/One.woff2 is shipped but not listed in fonts.json."])

    def test_listed_file_missing_fails(self):
        (self.dir / "Two.woff2").unlink()
        self.assertEqual(coverage.file_problems(self.files, self.dir),
                         ["Two.woff2 is listed in fonts.json but not shipped."])

    def test_changed_file_fails(self):
        (self.dir / "Two.woff2").write_bytes(b"recut")
        self.assertEqual(len(coverage.file_problems(self.files, self.dir)), 1)


if __name__ == "__main__":
    unittest.main()

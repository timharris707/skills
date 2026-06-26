#!/usr/bin/env python3
"""Tests for the Markdown -> HTML converter (scripts/_md.py) that renders seat
review bodies in the handoff. Covers the constructs models actually emit plus the
safety property that all text is escaped before any tag is inserted.

    python3 -m unittest discover -s tests -t tests
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import _md  # noqa: E402
from _md import md_to_html  # noqa: E402


class Headings(unittest.TestCase):
    def test_atx_heading_becomes_r_title(self):
        self.assertEqual(md_to_html("## 1. Verdict"), '<p class="r-title">1. Verdict</p>')

    def test_whole_line_bold_is_a_heading(self):
        # the ratelimiter reviews use **2. Strongest Objections** as a section head
        self.assertEqual(md_to_html("**2. Strongest Objections**"),
                         '<p class="r-title">2. Strongest Objections</p>')

    def test_partial_bold_is_not_a_heading(self):
        out = md_to_html("**What would change it:** switch the clock.")
        self.assertIn("<strong>What would change it:</strong>", out)
        self.assertNotIn("r-title", out)


class Inline(unittest.TestCase):
    def test_bold_italic_code(self):
        out = md_to_html("Use **bold**, *italic*, and `code()` here.")
        self.assertIn("<strong>bold</strong>", out)
        self.assertIn("<em>italic</em>", out)
        self.assertIn("<code>code()</code>", out)

    def test_inline_code_is_escaped_and_protected(self):
        # angle brackets inside code must escape; * inside code is NOT emphasis
        out = md_to_html("`SET k <x> NX` and `a*b*c`")
        self.assertIn("<code>SET k &lt;x&gt; NX</code>", out)
        self.assertIn("<code>a*b*c</code>", out)
        self.assertNotIn("<em>", out)

    def test_link(self):
        out = md_to_html("see [the docs](https://example.com/x) now")
        self.assertIn('<a href="https://example.com/x">the docs</a>', out)

    def test_html_is_escaped_not_executed(self):
        out = md_to_html("a <script>alert(1)</script> & b")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("&amp;", out)


class Blocks(unittest.TestCase):
    def test_unordered_list(self):
        out = md_to_html("- one\n- two\n- three")
        self.assertEqual(out, "<ul><li>one</li><li>two</li><li>three</li></ul>")

    def test_loose_ordered_list_is_one_list(self):
        # blank-line-separated numbered points must render as ONE <ol>, not three
        out = md_to_html("1. first\n\n2. second\n\n3. third")
        self.assertEqual(out.count("<ol>"), 1)
        self.assertEqual(out.count("<li>"), 3)

    def test_fenced_code_block(self):
        out = md_to_html("intro\n\n```python\nx = 1 < 2\n```\n\ndone")
        self.assertIn("<pre><code>x = 1 &lt; 2</code></pre>", out)
        self.assertIn("<p>intro</p>", out)
        self.assertIn("<p>done</p>", out)

    def test_blockquote(self):
        self.assertEqual(md_to_html("> quoted line"), "<blockquote>quoted line</blockquote>")

    def test_paragraphs_split_on_blank_line(self):
        out = md_to_html("para one\n\npara two")
        self.assertEqual(out, "<p>para one</p>\n<p>para two</p>")


class Robustness(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(md_to_html(""), "")
        self.assertEqual(md_to_html(None), "")

    def test_no_raw_markers_survive(self):
        src = ("## Heading\n\n**bold** and `code` and *em*\n\n- a\n- b\n\n"
               "1. x\n\n2. y\n\n> q\n\n```\nfence\n```")
        out = md_to_html(src)
        # nothing outside a code span should still look like raw markdown
        import re
        body = re.sub(r"<(code|pre)>.*?</\1>", "", out, flags=re.S)
        self.assertNotIn("**", body)
        self.assertNotIn("## ", body)

    def test_real_review_round_trips_clean(self):
        # the exact failure the user hit: a heading + bold + list review
        src = ("# Review\n*subtitle*\n\n## 1. Verdict\n\n"
               "**Ship with changes.** Confidence: high.\n\n"
               "The clock uses `time.time()`.\n\n## 2. Objections\n\n"
               "1. negative `n` passes\n\n2. config is incomplete")
        out = md_to_html(src)
        self.assertNotIn("##", out)
        for marker in ('<p class="r-title">1. Verdict</p>',
                       "<strong>Ship with changes.</strong> Confidence: high.",
                       "<code>time.time()</code>",
                       "<ol>"):
            self.assertIn(marker, out)


class Security(unittest.TestCase):
    """Adversarial-review regressions: a seat review is attacker-influenceable model
    output published as HTML, so it must never produce live HTML/JS."""

    def _attrs(self, out):
        # parse the first <a> and return its attribute dict, to assert no breakout
        from html.parser import HTMLParser
        found = {}

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "a" and not found:
                    found.update(dict(attrs))
        P().feed(out)
        return found

    def test_link_href_cannot_break_out_into_an_event_handler(self):
        out = md_to_html('[hi](x"onclick=alert(1)//)')
        attrs = self._attrs(out)
        self.assertNotIn("onclick", attrs, "a quote in the URL must not open a new attribute")

    def test_code_span_in_url_cannot_break_out(self):
        # round-2 bypass: an inline code span inside the link URL hid the raw quote from
        # _safe_href; the restore then spliced it into the href. Must NOT yield on* attrs.
        for payload in ('[click](#`" onclick=alert(document.cookie) `)',
                        '[x](#`" autofocus onfocus=alert(1) tabindex=1 `)'):
            out = md_to_html(payload)
            attrs = self._attrs(out)
            self.assertNotIn("onclick", attrs, payload)
            self.assertNotIn("onfocus", attrs, payload)
            self.assertNotIn("autofocus", attrs, payload)

    def test_quote_inside_code_span_is_escaped(self):
        out = md_to_html('config rejects `float(\"nan\")` early')
        self.assertIn("<code>float(&quot;nan&quot;)</code>", out)

    def test_javascript_scheme_is_neutralized(self):
        out = md_to_html("[Read more](javascript:alert%281%29)")
        self.assertNotIn("javascript:", out)
        self.assertIn('href="#"', out)

    def test_data_and_vbscript_schemes_neutralized(self):
        for url in ("data:text/html,<x>", "vbscript:msgbox", "VBScript:x"):
            out = md_to_html(f"[x]({url})")
            self.assertIn('href="#"', out, url)

    def test_safe_schemes_pass_through(self):
        for url in ("https://example.com/a", "mailto:a@b.com", "/rel/path", "#anchor"):
            out = md_to_html(f"[x]({url})")
            self.assertIn(f'href="{url}"', out, url)

    def test_forged_code_sentinel_does_not_crash_or_inject(self):
        # the PUA sentinels used internally must not be exploitable from input
        evil = "before 5 after"   # an out-of-range forged placeholder
        out = md_to_html(evil)                  # must not raise IndexError
        self.assertNotIn("", out)
        self.assertNotIn("", out)
        self.assertIn("before", out)
        self.assertIn("after", out)

    def test_unterminated_fence_does_not_swallow_the_review(self):
        src = "intro line\n\n```\nsome code\nVERDICT: block"
        out = md_to_html(src)
        self.assertIn("VERDICT: block", out, "an unterminated fence must not eat the verdict")
        self.assertIn("intro line", out)

    def test_ordered_list_preserves_start_number(self):
        self.assertIn('<ol start="3">', md_to_html("3. third\n4. fourth"))
        # a lone numbered sentence keeps its number rather than silently dropping it
        self.assertIn('start="1990"', md_to_html("1990. was a notable year for this"))

    def test_protocol_relative_url_is_rejected(self):
        out = md_to_html("[totally legit](//evil.example/login)")
        self.assertIn('href="#"', out)
        self.assertNotIn("evil.example", out)
        # a single-slash site-relative link still works
        self.assertIn('href="/internal/page"', md_to_html("[ok](/internal/page)"))

    def test_huge_ordered_number_does_not_crash(self):
        # >4300 digits would blow int(); the line must degrade to a paragraph, not raise
        out = md_to_html("9" * 5000 + ". item text here")
        self.assertIn("item text here", out)

    def test_unclosed_brackets_are_linear_not_quadratic(self):
        import time
        t = time.time()
        md_to_html("[" * 100000)        # would be ~18s with the backtracking regex
        self.assertLess(time.time() - t, 2.0, "link regex must be near-linear")


if __name__ == "__main__":
    unittest.main()

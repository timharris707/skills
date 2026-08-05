#!/usr/bin/env python3
"""Tests for the shared template engine (scripts/_render_engine.py).

The engine is the de-duplicated block / {{TOKEN}} machinery the three renderers
share. These cover the primitives directly, the loud guards, and the opt-in
SENTINEL stash that protects verbatim author content (an inlined SVG, a quoted
{{jinja}} snippet) from the comment-strip and leftover-placeholder passes.

    python3 -m unittest discover -s tests -t tests
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import _render_engine as eng  # noqa: E402

BLOCK_KEYS = {"ROW": "rows", "CELL": "cells"}
RAW_TOKENS = {"BODY"}


class FindFirstBlock(unittest.TestCase):
    def test_returns_none_when_no_block(self):
        self.assertIsNone(eng.find_first_block("<p>{{X}}</p>"))

    def test_depth_aware_nested_block(self):
        tpl = "<!-- BEGIN ROW -->a<!-- BEGIN CELL -->b<!-- END CELL -->c<!-- END ROW -->z"
        start, end, name, inner = eng.find_first_block(tpl)
        self.assertEqual(name, "ROW")
        self.assertEqual(tpl[start:end].count("END ROW"), 1)
        # inner spans the WHOLE outer body, including the nested CELL block.
        self.assertIn("BEGIN CELL", inner)
        self.assertIn("END CELL", inner)
        self.assertTrue(tpl[end:].startswith("z"))

    def test_unterminated_block_dies(self):
        with self.assertRaises(SystemExit) as cm:
            eng.find_first_block("<!-- BEGIN ROW -->oops")
        self.assertEqual(cm.exception.code, 2)


class Substitute(unittest.TestCase):
    def test_escapes_non_raw_passes_raw(self):
        ctx = {"name": "a<b>&c", "body": "<em>ok</em>"}
        out = eng.substitute("{{NAME}}|{{BODY}}", ctx, RAW_TOKENS)
        self.assertEqual(out, "a&lt;b&gt;&amp;c|<em>ok</em>")

    def test_missing_and_list_tokens_left_untouched(self):
        ctx = {"rows": [1, 2]}  # list-valued -> a block, not a scalar slot
        out = eng.substitute("{{ROWS}}|{{GONE}}", ctx, RAW_TOKENS)
        self.assertEqual(out, "{{ROWS}}|{{GONE}}")

    def test_none_renders_empty(self):
        self.assertEqual(eng.substitute("[{{X}}]", {"x": None}, RAW_TOKENS), "[]")

    def test_stash_hides_value_behind_sentinel(self):
        stash = []
        out = eng.substitute("{{BODY}}", {"body": "<svg><!--c--></svg>"}, RAW_TOKENS, stash)
        self.assertEqual(out, "\x00S0\x00")         # value hidden behind the exact sentinel
        self.assertEqual(stash, ["<svg><!--c--></svg>"])
        self.assertEqual(eng.restore_stash(out, stash), "<svg><!--c--></svg>")

    def test_restore_stash_dies_on_dangling_sentinel(self):
        with self.assertRaises(SystemExit) as cm:
            eng.restore_stash("\x00S5\x00", [])     # references a slot that was never minted
        self.assertEqual(cm.exception.code, 2)


class RenderItem(unittest.TestCase):
    def test_expands_nested_blocks(self):
        tpl = ("<!-- BEGIN ROW -->[{{LABEL}}:"
               "<!-- BEGIN CELL -->{{V}}<!-- END CELL -->]<!-- END ROW -->")
        ctx = {"rows": [
            {"label": "r1", "cells": [{"v": "x"}, {"v": "y"}]},
            {"label": "r2", "cells": [{"v": "z"}]},
        ]}
        out = eng.render_item(tpl, ctx, BLOCK_KEYS, RAW_TOKENS)
        self.assertEqual(out, "[r1:xy][r2:z]")

    def test_unknown_block_dies(self):
        with self.assertRaises(SystemExit) as cm:
            eng.render_item("<!-- BEGIN NOPE --><!-- END NOPE -->", {}, BLOCK_KEYS, RAW_TOKENS)
        self.assertEqual(cm.exception.code, 2)

    def test_non_list_block_value_dies(self):
        with self.assertRaises(SystemExit) as cm:
            eng.render_item("<!-- BEGIN ROW --><!-- END ROW -->",
                            {"rows": "notalist"}, BLOCK_KEYS, RAW_TOKENS)
        self.assertEqual(cm.exception.code, 2)


class StripComments(unittest.TestCase):
    def test_drops_authoring_keeps_divider(self):
        text = "<!-- note -->A\n<!-- ===== SECTION ===== -->\nB<!-- multi\nline -->C"
        out = eng.strip_comments(text)
        self.assertNotIn("note", out)
        self.assertNotIn("multi", out)
        self.assertIn("<!-- ===== SECTION ===== -->", out)


class Guards(unittest.TestCase):
    def test_leftover_token_dies(self):
        with self.assertRaises(SystemExit) as cm:
            eng.assert_fully_resolved("clean {{LEFT}} text")
        self.assertEqual(cm.exception.code, 2)

    def test_surviving_comment_dies(self):
        with self.assertRaises(SystemExit) as cm:
            eng.assert_fully_resolved("<!-- stray -->")
        self.assertEqual(cm.exception.code, 2)

    def test_clean_and_divider_pass(self):
        self.assertIsNone(eng.assert_fully_resolved("all good"))
        self.assertIsNone(eng.assert_fully_resolved("<!-- ===== KEPT ===== -->"))


class StashProtectsVerbatimContent(unittest.TestCase):
    """The render_plan use case: author content carrying an HTML comment or an
    uppercase {{TOKEN}}-shaped string must survive the guards untouched when
    stashed; inlined without the stash it is stripped or rejected instead."""

    TEMPLATE = "<main>{{BODY}}</main><!-- author note -->"
    # An inlined SVG with its own comment, plus a {{TOKEN}}-shaped quote.
    SVG = "<svg><!-- Generated by tool --><rect/></svg>"
    TEMPLATEY = "config uses {{DATABASE_URL}}"

    def _run(self, body, stash):
        out = eng.render_item(self.TEMPLATE, {"body": body}, {}, RAW_TOKENS, stash)
        out = eng.strip_comments(out)
        if stash is None:
            eng.assert_fully_resolved(out)
            return out
        eng.assert_fully_resolved(out)        # stashed body is invisible to the guard
        return eng.restore_stash(out, stash)

    def test_comment_stripped_without_stash_but_preserved_with(self):
        lost = self._run(self.SVG, stash=None)
        self.assertNotIn("Generated by tool", lost)        # author's SVG comment eaten
        kept = self._run(self.SVG, stash=[])
        self.assertEqual(kept, f"<main>{self.SVG}</main>")  # preserved verbatim
        self.assertNotIn("author note", kept)               # template comment still gone

    def test_uppercase_brace_rejected_without_stash_but_survives_with(self):
        with self.assertRaises(SystemExit) as cm:           # reads as an unfilled slot
            self._run(self.TEMPLATEY, stash=None)
        self.assertEqual(cm.exception.code, 2)
        kept = self._run(self.TEMPLATEY, stash=[])
        self.assertEqual(kept, f"<main>{self.TEMPLATEY}</main>")
        self.assertIn("{{DATABASE_URL}}", kept)


class SharedAcrossRenderers(unittest.TestCase):
    def test_renderers_import_the_same_die(self):
        import render_handoff as rh
        import render_verdict as rv
        self.assertIs(rh.die, eng.die)
        self.assertIs(rv.die, eng.die)

    def test_handoff_uses_shared_render_item(self):
        import render_handoff as rh
        self.assertIs(rh.render_item, eng.render_item)
        self.assertIs(rh.strip_comments, eng.strip_comments)


if __name__ == "__main__":
    unittest.main()

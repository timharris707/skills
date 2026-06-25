#!/usr/bin/env python3
"""Tests for render_plan.py — the markdown-plan -> self-contained HTML view.

    python3 -m unittest discover -s skills/advisory-board/tests

The view is a *render of the markdown* (the markdown is the source of truth), so
these assert that the structure, the COMPUTED progress/status, the escaping, and
the drop-when-empty behaviour all faithfully follow the markdown — and that the
no-leftover-placeholder guard fails loudly when a token or block is wrong.
"""
import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "scripts"))
REFS = os.path.normpath(os.path.join(HERE, "..", "references"))
REPO_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))

sys.path.insert(0, SCRIPTS)
import render_plan as rp  # noqa: E402

TEMPLATE_PATH = os.path.join(REFS, "plan-template.html")
FONTS_PATH = os.path.join(REFS, "plan-fonts.css")
REAL_PLAN = os.path.join(REPO_ROOT, "design", "run-board-v1x.md")


def template() -> str:
    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        return fh.read()


def silent_render(data, tpl, fonts=""):
    with contextlib.redirect_stderr(io.StringIO()):
        return rp.render(data, tpl, fonts)


def parse(src):
    """parse_plan with stderr suppressed (MINI intentionally trips a status warning)."""
    with contextlib.redirect_stderr(io.StringIO()):
        return rp.parse_plan(src)


MINI = """# Test Plan
> A short subtitle.

- **Updated:** 2026-01-01
- **Owner:** Tester

## Overview
Hello **world** and `code`.

## Milestone: Alpha
status: wip
A milestone description paragraph.

### Phase 1 — First phase
- [x] done task
- [ ] todo task
- [wip] active task
- [f] failed task
Testing: prove it with units.
Gate: `make check`

## Decisions
- **D1** Keep it simple — fewer moving parts win.

## Risks
- **R1** It might break — add a test.

## Dependency order
```svg
<svg id="dep"><rect/></svg>
```
"""


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.d = parse(MINI)

    def test_title_and_subtitle(self):
        self.assertEqual(self.d["title"], "Test Plan")
        self.assertEqual(len(self.d["subtitle"]), 1)
        self.assertIn("A short subtitle.", self.d["subtitle"][0]["subtitle"])

    def test_meta_chips(self):
        labels = {m["meta_label"]: m["meta_value"] for m in self.d["meta"]}
        self.assertEqual(labels["Updated"], "2026-01-01")
        self.assertEqual(labels["Owner"], "Tester")

    def test_overview_inline_formatting(self):
        html = self.d["overview"][0]["overview"]
        self.assertIn("<strong>world</strong>", html)
        self.assertIn("<code>code</code>", html)

    def test_one_milestone_with_description(self):
        self.assertEqual(len(self.d["milestones"]), 1)
        ms = self.d["milestones"][0]
        self.assertIn("Alpha", ms["ms_title"])
        # regression: the description before the first '###' must not be dropped
        self.assertEqual(len(ms["desc"]), 1)
        self.assertIn("description paragraph", ms["desc"][0]["ms_desc"])

    def test_checklist_states_and_glyphs(self):
        tasks = self.d["milestones"][0]["phases"][0]["tasks"]
        self.assertEqual([t["task_state"] for t in tasks],
                         ["done", "todo", "wip", "blocked"])
        self.assertEqual([t["task_glyph"] for t in tasks], ["✓", "", "●", "✕"])

    def test_testing_and_gate(self):
        ph = self.d["milestones"][0]["phases"][0]
        self.assertEqual(len(ph["testing"]), 1)
        self.assertIn("prove it", ph["testing"][0]["ph_testing"])
        self.assertEqual(len(ph["gate"]), 1)
        self.assertEqual(ph["gate"][0]["ph_gate"], "make check")  # backticks stripped

    def test_decisions_and_risks(self):
        dec = self.d["decisions"][0]["decision"][0]
        self.assertEqual(dec["dec_tag"], "D1")
        self.assertIn("Keep it simple", dec["dec_title"])
        self.assertIn("fewer moving parts", dec["dec_body"])
        risk = self.d["risks"][0]["risk"][0]
        self.assertEqual(risk["risk_tag"], "R1")
        self.assertIn("add a test", risk["risk_body"])

    def test_diagram_svg_inlined(self):
        self.assertEqual(len(self.d["diagram"]), 1)
        self.assertEqual(self.d["diagram"][0]["diagram"], '<svg id="dep"><rect/></svg>')


class TestProgressAndStatus(unittest.TestCase):
    def test_overall_progress_math(self):
        d = parse(MINI)                       # 1 done of 4 tasks
        self.assertEqual(d["done_count"], 1)
        self.assertEqual(d["total_count"], 4)
        self.assertEqual(d["progress_label"], "25%")

    def test_ring_offset_is_circumference_times_remaining(self):
        d = parse(MINI)
        self.assertAlmostEqual(float(d["ring_offset"]), rp.RING_CIRC * 0.75, places=1)

    def test_milestone_progress(self):
        ms = parse(MINI)["milestones"][0]
        self.assertEqual((ms["ms_done"], ms["ms_total"], ms["ms_pct"]), (1, 4, 25))

    def test_explicit_status_overrides_derivation(self):
        # phase has a [f] task -> derives "blocked"; milestone says wip -> wins
        d = parse(MINI)
        self.assertEqual(d["milestones"][0]["ms_state"], "wip")
        self.assertEqual(d["milestones"][0]["phases"][0]["ph_state"], "blocked")

    def test_derivation_all_done(self):
        src = "# P\n## Milestone: M\n### Phase 1 — x\n- [x] a\n- [x] b\n"
        d = rp.parse_plan(src)
        self.assertEqual(d["milestones"][0]["ms_state"], "done")
        self.assertEqual(d["progress_label"], "100%")

    def test_derivation_all_todo(self):
        src = "# P\n## Milestone: M\n### Phase 1 — x\n- [ ] a\n- [ ] b\n"
        d = rp.parse_plan(src)
        self.assertEqual(d["milestones"][0]["ms_state"], "todo")
        self.assertEqual(d["progress_label"], "0%")

    def test_empty_plan_no_divide_by_zero(self):
        d = rp.parse_plan("# Empty\n")
        self.assertEqual((d["done_count"], d["total_count"]), (0, 0))
        self.assertEqual(d["progress_label"], "0%")
        self.assertAlmostEqual(float(d["ring_offset"]), rp.RING_CIRC, places=1)  # 0% -> full offset


class TestRendering(unittest.TestCase):
    def test_real_plan_renders_with_no_leftovers(self):
        data = parse(MINI)
        data["eyebrow"] = "Advisory Board · Plan"
        data["metadata"] = "footer"
        out = silent_render(data, template(), fonts="/* fonts */")
        self.assertNotIn("{{", out)
        self.assertNotIn("}}", out)
        # authoring BEGIN/END comments must be gone; ===== dividers may remain
        self.assertNotIn("BEGIN ", out)
        self.assertNotIn("END ", out)
        self.assertIn("make check", out)
        self.assertIn("25%", out)
        self.assertIn('<svg id="dep">', out)

    def test_html_escaping_of_injected_text(self):
        src = "# P\n## Milestone: A & B <danger>\n### Phase 1 — x\n- [ ] safe\n"
        ms = rp.parse_plan(src)["milestones"][0]
        self.assertIn("A &amp; B &lt;danger&gt;", ms["ms_title"])

    def test_script_injection_is_escaped_in_output(self):
        src = "# P\n## Milestone: M\n### Phase 1 — x\n- [ ] <script>alert(1)</script>\n"
        data = rp.parse_plan(src)
        data["eyebrow"] = "e"
        data["metadata"] = "m"
        out = silent_render(data, template(), fonts="")
        self.assertNotIn("<script>alert(1)</script>", out)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", out)

    def test_optional_blocks_drop_when_empty(self):
        src = "# Bare\n## Milestone: Only\n### Phase 1 — x\n- [ ] a\n"
        data = rp.parse_plan(src)
        data["eyebrow"] = "e"
        data["metadata"] = "m"
        out = silent_render(data, template(), fonts="")
        self.assertNotIn(">Decisions<", out)
        self.assertNotIn("Risks &amp; mitigations", out)
        self.assertNotIn('class="gate"', out)
        self.assertNotIn('class="testing"', out)
        self.assertNotIn('class="ms-desc"', out)
        self.assertNotIn('class="subtitle"', out)
        self.assertNotIn('<figure class="diagram"', out)

    def test_fonts_are_injected(self):
        data = parse(MINI)
        data["eyebrow"] = "e"
        data["metadata"] = "m"
        out = silent_render(data, template(), fonts="@font-face{/*marker*/}")
        self.assertIn("@font-face{/*marker*/}", out)


class TestGuards(unittest.TestCase):
    def test_unresolved_token_dies(self):
        data = rp.parse_plan("# X")
        with self.assertRaises(SystemExit):
            silent_render(data, "<p>{{BOGUS_TOKEN}}</p>", "")

    def test_unknown_block_dies(self):
        data = rp.parse_plan("# X")
        with self.assertRaises(SystemExit):
            silent_render(data, "<!-- BEGIN ZZZ -->x<!-- END ZZZ -->", "")


class TestEndToEnd(unittest.TestCase):
    def test_check_on_real_plan(self):
        with contextlib.redirect_stdout(io.StringIO()):
            rc = rp.main([REAL_PLAN, "--check"])
        self.assertEqual(rc, 0)

    def test_writes_self_contained_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "plan.html")
            with contextlib.redirect_stdout(io.StringIO()):
                rc = rp.main([REAL_PLAN, "-o", out])
            self.assertEqual(rc, 0)
            with open(out, encoding="utf-8") as fh:
                html = fh.read()
            self.assertNotIn("{{", html)
            if os.path.exists(FONTS_PATH):
                self.assertIn("@font-face", html)        # embedded, offline-ready
            self.assertIn("Dependency order", html)        # the diagram section
            self.assertIn("Validation gate", html)


def render_full(src: str) -> str:
    data = rp.parse_plan(src)
    data["eyebrow"] = "e"
    data["metadata"] = "m"
    return silent_render(data, template(), fonts="")


class TestHardeningSilentLoss(unittest.TestCase):
    """The renderer must never silently drop authored content (its core contract)."""

    def test_endash_milestone_separator_is_recognized(self):
        d = rp.parse_plan("# P\n## Milestone – EnDash Name\n### Phase 1 — x\n- [x] a\n")
        self.assertEqual(len(d["milestones"]), 1)
        self.assertEqual(d["total_count"], 1)
        self.assertIn("EnDash Name", d["milestones"][0]["ms_title"])

    def test_milestone_with_no_separator(self):
        d = rp.parse_plan("# P\n## Milestone Bare Name\n### Phase 1 — x\n- [ ] a\n")
        self.assertEqual(len(d["milestones"]), 1)
        self.assertIn("Bare Name", d["milestones"][0]["ms_title"])

    def test_phase_before_any_milestone_fails_loud(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                rp.parse_plan("# P\n### Phase 1 — orphan\n- [ ] a\n")

    def test_unrecognized_checklist_mark_fails_loud(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                rp.parse_plan("# P\n## Milestone: M\n### Phase 1 — x\n- [done] task\n")

    def test_empty_milestone_title_fails_loud(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                rp.parse_plan("# P\n## Milestone:\n")

    def test_status_count_conflict_warns(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rp.parse_plan("# P\n## Milestone: M\n### Phase 1 — x\nstatus: done\n- [wip] a\n")
        self.assertIn("warning", err.getvalue())
        self.assertIn("tasks imply", err.getvalue())


class TestHardeningInjection(unittest.TestCase):
    def test_javascript_link_is_inert(self):
        out = rp.inline("see [click](javascript:alert(1)) now")
        self.assertNotIn("href", out)
        self.assertNotIn("javascript:", out)
        self.assertIn("click", out)

    def test_data_url_link_is_inert(self):
        out = rp.inline("[r](data:text/html,<x>)")
        self.assertNotIn("href", out)

    def test_safe_links_keep_href(self):
        self.assertIn('href="https://example.com"', rp.inline("[ok](https://example.com)"))
        self.assertIn('href="mailto:a@b.com"', rp.inline("[m](mailto:a@b.com)"))
        self.assertIn('href="#frag"', rp.inline("[a](#frag)"))
        self.assertIn('href="rel/page.html"', rp.inline("[a](rel/page.html)"))

    def test_diagram_script_and_handlers_are_scrubbed(self):
        src = ('# P\n## Dependency order\n```svg\n'
               '<svg onload="x()"><script>alert(1)</script><rect onclick="y()"/></svg>\n```\n')
        d = rp.parse_plan(src)
        svg = d["diagram"][0]["diagram"]
        self.assertNotIn("<script", svg.lower())
        self.assertNotIn("onload", svg.lower())
        self.assertNotIn("onclick", svg.lower())
        self.assertIn("<rect", svg)

    def test_non_svg_fence_is_not_injected(self):
        src = "# P\n## Dependency order\n```html\n<script>bad()</script>\n```\n"
        self.assertEqual(rp.parse_plan(src)["diagram"], [])


class TestHardeningVerbatim(unittest.TestCase):
    def test_literal_braces_in_diagram_render_clean(self):
        src = "# P\n## Dependency order\n```svg\n<svg><text>{{VALUE}}</text></svg>\n```\n"
        out = render_full(src)                      # must NOT die on the literal braces
        self.assertIn("{{VALUE}}", out)

    def test_svg_comment_is_preserved(self):
        src = "# P\n## Dependency order\n```svg\n<svg><!-- keep me --><rect/></svg>\n```\n"
        out = render_full(src)
        self.assertIn("<!-- keep me -->", out)      # inlined as-is, not stripped

    def test_gate_bold_wrapping_is_stripped(self):
        src = "# P\n## Milestone: M\n### Phase 1 — x\n- [ ] a\nGate: **`make verify`**\n"
        ph = rp.parse_plan(src)["milestones"][0]["phases"][0]
        self.assertEqual(ph["gate"][0]["ph_gate"], "make verify")


class TestDriftGuard(unittest.TestCase):
    def test_committed_html_matches_a_fresh_render(self):
        committed_path = os.path.join(REPO_ROOT, "design", "run-board-v1x.html")
        with tempfile.TemporaryDirectory() as tmp:
            fresh_path = os.path.join(tmp, "fresh.html")
            with contextlib.redirect_stdout(io.StringIO()):
                rp.main([REAL_PLAN, "-o", fresh_path])
            with open(fresh_path, encoding="utf-8") as fh:
                fresh = fh.read()
        with open(committed_path, encoding="utf-8") as fh:
            committed = fh.read()
        self.assertEqual(
            fresh, committed,
            "design/run-board-v1x.html is stale — run scripts/render_plan.py to regenerate it.",
        )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Binds references/prompt-templates.md to the prompt constants the conductor ships.

`prompt_template_sha()` hashes only the Python constants, so nothing else notices
when the doc's code fences drift from the bytes that actually reach a seat. This
test is that tripwire. It reads every fenced block in the doc, whatever its language
tag (or none) and wherever it sits, the text before the first `## ` heading included.
A section named in BOUND must hold exactly the fences it lists, each equal to (or a
verbatim slice of) its shipped constant. A section named in HAND_RUN may hold any
fences, unchecked. A fenced block in any other section fails the test.

    python3 -m unittest discover -s tests -p 'test_prompt_templates_doc.py'
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "scripts")))

from _conductor import prompts  # noqa: E402

DOC = os.path.normpath(os.path.join(HERE, "..", "references", "prompt-templates.md"))

# Section heading -> the constants its fences quote, in document order. A
# fence is "whole" when it equals the constant, or "excerpt" when it is a verbatim
# slice of it. Newlines around a constant are splice whitespace the doc does not show.
BOUND = {
    "Required suffix: Claude seat (`{{CLAUDE_OUTPUT_OVERRIDE}}`)": [
        ("CLAUDE_OUTPUT_OVERRIDE", "whole")],
    "Conditional clause: repo-grounded review (`{repo_grounding}` / `{repo_evidence_ask}`)": [
        ("REPO_GROUNDING_CLAUSE", "whole"), ("REPO_EVIDENCE_ASK", "whole")],
    "The independence / basis line: round 2+ (`BASIS:`)": [
        ("BASIS_LINE_INSTRUCTION", "excerpt")],
    "Rubric-first scoring: proposal, chair merge, and the `{rubric_scoring}` block (v1.15)": [
        ("RUBRIC_SCORING_BLOCK", "excerpt")],
    "Round 1 Seat Prompt": [("ROUND1_TEMPLATE", "whole")],
    "Round 2 Rebuttal Prompt": [
        ("ROUND2_TEMPLATE", "whole"),
        ("ROUND2_PEERS_BLOCK", "whole"),
        ("ROUND2_SOLO_BLOCK", "whole")],
}

# Fences the conductor does not send in this shape: starting points for a hand-run board.
HAND_RUN = {"Round 3 Convergence Prompt", "Final Synthesis Prompt"}


PREAMBLE = "(preamble)"  # the text before the first `## ` heading
OPENER = re.compile(r"^\s*(`{3,}|~{3,})")


def doc_fences():
    """{section heading: [body of each fenced block, in order]} for the doc.

    A block opens on a line of three or more backticks or tildes, with any info
    string, and closes on a bare line of the same character at least as long. An
    unclosed block runs to the end of the doc, so it still counts."""
    sections, heading, mark, body = {PREAMBLE: []}, PREAMBLE, None, []
    with open(DOC, encoding="utf-8") as fh:
        for line in fh.read().splitlines():
            if mark is None:
                opened = OPENER.match(line)
                if opened:
                    mark, body = opened.group(1), []
                elif line.startswith("## "):
                    heading = line[3:]
                    sections.setdefault(heading, [])
            elif re.match(rf"^\s*{mark[0]}{{{len(mark)},}}\s*$", line):
                sections[heading].append("\n".join(body))
                mark = None
            else:
                body.append(line)
    if mark is not None:
        sections[heading].append("\n".join(body))
    return sections


class PromptTemplatesDocMatchesShippedConstants(unittest.TestCase):
    def test_every_bound_fence_matches_its_constant(self):
        fences = doc_fences()
        for heading, bindings in BOUND.items():
            with self.subTest(section=heading):
                self.assertIn(heading, fences, f"section missing from {DOC}")
                found = fences[heading]
                self.assertEqual(
                    len(found), len(bindings),
                    f"expected {len(bindings)} fence(s) in '{heading}', found {len(found)}")
                for fence, (name, kind) in zip(found, bindings):
                    shipped = getattr(prompts, name).strip("\n")
                    if kind == "whole":
                        self.assertEqual(
                            fence, shipped,
                            f"fence in '{heading}' differs from prompts.{name}; "
                            f"copy the constant into the fence")
                    else:
                        self.assertIn(
                            fence, shipped,
                            f"excerpt in '{heading}' is not a verbatim slice of prompts.{name}")

    def test_no_fence_escapes_the_binding(self):
        # A new fenced block, in any section or the preamble and with any language
        # tag or none, must either quote a constant (add it to BOUND) or be declared
        # a hand-run prompt; otherwise it is another copy nothing checks.
        with_fences = {heading for heading, found in doc_fences().items() if found}
        self.assertEqual(with_fences - set(BOUND) - HAND_RUN, set())


if __name__ == "__main__":
    unittest.main()

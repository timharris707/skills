"""Tripwire for the review-settled merge gate's thread filters (skills#288).

The gate is shell + jq inside .github/workflows/review-settled.yml, so nothing
else in CI exercises it; a regression there (say, the reply requirement quietly
dropped, or a bot reply counted as a disposition) would pass every other check.
These tests lift the two jq filters verbatim out of the workflow text and run
them with jq against fixture pages shaped like the GraphQL response, so the
tested filter is always the shipped one.

Requires jq on PATH, as the workflow does; a missing jq fails the suite rather than
skipping it, so a green run always means the filters ran.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/review-settled.yml"


def filters() -> tuple[str, str]:
    text = WORKFLOW.read_text()
    unresolved = re.search(r"unresolved=\$\(\(unresolved \+ \$\(jq '(.+?)' <<<", text)
    unreplied = re.search(r"unreplied=\$\(\(unreplied \+ \$\(jq '(.+?)' <<<", text, re.S)
    assert unresolved and unreplied, "gate filters not found in the workflow"
    return unresolved.group(1), unreplied.group(1)


def run(filter_text: str, page: dict) -> int:
    out = subprocess.run(["jq", filter_text], input=json.dumps(page), capture_output=True, text=True, check=True)
    return int(out.stdout.strip())


def bot(login: str = "coderabbitai") -> dict:
    return {"author": {"__typename": "Bot", "login": login}}


def user(login: str = "timharris707") -> dict:
    return {"author": {"__typename": "User", "login": login}}


def thread(*comments: dict, resolved: bool = True) -> dict:
    return {"isResolved": resolved, "comments": {"nodes": list(comments)}}


def page(*threads: dict) -> dict:
    return {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": list(threads)}


class ReviewSettledFilters(unittest.TestCase):
    def setUp(self) -> None:
        # Fail, never skip: a skipped suite reports success without testing the gate.
        self.assertIsNotNone(shutil.which("jq"), "jq is required to test the gate's filters")
        self.unresolved, self.unreplied = filters()

    def test_unresolved_counts_only_open_threads(self) -> None:
        p = page(thread(bot(), user(), resolved=False), thread(bot(), user()), thread(user(), resolved=False))
        self.assertEqual(run(self.unresolved, p), 2)

    def test_resolved_bot_thread_without_reply_is_unreplied(self) -> None:
        # The escape #288 closes: every thread resolved, nothing answered.
        p = page(thread(bot()), thread(bot()))
        self.assertEqual(run(self.unreplied, p), 2)

    def test_human_reply_settles_a_thread(self) -> None:
        p = page(thread(bot(), user()), thread(bot(), user("someone-else"), bot()))
        self.assertEqual(run(self.unreplied, p), 0)

    def test_bot_only_replies_do_not_count(self) -> None:
        p = page(thread(bot(), bot()), thread(bot(), bot("github-actions")))
        self.assertEqual(run(self.unreplied, p), 2)

    def test_deleted_replier_counts_as_human(self) -> None:
        p = page(thread(bot(), {"author": None}))
        self.assertEqual(run(self.unreplied, p), 0)

    def test_human_opened_threads_are_ignored(self) -> None:
        # A reviewer's own thread needs resolution, not a reply.
        p = page(thread(user()), thread(user(), resolved=False))
        self.assertEqual(run(self.unreplied, p), 0)

    def test_merge_condition_still_requires_a_reply(self) -> None:
        # The filters mean nothing if the exit condition stops consuming them (#288).
        self.assertIn(
            '[ "$reviewed" -gt 0 ] && [ "$unresolved" -eq 0 ] && [ "$unreplied" -eq 0 ]',
            WORKFLOW.read_text(),
        )

    def test_empty_page(self) -> None:
        self.assertEqual(run(self.unreplied, page()), 0)
        self.assertEqual(run(self.unresolved, page()), 0)


if __name__ == "__main__":
    unittest.main()

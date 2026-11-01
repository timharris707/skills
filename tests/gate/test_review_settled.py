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
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/review-settled.yml"


ARGS = r"--arg head \"\$HEAD_SHA\" --argjson once \"\$REVIEW_ONCE\" \\\n\s+'(.+?)'\)"


def reviewed_filter() -> str:
    text = WORKFLOW.read_text()
    m = re.search(r"reviewed=\$\(gh api \"repos/\$REPO/issues/\$PR_NUMBER/comments\" --paginate \| jq -s \\\n\s+" + ARGS, text, re.S)
    assert m, "walkthrough filter not found in the workflow"
    return m.group(1)


def reviews_filter() -> str:
    text = WORKFLOW.read_text()
    m = re.search(r"reviewed=\$\(gh api \"repos/\$REPO/pulls/\$PR_NUMBER/reviews\" --paginate \| jq -s \\\n\s+" + ARGS, text, re.S)
    assert m, "review-object filter not found in the workflow"
    return m.group(1)


def pending_filter() -> str:
    text = WORKFLOW.read_text()
    m = re.search(r"pending=\$\(gh api \"repos/\$REPO/issues/\$PR_NUMBER/comments\" --paginate \| jq -s \\\n\s+'(.+?)'\)", text, re.S)
    assert m, "in-progress filter not found in the workflow"
    return m.group(1)


def count_pages(filter_text: str, *pages: list, head: str = "", once: bool = False) -> int:
    # The workflow feeds `--paginate` output (one JSON array per page, one per
    # line) to jq -s, which wraps the pages into the outer list itself.
    stream = "\n".join(json.dumps(p) for p in pages)
    args = ["jq", "-s", "--arg", "head", head, "--argjson", "once", json.dumps(once), filter_text]
    out = subprocess.run(args, input=stream, capture_output=True, text=True, check=True)
    return int(out.stdout.strip())


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


STUB_GH = """#!/bin/bash
# Stub gh for the gate script: no reviews, no comments, no threads; the PR
# head is $STUB_HEAD.
case "$*" in
  *"pulls/7/reviews"*|*"issues/7/comments"*) echo '[]' ;;
  "api graphql"*) echo '{"pageInfo":{"hasNextPage":false,"endCursor":null},"nodes":[]}' ;;
  *"pulls/7 "*) echo "$STUB_HEAD" ;;
  *) echo "unexpected gh call: $*" >&2; exit 2 ;;
esac
"""


def run_gate(stub_head: str, head: str) -> tuple[int, str]:
    """Run the workflow's shipped run: script with a zero-minute wait window."""
    m = re.search(r"\n {8}run: \|\n(.+)\Z", WORKFLOW.read_text(), re.S)
    assert m, "gate script not found in the workflow"
    script = textwrap.dedent(m.group(1))
    with tempfile.TemporaryDirectory() as tmp:
        gh = Path(tmp) / "gh"
        gh.write_text(STUB_GH)
        gh.chmod(0o755)
        env = {**os.environ, "PATH": f"{tmp}:{os.environ['PATH']}", "STUB_HEAD": stub_head,
               "REPO": "o/r", "PR_NUMBER": "7", "HEAD_SHA": head, "PR_TITLE": "t",
               "SKIP_TITLE_REGEX": "", "SKIP_LABEL": "", "WAIT_MINUTES": "0", "REVIEW_ONCE": "false"}
        out = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True, timeout=60)
    return out.returncode, out.stdout + out.stderr


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

    def test_rate_limit_notice_is_not_a_review(self) -> None:
        # skills#291: the limit notice carries the summarize marker and the reviewed
        # range, so the gate counted it as a review of head and passed unread.
        head = "4f355d22f64f20b6e131f95a9640fa95c28d7c6a"
        rng = f"between e60004682df7de66be55e0acd83445281d8c421c and {head}"
        walkthrough = {"user": {"login": "coderabbitai[bot]"},
                       "body": f"<!-- auto-generated comment: summarize by coderabbit.ai -->\nReviewing files {rng}."}
        limited = {"user": {"login": "coderabbitai[bot]"},
                   "body": f"<!-- auto-generated comment: summarize by coderabbit.ai -->\n<!-- auto-generated comment: rate limited by coderabbit.ai -->\nReview limit reached. {rng}."}
        pending = {"user": {"login": "coderabbitai[bot]"},
                   "body": f"<!-- auto-generated comment: summarize by coderabbit.ai -->\n<!-- auto-generated comment: review in progress by coderabbit.ai -->\nCurrently processing {rng}."}
        f = reviewed_filter()
        def count(*pages):
            return count_pages(f, *pages, head=head)
        self.assertEqual(count([walkthrough]), 1)
        self.assertEqual(count([limited]), 0)
        self.assertEqual(count([pending]), 0)
        self.assertEqual(count([limited, walkthrough]), 1)
        # Across pages, as --paginate delivers them: the notice on one, the walkthrough on another.
        self.assertEqual(count([limited], [walkthrough]), 1)
        self.assertEqual(count([pending], [limited]), 0)

    def test_review_once_counts_a_review_of_an_earlier_commit(self) -> None:
        # chili, 2026-10-29: CodeRabbit reviews once, so after a fix push the
        # head-only gate waited 20 minutes for a pass that never comes.
        head, old = "4f355d22f64f20b6e131f95a9640fa95c28d7c6a", "e60004682df7de66be55e0acd83445281d8c421c"
        review = {"user": {"login": "coderabbitai[bot]"}, "commit_id": old}
        walkthrough = {"user": {"login": "coderabbitai[bot]"},
                       "body": f"<!-- auto-generated comment: summarize by coderabbit.ai -->\nReviewing files between {'1' * 40} and {old}."}
        for f, item in ((reviews_filter(), review), (reviewed_filter(), walkthrough)):
            self.assertEqual(count_pages(f, [item], head=head, once=False), 0)
            self.assertEqual(count_pages(f, [item], head=head, once=True), 1)
        other = {"user": {"login": "someone[bot]"}, "commit_id": head}
        self.assertEqual(count_pages(reviews_filter(), [other], head=head, once=True), 0)

    def test_review_once_still_skips_rate_limit_and_in_progress_notices(self) -> None:
        rng = f"between {'1' * 40} and {'2' * 40}"
        marker = "<!-- auto-generated comment: summarize by coderabbit.ai -->\n"
        limited = {"user": {"login": "coderabbitai[bot]"},
                   "body": marker + f"<!-- auto-generated comment: rate limited by coderabbit.ai -->\n{rng}"}
        pending = {"user": {"login": "coderabbitai[bot]"},
                   "body": marker + f"<!-- auto-generated comment: review in progress by coderabbit.ai -->\n{rng}"}
        self.assertEqual(count_pages(reviewed_filter(), [limited], [pending], once=True), 0)
        # A review someone asked for explicitly holds the gate while it runs.
        self.assertEqual(count_pages(pending_filter(), [limited], [pending]), 1)
        self.assertEqual(count_pages(pending_filter(), [limited]), 0)
        text = WORKFLOW.read_text()
        self.assertIn('[ "$REVIEW_ONCE" = "true" ] && [ "$reviewed" -gt 0 ]', text)
        self.assertIn('[ "$pending" -eq 0 ] || reviewed=0', text)

    def test_merge_condition_still_requires_a_reply(self) -> None:
        # The filters mean nothing if the exit condition stops consuming them (#288).
        self.assertIn(
            '[ "$reviewed" -gt 0 ] && [ "$unresolved" -eq 0 ] && [ "$unreplied" -eq 0 ]',
            WORKFLOW.read_text(),
        )

    def test_superseded_run_passes_at_once_and_head_run_still_waits(self) -> None:
        # modeldeck-private, 2026-11-01: runs for a commit pushed over within
        # minutes waited out the full window and failed, though the head's own
        # run gated the merge. Runs the shipped script against a stub gh.
        head = "a" * 40
        code, out = run_gate(stub_head="b" * 40, head=head)
        self.assertEqual(code, 0, out)
        self.assertIn("superseded", out)
        # Same head: no shortcut; with nothing reviewed it times out as before.
        code, out = run_gate(stub_head=head, head=head)
        self.assertEqual(code, 1)
        self.assertIn("not settled", out)

    def test_empty_page(self) -> None:
        self.assertEqual(run(self.unreplied, page()), 0)
        self.assertEqual(run(self.unresolved, page()), 0)


if __name__ == "__main__":
    unittest.main()

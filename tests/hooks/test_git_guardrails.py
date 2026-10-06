"""Tripwire for the git guardrail hook that the setup skill seeds (skills#301).

Every listed irreversible action must return the PreToolUse "ask" decision; ordinary
pushes, commits, PRs, and merges, and near-misses such as a branch named `force` or
`--force` inside a commit message, must produce no output at all. Tag pushes by bare
name are checked against a throwaway repository, so git must be on PATH (CI has it).
The settings command setup seeds is run through a shell with and without the script,
so a missing script can never turn into a block on every Bash call.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/orient/setup/scripts/git_guardrails.py"
SETUP = ROOT / "skills/orient/setup/SKILL.md"
spec = importlib.util.spec_from_file_location("git_guardrails", SCRIPT)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

ASKS = {
    guard.FORCE_PUSH: [
        "git push --force",
        "git push -f origin main",
        "git push origin main --force-with-lease",
        "git push --force-with-lease=main:abc123 origin main",
        "git push --force-if-includes --force-with-lease origin main",
        "git push -uf origin feature",
        "git push origin +main",
        "git push origin +HEAD:refs/heads/main",
    ],
    guard.MIRROR_PUSH: [
        "git push --mirror backup",
    ],
    guard.TAG_PUSH: [
        "git push --tags",
        "git push --tag",
        "git push origin --follow-tags",
        "git push origin refs/tags/v1.0.0",
        "git push origin tags/v1.7.2",
        "git push origin tag v1.0.0",
        "git push origin HEAD:refs/tags/v1.0.0",
        # A tag created earlier in the same command does not exist yet when the hook runs.
        "git tag -a v1.8.0 -m x && git push origin v1.8.0",
        "git tag -am 'Release notes' v1.8.0; git push origin main v1.8.0",
        "bash -c 'git tag v1.8.0 && git push origin v1.8.0'",
    ],
    guard.REMOTE_DELETE: [
        "git push origin --delete feature",
        "git push origin -d feature",
        "git push origin :feature",
        "git push --prune origin",
    ],
    guard.RELEASE: [
        "gh release create v1.0.0 --repo owner/repo --notes x",
        "gh release new v1.0.0",
        "gh release edit v1.0.0 --draft=false",
        "gh release delete v1.0.0 --yes",
        "gh release upload v1.0.0 dist.zip",
        "gh release delete-asset v1.0.0 dist.zip",
        "gh release --repo owner/repo create v1.0.0",
        "gh release -R owner/repo delete v1.0.0 --yes",
        "gh release --repo=owner/repo edit v1.0.0",
    ],
    guard.RESET_HARD: [
        "git reset --hard",
        "git reset --hard HEAD~1",
        "git reset HEAD~1 --hard",
    ],
    guard.CLEAN_FORCE: [
        "git clean -f",
        "git clean -fd",
        "git clean -xdf",
        "git clean --force -d",
    ],
    guard.BRANCH_FORCE_DELETE: [
        "git branch -D feature",
        "git branch --delete --force feature",
        "git branch -d -f feature",
        "git branch -df feature",
        "git branch --merged | grep -v main | xargs git branch -D",
    ],
}

# Chained commands, git's own options, wrappers, and nested shells still reach the push.
WRAPPED_FORCE_PUSHES = [
    "cd repo && git push --force",
    "git status; git push -f",
    "npm test || git push -f",
    "git fetch\ngit push --force origin main",
    "(cd repo && git push -f)",
    "git -C ../other push --force",
    "git -c push.default=current push -f",
    "git --no-pager push -f",
    "GIT_TRACE=1 git push --force",
    "env GIT_TRACE=1 git push --force",
    "sudo git push --force",
    "/usr/bin/git push --force",
    "if true; then git push -f; fi",
    "bash -c 'git push --force'",
    "bash -lc \"git push --force\"",
    "eval git push --force",
    "cat <<'EOF' > notes.txt\nhello\nEOF\ngit push --force",
    "timeout 60 git push --force",
    "nice -n 10 git push --force",
    "nohup git push --force",
    # Bash runs $(...) and backticks inside double quotes.
    'OUT="$(git push --force 2>&1)"',
    'echo "result: $(git push --force)"',
    'echo "`git push --force`"',
    "git commit -m \"$(cat <<'EOF'\nHandle the \"quoted case, don't break\nEOF\n)\" && git push --force-with-lease",
    'git push origin "$(git branch --show-current)" --force',
    # $((...)) is arithmetic, not a here-document that swallows the next line.
    "echo $((1<<3))\ngit push --force",
]

PASSES = [
    "git push",
    "git push origin main",
    "git push -u origin lane/301-git-guardrails",
    "git push origin HEAD",
    "git push origin HEAD:refs/heads/main",
    "git commit -m 'Add guardrail'",
    "git add -A && git commit -m wip && git push -u origin feature",
    "gh pr create --repo owner/repo --title t --body b",
    "gh pr merge 12 --repo owner/repo --squash --delete-branch",
    "git merge main",
    "git pull --rebase",
    "git fetch --prune",
    "gh release view v1.0.0",
    "gh release list",
    "gh release download v1.0.0",
    "git reset HEAD~1",
    "git reset --soft HEAD~1",
    "git clean -n",
    "git branch -d merged-feature",
    "git branch -f feature main",
    "git tag v1.0.0",
    "git status",
    "git checkout -b x && git push -u origin x",
    'git push origin "$(git branch --show-current)"',
    "git tag -d old && git push origin main",
    "git push origin :",
    "xargs -n1 echo < files.txt",
    "gh release --repo owner/repo view v1.0.0",
]

NEAR_MISSES = [
    "git push origin force",
    "git push -u origin force",
    "git checkout -b force",
    "git branch force",
    "git push origin feature/force-push-fix",
    "git commit -m 'Add a --force flag'",
    "git commit -m \"git push --force is now guarded\"",
    "git commit -m \"$(cat <<'EOF'\nDocument git push --force and git reset --hard\nEOF\n)\"",
    "git commit -F - <<'EOF'\ngit push --force\ngit branch -D old\nEOF",
    "echo git push --force",
    "echo \"git reset --hard\"",
    "grep -rn 'git clean -f' docs",
    "git log --grep=--force",
    "git push origin main # not --force",
    "git tag -m main v1.8.0 && git push origin main",
    "git commit -m \"$(cat <<'EOF'\nUse `git push --force` with care\nEOF\n)\"",
]


def scratch_dir(test):
    """A temporary directory removed when the test finishes."""
    tmp = tempfile.TemporaryDirectory()
    test.addCleanup(tmp.cleanup)
    return tmp.name


class MatcherTests(unittest.TestCase):
    def setUp(self):
        self.cwd = scratch_dir(self)

    def test_every_listed_action_asks(self):
        for reason, commands in ASKS.items():
            for command in commands:
                with self.subTest(command=command):
                    self.assertIn(reason, guard.check(command, self.cwd))

    def test_chained_and_wrapped_commands_ask(self):
        for command in WRAPPED_FORCE_PUSHES:
            with self.subTest(command=command):
                self.assertEqual([guard.FORCE_PUSH], guard.check(command, self.cwd))

    def test_ordinary_pushes_commits_prs_and_merges_pass(self):
        for command in PASSES:
            with self.subTest(command=command):
                self.assertEqual([], guard.check(command, self.cwd))

    def test_near_misses_pass(self):
        for command in NEAR_MISSES:
            with self.subTest(command=command):
                self.assertEqual([], guard.check(command, self.cwd))

    def test_every_action_in_a_chain_is_named_once(self):
        found = guard.check("git reset --hard && git push -f origin +main && git push --force origin main", self.cwd)
        self.assertEqual([guard.RESET_HARD, guard.FORCE_PUSH], found)


class TagLookupTests(unittest.TestCase):
    """A bare refspec is a tag push only when a local tag by that name exists."""

    def setUp(self):
        self.repo = scratch_dir(self)
        git = ["git", "-C", self.repo, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        subprocess.run(git + ["commit", "--allow-empty", "-qm", "fixture"], check=True)
        subprocess.run(git + ["tag", "v1.2.3"], check=True)
        subprocess.run(git + ["tag", "team-workflow/v1.7.2"], check=True)

    def test_pushing_an_existing_tag_by_name_asks(self):
        for command in ["git push origin v1.2.3", "git push origin team-workflow/v1.7.2",
                        "git push origin v1.2.3:v1.2.3"]:
            with self.subTest(command=command):
                self.assertEqual([guard.TAG_PUSH], guard.check(command, self.repo))

    def test_lookup_follows_cd_and_git_dash_c(self):
        elsewhere = scratch_dir(self)
        for command in [f"cd {self.repo} && git push origin v1.2.3", f"git -C {self.repo} push origin v1.2.3"]:
            with self.subTest(command=command):
                self.assertEqual([guard.TAG_PUSH], guard.check(command, elsewhere))

    def test_a_branch_or_unknown_name_passes(self):
        for command in ["git push origin main", "git push origin v9.9.9", "git push origin force"]:
            with self.subTest(command=command):
                self.assertEqual([], guard.check(command, self.repo))


class HookContractTests(unittest.TestCase):
    """The script as the harness runs it: hook JSON on stdin, decision JSON on stdout."""

    def run_hook(self, command):
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
                   "tool_input": {"command": command}, "cwd": scratch_dir(self)}
        return subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(payload),
                              capture_output=True, text=True)

    def test_listed_action_returns_the_ask_decision(self):
        result = self.run_hook("git push --force origin main")
        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual("PreToolUse", output["hookEventName"])
        self.assertEqual("ask", output["permissionDecision"])
        self.assertIn("force-push", output["permissionDecisionReason"])

    def test_ordinary_command_is_silent(self):
        result = self.run_hook("git push -u origin feature")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    def test_mirror_reason_names_the_remote_deletes(self):
        reason = json.loads(self.run_hook("git push --mirror backup").stdout)["hookSpecificOutput"]
        self.assertIn("deletes remote branches and tags missing locally", reason["permissionDecisionReason"])


class SeededCommandTests(unittest.TestCase):
    """The settings command setup seeds, run through a shell as the harness runs it.

    Claude Code treats exit code 2 from a PreToolUse hook as a block, and python3 exits 2
    when its script is missing, so a clone with the settings entry but not the script must
    get a silent no-op, never a refusal of every Bash call.
    """

    def seeded_command(self):
        found = set(re.findall(r"`([^`]*\$CLAUDE_PROJECT_DIR[^`]*)`", SETUP.read_text()))
        self.assertEqual(1, len(found), f"setup should name exactly one seeded command: {found}")
        command = found.pop()
        self.assertIn(command, SCRIPT.read_text(), "the script header names a different command than setup")
        return command

    def run_seeded(self, project):
        payload = json.dumps({"tool_input": {"command": "git push --force"}, "cwd": project})
        return subprocess.run(["sh", "-c", self.seeded_command()], input=payload, capture_output=True,
                              text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=project))

    def test_missing_script_is_a_silent_no_op(self):
        result = self.run_seeded(scratch_dir(self))
        self.assertNotEqual(2, result.returncode)
        self.assertEqual(("", ""), (result.stdout, result.stderr))

    def test_seeded_script_answers_ask(self):
        project = scratch_dir(self)
        (Path(project) / ".claude/hooks").mkdir(parents=True)
        shutil.copy(SCRIPT, Path(project) / ".claude/hooks/git_guardrails.py")
        result = self.run_seeded(project)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("ask", json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"])


if __name__ == "__main__":
    unittest.main()

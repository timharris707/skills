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


class TagListingFilterTests(unittest.TestCase):
    """A `git tag` carrying a listing filter lists tags and creates none, as in git (skills#309).

    Git reads any of the five filters, wherever it sits, as list mode, so the commit or
    branch named after one is never a new tag, and pushing it later in the line passes.
    """

    def setUp(self):
        self.cwd = scratch_dir(self)

    def assert_lists(self, option):
        for command in [f"git tag {option} main && git push origin main",
                        f"git tag {option}=main feature-x && git push origin feature-x",
                        f"git tag feature-x {option} main && git push origin feature-x"]:
            with self.subTest(command=command):
                self.assertEqual([], guard.check(command, self.cwd))

    def test_contains_lists(self):
        self.assert_lists("--contains")

    def test_no_contains_lists(self):
        self.assert_lists("--no-contains")

    def test_merged_lists(self):
        self.assert_lists("--merged")

    def test_no_merged_lists(self):
        self.assert_lists("--no-merged")

    def test_points_at_lists(self):
        self.assert_lists("--points-at")

    def test_creating_and_pushing_tags_still_asks(self):
        for command in ["git tag v9.9.9 && git push origin v9.9.9", "git push --tags", "git push --follow-tags"]:
            with self.subTest(command=command):
                self.assertEqual([guard.TAG_PUSH], guard.check(command, self.cwd))

    def test_a_mode_option_after_the_name_records_no_tag(self):
        for option in ["-d", "-n", "-l", "-v"]:
            command = f"git tag v1 {option} && git push origin v1"
            with self.subTest(command=command):
                self.assertEqual([], guard.check(command, self.cwd))


class TagOptionValueTests(unittest.TestCase):
    """An option's value is never read as the tag name or as a mode option, wherever it sits.

    Git creates v1 in each command below, so pushing v1 after it must ask.
    """

    def setUp(self):
        self.cwd = scratch_dir(self)

    def assert_asks(self, *commands):
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual([guard.TAG_PUSH], guard.check(command, self.cwd))

    def test_sort_value_is_skipped(self):
        self.assert_asks("git tag v1 --sort -version:refname && git push origin v1",
                         "git tag --sort refname v1 && git push origin v1")

    def test_format_value_is_skipped(self):
        self.assert_asks("git tag v1 --format -d && git push origin v1",
                         "git tag --format x v1 && git push origin v1")

    def test_other_value_options_skip_a_dash_led_value(self):
        self.assert_asks(*[f"git tag v1 {option} -d && git push origin v1" for option in
                           ["-m", "--message", "-F", "--file", "-u", "--local-user", "--trailer", "--cleanup"]])


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


class UnignoreExampleTests(unittest.TestCase):
    """Setup's un-ignore lines, applied in a repo that ignored .claude/ wholesale (skills#311).

    Both halves of the guardrail must be committable, the script and the settings file
    that runs it, while local-only settings stay ignored.
    """

    def unignore_lines(self):
        sentence = re.search(r"replace that line with (.+?), or stage", SETUP.read_text())
        self.assertIsNotNone(sentence, "setup should name the lines that replace a wholesale .claude/ ignore")
        return re.findall(r"`([^`]+)`", sentence[1])

    def check_ignore(self, repo, path):
        return subprocess.run(["git", "-C", repo, "check-ignore", "-q", path]).returncode

    def test_script_and_settings_are_tracked_and_local_settings_ignored(self):
        repo = scratch_dir(self)
        subprocess.run(["git", "init", "-q", repo], check=True)
        (Path(repo) / ".gitignore").write_text("\n".join(self.unignore_lines()) + "\n")
        for path in [".claude/hooks/git_guardrails.py", ".claude/settings.json", ".claude/settings.local.json"]:
            (Path(repo) / path).parent.mkdir(parents=True, exist_ok=True)
            (Path(repo) / path).write_text("{}\n")
        self.assertEqual(1, self.check_ignore(repo, ".claude/hooks/git_guardrails.py"))
        self.assertEqual(1, self.check_ignore(repo, ".claude/settings.json"))
        self.assertEqual(0, self.check_ignore(repo, ".claude/settings.local.json"))

    def test_proof_commands_check_the_settings_file(self):
        proof = re.search(r"Prove the wiring on the seeded copy: (.+?) so both will be committed\.", SETUP.read_text())
        self.assertIsNotNone(proof, "setup should carry the guardrail's proof-commands sentence")
        self.assertIn("`git check-ignore -q .claude/settings.json` each exit 1", proof[1])


if __name__ == "__main__":
    unittest.main()

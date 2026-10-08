"""Tripwire for the session-start handoff hook that the setup skill seeds (skills#320).

A session running in its own git worktree saves its handoff there, so the hook has to find
the newest `.claude/handoff.md` across the main checkout and every worktree, and say which
checkout it came from and when it was saved. The hook that read only the session's own
checkout replayed a stale note, or nothing, in exactly that setup.

The command is read from setup's reference and run through every installed shell against
throwaway repositories, so git must be on PATH (CI has it). This repo's own settings file
must carry the same entry.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "skills/orient/setup/references/handoff-hook.md"
SETTINGS = ROOT / ".claude/settings.json"
HANDOFF = ".claude/handoff.md"
ALL_SHELLS = ("sh", "bash", "dash", "zsh")
SHELLS = [shell for shell in ALL_SHELLS if shutil.which(shell)]
# Git variables from an enclosing hook or rebase would point the fixtures at the wrong repo.
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def seeded_entry():
    blocks = re.findall(r"```json\n(.*?)```", REFERENCE.read_text(), re.S)
    if len(blocks) != 1:
        raise AssertionError(f"setup's hook reference should hold exactly one JSON block, found {len(blocks)}")
    return json.loads(blocks[0])["hooks"]["SessionStart"]


def seeded_command():
    return seeded_entry()[0]["hooks"][0]["command"]


def event(source, indent=None):
    return json.dumps({"session_id": "fixture", "cwd": "/fixture", "hook_event_name": "SessionStart",
                       "source": source}, indent=indent)


# Startup and clear load the newest note anywhere; so does anything the hook cannot read.
STARTUP_LIKE = [event("startup"), event("clear"), event("fork"), "", "not json", "{}"]
# A resume or a compaction continues this session, so its own checkout's note comes first.
OWN_FIRST = [event("resume"), event("compact"), event("compact", indent=2)]


class SeededHandoffHookTests(unittest.TestCase):
    """A main checkout and two worktrees, as the desktop app leaves them."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # Resolved, because git names worktrees by their real path (macOS /var is a symlink).
        self.root = Path(tmp.name).resolve()
        self.main = self.root / "main"
        self.git = ["git", "-C", str(self.main), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]
        subprocess.run(["git", "init", "-q", str(self.main)], check=True, env=ENV)
        subprocess.run(self.git + ["commit", "--allow-empty", "-qm", "fixture"], check=True, env=ENV)
        self.a, self.b = self.add_worktree("a"), self.add_worktree("b")

    def add_worktree(self, name):
        path = self.root / name
        subprocess.run(self.git + ["worktree", "add", "-q", "--detach", str(path)], check=True, env=ENV)
        return path

    def save(self, checkout, text, hours_ago):
        path = checkout / HANDOFF
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        saved = time.time() - hours_ago * 3600
        os.utime(path, (saved, saved))
        return saved

    def run_hook(self, project, shell, env=None, stdin=None):
        # The harness sends the hook's input as JSON on stdin; `source` says why it fired.
        env = dict(ENV, CLAUDE_PROJECT_DIR=str(project), **(env or {}))
        stdin = event("startup") if stdin is None else stdin
        return subprocess.run([shell, "-c", seeded_command()], cwd=project, env=env, input=stdin,
                              capture_output=True, text=True)

    def assertLoaded(self, result, note, checkout, saved):
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn(note, result.stdout)
        header = [line for line in result.stdout.splitlines() if line.startswith("-----")]
        self.assertEqual(1, len(header), result.stdout)
        self.assertIn(f"from {checkout}, saved ", header[0])
        self.assertIn(time.strftime("%Y-%m-%d %H:%M", time.localtime(saved)), header[0])

    def assertEveryShellLoads(self, projects, note, checkout, saved, absent, env=None, stdins=(None,)):
        for shell in SHELLS:
            for project in projects:
                for stdin in stdins:
                    with self.subTest(shell=shell, project=project.name, stdin=stdin):
                        result = self.run_hook(project, shell, env, stdin)
                        self.assertLoaded(result, note, checkout, saved)
                        self.assertNotIn(absent, result.stdout)

    def test_newest_handoff_across_checkouts_is_loaded_and_named(self):
        self.save(self.main, "OLDER NOTE in the main checkout\n", hours_ago=2)
        saved = self.save(self.a, "NEWER NOTE in worktree a\n", hours_ago=1)
        self.assertEveryShellLoads([self.main, self.b], "NEWER NOTE in worktree a", self.a, saved, "OLDER NOTE")

    def test_a_copy_made_when_a_worktree_is_created_is_not_a_save(self):
        # The desktop app copies the main checkout's handoff into a new worktree with a fresh
        # modification time, so the copy looks newest without being anyone's save.
        self.save(self.main, "OLDER NOTE in the main checkout\n", hours_ago=2)
        saved = self.save(self.a, "NEWER NOTE in worktree a\n", hours_ago=1)
        self.save(self.b, "OLDER NOTE in the main checkout\n", hours_ago=0)
        self.assertEveryShellLoads([self.b], "NEWER NOTE in worktree a", self.a, saved, "OLDER NOTE")

    def test_a_resume_or_compaction_loads_its_own_checkout_first(self):
        # Two sessions in parallel: b saved first, then a saved. When b resumes or compacts it
        # gets its own note back, not its sibling's; at startup or after a clear, and for any
        # input the hook cannot read, the newest note anywhere still wins.
        own = self.save(self.b, "OWN NOTE saved by the session in b\n", hours_ago=2)
        newest = self.save(self.a, "SIBLING NOTE saved later in a\n", hours_ago=1)
        self.assertEveryShellLoads([self.b], "OWN NOTE saved by the session in b", self.b, own, "SIBLING NOTE",
                                   stdins=OWN_FIRST)
        self.assertEveryShellLoads([self.b], "SIBLING NOTE saved later in a", self.a, newest, "OWN NOTE",
                                   stdins=STARTUP_LIKE)

    def test_a_resume_or_compaction_without_an_own_note_loads_the_newest(self):
        # Neither no note at all nor the copy a worktree receives at creation is this
        # session's save, so both fall back to the newest note anywhere.
        self.save(self.main, "OLDER NOTE in the main checkout\n", hours_ago=2)
        newest = self.save(self.a, "NEWER NOTE in worktree a\n", hours_ago=1)
        self.assertEveryShellLoads([self.b], "NEWER NOTE in worktree a", self.a, newest, "OLDER NOTE",
                                   stdins=OWN_FIRST)
        self.save(self.b, "OLDER NOTE in the main checkout\n", hours_ago=0)
        self.assertEveryShellLoads([self.b], "NEWER NOTE in worktree a", self.a, newest, "OLDER NOTE",
                                   stdins=OWN_FIRST)

    def assertBranchHandoffSkipped(self, committed, link=None, env=None):
        # A branch that commits a handoff, checked out in a review worktree, must not reach
        # every session, even when it is the newest file.
        saved = self.save(self.main, "OWN NOTE in the main checkout\n", hours_ago=2)
        path = self.a / committed
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("INJECTED NOTE committed on a branch\n")
        if link:
            os.symlink(link[1], self.a / link[0])
        a = ["git", "-C", str(self.a), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]
        subprocess.run(a + ["add", "-A", "-f"], check=True, env=ENV)
        subprocess.run(a + ["commit", "-qm", "commit a handoff"], check=True, env=ENV)
        self.assertEveryShellLoads([self.main, self.b], "OWN NOTE in the main checkout", self.main, saved,
                                   "INJECTED NOTE", env=env)

    def test_a_handoff_git_tracks_is_skipped(self):
        self.assertBranchHandoffSkipped(HANDOFF)

    def test_a_handoff_git_tracks_is_skipped_with_literal_pathspecs(self):
        self.assertBranchHandoffSkipped(HANDOFF, env={"GIT_LITERAL_PATHSPECS": "1"})

    # The case and Unicode variants reach the hook only on a case-insensitive disk, such as macOS's.
    def test_a_tracked_handoff_named_in_another_case_is_skipped(self):
        self.assertBranchHandoffSkipped(".claude/Handoff.md")

    def test_a_tracked_handoff_in_a_folder_named_in_another_case_is_skipped(self):
        self.assertBranchHandoffSkipped(".Claude/handoff.md")

    def test_a_tracked_handoff_spelled_with_a_ligature_is_skipped(self):
        self.assertBranchHandoffSkipped(".claude/handoﬀ.md")

    def test_a_handoff_behind_a_committed_folder_symlink_is_skipped(self):
        self.assertBranchHandoffSkipped("docs/handoff.md", link=(".claude", "docs"))

    def test_a_tracked_name_in_another_case_leaves_the_note_on_a_case_sensitive_disk(self):
        # There, a tracked `.claude/Handoff.md` is another file, and the untracked
        # `.claude/handoff.md` beside it is still a save. core.ignorecase=false stands in
        # for that disk; the index entry needs no file.
        subprocess.run(self.git + ["config", "core.ignorecase", "false"], check=True, env=ENV)
        blob = subprocess.run(self.git + ["hash-object", "-w", "--stdin"], input="TRACKED\n", capture_output=True,
                              text=True, check=True, env=ENV).stdout.strip()
        subprocess.run(self.git + ["update-index", "--add", "--cacheinfo", f"100644,{blob},.claude/Handoff.md"],
                       check=True, env=ENV)
        subprocess.run(self.git + ["commit", "-qm", "track another case"], check=True, env=ENV)
        saved = self.save(self.main, "OWN NOTE in the main checkout\n", hours_ago=1)
        self.assertEveryShellLoads([self.main, self.b], "OWN NOTE in the main checkout", self.main, saved, "TRACKED")

    def test_an_untracked_name_in_another_case_beside_the_note_leaves_it_loaded(self):
        # On a case-sensitive disk, an untracked `.claude/Handoff.md` can sit beside the note,
        # and git lists both. A case-insensitive disk cannot hold both files, so a git wrapper
        # adds the other name ahead of the real listing, where git's sort order puts it.
        saved = self.save(self.main, "OWN NOTE in the main checkout\n", hours_ago=1)
        wrapper = self.root / "listing-bin"
        wrapper.mkdir()
        (wrapper / "git").write_text('#!/bin/sh\ncase " $* " in *" ls-files -o "*) echo .claude/Handoff.md;; esac\n'
                                     f'exec "{shutil.which("git")}" "$@"\n')
        (wrapper / "git").chmod(0o755)
        path = {"PATH": f"{wrapper}{os.pathsep}{ENV['PATH']}"}
        self.assertEveryShellLoads([self.main, self.b], "OWN NOTE in the main checkout", self.main, saved,
                                   "Handoff.md", env=path)

    def test_unusual_worktree_paths_parse_safely(self):
        # A trailing space survives parsing; a newline in a path cannot forge another checkout.
        if subprocess.run(self.git + ["worktree", "list", "--porcelain", "-z"], capture_output=True,
                          env=ENV).returncode:
            self.skipTest("this git has no `worktree list -z` (before 2.36), so a newline in a path is ambiguous")
        trailing = self.add_worktree("trailing ")
        self.add_worktree(f"forged\nworktree {self.root / 'decoy'}")
        self.save(self.root / "decoy", "DECOY NOTE outside every checkout\n", hours_ago=0)
        saved = self.save(trailing, "NEWER NOTE in a path ending in a space\n", hours_ago=1)
        self.assertEveryShellLoads([self.main], "NEWER NOTE in a path ending in a space", trailing, saved,
                                   "DECOY NOTE")

    def test_without_git_the_own_checkout_is_read(self):
        self.save(self.a, "NEWER NOTE in worktree a\n", hours_ago=1)
        saved = self.save(self.b, "OWN NOTE in worktree b\n", hours_ago=2)
        stub = self.root / "bin"
        stub.mkdir()
        (stub / "git").write_text("#!/bin/sh\nexit 127\n")
        (stub / "git").chmod(0o755)
        path = {"PATH": f"{stub}{os.pathsep}{ENV['PATH']}"}
        self.assertEveryShellLoads([self.b], "OWN NOTE in worktree b", self.b, saved, "NEWER NOTE", env=path,
                                   stdins=STARTUP_LIKE + OWN_FIRST)

    def test_outside_a_git_repo_the_own_checkout_is_read(self):
        plain = self.root / "plain"
        saved = self.save(plain, "PLAIN NOTE outside any repo\n", hours_ago=1)
        self.assertEveryShellLoads([plain], "PLAIN NOTE outside any repo", plain, saved, "across the main checkout",
                                   stdins=STARTUP_LIKE + OWN_FIRST)

    def test_no_handoff_anywhere_is_silent(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                result = self.run_hook(self.b, shell)
                self.assertEqual((0, ""), (result.returncode, result.stdout), result.stderr)

    def test_git_runs_a_few_times_per_handoff_not_per_worktree(self):
        # Many worktrees, several handoffs: git runs for the listing and twice for each handoff
        # found (one hash, one untracked check), never once per worktree or once per pair of
        # handoffs. Without the existence check before hashing, git ran once per worktree, and
        # 150 worktrees took seconds; hashing every older handoff for each one grew with the
        # square of their number.
        for i in range(18):
            self.add_worktree(f"w{i}")
        handoffs = 6
        for i in range(handoffs):
            saved = self.save(self.root / f"w{i}", f"NOTE {i} in w{i}\n", hours_ago=handoffs - i)
        newest = self.root / f"w{handoffs - 1}"
        wrapper = self.root / "counting-bin"
        wrapper.mkdir()
        (wrapper / "git").write_text(f'#!/bin/sh\nprintf x >> "$HOOK_GIT_LOG"\nexec "{shutil.which("git")}" "$@"\n')
        (wrapper / "git").chmod(0o755)
        bound = 2 + 2 * handoffs
        for shell in SHELLS:
            with self.subTest(shell=shell):
                log = self.root / f"git-calls-{shell}"
                log.write_text("")
                env = {"PATH": f"{wrapper}{os.pathsep}{ENV['PATH']}", "HOOK_GIT_LOG": str(log)}
                self.assertLoaded(self.run_hook(self.main, shell, env), f"NOTE {handoffs - 1} in", newest, saved)
                calls = len(log.read_text())
                self.assertLessEqual(calls, bound, f"git ran {calls} times for 20 worktrees and {handoffs} handoffs")

    def test_every_shell_the_hook_targets_is_installed(self):
        missing = [shell for shell in ALL_SHELLS if shell not in SHELLS]
        if missing:
            self.skipTest(f"not installed, so the hook was not run under: {', '.join(missing)}")


class RepoSettingsTests(unittest.TestCase):
    def test_this_repo_carries_the_seeded_hook(self):
        settings = json.loads(SETTINGS.read_text())
        self.assertEqual(seeded_entry(), settings["hooks"]["SessionStart"])


if __name__ == "__main__":
    unittest.main()

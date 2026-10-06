"""Tests for trim_sessions.py: what a trimmed log keeps, drops, and redacts.

Fixtures are small synthetic logs in both formats (Claude Code, and Codex in its
current and older shapes), never real sessions. Secret-shaped values are built at
runtime and substituted for placeholders, so no secret-shaped string is committed.

Run:  python3 -m unittest discover -s tests -t tests
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import trim_sessions as ts  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Built at runtime so the repo never holds a string a secret scanner would flag.
GH_TOKEN = "gh" + "p_" + "A1b2C3d4" * 5
BEARER = "abc123" * 4
DB_PASSWORD = "s3cr3t-" + "pass" * 3
SECRETS = {"__GH_TOKEN__": GH_TOKEN, "__BEARER__": BEARER, "__DB_PASSWORD__": DB_PASSWORD}


def materialize(fixture: str, dest: Path, cwd: str) -> Path:
    """Copy a fixture to dest with the working directory and secrets filled in."""
    text = (FIXTURES / fixture).read_text(encoding="utf-8")
    for placeholder, value in {**SECRETS, "__CWD__": cwd}.items():
        text = text.replace(placeholder, json.dumps(value)[1:-1])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


def subagent_log(path: Path, cwd: str, errors: int) -> Path:
    """A subagent transcript (all sidechain) whose first `errors` commands fail."""
    rows = [{"type": "user", "isSidechain": True, "cwd": cwd, "timestamp": "2026-10-01T09:05:00.000Z",
             "message": {"role": "user", "content": "Run the tests."}}]
    for i in range(errors):
        rows.append({"type": "assistant", "isSidechain": True, "message": {"content": [
            {"type": "tool_use", "id": f"s{i}", "name": "Bash", "input": {"command": f"make test-{i}"}}]}})
        rows.append({"type": "user", "isSidechain": True, "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"s{i}", "is_error": True, "content": "Exit code 2"}]}})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


class TempCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.repo = str(self.base / "repo")
        os.makedirs(self.repo)
        # The default log folders point into the temp folder, so no test reads real logs.
        self.claude = self.base / "claude-config"
        self.codex = self.base / "codex-home"
        env = mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": str(self.claude), "CODEX_HOME": str(self.codex)})
        env.start()
        self.addCleanup(env.stop)

    def run_main(self, *args) -> int:
        with contextlib.redirect_stdout(io.StringIO()):
            return ts.main(list(args))


class TestRedaction(unittest.TestCase):
    def test_each_secret_family_is_replaced(self):
        samples = [
            GH_TOKEN,
            "github" + "_pat_" + "Z9" * 15,
            "sk" + "-proj-" + "q" * 30,
            "sk" + "_live_" + "x" * 20,
            "AK" + "IA" + "ABCDEFGHIJKLMNOP",
            "AI" + "za" + "b" * 35,
            "xo" + "xb-" + "1234567890-abc",
            "np" + "m_" + "c" * 36,
            "ey" + "J" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12,
        ]
        for secret in samples:
            with self.subTest(secret=secret[:6]):
                out = ts.redact(f"before {secret} after")
                self.assertNotIn(secret, out)
                self.assertIn(ts.REDACTED, out)
                self.assertTrue(out.startswith("before ") and out.endswith(" after"))

    def test_named_values_keep_the_name(self):
        out = ts.redact(f'export API_KEY={DB_PASSWORD} and "client_secret": "{DB_PASSWORD}"')
        self.assertNotIn(DB_PASSWORD, out)
        self.assertIn("API_KEY=" + ts.REDACTED, out)
        self.assertIn('"client_secret": ' + ts.REDACTED, out)

    def test_bearer_url_password_and_private_key(self):
        key = "-----BEGIN RSA PRIVATE" + " KEY-----\nMIIabc\n-----END RSA PRIVATE" + " KEY-----"
        text = f"Authorization: Bearer {BEARER}\npostgres://app:{DB_PASSWORD}@db.local/x\n{key}"
        out = ts.redact(text)
        for secret in (BEARER, DB_PASSWORD, "MIIabc"):
            self.assertNotIn(secret, out)
        self.assertIn("postgres://app:" + ts.REDACTED + "@db.local/x", out)

    def test_a_private_key_cut_off_before_its_end_is_still_redacted(self):
        out = ts.redact("key:\n-----BEGIN OPENSSH PRIVATE" + " KEY-----\nb3BlbnNzaC1rZXk")
        self.assertNotIn("b3BlbnNzaC1rZXk", out)

    def test_huge_text_is_excerpted_fast_with_both_ends_redacted(self):
        text = f"start {GH_TOKEN} " + "a.b-" * 500_000 + f" end TOKEN={DB_PASSWORD}"
        began = time.monotonic()
        out = ts.excerpt(text, 600)
        self.assertLess(time.monotonic() - began, 2)
        self.assertLess(len(out), 700)
        self.assertNotIn(GH_TOKEN, out)
        self.assertNotIn(DB_PASSWORD, out)
        self.assertIn("chars trimmed", out)

    def test_command_line_header_and_config_secrets(self):
        b64 = "dXNlcjpw" + "YXNzd29yZA=="
        cases = [  # (text, the secret, what stays around it)
            (f"mysql -h db -u root -p{DB_PASSWORD} app", DB_PASSWORD, "-u root -p" + ts.REDACTED + " app"),
            (f"mysqldump -uroot -p'{DB_PASSWORD}' app", DB_PASSWORD, "-p" + ts.REDACTED + " app"),
            (f"deploy --password {DB_PASSWORD} --user admin", DB_PASSWORD, "--password " + ts.REDACTED + " --user"),
            (f"curl -u admin:{DB_PASSWORD} https://api.local/x", DB_PASSWORD, "-u admin:" + ts.REDACTED + " https"),
            (f"curl --user=admin:{DB_PASSWORD} x", DB_PASSWORD, "--user=admin:" + ts.REDACTED),
            (f'-H "Authorization: Basic {b64}"', b64, "Basic " + ts.REDACTED + '"'),
            ("-----BEGIN PGP PRIVATE" + " KEY BLOCK-----\n\nlQOYBF\n-----END PGP PRIVATE" + " KEY BLOCK-----\nafter",
             "lQOYBF", ts.REDACTED + "\nafter"),
            (f"postgres://app:{DB_PASSWORD}@x@db.local/app", DB_PASSWORD + "@x",
             "postgres://app:" + ts.REDACTED + "@db.local/app"),
            (f"APP_KEY=base64:{b64}", b64, "APP_KEY=" + ts.REDACTED),
            (f"DB_PASS={DB_PASSWORD} MYSQL_PWD={DB_PASSWORD}", DB_PASSWORD,
             "DB_PASS=" + ts.REDACTED + " MYSQL_PWD=" + ts.REDACTED),
        ]
        for text, secret, kept in cases:
            with self.subTest(text=text[:12]):
                out = ts.redact(text)
                self.assertNotIn(secret, out)
                self.assertIn(kept, out)
                self.assertEqual(ts.redact(out), out)

    def test_vendor_token_shapes_are_replaced(self):
        fake = "FAKE" * 9  # prefixes are split below so no secret scanner flags this file
        for secret in [
            "gl" + "pat-" + fake,
            "h" + "f_" + fake,
            "S" + "G." + "A" * 22 + "." + "B" * 43,
            "y" + "a29." + fake,
            "https://hooks." + "slack.com/services/T0FAKE000/B0FAKE000/" + "F" * 24,
            "xa" + "pp-1-A0FAKE000-1234567890123-" + "ab" * 16,
            "whs" + "ec_" + fake,
        ]:
            with self.subTest(secret=secret[:8]):
                out = ts.redact(f"before {secret} after")
                self.assertEqual(out, f"before {ts.REDACTED} after")

    def test_azure_keys_flag_values_and_empty_user_urls(self):
        azure_key = "RkFL" * 16 + "=="
        cases = [  # (text, the secret, what stays around it)
            (f"AccountName=acct;AccountKey={azure_key};EndpointSuffix=x", azure_key,
             "AccountKey=" + ts.REDACTED + ";EndpointSuffix=x"),
            (f"tool --api-key {DB_PASSWORD} go", DB_PASSWORD, "--api-key " + ts.REDACTED + " go"),
            (f"tool --api-key={DB_PASSWORD} go", DB_PASSWORD, "--api-key=" + ts.REDACTED + " go"),
            (f"gh auth login --with-token {DB_PASSWORD}", DB_PASSWORD, "--with-token " + ts.REDACTED),
            (f"tool --client-secret '{DB_PASSWORD}' go", DB_PASSWORD, "--client-secret " + ts.REDACTED + " go"),
            (f"redis://:{DB_PASSWORD}@cache.local:6379/0", DB_PASSWORD,
             "redis://:" + ts.REDACTED + "@cache.local:6379/0"),
        ]
        for text, secret, kept in cases:
            with self.subTest(text=text[:16]):
                out = ts.redact(text)
                self.assertNotIn(secret, out)
                self.assertIn(kept, out)
                self.assertEqual(ts.redact(out), out)

    def test_prose_that_resembles_the_new_shapes_is_untouched(self):
        for text in [
            "the SG.1 release shipped; SG. is SendGrid's key prefix",
            "the --api-key flag is documented; pass --with-token <your token> or --api-key $API_KEY",
            "set --max-tokens 100000000 and --token-file ./t.txt, not --secret-store",
            "glpat- and hf_ and ya29. and xapp- and whsec_ are token prefixes; AccountKey= is a field name",
            "see https://hooks.slack.com/services/ for setup; redis://:6379 and http://:8080/x@y",
        ]:
            with self.subTest(text=text[:20]):
                self.assertEqual(ts.redact(text), text)

    def test_ordinary_text_is_untouched_and_redaction_is_idempotent(self):
        for text in [
            "commit 3f2a9c1d4e5b6a7f8091a2b3c4d5e6f708192a3b; the token budget ran out; max_tokens=64",
            "mkdir -pv build && cp -pr a b && ssh -p2222 host",
            "docker run -u 1000:1000 -p 8080:80 app; git push -u origin main",
            "ffuf -u https://target.local/FUZZ; open http://localhost:5173/@vite/client",
            "docker login --password-stdin; first_pass=True; basic auth works",
        ]:
            self.assertEqual(ts.redact(text), text)
        once = ts.redact(f"TOKEN={DB_PASSWORD}")
        self.assertEqual(ts.redact(once), once)


class TestClaudeLog(TempCase):
    def setUp(self):
        super().setUp()
        path = materialize("claude-session.jsonl", self.base / "c.jsonl", self.repo)
        self.s = ts.parse(path)
        self.kinds = [e[2] for e in self.s.events]

    def test_keeps_the_human_messages_and_only_those(self):
        humans = [e[3] for e in self.s.events if e[2] == "HUMAN"]
        self.assertEqual(len(humans), 4)
        self.assertEqual(humans[0], "Fix the failing login test, then open a PR.")
        self.assertEqual(humans[3], "/retro last week")
        for marker in ("META-MARKER", "NOTIFY-MARKER", "REMINDER-MARKER", "SUMMARY-MARKER",
                       "LOCAL-MARKER", "SIDECHAIN-MARKER", "PEER-MARKER", "ASSISTANT-PROSE-MARKER",
                       "THINKING-MARKER"):
            self.assertNotIn(marker, self.s.trimmed, marker)

    def test_tool_errors_name_the_call(self):
        errors = [e[3] for e in self.s.events if e[2] == "ERROR"]
        self.assertEqual(len(errors), 3)
        self.assertTrue(errors[0].startswith("Bash: npm test -- login => Exit code 1"))
        self.assertIn("Could not resolve host", errors[2])

    def test_interruption_and_compaction_counted_once_each(self):
        self.assertEqual(self.kinds.count("INTERRUPTED"), 1)
        self.assertEqual(self.kinds.count("COMPACTED"), 1)
        self.assertIn("COMPACTED: auto", self.s.trimmed)

    def test_repeated_command_with_its_failures(self):
        self.assertEqual(self.s.repeats(), [("Bash: npm test -- login", [3, 2])])
        self.assertIn("- 3x, 2 failed: Bash: npm test -- login", self.s.trimmed)
        self.assertEqual(self.s.score(), 3 + 2 * 1 + 2 * 1 + 2)

    def test_line_numbers_point_into_the_raw_log(self):
        self.assertIn("L2 09:00 HUMAN: Fix the failing login test", self.s.trimmed)
        raw = (self.base / "c.jsonl").read_text().splitlines()
        self.assertIn('"tool_use_id":"t1"', raw[5])
        self.assertIn("L6 09:01 ERROR", self.s.trimmed)

    def test_secrets_never_reach_the_trimmed_log(self):
        for secret in SECRETS.values():
            self.assertNotIn(secret, self.s.trimmed)
        self.assertIn("staging token " + ts.REDACTED, self.s.trimmed)
        self.assertIn("Bearer " + ts.REDACTED, self.s.trimmed)

    def test_text_riding_in_a_tool_result_entry_is_not_the_human(self):
        path = self.base / "r.jsonl"
        path.write_text(json.dumps({"type": "user", "cwd": self.repo, "message": {"content": [
            {"type": "tool_result", "tool_use_id": "z", "content": "ok"},
            {"type": "text", "text": "HOOK-FEEDBACK-MARKER"}]}}) + "\n")
        self.assertEqual(ts.parse(path).events, [])

    def test_a_subagent_transcript_keeps_its_prompt(self):
        path = self.base / "agent-1.jsonl"
        path.write_text(json.dumps({"type": "user", "isSidechain": True, "cwd": self.repo,
                                    "message": {"role": "user", "content": "Review the diff."}}) + "\n")
        s = ts.parse(path)
        self.assertEqual([e[2:] for e in s.events], [("PROMPT", "Review the diff.")])

    def test_a_lone_surrogate_in_a_log_is_written_not_fatal(self):
        path = self.base / "u.jsonl"
        path.write_text(json.dumps({"type": "user", "cwd": self.repo, "timestamp": "2026-10-01T09:00:00.000Z",
                                    "message": {"content": "half an emoji \ud83d here"}}) + "\n")
        out = self.base / "out"
        self.assertEqual(self.run_main("--session", str(path), "--out", str(out)), 0)
        (written,) = out.iterdir()
        self.assertIn("half an emoji ? here", written.read_text(encoding="utf-8"))


class TestSubagents(TempCase):
    """A subagent's transcript folds into its parent session."""

    def setUp(self):
        super().setUp()
        folder = self.claude / "projects" / ts.slug(self.repo)
        self.parent = folder / "p1.jsonl"
        folder.mkdir(parents=True)
        self.parent.write_text(json.dumps({"type": "user", "cwd": self.repo, "timestamp": "2026-10-01T09:00:00.000Z",
                                           "message": {"content": "Run the tests in a helper."}}) + "\n")
        self.sub = subagent_log(folder / "p1" / "subagents" / "agent-a1b2c3.jsonl", self.repo, 2)

    def test_found_with_its_parent_not_as_a_sample_entry(self):
        roots = {os.path.normpath(self.repo), os.path.realpath(self.repo)}
        self.assertEqual(ts.find_recent(roots, [self.claude], [], 14, time.time()), [self.parent])

    def test_its_signal_and_roughness_count_for_the_parent(self):
        s = ts.parse(self.parent)
        self.assertEqual([sub.path for sub in s.subagents], [self.sub])
        self.assertEqual(s.score(), 2)
        self.assertEqual(s.raw_total(), self.parent.stat().st_size + self.sub.stat().st_size)
        self.assertIn("# claude subagent agent-a1b2c3 of session p1", s.trimmed)
        self.assertIn("L1 09:05 PROMPT: Run the tests.", s.trimmed)
        self.assertIn("ERROR: Bash: make test-1 => Exit code 2", s.trimmed)


class TestCodexLog(TempCase):
    def test_current_format(self):
        s = ts.parse(materialize("codex-session.jsonl", self.base / "s" / "rollout-x.jsonl", self.repo))
        kinds = [e[2] for e in s.events]
        humans = [e[3] for e in s.events if e[2] == "HUMAN"]
        self.assertEqual(s.id, "0199aaaa-0000-7000-8000-000000000002")
        self.assertEqual(s.cwd, self.repo)
        self.assertEqual(humans[0], "Run the migration and tell me if it worked.")
        self.assertEqual(len(humans), 2)
        self.assertIn("[image]", humans[1])
        self.assertEqual(kinds.count("ERROR"), 3)
        self.assertEqual(kinds.count("INTERRUPTED"), 1)
        self.assertEqual(kinds.count("COMPACTED"), 1)
        self.assertIn("shell: make migrate => exit 2: migrate: connection refused", s.trimmed)
        self.assertIn("tracker.get_issue", s.trimmed)
        self.assertEqual(s.repeats(), [("shell: make migrate", [3, 2])])
        self.assertEqual(s.score(), 3 + 2 + 2 + 2)
        self.assertNotIn(DB_PASSWORD, s.trimmed)
        self.assertIn("DATABASE_PASSWORD=" + ts.REDACTED, s.trimmed)
        for marker in ("INJECTED-MARKER", "ENV-MARKER", "ASSISTANT-PROSE-MARKER", "SUMMARY-MARKER",
                       "REASONING-MARKER", "FINAL-MARKER"):
            self.assertNotIn(marker, s.trimmed, marker)

    def test_older_format(self):
        s = ts.parse(materialize("codex-older-session.jsonl", self.base / "s" / "rollout-y.jsonl", self.repo))
        kinds = [e[2] for e in s.events]
        self.assertEqual([e[3] for e in s.events if e[2] == "HUMAN"], ["Bump the version and push."])
        self.assertEqual(kinds.count("ERROR"), 2)
        self.assertIn("shell: git push origin main => exit 1:", s.trimmed)
        self.assertIn("shell: npm run build => exit 2: error TS2304", s.trimmed)
        self.assertNotIn("git status", s.trimmed)
        self.assertEqual(kinds.count("INTERRUPTED"), 1)
        self.assertEqual(kinds.count("COMPACTED"), 1)
        self.assertNotIn("INJECTED-MARKER", s.trimmed)


class TestFinding(TempCase):
    """Which logs belong to the repo, and which make the sample."""

    def setUp(self):
        super().setUp()
        projects = self.claude / "projects"
        worktree = os.path.join(self.repo, ".claude", "worktrees", "lane-1")
        other = self.repo + "-old"
        self.in_root = materialize("claude-session.jsonl", projects / ts.slug(self.repo) / "a1.jsonl", self.repo)
        self.in_tree = projects / ts.slug(worktree) / "a2.jsonl"
        self.in_tree.parent.mkdir(parents=True)
        self.in_tree.write_text(json.dumps({"type": "user", "cwd": worktree, "message": {"content": "hi"}}) + "\n")
        self.other_repo = materialize("claude-session.jsonl", projects / ts.slug(other) / "a3.jsonl", other)
        self.too_old = materialize("claude-session.jsonl", projects / ts.slug(self.repo) / "a4.jsonl", self.repo)
        old = time.time() - 60 * 86400
        os.utime(self.too_old, (old, old))
        day = self.codex / "sessions" / "2026" / "10" / "02"
        self.codex_in = materialize("codex-session.jsonl", day / "rollout-2026-10-02T14-00-00-0199aaaa.jsonl",
                                    worktree)
        self.codex_out = materialize("codex-older-session.jsonl", day / "rollout-2026-10-02T15-00-00-0198bbbb.jsonl",
                                     "/somewhere/else")

    def test_recent_logs_in_the_repo_and_its_worktrees_only(self):
        roots = {os.path.normpath(self.repo), os.path.realpath(self.repo)}
        found = ts.find_recent(roots, [self.claude], [self.codex], 14, time.time())
        self.assertEqual(sorted(found), sorted([self.in_root, self.in_tree, self.codex_in]))

    def test_a_flagged_folder_adds_to_the_default_once(self):
        self.assertEqual(ts.config_dirs([], "CLAUDE_CONFIG_DIR", ".claude"), [self.claude])
        self.assertEqual(ts.config_dirs(["/x", str(self.claude), "/x"], "CLAUDE_CONFIG_DIR", ".claude"),
                         [self.claude, Path("/x")])
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(Path, "home", return_value=Path("/h")):
                self.assertEqual(ts.config_dirs(["/x"], "CODEX_HOME", ".codex"), [Path("/h/.codex"), Path("/x")])

    def test_sessions_in_the_default_and_a_flagged_folder_are_both_found(self):
        extra = self.base / "extra-config"
        in_extra = materialize("claude-session.jsonl", extra / "projects" / ts.slug(self.repo) / "b1.jsonl", self.repo)
        roots = {os.path.normpath(self.repo), os.path.realpath(self.repo)}
        claude_dirs = ts.config_dirs([str(extra)], "CLAUDE_CONFIG_DIR", ".claude")
        found = ts.find_recent(roots, claude_dirs, [self.codex], 14, time.time())
        self.assertEqual(sorted(found), sorted([self.in_root, self.in_tree, in_extra, self.codex_in]))

    def test_sessions_sharing_an_id_prefix_get_their_own_files(self):
        second = self.codex_in.with_name("rollout-2026-10-02T14-00-30-0199aaaa.jsonl")
        second.write_text(self.codex_in.read_text().replace("0199aaaa-0000-7000", "0199aaaa-1111-7000"))
        subs = [subagent_log(self.base / p / "subagents" / "agent-a1b2c3.jsonl", self.repo, 1) for p in ("p1", "p2")]
        out = self.base / "out"
        paths = [self.codex_in, second] + subs
        self.assertEqual(self.run_main(*[a for p in paths for a in ("--session", str(p))], "--out", str(out)), 0)
        names = sorted(f.name for f in out.iterdir())
        self.assertEqual(len(names), 4)
        self.assertIn("codex-2026-10-02-0199aaaa-1111-7000-8000-000000000002.md", names)
        self.assertIn("claude-2026-10-01-p2-agent-a1b2c3.md", names)

    def test_named_sessions_by_id_prefix_or_path(self):
        found = ts.find_named(["a3", "0199aaaa", str(self.too_old)], [self.claude], [self.codex])
        self.assertEqual(found, [self.other_repo, self.codex_in, self.too_old])
        with self.assertRaises(SystemExit):
            ts.find_named(["a"], [self.claude], [self.codex])

    @unittest.skipUnless(subprocess.run(["git", "--version"], capture_output=True).returncode == 0, "needs git")
    def test_cli_samples_roughest_first_and_reports_sizes(self):
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        out = self.base / "out"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = ts.main(["--repo", self.repo, "--claude-dir", str(self.claude),
                            "--codex-home", str(self.codex), "--limit", "2", "--out", str(out)])
        self.assertEqual(code, 0)
        report = stdout.getvalue().splitlines()
        self.assertTrue(report[0].startswith("2 of 3 sessions from the last 30 days"))
        rows = [r for r in report if r.startswith(("claude", "codex"))]
        self.assertEqual(len(rows), 2)
        self.assertEqual([r.split()[-2] for r in rows], ["9", "9"])  # the plain "hi" log scores 0
        self.assertTrue(report[-1].startswith("TOTAL"))
        files = sorted(out.iterdir())
        self.assertEqual(len(files), 2)
        for f in files:
            text = f.read_text()
            for secret in SECRETS.values():
                self.assertNotIn(secret, text)
        raw = sum(p.stat().st_size for p in (self.in_root, self.codex_in))
        self.assertLess(sum(f.stat().st_size for f in files), raw)

    def test_every_git_call_has_a_timeout_and_a_hang_ends_the_run_with_a_message(self):
        done = subprocess.CompletedProcess([], 1, "", "")
        with mock.patch.object(ts.subprocess, "run", return_value=done) as run:
            ts.repo_roots(self.repo)
        self.assertEqual(run.call_count, 2)
        self.assertTrue(all(call.kwargs.get("timeout") == ts.GIT_TIMEOUT for call in run.call_args_list))
        hang = subprocess.TimeoutExpired(["git"], ts.GIT_TIMEOUT)
        with mock.patch.object(ts.subprocess, "run", side_effect=hang):
            with self.assertRaises(SystemExit) as stopped:
                ts.main(["--repo", self.repo, "--out", str(self.base / "o")])
        self.assertIn("did not finish", str(stopped.exception.code))
        self.assertIn(self.repo, str(stopped.exception.code))

    def test_cli_exits_1_when_nothing_matches(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code = ts.main(["--repo", str(self.base / "empty"), "--claude-dir", str(self.claude),
                            "--codex-home", str(self.codex), "--out", str(self.base / "o")])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

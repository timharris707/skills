"""Tripwire for show-me-your-work's log helper, `scripts/log.sh` (skills#283).

Before it appends, the helper adds a missing final newline so a new row never joins onto
the log's last line. When that last line was a row cut short mid-write, the newline left
the broken row in the log looking finished. The helper now stops with an error naming
that line when it has fewer than six fields or an empty last field (the helper never
writes one), and still heals a complete last line and appends after it.

The helper runs under sh, bash, and dash, each where installed, against throwaway logs;
on macOS, `sh` is bash 3.2.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LOG_SH = ROOT / "skills/run/show-me-your-work/scripts/log.sh"
SHELLS = [shell for shell in ("sh", "bash", "dash") if shutil.which(shell)]
HEADER = "ts\tphase\tdecision\twhy\tevidence\tresult"
COMPLETE = "2026-05-24T09:02:00Z\tframe\tcounted the work first\twanted the size\tcommit 3a9f1c2\topen"
PARTIAL = "2026-05-24T11:15:00Z\twidget\tmoved the widget sty"
# Cut right after the fifth tab: six fields, but log.sh never writes an empty one.
EMPTY_LAST = "2026-05-24T11:15:00Z\twidget\tmoved the widget styles\tkeep it small\tcommit 7c21e0a\t"
ROW = ["widget", "kept the change small", "result must look identical", "commit 7c21e0a", "tests pass"]


class LogHelperTests(unittest.TestCase):
    def run_helper(self, shell, before):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "decisions.tsv"
            log.write_text(before)
            done = subprocess.run([shell, str(LOG_SH), str(log), *ROW], capture_output=True, text=True)
            return done, log.read_text()

    def test_a_shell_to_run_the_helper_is_installed(self):
        self.assertTrue(SHELLS, "none of sh, bash, or dash is on PATH, so nothing was checked")

    def test_a_partial_last_record_stops_the_append_and_is_named(self):
        for partial, fields in ((PARTIAL, "3 of 6 fields"), (EMPTY_LAST, "6 of 6 fields, the last one empty")):
            before = f"{HEADER}\n{COMPLETE}\n{partial}"
            for shell in SHELLS:
                with self.subTest(shell=shell, fields=fields):
                    done, after = self.run_helper(shell, before)
                    self.assertNotEqual(done.returncode, 0)
                    self.assertIn("line 3", done.stderr)
                    self.assertIn(fields, done.stderr)
                    self.assertIn("supersedes line 3", done.stderr)
                    self.assertIn(partial, done.stderr)
                    self.assertEqual(after, before)

    def test_a_complete_unterminated_last_record_is_healed_and_appended_after(self):
        for shell in SHELLS:
            with self.subTest(shell=shell):
                done, after = self.run_helper(shell, f"{HEADER}\n{COMPLETE}")
                self.assertEqual(done.returncode, 0, done.stderr)
                lines = after.split("\n")
                self.assertEqual(lines[:2], [HEADER, COMPLETE])
                self.assertEqual(lines[2].split("\t")[1:], ROW)
                self.assertEqual(lines[3:], [""])


if __name__ == "__main__":
    unittest.main()

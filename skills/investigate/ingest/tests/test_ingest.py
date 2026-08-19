"""Tests for ingest.py — the defects the advisory board found, pinned.

Every case here failed on v1.0.0 (`~/.advisory-board/runs/ingest-skill-red-team-2026-08-06`).
Standard library only, no network, no media: the pipeline's mechanical
invariants are testable without ever invoking ffmpeg or whisper.

Run:  python3 -m unittest discover -s tests -t tests
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import ingest as ing  # noqa: E402


class Args:
    """The subset of parsed args the identity functions read."""

    def __init__(self, **kw):
        self.input = kw.get("input", "https://example.com/v")
        self.intent = kw.get("intent", "call")
        self.ladder = kw.get("ladder", 10)
        self.no_frames = kw.get("no_frames", False)


class TestManifestCompletion(unittest.TestCase):
    """A stage is done when it SAYS so, never because it has nothing to check."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_empty_artifacts_are_not_vacuously_done(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        m.data["stages"]["probe"] = {"artifacts": []}      # legacy shape
        self.assertFalse(m.done("probe"))

    def test_declared_stage_with_no_artifacts_is_done(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        m.finish("probe", [], info={"true_duration_s": 1})
        self.assertTrue(m.done("probe"))

    def test_skipped_stage_is_done(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        m.finish("frames", [], status="skipped", reason="--no-frames")
        self.assertTrue(m.done("frames"))

    def test_stage_from_another_identity_is_not_reused(self):
        m = ing.Manifest(self.dir, identity_hash="aaa")
        m.finish("transcribe", [])
        other = ing.Manifest(self.dir, identity_hash="bbb")
        self.assertFalse(other.done("transcribe"))

    def test_missing_artifact_defeats_completion(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        gone = self.dir / "transcript.srt"
        gone.write_text("x")
        m.finish("transcribe", [gone])
        self.assertTrue(m.done("transcribe"))
        gone.unlink()
        self.assertFalse(ing.Manifest(self.dir, identity_hash="abc").done("transcribe"))


class TestIdentity(unittest.TestCase):
    """Changing what the packet is evidence of must change its fingerprint."""

    def test_same_args_same_hash(self):
        a, b = Args(), Args()
        self.assertEqual(
            ing.identity_hash(ing.run_identity(a)),
            ing.identity_hash(ing.run_identity(b)),
        )

    def test_each_axis_changes_the_hash(self):
        base = ing.identity_hash(ing.run_identity(Args()))
        for kw in (
            {"input": "https://example.com/OTHER"},
            {"intent": "demo"},
            {"ladder": 5},
            {"no_frames": True},
        ):
            self.assertNotEqual(
                base, ing.identity_hash(ing.run_identity(Args(**kw))), kw
            )

    def test_local_file_edit_changes_the_hash(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "clip.mp4"
            f.write_text("one")
            first = ing.identity_hash(ing.run_identity(Args(input=str(f))))
            f.write_text("a different recording entirely")
            self.assertNotEqual(
                first, ing.identity_hash(ing.run_identity(Args(input=str(f))))
            )


class TestOutDirOwnership(unittest.TestCase):
    """Retention deletes inside the run dir, so the run dir must be ours."""

    def test_refuses_a_foreign_non_empty_directory(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "my-documents"
            d.mkdir()
            (d / "taxes.pdf").write_text("important")
            with self.assertRaises(SystemExit) as cm:
                ing.claim_out_dir(d)
            self.assertEqual(cm.exception.code, 2)
            self.assertTrue((d / "taxes.pdf").exists())

    def test_claims_a_fresh_directory_and_marks_it(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "packet"
            ing.claim_out_dir(d)
            self.assertTrue((d / ".ingest-run").exists())
            ing.claim_out_dir(d)      # a second run reuses its own dir


class TestPreviewMarksItsOwnDirectory(unittest.TestCase):
    """Issue #160: `preview --out DIR` created DIR without the adoption
    marker, so a same-dir `run --out DIR` afterwards was refused by
    claim_out_dir as a foreign non-empty directory. preview must claim the
    directory itself so the preview-then-run flow SKILL.md describes works,
    while a genuinely foreign non-empty directory stays refused."""

    def setUp(self):
        original = ing.run_cmd
        # No network: yt-dlp is mocked to "no captions available" so the
        # test exercises directory ownership, not the caption pipeline.
        ing.run_cmd = lambda argv, timeout=None, **kw: __import__(
            "subprocess"
        ).CompletedProcess(argv, 1, stdout="", stderr="")
        self.addCleanup(lambda: setattr(ing, "run_cmd", original))

    def test_preview_writes_the_marker_so_run_can_adopt_the_directory(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "packet"
            with self.assertRaises(SystemExit):
                ing.main(["preview", "--url", "https://example.com/v",
                          "--out", str(d)])
            self.assertTrue(
                (d / ".ingest-run").exists(),
                "preview must mark the directory it creates",
            )
            # A subsequent `run --out` on the same dir must adopt it, not
            # refuse it (the bug: exit 2, "not empty and was not created by
            # ingest").
            ing.claim_out_dir(d)

    def test_preview_still_refuses_a_foreign_non_empty_directory(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "my-documents"
            d.mkdir()
            (d / "taxes.pdf").write_text("important")
            with self.assertRaises(SystemExit) as cm:
                ing.main(["preview", "--url", "https://example.com/v",
                          "--out", str(d)])
            self.assertEqual(cm.exception.code, 2)
            self.assertTrue((d / "taxes.pdf").exists())


class TestRetention(unittest.TestCase):
    """Deletion is by ledger, never by directory name."""

    def test_only_ledgered_files_are_removed(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "packet"
            (out / "media").mkdir(parents=True)
            ours = out / "media" / "source.mp4"
            ours.write_text("downloaded")
            theirs = out / "media" / "wedding-video.mov"
            theirs.write_text("irreplaceable")
            wav = out / "audio.wav"
            wav.write_text("pcm")

            m = ing.Manifest(out, identity_hash="abc")
            m.finish("fetch", [ours])
            m.finish("audio", [wav])       # the ledger is the only delete list
            ing.discard_media(out, m)

            self.assertFalse(ours.exists())
            self.assertFalse(wav.exists())
            self.assertTrue(theirs.exists(), "deleted a file it never created")
            self.assertTrue(m.data["media_discarded"])

    def test_a_ledger_path_outside_the_packet_is_refused(self):
        # manifest.json is an input, not a fact: a hand-edited or corrupted
        # ledger must not be able to aim deletion at the rest of the disk.
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "packet"
            out.mkdir()
            outsider = Path(t) / "not-the-packet.mp4"
            outsider.write_text("someone else's file")
            m = ing.Manifest(out, identity_hash="abc")
            m.finish("fetch", [outsider])
            ing.discard_media(out, m)
            self.assertTrue(outsider.exists())

    def test_an_unledgered_wav_survives(self):
        # Nothing is deleted for being named audio.wav — only for being in the
        # ledger. Guards the rule itself, not just today's call sites.
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "packet"
            out.mkdir()
            stray = out / "audio.wav"
            stray.write_text("not ours")
            m = ing.Manifest(out, identity_hash="abc")
            ing.discard_media(out, m)
            self.assertTrue(stray.exists())


class TestTranscriptFidelity(unittest.TestCase):
    """The derived reading copy may compress, never assert what wasn't heard."""

    def test_genuine_quick_repetition_is_preserved(self):
        segs = [(10, "Yes"), (12, "Yes"), (14, "Yes"), (16, "Moving on")]
        out, collapsed = ing.collapse_repeats(segs)
        self.assertEqual(collapsed, 0)
        self.assertEqual(out, segs)

    def test_a_long_loop_is_collapsed_and_labelled_honestly(self):
        segs = [(0, "Thanks for watching!")]
        segs += [(t, "Thanks for watching!") for t in range(30, 130, 10)]
        out, collapsed = ing.collapse_repeats(segs)
        self.assertEqual(collapsed, 1)
        note = out[1][1]
        self.assertIn("repeated", note)
        self.assertIn("transcript.srt", note)
        self.assertNotIn("no speech", note)
        self.assertLess(len(out), len(segs))

    def test_unrepeated_speech_passes_through(self):
        segs = [(0, "one"), (5, "two"), (10, "three")]
        out, collapsed = ing.collapse_repeats(segs)
        self.assertEqual((out, collapsed), (segs, 0))


class TestPacketValidation(unittest.TestCase):
    """'Complete' is re-derived from disk, not inferred from control flow."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_clean_packet_has_no_problems(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        good = self.dir / "transcript.srt"
        good.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
        m.finish("transcribe", [good])
        self.assertEqual(ing.validate_packet(m, self.dir), [])

    def test_empty_artifact_is_a_problem(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        empty = self.dir / "transcript.txt"
        empty.write_text("")
        m.finish("transcribe", [empty])
        self.assertTrue(
            any("empty" in p for p in ing.validate_packet(m, self.dir))
        )

    def test_missing_frame_file_is_a_problem(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        m.finish("frames", [])
        m.data["frames"] = [{"file": "frames/ladder_00001.jpg", "ts": 0}]
        self.assertTrue(
            any("frames" in p for p in ing.validate_packet(m, self.dir))
        )

    def test_declared_no_speech_srt_may_be_empty(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        srt = self.dir / "transcript.srt"
        srt.write_text("")
        m.finish("transcribe", [srt], segments=0, no_speech=True)
        self.assertEqual(ing.validate_packet(m, self.dir), [])

    def test_an_undeclared_empty_srt_is_still_a_problem(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        srt = self.dir / "transcript.srt"
        srt.write_text("")
        m.finish("transcribe", [srt], segments=0)
        self.assertTrue(
            any("empty" in p for p in ing.validate_packet(m, self.dir))
        )

    def test_short_transcript_against_a_long_recording_is_a_problem(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        srt = self.dir / "transcript.srt"
        srt.write_text("1\n00:00:05,000 --> 00:00:07,000\nhello\n")
        m.finish("probe", [], info={"true_duration_s": 3600})
        m.finish("transcribe", [srt])
        problems = ing.validate_packet(m, self.dir)
        self.assertTrue(any("uncovered" in p for p in problems), problems)

    def test_trailing_silence_is_not_a_coverage_problem(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        srt = self.dir / "transcript.srt"
        srt.write_text("1\n00:04:30,000 --> 00:04:35,000\nbye\n")
        m.finish("probe", [], info={"true_duration_s": 300})
        m.finish("transcribe", [srt])
        self.assertEqual(ing.validate_packet(m, self.dir), [])

    def test_one_long_cue_covers_the_recording(self):
        # Coverage is measured from the last cue's END; measuring from its start
        # would call a single hour-long cue an hour of missing transcript.
        m = ing.Manifest(self.dir, identity_hash="abc")
        srt = self.dir / "transcript.srt"
        srt.write_text("1\n00:00:00,000 --> 01:00:00,000\na long single cue\n")
        m.finish("probe", [], info={"true_duration_s": 3600})
        m.finish("transcribe", [srt])
        self.assertEqual(ing.validate_packet(m, self.dir), [])

    def test_malformed_end_timestamp_does_not_count_as_coverage(self):
        # 00:99:99 is not a valid SRT time; a cue carrying it must not move the
        # coverage end (a fabricated end past true duration would make the gap
        # negative and pass a malformed transcript as complete).
        m = ing.Manifest(self.dir, identity_hash="abc")
        srt = self.dir / "transcript.srt"
        srt.write_text(
            "1\n00:00:00,000 --> 00:00:05,000\nhello\n"
            "\n2\n00:00:05,000 --> 00:99:99,000\nbroken\n"
        )
        m.finish("probe", [], info={"true_duration_s": 3600})
        m.finish("transcribe", [srt])
        problems = ing.validate_packet(m, self.dir)
        self.assertTrue(any("uncovered" in p for p in problems), problems)

    def test_timestamp_shaped_cue_text_does_not_count_as_coverage(self):
        # A speaker QUOTING a timing line ("... --> 00:59:00,000") is cue text,
        # not a cue; only structurally valid timing LINES may move the end.
        m = ing.Manifest(self.dir, identity_hash="abc")
        srt = self.dir / "transcript.srt"
        srt.write_text(
            "1\n00:00:00,000 --> 00:00:05,000\n"
            "the cue said 00:00:00,000 --> 00:59:00,000 on screen\n"
        )
        m.finish("probe", [], info={"true_duration_s": 3600})
        m.finish("transcribe", [srt])
        problems = ing.validate_packet(m, self.dir)
        self.assertTrue(any("uncovered" in p for p in problems), problems)

    def test_srt_with_bytes_but_no_cues_is_a_problem(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        srt = self.dir / "transcript.srt"
        srt.write_text("this is not an SRT at all\n")
        m.finish("probe", [], info={"true_duration_s": 300})
        m.finish("transcribe", [srt])
        self.assertTrue(
            any("no parseable cues" in p for p in ing.validate_packet(m, self.dir))
        )

    def test_declared_no_speech_skips_the_coverage_check(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        srt = self.dir / "transcript.srt"
        srt.write_text("")
        m.finish("probe", [], info={"true_duration_s": 3600})
        m.finish("transcribe", [srt], segments=0, no_speech=True)
        self.assertEqual(ing.validate_packet(m, self.dir), [])

    def test_discarded_media_is_not_reported_missing(self):
        m = ing.Manifest(self.dir, identity_hash="abc")
        m.finish("fetch", [self.dir / "media" / "source.mp4"])
        m.data["media_discarded"] = True
        self.assertEqual(ing.validate_packet(m, self.dir), [])


class TestCommandLine(unittest.TestCase):
    """The purpose gate is only real if the CLI enforces it.

    argparse writes its usage message to stderr on rejection; these tests
    silence it so a passing run's output stays readable.
    """

    def setUp(self):
        original = sys.stderr
        sys.stderr = io.StringIO()

        def restore():
            sys.stderr = original

        self.addCleanup(restore)

    def test_run_requires_a_goal(self):
        with self.assertRaises(SystemExit) as cm:
            ing.main(["run", "--input", "x.mp4", "--intent", "call", "--out", "/tmp/x"])
        self.assertEqual(cm.exception.code, 2)      # argparse: missing required

    def test_run_rejects_an_unknown_intent(self):
        with self.assertRaises(SystemExit) as cm:
            ing.main(["run", "--input", "x.mp4", "--intent", "not-an-intent",
                      "--goal", "why", "--out", "/tmp/x"])
        self.assertEqual(cm.exception.code, 2)


class TestPathSafety(unittest.TestCase):
    def test_applescript_literal_is_escaped(self):
        nasty = '/tmp/a"; do shell script "rm -rf ~/x'
        escaped = ing.applescript_str(nasty)
        self.assertNotIn('"', escaped.replace('\\"', ""))
        self.assertIn('\\"', escaped)

    def test_backslash_is_escaped_before_quotes(self):
        self.assertEqual(ing.applescript_str(r"a\b"), r"a\\b")


class TestManifestDurability(unittest.TestCase):
    def test_corrupt_manifest_is_kept_for_forensics_not_read(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "manifest.json").write_text("{ truncated")
            m = ing.Manifest(d, identity_hash="abc")
            self.assertEqual(m.data["stages"], {})
            self.assertTrue((d / "manifest.json.corrupt").exists())

    def test_an_interrupted_marker_write_leaves_no_marker(self):
        # #190: claim_out_dir wrote .ingest-run with a plain write_text(), so
        # a crash mid-write could leave a partial marker that adoption checks
        # then trusted. After an interrupted write, the marker must either
        # exist complete or not exist at all.
        import builtins
        import io as io_mod

        class SimulatedCrash(OSError):
            pass

        class CrashingWriter:
            """Wraps a real file handle; the first write() emits half the
            payload, flushes, then dies, like a process killed mid-write."""

            def __init__(self, fh):
                self._fh = fh

            def write(self, s):
                self._fh.write(s[: len(s) // 2])
                self._fh.flush()
                raise SimulatedCrash("interrupted mid-write")

            def __getattr__(self, name):
                return getattr(self._fh, name)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self._fh.close()
                return False

        real_open = io_mod.open

        def crashing_open(file, mode="r", *args, **kwargs):
            fh = real_open(file, mode, *args, **kwargs)
            if "w" in str(mode) and ing.RUN_MARKER in str(file):
                return CrashingWriter(fh)
            return fh

        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / "run"
            io_mod.open, builtins.open = crashing_open, crashing_open
            try:
                with self.assertRaises(SimulatedCrash):
                    ing.claim_out_dir(d)
            finally:
                io_mod.open, builtins.open = real_open, real_open
            self.assertFalse(
                (d / ing.RUN_MARKER).exists(),
                "an interrupted write must never leave a partial marker",
            )

    def test_save_is_atomic_and_reloadable(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            m = ing.Manifest(d, identity_hash="abc")
            m.data["goal"] = "find the demo bugs"
            m.save()
            self.assertEqual(
                json.loads((d / "manifest.json").read_text())["goal"],
                "find the demo bugs",
            )


class FakeProc:
    """A subprocess.CompletedProcess stand-in for mocked run_cmd calls."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class SweepBase(unittest.TestCase):
    """Shared plumbing: a temp home, packet builders, and a run_cmd mock that
    guarantees no test ever reaches gh or the network. The responder is any
    callable — including one that RAISES, because a subprocess layer that can
    only fail politely hides the crash family entirely."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.calls = []
        self._responder = lambda argv: FakeProc(
            returncode=127, stderr="unexpected subprocess call in test"
        )
        original = ing.run_cmd

        def fake_run(argv, timeout=None, **kw):
            self.calls.append(argv)
            return self._responder(argv)

        ing.run_cmd = fake_run
        self.addCleanup(lambda: setattr(ing, "run_cmd", original))

    def respond(self, fn):
        self._responder = fn

    def make_packet(self, name, items=(), extra_files=()):
        d = self.home / name
        d.mkdir()
        (d / ".ingest-run").write_text("created by ingest.py in test\n")
        m = ing.Manifest(d, identity_hash="abc")
        srt = d / "transcript.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
        m.finish("transcribe", [srt])
        for item in items:
            m.data["derived_items"].append({"id": item, "added": "2026-08-08"})
        m.save()
        for rel in extra_files:
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x")
        return d


class TestDerivedItemsLink(SweepBase):
    """Filing time is when the link is written — and only into our own dirs."""

    def test_link_appends_id_and_date(self):
        d = self.make_packet("p")
        ing.main(["link", "--out", str(d), "--item", "owner/repo#12"])
        items = json.loads((d / "manifest.json").read_text())["derived_items"]
        self.assertEqual([i["id"] for i in items], ["owner/repo#12"])
        self.assertRegex(items[0]["added"], r"^\d{4}-\d{2}-\d{2}$")

    def test_link_is_idempotent_and_keeps_the_original_date(self):
        d = self.make_packet("p")
        ing.main(["link", "--out", str(d), "--item", "owner/repo#12"])
        mpath = d / "manifest.json"
        data = json.loads(mpath.read_text())
        data["derived_items"][0]["added"] = "2000-01-01"
        mpath.write_text(json.dumps(data))
        ing.main(["link", "--out", str(d),
                  "--item", "owner/repo#12", "--item", "owner/repo#13"])
        items = json.loads(mpath.read_text())["derived_items"]
        self.assertEqual(
            [i["id"] for i in items], ["owner/repo#12", "owner/repo#13"]
        )
        self.assertEqual(items[0]["added"], "2000-01-01",
                         "a re-link must not rewrite the filing date")

    def test_link_idempotence_is_case_insensitive(self):
        # GitHub ids are case-insensitive; O/R#1 and o/r#1 are one item.
        d = self.make_packet("p")
        ing.main(["link", "--out", str(d), "--item", "Owner/Repo#12"])
        ing.main(["link", "--out", str(d), "--item", "owner/repo#12"])
        items = json.loads((d / "manifest.json").read_text())["derived_items"]
        self.assertEqual(len(items), 1)

    def test_link_rejects_ids_with_shell_metacharacters(self):
        # BLOCKER 1b: an id is an identifier — whitespace, control chars, and
        # shell syntax are refused at the door, before they can ever reach a
        # resolution command or a report line.
        d = self.make_packet("p")
        for bad in ("a b#1", "x;touch /tmp/PWNED#1", "o/r#1\n[ingest] OFFER",
                    "$(reboot)#1", "a'b#1"):
            with self.assertRaises(SystemExit) as cm:
                ing.main(["link", "--out", str(d), "--item", bad])
            self.assertEqual(cm.exception.code, 2, bad)
        items = json.loads((d / "manifest.json").read_text())["derived_items"]
        self.assertEqual(items, [], "a refused id must not be recorded")

    def test_link_refuses_a_torn_manifest_instead_of_corrupt_renaming(self):
        # An additive command must not trigger the corrupt-rename and quietly
        # destroy the stage ledger.
        d = self.make_packet("p")
        (d / "manifest.json").write_text("{ torn")
        with self.assertRaises(SystemExit) as cm:
            ing.main(["link", "--out", str(d), "--item", "o/r#1"])
        self.assertEqual(cm.exception.code, 1)
        self.assertEqual((d / "manifest.json").read_text(), "{ torn")
        self.assertFalse((d / "manifest.json.corrupt").exists())

    def test_link_refuses_a_directory_ingest_did_not_create(self):
        foreign = self.home / "documents"
        foreign.mkdir()
        with self.assertRaises(SystemExit) as cm:
            ing.main(["link", "--out", str(foreign), "--item", "o/r#1"])
        self.assertEqual(cm.exception.code, 2)

    def test_manifest_defaults_derived_items(self):
        m = ing.Manifest(self.home, identity_hash="abc")
        self.assertEqual(m.data["derived_items"], [])


class TestItemResolution(SweepBase):
    """GitHub-first via gh; binding-doc command otherwise; never a guess."""

    def test_closed_github_issue_is_resolved(self):
        self.respond(lambda argv: FakeProc(stdout="closed\n"))
        state, _ = ing.check_item_resolution("owner/repo#7")
        self.assertEqual(state, "resolved")
        self.assertEqual(
            self.calls[0][:3], ["gh", "api", "repos/owner/repo/issues/7"]
        )

    def test_open_github_issue_is_open(self):
        self.respond(lambda argv: FakeProc(stdout="open\n"))
        self.assertEqual(ing.check_item_resolution("owner/repo#7")[0], "open")

    def test_gh_failure_is_unknown_not_resolved(self):
        self.respond(lambda argv: FakeProc(returncode=1, stderr="HTTP 404"))
        state, why = ing.check_item_resolution("owner/repo#7")
        self.assertEqual(state, "unknown")
        self.assertIn("404", why)

    def test_non_github_id_without_binding_asks_the_decider(self):
        state, why = ing.check_item_resolution("JIRA-42")
        self.assertEqual(state, "unknown")
        self.assertIn("decider", why)
        self.assertEqual(self.calls, [], "must not shell out with no binding")

    def test_binding_doc_command_gets_the_id_as_data_not_shell(self):
        # BLOCKER 1a: {id} becomes a quoted positional reference and the id
        # itself rides in as $1 — never spliced into the -c string.
        self.respond(lambda argv: FakeProc(returncode=0))
        hostile = "X; touch /tmp/PWNED; exit 0"
        state, _ = ing.check_item_resolution(
            hostile, check_cmd="check-resolved {id}"
        )
        self.assertEqual(state, "resolved")
        self.assertEqual(
            self.calls[0],
            ["/bin/sh", "-c", 'check-resolved "$1"', "sh", hostile],
        )

    def test_binding_doc_exit_1_is_open_and_other_exits_are_unknown(self):
        self.respond(lambda argv: FakeProc(returncode=1))
        self.assertEqual(
            ing.check_item_resolution("JIRA-42", check_cmd="c {id}")[0], "open"
        )
        self.respond(lambda argv: FakeProc(returncode=3))
        self.assertEqual(
            ing.check_item_resolution("JIRA-42", check_cmd="c {id}")[0],
            "unknown",
        )

    def test_check_cmd_without_the_placeholder_is_refused(self):
        # MAJOR 4: `--check-cmd true` would resolve everything — fail closed.
        with self.assertRaises(SystemExit) as cm:
            ing.check_item_resolution("JIRA-42", check_cmd="true")
        self.assertEqual(cm.exception.code, 2)
        self.assertEqual(self.calls, [], "must die before running anything")

    def test_a_raising_run_cmd_is_unknown_not_a_crash(self):
        # MAJOR 3: gh missing (OSError) or hanging (TimeoutExpired) is a fact
        # about the machine, not the item — and never aborts the sweep.
        def boom(argv):
            raise OSError("No such file or directory: 'gh'")
        self.respond(boom)
        state, why = ing.check_item_resolution("o/r#1")
        self.assertEqual(state, "unknown")
        self.assertIn("gh", why)

        def hang(argv):
            raise ing.subprocess.TimeoutExpired(argv, 120)
        self.respond(hang)
        state, _ = ing.check_item_resolution("JIRA-42", check_cmd="c {id}")
        self.assertEqual(state, "unknown")

    def test_dot_segments_are_not_github_shaped(self):
        # NIT: '../..#1' must not ride into the gh API path as traversal.
        for tricky in ("../..#1", "./x#1", "a/..#2"):
            state, _ = ing.check_item_resolution(tricky)
            self.assertEqual(state, "unknown", tricky)
        self.assertEqual(self.calls, [], "no gh call for a non-GitHub shape")


class TestInjectionRealShell(unittest.TestCase):
    """BLOCKER 1 pinned against a real /bin/sh (no mock, no network): the
    reproduced exploit — a hostile id forging 'resolved' AND executing — must
    stay dead at the subprocess boundary itself."""

    def test_hostile_id_cannot_execute_or_forge_resolution(self):
        with tempfile.TemporaryDirectory() as t:
            pwned = Path(t) / "PWNED"
            hostile = f"X; touch {pwned}; exit 0"
            state, _ = ing.check_item_resolution(
                hostile, check_cmd="false {id}"
            )
            self.assertEqual(state, "open", "false must stay exit 1")
            self.assertFalse(pwned.exists(), "the id executed as shell")

    def test_the_id_arrives_as_the_first_positional_argument(self):
        state, _ = ing.check_item_resolution(
            "safe-id", check_cmd='test {id} = "safe-id"'
        )
        self.assertEqual(state, "resolved")
        state, _ = ing.check_item_resolution(
            "other", check_cmd='test {id} = "safe-id"'
        )
        self.assertEqual(state, "open")


class TestSweepVerdicts(SweepBase):
    """The verdict is what the offer hangs on: resolved may be offered,
    open stays, unknown/unlinked go to the decider."""

    def gh_states(self, mapping):
        def responder(argv):
            key = argv[2] if argv[0] == "gh" else None
            state = mapping.get(key, "open")
            return FakeProc(stdout=state + "\n")
        self.respond(responder)

    def test_all_items_closed_is_resolved(self):
        d = self.make_packet("p", items=["o/r#1", "o/r#2"])
        self.gh_states({"repos/o/r/issues/1": "closed",
                        "repos/o/r/issues/2": "closed"})
        self.assertEqual(ing.sweep_packet(d)["verdict"], "resolved")

    def test_one_open_item_keeps_the_packet(self):
        d = self.make_packet("p", items=["o/r#1", "o/r#2"])
        self.gh_states({"repos/o/r/issues/1": "closed",
                        "repos/o/r/issues/2": "open"})
        self.assertEqual(ing.sweep_packet(d)["verdict"], "open")

    def test_open_beats_unknown(self):
        # A live item settles the question — no need to bother the decider
        # about an unresolvable one in the same packet.
        d = self.make_packet("p", items=["o/r#1", "JIRA-9"])
        self.gh_states({"repos/o/r/issues/1": "open"})
        self.assertEqual(ing.sweep_packet(d)["verdict"], "open")

    def test_unresolvable_item_is_unknown(self):
        d = self.make_packet("p", items=["o/r#1", "JIRA-9"])
        self.gh_states({"repos/o/r/issues/1": "closed"})
        self.assertEqual(ing.sweep_packet(d)["verdict"], "unknown")

    def test_no_derived_items_is_unlinked_not_resolved(self):
        d = self.make_packet("p")
        report = ing.sweep_packet(d)
        self.assertEqual(report["verdict"], "unlinked")
        self.assertEqual(self.calls, [], "nothing to check, nothing called")

    def test_unreadable_manifest_is_unknown(self):
        d = self.make_packet("p")
        (d / "manifest.json").write_text("{ torn")
        self.assertEqual(ing.sweep_packet(d)["verdict"], "unknown")

    def test_find_packets_goes_by_marker_not_name(self):
        ours = self.make_packet("demo-run")
        lookalike = self.home / "demo-run-2"
        lookalike.mkdir()
        (lookalike / "manifest.json").write_text("{}")
        self.assertEqual(ing.find_packets(self.home), [ours])

    def test_a_home_that_is_itself_a_packet_sweeps_as_one(self):
        d = self.make_packet("p")
        self.assertEqual(ing.find_packets(d), [d])

    def test_a_bare_string_derived_item_is_coerced_not_a_crash(self):
        # MAJOR 3: a hand-edited manifest may hold "o/r#1" instead of the
        # {"id": ..., "added": ...} shape — coerce it, don't AttributeError.
        d = self.make_packet("p")
        mpath = d / "manifest.json"
        data = json.loads(mpath.read_text())
        data["derived_items"] = ["o/r#1"]
        mpath.write_text(json.dumps(data))
        self.gh_states({"repos/o/r/issues/1": "closed"})
        self.assertEqual(ing.sweep_packet(d)["verdict"], "resolved")

    def test_a_non_list_derived_items_is_unknown_not_a_crash(self):
        # CodeRabbit (PR #135): derived_items: 42 raised TypeError in
        # sweep_packet — malformed at the container level is unknown too.
        d = self.make_packet("p")
        mpath = d / "manifest.json"
        data = json.loads(mpath.read_text())
        data["derived_items"] = 42
        mpath.write_text(json.dumps(data))
        report = ing.sweep_packet(d)
        self.assertEqual(report["verdict"], "unknown")
        self.assertIn("not a list", report["note"])
        self.assertEqual(self.calls, [], "nothing checkable, nothing called")

    def test_a_garbage_derived_item_is_unknown_not_a_crash(self):
        d = self.make_packet("p")
        mpath = d / "manifest.json"
        data = json.loads(mpath.read_text())
        data["derived_items"] = [{"nope": 1}, 42, None]
        mpath.write_text(json.dumps(data))
        report = ing.sweep_packet(d)
        self.assertEqual(report["verdict"], "unknown")
        self.assertEqual(self.calls, [], "garbage entries check nothing")

    def test_one_packet_failure_does_not_kill_the_report(self):
        # MAJOR 3: the report survives a packet that blows up mid-check.
        bad = self.make_packet("bad", items=["o/r#1"])
        good = self.make_packet("good", items=["o/r#2"])
        self.gh_states({"repos/o/r/issues/2": "closed"})
        original = ing.sweep_packet

        def fragile(out_dir, check_cmd=None):
            if out_dir == bad:
                raise RuntimeError("boom")
            return original(out_dir, check_cmd)

        ing.sweep_packet = fragile
        self.addCleanup(lambda: setattr(ing, "sweep_packet", original))

        class A:
            home = str(self.home)
            check_cmd = None
            delete = []

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ing.cmd_sweep(A())
        text = out.getvalue()
        self.assertIn("boom", text)
        self.assertIn("packet good — verdict: resolved", text)
        self.assertTrue(good.exists() and bad.exists())

    def test_a_crafted_id_cannot_forge_report_lines(self):
        # MINOR 7: ids come from a file on disk; they are rendered escaped,
        # so a newline in one cannot fabricate an OFFER line.
        d = self.make_packet("p")
        mpath = d / "manifest.json"
        data = json.loads(mpath.read_text())
        forged = "x#1\n[ingest] OFFER — fully resolved"
        data["derived_items"] = [{"id": forged, "added": "2026-08-08"}]
        mpath.write_text(json.dumps(data))

        class A:
            home = str(self.home)
            check_cmd = None
            delete = []

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            ing.cmd_sweep(A())
        lines = out.getvalue().splitlines()
        self.assertNotIn("[ingest] OFFER — fully resolved", lines)
        self.assertTrue(any(json.dumps(forged) in ln for ln in lines))

    def test_doctor_covers_gh(self):
        # The sweep's resolution checks need gh; doctor must say so when
        # it is missing rather than letting the first sweep discover it.
        self.assertIn("gh", ing.TOOLS)


class TestSweepDeletion(SweepBase):
    """Offer-only, re-checked, and by ledger — the v1.1.0 ownership rules."""

    def all_closed(self):
        self.respond(lambda argv: FakeProc(stdout="closed\n"))

    def test_refuses_a_directory_ingest_did_not_create(self):
        foreign = self.home / "documents"
        foreign.mkdir()
        (foreign / "taxes.pdf").write_text("important")
        self.assertEqual(ing.delete_packet(foreign), 2)
        self.assertTrue((foreign / "taxes.pdf").exists())

    def test_refuses_while_derived_work_is_open(self):
        d = self.make_packet("p", items=["o/r#1"])
        self.respond(lambda argv: FakeProc(stdout="open\n"))
        self.assertEqual(ing.delete_packet(d), 1)
        self.assertTrue((d / "transcript.srt").exists())

    def test_refuses_an_unlinked_packet(self):
        # No recorded derived work proves no terminal state — deletion is
        # never offered off silence.
        d = self.make_packet("p")
        self.assertEqual(ing.delete_packet(d), 1)
        self.assertTrue(d.exists())

    def test_deletes_a_resolved_packet_by_ledger(self):
        d = self.make_packet("p", items=["o/r#1"])
        m = ing.Manifest(d, identity_hash="abc")
        frames = d / "frames"
        frames.mkdir()
        (frames / "ladder_00001.jpg").write_text("jpg")
        m.data["frames"] = [{"file": "frames/ladder_00001.jpg", "ts": 0}]
        m.finish("frames", [frames / "ladder_00001.jpg"])
        self.all_closed()
        self.assertEqual(ing.delete_packet(d), 0)
        self.assertFalse(d.exists(), "a fully-ledgered packet is removed")

    def test_partial_deletion_keeps_the_packet_sweepable(self):
        # BLOCKER 2: the kept directory (foreign files — e.g. a call run's
        # saved recap email) keeps its marker and manifest, stays visible to
        # find_packets, and is distinguishable from a refusal by exit code.
        d = self.make_packet("p", items=["o/r#1"],
                             extra_files=["notes/recap-email.md"])
        self.all_closed()
        self.assertEqual(ing.delete_packet(d), 5)
        self.assertTrue((d / "notes" / "recap-email.md").exists())
        self.assertFalse((d / "transcript.srt").exists())
        self.assertTrue((d / ".ingest-run").exists(),
                        "the marker is sweepability — never removed first")
        self.assertTrue((d / "manifest.json").exists())
        self.assertIn(d, ing.find_packets(self.home))
        self.assertEqual(ing.sweep_packet(d)["verdict"], "resolved",
                         "the kept packet can still be swept and re-offered")

    def test_a_ledger_path_outside_the_packet_is_refused(self):
        d = self.make_packet("p", items=["o/r#1"])
        outsider = self.home / "not-the-packet.mp4"
        outsider.write_text("someone else's file")
        m = ing.Manifest(d, identity_hash="abc")
        m.finish("fetch", [outsider])
        self.all_closed()
        ing.delete_packet(d)
        self.assertTrue(outsider.exists())

    def test_a_ledgered_path_that_became_a_symlink_is_left_alone(self):
        # MAJOR 6: the ledger recorded a file; a link in its place is not
        # that file, and deletion never reaches through it.
        d = self.make_packet("p", items=["o/r#1"])
        precious = self.home / "precious.txt"
        precious.write_text("irreplaceable")
        srt = d / "transcript.srt"
        srt.unlink()
        srt.symlink_to(precious)
        self.all_closed()
        self.assertEqual(ing.delete_packet(d), 5)
        self.assertTrue(precious.exists())
        self.assertTrue(srt.is_symlink(), "the link itself is a leftover")
        self.assertTrue((d / ".ingest-run").exists())

    def test_symlink_to_a_directory_does_not_crash_deletion(self):
        d = self.make_packet("p", items=["o/r#1"])
        target = self.home / "real-dir"
        target.mkdir()
        (target / "keep.txt").write_text("keep")
        (d / "linked").symlink_to(target)
        self.all_closed()
        self.assertEqual(ing.delete_packet(d), 5)
        self.assertTrue((target / "keep.txt").exists())
        self.assertTrue((d / "linked").is_symlink())

    def test_a_dangling_symlink_is_a_leftover_not_a_crash(self):
        d = self.make_packet("p", items=["o/r#1"])
        (d / "dangling").symlink_to(self.home / "no-such-target")
        self.all_closed()
        self.assertEqual(ing.delete_packet(d), 5)
        self.assertTrue((d / "dangling").is_symlink())
        self.assertTrue((d / ".ingest-run").exists())

    def test_delete_on_a_non_list_derived_items_refuses_not_crashes(self):
        # CodeRabbit (PR #135): --delete reached sweep_packet unguarded, so a
        # hand-edited derived_items: 42 ended in a traceback, not a refusal.
        d = self.make_packet("p")
        mpath = d / "manifest.json"
        data = json.loads(mpath.read_text())
        data["derived_items"] = 42
        mpath.write_text(json.dumps(data))
        self.assertEqual(ing.delete_packet(d), 1)
        self.assertTrue((d / "transcript.srt").exists())
        self.assertTrue((d / ".ingest-run").exists())

    def test_delete_refuses_when_assessment_itself_raises(self):
        # Deletion without a verdict would be deletion without the offer.
        d = self.make_packet("p", items=["o/r#1"])
        original = ing.sweep_packet

        def boom(out_dir, check_cmd=None):
            raise RuntimeError("assessment exploded")

        ing.sweep_packet = boom
        self.addCleanup(lambda: setattr(ing, "sweep_packet", original))
        self.assertEqual(ing.delete_packet(d), 1)
        self.assertTrue((d / "transcript.srt").exists())

    def test_a_pre_existing_empty_directory_is_not_pruned(self):
        # MINOR 10: only directories the deletion itself emptied are pruned —
        # an empty directory the decider made is not ours.
        d = self.make_packet("p", items=["o/r#1"])
        (d / "keep-me").mkdir()
        self.all_closed()
        self.assertEqual(ing.delete_packet(d), 5)
        self.assertTrue((d / "keep-me").is_dir())
        self.assertTrue((d / ".ingest-run").exists())

    def test_sweep_report_never_deletes(self):
        d = self.make_packet("p", items=["o/r#1"])
        self.all_closed()

        class A:
            home = str(self.home)
            check_cmd = None
            delete = []

        ing.cmd_sweep(A())
        self.assertTrue(d.exists())
        self.assertTrue((d / "transcript.srt").exists())


class TestSweepDeleteCli(SweepBase):
    """--delete is bounded by --home, processes every target, and reports
    an honest aggregate."""

    def all_closed(self):
        self.respond(lambda argv: FakeProc(stdout="closed\n"))

    def run_sweep(self, home, deletes, check_cmd=None):
        class A:
            pass
        A.home = str(home)
        A.check_cmd = check_cmd
        A.delete = list(deletes)
        with self.assertRaises(SystemExit) as cm:
            ing.cmd_sweep(A)
        return cm.exception.code

    def test_a_nonexistent_home_is_refused_before_any_deletion(self):
        # MAJOR 5 (reproduced upstream): --home was ignored on the delete
        # path — a bogus home plus an outside target still deleted.
        d = self.make_packet("p", items=["o/r#1"])
        self.all_closed()
        code = self.run_sweep(self.home / "no-such-home", [str(d)])
        self.assertEqual(code, 2)
        self.assertTrue((d / "transcript.srt").exists(), "nothing deleted")

    def test_a_target_outside_home_is_refused(self):
        inside_home = self.home / "the-home"
        inside_home.mkdir()
        d = self.make_packet("p", items=["o/r#1"])   # NOT under the-home
        self.all_closed()
        code = self.run_sweep(inside_home, [str(d)])
        self.assertEqual(code, 2)
        self.assertTrue((d / "transcript.srt").exists())

    def test_all_targets_processed_and_the_aggregate_is_honest(self):
        # MINOR 11: a refused first target must not stop the second, and the
        # exit code carries the worst outcome, not the last one.
        good = self.make_packet("good", items=["o/r#1"])
        foreign = self.home / "documents"
        foreign.mkdir()
        (foreign / "taxes.pdf").write_text("important")
        self.all_closed()
        code = self.run_sweep(self.home, [str(foreign), str(good)])
        self.assertEqual(code, 2)
        self.assertFalse(good.exists(), "the deletable target was processed")
        self.assertTrue((foreign / "taxes.pdf").exists())

    def test_all_targets_deleted_exits_zero(self):
        a = self.make_packet("a", items=["o/r#1"])
        b = self.make_packet("b", items=["o/r#2"])
        self.all_closed()
        code = self.run_sweep(self.home, [str(a), str(b)])
        self.assertEqual(code, 0)
        self.assertFalse(a.exists())
        self.assertFalse(b.exists())


if __name__ == "__main__":
    unittest.main()

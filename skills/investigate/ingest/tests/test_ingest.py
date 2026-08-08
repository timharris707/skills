"""Tests for ingest.py — the defects the advisory board found, pinned.

Every case here failed on v1.0.0 (`~/.advisory-board/runs/ingest-skill-red-team-2026-08-06`).
Standard library only, no network, no media: the pipeline's mechanical
invariants are testable without ever invoking ffmpeg or whisper.

Run:  python3 -m unittest discover -s tests -t tests
"""
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
    guarantees no test ever reaches gh or the network."""

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

    def test_link_is_idempotent(self):
        d = self.make_packet("p")
        ing.main(["link", "--out", str(d), "--item", "owner/repo#12"])
        ing.main(["link", "--out", str(d),
                  "--item", "owner/repo#12", "--item", "owner/repo#13"])
        items = json.loads((d / "manifest.json").read_text())["derived_items"]
        self.assertEqual(
            [i["id"] for i in items], ["owner/repo#12", "owner/repo#13"]
        )

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

    def test_binding_doc_command_resolves_other_trackers(self):
        self.respond(lambda argv: FakeProc(returncode=0))
        state, _ = ing.check_item_resolution(
            "JIRA-42", check_cmd="check-resolved {id}"
        )
        self.assertEqual(state, "resolved")
        self.assertEqual(self.calls[0][-1], "check-resolved JIRA-42")

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


class TestSweepDeletion(SweepBase):
    """Offer-only, re-checked, and by ledger — the v1.1.0 ownership rules."""

    def all_closed(self):
        self.respond(lambda argv: FakeProc(stdout="closed\n"))

    def test_refuses_a_directory_ingest_did_not_create(self):
        foreign = self.home / "documents"
        foreign.mkdir()
        (foreign / "taxes.pdf").write_text("important")
        with self.assertRaises(SystemExit) as cm:
            ing.delete_packet(foreign)
        self.assertEqual(cm.exception.code, 2)
        self.assertTrue((foreign / "taxes.pdf").exists())

    def test_refuses_while_derived_work_is_open(self):
        d = self.make_packet("p", items=["o/r#1"])
        self.respond(lambda argv: FakeProc(stdout="open\n"))
        with self.assertRaises(SystemExit) as cm:
            ing.delete_packet(d)
        self.assertEqual(cm.exception.code, 1)
        self.assertTrue((d / "transcript.srt").exists())

    def test_refuses_an_unlinked_packet(self):
        # No recorded derived work proves no terminal state — deletion is
        # never offered off silence.
        d = self.make_packet("p")
        with self.assertRaises(SystemExit) as cm:
            ing.delete_packet(d)
        self.assertEqual(cm.exception.code, 1)
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
        ing.delete_packet(d)
        self.assertFalse(d.exists(), "a fully-ledgered packet is removed")

    def test_a_foreign_file_survives_and_keeps_the_directory(self):
        d = self.make_packet("p", items=["o/r#1"],
                             extra_files=["notes/my-own-notes.md"])
        self.all_closed()
        ing.delete_packet(d)
        self.assertTrue((d / "notes" / "my-own-notes.md").exists())
        self.assertTrue(d.exists(), "a dir still holding foreign files stays")
        self.assertFalse((d / "transcript.srt").exists())

    def test_a_ledger_path_outside_the_packet_is_refused(self):
        d = self.make_packet("p", items=["o/r#1"])
        outsider = self.home / "not-the-packet.mp4"
        outsider.write_text("someone else's file")
        m = ing.Manifest(d, identity_hash="abc")
        m.finish("fetch", [outsider])
        self.all_closed()
        ing.delete_packet(d)
        self.assertTrue(outsider.exists())

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


if __name__ == "__main__":
    unittest.main()

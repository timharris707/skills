"""Offline regressions for packaged Advisory Board helper behavior."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'plugins/clickai-codex/skills/decide/advisory-board/scripts'


class AdvisoryHelperTests(unittest.TestCase):
    def run_helper_check(self, code):
        subprocess.run([sys.executable, '-c', code, str(SCRIPTS)],
                       env={**os.environ, 'PYTHONPATH': str(SCRIPTS)}, check=True)

    def test_missing_verdicts_do_not_count_as_opinion_changes(self):
        self.run_helper_check('''from types import SimpleNamespace
from _conductor.echo_score import echo_score, _band
def seat(name, verdict):
    return SimpleNamespace(seat=name, usable=True, verdict=verdict,
        stdout=f"`{name}.py:1`", basis="independent", provider=name)
for before, after in [(None, "ship"), ("ship", None), (None, None)]:
    score = echo_score([seat("a", before), seat("b", "ship")],
                       [seat("a", after), seat("b", "ship")])
    assert score["flippers"] == score["flippers_toward_majority"] == 0
    assert score["band"] == "low"
assert _band(1, 2, 0, 0, False) == "moderate", "Retain the tested half-of-seats threshold"
''')

    def test_packet_record_matches_the_approval_path(self):
        self.run_helper_check('''from types import SimpleNamespace
from unittest.mock import patch
from _conductor import rounds
from _conductor.egress import PacketBlob, EgressApproval, packet_hash
blob = PacketBlob("fixture", "local", "fixture.prompt", "approved material")
config = SimpleNamespace(rubric=True, grounding=None, grounded=False,
                         fs_scoped=False, board=[SimpleNamespace(id="fixture")])
approval = EgressApproval(True, "hash-bound", packet_hash([blob]), "fixture", "fixture")
def result(*args, **kwargs):
    return rounds.SeatRoundResult(seat="fixture", provider="local", round_no=1,
        model_requested="fixture", model_answered=None, status="ran", failure_class=None,
        attempts=1, elapsed_s=0, exit_code=0, timed_out=False, stdout="VERDICT: ship",
        stderr="", prompt_hash=blob.sha256, source_hash=blob.sha256,
        round_packet_hash=packet_hash([blob]), argv_preview="fixture",
        criterion_ids=("c1",))
for carried in [True, False]:
    with patch.object(rounds, "_run_seat_round", side_effect=result), \\
         patch.object(rounds, "build_packet", return_value=[blob]):
        records = rounds.run_round(config, [blob], approval, parallel=False,
            criterion_ids=("c1",), rubric_pre_consent=carried)
    text = rounds.render_raw_record(records[0])
    assert ("egress consent was bound to this" in text) == carried
    assert ("rubric-scored round-1 packet" in text) != carried
approval.content_hash = "unapproved"
with patch.object(rounds, "_run_seat_round") as spawn:
    try:
        rounds.run_round(config, [blob], approval, parallel=False, rubric_pre_consent=True)
    except SystemExit as error:
        assert error.code == 3
    else:
        raise AssertionError("Unapproved material reached the worker")
    spawn.assert_not_called()
''')

    def test_font_builder_uses_its_installed_location(self):
        self.run_helper_check('''import io, os, runpy, shutil, sys, tempfile
from pathlib import Path
from unittest.mock import patch
css = b"@font-face { font-style: normal; font-weight: 400; src: url(https://example.invalid/font.woff2); unicode-range: U+0000-00FF; }"
def response(request, **kwargs):
    return io.BytesIO(css if "fonts.googleapis.com" in request.full_url else b"fixture font")
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp); scripts = root / "installed/scripts"; scripts.mkdir(parents=True)
    references = scripts.parent / "references"; references.mkdir()
    source = scripts / "_embed_fonts.py"
    shutil.copy2(Path(sys.argv[1]) / source.name, source)
    unrelated = root / "unrelated"; unrelated.mkdir(); os.chdir(unrelated)
    with patch("urllib.request.urlopen", side_effect=response):
        runpy.run_path(str(source))
    generated = (references / "plan-fonts.css").read_text()
    assert generated.count("@font-face") == 2
    assert "data:font/woff2;base64," in generated
    assert not list(unrelated.iterdir())
''')


if __name__ == '__main__':
    unittest.main()

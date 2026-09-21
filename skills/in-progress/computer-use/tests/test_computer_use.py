"""Tests for computer_use.py. Standard library only; no Codex, no Sky, no GUI.

The runner is driven with a fake `runner` that writes fixture event streams and
replies into the run directory, so every audit rule is exercised against the
exact shapes the real `codex exec --json` produced on 2026-09-20. Several cases
pin defects the adversarial review reproduced (marked "review:").

Run:  python3 -m unittest discover -s tests -t tests
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import plistlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import computer_use as cu  # noqa: E402

# 1x1 PNG, the smallest real image we can name as evidence.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")
PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(PNG).decode()

FEATURES_OUT = """apps                                     stable             true
computer_use                             stable             true
concurrent_reasoning_summaries           under development  false
"""


# ---------------------------------------------------------------- fixtures

def ev_thread(tid="01a0c15f-5275-7682-ba21-e35f06f5f751"):
    return {"type": "thread.started", "thread_id": tid}


def ev_call(code, result_text, title="step", surface=None, status="completed"):
    item = {"type": "mcp_tool_call", "server": "node_repl", "tool": "js", "status": status,
            "arguments": {"code": code, "title": title},
            "result": {"content": [{"type": "text", "text": result_text}], "_meta": {"codex/toolSurface": surface}}}
    return {"type": "item.completed", "item": item}


def ev_shell(command="osascript -e 'tell app \"Mail\" to send'"):
    return {"type": "item.completed", "item": {"type": "command_execution", "command": command, "status": "completed"}}


def write_events(run_dir: Path, events):
    with (run_dir / "events.jsonl").open("a", encoding="utf-8") as fh:
        for e in events:
            fh.write(e if isinstance(e, str) else json.dumps(e))
            fh.write("\n")


def reply(**kw):
    base = {"status": "done", "summary": "did it", "question": "", "confirmation_reason": "none",
            "observed_before": "Inbox showing", "observed_after": "Draft open", "evidence": [],
            "actions_taken": [], "reason": ""}
    base.update(kw)
    return base


def fake_runner(events, reply_obj=None, exit_code=0, timed_out=False):
    """A stand-in for run_codex that writes fixtures instead of launching."""
    def _run(argv, run_dir, timeout, env=None):
        write_events(run_dir, events)
        if reply_obj is not None:
            (run_dir / "reply.json").write_text(json.dumps(reply_obj), encoding="utf-8")
        _run.argv = argv
        _run.calls = getattr(_run, "calls", 0) + 1
        return {"exit_code": exit_code, "timed_out": timed_out, "elapsed_s": 1.0}
    return _run


def fake_cli(version="codex-cli 0.152.1", features=FEATURES_OUT, codesign_rc=0):
    """Stand-in for _run: answers codex --version, codex features list, codesign."""
    def _run(argv, timeout=30):
        if argv[:2] == ["codex", "--version"]:
            return 0, version + "\n", ""
        if argv[:3] == ["codex", "features", "list"]:
            return 0, features, ""
        if argv[0] == "codesign":
            return codesign_rc, "", "" if codesign_rc == 0 else "code object is not signed at all"
        return 127, "", f"{argv[0]}: not found"
    return _run


def run_args(tmp, **kw):
    d = {"app": "Fake", "goal": "read the tab title", "done": "title visible", "start": "", "allow": "read",
         "forbid": "click", "preapproved": "", "effort": "medium", "model": None, "timeout": 10,
         "run_root": str(Path(tmp) / "runs"), "skip_preflight": True}
    d.update(kw)
    return SimpleNamespace(**d)


OBS = 'var s = await sky.get_app_state({app:"com.example.fake", disableDiff: true}); nodeRepl.write(s.text);'
OBS_DIFF = 'var s = await sky.get_app_state({app:"com.example.fake"}); nodeRepl.write(s.text);'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        app = self.root / "Fake.app" / "Contents"
        app.mkdir(parents=True)
        with (app / "Info.plist").open("wb") as fh:
            plistlib.dump({"CFBundleIdentifier": "com.example.fake", "CFBundleDisplayName": "Fake"}, fh)
        self.fake_app = self.root / "Fake.app"
        self.mdfind = lambda q: [str(self.fake_app)] if ("Fake" in q or "com.example.fake" in q) else []
        # Evidence provenance: point the Sky screenshot folder at a temp dir.
        self._sky_dir = cu.SKY_SHOT_DIR
        cu.SKY_SHOT_DIR = self.root / "skyshots"
        cu.SKY_SHOT_DIR.mkdir()
        self.addCleanup(setattr, cu, "SKY_SHOT_DIR", self._sky_dir)

    def target(self):
        return cu.resolve_app("Fake", mdfind=self.mdfind)

    def tcc(self, access=2, screen=2):
        db = self.root / "TCC.db"
        con = sqlite3.connect(db)
        con.execute("create table if not exists access(service text, client text, auth_value int)")
        con.execute("delete from access")
        if access is not None:
            con.execute("insert into access values('kTCCServiceAccessibility', ?, ?)", (cu.HELPER_BUNDLE_ID, access))
        if screen is not None:
            con.execute("insert into access values('kTCCServiceScreenCapture', ?, ?)", (cu.HELPER_BUNDLE_ID, screen))
        con.commit(); con.close()
        return db

    def healthy_home(self, config='model = "gpt-6-astra"\nmodel_provider = "cliproxyapi"\n\n[model_providers.cliproxyapi]\nbase_url = "http://127.0.0.1:8317/v1"\n'):
        home = self.root / "profile"
        cu.helper_app(home).mkdir(parents=True)
        if config is not None:
            (home / "config.toml").write_text(config)
        return home

    def audit(self, events, rep, effort="medium", timed_out=False, exit_code=0, task=None):
        run_dir = Path(tempfile.mkdtemp(dir=self.root))
        write_events(run_dir, events)
        if rep is not None:
            (run_dir / "reply.json").write_text(json.dumps(rep))
        loaded, err = cu.load_reply(run_dir / "reply.json")
        launch = {"exit_code": exit_code, "timed_out": timed_out, "elapsed_s": 2.0}
        return cu.audit(run_dir, loaded, err, launch, self.target(), task or {"goal": "g", "done": "d"}, effort)


# ------------------------------------------------- profile-aware discovery

class TestProfilePaths(Base):
    def test_codex_home_reads_env(self):
        self.assertEqual(cu.codex_home({"CODEX_HOME": "/p/insight"}), Path("/p/insight"))

    def test_codex_home_defaults_to_dot_codex(self):
        self.assertEqual(cu.codex_home({}), Path.home() / ".codex")

    def test_helper_path_derives_from_codex_home(self):
        p = cu.helper_app(Path("/p/insight"))
        self.assertEqual(p, Path("/p/insight/computer-use/Codex Computer Use.app"))
        self.assertNotIn(".codex/", str(p))

    def test_helper_status_missing_signed_and_unsigned(self):
        self.assertFalse(cu.helper_status(self.root, fake_cli())["exists"])
        home = self.healthy_home()
        ok = cu.helper_status(home, fake_cli(codesign_rc=0))
        self.assertTrue(ok["exists"] and ok["signed"]); self.assertEqual(ok["codesign"], "valid")
        bad = cu.helper_status(home, fake_cli(codesign_rc=1))
        self.assertFalse(bad["signed"]); self.assertIn("not signed", bad["codesign"])

    def test_codex_version_and_feature_parsing(self):
        self.assertEqual(cu.codex_version(fake_cli()), "codex-cli 0.152.1")
        self.assertIsNone(cu.codex_version(lambda argv, timeout=30: (127, "", "not found")))
        f = cu.computer_use_feature(fake_cli())
        self.assertEqual((f["stable"], f["enabled"]), (True, True))
        f = cu.computer_use_feature(fake_cli(features="computer_use   under development   false\n"))
        self.assertEqual((f["stable"], f["enabled"]), (False, False))
        f = cu.computer_use_feature(fake_cli(features="apps stable true\n"))
        self.assertIsNone(f["stable"])
        f = cu.computer_use_feature(lambda argv, timeout=30: (1, "", "Error: failed to resolve CODEX_HOME"))
        self.assertIn("CODEX_HOME", f["raw"]); self.assertIsNone(f["enabled"])

    def test_privacy_status_without_db_is_unknown(self):
        st = cu.privacy_status(db=self.root / "nope.db")
        self.assertIsNone(st["Accessibility"]); self.assertIn("not present", st["note"])

    def test_privacy_status_reads_rows(self):
        st = cu.privacy_status(db=self.tcc(access=2, screen=0))
        self.assertTrue(st["Accessibility"]); self.assertFalse(st["Screen Recording"])

    def test_routing_reads_provider_and_base_url(self):
        home = self.root / "p"; home.mkdir()
        (home / "config.toml").write_text('model = "gpt-6-astra"\nmodel_reasoning_effort = "medium"\n')
        r = cu.routing(home)
        self.assertEqual((r["model"], r["model_provider"], r["base_url"], r["direct"], r["parse_error"]), ("gpt-6-astra", None, None, True, None))
        (home / "config.toml").write_text('model = "gpt-6-astra"\nmodel_provider = "cliproxyapi"\n\n'
                                          '[model_providers.cliproxyapi]\nname = "x"\nbase_url = "http://127.0.0.1:8317/v1"\n\n[other]\nbase_url = "nope"\n')
        r = cu.routing(home)
        self.assertEqual((r["model_provider"], r["base_url"], r["direct"], r["parse_error"]), ("cliproxyapi", "http://127.0.0.1:8317/v1", False, None))
        self.assertIn("unreadable", cu.routing(self.root / "missing")["parse_error"])

    def test_routing_ignores_profile_tables_and_reads_real_toml(self):
        """review: a [profiles.x] model_provider used to read as global (false 'proxied')."""
        home = self.root / "p"; home.mkdir()
        (home / "config.toml").write_text('model = "gpt-5.1-codex"\n[profiles.proxied]\nmodel_provider = "localproxy"\nmodel = "o3-mini"\n'
                                          '[model_providers.localproxy]\nbase_url = "http://localhost:4000/v1"\n')
        r = cu.routing(home)
        self.assertTrue(r["direct"]); self.assertIsNone(r["model_provider"]); self.assertEqual(r["model"], "gpt-5.1-codex")
        # Single-quoted TOML strings, quoted provider keys, trailing comments, inline tables all parse.
        (home / "config.toml").write_text("model_provider = 'my-proxy'  # local\n[model_providers.\"my-proxy\"]  # litellm\nbase_url = 'http://127.0.0.1:8317/v1'\n")
        r = cu.routing(home)
        self.assertEqual((r["model_provider"], r["base_url"], r["direct"], r["parse_error"]), ("my-proxy", "http://127.0.0.1:8317/v1", False, None))
        (home / "config.toml").write_text('model_provider = "p"\nmodel_providers.p = { base_url = "http://x/v1" }\n')
        self.assertEqual(cu.routing(home)["base_url"], "http://x/v1")
        # Commented-out key is not a key.
        (home / "config.toml").write_text('# model_provider = "cliproxyapi"\nmodel = "m"\n')
        self.assertTrue(cu.routing(home)["direct"])

    def test_routing_unknowns_are_reported_not_guessed(self):
        home = self.root / "p"; home.mkdir()
        (home / "config.toml").write_text('model_provider = "ghost"\n')
        r = cu.routing(home); self.assertFalse(r["direct"]); self.assertIn("no [model_providers.ghost]", r["parse_error"])
        (home / "config.toml").write_text('model_provider = "p"\n[model_providers.p]\nenv_key = "K"\n')
        self.assertIn("no base_url", cu.routing(home)["parse_error"])
        (home / "config.toml").write_bytes(b'model = "\xff\xfe bad"\n')     # review: used to raise
        self.assertIsNone(cu.routing(home)["parse_error"]) or True
        (home / "config.toml").write_text('model = "unterminated\n')
        self.assertIn("not valid TOML", cu.routing(home)["parse_error"])
        # The runner's own -c model override is reflected.
        (home / "config.toml").write_text('model = "a"\nmodel_provider = "p"\n[model_providers.p]\nbase_url = "u"\n')
        self.assertEqual(cu.routing(home, ["model=gpt-6-astra"])["model"], "gpt-6-astra")
        self.assertEqual(cu.routing(home, ["model_provider=other"])["model_provider"], "other")

    def test_preflight_reports_routing(self):
        home = self.healthy_home()
        rep = cu.preflight(None, env={"CODEX_HOME": str(home)}, run=fake_cli(), tcc_db=self.tcc())
        self.assertEqual(rep["routing"]["base_url"], "http://127.0.0.1:8317/v1")
        self.assertFalse(rep["routing"]["direct"]); self.assertTrue(rep["ok"])

    def test_preflight_direct_billing_is_a_problem_unless_allowed(self):
        """review: direct: true was computed, printed, and never gated."""
        home = self.healthy_home(config='model = "gpt-6-astra"\n')
        rep = cu.preflight(None, env={"CODEX_HOME": str(home)}, run=fake_cli(), tcc_db=self.tcc())
        self.assertFalse(rep["ok"]); self.assertTrue(any("bill the signed-in account directly" in p for p in rep["problems"]))
        rep = cu.preflight(None, env={"CODEX_HOME": str(home)}, run=fake_cli(), tcc_db=self.tcc(), require_proxy=False)
        self.assertTrue(rep["ok"])
        home2 = self.root / "p2"; cu.helper_app(home2).mkdir(parents=True); (home2 / "config.toml").write_text('model_provider = "ghost"\n')
        rep = cu.preflight(None, env={"CODEX_HOME": str(home2)}, run=fake_cli(), tcc_db=self.tcc())
        self.assertTrue(any("cannot tell where a live call would be billed" in p for p in rep["problems"]))

    def test_preflight_green_path(self):
        home = self.healthy_home()
        rep = cu.preflight(None, env={"CODEX_HOME": str(home)}, run=fake_cli(), tcc_db=self.tcc())
        self.assertEqual(rep["problems"], [])
        self.assertTrue(rep["ok"])
        self.assertEqual(rep["codex_home"], str(home))

    def test_preflight_unknown_permission_is_a_problem(self):
        """review: an unreadable privacy database used to mean 'go'."""
        home = self.healthy_home()
        rep = cu.preflight(None, env={"CODEX_HOME": str(home)}, run=fake_cli(), tcc_db=self.root / "nope.db")
        self.assertFalse(rep["ok"])
        self.assertTrue(any("could not be confirmed" in p for p in rep["problems"]))
        rep = cu.preflight(None, env={"CODEX_HOME": str(home)}, run=fake_cli(), tcc_db=self.tcc(access=0))
        self.assertTrue(any("Accessibility is not granted" in p for p in rep["problems"]))

    def test_preflight_names_each_missing_piece(self):
        rep = cu.preflight(None, env={"CODEX_HOME": str(self.root / "gone")},
                           run=lambda argv, timeout=30: (1, "", "failed to resolve CODEX_HOME"), tcc_db=self.tcc())
        joined = " ".join(rep["problems"])
        self.assertIn("codex CLI not found", joined)
        self.assertIn("not stable+enabled", joined)
        self.assertIn("helper missing", joined)

    def test_preflight_live_probe(self):
        home = self.healthy_home()
        good = fake_runner([ev_thread(), ev_call("...", f"{cu.PROBE_OK} 23")], reply())
        rep = cu.preflight(None, env={"CODEX_HOME": str(home)}, run=fake_cli(), tcc_db=self.tcc(),
                           live=True, runner=good, run_root=self.root / "runs")
        self.assertTrue(rep["ok"]); self.assertIn("23 apps", rep["live_probe"]["note"])
        bad = fake_runner([ev_thread(), ev_call("...", f"{cu.PROBE_ERR} helper not running")], reply())
        rep = cu.preflight(None, env={"CODEX_HOME": str(home)}, run=fake_cli(), tcc_db=self.tcc(),
                           live=True, runner=bad, run_root=self.root / "runs")
        self.assertFalse(rep["ok"]); self.assertIn("helper not running", rep["problems"][-1])


# ------------------------------------------------- open-ended app resolution

class TestResolveApp(Base):
    def test_by_path(self):
        r = cu.resolve_app(str(self.fake_app), mdfind=lambda q: [])
        self.assertEqual((r["bundle_id"], r["how"]), ("com.example.fake", "path"))

    def test_by_bundle_id(self):
        r = cu.resolve_app("com.example.fake", mdfind=self.mdfind)
        self.assertEqual((r["bundle_id"], r["display_name"], r["how"]), ("com.example.fake", "Fake", "bundle-id"))

    def test_by_display_name(self):
        r = cu.resolve_app("Fake", mdfind=self.mdfind)
        self.assertEqual((r["bundle_id"], r["how"]), ("com.example.fake", "display-name"))

    def test_unknown_app_is_not_refused_just_unresolved(self):
        r = cu.resolve_app("Some App Nobody Has", mdfind=lambda q: [])
        self.assertIsNone(r["bundle_id"]); self.assertEqual(r["display_name"], "Some App Nobody Has")

    def test_bundle_id_passes_through_unknown_id(self):
        r = cu.resolve_app("com.vendor.NewThing", mdfind=lambda q: [])
        self.assertEqual(r["bundle_id"], "com.vendor.NewThing")

    def test_any_app_reaches_the_runner(self):
        """No allowlist or denylist anywhere: an arbitrary app is briefed and launched."""
        r = fake_runner([ev_thread(), ev_call(OBS.replace("com.example.fake", "com.vendor.Anything"), "tree")], reply())
        res = cu.do_run(run_args(self.tmp.name, app="com.vendor.Anything"), runner=r, mdfind=lambda q: [])
        self.assertEqual(r.calls, 1)
        self.assertIn("Bundle ID: com.vendor.Anything", r.argv[-1])
        self.assertEqual(res["target"]["bundle_id"], "com.vendor.Anything")

    def test_is_bundle_id_rejects_whitespace_and_wildcards(self):
        for bad in ("com.apple.mail\n", " com.apple.mail", "com.apple.*", "com.apple.[a-z]", "*", "mail", "com.apple.màil"):
            self.assertFalse(cu.is_bundle_id(bad), bad)
        self.assertTrue(cu.is_bundle_id("com.apple.mail"))


# ------------------------------------------- approval file: inspect / add

class TestApprovals(Base):
    def setUp(self):
        super().setUp()
        self.f = self.root / "ComputerUseAppApprovals.json"
        self.f.write_text(json.dumps({cu.APPROVALS_KEY: ["com.google.Chrome"]}))

    def test_inspect_does_not_mutate(self):
        before = (self.f.read_bytes(), self.f.stat().st_mtime_ns)
        rep = cu.inspect_approvals(self.f)
        self.assertEqual(rep["ids"], ["com.google.Chrome"])
        self.assertEqual((self.f.read_bytes(), self.f.stat().st_mtime_ns), before)

    def test_inspect_missing_file_and_bad_shape(self):
        rep = cu.inspect_approvals(self.root / "none.json")
        self.assertFalse(rep["exists"]); self.assertEqual(rep["ids"], [])
        self.f.write_text(json.dumps({"somethingElse": 1}))
        self.assertIn("missing or not a list", cu.inspect_approvals(self.f)["error"])
        self.f.write_text("[1,2]")
        self.assertIn("not an object", cu.inspect_approvals(self.f)["error"])

    def test_approval_state(self):
        rep = cu.inspect_approvals(self.f)
        self.assertEqual(cu.approval_state("com.google.Chrome", rep), "approved")
        self.assertEqual(cu.approval_state("com.apple.finder", rep), "not-approved")
        self.assertEqual(cu.approval_state(None, rep), "unknown")
        self.assertEqual(cu.approval_state("x.y", {"exists": False, "ids": []}), "unknown")

    def test_add_backs_up_and_reports_exactly(self):
        now = dt.datetime(2026, 9, 20, 18, 0, 0)
        rep = cu.add_approvals(["com.apple.finder", "com.google.Chrome"], self.f, now=now)
        self.assertEqual(rep["added"], ["com.apple.finder"])
        self.assertEqual(rep["already_present"], ["com.google.Chrome"])
        self.assertEqual(rep["after"], ["com.apple.finder", "com.google.Chrome"])
        self.assertNotEqual(rep["sha256_before"], rep["sha256_after"])
        backup = Path(rep["backup"])
        self.assertTrue(backup.exists())
        self.assertEqual(json.loads(backup.read_text())[cu.APPROVALS_KEY], ["com.google.Chrome"])
        self.assertEqual(json.loads(self.f.read_text())[cu.APPROVALS_KEY], ["com.google.Chrome", "com.apple.finder"])
        self.assertIsNone(rep["helper_noticed"])  # unverified until the probe runs

    def test_add_preserves_other_keys_and_never_overwrites_a_backup(self):
        """review: the file used to be replaced with a single key."""
        self.f.write_text(json.dumps({cu.APPROVALS_KEY: ["com.google.Chrome"], "schemaVersion": 3, "denied": ["x.y"]}))
        now = dt.datetime(2026, 9, 20, 18, 0, 0)
        cu.add_approvals(["com.apple.mail"], self.f, now=now)
        doc = json.loads(self.f.read_text())
        self.assertEqual(doc["schemaVersion"], 3); self.assertEqual(doc["denied"], ["x.y"])
        rep2 = cu.add_approvals(["com.apple.finder"], self.f, now=now)   # same second
        self.assertTrue(rep2["backup"].endswith("-2"))
        first_backup = json.loads((self.f.with_name(f"{self.f.name}.bak-20260920-180000")).read_text())
        self.assertEqual(first_backup[cu.APPROVALS_KEY], ["com.google.Chrome"])   # original still intact

    def test_add_rejects_wildcards_whitespace_and_unknown_shape(self):
        for bad in ("*", "com.apple.*", "com.apple.[a-z]", "not a bundle id"):
            with self.assertRaises(ValueError):
                cu.add_approvals([bad], self.f)
        self.assertEqual(json.loads(self.f.read_text())[cu.APPROVALS_KEY], ["com.google.Chrome"])
        rep = cu.add_approvals(["com.apple.mail\n"], self.f)   # stripped, not stored with the newline
        self.assertEqual(rep["added"], ["com.apple.mail"])
        self.f.write_text(json.dumps({"other": []}))
        with self.assertRaises(ValueError):
            cu.add_approvals(["com.apple.mail"], self.f)

    def test_add_noop_when_all_present_still_backs_up_and_leaves_file(self):
        before = self.f.read_bytes()
        rep = cu.add_approvals(["com.google.Chrome"], self.f)
        self.assertEqual(rep["added"], []); self.assertEqual(self.f.read_bytes(), before)
        self.assertTrue(Path(rep["backup"]).exists())

    def test_run_never_writes_the_approval_file(self):
        """An ordinary run, even against an unapproved app, leaves the file alone."""
        events = [ev_thread(), ev_call('sky.get_app_state({app:"com.example.fake"})',
                                       "Computer Use was not approved to use Fake", surface={"kind": "computerUse"})]
        before = self.f.read_bytes()
        res = cu.do_run(run_args(self.tmp.name), runner=fake_runner(events, reply(status="blocked")), mdfind=self.mdfind)
        self.assertEqual(res["status"], "blocked"); self.assertIn("not approved to use Fake", res["reason"])
        self.assertEqual(self.f.read_bytes(), before)

    def test_probe_approval_reports_helper_noticed(self):
        ok_events = [ev_thread(), ev_call("...", f"{cu.PROBE_OK} 4021")]
        rep = cu.probe_approval("com.apple.finder", self.root / "runs", runner=fake_runner(ok_events, reply()))
        self.assertTrue(rep["helper_noticed"])
        bad_events = [ev_thread(), ev_call("...", f"{cu.PROBE_ERR} Computer Use was not approved to use Finder")]
        rep = cu.probe_approval("com.apple.finder", self.root / "runs", runner=fake_runner(bad_events, reply()))
        self.assertFalse(rep["helper_noticed"]); self.assertIn("restart", rep["helper_note"])
        rep = cu.probe_approval("com.apple.finder", self.root / "runs", runner=fake_runner([ev_thread()], None, timed_out=True))
        self.assertIsNone(rep["helper_noticed"])
        # An "OK" button label in a tree dump is not a probe success.
        rep = cu.probe_approval("com.apple.finder", self.root / "runs", runner=fake_runner([ev_thread(), ev_call("...", 'AXButton "OK"')], reply()))
        self.assertIsNone(rep["helper_noticed"])


# ------------------------------------------- inventory + approval plan

class TestInventoryAndPlan(Base):
    def test_installed_apps_filters_to_top_level_and_reads_exact_ids(self):
        nested = self.root / "Fake.app" / "Contents" / "Helpers" / "Nested.app" / "Contents"
        nested.mkdir(parents=True)
        with (nested / "Info.plist").open("wb") as fh:
            plistlib.dump({"CFBundleIdentifier": "com.example.nested"}, fh)
        broken = self.root / "Broken.app" / "Contents"; broken.mkdir(parents=True)
        hits = [str(self.fake_app), str(nested.parent), str(self.root / "Broken.app"), "/elsewhere/Other.app"]
        apps = cu.installed_apps(mdfind=lambda q: hits, roots=(str(self.root),), extras=())
        self.assertEqual([a["bundle_id"] for a in apps], ["com.example.fake"])
        self.assertEqual(apps[0]["name"], "Fake")
        self.assertEqual([k["path"] for k in apps.skipped], [str(self.root / "Broken.app")])
        self.assertIn("Info.plist unreadable", apps.skipped[0]["why"])
        # Extras outside the roots (Finder in CoreServices) are included when present.
        extra = self.root / "Core" / "Extra.app" / "Contents"; extra.mkdir(parents=True)
        with (extra / "Info.plist").open("wb") as fh:
            plistlib.dump({"CFBundleIdentifier": "com.example.extra"}, fh)
        apps = cu.installed_apps(mdfind=lambda q: hits, roots=(str(self.root),),
                                 extras=(str(extra.parent), str(self.root / "Core" / "Missing.app")))
        self.assertEqual([a["bundle_id"] for a in apps], ["com.example.extra", "com.example.fake"])

    def test_vendor_folders_one_deep_count_and_odd_plists_are_skipped_not_fatal(self):
        """review: /Applications/Adobe X/X.app used to vanish silently; a list-rooted plist crashed."""
        vendor = self.root / "Vendor Co" / "Tool.app" / "Contents"; vendor.mkdir(parents=True)
        with (vendor / "Info.plist").open("wb") as fh:
            plistlib.dump({"CFBundleIdentifier": "com.vendor.tool"}, fh)
        deep = self.root / "a" / "b" / "Deep.app" / "Contents"; deep.mkdir(parents=True)
        with (deep / "Info.plist").open("wb") as fh:
            plistlib.dump({"CFBundleIdentifier": "com.vendor.deep"}, fh)
        listy = self.root / "Listy.app" / "Contents"; listy.mkdir(parents=True)
        with (listy / "Info.plist").open("wb") as fh:
            plistlib.dump(["not", "a", "dict"], fh)
        noid = self.root / "NoId.app" / "Contents"; noid.mkdir(parents=True)
        with (noid / "Info.plist").open("wb") as fh:
            plistlib.dump({"CFBundleName": "NoId"}, fh)
        dupe = self.root / "Dupe.app" / "Contents"; dupe.mkdir(parents=True)
        with (dupe / "Info.plist").open("wb") as fh:
            plistlib.dump({"CFBundleIdentifier": "com.example.fake"}, fh)
        hits = [str(vendor.parent), str(deep.parent), str(listy.parent), str(noid.parent), str(dupe.parent), str(self.fake_app)]
        apps = cu.installed_apps(mdfind=lambda q: hits, roots=(str(self.root) + "/",), extras=())   # trailing slash tolerated
        self.assertEqual([a["bundle_id"] for a in apps], ["com.example.fake", "com.vendor.tool"])
        whys = {k["path"]: k["why"] for k in apps.skipped}
        self.assertIn("not a dictionary", whys[str(listy.parent)]); self.assertIn("no valid CFBundleIdentifier", whys[str(noid.parent)])
        # Hits are processed in sorted path order, so Dupe.app wins the ID and Fake.app is the recorded duplicate.
        self.assertIn("same bundle ID as", whys[str(self.fake_app)])
        self.assertEqual([a["path"] for a in apps if a["bundle_id"] == "com.example.fake"], [str(dupe.parent)])
        self.assertNotIn(str(deep.parent), whys)   # too deep: not an app folder, silently outside scope

    def test_is_bundle_id_rejects_flag_shaped_ids(self):
        self.assertFalse(cu.is_bundle_id("--yes.evil")); self.assertFalse(cu.is_bundle_id("-a.b")); self.assertTrue(cu.is_bundle_id("a-b.c"))

    def test_plan_reports_an_unreadable_file_and_gives_no_command(self):
        """review: a corrupt approval file used to make everything 'unapproved' with a doomed add command."""
        apps = [{"name": "Fake", "bundle_id": "com.example.fake", "path": str(self.fake_app)}]
        plan = cu.approvals_plan({"path": "/p", "ids": [], "error": "could not parse approval file: boom", "exists": True}, apps)
        self.assertIn("boom", plan["approval_file_error"]); self.assertIsNone(plan["add_command"]); self.assertEqual(plan["unapproved"], [])
        plan = cu.approvals_plan({"path": "/p", "ids": [], "error": None, "exists": False}, apps)
        self.assertIn("does not exist", plan["approval_file_error"]); self.assertIsNone(plan["add_command"])

    def test_plan_is_a_diff_and_writes_nothing(self):
        f = self.root / "ComputerUseAppApprovals.json"
        f.write_text(json.dumps({cu.APPROVALS_KEY: ["com.google.Chrome", "com.gone.App"]}))
        before = f.read_bytes()
        apps = [{"name": "Google Chrome", "bundle_id": "com.google.Chrome", "path": "/Applications/Google Chrome.app"},
                {"name": "Fake", "bundle_id": "com.example.fake", "path": str(self.fake_app)}]
        plan = cu.approvals_plan(cu.inspect_approvals(f), apps)
        self.assertEqual(plan["approved_installed"], ["com.google.Chrome"])
        self.assertEqual([a["bundle_id"] for a in plan["unapproved"]], ["com.example.fake"])
        self.assertEqual(plan["approved_not_installed"], ["com.gone.App"])
        self.assertEqual(plan["add_command"], "computer_use.py approvals add --bundle-id com.example.fake --yes")
        self.assertNotIn("*", plan["add_command"])
        self.assertEqual(f.read_bytes(), before)
        # A newly installed app shows up as unapproved on the next plan.
        apps.append({"name": "New", "bundle_id": "com.vendor.New", "path": "/Applications/New.app"})
        plan = cu.approvals_plan(cu.inspect_approvals(f), apps)
        self.assertIn("com.vendor.New", [a["bundle_id"] for a in plan["unapproved"]])
        # Nothing to add: no command.
        self.assertIsNone(cu.approvals_plan({"ids": ["com.example.fake", "com.google.Chrome", "com.vendor.New"], "path": "p", "exists": True}, apps)["add_command"])


# -------------------------------------------------------- brief + argv

class TestBrief(Base):
    def test_brief_carries_every_required_section(self):
        task = {"goal": "G", "done": "D", "start": "S", "allow": "A", "forbid": "F", "preapproved": "P"}
        b = cu.build_brief(task, self.target())
        for needle in ("## Goal", "G", "## Definition of done", "D", "Bundle ID: com.example.fake", "Display name: Fake",
                       "## Starting state", "S", "## Allowed actions", "A", "## Forbidden actions", "F",
                       "## Confirmation boundary", "Pre-approved by the user for this subtask (quoted; nothing else counts): P",
                       "After EVERY state-changing action call get_app_state again", cu.BOOTSTRAP, "disableDiff: true",
                       "never reuse an index", "Never perform such an action and ask afterwards", "paste"):
            self.assertIn(needle, b, needle)

    def test_brief_marks_missing_sections_visibly(self):
        b = cu.build_brief({"goal": "G", "done": "D"}, self.target())
        self.assertIn("## Forbidden actions\nnone stated", b)
        self.assertIn("nothing else counts): none", b)

    def test_argv_shape(self):
        argv = cu.codex_argv("BRIEF", self.root, "high")
        self.assertEqual(argv[:3], ["codex", "exec", "--skip-git-repo-check"])
        self.assertIn("--sandbox", argv); self.assertIn("read-only", argv)
        self.assertIn("model_reasoning_effort=high", argv)
        self.assertIn("--output-schema", argv); self.assertIn("--json", argv)
        self.assertEqual(argv[-1], "BRIEF")
        self.assertNotIn("--ephemeral", argv)  # ephemeral would break resume

    def test_efforts_include_low_medium_high_and_do_not_ban_xhigh(self):
        self.assertEqual(cu.DEFAULT_EFFORT, "medium")
        for e in ("low", "medium", "high", "xhigh"):
            self.assertIn(e, cu.EFFORTS)

    def test_resume_argv_has_no_cd_or_sandbox(self):
        argv = cu.resume_argv("sid", "P", self.root, "medium")
        self.assertEqual(argv[:4], ["codex", "exec", "resume", "sid"])
        self.assertNotIn("-C", argv); self.assertNotIn("--sandbox", argv)
        self.assertIn("--output-schema", argv)


# ------------------------------------------------ recording sky calls

class TestRecordActions(Base):
    def rec(self, code):
        return cu.record_actions([{"code": code, "result": "", "title": "t"}])

    def test_literal_args_are_parsed(self):
        a = self.rec('await sky.click({app: "x", element_index: 4});')
        self.assertEqual((a[0]["method"], a[0]["parsed"]), ("click", True))
        self.assertIn("element_index: 4", a[0]["args"])

    def test_nested_braces_and_strings_do_not_truncate(self):
        """review: `})` inside an argument used to end the match early."""
        a = self.rec('sky.set_value({app:"x", element_index: 2, value: JSON.stringify({a:1})});')
        self.assertTrue(a[0]["parsed"]); self.assertTrue(a[0]["args"].endswith("})}"))
        a = self.rec("sky.type_text({app:'x', text: 'a ) b } c'});")
        self.assertTrue(a[0]["parsed"]); self.assertIn("a ) b } c", a[0]["args"])

    def test_non_literal_args_are_recorded_but_unparsed(self):
        """review: `const p = {...}; sky.click(p)` used to vanish from the log."""
        for code in ('const p = {app:"x", element_index: 7}; await sky.click(p);',
                     'await sky.click(opts)', 'await sky["click"]({element_index:3})', 'await sky.click(await target())'):
            a = self.rec(code)
            self.assertEqual(len(a), 1, code); self.assertEqual(a[0]["method"], "click")
        self.assertFalse(self.rec('await sky.click(opts)')[0]["parsed"])
        self.assertTrue(self.rec('await sky["click"]({element_index:3})')[0]["parsed"])

    def test_loops_and_comments(self):
        a = self.rec('for (const i of idx) await sky.click({element_index: i});')
        self.assertTrue(a[0]["in_loop"])
        self.assertEqual(self.rec('// await sky.click({element_index: 3})\n/* sky.drag({}) */'), [])
        self.assertEqual(self.rec(cu.BOOTSTRAP), [])

    def test_multiple_calls_one_line_in_order(self):
        a = self.rec('await sky.click({element_index:1}); await sky.press_key({app:"x", key:"Return"});')
        self.assertEqual([x["method"] for x in a], ["click", "press_key"])


# ---------------------------------------------------- event-stream audit

class TestAuditRules(Base):
    def test_session_id_and_actions_come_from_the_stream_not_the_model(self):
        events = [ev_thread("abc-123"), ev_call(cu.BOOTSTRAP, ""), ev_call(OBS, "tree"),
                  ev_call('await sky.click({app:"com.example.fake", element_index: 4});', ""), ev_call(OBS_DIFF, "tree2")]
        res = self.audit(events, reply(actions_taken=["I did ten things"]))
        self.assertEqual(res["session_id"], "abc-123")
        self.assertEqual([a["method"] for a in res["actions_recorded"]], ["get_app_state", "click", "get_app_state"])
        self.assertEqual(res["model_actions_claimed"], ["I did ten things"])
        self.assertEqual(res["status"], "done", res["reason"])
        self.assertTrue(res["may_have_had_effect"]); self.assertEqual(res["lint"], [])

    def test_done_with_no_sky_calls_fails(self):
        res = self.audit([ev_thread()], reply())
        self.assertEqual(res["status"], "failed"); self.assertIn("no Sky call", res["reason"])

    def test_diff_default_and_full_tree_lint(self):
        events = [ev_thread(), ev_call(OBS_DIFF, "diff"), ev_call('sky.click({app:"x", element_index: 1})', ""), ev_call(OBS_DIFF, "diff2")]
        res = self.audit(events, reply())
        self.assertTrue(any("disableDiff" in f for f in res["lint"]))
        events[1] = ev_call(OBS, "full")
        self.assertFalse(any("disableDiff" in f for f in self.audit(events, reply())["lint"]))

    def test_two_state_changes_without_observation_are_flagged(self):
        events = [ev_thread(), ev_call(OBS, "t"),
                  ev_call('sky.click({app:"x", element_index: 1}); sky.click({app:"x", element_index: 2});', ""), ev_call(OBS_DIFF, "t2")]
        self.assertTrue(any("no get_app_state between" in f for f in self.audit(events, reply())["lint"]))

    def test_trailing_state_change_blocks(self):
        """review: a run whose last call is a click used to stay done."""
        events = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.click({app:"x", element_index: 1})', "")]
        res = self.audit(events, reply())
        self.assertEqual(res["status"], "blocked"); self.assertIn("end state unverified", res["reason"])

    def test_multiline_type_text_is_flagged_and_paste_is_not(self):
        events = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.type_text({app:"x", text:"line one\\nline two"})', ""), ev_call(OBS_DIFF, "t2")]
        self.assertTrue(any("newline" in f for f in self.audit(events, reply())["lint"]))
        events[2] = ev_call('sky.paste({app:"x", text:"line one\\nline two", format:"text"})', "")
        res = self.audit(events, reply())
        self.assertFalse(any("newline" in f for f in res["lint"]))
        self.assertEqual(res["actions_recorded"][1]["method"], "paste")

    def test_scroll_by_index_and_by_coordinates_pass_and_bare_scroll_fails(self):
        obs = ev_call(OBS, "t")
        good = [ev_thread(), obs, ev_call('sky.scroll({app:"x", element_index: 7, direction:"down", pages:1})', ""), obs,
                ev_call('sky.scroll({app:"x", x: 400, y: 400, direction:"up", pages:1})', ""), obs]
        self.assertFalse(any("scroll without" in f for f in self.audit(good, reply())["lint"]))
        bad = [ev_thread(), obs, ev_call('sky.scroll({app:"x", direction:"down", pages:1})', "coordinate must include finite x and y coordinates"), obs]
        self.assertTrue(any("scroll without" in f for f in self.audit(bad, reply())["lint"]))
        # review: a bare substring "x" used to satisfy the coordinate check.
        xish = [ev_thread(), obs, ev_call('sky.scroll({app:"x", direction:"down", extra:"xy"})', ""), obs]
        self.assertTrue(any("scroll without" in f for f in self.audit(xish, reply())["lint"]))

    def test_drag_needs_fresh_state_immediately_before(self):
        obs = ev_call(OBS, "t")
        ok = [ev_thread(), obs, ev_call('sky.drag({app:"x", from_x:1, from_y:2, to_x:3, to_y:4})', ""), obs]
        self.assertFalse(any("drag" in f for f in self.audit(ok, reply())["lint"]))
        stale = [ev_thread(), obs, ev_call('sky.click({app:"x", element_index: 1})', ""),
                 ev_call('sky.drag({app:"x", from_x:1, from_y:2, to_x:3, to_y:4})', ""), obs]
        self.assertTrue(any("drag without a fresh" in f for f in self.audit(stale, reply())["lint"]))

    def test_secondary_action_must_be_exposed_by_the_tree(self):
        tree = ev_call(OBS, "[12] row  actions: Expand, Show Menu")
        obs = ev_call(OBS_DIFF, "t2")
        ok = [ev_thread(), tree, ev_call('sky.perform_secondary_action({app:"x", element_index: 12, action: "Show Menu"})', ""), obs]
        self.assertFalse(any("guessed" in f for f in self.audit(ok, reply())["lint"]))
        guessed = [ev_thread(), tree, ev_call('sky.perform_secondary_action({app:"x", element_index: 12, action: "Increment"})', ""), obs]
        self.assertTrue(any("guessed" in f for f in self.audit(guessed, reply())["lint"]))

    def test_stale_index_error_blocks_but_tree_dumps_do_not(self):
        events = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.click({app:"x", element_index: 99})', "Error: element_index 99 not found in current state"),
                  ev_call(OBS_DIFF, "t2"), ev_call(OBS_DIFF, "t3")]
        res = self.audit(events, reply())
        self.assertEqual(res["status"], "blocked"); self.assertIn("stale", res["reason"])
        # review: the bare field name appears in ordinary dumps and must not fire.
        fine = [ev_thread(), ev_call(OBS, 'AXButton "Save" element_index=12'), ev_call('sky.click({app:"x", element_index: 12})', ""), ev_call(OBS_DIFF, "element_index=13 AXWindow")]
        self.assertEqual(self.audit(fine, reply())["status"], "done")

    def test_risky_action_without_preapproval_blocks(self):
        """review: a recorded Send click with a `done` reply used to come back done."""
        events = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.click({app:"x", element_index: 3})', "", title="Click Send button"), ev_call(OBS_DIFF, "t2")]
        res = self.audit(events, reply())
        self.assertTrue(res["risky_signals"]); self.assertIn("send", res["risky_signals"][0].lower())
        self.assertEqual(res["status"], "blocked"); self.assertIn("without a matching pre-approval", res["reason"])
        ret = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.press_key({app:"x", key:"Return"})', ""), ev_call(OBS_DIFF, "t2")]
        self.assertEqual(self.audit(ret, reply())["status"], "blocked")

    def test_risky_action_with_matching_preapproval_is_done(self):
        events = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.click({app:"x", element_index: 3})', "", title="Click Send button"), ev_call(OBS_DIFF, "t2")]
        task = {"goal": "g", "done": "d", "preapproved": "yes, send the draft to a@b.test"}
        self.assertEqual(self.audit(events, reply(), task=task)["status"], "done")
        # A pre-approval for something else does not cover it.
        task = {"goal": "g", "done": "d", "preapproved": "you may delete the draft"}
        self.assertEqual(self.audit(events, reply(), task=task)["status"], "blocked")

    def test_actions_outside_sky_block(self):
        """review: a shell command driving the GUI was invisible to the audit."""
        events = [ev_thread(), ev_call(OBS, "t"), ev_shell(), ev_call(OBS_DIFF, "t2")]
        res = self.audit(events, reply())
        self.assertEqual(res["status"], "blocked"); self.assertIn("outside Sky", res["reason"])
        self.assertEqual(res["other_tool_calls"][0]["kind"], "command_execution")
        self.assertTrue(res["may_have_had_effect"])

    def test_unparsed_or_looped_state_change_blocks(self):
        events = [ev_thread(), ev_call(OBS, "t"), ev_call('const p = {app:"x", element_index: 7}; await sky.click(p);', ""), ev_call(OBS_DIFF, "t2")]
        res = self.audit(events, reply())
        self.assertEqual(res["status"], "blocked"); self.assertIn("non-literal", res["reason"])
        self.assertTrue(res["may_have_had_effect"])
        loop = [ev_thread(), ev_call(OBS, "t"), ev_call('for (const i of [1,2]) await sky.click({app:"x", element_index: i});', ""), ev_call(OBS_DIFF, "t2")]
        self.assertIn("inside a loop", self.audit(loop, reply())["reason"])

    def test_failed_tool_call_status_blocks(self):
        events = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.click({app:"x", element_index: 1})', "", status="failed"), ev_call(OBS_DIFF, "t2")]
        res = self.audit(events, reply())
        self.assertEqual(res["status"], "blocked"); self.assertIn("did not complete cleanly", res["reason"])

    def test_done_with_state_change_but_no_observed_after_fails(self):
        events = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.click({app:"x", element_index: 3})', ""), ev_call(OBS_DIFF, "t2")]
        res = self.audit(events, reply(observed_after=""))
        self.assertEqual(res["status"], "failed"); self.assertIn("observed_after", res["reason"])

    def test_done_with_confirmation_reason_is_downgraded(self):
        self.assertEqual(self.audit([ev_thread(), ev_call(OBS, "t")], reply(confirmation_reason="send"))["status"], "blocked")

    def test_nonzero_exit_fails_even_with_a_reply(self):
        res = self.audit([ev_thread(), ev_call(OBS, "t")], reply(), exit_code=1)
        self.assertEqual(res["status"], "failed"); self.assertIn("exited 1", res["reason"])


# --------------------------------------------- confirmation and resume

class TestConfirmationAndResume(Base):
    def first_run(self):
        events = [ev_thread("sess-9"), ev_call(OBS, "Compose window; Send button [7]")]
        rep = reply(status="needs_confirmation", question="Send the email to a@b.test now?", confirmation_reason="send",
                    observed_after="Compose window with To: a@b.test")
        return cu.do_run(run_args(self.tmp.name), runner=fake_runner(events, rep), mdfind=self.mdfind)

    def test_needs_confirmation_writes_pending_with_exact_question_and_session(self):
        res = self.first_run()
        self.assertEqual(res["status"], "needs_confirmation")
        pending = json.loads((Path(res["run_dir"]) / "pending.json").read_text())
        self.assertEqual(pending["session_id"], "sess-9")
        self.assertEqual(pending["question"], "Send the email to a@b.test now?")
        self.assertEqual(pending["last_verified_state"], "Compose window with To: a@b.test")
        self.assertEqual(pending["run_dir"], res["run_dir"])
        self.assertEqual(pending["target"]["bundle_id"], "com.example.fake")

    def test_needs_confirmation_without_question_fails(self):
        events = [ev_thread(), ev_call(OBS, "t")]
        res = cu.do_run(run_args(self.tmp.name), runner=fake_runner(events, reply(status="needs_confirmation", question="")), mdfind=self.mdfind)
        self.assertEqual(res["status"], "failed")
        self.assertFalse((Path(res["run_dir"]) / "pending.json").exists())

    def test_resume_rebootstraps_reobserves_and_uses_same_session(self):
        run_dir = Path(self.first_run()["run_dir"])
        second = [ev_call(cu.BOOTSTRAP, ""), ev_call(OBS, "Compose"),
                  ev_call('await sky.click({app:"com.example.fake", element_index: 7});', "", title="Click Send"),
                  ev_call(OBS_DIFF, "Sent")]
        r2 = fake_runner(second, reply(summary="sent", observed_after="Message moved to Sent"))
        out = cu.do_resume(SimpleNamespace(run_dir=str(run_dir), answer="yes, send it", effort=None, timeout=10), runner=r2)
        self.assertEqual(r2.argv[:4], ["codex", "exec", "resume", "sess-9"])
        prompt = r2.argv[-1]
        for needle in ("yes, send it", cu.BOOTSTRAP, "disableDiff: true", "Never reuse an index"):
            self.assertIn(needle, prompt)
        self.assertEqual(out["status"], "done", out["reason"])   # the yes covers the Send click
        self.assertEqual(out["session_id"], "sess-9"); self.assertEqual(out["turn"], 2)
        self.assertEqual([a["method"] for a in out["actions_recorded"]], ["get_app_state", "click", "get_app_state"])
        self.assertTrue(out["risky_signals"]); self.assertTrue(out["run_may_have_had_effect"])
        self.assertTrue((run_dir / "pending.json.answered").exists())
        self.assertTrue((run_dir / "result.json.turn1").exists())

    def test_resume_without_a_clear_yes_launches_nothing(self):
        """review: any --answer used to be forwarded; the runner now judges it."""
        run_dir = Path(self.first_run()["run_dir"])
        r2 = fake_runner([], reply())
        for answer in ("no", "yes but change the subject first", "hmm", "send it to someone else"):
            (run_dir / "pending.json").write_text((run_dir / "pending.json.answered").read_text()) if (run_dir / "pending.json.answered").exists() else None
            out = cu.do_resume(SimpleNamespace(run_dir=str(run_dir), answer=answer, effort=None, timeout=10), runner=r2)
            self.assertEqual(out["status"], "blocked", answer); self.assertIn("clear yes", out["reason"])
            self.assertEqual(getattr(r2, "calls", 0), 0)
            self.assertTrue((run_dir / "pending.json.answered").exists())

    def test_clear_yes_forms(self):
        for yes in ("yes", "Yes.", "y", "ok", "go ahead", "yes, send it", "proceed please"):
            self.assertTrue(cu.is_clear_yes(yes), yes)
        for no in ("no", "yes but", "yes if you change the recipient", "not yet", ""):
            self.assertFalse(cu.is_clear_yes(no), no)

    def test_resume_offset_survives_a_missing_trailing_newline(self):
        """review: a glued line used to drop the first call of the resumed turn."""
        run_dir = Path(self.first_run()["run_dir"])
        ev = run_dir / "events.jsonl"
        ev.write_bytes(ev.read_bytes().rstrip(b"\n"))
        second = [ev_call(cu.BOOTSTRAP, ""), ev_call(OBS, "Compose"), ev_call('await sky.click({app:"com.example.fake", element_index: 7});', "", title="Click Send"), ev_call(OBS_DIFF, "Sent")]
        out = cu.do_resume(SimpleNamespace(run_dir=str(run_dir), answer="yes", effort=None, timeout=10),
                           runner=fake_runner(second, reply(observed_after="Sent")))
        self.assertEqual([a["method"] for a in out["actions_recorded"]], ["get_app_state", "click", "get_app_state"])

    def test_resume_refuses_without_pending(self):
        d = self.root / "r"; d.mkdir()
        with self.assertRaises(SystemExit):
            cu.do_resume(SimpleNamespace(run_dir=str(d), answer="yes", effort=None, timeout=10), runner=fake_runner([], None))


# ------------------------------------------------- evidence validation

class TestEvidence(Base):
    def shot(self, name="My Shot 5.31 PM.jpeg", data=PNG, where=None):
        p = (where or cu.SKY_SHOT_DIR) / name
        p.write_bytes(data)
        return p

    def test_accepts_plain_path_file_url_percent_encoded_and_data_url(self):
        shot = self.shot()
        items = [str(shot), f"file://{shot}", "file://" + str(shot).replace(" ", "%20"), PNG_DATA_URL]
        ok, rejected = cu.validate_evidence(items, self.root / "shots", stream_text=PNG_DATA_URL)
        self.assertEqual(rejected, []); self.assertEqual(len(ok), 4)
        for p in ok:
            self.assertTrue(Path(p).is_file()); self.assertTrue(p.startswith(str(self.root / "shots")))

    def test_rejects_missing_relative_and_garbage(self):
        ok, rejected = cu.validate_evidence(["/nope/none.png", "relative.png", "Active tab title: X", 42, "data:image/png;base64,!!!"], self.root / "shots")
        self.assertEqual(ok, []); self.assertEqual(len(rejected), 5)

    def test_rejects_files_this_run_did_not_produce(self):
        """review: any user-readable file the model named used to be copied and opened."""
        secret = self.shot("id_rsa", b"-----BEGIN OPENSSH PRIVATE KEY-----", where=self.root)
        elsewhere = self.shot("real.png", where=self.root)
        ok, rejected = cu.validate_evidence([str(secret), str(elsewhere)], self.root / "shots")
        self.assertEqual(ok, []); self.assertTrue(all("not produced by this run" in r for r in rejected))
        # ...unless the event stream itself named the path.
        ok, _ = cu.validate_evidence([str(elsewhere)], self.root / "shots", allowed_sources=[str(elsewhere)])
        self.assertEqual(len(ok), 1)
        # A data URL that never appeared in the stream is rejected too.
        ok, rejected = cu.validate_evidence([PNG_DATA_URL], self.root / "shots", stream_text="")
        self.assertEqual(ok, []); self.assertIn("not produced", rejected[0])

    def test_rejects_symlinks_non_images_and_oversize(self):
        real = self.shot("real.png")
        link = cu.SKY_SHOT_DIR / "link.png"; link.symlink_to(real)
        text = self.shot("notes.png", b"just text pretending")
        big = self.shot("big.png", PNG + b"\0" * 64)
        old = cu.EVIDENCE_MAX_BYTES; cu.EVIDENCE_MAX_BYTES = len(PNG) + 16   # real passes, padded one does not
        self.addCleanup(setattr, cu, "EVIDENCE_MAX_BYTES", old)
        ok, rejected = cu.validate_evidence([str(link), str(text), str(big), str(real)], self.root / "shots")
        self.assertEqual(len(ok), 1)
        self.assertTrue(any("symlink" in r for r in rejected)); self.assertTrue(any("not a PNG" in r for r in rejected))
        self.assertTrue(any("larger than" in r for r in rejected))

    @unittest.skipUnless(__import__("shutil").which("sips"), "macOS sips needed to decode images")
    def test_blank_screenshots_are_rejected_and_real_ones_kept(self):
        """live 2026-09-20: the helper returned an all-white image for Finder's Desktop window and the
        audit accepted it as evidence."""
        import struct, subprocess
        def bmp(w, h, pixel):   # 24-bit BMP with a pixel function (x, y) -> (b, g, r)
            row = lambda y: b"".join(bytes(pixel(x, y)) for x in range(w)) + b"\0" * ((4 - (w * 3) % 4) % 4)
            body = b"".join(row(y) for y in range(h))
            hdr = struct.pack("<2sIHHI", b"BM", 54 + len(body), 0, 0, 54) + struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(body), 2835, 2835, 0, 0)
            return hdr + body
        flat_bmp = cu.SKY_SHOT_DIR / "flat.bmp"; flat_bmp.write_bytes(bmp(80, 80, lambda x, y: (255, 255, 255)))
        real_bmp = cu.SKY_SHOT_DIR / "real.bmp"; real_bmp.write_bytes(bmp(80, 80, lambda x, y: (x * 3 % 256, y * 3 % 256, (x + y) % 256)))
        flat = cu.SKY_SHOT_DIR / "flat.png"; real = cu.SKY_SHOT_DIR / "real.png"
        for src, dst in ((flat_bmp, flat), (real_bmp, real)):
            subprocess.run(["sips", "-s", "format", "png", str(src), "--out", str(dst)], capture_output=True, check=True)
        self.assertTrue(cu.image_is_flat(flat)[0]); self.assertFalse(cu.image_is_flat(real)[0])
        self.assertIsNone(cu.image_is_flat(self.shot("tiny.png"))[0])   # 1x1: too small to judge
        # review: the old byte-sampling rule called these real images blank.
        narrow_bmp = cu.SKY_SHOT_DIR / "narrow.bmp"; narrow_bmp.write_bytes(bmp(200, 120, lambda x, y: (60, 60, 60) if 90 <= x < 100 else (255, 255, 255)))
        redpanel_bmp = cu.SKY_SHOT_DIR / "redpanel.bmp"; redpanel_bmp.write_bytes(bmp(160, 120, lambda x, y: (48, 150, 230) if x < 80 and y < 60 else (48, 48, 48)))
        tinted_bmp = cu.SKY_SHOT_DIR / "tinted.bmp"; tinted_bmp.write_bytes(bmp(80, 80, lambda x, y: (30, 20, 10)))   # blank in a colour whose channels differ
        for name in ("narrow", "redpanel", "tinted"):
            subprocess.run(["sips", "-s", "format", "png", str(cu.SKY_SHOT_DIR / f"{name}.bmp"), "--out", str(cu.SKY_SHOT_DIR / f"{name}.png")], capture_output=True, check=True)
        self.assertFalse(cu.image_is_flat(cu.SKY_SHOT_DIR / "narrow.png")[0])
        self.assertFalse(cu.image_is_flat(cu.SKY_SHOT_DIR / "redpanel.png")[0])
        self.assertTrue(cu.image_is_flat(cu.SKY_SHOT_DIR / "tinted.png")[0])
        notes = []
        ok, rejected = cu.validate_evidence([str(flat), str(real), str(cu.SKY_SHOT_DIR / "narrow.png")], self.root / "shots", notes=notes)
        self.assertEqual(len(ok), 2); self.assertTrue(ok[0].endswith("real.png"))
        self.assertTrue(any("blank image" in r for r in rejected))
        self.assertEqual(notes, [])
        # An undecodable file is skipped with a recorded note, not silently accepted.
        junk = cu.SKY_SHOT_DIR / "junk.png"; junk.write_bytes(b"\x89PNG\r\n\x1a\n" + b"garbage" * 700)
        v, why = cu.image_is_flat(junk); self.assertIsNone(v); self.assertIn("skipped", why)
        # No stray temp files next to the source.
        self.assertEqual([f for f in os.listdir(cu.SKY_SHOT_DIR) if "flatcheck" in f or f.endswith(".tmp")], [])

    def test_evidence_never_overwrites_across_turns(self):
        """review: turn 2's evidence-00 used to replace turn 1's."""
        shot = self.shot("w.png")
        ok1, _ = cu.validate_evidence([str(shot)], self.root / "shots", prefix="t1")
        ok2, _ = cu.validate_evidence([str(shot)], self.root / "shots", prefix="t2")
        ok3, _ = cu.validate_evidence([str(shot)], self.root / "shots", prefix="t2")
        self.assertEqual(len({ok1[0], ok2[0], ok3[0]}), 3)
        self.assertTrue(Path(ok1[0]).exists())

    def test_done_with_only_unproduced_evidence_fails(self):
        events = [ev_thread(), ev_call(OBS, "t")]
        res = self.audit(events, reply(evidence=["/var/folders/x/Chrome%20Screenshot.jpeg"]))
        self.assertEqual(res["status"], "failed"); self.assertIn("no usable evidence survived validation", res["reason"])

    def test_screenshot_refs_from_stream_accept_both_forms(self):
        calls = [{"result": "screenshot: { url: 'file:///tmp/a%20b.jpeg' }", "code": ""}, {"result": "data:image/jpeg;base64,AAAA", "code": ""}]
        refs = cu.screenshot_refs(calls)
        self.assertEqual(refs[0], "/tmp/a b.jpeg"); self.assertTrue(refs[1].startswith("data:image/jpeg"))

    def test_same_second_runs_get_distinct_dirs(self):
        now = dt.datetime(2026, 1, 1)
        a = cu.new_run_dir(self.root / "runs", "task", now=now); b = cu.new_run_dir(self.root / "runs", "task", now=now)
        self.assertNotEqual(a, b); self.assertTrue(a.is_dir() and b.is_dir())

    def test_run_root_the_runner_did_not_create_keeps_its_mode(self):
        """review: --run-root ~ used to chmod the user's home to 0700."""
        root = self.root / "existing"; root.mkdir(mode=0o755)
        cu.new_run_dir(root, "task")
        self.assertEqual(oct(root.stat().st_mode & 0o777), "0o755")
        fresh = self.root / "fresh"; cu.new_run_dir(fresh, "task")
        self.assertEqual(oct(fresh.stat().st_mode & 0o777), "0o700")

    def test_prune_deletes_only_run_dirs_and_keeps_pending(self):
        """review: prune-runs used to rmtree any old directory under --run-root."""
        root = self.root / "runs"
        old = cu.new_run_dir(root, "old task", now=dt.datetime(2026, 1, 1)); (old / "result.json").write_text("{}")
        pend = cu.new_run_dir(root, "pending task", now=dt.datetime(2026, 1, 2)); (pend / "pending.json").write_text("{}"); (pend / "brief.md").write_text("")
        stray = root / "taxes"; stray.mkdir(); (stray / "return.pdf").write_bytes(b"%PDF")
        stamped_but_foreign = root / "20260101-000000-photos"; stamped_but_foreign.mkdir(); (stamped_but_foreign / "a.jpg").write_bytes(b"x")
        self.assertEqual(oct(old.stat().st_mode & 0o777), "0o700")
        past = (dt.datetime.now() - dt.timedelta(days=30)).timestamp()
        for d in (old, pend, stray, stamped_but_foreign):
            os.utime(d, (past, past))
        removed = cu.prune_runs(root, keep_days=7)
        self.assertEqual(removed, [str(old)])
        for d in (pend, stray, stamped_but_foreign):
            self.assertTrue(d.exists(), d)


# ------------------------------------- real codex exec --json shapes

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestRealStreams(Base):
    """Sanitized `codex exec --json` streams recorded on 2026-09-20 (tree text,
    shell commands, and model prose redacted; event shapes and the model's JS kept).
    If Codex changes its event format, these fail before a live run would."""

    def test_chrome_scroll_stream(self):
        parsed = cu.parse_events(FIXTURES / "chrome-scroll-2026-09-20.jsonl")
        self.assertTrue(parsed["session_id"]); self.assertEqual(parsed["malformed_lines"], 0)
        acts = cu.record_actions(parsed["calls"])
        self.assertEqual([a["method"] for a in acts], ["get_app_state", "scroll", "scroll"])
        self.assertTrue(all(a["parsed"] for a in acts))
        self.assertTrue(cu.screenshot_refs(parsed["calls"])[0].endswith("Chrome Screenshot 2026-09-20.jpeg"))
        lint = cu.lint_actions(acts, parsed["calls"])
        self.assertTrue(any("end state unverified" in f for f in lint))   # the probe ended on a scroll

    def test_stream_with_shell_commands_is_seen(self):
        parsed = cu.parse_events(FIXTURES / "chrome-scroll-with-shell-2026-09-20.jsonl")
        self.assertEqual([o["kind"] for o in parsed["other_tool_calls"]], ["command_execution", "command_execution"])
        self.assertIn("failed", {c["status"] for c in parsed["calls"]})
        acts = cu.record_actions(parsed["calls"])
        self.assertTrue(any("scroll without element_index" in f for f in cu.lint_actions(acts, parsed["calls"])))


# ------------------------------------------- helper, timeout, malformed

class TestFailClosed(Base):
    def run_with(self, events, rep=None, **kw):
        return cu.do_run(run_args(self.tmp.name), runner=fake_runner(events, rep, **kw), mdfind=self.mdfind)

    def test_timeout_with_effect_says_do_not_retry(self):
        events = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.click({app:"x", element_index: 1})', "")]
        res = self.run_with(events, None, timed_out=True)
        self.assertEqual(res["status"], "failed"); self.assertTrue(res["may_have_had_effect"]); self.assertIn("do NOT retry", res["reason"])

    def test_timeout_without_effect_says_so(self):
        res = self.run_with([ev_thread(), ev_call(OBS_DIFF, "t")], None, timed_out=True)
        self.assertFalse(res["may_have_had_effect"]); self.assertIn("No state-changing action", res["reason"])

    def test_helper_error_anywhere_fails(self):
        """review: only the last call used to be inspected."""
        sig = [ev_thread(), ev_call(cu.BOOTSTRAP, "Error: SkyComputerUseClient exited: invalid code signature (SIGKILL)")]
        res = self.run_with(sig, reply(summary="all good"))
        self.assertEqual(res["status"], "failed"); self.assertIn("helper error", res["reason"])
        mid = [ev_thread(), ev_call(OBS, "t"), ev_call('sky.click({app:"x", element_index: 1})', "Error: connect ENOENT computeruse.sock"),
               ev_call('nodeRepl.write("summary")', "summary")]
        self.assertEqual(self.run_with(mid, reply())["status"], "failed")
        # Ordinary UI text with the word "helper" is not a helper error.
        fine = [ev_thread(), ev_call(OBS, 'AXStaticText "Helpers and Support"')]
        self.assertEqual(self.run_with(fine, reply())["status"], "done")

    def test_not_approved_blocks_whatever_the_model_says(self):
        events = [ev_thread(), ev_call(OBS_DIFF, "Computer Use was not approved to use Safari")]
        res = self.run_with(events, reply(summary="I read Safari fine"))
        self.assertEqual(res["status"], "blocked"); self.assertIn("Safari", res["reason"])

    def test_missing_reply_fails(self):
        res = self.run_with([ev_thread(), ev_call(OBS_DIFF, "t")], None)
        self.assertEqual(res["status"], "failed"); self.assertIn("reply.json missing", res["reason"])

    def test_malformed_reply_fails(self):
        events = [ev_thread(), ev_call(OBS_DIFF, "t")]
        def r(argv, run_dir, timeout, env=None):
            write_events(run_dir, events); (run_dir / "reply.json").write_text("{not json")
            return {"exit_code": 0, "timed_out": False, "elapsed_s": 1}
        res = cu.do_run(run_args(self.tmp.name), runner=r, mdfind=self.mdfind)
        self.assertEqual(res["status"], "failed"); self.assertIn("not valid JSON", res["reason"])

    def test_reply_with_unknown_status_or_missing_fields_fails(self):
        events = [ev_thread(), ev_call(OBS_DIFF, "t")]
        self.assertEqual(self.run_with(events, {"status": "maybe"})["status"], "failed")
        self.assertEqual(self.run_with(events, {"status": "done"})["status"], "failed")

    def test_malformed_event_lines_block(self):
        """review: an unparseable stream used to still support done."""
        events = [ev_thread(), "this is not json", ev_call(OBS, "t")]
        res = self.run_with(events, reply())
        self.assertEqual(res["malformed_event_lines"], 1)
        self.assertEqual(res["status"], "blocked"); self.assertIn("unparseable", res["reason"])

    def test_preflight_failure_blocks_before_any_launch(self):
        r = fake_runner([], None)
        args = run_args(self.tmp.name, skip_preflight=False)
        res = cu.do_run(args, runner=r, mdfind=self.mdfind, env={"CODEX_HOME": str(self.root / "no-such-profile")},
                        run=fake_cli(), tcc_db=self.tcc())
        self.assertEqual(res["status"], "blocked")
        self.assertIn("preflight failed", res["reason"]); self.assertIn("helper missing", res["reason"])
        self.assertEqual(getattr(r, "calls", 0), 0)
        self.assertTrue((Path(res["run_dir"]) / "preflight.json").exists())

    def test_skip_preflight_is_recorded(self):
        events = [ev_thread(), ev_call(OBS, "t")]
        res = cu.do_run(run_args(self.tmp.name, skip_preflight=True), runner=fake_runner(events, reply()), mdfind=self.mdfind,
                        env={"CODEX_HOME": str(self.root / "no-such-profile")}, run=fake_cli(), tcc_db=self.tcc())
        self.assertTrue(res["preflight_skipped"])

    def test_ensure_trailing_newline(self):
        p = self.root / "e.jsonl"; p.write_bytes(b'{"a":1}')
        cu._ensure_trailing_newline(p); self.assertEqual(p.read_bytes(), b'{"a":1}\n')
        cu._ensure_trailing_newline(p); self.assertEqual(p.read_bytes(), b'{"a":1}\n')
        empty = self.root / "empty.jsonl"; empty.write_bytes(b""); cu._ensure_trailing_newline(empty)
        self.assertEqual(empty.read_bytes(), b"")

    def test_main_exit_codes(self):
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cu.main(["approvals", "add", "--bundle-id", "com.apple.mail"]), 2)   # no --yes
            self.assertEqual(cu.main(["resolve-app", str(self.fake_app)]), 0)
            self.assertEqual(cu.main(["prune-runs", "--run-root", str(self.root / "none")]), 0)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Hand one bounded GUI subtask on this Mac to Codex Computer Use and get back a
checked result.

Subcommands:
  preflight  [--app APP]       profile paths, codex version, feature flag, helper,
                               macOS privacy status, and the app's approval state
  resolve-app APP              display name | .app path | bundle ID -> bundle ID
  approvals inspect            read the persistent approval file; never writes
  approvals add --bundle-id X  explicit setup: backup, add exact IDs, report, verify
  run  ...                     one subtask: build brief, call codex exec, audit result
  resume --run-dir DIR --answer TEXT   continue a needs_confirmation run
  prune-runs [--keep-days N]   retention for the private run directory

Standard library only. The Codex call is a single injectable function so the
tests never launch anything. See ../SKILL.md for the operating rules and
../references/sky-rules.md for the Sky API guidance the brief carries.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import plistlib
import re
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

__version__ = "0.1.0"

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "reply-schema.json"
SKY_RULES_PATH = HERE.parent / "references" / "sky-rules.md"

# The helper's persistent approval store. Fixed by the helper's app group, not by
# CODEX_HOME (verified 2026-09-20: one file, one key, exact bundle IDs).
APPROVALS_PATH = Path.home() / (
    "Library/Group Containers/2DC432GLL2.com.openai.sky.CUAService/"
    "Library/Application Support/Software/ComputerUseAppApprovals.json"
)
APPROVALS_KEY = "approvedBundleIdentifiers"
HELPER_BUNDLE_ID = "com.openai.sky.CUAService"
TCC_DB = Path("/Library/Application Support/com.apple.TCC/TCC.db")
TCC_SERVICES = {
    "kTCCServiceAccessibility": "Accessibility",
    "kTCCServiceScreenCapture": "Screen Recording",
}

DEFAULT_RUN_ROOT = Path.home() / ".computer-use" / "runs"
DEFAULT_TIMEOUT = 300
DEFAULT_KEEP_DAYS = 7
EFFORTS = ("low", "medium", "high", "xhigh")
DEFAULT_EFFORT = "medium"

BOOTSTRAP = 'globalThis.sky = (await import("@oai/sky")).sky;'

# Sky calls that change what is on screen. Anything here in the recorded event
# stream means the run may have had an effect, so a timeout is never retried.
STATE_CHANGING = {
    "click", "drag", "paste", "perform_secondary_action", "press_key",
    "scroll", "select_text", "set_value", "type_text",
}
OBSERVING = {"get_app_state", "list_apps"}

# Wording that, in a tool-call title or clicked element, points at the
# confirmation boundary. Post-hoc audit only; the brief is what stops the model.
RISKY_WORDS = re.compile(
    r"\b(send|submit|delete|remove|trash|pay|purchase|buy|checkout|transfer|"
    r"permission|allow access|grant|unsubscribe|post|publish|share|sign in|log in|password)\b",
    re.I,
)
# Helper-level breakage (signature, socket, service down). Any of these anywhere
# in the stream ends the run as failed, whatever the model wrote afterwards.
HELPER_ERROR = re.compile(
    r"(code ?signature|SIGKILL|killed: 9|Computer Use (is )?unavailable|"
    r"computeruse\.sock|connection refused|SkyComputerUse\w* (exited|crashed|not running))", re.I,
)
NOT_APPROVED = re.compile(r"Computer Use was not approved to use (.+)", re.I)
# Error phrasing only. A bare "element_index" appears in ordinary tree dumps.
STALE_INDEX = re.compile(
    r"(stale (element )?index|index out of range|no element (at|with|for) (that )?index|"
    r"element_index \d+ (not found|is invalid|out of range|does not exist)|invalid element_index)", re.I,
)

DATA_URL = re.compile(r"data:image/(png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=]+)")
FILE_URL = re.compile(r"file://(/[^\s'\"\\)]+)")
IMAGE_MAGIC = {b"\x89PNG\r\n\x1a\n": "png", b"\xff\xd8\xff": "jpg", b"RIFF": "webp"}
EVIDENCE_MAX_BYTES = 20 * 1024 * 1024
# Where the Sky helper writes screenshots (verified 2026-09-20). Evidence must
# come from here or from a path the event stream itself named.
SKY_SHOT_DIR = Path(os.environ.get("TMPDIR", "/tmp")) / "com.openai.sky.CUAService"
RUN_DIR_NAME = re.compile(r"^\d{8}-\d{6}-[a-z0-9-]+(-\d+)?$")
RUN_DIR_MARKERS = ("brief.md", "preflight.json", "result.json")


# ----------------------------------------------------------------------------
# Profile-aware paths
# ----------------------------------------------------------------------------

def codex_home(env: dict | None = None) -> Path:
    """CODEX_HOME if set, else ~/.codex. Never assume the unprofiled path."""
    env = os.environ if env is None else env
    raw = env.get("CODEX_HOME")
    return Path(raw).expanduser() if raw else Path.home() / ".codex"


def helper_app(home: Path) -> Path:
    return home / "computer-use" / "Codex Computer Use.app"


def helper_client(home: Path) -> Path:
    return (helper_app(home) / "Contents/SharedSupport/SkyComputerUseClient.app"
            / "Contents/MacOS/SkyComputerUseClient")


# ----------------------------------------------------------------------------
# App resolution (open-ended: any display name, .app path, or bundle ID)
# ----------------------------------------------------------------------------

BUNDLE_ID_RE = re.compile(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+\Z")


def is_bundle_id(s: str) -> bool:
    """Exact bundle ID: ASCII, dotted, no whitespace, no wildcard characters."""
    return bool(BUNDLE_ID_RE.fullmatch(s)) and not any(ch in s for ch in "*?[]") and s == s.strip()


def _mdfind(query: str) -> list[str]:
    """Spotlight lookup. Read-only; never launches the app (osascript would)."""
    try:
        out = subprocess.run(["mdfind", query], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [line for line in out.stdout.splitlines() if line.strip()]


def _info_plist(app_path: Path) -> dict:
    plist = app_path / "Contents" / "Info.plist"
    with plist.open("rb") as fh:
        return plistlib.load(fh)


def resolve_app(target: str, mdfind=_mdfind) -> dict:
    """Return {"input", "bundle_id", "display_name", "path", "how"}; bundle_id is
    None when nothing on disk matched. No allowlist, no denylist, no launch."""
    t = target.strip()
    res = {"input": t, "bundle_id": None, "display_name": None, "path": None, "how": None}
    if t.endswith(".app") and Path(t).expanduser().is_dir():
        p = Path(t).expanduser().resolve()
        info = _info_plist(p)
        res.update(bundle_id=info.get("CFBundleIdentifier"), path=str(p),
                   display_name=info.get("CFBundleDisplayName") or info.get("CFBundleName") or p.stem,
                   how="path")
        return res
    if is_bundle_id(t):
        hits = mdfind(f"kMDItemCFBundleIdentifier == '{t}'")
        res.update(bundle_id=t, how="bundle-id")
        if hits:
            p = Path(hits[0])
            res["path"] = str(p)
            try:
                info = _info_plist(p)
                res["display_name"] = info.get("CFBundleDisplayName") or info.get("CFBundleName") or p.stem
            except (OSError, plistlib.InvalidFileException):
                res["display_name"] = p.stem
        return res
    safe = t.replace("'", "\\'")
    hits = mdfind(f"kMDItemKind == 'Application' && kMDItemDisplayName == '{safe}'c") \
        or mdfind(f"kMDItemKind == 'Application' && kMDItemFSName == '{safe}.app'c")
    res.update(display_name=t, how="display-name")
    if hits:
        p = Path(sorted(hits, key=lambda h: (not h.startswith("/System"), not h.startswith("/Applications"), h))[0])
        try:
            info = _info_plist(p)
            res.update(bundle_id=info.get("CFBundleIdentifier"), path=str(p),
                       display_name=info.get("CFBundleDisplayName") or info.get("CFBundleName") or t)
        except (OSError, plistlib.InvalidFileException):
            res["path"] = str(p)
    return res


# ----------------------------------------------------------------------------
# Approval file: inspect (read-only) and add (explicit, backed up, exact IDs)
# ----------------------------------------------------------------------------

def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def inspect_approvals(path: Path = APPROVALS_PATH) -> dict:
    """Read the approval file. Returns ids, hash, mtime, and the raw document;
    never writes. An unexpected shape is an error, not an empty list."""
    out = {"path": str(path), "exists": path.exists(), "ids": [], "sha256": _sha(path), "mtime": None,
           "error": None, "other_keys": [], "raw": None}
    if not path.exists():
        return out
    out["mtime"] = dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
        ids = data.get(APPROVALS_KEY)
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
            raise ValueError(f"{APPROVALS_KEY} is missing or not a list of strings")
        out["ids"] = sorted(ids)
        out["other_keys"] = sorted(k for k in data if k != APPROVALS_KEY)
        out["raw"] = data
    except (ValueError, OSError) as exc:
        out["error"] = f"could not parse approval file: {exc}"
    return out


def add_approvals(bundle_ids: list[str], path: Path = APPROVALS_PATH, now: dt.datetime | None = None) -> dict:
    """Explicit setup step. Backs up the file, adds exact bundle IDs (no
    wildcards, no patterns), preserves every other key, writes atomically, and
    reports exactly what changed. Refuses a file whose shape it does not know."""
    bundle_ids = [b.strip() for b in bundle_ids]
    for bid in bundle_ids:
        if not is_bundle_id(bid):
            raise ValueError(f"not an exact bundle ID: {bid!r} (wildcards and whitespace are not accepted)")
    before = inspect_approvals(path)
    if before["error"]:
        raise ValueError(before["error"] + "; refusing to rewrite a file of unknown shape")
    now = now or dt.datetime.now()
    backup = None
    if path.exists():
        stamp = now.strftime("%Y%m%d-%H%M%S")
        backup, n = path.with_name(f"{path.name}.bak-{stamp}"), 1
        while backup.exists():  # never overwrite an earlier backup
            n += 1
            backup = path.with_name(f"{path.name}.bak-{stamp}-{n}")
        shutil.copy2(path, backup)
    doc = dict(before["raw"] or {})
    existing = list(doc.get(APPROVALS_KEY, []))
    added = [b for b in bundle_ids if b not in existing]
    already = [b for b in bundle_ids if b in existing]
    if added:
        doc[APPROVALS_KEY] = existing + added
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        tmp.write_text(json.dumps(doc), encoding="utf-8")
        os.replace(tmp, path)   # atomic: a crash leaves either the old file or the new one
    after = inspect_approvals(path)
    return {
        "path": str(path), "backup": str(backup) if backup else None,
        "added": added, "already_present": already,
        "before": before["ids"], "after": after["ids"], "other_keys_preserved": before["other_keys"],
        "sha256_before": before["sha256"], "sha256_after": after["sha256"],
        "helper_noticed": None, "helper_note": "not probed",
    }


# ----------------------------------------------------------------------------
# Environment checks (preflight)
# ----------------------------------------------------------------------------

def _run(argv: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"{argv[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{argv[0]}: timed out"


def codex_version(run=_run) -> str | None:
    rc, out, _ = run(["codex", "--version"])
    return out.strip() if rc == 0 else None


def computer_use_feature(run=_run) -> dict:
    """Parse `codex features list` for the computer_use row."""
    rc, out, err = run(["codex", "features", "list"])
    row = {"stable": None, "enabled": None, "raw": None}
    if rc != 0:
        row["raw"] = err.strip() or f"exit {rc}"
        return row
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == "computer_use":
            row["raw"] = line.strip()
            row["stable"] = "stable" in line
            row["enabled"] = parts[-1].lower() == "true"
    return row


def helper_status(home: Path, run=_run) -> dict:
    app = helper_app(home)
    st = {"path": str(app), "exists": app.is_dir(), "signed": None, "codesign": None}
    if st["exists"]:
        rc, _, err = run(["codesign", "--verify", "--strict", str(app)])
        st["signed"] = rc == 0
        st["codesign"] = "valid" if rc == 0 else err.strip()
    return st


def privacy_status(db: Path = TCC_DB, client: str = HELPER_BUNDLE_ID) -> dict:
    """Best-effort, read-only look at macOS's privacy database. This is private
    Apple implementation detail, not a supported API; a row is not proof that the
    live helper can use the permission, so preflight also does a harmless Sky read."""
    out = {name: None for name in TCC_SERVICES.values()}
    out["note"] = "read-only query of the macOS privacy database (unsupported; best effort)"
    if not db.exists():
        out["note"] = f"{db} not present or not readable"
        return out
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = con.execute("select service, auth_value from access where client = ?", (client,)).fetchall()
        con.close()
    except sqlite3.Error as exc:
        out["note"] = f"could not read {db}: {exc}"
        return out
    for service, auth in rows:
        if service in TCC_SERVICES:
            out[TCC_SERVICES[service]] = auth == 2
    return out


def approval_state(bundle_id: str | None, approvals: dict) -> str:
    """'approved' | 'not-approved' | 'unknown'. Headless runs see the file only;
    the Codex desktop session can hold approvals in memory that this cannot see."""
    if approvals.get("error") or not approvals.get("exists"):
        return "unknown"
    if not bundle_id:
        return "unknown"
    return "approved" if bundle_id in approvals["ids"] else "not-approved"


def preflight(app: str | None, env: dict | None = None, mdfind=_mdfind, run=_run,
              live: bool = False, runner=None, run_root: Path | None = None, tcc_db: Path = TCC_DB) -> dict:
    """Environment and target checks. Unknown counts as a problem: a permission
    the runner cannot confirm is not a permission it can rely on. With live=True
    one harmless read-only Sky call proves the helper can actually act."""
    home = codex_home(env)
    report = {
        "codex_home": str(home),
        "codex_version": codex_version(run),
        "computer_use_feature": computer_use_feature(run),
        "helper": helper_status(home, run),
        "privacy": privacy_status(tcc_db),
        "approvals": inspect_approvals(),
        "target": None,
        "live_probe": None,
        "ok": True,
        "problems": [],
    }
    if not report["codex_version"]:
        report["problems"].append("codex CLI not found on PATH")
    feat = report["computer_use_feature"]
    if not (feat["stable"] and feat["enabled"]):
        report["problems"].append(f"computer_use feature is not stable+enabled: {feat['raw']}")
    if not report["helper"]["exists"]:
        report["problems"].append(f"Computer Use helper missing at {report['helper']['path']} (CODEX_HOME={home})")
    elif report["helper"]["signed"] is False:
        report["problems"].append(f"helper signature check failed: {report['helper']['codesign']}")
    for name in TCC_SERVICES.values():
        state = report["privacy"].get(name)
        if state is False:
            report["problems"].append(f"macOS {name} is not granted to {HELPER_BUNDLE_ID}")
        elif state is None:
            report["problems"].append(
                f"macOS {name} for {HELPER_BUNDLE_ID} could not be confirmed ({report['privacy'].get('note')}); "
                "grant it in System Settings > Privacy & Security, or run preflight with --live to prove the helper can act")
    if app:
        target = resolve_app(app, mdfind=mdfind)
        target["approval"] = approval_state(target["bundle_id"], report["approvals"])
        report["target"] = target
        appr = report["approvals"]
        if target["approval"] == "not-approved":
            report["problems"].append(
                f"{target['display_name'] or app} ({target['bundle_id']}) is not in the persistent approval file; "
                f"a headless run will be refused. Fix: `computer_use.py approvals add --bundle-id {target['bundle_id']} --yes`")
        elif not target["bundle_id"]:
            report["problems"].append(
                f"could not resolve a bundle ID for {app!r}; pass the bundle ID or .app path so approval can be checked")
        elif appr.get("error"):
            report["problems"].append(f"approval file unreadable: {appr['error']}")
        elif not appr.get("exists"):
            report["problems"].append(f"approval file missing at {appr['path']}; a headless run will be refused for every app")
    if live and not report["problems"]:
        report["live_probe"] = live_probe(run_root or DEFAULT_RUN_ROOT, runner or run_codex, env=env)
        if not report["live_probe"]["ok"]:
            report["problems"].append(f"live Sky probe failed: {report['live_probe']['note']}")
    report["ok"] = not report["problems"]
    return report


PROBE_OK, PROBE_ERR = "CU_PROBE_OK", "CU_PROBE_ERR"


def live_probe(run_root: Path, runner, timeout: int = 180, env: dict | None = None) -> dict:
    """One read-only sky.list_apps() through codex exec. Proves the CLI, the plugin,
    the helper, and its permissions work together. Performs no UI action."""
    run_dir = new_run_dir(Path(run_root).expanduser(), "preflight-live-probe")
    brief = "\n".join([
        f"Read-only probe. In node_repl run: {BOOTSTRAP}",
        f"Then: try {{ var a = await sky.list_apps(); nodeRepl.write('{PROBE_OK} ' + a.length); }} catch (e) {{ nodeRepl.write('{PROBE_ERR} ' + String(e && e.message || e)); }}",
        "Do not click, type, scroll, drag, or open anything. Reply in the required JSON shape with status done, "
        "summary = the exact string node_repl wrote, question empty, confirmation_reason none, evidence [] and actions_taken [].",
    ])
    (run_dir / "brief.md").write_text(brief, encoding="utf-8")
    launch = runner(codex_argv(brief, run_dir, "low"), run_dir, timeout, env)
    joined = "\n".join(c["result"] or "" for c in parse_events(run_dir / "events.jsonl")["calls"])
    if launch.get("timed_out"):
        return {"ok": False, "note": "probe timed out", "run_dir": str(run_dir)}
    m = re.search(rf"{PROBE_OK} (\d+)", joined)
    if m:
        return {"ok": True, "note": f"sky.list_apps() returned {m.group(1)} apps", "run_dir": str(run_dir)}
    err = re.search(rf"{PROBE_ERR} (.*)", joined)
    return {"ok": False, "note": err.group(1)[:200] if err else f"no probe marker in the event stream (exit {launch.get('exit_code')})", "run_dir": str(run_dir)}


# ----------------------------------------------------------------------------
# The brief (what Codex is told) and the codex exec call
# ----------------------------------------------------------------------------

def _sky_rules() -> str:
    try:
        return SKY_RULES_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def build_brief(task: dict, target: dict) -> str:
    """One bounded stateful subtask. Every required section is present even when
    the caller left it empty, so a missing rule is visible in the brief."""
    app_line = target.get("display_name") or target["input"]
    bid = target.get("bundle_id") or "(unresolved; use the display name)"
    forbid = task.get("forbid") or "none stated"
    allow = task.get("allow") or "none stated"
    pre = task.get("preapproved") or "none"
    lines = [
        "# Computer Use subtask (from Claude Code, via the computer-use skill)",
        "",
        "## Goal", task["goal"], "",
        "## Definition of done (must be visible in accessibility text or a screenshot)", task["done"], "",
        "## Target app", f"Display name: {app_line}", f"Bundle ID: {bid}",
        "Use the bundle ID for every sky call. If a call fails by name, retry once with the bundle ID; never guess another app.", "",
        "## Starting state (as the caller believes it is; verify before acting)", task.get("start") or "unknown; observe first", "",
        "## Allowed actions", allow, "",
        "## Forbidden actions", forbid, "",
        "## Confirmation boundary",
        "Stop BEFORE any action that sends, submits, posts, deletes, changes permissions or settings, spends money, or transmits personal or sensitive data. "
        "Prepare it, describe exactly what will happen and to whom, then reply with status needs_confirmation and the question. "
        "Never perform such an action and ask afterwards.",
        f"Pre-approved by the user for this subtask (quoted; nothing else counts): {pre}", "",
        "## Procedure",
        f"1. In node_repl, run the bootstrap once: {BOOTSTRAP}",
        f"2. Observe first: sky.get_app_state({{app: \"{target.get('bundle_id') or app_line}\", disableDiff: true}}). Record what you see as observed_before.",
        "3. Take one action at a time. After EVERY state-changing action call get_app_state again and confirm the change you expected before the next action. Derive every element_index from the latest state; never reuse an index from before an action.",
        "4. If the app was not approved for Computer Use, or the helper errors, stop and reply with status blocked and the exact error text in reason. Do not retry.",
        "5. Finish with a fresh get_app_state so a screenshot exists, and record what you see as observed_after.",
        "6. Reply ONLY in the required JSON shape. evidence must list absolute screenshot paths (strip file://) or data URLs you actually received; actions_taken lists each UI action in order.",
        "",
        "## Sky rules", _sky_rules().strip(),
    ]
    return "\n".join(lines)


def codex_argv(brief: str, run_dir: Path, effort: str, schema: Path = SCHEMA_PATH, model: str | None = None) -> list[str]:
    argv = ["codex", "exec", "--skip-git-repo-check", "-C", str(run_dir), "--sandbox", "read-only",
            "-c", f"model_reasoning_effort={effort}"]
    if model:
        argv += ["-c", f"model={model}"]
    argv += ["--output-schema", str(schema), "-o", str(run_dir / "reply.json"), "--json", brief]
    return argv


def resume_argv(session_id: str, prompt: str, run_dir: Path, effort: str, schema: Path = SCHEMA_PATH) -> list[str]:
    # `codex exec resume` takes no -C or --sandbox; those come from the session.
    return ["codex", "exec", "resume", session_id, "--skip-git-repo-check", "-c", f"model_reasoning_effort={effort}",
            "--output-schema", str(schema), "-o", str(run_dir / "reply.json"), "--json", prompt]



def run_codex(argv: list[str], run_dir: Path, timeout: int, env: dict | None = None) -> dict:
    """Launch codex, append events to events.jsonl, kill the whole process group on
    timeout and reap it. Returns exit code, timed_out flag, elapsed seconds."""
    env = dict(os.environ if env is None else env)
    events = run_dir / "events.jsonl"
    stderr = run_dir / "stderr.txt"
    _ensure_trailing_newline(events)
    start = time.monotonic()
    with events.open("ab") as out, stderr.open("ab") as err, open(os.devnull, "rb") as devnull:
        proc = subprocess.Popen(argv, stdin=devnull, stdout=out, stderr=err, env=env, start_new_session=True)
        try:
            rc = proc.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(proc.pid, sig)
                    proc.wait(timeout=5)
                    break
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    continue
            rc, timed_out = -1, True
    return {"exit_code": rc, "timed_out": timed_out, "elapsed_s": round(time.monotonic() - start, 1)}


def _ensure_trailing_newline(path: Path) -> None:
    """A resumed turn appends to events.jsonl; a missing final newline would glue
    two JSON lines together and drop the first call of the riskier turn."""
    if path.exists() and path.stat().st_size:
        with path.open("rb+") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                fh.write(b"\n")


# ----------------------------------------------------------------------------
# Auditing the event stream: what Sky actually did, what it actually saw
# ----------------------------------------------------------------------------

SKY_CALL = re.compile(r"sky\.(\w+)\(\s*(\{.*?\})?\s*\)", re.S)



def parse_events(path: Path, start: int = 0) -> dict:
    """Pull the session ID, every node_repl call (code, result text, status), and
    every OTHER tool call out of the --json event stream from byte offset
    `start`. Malformed lines are counted, not trusted."""
    out = {"session_id": None, "calls": [], "other_tool_calls": [], "malformed_lines": 0,
           "end_offset": start, "stream_error": None}
    if not path.exists():
        return out
    data = path.read_bytes()[start:]
    out["end_offset"] = start + len(data)
    for line in data.decode("utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            out["malformed_lines"] += 1
            continue
        t = ev.get("type")
        if t == "thread.started":
            out["session_id"] = ev.get("thread_id")
        elif t == "error":
            out["stream_error"] = str(ev.get("message") or ev)[:300]
        if t != "item.completed":
            continue
        it = ev.get("item") or {}
        kind = it.get("type")
        if kind in (None, "agent_message", "reasoning", "todo_list"):
            continue
        if kind == "mcp_tool_call" and it.get("server") == "node_repl":
            args = it.get("arguments") or {}
            result = it.get("result") or {}
            text = "".join(c.get("text", "") for c in result.get("content", []) if isinstance(c, dict))
            out["calls"].append({"title": args.get("title"), "code": args.get("code", ""), "result": text,
                                 "status": it.get("status"),
                                 "surface": (result.get("_meta") or {}).get("codex/toolSurface")})
        else:
            # Shell commands, patches, other MCP servers: anything that could act
            # on the machine outside Sky. The audit refuses to call such a run done.
            label = f"{kind}:{it.get('server') or ''}/{it.get('tool') or ''}".rstrip(":/")
            out["other_tool_calls"].append({"kind": kind, "label": label, "status": it.get("status"),
                                            "excerpt": json.dumps(it.get("arguments") or it.get("command") or "")[:200]})
    return out



def _strip_js_comments(code: str) -> str:
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.S)
    return re.sub(r"^\s*//.*$", "", code, flags=re.M)


def _balanced_object(s: str, i: int) -> str | None:
    """The object literal starting at s[i] == '{', braces balanced and strings
    respected, or None when the argument is not a literal."""
    if i >= len(s) or s[i] != "{":
        return None
    depth, j, in_str = 0, i, None
    while j < len(s):
        ch = s[j]
        if in_str:
            if ch == "\\":
                j += 1
            elif ch == in_str:
                in_str = None
        elif ch in "'\"`":
            in_str = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[i:j + 1]
        j += 1
    return None


SKY_SITE = re.compile(r"\bsky\s*(?:\.\s*(\w+)|\[\s*['\"](\w+)['\"]\s*\])\s*\(")
LOOP_RE = re.compile(r"\b(for|while)\s*\(|\.(forEach|map)\s*\(")


def record_actions(calls: list[dict]) -> list[dict]:
    """Every sky call SITE in the executed code, in order. The method name is
    always recorded; the args are the object literal when there is one, else
    `parsed` is False and the audit treats a state-changing call as unverifiable.
    This is the runner's own action log; the model's actions_taken is a claim."""
    actions = []
    for i, call in enumerate(calls):
        code = _strip_js_comments(call.get("code") or "")
        looped = bool(LOOP_RE.search(code))
        for m in SKY_SITE.finditer(code):
            method = m.group(1) or m.group(2)
            rest = code[m.end():]
            k = len(rest) - len(rest.lstrip())
            if rest[k:k + 1] == ")":
                obj, parsed = "", True
            else:
                obj = _balanced_object(rest, k)
                parsed = obj is not None
            actions.append({"call": i, "method": method, "args": obj if parsed else rest[:80].strip(),
                            "parsed": parsed, "in_loop": looped, "title": call.get("title"),
                            "result_excerpt": (call.get("result") or "")[:200]})
    return actions



def lint_actions(actions: list[dict], calls: list[dict]) -> list[str]:
    """Rule violations visible in the recorded calls. Each string is a finding.
    Advisory by themselves; the audit turns the load-bearing ones into a verdict."""
    findings = []
    seen_full_state = False
    last_state_idx = -1
    has_xy = lambda a: re.search(r"\bx\s*:", a) and re.search(r"\by\s*:", a)
    for n, a in enumerate(actions):
        args = a["args"]
        if a["method"] == "get_app_state":
            last_state_idx = n
            if re.search(r"disableDiff\s*:\s*true", args):
                seen_full_state = True
        if a["method"] in STATE_CHANGING and not a["parsed"]:
            findings.append(f"action {n}: {a['method']} with a non-literal argument ({args[:40]!r}); what it targeted cannot be verified")
        if a["method"] in STATE_CHANGING and a["in_loop"]:
            findings.append(f"action {n}: {a['method']} inside a loop; the number of actions taken is unknown")
        if a["method"] == "scroll" and a["parsed"] and "element_index" not in args and not has_xy(args):
            findings.append(f"action {n}: scroll without element_index or x/y coordinates (will fail)")
        if a["method"] == "type_text" and ("\\n" in args or "\\r" in args):
            findings.append(f"action {n}: type_text with a newline; newlines can submit or send. Use paste for multiline text")
        if a["method"] == "drag" and last_state_idx < n - 1:
            findings.append(f"action {n}: drag without a fresh get_app_state immediately before it")
        if a["method"] == "perform_secondary_action":
            m = re.search(r"action:\s*['\"]([^'\"]+)['\"]", args)
            name = m.group(1) if m else None
            prior = "\n".join(c["result"] for c in calls[: a["call"]])
            if name and name not in prior:
                findings.append(f"action {n}: secondary action {name!r} not seen in any earlier accessibility text (guessed name)")
        if a["method"] in STATE_CHANGING and n + 1 < len(actions) and actions[n + 1]["method"] in STATE_CHANGING:
            findings.append(f"action {n}: {a['method']} followed by {actions[n + 1]['method']} with no get_app_state between them (unverified state)")
    if actions and actions[-1]["method"] in STATE_CHANGING:
        findings.append(f"action {len(actions) - 1}: {actions[-1]['method']} is the last call; no get_app_state after it (end state unverified)")
    if actions and not seen_full_state and any(a["method"] == "get_app_state" for a in actions):
        findings.append("no get_app_state with disableDiff: true; the model never took a full tree")
    return findings


def risky_signals(actions: list[dict], calls: list[dict]) -> list[str]:
    """Post-hoc pointers at the confirmation boundary: risky words in tool-call
    titles or clicked-element args, Return pressed in a state-changing sequence."""
    out = []
    for a in actions:
        blob = f"{a.get('title') or ''} {a['args']}"
        if a["method"] in STATE_CHANGING and RISKY_WORDS.search(blob):
            out.append(f"{a['method']}: {RISKY_WORDS.search(blob).group(0)!r} in {blob[:120]!r}")
        if a["method"] == "press_key" and re.search(r"(Return|Enter|KP_Enter)", a["args"]):
            out.append(f"press_key Return/Enter: {a['args'][:120]}")
    return out


def screenshot_refs(calls: list[dict]) -> list[str]:
    refs = []
    for c in calls:
        for m in FILE_URL.finditer(c["result"] or ""):
            refs.append(urllib.parse.unquote(m.group(1)))
        for m in DATA_URL.finditer(c["result"] or ""):
            refs.append(f"data:image/{m.group(1)};base64,<{len(m.group(2))} chars>")
    return refs



def _real(p) -> str:
    return os.path.realpath(str(p))


def validate_evidence(items: list, shots_dir: Path, allowed_sources: list | None = None,
                      stream_text: str = "", prefix: str = "t1") -> tuple[list[str], list[str]]:
    """Copy each evidence item the model named into the private run dir, but only
    if it is an image THIS RUN produced: a regular file (no symlinks) under the Sky
    screenshot folder or named in the event stream, or a data URL that appears in
    the stream. Size-capped, magic-bytes checked, never overwritten."""
    ok, rejected = [], []
    shots_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    allowed = {_real(p) for p in (allowed_sources or [])}
    sky_dir = _real(SKY_SHOT_DIR)

    def dest_for(name: str) -> Path:
        d, n = shots_dir / f"{prefix}-{name}", 1
        while d.exists():
            n += 1
            d = shots_dir / f"{prefix}-{n}-{name}"
        return d

    def ext_for(head: bytes) -> str | None:
        return next((e for magic, e in IMAGE_MAGIC.items() if head.startswith(magic)), None)

    for n, raw in enumerate(items or []):
        if not isinstance(raw, str) or not raw.strip():
            rejected.append(f"{raw!r}: not a string")
            continue
        s = raw.strip()
        m = DATA_URL.match(s)
        if m:
            if m.group(0)[:120] not in stream_text:
                rejected.append(f"data URL {n}: not produced by this run")
                continue
            if len(m.group(2)) > EVIDENCE_MAX_BYTES * 4 // 3:
                rejected.append(f"data URL {n}: larger than {EVIDENCE_MAX_BYTES} bytes")
                continue
            try:
                data = base64.b64decode(m.group(2), validate=True)
            except (ValueError, base64.binascii.Error):
                rejected.append(f"data URL {n}: undecodable")
                continue
            ext = ext_for(data[:8])
            if not ext:
                rejected.append(f"data URL {n}: not a PNG, JPEG, or WebP")
                continue
            dest = dest_for(f"evidence-{n:02d}.{ext}")
            dest.write_bytes(data)
            ok.append(str(dest))
            continue
        path = s[len("file://"):] if s.startswith("file://") else s
        src, why = None, "no such file"
        for cand in (Path(path), Path(urllib.parse.unquote(path))):
            if not cand.is_absolute():
                why = "not an absolute path"
                continue
            try:
                st = os.lstat(cand)
            except OSError:
                continue
            if stat.S_ISLNK(st.st_mode):
                why = "is a symlink"
                break
            if not stat.S_ISREG(st.st_mode):
                why = "not a regular file"
                break
            src = cand
            break
        if src is None:
            rejected.append(f"{s}: {why}")
            continue
        real = _real(src)
        if real not in allowed and os.path.dirname(real) != sky_dir:
            rejected.append(f"{s}: not produced by this run (not under {SKY_SHOT_DIR} and not named in the event stream)")
            continue
        if src.stat().st_size > EVIDENCE_MAX_BYTES:
            rejected.append(f"{s}: larger than {EVIDENCE_MAX_BYTES} bytes")
            continue
        with src.open("rb") as fh:
            head = fh.read(12)
        if not ext_for(head):
            rejected.append(f"{s}: not a PNG, JPEG, or WebP")
            continue
        dest = dest_for(f"evidence-{n:02d}-{src.name}")
        shutil.copyfile(src, dest)
        ok.append(str(dest))
    return ok, rejected


def load_reply(path: Path) -> tuple[dict | None, str | None]:
    """The model's schema-shaped last message, or why it could not be trusted."""
    if not path.exists():
        return None, "reply.json missing (codex wrote no final message)"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return None, f"reply.json is not valid JSON: {exc}"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    missing = [k for k in schema["required"] if k not in data]
    if missing:
        return None, f"reply.json missing required fields: {missing}"
    if data.get("status") not in schema["properties"]["status"]["enum"]:
        return None, f"reply.json has an unknown status: {data.get('status')!r}"
    return data, None



def _base_result(run_dir: Path, target: dict, task: dict, effort: str) -> dict:
    return {
        "runner_version": __version__, "status": "failed", "summary": "", "question": "",
        "session_id": None,
        "target": {k: (target or {}).get(k) for k in ("input", "display_name", "bundle_id")},
        "confirmation_reason": "none", "observed_before": "", "observed_after": "",
        "evidence": [], "evidence_rejected": [], "actions_recorded": [], "model_actions_claimed": [],
        "other_tool_calls": [], "risky_signals": [], "lint": [], "screenshots_seen": [],
        "reason": "", "effort": effort,
        "task": {k: (task or {}).get(k) for k in ("goal", "done", "start", "allow", "forbid", "preapproved")},
        "launch": None, "run_dir": str(run_dir), "malformed_event_lines": 0,
        "may_have_had_effect": False, "run_may_have_had_effect": False, "preflight_skipped": False,
    }


def _preapproved_covers(signal: str, preapproved: str) -> bool:
    """A recorded risky action is only acceptable if the user's own pre-approval
    words name the same kind of action. Return/Enter needs send/submit/return/enter."""
    pre = (preapproved or "").lower()
    if not pre.strip():
        return False
    if signal.startswith("press_key Return/Enter"):
        return any(w in pre for w in ("return", "enter", "send", "submit"))
    m = re.search(r": '([^']+)' in", signal)
    return bool(m) and m.group(1).lower() in pre


def audit(run_dir: Path, reply: dict | None, reply_error: str | None, launch: dict, target: dict,
          task: dict, effort: str, parsed: dict | None = None, turn: int = 1, prior_effect: bool = False) -> dict:
    """Combine the model's claim with what the event stream shows. The runner's
    verdict fails closed: any doubt downgrades status and says why. Nothing here
    lets the model's prose upgrade a verdict; it can only lower one."""
    parsed = parsed or parse_events(run_dir / "events.jsonl")
    calls = parsed["calls"]
    actions = record_actions(calls)
    result = _base_result(run_dir, target, task, effort)
    result.update({
        "session_id": parsed["session_id"], "actions_recorded": actions,
        "other_tool_calls": parsed.get("other_tool_calls", []),
        "risky_signals": risky_signals(actions, calls), "lint": lint_actions(actions, calls),
        "screenshots_seen": screenshot_refs(calls), "launch": launch,
        "malformed_event_lines": parsed["malformed_lines"],
    })
    had_effect = any(a["method"] in STATE_CHANGING for a in actions) or bool(result["other_tool_calls"])
    result["may_have_had_effect"] = had_effect
    result["run_may_have_had_effect"] = had_effect or prior_effect
    joined = "\n".join(c["result"] or "" for c in calls)

    # Fail-closed checks that do not depend on the model's words.
    if launch.get("timed_out"):
        result["status"], result["reason"] = "failed", (
            f"timed out after {launch.get('elapsed_s')}s. " +
            ("State-changing actions were recorded; do NOT retry blindly, observe first." if had_effect
             else "No state-changing action was recorded."))
        return result
    if launch.get("exit_code") not in (0, None):
        result["status"], result["reason"] = "failed", f"codex exited {launch.get('exit_code')}: {parsed.get('stream_error') or 'see stderr.txt'}"
        return result
    helper_hit = next((c["result"][:200] for c in calls if c["result"] and HELPER_ERROR.search(c["result"])), None)
    if helper_hit:
        result["status"], result["reason"] = "failed", f"helper error in the event stream: {helper_hit}"
        return result
    na = NOT_APPROVED.search(joined)
    if na:
        result["status"], result["reason"] = "blocked", (
            f"Computer Use was not approved to use {na.group(1).strip()} (headless runs see only the persistent approval file)")
        return result
    if reply is None:
        result["status"], result["reason"] = "failed", reply_error or "no reply"
        return result

    # The model's claim, then the runner's own checks on top of it.
    result["summary"] = str(reply.get("summary", ""))
    result["question"] = str(reply.get("question", ""))
    result["confirmation_reason"] = reply.get("confirmation_reason", "none")
    result["observed_before"] = str(reply.get("observed_before", ""))
    result["observed_after"] = str(reply.get("observed_after", ""))
    result["model_actions_claimed"] = list(reply.get("actions_taken") or [])
    result["evidence"], result["evidence_rejected"] = validate_evidence(
        reply.get("evidence"), run_dir / "shots", allowed_sources=result["screenshots_seen"],
        stream_text=joined, prefix=f"t{turn}")
    status = reply["status"]
    reason = str(reply.get("reason", ""))

    def downgrade(new_status, why):
        nonlocal status, reason
        if status in ("done", "needs_confirmation"):
            status, reason = new_status, why

    if status == "needs_confirmation" and not result["question"].strip():
        downgrade("failed", "needs_confirmation without a question")
    if status == "done" and result["confirmation_reason"] not in ("none", None):
        downgrade("blocked", f"model marked confirmation_reason={result['confirmation_reason']} but reported done; treating as unverified")
    if parsed["malformed_lines"]:
        downgrade("blocked", f"{parsed['malformed_lines']} unparseable event line(s); the action log may be incomplete")
    if result["other_tool_calls"]:
        labels = sorted({o["label"] for o in result["other_tool_calls"]})
        downgrade("blocked", f"actions taken outside Sky ({', '.join(labels)}); the audit cannot see what they did")
    bad_status = [c for c in calls if c.get("status") not in (None, "completed")]
    if bad_status:
        downgrade("blocked", f"{len(bad_status)} node_repl call(s) did not complete cleanly")
    unverifiable = [f for f in result["lint"] if "non-literal argument" in f or "inside a loop" in f]
    if unverifiable:
        downgrade("blocked", unverifiable[0])
    if STALE_INDEX.search(joined):
        downgrade("blocked", "a call reported a stale or missing element index; state unverified")
    uncovered = [s for s in result["risky_signals"] if not _preapproved_covers(s, (task or {}).get("preapproved", ""))]
    if uncovered:
        downgrade("blocked", f"risky action recorded without a matching pre-approval: {uncovered[0]}")
    trailing = [f for f in result["lint"] if "end state unverified" in f]
    if trailing and had_effect:
        downgrade("blocked", trailing[0])
    if status == "done":
        if had_effect and not result["observed_after"].strip():
            status, reason = "failed", "state-changing actions recorded but no observed_after; end state unverified"
        elif not actions:
            status, reason = "failed", "model reported done but no Sky call was recorded in the event stream"
        elif reply.get("evidence") and not result["evidence"]:
            status, reason = "failed", f"none of the named evidence was produced by this run: {result['evidence_rejected']}"
    if status == "needs_confirmation" and result["confirmation_reason"] == "none":
        result["confirmation_reason"] = "other"
    result["status"], result["reason"] = status, reason
    return result


# ----------------------------------------------------------------------------
# Run, resume, pending state, retention
# ----------------------------------------------------------------------------


def new_run_dir(root: Path, slug: str, now: dt.datetime | None = None) -> Path:
    now = now or dt.datetime.now()
    safe = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")[:40] or "task"
    if not root.exists():
        root.mkdir(parents=True, mode=0o700)   # only a root the runner created gets its mode set
    base = root / f"{now.strftime('%Y%m%d-%H%M%S')}-{safe}"
    d, n = base, 1
    while True:  # two runs in the same second must not share a directory
        try:
            d.mkdir(mode=0o700)
            return d
        except FileExistsError:
            n += 1
            d = base.with_name(f"{base.name}-{n}")


def write_pending(run_dir: Path, result: dict) -> Path:
    """Everything a later resume needs, kept beside the run: exact question,
    session ID, last verified state, run directory."""
    p = run_dir / "pending.json"
    p.write_text(json.dumps({
        "session_id": result["session_id"], "question": result["question"],
        "confirmation_reason": result["confirmation_reason"],
        "last_verified_state": result["observed_after"] or result["observed_before"],
        "evidence": result["evidence"], "run_dir": str(run_dir), "target": result["target"],
        "effort": result["effort"], "created": dt.datetime.now().isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")
    return p


def resume_prompt(answer: str, pending: dict) -> str:
    bid = (pending.get("target") or {}).get("bundle_id") or (pending.get("target") or {}).get("display_name")
    return "\n".join([
        f"User's answer to your question ({pending.get('question', '')!r}): {answer}",
        "",
        "Before acting on it:",
        f"1. Re-run the bootstrap in node_repl (the REPL state did not survive): {BOOTSTRAP}",
        f"2. Take a fresh full state: sky.get_app_state({{app: \"{bid}\", disableDiff: true}}) and confirm the screen still matches your last verified state. If it does not, stop and reply blocked with what changed.",
        "3. Every element_index must come from this fresh state. Never reuse an index from before.",
        "4. If the answer is not a clear yes to the exact action you described, do not perform it; reply blocked with reason 'user declined'.",
        "5. After the action, get_app_state again, record observed_after, and reply in the required JSON shape. Do not perform any further action needing confirmation; stop and ask again instead.",
    ])



def do_run(args, runner=run_codex, mdfind=_mdfind, env: dict | None = None, run=_run, tcc_db: Path = TCC_DB) -> dict:
    """The `run` subcommand as a function so tests can drive it with a fake runner."""
    root = Path(args.run_root).expanduser()
    prune_runs(root, DEFAULT_KEEP_DAYS)
    pre = preflight(args.app, env=env, mdfind=mdfind, run=run, tcc_db=tcc_db)
    target = pre["target"] or resolve_app(args.app, mdfind=mdfind)
    run_dir = new_run_dir(root, args.goal)
    (run_dir / "preflight.json").write_text(json.dumps(pre, indent=2), encoding="utf-8")
    task = {"goal": args.goal, "done": args.done, "start": args.start, "allow": args.allow,
            "forbid": args.forbid, "preapproved": args.preapproved}
    if not pre["ok"] and not args.skip_preflight:
        result = _base_result(run_dir, target, task, args.effort)
        result.update(status="blocked", reason="preflight failed: " + "; ".join(pre["problems"]))
        (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    brief = build_brief(task, target)
    (run_dir / "brief.md").write_text(brief, encoding="utf-8")
    argv = codex_argv(brief, run_dir, args.effort, model=args.model)
    launch = runner(argv, run_dir, args.timeout, env)
    reply, err = load_reply(run_dir / "reply.json")
    result = audit(run_dir, reply, err, launch, target, task, args.effort)
    result["preflight_skipped"] = bool(args.skip_preflight and not pre["ok"])
    if result["status"] == "needs_confirmation":
        write_pending(run_dir, result)
    (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result



CLEAR_YES = re.compile(r"^\s*(yes|y|yep|yeah|ok|okay|go ahead|do it|proceed|confirmed?|approved?)\b[\s.!,]*(please|go ahead|do it|send it|proceed|thanks)?[\s.!]*$", re.I)


def is_clear_yes(answer: str) -> bool:
    """Only an unqualified yes resumes. 'yes but change X' is a new subtask."""
    return bool(CLEAR_YES.match(answer or ""))


def do_resume(args, runner=run_codex, env: dict | None = None) -> dict:
    run_dir = Path(args.run_dir).expanduser()
    pending_path = run_dir / "pending.json"
    if not pending_path.exists():
        raise SystemExit(f"nothing to resume: {pending_path} does not exist (only needs_confirmation runs can be resumed)")
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    if not pending.get("session_id"):
        raise SystemExit("pending.json has no session_id; cannot resume")
    if not (args.answer or "").strip():
        raise SystemExit("--answer is required; the user's exact words, not a paraphrase")
    prev_path = run_dir / "result.json"
    prev = json.loads(prev_path.read_text(encoding="utf-8")) if prev_path.exists() else {}
    turn = 2
    while (run_dir / f"result.json.turn{turn - 1}").exists():
        turn += 1
    for name in ("reply.json", "result.json"):   # keep every turn's record
        p = run_dir / name
        if p.exists():
            p.rename(run_dir / f"{name}.turn{turn - 1}")
    effort = args.effort or pending.get("effort") or DEFAULT_EFFORT
    task = prev.get("task") or {}
    target = pending.get("target") or prev.get("target") or {}
    prior_effect = bool(prev.get("run_may_have_had_effect") or prev.get("may_have_had_effect"))
    if not is_clear_yes(args.answer):
        # The runner, not the model, judges the answer. Nothing is launched.
        result = _base_result(run_dir, target, task, effort)
        result.update(status="blocked", session_id=pending["session_id"], run_may_have_had_effect=prior_effect,
                      reason=f"user did not give a clear yes ({args.answer!r}); nothing was resumed. Start a new subtask if the answer changes the task")
        result["resumed_from"] = str(pending_path)
        pending_path.rename(run_dir / "pending.json.answered")
        (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    # The user's yes to the exact question IS the pre-approval for this turn, and
    # only for the action that question described.
    task = dict(task)
    task["preapproved"] = " | ".join(x for x in (
        task.get("preapproved") or "", f"user answered {args.answer!r} to {pending.get('question', '')!r}") if x)
    events = run_dir / "events.jsonl"
    _ensure_trailing_newline(events)
    offset = events.stat().st_size if events.exists() else 0
    prompt = resume_prompt(args.answer, pending)
    (run_dir / f"resume-prompt.turn{turn}.md").write_text(prompt, encoding="utf-8")
    argv = resume_argv(pending["session_id"], prompt, run_dir, effort)
    launch = runner(argv, run_dir, args.timeout, env)
    reply, err = load_reply(run_dir / "reply.json")
    parsed = parse_events(events, start=offset)   # only this turn's bytes are this turn's actions
    parsed["session_id"] = parsed["session_id"] or pending["session_id"]
    result = audit(run_dir, reply, err, launch, target, task, effort, parsed=parsed, turn=turn, prior_effect=prior_effect)
    result["resumed_from"] = str(pending_path)
    result["turn"] = turn
    if result["status"] == "needs_confirmation":
        write_pending(run_dir, result)
    else:
        pending_path.rename(run_dir / "pending.json.answered")
    (run_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def is_run_dir(d: Path) -> bool:
    """Only directories this runner made: stamped name AND a runner marker file."""
    return d.is_dir() and bool(RUN_DIR_NAME.match(d.name)) and any((d / m).exists() for m in RUN_DIR_MARKERS)


def prune_runs(root: Path, keep_days: int, now: dt.datetime | None = None) -> list[str]:
    """Delete run directories older than keep_days, except ones still pending.
    Anything that is not recognisably a run directory is left alone."""
    now = now or dt.datetime.now()
    removed = []
    if not root.exists():
        return removed
    cutoff = now - dt.timedelta(days=keep_days)
    for d in sorted(root.iterdir()):
        if not is_run_dir(d) or (d / "pending.json").exists():
            continue
        if dt.datetime.fromtimestamp(d.stat().st_mtime) < cutoff:
            shutil.rmtree(d)
            removed.append(str(d))
    return removed


# ----------------------------------------------------------------------------
# Approval setup verification (does the live helper notice a file change?)
# ----------------------------------------------------------------------------


def probe_approval(bundle_id: str, run_root: Path, runner=run_codex, timeout: int = 180, env: dict | None = None) -> dict:
    """One read-only get_app_state against the app, straight after a file edit.
    Tells the caller whether the running helper saw the new approval. This is a
    real Codex call and may bring the app forward."""
    run_dir = new_run_dir(Path(run_root).expanduser(), f"approval-probe-{bundle_id}")
    brief = "\n".join([
        f"Read-only probe. In node_repl run: {BOOTSTRAP}",
        f"Then: try {{ var s = await sky.get_app_state({{app: \"{bundle_id}\", disableDiff: true}}); nodeRepl.write('{PROBE_OK} ' + s.text.length); }} catch (e) {{ nodeRepl.write('{PROBE_ERR} ' + String(e && e.message || e)); }}",
        "Do not click, type, scroll, drag, or open anything else. Reply in the required JSON shape with status done, "
        "summary = the exact string node_repl wrote, question empty, confirmation_reason none, evidence [] and actions_taken [].",
    ])
    (run_dir / "brief.md").write_text(brief, encoding="utf-8")
    launch = runner(codex_argv(brief, run_dir, "low"), run_dir, timeout, env)
    joined = "\n".join(c["result"] or "" for c in parse_events(run_dir / "events.jsonl")["calls"])
    if launch.get("timed_out"):
        verdict, note = None, "probe timed out; helper state unknown"
    elif NOT_APPROVED.search(joined):
        verdict, note = False, "helper still reports the app as not approved; restart the helper (quit the Codex app and any SkyComputerUse process) and probe again"
    elif re.search(rf"{PROBE_OK} \d+", joined):
        verdict, note = True, "helper accepted the newly approved app without a restart"
    else:
        verdict, note = None, f"probe gave no clear answer (exit {launch.get('exit_code')}); see {run_dir}"
    return {"helper_noticed": verdict, "helper_note": note, "probe_run_dir": str(run_dir), "launch": launch}


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def _print(obj) -> None:
    print(json.dumps(obj, indent=2))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="computer_use.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("preflight", help="check the environment and, with --app, the target's approval state")
    p.add_argument("--app")
    p.add_argument("--live", action="store_true", help="also run one read-only Sky call through codex exec (a real model call)")
    p.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))

    p = sub.add_parser("resolve-app", help="display name | .app path | bundle ID -> bundle ID")
    p.add_argument("app")

    p = sub.add_parser("approvals", help="inspect or (explicitly) extend the persistent approval file")
    ps = p.add_subparsers(dest="acmd", required=True)
    ps.add_parser("inspect")
    pa = ps.add_parser("add", help="backup, add exact bundle IDs, report, verify the helper noticed")
    pa.add_argument("--bundle-id", action="append", required=True, help="exact bundle ID; repeatable; no wildcards")
    pa.add_argument("--yes", action="store_true", help="required; this edits the helper's approval file")
    pa.add_argument("--no-probe", action="store_true", help="skip the read-only helper probe after the edit")
    pa.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))

    p = sub.add_parser("run", help="one bounded subtask")
    p.add_argument("--app", required=True, help="any Mac app: display name, .app path, or bundle ID")
    p.add_argument("--goal", required=True)
    p.add_argument("--done", required=True, help="what must be visible when the subtask is complete")
    p.add_argument("--start", default="", help="the starting state as you believe it is")
    p.add_argument("--allow", default="", help="allowed actions, plain words")
    p.add_argument("--forbid", default="", help="forbidden actions, plain words")
    p.add_argument("--preapproved", default="", help="the user's exact pre-approval words, or empty")
    p.add_argument("--effort", choices=EFFORTS, default=DEFAULT_EFFORT)
    p.add_argument("--model", default=None, help="override the Codex model (default: the profile's)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))
    p.add_argument("--skip-preflight", action="store_true", help="run even when preflight found problems (not recommended)")

    p = sub.add_parser("resume", help="answer a needs_confirmation question and continue the same Codex session")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--answer", required=True, help="the user's exact words")
    p.add_argument("--effort", choices=EFFORTS, default=None)
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    p = sub.add_parser("prune-runs", help="delete old run directories (pending ones are kept)")
    p.add_argument("--keep-days", type=int, default=DEFAULT_KEEP_DAYS)
    p.add_argument("--run-root", default=str(DEFAULT_RUN_ROOT))

    args = ap.parse_args(argv)

    if args.cmd == "preflight":
        rep = preflight(args.app, live=args.live, run_root=Path(args.run_root).expanduser())
        _print(rep)
        return 0 if rep["ok"] else 2
    if args.cmd == "resolve-app":
        _print(resolve_app(args.app))
        return 0
    if args.cmd == "approvals":
        if args.acmd == "inspect":
            _print(inspect_approvals())
            return 0
        if not args.yes:
            print("refusing: `approvals add` edits the Computer Use approval file. Re-run with --yes.", file=sys.stderr)
            return 2
        try:
            rep = add_approvals([b.strip() for b in args.bundle_id])
        except ValueError as exc:
            print(f"refusing: {exc}", file=sys.stderr)
            return 2
        if rep["added"] and not args.no_probe:
            rep.update(probe_approval(rep["added"][0], Path(args.run_root).expanduser()))
        _print(rep)
        return 0
    if args.cmd == "run":
        res = do_run(args)
        _print(res)
        return {"done": 0, "needs_confirmation": 3, "blocked": 4, "failed": 5}[res["status"]]
    if args.cmd == "resume":
        res = do_resume(args)
        _print(res)
        return {"done": 0, "needs_confirmation": 3, "blocked": 4, "failed": 5}[res["status"]]
    if args.cmd == "prune-runs":
        _print({"removed": prune_runs(Path(args.run_root).expanduser(), args.keep_days)})
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

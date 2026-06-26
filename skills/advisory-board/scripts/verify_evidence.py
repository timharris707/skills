#!/usr/bin/env python3
"""Resolve a verdict.json's typed evidence against the reviewed material and stamp
each citation verified | unverified | refuted.

WHAT THIS PROVES (design section 9 - read it before trusting a green stamp): that
the *receipt resolves* - the cited line exists, the quoted text is present in the
captured packet. It does NOT prove the inference drawn from that receipt is sound.
It catches fabrication (a hallucinated path:line, a quote that was never in the
source), not faulty reasoning. The scary failure is a hallucinated citation driving
a false gate; this is the cheapest partial defense against it.

Resolution respects quarantine:
  * `source` quotes are checked against the CAPTURED PACKET, never by re-fetching
    the URL (a live fetch would reintroduce the network in gate mode).
  * `command` re-execution is OPT-IN and allowlist-gated (M3 / v1.x). With no
    `--allow-command` pattern it stays `unverified` (the safe default — exactly
    the pre-M3 behavior). See "Command re-execution" below.
  * `judgment` evidence has no external referent and is left unstamped, by design.

How each kind resolves:
  code  path:line   -> verified  if the file has that line;
                       refuted   if the file exists but the line is out of range;
                       unverified if the file isn't under --source, or no --source.
  code  path:symbol -> verified  if the symbol token appears in the cited file;
                       refuted   if the file exists but the token does not;
                       unverified if the file isn't found / no --source.
  source url+quote  -> verified  if the (whitespace-normalized) quote is in the packet;
                       refuted   if a packet was given and the quote is absent;
                       unverified if no packet was given.
  command           -> verified  if (re-run, allowlisted) exit == expect_exit (default 0)
                       AND any `expect` substring is present in the output;
                       refuted   if it ran but the exit or `expect` substring mismatched;
                       unverified if not allowlisted, or it could not be run at all.

A missing file is `unverified`, not `refuted`: --source may be an incomplete tree,
and we refuse to cry fabrication on a file we simply weren't handed. A file we DO
have with a bad line/symbol is `refuted` - that is a positive contradiction. The
same asymmetry holds for `command`: a command that COULDN'T run (not allowlisted,
executable absent, timed out, unparseable) is `unverified`; one that RAN and
contradicted its expectation is `refuted`.

Command re-execution (M3) — read before enabling:
  Re-running a command cited as evidence is an EXECUTION surface. When the verdict
  was synthesized from untrusted source (the M2 synthesizer over poisoned reviews),
  a `command` citation can be attacker-influenced. Re-execution is OFF by default;
  enabling it is two explicit allowlists plus several structural containments. The
  program allowlist (NOT the regex) is the load-bearing control:
    * OPT-IN, PROGRAM-PINNED: nothing re-runs unless you pass `--allow-program NAME`
      (repeatable). A command runs only if its argv[0] (after shlex.split) is a BARE
      program name in that set — never a path (`./x`, `/bin/sh`, `../x` are refused).
      This pins which program runs INDEPENDENT of any regex, so a too-broad
      `--allow-command` pattern cannot let the attacker choose the executable.
    * OPTIONAL ARG CONSTRAINT: `--allow-command REGEX` (repeatable) further requires
      the full command to `re.fullmatch` a pattern — for pinning args, not the
      program. PATTERNS ARE LIVE REGEXES (`.` is a wildcard); they refine, never
      widen, the program allowlist.
    * NO SHELL: split with shlex, run with shell=False, so `;`/`&&`/`|`/`>`/`$(...)`/
      globs are inert literal args, not operators.
    * CLEAN PATH, NO PLANTED BINARIES: argv[0] is resolved with shutil.which against
      a CURATED PATH (inherited PATH minus `.`/empty/relative entries), and a binary
      that resolves INSIDE the working dir is refused — so a `pytest` planted in the
      material under review cannot shadow the real one.
    * ISOLATED CWD + HOME: commands run in a fresh empty throwaway dir by default
      (NOT the source tree) — so a command cannot read attacker files from cwd or
      execute an attacker `conftest.py`/`Makefile`. HOME is a SEPARATE throwaway
      (never cwd), so a HOME-writing command can't drop dotfiles into a real
      `--rerun-cwd` tree either. `--rerun-cwd DIR` opts into a real tree (a sharper
      edge); a filesystem root is refused.
    * SCRUBBED ENV: only PATH (curated) + HOME (a throwaway) + locale vars pass; no
      inherited API keys / tokens (and no PYTHONPATH/VIRTUAL_ENV — a bare command
      that then exits non-zero is `unverified`, not `refuted`, so an env-shaped
      failure isn't defamed as a fabricated receipt). stdin is closed; a hard
      timeout process-group-kills.
    * STRUCTURAL MATCH ONLY (design section 11 / principle 1): the verdict is exit
      code + optional verbatim `expect` substring — never a reading of the output's
      meaning. The observed exit, a head+tail output excerpt, and whether `expect`
      was found are attached to the evidence under `observed`.
  Still best-effort: a subprocess is not a kernel sandbox. A command you allowlist
  can still READ files its uid can read and PERSIST them into verdict.json's
  `observed.output` — so do NOT allowlist programs that read secrets (`cat`, `env`,
  `printenv`). Allowlist only programs you trust to be read-only over public material.

Usage:
  verify_evidence.py verdict.json --source SRC --packet PKT      stamp in place
  verify_evidence.py verdict.json --run RUNDIR                   derive the packet from a run dir
  verify_evidence.py verdict.json --source SRC -o stamped.json   write elsewhere
  verify_evidence.py verdict.json --source SRC --check           report only; write nothing
  verify_evidence.py verdict.json --allow-program pytest --allow-command 'pytest -q .*' \
      --rerun-cwd ./src                                          re-run allowlisted commands

Exit codes: 0 ok, 2 usage / bad JSON. Gating on the stamps is board_verdict.py's job.
Standard library only; no third-party dependencies.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys

EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")
_WS = re.compile(r"\s+")

# Command re-execution (M3) tunables.
DEFAULT_RERUN_TIMEOUT = 30          # hard per-command timeout (seconds)
RERUN_OUTPUT_LIMIT = 4000           # chars of combined output attached to `observed`
                                    # (kept as head+tail so a runner's tail summary survives)
# Locale-only env passthrough for a re-executed command. PATH and HOME are set
# EXPLICITLY by _rerun_env (curated PATH; HOME = the throwaway cwd), never inherited —
# so a re-run can neither resolve a planted binary via a dirty PATH nor read ~/.aws,
# ~/.ssh, ~/.netrc via $HOME. Everything else (API keys, cloud creds, tokens) is dropped.
RERUN_ENV_KEYS = ("LANG", "LC_ALL", "LC_CTYPE", "TERM", "TZ")


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip()


def iter_evidence_containers(data: dict):
    """Yield every object that may carry an evidence[] list (blockers/dissent/concerns + top level)."""
    for key in EVIDENCE_CONTAINERS:
        items = data.get(key) or []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    yield item
    yield data


def resolve_file(source_root, rel: str):
    """Return the path to the cited file, or None if it can't be SAFELY resolved.

    --source may be a single file (single-file review) or a directory root. We refuse
    to resolve an absolute path or one that escapes the root with '..' (a hallucinated
    citation must not read arbitrary files off disk and earn a green stamp), and a
    single-file source matches only a bare-filename citation OF THAT FILE (a different
    directory that merely shares the basename must not resolve to it).
    """
    if source_root is None or not rel:
        return None
    rel = rel.replace("\\", "/")
    if os.path.isabs(rel) or any(part == ".." for part in rel.split("/")):
        return None
    if os.path.isfile(source_root):
        return source_root if rel == os.path.basename(source_root) else None
    candidate = os.path.join(source_root, rel)
    return candidate if os.path.isfile(candidate) else None


def _read_lines(path: str):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read().splitlines()


def resolve_code(ev: dict, source_root) -> str:
    target = resolve_file(source_root, ev.get("path", ""))
    if target is None:
        return "unverified"  # no --source, or the file isn't in the tree we were handed
    try:
        lines = _read_lines(target)
    except OSError:
        return "unverified"
    if "line" in ev:
        line = ev["line"]
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            return "unverified"  # malformed line locator - can't resolve, don't crash
        return "verified" if line <= len(lines) else "refuted"
    symbol = ev.get("symbol", "")
    if symbol and re.search(r"\b" + re.escape(symbol) + r"\b", "\n".join(lines)):
        return "verified"
    return "refuted"


def resolve_source(ev: dict, packet_text) -> str:
    if packet_text is None:
        return "unverified"  # no captured packet to check against; we never live-fetch
    quote = _norm(ev.get("quote", ""))
    if not quote:
        return "unverified"
    return "verified" if quote in _norm(packet_text) else "refuted"


def load_packet_text(packet, run_dir):
    """Concatenate the captured-packet text. The packet is what was EGRESSED - the
    `prompts/*.prompt` blobs under a run dir - never a re-fetch of any cited URL."""
    paths = []
    if run_dir:
        prompts = os.path.join(run_dir, "prompts")
        if os.path.isdir(prompts):
            paths += sorted(glob.glob(os.path.join(prompts, "*.prompt")))
        elif os.path.isdir(run_dir):
            paths += sorted(glob.glob(os.path.join(run_dir, "*.prompt")))
    if packet:
        if os.path.isdir(packet):
            for pattern in ("*.prompt", "*.md", "*.txt"):
                paths += sorted(glob.glob(os.path.join(packet, pattern)))
        elif os.path.isfile(packet):
            paths.append(packet)
        else:
            die(f"--packet: {packet} not found")
    seen, uniq = set(), []  # --packet and --run can name the same prompts dir
    for path in paths:
        key = os.path.abspath(path)
        if key not in seen:
            seen.add(key)
            uniq.append(path)
    paths = uniq
    if not paths:
        return None
    chunks = []
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                chunks.append(handle.read())
        except OSError:
            pass
    return "\n".join(chunks) if chunks else None


def command_allowed(command, rerun):
    """Decide whether a `command` citation may be re-executed, and how.

    Returns (argv, None) when it may run, or (None, reason) when it may not. The
    checks, in order — argv[0] is pinned to an explicit program allowlist FIRST so
    the regex (a later, optional refinement) can never choose the executable:
      1. parseable by shlex (no shell is ever involved);
      2. argv[0] is a BARE program name — no `/`, no leading `.`, not absolute
         (kills `./build.sh`, `/bin/sh`, `../x` and other path-based argv[0]);
      3. argv[0] is in `--allow-program` (the load-bearing pin);
      4. if any `--allow-command` patterns were given, the full command string
         `re.fullmatch`es one (fullmatch, not search — `pytest -q` never green-lights
         `pytest -q; rm -rf ~`; a malformed pattern is skipped, never crashes).
    """
    cmd = (command or "").strip()
    if not cmd:
        return None, "empty command"
    try:
        argv = shlex.split(cmd)
    except ValueError as exc:
        return None, f"unparseable command ({exc})"
    if not argv:
        return None, "empty command"
    prog = argv[0]
    if os.sep in prog or (os.altsep and os.altsep in prog) or prog.startswith(".") or os.path.isabs(prog):
        return None, (f"argv[0] {prog!r} must be a bare program name, not a path "
                      "(path-based argv[0] is refused — it could run a planted binary)")
    if prog not in rerun["programs"]:
        return None, (f"program {prog!r} is not in the --allow-program allowlist "
                      f"({', '.join(sorted(rerun['programs'])) or 'empty'})")
    patterns = rerun.get("patterns") or []
    if patterns:
        matched = False
        for pat in patterns:
            try:
                if re.fullmatch(pat, cmd):
                    matched = True
                    break
            except re.error:
                continue
        if not matched:
            return None, "command does not match any --allow-command pattern"
    return argv, None


def _curated_path() -> str:
    """The inherited PATH with `.`, empty, and relative entries removed, so a
    re-executed bare command can only resolve to an ABSOLUTE, system-trusted dir —
    never `./pytest` from a poisoned cwd. Falls back to os.defpath if nothing's left."""
    entries = [p for p in os.environ.get("PATH", "").split(os.pathsep)
               if p and p not in (".", "") and os.path.isabs(p)]
    return os.pathsep.join(entries) if entries else os.defpath


def _rerun_env(cwd: str, home=None) -> dict:
    """The scrubbed environment for a re-executed command. PATH is curated (absolute
    entries only); HOME points at `home` (a throwaway dir kept SEPARATE from cwd so
    a HOME-writing command — `git config --global`, npm, pip cache — cannot drop
    dotfiles INTO the reviewed source when --rerun-cwd is a real tree); if no `home`
    is given it falls back to cwd (the direct-call default — fine when cwd is itself
    a throwaway). Only locale vars otherwise; no inherited secret is exposed."""
    env = {k: os.environ[k] for k in RERUN_ENV_KEYS if k in os.environ}
    env["PATH"] = _curated_path()
    env["HOME"] = home or cwd
    return env


def run_command(argv, *, cwd, timeout: int, home=None):
    """Run a vetted argv WITHOUT a shell, process-group-killed on timeout. Returns
    (exit, output, error). error is None on a clean run; a non-None error string
    means the command could not be run to a verdict (executable not found on the
    curated PATH, resolves inside cwd, timeout, OSError) — mapped to `unverified`,
    never `refuted`.

    argv[0] is resolved with shutil.which against the curated PATH and rejected if
    it resolves INSIDE cwd (a planted binary). The child runs in its own session so
    a timeout kills the whole process GROUP — a command that forks workers can't
    orphan them past the deadline (mirrors _conductor/spawn.py)."""
    env = _rerun_env(cwd, home)
    resolved = shutil.which(argv[0], path=env["PATH"])
    if not resolved:
        return None, "", f"executable not found on the curated PATH: {argv[0]!r}"
    real_resolved = os.path.realpath(resolved)
    real_cwd = os.path.realpath(cwd)
    # Normalize the prefix so a filesystem-root cwd ("/") doesn't yield "//" (which
    # would never prefix-match and silently disable the guard).
    cwd_prefix = real_cwd if real_cwd.endswith(os.sep) else real_cwd + os.sep
    if real_resolved == real_cwd or real_resolved.startswith(cwd_prefix):
        return None, "", (f"executable {argv[0]!r} resolves inside the working dir "
                          "(possible planted binary) — refusing to run it")
    real_argv = [resolved] + argv[1:]
    try:
        proc = subprocess.Popen(
            real_argv, cwd=cwd, env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True,
        )
    except FileNotFoundError:
        return None, "", f"executable not found: {argv[0]!r}"
    except OSError as exc:
        return None, "", f"could not run ({exc})"
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, out or "", None
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        return None, "", f"timed out after {timeout}s"


def _kill_group(proc) -> None:
    """SIGKILL the timed-out child's whole process group, then reap it (mirrors
    _conductor/spawn.py). Falls back to the bare child if the group is gone."""
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        try:
            proc.kill()
        except ProcessLookupError:
            pass
    try:
        proc.communicate(timeout=5)
    except Exception:
        pass


def _output_excerpt(output: str) -> tuple:
    """(excerpt, truncated). Keep the HEAD and the TAIL when output exceeds the
    limit — a runner's pass/fail summary is usually at the tail, so a head-only
    truncation would drop exactly the line a human wants to see."""
    if len(output) <= RERUN_OUTPUT_LIMIT:
        return output, False
    half = RERUN_OUTPUT_LIMIT // 2
    elided = len(output) - 2 * half
    return output[:half] + f"\n…[{elided} chars elided]…\n" + output[-half:], True


def resolve_command(ev: dict, rerun) -> str:
    """Resolve a `command` citation by RE-EXECUTING it (M3). `rerun` is None (the
    feature is off → `unverified`, the pre-M3 default) or a dict with keys
    `programs` (the argv[0] allowlist), `patterns` (optional full-command regexes),
    `cwd`, `timeout`, and optional `home`.

    Structural match only (design section 11): verified iff exit == expect_exit
    (default 0) AND any verbatim `expect` substring is present in the output. The
    decision is made against the FULL output; the attached `observed` carries the
    exit, a head+tail excerpt, a `truncated` flag, and (when `expect` was given) an
    explicit `expect_found` so the receipt asserts the match even if the matched
    text falls in an elided region. A recorded `status_reason` explains a non-run.

    Refuted vs unverified: a clean run that contradicts an EXPLICIT expectation
    (a pinned `expect_exit` or `expect`) is `refuted` — a positive contradiction. A
    BARE command (neither pinned) that merely exits non-zero is `unverified`, not
    `refuted`: re-execution drops PYTHONPATH/VIRTUAL_ENV etc., so an env-shaped
    failure must NOT be defamed as a fabricated receipt (and a refuted citation
    routes the gate to abstain)."""
    if rerun is None:
        return "unverified"   # re-execution not enabled for this verify pass
    argv, reason = command_allowed(ev.get("command", ""), rerun)
    if argv is None:
        ev["status_reason"] = f"{reason} (re-execution skipped)"
        return "unverified"
    exit_code, output, error = run_command(argv, cwd=rerun["cwd"], timeout=rerun["timeout"],
                                           home=rerun.get("home"))
    if error is not None:
        # Couldn't run to a verdict — an inability, not a contradiction.
        ev["status_reason"] = f"could not re-execute: {error}"
        ev["observed"] = {"error": error}
        return "unverified"
    excerpt, truncated = _output_excerpt(output)
    observed = {"exit": exit_code, "output": excerpt, "truncated": truncated}
    # The KEY's presence signals the author intended an exit check (so a mismatch is
    # a real refutation); a malformed value can't be trusted, so compare against 0.
    has_expect_exit = "expect_exit" in ev
    raw_expect_exit = ev.get("expect_exit")
    expect_exit = raw_expect_exit if (isinstance(raw_expect_exit, int)
                                      and not isinstance(raw_expect_exit, bool)) else 0
    ok_exit = (exit_code == expect_exit)
    expect = ev.get("expect")
    has_expect = isinstance(expect, str) and bool(expect.strip())
    ok_expect = True
    if has_expect:
        ok_expect = _norm(expect) in _norm(output)
        observed["expect_found"] = ok_expect   # the receipt records the match decision
    ev["observed"] = observed
    if ok_exit and ok_expect:
        return "verified"
    if not has_expect_exit and not has_expect:
        # Bare command, non-zero exit, no expectation pinned — ambiguous (an env
        # difference, not a fabricated claim). Unverified, not refuted.
        ev["status_reason"] = (f"exited {exit_code}; no expect/expect_exit pinned — cannot "
                               "distinguish a real failure from an environment difference")
        return "unverified"
    return "refuted"


def stamp(data: dict, source_root, packet_text, rerun=None) -> dict:
    """Resolve every code/source/command citation and write its `status`. Mutates data.

    `rerun` (M3) is None by default — command citations stay `unverified`, exactly
    the pre-M3 behavior — or a dict {allow, cwd, timeout} that enables allowlisted
    command re-execution (see resolve_command)."""
    counts = {"verified": 0, "unverified": 0, "refuted": 0, "skipped": 0}
    for obj in iter_evidence_containers(data):
        for ev in (obj.get("evidence") or []):
            if not isinstance(ev, dict):
                continue
            kind = ev.get("kind")
            if kind == "code":
                status = resolve_code(ev, source_root)
            elif kind == "source":
                status = resolve_source(ev, packet_text)
            elif kind == "command":
                status = resolve_command(ev, rerun)
            else:  # judgment / unknown: no external referent to resolve
                counts["skipped"] += 1
                continue
            ev["status"] = status
            counts[status] += 1
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Resolve and stamp a verdict.json's typed evidence.")
    parser.add_argument("path", help="path to verdict.json")
    parser.add_argument("--source", help="source tree (dir) or file for `code` path:line / symbol resolution")
    parser.add_argument("--packet", help="captured packet (file or dir) for `source` quote resolution")
    parser.add_argument("--run", dest="run_dir", help="a run dir; derives --packet from its prompts/")
    parser.add_argument("-o", "--out", help="write stamped JSON here (default: in place)")
    parser.add_argument("--check", action="store_true", help="report only; write nothing")
    parser.add_argument(
        "--allow-program", dest="allow_program", action="append", default=[], metavar="NAME",
        help="ENABLE command-evidence re-execution for commands whose argv[0] is exactly this bare "
             "program name (repeatable). This is the load-bearing control: argv[0] is pinned to a "
             "program you name, never a path and never chosen by a regex. OMITTED => command "
             "citations stay unverified (re-execution is opt-in). Allowlist only programs you trust "
             "to be read-only over public material — a re-run's output is persisted to verdict.json.")
    parser.add_argument(
        "--allow-command", dest="allow_command", action="append", default=[], metavar="REGEX",
        help="OPTIONAL extra constraint: also require the full command to re.fullmatch this regex "
             "(repeatable) — for pinning ARGS, not the program. Patterns are LIVE regexes (`.` is a "
             "wildcard). Refines the --allow-program allowlist; cannot enable re-execution on its own.")
    parser.add_argument(
        "--rerun-timeout", dest="rerun_timeout", type=int, default=DEFAULT_RERUN_TIMEOUT,
        metavar="SECONDS", help=f"hard timeout per re-executed command (default {DEFAULT_RERUN_TIMEOUT}s)")
    parser.add_argument(
        "--rerun-cwd", dest="rerun_cwd", metavar="DIR",
        help="working dir for re-executed commands (default: a fresh empty throwaway dir, so "
             "commands cannot read attacker files from cwd or execute a planted conftest/Makefile). "
             "Point it at a real tree (e.g. ./src) only if a command needs to inspect it.")
    args = parser.parse_args(argv)

    try:
        with open(args.path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        die(f"{args.path}: not found")
    except json.JSONDecodeError as exc:
        die(f"{args.path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        die(f"{args.path}: top level must be a JSON object")

    packet_text = load_packet_text(args.packet, args.run_dir)

    # M3: assemble the re-execution config only when the user opted in with at least
    # one --allow-program. The PROGRAM allowlist (not the regex) is the enabler; a
    # bare --allow-command does NOT run anything. cwd defaults to a fresh empty
    # throwaway dir (no attacker files in cwd, no planted conftest/Makefile, nothing
    # writes into the reviewed source); --rerun-cwd opts into a real tree.
    rerun = None
    throwaways = []
    if args.allow_program:
        if args.rerun_timeout < 1:
            die("--rerun-timeout must be >= 1 second")
        import tempfile
        cwd = args.rerun_cwd
        if cwd:
            if not os.path.isdir(cwd):
                die(f"--rerun-cwd {cwd!r} is not a directory")
            real = os.path.realpath(cwd)
            if os.path.dirname(real) == real:
                die(f"--rerun-cwd {cwd!r} is a filesystem root; refusing (it discards isolation)")
        else:
            cwd = tempfile.mkdtemp(prefix="advisory-board-rerun-")
            throwaways.append(cwd)
        # HOME is ALWAYS a separate throwaway, never cwd — so a HOME-writing command
        # can't drop dotfiles into a real --rerun-cwd tree (the reviewed source).
        home = tempfile.mkdtemp(prefix="advisory-board-rerun-home-")
        throwaways.append(home)
        rerun = {
            "programs": set(args.allow_program),
            "patterns": list(args.allow_command),
            "cwd": cwd,
            "home": home,
            "timeout": args.rerun_timeout,
        }
    elif args.allow_command:
        print("note: --allow-command was given but re-execution stayed OFF — the program allowlist "
              "is the enabler. Add --allow-program NAME to re-run commands invoking NAME.",
              file=sys.stderr)

    try:
        counts = stamp(data, args.source, packet_text, rerun)
    finally:
        import shutil as _shutil
        for tmp in throwaways:
            _shutil.rmtree(tmp, ignore_errors=True)

    total = sum(counts.values()) - counts["skipped"]
    print(
        f"resolved {total} citation(s): "
        f"{counts['verified']} verified, {counts['unverified']} unverified, "
        f"{counts['refuted']} refuted"
        + (f" ({counts['skipped']} judgment/skipped)" if counts["skipped"] else "")
    )
    if not args.source and any(
        ev.get("kind") == "code"
        for obj in iter_evidence_containers(data)
        for ev in (obj.get("evidence") or [])
        if isinstance(ev, dict)
    ):
        print("note: no --source given - `code` citations stamped unverified (could not resolve).",
              file=sys.stderr)
    if packet_text is None and any(
        ev.get("kind") == "source"
        for obj in iter_evidence_containers(data)
        for ev in (obj.get("evidence") or [])
        if isinstance(ev, dict)
    ):
        print("note: no --packet/--run given - `source` quotes stamped unverified (no captured packet).",
              file=sys.stderr)
    if rerun is None and any(
        ev.get("kind") == "command"
        for obj in iter_evidence_containers(data)
        for ev in (obj.get("evidence") or [])
        if isinstance(ev, dict)
    ):
        print("note: command citations stayed unverified - re-execution is opt-in; pass "
              "--allow-program NAME to re-run commands invoking a program you trust.",
              file=sys.stderr)
    if counts["refuted"]:
        print(f"WARNING: {counts['refuted']} citation(s) REFUTED - a cited line/quote was not "
              "found in the material, or a re-executed command contradicted its expectation. "
              "Inspect before trusting the verdict.", file=sys.stderr)

    if args.check:
        print("(--check: no file written)")
        return 0

    out_path = args.out or args.path
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
import hashlib
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

# Grounded citation snippets (v1.13 P3, #12). When a `code` citation RESOLVES
# against the live --source tree, capture the cited lines so the handoff is self-
# contained (grounded runs keep NO repo bytes — only repo-scope-manifest.json —
# so this is the ONLY moment the lines are on disk). A line citation captures the
# cited line ±SNIPPET_CONTEXT_LINES; a symbol citation captures the first
# SNIPPET_SYMBOL_LINES of the resolved region. Total text is capped at
# SNIPPET_CHAR_LIMIT chars (never embed an unbounded slice of a file).
#   CONTENT capture is HARD-GATED (Blocker 1): before any bytes are read for a
#   snippet, _capture_path_ok refuses a symlinked candidate/intermediate dir and
#   requires realpath-containment inside the source root — a snippet egresses into
#   verdict.json/the handoff, so an in-tree symlink pointing outside the root must
#   not exfiltrate those bytes. STATUS resolution (verified/unverified/refuted) is
#   UNCHANGED from pre-P3 (resolve_file's textual containment + isfile, which
#   follows symlinks): a status badge egresses no file content, and the human
#   supplied --source. Only the CONTENT gate is new.
SNIPPET_CONTEXT_LINES = 2           # ± context lines around a {path, line} citation
SNIPPET_SYMBOL_LINES = 8            # first N lines of a {path, symbol} region
SNIPPET_CHAR_LIMIT = 4000           # hard cap on a captured snippet's text (chars)
# Sentinel: the run dir HAS a repo-scope-manifest.json but it is unusable (malformed,
# unreadable, symlinked, or shaped wrong). A grounded run whose whitelist can't be
# trusted must capture NO snippets at all (fail closed) — distinct from None (no
# manifest file → ungrounded → capture allowed under Blocker 1's hardened read).
MANIFEST_UNUSABLE = object()
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


# One stderr note per run when a symlinked citation is refused CONTENT capture —
# not one per citation. Reset at the top of stamp() so a re-verify starts fresh.
_SNIPPET_SYMLINK_NOTED = False


def _note_snippet_symlink_refused() -> None:
    """Emit the capture-refusal note at most ONCE per stamp() pass (a run may cite
    many files under the same offending symlinked dir; one note is enough)."""
    global _SNIPPET_SYMLINK_NOTED
    if not _SNIPPET_SYMLINK_NOTED:
        _SNIPPET_SYMLINK_NOTED = True
        print("note: a code citation resolved through a symlink or outside the source "
              "root — snippet CONTENT capture refused for it (status is unaffected).",
              file=sys.stderr)


def _capture_path_ok(source_root, target: str, rel: str) -> bool:
    """The hard gate at the CONTENT-capture boundary (v1.13 P3 hardening). STATUS
    resolution keeps its pre-P3 behavior (resolve_file's textual containment +
    isfile, which follows symlinks — the human supplied --source, and a status
    badge egresses no bytes). But a SNIPPET persists file CONTENT into verdict.json
    / the handoff, so an in-tree symlink pointing outside the source root (e.g.
    node_modules/.bin → …, a dotfile link, ~/.ssh/…) could exfiltrate those bytes.
    Before capturing, require BOTH:
      (a) no symlink on the path — neither the candidate itself nor any intermediate
          component (relative to source_root) is os.path.islink; and
      (b) realpath containment — os.path.realpath(target) is INSIDE
          os.path.realpath(source_root) (or IS it, for a single-file --source).
    Single-file --source: the file itself must not be a symlink; containment
    degenerates to realpath(target) == realpath(source_root).

    Refusal returns False (no snippet); the caller emits one per-run note. A refused
    CONTENT capture never changes the citation's status."""
    if source_root is None:
        return False
    # (a) Single-file --source: the file itself must not be a symlink; there are no
    #     intermediate components to walk relative to a file root.
    if os.path.isfile(source_root):
        if os.path.islink(target):
            return False
        real_root = os.path.realpath(source_root)
        return os.path.realpath(target) == real_root
    # (a) Directory --source: refuse a symlink at the candidate OR at any component
    #     between source_root and it (a symlinked intermediate dir escapes too).
    if os.path.islink(target):
        return False
    walk = source_root
    for part in rel.replace("\\", "/").split("/"):
        if not part or part == ".":
            continue
        walk = os.path.join(walk, part)
        if os.path.islink(walk):
            return False
    # (b) realpath containment: the resolved candidate must sit inside the resolved
    #     root (commonpath over the realpaths; a mismatched drive/root raises).
    real_root = os.path.realpath(source_root)
    real_target = os.path.realpath(target)
    try:
        return os.path.commonpath([real_root, real_target]) == real_root
    except ValueError:
        return False


def resolve_code(ev: dict, source_root, manifest=None) -> str:
    """Stamp a `code` citation, and — when it VERIFIES and the capture gates pass —
    capture the cited lines onto `ev['snippet']` (v1.13 P3). Capture is subject to
    Blocker 1's symlink/containment read gate then the `manifest` gate: None
    (ungrounded --source, capture under the read gate), MANIFEST_UNUSABLE (a broken
    grounded manifest, capture nothing), or the {path: sha256} whitelist (grounded
    run: capture ONLY a listed path whose live sha matches — a changed or unlisted
    file gets its badge but NO snippet, so the handoff never embeds lines the board
    didn't see)."""
    rel = ev.get("path", "")
    target = resolve_file(source_root, rel)
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
        if line > len(lines):
            return "refuted"
        _maybe_capture_snippet(ev, source_root, target, rel, lines, manifest, mode="line", line=line)
        return "verified"
    symbol = ev.get("symbol", "")
    if symbol and re.search(r"\b" + re.escape(symbol) + r"\b", "\n".join(lines)):
        _maybe_capture_snippet(ev, source_root, target, rel, lines, manifest, mode="symbol", symbol=symbol)
        return "verified"
    return "refuted"


def _manifest_key(rel: str) -> str:
    """Normalize a citation path to the SAME form build_scope_manifest records its
    keys in — `os.path.relpath` output (see grounding.build_scope_manifest), which
    is already normpath'd (no `./` prefix, collapsed `a/./b`). So `./f.py`, `f.py`,
    and `a/../f.py` all key to `f.py` and hit the manifest entry `f.py`. Without
    this a citation spelled `./f.py` resolves to the same file but MISSES the
    manifest lookup — a listed, possibly-changed file would then be misread as
    unlisted and (under the whitelist-only gate) silently DROPPED. os.path.normpath
    collapses the spelling; posix separators match the manifest keys' forward-slash
    form (grounding stores relpaths with `\\`→`/`)."""
    return os.path.normpath(rel).replace("\\", "/")


# One stderr warning per run when an UNUSABLE manifest disables capture (Blocker 2).
_MANIFEST_UNUSABLE_NOTED = False


def _note_manifest_unusable() -> None:
    """Emit the unusable-manifest warning at most ONCE per stamp() pass."""
    global _MANIFEST_UNUSABLE_NOTED
    if not _MANIFEST_UNUSABLE_NOTED:
        _MANIFEST_UNUSABLE_NOTED = True
        print("warning: manifest present but unusable — snippet capture disabled for "
              "this run.", file=sys.stderr)


def _snippet_capture_ok(target: str, rel: str, manifest) -> bool:
    """The manifest gate for a snippet (Blocker 2 — grounded runs are WHITELIST-ONLY).
    Three states of `manifest`:
      * None — no manifest file (an UNGROUNDED verify: the human supplied --source,
        so capture is allowed here and only the Blocker-1 read gate applies). True.
      * MANIFEST_UNUSABLE — a manifest file EXISTS but is malformed/unreadable/
        symlinked/mis-shaped. A grounded run whose whitelist can't be trusted fails
        CLOSED: capture NOTHING + one per-run warning. False.
      * a {path: sha256} dict — a GROUNDED run. Capture ONLY when the cited path is
        LISTED and the live file's sha256 matches the recorded bytes. An UNLISTED
        path → no snippet (whitelist-only; the flip from the old opt-out gate); a
        listed-but-changed file → no snippet.

    The citation path is normalized to the manifest's own key form BEFORE lookup
    (see _manifest_key) so a spelling like `./f.py` cannot dodge the gate by missing
    an exact-string key match."""
    if manifest is None:
        return True
    if manifest is MANIFEST_UNUSABLE:
        _note_manifest_unusable()
        return False
    want = manifest.get(_manifest_key(rel))
    if want is None:
        return False   # unlisted in a grounded run's whitelist — no snippet
    try:
        with open(target, "rb") as handle:
            live = hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return False
    return live == want


def _maybe_capture_snippet(ev: dict, source_root, target: str, rel: str, lines, manifest,
                           *, mode: str, line=None, symbol=None) -> None:
    """Attach `ev['snippet'] = {from, to, text}` for a resolved code citation,
    subject to the symlink/containment gate (Blocker 1) THEN the manifest gate. A `line`
    citation captures the cited line ± SNIPPET_CONTEXT_LINES (clamped at the file
    edges); a `symbol` citation captures the first SNIPPET_SYMBOL_LINES of the
    region at the symbol's first occurrence. `from`/`to` are 1-based inclusive line
    numbers; `text` is the verbatim lines joined by LF, hard-capped at
    SNIPPET_CHAR_LIMIT chars (a cap hit is marked with a trailing '…[truncated]' so
    the receipt is honest)."""
    # Blocker 1: refuse CONTENT capture through a symlink or outside the source root
    # (status already resolved above and is unaffected). One per-run note on refusal.
    if not _capture_path_ok(source_root, target, rel):
        _note_snippet_symlink_refused()
        return
    if not _snippet_capture_ok(target, rel, manifest):
        return
    n = len(lines)
    if mode == "line":
        first = max(1, line - SNIPPET_CONTEXT_LINES)
        last = min(n, line + SNIPPET_CONTEXT_LINES)
    else:  # symbol — window from the symbol's first occurrence
        hit = 1
        pat = re.compile(r"\b" + re.escape(symbol) + r"\b")
        for i, text in enumerate(lines, 1):
            if pat.search(text):
                hit = i
                break
        first = hit
        last = min(n, hit + SNIPPET_SYMBOL_LINES - 1)
    if first > last:   # empty file / degenerate window — capture nothing
        return
    body = "\n".join(lines[first - 1:last])
    if len(body) > SNIPPET_CHAR_LIMIT:
        body = body[:SNIPPET_CHAR_LIMIT].rstrip() + "\n…[truncated]"
    ev["snippet"] = {"from": first, "to": last, "text": body}


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


def load_scope_manifest(run_dir):
    """The snippet-capture whitelist for a run (Blocker 2). Returns one of three:
      * None — the run dir has NO repo-scope-manifest.json (an UNGROUNDED verify):
        capture is allowed, gated only by Blocker 1's hardened read.
      * MANIFEST_UNUSABLE — a manifest file is PRESENT but unusable (symlinked,
        unreadable, invalid JSON, or mis-shaped): a grounded run whose whitelist
        can't be trusted must capture NOTHING (fail closed + one warning).
      * a {path: sha256} dict — a GROUNDED run: capture ONLY for listed paths whose
        live sha matches (whitelist-only; see _snippet_capture_ok).

    Presence is decided on lexists (a symlink AT the path counts as present-but-
    refused — it could point the gate at arbitrary bytes, so it is UNUSABLE, not
    absent). Presence implies never-None: an empty `files` list, any malformed
    entry, or two entries normalizing to the same key with different shas all
    poison the WHOLE manifest to MANIFEST_UNUSABLE — the gate fails closed rather
    than silently pruning its own whitelist."""
    if not run_dir:
        return None
    path = os.path.join(run_dir, "repo-scope-manifest.json")
    if not os.path.lexists(path):
        return None                      # no manifest file → ungrounded
    if os.path.islink(path) or not os.path.isfile(path):
        return MANIFEST_UNUSABLE         # present but a symlink/non-file → fail closed
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return MANIFEST_UNUSABLE         # present but unreadable/invalid JSON
    files = data.get("files") if isinstance(data, dict) else None
    if not isinstance(files, list):
        return MANIFEST_UNUSABLE         # present but mis-shaped
    out = {}
    for entry in files:
        # A single malformed entry poisons the whole manifest: a whitelist that
        # silently prunes its own rows is a fail-open (a present manifest must
        # NEVER degrade back to the ungrounded None path).
        if not (isinstance(entry, dict) and isinstance(entry.get("path"), str)
                and entry["path"].strip()
                and isinstance(entry.get("sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])):
            return MANIFEST_UNUSABLE
        # Normalize keys the SAME way _snippet_capture_ok normalizes a citation
        # before lookup (normpath + posix), so a citation and its manifest key
        # match regardless of `./`-spelling on either side.
        key = _manifest_key(entry["path"])
        if key in out and out[key] != entry["sha256"]:
            return MANIFEST_UNUSABLE     # ambiguous duplicate → fail closed
        out[key] = entry["sha256"]
    return out if out else MANIFEST_UNUSABLE


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


def stamp(data: dict, source_root, packet_text, rerun=None, manifest=None) -> dict:
    """Resolve every code/source/command citation and write its `status`. Mutates data.

    `rerun` (M3) is None by default — command citations stay `unverified`, exactly
    the pre-M3 behavior — or a dict {allow, cwd, timeout} that enables allowlisted
    command re-execution (see resolve_command).

    `manifest` (v1.13 P3, Blocker 2) is None (ungrounded verify — capture allowed,
    gated only by Blocker 1's read), MANIFEST_UNUSABLE (a present-but-broken
    manifest — capture nothing + one warning), or the repo-scope-manifest's
    {path: sha256} whitelist (grounded run — a `code` citation captures a snippet
    ONLY when the cited path is listed AND the live file's sha matches). Returns
    counts incl. `snippets`, the number of code citations that also captured one."""
    global _SNIPPET_SYMLINK_NOTED, _MANIFEST_UNUSABLE_NOTED
    _SNIPPET_SYMLINK_NOTED = False    # one per-run capture-refusal note (Blocker 1)
    _MANIFEST_UNUSABLE_NOTED = False  # one per-run unusable-manifest warning (Blocker 2)
    counts = {"verified": 0, "unverified": 0, "refuted": 0, "skipped": 0, "snippets": 0}
    for obj in iter_evidence_containers(data):
        for ev in (obj.get("evidence") or []):
            if not isinstance(ev, dict):
                continue
            kind = ev.get("kind")
            if kind == "code":
                # A re-verify must never carry a STALE snippet from a prior pass —
                # drop it, then resolve_code re-captures (or not, per the gate).
                ev.pop("snippet", None)
                status = resolve_code(ev, source_root, manifest)
                if "snippet" in ev:
                    counts["snippets"] += 1
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
    # The snippet-capture whitelist for grounded runs (v1.13 P3, Blocker 2): the
    # run's repo-scope-manifest.json when a --run dir carries one → capture is
    # whitelist-only. MANIFEST_UNUSABLE if it's present but broken → capture nothing.
    # None when the run dir has no manifest (ungrounded verify) → capture under the
    # Blocker-1 read gate only.
    manifest = load_scope_manifest(args.run_dir)

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
        counts = stamp(data, args.source, packet_text, rerun, manifest)
    finally:
        import shutil as _shutil
        for tmp in throwaways:
            _shutil.rmtree(tmp, ignore_errors=True)

    # `snippets` is a side counter (captured snippets), not a resolution status —
    # exclude it (with `skipped`) from the resolved-citation total.
    total = sum(counts.values()) - counts["skipped"] - counts["snippets"]
    print(
        f"resolved {total} citation(s): "
        f"{counts['verified']} verified, {counts['unverified']} unverified, "
        f"{counts['refuted']} refuted"
        + (f" ({counts['skipped']} judgment/skipped)" if counts["skipped"] else "")
    )
    if counts["snippets"]:
        gated = (" (sha-gated to the manifest bytes)"
                 if isinstance(manifest, dict) else "")
        print(f"captured {counts['snippets']} code snippet(s) into the verdict{gated} — "
              "the handoff is self-contained.")
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

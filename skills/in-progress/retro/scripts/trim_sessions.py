#!/usr/bin/env python3
"""Find a repo's recent agent session logs and trim each one to what a retro reads.

Where the logs come from:

  Claude Code  <config dir>/projects/<folder>/<session>.jsonl. The config dirs are
               $CLAUDE_CONFIG_DIR (else ~/.claude) plus each --claude-dir.
               A session's subagents log to <folder>/<session>/subagents/*.jsonl.
  Codex        <codex home>/sessions/**/rollout-*.jsonl. The homes are
               $CODEX_HOME (else ~/.codex) plus each --codex-home.

A session belongs to the repo when the working directory it recorded is the repo
root, one of the repo's git worktrees, or anywhere beneath them. A subagent belongs
to its parent session and folds into it: its trimmed log follows the parent's in the
same file, and its raw size and roughness add to the parent's.

What a trimmed log keeps, in log order, each line tagged L<n> with its line number
in the raw log: the human's messages (in a subagent's log, PROMPT lines from its
parent agent), tool errors, interruptions, and compactions. A closing list names
every command or tool call run more than once and how many of those runs failed.
Everything else is dropped. Common secret shapes are replaced with <REDACTED> before
anything is written; no pattern list catches every secret.

Which sessions: --session (an id, an id prefix, or a log path; repeatable) names
them outright. Otherwise every repo session modified in the last --days days is
scored for roughness, errors + 2 x interruptions + 2 x compactions + retries (a
failed command or call that was run again), and the roughest --limit are kept,
newest first on a tie.

Output: one trimmed Markdown file per session in --out (default: a new private
temp folder), named by tool, start date, and full session id, and a table on
stdout with each session's size before and after trimming and its trimmed size in
estimated tokens (characters / 4), so a cost estimate rests on real numbers.

Standard library only. Exit 0 on success; 1 when no session matched.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REDACTED = "<REDACTED>"
HUMAN_LIMIT = 2000
ERROR_LIMIT = 600
CALL_LIMIT = 200

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----"
               r"(?:.*?-----END [A-Z ]*PRIVATE KEY(?: BLOCK)?-----|.*)", re.S),
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\b[rsp]k_(?:live|test)_[A-Za-z0-9]{10,}"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}"),
    re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bnpm_[A-Za-z0-9]{36}"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bhf_[A-Za-z0-9]{30,}"),
    re.compile(r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43,}"),
    re.compile(r"\bya29\.[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bxapp-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bwhsec_[A-Za-z0-9]{20,}"),
    re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{20,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
]
# The value after a secret-sounding name (API_KEY=..., "token": "..."). The name's
# length is bounded so a long run of word characters cannot make the scan quadratic.
KEYED_SECRET = re.compile(
    r"(?i)(\b(?:[\w.-]{0,40}?(?:secret|token|passw(?:or)?d|api[_-]?key|access[_-]?key|private[_-]?key|app[_-]?key"
    r"|credential)[\w.-]{0,40}|[\w.-]{0,40}_(?:pass|pwd))[\"']?\s*[:=]\s*)"
    r"(\"[^\"\n]{1,200}\"|'[^'\n]{1,200}'|[^\s,;\"']{6,})"
)
# A secret passed as a command-line value: --password <pw>, mysql's -p<pw>, curl's -u user:pw.
FLAG_PASSWORD = re.compile(r"(?i)((?<!\S)--?[\w-]{0,30}passw(?:or)?d\s+)(\"[^\"\n]*\"|'[^'\n]*'|[^\s\"'-]\S*)")
# A secret passed to a --token, --secret, or --api-key style flag. The flag name must end at that
# word (so --max-tokens is not one), and an unquoted value needs 8+ characters with a digit in
# them, so prose after the flag ("--api-key flag is documented") is left alone.
FLAG_SECRET = re.compile(
    r"(?i)((?<!\S)--[\w-]{0,30}(?:token|secret|api[_-]?key|access[_-]?key|private[_-]?key)[ \t]+)"
    r"(\"[^\"\n]*\"|'[^'\n]*'|(?=\S*\d)[^\s\"'-]\S{7,})"
)
MYSQL_PASSWORD = re.compile(r"(\b(?:mysql|mariadb)[\w-]*\b[^\n;|&]{0,200}?\s-p)(\"[^\"\n]*\"|'[^'\n]*'|[^\s\"']+)")
USER_PASSWORD = re.compile(r"((?<!\S)(?:-u|--user)[\s=]*[\"']?(?!\d+:)[^\s:\"'/]+:)(?!//)([^\s\"'@]+)")
BEARER = re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]{8,}")
BASIC_AUTH = re.compile(r"(?i)(\bauthorization[\"']?\s*[:=]\s*[\"']?basic\s+)[A-Za-z0-9+/=]{4,}")
# Azure storage's connection-string key. (SharedAccessKey= is already caught by KEYED_SECRET.)
ACCOUNT_KEY = re.compile(r"(?i)(\bAccountKey=)[A-Za-z0-9+/]{20,}={0,2}")
# A URL's password runs to the last @ before the host, so a password holding @ is covered whole.
# The user may be empty (redis://:password@host).
URL_PASSWORD = re.compile(r"(\b[a-z][a-z0-9+.-]*://[^\s:/@\"'<>]*:)[^\s/\"'<>]+(@)")

SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
COMMAND_NAME = re.compile(r"<command-name>(.*?)</command-name>", re.S)
COMMAND_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
BASH_INPUT = re.compile(r"<bash-input>(.*?)</bash-input>", re.S)
CLAUDE_NOT_HUMAN = ("<local-command-", "<bash-stdout", "<bash-stderr", "<task-notification", "<command-message>")
CODEX_INJECTED = ("<environment_context>", "<user_instructions>", "# AGENTS.md instructions")
CODEX_SHELL_TOOLS = {"shell", "exec_command", "local_shell", "container.exec"}
EXIT_CODE_TEXT = re.compile(r"(?:Process exited with code|[Ee]xit code:?)\s*(-?\d+)")


def redact(text: str) -> str:
    """Replace every secret-shaped string with <REDACTED>."""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(REDACTED, text)
    for pattern in (KEYED_SECRET, FLAG_PASSWORD, FLAG_SECRET, MYSQL_PASSWORD, USER_PASSWORD, BEARER, BASIC_AUTH,
                    ACCOUNT_KEY):
        text = pattern.sub(lambda m: m.group(1) + REDACTED, text)
    return URL_PASSWORD.sub(lambda m: m.group(1) + REDACTED + m.group(2), text)


def excerpt(text: str, limit: int) -> str:
    """The redacted head and tail of a text, about `limit` characters in all.

    A huge text is first cut to a wide window so redaction stays fast. That cut lies
    far outside the head and tail kept here, so it never splits a secret that shows.
    """
    text = text.strip()
    total = len(text)
    if total > 20 * limit:
        text = text[:10 * limit] + "\n" + text[-10 * limit:]
    text = redact(text)
    if len(text) <= limit:
        return text
    head = limit * 2 // 3
    return f"{text[:head]} [... {total - limit} chars trimmed ...] {text[head - limit:]}"


def one_line(text: str) -> str:
    return " ".join(text.split())


def block_text(content) -> str:
    """Text of a message or tool-result content: a string or a list of blocks."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind in ("text", "input_text", "output_text"):
            parts.append(str(block.get("text", "")))
        elif kind in ("image", "input_image", "local_image"):
            parts.append("[image]")
    return "\n".join(parts)


def command_text(command) -> str:
    if isinstance(command, list):
        parts = [str(p) for p in command]
        if len(parts) >= 3 and parts[-2] in ("-lc", "-c"):
            return one_line(parts[-1])
        return one_line(" ".join(parts))
    return one_line(str(command or ""))


def describe_call(arguments) -> str:
    """One line naming what a tool call did: its command, else its arguments."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            return one_line(arguments)
    if isinstance(arguments, dict):
        for key in ("command", "cmd"):
            if key in arguments:
                return command_text(arguments[key])
        return json.dumps(arguments, sort_keys=True)
    return command_text(arguments)


def stamp(ts) -> str:
    return f"{ts[:10]} {ts[11:16]}" if isinstance(ts, str) and len(ts) >= 16 else "?"


def clock(ts) -> str:
    return ts[11:16] if isinstance(ts, str) and len(ts) >= 16 else "--:--"


class Session:
    """One session's kept signal, plus the bookkeeping that scores it."""

    def __init__(self, tool: str, path: Path):
        self.tool = tool
        self.path = path
        self.id = path.stem
        # A subagent's log sits in <session>/subagents/; its parent is that session.
        self.parent = path.parent.parent.name if path.parent.name == "subagents" else None
        self.subagents = []  # each a Session, folded into this one
        self.cwd = None
        self.start = None
        self.end = None
        self.events = []  # (line number, timestamp, kind, text)
        self.calls = {}  # call description -> [runs, failures]
        self.compactions = {}  # representation -> [(line number, timestamp, text)]
        self.raw_bytes = path.stat().st_size
        self.mtime = path.stat().st_mtime
        self.trimmed = ""

    def saw_time(self, ts) -> None:
        if isinstance(ts, str) and ts:
            self.start = self.start or ts
            self.end = ts

    def add(self, line: int, ts, kind: str, text: str = "") -> None:
        if kind == "INTERRUPTED" and self.events and self.events[-1][2] == "INTERRUPTED":
            return
        self.events.append((line, ts, kind, text))

    def human(self, line: int, ts, text: str, kind: str = "HUMAN") -> None:
        if text.strip():
            self.add(line, ts, kind, excerpt(text, HUMAN_LIMIT))

    def call(self, name: str, detail: str) -> str:
        key = f"{name}: {detail}" if detail else name
        self.calls.setdefault(key, [0, 0])[0] += 1
        return key

    def failed(self, line: int, ts, key: str, error: str) -> None:
        self.calls.setdefault(key, [1, 0])[1] += 1
        self.add(line, ts, "ERROR", f"{excerpt(key, CALL_LIMIT)} => {excerpt(error, ERROR_LIMIT)}")

    def compaction(self, form: str, line: int, ts, text: str = "") -> None:
        self.compactions.setdefault(form, []).append((line, ts, text))

    def finish(self) -> None:
        """Fold compactions in (the most frequent representation wins) and render."""
        if self.compactions:
            for line, ts, text in max(self.compactions.values(), key=len):
                self.events.append((line, ts, "COMPACTED", text))
        self.events.sort(key=lambda e: e[0])
        self.trimmed = redact(self.render())

    def count(self, kind: str) -> int:
        return sum(1 for e in self.events if e[2] == kind)

    def repeats(self):
        return sorted(((k, v) for k, v in self.calls.items() if v[0] >= 2), key=lambda kv: (-kv[1][0], kv[0]))

    def retries(self) -> int:
        return sum(min(failures, runs - 1) for _, (runs, failures) in self.repeats())

    def score(self) -> int:
        return (self.count("ERROR") + 2 * self.count("INTERRUPTED")
                + 2 * self.count("COMPACTED") + self.retries() + sum(s.score() for s in self.subagents))

    def raw_total(self) -> int:
        return self.raw_bytes + sum(s.raw_bytes for s in self.subagents)

    def file_name(self) -> str:
        """Tool, start date, and the full id, so no two sessions share a file."""
        full_id = f"{self.parent}-{self.id}" if self.parent else self.id
        return f"{self.tool}-{(self.start or '')[:10] or 'undated'}-{full_id}.md"

    def render(self) -> str:
        lines = [
            f"# {self.tool} subagent {self.id} of session {self.parent}" if self.parent
            else f"# {self.tool} session {self.id}",
            f"time (UTC): {stamp(self.start)} to {stamp(self.end)}",
            f"cwd: {self.cwd or '?'}",
            f"raw log: {self.path} ({self.raw_bytes:,} bytes)",
            (f"signal: {self.count('HUMAN')} human messages, {self.count('ERROR')} tool errors, "
             f"{self.count('INTERRUPTED')} interruptions, {self.count('COMPACTED')} compactions, "
             f"{len(self.repeats())} repeated calls"),
            "L<n> is the line number in the raw log.",
            "",
        ]
        for line, ts, kind, text in self.events:
            head = f"L{line} {clock(ts)} {kind}"
            lines.append(f"{head}: {text.replace(chr(10), chr(10) + '    ')}" if text else head)
        repeats = self.repeats()
        if repeats:
            lines += ["", "Repeated calls (runs, failed runs):"]
            lines += [f"- {runs}x, {failures} failed: {excerpt(key, CALL_LIMIT)}"
                      for key, (runs, failures) in repeats]
        for sub in self.subagents:
            lines += ["", sub.trimmed.rstrip("\n")]
        return "\n".join(lines) + "\n"


def read_jsonl(path: Path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for number, raw in enumerate(fh, 1):
            try:
                obj = json.loads(raw)
            except ValueError:
                continue
            if isinstance(obj, dict):
                yield number, obj


def parse_claude(path: Path) -> Session:
    s = Session("claude", path)
    entries = list(read_jsonl(path))
    turns = [o for _, o in entries if o.get("type") in ("user", "assistant")]
    # A subagent's own transcript is all sidechain; in a main log, sidechain turns are not the human.
    sidechain_only = bool(turns) and all(o.get("isSidechain") for o in turns)
    tool_calls = {}
    for line, o in entries:
        ts = o.get("timestamp")
        s.saw_time(ts)
        s.cwd = s.cwd or o.get("cwd")
        if o.get("isSidechain") and not sidechain_only:
            continue
        kind = o.get("type")
        if kind == "system" and o.get("subtype") == "compact_boundary":
            trigger = (o.get("compactMetadata") or {}).get("trigger")
            s.compaction("boundary", line, ts, trigger or "")
            continue
        message = o.get("message") if isinstance(o.get("message"), dict) else {}
        content = message.get("content")
        if kind == "assistant" and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    name = str(block.get("name") or "tool")
                    tool_calls[block.get("id")] = s.call(name, describe_call(block.get("input")))
        if kind != "user":
            continue
        if o.get("isCompactSummary"):
            s.compaction("summary", line, ts)
            continue
        results = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_result"] \
            if isinstance(content, list) else []
        if results:  # A tool-result entry is never the human typing, save an interruption marker.
            for block in results:
                text = block_text(block.get("content"))
                if text.startswith("[Request interrupted"):
                    s.add(line, ts, "INTERRUPTED")
                elif block.get("is_error"):
                    s.failed(line, ts, tool_calls.get(block.get("tool_use_id"), "tool"), text)
            rest = [b for b in content if b not in results]
            if SYSTEM_REMINDER.sub("", block_text(rest)).strip().startswith("[Request interrupted"):
                s.add(line, ts, "INTERRUPTED")
            continue
        origin = o.get("origin") if isinstance(o.get("origin"), dict) else {}
        if o.get("isMeta") or origin.get("kind") not in (None, "human"):
            continue
        text = SYSTEM_REMINDER.sub("", block_text(content)).strip()
        if text.startswith("[Request interrupted"):
            s.add(line, ts, "INTERRUPTED")
            continue
        command = COMMAND_NAME.search(text)
        bash = BASH_INPUT.search(text)
        if command:
            args = COMMAND_ARGS.search(text)
            text = f"{command.group(1).strip()} {args.group(1).strip() if args else ''}"
        elif bash:
            text = f"! {bash.group(1).strip()}"
        elif text.startswith(CLAUDE_NOT_HUMAN):
            continue
        s.human(line, ts, text, "PROMPT" if sidechain_only else "HUMAN")
    s.subagents = [parse_claude(p) for p in sorted((path.parent / path.stem / "subagents").glob("*.jsonl"))]
    s.finish()
    return s


def exit_code_of(output):
    """Exit code from an older Codex shell output: JSON metadata, else the text form."""
    if not isinstance(output, str):
        return None
    try:
        data = json.loads(output)
        if isinstance(data, dict) and isinstance(data.get("metadata"), dict):
            code = data["metadata"].get("exit_code")
            return code if isinstance(code, int) else None
    except ValueError:
        pass
    match = EXIT_CODE_TEXT.search(output)
    return int(match.group(1)) if match else None


def output_text(output) -> str:
    if isinstance(output, str):
        try:
            data = json.loads(output)
            if isinstance(data, dict) and "output" in data:
                return str(data["output"])
        except ValueError:
            pass
        return output
    return block_text(output)


def parse_codex(path: Path) -> Session:
    s = Session("codex", path)
    shell_calls = {}  # call_id -> description
    shell_outputs = []  # (line, ts, call_id, output)
    has_command_items = False
    for line, o in read_jsonl(path):
        ts = o.get("timestamp")
        s.saw_time(ts)
        kind = o.get("type")
        p = o.get("payload") if isinstance(o.get("payload"), dict) else {}
        ptype = p.get("type")
        if kind == "session_meta":
            s.id = str(p.get("id") or s.id)
            s.cwd = p.get("cwd") or s.cwd
        elif kind == "turn_context":
            s.cwd = s.cwd or p.get("cwd")
        elif kind == "compacted":
            s.compaction("compacted", line, ts)
        elif kind == "event_msg":
            if ptype == "user_message":
                text = str(p.get("message") or "")
                if not text.lstrip().startswith(CODEX_INJECTED):
                    s.human(line, ts, text)
            elif ptype == "turn_aborted":
                s.add(line, ts, "INTERRUPTED", str(p.get("reason") or ""))
            elif ptype == "context_compacted":
                s.compaction("event", line, ts)
            elif ptype == "item_completed":
                item = p.get("item") if isinstance(p.get("item"), dict) else {}
                itype = item.get("type")
                if itype == "UserMessage":
                    text = block_text(item.get("content"))
                    if not text.lstrip().startswith(CODEX_INJECTED):
                        s.human(line, ts, text)
                elif itype == "CommandExecution":
                    has_command_items = True
                    key = s.call("shell", command_text(item.get("command")))
                    code = item.get("exit_code")
                    if item.get("status") == "failed" or (isinstance(code, int) and code != 0):
                        detail = str(item.get("stderr") or "").strip() or str(item.get("aggregated_output") or "")
                        s.failed(line, ts, key, f"exit {code}: {detail}")
                elif itype == "McpToolCall":
                    name = f"{item.get('server', 'mcp')}.{item.get('tool', 'tool')}"
                    key = s.call(name, describe_call(item.get("arguments")))
                    result = item.get("result") if isinstance(item.get("result"), dict) else {}
                    if item.get("status") == "failed" or result.get("isError"):
                        s.failed(line, ts, key, block_text(result.get("content")))
                elif itype == "ContextCompaction":
                    s.compaction("item", line, ts)
        elif kind == "response_item":
            if ptype == "function_call" and p.get("name") in CODEX_SHELL_TOOLS:
                shell_calls[p.get("call_id")] = describe_call(p.get("arguments"))
            elif ptype == "function_call_output" and p.get("call_id") in shell_calls:
                shell_outputs.append((line, ts, p.get("call_id"), p.get("output")))
    if not has_command_items:  # Older Codex logs record shell runs only as call and output pairs.
        keys = {cid: s.call("shell", detail) for cid, detail in shell_calls.items()}
        for line, ts, call_id, output in shell_outputs:
            code = exit_code_of(output)
            if code not in (None, 0):
                s.failed(line, ts, keys[call_id], f"exit {code}: {output_text(output)}")
    s.finish()
    return s


def parse(path: Path) -> Session:
    if path.name.startswith("rollout-"):
        return parse_codex(path)
    for _, obj in read_jsonl(path):
        return parse_codex(path) if "payload" in obj else parse_claude(path)
    return parse_claude(path)


def slug(path: str) -> str:
    """Claude Code's project folder name for a working directory."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def repo_roots(repo: str) -> set:
    """The repo's root and every worktree path, each in raw and resolved form."""
    roots = {os.path.abspath(repo)}
    listed = subprocess.run(["git", "-C", repo, "worktree", "list", "--porcelain"],
                            capture_output=True, text=True)
    if listed.returncode == 0:
        roots |= {ln[len("worktree "):] for ln in listed.stdout.splitlines() if ln.startswith("worktree ")}
    top = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode == 0 and top.stdout.strip():
        roots.add(top.stdout.strip())
    return {os.path.normpath(r) for r in roots} | {os.path.realpath(r) for r in roots}


def under(cwd, roots: set) -> bool:
    if not cwd:
        return False
    for candidate in {os.path.normpath(cwd), os.path.realpath(cwd)}:
        for root in roots:
            if candidate == root or candidate.startswith(root.rstrip(os.sep) + os.sep):
                return True
    return False


def first_cwd(path: Path, codex: bool):
    for number, obj in read_jsonl(path):
        if codex:
            payload = obj.get("payload") if isinstance(obj.get("payload"), dict) else {}
            if obj.get("type") in ("session_meta", "turn_context") and payload.get("cwd"):
                return payload["cwd"]
        elif obj.get("cwd"):
            return obj["cwd"]
        if number >= 200:
            return None
    return None


def config_dirs(values, env_var: str, default: str) -> list:
    """The default folder ($env_var, else ~/default) and each flagged one, once each.

    A flag adds a folder rather than replacing the default, so naming an extra
    folder never silently drops the sessions in the default one.
    """
    env = os.environ.get(env_var)
    dirs = [Path(env).expanduser() if env else Path.home() / default] + [Path(v).expanduser() for v in values]
    unique = {}
    for d in dirs:
        unique.setdefault(os.path.realpath(d), d)
    return list(unique.values())


def claude_logs(claude_dirs) -> list:
    out = []
    for base in claude_dirs:
        projects = base / "projects"
        if projects.is_dir():
            out += [(f, False) for d in projects.iterdir() if d.is_dir() for f in d.glob("*.jsonl")]
    return out


def codex_logs(codex_homes) -> list:
    out = []
    for base in codex_homes:
        sessions = base / "sessions"
        if sessions.is_dir():
            out += [(f, True) for f in sessions.rglob("rollout-*.jsonl")]
    return out


def find_recent(roots: set, claude_dirs, codex_homes, days: float, now: float) -> list:
    """Every log modified in the window whose recorded working directory is in the repo."""
    cutoff = now - days * 86400
    prefixes = {slug(r) for r in roots}
    candidates = [(f, c) for f, c in claude_logs(claude_dirs)
                  if any(f.parent.name == p or f.parent.name.startswith(p + "-") for p in prefixes)]
    return [path for path, codex in candidates + codex_logs(codex_homes)
            if path.stat().st_mtime >= cutoff and under(first_cwd(path, codex), roots)]


def find_named(names, claude_dirs, codex_homes) -> list:
    """Resolve each --session value to exactly one log: a path, an id, or an id prefix."""
    found = []
    every_log = None
    for name in names:
        if Path(name).expanduser().is_file():
            found.append(Path(name).expanduser())
            continue
        if every_log is None:
            every_log = [f for f, _ in claude_logs(claude_dirs) + codex_logs(codex_homes)]
        matches = [f for f in every_log
                   if f.stem.startswith(name) or (f.name.startswith("rollout-") and name in f.stem)]
        if len(matches) != 1:
            raise SystemExit(f"--session {name}: {len(matches)} logs match; give a longer id or the log path")
        found.append(matches[0])
    return found


def size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Trim a repo's recent agent session logs to retro signal.")
    parser.add_argument("--repo", default=".", help="the repo whose sessions to read (default: current folder)")
    parser.add_argument("--session", action="append", default=[],
                        help="a session id, id prefix, or log path; repeatable; overrides the sample")
    parser.add_argument("--limit", type=int, default=8, help="sessions in the sample (default 8)")
    parser.add_argument("--days", type=float, default=30, help="how far back the sample looks (default 30)")
    parser.add_argument("--claude-dir", action="append", default=[],
                        help="a Claude Code config folder to read besides the default "
                             "($CLAUDE_CONFIG_DIR or ~/.claude); repeatable")
    parser.add_argument("--codex-home", action="append", default=[],
                        help="a Codex home folder to read besides the default ($CODEX_HOME or ~/.codex); repeatable")
    parser.add_argument("--out", help="folder for the trimmed logs (default: a new private temp folder)")
    args = parser.parse_args(argv)

    claude_dirs = config_dirs(args.claude_dir, "CLAUDE_CONFIG_DIR", ".claude")
    codex_homes = config_dirs(args.codex_home, "CODEX_HOME", ".codex")
    if args.session:
        sessions = [parse(p) for p in find_named(args.session, claude_dirs, codex_homes)]
        heading = f"{len(sessions)} named sessions."
    else:
        found = find_recent(repo_roots(args.repo), claude_dirs, codex_homes, args.days, time.time())
        ranked = sorted((parse(p) for p in found), key=lambda s: (s.score(), s.mtime), reverse=True)
        sessions = ranked[:args.limit]
        heading = f"{len(sessions)} of {len(found)} sessions from the last {args.days:g} days, roughest first."
    if not sessions:
        searched = ", ".join(str(d) for d in claude_dirs + codex_homes)
        print(f"No sessions found for {os.path.abspath(args.repo)} in {searched}.", file=sys.stderr)
        return 1

    if args.out:
        out = Path(args.out).expanduser()
        out.mkdir(mode=0o700, parents=True, exist_ok=True)
    else:
        out = Path(tempfile.mkdtemp(prefix="retro-"))
    rows = []
    for s in sessions:
        target = out / s.file_name()
        data = s.trimmed.encode("utf-8", errors="replace")  # a lone surrogate in a log becomes "?"
        target.write_bytes(data)
        rows.append((s, len(data), target))

    print(heading)
    print("RAW is the log on disk with its subagents' logs, TRIMMED the file a reader gets; "
          "TOKENS is trimmed characters / 4.")
    print(f"{'TOOL':<7}{'STARTED (UTC)':<18}{'SESSION':<10}{'RAW':>10}{'TRIMMED':>10}"
          f"{'TOKENS':>9}{'SCORE':>7}  FILE")
    for s, trimmed_bytes, target in rows:
        print(f"{s.tool:<7}{stamp(s.start):<18}{s.id[:8]:<10}{size(s.raw_total()):>10}"
              f"{size(trimmed_bytes):>10}{len(s.trimmed) // 4:>9,}{s.score():>7}  {target}")
    raw_total = sum(s.raw_total() for s, _, _ in rows)
    trimmed_total = sum(t for _, t, _ in rows)
    tokens_total = sum(len(s.trimmed) // 4 for s, _, _ in rows)
    print(f"{'TOTAL':<35}{size(raw_total):>10}{size(trimmed_total):>10}{tokens_total:>9,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

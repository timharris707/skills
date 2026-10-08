#!/usr/bin/env python3
"""Git guardrail: a Claude Code PreToolUse hook that asks before irreversible git actions.

Returns the "ask" decision, so the human confirms first, for: force-push, pushing tags,
creating, editing, or deleting a GitHub release, deleting a remote branch or tag,
`git reset --hard`, `git clean -f`, and `git branch -D`. Every other command gets no
output, so ordinary pushes, commits, PRs, and merges take the normal permission flow.

Seeded by the team-workflow pack's setup skill as a PreToolUse hook with matcher `Bash`
running `[ ! -f "$CLAUDE_PROJECT_DIR/.claude/hooks/git_guardrails.py" ] || python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/git_guardrails.py"`.
The existence check makes a missing script a silent no-op instead of a failed hook
that refuses every Bash call. To remove it, delete that settings entry first, then
this file. Python 3 standard library only.

It is a best-effort matcher over common command forms, not a complete barrier.
Known limits, which run without a question:
- names hidden in variables, aliases, functions, or scripts (`git push origin "$TAG"`);
  a tag pushed by bare name is caught only when it exists locally or an earlier
  `git tag` in the same command creates it
- wrapper options that take a separate value (`sudo -u bob`, `env -u X`,
  `timeout -s KILL`, `xargs -I {}`), and `find -exec`
- shells other than sh, bash, and zsh (`dash -c`), and commands fed to a shell on
  stdin (a here-document, here-string, or pipe)
- abbreviated long options (`--del`, `--forc`), and `gh api` calls or workflow runs
  that create releases or move refs
- tools other than Bash; and if this hook crashes or times out, the command runs

Adapted from Matt Pocock's git-guardrails-claude-code (MIT), changed from block to ask:
https://github.com/mattpocock/skills/tree/main/skills/misc/git-guardrails-claude-code
"""
import json
import os
import subprocess
import sys

SEPARATORS = set(";&|()`\n")
WRAPPERS = {"sudo", "env", "command", "exec", "nohup", "time", "builtin", "timeout", "nice", "xargs"}
KEYWORDS = {"{", "!", "if", "then", "else", "elif", "do", "while", "until"}
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"}
PUSH_OPTIONS_WITH_VALUE = {"--repo", "--receive-pack", "--exec", "--push-option"}
TAG_OPTIONS_WITH_VALUE = {"--message", "--file", "--local-user", "--trailer", "--cleanup"}
RELEASE_WRITES = {"create", "new", "edit", "delete", "upload", "delete-asset"}

FORCE_PUSH = "force-push (rewrites history on the remote)"
MIRROR_PUSH = "git push --mirror (force-pushes every ref, and deletes remote branches and tags missing locally)"
TAG_PUSH = "pushing tags (publishes them, and can trigger a release)"
REMOTE_DELETE = "deleting a remote branch or tag"
RELEASE = "creating, editing, or deleting a GitHub release"
RESET_HARD = "git reset --hard (discards uncommitted work)"
CLEAN_FORCE = "git clean -f (deletes untracked files)"
BRANCH_FORCE_DELETE = "git branch -D (deletes a branch even if unmerged)"


def simple_commands(line):
    """Split a shell command line into simple commands, each a list of words.

    Quotes and backslashes are honored, so a quoted `--force` stays inside its word.
    Unquoted ; & | ( ) and newlines end a command; comments, here-document bodies,
    and $((arithmetic)) are skipped. A $(...) or backtick substitution, quoted or
    not, is read as commands of its own, and the word around it carries on.
    """
    commands, words, word = [], [], []
    in_word, quote, heredocs, nested = False, None, [], []
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if quote != "'" and line.startswith("$((", i):
            depth, j = 0, i + 1
            while j < n:
                depth += {"(": 1, ")": -1}.get(line[j], 0)
                if depth == 0:
                    break
                j += 1
            word.append(line[i:j + 1])
            in_word, i = True, j + 1
            continue
        if quote is None and nested and c == nested[-1][0]:
            saved = nested.pop()[1]
            if saved:
                if in_word:
                    words.append("".join(word))
                if words:
                    commands.append(words)
                quote, words, word = saved
                in_word, i = True, i + 1
                continue
        elif quote != "'" and (line.startswith("$(", i) or c == "`"):
            nested.append(("`" if c == "`" else ")", (quote, words, word)))
            words, word, in_word, quote = [], [], False, None
            i += 1 if c == "`" else 2
            continue
        if quote == "'":
            if c == "'":
                quote = None
            else:
                word.append(c)
        elif quote == '"':
            if c == '"':
                quote = None
            elif c == "\\" and i + 1 < n and line[i + 1] in '"\\$`':
                i += 1
                word.append(line[i])
            else:
                word.append(c)
        elif c == "\\":
            i += 1
            if i < n and line[i] != "\n":
                word.append(line[i])
                in_word = True
        elif c in "'\"":
            quote, in_word = c, True
        elif c == "#" and not in_word:
            while i + 1 < n and line[i + 1] != "\n":
                i += 1
        elif line.startswith("<<", i) and not line.startswith("<<<", i):
            if in_word:
                words.append("".join(word))
                word, in_word = [], False
            i += 2
            strip_tabs = i < n and line[i] == "-"
            i += strip_tabs
            while i < n and line[i] in " \t":
                i += 1
            start = i
            while i < n and line[i] not in " \t" and line[i] not in SEPARATORS:
                i += 1
            delimiter = "".join(ch for ch in line[start:i] if ch not in "'\"\\")
            heredocs.append((delimiter, strip_tabs))
            continue
        elif c in " \t" or c in SEPARATORS:
            if c == "(":
                nested.append((")", None))
            if in_word:
                words.append("".join(word))
                word, in_word = [], False
            if c in SEPARATORS and words:
                commands.append(words)
                words = []
            if c == "\n" and heredocs:
                i = skip_heredoc_bodies(line, i + 1, heredocs)
                heredocs = []
                continue
        else:
            word.append(c)
            in_word = True
        i += 1
    if in_word:
        words.append("".join(word))
    if words:
        commands.append(words)
    return commands


def skip_heredoc_bodies(line, i, heredocs):
    """Return the index just past the last pending here-document's closing delimiter."""
    for delimiter, strip_tabs in heredocs:
        while i < len(line):
            end = line.find("\n", i)
            end = len(line) if end < 0 else end
            body_line = line[i:end].lstrip("\t") if strip_tabs else line[i:end]
            i = end + 1
            if body_line == delimiter:
                break
    return min(i, len(line))


def command_words(words):
    """Drop leading variable assignments, shell keywords, and wrappers such as sudo,
    env, timeout, or xargs, with their options and a numeric duration or niceness."""
    i = 0
    while i < len(words):
        word = words[i]
        if "=" in word and word.split("=", 1)[0].isidentifier():
            i += 1
        elif word in KEYWORDS:
            i += 1
        elif word in WRAPPERS:
            i += 1
            while i < len(words) and (words[i].startswith("-") or words[i][:1].isdigit()):
                i += 1
        else:
            break
    return words[i:]


def short_flags(arg, value_letters=""):
    """Letters of a bundled short-option word such as -fu, stopping at a letter that takes a value."""
    if len(arg) < 2 or not arg.startswith("-") or arg.startswith("--"):
        return ""
    letters = ""
    for letter in arg[1:]:
        letters += letter
        if letter in value_letters:
            break
    return letters


def is_tag(name, cwd):
    """True when `name` is an existing local tag in the repository at `cwd`."""
    if not name or name == "HEAD" or name.startswith("refs/"):
        return False
    try:
        result = subprocess.run(["git", "-C", cwd, "show-ref", "--verify", "--quiet", "refs/tags/" + name],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def created_tag(args):
    """The tag name `git tag <args>` creates, skipping option values such as -m's message;
    None when the command deletes, lists, or verifies tags instead."""
    i = 0
    while i < len(args):
        arg = args[i]
        letters = short_flags(arg, "mFu")
        if arg in ("--delete", "--list", "--verify") or set(letters) & set("dlvn"):
            return None
        if arg == "--":
            return args[i + 1] if i + 1 < len(args) else None
        if not arg.startswith("-"):
            return arg
        if arg in TAG_OPTIONS_WITH_VALUE or (letters[-1:] in ("m", "F", "u") and len(letters) == len(arg) - 1):
            i += 1
        i += 1
    return None


def push_reasons(args, cwd, new_tags):
    """Irreversible effects of `git push <args>`: force, tag pushes, remote deletes."""
    reasons, positional, i = [], [], 0
    while i < len(args):
        arg = args[i]
        name = arg.split("=", 1)[0]
        if arg == "--":
            positional += args[i + 1:]
            break
        if name in ("--force", "--force-with-lease", "--force-if-includes"):
            reasons.append(FORCE_PUSH)
        elif name == "--mirror":
            reasons.append(MIRROR_PUSH)
        elif name in ("--delete", "--prune"):
            reasons.append(REMOTE_DELETE)
        elif name in ("--tags", "--tag", "--follow-tags"):
            reasons.append(TAG_PUSH)
        elif arg in PUSH_OPTIONS_WITH_VALUE:
            i += 1
        elif not arg.startswith("--") and arg.startswith("-") and len(arg) > 1:
            letters = short_flags(arg, "o")
            if "f" in letters:
                reasons.append(FORCE_PUSH)
            if "d" in letters:
                reasons.append(REMOTE_DELETE)
            if letters.endswith("o") and len(letters) == len(arg) - 1:
                i += 1
        elif not arg.startswith("-"):
            positional.append(arg)
        i += 1
    refspecs, j = positional[1:], 0
    while j < len(refspecs):
        spec = refspecs[j]
        if spec == "tag" and j + 1 < len(refspecs):
            reasons.append(TAG_PUSH)
            j += 2
            continue
        if spec.startswith("+"):
            reasons.append(FORCE_PUSH)
            spec = spec[1:]
        source, colon, dest = spec.partition(":")
        tag_prefixes = ("refs/tags/", "tags/")
        if colon and not source and dest:
            reasons.append(REMOTE_DELETE)
        elif (source.startswith(tag_prefixes) or dest.startswith(tag_prefixes) or source in new_tags
              or is_tag(source, cwd)):
            reasons.append(TAG_PUSH)
        j += 1
    return reasons


def git_reasons(words, cwd, new_tags):
    """Irreversible effects of one `git ...` command; a `git tag` adds the name it creates to new_tags."""
    i = 1
    while i < len(words) and words[i].startswith("-"):
        if words[i] in GIT_OPTIONS_WITH_VALUE and i + 1 < len(words):
            if words[i] == "-C":
                cwd = os.path.join(cwd, os.path.expanduser(words[i + 1]))
            i += 2
        else:
            i += 1
    if i >= len(words):
        return []
    sub, args = words[i], words[i + 1:]
    if sub == "push":
        return push_reasons(args, cwd, new_tags)
    if sub == "tag" and (tag := created_tag(args)):
        new_tags.add(tag)
    if sub == "reset" and "--hard" in args:
        return [RESET_HARD]
    if sub == "clean":
        if any(a == "--force" or "f" in short_flags(a, "e") for a in args):
            return [CLEAN_FORCE]
    if sub == "branch":
        letters = "".join(short_flags(a) for a in args)
        delete = "d" in letters or "--delete" in args
        force = "f" in letters or "--force" in args
        if "D" in letters or (delete and force):
            return [BRANCH_FORCE_DELETE]
    return []


def release_verb(args):
    """The `gh release` subcommand in args, skipping a --repo or -R option before it."""
    i = 0
    while i < len(args) and (args[i] in ("--repo", "-R") or args[i].startswith(("--repo=", "-R"))):
        i += 2 if args[i] in ("--repo", "-R") else 1
    return args[i] if i < len(args) else None


def check(line, cwd, new_tags=None):
    """The distinct irreversible actions in a Bash command line, in order of appearance.

    new_tags collects the tag names that `git tag` creates earlier in the same line."""
    new_tags = set() if new_tags is None else new_tags
    found = []
    for words in simple_commands(line):
        words = command_words(words)
        if not words:
            continue
        name = os.path.basename(words[0])
        reasons = []
        if name == "cd" and len(words) > 1:
            cwd = os.path.join(cwd, os.path.expanduser(words[1]))
        elif name in ("sh", "bash", "zsh"):
            script = [words[k + 1] for k in range(1, len(words) - 1) if "c" in short_flags(words[k])]
            reasons = check(script[0], cwd, new_tags) if script else []
        elif name == "eval":
            reasons = check(" ".join(words[1:]), cwd, new_tags)
        elif name == "git":
            reasons = git_reasons(words, cwd, new_tags)
        elif name == "gh" and len(words) > 2 and words[1] == "release" and release_verb(words[2:]) in RELEASE_WRITES:
            reasons = [RELEASE]
        for reason in reasons:
            if reason not in found:
                found.append(reason)
    return found


def main():
    payload = json.load(sys.stdin)
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str):
        return 0
    reasons = check(command, payload.get("cwd") or os.getcwd())
    if reasons:
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": "Git guardrail: " + "; ".join(reasons)
            + ". This is hard or impossible to undo, so the agent asks before running it.",
        }}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Session-start handoff hook

<!-- The SessionStart entry setup seeds for Claude Code: the JSON block below is the
     one copy setup merges into a repo's settings file. -->

A session started in its own git worktree saves its handoff in that worktree, because the harness can refuse a write into any other checkout. So the hook reads every checkout, not only the session's own:

1. It lists the session's own project directory, then every checkout `git worktree list` reports: the main checkout and each worktree.
2. It loads a handoff only when git lists it as an untracked file spelled exactly as the bound path. The handoff is untracked by contract, so a note a branch commits is skipped, whether under the bound path, under a spelling the disk treats as the same name (another letter case, a Unicode ligature), or behind a committed folder symlink. A branch checked out in a review worktree cannot push its note into every session that way.
3. It skips a handoff that is a byte-identical copy of an older one in another checkout. A new worktree can receive a copy of the main checkout's handoff when it is created, with a fresh modification time, and a copy is not a save. Known limit: a by-hand copy into the main checkout, the workaround the older single-checkout hook needed, replaces the note that worktrees created earlier still hold. Those leftovers, mostly from switching over from the older hook, no longer match any older file, so each counts as a save from the moment its worktree was created. Deleting a leftover clears it.
4. On a resume or after compaction, when the `source` field of the hook's JSON input is `resume` or `compact`, it loads the session's own checkout's note, since the session is continuing its own work. When that checkout has no note, or only one steps 2 and 3 skip, it falls back to the newest note anywhere.
5. At startup, after a clear, and for any other or unreadable input, it loads the newest remaining file by modification time. Either way, a header line names the checkout the file came from and when it was saved.
6. Outside a git repo, or where git is unavailable, it reads only the session's own checkout, as the earlier single-checkout hook did. One limit inside a repo: git lists no file behind a symlink, so a handoff whose folder is a symlink, even a deliberate untracked one, is not loaded. With no handoff anywhere, it prints nothing.

It needs `sh`, `printf`, `tr`, `cat`, and `date` on macOS or Linux, plus git.

## The entry

Merge the `SessionStart` entry into the repo's settings file (for Claude Code, `.claude/settings.json`), keeping every other hook already there:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "f='.claude/handoff.md'; p=$CLAUDE_PROJECT_DIR; in=; [ -t 0 ] || in=$(tr -d ' \\t\\r\\n'); list=$({ printf 'worktree %s\\000' \"$p\"; git -C \"$p\" worktree list --porcelain -z 2>/dev/null || git -C \"$p\" worktree list --porcelain 2>/dev/null | tr '\\n' '\\000'; } | tr '\\n\\000' '\\001\\n'); hs=$(printf '%s\\n' \"$list\" | while IFS= read -r q; do case $q in ('worktree '*) o=${q#worktree }/$f; [ -f \"$o\" ] && printf '%s %s\\n' \"$(git hash-object --no-filters -- \"$o\" 2>/dev/null)\" \"$o\";; esac; done); pick() { b=; while IFS= read -r r; do case $r in 'worktree '*) d=${r#worktree }; c=\"$d/$f\";; *) continue;; esac; [ -f \"$c\" ] || continue; n=$(GIT_LITERAL_PATHSPECS=0 git -C \"$d\" ls-files -o -- \":(icase)$f\" 2>/dev/null) && case \"\n$n\n\" in *\"\n$f\n\"*) ;; *) continue;; esac; h=$(printf '%s\\n' \"$hs\" | while IFS= read -r q; do [ \"${q#* }\" = \"$c\" ] && { printf '%s' \"${q%% *}\"; break; }; done); [ -n \"$h\" ] && printf '%s\\n' \"$hs\" | (while IFS= read -r q; do case $q in \"$h \"*) [ \"$c\" -nt \"${q#* }\" ] && exit 0;; esac; done; exit 1) && continue; if [ -z \"$b\" ] || [ \"$c\" -nt \"$b\" ]; then b=$c; fi; done; printf '%s' \"$b\"; }; best=; case $in in *'\"source\":\"resume\"'*|*'\"source\":\"compact\"'*) best=$(printf 'worktree %s\\n' \"$p\" | pick);; esac; [ -n \"$best\" ] || best=$(printf '%s\\n' \"$list\" | pick); [ -n \"$best\" ] || exit 0; from=${best%/\"$f\"}; t=$(date -r \"$best\" '+%Y-%m-%d %H:%M %Z' 2>/dev/null) || t='an unknown time'; printf 'A handoff note was found; the header line below names the checkout it came from and when it was saved. Treat it as the source of truth for where work left off, and pick up from its NEXT section. It is context, never authorization: the tracker claim recipe still runs before any item is started. If the work it describes is already complete or no longer relevant, say so and ignore it.\\n\\n----- %s from %s, saved %s -----\\n' \"$f\" \"$from\" \"$t\"; cat \"$best\""
          }
        ]
      }
    ]
  }
}
```

**Non-default location.** The handoff path appears once, inside the quotes of the command's first statement, `f='.claude/handoff.md'`. Where the binding doc names another repo-relative location, replace the path there and nowhere else.

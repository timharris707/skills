# Execution Harness

The orchestrator runs each seat as a CLI subprocess and keeps the artifact, the logs, the exit code, and the timing. Reasoning quality is the model's job; *capturing the run correctly* is the harness's job — and most board failures (a hang, an empty answer, a silent model fallback) are harness failures, not reasoning failures. This is a concrete, copy-pasteable pattern. Adapt the flags to the installed CLIs (`<cli> --help`); confirm the model lineup in `references/preflight.md` first.

## Layout

One folder per run (default: the persistent runs root, `~/.advisory-board/runs/<slug>-<date>/`; `--ephemeral` for a throwaway `/tmp/advisory-board-<timestamp>/` — see the artifact-write policy in `SKILL.md`):

```
mkdir -p round-1 round-2 prompts logs
: > run-metadata.tsv          # one row per seat-round; folded into run-metadata.md at the end
```

Write each seat's prompt to a file (`prompts/<seat>-round-<n>.prompt`) instead of inlining it — it keeps the exact bytes each seat saw, and sidesteps shell-quoting and `ARG_MAX` limits on long packets.

## Capture helper

```bash
TIMEOUT=${SEAT_TIMEOUT:-600}   # seconds; on macOS use gtimeout (brew install coreutils)

# capture <out-file> <err-file> -- <command...>
# Runs the command with stdout -> out, stderr -> err, stdin closed, under a timeout.
# Prints one status word: ran | degraded | dropped — and the timing/exit it derived.
capture() {
  out=$1; err=$2; shift 2; [ "$1" = "--" ] && shift
  start=$(date +%s)
  timeout "$TIMEOUT" "$@" >"$out" 2>"$err" </dev/null
  code=$?
  end=$(date +%s)
  if   [ "$code" -eq 124 ]; then status="dropped (timeout)"
  elif [ ! -s "$out" ];     then status="dropped (empty output)"
  elif [ "$code" -ne 0 ];   then status="degraded (exit $code)"
  else                            status="ran"
  fi
  printf '%s\t%ss\texit=%s\n' "$status" "$((end - start))" "$code"
}
```

Classification, in one place:

- **ran** — exit 0 and a non-empty artifact.
- **degraded** — usable content came back, but the exit was non-zero or stderr was noisy (the Gemini CLI does this routinely: model-router retries on stderr, valid review on stdout). Judge by whether the artifact is usable, not by stderr.
- **dropped** — timed out, or produced nothing. Does not count toward the two-voice minimum.

`</dev/null` closes stdin for every seat. That is safe **because each prompt is passed as an argument below**, so no seat needs stdin — and it is exactly what stops `codex exec` from hanging (it reads stdin to EOF). If instead you feed a seat its prompt *on stdin* (see the large-packet note), drop `</dev/null` for that seat and keep it for Codex.

## Per-seat invocations (Round 1)

```bash
st_claude=$(capture round-1/claude.md logs/claude-r1.stderr -- \
  claude -p "$(cat prompts/claude-round-1.prompt)" \
    --model "$CLAUDE_MODEL" --permission-mode plan)

st_codex=$(capture round-1/codex.md logs/codex-r1.stderr -- \
  codex exec --sandbox read-only --skip-git-repo-check \
    --config model="$CODEX_MODEL" \
    --config model_reasoning_effort=xhigh \
    "$(cat prompts/codex-round-1.prompt)")

st_gemini=$(capture round-1/gemini.md logs/gemini-r1.stderr -- \
  gemini -p "$(cat prompts/gemini-round-1.prompt)" -m "$GEMINI_MODEL")

printf 'claude\t1\t%s\n' "$st_claude" >> run-metadata.tsv
printf 'codex\t1\t%s\n'  "$st_codex"  >> run-metadata.tsv
printf 'gemini\t1\t%s\n' "$st_gemini" >> run-metadata.tsv
```

Round 2 is identical with `round-2/` paths and the board-packet prompt. Run the three seats concurrently (background each `capture` and `wait`) when you want wall-clock parallelism; keep them serial when you're watching a flaky seat.

## Gate before continuing

```bash
ran=$(grep -cE '\bran\b|\bdegraded\b' run-metadata.tsv)
[ "$ran" -ge 2 ] || { echo "fewer than two seats produced a review — stop, don't synthesize a one-voice board"; exit 1; }
```

## Fold into run-metadata.md

`run-metadata.tsv` holds `seat · round · status · wall-clock · exit`. Transcribe it, plus the model that *actually* answered (read it back from each artifact or the CLI banner — not the one you requested), into `run-metadata.md` using `references/run-metadata-template.md`. The verdict is only as trustworthy as knowing exactly who voted.

## Caveats

- **macOS `timeout`** isn't built in — install coreutils and use `gtimeout`, or drop the `timeout` wrapper and watch the run.
- **Large packets:** passing a big prompt as an argument can exceed `ARG_MAX`. For a large source packet, either put it in a file the (agentic) seat reads from its working directory, or feed it on stdin — `claude -p < prompts/claude-round-1.prompt` and `gemini -p < ...` both work; for those, don't redirect `</dev/null`. Codex always takes its prompt as an argument with stdin closed.
- **Never echo secrets.** Don't print env values, tokens, or cookies into logs or `run-metadata.md`. Keep `logs/` out of any committed artifact set.
- These commands are illustrative, not guaranteed current — confirm flags against `<cli> --help` before a large run.

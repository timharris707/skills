# Advisory Board Scripts

Optional helpers for a board run. The skill works without them — they make two roadmap features concrete. Python 3 standard library only; no install step.

| Script | Does | Reference |
| ------ | ---- | --------- |
| `board_verdict.py` | Validate `verdict.json`; gate CI on the verdict (`--gate`). | `references/verdict-schema.md` |
| `format_output.py` | Render `verdict.json` as a TL;DR, PR comment, Slack message, or normalized JSON. | `references/output-formats.md` |
| `render_handoff.py` | Render `final-consensus.html` from a `handoff-data.json` — deterministic, fails on any leftover placeholder. | `references/handoff-template.html` |

## Quick start

```
# validate and summarize
python3 scripts/board_verdict.py path/to/verdict.json

# gate a merge: non-zero exit when the board says "block"
python3 scripts/board_verdict.py path/to/verdict.json --gate

# turn the verdict into a PR comment
python3 scripts/format_output.py path/to/verdict.json --format pr

# render the HTML handoff deterministically from structured data
python3 scripts/render_handoff.py path/to/handoff-data.json -o final-consensus.html
```

> Paths above are relative to the **skill directory** — `skills/advisory-board/` in this repo, or the installed skill root (e.g. `~/.codex/skills/advisory-board/`) — the same convention as every `references/…` path in the skill. Run the scripts from there, or prefix them with that directory; `scripts/board_verdict.py` won't resolve from the repo root.

Both read the `verdict.json` a run emits next to `final-consensus.md`. See `examples/payments-idempotency-review/verdict.json` for a filled-in sample.

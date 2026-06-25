# Verdict Schema — `verdict.json`

Alongside the prose handoff, a run emits `verdict.json`: a small, machine-readable summary so the board's conclusion can drive tooling — most usefully a **CI / launch gate** ("block the merge when the board says block"). It is a *view* of `final-consensus.md`; the two must agree.

## Schema (`advisory-board/verdict@1`)

```json
{
  "schema": "advisory-board/verdict@1",
  "title": "Payments API idempotency keys",
  "date": "2026-06-24",
  "verdict": "block",
  "confidence": "high",
  "unanimous": true,
  "rounds": 2,
  "board": [
    {
      "seat": "Claude",
      "model": "claude-opus-4-8",
      "lens": "architecture",
      "round_verdicts": ["block", "block"],
      "dropped": false
    }
  ],
  "blockers": [
    { "title": "Atomic dedup", "body": "SET NX claim with an in-progress sentinel ..." }
  ],
  "dissent": [
    { "who": "Codex", "body": "..." }
  ],
  "open_questions": ["..."],
  "next_actions": ["..."]
}
```

### Fields

- `verdict` — `ship` | `caution` | `block`. The board's final position.
- `confidence` — `low` | `medium` | `high`.
- `unanimous` — did every seat land on `verdict` in the final round.
- `board[]` — one entry per seat; `round_verdicts` is per-round, `dropped` flags a seat that didn't finish (see `references/run-metadata-template.md`).
- `blockers[]` / `dissent[]` / `open_questions[]` / `next_actions[]` — the same content the handoff shows.

Required: `schema`, `verdict`, `confidence`, `board`, `rounds`. The rest are recommended.

## Using it as a gate

`scripts/board_verdict.py` validates the file and, with `--gate`, exits non-zero when the verdict meets a threshold:

```
python3 scripts/board_verdict.py verdict.json --gate                    # fail on block
python3 scripts/board_verdict.py verdict.json --gate --fail-on caution  # fail on caution or block
```

Exit codes: `0` pass · `1` gate fail · `2` usage/schema error. Drop it into CI to hold a merge or launch until the board clears it.

See `references/output-formats.md` for turning the same file into a PR comment, Slack message, or TL;DR.

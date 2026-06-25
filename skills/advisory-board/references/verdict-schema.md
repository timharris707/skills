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

- `verdict` — `ship` | `caution` | `block`. The board's final position, and the canonical gate axis.
- `decision` (optional) — the native call when the decision isn't software-shipping (e.g. `invest` / `hold` / `wind-down`, or `go` / `no-go`). Map it onto `verdict` (invest→ship, hold→caution, wind-down/no-go→block); tooling reads `verdict`, while humans and `scripts/format_output.py` show `decision`.
- `confidence` — `low` | `medium` | `high`.
- `unanimous` — did every seat land on `verdict` in the final round.
- `board[]` — one entry per seat; `round_verdicts` is per-round, `dropped` flags a seat that didn't finish (see `references/run-metadata-template.md`).
- `blockers[]` / `dissent[]` / `open_questions[]` / `next_actions[]` — the same content the handoff shows.

Required: `schema`, `verdict`, `confidence`, `board`, `rounds`. The rest are recommended.

## What `board_verdict.py` enforces

Validation is strict so a malformed verdict can't quietly pass a gate. Beyond the required fields, `scripts/board_verdict.py` checks:

- `schema` is exactly `advisory-board/verdict@1`.
- `verdict` ∈ {ship, caution, block}; `confidence` ∈ {low, medium, high}; `rounds` is a positive integer.
- each `board[]` seat has `seat`, `model`, and a non-empty `round_verdicts` (every entry ∈ {ship, caution, block}); `lens` and `dropped` are type-checked when present.
- at least **two** seats actually ran — a seat with `dropped: true` doesn't count, because a one-voice board isn't a board.
- if `unanimous` is present, it matches the seats' final-round verdicts (claiming unanimity the votes don't support is rejected).

A schema violation exits `2`, distinct from a clean file that simply fails the gate (`1`).

## Using it as a gate

`scripts/board_verdict.py` validates the file and, with `--gate`, exits non-zero when the verdict meets a threshold:

```
python3 scripts/board_verdict.py verdict.json --gate                    # fail on block
python3 scripts/board_verdict.py verdict.json --gate --fail-on caution  # fail on caution or block
```

Exit codes: `0` pass · `1` gate fail · `2` usage/schema error. Drop it into CI to hold a merge or launch until the board clears it.

See `references/output-formats.md` for turning the same file into a PR comment, Slack message, or TL;DR.

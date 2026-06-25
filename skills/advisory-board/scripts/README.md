# Advisory Board Scripts

`run_board.py` is the conductor that drives a board run; the others are optional helpers that wire a board's `verdict.json` into CI and tooling (gating, formatting, deterministic HTML rendering). Python 3 standard library only; no install step.

| Script | Does | Reference |
| ------ | ---- | --------- |
| `run_board.py` | The **conductor** (M1–M3): deterministic seat-adapter registry, `--dry-run`, toolchain currency (`toolchain` — check/update stale CLIs, propose fallback model ids), executable preflight (GO/NO-GO), a hash-bound egress/quarantine gate before any provider call, and the **round-1 fan-out** (real spawn, §13 failure protocol, per-seat `round-1/` artifacts). Calls the scripts below; never reimplements them. | `design/run-board-conductor.md` |
| `board_verdict.py` | Validate `verdict.json`; gate CI on the verdict (`--gate`). | `references/verdict-schema.md` |
| `format_output.py` | Render `verdict.json` as a TL;DR, PR comment, Slack message, or normalized JSON. | `references/output-formats.md` |
| `render_handoff.py` | Render `final-consensus.html` from a `handoff-data.json` — deterministic, fails on any leftover placeholder. | `references/handoff-template.html` |

## Quick start

```
# check each seat CLI vs its latest release (read-only): current / STALE / missing / unknown
python3 scripts/run_board.py toolchain

# update stale CLIs and/or install absent ones (consent-gated; --yes approves unattended)
python3 scripts/run_board.py toolchain --update
python3 scripts/run_board.py toolchain --install   # installs absent CLIs (account/auth still required)

# preview a run — config, run-card, preflight plan, egress manifest, artifact tree (no spawn)
python3 scripts/run_board.py run --source plan.md --dry-run

# probe the seats (GO/NO-GO); exits non-zero if fewer than two are GO
python3 scripts/run_board.py preflight --source plan.md

# full run: preflight + egress gate + round-1 fan-out -> round-1/<seat>.md + .raw
# (stops at the round-1 boundary; synthesis -> verdict.json is M4/M5)
python3 scripts/run_board.py run --source plan.md --sensitivity public

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

`board_verdict.py` and `format_output.py` read the `verdict.json` a *completed* run emits next to `final-consensus.md` (produced once the conductor reaches synthesis — M5). `run_board.py` currently stops at the **round-1 boundary**: it spawns the board and captures each seat's review under `round-1/`, but does not yet synthesize a `verdict.json` (M4 packets, M5 verdict). See the repo-root `examples/payments-idempotency-review/verdict.json` for a filled-in sample, and `references/verdict-schema.md` for the schema.

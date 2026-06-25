# Advisory Board Preflight

Run this before launching a board. Most board failures are environmental — a CLI not installed, expired auth, a renamed model, a hung process — not reasoning. Catch them here, before spending real tokens.

Goal: a go/no-go table. Proceed only when at least two seats are **GO** (a board needs at least two voices). Label any seat that is degraded or dropped in the final handoff.

## What to check, per seat

For each seat in the lineup (Claude, Codex, Gemini, or whatever you're running):

1. **CLI present** — the binary exists and runs.
   - `claude --version` · `codex --version` · `gemini --version`
2. **Auth active, subscription-backed where possible** — not API-key-only, not logged out.
   - Use the CLI's own status / whoami command. Never print tokens, cookies, or keys.
3. **Requested model resolves** — the model named in the lineup is actually available.
   - List models if the CLI supports it, or run the smoke ping below with the real model flag and confirm it isn't rejected as unknown.
4. **Smoke ping** — a trivial read-only prompt returns a non-empty answer.
   - Keep it to one word back. This proves auth + model + transport end to end in one shot.

Verify every flag against `<cli> --help` first — CLI syntax drifts between versions, and the commands here are illustrative, not guaranteed current. Close stdin on Codex (`</dev/null`) so `codex exec` can't hang waiting for EOF.

## Smoke-ping templates

Read-only, one-token answers. Adapt flags to the installed CLI.

```
# Claude
claude -p "Reply with the single word: ready" --model <model> --permission-mode plan

# Codex
codex exec --sandbox read-only --config model="<model>" "Reply with the single word: ready" </dev/null

# Gemini
gemini -p "Reply with the single word: ready" -m "<model>"
```

## Go/no-go table

Record one row per seat, then decide:

| Seat   | CLI | Auth | Model | Smoke | Verdict |
| ------ | --- | ---- | ----- | ----- | ------- |
| Claude |  ✓  |  ✓   |   ✓   |   ✓   | GO      |
| Codex  |  ✓  |  ✓   |   ✓   |   ✓   | GO      |
| Gemini |  ✓  |  ✗   |   —   |   —   | NO-GO   |

Decision rule:

- **≥ 2 seats GO** → proceed. If a seat is NO-GO, run the smaller board and label the missing seat (and the round it dropped) in the handoff.
- **< 2 seats GO** → stop and report which checks failed and how to fix them. Do not run a one-voice "board."

## What to capture

Fold the result into `run-metadata.md`: each seat's CLI version, the model that actually answered (not just the one requested), auth mode (subscription / API key — no secrets), and the go/no-go verdict. This is the provenance the final handoff cites.

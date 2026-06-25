# Advisory Board Preflight

Run this before launching a board. Most board failures are environmental — a CLI not installed, expired auth, a renamed model, a hung process — not reasoning. Catch them here, before spending real tokens.

Goal: a go/no-go table. Proceed only when at least two seats are **GO** (a board needs at least two voices). Label any seat that is degraded or dropped in the final handoff.

## Step 0: toolchain currency (run this first)

A stale seat CLI is the single most common reason a board half-fails: a frontier model gets renamed (e.g. `gemini-3-flash-preview` → `gemini-3.5-flash` on GA) and the pinned id suddenly 404s on a CLI too old to know the new route. So the conductor checks each CLI against its latest release *before* probing models, and offers to update the stale ones.

```
run_board.py toolchain            # read-only: installed vs latest, per seat
run_board.py toolchain --update   # update stale CLIs (confirms first; --yes to skip the prompt)
run_board.py toolchain --install  # install absent CLIs (consent-gated; auth still required)
```

- **Check** is read-only — it never mutates anything. It reads the installed version (`<cli> --version`) and the latest published version (npm for claude/codex, Homebrew for gemini/antigravity/ollama), and reports each seat as **current / STALE / missing / unknown**, plus a *flag-drift* advisory when the installed CLI is newer than the version its argv flags were last grounded against (re-verify `--help`).
- **Update is consent-gated** (`detect → confirm → update`): it lists what's stale and updates only what you approve. `--yes` approves unattended; a non-interactive shell without `--yes` is a no-op, not an error.
- **Missing CLIs**: an absent binary is reported as `missing` (distinct from `unknown`), and the exact install command is printed. `--install` runs it on consent. **Installing a CLI does not grant an account** — you still need provider auth, so it's only worth installing a CLI you can log into.
- `run --update-tools` folds Step 0 into a run: check + (gated) update, then preflight, then the board.

## When the board can't form (fewer than 2 usable seats)

A board needs at least two independent voices. Rather than dead-ending, preflight (and `run`) print actionable guidance: which seats are *not installed* (with the install command) vs *installed but unusable* (auth/login or model), and the realistic ways to still run a board:

- **Install + authenticate another provider** (the commands are printed).
- **A same-provider, multi-lens board** — two seats on the same model with different lenses. Lower independence than two providers, so flag it in provenance. See `references/board-composition.md`.
- **A human or local-model seat** — no extra account needed. See `references/board-composition.md`.

So a user who only has one provider (say, only Anthropic) is never stuck: they can run a same-provider multi-lens board or add a local/human seat, and the skill says so instead of just refusing.

**Model ids stay pinned, never auto-swapped.** If a pinned model id still doesn't resolve after the CLI is current, preflight probes that seat's known fallbacks and **proposes** a resolvable id (surfaced in the preflight table and `run-metadata.md`) — it does not silently switch models. Apply it yourself with `--model <seat>=<id>` or by updating the registry.

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

Verify every flag against `<cli> --help` first — CLI syntax drifts between versions, and the commands here are illustrative, not guaranteed current. Close stdin on Codex (`</dev/null`) so `codex exec` can't hang waiting for EOF, and pass `--skip-git-repo-check` when running outside a git repo. Some CLIs (e.g. Gemini) print internal errors to stderr yet still return a valid answer — judge a seat by whether usable content came back, not by stderr noise alone.

## Smoke-ping templates

Read-only, one-token answers. Adapt flags to the installed CLI.

```
# Claude
claude -p "Reply with the single word: ready" --model <model> --permission-mode plan

# Codex
codex exec --sandbox read-only --skip-git-repo-check --config model="<model>" "Reply with the single word: ready" </dev/null

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

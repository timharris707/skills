---
name: wizard
description: Generate an interactive bash wizard that walks a human through a procedure only they can perform: third-party dashboards, credentials, DNS records, CI secrets, one-off cutovers. Use when a task stalls on steps an agent cannot take, or when a manual setup is tedious to re-explain every time. Not for steps the agent can perform itself.
---

# Wizard

A **wizard** is a bash script that walks a human through a manual procedure one step at a time. It opens each URL, says exactly what to click and copy, captures the values, writes them where they belong, verifies what it can, and shows how much is left.

It exists for the class of work that blocks agents outright: a dashboard behind someone's SSO, a registrar's DNS panel, a secret that must never enter an agent's context. The alternative is a wall of numbered prose the human loses their place in on step four. A build lane that hits such a step mid-item routes it here per [implement](../implement/SKILL.md)'s interlock: the wizard carries the human steps while the `blocked` label carries the wait.

The UX is already solved by [template.sh](template.sh): progress with time remaining, confirmation gates, cross-platform URL opening, hidden secret entry, idempotent `.env` upserts, `gh secret` writes, live verification, and a closing summary of what still needs doing by hand. **Your job is to scope the procedure and author its stages.** The library above the `STAGES` marker is identical in every wizard; that consistency is the point.

A wizard is **ephemeral by default**: built for one run, written to a scratch or `scripts/` path, deleted when the job is done. Commit it only when the repo wants a repeatable setup path, and then link it from the README so the next person runs the script instead of re-deriving it.

## 1. Scope the procedure

Work out every manual step and every value captured along the way. Read the repo first; do not interview cold:

- **Setup**: `.env`, `.env.example`, `README`, `docker-compose*`, framework config, and `.github/workflows/*` (every `secrets.*` and `vars.*` reference is a value the wizard must produce).
- **Migration or cutover**: the current state, the target state, and every irreversible action between them.

Then show the decider the ordered stage list and the values each produces, and confirm. They may add, drop, or reorder.

**Done when:** every stage is named in order, and for each value you know (a) where the human gets it, (b) where it is written (`.env`, a CI secret, both, or nowhere, since some stages are pure actions) and (c) whether it is secret.

## 2. Map each stage's journey

For each stage, write the exact path a human follows: which URL, what to do there, where the value appears, which variable it fills: "Dashboard → Developers → API keys → Reveal test key → copy".

**Where you do not know the current UI or the exact command, say so and ask, or check the vendor's docs.** Inventing a menu path that does not exist is worse than admitting the gap: the human trusts the script and burns ten minutes hunting for a button that was never there. This is the single most common way a wizard fails.

**Done when:** every stage traces to concrete instructions a stranger could follow, and every uncertain path is either verified against primary sources or explicitly flagged in the script.

## 3. Author the wizard

Copy `template.sh` to the target path and replace the example stage with one `stage` per step, in dependency order. Use the library helpers (`require`, `stage`, `say`/`step`/`note`, `open_url`, `ask`/`ask_secret`, `write_env`, `set_secret`/`set_var`, `check`, `pause`/`confirm`, `manual`) and set `TOTAL_STAGES` and `TOTAL_MINUTES` to honest estimates.

Hold the bar the template sets:

- Open the URL **before** asking for the value it produces.
- `ask_secret` for anything secret; `write_env` for every persisted value; `set_secret` only for what CI actually needs.
- `confirm` before any irreversible action.
- `check` wherever a manual step has an observable result: a DNS record that should resolve, an endpoint that should answer. A step the script can verify is a step the human cannot silently get wrong. Use `await` instead when the result propagates.
- `manual` for anything the script cannot do, so it lands in the closing summary instead of being forgotten.
- `require` returns non-zero on a missing tool, so under `set -e` it is always called as `if require gh; then …` or `require gh || true`. `check` and `await` never return non-zero: a half-finished procedure that aborts before its summary is worse than one that records what it could not confirm.
- One focused task per stage. Each `stage` clears the screen, so anything the human still needs must not have scrolled away.
- Never hand-edit the library above the marker.

## 4. Verify and hand off

- `bash -n <script>`, and `shellcheck` if available.
- `chmod +x <script>`.
- **Do not run it end to end yourself**: it opens browsers and blocks on human input. Trace it statically: every value from step 1 is captured and lands where step 1 said, and every `set_secret` name matches a `secrets.*` reference in CI exactly.
- Tell the human how to run it, and what they will need open before they start (accounts, logins, a payment method).
- **Where a tracker item drives this procedure, its pending manual steps block it.** Until the human has run the wizard and cleared the closing summary, apply the `blocked` label to the driving item, with a comment naming the wizard and the steps; pending human steps are exactly the non-ticket blocker the pack's tracker discipline expresses with that label. When the human reports the run complete (or the `check`s confirm it), recompute the item's remaining non-ticket blockers (the wizard's pending steps are one contributor, not necessarily the only one) and remove the label only when none remain.

## Done when (checkable: verify each line before reporting complete)

- `bash -n` passes and the script is executable.
- Every value identified in step 1 is captured by a stage and written where step 1 said it goes.
- Every `set_secret` name matches a CI reference exactly, checked against `.github/workflows/*`, not from memory.
- Every stage that has an observable result carries a `check`; everything the script cannot do carries a `manual`.
- `TOTAL_STAGES` equals the number of `stage` calls, and `TOTAL_MINUTES` is an honest sum.
- No invented UI paths: every menu path is either verified against primary sources or flagged in the script as unverified.
- Where a tracker item drives the procedure, it carries the `blocked` label with a comment naming the wizard and its pending steps, or the run is confirmed complete and the label came off only after the remaining-blockers recompute.

## Attribution

The wizard concept and the shape of its library are adapted from Matt Pocock's [`wizard`](https://github.com/mattpocock/skills/tree/main/skills/engineering/wizard) (MIT). This implementation adds prerequisite checks, live verification, and manual-step tracking.

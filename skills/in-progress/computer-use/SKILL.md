---
name: computer-use
description: "Hand a GUI task on this Mac (click, type, read a window, move through an app) to Codex Computer Use, one bounded subtask at a time, and get back a result the runner has checked against what actually happened. Use when a task needs a desktop app driven or read and no API, CLI, or connector covers it, or when the user says use the computer, drive the app, or computer use."
---

# Computer Use

Codex Computer Use (the Codex desktop plugin, model gpt-6-astra) can read and operate
Mac apps through their accessibility trees and screenshots. This skill hands it one
bounded subtask per call, headless, through `codex exec`, and audits the result against
the recorded event stream rather than the model's own account. You write the brief, run
the script, read the audited result and the screenshots, and report to the user in plain
words.

Every call is a Codex model call billed to whatever the user's Codex profile is
configured for. Preflight and each subtask take tens of seconds to a few minutes.

## What has and has not been verified

Verified live on 2026-09-20 with this runner, on the development Mac:

- Four Codex profiles, each with `CODEX_HOME` set to it: live preflight passed (one
  read-only Sky call listed the running apps) and a read-only `run` against Chrome came
  back `done` with a screenshot the reviewer opened and matched to the screen. All four
  resolve to one signed helper inside the ChatGPT app. Every call was routed through the
  user's local proxy, as the `routing` line in preflight showed beforehand.
- Three non-Chrome apps by exact bundle ID, read-only: Calculator (a system app that was
  not running; the helper launched it), Spotify (a third-party app that was running), both
  `done` with verified screenshots; Finder was refused by preflight because it was not in
  the approval file, which is the expected approval boundary, with no model call spent.
- The persistent approval file was extended from 1 to 77 exact IDs by `approvals add`, with
  a backup. Runs against the newly approved apps succeeded seventeen minutes later with no
  restart of the ChatGPT app or any helper process by the operator. The helper service does
  not show up as a long-lived process, so it most likely reads the file on each call.
- Finder by bundle ID after the user approved it: `done` on the accessibility text, but the
  helper's screenshot of the Desktop window was a blank white image and the audit accepted
  it. The validator now rejects a flat single-colour image as evidence.
- The confirmation path, live, in Calculator: a brief whose last step (pressing AC after
  1 + 2 =) was declared consequential. The model clicked AC, 1, +, 2, = with a fresh state
  after each click, then stopped with `needs_confirmation` and the exact question; the
  screenshot showed 1+2 and 3. `resume --answer "no, leave it showing 3"` ended `blocked`
  with no Codex call (the proxy log shows zero requests). `resume --answer yes` continued
  the same session, re-bootstrapped, re-observed, clicked AC once, and ended `done` with
  the display at 0 and a matching screenshot. Turn 1's records were kept beside turn 2's.
- Earlier hand probes: coordinate scroll, JSON reply schema, session resume by ID.

Not yet verified live: typing, paste, drag, secondary actions, and scrolling by element
index through this runner; apps beyond the five above; any Mac other than this one. An
app that has passed once is not a guarantee for a different window or task in that app.
Do not tell the user that headless mode can drive an app until a run against it has
passed.

## Before the first call in a session

```bash
python3 skills/in-progress/computer-use/scripts/computer_use.py preflight --app "<app>"
```

It checks the active profile (`CODEX_HOME`), the Codex version, that the `computer_use`
feature is stable and enabled, the helper app and its signature, macOS Accessibility and
Screen Recording for the helper (a read-only look at the privacy database, which is
private Apple implementation detail), and whether the target app is in the persistent
approval file. Anything it cannot confirm is a problem, not a pass. Exit 0 means every
check passed. Exit 2 lists the problems in plain words; report them, do not work around
them. Add `--live` to also run one read-only Sky call through Codex, which proves the CLI,
plugin, helper, and permissions work together. That is a real model call.

Preflight also reports `routing`: the model provider and base URL the profile's
config.toml names, read with a real TOML parser from the top-level keys only, plus the
runner's own `--model` override. A config that names no provider bills the signed-in
account directly; the user's standing rule is to route through the local proxy, so that
is a problem unless you pass `--allow-direct` on their say-so. A provider the parser
cannot resolve to a base URL is also a problem. Routing reads the file only: it cannot
see a `-p` profile layer or `-c` overrides the runner itself does not pass.

**Two approval states exist.** The running Codex desktop session can approve apps on
screen and hold those approvals in memory. A headless `codex exec` process cannot show
that prompt, so it sees only the persistent approval file. If preflight says the app is
not approved, that is a headless-only limit, not a product limit, and the fix is the
explicit setup step below. Ordinary runs never touch that file.

## One subtask per call

```bash
python3 skills/in-progress/computer-use/scripts/computer_use.py run \
  --app "Mail" \
  --goal "Open the draft titled 'Q3 numbers' and read its recipient list" \
  --done "The draft is frontmost and its To field is visible in the accessibility text" \
  --start "Mail is running with the Inbox showing" \
  --allow "click, scroll, read" \
  --forbid "send, delete, edit the body, open any other message" \
  --effort medium
```

`--app` accepts any Mac app by display name, `.app` path, or bundle ID. There is no
built-in app list. Always pass `--start`, `--allow`, and `--forbid`; the brief prints
"none stated" when you leave one out, and the model then decides for itself. `--effort`
is `medium` by default; use `low` for a pure read, `high` for an ambiguous or multi-app
subtask. `xhigh` is allowed and slow.

A subtask is one coherent slice that ends in a verified state: several reads and
reversible steps are fine, but split immediately before any action that sends, submits,
posts, deletes, changes permissions or settings, spends money, or transmits personal
data. The brief tells Codex to stop before such an action and ask; the audit then
refuses to call a run `done` if a recorded action looks like one of those and the user's
`--preapproved` words do not name it. `--preapproved` carries the user's exact words
when they approved one of those in advance; nothing else counts.

The script writes the brief (goal, definition of done, app and bundle ID, starting state,
allowed and forbidden actions, confirmation boundary, observe-after-every-action rule,
and the Sky rules in references/sky-rules.md) and runs Codex with a read-only shell
sandbox, a JSON reply schema, and a timeout. The shell sandbox does not make GUI actions
read-only. The brief steers the model, the audit catches what it can see in the record,
and the user is the last line.

## Reading the result

Everything lands in a private run directory (`~/.computer-use/runs/<stamp>-<slug>/`,
mode 0700): `brief.md`, `events.jsonl`, `reply.json`, `result.json`, `shots/`, and
`pending.json` when a question is open. `result.json` is the runner's verdict, not the
model's. The model's words can lower a verdict, never raise one. It carries:

- `status`: `done`, `needs_confirmation`, `blocked`, or `failed`. Exit codes 0, 3, 4, 5.
- `session_id`, `target` (input, display name, bundle ID), `effort`, `run_dir`, `preflight_skipped`.
- `observed_before` and `observed_after`: what the app showed, in the model's words.
- `actions_recorded`: every Sky call parsed from the event stream, in order, with whether its arguments were a literal the runner could read. This is the record; `model_actions_claimed` is only the model's list.
- `other_tool_calls`: anything the model did outside Sky, such as a shell command. Any entry here blocks the run.
- `evidence`: screenshots that this run produced (under the helper's screenshot folder or named in the event stream), copied into `shots/`. `evidence_rejected`: what the model named that was not.
- `lint`: Sky-rule violations seen in the recorded calls.
- `risky_signals`: recorded actions whose tool-call title or target mentioned send, submit, delete, pay, permission, and so on, or a Return key press.
- `may_have_had_effect` for this turn and `run_may_have_had_effect` across turns.
- `reason`: why a run is `blocked` or `failed`, quoted from the source.

Open the evidence screenshots yourself before reporting. If `observed_after` claims a
change and the screenshot does not show it, say so; do not pass the claim through.

The audit fails closed. A permission it cannot confirm, an unapproved app, a helper or
signature error anywhere in the stream, a timeout, a non-zero exit, malformed output or
event lines, an action outside Sky, a state-changing call whose arguments it could not
read, a state change with no observation after it, a risky action with no matching
pre-approval, a stale-index error, or evidence this run did not produce all downgrade the
status and name the cause. A timed-out run that recorded state-changing actions says so:
do not retry it, observe first with a fresh read-only run.

## Confirmations and resume

When status is `needs_confirmation`, `pending.json` holds the exact question, the session
ID, the last verified state, and the run directory. Ask the user the question verbatim,
then:

```bash
python3 skills/in-progress/computer-use/scripts/computer_use.py resume \
  --run-dir ~/.computer-use/runs/<stamp>-<slug> --answer "<the user's exact words>"
```

The runner, not the model, reads the answer. Only an unqualified yes ("yes", "ok", "go
ahead", "yes, send it") launches anything; "no", "yes but", or anything conditional ends
as `blocked` without a Codex call, and a changed request is a new subtask. On a yes, the
resume continues the same Codex session, re-runs the Sky bootstrap (REPL state does not
survive), tells the model to take a fresh full app state and stop if it no longer matches
the last verified state, and treats the user's yes to that exact question as the
pre-approval for the action it described. Never answer on the user's behalf, and never
rephrase their answer.

## Explicit setup: broadening headless approvals

"Any app" means two separate things here. Targeting is open-ended: `--app` resolves any
installed app by name, path, or bundle ID with no list to maintain. Headless approval is
not: the helper refuses an app that is not in its persistent approval file, so each app
needs one explicit entry, and a newly installed app needs one too. The approval file is
system-wide, so one entry covers all four Codex profiles.

Only when the user asks for it, and never inside an ordinary run:

```bash
python3 skills/in-progress/computer-use/scripts/computer_use.py approvals inspect
python3 skills/in-progress/computer-use/scripts/computer_use.py approvals plan
python3 skills/in-progress/computer-use/scripts/computer_use.py approvals add --bundle-id com.apple.mail --bundle-id com.apple.finder --yes
```

`plan` lists every user-facing app in the standard app folders (including apps one
vendor folder deep, such as `/Applications/Adobe X/X.app`, but not helpers nested inside
other apps) with its exact bundle ID, diffs that against the approval file, and prints
the exact `add` command it would take to cover the rest. It writes nothing. Apps it could
not read are listed under `skipped` with the reason. An app installed somewhere else can
still be added by hand with `add --bundle-id`. After the user installs a new app, run
`plan` again: the new app appears under `unapproved` with the one-line command to add it.
Show the user the IDs and get a yes before running `add`.

Editing this file is not something OpenAI documents or supports; the helper may ignore
or rewrite it. `add` backs up the file beside itself (never overwriting an earlier
backup), adds the exact bundle IDs given (no wildcards; the file holds exact IDs only),
keeps every other key in the file, writes atomically, reports before and after with
hashes, then runs one read-only probe against the first new app to say whether the
running helper noticed the change or needs a restart. That probe is a real Codex call
and may bring the app forward; `--no-probe` skips it. Report the whole result to the
user, including the backup path. Adding an app here does not grant macOS Accessibility or
Screen Recording; those belong to the helper and preflight reports them separately.

## Retention

Screenshots can hold passwords, messages, and money. Runs live only in the private run
directory. Every `run` first prunes runs older than seven days (pending ones are kept);
`prune-runs` does the same on demand and only ever deletes directories this runner made.
Never copy screenshots anywhere else without the user asking.

## Done when (checkable: verify each line before reporting complete)

- Preflight ran once this session and exited 0, or its problems were reported unchanged.
- Every call was one bounded subtask with a `--done` the user could see on screen and explicit `--allow` and `--forbid`.
- `result.json` was read, and the report to the user gives its status, `actions_recorded` in plain words, and the screenshot paths.
- Any `risky_signals`, `lint`, `other_tool_calls`, or `evidence_rejected` entries were mentioned, even on `done`.
- Any `needs_confirmation` was put to the user verbatim and resumed only with their exact words.
- The approval file was not edited except through `approvals add --yes` at the user's request, and that result was reported in full.
- No claim about the app's end state rests on the model's words alone: a screenshot or accessibility text was checked.

## Attribution

Designed from live probes of Codex Computer Use on 2026-09-20 and a design review by the
operator it wraps (Codex, gpt-6-astra); the runner itself was then hardened against an
adversarial review before any end-to-end run. The subprocess pattern follows this repo's
advisory-board. Not adapted from another skill.

<!-- lineage: own -->

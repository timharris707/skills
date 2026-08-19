---
name: show-me-your-work
description: "Keep a reviewable decision trail for long-running or unattended work: one append-only TSV log, one row per decision with its why, evidence, and result. Use when starting an autonomous, multi-phase, or loop run a human reviews after stepping away, when a reviewer needs the trail to trust a result without rerunning it, or when the user asks for a decision log or says show your work."
---

# Show me your work

For work a human reviews after the fact, a decision trail lets them reconstruct what was decided, why, and on what evidence, without rerunning the work or reading the whole transcript. Keep one canonical log so the trail is consistent and a future agent can find it.

## A third artifact type

This log is a per-run audit ledger, and it is deliberately not either of the catalog's other two record types:

- **Not a handoff.** The handoff skill writes a resume pointer: where the work stands right now, overwrite-don't-append, so a fresh session picks up losslessly. This log is the opposite shape on purpose: append-only history of one run, kept so a reviewer can audit it, never read to resume. The handoff's overwrite rule still stands; it applies to the handoff, not to this ledger.
- **Not domain memory.** The domain-memory skill keeps a repo's durable institutional why: settled decisions and terms that outlive any run. This log is scoped to one run and is usually discarded after review. A decision made mid-run that deserves to outlive the run still goes to domain memory through its own write moments; a row here is evidence, not institutional record.

When a run produces all three, they don't overlap: the handoff says where to resume, domain memory says what the team settled, and this ledger shows how this run earned its result.

## The format

A single TSV file, one row per decision. TSV because GitHub renders it as a sortable table, `column -s$'\t' -t` and spreadsheets read it, and a row appends with one command. Cells stay single-line. Evidence is a pointer, not prose.

Copy `references/decision-log-template.tsv` (the header row) to start a clean log. Columns:

- **ts.** ISO8601 timestamp. The timeline axis.
- **phase.** The phase or workstream.
- **decision.** What was chosen or done, one line.
- **why.** The reason in plain words. If a principle drove it, say it plainly (`explored options first, this was a one-way door`), not as a jargon tag.
- **evidence.** A link or path that proves it: commit SHA, PR number, `file:line`, or an artifact, trace, or screenshot path. Never a paragraph.
- **result.** The outcome or predicate state: `tests green`, `reverted`, `pixel-diff 0`, `INCONCLUSIVE`, `open`.

An example, plain-spoken so a reviewer reads it at a glance. This is illustration only; don't copy these rows into a real log.

```
ts	phase	decision	why	evidence	result
2026-05-24T09:02:00Z	frame	counted the work first, about 100 components and roughly 75 hours	wanted to know the size before starting a long run	commit 3a9f1c2	found 5 things to sort out before starting
2026-05-24T09:40:00Z	harness	took screenshots of the old version before changing anything	so we can compare old against new and catch any visual change	scripts/snapshot.sh, baseline/	saved 120 reference screenshots
2026-05-24T11:15:00Z	widget	moved the widget styles over without changing how it looks	keep the change small and the result identical	commit 7c21e0a, pixel-diff 0	looks identical, tests pass
2026-05-24T12:30:00Z	widget	threw out a helper's work because its screenshots were blank	checked the real files instead of trusting its summary	worktree reset	reverted, tightened the instructions for next time
```

## Logging a row

Write each entry the way you'd tell a teammate what you did. Plain words, concrete actions, no AI speak or abstract jargon. A reviewer should understand each row without decoding it.

Use the helper so rows stay well-formed: `scripts/log.sh <logfile> <phase> <decision> <why> <evidence> <result>`. It stamps `ts`, writes the header on first use, strips stray tabs/newlines, and prefixes any cell starting with `=`, `+`, `-`, or `@` with a single quote so a reviewer opening the log in a spreadsheet doesn't trigger formula execution. If the script isn't present, a bare `printf` appending a tab-separated row works too, but apply those same two protections by hand: keep every cell single-line, and quote-prefix those leading bytes when cells come from generated or user-supplied text.

Log decision points and checkpoints, not every action: a fork chosen, a unit completed with its verification result, a pivot or revert with its trigger, a blocker surfaced, a gate fixed. For loop runs, one row per iteration. Skip the trivial and self-evident.

## Where it lives

By default the log is a working artifact, not committed. Keep it at `decisions.tsv` in the work dir, or `.audit/<task-slug>.tsv` when several efforts run at once, and leave it out of git. Most work doesn't need a committed trail; the local log still keeps the run honest and can be discarded after.

Commit it only when the work is ambitious enough that a reviewer needs the trail to trust the result: a large cross-language port, a multi-week migration, anything where confidence has to be shown rather than assumed. A committed log renders as a table in the PR.

## Rules

- One row is one decision or checkpoint. If it doesn't fit on one line, the decision isn't crisp yet.
- Append-only. A wrong call gets a new row that supersedes it. Never edit or delete history.
- Prefer evidence produced by committed scripts over hand-made one-offs, so a reviewer can re-run it.

## Audit the log against the run's record

At the end of the run, before handing back, check the log told the truth. Audit it against the session's own record: the transcript or session log if your harness exposes one, otherwise the run's observable traces (git history, tool outputs, produced artifacts) plus your own record of the session. Read only this run's record; other sessions' transcripts are private and irrelevant. Walk the log against what actually happened:

- Every row maps to a real action. Cut invented or aspirational entries.
- Each row's evidence resolves and shows what the row claims.
- A fork, pivot, or abandoned approach that shaped the work but isn't logged is a gap. Add it.
- Drop padding. If nobody would audit a row, it doesn't earn its place.

Fix the log, not the story. If the work diverged from what a row claims, the row is wrong.

## Optional gate: cross-model review of the trail

For high-stakes runs, or when the user asks for it, add a closing review by fresh eyes before handing back. Route it through the advisory-board skill's CLI-seat runners: one seat on a different model family from the one that did the work (a Codex, Gemini, or Grok seat when Claude did the work) reads the trail and the run's record, then flags what the user should pay attention to. Not a redo of the work, a scan for what's suboptimal or risky:

- Decisions logged with weak or absent evidence.
- Verification steps skipped or claimed without proof in the record.
- Choices that look risky in hindsight (premature, scope-creeping, papering over a symptom).
- Gaps the user would otherwise miss on a casual skim.

When no other family's CLI is available, fall back to a fresh subagent from the same family that did the work, and say so in the handback: same-family review is the weaker form, not an equivalent. It brings fresh context but shares the blind spots of the model it is auditing.

When the gate runs, end the handback with an "Attention" section. Lead with the reviewer's model on its own line (`reviewed by <model>`), then list each flag pointing to specific rows or moments. "No flags" is a valid value; the model name is not. The self-audit asks if the log told the truth; this gate asks what the user should still scrutinize even when it did.

## Reviewing the trail

Read top to bottom, follow the evidence pointers, spot-check. GitHub renders a committed TSV as a table; `column -s$'\t' -t decisions.tsv` renders it in a terminal. A row whose evidence doesn't resolve, or whose result is unverified, is the audit catching a gap.

## Composing this skill

Other skills route their audit trail here instead of inventing one. Reference it by name and let it own the format; don't restate the columns.

## Done when (checkable, verify each line before reporting complete)

- One canonical TSV exists at a stated path, header row intact, every cell single-line, and history append-only: wrong calls got superseding rows, nothing was edited or deleted.
- Every row survived the closing audit: it maps to a real action in the run's record, its evidence resolves and shows what it claims, and no shaping fork or pivot is missing.
- Formula-risk bytes are neutralized: no cell in the final log starts with a bare `=`, `+`, `-`, or `@`.
- The log's fate is decided and stated: discarded, kept local, or committed because a reviewer needs it to trust the result.
- If the cross-model gate ran, the handback ends with an "Attention" section naming the reviewer's model, and a same-family fallback was labeled as the weaker form.

## Attribution

Adapted from Lauren Tan's [`show-me-your-work`](https://github.com/cursor/plugins/tree/main/pstack/skills/show-me-your-work) in the pstack plugin (github.com/cursor/plugins, MIT). The core is hers, much of it near-verbatim: the TSV format and columns, one-row-one-decision with the one-line-or-not-crisp rule, append-only with superseding rows, evidence as a pointer a reviewer can re-run, local-by-default with the commit-when-trust-requires-it bar, the closing self-audit's "fix the log, not the story", and `log.sh` with its spreadsheet-formula-injection hardening.

Two adaptations: her Cursor-specific transcript-audit instructions (read this run under `agent-transcripts/`, don't glob other projects' chats) became the harness-generic self-audit against the session's own record above; and her mandatory cross-model closing review became an optional gate routed through the advisory-board skill's CLI-seat runners, with the no-other-CLI fallback being a fresh same-family subagent review, stated as weaker. This catalog also adds the third-artifact-type boundary against handoff and domain-memory.

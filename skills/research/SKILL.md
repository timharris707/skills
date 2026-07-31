---
name: research
description: Run an autonomous research lane against primary sources, ending in a cited findings file linked from the driving ticket — and, when the missing facts are human-held, a questionnaire. Use for investigations of vendor materials, regulations, upstream repos, recorded calls, or any fact-finding that should run fire-and-report.
---

# Research

A research lane runs **autonomously** (fire-and-report): it investigates against primary sources — vendor materials, regulations, upstream repos, recorded calls, live systems you have access to — and ends in a **cited findings file** linked from the driving ticket. It runs two ways: as a `research` ticket inside a decision map (see the decision-map skill), and standalone for any investigation worth a recorded answer.

## Contract

1. **Primary sources only.** Read the actual material — the vendor doc, the upstream code, the regulation text, the recording. Secondary summaries are leads, not evidence.
2. **The deliverable is a findings file**, tracked in the repo's docs (default `docs/research/<topic>.md`, or the findings home the team-workflow binding doc names). Material that is PII-bearing or otherwise local-only goes in a git-ignored location instead — the findings file there is still linked from the ticket by path.
3. **Findings cite their sources inline.** A claim without a source is a hypothesis and is labeled as one. Distinguish clearly: what the source says, what you infer, what remains unknown.
4. **Link the findings file from the ticket** and summarize the feature-level answers in a ticket comment, so downstream decision rounds can cite it without opening the file.
5. Multiple research lanes may run in parallel — they share no state beyond the tracker.

## When the facts are human-held

When a research lane hits facts only an external human holds (a vendor contact, a partner engineer, a pilot user), it does not stall or guess — it ends with the **questionnaire terminal move**: [references/questionnaire.md](references/questionnaire.md).

## Done when (checkable)

- The findings file exists at the named location, every claim cited or labeled a hypothesis.
- The driving ticket links the file and carries the feature-level summary.
- Any human-held gaps are covered by an emitted questionnaire (per the terminal move), not by silent assumptions.

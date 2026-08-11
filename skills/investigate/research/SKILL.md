---
name: research
description: Run an autonomous research lane against primary sources, ending in cited findings — and, when the missing facts are human-held, a questionnaire. Use for investigations of vendor materials, regulations, upstream repos, recorded calls, or any fact-finding that should run fire-and-report.
---

# Research

A research lane runs **autonomously** (fire-and-report): it investigates against primary sources — vendor materials, regulations, upstream repos, recorded calls, live systems you have access to — and ends in a **cited findings file** linked from the driving ticket. It runs two ways: as a `research` ticket inside a decision map (see the decision-map skill), and standalone for any investigation worth a recorded answer.

## Contract

1. **Primary sources only.** Read the actual material — the vendor doc, the upstream code, the regulation text, the recording. Secondary summaries are leads, not evidence.
2. **The deliverable is a findings file**, tracked in the repo's docs (default `docs/research/<topic>.md`, or the findings home the team-workflow binding doc names). Material that is PII-bearing or otherwise local-only goes in a git-ignored location instead — the findings file there is still linked from the ticket by path.
3. **Findings cite their sources inline.** A claim without a source is a hypothesis and is labeled as one. Distinguish clearly: what the source says, what you infer, what remains unknown.
4. **Link the findings file from the ticket** and summarize the feature-level answers in a ticket comment, so downstream decision rounds can cite it without opening the file.
5. Multiple research lanes may run in parallel — they share no state beyond the tracker.

## Standalone lanes still ride the tracker

A research lane outside a map follows the same discipline a map ticket would: **claim the driving ticket per the repo's claim recipe before investigating**, and **title the session with the item** (default `#<N> — <short item name>`, per the [orchestrate skill's](../../run/orchestrate/SKILL.md) lane titling), so parallel lanes stay legible on the picker and the tracker alike. An investigation with no driving ticket gets one filed first — the findings need somewhere durable to land.

## The skeptic pass

Findings that will drive a build decision face a skeptic before they are reported: dispatch an independent subagent whose brief is to **kill each load-bearing claim** — re-read the cited source, hunt the contradicting primary material, check versions and dates. A claim the skeptic kills is corrected or relabeled a hypothesis; the findings file records that the pass ran and what it changed. When nothing downstream builds on the findings, the pass is optional — say which way you called it in the ticket summary.

## When the facts are human-held

When a research lane hits facts only an external human holds (a vendor contact, a partner engineer, a pilot user), it does not stall or guess — it ends with the **questionnaire terminal move**: [references/questionnaire.md](references/questionnaire.md).

## Done when (checkable — verify each line before reporting complete)

- The findings file exists at the named location, every claim cited or labeled a hypothesis.
- The driving ticket links the file and carries the feature-level summary.
- Standalone lane: the discipline in "Standalone lanes still ride the tracker" held — check the claim and the title on the tracker and picker, not your memory of doing it.
- The skeptic pass ran or was skipped per its section above, and the call is recorded in the ticket summary.
- Any human-held gaps are covered by an emitted questionnaire (per the terminal move), not by silent assumptions.

## Attribution

This skill is adapted from Matt Pocock's skills (MIT), and follows them closely: [`research`](https://github.com/mattpocock/skills/tree/main/skills/engineering/research) — a background agent investigating against primary sources, following every claim back to the source that owns it, leaving a cited Markdown file in the repo — and [`to-questionnaire`](https://github.com/mattpocock/skills/tree/main/skills/productivity/to-questionnaire), which the questionnaire terminal move tracks structure for structure: **"grill the send, not the subject" is his phrase**, and the gap-targeted questions, most-important-first ordering, answer stubs, welcome for partial answers, and closing catch-all are his design. The tracker half of the lane framing — research tickets run fire-and-report, in parallel, linked from the driving issue — is his [`wayfinder`](https://github.com/mattpocock/skills/tree/main/skills/engineering/wayfinder)'s.

What this repo adds: the standalone-lane discipline — the claim recipe and session titling, the findings home, the PII carve-out — and the skeptic pass.

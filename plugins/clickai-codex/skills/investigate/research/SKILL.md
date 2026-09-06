---
name: research
description: "For factual investigations of vendor materials, regulations, upstream repositories, recorded calls, or other evidence, investigate primary sources and return cited findings. Ask targeted questions when missing facts are held by people; match the requested scope."
---

# Research

Read the [Codex desktop binding](../../../CODEX.md) when this workflow needs harness mechanics, model routing, or recovery.

Research investigates autonomously against primary sources: vendor materials, regulations, upstream repositories, recorded calls, and accessible live systems. Deliver cited findings in the current task for a bounded question, or in the agreed findings file for durable project research. Existing research tickets retain their tracking contract.

## Contract

1. **Primary sources only.** Read the actual material: the vendor doc, the upstream code, the regulation text, the recording. Secondary summaries are leads, not evidence.
2. **Match the requested destination.** For durable research, save to the bound findings home (default `docs/research/<topic>.md`). PII-bearing or local-only material belongs in an ignored location. For a bounded answer, keep the cited result in the current task.
3. **Findings cite their sources inline.** A claim without a source is a hypothesis and is labeled as one. Distinguish clearly: what the source says, what you infer, what remains unknown.
4. **Link durable findings from an existing ticket when that publication is authorized.** Otherwise deliver the cited answer or file link in the current task.
5. Multiple research lanes may run in parallel: they share no state beyond the tracker.

## Standalone research

For a bounded question or read-only audit, deliver the cited findings in the
current task. Do not create a tracker item solely to satisfy this skill. When
the user requests durable project research, save to the agreed findings home.
For an existing tracked research item, use its claim and title conventions and
link the findings back when posting is authorized.

## The skeptic pass

Findings that will drive a build decision face a skeptic before they are reported: dispatch an independent subagent whose brief is to **kill each load-bearing claim**: re-read the cited source, hunt the contradicting primary material, check versions and dates. A claim the skeptic kills is corrected or relabeled a hypothesis; the findings file records that the pass ran and what it changed. When nothing downstream builds on the findings, the pass is optional; say which way you called it in the delivered summary.

## When the facts are human-held

When a research lane hits facts only an external human holds (a vendor contact, a partner engineer, a pilot user), it does not stall or guess: it ends with the **questionnaire terminal move**, [references/questionnaire.md](references/questionnaire.md).

## Done when (checkable: verify each line before reporting complete)

- Findings were delivered in the current task or saved at the agreed location, every claim cited or labeled a hypothesis.
- An existing driving ticket received the link and summary when that publication was authorized; otherwise the current task carries the result.
- Standalone research: the result was delivered at the requested scope and destination, without an unsolicited tracker item.
- The skeptic pass ran or was skipped per its section above, and the call is recorded in the delivered summary.
- Any human-held gaps are covered by an emitted questionnaire (per the terminal move), not by silent assumptions.

## Attribution

This skill is adapted from Matt Pocock's skills (MIT), and follows them closely: [`research`](https://github.com/mattpocock/skills/tree/main/skills/engineering/research), a background agent investigating against primary sources, following every claim back to the source that owns it, leaving a cited Markdown file in the repo, and [`to-questionnaire`](https://github.com/mattpocock/skills/tree/main/skills/productivity/to-questionnaire), which the questionnaire terminal move tracks structure for structure: **"grill the send, not the subject" is his phrase**, and the gap-targeted questions, most-important-first ordering, answer stubs, welcome for partial answers, and closing catch-all are his design. The tracker half of the lane framing is his [`wayfinder`](https://github.com/mattpocock/skills/tree/main/skills/engineering/wayfinder)'s: research tickets run fire-and-report, in parallel, linked from the driving issue.

What this repo adds: the standalone-lane discipline (the claim recipe and session titling, the findings home, the PII carve-out) and the skeptic pass.

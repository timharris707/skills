---
name: ingest
description: Turn a video, recording, voice memo, or media URL into an evidence packet — authoritative transcript, timestamped frames, manifest — plus a routing recommendation. Use when the user shares a media file or URL with a goal, asks to process or transcribe a recording, or wants takeaways from a call, demo, playtest, or video.
---

# Ingest

Media in, evidence out. A run converts a recording or URL into a **packet** — transcript, frames, manifest — reads it, and ends with a **routing recommendation**: what in this media looks like tickets, what needs a grilling session, what is strategy for the decider. The recommendation is where a run stops. Filing, claiming, and building are separate acts that follow it.

## The purpose gate

Every run carries a **purpose**: a named intent plus the user's goal in their own words. The intent picks the pipeline; the goal steers the recommendation. Invoked without one, the first step is asking for it — "why am I getting this media?" is the decider's to answer, never inferred from content.

| Intent | Media | Frames | The recommendation leans toward |
| --- | --- | --- | --- |
| `call` | recorded stakeholder call / walkthrough | yes | takeaways doc, tracker comments, discussion items for the decider |
| `playtest` | recorded play session | dense | findings against the session, filed per the project's review loop |
| `demo` | the user demonstrating + reacting | dense | feedback mapped against where the product actually is |
| `memo` | voice recording, thinking aloud | none | the ideas sorted: actionable now / project-bound / parking lot |
| `triage` | anything — "is something useful here?" | if video | only what clears the bar, named per project it would benefit |
| `reference` | public URL / third-party material | if video | what it claims, what checks out, where it touches our work |

## Run the pipeline

`scripts/ingest.py` owns everything mechanical — staging (with the macOS TCC fallback), URL fetch, caption preview, true duration, transcription, frames, manifest:

```bash
python3 scripts/ingest.py doctor                 # first run: checks tools, prints fixes
python3 scripts/ingest.py run --input <path-or-URL> --intent <intent> --out <run-dir>
```

Run it in the background — transcription takes minutes. For a URL, `captions-preview.txt` appears in seconds: read it to triage whether the media deserves the full pass, and quote only the whisper transcript, never the preview. Several files means one run each, one combined recommendation.

The run directory: the team-workflow binding doc's git-ignored reference home when one names it, else `~/.ingest/<slug>-<date>/`. With the script unavailable, the same pipeline runs by hand — commands, ordering, and the gotchas the script encodes are in [references/pipeline.md](references/pipeline.md).

## Read, then look

The packet is evidence; this step is the judgment, and it belongs to the session that invoked the skill, not a delegate.

1. Read `transcript.md` end to end before opening any frame.
2. Walk `manifest.json` for the moments that matter — every frame carries its timestamp and *why* it exists (`ladder`, `signal`, `screen-change`). Open the frame at every reaction and every load-bearing claim; the words say what the speaker believed, the frame says what the screen showed.
3. Cross-reference what the purpose names: the tracker and existing issues (`call`), the product's current state (`demo`), the projects offered (`triage`), our own work it touches (`reference`).

## Recommend the routing

End with the takeaways ranked and each one routed — as a recommendation, in the language of the table above:

- **Tracker-shaped** items name the issue they'd update or the item they'd become, with the binding doc's labels. No binding doc bound: say so, and route in prose.
- **Undecided-shaped** items name the open questions; offer a [grilling](../../decide/grilling/SKILL.md) session rather than answers.
- **Decider-shaped** items (pricing, partnerships, strategy) are listed for discussion, never resolved.
- A `call` run whose stated purpose asks for it also drafts the thank-you/recap email — saved to the run dir, put on the clipboard as plain text, never sent.

## Retention

The run dir is the archive, and the rule is what can't be re-fetched stays: a local recording's staged copy is kept; a URL's media is discarded after the run (transcript and frames remain — the script does this itself). Nothing under the run dir is ever committed.

## Done when (checkable — verify each line before reporting complete)

- The purpose was stated by the user — intent and goal — before the pipeline ran.
- `manifest.json` shows every stage complete, and the transcript's last timestamp is within a minute of the probed true duration.
- The whole transcript was read, and a frame was opened at every reaction and every load-bearing claim.
- Every takeaway in the recommendation carries a route and, where the transcript supports it, a timestamp.
- Anything quoted came from the whisper transcript, with the caption preview used for triage only.
- Nothing was filed, claimed, or built, and nothing from the run dir was committed.

## Hard guardrails

- **Confidential material on screen never enters a tracked tree in any form, frames included** — crop or omit; summarize in tracked docs instead of pasting.
- **Recommendations only.** The tracker changes when the decider says so, in a separate act — a run that files its own takeaways has skipped the decider it exists to serve.

## Attribution

Consolidates two private predecessors — loanmeld's `video-review` (stakeholder calls, four precedent runs) and gameoflife's `playtest-review` — each of which had learned pipeline lessons the other lacked. The gotcha ledger in [references/pipeline.md](references/pipeline.md) is their merged experience.

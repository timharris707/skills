# Changelog — ingest

All notable changes to the **ingest** skill. Versioned as a standalone plugin
(`ingest/vX.Y.Z`); this file is the source for its release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v1.0.0] - 2026-08-06

### Added

- First release: media file or URL → evidence packet (authoritative whisper
  transcript, timestamped frame ladder + signal extras, manifest) plus a
  routing recommendation. Six intents — call, playtest, demo, memo, triage,
  reference — behind a mandatory purpose gate.
- `scripts/ingest.py`: resumable pipeline (doctor / preview / run) encoding
  the gotcha ledger merged from two private predecessors — loanmeld's
  `video-review` and gameoflife's `playtest-review` — which had each learned
  lessons the other lacked (Zoom duration lies, whisper one-file-per-invocation,
  silence-hallucination collapse, freezedetect over scene scoring on screen
  shares, TCC Finder staging, caption-preview-never-quoted).
- Verified on release day against a real YouTube video: caption preview in
  seconds, 101-segment whisper transcript spanning the full decoded duration,
  99 frames (69 ladder, 26 screen-change, 4 signal), re-fetchable media
  discarded per the retention rule.

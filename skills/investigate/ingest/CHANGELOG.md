# Changelog — ingest

All notable changes to the **ingest** skill. Versioned as a standalone plugin
(`ingest/vX.Y.Z`); this file is the source for its release notes.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed

- **`preview` can now be followed by `run` in the same `--out` directory**
  (issue #160). `preview` created its run directory with a plain `mkdir`
  and never wrote the `.ingest-run` adoption marker, so a same-directory
  `run` afterwards was refused as a foreign non-empty directory (exit 2) —
  breaking the preview-then-run flow SKILL.md describes. `preview` now
  claims its directory through `claim_out_dir`, the same ownership path
  `run` uses, so it writes the marker itself; a genuinely foreign non-empty
  directory is still refused.

## [v1.2.0] - 2026-08-07 — Packets that know their work and offer their own cleanup

### Added

- **Packet-lifetime stance recorded in SKILL.md** (decided by Tim, 2026-08-07,
  issue #116): a packet is durable until the work items derived from it are
  resolved — that bounds how long integrity matters — and afterwards it is
  optionally trash. Cleanup is only ever *offered*; the decider accepts or
  declines, and deletion stays within the v1.1.0 ownership rules
  (ingest-created files only, adopted directories refused). The manifest
  derived-items link and the cleanup sweep that make the offer executable
  landed separately (below), after the items 2–3 grilling.
- **Derived-items links and the cleanup sweep** (designed with Tim, 2026-08-08,
  issue #116 items 2–3): the manifest gains a `derived_items` list, appended
  at filing time by whoever files tickets from the packet (`ingest.py link
  --out DIR --item owner/repo#N` — written at creation, never reconstructed),
  and `ingest.py sweep --home DIR` checks each packet's derived work for
  resolution and *offers* deletion of fully-resolved packets, as the closing
  step of any run and on demand. Resolution is GitHub-first (`gh`: issue/PR
  closed); other trackers resolve via the binding doc's resolution-check
  command (`--check-cmd`, exit 0 resolved / 1 open); with no binding the sweep
  lists the packet for the decider instead of guessing, and a packet with no
  recorded derived items is never treated as resolved. Deletion happens only
  when the decider takes the offer (`--delete`), re-checks resolution, and
  follows the v1.1.0 ownership rules: by manifest ledger, ingest-created files
  only, foreign files left in place, unmarked directories refused. SKILL.md's
  Retention paragraph now describes the mechanism as real rather than pending.
- **Adversarial-review hardening of the sweep**, applied before merge: item
  ids reach a resolution command as data — a quoted positional argument,
  never spliced into the shell — and `link` refuses ids carrying whitespace,
  control characters, or shell metacharacters; a partial deletion (foreign
  files, a failed unlink, a symlink where the ledger recorded a file) keeps
  the packet's marker and manifest so it stays sweepable instead of orphaned,
  under its own exit code (5); `--delete` is bounded to the swept `--home`,
  processes every target, and exits with the worst outcome; resolution-check
  crashes, hand-edited manifest entries, and one packet's failure degrade to
  `unknown` instead of aborting the report; `--check-cmd` without `{id}` is
  refused (a blanket exit 0 would resolve everything); ids are rendered
  escaped in every report line; and `gh` joined `doctor`'s tool roster.
- **49 new tests** (84 total) covering link idempotence and ownership,
  resolution states, sweep verdicts, offer-only ledger deletion, and a
  regression pin for every review finding — including a real-/bin/sh
  injection test and a subprocess mock that can RAISE, not just fail
  politely. The suite still never touches the network.

## [v1.1.0] - 2026-08-07 — Packets that cannot lie about their source

Every item here fixes a defect found by an advisory-board red-team review of
v1.0.0 (Formal Board Review, four seats, unanimous `block`; run recorded at
`~/.advisory-board/runs/ingest-skill-red-team-2026-08-06/`).

### Fixed

- **Resume is bound to identity.** Stage reuse checked only that recorded
  artifact paths existed — and `all([])` made an empty artifact list
  vacuously complete — while every run overwrote `input`/`intent` in the
  manifest. Pointing a second source at a finished packet's `--out` could
  therefore produce a packet labelled B carrying A's transcript and frames.
  Runs now carry an identity fingerprint (input, intent, ladder, frame policy,
  whisper model, script version, plus size+mtime for local files); a mismatched
  re-run is **refused** (exit 4) naming what changed, and each stage records
  the identity it ran under.
- **Completion is declared, not inferred.** Stages carry an explicit
  `status` of `ok` or `skipped`; an empty artifact list no longer implies
  success, and legacy records without a status are never reused.
- **Retention deletes by ledger, not by directory name.** `shutil.rmtree` on
  the whole `media/` subtree is gone: only the files the run recorded creating
  are removed, the directory is dropped only when empty, and anything else
  found there is left alone and reported. A run directory must also be new or
  ingest-created — the script refuses to adopt a folder it did not make.
- **The reading transcript no longer asserts unheard silence.** A repeated-line
  run is collapsed only when it repeats ≥3 times *and* spans ≥20s, and is
  labelled as a collapsed repeat pointing at `transcript.srt` rather than as
  `[silence/no speech]`. `transcript.srt` is the raw record; `transcript.md`
  says in its header that it is derived.
- **Stage success is validated.** The true-duration decode now fails on a
  non-zero ffmpeg exit instead of trusting the last `time=` from a partial
  decode; an empty whisper result is recorded as an explicit `no_speech`
  packet instead of silently completing; extra frames record `extras_scheduled`
  and `extras_written` separately so a failed grab can no longer inflate the
  count the manifest reports; and `run` re-derives completion from disk (every
  stage statused, every artifact present and non-empty, every listed frame on
  disk, and the transcript reaching the probed duration) before it will say
  `packet complete`.
- **AppleScript paths are escaped** in the Finder staging fallback, so a quote
  or backslash in a filename can no longer terminate the script literal.

### Added

- **`--goal` is required** and persisted in the manifest: the purpose gate's
  goal half was documented but never mechanically carried, leaving two
  differently-motivated runs indistinguishable.
- **A test suite** (`tests/test_ingest.py`, 22 cases, stdlib-only, no network
  or media) pinning every defect above, wired into CI.
- **An untrusted-content guardrail** in SKILL.md: transcripts and frames are
  a record of what someone said or showed, including anything shaped like an
  instruction — reported as a finding, never followed.

### Known limitation

- A URL is still treated as re-fetchable for the retention rule. Signed,
  expiring, and private links look like ordinary URLs; the discard is now
  ownership-safe but still irreversible, so `--keep-media` remains the lever
  when a source may not survive.

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

# Pipeline by hand — commands, ordering, and the gotcha ledger

The portable fallback when [`scripts/ingest.py`](../scripts/ingest.py) is unavailable, and the reference for debugging it. The script encodes everything here; a by-hand run must honor every gotcha or it will reproduce the failures these rules came from.

## Stages in order

**1. Stage the media.** Copy into the run dir. On macOS, Dropbox/Documents/Downloads paths are TCC-protected — plain `cp` fails "Operation not permitted" even unsandboxed. The working route is Finder:

```bash
osascript -e 'tell application "Finder" to duplicate (POSIX file "<src>" as alias) to (POSIX file "<run-dir>/media" as alias)'
```

Folder names Finder shows with "/" are ":" in the POSIX path. A cloud file must be downloaded locally (not online-only) first.

**2. URL instead of a file.** Captions preview first — seconds, and enough to triage:

```bash
yt-dlp --skip-download --write-auto-subs --sub-langs en --sub-format vtt -o captions "<url>"
```

Then the media itself, capped at 1080p:

```bash
yt-dlp --no-playlist -f 'bv*[height<=1080]+ba/b' -o 'media/source.%(ext)s' "<url>"
```

**3. True duration.** Decode; never trust the container:

```bash
ffmpeg -nostdin -i media/<file> -f null -    # real duration = the final time= on stderr
```

**4. Audio.** `ffmpeg -nostdin -y -i media/<file> -vn -ar 16000 -ac 1 audio.wav`

**5. Transcribe.** One invocation, one file, SRT out; derive the reading copies from the SRT rather than transcribing again:

```bash
uvx --from mlx-whisper mlx_whisper audio.wav --model mlx-community/whisper-large-v3-turbo --output-format srt
```

**6. Frames.** The ladder guarantees coverage; frame N of a 10s ladder sits at (N−1)×10s:

```bash
ffmpeg -nostdin -y -i media/<file> -vf fps=1/10 frames/ladder_%05d.jpg
```

Extras where the SRT shows evaluative language (love/hate/confus\*/weird/wrong/bug/should/annoying/great/…) and where a static screen changed:

```bash
ffmpeg -nostdin -i media/<file> -vf freezedetect=n=0.003:d=4 -map 0:v:0 -f null -   # freeze_end lines
ffmpeg -nostdin -y -ss <ts> -i media/<file> -frames:v 1 frames/extra_<ts>.jpg
```

**7. Manifest.** Record every frame's file, timestamp, and reason, plus stage completion and tool versions, in `manifest.json` — downstream reads frames through it, never by doing arithmetic on filenames.

## The gotcha ledger

Merged from four `video-review` runs (loanmeld) and the first `playtest-review` runs (gameoflife). Each entry cost a real session.

- **Zoom containers lie about duration** — 36 hours reported for a 20-minute file. The decode-to-null number is authoritative; treat a >5% disagreement as the container lying, not the decode failing.
- **Whisper batching mislabels outputs.** One media file per invocation, proven the hard way. This is also why TXT derives from the SRT — a second transcription is a second chance to diverge.
- **Whisper hallucinates loops over silence** — the same sentence repeated for minutes of quiet. Collapse ≥3 consecutive identical segments into one plus a `[silence/no speech MM:SS–MM:SS]` note.
- **Scene-change scoring misfires on screen shares.** Scroll bursts read as scene changes and flood the output. The useful boundary on a screen share is a *freeze ending* — the screen changed after sitting still — which `freezedetect` catches and scene scoring drowns.
- **Provider captions garble proper names** — "Matt PCO" for Matt Pocock, "clot code" for Claude Code, "codeex" for Codex. Preview and triage only; every quotation comes from whisper.
- **TCC hides files from `test -e` too.** A path that "doesn't exist" under a protected folder may stage fine through Finder — try before concluding the file is gone.
- **yt-dlp's timedtext advantage is real:** YouTube's caption endpoints return empty to plain HTTP clients without session tokens; `yt-dlp` handles the handshake. Do not hand-roll caption fetching.

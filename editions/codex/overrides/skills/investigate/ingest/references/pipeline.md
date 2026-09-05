# Pipeline by hand: commands, ordering, and the gotcha ledger

The portable fallback when [`scripts/ingest.py`](../scripts/ingest.py) is unavailable, and the reference for debugging it. The script encodes everything here; a by-hand run must honor every gotcha or it will reproduce the failures these rules came from.

## Stages in order

**1. Stage the media.** Copy into the run dir. On macOS, Dropbox/Documents/Downloads paths are TCC-protected: plain `cp` fails "Operation not permitted" even unsandboxed. The working route is Finder:

```bash
osascript -e 'tell application "Finder" to duplicate (POSIX file "<src>" as alias) to (POSIX file "<run-dir>/media" as alias)'
```

Folder names Finder shows with "/" are ":" in the POSIX path. A cloud file must be downloaded locally (not online-only) first.

**2. URL instead of a file.** Captions preview first, in seconds and enough to triage:

```bash
yt-dlp --skip-download --write-auto-subs --sub-langs en --sub-format vtt -o captions "<url>"
```

Then the media itself, capped at 1080p:

```bash
yt-dlp --no-playlist -f 'bv*[height<=1080]+ba/b' -o 'media/source.%(ext)s' "<url>"
```

**3. True duration.** Decode; never trust the container:

```bash
ffmpeg -nostdin -i media/<file> -f null - ; echo "exit=$?"   # duration = final time= on stderr
```

**Check that exit code.** A truncated file still prints timestamps up to the point it broke, so a non-zero exit with a plausible-looking `time=` is exactly how a corrupt recording becomes a confident wrong duration that every later stage inherits. Non-zero means stop, not "use the last number".

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

**7. Manifest.** Record every frame's file, timestamp, and reason, plus stage completion and tool versions, in `manifest.json`; downstream reads frames through it, never by doing arithmetic on filenames.

**8. Validate before calling it complete.** Walk the manifest: every stage has a status, every artifact it lists exists and is non-empty, every frame it lists is on disk, and the transcript's last timestamp reaches the probed duration. A failure here is a failed run, not a caveat.

## The packet contract by hand

The script enforces these; a by-hand run has to enforce them itself, or the packet it produces is not the same artifact.

**Claim the directory before writing anything.** Use a new directory, or one you created for this purpose earlier. Drop a `.ingest-run` marker in it. Never point a run at a directory holding anything else: step 9 deletes files inside it.

**Write the purpose and the identity first.** Before staging a byte:

```json
{
  "input": "<path or URL>",
  "intent": "<call|playtest|demo|memo|triage|reference>",
  "goal": "<why, in the user's own words — verbatim>",
  "identity": {"input": "…", "intent": "…", "ladder_s": 10, "frames": true,
               "whisper_model": "mlx-community/whisper-large-v3-turbo",
               "source_size": 0, "source_mtime_ns": 0},
  "stages": {}, "frames": []
}
```

**One packet, one source.** Before reusing a directory, compare its recorded `identity` with this run's. Any difference (a different URL, an edited local file, a changed ladder or frame policy) means **stop and use a fresh directory**. Reusing it mixes two sources' evidence under one label, which is the failure this contract exists to prevent.

**A stage is complete when it says so.** Each entry records a status and what it produced:

```json
"transcribe": {"status": "ok", "artifacts": ["transcript.srt", "transcript.txt",
               "transcript.md"], "segments": 101, "at": "2026-08-07T09:14:02"}
```

Use `"status": "skipped"` with a reason for a stage you deliberately did not run (frames on a `memo`, say). "No artifacts" never means "finished" on its own: an empty list plus no status is an unfinished stage, and re-running must redo it.

**9. Retention deletes by ledger.** When the source is re-fetchable and you are discarding media, delete exactly the paths the manifest recorded under `fetch`/`stage`/`audio`, never the `media/` directory wholesale. Remove the directory only if it ends up empty; anything else in there was not yours. Remember a URL is not a promise: signed, expiring, and private links look identical to durable ones, so keep the media whenever the source might not survive.

## The gotcha ledger

Technical lessons from media-review pipelines, with recovery procedures that can be checked against the current input.

- **Zoom containers lie about duration**: 36 hours reported for a 20-minute file. The decode-to-null number is authoritative; treat a >5% disagreement as the container lying, not the decode failing.
- **Whisper batching mislabels outputs.** One media file per invocation, proven the hard way. This is also why TXT derives from the SRT: a second transcription is a second chance to diverge.
- **Whisper hallucinates loops over silence**: the same sentence repeated for minutes of quiet. Collapse such a run **only in the derived reading copy**, and only when it both repeats ≥3 times and spans ≥20s: three quick "yes"es are speech, the same line held for half a minute is the model looping. Label it as a collapsed repeat pointing at the SRT, never as `[silence]`: the audio was never checked, and asserting silence puts a claim in the transcript that nothing verified. `transcript.srt` keeps the raw output and is the record for exact wording.
- **"Silence" under a wedge may be conversation.** A collapsed identical-line run (one line, "uh uh…" or "!", held for minutes, sometimes strewn with zero-length empty cues) can cover substantive speech. The script auto-recovers: any identical-line run ≥15s is re-cut from `audio.wav` with `-af "highpass=f=80,lowpass=f=8000,loudnorm=I=-14:TP=-1.5"`, re-transcribed with `--condition-on-previous-text False`, and spliced back at absolute timestamps (raw output kept as `transcript.orig.srt`; spans in the manifest under `recovered_spans`). By hand, do the same for any run of two or more identical non-empty cues spanning ≥15s in `transcript.srt`, treating zero-length empty cues as transparent (they neither break a run nor end it). That net is wider than the reading copy's collapse rule (≥3 repeats over ≥20s), so check the SRT itself, and never trust the "likely silence" label unverified.
- **Scene-change scoring misfires on screen shares.** Scroll bursts read as scene changes and flood the output. The useful boundary on a screen share is a *freeze ending*, the screen changed after sitting still, which `freezedetect` catches and scene scoring drowns.
- **Provider captions garble proper names**: "Matt PCO" for Matt Pocock, "clot code" for Claude Code, "codeex" for Codex. Preview and triage only; every quotation comes from whisper.
- **TCC hides files from `test -e` too.** A path that "doesn't exist" under a protected folder may stage fine through Finder; try before concluding the file is gone.
- **yt-dlp's timedtext advantage is real:** YouTube's caption endpoints return empty to plain HTTP clients without session tokens; `yt-dlp` handles the handshake. Do not hand-roll caption fetching.

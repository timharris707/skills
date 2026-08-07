#!/usr/bin/env python3
"""ingest.py — the mechanical half of the ingest skill.

Turns a media file or URL into an evidence packet: authoritative transcript,
timestamped frames with a manifest, true duration, and (for URLs) an instant
caption preview. Python 3 standard library only; shells out to ffmpeg/ffprobe,
yt-dlp, and uvx (mlx-whisper).

Stages are resumable, but resume is bound to IDENTITY: the run's input,
intent, and processing options are fingerprinted, and a re-run whose
fingerprint differs is refused rather than allowed to mix two sources'
evidence in one packet. A 90-minute video that fails at transcription never
re-downloads; a *different* video pointed at the same --out never inherits
the first one's transcript.

Hard-won rules encoded here so no agent re-derives them:
  * Container duration lies (Zoom reports 36h for a 20-min file) — the real
    number comes from decoding the stream, never from metadata. A decode
    that exits non-zero is a failure, not a duration.
  * Whisper runs once per media file, on one file per invocation. Batching
    mislabels outputs. One transcription produces the SRT; TXT is derived
    from it rather than transcribed a second time.
  * Whisper hallucinates loops over silence — long runs of identical
    segments are collapsed in the DERIVED reading copy only, labelled as
    collapsed repeats (never asserted as silence). transcript.srt keeps the
    raw model output and is the record for exact wording.
  * Scene-change scoring misfires on screen shares (scroll bursts). Coverage
    comes from a fixed 10s ladder; extras come from transcript signals and
    freeze-boundary detection, not scene scores.
  * macOS TCC blocks plain reads of Dropbox/Documents/Downloads paths even
    unsandboxed — staging falls back to Finder duplication via AppleScript.
  * Provider captions are a preview, never the record: they garble names
    ("Matt PCO" for Matt Pocock, "clot code" for Claude Code).

Usage:
  ingest.py doctor
  ingest.py preview --url URL --out DIR
  ingest.py run --input PATH_OR_URL --intent INTENT --goal "why" --out DIR
                [--no-frames] [--keep-media] [--ladder SECONDS]

Exit codes: 0 ok · 1 stage failed · 2 bad arguments · 3 missing tools
             4 identity mismatch (refused to mix sources in one packet)
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

SCRIPT_VERSION = 2
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
INTENTS = ("call", "playtest", "demo", "memo", "triage", "reference")
# memo is audio-thinking aloud: frames are noise. Everything else gets them
# when the media has a video stream at all.
FRAMELESS_INTENTS = {"memo"}
# Words in the SRT that mark a moment worth a dedicated frame — evaluative
# language means the speaker is reacting to what is on screen.
SIGNAL_RE = re.compile(
    r"\b(love|hate|confus\w*|weird|wrong|bug|broken|should|annoy\w*|great|"
    r"terrible|awesome|issue|problem|fix\w*|slow|stuck|fail\w*|error)\b",
    re.IGNORECASE,
)
MAX_EXTRA_FRAMES = 240
# A repeated-line run is only treated as a transcription loop when it also
# spans real time. Three quick "yes"es are speech; the same line held for
# half a minute is the model looping over silence.
MIN_LOOP_REPEATS = 3
MIN_LOOP_SPAN_S = 20
EXIT_IDENTITY_MISMATCH = 4


def log(msg: str) -> None:
    print(f"[ingest] {msg}", flush=True)


def die(msg: str, code: int = 1) -> "NoReturn":  # noqa: F821
    print(f"[ingest] ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def run_cmd(argv, timeout=None, **kw):
    """Run a subprocess, capturing text output; raise on unexpected failure."""
    return subprocess.run(
        argv, capture_output=True, text=True, timeout=timeout, **kw
    )


# ---------------------------------------------------------------- doctor ---

TOOLS = {
    "ffmpeg": "brew install ffmpeg",
    "ffprobe": "brew install ffmpeg",
    "yt-dlp": "brew install yt-dlp",
    "uvx": "brew install uv",
}


def doctor(quiet: bool = False) -> bool:
    """Check every external tool; print an install command for what's absent."""
    ok = True
    for tool, fix in TOOLS.items():
        path = shutil.which(tool)
        if path:
            if not quiet:
                log(f"ok       {tool} -> {path}")
        else:
            ok = False
            log(f"MISSING  {tool} — install with: {fix}")
    if not quiet:
        cached = Path.home() / ".cache/huggingface/hub"
        hit = list(cached.glob(f"models--{WHISPER_MODEL.replace('/', '--')}*"))
        log(
            "ok       whisper model cached"
            if hit
            else "note     whisper model not cached — first run downloads it (~1.6 GB)"
        )
    return ok


# -------------------------------------------------------------- manifest ---


class Manifest:
    """Run state: stage completion, artifacts, provenance. One JSON file.

    Completion is DECLARED, never inferred: a stage carries an explicit
    status (ok | skipped) plus the identity fingerprint it ran under. An
    empty artifact list therefore means "this stage produced no files",
    not "this stage is vacuously finished".
    """

    def __init__(self, out_dir: Path, identity_hash: str | None = None):
        self.path = out_dir / "manifest.json"
        self.identity_hash = identity_hash
        self.data = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                # A torn write from a crashed run: keep the file for forensics,
                # start clean so the run can proceed.
                self.path.rename(self.path.with_suffix(".json.corrupt"))
        self.data.setdefault("stages", {})
        self.data.setdefault("frames", [])

    def save(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.data, indent=2))
        tmp.replace(self.path)

    def done(self, stage: str) -> bool:
        rec = self.data["stages"].get(stage)
        if not rec:
            return False
        # Legacy records (written before stage status existed) are never
        # reused — an unlabelled stage cannot prove what it ran against.
        if rec.get("status") not in ("ok", "skipped"):
            return False
        # A stage may only be reused by a run with the same identity.
        if self.identity_hash and rec.get("identity") != self.identity_hash:
            return False
        return all(Path(p).exists() for p in rec.get("artifacts", []))

    def artifacts(self, stage: str) -> list:
        rec = self.data["stages"].get(stage) or {}
        return [Path(p) for p in rec.get("artifacts", [])]

    def finish(self, stage: str, artifacts=(), status: str = "ok", **extra) -> None:
        self.data["stages"][stage] = {
            "status": status,
            "identity": self.identity_hash,
            "artifacts": [str(a) for a in artifacts],
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **extra,
        }
        self.save()


# -------------------------------------------------------------- identity ---


def run_identity(args) -> dict:
    """What this packet is evidence OF, plus how it was processed. Any change
    here invalidates every stage — the alternative is a packet whose transcript
    and frames came from a different source than its manifest claims."""
    ident = {
        "input": args.input,
        "intent": args.intent,
        "ladder_s": args.ladder,
        "frames": not args.no_frames,
        "whisper_model": WHISPER_MODEL,
        "script_version": SCRIPT_VERSION,
    }
    if not is_url(args.input):
        # Local files can be edited or swapped under a stable name; size and
        # mtime catch that without hashing gigabytes. A TCC-hidden file simply
        # contributes no stat fields — staging still verifies it downstream.
        try:
            st = Path(args.input).expanduser().stat()
            ident["source_size"] = st.st_size
            ident["source_mtime_ns"] = st.st_mtime_ns
        except OSError:
            pass
    return ident


def identity_hash(ident: dict) -> str:
    blob = json.dumps(ident, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def claim_out_dir(out_dir: Path) -> None:
    """A run directory is tool-owned. Adopting a directory this script did not
    create is refused — retention deletes files inside it later, and a stray
    --out must never put a user's own folder in that path."""
    marker = out_dir / ".ingest-run"
    if out_dir.exists() and any(out_dir.iterdir()) and not marker.exists():
        die(
            f"{out_dir} is not empty and was not created by ingest.\n"
            "Refusing to adopt it: this tool deletes files under its own run "
            "directory. Point --out at a new directory.",
            2,
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        marker.write_text(
            f"created by ingest.py v{SCRIPT_VERSION} at "
            f"{time.strftime('%Y-%m-%dT%H:%M:%S')}\n"
        )


# --------------------------------------------------------------- staging ---


def is_url(s: str) -> bool:
    return urllib.parse.urlparse(s).scheme in ("http", "https")


def applescript_str(p) -> str:
    """Escape a path for interpolation into an AppleScript string literal.
    A quote or backslash in a filename would otherwise end the literal and
    let the rest of the name be read as script."""
    return str(p).replace("\\", "\\\\").replace('"', '\\"')


def stage_local(src: Path, out_dir: Path, manifest: Manifest) -> Path:
    """Copy a local file into the run dir. TCC-protected paths (Dropbox,
    Documents, Downloads) refuse plain reads even unsandboxed; the working
    route is asking Finder to do the copy."""
    if manifest.done("stage"):
        return manifest.artifacts("stage")[0]
    dest = out_dir / "media" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(src, dest)
        manifest.finish("stage", [dest], source=str(src))
        return dest
    except (PermissionError, OSError) as e:
        log(f"plain copy refused ({e.__class__.__name__}) — trying Finder")
    script = (
        'tell application "Finder" to duplicate '
        f'(POSIX file "{applescript_str(src)}" as alias) to '
        f'(POSIX file "{applescript_str(dest.parent)}" as alias) with replacing'
    )
    r = run_cmd(["osascript", "-e", script], timeout=600)
    if r.returncode != 0 or not dest.exists():
        die(
            f"could not stage {src} — plain copy and Finder both failed.\n"
            f"osascript said: {r.stderr.strip()}\n"
            "If this is a cloud path, check the file is downloaded locally "
            "(not online-only), and that the folder name uses ':' where "
            "Finder displays '/'."
        )
    manifest.finish("stage", [dest], source=str(src), via="finder")
    return dest


def fetch_url(url: str, out_dir: Path, manifest: Manifest) -> Path:
    """Download a URL's media via yt-dlp, capped at 1080p to keep it fast."""
    media_dir = out_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    # Reuse only the file this run's manifest actually recorded — never
    # "whatever media file happens to sit in the directory".
    if manifest.done("fetch"):
        return manifest.artifacts("fetch")[0]
    log(f"downloading {url}")
    r = run_cmd(
        [
            "yt-dlp",
            "--no-playlist",
            "-f",
            "bv*[height<=1080]+ba/b[height<=1080]/b",
            "-o",
            str(media_dir / "source.%(ext)s"),
            "--print",
            "after_move:filepath",
            "--no-simulate",
            url,
        ],
        timeout=3600,
    )
    if r.returncode != 0:
        die(f"yt-dlp failed:\n{r.stderr.strip()[-2000:]}")
    path = Path(r.stdout.strip().splitlines()[-1])
    if not path.exists():
        die("yt-dlp reported success but the file is missing")
    manifest.finish("fetch", [path], url=url)
    return path


def captions_preview(url: str, out_dir: Path, manifest: Manifest) -> Path | None:
    """Pull provider auto-captions as a seconds-fast preview. Approximate by
    nature — proper names arrive garbled — so the file says so in line 1."""
    if manifest.done("preview"):
        return Path(manifest.data["stages"]["preview"]["artifacts"][0])
    r = run_cmd(
        [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs",
            "en",
            "--sub-format",
            "vtt",
            "-o",
            str(out_dir / "captions"),
            url,
        ],
        timeout=300,
    )
    vtt = out_dir / "captions.en.vtt"
    if r.returncode != 0 or not vtt.exists():
        log("no provider captions available — skipping preview")
        return None
    lines, seen, ts = [], None, 0
    for ln in vtt.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^(\d\d):(\d\d):(\d\d)\.\d+ -->", ln)
        if m:
            ts = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            continue
        t = re.sub(r"<[^>]+>", "", ln).strip()
        if not t or t.startswith(("WEBVTT", "Kind:", "Language:")) or t == seen:
            continue
        seen = t
        lines.append(f"[{ts // 60}:{ts % 60:02d}] {t}")
    preview = out_dir / "captions-preview.txt"
    preview.write_text(
        "PREVIEW — provider auto-captions, approximate wording (proper names "
        "are unreliable). The whisper transcript is authoritative.\n\n"
        + "\n".join(lines)
    )
    vtt.unlink()
    manifest.finish("preview", [preview])
    log(f"caption preview ready: {preview.name} ({len(lines)} lines)")
    return preview


# ----------------------------------------------------------------- probe ---


def probe(media: Path, out_dir: Path, manifest: Manifest) -> dict:
    """Streams and TRUE duration. Container metadata is recorded but never
    trusted — the authoritative number comes from decoding to null."""
    if manifest.done("probe"):
        return manifest.data["stages"]["probe"]["info"]
    r = run_cmd(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(media),
        ],
        timeout=120,
    )
    if r.returncode != 0:
        die(f"ffprobe failed:\n{r.stderr.strip()}")
    meta = json.loads(r.stdout)
    has_video = any(
        s.get("codec_type") == "video"
        and s.get("disposition", {}).get("attached_pic", 0) == 0
        for s in meta.get("streams", [])
    )
    container_dur = float(meta.get("format", {}).get("duration") or 0)

    log("decoding for true duration (containers lie — Zoom especially)")
    d = run_cmd(
        ["ffmpeg", "-nostdin", "-i", str(media), "-f", "null", "-"],
        timeout=7200,
    )
    # A non-zero decode still prints timestamps up to the point it broke, so
    # trusting the last one would turn a truncated file into a confident wrong
    # duration — and every downstream stage would inherit it.
    if d.returncode != 0:
        die(
            "media did not decode completely — the duration cannot be trusted "
            f"(ffmpeg exit {d.returncode}). The file is likely truncated or "
            f"corrupt.\n{d.stderr.strip()[-1500:]}"
        )
    times = re.findall(r"time=(\d+):(\d\d):(\d\d(?:\.\d+)?)", d.stderr)
    if not times:
        die("could not decode media for duration — file may be corrupt")
    h, m, s = times[-1]
    true_dur = int(h) * 3600 + int(m) * 60 + float(s)
    if container_dur and abs(container_dur - true_dur) > max(5, true_dur * 0.05):
        log(
            f"container claimed {container_dur:.0f}s but the stream decodes to "
            f"{true_dur:.0f}s — using the decoded number"
        )
    info = {
        "true_duration_s": round(true_dur, 2),
        "container_duration_s": round(container_dur, 2),
        "has_video": has_video,
    }
    manifest.finish("probe", [], info=info)
    return info


# ------------------------------------------------------------ transcript ---


def extract_audio(media: Path, out_dir: Path, manifest: Manifest) -> Path:
    wav = out_dir / "audio.wav"
    if manifest.done("audio"):
        return wav
    r = run_cmd(
        [
            "ffmpeg", "-nostdin", "-y", "-i", str(media),
            "-vn", "-ar", "16000", "-ac", "1", str(wav),
        ],
        timeout=3600,
    )
    if r.returncode != 0:
        die(f"audio extraction failed:\n{r.stderr.strip()[-1500:]}")
    manifest.finish("audio", [wav])
    return wav


def srt_to_segments(srt_text: str):
    """Parse SRT into (start_seconds, text) pairs."""
    segs = []
    for block in re.split(r"\n\s*\n", srt_text.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        m = re.search(r"(\d+):(\d\d):(\d\d)[,.](\d+)\s*-->", block)
        if not m:
            continue
        start = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        text = " ".join(
            ln.strip() for ln in lines if "-->" not in ln and not ln.strip().isdigit()
        ).strip()
        if text:
            segs.append((start, text))
    return segs


_SRT_END_RE = re.compile(r"-->\s*(\d+):(\d\d):(\d\d)[,.](\d+)")


def srt_last_end(srt_text: str):
    """Where the transcript STOPS, in seconds — the last cue's END, not its
    start. One long cue covers everything between its two timestamps, so
    measuring coverage from cue starts would report a whole recording as
    uncovered. None when nothing parses."""
    ends = [
        int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000
        for h, m, s, ms in _SRT_END_RE.findall(srt_text)
    ]
    return max(ends) if ends else None


def collapse_repeats(segs):
    """Whisper loops one line over silence. Collapse such a run in the DERIVED
    reading copy — but only when it repeats enough AND spans enough time to be
    a loop rather than real repetition, and label it as a collapsed repeat.
    Asserting "silence" would put a claim in the transcript that the audio was
    never checked for; genuine repeated speech is a normal thing to say."""
    out, i, collapsed = [], 0, 0
    while i < len(segs):
        j = i
        while j + 1 < len(segs) and segs[j + 1][1] == segs[i][1]:
            j += 1
        span = segs[j][0] - segs[i][0]
        if (j - i + 1) >= MIN_LOOP_REPEATS and span >= MIN_LOOP_SPAN_S:
            out.append(segs[i])
            out.append(
                (
                    segs[i + 1][0],
                    f"[same line repeated {j - i + 1}× to "
                    f"{segs[j][0]//60}:{segs[j][0]%60:02d} — collapsed; "
                    f"likely a transcription loop over silence, "
                    f"verify in transcript.srt]",
                )
            )
            collapsed += 1
        else:
            out.extend(segs[i : j + 1])
        i = j + 1
    return out, collapsed


def transcribe(wav: Path, out_dir: Path, manifest: Manifest) -> tuple:
    """One whisper invocation, one file, SRT out; TXT and a timestamped
    reading copy are derived — never transcribed twice."""
    srt = out_dir / "transcript.srt"
    txt = out_dir / "transcript.txt"
    reading = out_dir / "transcript.md"
    if manifest.done("transcribe"):
        return srt, txt, reading
    log(f"transcribing with {WHISPER_MODEL} (minutes, not seconds — patience)")
    r = run_cmd(
        [
            "uvx", "--from", "mlx-whisper", "mlx_whisper", str(wav),
            "--model", WHISPER_MODEL,
            "--output-format", "srt",
            "--output-dir", str(out_dir),
        ],
        timeout=4 * 3600,
    )
    produced = out_dir / (wav.stem + ".srt")
    if r.returncode != 0 or not produced.exists():
        die(f"whisper failed:\n{(r.stderr or r.stdout).strip()[-2000:]}")
    produced.replace(srt)

    raw = srt_to_segments(srt.read_text())
    segs, collapsed = collapse_repeats(raw)
    header = (
        "# Reading copy — DERIVED from transcript.srt (raw whisper output).\n"
        "# transcript.srt is the record for exact wording; repeated-line runs\n"
        "# are collapsed here and marked inline.\n\n"
    )
    if not raw:
        # A silent recording is legitimate; a silently-empty transcript that
        # still reports success is not. Say so in the file and the manifest.
        log("WARNING: whisper returned no speech segments — recording the "
            "packet as no-speech rather than reporting a transcript")
        note = "[no speech detected in this recording]"
        txt.write_text(note + "\n")
        reading.write_text(header + note + "\n")
        manifest.finish(
            "transcribe", [srt, txt, reading], segments=0, no_speech=True
        )
        return srt, txt, reading

    txt.write_text("\n".join(t for _, t in segs))
    reading.write_text(
        header + "\n".join(f"[{ts//60}:{ts%60:02d}] {t}" for ts, t in segs)
    )
    manifest.finish(
        "transcribe",
        [srt, txt, reading],
        segments=len(segs),
        raw_segments=len(raw),
        collapsed_runs=collapsed,
    )
    log(
        f"transcript ready: {len(segs)} segments"
        + (f" ({collapsed} repeated run(s) collapsed)" if collapsed else "")
    )
    return srt, txt, reading


# ---------------------------------------------------------------- frames ---


def freeze_boundaries(media: Path, timeout_s: int):
    """Timestamps where a static screen changed — freeze *ends*. On screen
    shares this is the useful boundary; scene scoring is noise there."""
    r = run_cmd(
        [
            "ffmpeg", "-nostdin", "-i", str(media),
            "-vf", "freezedetect=n=0.003:d=4",
            "-map", "0:v:0", "-f", "null", "-",
        ],
        timeout=timeout_s,
    )
    return [
        float(m)
        for m in re.findall(r"freeze_end:\s*([\d.]+)", r.stderr)
    ]


def extract_frames(media, out_dir, manifest, duration, srt, ladder=10):
    """A fixed ladder guarantees coverage; extras land where the transcript
    reacts and where the screen changed after sitting still."""
    frames_dir = out_dir / "frames"
    if manifest.done("frames"):
        return
    frames_dir.mkdir(exist_ok=True)

    r = run_cmd(
        [
            "ffmpeg", "-nostdin", "-y", "-i", str(media),
            "-vf", f"fps=1/{ladder}",
            str(frames_dir / "ladder_%05d.jpg"),
        ],
        timeout=7200,
    )
    if r.returncode != 0:
        die(f"frame ladder failed:\n{r.stderr.strip()[-1500:]}")
    frames = [
        {
            "file": f"frames/{p.name}",
            "ts": (int(p.stem.split("_")[1]) - 1) * ladder,
            "why": "ladder",
        }
        for p in sorted(frames_dir.glob("ladder_*.jpg"))
    ]

    # Extras: transcript signals + freeze boundaries, deduped against the
    # ladder (skip anything within 2s of an existing frame), capped.
    signal_ts = [
        ts
        for ts, text in srt_to_segments(srt.read_text())
        if SIGNAL_RE.search(text)
    ]
    freeze_ts = freeze_boundaries(media, timeout_s=7200)
    have = sorted(f["ts"] for f in frames)
    extras = []
    for ts, why in [(t, "signal") for t in signal_ts] + [
        (t, "screen-change") for t in freeze_ts
    ]:
        if ts > duration or any(abs(ts - h) < 2 for h in have):
            continue
        have.append(ts)
        extras.append((ts, why))
    if len(extras) > MAX_EXTRA_FRAMES:
        log(f"capping extras at {MAX_EXTRA_FRAMES} (had {len(extras)})")
        extras = extras[:MAX_EXTRA_FRAMES]
    written = 0
    for ts, why in extras:
        name = f"extra_{int(ts):06d}.jpg"
        r = run_cmd(
            [
                "ffmpeg", "-nostdin", "-y", "-ss", str(ts), "-i", str(media),
                "-frames:v", "1", str(frames_dir / name),
            ],
            timeout=120,
        )
        # Count what landed on disk, not what was scheduled: a failed grab
        # that still inflates the manifest makes coverage look better than
        # it is, and the manifest is what the reader trusts.
        if r.returncode == 0 and (frames_dir / name).exists():
            frames.append({"file": f"frames/{name}", "ts": ts, "why": why})
            written += 1
        else:
            log(f"note: could not grab extra frame at {ts:.0f}s — skipped")

    frames.sort(key=lambda f: f["ts"])
    manifest.data["frames"] = frames
    manifest.finish(
        "frames",
        [frames_dir / Path(f["file"]).name for f in frames],
        ladder_s=ladder,
        extras_scheduled=len(extras),
        extras_written=written,
    )
    log(f"frames ready: {len(frames)} total ({written} extras)")


# ------------------------------------------------------------------- run ---


def tool_versions() -> dict:
    out = {}
    for tool, argv in {
        "ffmpeg": ["ffmpeg", "-version"],
        "yt-dlp": ["yt-dlp", "--version"],
    }.items():
        try:
            out[tool] = run_cmd(argv, timeout=15).stdout.splitlines()[0]
        except Exception:
            out[tool] = "unknown"
    out["whisper_model"] = WHISPER_MODEL
    return out


def discard_media(out_dir: Path, manifest: Manifest) -> None:
    """Delete only the media files THIS run recorded creating. The run
    directory belongs to the tool, but a blanket rmtree of media/ would still
    take anything else that landed there — deletion is by ledger, not by
    directory name, and the ledger is the only list consulted (the extracted
    wav included: extract_audio records it under the `audio` stage).

    The ledger is a file on disk, so it is an input, not a fact: every path is
    resolved and refused unless it lands inside this packet. A hand-edited or
    corrupted manifest must not be able to point deletion at the rest of the
    filesystem."""
    packet_root = out_dir.resolve()
    removed = 0
    for stage in ("fetch", "stage", "audio"):
        for path in manifest.artifacts(stage):
            try:
                resolved = path.resolve()
                resolved.relative_to(packet_root)
            except (OSError, ValueError):
                log(f"note: manifest lists {path} outside the packet — not deleting")
                continue
            if resolved.is_file():
                resolved.unlink()
                removed += 1
    media_dir = out_dir / "media"
    if media_dir.is_dir() and not any(media_dir.iterdir()):
        media_dir.rmdir()
    elif media_dir.is_dir():
        log(f"note: {media_dir} still holds files this run did not create — left alone")
    manifest.data["media_discarded"] = True
    manifest.save()
    log(f"re-fetchable source: {removed} media file(s) discarded "
        "(transcript + frames kept)")


def validate_packet(manifest: Manifest, out_dir: Path) -> list:
    """Re-derive completion instead of trusting the control flow that produced
    it. Returns the problems found; an empty list is what 'complete' means."""
    problems = []
    discarded = manifest.data.get("media_discarded")
    for stage, rec in manifest.data["stages"].items():
        if rec.get("status") not in ("ok", "skipped"):
            problems.append(f"{stage}: no recorded status")
            continue
        if discarded and stage in ("fetch", "stage", "audio"):
            continue          # deliberately removed by the retention rule
        for path in (Path(p) for p in rec.get("artifacts", [])):
            if not path.exists():
                problems.append(f"{stage}: missing artifact {path.name}")
                continue
            if path.stat().st_size == 0:
                # A genuinely silent recording yields an empty raw SRT, and the
                # stage says so. Every other empty artifact is a defect.
                if rec.get("no_speech") and path.suffix == ".srt":
                    continue
                problems.append(f"{stage}: empty artifact {path.name}")
    for frame in manifest.data.get("frames", []):
        if not (out_dir / frame["file"]).exists():
            problems.append(f"frames: manifest lists missing {frame['file']}")
            break
    problems += transcript_coverage_problems(manifest)
    return problems


def transcript_coverage_problems(manifest: Manifest) -> list:
    """The documented Done-when says the transcript must reach the probed true
    duration. Checking it here is the difference between a criterion a reader is
    asked to eyeball and one the run actually enforces — a transcription that
    stops a third of the way in otherwise reports `packet complete`.

    Trailing silence is legitimate, so the gap is only a problem when it is
    large AND unexplained; a declared no-speech packet is exempt outright.
    """
    tr = manifest.data["stages"].get("transcribe")
    probe_rec = manifest.data["stages"].get("probe")
    if not tr or not probe_rec or tr.get("status") != "ok":
        return []
    if tr.get("no_speech"):
        return []                      # declared, not silently short
    duration = (probe_rec.get("info") or {}).get("true_duration_s") or 0
    srt = next((Path(p) for p in tr.get("artifacts", []) if str(p).endswith(".srt")), None)
    if not duration or srt is None or not srt.exists():
        return []
    text = srt.read_text(errors="replace")
    last = srt_last_end(text)
    if last is None:
        if text.strip():
            # Bytes but no cues: the artifact check sees a non-empty file and
            # passes it, so this is the only place the garbage is caught.
            return [f"transcribe: {srt.name} has no parseable cues"]
        return []                      # empty: already caught as an empty artifact
    gap = duration - last
    # A tail of quiet is normal; losing a quarter of a recording is not.
    if gap > max(60, duration * 0.25):
        return [
            f"transcribe: transcript ends at {last:.0f}s of {duration:.0f}s "
            f"({gap:.0f}s uncovered) — re-run transcription, or record the "
            f"packet as no_speech if the tail is genuinely silent"
        ]
    return []


def cmd_run(args) -> None:
    if not doctor(quiet=True):
        die("missing tools — run `ingest.py doctor` for install commands", 3)
    out_dir = Path(args.out).expanduser()
    claim_out_dir(out_dir)

    ident = run_identity(args)
    ihash = identity_hash(ident)
    manifest = Manifest(out_dir, identity_hash=ihash)
    prior = manifest.data.get("identity_hash")
    if prior and prior != ihash:
        # The packet already stands for something else. Overwriting its
        # identity while its stages survive is how one packet ends up
        # presenting source A's transcript as evidence about source B.
        was = manifest.data.get("identity", {})
        changed = [
            k for k in set(was) | set(ident) if was.get(k) != ident.get(k)
        ]
        die(
            f"{out_dir} is already the packet for a different run "
            f"(changed: {', '.join(sorted(changed))}).\n"
            "Refusing to reuse it — the finished stages belong to the other "
            "source, and mixing them would make this packet lie about where "
            "its evidence came from. Use a fresh --out.",
            EXIT_IDENTITY_MISMATCH,
        )

    manifest.data.update(
        {
            "input": args.input,
            "intent": args.intent,
            "goal": args.goal,
            "identity": ident,
            "identity_hash": ihash,
            "refetchable": is_url(args.input),
            "tools": manifest.data.get("tools") or tool_versions(),
        }
    )
    manifest.save()

    if is_url(args.input):
        captions_preview(args.input, out_dir, manifest)
        media = fetch_url(args.input, out_dir, manifest)
    else:
        src = Path(args.input).expanduser()
        if not src.exists():
            # TCC can hide a file from exists() too — let staging try anyway
            log(f"note: {src} not directly visible; attempting staged copy")
        media = stage_local(src, out_dir, manifest)

    info = probe(media, out_dir, manifest)
    wav = extract_audio(media, out_dir, manifest)
    srt, _txt, reading = transcribe(wav, out_dir, manifest)

    want_frames = (
        info["has_video"]
        and args.intent not in FRAMELESS_INTENTS
        and not args.no_frames
    )
    if want_frames:
        extract_frames(
            media, out_dir, manifest, info["true_duration_s"], srt,
            ladder=args.ladder,
        )
    else:
        manifest.finish("frames", [], status="skipped",
                        reason="no video stream" if not info["has_video"]
                        else f"intent {args.intent}" if args.intent in FRAMELESS_INTENTS
                        else "--no-frames")

    # Retention: what can be re-fetched is not archived. A local recording
    # is irreplaceable, so its staged copy stays. Note that a URL is not a
    # guarantee of re-fetchability (signed, expiring, and private links all
    # look the same) — pass --keep-media when the source may not survive.
    if manifest.data["refetchable"] and not args.keep_media:
        discard_media(out_dir, manifest)

    problems = validate_packet(manifest, out_dir)
    if problems:
        manifest.finish("run", [manifest.path], status="ok", problems=problems)
        die(
            "packet INCOMPLETE — refusing to report success:\n  "
            + "\n  ".join(problems)
        )
    manifest.finish("run", [manifest.path])
    log(f"packet complete: {out_dir}")
    log(f"  read first : {reading.name}")
    log(f"  then frames: manifest.json maps every frame to its timestamp")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="check external tools; print fixes")

    pv = sub.add_parser("preview", help="provider captions only, seconds-fast")
    pv.add_argument("--url", required=True)
    pv.add_argument("--out", required=True)

    rn = sub.add_parser("run", help="full pipeline, resumable")
    rn.add_argument("--input", required=True, help="local path or URL")
    rn.add_argument("--intent", required=True, choices=INTENTS)
    rn.add_argument("--goal", required=True,
                    help="why this media is being processed, in the user's own "
                         "words — recorded in the manifest so the packet says "
                         "what it was made to answer")
    rn.add_argument("--out", required=True, help="run directory (the packet)")
    rn.add_argument("--no-frames", action="store_true")
    rn.add_argument("--keep-media", action="store_true",
                    help="keep downloaded media even for re-fetchable URLs")
    rn.add_argument("--ladder", type=int, default=10,
                    help="ladder interval in seconds (default 10)")

    args = p.parse_args(argv)
    if args.cmd == "doctor":
        sys.exit(0 if doctor() else 3)
    elif args.cmd == "preview":
        out_dir = Path(args.out).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        got = captions_preview(args.url, out_dir, Manifest(out_dir))
        sys.exit(0 if got else 1)
    elif args.cmd == "run":
        cmd_run(args)


if __name__ == "__main__":
    main()

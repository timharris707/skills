#!/usr/bin/env python3
"""ingest.py — the mechanical half of the ingest skill.

Turns a media file or URL into an evidence packet: authoritative transcript,
timestamped frames with a manifest, true duration, and (for URLs) an instant
caption preview. Python 3 standard library only; shells out to ffmpeg/ffprobe,
yt-dlp, and uvx (mlx-whisper).

Stages are resumable: each writes its output and records completion in
manifest.json, and a re-run with the same --out skips what already finished.
A 90-minute video that fails at transcription never re-downloads.

Hard-won rules encoded here so no agent re-derives them:
  * Container duration lies (Zoom reports 36h for a 20-min file) — the real
    number comes from decoding the stream, never from metadata.
  * Whisper runs once per media file, on one file per invocation. Batching
    mislabels outputs. One transcription produces the SRT; TXT is derived
    from it rather than transcribed a second time.
  * Whisper hallucinates loops over silence — repeated identical segments
    are collapsed into a single [silence/no speech] note.
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
  ingest.py run --input PATH_OR_URL --intent INTENT --out DIR
                [--no-frames] [--keep-media] [--ladder SECONDS]

Exit codes: 0 ok · 1 stage failed · 2 bad arguments · 3 missing tools
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

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
    """Run state: stage completion, artifacts, provenance. One JSON file."""

    def __init__(self, out_dir: Path):
        self.path = out_dir / "manifest.json"
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
        # A stage is only done if every artifact it recorded still exists.
        return all(Path(p).exists() for p in rec.get("artifacts", []))

    def finish(self, stage: str, artifacts=(), **extra) -> None:
        self.data["stages"][stage] = {
            "artifacts": [str(a) for a in artifacts],
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            **extra,
        }
        self.save()


# --------------------------------------------------------------- staging ---


def is_url(s: str) -> bool:
    return urllib.parse.urlparse(s).scheme in ("http", "https")


def stage_local(src: Path, out_dir: Path) -> Path:
    """Copy a local file into the run dir. TCC-protected paths (Dropbox,
    Documents, Downloads) refuse plain reads even unsandboxed; the working
    route is asking Finder to do the copy."""
    dest = out_dir / "media" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    try:
        shutil.copy2(src, dest)
        return dest
    except (PermissionError, OSError) as e:
        log(f"plain copy refused ({e.__class__.__name__}) — trying Finder")
    script = (
        'tell application "Finder" to duplicate '
        f'(POSIX file "{src}" as alias) to '
        f'(POSIX file "{dest.parent}" as alias) with replacing'
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
    return dest


def fetch_url(url: str, out_dir: Path, manifest: Manifest) -> Path:
    """Download a URL's media via yt-dlp, capped at 1080p to keep it fast."""
    media_dir = out_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    existing = [
        p
        for p in media_dir.iterdir()
        if p.suffix in (".mp4", ".mkv", ".webm", ".m4a", ".mp3", ".wav", ".opus")
    ]
    if manifest.done("fetch") and existing:
        return existing[0]
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
    manifest.data["stages"]["probe"] = {"artifacts": [], "info": info}
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


def collapse_hallucinations(segs):
    """Whisper loops the same line over silence. Three or more consecutive
    identical texts collapse into one segment plus a silence note."""
    out, i = [], 0
    while i < len(segs):
        j = i
        while j + 1 < len(segs) and segs[j + 1][1] == segs[i][1]:
            j += 1
        if j - i >= 2:
            out.append(segs[i])
            out.append(
                (
                    segs[i + 1][0],
                    f"[silence/no speech {segs[i+1][0]//60}:{segs[i+1][0]%60:02d}"
                    f"–{segs[j][0]//60}:{segs[j][0]%60:02d}]",
                )
            )
        else:
            out.extend(segs[i : j + 1])
        i = j + 1
    return out


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

    segs = collapse_hallucinations(srt_to_segments(srt.read_text()))
    txt.write_text("\n".join(t for _, t in segs))
    reading.write_text(
        "\n".join(f"[{ts//60}:{ts%60:02d}] {t}" for ts, t in segs)
    )
    manifest.finish("transcribe", [srt, txt, reading], segments=len(segs))
    log(f"transcript ready: {len(segs)} segments")
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
    for ts, why in extras:
        name = f"extra_{int(ts):06d}.jpg"
        run_cmd(
            [
                "ffmpeg", "-nostdin", "-y", "-ss", str(ts), "-i", str(media),
                "-frames:v", "1", str(frames_dir / name),
            ],
            timeout=120,
        )
        if (frames_dir / name).exists():
            frames.append({"file": f"frames/{name}", "ts": ts, "why": why})

    frames.sort(key=lambda f: f["ts"])
    manifest.data["frames"] = frames
    manifest.finish(
        "frames",
        [frames_dir / Path(f["file"]).name for f in frames],
        ladder_s=ladder,
        extras=len(extras),
    )
    log(f"frames ready: {len(frames)} total ({len(extras)} extras)")


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


def cmd_run(args) -> None:
    if not doctor(quiet=True):
        die("missing tools — run `ingest.py doctor` for install commands", 3)
    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(out_dir)
    manifest.data.update(
        {
            "input": args.input,
            "intent": args.intent,
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
        media = stage_local(src, out_dir)

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
        manifest.finish("frames", [], skipped=True)

    # Retention: what can be re-fetched is not archived. A local recording
    # is irreplaceable, so its staged copy stays.
    if manifest.data["refetchable"] and not args.keep_media:
        media_dir = out_dir / "media"
        if media_dir.exists():
            shutil.rmtree(media_dir)
        wav.unlink(missing_ok=True)
        log("re-fetchable source: media discarded (transcript + frames kept)")
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

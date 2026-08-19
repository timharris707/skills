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
  ingest.py link --out DIR --item OWNER/REPO#N [--item ...]
  ingest.py sweep --home DIR [--check-cmd CMD] [--delete PACKET_DIR ...]

Exit codes: 0 ok · 1 stage failed, or sweep --delete refused (unresolved)
             2 bad arguments, or a directory ingest does not own
             3 missing tools
             4 identity mismatch (refused to mix sources in one packet)
             5 deletion incomplete — foreign or undeletable content remains;
               the packet directory, marker, and manifest are KEPT so it
               stays sweepable rather than orphaned
"""

import argparse
import hashlib
import json
import re
import shlex
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
# Loop-wedge auto-recovery. Twice on real team calls (2026-08-17/18) whisper
# wedged over quiet-but-substantive spans — identical-line runs the reading
# copy collapses as "likely silence" that actually held conversation. Any
# identical-line run of ≥2 cues covering this much wall time is re-transcribed
# with audio normalization and conditioning off, which recovered both real
# cases; losing more than 15s of a call is unacceptable (Tim, 2026-08-18).
RECOVERY_MIN_SPAN_S = 15
RECOVERY_PAD_S = 3
# Band-limit to speech and normalize loudness: quiet spans stop reading to the
# model as "keep emitting the previous line".
RECOVERY_AUDIO_FILTER = "highpass=f=80,lowpass=f=8000,loudnorm=I=-14:TP=-1.5"
EXIT_IDENTITY_MISMATCH = 4
EXIT_DELETE_INCOMPLETE = 5
RUN_MARKER = ".ingest-run"
# A GitHub-shaped derived-item id: owner/repo#number. Anything else belongs
# to another tracker and resolves only through a binding-doc command — the
# sweep never guesses what an id it cannot read means. Segments of '.' or
# '..' are refused: they would ride into the gh API path as traversal.
_ID_SEG = r"(?!\.\.?[/#])[\w.-]+"
GH_ITEM_RE = re.compile(rf"^({_ID_SEG}/{_ID_SEG})#(\d+)$")
# What link will record at all: ids are identifiers, not text. No whitespace,
# no control characters, no shell metacharacters — an id that needs them is
# an id that will later be handed to a resolution command and a log line.
ITEM_ID_OK_RE = re.compile(r"^[A-Za-z0-9._/#-]+$")


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
    "gh": "brew install gh",   # the sweep's GitHub-first resolution checks
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
        self.data.setdefault("derived_items", [])

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
    marker = out_dir / RUN_MARKER
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


# A structurally valid SRT timing LINE — both timestamps, anchored to the line,
# minutes/seconds 00-59. Cue TEXT that merely resembles a timestamp, and a
# malformed end like 00:99:99, must not move the coverage measurement: a
# fabricated end past true_duration_s would make the gap negative and let a
# malformed transcript read as complete.
_SRT_TIMING_RE = re.compile(
    r"^\s*\d+:[0-5]\d:[0-5]\d[,.]\d+\s*-->\s*(\d+):([0-5]\d):([0-5]\d)[,.](\d+)\s*$",
    re.MULTILINE,
)


def srt_last_end(srt_text: str):
    """Where the transcript STOPS, in seconds — the last cue's END, not its
    start. One long cue covers everything between its two timestamps, so
    measuring coverage from cue starts would report a whole recording as
    uncovered. None when nothing parses."""
    ends = [
        int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000
        for h, m, s, ms in _SRT_TIMING_RE.findall(srt_text)
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


# ------------------------------------------------ loop-wedge recovery ---

_SRT_CUE_TIMES_RE = re.compile(
    r"(\d+):(\d\d):(\d\d)[,.](\d+)\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d+)"
)


def _srt_time_s(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000


def parse_srt_cues(srt_text: str):
    """Parse SRT into (start_s, end_s, text) triples at millisecond precision —
    the full-fidelity counterpart to srt_to_segments, for the paths that
    REWRITE cues rather than read them."""
    cues = []
    for block in re.split(r"\n\s*\n", srt_text.strip()):
        lines = block.strip().splitlines()
        for idx, ln in enumerate(lines):
            m = _SRT_CUE_TIMES_RE.search(ln)
            if m:
                g = m.groups()
                text = " ".join(x.strip() for x in lines[idx + 1 :]).strip()
                cues.append((_srt_time_s(*g[:4]), _srt_time_s(*g[4:]), text))
                break
    return cues


def srt_timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def cues_to_srt(cues) -> str:
    return "\n".join(
        f"{n}\n{srt_timestamp(a)} --> {srt_timestamp(b)}\n{t}\n"
        for n, (a, b, t) in enumerate(cues, 1)
    )


def wedged_spans(cues):
    """Index ranges [i, j] of identical-line runs long enough to be a wedge:
    ≥2 consecutive cues with the same non-empty text covering
    RECOVERY_MIN_SPAN_S of wall time (last cue's END minus first cue's start —
    the audio the wedge is sitting on, not just the cue starts). Empty cues
    are transparent: a wedged whisper strews zero-length empty cues between
    the repeated lines (2026-08-18 call), so they neither break a run nor
    anchor one."""
    spans, i, n = [], 0, len(cues)
    while i < n:
        if not cues[i][2]:
            i += 1
            continue
        j = last = i
        while j + 1 < n and cues[j + 1][2] in ("", cues[i][2]):
            j += 1
            if cues[j][2]:
                last = j
        if last > i and cues[last][1] - cues[i][0] >= RECOVERY_MIN_SPAN_S:
            spans.append((i, last))
        i = j + 1
    return spans


def retranscribe_span(wav: Path, start: float, end: float, out_dir: Path):
    """One recovery window: cut it from the extracted audio with the
    normalization filter, transcribe it with conditioning OFF (conditioning on
    the looped line is what keeps the wedge fed), and return the cues offset
    back to absolute timestamps. None on any tool failure — recovery must
    never take the packet down with it."""
    clip = out_dir / "recover-clip.wav"
    produced = out_dir / "recover-clip.srt"
    try:
        r = run_cmd(
            [
                "ffmpeg", "-nostdin", "-y",
                "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(wav),
                "-af", RECOVERY_AUDIO_FILTER, "-ar", "16000", "-ac", "1",
                str(clip),
            ],
            timeout=1800,
        )
        if r.returncode != 0 or not clip.exists():
            return None
        r = run_cmd(
            [
                "uvx", "--from", "mlx-whisper", "mlx_whisper", str(clip),
                "--model", WHISPER_MODEL,
                "--output-format", "srt",
                "--output-dir", str(out_dir),
                "--condition-on-previous-text", "False",
            ],
            timeout=3600,
        )
        if r.returncode != 0 or not produced.exists():
            return None
        cues = parse_srt_cues(produced.read_text())
        return [(a + start, b + start, t) for a, b, t in cues if t]
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        clip.unlink(missing_ok=True)
        produced.unlink(missing_ok=True)


def recover_wedged_spans(wav: Path, srt: Path, out_dir: Path) -> tuple:
    """Detect wedged spans in transcript.srt and splice re-transcribed cues
    over them; the untouched original is kept as transcript.orig.srt. Returns
    (spans_meta, words_recovered, failed_spans). Prints its coverage line
    ALWAYS — a human must be able to see at a glance whether the transcript
    needed rescue. A failed recovery keeps the original cues and warns loudly;
    it is never a failed packet."""
    original_text = srt.read_text()
    cues = parse_srt_cues(original_text)
    spans = wedged_spans(cues)
    if not spans:
        log("loop-wedge recovery: none needed")
        return [], 0, []
    meta, words, failed = [], 0, []
    # Splice back-to-front so earlier spans' indices stay valid.
    for i, j in reversed(spans):
        w_start = max(0.0, cues[i][0] - RECOVERY_PAD_S)
        w_end = cues[j][1] + RECOVERY_PAD_S
        new = retranscribe_span(wav, w_start, w_end, out_dir)
        if new is not None:
            # The padding re-hears the neighbours' edges; keep only cues that
            # overlap the wedged span itself so neighbour text is not
            # duplicated.
            new = [c for c in new if c[1] > cues[i][0] and c[0] < cues[j][1]]
        if not new:
            # Tool failure, or nothing usable came back. Either way the span
            # was NOT verified: keep the original cues so the wedge stays
            # visible, and record the failure so a resumed run still reports
            # it instead of "none needed".
            why = ("recovery tool failed" if new is None
                   else "re-transcription produced no usable cues")
            failed.append(
                {
                    "start_s": round(cues[i][0], 2),
                    "end_s": round(cues[j][1], 2),
                    "seconds": round(cues[j][1] - cues[i][0], 2),
                }
            )
            log(
                f"WARNING: loop-wedge recovery FAILED for "
                f"{cues[i][0]:.0f}s-{cues[j][1]:.0f}s ({why}); original cues "
                f"kept, re-transcribe that span by hand (normalize + "
                f"--condition-on-previous-text False, see "
                f"references/pipeline.md)"
            )
            continue
        meta.append(
            {
                "start_s": round(cues[i][0], 2),
                "end_s": round(cues[j][1], 2),
                "seconds": round(cues[j][1] - cues[i][0], 2),
                "cues_before": j - i + 1,
                "cues_after": len(new),
            }
        )
        words += sum(len(t.split()) for _, _, t in new)
        cues[i : j + 1] = new
    meta.reverse()
    failed.reverse()
    if meta:
        # Original first, so a crash between the two writes loses nothing.
        (out_dir / "transcript.orig.srt").write_text(original_text)
        srt.write_text(cues_to_srt(cues))
    log(recovery_summary(meta, words, failed))
    return meta, words, failed


def recovery_summary(spans_meta, words: int, failed_spans=()) -> str:
    if not spans_meta and not failed_spans:
        return "loop-wedge recovery: none needed"
    line = (
        f"loop-wedge recovery: {len(spans_meta)} span(s), "
        f"{sum(m['seconds'] for m in spans_meta):.0f}s re-transcribed, "
        f"{words} words recovered"
    )
    if failed_spans:
        line += f"; {len(failed_spans)} span(s) FAILED, original cues kept"
    return line


def transcribe(wav: Path, out_dir: Path, manifest: Manifest) -> tuple:
    """One whisper invocation, one file, SRT out; TXT and a timestamped
    reading copy are derived — never transcribed twice."""
    srt = out_dir / "transcript.srt"
    txt = out_dir / "transcript.txt"
    reading = out_dir / "transcript.md"
    if manifest.done("transcribe"):
        rec = manifest.data["stages"]["transcribe"]
        log(recovery_summary(rec.get("recovered_spans") or [],
                             rec.get("recovered_words", 0),
                             rec.get("failed_spans") or []))
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

    # Recovery runs INSIDE this stage, before it is declared done, so a
    # resumed run never reuses a wedged transcript as finished work.
    recovered, rec_words, failed = recover_wedged_spans(wav, srt, out_dir)
    orig = out_dir / "transcript.orig.srt"

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
            "transcribe",
            [srt, txt, reading] + ([orig] if orig.exists() else []),
            segments=0,
            no_speech=True,
            recovered_spans=recovered,
            recovered_words=rec_words,
            failed_spans=failed,
        )
        return srt, txt, reading

    txt.write_text("\n".join(t for _, t in segs))
    reading.write_text(
        header + "\n".join(f"[{ts//60}:{ts%60:02d}] {t}" for ts, t in segs)
    )
    manifest.finish(
        "transcribe",
        [srt, txt, reading] + ([orig] if orig.exists() else []),
        segments=len(segs),
        raw_segments=len(raw),
        collapsed_runs=collapsed,
        recovered_spans=recovered,
        recovered_words=rec_words,
        failed_spans=failed,
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


# -------------------------------------------------- derived items & sweep ---
#
# A packet lives as long as the work it spawned. The filing session records
# what that work IS (link, at filing time — written at creation, never
# reconstructed); the sweep later checks whether it has all resolved and
# OFFERS deletion. Nothing here deletes unasked: the report is the offer, and
# --delete is the decider taking it.


def require_packet(out_dir: Path) -> Path:
    """A link or sweep target must be a directory ingest created — the same
    ownership rule the run itself enforces, because both end in deletion."""
    if not out_dir.is_dir():
        die(f"{out_dir} is not a directory", 2)
    if not (out_dir / RUN_MARKER).exists():
        die(
            f"{out_dir} was not created by ingest (no {RUN_MARKER} marker).\n"
            "Refusing to touch it: retention only ever operates on the tool's "
            "own run directories.",
            2,
        )
    return out_dir


def cmd_link(args) -> None:
    """Append derived work items to the packet's manifest. Idempotent: an id
    already recorded (case-insensitively — GitHub ids are) is kept with its
    original date, not duplicated. Additive only: a manifest this command
    cannot parse is refused rather than run through the corrupt-rename,
    which would silently destroy the stage ledger."""
    out_dir = require_packet(Path(args.out).expanduser())
    mpath = out_dir / "manifest.json"
    if mpath.exists():
        try:
            json.loads(mpath.read_text())
        except (OSError, json.JSONDecodeError):
            die(
                f"{mpath} is unreadable — refusing to link into a torn "
                "manifest. Fix or re-run the packet first."
            )
    manifest = Manifest(out_dir)
    known = set()
    for rec in manifest.data["derived_items"]:
        rid = rec if isinstance(rec, str) else (rec or {}).get("id")
        if isinstance(rid, str):
            known.add(rid.lower())
    today = time.strftime("%Y-%m-%d")
    added = 0
    for item in args.item:
        item = item.strip()
        if not item:
            continue
        if not ITEM_ID_OK_RE.match(item):
            die(
                f"refusing item id {json.dumps(item)} — ids are letters, "
                "digits, and . _ / # - only (no whitespace, control "
                "characters, or shell metacharacters: this id is later "
                "handed to a resolution command and printed in reports)",
                2,
            )
        if item.lower() in known:
            log(f"already recorded: {json.dumps(item)}")
            continue
        if not GH_ITEM_RE.match(item):
            # Not fatal — other trackers are legitimate — but say what it
            # means: this id will need a binding-doc command to resolve.
            log(
                f"note: {json.dumps(item)} is not owner/repo#number — the "
                "sweep will need the binding doc's resolution command "
                "(--check-cmd) to resolve it"
            )
        manifest.data["derived_items"].append({"id": item, "added": today})
        known.add(item.lower())
        added += 1
    manifest.save()
    log(
        f"derived items recorded: {added} new, "
        f"{len(manifest.data['derived_items'])} total in {manifest.path}"
    )


def check_item_resolution(item_id: str, check_cmd: str | None = None) -> tuple:
    """One derived item's terminal state: ('resolved'|'open'|'unknown', why).

    GitHub-first: owner/repo#number resolves via gh — the issues endpoint
    covers PRs too, and resolution means state == closed. Any other id runs
    the binding doc's resolution command (exit 0 resolved, 1 open, anything
    else unknown); with no binding the answer is unknown, and unknown is the
    decider's to settle — never guessed.
    """
    m = GH_ITEM_RE.match(item_id)
    if m:
        try:
            r = run_cmd(
                ["gh", "api", f"repos/{m.group(1)}/issues/{m.group(2)}",
                 "--jq", ".state"],
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as e:
            # gh missing, timing out, or unrunnable is a fact about this
            # machine, not about the item — unknown, never resolved, and
            # never a crash that takes the rest of the sweep with it.
            return ("unknown", f"gh could not run: {e}")
        if r.returncode != 0:
            reason = (r.stderr or "").strip().splitlines()
            return ("unknown", f"gh failed: {reason[-1] if reason else f'exit {r.returncode}'}")
        state = r.stdout.strip()
        return ("resolved", state) if state == "closed" else ("open", state)
    if check_cmd:
        if "{id}" not in check_cmd:
            die(
                "--check-cmd must contain the {id} placeholder — a template "
                "without it runs the same command for every item, and a "
                "blanket exit 0 would mark everything resolved",
                2,
            )
        # The id is DATA, never shell: it rides in as $1 and the template's
        # {id} becomes a quoted positional reference. A hostile id in a
        # hand-edited manifest cannot become syntax, and cannot forge a
        # resolution by ending the command with `exit 0`.
        try:
            r = run_cmd(
                ["/bin/sh", "-c", check_cmd.replace("{id}", '"$1"'),
                 "sh", item_id],
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError) as e:
            return ("unknown", f"binding-doc check could not run: {e}")
        if r.returncode == 0:
            return ("resolved", "binding-doc check: exit 0")
        if r.returncode == 1:
            return ("open", "binding-doc check: exit 1")
        return ("unknown", f"binding-doc check failed: exit {r.returncode}")
    return ("unknown", "no binding for this tracker — ask the decider")


def sweep_packet(out_dir: Path, check_cmd: str | None = None) -> dict:
    """One packet's report. Verdicts:
      resolved — every derived item terminal: deletion may be OFFERED
      open     — work still live: the packet stays, no question to ask
      unknown  — at least one id the sweep cannot read: the decider's call
      unlinked — nothing recorded: nothing proves a terminal state, so the
                 sweep lists it rather than inventing one
    """
    manifest_path = out_dir / "manifest.json"
    report = {"dir": out_dir, "items": [], "verdict": "unknown"}
    try:
        data = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        report["note"] = "manifest missing or unreadable"
        return report
    items = data.get("derived_items")
    if items is None:
        items = []
    if not isinstance(items, list):
        # A hand-edited scalar here is damage, not absence: unknown — so a
        # deletion built on it refuses — never "unlinked", and never a
        # TypeError that turns --delete into a traceback.
        report["note"] = "derived_items is not a list — hand-edited?"
        return report                      # verdict stays "unknown"
    if not items:
        report["verdict"] = "unlinked"
        return report
    states = []
    for rec in items:
        # The manifest is an input, not a fact: a hand-edited bare string is
        # coerced, and anything else unreadable is reported as unknown
        # rather than crashing the packet's report.
        if isinstance(rec, str):
            rec = {"id": rec}
        rid = (rec or {}).get("id") if isinstance(rec, dict) else None
        if not isinstance(rid, str) or not rid:
            states.append("unknown")
            report["items"].append(
                {"id": repr(rec)[:80], "added": None, "state": "unknown",
                 "why": "malformed derived_items entry — hand-edited?"}
            )
            continue
        state, why = check_item_resolution(rid, check_cmd)
        states.append(state)
        report["items"].append(
            {"id": rid, "added": rec.get("added"),
             "state": state, "why": why}
        )
    if "open" in states:
        report["verdict"] = "open"
    elif "unknown" in states:
        report["verdict"] = "unknown"
    else:
        report["verdict"] = "resolved"
    return report


def find_packets(home: Path) -> list:
    """Ingest-created run dirs under the output home — the marker decides
    membership, never the directory name. A home that is itself a packet
    (someone pointed --home at a run dir) sweeps as that one packet."""
    if (home / RUN_MARKER).exists():
        return [home]
    return sorted(
        p for p in home.iterdir()
        if p.is_dir() and (p / RUN_MARKER).exists()
    )


def delete_packet(out_dir: Path, check_cmd: str | None = None) -> int:
    """The decider took the offer. Returns an exit-code-shaped outcome so a
    multi-target --delete finishes every target and reports honestly:

      0 deleted · 1 refused (derived work not fully resolved)
      2 refused (not an ingest-created directory)
      5 incomplete (foreign or undeletable content remains)

    Resolution is RE-CHECKED here — an offer can go stale between the sweep
    and the yes. Deletion follows the ledger: manifest-recorded artifacts and
    listed frames, each path refused unless it resolves inside the packet,
    and a ledgered path that turned into a symlink is left alone — the
    ledger recorded a file, and a link in its place is not that file.

    Bookkeeping (manifest, then the run marker LAST) goes only when the
    directory is actually going away: a kept directory — foreign files, a
    failed unlink — keeps its marker and manifest, so it stays visible to
    the sweep instead of becoming an orphan nothing will ever offer again.
    """
    if not out_dir.is_dir() or not (out_dir / RUN_MARKER).exists():
        log(
            f"ERROR: {out_dir} was not created by ingest (no {RUN_MARKER} "
            "marker) — refusing to touch it"
        )
        return 2
    try:
        report = sweep_packet(out_dir, check_cmd)
    except Exception as e:
        # An assessment that cannot complete is a refusal, never a traceback:
        # deletion without a verdict would be deletion without the offer.
        log(f"ERROR: {out_dir}: could not assess resolution "
            f"({e.__class__.__name__}: {e}) — refusing to delete")
        return 1
    if report["verdict"] != "resolved":
        detail = "; ".join(
            f"{json.dumps(str(i['id']))}: {i['state']}" for i in report["items"]
        ) or report.get("note", "no derived items recorded")
        log(
            f"ERROR: {out_dir}: derived work is not fully resolved "
            f"(verdict: {report['verdict']} — {detail}). Refusing to delete: "
            "a packet lives as long as the work it spawned."
        )
        return 1
    try:
        data = json.loads((out_dir / "manifest.json").read_text())
    except (OSError, json.JSONDecodeError):
        log(f"ERROR: {out_dir}/manifest.json unreadable — refusing to "
            "delete without the ledger")
        return 2

    bookkeeping = [
        out_dir / "manifest.json.tmp",
        out_dir / "manifest.json.corrupt",
        out_dir / "manifest.json",
        out_dir / RUN_MARKER,          # last: the marker is sweepability
    ]
    bookkeeping_strs = {str(b) for b in bookkeeping}
    ledgered = set()
    for rec in data.get("stages", {}).values():
        ledgered.update(str(a) for a in rec.get("artifacts", []))
    for frame in data.get("frames", []):
        try:
            ledgered.add(str(out_dir / frame["file"]))
        except (TypeError, KeyError):
            pass                       # malformed frame entry: nothing to delete
    ledgered -= bookkeeping_strs

    packet_root = out_dir.resolve()
    removed, trouble = 0, False
    emptied_parents = set()
    for path in (Path(p) for p in sorted(ledgered)):
        if path.is_symlink():
            log(f"note: ledgered path {json.dumps(str(path))} is now a "
                "symlink — left alone")
            trouble = True
            continue
        try:
            resolved = path.resolve()
            resolved.relative_to(packet_root)
        except (OSError, ValueError):
            log(f"note: ledger lists {json.dumps(str(path))} outside the "
                "packet — not deleting")
            continue
        if resolved.is_file():
            try:
                resolved.unlink()
            except OSError as e:
                log(f"note: could not delete {json.dumps(str(resolved))}: {e}")
                trouble = True
                continue
            removed += 1
            for parent in resolved.parents:
                if parent == packet_root:
                    break
                emptied_parents.add(parent)

    # Prune ONLY the directories this deletion emptied, deepest first. A
    # pre-existing empty directory the decider made is not ours to remove,
    # and a symlink to a directory is never rmdir material.
    for d in sorted(emptied_parents, key=lambda p: len(p.parts), reverse=True):
        if d.is_symlink() or not d.is_dir():
            continue
        try:
            if not any(d.iterdir()):
                d.rmdir()
        except OSError:
            trouble = True

    # A leftover is anything still present that is not our bookkeeping —
    # files, foreign directories, and symlinks (including dangling ones,
    # which exist without being files).
    leftovers = [
        p for p in out_dir.rglob("*")
        if (p.is_symlink() or p.exists()) and str(p) not in bookkeeping_strs
    ]
    if trouble or leftovers:
        log(
            f"{out_dir}: removed {removed} ledgered file(s); "
            f"{len(leftovers)} item(s) ingest did not create (or could not "
            "delete) remain — directory, marker, and manifest kept so the "
            "packet stays sweepable"
        )
        return EXIT_DELETE_INCOMPLETE
    for b in bookkeeping:
        if b.is_symlink():
            log(f"note: {json.dumps(str(b))} is a symlink — left alone, "
                "packet kept")
            return EXIT_DELETE_INCOMPLETE
        try:
            if b.is_file():
                b.unlink()
        except OSError as e:
            # The marker is removed last, so a failure here leaves the
            # packet marked and sweepable, never orphaned.
            log(f"note: could not delete {json.dumps(str(b))}: {e} — "
                "packet kept")
            return EXIT_DELETE_INCOMPLETE
    try:
        out_dir.rmdir()
    except OSError as e:
        log(f"note: could not remove {out_dir}: {e}")
        return EXIT_DELETE_INCOMPLETE
    log(f"packet deleted: {out_dir} ({removed} files)")
    return 0


def cmd_sweep(args) -> None:
    if args.check_cmd and "{id}" not in args.check_cmd:
        die(
            "--check-cmd must contain the {id} placeholder — a template "
            "without it runs the same command for every item, and a blanket "
            "exit 0 would mark everything resolved",
            2,
        )
    home = Path(args.home).expanduser()
    if not home.is_dir():
        die(f"{home} is not a directory", 2)
    if args.delete:
        # Every target is processed; the exit code is the worst outcome, so
        # partial success is visible in the per-target lines and the summary
        # while the process still reports the failure honestly.
        home_root = home.resolve()
        outcomes = []
        for target in args.delete:
            t = Path(target).expanduser()
            try:
                t.resolve().relative_to(home_root)
            except (OSError, ValueError):
                log(f"ERROR: {t} is not under {home} — refusing "
                    "(--delete only takes packets from the swept home)")
                outcomes.append((t, 2))
                continue
            outcomes.append((t, delete_packet(t, args.check_cmd)))
        deleted = sum(1 for _, c in outcomes if c == 0)
        log(f"deleted {deleted} of {len(outcomes)} target(s)")
        sys.exit(max(c for _, c in outcomes))
    packets = find_packets(home)
    if not packets:
        log(f"no ingest packets directly under {home} — the sweep looks "
            "one level deep; point --home at the output home or at a packet")
        return
    offers, ask = [], []
    for packet in packets:
        try:
            report = sweep_packet(packet, args.check_cmd)
        except Exception as e:  # one packet's failure must not kill the report
            log(f"packet {packet.name} — ERROR: {e.__class__.__name__}: {e}")
            ask.append((packet, "unknown"))
            continue
        log(f"packet {packet.name} — verdict: {report['verdict']}"
            + (f" ({report['note']})" if report.get("note") else ""))
        for item in report["items"]:
            # Ids come from a file on disk: rendered escaped, so a crafted id
            # cannot forge report lines (an OFFER, another packet's verdict).
            log(f"  {item['state']:8s} {json.dumps(str(item['id']))} "
                f"({item['why']})")
        if report["verdict"] == "resolved":
            offers.append(packet)
        elif report["verdict"] in ("unknown", "unlinked"):
            ask.append((packet, report["verdict"]))
    if offers:
        log("OFFER — derived work fully resolved; the decider may take or "
            "decline (nothing is deleted unasked):")
        script = str(Path(__file__).resolve())
        for packet in offers:
            argv = [sys.executable, script, "sweep",
                    "--home", str(home), "--delete", str(packet)]
            if args.check_cmd:
                argv += ["--check-cmd", args.check_cmd]
            log("  " + " ".join(shlex.quote(a) for a in argv))
    if ask:
        log("NEEDS THE DECIDER — the sweep does not guess:")
        for packet, verdict in ask:
            log(f"  {packet} ({'no derived items recorded' if verdict == 'unlinked' else 'unresolvable item(s) — no tracker binding or check failed'})")


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

    lk = sub.add_parser(
        "link",
        help="record the work items filed from a packet, at filing time",
    )
    lk.add_argument("--out", required=True, help="the packet (run directory)")
    lk.add_argument("--item", required=True, action="append",
                    help="derived work item id — owner/repo#number for "
                         "GitHub, the tracker's own id otherwise (repeatable)")

    sw = sub.add_parser(
        "sweep",
        help="check derived-item resolution across packets; OFFER cleanup",
    )
    sw.add_argument("--home", required=True,
                    help="the output home holding packets (or one packet dir)")
    sw.add_argument("--check-cmd",
                    help="resolution-check command from the repo's binding "
                         "doc, for non-GitHub items; must contain a literal "
                         "{id}, which is replaced by a quoted positional "
                         "reference — the id is passed as data, never "
                         "spliced into the shell; exit 0 = resolved, "
                         "1 = open, anything else = unknown")
    sw.add_argument("--delete", action="append", default=[],
                    help="delete this fully-resolved packet under --home — "
                         "the decider taking the offer, never the default "
                         "(repeatable; resolution is re-checked first)")

    args = p.parse_args(argv)
    if args.cmd == "doctor":
        sys.exit(0 if doctor() else 3)
    elif args.cmd == "preview":
        out_dir = Path(args.out).expanduser()
        claim_out_dir(out_dir)
        got = captions_preview(args.url, out_dir, Manifest(out_dir))
        sys.exit(0 if got else 1)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "link":
        cmd_link(args)
    elif args.cmd == "sweep":
        cmd_sweep(args)


if __name__ == "__main__":
    main()

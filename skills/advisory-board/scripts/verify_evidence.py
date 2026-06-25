#!/usr/bin/env python3
"""Resolve a verdict.json's typed evidence against the reviewed material and stamp
each citation verified | unverified | refuted.

WHAT THIS PROVES (design section 9 - read it before trusting a green stamp): that
the *receipt resolves* - the cited line exists, the quoted text is present in the
captured packet. It does NOT prove the inference drawn from that receipt is sound.
It catches fabrication (a hallucinated path:line, a quote that was never in the
source), not faulty reasoning. The scary failure is a hallucinated citation driving
a false gate; this is the cheapest partial defense against it.

Resolution respects quarantine:
  * `source` quotes are checked against the CAPTURED PACKET, never by re-fetching
    the URL (a live fetch would reintroduce the network in gate mode).
  * `command` re-execution is deferred to v1.x -> those citations stamp `unverified`.
  * `judgment` evidence has no external referent and is left unstamped, by design.

How each kind resolves:
  code  path:line   -> verified  if the file has that line;
                       refuted   if the file exists but the line is out of range;
                       unverified if the file isn't under --source, or no --source.
  code  path:symbol -> verified  if the symbol token appears in the cited file;
                       refuted   if the file exists but the token does not;
                       unverified if the file isn't found / no --source.
  source url+quote  -> verified  if the (whitespace-normalized) quote is in the packet;
                       refuted   if a packet was given and the quote is absent;
                       unverified if no packet was given.

A missing file is `unverified`, not `refuted`: --source may be an incomplete tree,
and we refuse to cry fabrication on a file we simply weren't handed. A file we DO
have with a bad line/symbol is `refuted` - that is a positive contradiction.

Usage:
  verify_evidence.py verdict.json --source SRC --packet PKT      stamp in place
  verify_evidence.py verdict.json --run RUNDIR                   derive the packet from a run dir
  verify_evidence.py verdict.json --source SRC -o stamped.json   write elsewhere
  verify_evidence.py verdict.json --source SRC --check           report only; write nothing

Exit codes: 0 ok, 2 usage / bad JSON. Gating on the stamps is board_verdict.py's job.
Standard library only; no third-party dependencies.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")
_WS = re.compile(r"\s+")


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def _norm(text: str) -> str:
    return _WS.sub(" ", text).strip()


def iter_evidence_containers(data: dict):
    """Yield every object that may carry an evidence[] list (blockers/dissent/concerns + top level)."""
    for key in EVIDENCE_CONTAINERS:
        items = data.get(key) or []
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    yield item
    yield data


def resolve_file(source_root, rel: str):
    """Return the path to the cited file, or None if it can't be SAFELY resolved.

    --source may be a single file (single-file review) or a directory root. We refuse
    to resolve an absolute path or one that escapes the root with '..' (a hallucinated
    citation must not read arbitrary files off disk and earn a green stamp), and a
    single-file source matches only a bare-filename citation OF THAT FILE (a different
    directory that merely shares the basename must not resolve to it).
    """
    if source_root is None or not rel:
        return None
    rel = rel.replace("\\", "/")
    if os.path.isabs(rel) or any(part == ".." for part in rel.split("/")):
        return None
    if os.path.isfile(source_root):
        return source_root if rel == os.path.basename(source_root) else None
    candidate = os.path.join(source_root, rel)
    return candidate if os.path.isfile(candidate) else None


def _read_lines(path: str):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read().splitlines()


def resolve_code(ev: dict, source_root) -> str:
    target = resolve_file(source_root, ev.get("path", ""))
    if target is None:
        return "unverified"  # no --source, or the file isn't in the tree we were handed
    try:
        lines = _read_lines(target)
    except OSError:
        return "unverified"
    if "line" in ev:
        line = ev["line"]
        if isinstance(line, bool) or not isinstance(line, int) or line < 1:
            return "unverified"  # malformed line locator - can't resolve, don't crash
        return "verified" if line <= len(lines) else "refuted"
    symbol = ev.get("symbol", "")
    if symbol and re.search(r"\b" + re.escape(symbol) + r"\b", "\n".join(lines)):
        return "verified"
    return "refuted"


def resolve_source(ev: dict, packet_text) -> str:
    if packet_text is None:
        return "unverified"  # no captured packet to check against; we never live-fetch
    quote = _norm(ev.get("quote", ""))
    if not quote:
        return "unverified"
    return "verified" if quote in _norm(packet_text) else "refuted"


def load_packet_text(packet, run_dir):
    """Concatenate the captured-packet text. The packet is what was EGRESSED - the
    `prompts/*.prompt` blobs under a run dir - never a re-fetch of any cited URL."""
    paths = []
    if run_dir:
        prompts = os.path.join(run_dir, "prompts")
        if os.path.isdir(prompts):
            paths += sorted(glob.glob(os.path.join(prompts, "*.prompt")))
        elif os.path.isdir(run_dir):
            paths += sorted(glob.glob(os.path.join(run_dir, "*.prompt")))
    if packet:
        if os.path.isdir(packet):
            for pattern in ("*.prompt", "*.md", "*.txt"):
                paths += sorted(glob.glob(os.path.join(packet, pattern)))
        elif os.path.isfile(packet):
            paths.append(packet)
        else:
            die(f"--packet: {packet} not found")
    seen, uniq = set(), []  # --packet and --run can name the same prompts dir
    for path in paths:
        key = os.path.abspath(path)
        if key not in seen:
            seen.add(key)
            uniq.append(path)
    paths = uniq
    if not paths:
        return None
    chunks = []
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                chunks.append(handle.read())
        except OSError:
            pass
    return "\n".join(chunks) if chunks else None


def stamp(data: dict, source_root, packet_text) -> dict:
    """Resolve every code/source/command citation and write its `status`. Mutates data."""
    counts = {"verified": 0, "unverified": 0, "refuted": 0, "skipped": 0}
    for obj in iter_evidence_containers(data):
        for ev in (obj.get("evidence") or []):
            if not isinstance(ev, dict):
                continue
            kind = ev.get("kind")
            if kind == "code":
                status = resolve_code(ev, source_root)
            elif kind == "source":
                status = resolve_source(ev, packet_text)
            elif kind == "command":
                status = "unverified"  # re-execution deferred to v1.x
            else:  # judgment / unknown: no external referent to resolve
                counts["skipped"] += 1
                continue
            ev["status"] = status
            counts[status] += 1
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Resolve and stamp a verdict.json's typed evidence.")
    parser.add_argument("path", help="path to verdict.json")
    parser.add_argument("--source", help="source tree (dir) or file for `code` path:line / symbol resolution")
    parser.add_argument("--packet", help="captured packet (file or dir) for `source` quote resolution")
    parser.add_argument("--run", dest="run_dir", help="a run dir; derives --packet from its prompts/")
    parser.add_argument("-o", "--out", help="write stamped JSON here (default: in place)")
    parser.add_argument("--check", action="store_true", help="report only; write nothing")
    args = parser.parse_args(argv)

    try:
        with open(args.path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        die(f"{args.path}: not found")
    except json.JSONDecodeError as exc:
        die(f"{args.path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        die(f"{args.path}: top level must be a JSON object")

    packet_text = load_packet_text(args.packet, args.run_dir)
    counts = stamp(data, args.source, packet_text)

    total = sum(counts.values()) - counts["skipped"]
    print(
        f"resolved {total} citation(s): "
        f"{counts['verified']} verified, {counts['unverified']} unverified, "
        f"{counts['refuted']} refuted"
        + (f" ({counts['skipped']} judgment/skipped)" if counts["skipped"] else "")
    )
    if not args.source and any(
        ev.get("kind") == "code"
        for obj in iter_evidence_containers(data)
        for ev in (obj.get("evidence") or [])
        if isinstance(ev, dict)
    ):
        print("note: no --source given - `code` citations stamped unverified (could not resolve).",
              file=sys.stderr)
    if packet_text is None and any(
        ev.get("kind") == "source"
        for obj in iter_evidence_containers(data)
        for ev in (obj.get("evidence") or [])
        if isinstance(ev, dict)
    ):
        print("note: no --packet/--run given - `source` quotes stamped unverified (no captured packet).",
              file=sys.stderr)
    if counts["refuted"]:
        print(f"WARNING: {counts['refuted']} citation(s) REFUTED - a cited line/quote was not "
              "found in the material. Inspect before trusting the verdict.", file=sys.stderr)

    if args.check:
        print("(--check: no file written)")
        return 0

    out_path = args.out or args.path
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

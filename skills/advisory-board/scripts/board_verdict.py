#!/usr/bin/env python3
"""Validate an advisory-board verdict.json and optionally gate CI on it.

Examples:
  board_verdict.py verdict.json                            validate + print a summary
  board_verdict.py verdict.json --gate                     exit 1 if verdict is "block"
  board_verdict.py verdict.json --gate --fail-on caution   exit 1 if "caution" or "block"
  board_verdict.py verdict.json --json                     echo normalized JSON

Exit codes: 0 ok / gate pass, 1 gate fail, 2 usage or schema error.
Standard library only; no third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import sys

SEVERITY = {"ship": 0, "caution": 1, "block": 2}
REQUIRED = ("schema", "verdict", "confidence", "board", "rounds")


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        die(f"{path}: not found")
    except json.JSONDecodeError as exc:
        die(f"{path}: invalid JSON ({exc})")
    if not isinstance(data, dict):
        die(f"{path}: top level must be a JSON object")
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        die(f"{path}: missing required field(s): {', '.join(missing)}")
    if data["verdict"] not in SEVERITY:
        die(f"verdict must be one of {', '.join(SEVERITY)}; got {data['verdict']!r}")
    if not isinstance(data["board"], list) or not data["board"]:
        die("board must be a non-empty list of seats")
    return data


def summarize(data: dict) -> str:
    board = data["board"]
    ran = [s for s in board if not s.get("dropped")]
    dropped = [s for s in board if s.get("dropped")]
    seats_line = f"{len(ran)} ran"
    if dropped:
        names = ", ".join(s.get("seat", "?") for s in dropped)
        seats_line += f", {len(dropped)} dropped ({names})"
    return "\n".join(
        [
            f"title      : {data.get('title', '(untitled)')}",
            f"verdict    : {data['verdict']}  ({data['confidence']} confidence)",
            f"unanimous  : {data.get('unanimous', 'n/a')}",
            f"rounds     : {data['rounds']}",
            f"seats      : {seats_line}",
            f"blockers   : {len(data.get('blockers', []))}",
        ]
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate / gate an advisory-board verdict.json.")
    parser.add_argument("path", nargs="?", default="verdict.json", help="path to verdict.json (default: verdict.json)")
    parser.add_argument("--gate", action="store_true", help="exit 1 when the verdict meets the fail threshold")
    parser.add_argument(
        "--fail-on", choices=("caution", "block"), default="block", help="threshold for --gate (default: block)"
    )
    parser.add_argument("--json", dest="as_json", action="store_true", help="echo normalized JSON and exit")
    args = parser.parse_args(argv)

    data = load(args.path)

    if args.as_json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0

    print(summarize(data))

    if args.gate:
        if SEVERITY[data["verdict"]] >= SEVERITY[args.fail_on]:
            print(
                f"gate: FAIL - verdict '{data['verdict']}' meets threshold '{args.fail_on}'",
                file=sys.stderr,
            )
            return 1
        print(f"gate: pass - verdict '{data['verdict']}' is below threshold '{args.fail_on}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

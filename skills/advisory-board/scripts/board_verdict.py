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
CONFIDENCE = {"low", "medium", "high"}
SCHEMA = "advisory-board/verdict@1"
REQUIRED = ("schema", "verdict", "confidence", "board", "rounds")
SEAT_REQUIRED = ("seat", "model", "round_verdicts")


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
    validate(data)
    return data


def validate(data: dict) -> None:
    """Strict schema check: a malformed verdict must not quietly pass a gate."""
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        die(f"missing required field(s): {', '.join(missing)}")

    if data["schema"] != SCHEMA:
        die(f"schema must be {SCHEMA!r}; got {data['schema']!r}")
    if data["verdict"] not in SEVERITY:
        die(f"verdict must be one of {', '.join(SEVERITY)}; got {data['verdict']!r}")
    if data["confidence"] not in CONFIDENCE:
        die(f"confidence must be one of {', '.join(sorted(CONFIDENCE))}; got {data['confidence']!r}")

    rounds = data["rounds"]
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
        die(f"rounds must be a positive integer; got {rounds!r}")

    board = data["board"]
    if not isinstance(board, list) or not board:
        die("board must be a non-empty list of seats")

    for index, seat in enumerate(board):
        where = f"board[{index}]"
        if not isinstance(seat, dict):
            die(f"{where} must be an object")
        name = seat.get("seat", where)
        seat_missing = [key for key in SEAT_REQUIRED if key not in seat]
        if seat_missing:
            die(f"{where} ({name}) missing field(s): {', '.join(seat_missing)}")
        for key in ("seat", "model"):
            if not isinstance(seat[key], str) or not seat[key].strip():
                die(f"{where} ({name}): {key} must be a non-empty string")
        if "lens" in seat and not isinstance(seat["lens"], str):
            die(f"{where} ({name}): lens must be a string")
        if "dropped" in seat and not isinstance(seat["dropped"], bool):
            die(f"{where} ({name}): dropped must be true or false")
        verdicts = seat["round_verdicts"]
        if not isinstance(verdicts, list) or not verdicts:
            die(f"{where} ({name}): round_verdicts must be a non-empty list")
        bad = [v for v in verdicts if v not in SEVERITY]
        if bad:
            die(f"{where} ({name}): round_verdicts has invalid value(s): {', '.join(map(repr, bad))}")

    ran = [seat for seat in board if not seat.get("dropped")]
    if len(ran) < 2:
        die(f"a board needs >= 2 seats that ran; found {len(ran)} (dropped seats don't count)")

    if "unanimous" in data:
        if not isinstance(data["unanimous"], bool):
            die(f"unanimous must be true or false; got {data['unanimous']!r}")
        finals = {seat["round_verdicts"][-1] for seat in ran}
        actually_unanimous = finals == {data["verdict"]}
        if data["unanimous"] != actually_unanimous:
            die(
                f"unanimous={str(data['unanimous']).lower()} contradicts the seats that ran: "
                f"their final-round verdicts are {sorted(finals)} vs the overall verdict "
                f"{data['verdict']!r}"
            )


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
            f"verdict    : {data['verdict']}"
            + (f" ({data['decision']})" if data.get("decision") else "")
            + f"  ({data['confidence']} confidence)",
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

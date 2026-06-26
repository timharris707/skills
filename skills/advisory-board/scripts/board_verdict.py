#!/usr/bin/env python3
"""Validate an advisory-board verdict.json and optionally gate CI on it.

Examples:
  board_verdict.py verdict.json                            validate + print a summary
  board_verdict.py verdict.json --gate                     exit 1 if verdict is "block"
  board_verdict.py verdict.json --gate --fail-on caution   exit 1 if "caution" or "block"
  board_verdict.py verdict.json --json                     echo normalized JSON

Exit codes:
  0  ok / gate pass
  1  gate fail (the board's verdict meets the fail threshold)
  2  usage or schema error
  3  gate abstain - the board is too split, the declared verdict contradicts the
     observed board, or a citation was refuted; a human must decide. Neutral, not a fail.

Schema: accepts advisory-board/verdict@1 and @2. @2 adds typed `evidence[]` on
blockers/dissent/concerns (kinds code|source|command|judgment) and an optional
per-citation `status` (verified|unverified|refuted) stamped by verify_evidence.py.

Standard library only; no third-party dependencies.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

SEVERITY = {"ship": 0, "caution": 1, "block": 2}
CONFIDENCE = {"low", "medium", "high"}
SCHEMAS = {"advisory-board/verdict@1", "advisory-board/verdict@2"}
CURRENT_SCHEMA = "advisory-board/verdict@2"
REQUIRED = ("schema", "verdict", "confidence", "board", "rounds")
SEAT_REQUIRED = ("seat", "model", "round_verdicts")
EVIDENCE_KINDS = {"code", "source", "command", "judgment"}
EVIDENCE_STATUS = {"verified", "unverified", "refuted"}
# Top-level keys whose items may each carry an `evidence[]` list.
EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")

EXIT_OK = 0
EXIT_GATE_FAIL = 1
EXIT_SCHEMA = 2
EXIT_ABSTAIN = 3


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(EXIT_SCHEMA)


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


def _validate_evidence_list(items, where: str) -> None:
    """Structural check for a typed evidence[] list (schema @2)."""
    if not isinstance(items, list):
        die(f"{where}.evidence must be a list")
    for index, ev in enumerate(items):
        loc = f"{where}.evidence[{index}]"
        if not isinstance(ev, dict):
            die(f"{loc} must be an object")
        kind = ev.get("kind")
        if kind not in EVIDENCE_KINDS:
            die(f"{loc}: kind must be one of {', '.join(sorted(EVIDENCE_KINDS))}; got {kind!r}")
        if "status" in ev and ev["status"] not in EVIDENCE_STATUS:
            die(f"{loc}: status must be one of {', '.join(sorted(EVIDENCE_STATUS))}; got {ev['status']!r}")
        if kind == "code":
            if not isinstance(ev.get("path"), str) or not ev["path"].strip():
                die(f"{loc}: code evidence needs a non-empty 'path'")
            has_line, has_symbol = "line" in ev, "symbol" in ev
            if not (has_line or has_symbol):
                die(f"{loc}: code evidence needs 'line' or 'symbol'")
            if has_line:
                line = ev["line"]
                if isinstance(line, bool) or not isinstance(line, int) or line < 1:
                    die(f"{loc}: code 'line' must be a positive integer; got {line!r}")
            if has_symbol and (not isinstance(ev["symbol"], str) or not ev["symbol"].strip()):
                die(f"{loc}: code 'symbol' must be a non-empty string")
        elif kind == "source":
            if not isinstance(ev.get("url"), str) or not ev["url"].strip():
                die(f"{loc}: source evidence needs a non-empty 'url'")
            if not isinstance(ev.get("quote"), str) or not ev["quote"].strip():
                die(f"{loc}: source evidence needs a non-empty 'quote'")
        elif kind == "command":
            if not isinstance(ev.get("command"), str) or not ev["command"].strip():
                die(f"{loc}: command evidence needs a non-empty 'command'")
        # kind == "judgment": no external referent required, by design.


def iter_evidence_containers(data: dict):
    """Yield (label, obj) for every object that may carry an evidence[] list."""
    for key in EVIDENCE_CONTAINERS:
        items = data.get(key) or []
        if isinstance(items, list):
            for index, item in enumerate(items):
                if isinstance(item, dict):
                    yield f"{key}[{index}]", item
    yield "verdict", data  # the top level may carry a bare evidence[]


def validate(data: dict) -> None:
    """Strict schema check: a malformed verdict must not quietly pass a gate."""
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        die(f"missing required field(s): {', '.join(missing)}")

    if data["schema"] not in SCHEMAS:
        die(f"schema must be one of {', '.join(sorted(SCHEMAS))}; got {data['schema']!r}")
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
        is_dropped = bool(seat.get("dropped"))
        verdicts = seat["round_verdicts"]
        if not isinstance(verdicts, list):
            die(f"{where} ({name}): round_verdicts must be a list")
        # A dropped seat may have an empty round_verdicts list (it contributed
        # no tokens — recording None placeholders would be the conductor inventing
        # a verdict, which §11 forbids). A seat that ran must have at least one
        # token, and every recorded token must be a valid SEVERITY.
        if not is_dropped and not verdicts:
            die(f"{where} ({name}): round_verdicts must be non-empty for a seat that ran")
        bad = [v for v in verdicts if v not in SEVERITY]
        if bad:
            die(f"{where} ({name}): round_verdicts has invalid value(s): {', '.join(map(repr, bad))}")

    ran = [seat for seat in board if not seat.get("dropped")]
    if len(ran) < 2:
        die(f"a board needs >= 2 seats that ran; found {len(ran)} (dropped seats don't count)")

    for key in EVIDENCE_CONTAINERS:
        if key in data and not isinstance(data[key], list):
            die(f"{key} must be a list when present; got {type(data[key]).__name__}")

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

    for label, obj in iter_evidence_containers(data):
        if "evidence" in obj:
            _validate_evidence_list(obj["evidence"], label)


# --------------------------------------------------------------------------- #
# Gate logic
# --------------------------------------------------------------------------- #


def refuted_citations(data: dict) -> list:
    """Locations of any `refuted` (fabricated-receipt) citation, anywhere in the verdict.

    A refuted citation is a detected fabrication in the decision document — on a
    blocker, a dissent, a concern, or the top level. The gate cannot tell a 'harmless'
    fabrication from a load-bearing one, so it routes ALL of them to a human.
    """
    hits = []
    for label, obj in iter_evidence_containers(data):
        if any(isinstance(ev, dict) and ev.get("status") == "refuted"
               for ev in (obj.get("evidence") or [])):
            name = obj.get("title") or obj.get("who")
            hits.append(f"{label}" + (f" ({name})" if name else ""))
    return hits


def gate_outcome(data: dict, fail_on: str):
    """Decide the gate from OBSERVED cross-seat agreement, returning (outcome, reason).

    outcome is 'pass' | 'fail' | 'abstain'. abstain ("human required") fires when:
      1. any citation is refuted (a fabricated receipt in the decision basis); or
      2. the seats that ran are genuinely torn at the threshold (some trip it, some
         clear it, with no strict majority) — the regime where a stochastic gate is
         dangerous; or
      3. the declared `verdict` field *clears* the gate while a majority of seats
         *trip* it — the verdict contradicts the board it summarizes (an injected or
         fabricated 'ship' over a block-leaning board is exactly this case).

    Synthesis ESCALATION is honored: a declared verdict that trips the gate fails it,
    even if the seats lean the other way (blocking on a minority-but-correct concern is
    a legitimate, safe call). Only DE-escalation below the observed board is distrusted.
    The decision reads each seat's final-round verdict, never the gameable `confidence`.
    """
    refuted = refuted_citations(data)
    if refuted:
        return "abstain", "a citation was refuted (fabricated receipt): " + "; ".join(refuted)

    ran = [seat for seat in data["board"] if not seat.get("dropped")]
    finals = [seat["round_verdicts"][-1] for seat in ran]
    threshold = SEVERITY[fail_on]
    trip = [v for v in finals if SEVERITY[v] >= threshold]
    clear = [v for v in finals if SEVERITY[v] < threshold]
    top_count = Counter(finals).most_common(1)[0][1] if finals else 0
    has_majority = top_count * 2 > len(finals)
    if trip and clear and not has_majority:
        return "abstain", (
            f"board is split across the '{fail_on}' line with no majority "
            f"(final-round verdicts: {finals}) - human review required"
        )

    declared_fails = SEVERITY[data["verdict"]] >= threshold
    observed_majority_trips = len(trip) * 2 > len(finals)
    if not declared_fails and observed_majority_trips:
        return "abstain", (
            f"declared verdict '{data['verdict']}' clears the '{fail_on}' gate but a "
            f"majority of seats trip it (final-round verdicts: {finals}) - the verdict "
            "contradicts the board; human review required"
        )

    if declared_fails:
        return "fail", f"verdict '{data['verdict']}' meets threshold '{fail_on}'"
    return "pass", f"verdict '{data['verdict']}' is below threshold '{fail_on}'"


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #


def _evidence_tally(data: dict) -> Counter:
    tally = Counter()
    for _, obj in iter_evidence_containers(data):
        for ev in (obj.get("evidence") or []):
            if isinstance(ev, dict):
                tally[ev.get("status", "unchecked")] += 1
    return tally


def summarize(data: dict) -> str:
    board = data["board"]
    ran = [s for s in board if not s.get("dropped")]
    dropped = [s for s in board if s.get("dropped")]
    seats_line = f"{len(ran)} ran"
    if dropped:
        names = ", ".join(s.get("seat", "?") for s in dropped)
        seats_line += f", {len(dropped)} dropped ({names})"
    lines = [
        f"title      : {data.get('title', '(untitled)')}",
        f"verdict    : {data['verdict']}"
        + (f" ({data['decision']})" if data.get("decision") else "")
        + f"  ({data['confidence']} confidence)",
        f"unanimous  : {data.get('unanimous', 'n/a')}",
        f"rounds     : {data['rounds']}",
        f"seats      : {seats_line}",
        f"blockers   : {len(data.get('blockers', []))}",
    ]
    tally = _evidence_tally(data)
    if tally:
        parts = [f"{tally[k]} {k}" for k in ("verified", "unverified", "refuted", "unchecked") if tally.get(k)]
        lines.append(f"evidence   : {', '.join(parts)}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate / gate an advisory-board verdict.json.")
    parser.add_argument("path", nargs="?", default="verdict.json", help="path to verdict.json (default: verdict.json)")
    parser.add_argument("--gate", action="store_true", help="exit 1 when the verdict meets the fail threshold (3 to abstain)")
    parser.add_argument(
        "--fail-on", choices=("caution", "block"), default="block", help="threshold for --gate (default: block)"
    )
    parser.add_argument("--json", dest="as_json", action="store_true", help="echo normalized JSON and exit")
    args = parser.parse_args(argv)

    data = load(args.path)

    if args.as_json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return EXIT_OK

    print(summarize(data))

    if args.gate:
        outcome, reason = gate_outcome(data, args.fail_on)
        if outcome == "abstain":
            print(f"gate: ABSTAIN - {reason}", file=sys.stderr)
            return EXIT_ABSTAIN
        if outcome == "fail":
            print(f"gate: FAIL - {reason}", file=sys.stderr)
            return EXIT_GATE_FAIL
        print(f"gate: pass - {reason}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

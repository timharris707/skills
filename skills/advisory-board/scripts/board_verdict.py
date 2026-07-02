#!/usr/bin/env python3
"""Validate an advisory-board verdict.json and optionally gate CI on it.

Examples:
  board_verdict.py verdict.json                            validate + print a summary
  board_verdict.py verdict.json --gate                     exit 1 if verdict is "block"
  board_verdict.py verdict.json --gate --fail-on caution   exit 1 if "caution" or "block"
  board_verdict.py verdict.json --json                     echo normalized JSON
  board_verdict.py amend --run <dir> --author … --reason … --confidence medium
                                                           append a human amendment (P4)

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
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime

SEVERITY = {"ship": 0, "caution": 1, "block": 2}
CONFIDENCE = {"low", "medium", "high"}
# --min-severity (v1.14 P1): the FINDING severity a fail must rest on. It composes
# WITH --fail-on (the verdict-token threshold), never against it — a fail requires
# BOTH the verdict token to meet --fail-on AND a finding at/above this tier. Ranked
# blocker > concern; dissent is a minority view, not a finding tier, so it never
# counts (a caution whose only findings are concerns/dissent does not fail under
# `blocker`). Absent = today's behavior (the verdict token alone drives the gate).
FINDING_SEVERITY = {"concern": 0, "blocker": 1}
SCHEMAS = {"advisory-board/verdict@1", "advisory-board/verdict@2"}
CURRENT_SCHEMA = "advisory-board/verdict@2"
REQUIRED = ("schema", "verdict", "confidence", "board", "rounds")
SEAT_REQUIRED = ("seat", "model", "round_verdicts")
EVIDENCE_KINDS = {"code", "source", "command", "judgment"}
EVIDENCE_STATUS = {"verified", "unverified", "refuted"}
# Optional captured snippet on an evidence entry (v1.13 P3). Strict-when-present:
# a 1-based inclusive line range + the verbatim lines; unknown keys refused.
SNIPPET_KEYS = {"from", "to", "text"}
# Top-level keys whose items may each carry an `evidence[]` list.
EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")
# Verdict-lifecycle fields (since v1.12) — optional and additive within @2:
# `previous_run` (lineage to the run this one revises) and `amendments[]`
# (append-only human tuning, each entry carrying its own provenance). They are
# tool/human-authored, never model reasoning: the synthesizer merge strips them
# (see _conductor/synthesizer.py LIFECYCLE_KEYS) and gate_outcome() never reads
# them. `changes` (v1.13) is the tool-authored pointer to the revision artifact —
# a strict `{artifact, sha256}` object validated when present (the "changes"
# block in validate() below), and — like the others — stripped from synthesizer
# merges (LIFECYCLE_KEYS) so no model can forge it.
LIFECYCLE_FIELDS = ("previous_run", "amendments", "changes")
AMENDMENT_REQUIRED = ("author", "timestamp", "reason")

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


def _validate_snippet(snip, where: str) -> None:
    """A captured code snippet (v1.13 P3), strict-when-present:
      * an object with EXACTLY {from, to, text} (unknown keys refused);
      * `from` an int ≥ 1, `to` an int ≥ `from` (both real ints, not bools);
      * `text` a non-empty string.
    Same strictness the lifecycle fields get — a fuzzed/hand-authored snippet with
    the wrong shape (or a bool masquerading as a line number) can't smuggle past."""
    if not isinstance(snip, dict):
        die(f"{where}.snippet must be an object with 'from', 'to' and 'text'")
    unknown = set(snip) - SNIPPET_KEYS
    if unknown:
        die(f"{where}.snippet: unknown key(s): {', '.join(sorted(unknown))}")
    missing = [k for k in ("from", "to", "text") if k not in snip]
    if missing:
        die(f"{where}.snippet missing field(s): {', '.join(missing)}")
    frm, to = snip["from"], snip["to"]
    if isinstance(frm, bool) or not isinstance(frm, int) or frm < 1:
        die(f"{where}.snippet.from must be a positive integer; got {frm!r}")
    if isinstance(to, bool) or not isinstance(to, int) or to < frm:
        die(f"{where}.snippet.to must be an integer >= from ({frm}); got {to!r}")
    if not isinstance(snip["text"], str) or not snip["text"]:
        die(f"{where}.snippet.text must be a non-empty string")


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
        # Optional captured snippet (v1.13 P3): the cited lines, embedded by
        # verify_evidence at stamp time so the handoff is self-contained. Strict
        # WHEN PRESENT (absent = invisible, old verdicts untouched); the same
        # discipline as every lifecycle field.
        if "snippet" in ev:
            _validate_snippet(ev["snippet"], loc)
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
            # Optional re-execution expectation fields (M3): expect_exit (int) and a
            # verbatim `expect` substring. Additive to schema @2 — validated only when
            # present so older verdicts and bare command citations still pass.
            if "expect_exit" in ev:
                ee = ev["expect_exit"]
                if isinstance(ee, bool) or not isinstance(ee, int):
                    die(f"{loc}: command 'expect_exit' must be an integer; got {ee!r}")
            if "expect" in ev and not isinstance(ev["expect"], str):
                die(f"{loc}: command 'expect' must be a string; got {type(ev['expect']).__name__}")
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


def _validate_lifecycle(data: dict) -> None:
    """Lifecycle fields (since v1.12): validated strictly WHEN PRESENT, invisible
    when absent — an existing verdict without them validates and gates
    byte-identically. These fields carry lineage and human provenance, not board
    reasoning, so gate_outcome() never reads them."""
    # `changes` (v1.13): a TOOL-AUTHORED pointer to the revision artifact
    # (changes.json), written by the conductor's revision step with amend's
    # discipline — NEVER by a model (the synthesizer merge strips it, see
    # synthesizer.LIFECYCLE_KEYS). Strict-when-present, exactly {artifact, sha256}
    # and nothing else: an acyclic pin (verdict → changes → {source, revised}).
    if "changes" in data:
        changes = data["changes"]
        if not isinstance(changes, dict):
            die(f"changes must be an object when present; got {type(changes).__name__}")
        unknown = set(changes) - {"artifact", "sha256"}
        if unknown:
            die(f"changes: unknown key(s): {', '.join(sorted(unknown))} "
                "(changes is exactly {artifact, sha256} — the revision-artifact pointer)")
        for key in ("artifact", "sha256"):
            if key not in changes:
                die(f"changes missing '{key}' (changes is the pointer {{artifact, sha256}})")
        if not isinstance(changes["artifact"], str) or not changes["artifact"].strip():
            die("changes.artifact must be a non-empty string")
        # The renderer joins changes.artifact onto run_dir to load changes.json, so
        # it must be a BARE filename: an absolute path or `..` component would read
        # outside the run dir (the renderer's islink check misses absolute targets
        # and parent-dir symlinks). Mirrors board_changes' bare-filename gate on
        # revised.artifact — refuse the escape at the validator, confine at the load.
        art = changes["artifact"]
        if (os.sep in art or (os.altsep and os.altsep in art)
                or os.path.isabs(art) or ".." in art.replace("\\", "/").split("/")):
            die("changes.artifact must be a bare filename (no path separator, no "
                f"'..', not absolute); got {art!r}")
        sha = changes["sha256"]
        if (not isinstance(sha, str) or len(sha) != 64
                or any(c not in "0123456789abcdef" for c in sha)):
            die("changes.sha256 must be 64 lowercase hex chars (the sha256 of the "
                "changes.json bytes)")

    if "previous_run" in data:
        prev = data["previous_run"]
        if not isinstance(prev, dict):
            die(f"previous_run must be an object when present; got {type(prev).__name__}")
        run_dir = prev.get("run_dir")
        if not isinstance(run_dir, str) or not run_dir.strip():
            die("previous_run.run_dir must be a non-empty string")
        for key in ("title", "date"):
            if key in prev and not isinstance(prev[key], str):
                die(f"previous_run.{key} must be a string when present; "
                    f"got {type(prev[key]).__name__}")
        # isinstance guard first: an unhashable value (list/dict) would TypeError
        # on the `in` check and escape die()'s clean schema exit.
        if "verdict" in prev and (not isinstance(prev["verdict"], str)
                                  or prev["verdict"] not in SEVERITY):
            die(f"previous_run.verdict must be one of {', '.join(SEVERITY)}; "
                f"got {prev['verdict']!r}")
        if "verdict_sha256" in prev:
            sha = prev["verdict_sha256"]
            if (not isinstance(sha, str) or len(sha) != 64
                    or any(c not in "0123456789abcdef" for c in sha)):
                die("previous_run.verdict_sha256 must be 64 lowercase hex chars "
                    "when present (the sha256 of the prior verdict.json bytes)")

    if "amendments" in data:
        entries = data["amendments"]
        if not isinstance(entries, list):
            die(f"amendments must be a list when present; got {type(entries).__name__}")
        for index, entry in enumerate(entries):
            where = f"amendments[{index}]"
            if not isinstance(entry, dict):
                die(f"{where} must be an object")
            missing = [key for key in AMENDMENT_REQUIRED if key not in entry]
            if missing:
                die(f"{where} missing field(s): {', '.join(missing)}")
            for key in AMENDMENT_REQUIRED:
                if not isinstance(entry[key], str) or not entry[key].strip():
                    die(f"{where}: {key} must be a non-empty string")
            # Effect fields (what an amendment touches, since v1.12 P4). Each is
            # validated strictly WHEN PRESENT — an absent field checks nothing, so a
            # zero-effect entry (P1 compat) still passes. At most ONE effect field
            # per entry; the amend tooling enforces one-effect-per-invocation.
            if "field" in entry:
                # A `field` amendment records an effective-value change; only
                # `confidence` is defined, and both endpoints must be valid so
                # effective_confidence() can never surface garbage.
                if entry["field"] != "confidence":
                    die(f"{where}: field must be 'confidence' when present; "
                        f"got {entry['field']!r}")
                for key in ("from", "to"):
                    if key not in entry:
                        die(f"{where}: a confidence amendment needs both "
                            f"'from' and 'to'")
                    # isinstance guard first: an unhashable hand-edited value
                    # (list/dict) would TypeError on the `in` check and escape
                    # die()'s clean schema exit (mirrors previous_run.verdict above).
                    if (not isinstance(entry[key], str)
                            or entry[key] not in CONFIDENCE):
                        die(f"{where}: {key} must be one of "
                            f"{', '.join(sorted(CONFIDENCE))}; got {entry[key]!r}")
            if "caveat" in entry and (not isinstance(entry["caveat"], str)
                                      or not entry["caveat"].strip()):
                die(f"{where}: caveat must be a non-empty string when present")
            if "severity_note" in entry and (
                    not isinstance(entry["severity_note"], str)
                    or not entry["severity_note"].strip()):
                die(f"{where}: severity_note must be a non-empty string when present")
            # `on` scopes a severity_note to a finding; the strict title match is an
            # amend-time check (a verdict shouldn't fail validation over prose), so
            # here we only type-check.
            if "on" in entry and (not isinstance(entry["on"], str)
                                  or not entry["on"].strip()):
                die(f"{where}: on must be a non-empty string when present")
            effects = [k for k in ("field", "caveat", "severity_note") if k in entry]
            if len(effects) > 1:
                die(f"{where}: an amendment carries at most one effect field; "
                    f"got {', '.join(effects)}")

        # Chain consistency: walk the amendments in order tracking the effective
        # confidence (seeded from the board's own, already validated above) and
        # require each confidence change's `from` to equal the value in force at
        # that point. The amend CLI produces a correct chain by construction; this
        # catches a HAND-EDITED chain that would render false provenance, and turns
        # it into a clean schema exit — so gated paths never see a broken chain,
        # while effective_confidence() stays defensive for unvalidated render paths.
        # A from == to entry is left structurally legal (the CLI refuses to create
        # one; validate() doesn't care).
        effective = data.get("confidence")
        for index, entry in enumerate(entries):
            if isinstance(entry, dict) and entry.get("field") == "confidence":
                if entry.get("from") != effective:
                    die(f"amendments[{index}]: confidence change claims from "
                        f"{entry.get('from')!r} but the value in force here is "
                        f"{effective!r} (the amendment chain is inconsistent — "
                        "hand-edited?)")
                effective = entry.get("to")


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

    # Optional board-level lens preset (e.g. "software-architecture", "business-decision").
    # Used only to pick a lens-aware human label; the machine `verdict` is unaffected.
    if "lens_preset" in data and not isinstance(data["lens_preset"], str):
        die(f"lens_preset must be a string when present; got {type(data['lens_preset']).__name__}")

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

    _validate_lifecycle(data)


def effective_confidence(data: dict) -> tuple:
    """The confidence in force after amendments, with its provenance.

    Returns ``(value, entry_or_None)``: the LAST ``amendments[]`` entry that is a
    WELL-FORMED confidence change wins (its ``to`` is the value); with no such
    entry, ``(data["confidence"], None)`` — the board's own recorded confidence.

    Defensive by design: renderers (format_output.py, render_verdict.py) call this
    WITHOUT validate(), so an entry only counts when ``field == "confidence"`` AND
    ``to`` is a real CONFIDENCE token. A malformed entry (missing/garbage ``to``,
    non-dict) is ignored, so an unvalidated verdict falls back to the base
    confidence instead of crashing. validate() separately guarantees a clean chain
    for gated paths (see _validate_lifecycle). Renderers import this (via a same-dir
    ``import board_verdict``) so the amended value and its provenance are read from
    ONE place, not re-derived.
    """
    winner = None
    for entry in data.get("amendments", []) or []:
        if (isinstance(entry, dict) and entry.get("field") == "confidence"
                and entry.get("to") in CONFIDENCE):
            winner = entry
    if winner is not None:
        return winner["to"], winner
    return data["confidence"], None


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


def _has_finding_at_severity(data: dict, min_severity: str) -> bool:
    """True when the verdict carries at least one FINDING at or above `min_severity`
    (blocker > concern). A blocker satisfies any tier; a concern satisfies `concern`
    but not `blocker`. Dissent is a minority view, not a finding tier, so it never
    counts (D5-style: this is exposure of the existing structured containers, not new
    modeling). A non-list container counts as no findings — validate() already type-
    checks these, so this stays robust for a directly-called gate too."""
    rank = FINDING_SEVERITY[min_severity]
    blockers = data.get("blockers")
    if isinstance(blockers, list) and blockers:
        return True   # a blocker is the top finding tier — satisfies every min-severity
    if rank <= FINDING_SEVERITY["concern"]:
        concerns = data.get("concerns")
        if isinstance(concerns, list) and concerns:
            return True
    return False


def gate_outcome(data: dict, fail_on: str, min_severity: str = None):
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

    `min_severity` (v1.14 P1; 'blocker' | 'concern' | None) COMPOSES WITH `fail_on`:
    it is an ADDITIONAL condition for a FAIL, applied only after the verdict-token
    decision above lands on 'fail'. A fail then requires the verdict to also carry a
    finding at/above that tier; a caution/block verdict whose only findings are
    concerns/dissent does NOT fail under 'blocker' — it PASSES (downgraded), with a
    reason that names the missing tier. It can only turn a would-be fail into a pass;
    it never escalates a pass, and it never touches the abstain integrity checks (a
    refuted citation, a torn board, a verdict-vs-board contradiction all still abstain
    regardless), so the safety floor is unchanged. None = today's behavior exactly.
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
        # --min-severity narrows a would-be fail: the verdict must ALSO rest on a
        # finding at/above the named tier. Applied last so it composes with (never
        # replaces) the token threshold + abstain checks above.
        if min_severity is not None and not _has_finding_at_severity(data, min_severity):
            return "pass", (
                f"verdict '{data['verdict']}' meets threshold '{fail_on}' but carries no "
                f"'{min_severity}'-severity finding (--min-severity {min_severity}); "
                "not failed"
            )
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


def _amendments_summary(amendments: list) -> str:
    """`N (a confidence change, b caveat, c severity note)` — a count plus a
    per-kind breakdown, in a stable order. Zero-effect provenance-only entries
    fall into an `other` bucket so the parts always sum to N."""
    kinds = Counter()
    for entry in amendments:
        if not isinstance(entry, dict):
            kinds["other"] += 1
        elif entry.get("field") == "confidence":
            kinds["confidence change"] += 1
        elif "caveat" in entry:
            kinds["caveat"] += 1
        elif "severity_note" in entry:
            kinds["severity note"] += 1
        else:
            kinds["other"] += 1
    order = ("confidence change", "caveat", "severity note", "other")
    parts = [f"{kinds[k]} {k}" for k in order if kinds.get(k)]
    return f"{len(amendments)} ({', '.join(parts)})"


def summarize(data: dict) -> str:
    board = data["board"]
    ran = [s for s in board if not s.get("dropped")]
    dropped = [s for s in board if s.get("dropped")]
    seats_line = f"{len(ran)} ran"
    if dropped:
        names = ", ".join(s.get("seat", "?") for s in dropped)
        seats_line += f", {len(dropped)} dropped ({names})"
    amendments = data.get("amendments") or []
    # Provenance is shown ONLY when amendments exist; with none, this branch is
    # never taken and the verdict line is byte-identical to pre-v1.12 output.
    conf_value, conf_entry = effective_confidence(data)
    if amendments and conf_entry is not None:
        confidence_label = (
            f"{conf_value} confidence, amended from {conf_entry['from']} by "
            f"{conf_entry['author']} @ {conf_entry['timestamp']}"
        )
    else:
        confidence_label = f"{data['confidence']} confidence"
    lines = [
        f"title      : {data.get('title', '(untitled)')}",
        f"verdict    : {data['verdict']}"
        + (f" ({data['decision']})" if data.get("decision") else "")
        + f"  ({confidence_label})",
        f"unanimous  : {data.get('unanimous', 'n/a')}",
        f"rounds     : {data['rounds']}",
        f"seats      : {seats_line}",
        f"blockers   : {len(data.get('blockers', []))}",
    ]
    tally = _evidence_tally(data)
    if tally:
        parts = [f"{tally[k]} {k}" for k in ("verified", "unverified", "refuted", "unchecked") if tally.get(k)]
        lines.append(f"evidence   : {', '.join(parts)}")
    if amendments:
        lines.append(f"amendments : {_amendments_summary(amendments)}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# amend — human-owned, append-only verdict tuning (v1.12 P4)
# --------------------------------------------------------------------------- #


def _now_stamp() -> str:
    """ISO-8601 timestamp, overridable for determinism. Mirrors
    _conductor/constants.now_stamp but is inlined — this module is standalone."""
    return (os.environ.get("ADVISORY_BOARD_NOW_TS")
            or datetime.now().isoformat(timespec="seconds"))


def _file_sha256(path: str) -> "str | None":
    """sha256 of the file's raw bytes, or None if unreadable — the fingerprint the
    optimistic change guard compares. None (missing/unreadable) never equals a real
    digest, so the guard can't false-pass on a vanished target."""
    try:
        with open(path, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return None


def _cleanup(path: str) -> None:
    """Remove a tmp file, ignoring its absence — leave no scratch behind on failure."""
    try:
        os.unlink(path)
    except OSError:
        pass


def _finding_titles(data: dict) -> list:
    """Every blocker/concern `title`, in order — the valid targets for `--on`."""
    titles = []
    for key in ("blockers", "concerns"):
        for item in (data.get(key) or []):
            if isinstance(item, dict) and isinstance(item.get("title"), str):
                titles.append(item["title"])
    return titles


def cmd_amend(argv) -> int:
    """Append ONE human amendment to a run's verdict.json. Append-only: never
    rewrites existing entries, never touches board fields or data["confidence"]."""
    parser = argparse.ArgumentParser(
        prog="board_verdict.py amend",
        description="Append a human amendment to a run's verdict.json (append-only).")
    parser.add_argument("--run", required=True,
                        help="run directory containing verdict.json")
    parser.add_argument("--author", required=True, help="who is amending")
    parser.add_argument("--reason", required=True, help="why (recorded verbatim)")
    parser.add_argument("--confidence", choices=("low", "medium", "high"),
                        help="record a confidence change (effective value)")
    parser.add_argument("--caveat", help="attach a standing caveat")
    parser.add_argument("--severity-note", dest="severity_note",
                        help="attach a note about a finding's severity")
    parser.add_argument("--on", dest="on",
                        help="scope --severity-note to an existing finding title")
    args = parser.parse_args(argv)

    # Exactly one effect per invocation — the amendment trail stays one-fact-per-row.
    effects = [name for name, present in (
        ("--confidence", args.confidence is not None),
        ("--caveat", args.caveat is not None),
        ("--severity-note", args.severity_note is not None),
    ) if present]
    if len(effects) != 1:
        if not effects:
            die("amend needs exactly one effect: --confidence, --caveat, or "
                "--severity-note")
        die(f"amend takes exactly one effect per invocation; got {', '.join(effects)}")
    if args.on is not None and args.severity_note is None:
        die("--on scopes --severity-note; it can't be used on its own")

    if not os.path.isdir(args.run):
        die(f"--run: not a directory: {args.run}")
    # Resolve through any symlink so we read AND write the real target: os.replace on
    # a symlink path would swap the LINK for a regular file and orphan the target, so
    # we operate on realpath (and keep tmp in its dir for same-dir atomicity).
    path = os.path.realpath(os.path.join(args.run, "verdict.json"))
    baseline = _file_sha256(path)  # for the pre-replace change guard (fix: lost-update)
    data = load(path)  # validates before we touch it

    entry = {
        "author": args.author,
        "timestamp": _now_stamp(),
        "reason": args.reason,
    }
    if args.confidence is not None:
        current, _ = effective_confidence(data)  # value BEFORE this amendment
        if args.confidence == current:
            die(f"confidence is already {current!r}; nothing to amend "
                "(a no-op amendment is refused)")
        entry.update({"field": "confidence", "from": current, "to": args.confidence})
    elif args.caveat is not None:
        entry["caveat"] = args.caveat
    else:  # severity_note
        entry["severity_note"] = args.severity_note
        if args.on is not None:
            titles = _finding_titles(data)
            if args.on not in titles:
                available = "; ".join(titles) if titles else "(none)"
                die(f"--on {args.on!r} matches no blocker or concern title; "
                    f"available titles: {available}")
            entry["on"] = args.on

    data.setdefault("amendments", []).append(entry)  # append-only
    validate(data)  # re-check with the new entry in place

    # Write to a UNIQUE tmp in the target's own directory (same-dir keeps os.replace
    # atomic; unique avoids two concurrent amends clobbering one shared tmp), then
    # replace. On any OSError — incl. an unwritable dir at mkstemp — clean any tmp and
    # die cleanly rather than tracebacking.
    dest_dir = os.path.dirname(path) or "."
    try:
        orig_mode = os.stat(path).st_mode & 0o777
    except OSError:
        orig_mode = 0o644
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=dest_dir, prefix=".verdict.json.amend.",
                                   suffix=".tmp")
        # newline="" writes byte-exact (no platform \n → \r\n translation), so the
        # optimistic-concurrency guard — which reads the file in BINARY
        # (_file_sha256) — compares the same bytes it wrote. Without it a Windows
        # text-mode rewrite would diverge the on-disk bytes from the loaded baseline
        # and false-trip the guard. JSON is \n-only, so this is a POSIX no-op.
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        # Preserve the original file's permission bits (mkstemp makes 0600, which
        # would silently tighten verdict.json); fall back to 0644 if it was new.
        os.chmod(tmp, orig_mode)
        # Best-effort optimistic guard (a narrowing, NOT a lock): if the file changed
        # since we loaded it, another amend raced us — refuse rather than lose theirs.
        if _file_sha256(path) != baseline:
            die("verdict.json changed while amending — re-run")
        os.replace(tmp, path)
    except OSError as exc:
        if tmp is not None:
            _cleanup(tmp)
        die(f"cannot write verdict.json: {exc}")
    except BaseException:
        # die() raises SystemExit (the race guard): drop the tmp before it propagates.
        if tmp is not None:
            _cleanup(tmp)
        raise

    kind = ("confidence" if args.confidence is not None
            else "caveat" if args.caveat is not None else "severity note")
    print(f"amended: appended {kind} amendment by {args.author} to {path}")
    print(summarize(data))
    return EXIT_OK


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    # Route the `amend` subcommand BEFORE the legacy parser so every other
    # invocation stays byte-identical. A file literally named "amend" is an
    # accepted known edge (not special-cased).
    if argv and argv[0] == "amend":
        return cmd_amend(argv[1:])

    parser = argparse.ArgumentParser(description="Validate / gate an advisory-board verdict.json.")
    parser.add_argument("path", nargs="?", default="verdict.json", help="path to verdict.json (default: verdict.json)")
    parser.add_argument("--gate", action="store_true", help="exit 1 when the verdict meets the fail threshold (3 to abstain)")
    parser.add_argument(
        "--fail-on", choices=("caution", "block"), default="block", help="threshold for --gate (default: block)"
    )
    parser.add_argument(
        "--min-severity", dest="min_severity", choices=("blocker", "concern"), default=None,
        help="compose with --gate/--fail-on: a fail must ALSO rest on a finding at/above "
             "this tier (blocker > concern; dissent never counts). With 'blocker', a "
             "caution/block verdict whose only findings are concerns/dissent PASSES "
             "instead of failing. Only narrows a fail to a pass — abstain (refuted "
             "citation, torn board, verdict-vs-board contradiction) is unaffected. "
             "Absent = today's behavior (the verdict token alone drives the gate).")
    parser.add_argument("--json", dest="as_json", action="store_true", help="echo normalized JSON and exit")
    args = parser.parse_args(argv)

    data = load(args.path)

    if args.as_json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return EXIT_OK

    print(summarize(data))

    if args.gate:
        outcome, reason = gate_outcome(data, args.fail_on, args.min_severity)
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

#!/usr/bin/env python3
"""Validate an advisory-board changes.json — the revision artifact of record (v1.13).

`changes.json` is the machine-readable edit → finding mapping produced by
`run_board.py run --output revised-draft`: it records which board findings each
edit resolved, which the revision seat left unresolved (conflicts), and the
sha256 pins binding the revised draft and the original source. The verdict points
at it (`verdict.json.changes = {artifact, sha256}`); this file is the source of
truth for the revision.

Examples:
  board_changes.py changes.json          validate + print a summary
  board_changes.py changes.json --json    echo normalized JSON

Exit codes:
  0  ok
  2  usage or schema error

Schema: `advisory-board/changes@1`. Model-authored fields are limited to
`summary`/`resolves`/`note`; everything structural (`n`, `status`, the shas,
`source_type`, `revision_seat`, `title`, `endorsements`) is conductor-computed.
This validator is strict — unknown top-level keys are refused, field types are
exact, locator shapes are checked, and `resolves`/`findings` list entries name a
finding by its `{list, index, title}` composite (list ∈ {blockers, concerns},
index a 0-based position; the conductor cross-asserts index+title against the
verdict at write time — the shape check here is bounds-independent).

`endorsements[]` (D13/P4) carries the per-target board vote, one row per seat per
target: `{seat, edit_n|unresolved_n, position, note?, dropped?}`. Each row names
exactly one target (an edit by `edit_n` OR an unresolved conflict by
`unresolved_n`), a `position` ∈ {ENDORSE, OBJECT, ABSTAIN}, an optional `note`
(recorded for OBJECT and drop reasons), and an optional `dropped: true` marker for
a seat whose endorsement spawn failed (its rows are the ABSTAIN fallback). The
conductor BUILDS these rows from the seats' parsed tokens — the model never authors
a row — but the validator still checks the built shape exactly.

The conductor runs `validate()` before writing `changes.json`; anything invalid
takes the reject path (`changes-rejected.json`). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

SCHEMA = "advisory-board/changes@1"
# The two finding lists a revision edit may resolve. Per D9 these are blockers and
# concerns ONLY — `caveats[]` is a plain-strings bucket with no titles/evidence,
# and dissent entries are not editable findings.
RESOLVE_LISTS = ("blockers", "concerns")
# The only `status` value @1 defines. It is conductor-computed from the diff
# reconciliation (INV-1), never model-asserted — but the validator still checks
# the shape so a hand-authored/fuzzed changes.json can't smuggle another value.
STATUSES = ("applied",)
# `source_type` (D12) drives redline-vs-patch downstream (P3). Recorded here so a
# `--from-recipe` replay and any consumer read the resolved value from one place.
SOURCE_TYPES = ("prose", "code")

# Strict key sets. Unknown keys are refused so a fabricated/fuzzed artifact can't
# smuggle fields past the validator (mirrors board_verdict's strict-when-present
# discipline, extended to the whole document since changes.json is conductor-born).
TOP_LEVEL_KEYS = {
    "schema", "title", "source", "revised", "source_type", "revision_seat",
    "edits", "unresolved", "endorsements",
}
TOP_LEVEL_REQUIRED = (
    "schema", "title", "source", "revised", "source_type", "revision_seat",
    "edits", "unresolved", "endorsements",
)
EDIT_KEYS = {"n", "locator", "summary", "resolves", "status"}
UNRESOLVED_KEYS = {"findings", "reason", "note"}
# An endorsement row (D13/P4). Every row names its SEAT, exactly ONE target (an
# edit by `edit_n` OR an unresolved conflict by `unresolved_n` — a seat may object
# to how a conflict was characterized), and a `position` ∈ ENDORSE/OBJECT/ABSTAIN.
# `note` is optional (recorded for OBJECT, or the drop reason). `dropped` is an
# optional `true` marker recorded when the seat's endorsement spawn failed and its
# rows are the ABSTAIN fallback.
ENDORSEMENT_KEYS = {"seat", "edit_n", "unresolved_n", "position", "note", "dropped"}
ENDORSEMENT_POSITIONS = ("ENDORSE", "OBJECT", "ABSTAIN")
FINDING_REF_KEYS = {"list", "index", "title"}
LINES_LOCATOR_KEYS = {"kind", "from", "to"}
INSERT_LOCATOR_KEYS = {"kind", "line"}

EXIT_OK = 0
EXIT_SCHEMA = 2


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(EXIT_SCHEMA)


def _is_sha256(value) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _is_int(value) -> bool:
    """A real integer, not a bool (bool is an int subclass in Python)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _is_bare_filename(value) -> bool:
    """True iff `value` is a BARE filename safe to join onto the run dir: a
    non-empty string (after strip) with no path separator (os.sep / os.altsep), no
    `..` component, and not absolute. `revised.artifact` and the verdict's
    `changes.artifact` pointer are joined onto run_dir by the renderer; an absolute
    or `../escape` value would read outside the run dir (the islink checks miss
    absolute targets and parent-dir symlinks), so both layers refuse anything that
    is not a bare filename — matching the fixed-filename precedent
    (revise.prior_source_text)."""
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped or stripped != value:
        return False
    if os.sep in value or (os.altsep and os.altsep in value):
        return False
    if os.path.isabs(value):
        return False
    return ".." not in value.replace("\\", "/").split("/")


def _validate_finding_ref(ref, where: str) -> None:
    """A `{list, index, title}` composite finding locator (D9; model-supplied, but
    the conductor CROSS-asserts it against the verdict before write —
    `verdict[list][index].title == title`). Strict SHAPE only here — the bounds and
    index/title cross-check need the verdict, which this standalone validator does
    not have, so it checks `index` is a non-negative int and leaves the cross-assert
    to the conductor. All three keys are required; unknown keys are refused."""
    if not isinstance(ref, dict):
        die(f"{where} must be an object with 'list', 'index' and 'title'")
    unknown = set(ref) - FINDING_REF_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    missing = [k for k in ("list", "index", "title") if k not in ref]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    if ref["list"] not in RESOLVE_LISTS:
        die(f"{where}.list must be one of {', '.join(RESOLVE_LISTS)}; got {ref['list']!r}")
    if not _is_int(ref["index"]) or ref["index"] < 0:
        die(f"{where}.index must be a non-negative integer (0-based position in its "
            f"list); got {ref['index']!r}")
    if not isinstance(ref["title"], str) or not ref["title"].strip():
        die(f"{where}.title must be a non-empty string")


def _validate_locator(loc, where: str) -> None:
    """An edit locator against the ORIGINAL source (model-supplied, conductor-
    validated against the diff — see INV-1 reconciliation). Two shapes:
      * {"kind": "lines", "from": N, "to": M}   — a 1-based inclusive line range
      * {"kind": "insert-after", "line": N}      — a pure insertion (0 = top of file)
    """
    if not isinstance(loc, dict):
        die(f"{where} must be an object")
    kind = loc.get("kind")
    if kind == "lines":
        unknown = set(loc) - LINES_LOCATOR_KEYS
        if unknown:
            die(f"{where}: unknown key(s) for a 'lines' locator: {', '.join(sorted(unknown))}")
        for key in ("from", "to"):
            if key not in loc:
                die(f"{where}: a 'lines' locator needs both 'from' and 'to'")
            if not _is_int(loc[key]) or loc[key] < 1:
                die(f"{where}.{key} must be a positive integer (1-based); got {loc[key]!r}")
        if loc["to"] < loc["from"]:
            die(f"{where}: 'to' ({loc['to']}) must be >= 'from' ({loc['from']})")
    elif kind == "insert-after":
        unknown = set(loc) - INSERT_LOCATOR_KEYS
        if unknown:
            die(f"{where}: unknown key(s) for an 'insert-after' locator: "
                f"{', '.join(sorted(unknown))}")
        if "line" not in loc:
            die(f"{where}: an 'insert-after' locator needs 'line'")
        # 0 is allowed: insert-after line 0 means "at the top of the file".
        if not _is_int(loc["line"]) or loc["line"] < 0:
            die(f"{where}.line must be a non-negative integer (0 = top of file); "
                f"got {loc['line']!r}")
    else:
        die(f"{where}.kind must be 'lines' or 'insert-after'; got {kind!r}")


def _validate_edit(edit, index: int) -> None:
    where = f"edits[{index}]"
    if not isinstance(edit, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("n", "locator", "summary", "resolves", "status") if k not in edit]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(edit) - EDIT_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    if not _is_int(edit["n"]) or edit["n"] < 1:
        die(f"{where}.n must be a positive integer; got {edit['n']!r}")
    _validate_locator(edit["locator"], f"{where}.locator")
    if not isinstance(edit["summary"], str) or not edit["summary"].strip():
        die(f"{where}.summary must be a non-empty string")
    if edit["status"] not in STATUSES:
        die(f"{where}.status must be one of {', '.join(STATUSES)}; got {edit['status']!r}")
    resolves = edit["resolves"]
    if not isinstance(resolves, list) or not resolves:
        die(f"{where}.resolves must be a non-empty list of finding refs")
    for j, ref in enumerate(resolves):
        _validate_finding_ref(ref, f"{where}.resolves[{j}]")


def _validate_unresolved(entry, index: int) -> None:
    where = f"unresolved[{index}]"
    if not isinstance(entry, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("findings", "reason", "note") if k not in entry]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(entry) - UNRESOLVED_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    findings = entry["findings"]
    if not isinstance(findings, list) or not findings:
        die(f"{where}.findings must be a non-empty list of finding refs")
    for j, ref in enumerate(findings):
        _validate_finding_ref(ref, f"{where}.findings[{j}]")
    for key in ("reason", "note"):
        if not isinstance(entry[key], str) or not entry[key].strip():
            die(f"{where}.{key} must be a non-empty string")


def _validate_endorsement(entry, index: int) -> None:
    # An endorsement row (D13/P4). The conductor BUILDS these from the seats' parsed
    # tokens — the model never authors a row — but the validator is the last strict
    # gate before write, so it checks the built shape exactly. Each row names its
    # seat, EXACTLY ONE target (`edit_n` XOR `unresolved_n`), and a position; `note`
    # and the `dropped` marker are optional.
    where = f"endorsements[{index}]"
    if not isinstance(entry, dict):
        die(f"{where} must be an object")
    if "seat" not in entry or "position" not in entry:
        die(f"{where} missing field(s): "
            f"{', '.join(k for k in ('seat', 'position') if k not in entry)}")
    unknown = set(entry) - ENDORSEMENT_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    if not isinstance(entry["seat"], str) or not entry["seat"].strip():
        die(f"{where}.seat must be a non-empty string")
    # Exactly one target: an edit (`edit_n`) OR an unresolved conflict
    # (`unresolved_n`). Neither and both are refused — a row must vote on one target.
    has_edit = "edit_n" in entry
    has_unres = "unresolved_n" in entry
    if has_edit == has_unres:
        die(f"{where} must name exactly one of 'edit_n' or 'unresolved_n'")
    target_field = "edit_n" if has_edit else "unresolved_n"
    if not _is_int(entry[target_field]) or entry[target_field] < 1:
        die(f"{where}.{target_field} must be a positive integer; got {entry[target_field]!r}")
    if entry["position"] not in ENDORSEMENT_POSITIONS:
        die(f"{where}.position must be ENDORSE|OBJECT|ABSTAIN; got {entry['position']!r}")
    if "note" in entry and not isinstance(entry["note"], str):
        die(f"{where}.note must be a string when present")
    # `dropped`, when present, is a strict `true` marker (a dropped endorsement
    # seat's ABSTAIN fallback). `false`/other values are refused — its presence IS
    # the signal, so it is only ever recorded as true. A dropped row must ALSO be
    # what the conductor emits: an ABSTAIN carrying the drop reason in `note` —
    # a hand-authored dropped ENDORSE/OBJECT would otherwise count as a vote in
    # the rendered tally while claiming the seat never voted.
    if "dropped" in entry:
        if entry["dropped"] is not True:
            die(f"{where}.dropped must be true when present; got {entry['dropped']!r}")
        if entry["position"] != "ABSTAIN":
            die(f"{where}: a dropped row must have position ABSTAIN; got {entry['position']!r}")
        if not isinstance(entry.get("note"), str) or not entry["note"].strip():
            die(f"{where}: a dropped row must carry the drop reason in a non-empty note")


def _validate_source_pin(obj, where: str, artifact_field: str) -> None:
    if not isinstance(obj, dict):
        die(f"{where} must be an object")
    expected = {artifact_field, "sha256"} if artifact_field else {"name", "sha256"}
    unknown = set(obj) - expected
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    label = artifact_field or "name"
    if not isinstance(obj.get(label), str) or not obj[label].strip():
        die(f"{where}.{label} must be a non-empty string")
    # The `revised.artifact` is joined onto run_dir by the renderer, so it must be
    # a BARE filename — an absolute path or `..` would read outside the run dir
    # (the renderer's islink check misses absolute targets / parent-dir symlinks).
    # `source.name` is display-only (never path-joined), so it is not constrained.
    if label == "artifact" and not _is_bare_filename(obj[label]):
        die(f"{where}.artifact must be a bare filename (no path separator, no '..', "
            f"not absolute); got {obj[label]!r}")
    if not _is_sha256(obj.get("sha256")):
        die(f"{where}.sha256 must be 64 lowercase hex chars")


def validate(data: dict) -> None:
    """Strict schema check for a changes.json document. A malformed artifact of
    record must never quietly pass — the conductor rejects on any failure here."""
    if not isinstance(data, dict):
        die("top level must be a JSON object")
    unknown = set(data) - TOP_LEVEL_KEYS
    if unknown:
        die(f"unknown top-level key(s): {', '.join(sorted(unknown))}")
    missing = [k for k in TOP_LEVEL_REQUIRED if k not in data]
    if missing:
        die(f"missing required field(s): {', '.join(missing)}")

    if data["schema"] != SCHEMA:
        die(f"schema must be {SCHEMA!r}; got {data['schema']!r}")
    if not isinstance(data["title"], str) or not data["title"].strip():
        die("title must be a non-empty string")
    _validate_source_pin(data["source"], "source", "name")
    _validate_source_pin(data["revised"], "revised", "artifact")
    if data["source_type"] not in SOURCE_TYPES:
        die(f"source_type must be one of {', '.join(SOURCE_TYPES)}; got {data['source_type']!r}")
    if not isinstance(data["revision_seat"], str) or not data["revision_seat"].strip():
        die("revision_seat must be a non-empty string")

    edits = data["edits"]
    if not isinstance(edits, list):
        die("edits must be a list")
    for index, edit in enumerate(edits):
        _validate_edit(edit, index)
    # `n` must be a dense 1-based sequence in edit order (conductor-computed).
    ns = [e["n"] for e in edits if isinstance(e, dict)]
    if ns != list(range(1, len(edits) + 1)):
        die(f"edits[].n must be a dense 1-based sequence in order; got {ns}")

    unresolved = data["unresolved"]
    if not isinstance(unresolved, list):
        die("unresolved must be a list")
    for index, entry in enumerate(unresolved):
        _validate_unresolved(entry, index)

    endorsements = data["endorsements"]
    if not isinstance(endorsements, list):
        die("endorsements must be a list")
    for index, entry in enumerate(endorsements):
        _validate_endorsement(entry, index)
    # Cross-row endorsement checks (need the whole doc, like the dense-n edit check
    # above): every vote must target an EXISTING edit/unresolved entry (upper bound),
    # and no (seat, target-kind, n) may repeat — one seat votes on each target at
    # most once. The conductor never emits an out-of-range or duplicate row (it
    # builds exactly one row per seat per target from _expected_targets), so this is
    # a strict gate against a hand-authored or corrupted file, not a pipeline path.
    n_edits = len(edits)
    n_unresolved = len(unresolved)
    seen_rows: set = set()
    for index, entry in enumerate(endorsements):
        where = f"endorsements[{index}]"
        if "edit_n" in entry:
            kind, n, bound = "edit_n", entry["edit_n"], n_edits
        else:
            kind, n, bound = "unresolved_n", entry["unresolved_n"], n_unresolved
        if n > bound:
            die(f"{where}.{kind} = {n} is out of range; there {'is' if bound == 1 else 'are'} "
                f"{bound} {kind[:-2].replace('_', ' ')} target(s)")
        key = (entry["seat"], kind, n)
        if key in seen_rows:
            die(f"{where} is a duplicate endorsement row: seat {entry['seat']!r} already "
                f"voted on {kind}={n} (one vote per seat per target)")
        seen_rows.add(key)


def load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        die(f"{path}: not found")
    except json.JSONDecodeError as exc:
        die(f"{path}: invalid JSON ({exc})")
    except OSError as exc:
        die(f"{path}: cannot read ({exc})")
    validate(data)
    return data


def summarize(data: dict) -> str:
    n_edits = len(data.get("edits") or [])
    n_unresolved = len(data.get("unresolved") or [])
    n_endorse = len(data.get("endorsements") or [])
    lines = [
        f"title        : {data.get('title', '(untitled)')}",
        f"source       : {data['source']['name']} (sha256:{data['source']['sha256'][:12]}…)",
        f"revised      : {data['revised']['artifact']} (sha256:{data['revised']['sha256'][:12]}…)",
        f"source type  : {data['source_type']}",
        f"revision seat: {data['revision_seat']}",
        f"edits        : {n_edits}",
        f"unresolved   : {n_unresolved}"
        + ("  (conflicts — surfaced, not fatal; a human decides)" if n_unresolved else ""),
        f"endorsements : {n_endorse}",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="board_changes.py",
        description="Validate an advisory-board changes.json (the revision artifact).")
    parser.add_argument("path", nargs="?", default="changes.json",
                        help="path to changes.json (default: changes.json)")
    parser.add_argument("--json", dest="as_json", action="store_true",
                        help="echo normalized JSON and exit")
    args = parser.parse_args(argv)

    data = load(args.path)
    if args.as_json:
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return EXIT_OK
    print(summarize(data))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())

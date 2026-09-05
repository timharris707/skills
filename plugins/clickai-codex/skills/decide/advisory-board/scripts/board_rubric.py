#!/usr/bin/env python3
"""Validate an advisory-board rubric.json — the pre-round artifact of record (v1.15).

`rubric.json` is the weighted CRITERIA the board agreed BEFORE it opined: a
proposal fan-out (every seat proposes 3–7 weighted criteria) plus a mechanically-
reconciled CHAIR merge (one board seat merges the proposals into one weighted
rubric). It is written at chair-merge time — after egress consent (RH-1), before
the opinion rounds that inject it — so it survives a later scoring failure. The
verdict points at it (`verdict.json.rubric = {artifact, sha256}`, a P4 pointer);
this file is the source of truth for the rubric.

Examples:
  board_rubric.py rubric.json          validate + print a summary
  board_rubric.py rubric.json --json    echo normalized JSON

Exit codes:
  0  ok
  2  usage or schema error

Schema: `advisory-board/rubric@1`. Model-authored fields are ONLY the prose — the
criterion/proposal `title` and `description`, and each dropped proposal's `reason`.
EVERYTHING structural is conductor-computed: the criterion ids (`c1`…`cN`), the
proposal ids (`p1`…`pN`), the subsumes/dropped partition, the integer-percentage
weights, the template versions/shas. This validator is strict — unknown top-level
keys are refused, field types are exact, and the two invariants the conductor
enforces at write time are RE-CHECKED here as the last gate before any consumer
trusts the file:

  * PARTITION (D15): every conductor-minted proposal-id appears EXACTLY ONCE across
    (the union of all criteria `subsumes` lists) ∪ (the `dropped` list); no phantom
    id (an id not in `proposals`); no merged criterion with an empty `subsumes`.
  * WEIGHT-SUM (D18): the merged criteria's integer weights sum to EXACTLY 100 —
    the codebase's FIRST numeric-sum invariant. Stated loudly here; reject-on-
    violation. The weights are conductor-validated integer percentages, never
    model-asserted.

The conductor runs `validate()` before writing `rubric.json`; anything invalid takes
the refusal path (`rubric-rejected.json` + a non-zero exit — the run cannot proceed
to a meaningful board without a rubric). Standard library only.

isinstance guards precede every membership (`in`) check, deliberately: an unhashable
hand-authored value (a list/dict where a scalar belongs) would otherwise TypeError
on the `in` and escape die()'s clean schema exit 2 (the `board_verdict.py`
TypeError-on-unhashable idiom the roadmap's "Later" flags — NOT repeated here).
"""
from __future__ import annotations

import argparse
import json
import re
import sys

SCHEMA = "advisory-board/rubric@1"

# Strict key sets. Unknown keys are refused so a fabricated/fuzzed artifact can't
# smuggle fields past the validator (mirrors board_changes' strict discipline —
# rubric.json is conductor-born, so the whole document is strict).
TOP_LEVEL_KEYS = {
    "schema", "title", "chair_seat",
    "rubric_proposal_template", "rubric_proposal_template_sha256",
    "rubric_chair_template", "rubric_chair_template_sha256",
    "criteria", "dropped", "proposals",
}
TOP_LEVEL_REQUIRED = (
    "schema", "title", "chair_seat",
    "rubric_proposal_template", "rubric_proposal_template_sha256",
    "rubric_chair_template", "rubric_chair_template_sha256",
    "criteria", "dropped", "proposals",
)
CRITERION_KEYS = {"id", "title", "description", "weight", "subsumes"}
DROPPED_KEYS = {"proposal_id", "seat", "title", "reason"}
PROPOSAL_KEYS = {"proposal_id", "seat", "title", "weight"}

# The exact percentage the merged criterion weights must sum to (D18).
WEIGHT_SUM = 100

_CRITERION_ID = re.compile(r"^c[1-9][0-9]*$")
_PROPOSAL_ID = re.compile(r"^p[1-9][0-9]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

EXIT_OK = 0
EXIT_SCHEMA = 2


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(EXIT_SCHEMA)


def _is_int(value) -> bool:
    """A real integer, not a bool (bool is an int subclass in Python)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _nonempty_str(value, where: str) -> None:
    if not isinstance(value, str) or not value.strip():
        die(f"{where} must be a non-empty string")


def _validate_proposal_id(value, where: str) -> None:
    """A conductor-minted proposal id: `p` + a positive integer (p1, p2, …). The
    isinstance guard precedes the regex — a non-string (unhashable or otherwise)
    dies cleanly instead of raising inside `re`."""
    if not isinstance(value, str):
        die(f"{where} must be a proposal-id string (p1, p2, …); got {value!r}")
    if not _PROPOSAL_ID.match(value):
        die(f"{where} must match p<positive-int> (p1, p2, …); got {value!r}")


def _validate_criterion(crit, index: int) -> None:
    where = f"criteria[{index}]"
    if not isinstance(crit, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("id", "title", "description", "weight", "subsumes")
               if k not in crit]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(crit) - CRITERION_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    # id: c1…cN. isinstance guard before the regex.
    if not isinstance(crit["id"], str) or not _CRITERION_ID.match(crit["id"]):
        die(f"{where}.id must match c<positive-int> (c1, c2, …); got {crit['id']!r}")
    _nonempty_str(crit["title"], f"{where}.title")
    _nonempty_str(crit["description"], f"{where}.description")
    # A merged criterion weighted at NOTHING is a soundness smell (it still names a
    # subsumed proposal but contributes nothing to scoring), so require weight >= 1 —
    # matching rubric._validate_chair_weight (write-time). The sum-to-100 invariant
    # alone would accept a 0 among positives.
    if not _is_int(crit["weight"]) or crit["weight"] < 1:
        die(f"{where}.weight must be a positive integer percentage (>= 1); got {crit['weight']!r}")
    subsumes = crit["subsumes"]
    if not isinstance(subsumes, list) or not subsumes:
        die(f"{where}.subsumes must be a non-empty list of proposal ids (every merged "
            "criterion folds in at least one proposal)")
    for j, pid in enumerate(subsumes):
        _validate_proposal_id(pid, f"{where}.subsumes[{j}]")


def _validate_dropped(entry, index: int) -> None:
    where = f"dropped[{index}]"
    if not isinstance(entry, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("proposal_id", "seat", "title", "reason") if k not in entry]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(entry) - DROPPED_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    _validate_proposal_id(entry["proposal_id"], f"{where}.proposal_id")
    _nonempty_str(entry["seat"], f"{where}.seat")
    # title is display-only provenance (the dropped proposal's title); a non-empty
    # string, consistent with the criterion/proposal titles.
    _nonempty_str(entry["title"], f"{where}.title")
    _nonempty_str(entry["reason"], f"{where}.reason")


def _validate_proposal(entry, index: int) -> None:
    where = f"proposals[{index}]"
    if not isinstance(entry, dict):
        die(f"{where} must be an object")
    missing = [k for k in ("proposal_id", "seat", "title", "weight") if k not in entry]
    if missing:
        die(f"{where} missing field(s): {', '.join(missing)}")
    unknown = set(entry) - PROPOSAL_KEYS
    if unknown:
        die(f"{where}: unknown key(s): {', '.join(sorted(unknown))}")
    _validate_proposal_id(entry["proposal_id"], f"{where}.proposal_id")
    _nonempty_str(entry["seat"], f"{where}.seat")
    _nonempty_str(entry["title"], f"{where}.title")
    # The proposal's ORIGINAL proposed weight (a seat's own relative importance) is a
    # positive number — it is NOT re-weighted to an integer percentage (that is the
    # merged criterion's weight). A bool is refused.
    w = entry["weight"]
    if isinstance(w, bool) or not isinstance(w, (int, float)):
        die(f"{where}.weight must be a number; got {w!r}")
    if w != w or w in (float("inf"), float("-inf")):
        die(f"{where}.weight must be a finite number; got {w!r}")
    if w <= 0:
        die(f"{where}.weight must be positive; got {w!r}")


def validate(data: dict) -> None:
    """Strict schema check for a rubric.json document. A malformed artifact of record
    must never quietly pass — the conductor refuses the run on any failure here."""
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
    _nonempty_str(data["title"], "title")
    _nonempty_str(data["chair_seat"], "chair_seat")
    for key in ("rubric_proposal_template", "rubric_chair_template"):
        _nonempty_str(data[key], key)
    for key in ("rubric_proposal_template_sha256", "rubric_chair_template_sha256"):
        # isinstance guard before the regex match (unhashable-safe, though a sha is a
        # string; the guard also gives the clean 'must be a string' message).
        if not isinstance(data[key], str) or not _SHA256.match(data[key]):
            die(f"{key} must be 64 lowercase hex chars")

    criteria = data["criteria"]
    if not isinstance(criteria, list) or not criteria:
        die("criteria must be a non-empty list")
    for index, crit in enumerate(criteria):
        _validate_criterion(crit, index)
    # Criterion ids must be a dense c1…cN sequence in order (conductor-computed).
    cids = [c["id"] for c in criteria if isinstance(c, dict)]
    if cids != [f"c{n}" for n in range(1, len(criteria) + 1)]:
        die(f"criteria[].id must be a dense c1…cN sequence in order; got {cids}")

    dropped = data["dropped"]
    if not isinstance(dropped, list):
        die("dropped must be a list")
    for index, entry in enumerate(dropped):
        _validate_dropped(entry, index)

    proposals = data["proposals"]
    if not isinstance(proposals, list) or not proposals:
        die("proposals must be a non-empty list")
    for index, entry in enumerate(proposals):
        _validate_proposal(entry, index)
    # Proposal ids must be a dense p1…pN sequence in order (conductor-minted).
    pids = [p["proposal_id"] for p in proposals if isinstance(p, dict)]
    if pids != [f"p{n}" for n in range(1, len(proposals) + 1)]:
        die(f"proposals[].proposal_id must be a dense p1…pN sequence in order; got {pids}")

    # THE PARTITION INVARIANT (D15): every minted proposal id appears EXACTLY ONCE
    # across (∪ subsumes) ∪ dropped; no phantom id; no double-claim. The
    # per-criterion check already refused an empty subsumes list, so coverage here is
    # over the whole set. This needs the whole doc (like the dense-id checks above),
    # so it runs after the per-entry validation.
    # PARITY NOTE: the same invariant is enforced at write time by
    # rubric.reconcile_partition. The duplication is deliberate defense-in-depth
    # across a trust boundary (write-time there; read-time here as the last gate) and
    # is NOT collapsed — but the two must stay in lockstep. A parity test
    # (tests/test_run_board.py) asserts a partition-violating doc is rejected by BOTH
    # and a valid doc accepted by both.
    valid_ids = set(pids)
    seen: dict = {}   # id -> where first claimed (for the double-claim message)
    for ci, crit in enumerate(criteria):
        for pid in crit["subsumes"]:
            where = f"criteria[{ci}].subsumes"
            if pid not in valid_ids:
                die(f"{where} names proposal id {pid!r}, which is not in proposals[] "
                    "(a phantom id is refused)")
            if pid in seen:
                die(f"{where} claims proposal id {pid!r} again — already claimed by "
                    f"{seen[pid]} (every proposal must appear EXACTLY ONCE across "
                    "subsumes ∪ dropped)")
            seen[pid] = where
    # Provenance of each proposal id → the conductor-recorded (seat, title) from
    # proposals[]. build_rubric copies these from the minted proposal, so a
    # well-formed rubric.json ALWAYS agrees; a hand-edited one that changed a dropped
    # entry's seat/title (to misattribute who proposed a dropped criterion, or to
    # relabel it) must fail here — dropped[].seat/title are cross-checked, not just
    # type-checked. Keyed by the already-validated proposal_id string (hashable).
    provenance = {p["proposal_id"]: (p["seat"], p["title"])
                  for p in proposals if isinstance(p, dict)}
    for di, entry in enumerate(dropped):
        pid = entry["proposal_id"]
        where = f"dropped[{di}]"
        if pid not in valid_ids:
            die(f"{where} names proposal id {pid!r}, which is not in proposals[] "
                "(a phantom id is refused)")
        if pid in seen:
            die(f"{where} claims proposal id {pid!r} again — already claimed by "
                f"{seen[pid]} (every proposal must appear EXACTLY ONCE across "
                "subsumes ∪ dropped)")
        seen[pid] = where
        # Cross-check the dropped entry's provenance against the ground-truth
        # proposal it names (both were validated as non-empty strings above).
        true_seat, true_title = provenance[pid]
        if entry["seat"] != true_seat:
            die(f"{where}.seat is {entry['seat']!r} but proposal {pid} was proposed by "
                f"{true_seat!r} in proposals[] (dropped provenance must match the "
                "proposal it names)")
        if entry["title"] != true_title:
            die(f"{where}.title is {entry['title']!r} but proposal {pid}'s title in "
                f"proposals[] is {true_title!r} (dropped provenance must match the "
                "proposal it names)")
    missing_ids = [pid for pid in pids if pid not in seen]
    if missing_ids:
        die(f"proposal id(s) {', '.join(missing_ids)} appear in NEITHER a merged "
            "criterion's subsumes list NOR the dropped list — every proposal must be "
            "accounted for exactly once (the partition must be complete; D15)")

    # THE WEIGHT-SUM INVARIANT (D18) — the codebase's FIRST numeric-sum invariant,
    # stated LOUDLY. The merged criteria's integer-percentage weights must sum to
    # EXACTLY 100. Reject-on-violation: the board scores against a real 100% partition
    # of importance, never a set that "roughly" adds up.
    weight_sum = sum(c["weight"] for c in criteria)
    if weight_sum != WEIGHT_SUM:
        die(f"the merged criteria weights sum to {weight_sum}, not {WEIGHT_SUM} — the "
            f"weights must be integer percentages summing to EXACTLY {WEIGHT_SUM} (D18)")


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
    criteria = data.get("criteria") or []
    dropped = data.get("dropped") or []
    proposals = data.get("proposals") or []
    lines = [
        f"title        : {data.get('title', '(untitled)')}",
        f"chair seat   : {data.get('chair_seat', '?')}",
        f"proposals    : {len(proposals)}",
        f"criteria     : {len(criteria)}",
        f"dropped      : {len(dropped)}",
        f"weight sum   : {sum(c.get('weight', 0) for c in criteria if isinstance(c, dict))}%",
        "",
        "Merged criteria:",
    ]
    for c in criteria:
        if not isinstance(c, dict):
            continue
        subsumes = ", ".join(c.get("subsumes") or [])
        lines.append(f"  {c.get('id')}. {c.get('title')} — {c.get('weight')}% "
                     f"(subsumes {subsumes})")
    return "\n".join(lines)


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="board_rubric.py",
        description="Validate an advisory-board rubric.json (the pre-round rubric artifact).")
    parser.add_argument("path", nargs="?", default="rubric.json",
                        help="path to rubric.json (default: rubric.json)")
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

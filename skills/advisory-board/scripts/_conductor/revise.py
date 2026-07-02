"""--revise (v1.12 #1): re-review a revised draft with the prior run's verdict
as context.

Loads the prior run's verdict (and recipe, when present), recovers the prior
source bytes where possible, and builds the revision material injected into the
round-1 prompts: a MECHANICAL digest of the prior verdict (tokens, titles,
citations — no re-reasoning, §11) plus a unified diff from the previously
reviewed draft to the current source. The material lands inside the packet
blobs, so the egress consent hash covers every added byte automatically.

Prior-source recovery, in order, each sha-verified against the prior recipe's
`source_sha256` (a failed check falls through, loudly noted):
  1. `source-material.txt` in the prior run dir (persisted since v1.12);
  2. extraction from a persisted `prompts/*-round-1.prompt` between the
     BEGIN/END MATERIAL markers (pre-v1.12 runs);
  3. give up — the digest still injects, the diff is honestly omitted.
"""
from __future__ import annotations

import difflib
import glob
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Optional

from _conductor.constants import die
from _conductor.delta import _citation_refs
from _conductor.recipe import load_recipe

__all__ = [
    "RevisionContext",
    "DIFF_MAX_LINES",
    "SOURCE_MATERIAL_FILENAME",
    "prepare_revision",
    "prior_source_text",
    "build_revision_digest",
    "build_source_diff",
]

# The persisted copy of the exact reviewed source (written post-approval with
# the prompts, which already embed the same bytes — same consent envelope, same
# sensitivity handling; see references/data-handling.md).
SOURCE_MATERIAL_FILENAME = "source-material.txt"

# Unified-diff budget for the injected material. A revise run re-sends the full
# current source anyway (it IS the material under review); the diff is
# orientation, not the material, so it is capped loudly rather than dominating
# the packet.
DIFF_MAX_LINES = 400

_BEGIN_MARKER = "<<<<<<<< BEGIN MATERIAL UNDER REVIEW >>>>>>>>\n"
_END_MARKER = "\n<<<<<<<< END MATERIAL UNDER REVIEW >>>>>>>>"


@dataclass
class RevisionContext:
    run_dir: str                 # the prior run dir (normalized)
    previous_run: dict           # the verdict `previous_run` object (schema-shaped)
    material: str                # digest (+ diff) injected into round-1 prompts
    diff_available: bool         # False -> prior source unrecoverable, diff omitted
    source_recovered_from: Optional[str]   # provenance for run-metadata / run card
    source_verified: Optional[bool]  # sha-matched the prior recipe? None = no source
    prior_sensitivity: Optional[str]  # the prior run's declared sensitivity, if recorded
    note: str                    # one-line provenance summary


# Sensitivity strictness order for the escalation gate below.
_STRICTNESS = {"public": 0, "redacted": 1, "local-only": 2}


def _prior_sensitivity(run_dir: str) -> Optional[str]:
    """The prior run's declared sensitivity from its sensitivity.json, or None
    when absent/unreadable (a legacy or partial run)."""
    try:
        with open(os.path.join(run_dir, "sensitivity.json"), encoding="utf-8") as handle:
            value = json.load(handle).get("sensitivity")
    except (OSError, ValueError):
        return None
    return value if value in _STRICTNESS else None


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_run_dir(ref: str) -> str:
    """Accept a prior run dir or a path to its verdict.json."""
    path = os.path.expanduser(ref)
    if os.path.isfile(path) and os.path.basename(path) == "verdict.json":
        return os.path.dirname(os.path.abspath(path)) or "."
    if os.path.isdir(path):
        return os.path.abspath(path)
    die(f"--revise: {ref!r} is neither a run directory nor a verdict.json path")


def _load_prior_verdict(run_dir: str):
    path = os.path.join(run_dir, "verdict.json")
    if not os.path.exists(path):
        die(f"--revise: no verdict.json in {run_dir} — a run can only revise a "
            "prior run that reached a verdict")
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        die(f"--revise: {path} is not valid JSON ({exc})")
    # The prior verdict anchors the lineage and feeds the injected digest —
    # validate it as strictly as the gate would (loud beats garbage-in).
    import board_verdict
    try:
        board_verdict.validate(data)
    except SystemExit:
        # validate() already printed the schema error; add the --revise framing
        # so the user knows WHICH file failed and why the run stopped.
        die(f"--revise: the prior verdict at {path} failed schema validation "
            "(see the error above) — a run can only revise a valid prior verdict")
    return data, hashlib.sha256(raw).hexdigest()


def _load_prior_recipe(run_dir: str) -> Optional[dict]:
    path = os.path.join(run_dir, "run-recipe.yaml")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return load_recipe(handle.read())
    except (Exception, SystemExit):
        # load_recipe die()s (SystemExit) on malformed YAML — a partial/legacy
        # prior run must degrade to digest-only (its stderr line says why),
        # never abort the whole revise run.
        return None


def prior_source_text(run_dir: str, recipe: Optional[dict]):
    """(text, how, verified) for the prior run's reviewed source, or
    (None, reason, None). Recovery is verified against the recipe's
    source_sha256 when the recipe records one; bytes recovered WITHOUT a
    recorded sha are accepted but flagged verified=False, and every consent
    surface says so. Symlinked artifacts are refused — revise reads only real
    files the prior run wrote (a symlink here would splice arbitrary local
    bytes into an egressing diff)."""
    want_sha = (recipe or {}).get("source_sha256")

    copy_path = os.path.join(run_dir, SOURCE_MATERIAL_FILENAME)
    if os.path.islink(copy_path):
        return None, f"{SOURCE_MATERIAL_FILENAME} is a symlink — refused", None
    if os.path.exists(copy_path):
        try:
            with open(copy_path, encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            return None, f"{SOURCE_MATERIAL_FILENAME} unreadable ({exc})", None
        if want_sha:
            if _sha256_text(text) == want_sha:
                return text, SOURCE_MATERIAL_FILENAME, True
            return None, (f"{SOURCE_MATERIAL_FILENAME} does not match the recipe's "
                          "source_sha256"), None
        return text, SOURCE_MATERIAL_FILENAME, False

    if not want_sha:
        # Prompt extraction PARSES markers, and a prior source that itself
        # contained the END-marker line would extract silently truncated —
        # only the recipe sha can prove the parse recovered the real bytes.
        # No sha -> no extraction. (The plain copy above is parse-free, so it
        # is still usable without a sha, labeled UNVERIFIED.)
        return None, ("prior run has no source copy, and prompt extraction is "
                      "only trusted when the recipe records a source_sha256 to "
                      "verify it against"), None

    for prompt_path in sorted(glob.glob(os.path.join(run_dir, "prompts",
                                                     "*-round-1.prompt"))):
        if os.path.islink(prompt_path):
            continue
        try:
            with open(prompt_path, encoding="utf-8") as handle:
                prompt = handle.read()
        except (OSError, UnicodeDecodeError):
            continue
        begin = prompt.find(_BEGIN_MARKER)
        end = prompt.find(_END_MARKER, begin)
        if begin < 0 or end < 0:
            continue
        text = prompt[begin + len(_BEGIN_MARKER):end]
        if _sha256_text(text) == want_sha:
            return text, os.path.relpath(prompt_path, run_dir), True
        # this prompt's extraction doesn't verify (e.g. the prior source itself
        # contained a marker line and truncated the parse); try the next

    return None, ("prior source unrecoverable (no verified copy or prompt "
                  "extraction matching the recipe's source_sha256)"), None


def _final_seat_verdicts(verdict: dict) -> str:
    parts = []
    for seat in verdict.get("board", []):
        name = seat.get("seat", "?")
        if seat.get("dropped"):
            parts.append(f"{name}=dropped")
        elif seat.get("round_verdicts"):
            parts.append(f"{name}={seat['round_verdicts'][-1]}")
    return " · ".join(parts)


def _titled_lines(verdict: dict, container: str) -> list:
    lines = []
    for item in verdict.get(container) or []:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or "(untitled)"
        refs = sorted(_citation_refs(item))
        cite = f"  [{', '.join(refs)}]" if refs else ""
        lines.append(f"- {title}{cite}")
    return lines


def build_revision_digest(verdict: dict, run_dir: str) -> str:
    """A MECHANICAL digest of the prior verdict for the round-1 packet: tokens,
    titles, and citations the verdict already carries — never a rereading of
    the prose (§11)."""
    head = f"verdict: {verdict.get('verdict', '?')}"
    if verdict.get("confidence"):
        head += f" ({verdict['confidence']} confidence"
        head += ", unanimous)" if verdict.get("unanimous") else ")"
    lines = ["PRIOR BOARD VERDICT (mechanical digest — tokens, titles, and "
             "citations as recorded; not a summary):",
             f"Run: {verdict.get('title') or os.path.basename(run_dir)}"
             + (f" ({verdict['date']})" if verdict.get("date") else ""),
             head]
    seats = _final_seat_verdicts(verdict)
    if seats:
        lines.append(f"Seats (final round): {seats}")
    for container, label in (("blockers", "Blockers raised"),
                             ("concerns", "Concerns raised")):
        titled = _titled_lines(verdict, container)
        if titled:
            lines.append(f"{label} ({len(titled)}):")
            lines.extend(titled)
    actions = [a.get("action") if isinstance(a, dict) else a
               for a in verdict.get("next_actions") or []]
    actions = [a for a in actions if isinstance(a, str) and a.strip()]
    if actions:
        lines.append(f"Next actions given ({len(actions)}):")
        lines.extend(f"- {a}" for a in actions)
    return "\n".join(lines)


def build_source_diff(prior_text: str, current_text: str) -> str:
    """Unified diff, previously-reviewed draft -> current material, capped at
    DIFF_MAX_LINES with a loud truncation marker (deterministic). Inputs are
    normalized to end with a newline so difflib's keepends lines never glue a
    final `-old+new` pair into one unreadable line (the diff is line-based
    orientation; a missing EOF newline is not a change the board must weigh)."""
    if prior_text and not prior_text.endswith("\n"):
        prior_text += "\n"
    if current_text and not current_text.endswith("\n"):
        current_text += "\n"
    diff = list(difflib.unified_diff(
        prior_text.splitlines(keepends=True),
        current_text.splitlines(keepends=True),
        fromfile="previously-reviewed draft",
        tofile="material under review (above)",
    ))
    if not diff:
        return ("SOURCE DIFF: the material is byte-identical to the previously "
                "reviewed draft (no textual changes).")
    body = "".join(diff[:DIFF_MAX_LINES])
    if not body.endswith("\n"):
        body += "\n"
    out = "SOURCE DIFF (previously reviewed draft -> the material above):\n" + body
    if len(diff) > DIFF_MAX_LINES:
        out += (f"... diff truncated at {DIFF_MAX_LINES} of {len(diff)} lines — "
                "the FULL revised text is the material under review above.\n")
    return out.rstrip("\n")


def prepare_revision(config) -> RevisionContext:
    """Resolve the prior run, build the injected material, and shape the
    `previous_run` lineage object the conductor will pin into the verdict."""
    run_dir = _resolve_run_dir(config.revise_of)
    verdict, verdict_sha = _load_prior_verdict(run_dir)
    recipe = _load_prior_recipe(run_dir)

    # Sensitivity escalation gate: material handled under a stricter declaration
    # (e.g. local-only) must never silently egress under a looser new run. The
    # user decides — by re-running at the prior strictness, or by deliberately
    # reviewing the material fresh (a non---revise run) if they mean to change
    # its handling.
    prior_sensitivity = _prior_sensitivity(run_dir)
    if (prior_sensitivity is not None
            and _STRICTNESS[prior_sensitivity] > _STRICTNESS.get(config.sensitivity, 1)):
        die(f"--revise: the prior run declared --sensitivity {prior_sensitivity}, "
            f"stricter than this run's {config.sensitivity!r} — its verdict digest "
            "and source diff would egress beyond the handling that material was "
            f"given. Re-run with --sensitivity {prior_sensitivity}, or review the "
            "revised draft fresh (without --revise) if you deliberately intend to "
            "change its handling")

    previous_run = {"run_dir": run_dir, "verdict_sha256": verdict_sha}
    for key in ("title", "date", "verdict"):
        if isinstance(verdict.get(key), str) and verdict[key].strip():
            previous_run[key] = verdict[key]

    digest = build_revision_digest(verdict, run_dir)

    prior_text, how, verified = prior_source_text(run_dir, recipe)
    if prior_text is not None:
        diff_block = build_source_diff(prior_text, config.source.text)
        diff_available = True
        source_from = how
        verification = ("sha-verified" if verified
                        else "UNVERIFIED — the prior run records no source_sha256")
        note = f"prior verdict digest + source diff (prior source: {how}, {verification})"
    else:
        diff_block = (f"SOURCE DIFF: unavailable — {how}. The board sees the "
                      "prior verdict digest and the full current material only.")
        diff_available = False
        source_from = None
        note = f"prior verdict digest only ({how})"

    if recipe and recipe.get("source_sha256") == config.source.sha256:
        print("note: --revise source is byte-identical to the previously "
              "reviewed draft (same source_sha256) — this is a re-review, "
              "not a revision")

    material = digest + "\n\n" + diff_block
    return RevisionContext(run_dir=run_dir, previous_run=previous_run,
                           material=material, diff_available=diff_available,
                           source_recovered_from=source_from,
                           source_verified=verified if prior_text is not None else None,
                           prior_sensitivity=prior_sensitivity, note=note)

"""Run history (v1.11 #5): scan the persistent runs root and render a table of
past runs — date, title, verdict, confidence, unanimous, seats — read from each
run's verdict.json, falling back to run-recipe.yaml for a partial or legacy run
(one that never reached a verdict). Pure scan + render, and deliberately
forgiving: a half-finished, malformed, or pre-verdict run dir lists as
`incomplete`; it never crashes the listing."""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
from typing import Optional

from _conductor.recipe import load_recipe

__all__ = [
    "collect_history",
    "render_history_table",
]

# A directory under the runs root counts as a run when it carries at least one
# conductor artifact; anything else (a stray folder made by hand) is skipped
# rather than listed as a phantom "incomplete" run.
RUN_MARKERS = ("verdict.json", "run-recipe.yaml", "run-metadata.md", "egress-manifest.md")

# How wide the Title cell may grow before it is ellipsized — long titles are the
# one unbounded field and would otherwise stretch every row of the table.
_TITLE_WIDTH = 44


def _verdict_cell(data: dict) -> str:
    """The human-facing verdict label for a table cell.

    Rendered with the same lens-aware `human_label` the consensus artifacts use
    (an explicit `decision` verbatim; the software preset's legacy SHIP family;
    plain language for every other lens) — the machine token stays untouched in
    verdict.json. Falls back to the raw token if the label module is unavailable
    (history must list, not crash)."""
    token = data.get("verdict")
    if not isinstance(token, str) or not token:
        return "incomplete"
    lens = data.get("lens_preset") if isinstance(data.get("lens_preset"), str) else None
    decision = data.get("decision") if isinstance(data.get("decision"), str) else None
    try:
        # Deferred sibling-script import (scripts/ is on sys.path for every entry
        # point — the run_board façade and the tests both arrange that): the label
        # families live in one place, shared with render_verdict/format_output.
        from _verdict_labels import human_label
        return human_label(token, lens, decision)[0]
    except Exception:
        return token


def _seats_cell(entries) -> str:
    """Comma-joined seat names from a verdict board[] or recipe board[] list;
    a verdict seat that dropped mid-run is marked so the table doesn't present
    a collapsed board as a full one."""
    names = []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("seat")
        if not isinstance(name, str) or not name:
            continue
        if entry.get("dropped") is True:
            name += " (dropped)"
        names.append(name)
    return ", ".join(names)


def _row_from_verdict(run: str, data: dict) -> dict:
    verdict = _verdict_cell(data)
    return {
        "run": run,
        "date": data.get("date") if isinstance(data.get("date"), str) else "",
        "title": data.get("title") if isinstance(data.get("title"), str) else run,
        "verdict": verdict,
        "confidence": data.get("confidence") if isinstance(data.get("confidence"), str) else "",
        "unanimous": {True: "yes", False: "no"}.get(data.get("unanimous"), ""),
        "seats": _seats_cell(data.get("board")),
        # A verdict.json that parsed but carries no verdict token is still an
        # incomplete run (a hand-started file, or a schema the gate would reject).
        "incomplete": verdict == "incomplete",
    }


def _row_incomplete(run: str, run_dir: str) -> dict:
    """A partial/legacy run (no usable verdict.json): title/date/seats degrade to
    the run-recipe.yaml when one parses, else to the dir name alone."""
    title, date, seats = run, "", ""
    try:
        with open(os.path.join(run_dir, "run-recipe.yaml"), encoding="utf-8") as handle:
            text = handle.read()
        # load_recipe die()s on malformed text — a SystemExit plus an error line on
        # stderr. One rotten legacy recipe must neither kill nor litter the listing,
        # so swallow both and let the row degrade to the dir name.
        with contextlib.redirect_stderr(io.StringIO()):
            recipe = load_recipe(text)
        if isinstance(recipe.get("title"), str):
            title = recipe["title"]
        if isinstance(recipe.get("date"), str):
            date = recipe["date"]
        seats = _seats_cell(recipe.get("board"))
    except (OSError, UnicodeDecodeError, SystemExit):
        pass
    return {
        "run": run,
        "date": date,
        "title": title,
        "verdict": "incomplete",
        "confidence": "",
        "unanimous": "",
        "seats": seats,
        "incomplete": True,
    }


def collect_history(root: str) -> list:
    """One row dict per run dir under `root`, newest first (date descending, dir
    name ascending within a date; runs with no recoverable date sort last).

    A complete run reads its fields from verdict.json — the canonical machine
    surface. A run whose verdict.json is missing or unreadable degrades to an
    `incomplete` row (via run-recipe.yaml where possible) rather than raising:
    the listing must survive interrupted, blocked, and pre-v1.11 runs alike."""
    try:
        runs = sorted(os.listdir(root))
    except OSError:
        return []   # absent or unreadable root — an empty history, not a crash
    rows: list = []
    for run in runs:
        run_dir = os.path.join(root, run)
        if not os.path.isdir(run_dir):
            continue
        if not any(os.path.isfile(os.path.join(run_dir, marker)) for marker in RUN_MARKERS):
            continue
        data: Optional[dict] = None
        try:
            with open(os.path.join(run_dir, "verdict.json"), encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, UnicodeDecodeError, ValueError):
            data = None   # absent or malformed verdict.json -> incomplete row
        rows.append(_row_from_verdict(run, data) if data is not None
                    else _row_incomplete(run, run_dir))
    rows.sort(key=lambda r: r["run"])
    rows.sort(key=lambda r: r["date"], reverse=True)   # stable: name breaks date ties
    return rows


def _cell(row: dict, key: str) -> str:
    # A title (or any verdict-sourced string) may legitimately contain newlines —
    # the recipe codec round-trips multi-line --title values — and one raw \n
    # would split a table row, so every cell is collapsed to single-spaced text.
    value = re.sub(r"\s+", " ", row.get(key) or "").strip()
    if key == "title" and len(value) > _TITLE_WIDTH:
        value = value[:_TITLE_WIDTH - 1].rstrip() + "…"
    return value or "—"


def render_history_table(rows: list, root: str) -> str:
    """The `history` table (preflight-table style): one row per past run."""
    if not rows:
        return (f"no runs recorded under {root}\n"
                "(a run without --out/--ephemeral persists here; "
                "--runs-root/$ADVISORY_BOARD_RUNS_ROOT relocate it)")
    columns = [("date", "Date"), ("title", "Title"), ("verdict", "Verdict"),
               ("confidence", "Confidence"), ("unanimous", "Unanimous"),
               ("seats", "Seats"), ("run", "Run dir")]
    widths = {key: max(len(header), *(len(_cell(r, key)) for r in rows))
              for key, header in columns}
    header = "| " + " | ".join(h.ljust(widths[k]) for k, h in columns) + " |"
    rule = "| " + " | ".join("-" * widths[k] for k, _ in columns) + " |"
    lines = [f"runs root: {root}", "", header, rule]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row, k).ljust(widths[k]) for k, _ in columns) + " |")
    incomplete = sum(1 for r in rows if r["incomplete"])
    lines.append("")
    lines.append(f"{len(rows)} run(s)"
                 + (f", {incomplete} incomplete (no verdict.json — an interrupted, blocked, "
                    "or pre-verdict run)" if incomplete else "") + ".")
    return "\n".join(lines)

"""`ask` (v1.12 #4): post-verdict cross-examination.

`run_board.py ask "<question>" --run <dir> [--seat <id>]` puts a follow-up question
to a COMPLETED run's board. It is not a re-review (that is `--revise`): it loads the
prior run's recorded board from `run-recipe.yaml`, builds a context packet from that
run's OWN artifacts (the reviewed material, a mechanical verdict digest, and each
addressed seat's own prior review), RE-CONSENTS the new bytes through the same egress
gate a fresh run uses, fans ONE round out to the addressed seat(s), and writes an
`addendum-N.md` plus a refreshed handoff pointer.

Invariants held from the rest of the conductor:
  * bounded to the named run — every byte in the packet is recovered from `<dir>`'s
    own artifacts (symlinks and out-of-tree resolutions refused); grounding is forced
    OFF (no live repo read), so a grounded run's `ask` still egresses only artifacts;
  * consent binds to the exact bytes — the packet hash covers the question + context,
    the gate re-decides per the run's sensitivity (public → disclosure; non-public →
    hash-bound approval, refused non-interactively without --yes), and the effective
    sensitivity is the STRICTER of the recipe's and the run's sensitivity.json (ask
    never egresses under a looser posture than the material was handled with);
  * the injected context is byte-neutralized against fence-marker echoes (it embeds
    prior MODEL output), exactly like `--revise`'s injected material.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Optional

from _conductor.constants import (
    EXIT_EGRESS_BLOCKED,
    EXIT_OK,
    EXIT_PREFLIGHT_NOGO,
    EXIT_USAGE,
    die,
    now_date,
)
from _conductor.config import (
    RunConfig,
    _source_from_text,
    board_from_recipe,
    resolve_board,
)
from _conductor.recipe import recipe_to_config
from _conductor.revise import build_revision_digest, prior_source_text
from _conductor.egress import (
    PacketBlob,
    disclosure_line,
    enforce_egress_gate,
    packet_hash,
    render_egress_manifest,
)
from _conductor.prompts import (
    PROMPT_TEMPLATE_ASK,
    ask_template_sha,
    build_ask_prompt,
)
from _conductor.artifacts import _write, render_sensitivity_json
from _conductor.rounds import run_round
from _conductor.spawn import classify_ask

__all__ = [
    "AskContext",
    "ADDENDA_INDEX_FILENAME",
    "ADDENDA_SCHEMA",
    "load_ask_config",
    "build_ask_run_context",
    "build_ask_packet",
    "next_addendum_index",
    "render_addendum",
    "render_ask_table",
    "refresh_handoff",
    "run_ask",
]

ADDENDA_INDEX_FILENAME = "addenda.json"
ADDENDA_SCHEMA = "advisory-board/addenda@1"

# Sensitivity strictness order for the never-loosen gate (mirrors revise._STRICTNESS;
# kept local so `ask` stays self-contained).
_STRICTNESS = {"public": 0, "redacted": 1, "local-only": 2}

# Managed block sentinels for the handoff-refresh section in final-consensus.md.
_ADDENDA_BEGIN = "<!-- advisory-board:addenda -->"
_ADDENDA_END = "<!-- /advisory-board:addenda -->"


@dataclass
class AskContext:
    run_dir: str                          # the run being questioned (normalized)
    question: str                         # the operator's follow-up question
    seat_ids: list                        # addressed seat ids (== config.board ids)
    previous_run: dict                    # {run_dir, verdict_sha256, title?, date?, verdict?}
    source_recovered_from: Optional[str]  # provenance of the recovered reviewed material
    source_verified: Optional[bool]       # sha-matched the recipe? None = no source
    prior_sensitivity: Optional[str]      # the run's sensitivity.json value, if recorded
    template_version: str                 # ask prompt-template id (recorded on the record)
    template_sha256: str                  # ask prompt-template sha (edit-detectable)
    note: str = ""
    floor_note: Optional[str] = None      # fail-closed sensitivity flooring, when applied


# ---------------------------------------------------------------------------
# Loading a completed run (bounded to <dir>)
# ---------------------------------------------------------------------------

def _load_run_verdict(run_dir: str):
    """The run's verdict.json, validated as strictly as the gate would — ask is
    post-verdict, so a run without a valid verdict cannot be questioned. Returns
    (verdict_dict, sha256_of_raw_bytes)."""
    path = os.path.join(run_dir, "verdict.json")
    if os.path.islink(path):
        die(f"ask: {path} is a symlink — refused")
    if not os.path.exists(path):
        die(f"ask: no verdict.json in {run_dir} — ask is post-verdict cross-examination; "
            "a run can only be questioned once it has reached a verdict")
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        die(f"ask: {path} is not valid JSON ({exc})")
    if not isinstance(data, dict):
        die(f"ask: {path} is not a verdict object (top-level "
            f"{type(data).__name__}) — ask can only question a valid verdict")
    import board_verdict
    try:
        board_verdict.validate(data)
    except SystemExit:
        die(f"ask: the verdict at {path} failed schema validation (see the error above) "
            "— ask can only question a valid verdict")
    return data, hashlib.sha256(raw).hexdigest()


def _sensitivity_json_value(run_dir: str) -> Optional[str]:
    """The run's declared sensitivity from its sensitivity.json, or None when
    absent/unreadable/not-an-object (a legacy, partial, or hand-edited run)."""
    try:
        with open(os.path.join(run_dir, "sensitivity.json"), encoding="utf-8") as handle:
            loaded = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(loaded, dict):
        return None
    value = loaded.get("sensitivity")
    return value if value in _STRICTNESS else None


def _effective_sensitivity(run_dir: str, recipe_sensitivity: Optional[str],
                           cli_floor: Optional[str] = None) -> tuple:
    """(sensitivity, json_value, floor_note). The STRICTEST of the recipe's
    sensitivity, the run's sensitivity.json, and an operator --sensitivity floor —
    an ask never egresses under a looser posture than the material was handled with
    (the never-loosen principle --revise enforces across runs, applied within one).

    Both disk values live inside the run dir and are therefore tamperable on a
    shared/hand-built run, so two fail-closed rules apply: the CLI floor can only
    TIGHTEN (it joins the max, never replaces it), and a run with no readable
    sensitivity.json never floats down to public — its original posture is unknown,
    so public floors to redacted (hash-bound approval), loudly."""
    js = _sensitivity_json_value(run_dir)
    candidates = [s for s in (recipe_sensitivity, js, cli_floor) if s in _STRICTNESS]
    sensitivity = (max(candidates, key=lambda s: _STRICTNESS[s])
                   if candidates else "redacted")
    note = None
    if js is None and sensitivity == "public":
        sensitivity = "redacted"
        note = ("this run has no readable sensitivity.json — its original handling "
                "posture is unknown, so the ask floors public to redacted "
                "(hash-bound approval required; --yes or interactive approval)")
    return sensitivity, js, note


def _is_dropped_placeholder(text: str, seat_id: str) -> bool:
    """True when a round-N/<seat>.md is the `_dropped_md` placeholder the round
    writer leaves for a seat that produced no usable review (rounds.py) — not a
    review, so it must never be fed back to the seat as its own prior position."""
    first = text.lstrip().split("\n", 1)[0]
    return (first.startswith(f"# {seat_id} — round ")
            and first.rstrip().endswith(": no usable review"))


def _seat_prior_review(run_dir: str, seat_id: str):
    """The addressed seat's own last USABLE review, recovered from the run's
    `round-*` dirs — the seat's continuity of position for the cross-examination.
    Rounds are tried highest-first; a `_dropped_md` placeholder (the seat dropped
    that round) is skipped in favor of the seat's last real review. Bounded to
    run_dir: a symlink or a path resolving outside the run is refused (a refused
    round is skipped, not trusted). Returns (text, provenance) or (None, reason)."""
    real_run = os.path.realpath(run_dir)
    rounds: list = []
    for path in glob.glob(os.path.join(run_dir, "round-*", f"{seat_id}.md")):
        base = os.path.basename(os.path.dirname(path))   # round-N
        try:
            n = int(base.split("-", 1)[1])
        except (IndexError, ValueError):
            continue
        rounds.append((n, path))
    if not rounds:
        return None, "no prior review found for this seat in the run"
    reasons = []
    for n, path in sorted(rounds, reverse=True):
        rel = f"round-{n}/{seat_id}.md"
        if os.path.islink(path):
            reasons.append(f"{rel} is a symlink — refused")
            continue
        if not os.path.realpath(path).startswith(real_run + os.sep):
            reasons.append(f"{rel} resolves outside the run — refused")
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            reasons.append(f"{rel} unreadable ({exc})")
            continue
        if _is_dropped_placeholder(text, seat_id):
            reasons.append(f"{rel} is a dropped-seat placeholder — skipped")
            continue
        return text, rel
    return None, "; ".join(reasons)


def load_ask_config(run_dir: str, question: str, seat_id: Optional[str],
                    sensitivity_floor: Optional[str] = None):
    """Reconstruct a RunConfig for the ask from the run's recipe, filter it to the
    addressed seat(s), recover the reviewed source (bounded to run_dir), and attach the
    AskContext. Grounding is forced OFF — the packet is built from the run's artifacts
    only. `sensitivity_floor` is the operator's --sensitivity (tighten-only).
    Returns (config, verdict, prior_source_text_or_None, source_provenance)."""
    recipe_path = os.path.join(run_dir, "run-recipe.yaml")
    if not os.path.isfile(recipe_path):
        die(f"ask: {run_dir} has no run-recipe.yaml — ask needs the recorded board to "
            "re-address the run's seats (only a run produced by this conductor can be "
            "asked)")
    base = recipe_to_config(recipe_path)   # validates board/enums; die()s on malformed
    verdict, verdict_sha = _load_run_verdict(run_dir)

    model_overrides: dict = {}
    lens_overrides: dict = {}
    reasoning_overrides: dict = {}
    seat_specs, lens_preset = board_from_recipe(
        base, model_overrides, lens_overrides, reasoning_overrides)
    full_board = resolve_board(seat_specs, lens_preset, model_overrides,
                               lens_overrides, reasoning_overrides)
    if seat_id:
        addressed = [s for s in full_board if s.id == seat_id]
        if not addressed:
            die(f"ask: --seat {seat_id!r} is not a seat in this run "
                f"({', '.join(s.id for s in full_board)})", EXIT_USAGE)
    else:
        addressed = full_board

    mode = base.get("mode") or "gate"
    sensitivity, sens_json, floor_note = _effective_sensitivity(
        run_dir, base.get("sensitivity") or "redacted", sensitivity_floor)

    prior_text, source_how, source_verified = prior_source_text(run_dir, base)
    source = _source_from_text("recovered", source_how or "-", prior_text or "")

    previous_run = {"run_dir": run_dir, "verdict_sha256": verdict_sha}
    for key in ("title", "date", "verdict"):
        if isinstance(verdict.get(key), str) and verdict[key].strip():
            previous_run[key] = verdict[key]

    if prior_text is not None:
        src_note = (f"reviewed material: {source_how} "
                    + ("(sha-verified)" if source_verified else "(UNVERIFIED)"))
    else:
        src_note = f"reviewed material unrecoverable ({source_how})"

    ask_ctx = AskContext(
        run_dir=run_dir,
        question=question,
        seat_ids=[s.id for s in addressed],
        previous_run=previous_run,
        source_recovered_from=source_how if prior_text is not None else None,
        source_verified=source_verified if prior_text is not None else None,
        prior_sensitivity=sens_json,
        template_version=PROMPT_TEMPLATE_ASK,
        template_sha256=ask_template_sha(),
        note=f"post-verdict follow-up to {len(addressed)} seat(s); {src_note}",
        floor_note=floor_note,
    )

    config = RunConfig(
        title=base.get("title") or os.path.basename(os.path.abspath(run_dir)),
        date=now_date(),
        source=source,
        mode=mode,
        sensitivity=sensitivity,
        rounds="1",
        max_rounds=1,
        cross_reading="none",
        lens=lens_preset,
        output=base.get("output") or "full-handoff",
        out_dir=run_dir,
        board=addressed,
        network_on=(mode == "advisory"),
        fs_scoped=(mode == "gate"),
        repo=None,          # grounding OFF — ask is bounded to the run's own artifacts
    )
    config.ask = ask_ctx
    return config, verdict, prior_text, source_how


# ---------------------------------------------------------------------------
# The ask packet (context built from the run's own artifacts)
# ---------------------------------------------------------------------------

def build_ask_run_context(verdict: dict, run_dir: str, source_text: Optional[str],
                          source_how: str, seat) -> str:
    """The run-context block for one seat: the reviewed material, a MECHANICAL digest
    of the board's verdict (reused from --revise — tokens/titles/citations, never a
    re-reading, §11), and THIS seat's own prior review. Everything here is third-party
    or prior-MODEL data; build_ask_prompt neutralizes it before the fence splice."""
    parts = ["## Material the board reviewed", ""]
    if source_text:
        parts.append(source_text.rstrip("\n"))
    else:
        parts.append(f"(the reviewed material could not be recovered from this run: "
                     f"{source_how})")
    parts += ["", "## The board's verdict (mechanical digest)", "",
              build_revision_digest(verdict, run_dir)]
    review, how = _seat_prior_review(run_dir, seat.id)
    if review:
        parts += ["", f"## Your own prior review ({how})", "", review.rstrip("\n")]
    else:
        parts += ["", "## Your own prior review", "", f"(not recovered: {how})"]
    return "\n".join(parts)


def build_ask_packet(config: RunConfig, run_dir: str, verdict: dict,
                     source_text: Optional[str], source_how: str, n: int) -> list:
    """One PacketBlob per addressed seat — each carries the shared question plus that
    seat's OWN run-context (so `--seat` targeting and per-seat continuity both hold).
    Prompts land under `addendum-N/` so the run's original prompts are never clobbered."""
    blobs: list = []
    question = config.ask.question
    for seat in config.board:
        run_context = build_ask_run_context(verdict, run_dir, source_text, source_how, seat)
        prompt = build_ask_prompt(seat, run_context, question)
        blobs.append(PacketBlob(
            seat=seat.id,
            provider=seat.provider,
            relpath=os.path.join(f"addendum-{n}", f"{seat.id}.prompt"),
            text=prompt,
        ))
    return blobs


def next_addendum_index(run_dir: str) -> int:
    """The next free addendum number N (1-based). Skips any N whose `addendum-N.md` or
    `addendum-N/` already exists, so a second ask never overwrites the first."""
    n = 1
    while (os.path.exists(os.path.join(run_dir, f"addendum-{n}.md"))
           or os.path.exists(os.path.join(run_dir, f"addendum-{n}"))):
        n += 1
    return n


# ---------------------------------------------------------------------------
# Rendering the addendum + refreshing the handoff
# ---------------------------------------------------------------------------

def render_ask_table(results: list) -> str:
    rows = ["| Seat   | Status   | Model answered | Elapsed |",
            "| ------ | -------- | -------------- | ------- |"]
    for r in results:
        rows.append(f"| {r.seat:<6} | {r.status:<8} | {(r.model_answered or 'unknown'):<14} "
                    f"| {r.elapsed_s:>5.1f}s |")
    usable = sum(1 for r in results if r.usable)
    rows += ["", f"{usable} of {len(results)} addressed seat(s) answered."]
    return "\n".join(rows)


def render_addendum(config: RunConfig, results: list, n: int, approval, content_hash: str) -> str:
    """The human-facing Q&A artifact: the question, provenance (what was asked of whom,
    grounded on which material, under what consent), and each seat's answer with a
    falsifiable per-seat footer (prompt + packet hashes)."""
    a = config.ask
    pr = a.previous_run
    if a.source_recovered_from:
        material = (f"{a.source_recovered_from} "
                    + ("(sha-verified)" if a.source_verified else "(UNVERIFIED)"))
    else:
        material = "not recovered — verdict digest + prior reviews only"
    lines = [
        f"# Addendum {n} — {config.title}",
        "",
        f"**Question:** {a.question}",
        "",
        "## Provenance",
        "",
        f"- Date: {config.date}",
        f"- Run questioned: {a.run_dir}",
        f"- Addressed seats: {', '.join(s.id for s in config.board)}",
        f"- Prior verdict: {pr.get('verdict', '?')}"
        + (f" — sha256:{pr['verdict_sha256'][:16]}…" if pr.get("verdict_sha256") else ""),
        f"- Reviewed material: {material}",
        f"- Egress: {approval.mode} — content hash sha256:{content_hash[:16]}…",
        f"- Ask template: {a.template_version} (sha256:{a.template_sha256[:16]}…)",
        "",
        "## Answers",
        "",
    ]
    by_id = {r.seat: r for r in results}
    for seat in config.board:
        r = by_id.get(seat.id)
        heading = seat.label + (f" — {r.model_answered}" if r and r.model_answered else "")
        lines += [f"### {heading}", ""]
        if r is None:
            lines.append("(no result — seat not run)")
        elif r.usable:
            lines.append(r.stdout.rstrip("\n"))
        else:
            lines.append(f"**No usable answer** — status: {r.status}, failure: "
                         f"{r.failure_class or '-'}, attempts: {r.attempts}.")
            if r.stderr.strip():
                tail = "\n".join(r.stderr.rstrip("\n").splitlines()[-15:])
                lines += ["", "```", tail, "```"]
        if r is not None:
            lines += ["", f"_prompt sha256:{r.prompt_hash[:16]}… · packet sha256:"
                          f"{content_hash[:16]}… (egress consent was bound to this)_"]
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def _append_addenda_index(run_dir: str, entry: dict) -> list:
    """Append (idempotently, keyed by N) to the machine-readable addenda index. The
    index is the source of truth the handoff block is rebuilt from — derived and
    rebuildable, so a corrupt/legacy file is replaced rather than fatal."""
    path = os.path.join(run_dir, ADDENDA_INDEX_FILENAME)
    addenda: list = []
    if os.path.exists(path) and not os.path.islink(path):
        try:
            with open(path, encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict) and isinstance(loaded.get("addenda"), list):
                addenda = [e for e in loaded["addenda"] if isinstance(e, dict)]
        except (OSError, ValueError):
            addenda = []
    addenda = [e for e in addenda if e.get("n") != entry["n"]]
    addenda.append(entry)
    addenda.sort(key=lambda e: e.get("n", 0))
    _write(path, json.dumps({"schema": ADDENDA_SCHEMA, "addenda": addenda}, indent=2) + "\n")
    return addenda


def _neutralize_addenda_markers(text: str) -> str:
    """Scrub literal copies of the managed-block sentinels from content rendered
    INSIDE the block (questions, index fields). Without this, a question containing
    the end sentinel would terminate the block early and every later refresh would
    splice at the forged marker, corrupting the handoff cumulatively."""
    return (text.replace(_ADDENDA_BEGIN, "[addenda-marker]")
                .replace(_ADDENDA_END, "[addenda-marker]"))


def refresh_handoff(run_dir: str) -> Optional[str]:
    """Rebuild the managed 'Post-verdict addenda' block in final-consensus.md from the
    addenda index, so the run's handoff points at every follow-up. Idempotent
    (sentinel-delimited, rebuilt each call). Returns the path refreshed, or None when
    there is no consensus handoff to refresh (a run that never rendered one)."""
    consensus = os.path.join(run_dir, "final-consensus.md")
    if not os.path.isfile(consensus) or os.path.islink(consensus):
        return None
    addenda: list = []
    try:
        with open(os.path.join(run_dir, ADDENDA_INDEX_FILENAME), encoding="utf-8") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict) and isinstance(loaded.get("addenda"), list):
            addenda = [e for e in loaded["addenda"] if isinstance(e, dict)]
    except (OSError, ValueError):
        addenda = []
    entries = []
    for e in addenda:
        seats = ", ".join(s for s in e.get("seats", []) if isinstance(s, str))
        question = (e.get("question", "") or "").strip().replace("\n", " ")
        entries.append(f"- **Addendum {e.get('n')}** ({e.get('date', '?')}) — "
                       f"\"{question}\" → seats: {seats} · "
                       f"[{e.get('file')}]({e.get('file')})")
    block_text = "\n".join(
        [_ADDENDA_BEGIN, "## Post-verdict addenda", "",
         "Follow-up questions put to the board after this verdict "
         "(`run_board.py ask`):", ""]
        # Everything BETWEEN the sentinels is data — neutralize any literal
        # sentinel echo so the block can never terminate early (S2).
        + [_neutralize_addenda_markers("\n".join(entries))]
        + ["", _ADDENDA_END])

    with open(consensus, encoding="utf-8") as handle:
        text = handle.read()
    start = text.find(_ADDENDA_BEGIN)
    # The END is only meaningful AFTER the BEGIN (searching the whole file could
    # match a stray/earlier sentinel and splice garbage). No well-formed pair ->
    # append a fresh block; never guess a splice that could destroy content.
    end = text.find(_ADDENDA_END, start) if start >= 0 else -1
    if start >= 0 and end >= 0:
        new_text = text[:start] + block_text + text[end + len(_ADDENDA_END):]
    else:
        new_text = text.rstrip("\n") + "\n\n" + block_text + "\n"
    _write(consensus, new_text)
    return consensus


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_ask(run_dir_ref: str, question: str, seat_id: Optional[str], *,
            assume_yes: bool = False, skip_gate: bool = False,
            interactive: Optional[bool] = None,
            sensitivity_floor: Optional[str] = None) -> int:
    """Drive an ask end to end: load the run, re-consent the new bytes, fan one round
    out to the addressed seat(s), write the addendum, and refresh the handoff."""
    run_dir = os.path.abspath(os.path.expanduser(run_dir_ref))
    if not os.path.isdir(run_dir):
        die(f"ask: --run {run_dir_ref!r} is not a directory", EXIT_USAGE)
    if not question or not question.strip():
        die("ask: the question is empty — pass a follow-up question to put to the board",
            EXIT_USAGE)
    if sensitivity_floor is not None and sensitivity_floor not in _STRICTNESS:
        die(f"ask: --sensitivity must be public, redacted, or local-only; "
            f"got {sensitivity_floor!r}", EXIT_USAGE)

    config, verdict, prior_text, source_how = load_ask_config(
        run_dir, question, seat_id, sensitivity_floor)
    n = next_addendum_index(run_dir)
    blobs = build_ask_packet(config, run_dir, verdict, prior_text, source_how, n)
    content_hash = packet_hash(blobs)
    addendum_dir = os.path.join(run_dir, f"addendum-{n}")

    print(f"ask → {run_dir} (addendum {n})")
    print(f"addressed seats: {', '.join(s.id for s in config.board)}")
    print(f"sensitivity: {config.sensitivity}")
    if config.ask.floor_note:
        print(f"⚠ {config.ask.floor_note}")

    # Egress gate — re-consent for the new bytes (question + run context). The same
    # tiered gate a fresh run uses: public discloses and proceeds; non-public requires
    # hash-bound approval (--yes or interactive) and refuses non-interactively.
    print("\n=== egress gate (re-consent) ===")
    print(disclosure_line(config))
    approval = enforce_egress_gate(config, blobs, assume_yes=assume_yes,
                                   skip_gate=skip_gate, interactive=interactive)
    print(f"egress: {'APPROVED' if approval.approved else 'REFUSED'} "
          f"({approval.mode}) — {approval.detail}")
    print(f"content hash: sha256:{content_hash}")

    if not approval.approved:
        # Persist the manifest + refusal record so the user can see exactly what was
        # blocked; the prompts are NOT written (nothing the gate refused is materialized).
        os.makedirs(addendum_dir, exist_ok=True)
        _write(os.path.join(addendum_dir, "egress-manifest.md"),
               render_egress_manifest(config, blobs, content_hash))
        _write(os.path.join(addendum_dir, "sensitivity.json"),
               render_sensitivity_json(config, approval))
        die(f"ask: egress blocked — see {addendum_dir}/egress-manifest.md", EXIT_EGRESS_BLOCKED)

    # Approved: persist the exact approved packet + provenance BEFORE spawning.
    os.makedirs(addendum_dir, exist_ok=True)
    _write(os.path.join(addendum_dir, "egress-manifest.md"),
           render_egress_manifest(config, blobs, content_hash))
    _write(os.path.join(addendum_dir, "sensitivity.json"),
           render_sensitivity_json(config, approval))
    for b in blobs:
        _write(os.path.join(run_dir, b.relpath), b.text)

    # One-round fan-out. run_round re-asserts the packet hash == approval hash right
    # before the first spawn (the pre-spawn hard stop), then feeds each addressed seat
    # its approved blob verbatim.
    print("\n=== ask (one-round fan-out) ===")
    results = run_round(config, blobs, approval, round_no=1, classify=classify_ask)

    _write(os.path.join(run_dir, f"addendum-{n}.md"),
           render_addendum(config, results, n, approval, content_hash))
    _append_addenda_index(run_dir, {
        "n": n,
        "date": config.date,
        "question": question,
        "seats": [s.id for s in config.board],
        "file": f"addendum-{n}.md",
        "verdict_sha256": config.ask.previous_run.get("verdict_sha256"),
    })
    handoff = refresh_handoff(run_dir)

    print(render_ask_table(results))
    print(f"\nwrote addendum → {run_dir}/addendum-{n}.md")
    if handoff:
        print(f"refreshed handoff → {handoff}")

    if not any(r.usable for r in results):
        print("\nWARNING: no addressed seat produced a usable answer — inspect the "
              f"addendum and {addendum_dir}/ for per-seat failure detail.")
        return EXIT_PREFLIGHT_NOGO
    return EXIT_OK

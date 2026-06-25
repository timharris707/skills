"""Renderers and writers for the pre-spawn artifacts: run-card, sensitivity.json,
the artifact tree, and the run-metadata stamp (md + tsv)."""
from __future__ import annotations

import json
import os
from typing import Optional

from _conductor.constants import SENSITIVITY_SCHEMA
from _conductor.config import (
    RunConfig,
    SeatConfig,
)
from _conductor.egress import (
    EgressApproval,
    consent_mode_for,
    consent_token,
    disclosure_line,
    render_egress_manifest,
    unenforced_network_note,
)
from _conductor.recipe import (
    RECIPE_COMMENTS,
    config_to_recipe,
    dump_recipe,
)

__all__ = [
    "seat_network_status",
    "render_run_card",
    "render_sensitivity_json",
    "render_artifact_tree",
    "render_run_metadata",
    "RUN_METADATA_TSV_COLUMNS",
    "render_run_metadata_tsv",
    "write_pre_spawn_artifacts",
    "_write",
]


def seat_network_status(seat: SeatConfig, config: RunConfig) -> str:
    if config.network_on:
        return "on"
    return "off" if seat.adapter.isolates_network else "NOT ENFORCED"


def render_run_card(config: RunConfig) -> str:
    seats = "\n".join(
        f"    - {s.name:<7} {s.provider:<10} {s.model:<18} [{s.reasoning}]  — {s.lens}"
        for s in config.board
    )
    net = ", ".join(f"{s.name}={seat_network_status(s, config)}" for s in config.board)
    lines = [
        f"Advisory board run-card — {config.title}",
        f"  date          : {config.date}",
        f"  mode          : {config.mode}  (fs {'scoped' if config.fs_scoped else 'open'})",
        f"  network       : {net}",
        f"  sensitivity   : {config.sensitivity}",
        f"  rounds        : {config.rounds}    cross-reading: {config.cross_reading}",
        f"  lens preset   : {config.lens}",
        f"  output        : {config.output}",
        f"  source        : {config.source.ref} "
        f"({config.source.nbytes} bytes, {config.source.nlines} lines, sha256:{config.source.sha256[:12]}…)",
        f"  out dir       : {config.out_dir}",
        "  board         :",
        seats,
        "",
        f"  EGRESS        : {disclosure_line(config)}",
        f"                  consent = {consent_mode_for(config.sensitivity)}",
    ]
    note = unenforced_network_note(config)
    if note:
        lines += ["", "  " + note]
    return "\n".join(lines)


def render_sensitivity_json(config: RunConfig, approval: Optional[EgressApproval] = None) -> str:
    external = sorted({s.provider for s in config.board if s.provider != "local"})
    payload = {
        "schema": SENSITIVITY_SCHEMA,
        "sensitivity": config.sensitivity,
        "egress_allowed": config.sensitivity != "local-only" or not external,
        "providers": external,
        "consent": {
            "required": config.sensitivity != "public",
            "mode": consent_token(config.sensitivity),
        },
        "network_isolation": {s.name: seat_network_status(s, config) for s in config.board},
        "network_unenforced": config.unenforced_network_seats,
    }
    if approval is not None:
        payload["approval"] = {
            "approved": approval.approved,
            "mode": approval.mode,
            "content_hash": approval.content_hash,
            "timestamp": approval.timestamp,
        }
    return json.dumps(payload, indent=2) + "\n"


def render_artifact_tree(config: RunConfig) -> str:
    rounds = []
    n = 3 if config.rounds == "auto" else int(config.rounds)
    for r in range(1, n + 1):
        rounds.append(f"  round-{r}/<seat>.md   round-{r}/<seat>.raw")
    packet_rounds = "\n".join(
        f"  board-packet-round-{r}.md" for r in range(2, n + 1)
    )
    seat_prompts = "\n".join(
        f"  prompts/{s.name}-round-1.prompt" for s in config.board
    )
    parts = [
        f"{config.out_dir}/",
        "  run-recipe.yaml   egress-manifest.md   sensitivity.json",
        seat_prompts,
        *rounds,
    ]
    if packet_rounds:
        parts.append(packet_rounds)
    parts += [
        "  logs/<seat>-round-N.stderr",
        "  verdict.json   final-consensus.md   handoff-data.json   final-consensus.html",
        "  run-metadata.md   run-metadata.tsv",
    ]
    return "\n".join(parts)


def render_run_metadata(config: RunConfig, preflight: list, approval: EgressApproval,
                        rounds: Optional[list] = None) -> str:
    # `rounds` is an ordered list of per-round result lists: [round1_results,
    # round2_results, ...]. None until the first fan-out completes.
    lines = [
        f"# Run Metadata — {config.title}",
        "",
        f"Date: {config.date}   ·   Rounds: {config.rounds}   ·   Cross-reading: {config.cross_reading}",
        f"Mode: {config.mode}   ·   Sensitivity: {config.sensitivity}   ·   Output: {config.output}",
        f"Lens preset: {config.lens}",
        "",
        "## Seats",
        "",
        "| Seat   | Lens | Model requested | Reasoning | Auth | Preflight |",
        "| ------ | ---- | --------------- | --------- | ---- | --------- |",
    ]
    pf = {p.seat: p for p in preflight}
    for s in config.board:
        p = pf.get(s.name)
        verdict = ("GO" if p and p.go else "NO-GO") if p else "n/a"
        auth = p.auth if p else "n/a"
        lens_short = s.lens.split("—")[0].strip()
        lines.append(
            f"| {s.name:<6} | {lens_short} | {s.model} | {s.reasoning} | {auth} | {verdict} |"
        )
    lines += [
        "",
        "## Source",
        "",
        f"Access method: single source packet",
        f"Source: {config.source.ref} (sha256:{config.source.sha256})",
        f"Sensitivity & handling: {config.sensitivity}",
        "",
        "## Egress approval",
        "",
        f"- Decision     : {'APPROVED' if approval.approved else 'REFUSED'} ({approval.mode})",
        f"- Content hash : sha256:{approval.content_hash}",
        f"- Timestamp    : {approval.timestamp}",
        f"- Providers    : {', '.join(sorted({s.provider for s in config.board if s.provider != 'local'})) or '(none)'}",
        f"- Detail       : {approval.detail}",
    ]
    for round_results in (rounds or []):
        if not round_results:
            continue
        n = round_results[0].round_no
        usable = sum(1 for r in round_results if r.usable)
        lines += [
            "",
            f"## Round {n}",
            "",
            f"{usable} of {len(round_results)} seats produced a usable review.",
            "",
            "| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |",
            "| ------ | -------- | -------------- | -------- | ------- | ------- |",
        ]
        for r in round_results:
            answered = r.model_answered or "unknown"
            lines.append(
                f"| {r.seat:<6} | {r.status:<8} | {answered} | {r.attempts} "
                f"| {r.elapsed_s:.1f}s | {r.failure_class or '-'} |"
            )
        # Provider-correlation disclosure (§12): "three voices" can be fewer
        # providers; the answered models above expose it, and antigravity's model
        # is structurally unknowable (it silently substitutes — never trusted).
    lines += [
        "",
        "## Notes",
        "",
    ]
    if not rounds:
        lines.append("- Model that *answered* per seat is captured at the round-1 fan-out, not here.")
    else:
        lines.append("- 'Model answered' is what the CLI *reported*; 'unknown' means it reported "
                     "nothing parseable (never assume the requested model answered).")
        lines.append("- Round 2+ egresses round-1 reviews (derivatives of already-approved source) "
                     "to the same providers under the disclosed multi-round plan; each round's "
                     "packet hash is recorded in round-N/<seat>.raw and run-metadata.tsv.")
    lines.append("- Never record secrets, tokens, cookies, or private environment values.")
    if config.unenforced_network_seats:
        lines.append(
            f"- ⚠ Network NOT isolated for: {', '.join(config.unenforced_network_seats)} "
            "(no CLI flag removes their web/grounding tools); treat as networked despite gate mode."
        )
    for p in preflight:
        if getattr(p, "model_proposal", None):
            lines.append(
                f"- ⚠ {p.seat}: pinned model did not resolve on the installed CLI; "
                f"resolvable fallback proposed: {p.model_proposal} "
                f"(update the CLI via `toolchain --update`, or pass --model {p.seat}={p.model_proposal})."
            )
    return "\n".join(lines) + "\n"


RUN_METADATA_TSV_COLUMNS = (
    "round", "seat", "provider", "model_requested", "model_answered", "status",
    "failure_class", "attempts", "elapsed_s", "exit_code", "timed_out",
    "prompt_sha256", "packet_sha256",
)


def render_run_metadata_tsv(rounds: list) -> str:
    """The diffable, machine-readable provenance companion to run-metadata.md
    (§12): one row per seat per round. Tabs are stripped from any field so the TSV
    can't be corrupted by a stray tab in a model id."""
    def cell(v) -> str:
        return str(v).replace("\t", " ").replace("\n", " ")
    out = ["\t".join(RUN_METADATA_TSV_COLUMNS)]
    for round_results in (rounds or []):
        for r in round_results:
            out.append("\t".join(cell(v) for v in (
                r.round_no, r.seat, r.provider, r.model_requested,
                r.model_answered or "unknown", r.status, r.failure_class or "-",
                r.attempts, f"{r.elapsed_s:.2f}", r.exit_code,
                "yes" if r.timed_out else "no", r.prompt_hash, r.round_packet_hash,
            )))
    return "\n".join(out) + "\n"


def write_pre_spawn_artifacts(config: RunConfig, blobs: list, approval: EgressApproval,
                              content_hash: str) -> None:
    """Persist the APPROVED packet + recipe/manifest/sensitivity BEFORE any spawn.

    Writing the exact approved bytes up front means an interrupted fan-out still
    leaves a faithful record of what was approved and would egress (the artifact
    tree is designed for idempotent per-seat writes, §15). run-metadata is written
    AFTER the fan-out so it can carry the answered models + per-seat outcome.
    """
    out = config.out_dir
    os.makedirs(os.path.join(out, "prompts"), exist_ok=True)
    os.makedirs(os.path.join(out, "logs"), exist_ok=True)
    _write(os.path.join(out, "run-recipe.yaml"),
           dump_recipe(config_to_recipe(config), comments=RECIPE_COMMENTS))
    _write(os.path.join(out, "sensitivity.json"), render_sensitivity_json(config, approval))
    _write(os.path.join(out, "egress-manifest.md"),
           render_egress_manifest(config, blobs, content_hash))
    for b in blobs:
        _write(os.path.join(out, b.relpath), b.text)


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)

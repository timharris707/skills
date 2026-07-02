"""Renderers and writers for the pre-spawn artifacts: run-card, sensitivity.json,
the artifact tree, and the run-metadata stamp (md + tsv)."""
from __future__ import annotations

import json
import os
from typing import Optional

from _conductor.constants import (
    PRICING_AS_OF,
    SENSITIVITY_SCHEMA,
    price_band_usd,
    tier_provenance_line,
)
from _conductor.revise import SOURCE_MATERIAL_FILENAME
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
from _conductor.grounding import quoted_repo_paths, render_repo_scope_lines
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
    "seat_tokens_label",
    "render_cost_time_section",
    "render_run_metadata",
    "RUN_METADATA_TSV_COLUMNS",
    "RUN_METADATA_TSV_TOKEN_COLUMNS",
    "render_run_metadata_tsv",
    "write_pre_spawn_artifacts",
    "_write",
]


def _has_tokens(r) -> bool:
    """True when the seat CLI reported ANY usage for this seat-round."""
    return r.tokens_in is not None or r.tokens_out is not None or r.tokens_total is not None


def _tokens_total_or_none(r):
    """The seat-round's combined token count when derivable, else None."""
    if r.tokens_total is not None:
        return r.tokens_total
    if r.tokens_in is not None and r.tokens_out is not None:
        return r.tokens_in + r.tokens_out
    return None


def seat_tokens_label(r) -> str:
    """Human label for one seat-round's reported tokens ("unknown" when none)."""
    if r.tokens_in is not None and r.tokens_out is not None:
        total = _tokens_total_or_none(r)
        return f"in {r.tokens_in:,} · out {r.tokens_out:,} · total {total:,}"
    if r.tokens_total is not None:
        return f"total {r.tokens_total:,} (combined count; the CLI reports no in/out split)"
    return "unknown (the CLI reported no usage — not assumed)"


def seat_network_status(seat: SeatConfig, config: RunConfig) -> str:
    if config.network_on:
        return "on"
    return "off" if seat.adapter.isolates_network else "NOT ENFORCED"


def render_run_card(config: RunConfig) -> str:
    seats = "\n".join(
        f"    - {s.id:<7} {s.provider:<10} {s.model:<18} [{s.reasoning}]  — {s.lens}"
        for s in config.board
    )
    net = ", ".join(f"{s.id}={seat_network_status(s, config)}" for s in config.board)
    synth_line = "off (verdict.json hand-authored from the round artifacts)"
    if config.synthesize:
        chosen = config.synthesizer_seat or (
            "claude" if any(s.name == "claude" for s in config.board) else config.board[0].name)
        provider = next((s.provider for s in config.board if s.name == chosen),
                        config.board[0].provider)
        synth_line = (f"on — seat={chosen} → {provider} (no-lens; verdict.json drafted and "
                      "schema-validated; human still gates ship/abstain)")
    lines = [
        f"Advisory board run-card — {config.title}",
        f"  date          : {config.date}",
        f"  mode          : {config.mode}  (fs {'scoped' if config.fs_scoped else 'open'})",
        f"  network       : {net}",
        f"  sensitivity   : {config.sensitivity}",
        f"  rounds        : {config.rounds}    cross-reading: {config.cross_reading}",
        f"  lens preset   : {config.lens}",
        f"  output        : {config.output}"
        + (f"  (source type: {config.source_type})" if config.output == "revised-draft" else ""),
        f"  synthesizer   : {synth_line}",
        f"  source        : {config.source.ref} "
        f"({config.source.nbytes} bytes, {config.source.nlines} lines, sha256:{config.source.sha256[:12]}…)",
        f"  out dir       : {config.out_dir}",
        "  board         :",
        seats,
        "",
        f"  EGRESS        : {disclosure_line(config)}",
        f"                  consent = {consent_mode_for(config.sensitivity)}",
    ]
    if config.output == "revised-draft":
        # Pre-spawn seat PROJECTION — deliberately mirrors the synthesizer line
        # above (--seat → claude-if-seated → board[0]). Like the synthesizer, it
        # omits choose_revision_seat's "first usable seat" step: the card renders
        # before any round runs, so usability is unknown here. Keep the two in
        # lockstep — a change to one projection should change the other.
        chosen = config.revision_seat or (
            "claude" if any(s.name == "claude" for s in config.board) else config.board[0].name)
        provider = next((s.provider for s in config.board if s.name == chosen),
                        config.board[0].provider)
        # A code source also gets an apply-able revised-draft.patch; a prose
        # source's redline lives in the HTML handoff instead (D12).
        extra_artifact = (" + revised-draft.patch" if config.source_type == "code"
                          else " + a redline in the HTML handoff")
        lines += [
            f"  revision      : after synthesis — seat={chosen} → {provider} produces a "
            f"revised {config.source_type} copy",
            f"                  + changes.json (edit→finding mapping){extra_artifact}. Source is "
            "never written (D6); no new egress",
            "                  (the revision seat sees only source the run already sent).",
        ]
    if config.grounding is not None:
        g = config.grounding
        lines += [
            f"  repo grounding: {g.n_files} file(s), {g.n_bytes} bytes readable under {g.repo_root}",
            f"                  scope sha256:{g.scope_hash[:12]}…"
            + (f"  ·  ⚠ {len(g.secret_hits)} secret-scan hit(s)" if g.secret_hits else ""),
        ]
    if config.revision is not None:
        r = config.revision
        lines += [
            f"  revises       : {r.run_dir}"
            f"  (prior sensitivity: {r.prior_sensitivity or 'unknown'})",
            f"                  injected into round-1 prompts: {r.note} "
            f"({len(r.material.encode('utf-8'))} bytes — inside the packet hash)",
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
        "network_isolation": {s.id: seat_network_status(s, config) for s in config.board},
        "network_unenforced": config.unenforced_network_seats,
    }
    if config.grounding is not None:
        g = config.grounding
        payload["repo_scope"] = {
            "root": g.repo_root,
            "n_files": g.n_files,
            "n_bytes": g.n_bytes,
            "scope_hash": g.scope_hash,
            "include": g.include or [],
            "exclude": g.exclude or [],
            "secret_scan_hits": [{"path": rel, "kind": kind} for rel, kind in g.secret_hits],
        }
    if config.revision is not None:
        # --revise provenance on the consent record (mirrors repo_scope): what prior
        # material rides in the packet and how it was recovered. Only present on a
        # revise run, so every other sensitivity.json is unchanged.
        r = config.revision
        payload["revision"] = {
            "revises_run_dir": r.run_dir,
            "prior_sensitivity": r.prior_sensitivity,
            "prior_verdict_sha256": r.previous_run.get("verdict_sha256"),
            "source_recovered_from": r.source_recovered_from,
            "source_verified": r.source_verified,
            "injected_bytes": len(r.material.encode("utf-8")),
        }
    if config.ask is not None:
        # `ask` provenance on the consent record (mirrors revision): the post-verdict
        # question, which run it interrogates, and how the run context was recovered.
        # Only present on an ask, so every other sensitivity.json is unchanged.
        a = config.ask
        payload["ask"] = {
            "questioned_run_dir": a.run_dir,
            "question": a.question,
            "addressed_seats": [s.id for s in config.board],
            "prior_verdict_sha256": a.previous_run.get("verdict_sha256"),
            "prior_sensitivity": a.prior_sensitivity,
            "source_recovered_from": a.source_recovered_from,
            "source_verified": a.source_verified,
            "prompt_template": a.template_version,
            "prompt_template_sha256": a.template_sha256,
        }
        if a.floor_note:
            # The fail-closed flooring (no readable sensitivity.json -> never
            # public) is consent provenance — record WHY the posture tightened.
            payload["ask"]["sensitivity_floored"] = a.floor_note
    if approval is not None:
        payload["approval"] = {
            "approved": approval.approved,
            "mode": approval.mode,
            "content_hash": approval.content_hash,
            "timestamp": approval.timestamp,
        }
        # Only present on a grounded run, so an ungrounded sensitivity.json is unchanged.
        if approval.scope_hash is not None:
            payload["approval"]["scope_hash"] = approval.scope_hash
    return json.dumps(payload, indent=2) + "\n"


def render_artifact_tree(config: RunConfig) -> str:
    rounds = []
    # `auto` may run up to the ceiling; preview the maximum tree it could create.
    n = config.max_rounds if config.rounds == "auto" else int(config.rounds)
    for r in range(1, n + 1):
        rounds.append(f"  round-{r}/<seat>.md   round-{r}/<seat>.raw")
    packet_rounds = "\n".join(
        f"  board-packet-round-{r}.md" for r in range(2, n + 1)
    )
    seat_prompts = "\n".join(
        f"  prompts/{s.id}-round-1.prompt" for s in config.board
    )
    top = "  run-recipe.yaml   egress-manifest.md   sensitivity.json"
    if config.grounding is not None:
        top += "   repo-scope-manifest.json"
    parts = [
        f"{config.out_dir}/",
        top,
        seat_prompts,
        *rounds,
    ]
    if packet_rounds:
        parts.append(packet_rounds)
    if config.synthesize:
        parts += [
            "  prompts/synthesizer.prompt",
            "  synthesizer/<seat>.md   synthesizer/<seat>.raw",
        ]
    if config.output == "revised-draft":
        # The revised-draft filename depends on source_type: prose → .md, code →
        # the source's own extension (byte-clean, so a saved code file stays valid).
        # A code source ALSO gets a git-apply-able revised-draft.patch (D12); a
        # prose source gets none (its redline lives in the HTML handoff only).
        draft = "revised-draft.md" if config.source_type != "code" else "revised-draft.<orig-ext>"
        draft_line = (f"  {draft}   changes.json   revised-draft.patch"
                      if config.source_type == "code"
                      else f"  {draft}   changes.json")
        parts += [
            "  prompts/revision.prompt",
            "  revision/<seat>.md   revision/<seat>.raw",
            draft_line,
        ]
    parts += [
        "  logs/<seat>-round-N.stderr",
        "  verdict.json   final-consensus.md   handoff-data.json   final-consensus.html",
        "  run-metadata.md   run-metadata.tsv",
    ]
    return "\n".join(parts)


def render_convergence_section(convergence: dict) -> list:
    """The M1 convergence trace: why `--rounds auto` stopped, plus a per-transition
    movement table (verdict-token shifts + new-citation counts). `convergence` is
    the dict the conductor's round loop assembles; absent for a single-round run."""
    from _conductor.convergence import movement_detail_line
    movements = convergence.get("movements") or []
    stop_reason = convergence.get("stop_reason", "-")
    rounds_run = convergence.get("rounds_run", "-")
    mode = "auto" if convergence.get("is_auto") else f"fixed ({convergence.get('requested', '-')})"
    ceiling = convergence.get("max_rounds", "-")
    lines = [
        "",
        "## Convergence",
        "",
        f"Stop reason: {stop_reason}   ·   Rounds run: {rounds_run}   ·   "
        f"Ceiling (--max-rounds): {ceiling}   ·   Rounds mode: {mode}",
    ]
    if not movements:
        lines += ["", "Single round — no cross-round movement to measure."]
        return lines
    lines += [
        "",
        "| Transition | Seats moved | Considered | Per-seat movement |",
        "| ---------- | ----------- | ---------- | ----------------- |",
    ]
    for mv in movements:
        lines.append(
            f"| {mv['from_round']} → {mv['to_round']} | {mv['moved']} | "
            f"{mv['considered']} | {movement_detail_line(mv)} |"
        )
    lines += [
        "",
        "Movement is a pure function over each seat's parsed `VERDICT:` token and its "
        "concrete citation set (inline-code spans + slash paths) — never its prose "
        "(principle #1 / §11). A seat moved if its verdict token shifted or it added a "
        "new citation; `auto` stops when board-wide movement falls below the threshold.",
    ]
    return lines


def render_synthesizer_section(synth) -> list:
    """The M2 synthesizer trace: what spawned, whether the merged JSON validated,
    and the parse/schema reasons when not. `synth` is the SynthesizerResult the
    conductor's run_synthesizer returned; absent for a run without --synthesize."""
    accepted = "yes" if synth.verdict_data is not None else "no"
    lines = [
        "",
        "## Synthesizer",
        "",
        f"Seat: {synth.seat}   ·   Model requested: {synth.model_requested}   "
        f"·   Model answered: {synth.model_answered or 'unknown'}",
        f"Status: {synth.status}"
        + (f" ({synth.failure_class})" if synth.failure_class else ""),
        f"Elapsed: {synth.elapsed_s:.2f}s   ·   Attempts: {synth.attempts}   "
        f"·   Packet sha256: {synth.packet_hash[:16]}…",
        f"Accepted (passed advisory-board/verdict@2 validation): {accepted}",
    ]
    if synth.parse_error:
        lines.append(f"Parse error: {synth.parse_error}")
    if synth.schema_error:
        lines.append(f"Schema error: {synth.schema_error}")
    lines.append("")
    lines.append("The synthesizer is a no-lens reasoning seat (§11): briefed only on the "
                 "final-round reviews + the conductor-extracted VERDICT tokens, never the "
                 "source. The conductor merges its content fields into an authoritative "
                 "skeleton (schema/title/date/rounds/board[]) and runs `board_verdict.validate` "
                 "before writing verdict.json — the human still gates ship/abstain.")
    return lines


def render_cost_time_section(rounds: list) -> list:
    """The v1.11 cost/time trace for run-metadata.md — [] unless a seat REPORTED tokens.

    Emitting nothing when every seat-round is unknown keeps a tokenless run's
    run-metadata.md byte-identical to the pre-feature baseline (the standing
    invariant). When any CLI did report usage: the known token sum, a list-price
    cost band for the priceable part, and the measured wall clock — all labeled
    best-effort/estimate, never a gate.
    """
    results = [r for round_results in (rounds or []) for r in round_results]
    reported = [r for r in results if _has_tokens(r)]
    if not reported:
        return []
    known_totals = [t for t in (_tokens_total_or_none(r) for r in reported) if t is not None]
    tokens_sum = sum(known_totals)
    cost_low = cost_high = 0.0
    priced_any = False
    for r in reported:
        band = price_band_usd(r.model_requested, r.tokens_in, r.tokens_out, r.tokens_total)
        if band is not None:
            cost_low += band[0]
            cost_high += band[1]
            priced_any = True
    # Parallel fan-out: each round's wall clock is its slowest seat's elapsed time.
    wall_s = sum(max((r.elapsed_s for r in round_results), default=0.0)
                 for round_results in (rounds or []))
    rest = ("; the rest reported nothing and are counted as unknown, never guessed"
            if len(known_totals) < len(results) else " (every seat-round reported; "
            "unreported usage is counted as unknown, never guessed)")
    lines = [
        "",
        "## Cost & time (best effort)",
        "",
        f"- Tokens reported by the seat CLIs: {tokens_sum:,} across "
        f"{len(known_totals)} of {len(results)} seat-round(s){rest}.",
    ]
    if priced_any:
        lines.append(
            f"- Estimated cost of the reported tokens: ~${cost_low:.2f}–${cost_high:.2f} "
            f"at list prices dated {PRICING_AS_OF} (an ESTIMATE — subscription-backed "
            "CLIs may bill nothing per token; unknown/unpriced seat-rounds excluded).")
    else:
        lines.append(
            "- Cost: unknown — no verified list price for the reporting seats' models "
            "(see constants.MODEL_PRICING_USD_PER_MTOK).")
    lines.append(
        f"- Wall clock (measured): {wall_s / 60:.1f} min across {len(rounds or [])} round(s) "
        "— seats fan out in parallel, so each round costs its slowest seat.")
    return lines


def render_run_metadata(config: RunConfig, preflight: list, approval: EgressApproval,
                        rounds: Optional[list] = None, convergence: Optional[dict] = None,
                        synthesizer=None) -> str:
    # `rounds` is an ordered list of per-round result lists: [round1_results,
    # round2_results, ...]. None until the first fan-out completes. `convergence`
    # is the M1 stop-rule trace (movement per transition + stop reason).
    lines = [
        f"# Run Metadata — {config.title}",
        "",
        f"Date: {config.date}   ·   Rounds: {config.rounds}   ·   Cross-reading: {config.cross_reading}",
        f"Mode: {config.mode}   ·   Sensitivity: {config.sensitivity}   ·   Output: {config.output}",
        f"Lens preset: {config.lens}",
    ]
    # --tier provenance (v1.11 #3b): one line, and ONLY when the flag was given —
    # a no-tier run's run-metadata.md stays byte-identical to baseline.
    if config.tier:
        lines.append(f"Tier: {tier_provenance_line(config.tier)}")
    # --revise provenance (v1.12 #1): same discipline — only on a revise run.
    if config.revision is not None:
        lines.append(f"Revises: {config.revision.run_dir}   ·   "
                     f"injected: {config.revision.note}")
    lines += [
        "",
        "## Seats",
        "",
        "| Seat   | Lens | Model requested | Reasoning | Auth | Preflight |",
        "| ------ | ---- | --------------- | --------- | ---- | --------- |",
    ]
    pf = {p.seat: p for p in preflight}     # p.seat is the seat id
    for s in config.board:
        p = pf.get(s.id)
        verdict = ("GO" if p and p.go else "NO-GO") if p else "n/a"
        auth = p.auth if p else "n/a"
        lens_short = s.lens.split("—")[0].strip()
        lines.append(
            f"| {s.id:<6} | {lens_short} | {s.model} | {s.reasoning} | {auth} | {verdict} |"
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
    ]
    if approval.scope_hash is not None:
        lines.append(f"- Scope hash   : sha256:{approval.scope_hash}   (repo grounding; consent "
                     "bound to this too)")
    lines += [
        f"- Timestamp    : {approval.timestamp}",
        f"- Providers    : {', '.join(sorted({s.provider for s in config.board if s.provider != 'local'})) or '(none)'}",
        f"- Detail       : {approval.detail}",
    ]
    if config.grounding is not None:
        lines += ["", "## Readable repository scope", ""]
        lines += render_repo_scope_lines(config.grounding)
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
        # Per-seat token capture (v1.11 #3a) — rendered ONLY when a CLI actually
        # reported usage this round, so a tokenless run (all seats unknown) keeps
        # this file byte-identical to the pre-feature baseline.
        token_rows = [r for r in round_results if _has_tokens(r)]
        if token_rows:
            lines += ["", "Tokens as reported by the seat CLIs (if known; capture is best-effort):"]
            for r in token_rows:
                lines.append(f"- {r.seat}: {seat_tokens_label(r)}")
        # Post-hoc egress accounting (R4): the pre-spawn scope hash bounds what a seat
        # COULD read; this records which in-scope paths each usable reply actually
        # referenced. Best-effort substring match — over-, not under-counts.
        if config.grounding is not None:
            scope_paths = config.grounding.scope_paths
            lines += ["", f"Repo paths referenced in round {n} (best-effort, not a proof of read):"]
            any_ref = False
            for r in round_results:
                if not r.usable:
                    continue
                cited = quoted_repo_paths(r.stdout, scope_paths)
                if cited:
                    any_ref = True
                    shown = ", ".join(f"`{p}`" for p in cited[:15])
                    more = len(cited) - 15
                    lines.append(f"- {r.seat}: {shown}" + (f" (+{more} more)" if more > 0 else ""))
            if not any_ref:
                lines.append("- (no in-scope repo path referenced in any usable reply this round)")
        # Provider-correlation disclosure (§12): "three voices" can be fewer
        # providers; the answered models above expose it, and antigravity's model
        # is structurally unknowable (it silently substitutes — never trusted).
    if convergence is not None:
        lines += render_convergence_section(convergence)
    if synthesizer is not None:
        lines += render_synthesizer_section(synthesizer)
    # Cost & time (v1.11 #3a) — empty (and therefore absent) unless a seat CLI
    # actually reported token usage, keeping tokenless runs byte-identical.
    lines += render_cost_time_section(rounds)
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
        if config.grounding is not None:
            lines.append("- Round 2+ egresses round-1 reviews to the same providers under the "
                         "disclosed multi-round plan. With --repo, a round-1 reply CAN carry fresh "
                         "repo-derived quotes (within the approved scope hash); D8 elides verbatim "
                         "repo bodies from the cross-reading packet (matched against in-scope file "
                         "content), keeping path:line citations, to limit one seat's read becoming a "
                         "cross-provider broadcast.")
        else:
            lines.append("- Round 2+ egresses round-1 reviews (derivatives of already-approved "
                         "source) to the same providers under the disclosed multi-round plan; each "
                         "round's packet hash is recorded in round-N/<seat>.raw and run-metadata.tsv.")
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
    "verdict", "failure_class", "attempts", "elapsed_s", "exit_code", "timed_out",
    "prompt_sha256", "packet_sha256",
)

# Trailing token columns (v1.11 #3a), appended ONLY when at least one seat-round
# actually reported usage. A tokenless run keeps the original header and rows
# byte-identical to the pre-feature baseline (and existing consumers that read
# the packet hash as the LAST column keep working); "-" marks an unknown cell.
RUN_METADATA_TSV_TOKEN_COLUMNS = ("tokens_in", "tokens_out", "tokens_total")


def render_run_metadata_tsv(rounds: list) -> str:
    """The diffable, machine-readable provenance companion to run-metadata.md
    (§12): one row per seat per round, including the parsed `VERDICT:` token (M1)
    so the movement trace is reproducible from the TSV. Tabs are stripped from any
    field so the TSV can't be corrupted by a stray tab in a model id. When any
    seat CLI reported token usage, three trailing columns (tokens_in, tokens_out,
    tokens_total) are appended — see RUN_METADATA_TSV_TOKEN_COLUMNS."""
    def cell(v) -> str:
        return str(v).replace("\t", " ").replace("\n", " ")
    results = [r for round_results in (rounds or []) for r in round_results]
    with_tokens = any(_has_tokens(r) for r in results)
    columns = RUN_METADATA_TSV_COLUMNS + (RUN_METADATA_TSV_TOKEN_COLUMNS if with_tokens else ())
    out = ["\t".join(columns)]
    for round_results in (rounds or []):
        for r in round_results:
            values = [
                r.round_no, r.seat, r.provider, r.model_requested,
                r.model_answered or "unknown", r.status, r.verdict or "-",
                r.failure_class or "-", r.attempts, f"{r.elapsed_s:.2f}", r.exit_code,
                "yes" if r.timed_out else "no", r.prompt_hash, r.round_packet_hash,
            ]
            if with_tokens:
                values += [
                    r.tokens_in if r.tokens_in is not None else "-",
                    r.tokens_out if r.tokens_out is not None else "-",
                    r.tokens_total if r.tokens_total is not None else "-",
                ]
            out.append("\t".join(cell(v) for v in values))
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
    if config.grounding is not None:
        # Persist the exact read surface consent bound to, so `verify` and a later
        # audit can resolve citations against the same file list + scope hash.
        _write(os.path.join(out, "repo-scope-manifest.json"),
               json.dumps(config.grounding.manifest, indent=2) + "\n")
    # Persist the exact reviewed source (v1.12 #1) so a later `--revise` of THIS
    # run can diff against it. Post-approval only, next to the prompts that embed
    # the same bytes — the same consent envelope and sensitivity handling
    # (references/data-handling.md).
    _write(os.path.join(out, SOURCE_MATERIAL_FILENAME), config.source.text)
    for b in blobs:
        _write(os.path.join(out, b.relpath), b.text)


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)

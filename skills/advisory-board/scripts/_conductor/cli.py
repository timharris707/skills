"""The argparse front end: subcommand handlers, the delegation shim, and main()."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys

from _conductor.constants import (
    DEFAULT_LENS,
    DEFAULT_MAX_ROUNDS,
    EXIT_EGRESS_BLOCKED,
    EXIT_NO_VERDICT,
    EXIT_OK,
    EXIT_PREFLIGHT_NOGO,
    EXIT_USAGE,
    SMOKE_PROMPT,
    die,
    estimate_run,
    render_estimate,
)
from _conductor.registry import REGISTRY
from _conductor.convergence import (
    DEFAULT_CONVERGE_THRESHOLD,
    SCORE_MAX,
    SCORE_MIN,
    board_movement,
    movement_detail_line,
)
from _conductor.config import (
    default_runs_root,
    parse_board,
    resolve_config,
)
from _conductor.grounding import (
    cleanup_snapshot,
    prepare_grounding,
)
from _conductor.revise import prepare_revision
from _conductor.ask import run_ask
from _conductor.history import (
    collect_history,
    render_history_table,
)
from _conductor.toolchain import (
    check_toolchain,
    install_missing_tools,
    render_toolchain_table,
    update_stale_tools,
)
from _conductor.egress import (
    build_packet,
    build_round2,
    disclosure_line,
    enforce_egress_gate,
    packet_hash,
    render_egress_manifest,
)
from _conductor.preflight import (
    render_board_guidance,
    render_preflight_table,
    run_preflight,
)
from _conductor.doctor import (
    conductor_script_path,
    find_sample_source,
    render_doctor_header,
    render_doctor_summary,
    render_provider_block,
    run_doctor,
    summarize_doctor,
)
from _conductor.recipe import (
    RECIPE_COMMENTS,
    config_to_recipe,
    dump_recipe,
)
from _conductor.artifacts import (
    _write,
    render_artifact_tree,
    render_run_card,
    render_run_metadata,
    render_run_metadata_tsv,
    render_sensitivity_json,
    write_pre_spawn_artifacts,
)
from _conductor.rounds import (
    _argv_preview,
    render_round_table,
    run_round,
    write_round_artifacts,
)
from _conductor.status import (
    NullTracker,
    OUTCOME_INTERRUPTED,
    StatusTracker,
)
from _conductor.synthesizer import (
    SYNTHESIZER_TEMPLATE_VERSION,
    choose_synthesizer_seat,
    render_synthesizer_raw,
    run_synthesizer,
    synthesizer_template_sha,
)
from _conductor.revision import (
    REVISION_TEMPLATE_VERSION,
    build_unified_patch,
    choose_revision_seat,
    render_revision_raw,
    revision_template_sha,
    run_revision,
)
from _conductor.endorsement import (
    ENDORSEMENT_TEMPLATE_VERSION,
    endorsement_seats,
    endorsement_template_sha,
    render_endorsement_md,
    render_endorsement_raw,
    run_endorsement_pass,
)
from _conductor.rubric import (
    RUBRIC_CHAIR_TEMPLATE_VERSION,
    RUBRIC_REFUSAL_EXIT,
    MIN_USABLE_PROPOSALS,
    build_rubric_proposal_blobs,
    choose_chair_seat,
    mint_proposals,
    render_chair_md,
    render_chair_raw,
    render_rubric_proposal_md,
    render_rubric_proposal_raw,
    rubric_chair_template_sha,
    rubric_proposal_template_sha,
    rubric_proposal_template_version,
    run_rubric_chair,
    run_rubric_proposals,
)

__all__ = [
    "cmd_init",
    "cmd_preflight",
    "cmd_toolchain",
    "cmd_doctor",
    "_maybe_update_tools",
    "cmd_run",
    "_run_rubric_step",
    "_run_revision_step",
    "_run_endorsement_pass",
    "cmd_ask",
    "cmd_history",
    "cmd_render",
    "cmd_consensus",
    "cmd_verify",
    "cmd_validate",
    "_delegate",
    "add_run_options",
    "build_parser",
    "main",
]


def cmd_init(args) -> int:
    config = resolve_config(args)
    recipe_text = dump_recipe(config_to_recipe(config), comments=RECIPE_COMMENTS)
    if getattr(args, "dry_run", False):
        print(render_run_card(config))
        print()
        print("--- run-recipe.yaml (not written; --dry-run) ---")
        print(recipe_text, end="")
        return EXIT_OK
    os.makedirs(config.out_dir, exist_ok=True)
    path = os.path.join(config.out_dir, "run-recipe.yaml")
    _write(path, recipe_text)
    print(render_run_card(config))
    print(f"\nwrote {path}")
    return EXIT_OK


def cmd_preflight(args) -> int:
    config = resolve_config(args)
    results = run_preflight(config)
    print(render_preflight_table(results))
    go = sum(1 for r in results if r.go)
    if go < 2:
        guidance = render_board_guidance(results, config)
        if guidance:
            print("\n" + guidance)
        return EXIT_PREFLIGHT_NOGO
    return EXIT_OK


def cmd_toolchain(args) -> int:
    # No --board => check EVERY registered seat CLI (incl. ones outside the default
    # board, like antigravity), since toolchain currency is about all installed CLIs.
    board_arg = getattr(args, "board", None)
    if board_arg:
        # parse_board returns (alias, provider) specs; toolchain currency is per-CLI, so
        # check each distinct provider once (a duplicate-seat board reuses one CLI).
        names = []
        for _, provider in parse_board(board_arg):
            if provider not in names:
                names.append(provider)
    else:
        names = list(REGISTRY.keys())
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        die(f"unknown seat(s): {', '.join(unknown)}", EXIT_USAGE)
    statuses = check_toolchain([REGISTRY[n] for n in names])
    print(render_toolchain_table(statuses))
    rc = EXIT_OK
    assume_yes = getattr(args, "yes", False)
    if getattr(args, "install", False):
        if install_missing_tools(statuses, assume_yes=assume_yes) != 0:
            rc = EXIT_USAGE
    if getattr(args, "update", False):
        if update_stale_tools(statuses, assume_yes=assume_yes) != 0:
            rc = EXIT_USAGE
    return rc


def cmd_doctor(args) -> int:
    # Guided onboarding (roadmap v1.11 #7): sweep EVERY registered provider — not
    # just a chosen board — and print per-provider fix-it steps plus which boards
    # are viable today. Probes and smoke-pings only; the header says so. Blocks
    # stream as each provider is probed (a slow one can take up to a minute).
    names = list(REGISTRY)
    print(render_doctor_header(names))
    print()

    def _emit(health) -> None:
        print(render_provider_block(health))
        print()

    healths = run_doctor(names, on_result=_emit)
    summary = summarize_doctor(healths)
    print(render_doctor_summary(summary, sample_source=find_sample_source(),
                                script_path=conductor_script_path()))
    return EXIT_OK if summary["viable"] else EXIT_PREFLIGHT_NOGO


def _maybe_update_tools(config, args) -> None:
    """run --update-tools: check currency and (consent-gated) update before the board."""
    if not getattr(args, "update_tools", False):
        return
    print("=== toolchain ===")
    statuses = check_toolchain([seat.adapter for seat in config.board])
    print(render_toolchain_table(statuses))
    update_stale_tools(statuses, assume_yes=getattr(args, "yes", False))
    print()


def cmd_run(args) -> int:
    config = resolve_config(args)   # validates --max-rounds (>= 1) too
    # Repo-grounding: resolve + snapshot + hash the read surface ONCE, before the
    # egress gate, so consent binds to the scope (P2). A real run snapshots (the
    # frozen bytes seats read + verify resolves against); --dry-run only previews the
    # live tree. The snapshot is a temp dir — always cleaned up, even on a NO-GO/error.
    if config.grounded:
        config.grounding = prepare_grounding(config, snapshot=not getattr(args, "dry_run", False))
    # --revise (v1.12 #1): build the revision context BEFORE the packet, so the
    # injected digest+diff bytes are inside the consent hash. Reads the prior run
    # dir only — nothing egresses here.
    if config.revise_of:
        config.revision = prepare_revision(config)
    try:
        return _execute_run(config, args)
    finally:
        if config.grounding is not None and config.grounding.snapshot_dir:
            cleanup_snapshot(config.grounding.snapshot_dir)


def _execute_run(config, args) -> int:
    # --digest-format json serializes the STRUCTURED digest, which only exists under
    # --cross-reading summaries (`full` is verbatim reviews; `none` has no board
    # packet). Refuse the meaningless combination up front — loudly, not silently.
    digest_json = getattr(args, "digest_format", "markdown") == "json"
    if digest_json and config.cross_reading != "summaries":
        # Name the real cause: under --tier the offending value may come from the
        # preset, not a flag the user typed (an explicit flag still wins over it).
        cause = ""
        if config.tier and getattr(args, "cross_reading", None) is None:
            cause = (f", set by --tier {config.tier} — an explicit "
                     "--cross-reading summaries overrides the tier")
        die("--digest-format json serializes the structured digest, which requires "
            f"--cross-reading summaries (this run uses {config.cross_reading!r}{cause})",
            EXIT_USAGE)

    blobs = build_packet(config)
    # B1: under --rubric, the PROPOSAL-pass prompts are deterministic pre-run — each
    # embeds the source PLUS the SHARED composed review-context (P3): the same surface
    # round 1 carries beyond the bare source (the --repo grounding clause and/or the
    # --revise prior-verdict digest + source diff, from the ONE builder both read — set
    # pre-round only from config.revise_of; a revised-draft run without --revise revises
    # AFTER synthesis and adds no pre-round revision context). config.grounded is
    # resolved and config.revision.material is built
    # (cmd_run, above) before this point, so the composed context is deterministic and
    # these EXACT bytes are prebuilt HERE and folded into the egress manifest + consent
    # CONTENT HASH — consent binds the true outbound proposal bytes, composed context
    # included, not just the round-1 prompts. A source-only rubric renders the composed
    # splice empty (byte-identical to before), so plain --rubric is unchanged. The
    # rubric step spawns from these exact blobs (re-asserting the hash first). `blobs`
    # stays the round-1 packet the round fan-out consumes; `egress_blobs` is what the
    # gate, manifest, and content hash cover (round-1 ∪ rubric-proposal). The CHAIR
    # prompt is a board-generated derivative (it embeds seat proposals that don't exist
    # yet) and follows the round-2 precedent — its packet hash is logged at spawn, not
    # in this initial consent hash. (See rubric.py's CONSENT-HASH BINDING docstring.)
    rubric_blobs = build_rubric_proposal_blobs(config) if config.rubric else []
    egress_blobs = blobs + rubric_blobs
    content_hash = packet_hash(egress_blobs)

    if getattr(args, "dry_run", False):
        print(render_run_card(config))
        print()
        print("=== preflight plan (commands that WOULD run; not executed) ===")
        preview_workdir = config.out_dir if config.fs_scoped else None
        for seat in config.board:
            argv = seat.adapter.build_argv(seat.model, SMOKE_PROMPT, reasoning=seat.reasoning,
                                           workdir=preview_workdir, network=config.network_on)
            print(f"  {seat.name}: {_argv_preview(argv)}")
        print()
        print("=== egress manifest (preview) ===")
        print(render_egress_manifest(config, egress_blobs, content_hash), end="")
        print()
        print("=== artifact tree it WOULD create ===")
        print(render_artifact_tree(config))
        print()
        # The preflight cost/time estimate (v1.11 #3a) — the "know before you
        # convene" number SKILL.md's large-run flag points at. Pure function of
        # the run shape (deterministic), best-effort, and never a gate.
        print("=== estimate (best effort — never a gate) ===")
        est_rounds = config.max_rounds if config.rounds == "auto" else int(config.rounds)
        # Price the chair spawn on the ACTUAL projected chair seat's model (not
        # board[0]): choose_chair_seat is the same claude-if-seated → board[0]
        # projection the run uses, honoring --chair-seat. Only computed under --rubric;
        # the config is already resolved, so the preferred chair is on-board (no die()).
        est_chair_model = (choose_chair_seat(config, preferred=config.chair_seat).model
                           if config.rubric else None)
        est = estimate_run(config.source.nbytes, [s.model for s in config.board],
                           est_rounds, config.cross_reading, rubric=config.rubric,
                           chair_model=est_chair_model)
        for line in render_estimate(est):
            print(f"  {line}")
        if config.rounds == "auto":
            print(f"  (--rounds auto: sized at the --max-rounds ceiling of {config.max_rounds}; "
                  "the convergence stop-rule may finish earlier and cheaper)")
        print()
        print(f"[dry-run] no preflight, no packet written, no egress, no spawn. "
              f"content hash = sha256:{content_hash}")
        return EXIT_OK

    # 0. Say where artifacts land, loudly, before anything else runs (v1.11: the
    #    default moved from a throwaway /tmp dir to the persistent runs root — D5's
    #    one loudly-documented default change). One line, always.
    if getattr(args, "ephemeral", False):
        where_note = "  (ephemeral — a /tmp dir the OS may clean; default runs persist)"
    elif (getattr(args, "from_recipe", None) and not getattr(args, "out", None)
          and os.path.isdir(config.out_dir)):
        # A recipe re-run reuses the recipe's RECORDED dir — which now persists,
        # so replaying rewrites that run's artifacts in place. Say so.
        where_note = "  (recipe re-run — rewriting the recipe's recorded run dir; --out DIR for a fresh one)"
    elif (getattr(args, "out", None) or getattr(args, "from_recipe", None)
          or getattr(args, "runs_root", None)):
        where_note = ""   # the user (or the recipe) chose — no default hint to give
    else:
        where_note = "  (persistent default — --out DIR, --runs-root DIR, or --ephemeral to relocate)"
    print(f"run artifacts → {config.out_dir}{where_note}\n")

    # 0a. Live progress view (v1.14 #10): a status.json + self-refreshing status.html
    #     in the run dir, rewritten atomically on every seat/round/stage transition,
    #     plus flushed per-seat terminal lines — the run dir is the only live window
    #     while stdout block-buffers a background run. Best-effort: a status-write
    #     failure warns once and never touches the run. --no-live-status opts out for
    #     a byte-exact run dir (a NullTracker keeps the hook sites branch-free).
    if not config.live_status:
        tracker = NullTracker()
    else:
        planned = config.max_rounds if config.rounds == "auto" else int(config.rounds)
        tracker = StatusTracker(config.out_dir, title=config.title,
                                rounds_planned=planned, seats=config.board)

    def _seat_cb(event, seat_id, round_no, result):
        # Bridge rounds.run_round's per-seat callback → the tracker. Runs from the
        # fan-out's worker threads; the tracker serializes internally.
        detail = None
        if event == "done" and result is not None:
            detail = f"{result.elapsed_s:.0f}s"
        elif event == "dropped" and result is not None:
            detail = result.failure_class or "no usable review"
        tracker.seat(seat_id, event, round_no, detail)

    # 0b. Toolchain currency (opt-in): update stale CLIs before probing, so a
    #     freshly-renamed model id resolves instead of 404-ing the board.
    _maybe_update_tools(config, args)

    # 1. Preflight — GO/NO-GO before anything else.
    tracker.stage("preflight", "started")
    print("=== preflight ===")
    preflight = run_preflight(config)
    print(render_preflight_table(preflight))
    go = sum(1 for r in preflight if r.go)
    if go < 2:
        guidance = render_board_guidance(preflight, config)
        if guidance:
            print("\n" + guidance)
        tracker.finish("no-board", f"preflight NO-GO ({go} of {len(preflight)} seats GO)")
        die("fewer than two seats are GO — not running a one-voice board", EXIT_PREFLIGHT_NOGO)
    tracker.stage("preflight", "done", f"{go} of {len(preflight)} seats GO")

    # 2. Egress gate — the pre-spawn hard stop. Nothing has left the machine yet;
    #    the smoke pings above carried only a fixed token, never the source.
    tracker.stage("egress", "started")
    print("\n=== egress gate ===")
    print(disclosure_line(config))
    approval = enforce_egress_gate(
        config, egress_blobs,
        assume_yes=getattr(args, "yes", False),
        skip_gate=getattr(args, "skip_sensitivity_gate", False),
    )
    # B1: when the approved content hash folds in the prebuilt rubric proposal prompts,
    # record the round-1 SUB-hash so run_round's round-1 pre-spawn guard can re-assert
    # the exact round-1 bytes (packet_hash(round-1 blobs) no longer == content_hash).
    # None on a non-rubric run, so the guard's fallback keeps identical behavior.
    if rubric_blobs:
        approval.round1_hash = packet_hash(blobs)
    print(f"egress: {'APPROVED' if approval.approved else 'REFUSED'} "
          f"({approval.mode}) — {approval.detail}")
    print(f"content hash: sha256:{content_hash}")

    if not approval.approved:
        # Persist the manifest + a machine-readable refusal record so the user can
        # review exactly what was blocked. The packet/prompts are NOT written —
        # nothing the gate refused may be materialized (the pre-spawn hard stop).
        os.makedirs(config.out_dir, exist_ok=True)
        _write(os.path.join(config.out_dir, "egress-manifest.md"),
               render_egress_manifest(config, egress_blobs, content_hash))
        _write(os.path.join(config.out_dir, "sensitivity.json"),
               render_sensitivity_json(config, approval))
        tracker.finish("egress-blocked", "egress refused at the gate")
        die(f"egress blocked — see {config.out_dir}/egress-manifest.md", EXIT_EGRESS_BLOCKED)
    tracker.stage("egress", "done", f"approved ({approval.mode})")

    # 3. Approved: persist the exact approved packet + provenance BEFORE spawning.
    #    egress_blobs (round-1 ∪ rubric-proposal) is the full approved packet — the
    #    manifest + the on-disk prompt files cover the rubric proposal prompts too.
    write_pre_spawn_artifacts(config, egress_blobs, approval, content_hash)
    # The run has committed to spawning + materialized its dir — NOW the live view
    # may write status.json/status.html (before this, a NO-GO preflight or a refused
    # egress must leave no dir; RH-1). This flush carries the full pre-spawn history
    # (preflight + egress events already recorded in memory).
    tracker.activate()

    # Abort guard (v1.14 #10, P3 finding O3): once activate() has committed the live
    # view to disk, ANY abnormal exit from the run body below — a die() inside run_round
    # (egress-hash / repo-scope drift), a KeyboardInterrupt, an unhandled exception —
    # would otherwise skip the normal tracker.finish() and leave status.json unfinished
    # + status.html meta-refreshing forever over a dead run. The finally stamps a terminal
    # `interrupted` outcome ONLY if the body didn't already finish (a normal path stamps
    # its own outcome), re-rendering the now-STATIC html, then the exception RE-RAISES
    # untouched — exit codes and die() messages are unchanged. Best-effort: a failing
    # stamp must never mask the original exception.
    try:
        return _run_after_activate(
            config, args, tracker, blobs, approval, content_hash,
            preflight, digest_json, _seat_cb, _write, rubric_blobs=rubric_blobs)
    finally:
        try:
            tracker.finish_if_unfinished(
                OUTCOME_INTERRUPTED,
                "run aborted before a terminal outcome (die/interrupt/exception)")
        except Exception:
            pass   # best-effort: the stamp must not mask the original exception


def _scoring_detail(results: list, criterion_ids) -> str:
    """A compact `; scored N/M cells` suffix for the round-done status detail on a
    --rubric run (D17 — scores land in seat review parsing; this is the status-event
    surface P4's scorecard reads the trajectory from). Empty on a non-rubric round
    (criterion_ids None), so a plain run's status detail is unchanged. Never raises."""
    if not criterion_ids:
        return ""
    usable = [r for r in results if r.usable]
    total = len(usable) * len(criterion_ids)
    got = sum(len(r.scores) for r in usable)   # r.scores is a per-access parse; one read each
    return f"; scored {got}/{total} cells"


def _print_scoring_summary(results: list, criterion_ids) -> None:
    """Print the per-seat per-criterion scores for a scored round (D17). One line per
    usable seat: the seat's scores in c1…cN order, a missing cell as "—" (never imputed),
    plus its `RUBRIC-NOTE:` objection if any. No-op on a non-rubric round. This is the
    human-facing surface of the parsed scores; P4 consumes the same parsed scores off the
    result objects (`r.scores`, `r.rubric_note`) to write scorecard.json."""
    if not criterion_ids:
        return
    # "1–5" here is hand-coupled to convergence.SCORE_MIN=1 / SCORE_MAX=5 (see the COUPLING
    # note on prompts.RUBRIC_SCORING_BLOCK). If the band changes, update both prose sites.
    print(f"scores ({SCORE_MIN}–{SCORE_MAX}; — = no clean SCORE line, never imputed):")
    for r in results:
        if not r.usable:
            continue
        s = r.scores   # bind once — the property re-parses stdout on every access
        cells = " ".join(f"{cid}={s[cid]}" if cid in s else f"{cid}=—"
                         for cid in criterion_ids)
        partial = "  (partial)" if len(s) < len(criterion_ids) else ""
        note = f"  · RUBRIC-NOTE: {r.rubric_note}" if r.rubric_note else ""
        print(f"  {r.seat:<8} {cells}{partial}{note}")


def _run_after_activate(config, args, tracker, blobs, approval, content_hash,
                        preflight, digest_json, _seat_cb, _write,
                        *, rubric_blobs=None) -> int:
    """The post-activate run body (rounds → synthesis/hand-off). Split out of
    _execute_run so its caller can wrap it in the abort guard: everything here runs
    AFTER the live view committed to disk, so any abnormal exit must land in that
    guard's finally to stamp a terminal outcome + a static html. Returns the run's
    exit code; raises on a die()/interrupt/exception exactly as before (the guard
    re-raises untouched)."""
    # 3b. Rubric-first (v1.15 #P2 — D15/D16/D18/D20): a pre-round-1 pass. When --rubric
    #     is on, every seat proposes weighted criteria in parallel and one chair merges
    #     them into rubric.json BEFORE any opinion round spends a token. It runs INSIDE
    #     this guard (so an abort still stamps a terminal status), AFTER egress consent
    #     (the proposal packet embeds the same source the round-1 packet already sends —
    #     no new consent category). A refusal (<2 usable proposals, or a chair merge the
    #     conductor can't reconcile) returns RUBRIC_REFUSAL_EXIT — the run cannot
    #     proceed to a meaningful board without a rubric, and nothing valuable exists yet
    #     to protect (D20's one non-never-fail-the-run posture). On success rubric.json
    #     is written and the run proceeds to round 1. (Injecting the rubric into the
    #     round prompts + scoring is P3's job; P2 stops at rubric.json.)
    # v1.15 #P3: the merged rubric's criteria (c1…cN), injected into every round's
    # scoring block. None on a non-rubric run — the {rubric_scoring} fill stays empty
    # and the round bytes are byte-identical to a non-rubric run (D5/D6).
    rubric_criteria = None
    criterion_ids = None
    if config.rubric:
        outcome = _run_rubric_step(config, blobs, approval, tracker=tracker,
                                   _write=_write, rubric_blobs=rubric_blobs)
        if isinstance(outcome, int):
            return outcome   # a refusal exit code — nothing valuable ran yet (D20)
        # Success: the merged rubric dict. Rebuild the round-1 packet WITH the scoring
        # block. This scored packet is a DERIVATIVE of already-approved material (the
        # proposal fan-out consent-hashed prompts + the chair merge, covered by the
        # disclosed rubric plan) — the round-2 precedent, NOT the --revise one (the
        # chair merge is not deterministic pre-approval). run_round records its hash for
        # provenance and reuses the approval rather than re-asserting the round-1
        # sub-hash (see the RUBRIC_SCORING_BLOCK consent note in prompts.py).
        rubric_criteria = outcome.get("criteria") or []
        criterion_ids = tuple(c["id"] for c in rubric_criteria if isinstance(c, dict) and c.get("id"))
        blobs = build_packet(config, rubric_criteria=rubric_criteria)
        for b in blobs:
            _write(os.path.join(config.out_dir, b.relpath), b.text)

    # 4. Round-1 fan-out (M3) — the first real spawn. run_round re-asserts the
    #    egress hash one last time, then feeds each seat its approved blob verbatim
    #    (so the bytes that actually leave equal what consent was bound to), with
    #    per-seat timeout / one-retry / failure classification (§13). The --timeout
    #    values (bare default + id=SECONDS overrides) are already resolved onto each
    #    SeatConfig (config.resolve_board), so the fan-out reads them per seat.
    print("\n=== round 1 (fan-out) ===")
    tracker.round_started(1)
    r1 = run_round(config, blobs, approval, round_no=1, on_seat=_seat_cb,
                   criterion_ids=criterion_ids, rubric_criteria=rubric_criteria)
    write_round_artifacts(config, r1, 1)
    rounds_done = [r1]
    tracker.round_done(1, f"{sum(1 for r in r1 if r.usable)} of {len(r1)} usable"
                       + _scoring_detail(r1, criterion_ids))
    print(render_round_table(r1, 1))
    _print_scoring_summary(r1, criterion_ids)

    usable1 = [r for r in r1 if r.usable]
    if len(usable1) < 2:
        _write(os.path.join(config.out_dir, "run-metadata.md"),
               render_run_metadata(config, preflight, approval, rounds=rounds_done))
        _write(os.path.join(config.out_dir, "run-metadata.tsv"),
               render_run_metadata_tsv(rounds_done))
        tracker.finish("no-board", f"only {len(usable1)} usable round-1 review(s)")
        print(f"\nwrote run dir: {config.out_dir}")
        print(f"\nWARNING: only {len(usable1)} of {len(r1)} seats produced a usable "
              "round-1 review — that is not a board. Inspect round-1/*.raw and logs/, fix "
              "the failed seats, and re-run. Round 2 and synthesis are intentionally NOT "
              "attempted on fewer than two voices.")
        return EXIT_PREFLIGHT_NOGO

    # 5. Rounds 2…N (M4 + M1) — cross-reading + debate, looped under the stop-rule.
    #    Only seats usable in the PREVIOUS round continue; each is re-supplied the
    #    source AND (per --cross-reading) that round's reviews. This egresses
    #    derivatives of already-approved source to the same providers under the
    #    disclosed multi-round plan, so each round records its own packet hash but
    #    reuses the run's approval (no re-prompt). `--rounds auto` keeps looping
    #    while the board is still MOVING — a verdict-token shift or a new citation,
    #    measured by a pure function over the parsed tokens (principle #1) — and
    #    stops the moment movement falls below the threshold, or at --max-rounds.
    #    An explicit `--rounds N` runs exactly N rounds (movement is still recorded).
    is_auto = config.rounds == "auto"
    max_rounds = config.max_rounds
    target = max_rounds if is_auto else int(config.rounds)
    movements: list = []
    stop_reason = None
    prev = r1
    round_no = 2
    while round_no <= target:
        if len([r for r in prev if r.usable]) < 2:
            stop_reason = "insufficient-voices"   # a one-voice round is not a board
            break
        rN_blobs, board_packet = build_round2(config, prev, round_no=round_no,
                                              rubric_criteria=rubric_criteria)
        if board_packet is not None:
            _write(os.path.join(config.out_dir, f"board-packet-round-{round_no}.md"), board_packet)
            if digest_json:
                # --digest-format json: the SAME parsed signals the markdown digest
                # carries, serialized as typed JSON next to the .md (no new reasoning).
                import json as _json
                from _conductor.digest import build_structured_digest_data
                payload = build_structured_digest_data(
                    [r for r in prev if r.usable], round_no=round_no)
                _write(os.path.join(config.out_dir, f"board-packet-round-{round_no}.json"),
                       _json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        for b in rN_blobs:
            _write(os.path.join(config.out_dir, b.relpath), b.text)
        rN_hash = packet_hash(rN_blobs)
        print(f"\n=== round {round_no} (cross-reading + debate) ===")
        print(f"cross-reading: {config.cross_reading}  ·  round-{round_no} packet hash: sha256:{rN_hash}")
        if config.grounding is not None:
            print(f"(round {round_no} sends each seat's round-{round_no - 1} review to the others at "
                  "the same providers; with --repo a review CAN carry repo-derived quotes within the "
                  "approved scope — D8 elides verbatim repo bodies from the cross-reading packet.)")
        else:
            print(f"(round {round_no} sends each seat's round-{round_no - 1} review to the others at "
                  "the same providers — no new source egresses; covered by the run-card's disclosed "
                  "multi-round plan.)")
        tracker.round_started(round_no)
        rN = run_round(config, rN_blobs, approval, round_no=round_no, on_seat=_seat_cb,
                       criterion_ids=criterion_ids)
        write_round_artifacts(config, rN, round_no)
        rounds_done.append(rN)
        # Movement is widened by the score arm on a --rubric run (D19): criterion_ids
        # enables the per-criterion score-change check; None (non-rubric) is the
        # unchanged two-arm movement. Compute it BEFORE round_done so the still-moving
        # criteria can ride into the round-done status detail — status.json consumers
        # (P4's scorecard reads the trajectory off round_done) recover which criteria
        # were still moving from the event itself, not just the console.
        mv = board_movement(prev, rN, criterion_ids=criterion_ids)
        movements.append(mv)
        moving = mv.get("moving_criteria") or []
        crit_note = (f"; criteria still moving: {', '.join(moving)}" if moving else "")
        tracker.round_done(round_no, f"{sum(1 for r in rN if r.usable)} of {len(rN)} usable"
                           + _scoring_detail(rN, criterion_ids) + crit_note)
        print(render_round_table(rN, round_no))
        _print_scoring_summary(rN, criterion_ids)
        print(f"movement {mv['from_round']} → {mv['to_round']}: {mv['moved']} of "
              f"{mv['considered']} seat(s) moved — {movement_detail_line(mv)}{crit_note}")
        prev = rN
        if is_auto:
            if mv["considered"] < 2:
                stop_reason = "insufficient-voices"   # too few overlapping voices to judge
                break
            if mv["moved"] < DEFAULT_CONVERGE_THRESHOLD:
                stop_reason = "converged"             # the board went quiet
                break
        round_no += 1
    else:
        stop_reason = "max-rounds" if is_auto else "round-count"

    convergence = {
        "is_auto": is_auto,
        "requested": config.rounds,
        "max_rounds": max_rounds,
        "rounds_run": len(rounds_done),
        "stop_reason": stop_reason,
        "movements": movements,
    }

    # Independence / echo score (v1.14 #9): a pure metric over the FINAL round
    # transition's parsed signals (verdict flips, citation overlap, the self-reported
    # BASIS token). Only meaningful with ≥2 rounds; echo_score returns `not_computed`
    # for a single-round run, so we only attach it when there IS a final transition.
    # The same-provider discount is derived INSIDE echo_score from the scored (overlap)
    # seats' own `.provider`, so a seat dropping before the final round can never make
    # the discount read a population the metric did not score.
    if len(rounds_done) >= 2:
        from _conductor.echo_score import echo_score
        echo = echo_score(rounds_done[-2], rounds_done[-1])
        convergence["echo"] = echo
        # A machine-readable sidecar for the full-handoff HTML pill (read best-effort
        # by render_verdict.build_handoff_data). A single-round run never reaches here,
        # so the file is absent there and the pill drops → byte-identical (D5).
        _write(os.path.join(config.out_dir, "echo-score.json"),
               json.dumps(echo, indent=2, ensure_ascii=False) + "\n")

    # Provenance after the last fan-out (carries every round's outcome + the M1
    # convergence trace: per-transition movement and why the loop stopped).
    _write(os.path.join(config.out_dir, "run-metadata.md"),
           render_run_metadata(config, preflight, approval, rounds=rounds_done,
                               convergence=convergence))
    _write(os.path.join(config.out_dir, "run-metadata.tsv"),
           render_run_metadata_tsv(rounds_done))
    print(f"\nwrote run dir: {config.out_dir}")
    print(f"rounds run: {len(rounds_done)}  ·  stop reason: {stop_reason}"
          + (f"  ·  ceiling (--max-rounds): {max_rounds}" if is_auto else ""))

    last = rounds_done[-1]
    usable_last = [r for r in last if r.usable]
    # "One voice is not a board" — the same invariant preflight and round 1 enforce
    # (§13). A board can also COLLAPSE mid-debate (seats drop in round 2+), so re-check
    # the last round here: fewer than two usable reviews must NOT be handed off as a
    # synthesizable board. Exit NO-GO with a loud warning instead of inviting a verdict
    # over one (or zero) voices. (stop_reason is already 'insufficient-voices' for the
    # auto path; an explicit --rounds N collapse is caught here too.)
    if len(usable_last) < 2:
        tracker.finish("no-board", f"board collapsed to {len(usable_last)} usable voice(s)")
        print(f"\nWARNING: the board collapsed to {len(usable_last)} usable voice(s) by round "
              f"{last[0].round_no} — that is not a board. Inspect round-{last[0].round_no}/*.raw and "
              "logs/, fix the failed seats, and re-run. Synthesis is intentionally NOT attempted on "
              "fewer than two voices.")
        return EXIT_PREFLIGHT_NOGO

    # Rounds are captured. Synthesis stays a REASONING task (§11): the conductor
    # produces clean packets and either hands them to the orchestrating agent (the
    # default — verdict.json is hand-authored) or — under `--synthesize` (M2) —
    # spawns a single no-lens "synthesizer" seat that DRAFTS verdict.json from the
    # final-round reviews. The conductor does NOT generate the verdict in code in
    # either path; the synthesizer is a model call whose output is schema-validated
    # against verdict@2 before acceptance (the human still gates ship/abstain).
    last_dir = f"{config.out_dir}/round-{last[0].round_no}"
    print(f"\nRounds complete ({len(rounds_done)} round(s)): {len(usable_last)} usable reviews in "
          f"{last_dir}/.")

    if config.synthesize:
        return _run_synthesis_step(config, rounds_done, args, last_dir,
                                   preflight=preflight, approval=approval,
                                   convergence=convergence, tracker=tracker)

    # No --synthesize: the rounds are the conductor's product; the verdict is the
    # agent's hand-authored step. The run (as the conductor drives it) ends here.
    tracker.finish("rounds-complete", f"{len(rounds_done)} round(s) captured — verdict is yours")
    print("\nNext — synthesize, then run the deterministic M5 chain:")
    print(f"  1. Read {last_dir}/*.md and write {config.out_dir}/verdict.json "
          "(advisory-board/verdict@2; cite typed evidence on each blocker).")
    if config.revision is not None:
        print("     Include the lineage object this revise run pins:\n"
              f"     \"previous_run\": {json.dumps(config.revision.previous_run)}")
    print(f"     (or re-run with --synthesize to spawn the neutral synthesizer seat)")
    print(f"  2. run_board.py verify {config.out_dir}/verdict.json --source <src> --run {config.out_dir}")
    print(f"  3. run_board.py consensus {config.out_dir}/verdict.json --run {config.out_dir} "
          f"-o {config.out_dir}/final-consensus.md")
    print(f"  4. run_board.py validate {config.out_dir}/verdict.json --gate")
    return EXIT_OK


def _run_rubric_step(config, blobs, approval, *, tracker=None, _write=None,
                     rubric_blobs=None):
    """The v1.15 rubric-first pass (D15/D16/D18/D20). Runs BEFORE round 1 (from
    _run_after_activate, gated on config.rubric). Two spawns:

      1. PROPOSAL fan-out: every board seat proposes 3–7 weighted criteria in
         parallel (the same ThreadPoolExecutor shape as a round). The conductor mints
         the proposal ids (§11). Floor: ≥2 usable proposals or REFUSE.
      2. CHAIR merge: one board seat (chosen on the unique-id axis, D16) merges the
         proposals into rubric.json; the conductor reconciles the partition + the
         weight-sum-to-100 invariant mechanically. Chair final failure REFUSES.

    Returns the MERGED RUBRIC dict on success (rubric.json written; the caller rebuilds
    the round prompts with its criteria — v1.15 #P3) or the refusal exit code
    (RUBRIC_REFUSAL_EXIT, an int) on a refusal. A refusal writes
    rubric-rejected.json + the raw records for the post-mortem, stamps the tracker,
    and prints a loud message. This is D20's one place the never-fail-the-run posture
    does NOT apply — the refusal lands before any opinion round has produced value."""
    import shutil
    import tempfile
    tk = tracker if tracker is not None else NullTracker()
    write = _write if _write is not None else globals()["_write"]
    tk.stage("rubric", "started")

    # B1: the rubric PROPOSAL prompts are prebuilt into the approved consent hash (in
    # _execute_run). Recover the exact approved proposal blobs (passed down, or rebuilt
    # deterministically as a fallback) and re-assert the FULL approved packet hash —
    # round-1 ∪ rubric-proposal — before anything egresses. This is a DIRECT binding:
    # the exact outbound proposal bytes are in approval.content_hash, not a source
    # proxy. A per-seat re-assertion also runs inside run_rubric_proposal.
    if rubric_blobs is None:
        rubric_blobs = build_rubric_proposal_blobs(config)
    egress_blobs = list(blobs) + list(rubric_blobs)

    # Re-assert the egress hash one last time before the rubric pass egresses the
    # source (defense-in-depth, mirroring run_round's pre-spawn hard stop). The
    # approved packet (round-1 prompts AND the prebuilt proposal prompts) MUST still
    # hash to exactly what consent was bound to, or nothing leaves the machine. The
    # repo-scope re-hash applies whenever the run is grounded (the frozen tree the
    # seats read is bound to the approved scope). A drift is the same labeled NO-GO
    # (EXIT_EGRESS_BLOCKED), never an uncaught traceback.
    if packet_hash(egress_blobs) != approval.content_hash:
        die("egress hash drift: the packet no longer matches the approved content "
            "hash — refusing to spawn the rubric pass", EXIT_EGRESS_BLOCKED)
    if config.grounding is not None and config.grounding.snapshot_dir:
        from _conductor.grounding import rehash_snapshot
        try:
            current_scope_hash = rehash_snapshot(config.grounding.snapshot_dir)
        except (ValueError, OSError):
            die("repo scope snapshot is missing or unreadable — refusing to spawn the "
                "rubric pass", EXIT_EGRESS_BLOCKED)
        if current_scope_hash != approval.scope_hash:
            die("repo scope hash drift: the snapshot no longer matches the approved scope "
                "hash — refusing to spawn the rubric pass", EXIT_EGRESS_BLOCKED)

    # -- 1. Proposal fan-out ------------------------------------------------- #
    print(f"\n=== rubric proposals ({rubric_proposal_template_version(config)}; "
          f"sha256:{rubric_proposal_template_sha(config)[:12]}…) ===")
    print(f"  {len(config.board)} seat(s) each propose 3–7 weighted criteria (parallel "
          "fan-out; each is sent the full source under the run's existing disclosure — "
          "the same source round 1 sends, no new consent category).")

    # Workdir parity with run_round (v1.15 P3): under --repo every proposal seat is
    # pointed at the FROZEN snapshot cwd (config.grounding.snapshot_dir) — the exact
    # read-only tree consent bound to and round 1 reads — so a rubric seat grounds
    # its criteria in the same bytes; otherwise a scoped ephemeral tempdir (gate) or
    # None (advisory). We do NOT own the snapshot (cmd_run made + cleans it), so the
    # finally below only rmtree's an ephemeral tempdir WE created here.
    # C1: the effective grounded flag MUST follow the SAME predicate that selects the
    # snapshot workdir — a grounded claim to the adapter (build_argv grounded=…) is only
    # honest when the seat is actually pointed at the snapshot cwd. Keying both off one
    # predicate means config.grounded=True with no snapshot_dir (a snapshot that never
    # materialized) does NOT spawn a rubric seat claiming grounding without the tree.
    grounded_snapshot = (
        config.grounded and config.grounding is not None and config.grounding.snapshot_dir)
    own_workdir = None
    if grounded_snapshot:
        workdir = config.grounding.snapshot_dir
    elif config.fs_scoped:
        own_workdir = tempfile.mkdtemp(prefix="advisory-board-rubric-")
        workdir = own_workdir
    else:
        workdir = None
    try:
        # B1: spawn from the exact prebuilt proposal blobs bound into the approved
        # consent hash (re-asserted per seat), not a fresh rebuild at spawn time.
        # grounded=bool(grounded_snapshot): same predicate as the workdir (C1).
        prop_results = run_rubric_proposals(config, config.board, workdir=workdir,
                                            grounded=bool(grounded_snapshot),
                                            blobs=rubric_blobs,
                                            approved_hash=approval.content_hash)
    finally:
        if own_workdir:
            shutil.rmtree(own_workdir, ignore_errors=True)

    # Persist each proposal's black-box + prompt + human record (mirrors revision/).
    rub_dir = os.path.join(config.out_dir, "rubric")
    os.makedirs(rub_dir, exist_ok=True)
    for rr in prop_results:
        write(os.path.join(config.out_dir, "prompts", f"rubric-{rr.seat}.prompt"),
              rr.prompt_text)
        write(os.path.join(rub_dir, f"{rr.seat}.md"), render_rubric_proposal_md(rr))
        write(os.path.join(rub_dir, f"{rr.seat}.raw"), render_rubric_proposal_raw(rr, config))
        write(os.path.join(config.out_dir, "logs", f"rubric-{rr.seat}.stderr"), rr.stderr or "")

    usable = [rr for rr in prop_results if rr.usable]
    summary = ", ".join(f"{rr.seat}={'usable' if rr.usable else 'dropped'}"
                        for rr in prop_results)
    print(f"  proposals: {summary}  ·  {len(usable)} of {len(prop_results)} usable")

    # Floor (D15/D20): fewer than two usable proposals REFUSES the run before any
    # opinion round spends a token.
    if len(usable) < MIN_USABLE_PROPOSALS:
        return _refuse_rubric(
            config, tk, write,
            reason=(f"only {len(usable)} usable rubric proposal(s) — a rubric needs at "
                    f"least {MIN_USABLE_PROPOSALS} to merge (inspect rubric/*.raw and "
                    "logs/, fix the failed seats, and re-run, or run without --rubric)"),
            chair_result=None)

    # -- 2. Mint proposal ids + chair merge --------------------------------- #
    # The conductor mints the ids — a model never mints identity (§11). In BOARD
    # order, keeping only the seats that produced a usable proposal.
    usable_ids = [rr.seat for rr in usable]
    per_seat = [(rr.seat, rr.criteria) for rr in usable]
    proposals = mint_proposals(per_seat)

    chair_seat = choose_chair_seat(config, usable_seats=usable_ids,
                                   preferred=config.chair_seat)
    print(f"\n=== rubric chair ({chair_seat.id}; {RUBRIC_CHAIR_TEMPLATE_VERSION}; "
          f"sha256:{rubric_chair_template_sha()[:12]}…) ===")
    print(f"  chair merges {len(proposals)} proposal(s) into one weighted rubric; the "
          "conductor reconciles the partition (every proposal subsumed or dropped) and "
          "the weight-sum-to-100 invariant mechanically (§11).")

    workdir = tempfile.mkdtemp(prefix="advisory-board-chair-") if config.fs_scoped else None
    try:
        cr = run_rubric_chair(config, proposals, seat=chair_seat,
                              timeout=chair_seat.timeout_s, workdir=workdir)
    finally:
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)

    # Always persist the chair's black-box + prompt + human record.
    if cr.prompt_text:
        write(os.path.join(config.out_dir, "prompts", "rubric-chair.prompt"), cr.prompt_text)
    write(os.path.join(rub_dir, "chair.md"), render_chair_md(cr))
    write(os.path.join(rub_dir, "chair.raw"), render_chair_raw(cr))
    write(os.path.join(config.out_dir, "logs", f"rubric-chair-{cr.seat}.stderr"), cr.stderr or "")

    print(f"  chair: {cr.status}"
          + (f" ({cr.failure_class})" if cr.failure_class else "")
          + f"  ·  elapsed {cr.elapsed_s:.1f}s  ·  packet sha256:{cr.packet_hash[:12]}…")

    if cr.rubric is None:
        reason = (cr.reject_error or cr.parse_error or cr.failure_class
                  or "chair merge dropped")
        return _refuse_rubric(config, tk, write,
                              reason=f"the chair could not merge the proposals ({reason})",
                              chair_result=cr)

    # -- 3. Success: write rubric.json (the pre-round artifact of record) ---- #
    rubric_path = os.path.join(config.out_dir, "rubric.json")
    rejected_path = os.path.join(config.out_dir, "rubric-rejected.json")
    if os.path.exists(rejected_path):
        os.unlink(rejected_path)   # a prior refusal peer; this run produced a rubric
    with open(rubric_path, "w", encoding="utf-8", newline="") as handle:
        json.dump(cr.rubric, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    n_criteria = len(cr.rubric["criteria"])
    n_dropped = len(cr.rubric.get("dropped") or [])
    tk.stage("rubric", "done", f"{n_criteria} criteria merged")
    print(f"\nwrote {rubric_path} (advisory-board/rubric@1 — validated; "
          f"{n_criteria} criteria from {len(proposals)} proposal(s), {n_dropped} dropped; "
          "weights sum to 100)")
    print("  (the rubric is the pre-round artifact of record; it is now injected into "
          "every opinion round's prompt and each seat scores every criterion 1–5 — "
          "SCORE lines coexist with the VERDICT token and never gate, D17.)")
    # v1.15 #P3: hand the merged rubric back so the caller rebuilds the round prompts
    # with the scoring block. Success is the rubric dict (truthy); a refusal is the
    # int exit code (see _refuse_rubric) — the caller branches on isinstance(_, int).
    return cr.rubric


def _refuse_rubric(config, tk, write, *, reason: str, chair_result) -> int:
    """The rubric refusal path (D20): write rubric-rejected.json + (when the chair
    ran) its raw record for the post-mortem, stamp the tracker, print a loud message,
    and return the non-zero refusal exit code. This is the ONE place the
    never-fail-the-run posture does not apply — nothing valuable exists yet."""
    rejected_path = os.path.join(config.out_dir, "rubric-rejected.json")
    rubric_path = os.path.join(config.out_dir, "rubric.json")
    # Never ship a stale accepted rubric alongside a refusal.
    if os.path.exists(rubric_path):
        os.unlink(rubric_path)
    record = {
        "schema": "advisory-board/rubric@1",
        "rejected": True,
        "reason": reason,
        "chair_seat": (chair_result.seat if chair_result is not None
                       else (config.chair_seat or "(not selected)")),
    }
    with open(rejected_path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tk.finish("no-rubric", f"rubric refused ({reason})")
    print(f"\n⚠ RUBRIC REFUSED — {reason}")
    print(f"  the refusal was recorded to {rejected_path}")
    print("  No opinion round ran — nothing valuable was discarded (D20). The rubric "
          "pass runs before round 1 precisely so a failure lands before any tokens are "
          "spent on the board.")
    return RUBRIC_REFUSAL_EXIT


def _run_synthesis_step(config, rounds_done: list, args, last_dir: str, *,
                        preflight, approval, convergence, tracker=None) -> int:
    """The M2 synthesizer step. Spawns one no-lens seat to draft verdict.json from
    the final-round reviews; merges into the conductor's authoritative skeleton;
    rejects on schema-validation failure. The rounds already succeeded (the value
    the board produced), so a synth failure prints a loud warning + falls back to
    the manual hand-off message, exit 0 — never silently 0 with no verdict.json
    nor a hard error that swallows the successful rounds. The user explicitly
    asked for synthesis with --synthesize; the loud-warning + verdict.json absence
    is how they detect that synthesis didn't deliver."""
    import shutil
    import tempfile
    tk = tracker if tracker is not None else NullTracker()
    tk.stage("synthesis", "started")
    last = rounds_done[-1]
    seat = choose_synthesizer_seat(config, last, preferred=config.synthesizer_seat)
    # The synthesizer spawns on a board seat, so it honors that seat's resolved
    # --timeout (per-seat or bare default); None falls back to the adapter cap.
    timeout = seat.timeout_s
    print(f"\n=== synthesizer ({seat.name}, no-lens; --synthesize) ===")
    print(f"prompt template: {SYNTHESIZER_TEMPLATE_VERSION} "
          f"(sha256:{synthesizer_template_sha()[:12]}…)")
    print("(the synthesizer is briefed only on the final-round reviews + the conductor-extracted "
          "VERDICT tokens — it has no lens and never sees the source directly. §11: synthesis "
          "stays reasoning; the conductor only plumbs the structural fields.)")

    # Gate-mode workdir: scoped, ephemeral, cleaned up after the spawn (mirrors
    # rounds.run_round's try/finally — without cleanup, every gate-mode synth run
    # would leak a tmpdir).
    workdir = tempfile.mkdtemp(prefix="advisory-board-synth-") if config.fs_scoped else None
    try:
        sr = run_synthesizer(config, rounds_done, seat=seat, timeout=timeout,
                             workdir_factory=(lambda: workdir) if workdir else None)
    finally:
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)

    # Re-write run-metadata.md with the synthesizer section appended (the earlier
    # write right after the round loop didn't have this — synthesis happens after).
    _write(os.path.join(config.out_dir, "run-metadata.md"),
           render_run_metadata(config, preflight, approval, rounds=rounds_done,
                               convergence=convergence, synthesizer=sr))

    synth_dir = os.path.join(config.out_dir, "synthesizer")
    os.makedirs(synth_dir, exist_ok=True)
    # Always persist what the synthesizer produced (or what it failed to produce),
    # mirroring the round-artifact Black-Box Recorder pattern — a failed call is
    # forensically inspectable, not lost.
    if sr.prompt_text:
        _write(os.path.join(config.out_dir, "prompts", "synthesizer.prompt"), sr.prompt_text)
    _write(os.path.join(synth_dir, f"{seat.name}.md"), sr.stdout or "(synthesizer produced no stdout)\n")
    _write(os.path.join(synth_dir, f"{seat.name}.raw"), render_synthesizer_raw(config, sr))
    _write(os.path.join(config.out_dir, "logs", f"synthesizer-{seat.name}.stderr"),
           sr.stderr or "")

    print(f"synthesizer: {sr.status}"
          + (f" ({sr.failure_class})" if sr.failure_class else "")
          + f"  ·  elapsed {sr.elapsed_s:.1f}s  ·  packet sha256:{sr.packet_hash[:12]}…")

    verdict_path = os.path.join(config.out_dir, "verdict.json")
    rejected_path = os.path.join(config.out_dir, "verdict-rejected.json")

    if sr.verdict_data is not None:
        import json
        # Drop a stale peer artifact from a prior run — only NOW, after this run
        # has produced a successor. Doing it at the top would have destroyed the
        # prior good state on any exception path.
        if os.path.exists(rejected_path):
            os.unlink(rejected_path)
            print(f"  (removed stale verdict-rejected.json from a prior run)")
        # The exact bytes written to verdict.json — captured so the revision step's
        # pointer write (D10) can sha-guard against them (optimistic concurrency).
        # newline="" disables platform newline translation so the ON-DISK bytes equal
        # verdict_bytes exactly: the pointer guard reads verdict.json in BINARY
        # (_file_sha256), so a text-mode \n → \r\n rewrite on Windows would diverge
        # the file from the sha baseline below and FALSE-TRIP the guard on the very
        # first pointer write. The JSON content is already \n-only, so this is a
        # no-op on POSIX and a correctness fix on Windows.
        verdict_bytes = (json.dumps(sr.verdict_data, indent=2, ensure_ascii=False) + "\n")
        with open(verdict_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(verdict_bytes)
        print(f"\nwrote {verdict_path} (synthesized; advisory-board/verdict@2 — validated)")
        # --output revised-draft (v1.13 #2): a validated verdict.json now exists, so
        # the revision step runs — analogous placement/shape to the synthesis step,
        # gated on config.output. A revision failure never discards the verdict/rounds
        # (rejected artifacts + exit 0; --strict-exit → 4, same as the synthesizer).
        tk.stage("synthesis", "done", "verdict.json validated")
        if config.output == "revised-draft":
            return _run_revision_step(config, sr.verdict_data, rounds_done, args,
                                      verdict_path=verdict_path,
                                      verdict_sha256=hashlib.sha256(
                                          verdict_bytes.encode("utf-8")).hexdigest(),
                                      tracker=tk)
        tk.finish("ok", "verdict synthesized")
        print("\nNext — the deterministic M5 chain (human still gates ship/abstain):")
        print(f"  1. run_board.py verify {verdict_path} --source <src> --run {config.out_dir}")
        print(f"  2. run_board.py consensus {verdict_path} --run {config.out_dir} "
              f"-o {config.out_dir}/final-consensus.md")
        print(f"  3. run_board.py validate {verdict_path} --gate")
        return EXIT_OK

    # Failure path: keep the rounds' value, but be loud that synthesis did NOT
    # deliver verdict.json. Persist the rejected merged JSON when we got that far,
    # so the user can hand-fix from there instead of starting from scratch.
    # The stale verdict.json from a PRIOR run is unlinked HERE — never higher up —
    # so an unexpected exception above doesn't destroy a prior good state.
    if sr.raw_content is not None and sr.schema_error:
        from _conductor.synthesizer import build_skeleton, merge_synthesizer_content
        try:
            merged = merge_synthesizer_content(build_skeleton(config, rounds_done), sr.raw_content)
            import json
            if os.path.exists(verdict_path):
                os.unlink(verdict_path)
                print(f"  (removed stale verdict.json from a prior run)")
            with open(rejected_path, "w", encoding="utf-8") as handle:
                json.dump(merged, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
        except ValueError:
            pass

    reason = sr.parse_error or sr.schema_error or sr.failure_class or "synthesizer dropped"
    tk.finish("no-verdict", f"synthesizer did not deliver ({reason})")
    print(f"\n⚠ synthesizer did NOT produce a usable verdict.json — reason: {reason}")
    print(f"  see {synth_dir}/{seat.name}.md and {synth_dir}/{seat.name}.raw "
          "for the full record")
    if sr.schema_error and sr.raw_content is not None:
        print(f"  the merged-but-rejected JSON was written to {rejected_path}")
    print(f"\nFall back to the manual hand-off — read {last_dir}/*.md and write "
          f"{verdict_path} (advisory-board/verdict@2; cite typed evidence on each "
          "blocker). Then run the deterministic M5 chain "
          f"(verify → consensus → validate --gate).")
    # Default: exit 0 so a synth hiccup never discards the successful rounds (the
    # warning + absent verdict.json is the signal). --strict-exit flips ONLY the
    # return code to EXIT_NO_VERDICT so a CI gate can't misread synth failure as
    # success — every print, the verdict-rejected.json write, and the fallback
    # message above are byte-identical in both modes. Both synth-failure modes
    # (parse error and schema-rejected) flow through here, so both honor the flag.
    if getattr(args, "strict_exit", False):
        return EXIT_NO_VERDICT
    return EXIT_OK


def _revised_draft_name(config, *, rejected: bool) -> str:
    """The on-disk filename for the revised draft. Prose → `revised-draft.md`;
    code → `revised-draft.<orig-ext>` (so a saved code file keeps its extension
    and stays syntactically valid), falling back to `.txt` for an extensionless
    code source (e.g. a `Makefile` reached via an explicit `--source-type code`).
    The rejected variant carries the same suffix with `-rejected` before it.
    Byte-clean: this file holds the revised source bytes and nothing else (D12 —
    no metadata header of any kind)."""
    if config.source_type == "code" and config.source.kind == "path":
        ext = os.path.splitext(config.source.ref)[1] or ".txt"
    else:
        ext = ".md"
    stem = "revised-draft-rejected" if rejected else "revised-draft"
    return stem + ext


def _write_verdict_changes_pointer(verdict_path: str, changes_sha256: str, *,
                                   baseline_sha256: str) -> "tuple":
    """Write `verdict.json.changes = {artifact, sha256}` (D10) with amend's full
    write discipline: re-read + re-validate, an optimistic sha guard against the
    bytes synthesis wrote (a race/outside edit refuses), symlink-preserving
    realpath, mkstemp + rename, mode preservation. The pointer is acyclic
    (verdict → changes → {source, revised}); changes.json never references the
    verdict by hash. Returns (ok, detail)."""
    import tempfile
    import board_verdict
    # Resolve through any symlink so we read AND write the real target (amend's rule).
    path = os.path.realpath(verdict_path)
    current_sha = board_verdict._file_sha256(path)
    if current_sha != baseline_sha256:
        return (False, "verdict.json changed since synthesis wrote it — the changes "
                "pointer was NOT written (optimistic-concurrency guard); changes.json "
                "still stands on its own")
    try:
        data = board_verdict.load(path)   # re-read + re-validate before touching
    except SystemExit:
        return (False, "verdict.json failed re-validation before the pointer write — "
                "pointer NOT written")
    data["changes"] = {"artifact": "changes.json", "sha256": changes_sha256}
    try:
        board_verdict.validate(data)      # the pointer must itself validate (strict-when-present)
    except SystemExit:
        return (False, "the changes pointer failed verdict schema validation — NOT written")

    dest_dir = os.path.dirname(path) or "."
    try:
        orig_mode = os.stat(path).st_mode & 0o777
    except OSError:
        orig_mode = 0o644
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=dest_dir, prefix=".verdict.json.changes.", suffix=".tmp")
        # newline="" writes byte-exact (no platform \n → \r\n translation) so the
        # bytes on disk are the bytes the guard hashes in binary — a later re-read /
        # re-guard of this same file must not diverge from what we wrote.
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.chmod(tmp, orig_mode)
        # Re-check the race guard just before the swap (a narrowing, not a lock).
        if board_verdict._file_sha256(path) != baseline_sha256:
            board_verdict._cleanup(tmp)
            return (False, "verdict.json changed while writing the changes pointer — NOT written")
        os.replace(tmp, path)
    except OSError as exc:
        if tmp is not None:
            board_verdict._cleanup(tmp)
        return (False, f"cannot write the changes pointer to verdict.json: {exc}")
    except BaseException:
        # A non-OSError (e.g. KeyboardInterrupt) between mkstemp and replace must
        # not leave a scratch tmp behind (parity with amend's write path).
        if tmp is not None:
            board_verdict._cleanup(tmp)
        raise
    return (True, "wrote verdict.json.changes pointer (sha-bound to changes.json)")


def _run_endorsement_pass(config, rr, revision_seat, args) -> list:
    """The endorsement pass (D13). Called ONLY after the revision succeeded and only
    when config.endorse. Fans the non-revision seats out concurrently, writes each
    seat's black-box + human record under endorsement/, and merges the conductor-
    built rows into rr.changes["endorsements"] IN PLACE (before changes.json is
    written, so the pinned bytes carry them). Returns the per-seat results (for the
    caller's summary print), or [] when the pass didn't run / had no seats.

    Never fails the run: a --no-endorse run does nothing (byte-identical changes.json
    to the P2 shape); a single-seat board endorses nothing (a note, not a crash); a
    dropped seat records ABSTAIN/dropped rows; all-dropped warns loudly but still
    writes rows. After merging, the changes doc is RE-VALIDATED — a validation
    failure (which the conductor-built rows should never trigger) leaves endorsements
    empty and warns, rather than shipping an invalid changes.json."""
    import shutil
    import tempfile
    if not config.endorse:
        # --no-endorse: no pass, endorsements stays [] exactly as build_changes wrote
        # it. The run card already disclosed the opt-out; nothing more to print.
        return []

    seats = endorsement_seats(config, revision_seat.id)
    print(f"\n=== endorsement ({ENDORSEMENT_TEMPLATE_VERSION}; "
          f"sha256:{endorsement_template_sha()[:12]}…) ===")
    if not seats:
        # Single-seat board: the revision seat is the only seat, so there is no
        # non-revision seat to endorse. Not a failure — a note, and endorsements
        # stays [].
        print("  (no non-revision seats to endorse — the revision seat is the only "
              "board seat; endorsements left empty)")
        return []
    print(f"  {len(seats)} seat(s) vote on {len(rr.changes.get('edits') or [])} edit(s) + "
          f"{len(rr.changes.get('unresolved') or [])} unresolved conflict(s); each is sent the "
          "source + the board-generated revised draft/changes under the run's existing "
          "disclosure (same category as round-2 review sharing; no new exposure class).")

    workdir = tempfile.mkdtemp(prefix="advisory-board-endorsement-") if config.fs_scoped else None
    try:
        # No call-level timeout: each endorsement seat honors its OWN resolved
        # --timeout (per-seat id=SECONDS → seat.timeout_s → adapter cap), exactly like
        # the round fan-out. The revision seat's timeout is not imposed on the voters.
        results = run_endorsement_pass(config, rr.changes, rr.revised_text or "", seats,
                                       workdir=workdir)
    finally:
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)

    # Persist the per-seat black-box + prompt + human records (mirrors revision/).
    edir = os.path.join(config.out_dir, "endorsement")
    os.makedirs(edir, exist_ok=True)
    rows: list = []
    for er in results:
        _write(os.path.join(config.out_dir, "prompts", f"endorsement-{er.seat}.prompt"),
               er.prompt_text)
        _write(os.path.join(edir, f"{er.seat}.md"), render_endorsement_md(er))
        _write(os.path.join(edir, f"{er.seat}.raw"), render_endorsement_raw(er))
        _write(os.path.join(config.out_dir, "logs", f"endorsement-{er.seat}.stderr"),
               er.stderr or "")
        rows.extend(er.rows)

    # Merge the conductor-built rows into the changes dict, then re-validate. The
    # rows are conductor-authored (never model-authored), so validation should pass;
    # if it somehow doesn't, drop the rows rather than ship an invalid artifact.
    candidate = dict(rr.changes)
    candidate["endorsements"] = rows
    schema_err = _validate_changes_doc(candidate)
    if schema_err is not None:
        print(f"  ⚠ endorsement rows failed changes@1 re-validation ({schema_err}) — "
              "endorsements left empty; the revision itself is unaffected.")
        return results
    rr.changes["endorsements"] = rows

    dropped = [er for er in results if er.dropped]
    n_object = sum(1 for r in rows if r.get("position") == "OBJECT")
    if dropped and len(dropped) == len(results):
        print(f"  ⚠ ALL {len(results)} endorsement seat(s) dropped — every row recorded "
              "as ABSTAIN (dropped). The revision stands; the endorsement is empty of "
              "signal (D13: the pass never fails the run).")
    else:
        summary = ", ".join(f"{er.seat}={'dropped' if er.dropped else er.status}"
                            for er in results)
        print(f"  endorsement: {summary}"
              + (f"  ·  {len(dropped)} dropped" if dropped else "")
              + (f"  ·  {n_object} objection(s) recorded" if n_object else ""))
    return results


def _validate_changes_doc(data: dict):
    """Run board_changes.validate against an assembled changes doc; return an error
    string if invalid, else None (mirrors revision.validate_changes' capture)."""
    import contextlib
    import io as _io
    try:
        import board_changes
    except ImportError as exc:
        return f"could not import board_changes ({exc})"
    buf = _io.StringIO()
    try:
        with contextlib.redirect_stderr(buf):
            board_changes.validate(data)
    except SystemExit:
        captured = buf.getvalue().strip()
        if captured.startswith("error:"):
            captured = captured[len("error:"):].strip()
        return captured or "schema validation failed"
    return None


def _run_revision_step(config, verdict_data: dict, rounds_done: list, args, *,
                       verdict_path: str, verdict_sha256: str, tracker=None) -> int:
    """The v1.13 revision step. Runs ONLY after synthesis produced a validated
    verdict.json (this function is reached from _run_synthesis_step's success
    branch, gated on config.output == "revised-draft"). Spawns one board seat to
    produce a revised copy of the source + the changes mapping; the conductor
    mechanically validates every claim, builds changes.json, writes the byte-clean
    revised draft, and pins the verdict → changes pointer. A revision failure never
    discards the completed rounds/verdict: rejected artifacts + a loud warning +
    exit 0 (--strict-exit → 4, the same code the synthesizer uses)."""
    import shutil
    import tempfile
    tk = tracker if tracker is not None else NullTracker()
    tk.stage("revision", "started")
    last = rounds_done[-1]
    seat = choose_revision_seat(config, last, preferred=config.revision_seat)
    timeout = seat.timeout_s
    revised_artifact = _revised_draft_name(config, rejected=False)

    print(f"\n=== revision ({seat.name}; --output revised-draft) ===")
    print(f"prompt template: {REVISION_TEMPLATE_VERSION} "
          f"(sha256:{revision_template_sha()[:12]}…)")
    print("(the revision seat is handed the full source + the verdict's resolvable findings "
          "enumerated BY THE CONDUCTOR; it returns the edit->finding mapping first and the "
          "revised source second. Every edit is mechanically reconciled against the diff — "
          "§11: the model reasons the edits, the conductor owns the finding skeleton.)")

    workdir = tempfile.mkdtemp(prefix="advisory-board-revision-") if config.fs_scoped else None
    try:
        rr = run_revision(config, verdict_data, rounds_done, seat=seat,
                          revised_artifact=revised_artifact, timeout=timeout,
                          workdir_factory=(lambda: workdir) if workdir else None)
    finally:
        if workdir:
            shutil.rmtree(workdir, ignore_errors=True)

    # Persist the black-box record (mirrors synthesizer/), always — a failed
    # revision is forensically inspectable, not lost.
    rev_dir = os.path.join(config.out_dir, "revision")
    os.makedirs(rev_dir, exist_ok=True)
    if rr.prompt_text:
        _write(os.path.join(config.out_dir, "prompts", "revision.prompt"), rr.prompt_text)
    # Per-seat revision artifacts are keyed on the reviser's UNIQUE id (== name on a
    # non-duplicate board, so single-provider paths are byte-identical; on a duplicate
    # board it names the exact claude that revised, matching changes.revision_seat).
    _write(os.path.join(rev_dir, f"{seat.id}.md"),
           rr.stdout or "(revision seat produced no stdout)\n")
    _write(os.path.join(rev_dir, f"{seat.id}.raw"), render_revision_raw(config, rr))
    _write(os.path.join(config.out_dir, "logs", f"revision-{seat.id}.stderr"), rr.stderr or "")

    print(f"revision: {rr.status}"
          + (f" ({rr.failure_class})" if rr.failure_class else "")
          + f"  ·  elapsed {rr.elapsed_s:.1f}s  ·  packet sha256:{rr.packet_hash[:12]}…")

    draft_path = os.path.join(config.out_dir, revised_artifact)
    rejected_artifact = _revised_draft_name(config, rejected=True)
    rejected_draft_path = os.path.join(config.out_dir, rejected_artifact)
    changes_path = os.path.join(config.out_dir, "changes.json")
    changes_rejected_path = os.path.join(config.out_dir, "changes-rejected.json")
    # The apply-able unified patch (v1.13 P3, D12) — code sources only. It is a
    # redundant, git-apply-able RENDERING of the same change changes.json already
    # certifies (no new trust surface; both derive from the same pinned strings).
    patch_path = os.path.join(config.out_dir, "revised-draft.patch")

    # Endorsement write-path guard (D13): the model NEVER authors endorsement rows
    # (the seats produce TOKENS; the conductor builds the rows). build_changes stamps
    # `endorsements: []`, so anything non-empty at THIS point — before the conductor's
    # own merge below — could only be smuggled. Divert to the reject path (internal
    # error, not model-blamed). The conductor-built rows enter AFTER this guard.
    if rr.changes is not None and (rr.changes.get("endorsements") or []) != []:
        rr.changes = None
        rr.reject_error = ("internal error: a non-empty 'endorsements' reached the "
                           "changes.json write path before the endorsement pass ran — "
                           "the model cannot author endorsement rows (the conductor "
                           "builds them from the seats' tokens); refusing to write")

    if rr.changes is not None:
        # Drop stale rejected peers from a prior run only AFTER this run produced
        # a successor (never destroy prior good state on an exception path). A
        # stale .patch from a prior CODE run is dropped too when this run is prose
        # (it writes no patch, so a leftover would misrepresent the current run).
        for stale in (changes_rejected_path, rejected_draft_path,
                      *(() if config.source_type == "code" else (patch_path,))):
            if os.path.exists(stale):
                os.unlink(stale)
        # ENDORSEMENT PASS (D13) — the revision SUCCEEDED (all mechanical checks
        # passed), so unless --no-endorse each NON-revision seat votes on every edit
        # + unresolved entry, fanned out concurrently. The rows are merged into the
        # changes dict HERE — BEFORE changes.json is written and BEFORE the pointer
        # write — because verdict.json.changes sha-pins the changes.json BYTES, so
        # the endorsement rows must be inside those bytes. A --no-endorse run keeps
        # `endorsements: []` exactly as build_changes wrote it (byte-identical to a
        # P2-shape changes.json). The pass never fails the run: a dropped seat
        # becomes ABSTAIN/dropped rows, all-dropped is a loud warning + rows. It
        # writes its own artifacts + summary and merges rows into rr.changes IN PLACE.
        tk.stage("revision", "done", "revised draft accepted")
        if config.endorse:
            tk.stage("endorsement", "started")
        _run_endorsement_pass(config, rr, seat, args)
        if config.endorse:
            tk.stage("endorsement", "done",
                     f"{len(rr.changes.get('endorsements') or [])} endorsement row(s)")
        # 1. The byte-clean revised draft — the revised source bytes and NOTHING
        #    else (no header). Its sha256 MUST equal changes.json.revised.sha256,
        #    so newline="" disables platform newline translation: the on-disk
        #    bytes are exactly the bytes the sha was pinned over (the integrity
        #    anchor). Without it, a \n → \r\n rewrite on Windows would diverge the
        #    file from its own recorded sha.
        with open(draft_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(rr.revised_text or "")
        # 2. changes.json — the artifact of record, now carrying the endorsement
        #    rows. Same newline="" discipline: the verdict→changes pointer below pins
        #    the sha of these exact bytes (json.dumps + "\n"), so the disk bytes must
        #    not be newline-translated.
        with open(changes_path, "w", encoding="utf-8", newline="") as handle:
            json.dump(rr.changes, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        changes_sha = hashlib.sha256(
            (json.dumps(rr.changes, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        ).hexdigest()
        # 2b. revised-draft.patch — code sources only (D12): a git-apply-able
        #     unified diff, a/<name> / b/<name>. It derives from the SAME strings
        #     whose shas are already pinned in changes.json (source over the
        #     original, revised over the byte-clean draft), so it adds no new
        #     trust surface — a redundant, human-apply-able rendering of the
        #     change. newline="" keeps the LF discipline byte-exact on disk.
        patch_written = False
        if config.source_type == "code":
            patch_text = build_unified_patch(
                config.source.text, rr.revised_text or "",
                rr.changes["source"]["name"])
            with open(patch_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(patch_text)
            patch_written = True
        elif os.path.exists(patch_path):
            os.unlink(patch_path)   # a prose run never carries a patch
        # 3. The verdict → changes pointer (D10), with amend's write discipline.
        ok, detail = _write_verdict_changes_pointer(
            verdict_path, changes_sha, baseline_sha256=verdict_sha256)
        n_unresolved = len(rr.changes.get("unresolved") or [])
        print(f"\nwrote {draft_path} (byte-clean revised {config.source_type} — no header)")
        if patch_written:
            print(f"wrote {patch_path} (unified diff, a/ b/ headers — apply with `git apply -p1`)")
        n_endorse = len(rr.changes.get("endorsements") or [])
        print(f"wrote {changes_path} (advisory-board/changes@1 — validated; "
              f"{len(rr.changes['edits'])} edit(s), {n_unresolved} unresolved, "
              f"{n_endorse} endorsement row(s))")
        if n_unresolved:
            print(f"⚠ {n_unresolved} finding-conflict(s) left UNRESOLVED — surfaced in "
                  "changes.json, decided by you (a conflict never fails the run; D14).")
        if ok:
            print(f"  {detail}")
        else:
            print(f"  ⚠ {detail}")
        print("\nThe revised draft is an ARTIFACT — applying it is your act (D6); the source "
              "was never written.")
        tk.finish("ok", "verdict + revised draft written")
        return EXIT_OK

    # Failure path: keep the verdict + rounds, be loud that the revision did NOT
    # deliver. Persist rejected artifacts so the human can inspect/hand-fix. A
    # stale accepted patch from a prior run is dropped alongside the draft/changes
    # so the reject state is not contradicted by a leftover apply-able patch.
    for stale in (changes_path, draft_path, patch_path):
        if os.path.exists(stale):
            os.unlink(stale)
    if rr.revised_text is not None:
        # We parsed a draft but a mechanical check rejected it — persist it so the
        # human can see what the seat produced (clearly marked rejected).
        # newline="" keeps the on-disk bytes faithful to what the seat emitted
        # (same byte-fidelity discipline as the accepted draft), so a human
        # inspecting the reject sees the exact revised bytes.
        with open(rejected_draft_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(rr.revised_text)
    # A best-effort rejected changes record: what we could assemble, or the reason.
    rejected_record = {
        "schema": "advisory-board/changes@1",
        "rejected": True,
        "reason": (rr.pre_spawn_error or rr.reject_error or rr.parse_error
                   or rr.failure_class or "revision seat dropped"),
        "revision_seat": rr.seat,
    }
    with open(changes_rejected_path, "w", encoding="utf-8") as handle:
        json.dump(rejected_record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    reason = rejected_record["reason"]
    tk.finish("verdict-only", f"revision did not deliver ({reason})")
    print(f"\n⚠ revision did NOT produce a usable revised draft — reason: {reason}")
    print(f"  see {rev_dir}/{seat.id}.md and {rev_dir}/{seat.id}.raw for the full record")
    print(f"  the rejection was recorded to {changes_rejected_path}"
          + (f" and {rejected_draft_path}" if rr.revised_text is not None else ""))
    print("\nThe verdict + rounds are intact — the revision failure discards nothing. "
          "Re-run with --output revised-draft to retry, or apply the verdict's findings "
          "by hand.")
    # exit 0 by default (a revision hiccup never discards the verdict/rounds);
    # --strict-exit → EXIT_NO_VERDICT (4), the same code the synthesizer uses.
    if getattr(args, "strict_exit", False):
        return EXIT_NO_VERDICT
    return EXIT_OK


def cmd_history(args) -> int:
    """`history` (v1.11 #5): list past runs from the persistent runs root.

    Reads each run's verdict.json (falling back to run-recipe.yaml for a
    partial/legacy run, which lists as `incomplete`) — a local disk read only,
    nothing is spawned and nothing egresses. Exits 0 even when the root is
    empty or absent: an empty history is an answer, not an error."""
    root = getattr(args, "runs_root", None) or default_runs_root()
    root = os.path.abspath(os.path.expanduser(root))
    print(render_history_table(collect_history(root), root))
    return EXIT_OK


def cmd_ask(args) -> int:
    """`ask` (v1.12 #4): post-verdict cross-examination of a completed run.

    Loads the run's recorded board, builds a context packet from that run's OWN
    artifacts (reviewed material + mechanical verdict digest + each addressed seat's
    prior review), RE-CONSENTS the new bytes, fans one round out to the addressed
    seat(s), and writes addendum-N.md + a refreshed handoff pointer."""
    return run_ask(
        args.run_dir, args.question, getattr(args, "seat", None),
        assume_yes=getattr(args, "yes", False),
        skip_gate=getattr(args, "skip_sensitivity_gate", False),
        sensitivity_floor=getattr(args, "sensitivity", None),
    )


def cmd_render(args) -> int:
    return _delegate("render_handoff.py", args.passthrough)


def cmd_consensus(args) -> int:
    return _delegate("render_verdict.py", args.passthrough)


def cmd_verify(args) -> int:
    return _delegate("verify_evidence.py", args.passthrough)


def cmd_validate(args) -> int:
    return _delegate("board_verdict.py", args.passthrough)


def _delegate(script: str, passthrough: list) -> int:
    # __file__ is _conductor/cli.py; the delegated scripts sit in the
    # parent scripts/ dir, next to run_board.py.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target = os.path.join(here, script)
    if not os.path.isfile(target):
        die(f"{script} not found next to run_board.py", EXIT_USAGE)
    completed = subprocess.run([sys.executable, target, *passthrough])
    return completed.returncode


# Argument parsing


def add_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", help="PATH to source material, or - for stdin")
    parser.add_argument("--mode", choices=("gate", "advisory"),
                        help="gate (default; quarantined) or advisory (opt-in; your own non-sensitive material)")
    parser.add_argument("--rounds", choices=("1", "2", "3", "auto"))
    parser.add_argument("--max-rounds", dest="max_rounds", type=int, default=None, metavar="N",
                        help=f"hard ceiling for --rounds auto (default {DEFAULT_MAX_ROUNDS}); the "
                             "convergence stop-rule may stop earlier. Ignored for an explicit "
                             "--rounds 1|2|3. Persisted in the recipe so an auto run reproduces.")
    parser.add_argument("--cross-reading", dest="cross_reading",
                        choices=("none", "summaries", "full"))
    parser.add_argument("--tier", choices=("quick", "standard", "deep"),
                        help="one-flag cost/depth posture, applied as a BASE that explicit "
                             "flags always override. quick: 1 round, summaries cross-reading, "
                             "reduced per-seat reasoning (claude high, codex medium; seats "
                             "without an effort knob untouched — model ids never change). "
                             "standard: today's defaults (a no-op). deep: 3 rounds, full "
                             "cross-reading, default max-tier reasoning (codex stays at "
                             "xhigh, its API ceiling). The recipe records the RESOLVED "
                             "values, never the tier, so --from-recipe replays exactly — "
                             "the pair is refused.")
    parser.add_argument("--lens", action="append", metavar="PRESET | SEAT=LENS",
                        help=f"lens preset for the board (default {DEFAULT_LENS}); repeat with "
                             "SEAT=LENS to give one seat its own focus (a free-form string, or a "
                             "preset name for its primary focus)")
    parser.add_argument("--board", help="comma-separated seats (default claude,codex,gemini)")
    parser.add_argument("--model", action="append", metavar="SEAT=ID",
                        help="override a seat's model (repeatable)")
    parser.add_argument("--sensitivity", choices=("public", "redacted", "local-only"),
                        help="public proceeds after disclosure; redacted (default) blocks for "
                             "hash-bound approval; local-only forbids external egress")
    parser.add_argument("--output",
                        choices=("quick-verdict", "full-handoff", "implementation-sequence",
                                 "revised-draft"),
                        help="verdict render shape, or (v1.13) revised-draft: after synthesis, "
                             "spawn a revision seat to produce a board-derived, findings-mapped "
                             "fixed copy of the source + changes.json (the edit->finding "
                             "mapping; per-edit board endorsement is the later P4 pass). "
                             "revised-draft REQUIRES --synthesize (or a --from-recipe replay of "
                             "a synthesized revised-draft run) — a verdict must exist to revise.")
    parser.add_argument("--source-type", dest="source_type", choices=("prose", "code"),
                        help="prose|code for --output revised-draft — selects the redline "
                             "format downstream (P3). Overrides the extension heuristic; "
                             "REQUIRED for a stdin or unknown-extension source. Only accepted "
                             "with --output revised-draft.")
    parser.add_argument("--revision-seat", dest="revision_seat", metavar="SEAT",
                        help="which board seat's CLI/adapter spawns the revision (default: "
                             "claude if seated, else the first usable seat). Must be one of "
                             "the run's board seats — the revision seat egresses to that "
                             "provider, covered by the run's existing disclosure. Only "
                             "accepted with --output revised-draft.")
    parser.add_argument("--no-endorse", dest="no_endorse", action="store_true",
                        help="skip the endorsement pass on a --output revised-draft run "
                             "(the token-cost opt-out). By default, once the revision "
                             "succeeds every NON-revision seat votes ENDORSE/OBJECT/ABSTAIN "
                             "on each edit + unresolved conflict, recorded in "
                             "changes.json.endorsements — so the fixed copy is board-endorsed, "
                             "not just findings-mapped. Only accepted with --output revised-draft.")
    parser.add_argument("--rubric", action="store_true",
                        help="RUBRIC-FIRST (v1.15): before round 1, every seat proposes 3–7 "
                             "weighted criteria (a parallel fan-out under the run's existing "
                             "egress disclosure — the same source the round-1 packet sends), then "
                             "one board seat (the CHAIR) merges them into one weighted rubric the "
                             "conductor reconciles mechanically (every proposal subsumed or "
                             "dropped-with-reason; weights sum to exactly 100). rubric.json becomes "
                             "the pre-round artifact of record. Fewer than two usable proposals, or "
                             "a chair merge that can't be reconciled, REFUSES the run before any "
                             "opinion round spends a token. Orthogonal to --tier/--lens; recorded "
                             "in the recipe so --from-recipe replays it.")
    parser.add_argument("--chair-seat", dest="chair_seat", metavar="SEAT",
                        help="which board seat's CLI/adapter spawns the rubric CHAIR merge "
                             "(default: claude if seated, else the first seat with a usable "
                             "proposal). Selected on the UNIQUE seat-id axis (the same ids --model "
                             "and --revision-seat use), so a duplicate-provider seat is individually "
                             "selectable and an ambiguous provider name is refused. Must be a board "
                             "seat — the chair egresses to that provider, covered by the run's "
                             "existing disclosure. Only accepted with --rubric.")
    parser.add_argument("--out", help="exact output directory (default: a persistent "
                                      "<runs root>/<slug>-<date> — see --runs-root/--ephemeral)")
    parser.add_argument("--runs-root", dest="runs_root", metavar="DIR",
                        help="parent for the default per-run dir (default ~/.advisory-board/runs; "
                             "$ADVISORY_BOARD_RUNS_ROOT overrides, this flag wins over both). "
                             "Contradicts --out/--ephemeral (refused).")
    parser.add_argument("--ephemeral", action="store_true",
                        help="write artifacts to a throwaway /tmp/advisory-board-<ts> instead of "
                             "the persistent runs root (the pre-v1.11 default). Contradicts "
                             "--out/--runs-root (refused).")
    parser.add_argument("--no-live-status", dest="no_live_status", action="store_true",
                        help="skip the live progress view (v1.14 #10). By default a run writes a "
                             "status.json + self-refreshing status.html into the run dir, rewritten "
                             "atomically on every seat/round transition, and prints flushed per-seat "
                             "progress lines — something to watch during a long background run. This "
                             "opts out (no status.* files, no extra lines) for a byte-exact run dir; "
                             "the artifacts of record are identical either way.")
    parser.add_argument("--title", help="run title (default derived from the source; also names "
                                        "the default run dir's <slug>)")
    parser.add_argument("--from-recipe", dest="from_recipe",
                        help="re-run from a run-recipe.yaml. Reuses the recipe's recorded out dir "
                             "(rewriting that run's artifacts in place) unless --out/--runs-root/"
                             "--ephemeral name somewhere fresh.")
    parser.add_argument("--revise", metavar="PRIOR_RUN_DIR|verdict.json",
                        help="re-review a revised draft with the prior run's verdict as context "
                             "(v1.12). --source is the REVISED draft; the round-1 prompts "
                             "additionally carry a mechanical digest of the prior verdict plus "
                             "the diff from the previously reviewed draft (recovered from the "
                             "prior run dir, sha-verified; diff omitted loudly if unrecoverable). "
                             "Every injected byte is inside the consent packet hash. The new "
                             "verdict records previous_run lineage; final-consensus renders the "
                             "cleared/still-open/new delta. Refused with --from-recipe (a revise "
                             "recipe already records revise_of).")
    parser.add_argument("--synthesize", action="store_true",
                        help="after the rounds complete, spawn a no-lens synthesizer seat to draft "
                             "verdict.json from the final-round reviews (M2). §11-safe: the "
                             "synthesizer is a REASONING SEAT, briefed only on the reviews + the "
                             "conductor-extracted VERDICT tokens; its output is merged into the "
                             "conductor's authoritative skeleton and schema-validated against "
                             "advisory-board/verdict@2 before write. The human still gates ship/abstain.")
    parser.add_argument("--synthesizer-seat", dest="synthesizer_seat", metavar="SEAT",
                        help="which seat's CLI/adapter spawns the synthesizer (default: claude if "
                             "in the board, else the first board seat). Must be one of the run's "
                             "board seats — the synthesizer egresses to that provider, covered by "
                             "the run's existing disclosure (a fresh provider would need its own).")
    parser.add_argument("--repo", metavar="PATH",
                        help="REPO-GROUNDING: a local repository the board may READ (read-only) "
                             "while reviewing, so findings cite real path:line. Augments --source "
                             "(source frames the question; the repo is the evidence base). The scope "
                             "is .gitignore-respecting, secret-denylisted, and symlink-confined; its "
                             "contents become part of the egress disclosure. In gate mode this "
                             "requires every seat to be network-isolatable (gemini/antigravity are "
                             "refused — read+network is an exfil channel); advisory mode allows it.")
    parser.add_argument("--repo-include", dest="repo_include", action="append", metavar="GLOB",
                        help="narrow the --repo grounding scope to files matching this fnmatch glob "
                             "(repeatable).")
    parser.add_argument("--repo-exclude", dest="repo_exclude", action="append", metavar="GLOB",
                        help="remove files matching this fnmatch glob from the --repo grounding "
                             "scope (repeatable).")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_board.py",
        description="The Advisory Board conductor: registry, dry-run, preflight, "
                    "egress/quarantine gate, round-1 + round-2 fan-out with failure "
                    "protocol and cross-reading packets, and the canonical-verdict chain "
                    "(verify evidence -> consensus -> validate/gate).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="resolve config and emit run-recipe.yaml + run-card")
    add_run_options(p_init)
    p_init.add_argument("--dry-run", action="store_true", help="print config + recipe, write nothing")
    p_init.set_defaults(func=cmd_init)

    p_pre = sub.add_parser("preflight", help="probe each seat and print a GO/NO-GO table")
    add_run_options(p_pre)
    p_pre.set_defaults(func=cmd_preflight)

    p_run = sub.add_parser("run", help="resolve -> preflight -> egress gate -> round-1 -> round-2")
    add_run_options(p_run)
    p_run.add_argument("--dry-run", action="store_true",
                       help="print config + run-card + preflight plan + manifest + tree; no spawn")
    p_run.add_argument("--yes", action="store_true",
                       help="auto-approve egress (still bound to and stamped with the content hash)")
    p_run.add_argument("--skip-sensitivity-gate", dest="skip_sensitivity_gate", action="store_true",
                       help="OVERRIDE: bypass hash-bound approval for non-public material (logged loudly)")
    p_run.add_argument("--update-tools", dest="update_tools", action="store_true",
                       help="before preflight, check each CLI vs latest and update stale ones "
                            "(consent-gated; --yes auto-approves)")
    p_run.add_argument("--timeout", action="append", default=None,
                       metavar="SECONDS | SEAT=SECONDS",
                       help="per-seat hard timeout for the round fan-outs and the synthesizer "
                            "(default: the adapter cap, 900s = 15 min). Repeatable: a bare "
                            "SECONDS applies to every seat; SEAT=SECONDS overrides one seat, "
                            "targeted by id exactly like --model/--lens (an unknown id fails "
                            "loudly).")
    p_run.add_argument("--digest-format", dest="digest_format",
                       choices=("markdown", "json"), default="markdown",
                       help="board-packet digest format for round 2+ under --cross-reading "
                            "summaries. markdown (default) writes board-packet-round-N.md as "
                            "before; json ALSO writes board-packet-round-N.json — the same "
                            "parsed signals (verdict tokens, agreement, shared citations, "
                            "per-topic per-seat takes) as typed JSON. No new reasoning; a "
                            "serialization of the digest the run already computes.")
    p_run.add_argument("--strict-exit", dest="strict_exit", action="store_true",
                       help="exit non-zero if --synthesize fails to produce a usable "
                            "verdict.json (for CI gates). Default exits 0 with a warning "
                            "so a synth hiccup never discards the successful rounds.")
    p_run.set_defaults(func=cmd_run)

    p_tool = sub.add_parser("toolchain",
                            help="check each seat CLI vs its latest release; --update upgrades stale ones")
    p_tool.add_argument("--board", help="comma-separated seats (default: all registered seats)")
    p_tool.add_argument("--update", action="store_true",
                        help="update stale CLIs (consent-gated: confirms first unless --yes)")
    p_tool.add_argument("--install", action="store_true",
                        help="install absent CLIs (consent-gated; an account/auth is still required)")
    p_tool.add_argument("--yes", action="store_true",
                        help="skip the confirmation prompt (for unattended runs)")
    p_tool.set_defaults(func=cmd_toolchain)

    p_doctor = sub.add_parser(
        "doctor",
        help="guided setup check: sweep EVERY registered provider (installed -> version -> "
             "auth -> model) with per-provider fix-it steps and a viable-board summary; "
             "probes and smoke-pings only — never your material")
    p_doctor.set_defaults(func=cmd_doctor)
    p_hist = sub.add_parser("history",
                            help="list past runs from the persistent runs root (date, title, "
                                 "verdict, confidence, unanimous, seats, run dir)")
    p_hist.add_argument("--runs-root", dest="runs_root", metavar="DIR",
                        help="runs root to list (default $ADVISORY_BOARD_RUNS_ROOT, "
                             "else ~/.advisory-board/runs)")
    p_hist.set_defaults(func=cmd_history)

    p_ask = sub.add_parser("ask",
                           help="post-verdict cross-examination: put a follow-up question to a "
                                "completed run's board (writes addendum-N.md; re-consents egress)")
    p_ask.add_argument("question", help="the follow-up question to put to the board")
    p_ask.add_argument("--run", required=True, dest="run_dir", metavar="DIR",
                       help="the completed run directory to question")
    p_ask.add_argument("--seat", metavar="ID",
                       help="address one seat only, by its run seat id (default: every seat "
                            "in the run's recipe)")
    p_ask.add_argument("--sensitivity", metavar="LEVEL",
                       help="sensitivity floor for the ask egress (public|redacted|local-only); "
                            "joins the stricter-of rule with the run's recorded posture — it "
                            "can only TIGHTEN, never loosen")
    p_ask.add_argument("--yes", action="store_true", dest="yes",
                       help="auto-approve egress of the ask packet (non-public runs)")
    p_ask.add_argument("--skip-sensitivity-gate", action="store_true",
                       dest="skip_sensitivity_gate",
                       help="OVERRIDE: bypass hash-bound approval (records the override)")
    p_ask.set_defaults(func=cmd_ask)

    p_render = sub.add_parser("render", help="delegate to render_handoff.py (HTML from handoff-data.json)")
    p_render.add_argument("passthrough", nargs=argparse.REMAINDER)
    p_render.set_defaults(func=cmd_render)

    p_verify = sub.add_parser("verify", help="delegate to verify_evidence.py (resolve + stamp evidence)")
    p_verify.add_argument("passthrough", nargs=argparse.REMAINDER)
    p_verify.set_defaults(func=cmd_verify)

    p_consensus = sub.add_parser("consensus", help="delegate to render_verdict.py (final-consensus.md from verdict.json)")
    p_consensus.add_argument("passthrough", nargs=argparse.REMAINDER)
    p_consensus.set_defaults(func=cmd_consensus)

    p_validate = sub.add_parser("validate", help="delegate to board_verdict.py (schema check + --gate)")
    p_validate.add_argument("passthrough", nargs=argparse.REMAINDER)
    p_validate.set_defaults(func=cmd_validate)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

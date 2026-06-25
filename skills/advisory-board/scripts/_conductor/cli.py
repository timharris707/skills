"""The argparse front end: subcommand handlers, the delegation shim, and main()."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

from _conductor.constants import (
    DEFAULT_LENS,
    DEFAULT_MAX_ROUNDS,
    EXIT_EGRESS_BLOCKED,
    EXIT_OK,
    EXIT_PREFLIGHT_NOGO,
    EXIT_USAGE,
    SMOKE_PROMPT,
    die,
)
from _conductor.registry import REGISTRY
from _conductor.convergence import (
    DEFAULT_CONVERGE_THRESHOLD,
    board_movement,
    movement_detail_line,
)
from _conductor.config import (
    parse_board,
    resolve_config,
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

__all__ = [
    "cmd_init",
    "cmd_preflight",
    "cmd_toolchain",
    "_maybe_update_tools",
    "cmd_run",
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
    names = parse_board(board_arg) if board_arg else list(REGISTRY.keys())
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
    blobs = build_packet(config)
    content_hash = packet_hash(blobs)

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
        print(render_egress_manifest(config, blobs, content_hash), end="")
        print()
        print("=== artifact tree it WOULD create ===")
        print(render_artifact_tree(config))
        print()
        print(f"[dry-run] no preflight, no packet written, no egress, no spawn. "
              f"content hash = sha256:{content_hash}")
        return EXIT_OK

    # 0. Toolchain currency (opt-in): update stale CLIs before probing, so a
    #    freshly-renamed model id resolves instead of 404-ing the board.
    _maybe_update_tools(config, args)

    # 1. Preflight — GO/NO-GO before anything else.
    print("=== preflight ===")
    preflight = run_preflight(config)
    print(render_preflight_table(preflight))
    go = sum(1 for r in preflight if r.go)
    if go < 2:
        guidance = render_board_guidance(preflight, config)
        if guidance:
            print("\n" + guidance)
        die("fewer than two seats are GO — not running a one-voice board", EXIT_PREFLIGHT_NOGO)

    # 2. Egress gate — the pre-spawn hard stop. Nothing has left the machine yet;
    #    the smoke pings above carried only a fixed token, never the source.
    print("\n=== egress gate ===")
    print(disclosure_line(config))
    approval = enforce_egress_gate(
        config, blobs,
        assume_yes=getattr(args, "yes", False),
        skip_gate=getattr(args, "skip_sensitivity_gate", False),
    )
    print(f"egress: {'APPROVED' if approval.approved else 'REFUSED'} "
          f"({approval.mode}) — {approval.detail}")
    print(f"content hash: sha256:{content_hash}")

    if not approval.approved:
        # Persist the manifest + a machine-readable refusal record so the user can
        # review exactly what was blocked. The packet/prompts are NOT written —
        # nothing the gate refused may be materialized (the pre-spawn hard stop).
        os.makedirs(config.out_dir, exist_ok=True)
        _write(os.path.join(config.out_dir, "egress-manifest.md"),
               render_egress_manifest(config, blobs, content_hash))
        _write(os.path.join(config.out_dir, "sensitivity.json"),
               render_sensitivity_json(config, approval))
        die(f"egress blocked — see {config.out_dir}/egress-manifest.md", EXIT_EGRESS_BLOCKED)

    # 3. Approved: persist the exact approved packet + provenance BEFORE spawning.
    write_pre_spawn_artifacts(config, blobs, approval, content_hash)

    # 4. Round-1 fan-out (M3) — the first real spawn. run_round re-asserts the
    #    egress hash one last time, then feeds each seat its approved blob verbatim
    #    (so the bytes that actually leave equal what consent was bound to), with
    #    per-seat timeout / one-retry / failure classification (§13).
    timeout = getattr(args, "timeout", None)
    print("\n=== round 1 (fan-out) ===")
    r1 = run_round(config, blobs, approval, round_no=1, timeout=timeout)
    write_round_artifacts(config, r1, 1)
    rounds_done = [r1]
    print(render_round_table(r1, 1))

    usable1 = [r for r in r1 if r.usable]
    if len(usable1) < 2:
        _write(os.path.join(config.out_dir, "run-metadata.md"),
               render_run_metadata(config, preflight, approval, rounds=rounds_done))
        _write(os.path.join(config.out_dir, "run-metadata.tsv"),
               render_run_metadata_tsv(rounds_done))
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
        rN_blobs, board_packet = build_round2(config, prev, round_no=round_no)
        if board_packet is not None:
            _write(os.path.join(config.out_dir, f"board-packet-round-{round_no}.md"), board_packet)
        for b in rN_blobs:
            _write(os.path.join(config.out_dir, b.relpath), b.text)
        rN_hash = packet_hash(rN_blobs)
        print(f"\n=== round {round_no} (cross-reading + debate) ===")
        print(f"cross-reading: {config.cross_reading}  ·  round-{round_no} packet hash: sha256:{rN_hash}")
        print(f"(round {round_no} sends each seat's round-{round_no - 1} review to the others at the "
              "same providers — no new source egresses; covered by the run-card's disclosed "
              "multi-round plan.)")
        rN = run_round(config, rN_blobs, approval, round_no=round_no, timeout=timeout)
        write_round_artifacts(config, rN, round_no)
        rounds_done.append(rN)
        print(render_round_table(rN, round_no))
        mv = board_movement(prev, rN)
        movements.append(mv)
        print(f"movement {mv['from_round']} → {mv['to_round']}: {mv['moved']} of "
              f"{mv['considered']} seat(s) moved — {movement_detail_line(mv)}")
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
        print(f"\nWARNING: the board collapsed to {len(usable_last)} usable voice(s) by round "
              f"{last[0].round_no} — that is not a board. Inspect round-{last[0].round_no}/*.raw and "
              "logs/, fix the failed seats, and re-run. Synthesis is intentionally NOT attempted on "
              "fewer than two voices.")
        return EXIT_PREFLIGHT_NOGO

    # Rounds are captured. Synthesis stays a REASONING task (§11): the conductor
    # produces clean packets and hands the latest round's reviews to the orchestrating
    # agent (or one neutral seat) to fill verdict.json — it does NOT generate the
    # verdict in code. Once verdict.json exists, the deterministic M5 chain runs:
    last_dir = f"{config.out_dir}/round-{last[0].round_no}"
    print(f"\nRounds complete ({len(rounds_done)} round(s)): {len(usable_last)} usable reviews in "
          f"{last_dir}/.")
    print("\nNext — synthesize, then run the deterministic M5 chain:")
    print(f"  1. Read {last_dir}/*.md and write {config.out_dir}/verdict.json "
          "(advisory-board/verdict@2; cite typed evidence on each blocker).")
    print(f"  2. run_board.py verify {config.out_dir}/verdict.json --source <src> --run {config.out_dir}")
    print(f"  3. run_board.py consensus {config.out_dir}/verdict.json --run {config.out_dir} "
          f"-o {config.out_dir}/final-consensus.md")
    print(f"  4. run_board.py validate {config.out_dir}/verdict.json --gate")
    return EXIT_OK


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
    parser.add_argument("--lens", help=f"lens preset (default {DEFAULT_LENS})")
    parser.add_argument("--board", help="comma-separated seats (default claude,codex,gemini)")
    parser.add_argument("--model", action="append", metavar="SEAT=ID",
                        help="override a seat's model (repeatable)")
    parser.add_argument("--sensitivity", choices=("public", "redacted", "local-only"),
                        help="public proceeds after disclosure; redacted (default) blocks for "
                             "hash-bound approval; local-only forbids external egress")
    parser.add_argument("--output",
                        choices=("quick-verdict", "full-handoff", "implementation-sequence"))
    parser.add_argument("--out", help="output directory (default /tmp/advisory-board-<ts>)")
    parser.add_argument("--title", help="run title (default derived from the source)")
    parser.add_argument("--from-recipe", dest="from_recipe", help="re-run from a run-recipe.yaml")


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
    p_run.add_argument("--timeout", type=int, default=None, metavar="SECONDS",
                       help="per-seat hard timeout for the round-1 fan-out "
                            "(default: the adapter cap, 900s = 15 min)")
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

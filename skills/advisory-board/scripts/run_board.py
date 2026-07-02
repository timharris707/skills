#!/usr/bin/env python3
"""run_board.py — the Advisory Board conductor (M1 + M2 + M3 + M4 + M5).

The skill's controls used to be prose addressed to the very agent that wants to
run the board. This conductor turns the load-bearing mechanics into code: a
deterministic seat-adapter registry (one place that knows each CLI's quirks), an
executable preflight (GO/NO-GO), and — before a single byte of source material
leaves the machine — a hash-bound egress gate with a mode-dependent quarantine
posture, followed by a real Round-1 fan-out with a defined failure protocol.

This file implements milestones M1, M2 and M3 of design/run-board-conductor.md:

  M1  skeleton + arg parsing + config/mode resolution + the SeatAdapter registry
      (claude / codex / gemini) + run-recipe/run-card render + `--dry-run`.
  M2  executable preflight (GO/NO-GO) + the egress manifest (consent bound to a
      content hash) + the pre-spawn hard stop + gate-mode isolation flags wired
      through the registry.
  M3  Round-1 fan-out: real subprocess spawn (process-group-killed on timeout),
      isolation enforced at spawn, the §13 failure protocol (success-shape check,
      Timeout|AuthFailure|InvalidOutput|NoOutput|ModelNotFound classes, one retry
      on Timeout|InvalidOutput), and per-seat artifacts — round-1/<seat>.md, the
      .raw black-box recorder (input/source/packet hashes + answered model), and
      logs/<seat>-round-1.stderr.
  M4  Round 2: a cross-reading board-packet-round-2.md built from round-1, a debate
      fan-out (only usable round-1 seats continue; source + peers re-supplied since
      each spawn is stateless), and the diffable run-metadata.tsv (one row per seat
      per round). Round 2 egresses only derivatives of already-approved source to the
      same providers, so it records its own packet hash but reuses the run's approval
      (the run-card disclosed the multi-round plan). The `summaries` packet is the M4
      structured digest (_conductor/digest.py): a verdict/citation agreement header
      over the board + every seat's take on each topic side by side, regrouped from
      each review's own section headers (never claim-clustered — principle #1). `full`
      is verbatim; `none` keeps each seat solo.

  M1' Round 3 / `auto` stop-rule (v1.x): each seat ends its review with a machine-
      readable `VERDICT: ship|caution|block` line; _conductor/convergence.py measures
      movement between rounds as a PURE function over that token + the seat's citation
      set (never the prose — principle #1). `--rounds auto` loops rounds 2…N while the
      board is still moving and stops at `converged` (or `--max-rounds`, default 3);
      an explicit `--rounds N` runs N rounds. The per-transition movement + stop reason
      land in run-metadata.md's `## Convergence` section and the tsv's `verdict` column.

  M5  Canonical verdict + resolved evidence. `run` still stops at the last round's
      boundary and hands the clean per-seat reviews to the synthesizer (§11) — the
      conductor does NOT generate the verdict in code. Once verdict.json exists
      (schema advisory-board/verdict@2, with typed evidence[] on blockers), the
      deterministic chain runs as subcommands: `verify` resolves and stamps each
      citation (verify_evidence.py — code path:line/symbol against the source,
      source quotes against the captured packet, never a live fetch), `consensus`
      renders final-consensus.md FROM the verdict (render_verdict.py), and
      `validate --gate` decides ship/block/ABSTAIN (board_verdict.py). `abstain`
      ("human required", exit 3) fires when the board is torn across the gate line
      with no majority, or a blocker rests on a refuted citation — driven by
      OBSERVED cross-seat agreement, never self-reported confidence.

Subcommands:
  init        resolve config and emit run-recipe.yaml + the run-card (no spawn)
  toolchain   check each seat CLI vs its latest release; --update upgrades stale ones
  doctor      guided setup check — sweep EVERY registered provider (installed ->
              version -> auth -> model) with fix-it steps + a viable-board summary;
              probes and smoke-pings only, never the user's material
  preflight   probe each seat (version / smoke ping) and print a GO/NO-GO table
  run         resolve -> preflight -> egress gate -> round-1 -> round-2 -> artifacts
  history     list past runs from the persistent runs root (~/.advisory-board/runs by
              default; $ADVISORY_BOARD_RUNS_ROOT / --runs-root relocate it) — read
              from each run's verdict.json, degrading to `incomplete` for a
              partial/legacy run. A run opts back into a throwaway /tmp dir with
              `--ephemeral`; `--out DIR` still names an exact dir.
  verify      delegate to verify_evidence.py (resolve + stamp a verdict's evidence)
  consensus   delegate to render_verdict.py (final-consensus.md from verdict.json)
  render      delegate to render_handoff.py (final-consensus.html from handoff-data.json)
  validate    delegate to board_verdict.py (validate / gate verdict.json; abstain = exit 3)

Toolchain currency (the `toolchain` subcommand, also `run --update-tools`) keeps a
stale CLI from 404-ing a freshly-renamed frontier model id: it reads installed-vs-
latest per seat (reporting current / STALE / missing / unknown), updates stale CLIs
and installs absent ones on consent (`--update` / `--install`). Model ids stay
pinned; a still-unresolvable id yields a *proposed* fallback, never an auto swap.
When fewer than two seats are usable, preflight/run print actionable guidance
(install vs auth, plus same-provider / local-seat fallbacks) instead of dead-ending,
so a single-provider user is never stuck. Installing a CLI never implies an account.

Standard library only. Tested against mock CLIs on PATH (see ../tests/).
"""
from __future__ import annotations

# The conductor's implementation lives in the _conductor package (split out
# for navigability; see scripts/README.md). This module is a thin façade: it
# re-exports the entire public API so `import run_board` keeps working, and it
# stays the CLI entry point.
from _conductor.constants import *  # noqa: F401,F403
from _conductor.registry import *  # noqa: F401,F403
from _conductor.config import *  # noqa: F401,F403
from _conductor.grounding import *  # noqa: F401,F403  (repo-grounding: scope/snapshot/consent)
from _conductor.spawn import *  # noqa: F401,F403
from _conductor.convergence import *  # noqa: F401,F403
from _conductor.digest import *  # noqa: F401,F403
from _conductor.prompts import *  # noqa: F401,F403
# (convergence re-exported above; digest builds on it and feeds the summaries packet)
from _conductor.toolchain import *  # noqa: F401,F403
from _conductor.egress import *  # noqa: F401,F403
from _conductor.preflight import *  # noqa: F401,F403
from _conductor.doctor import *  # noqa: F401,F403  (setup doctor: guided provider sweep)
from _conductor.synthesizer import *  # noqa: F401,F403
from _conductor.recipe import *  # noqa: F401,F403
from _conductor.history import *  # noqa: F401,F403  (v1.11: the `history` run listing)
from _conductor.artifacts import *  # noqa: F401,F403
from _conductor.rounds import *  # noqa: F401,F403
from _conductor.cli import *  # noqa: F401,F403

if __name__ == "__main__":
    raise SystemExit(main())

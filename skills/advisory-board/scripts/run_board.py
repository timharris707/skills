#!/usr/bin/env python3
"""run_board.py — the Advisory Board conductor (M1 + M2 + M3 + M4).

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
  M4  Round 2: a cross-reading board-packet-round-2.md (full | structural digest |
      none) built from round-1, a debate fan-out (only usable round-1 seats
      continue; source + peers re-supplied since each spawn is stateless), and the
      diffable run-metadata.tsv (one row per seat per round). Round 2 egresses only
      derivatives of already-approved source to the same providers, so it records
      its own packet hash but reuses the run's approval (the run-card disclosed the
      multi-round plan). Round 3 / `auto` stay v1.x.

What is deliberately NOT here yet (later milestones): the canonical verdict +
resolved evidence (M5). `run` stops at the last round's boundary and hands the
clean per-seat reviews to the synthesizer (§11) rather than flattening them in
code.

Subcommands:
  init        resolve config and emit run-recipe.yaml + the run-card (no spawn)
  toolchain   check each seat CLI vs its latest release; --update upgrades stale ones
  preflight   probe each seat (version / smoke ping) and print a GO/NO-GO table
  run         resolve -> preflight -> egress gate -> round-1 -> round-2 -> artifacts
  render      delegate to render_handoff.py (final-consensus.html from data)
  validate    delegate to board_verdict.py (validate / gate verdict.json)

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
from _conductor.spawn import *  # noqa: F401,F403
from _conductor.prompts import *  # noqa: F401,F403
from _conductor.toolchain import *  # noqa: F401,F403
from _conductor.egress import *  # noqa: F401,F403
from _conductor.preflight import *  # noqa: F401,F403
from _conductor.recipe import *  # noqa: F401,F403
from _conductor.artifacts import *  # noqa: F401,F403
from _conductor.rounds import *  # noqa: F401,F403
from _conductor.cli import *  # noqa: F401,F403

if __name__ == "__main__":
    raise SystemExit(main())

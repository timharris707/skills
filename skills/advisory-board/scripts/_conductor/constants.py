"""Shared constants and tiny helpers (exit codes, schema ids, providers,
lens presets, failure classes, and the date/time + die primitives)."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime

__all__ = [
    "RECIPE_SCHEMA",
    "SENSITIVITY_SCHEMA",
    "SMOKE_PROMPT",
    "DEFAULT_MAX_ROUNDS",
    "EXIT_OK",
    "EXIT_PREFLIGHT_NOGO",
    "EXIT_USAGE",
    "EXIT_EGRESS_BLOCKED",
    "EXIT_NO_VERDICT",
    "PROVIDERS",
    "LENS_PRESETS",
    "DEFAULT_LENS",
    "FAILURE_TIMEOUT",
    "FAILURE_AUTH",
    "FAILURE_INVALID",
    "FAILURE_NOOUTPUT",
    "FAILURE_MODEL",
    "MODEL_PRICING_USD_PER_MTOK",
    "PRICING_AS_OF",
    "TIER_PRESETS",
    "TIERS_AS_OF",
    "tier_provenance_line",
    "price_band_usd",
    "estimate_run",
    "render_estimate",
    "die",
    "now_date",
    "now_stamp",
]


RECIPE_SCHEMA = "advisory-board/run-recipe@1"
SENSITIVITY_SCHEMA = "advisory-board/sensitivity@1"
SMOKE_PROMPT = "Reply with the single word: ready"

# The hard ceiling on `--rounds auto` (M1): the convergence stop-rule keeps going
# while the board is still moving, but never past this many rounds. Overridable
# per run with `--max-rounds`. Default 3 keeps the common case bounded (round 3 is
# the headline "extra" round) while still letting `auto` stop early at 2.
DEFAULT_MAX_ROUNDS = 3

# Exit codes (distinct so callers / CI can branch).
EXIT_OK = 0
EXIT_PREFLIGHT_NOGO = 1   # fewer than two seats GO, or a delegated gate failed
EXIT_USAGE = 2            # bad arguments / config / IO
EXIT_EGRESS_BLOCKED = 3   # consent not granted, or sensitivity forbids egress
EXIT_NO_VERDICT = 4       # --synthesize failed to produce a usable verdict.json,
                          # and --strict-exit was set (opt-in CI gate). Without
                          # --strict-exit the same failure exits EXIT_OK (the
                          # successful rounds are never discarded by a synth hiccup).

PROVIDERS = {
    "claude": "Anthropic",
    "codex": "OpenAI",
    "gemini": "Google",
    "antigravity": "Google",
    "ollama": "local",
}

# Lens presets (mirrors references/lens-presets.md). Each preset is the ordered
# trio of lenses; the default Claude/Codex/Gemini lineup maps to them in order.
LENS_PRESETS = {
    "software-architecture": [
        "Architecture & systems — design soundness, invariants, failure modes, adversarial review",
        "Implementation & testing — repo-grounded execution, migration, test strategy, edge cases",
        "Product & operations — rollout, latency, observability, evaluation, user-workflow risk",
    ],
    "product-strategy": [
        "Market & user value — positioning, demand, differentiation, jobs-to-be-done",
        "Execution & GTM — feasibility, resourcing, sequencing, go-to-market mechanics",
        "Second-order & risk — competitive response, cannibalization, downside and stakeholder risk",
    ],
    "research-paper": [
        "Methodology & validity — design, statistics, threats to validity, confounds",
        "Novelty & positioning — contribution, related work, what is actually new",
        "Reproducibility & impact — can it be reproduced, stated limitations, who it helps",
    ],
    "legal-contract": [
        "Risk allocation — liability, indemnity, limitation of liability, termination, IP",
        "Enforceability & compliance — governing law, regulatory fit, ambiguity, gaps",
        "Commercial practicality — operational burden, counterparty reality, negotiation leverage",
    ],
    "business-decision": [
        "First principles & economics — does the core logic and the math hold up",
        "Execution & feasibility — can this org actually do it, with what and by when",
        "Second-order & downside — stakeholders, incentives, what breaks if it works",
    ],
    "writing-editing": [
        "Argument & structure — thesis, logic, evidence, what is load-bearing",
        "Clarity & style — concision, flow, precision, tone for the audience",
        "Audience & impact — does it land, what is missing, what a skeptic seizes on",
    ],
}
DEFAULT_LENS = "software-architecture"

# --------------------------------------------------------------------------- #
# Run tiers (v1.11 #3b): one flag — `--tier quick|standard|deep` — that sets the
# run's whole cost/depth posture. Applied in config resolution as a BASE beneath
# explicit flags (--rounds / --cross-reading / per-seat reasoning always win;
# built-in defaults fill last) and NEVER persisted: run-recipe.yaml records the
# RESOLVED values, so --from-recipe replays exactly without knowing the tier
# (the pair is refused as contradictory).
#
# Model ids are deliberately NOT a tier knob: swapping in unverified "budget"
# ids risks model-404ing the board, so every tier runs the pinned REGISTRY
# models and dials rounds / cross-reading / reasoning instead.
#
# `reasoning` is keyed by PROVIDER (the REGISTRY name — so every claude seat on
# a duplicate/aliased board moves together) and lists only providers whose CLI
# exposes an effort knob to move; gemini / antigravity / ollama have none and
# stay untouched at every tier.
#
# HARD CEILING: codex's reasoning tops out at `xhigh` — `model_reasoning_effort=
# max` is a hard API 400 (see the v1.10 notes). No tier may set codex above
# xhigh; test-guarded.
# --------------------------------------------------------------------------- #

TIERS_AS_OF = "2026-07-01"   # levels last checked against the pinned CLIs' effort knobs
TIER_PRESETS = {
    # quick — the cheap pass: one round, digest cross-reading, reduced reasoning
    # on the seats that have the knob (claude high, codex medium).
    "quick": {
        "rounds": "1",
        "cross_reading": "summaries",
        "reasoning": {"claude": "high", "codex": "medium"},
    },
    # standard — exactly today's defaults; the flag is allowed and a no-op
    # (still noted in run-metadata provenance, since it was asked for).
    "standard": {
        "rounds": "2",
        "cross_reading": "summaries",
        "reasoning": {},   # registry defaults untouched
    },
    # deep — the high-stakes posture: three rounds, full cross-reading, and the
    # registry-default (max-tier) reasoning: claude stays max, codex stays
    # xhigh (its ceiling — never max).
    "deep": {
        "rounds": "3",
        "cross_reading": "full",
        "reasoning": {},   # registry defaults ARE the maximum safe tier
    },
}


def tier_provenance_line(name: str) -> str:
    """The one-line run-metadata provenance for a `--tier` run: the tier name
    plus the base values it set, rendered from TIER_PRESETS so the dict stays
    the single source of truth. Only rendered when the flag was given — a
    no-tier run's artifacts stay byte-identical."""
    preset = TIER_PRESETS[name]
    reasoning = preset["reasoning"]
    effort = (", ".join(f"{provider}={level}" for provider, level in reasoning.items())
              or "registry defaults")
    return (f"{name} (--tier) — base: rounds {preset['rounds']} · cross-reading "
            f"{preset['cross_reading']} · reasoning {effort}; explicit flags override")


# Failure classes (design §13). Tool-agnostic; consumed in full by M3.
FAILURE_TIMEOUT = "Timeout"
FAILURE_AUTH = "AuthFailure"
FAILURE_INVALID = "InvalidOutput"
FAILURE_NOOUTPUT = "NoOutput"
FAILURE_MODEL = "ModelNotFound"   # pinned model id did not resolve on the installed CLI


# --------------------------------------------------------------------------- #
# Cost & time transparency (v1.11 #3a): list prices + the preflight estimator.
# Everything here is BEST-EFFORT and labeled an estimate — never a gate (§ roadmap
# "always best-effort, never a gate"). Actual spend depends on caching, discounts,
# and each provider's subscription vs API billing; the board's default posture is
# subscription CLIs, where per-token dollars may not be billed at all.
# --------------------------------------------------------------------------- #

# Published list prices in USD per MILLION tokens, keyed by the model ids the
# REGISTRY pins (registry.py — frontier ids stay inline per the model-id policy).
# Table dated 2026-07-01, checked against the providers' published prices that
# day. Prices move; re-check before trusting a large-run estimate. A `None`
# entry means "not verified" — the estimator then reports that seat's cost as
# unknown rather than inventing a number (never $0, never a guess). The local
# ollama seat is genuinely $0 (no external egress, no metered billing).
PRICING_AS_OF = "2026-07-01"
MODEL_PRICING_USD_PER_MTOK = {
    # (input $/MTok, output $/MTok) — uncached list rates; cache reads are cheaper
    "claude-fable-5": (10.00, 50.00),          # Anthropic
    "gpt-5.5": (5.00, 30.00),                  # OpenAI
    "gemini-3.5-flash": (1.50, 9.00),          # Google
    "Gemini 3.5 Flash (High)": (1.50, 9.00),   # antigravity display name — same model family
    "llama3.3": (0.00, 0.00),                  # local seat — no per-token cost at all
}


def price_band_usd(model: str, tokens_in: "Optional[int]" = None,
                   tokens_out: "Optional[int]" = None,
                   tokens_total: "Optional[int]" = None) -> "Optional[tuple]":
    """(low, high) USD estimate for one seat's REPORTED tokens, or None.

    None when the model has no verified table entry or nothing was reported.
    A known in/out split prices exactly at list (low == high); a total-only
    count (codex) is banded between all-input and all-output pricing. Either
    way it is an estimate — list prices, no caching/discount/subscription math.
    """
    prices = MODEL_PRICING_USD_PER_MTOK.get(model)
    if not prices or prices[0] is None or prices[1] is None:
        return None
    p_in, p_out = prices
    if tokens_in is not None and tokens_out is not None:
        cost = (tokens_in * p_in + tokens_out * p_out) / 1_000_000
        return (cost, cost)
    if tokens_total is not None:
        lo, hi = sorted((p_in, p_out))
        return (tokens_total * lo / 1_000_000, tokens_total * hi / 1_000_000)
    return None


# Rough estimator constants — deliberately coarse (order-of-magnitude bands, not
# precision): ~4 bytes/token for English/markdown, a fixed allowance for the round
# template + lens framing, and an output band covering a typical 7-section review.
_EST_BYTES_PER_TOKEN = 4
_EST_PROMPT_OVERHEAD_TOKENS = 1_200
_EST_REVIEW_OUT_TOKENS = (800, 2_600)      # (low, high) per seat per round
_EST_SUMMARY_TOKENS = 400                  # per peer review under --cross-reading summaries
_EST_MINUTES_PER_ROUND = (1.0, 5.0)        # frontier seats at high reasoning, parallel fan-out


def estimate_run(source_bytes: int, models: list, rounds: int, cross_reading: str) -> dict:
    """Pure preflight estimate: token band + cost band + rough minutes.

    Inputs are the run's shape only (source size, the per-seat model ids, the
    round count, the cross-reading mode) — no I/O, no clock, fully deterministic.
    The returned numbers are labeled estimates wherever they are rendered; they
    inform the human before launch and never gate anything.
    """
    seats = len(models)
    rounds = max(1, int(rounds))
    source_tokens = max(1, source_bytes // _EST_BYTES_PER_TOKEN)
    out_lo, out_hi = _EST_REVIEW_OUT_TOKENS

    # Cross-reading adds each peer's round-(N-1) review to every round-2+ packet.
    peers = max(0, seats - 1)
    if cross_reading == "full":
        cross_lo, cross_hi = peers * out_lo, peers * out_hi
    elif cross_reading == "none":
        cross_lo = cross_hi = 0
    else:   # summaries (the default)
        cross_lo = cross_hi = peers * _EST_SUMMARY_TOKENS

    base_in = source_tokens + _EST_PROMPT_OVERHEAD_TOKENS
    per_seat_in_lo = base_in * rounds + cross_lo * (rounds - 1)
    per_seat_in_hi = base_in * rounds + cross_hi * (rounds - 1)
    per_seat_out_lo, per_seat_out_hi = out_lo * rounds, out_hi * rounds

    tokens_low = seats * (per_seat_in_lo + per_seat_out_lo)
    tokens_high = seats * (per_seat_in_hi + per_seat_out_hi)

    cost_low = cost_high = 0.0
    priced_any = False
    unpriced = []
    for model in models:
        prices = MODEL_PRICING_USD_PER_MTOK.get(model)
        if not prices or prices[0] is None or prices[1] is None:
            if model not in unpriced:
                unpriced.append(model)
            continue
        p_in, p_out = prices
        cost_low += (per_seat_in_lo * p_in + per_seat_out_lo * p_out) / 1_000_000
        cost_high += (per_seat_in_hi * p_in + per_seat_out_hi * p_out) / 1_000_000
        priced_any = True

    m_lo, m_hi = _EST_MINUTES_PER_ROUND
    return {
        "seats": seats,
        "rounds": rounds,
        "cross_reading": cross_reading,
        "tokens_low": tokens_low,
        "tokens_high": tokens_high,
        "cost_low_usd": cost_low if priced_any else None,
        "cost_high_usd": cost_high if priced_any else None,
        "cost_is_partial": priced_any and bool(unpriced),
        "unpriced_models": unpriced,
        "minutes_low": rounds * m_lo,
        "minutes_high": rounds * m_hi,
    }


def render_estimate(est: dict) -> list:
    """Human lines for an estimate_run() result — explicit estimate wording."""
    lines = [
        f"tokens  : ~{est['tokens_low']:,}–{est['tokens_high']:,} across the board "
        f"({est['seats']} seat(s) × {est['rounds']} round(s), cross-reading: {est['cross_reading']})",
    ]
    if est["cost_low_usd"] is None:
        lines.append("cost    : unknown — no verified list price for "
                     f"{', '.join(est['unpriced_models'])} (see constants.MODEL_PRICING_USD_PER_MTOK)")
    else:
        partial = ""
        if est["cost_is_partial"]:
            partial = f"  (excludes unpriced: {', '.join(est['unpriced_models'])})"
        lines.append(f"cost    : ~${est['cost_low_usd']:.2f}–${est['cost_high_usd']:.2f} "
                     f"at list prices dated {PRICING_AS_OF}{partial}")
    lines.append(f"time    : roughly {est['minutes_low']:.0f}–{est['minutes_high']:.0f} minutes "
                 "(seats run in parallel; deep reasoning rounds vary widely)")
    lines.append("These are ESTIMATES, not measurements or a gate — subscription-backed CLIs "
                 "may bill nothing per token; actuals land in run-metadata after the run.")
    return lines


def die(message: str, code: int = EXIT_USAGE) -> "NoReturn":  # type: ignore[name-defined]
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def now_date() -> str:
    """Today's date (YYYY-MM-DD), overridable via env for deterministic tests."""
    return os.environ.get("ADVISORY_BOARD_NOW") or date.today().isoformat()


def now_stamp() -> str:
    """ISO timestamp, overridable via env for deterministic tests/goldens."""
    return os.environ.get("ADVISORY_BOARD_NOW_TS") or datetime.now().isoformat(timespec="seconds")

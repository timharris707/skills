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
    "EXIT_OK",
    "EXIT_PREFLIGHT_NOGO",
    "EXIT_USAGE",
    "EXIT_EGRESS_BLOCKED",
    "PROVIDERS",
    "LENS_PRESETS",
    "DEFAULT_LENS",
    "FAILURE_TIMEOUT",
    "FAILURE_AUTH",
    "FAILURE_INVALID",
    "FAILURE_NOOUTPUT",
    "FAILURE_MODEL",
    "die",
    "now_date",
    "now_stamp",
]


RECIPE_SCHEMA = "advisory-board/run-recipe@1"
SENSITIVITY_SCHEMA = "advisory-board/sensitivity@1"
SMOKE_PROMPT = "Reply with the single word: ready"

# Exit codes (distinct so callers / CI can branch).
EXIT_OK = 0
EXIT_PREFLIGHT_NOGO = 1   # fewer than two seats GO, or a delegated gate failed
EXIT_USAGE = 2            # bad arguments / config / IO
EXIT_EGRESS_BLOCKED = 3   # consent not granted, or sensitivity forbids egress

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

# Failure classes (design §13). Tool-agnostic; consumed in full by M3.
FAILURE_TIMEOUT = "Timeout"
FAILURE_AUTH = "AuthFailure"
FAILURE_INVALID = "InvalidOutput"
FAILURE_NOOUTPUT = "NoOutput"
FAILURE_MODEL = "ModelNotFound"   # pinned model id did not resolve on the installed CLI


def die(message: str, code: int = EXIT_USAGE) -> "NoReturn":  # type: ignore[name-defined]
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def now_date() -> str:
    """Today's date (YYYY-MM-DD), overridable via env for deterministic tests."""
    return os.environ.get("ADVISORY_BOARD_NOW") or date.today().isoformat()


def now_stamp() -> str:
    """ISO timestamp, overridable via env for deterministic tests/goldens."""
    return os.environ.get("ADVISORY_BOARD_NOW_TS") or datetime.now().isoformat(timespec="seconds")

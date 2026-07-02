"""Verdict delta (v1.12 #1) — PURE mechanical matching of verdict-moving items
across two runs of the same material.

Given the prior run's verdict and the new run's verdict, classify every blocker
and concern as cleared (was raised before, not raised now), still-open (raised
in both), or new (raised now only), plus the verdict trajectory (prior token →
new token). Matching is mechanical only (§11 — the conductor plumbs, the models
reason): exact normalized title, then shared concrete citations, then stdlib
sequence similarity on titles. No meaning clustering, ever — a reworded finding
with no shared citation and a dissimilar title counts as cleared+new, and the
renderer shows both lists so a human can see exactly that.
"""
from __future__ import annotations

from difflib import SequenceMatcher

__all__ = [
    "DELTA_CONTAINERS",
    "TITLE_SIMILARITY_FLOOR",
    "verdict_delta",
]

# The verdict-moving containers the delta classifies. Dissent is deliberately
# excluded: it is attributed to a seat, not to the material, so "cleared
# dissent" would misread a seat changing its mind as the draft improving.
DELTA_CONTAINERS = ("blockers", "concerns")

# Match tier 3: difflib.SequenceMatcher ratio on normalized titles. 0.75 keeps
# small rewordings ("Atomic dedup claim" ~ "Atomic dedup") matched while two
# genuinely different findings stay apart. Mechanical, deterministic, stdlib.
TITLE_SIMILARITY_FLOOR = 0.75


def _norm_title(item: dict) -> str:
    title = item.get("title") if isinstance(item, dict) else None
    if not isinstance(title, str):
        return ""
    return " ".join(title.casefold().split())


def _citation_refs(item: dict) -> set:
    """The item's concrete citations as comparable tokens. Only referents
    precise enough to identify a FINDING, not just a file: code path:line /
    path#symbol, source url, command string. A bare path is emitted only when
    the evidence carries no line/symbol at all — otherwise every finding in a
    single-file review would "share" a citation and the delta would collapse
    into all-still-open. `judgment` evidence has no referent, by design."""
    refs = set()
    if not isinstance(item, dict):
        return refs
    evidence = item.get("evidence")
    if not isinstance(evidence, list):
        return refs
    for ev in evidence:
        if not isinstance(ev, dict):
            continue
        kind = ev.get("kind")
        if kind == "code" and isinstance(ev.get("path"), str):
            has_line = isinstance(ev.get("line"), int) and not isinstance(ev.get("line"), bool)
            has_symbol = isinstance(ev.get("symbol"), str) and ev["symbol"].strip()
            if has_line:
                refs.add(f"code:{ev['path']}:{ev['line']}")
            if has_symbol:
                refs.add(f"code:{ev['path']}#{ev['symbol']}")
            if not has_line and not has_symbol:
                refs.add(f"code:{ev['path']}")
        elif kind == "source" and isinstance(ev.get("url"), str):
            refs.add(f"source:{ev['url']}")
        elif kind == "command" and isinstance(ev.get("command"), str):
            refs.add(f"command:{' '.join(ev['command'].split())}")
    return refs


def _titles_similar(a: str, b: str) -> bool:
    """Tier-3 similarity: char-level ratio >= floor AND at least one shared
    substantive token (len >= 4). The token guard keeps template-shaped titles
    ("Fix X" / "Fix Y") apart; genuinely-different-but-parallel titles can
    still collide — a documented mechanical limit, and the renderer shows both
    lists so a human can see exactly what paired."""
    if not a or not b:
        return False
    if SequenceMatcher(None, a, b).ratio() < TITLE_SIMILARITY_FLOOR:
        return False
    shared = set(t for t in a.split() if len(t) >= 4) & \
        set(t for t in b.split() if len(t) >= 4)
    return bool(shared)


def _tier_title(prior_item: dict, candidate: dict) -> bool:
    p = _norm_title(prior_item)
    return bool(p) and _norm_title(candidate) == p


def _tier_citation(prior_item: dict, candidate: dict) -> bool:
    p_refs = _citation_refs(prior_item)
    return bool(p_refs) and bool(p_refs & _citation_refs(candidate))


def _tier_similar(prior_item: dict, candidate: dict) -> bool:
    return _titles_similar(_norm_title(prior_item), _norm_title(candidate))


# Matching runs as GLOBAL tier passes (every exact-title match board-wide, then
# citations over the remainder, then similarity) — never per-prior-item tier
# descent, where an earlier item's fuzzy match could steal a later item's exact
# match. Within a tier: prior order, then candidate order — deterministic.
_MATCH_TIERS = (("title", _tier_title), ("citation", _tier_citation),
                ("similar-title", _tier_similar))


def _items(verdict: dict, container: str) -> list:
    items = verdict.get(container) if isinstance(verdict, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def verdict_delta(prior: dict, current: dict) -> dict:
    """The mechanical delta between two verdicts.

    Returns:
      {
        "trajectory": {"from": <prior verdict token>, "to": <new verdict token>},
        "blockers":  {"cleared": [...], "still_open": [...], "new": [...]},
        "concerns":  {"cleared": [...], "still_open": [...], "new": [...]},
      }
    cleared/new entries are the original item dicts (prior-run dicts for
    cleared, current-run dicts for new); still_open entries are
    {"prior": <dict>, "current": <dict>, "matched_by": "title|citation|similar-title"}.
    Each current item matches at most one prior item; matching runs as global
    tier passes so an exact title always beats a fuzzy pairing.
    """
    out = {
        "trajectory": {
            "from": prior.get("verdict") if isinstance(prior, dict) else None,
            "to": current.get("verdict") if isinstance(current, dict) else None,
        },
    }
    for container in DELTA_CONTAINERS:
        prior_items = _items(prior, container)
        remaining = _items(current, container)
        matches = {}   # prior index -> (current item, tier name)
        for tier_name, tier_fn in _MATCH_TIERS:
            for p_index, prior_item in enumerate(prior_items):
                if p_index in matches:
                    continue
                for c_index, candidate in enumerate(remaining):
                    if tier_fn(prior_item, candidate):
                        matches[p_index] = (remaining.pop(c_index), tier_name)
                        break
        cleared = [item for index, item in enumerate(prior_items)
                   if index not in matches]
        still_open = [{"prior": prior_items[index],
                       "current": matches[index][0],
                       "matched_by": matches[index][1]}
                      for index in sorted(matches)]
        out[container] = {"cleared": cleared, "still_open": still_open,
                          "new": remaining}
    return out

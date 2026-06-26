"""The restricted-YAML codec for run-recipe.yaml plus the recipe<->config
conversion and validation."""
from __future__ import annotations

import json
from typing import Optional

from _conductor.constants import (
    RECIPE_SCHEMA,
    die,
)
from _conductor.registry import REGISTRY
from _conductor.config import RunConfig
from _conductor.prompts import (
    PROMPT_TEMPLATE_VERSION,
    prompt_template_sha,
)
from _conductor.synthesizer import (
    SYNTHESIZER_TEMPLATE_VERSION,
    synthesizer_template_sha,
)

__all__ = [
    "_scalar_to_yaml",
    "_looks_numeric",
    "_scalar_from_yaml",
    "dump_recipe",
    "load_recipe",
    "RECIPE_COMMENTS",
    "config_to_recipe",
    "_RECIPE_ENUMS",
    "validate_recipe",
    "recipe_to_config",
]


# Restricted YAML codec for run-recipe.yaml.
#
# stdlib only -> no PyYAML. We emit and consume a deliberately small, regular
# subset: top-level `key: scalar`, top-level `key:` followed by a list of
# scalars, and top-level `key:` followed by a list of mappings (each mapping has
# scalar children only). That is exactly what the recipe needs and nothing more.
# Contract: load_recipe() consumes recipes produced by dump_recipe(); it is not a
# general YAML parser. Round-trip is covered by tests.
#
# Quoted scalars use JSON string encoding (json.dumps/json.loads): a YAML
# double-quoted flow scalar is JSON-compatible, so this round-trips embedded
# newlines, tabs, quotes, and backslashes losslessly and is read identically by a
# real YAML reader. This closes the "the tool emits a file it cannot read back"
# class of bug for values like a multi-line --title.


def _scalar_to_yaml(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if value is None:
        return "null"
    text = str(value)
    needs_quote = (
        text == ""
        or text.strip() != text
        or text[:1] in "#&*!|>%@`\"'[]{},"
        or ": " in text
        or text.endswith(":")
        or any(ord(c) < 0x20 for c in text)   # control chars (newline, tab, CR ...)
        # Reserved words a YAML 1.1 reader (e.g. PyYAML) would coerce to bool/null;
        # quote them so the recipe means the same string to any parser.
        or text.lower() in ("true", "false", "null", "yes", "no", "on", "off", "~")
        or _looks_numeric(text)
    )
    if needs_quote:
        return json.dumps(text, ensure_ascii=False)
    return text


def _looks_numeric(text: str) -> bool:
    try:
        int(text)
        return True
    except ValueError:
        pass
    try:
        float(text)
        return True
    except ValueError:
        return False


def _scalar_from_yaml(token: str):
    token = token.strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        try:
            return json.loads(token)
        except json.JSONDecodeError:
            return token[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
        return token[1:-1].replace("''", "'")   # tolerate hand-edited single quotes
    if token in ("true", "false"):
        return token == "true"
    if token == "null":
        return None
    try:
        return int(token)
    except ValueError:
        pass
    return token


def dump_recipe(recipe: dict, *, comments: Optional[dict] = None) -> str:
    """Serialize a recipe dict to the restricted YAML subset.

    comments maps a key -> a comment line emitted just before that key (used for
    human-readable section grouping; ignored on load).
    """
    comments = comments or {}
    lines: list = []
    for key, value in recipe.items():
        if key in comments:
            lines.append("")
            lines.append(f"# {comments[key]}")
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    first = True
                    for k, v in item.items():
                        prefix = "  - " if first else "    "
                        lines.append(f"{prefix}{k}: {_scalar_to_yaml(v)}")
                        first = False
                    if not item:
                        lines.append("  - {}")
                else:
                    lines.append(f"  - {_scalar_to_yaml(item)}")
        else:
            lines.append(f"{key}: {_scalar_to_yaml(value)}")
    return "\n".join(lines) + "\n"


def load_recipe(text: str) -> dict:
    """Parse the restricted YAML subset produced by dump_recipe()."""
    rows: list = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        rows.append((indent, raw.rstrip()))

    result: dict = {}
    i = 0
    n = len(rows)
    while i < n:
        indent, content = rows[i]
        if indent != 0:
            die(f"run-recipe: unexpected indentation at {content.strip()!r}")
        stripped = content.strip()
        if ":" not in stripped:
            die(f"run-recipe: expected 'key: value' at {stripped!r}")
        key, _, inline = stripped.partition(":")
        key = key.strip()
        inline = inline.strip()
        if inline:
            result[key] = _scalar_from_yaml(inline)
            i += 1
            continue
        # Block value: a list of scalars or a list of mappings.
        items: list = []
        i += 1
        while i < n and rows[i][0] > 0:
            child_indent, child = rows[i]
            child = child.strip()
            if not child.startswith("- "):
                die(f"run-recipe: expected list item under {key!r}, got {child!r}")
            body = child[2:].strip()
            if ":" in body and not (body.startswith('"') and body.endswith('"')):
                # Mapping item: this line is its first key; deeper non-'- ' lines continue it.
                mapping: dict = {}
                mk, _, mv = body.partition(":")
                mapping[mk.strip()] = _scalar_from_yaml(mv.strip())
                i += 1
                while i < n and rows[i][0] > child_indent and not rows[i][1].strip().startswith("- "):
                    cont = rows[i][1].strip()
                    ck, _, cv = cont.partition(":")
                    mapping[ck.strip()] = _scalar_from_yaml(cv.strip())
                    i += 1
                items.append(mapping)
            else:
                items.append(_scalar_from_yaml(body))
                i += 1
        result[key] = items
    return result


# Recipe <-> config

RECIPE_COMMENTS = {
    "mode": "run shape",
    "prompt_template": "prompt template (bump/hash changes when the egressed prompt shape changes)",
    "synthesize": "synthesizer (M2): spawn a no-lens seat after rounds to draft verdict.json",
    "source_kind": "source",
    "board": "board (seat -> provider, model, lens, reasoning)",
    "egress_consent": "egress (consent is bound to the content hash in egress-manifest.md)",
    "isolation_network": "isolation posture (follows mode); 'partial' = some seats not network-isolated",
}


def config_to_recipe(config: RunConfig) -> dict:
    unenforced = config.unenforced_network_seats
    if config.network_on:
        network = "on"
    elif unenforced:
        network = "partial"   # gate mode, but at least one seat cannot be network-isolated
    else:
        network = "off"
    recipe = {
        "schema": RECIPE_SCHEMA,
        "title": config.title,
        "date": config.date,
        "mode": config.mode,
        "sensitivity": config.sensitivity,
        "rounds": config.rounds,
        "max_rounds": config.max_rounds,
        "cross_reading": config.cross_reading,
        "lens": config.lens,
        "output": config.output,
        "out_dir": config.out_dir,
        "prompt_template": PROMPT_TEMPLATE_VERSION,
        "prompt_template_sha256": prompt_template_sha(),
        "synthesize": config.synthesize,
        "synthesizer_seat": config.synthesizer_seat,
        "synthesizer_template": SYNTHESIZER_TEMPLATE_VERSION if config.synthesize else None,
        "synthesizer_template_sha256": synthesizer_template_sha() if config.synthesize else None,
        "source_kind": config.source.kind,
        "source_ref": config.source.ref,
        "source_bytes": config.source.nbytes,
        "source_lines": config.source.nlines,
        "source_sha256": config.source.sha256,
        "board": [
            {
                "seat": seat.name,
                "provider": seat.provider,
                "model": seat.model,
                "lens": seat.lens,
                "reasoning": seat.reasoning,
            }
            for seat in config.board
        ],
        "egress_consent": "tiered",
        "egress_providers": [
            f"{seat.name} seat -> {seat.provider}" for seat in config.board
        ],
        "isolation_network": network,
        "isolation_network_unenforced": unenforced,
        "isolation_filesystem": "scoped" if config.fs_scoped else "open",
    }
    # Repo-grounding: persist the scope so `--from-recipe` reproduces a grounded run.
    # Only added when grounding is on, so ungrounded recipes stay byte-identical.
    if config.repo:
        recipe["repo"] = config.repo
        if config.repo_include:
            recipe["repo_include"] = list(config.repo_include)
        if config.repo_exclude:
            recipe["repo_exclude"] = list(config.repo_exclude)
    return recipe


_RECIPE_ENUMS = {
    "mode": ("gate", "advisory"),
    "sensitivity": ("public", "redacted", "local-only"),
    "rounds": ("1", "2", "3", "auto"),
    "cross_reading": ("none", "summaries", "full"),
}


def validate_recipe(recipe: dict) -> None:
    """Structural validation for --from-recipe: a malformed recipe must fail with
    a precise error and EXIT_USAGE, never a raw traceback."""
    if recipe.get("schema") != RECIPE_SCHEMA:
        die(f"recipe schema must be {RECIPE_SCHEMA!r}; got {recipe.get('schema')!r}")
    ref = recipe.get("source_ref")
    if not isinstance(ref, str) or not ref.strip():
        die("recipe: 'source_ref' must be a non-empty string")
    board = recipe.get("board")
    if not isinstance(board, list) or not board:
        die("recipe: 'board' must be a non-empty list of seats")
    for index, seat in enumerate(board):
        if not isinstance(seat, dict):
            die(f"recipe: board[{index}] must be a mapping (seat/model/...)")
        name = seat.get("seat")
        if not isinstance(name, str) or name not in REGISTRY:
            die(f"recipe: board[{index}].seat must be one of {', '.join(sorted(REGISTRY))}; got {name!r}")
        if "model" in seat and not isinstance(seat["model"], str):
            die(f"recipe: board[{index}].model must be a string")
    for key, allowed in _RECIPE_ENUMS.items():
        if key in recipe and str(recipe[key]) not in allowed:
            die(f"recipe: {key} must be one of {', '.join(allowed)}; got {recipe[key]!r}")
    if "max_rounds" in recipe:
        mr = recipe["max_rounds"]
        if not isinstance(mr, int) or isinstance(mr, bool) or mr < 1:
            die(f"recipe: 'max_rounds' must be an integer >= 1; got {mr!r}")
    if "synthesize" in recipe and not isinstance(recipe["synthesize"], bool):
        die(f"recipe: 'synthesize' must be true or false; got {recipe['synthesize']!r}")
    if recipe.get("synthesizer_seat") is not None:
        ss = recipe["synthesizer_seat"]
        if not isinstance(ss, str) or ss not in REGISTRY:
            die(f"recipe: 'synthesizer_seat' must be one of {', '.join(sorted(REGISTRY))} or null; "
                f"got {ss!r}")
        # The synth seat must also be in THIS recipe's board (same rule as
        # resolve_config — egress to a board provider only).
        board_names = {s.get("seat") for s in board if isinstance(s, dict)}
        if ss not in board_names:
            pretty = ", ".join(sorted(n for n in board_names if isinstance(n, str)))
            die(f"recipe: 'synthesizer_seat' {ss!r} is not in this recipe's board "
                f"({pretty}); the synthesizer egresses to that seat's provider, which "
                "the run's disclosure only covers for board seats")
    # Repo-grounding fields (optional; present only for a grounded recipe).
    if "repo" in recipe and not (isinstance(recipe["repo"], str) and recipe["repo"].strip()):
        die(f"recipe: 'repo' must be a non-empty string path; got {recipe['repo']!r}")
    for key in ("repo_include", "repo_exclude"):
        if key in recipe:
            val = recipe[key]
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                die(f"recipe: '{key}' must be a list of glob strings; got {val!r}")


def recipe_to_config(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            recipe = load_recipe(handle.read())
    except FileNotFoundError:
        die(f"recipe not found: {path}")
    validate_recipe(recipe)
    return recipe

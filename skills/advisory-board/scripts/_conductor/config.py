"""Config resolution (design §4, §10): the SourceSpec/SeatConfig/RunConfig
dataclasses and everything that turns CLI args (or a recipe) into a RunConfig."""
from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from _conductor.grounding import GroundingContext

from _conductor.constants import (
    DEFAULT_LENS,
    DEFAULT_MAX_ROUNDS,
    LENS_PRESETS,
    die,
    now_date,
    now_stamp,
)
from _conductor.registry import (
    REGISTRY,
    SeatAdapter,
)

__all__ = [
    "SourceSpec",
    "SeatConfig",
    "RunConfig",
    "load_source",
    "_source_from_text",
    "resolve_board",
    "default_out_dir",
    "resolve_config",
    "derive_title",
    "parse_board",
    "parse_model_overrides",
]


@dataclass
class SourceSpec:
    kind: str            # path | url | stdin
    ref: str
    text: str
    nbytes: int
    nlines: int
    sha256: str


@dataclass
class SeatConfig:
    id: str              # unique per-seat identity (alias, or provider[#N]) — the run's key:
                         # filesystem paths, dicts, cross-reading, render, dissent attribution
    name: str            # provider/registry name (claude/codex/gemini) — adapter + egress provider
    adapter: SeatAdapter
    model: str
    lens: str
    reasoning: str

    @property
    def provider(self) -> str:
        return self.adapter.provider

    @property
    def label(self) -> str:
        """Human display label. For a bare unique seat this is just the provider
        (e.g. "Claude"); for an alias or an auto-numbered duplicate it disambiguates
        (e.g. "econ" / "Claude #2")."""
        if self.id == self.name:
            return self.name.capitalize()
        if self.id.startswith(f"{self.name}#"):
            return f"{self.name.capitalize()} #{self.id.split('#', 1)[1]}"
        return self.id


@dataclass
class RunConfig:
    title: str
    date: str
    source: SourceSpec
    mode: str            # gate | advisory
    sensitivity: str     # public | redacted | local-only
    rounds: str          # 1 | 2 | 3 | auto
    max_rounds: int      # hard ceiling for `auto` (ignored for an explicit 1|2|3)
    cross_reading: str   # none | summaries | full
    lens: str            # preset name
    output: str          # quick-verdict | full-handoff | implementation-sequence
    out_dir: str
    board: list          # list[SeatConfig]
    network_on: bool     # isolation: network
    fs_scoped: bool      # isolation: filesystem scoped
    synthesize: bool = False         # M2: spawn the neutral synthesizer after rounds
    synthesizer_seat: Optional[str] = None   # which board seat's adapter runs it
    repo: Optional[str] = None       # repo-grounding: a local repo seats may read (read-only)
    repo_include: Optional[list] = None   # optional fnmatch globs narrowing the grounding scope
    repo_exclude: Optional[list] = None   # optional fnmatch globs removed from the grounding scope
    # Runtime-populated (NOT by resolve_config): the resolved+snapshotted+hashed read
    # surface, computed once at pre-spawn (cli.cmd_run) so every consent surface reads
    # one source of truth. None until then, and always None for an ungrounded run.
    grounding: "Optional[GroundingContext]" = None

    @property
    def grounded(self) -> bool:
        """True when repo-grounding is on — seats read a read-only snapshot of `repo`."""
        return bool(self.repo)

    @property
    def gate_mode(self) -> bool:
        return self.mode == "gate"

    @property
    def unenforced_network_seats(self) -> list:
        """Gate-mode seats whose network the conductor CANNOT actually remove.

        These are seats the consent surface must NOT claim as network-isolated
        (today: gemini — no flag disables GoogleSearch grounding). Empty in
        advisory mode (grounding is intentional there).
        """
        if not self.gate_mode:
            return []
        return [s.id for s in self.board if not s.adapter.isolates_network]


def load_source(ref: str) -> SourceSpec:
    if ref == "-":
        text = sys.stdin.read()
        return _source_from_text("stdin", "-", text)
    if ref.startswith(("http://", "https://")):
        # v1 does not fetch URLs (that reintroduces network before the egress
        # gate). Record the URL as the source ref; the user supplies the bytes.
        die("URL sources are not fetched in v1 (would egress before the gate); "
            "download the page and pass the file path instead")
    if not os.path.isfile(ref):
        die(f"source not found: {ref}")
    try:
        with open(ref, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        die(f"cannot read source {ref}: {exc}")
    return _source_from_text("path", ref, text)


def _source_from_text(kind: str, ref: str, text: str) -> SourceSpec:
    data = text.encode("utf-8")
    return SourceSpec(
        kind=kind,
        ref=ref,
        text=text,
        nbytes=len(data),
        nlines=text.count("\n") + (1 if text and not text.endswith("\n") else 0),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def assign_seat_ids(seat_specs: list) -> list:
    """Turn parsed board entries [(alias|None, provider), ...] into unique ids.

    An alias is the id verbatim. A bare provider keeps its name as the id unless that
    provider is bare-repeated, in which case the repeats are numbered provider#1, #2…
    in board order. So a unique-provider board (claude,codex,gemini) keeps id==name —
    byte-identical to the pre-feature behavior. Returns [(id, provider), ...]."""
    bare_total: dict = {}
    for alias, provider in seat_specs:
        if alias is None:
            bare_total[provider] = bare_total.get(provider, 0) + 1
    bare_seen: dict = {}
    out = []
    for alias, provider in seat_specs:
        if alias is not None:
            sid = alias
        elif bare_total.get(provider, 0) > 1:
            bare_seen[provider] = bare_seen.get(provider, 0) + 1
            sid = f"{provider}#{bare_seen[provider]}"
        else:
            sid = provider
        out.append((sid, provider))
    return out


def resolve_board(seat_specs: list, lens_preset: str, model_overrides: dict,
                  lens_overrides: Optional[dict] = None) -> list:
    lenses = LENS_PRESETS.get(lens_preset)
    if lenses is None:
        die(f"unknown lens preset {lens_preset!r}; choose from {', '.join(sorted(LENS_PRESETS))}")
    lens_overrides = lens_overrides or {}
    ids = assign_seat_ids(seat_specs)
    # Uniqueness guard — replaces today's SILENT collapse of two same-named seats with a
    # loud failure. Only reachable when a user aliases two seats identically (auto-numbering
    # can't collide); we surface it rather than overwrite one seat's artifacts/board entry.
    seen: set = set()
    for sid, _ in ids:
        if sid in seen:
            die(f"duplicate seat id {sid!r}; give each seat a distinct alias (alias=provider)")
        seen.add(sid)
    # An override that targets a seat that isn't on the board is almost always a typo or a
    # stale id — fail loudly rather than silently ignore it (the old behavior). A bare
    # provider name is a valid target only when that provider is the seat's id (unique board).
    for kind, keys in (("--model", model_overrides), ("--lens", lens_overrides)):
        for key in keys:
            if key not in seen:
                die(f"{kind} targets seat {key!r}, which isn't on the board "
                    f"({', '.join(sorted(seen))})")
    board: list = []
    for index, (sid, provider) in enumerate(ids):
        adapter = REGISTRY.get(provider)
        if adapter is None:
            die(f"unknown seat {provider!r}; known seats: {', '.join(sorted(REGISTRY))}")
        # Lens: an explicit per-seat override (by id) wins; else the preset's positional
        # default (slot i → lens i; seats past the trio reuse the last focus).
        lens = lens_overrides.get(sid) or (lenses[index] if index < len(lenses) else lenses[-1])
        board.append(SeatConfig(
            id=sid,
            name=provider,
            adapter=adapter,
            # Model override is keyed by id; a bare provider name == its id when unique,
            # so `--model claude=…` still works for a single-Claude board.
            model=model_overrides.get(sid, adapter.default_model),
            lens=lens,
            reasoning=adapter.default_reasoning,
        ))
    return board


def default_out_dir() -> str:
    stamp = now_stamp().replace(":", "").replace("-", "").replace("T", "-")
    return os.path.join("/tmp", f"advisory-board-{stamp}")


def resolve_config(args) -> RunConfig:
    # Deferred import: resolve_config is the one config->recipe edge;
    # importing at module scope would create a config<->recipe cycle.
    from _conductor.recipe import recipe_to_config
    model_overrides = parse_model_overrides(getattr(args, "model", []) or [])

    if getattr(args, "from_recipe", None):
        base = recipe_to_config(args.from_recipe)
    else:
        base = None

    lens_overrides: dict = {}
    if base is not None and not getattr(args, "source", None):
        source = load_source(base["source_ref"])
        # Reconstruct the exact board from the recipe. Each entry's "seat" is the seat id
        # and "registry" (when present) is its REGISTRY key; a default/auto-numbered seat
        # restores as a bare provider so its id re-derives deterministically, while a true
        # alias restores as alias=provider. Per-seat models and lenses are restored so a
        # duplicate-seat / per-seat-lens run reproduces exactly; an explicit CLI --model wins.
        seat_specs = []
        for entry in base["board"]:
            sid = entry["seat"]
            registry = entry.get("registry", sid)
            if registry == sid or re.match(rf"^{re.escape(registry)}#\d+$", sid):
                seat_specs.append((None, registry))
            else:
                seat_specs.append((sid, registry))
            model_overrides.setdefault(sid, entry["model"])
            if entry.get("lens"):
                lens_overrides.setdefault(sid, entry["lens"])
        lens_preset = base.get("lens", DEFAULT_LENS)
    else:
        if not getattr(args, "source", None):
            die("a --source is required (PATH, or - for stdin)")
        source = load_source(args.source)
        seat_specs = parse_board(getattr(args, "board", None))
        board_preset, lens_overrides = parse_lens_args(getattr(args, "lens", None))
        lens_preset = board_preset or (base or {}).get("lens", DEFAULT_LENS)

    board = resolve_board(seat_specs, lens_preset, model_overrides, lens_overrides)

    mode = getattr(args, "mode", None) or (base or {}).get("mode") or "gate"
    if mode not in ("gate", "advisory"):
        die(f"--mode must be gate or advisory; got {mode!r}")

    sensitivity = getattr(args, "sensitivity", None) or (base or {}).get("sensitivity") or "redacted"
    if sensitivity not in ("public", "redacted", "local-only"):
        die(f"--sensitivity must be public, redacted, or local-only; got {sensitivity!r}")

    rounds = str(getattr(args, "rounds", None) or (base or {}).get("rounds") or "2")
    if rounds not in ("1", "2", "3", "auto"):
        die(f"--rounds must be 1, 2, 3, or auto; got {rounds!r}")

    # The `auto` ceiling. Persisted in the recipe (so an `auto` run reproduces its
    # ceiling via --from-recipe); a CLI --max-rounds wins, else the recipe's, else
    # the default. Ignored at runtime for an explicit --rounds 1|2|3.
    max_rounds_raw = getattr(args, "max_rounds", None)
    if max_rounds_raw is None:
        max_rounds_raw = (base or {}).get("max_rounds")
    try:
        max_rounds = int(max_rounds_raw) if max_rounds_raw is not None else DEFAULT_MAX_ROUNDS
    except (TypeError, ValueError):
        die(f"--max-rounds must be an integer; got {max_rounds_raw!r}")
    if max_rounds < 1:
        die(f"--max-rounds must be >= 1; got {max_rounds}")

    cross = getattr(args, "cross_reading", None) or (base or {}).get("cross_reading") or "summaries"
    if cross not in ("none", "summaries", "full"):
        die(f"--cross-reading must be none, summaries, or full; got {cross!r}")

    output = getattr(args, "output", None) or (base or {}).get("output") or "full-handoff"

    out_dir = getattr(args, "out", None) or (base or {}).get("out_dir") or default_out_dir()

    title = getattr(args, "title", None) or (base or {}).get("title") or derive_title(source)

    # Mode decides the quarantine posture (design §4). Gate: network off, fs
    # scoped. Advisory (opt-in, your own non-sensitive material): grounding on.
    network_on = (mode == "advisory")
    fs_scoped = (mode == "gate")

    # M2 synthesizer. CLI flag wins; otherwise the recipe re-runs as authored.
    # Both flag and recipe being false → manual hand-off (the v1 default).
    cli_synthesize = bool(getattr(args, "synthesize", False))
    recipe_synthesize = bool((base or {}).get("synthesize"))
    synthesize = cli_synthesize or recipe_synthesize
    synthesizer_seat = (getattr(args, "synthesizer_seat", None)
                        or (base or {}).get("synthesizer_seat"))
    if synthesizer_seat is not None:
        # The synthesizer egresses to its seat's provider, which the run's
        # disclosure only covers when that seat is ON the board. Reject HERE so we
        # don't spend rounds before realizing the choice is invalid — and so the
        # dry-run run-card doesn't lie about a synth seat the run would refuse.
        if synthesizer_seat not in REGISTRY:
            die(f"--synthesizer-seat must be a registered seat ({', '.join(sorted(REGISTRY))}); "
                f"got {synthesizer_seat!r}")
        board_names = {s.name for s in board}
        if synthesizer_seat not in board_names:
            die(f"--synthesizer-seat {synthesizer_seat!r} is not one of this run's board seats "
                f"({', '.join(sorted(board_names))}); the synthesizer egresses to that seat's "
                "provider, which the run's disclosure only covers for board seats")

    # Repo-grounding (design/run-board-repo-grounding.md): a local repo seats may
    # read read-only. Resolved + validated as a directory here; the scope/snapshot
    # and the consent/network safety policy are applied at run time (P2/P3).
    repo = getattr(args, "repo", None) or (base or {}).get("repo")
    if repo is not None:
        repo = os.path.abspath(os.path.expanduser(repo))
        if not os.path.isdir(repo):
            die(f"--repo is not a directory: {repo}")
    repo_include = getattr(args, "repo_include", None) or (base or {}).get("repo_include") or None
    repo_exclude = getattr(args, "repo_exclude", None) or (base or {}).get("repo_exclude") or None

    return RunConfig(
        title=title,
        date=now_date(),
        source=source,
        mode=mode,
        sensitivity=sensitivity,
        rounds=rounds,
        max_rounds=max_rounds,
        cross_reading=cross,
        lens=lens_preset,
        output=output,
        out_dir=out_dir,
        board=board,
        network_on=network_on,
        fs_scoped=fs_scoped,
        synthesize=synthesize,
        synthesizer_seat=synthesizer_seat,
        repo=repo,
        repo_include=repo_include,
        repo_exclude=repo_exclude,
    )


def derive_title(source: SourceSpec) -> str:
    if source.kind == "path":
        stem = os.path.splitext(os.path.basename(source.ref))[0]
        return stem.replace("-", " ").replace("_", " ").strip() or "Advisory board review"
    first = source.text.strip().splitlines()[0] if source.text.strip() else ""
    return (first[:60] or "Advisory board review").strip()


# An alias is a user-chosen seat id; it becomes a filesystem path component and a CLI
# target, so it is restricted to safe chars and must not contain '#' (reserved for the
# provider#N auto-numbering convention).
_ALIAS_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def parse_board(value: Optional[str]) -> list:
    """Parse --board into [(alias|None, provider), ...] in board order.

    Each comma-separated entry is either a bare `provider` (claude/codex/gemini) or an
    `alias=provider` (a user-named seat). The default board is the three providers, bare."""
    if not value:
        return [(None, "claude"), (None, "codex"), (None, "gemini")]
    specs: list = []
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        if "=" in item:
            alias, _, provider = item.partition("=")
            alias, provider = alias.strip(), provider.strip()
            if not alias or not provider:
                die(f"--board entry {item!r} must be alias=provider")
            if not _ALIAS_RE.match(alias):
                die(f"--board alias {alias!r} must be alphanumeric (A-Z a-z 0-9 . _ -) and "
                    "may not contain '#'")
        else:
            alias, provider = None, item
        specs.append((alias, provider))
    if not specs:
        die("--board must list at least one seat")
    return specs


def parse_model_overrides(pairs: list) -> dict:
    overrides: dict = {}
    for pair in pairs:
        if "=" not in pair:
            die(f"--model expects seat=model_id; got {pair!r}")
        seat, _, model = pair.partition("=")
        overrides[seat.strip()] = model.strip()
    return overrides


def _resolve_seat_lens(value: str) -> str:
    """A per-seat lens VALUE is either a free-form focus string (used verbatim) or a
    known preset name, which expands to that preset's PRIMARY (first) focus."""
    preset = LENS_PRESETS.get(value)
    return preset[0] if preset else value


def parse_lens_args(values) -> tuple:
    """Split the repeated --lens into (board_preset|None, {seat_id: focus}).

    A bare token is the board-level preset (the verdict's vocabulary/disclaimer +
    the positional default focus trio); an `id=value` token overrides one seat's
    focus. At most one bare preset is allowed."""
    if values is None:
        values = []
    if isinstance(values, str):   # a test/_args may pass a single string
        values = [values]
    board_preset = None
    overrides: dict = {}
    for raw in values:
        item = (raw or "").strip()
        if not item:
            continue
        if "=" in item:
            sid, _, val = item.partition("=")
            sid, val = sid.strip(), val.strip()
            if not sid or not val:
                die(f"--lens per-seat override {item!r} must be id=lens")
            overrides[sid] = _resolve_seat_lens(val)
        elif board_preset is not None and board_preset != item:
            die(f"--lens given two board presets ({board_preset!r} and {item!r}); pass at "
                "most one bare preset — per-seat focus uses id=lens")
        else:
            board_preset = item
    return board_preset, overrides

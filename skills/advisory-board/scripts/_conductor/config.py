"""Config resolution (design §4, §10): the SourceSpec/SeatConfig/RunConfig
dataclasses and everything that turns CLI args (or a recipe) into a RunConfig."""
from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from typing import Optional

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
    name: str
    adapter: SeatAdapter
    model: str
    lens: str
    reasoning: str

    @property
    def provider(self) -> str:
        return self.adapter.provider


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
        return [s.name for s in self.board if not s.adapter.isolates_network]


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


def resolve_board(seat_names: list, lens_preset: str, model_overrides: dict) -> list:
    lenses = LENS_PRESETS.get(lens_preset)
    if lenses is None:
        die(f"unknown lens preset {lens_preset!r}; choose from {', '.join(sorted(LENS_PRESETS))}")
    board: list = []
    for index, name in enumerate(seat_names):
        adapter = REGISTRY.get(name)
        if adapter is None:
            die(f"unknown seat {name!r}; known seats: {', '.join(sorted(REGISTRY))}")
        lens = lenses[index] if index < len(lenses) else lenses[-1]
        board.append(SeatConfig(
            name=name,
            adapter=adapter,
            model=model_overrides.get(name, adapter.default_model),
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

    if base is not None and not getattr(args, "source", None):
        source = load_source(base["source_ref"])
        seat_names = [s["seat"] for s in base["board"]]
        lens_preset = base.get("lens", DEFAULT_LENS)
        # Restore the recipe's exact per-seat models so --from-recipe reproduces
        # the original run; an explicit --model on the CLI still wins.
        for entry in base["board"]:
            model_overrides.setdefault(entry["seat"], entry["model"])
    else:
        if not getattr(args, "source", None):
            die("a --source is required (PATH, or - for stdin)")
        source = load_source(args.source)
        seat_names = parse_board(getattr(args, "board", None))
        lens_preset = getattr(args, "lens", None) or (base or {}).get("lens", DEFAULT_LENS)

    board = resolve_board(seat_names, lens_preset, model_overrides)

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
    )


def derive_title(source: SourceSpec) -> str:
    if source.kind == "path":
        stem = os.path.splitext(os.path.basename(source.ref))[0]
        return stem.replace("-", " ").replace("_", " ").strip() or "Advisory board review"
    first = source.text.strip().splitlines()[0] if source.text.strip() else ""
    return (first[:60] or "Advisory board review").strip()


def parse_board(value: Optional[str]) -> list:
    if not value:
        return ["claude", "codex", "gemini"]
    seats = [s.strip() for s in value.split(",") if s.strip()]
    if not seats:
        die("--board must list at least one seat")
    return seats


def parse_model_overrides(pairs: list) -> dict:
    overrides: dict = {}
    for pair in pairs:
        if "=" not in pair:
            die(f"--model expects seat=model_id; got {pair!r}")
        seat, _, model = pair.partition("=")
        overrides[seat.strip()] = model.strip()
    return overrides

"""The M4 structured cross-reading digest (design §5 / v1.x M4) — a deterministic,
§11-safe replacement for the head-truncation `summaries` packet.

Principle #1 ("models reason; the conductor plumbs") forbids the conductor from
clustering CLAIMS semantically — deciding that one seat's objection "means the same
as" another's would be reasoning over prose. So this module does NOT do that. It:

  * regroups each review BY THE REVIEW'S OWN SECTION HEADERS, matching the section
    LABELS (not the claim content) to a fixed canonical taxonomy — the same kind of
    structural plumbing as the old head-excerpt `_digest`, just organized for
    comparison instead of truncated; and
  * surfaces agreements/conflicts ONLY through the machine signals already blessed
    in M1 — the parsed `VERDICT:` token and the concrete citation set.

A seat reading round 2 then sees every seat's take on each topic side by side, plus
where the board agrees (same verdict token / a citation ≥2 seats raised) and where it
splits — a sharper signal to debate against (and for the `auto` stop-rule to read)
than three head-truncated reviews. Reviews with no parseable headers degrade
gracefully to a head excerpt; the full review always remains in round-N/<seat>.md.
"""
from __future__ import annotations

import re
from collections import Counter

from _conductor.convergence import citations, parse_verdict

__all__ = [
    "CANONICAL_SECTIONS",
    "DIGEST_SECTION_BUDGET",
    "DIGEST_JSON_SCHEMA",
    "classify_header",
    "parse_sections",
    "verdict_agreement",
    "shared_citations",
    "build_structured_digest",
    "build_structured_digest_data",
]


# The canonical topics, in render order, each with the keywords that map a review's
# own section header onto it. Classification is FIRST-match in this order, so the
# more specific buckets (risks owns "missing evidence") precede the general ones
# (evidence owns a bare "evidence"). Matching is on the header LABEL only — never the
# body — so this stays structural plumbing, not claim reasoning.
CANONICAL_SECTIONS = [
    ("Verdict", ("verdict",)),
    ("Changed mind & remaining dissent", ("changed", "dissent", "still dispute")),
    ("Strongest objections", ("objection",)),
    ("Recommended execution sequence", ("execution", "sequence", "recommend")),
    ("Invariants & guardrails", ("invariant", "guardrail")),
    ("Risks, stale assumptions & missing evidence", ("risk", "assumption", "stale", "missing")),
    ("Concrete evidence", ("evidence", "citation", "cited")),
    ("Challenges to the board", ("challenge", "ask the other", "other seats", "other board")),
]

# Per (seat, section) head-excerpt budget, in characters. The digest is one excerpt
# per seat per present section, so the total is bounded by
# (#sections × #seats × this) plus a small agreement header — comfortably smaller
# than the verbatim `full` packet, while covering EVERY section (not just the head).
DIGEST_SECTION_BUDGET = 240
_SHARED_CITATIONS_CAP = 20   # bound the agreement header's shared-evidence list too

# A section header is either a markdown heading (`## 2. Strongest objections`, any
# level — claude/gemini) OR a WHOLE-LINE, NUMBERED bold line (`**2. Strongest
# Objections**` — codex). The numbered-bold form is deliberately strict — it must be
# the whole line AND lead with `N.` — so a bolded verdict statement
# (`**REVISE — do not ship.**`) or a lettered objection sub-point
# (`**A. Concurrency window…**`) is body, not a header. (The round templates ask for a
# NUMBERED list of sections, so real section headers carry the number.)
_HEADER = re.compile(r"^(?:#{1,6}\s+(.+?)\s*#*|\*\*\s*(\d+\..+?)\s*\*\*)\s*$")
# A nested enumerator (a sub-point WITHIN a section, NOT a section): a single letter, or
# 1-5 roman-numeral letters, then `.`/`)` and a space — "A. ", "B) ", "II. ", "iv) ". A
# plain arabic number is deliberately NOT here — that is how SECTIONS are numbered.
_SUBHEADER = re.compile(r"^(?:[A-Za-z]|[IVXLCDMivxlcdm]{1,5})[.)]\s")
_FENCE = re.compile(r"^\s*(```|~~~)")
_WS = re.compile(r"\s+")


def _header_text(line: str):
    """The header LABEL of a line if it is a header (markdown heading or numbered-bold),
    else None."""
    m = _HEADER.match(line)
    if not m:
        return None
    return (m.group(1) or m.group(2) or "").strip()


def classify_header(header_text: str):
    """Map a review's section header LABEL to a canonical topic, or None if it matches
    no bucket (a title or a non-standard section — omitted from the digest, never
    interpreted)."""
    low = header_text.lower()
    for label, keywords in CANONICAL_SECTIONS:
        if any(k in low for k in keywords):
            return label
    return None


def parse_sections(review: str) -> dict:
    """Split a review into {canonical label -> body text} by its own section headers.

    A line is a SECTION boundary ONLY if it is a header (markdown heading or numbered-bold
    line), is NOT an enumerator sub-point ("A. …", "II. …"), AND classifies to a canonical
    topic. Everything else — sub-points, non-canonical headers, fenced code/diagrams — stays
    in the current section's body, so no content is dropped and a keyword in a sub-point's
    label can't scatter it into another topic. A leading title/preamble (before the first
    canonical section) falls before any open section and is dropped. Returns {} when no
    canonical section header is found at all (caller falls back to a head excerpt)."""
    sections: dict = {}
    current = None
    buf: list = []
    in_fence = False

    def flush():
        if current is None:
            return
        text = "\n".join(buf).strip()
        if text:
            sections[current] = (sections[current] + "\n\n" + text) if current in sections else text

    for line in (review or "").splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence          # a ``` / ~~~ line inside a review's code/diagram block
        if not in_fence:
            htext = _header_text(line)
            if htext is not None and not _SUBHEADER.match(htext):
                label = classify_header(htext)
                if label is not None:        # the only real section boundary
                    flush()
                    current, buf = label, []
                    continue
                # a non-canonical header (title, appendix, a bolded statement): not a
                # boundary — fall through so its content stays in the current section.
        if current is not None:              # body, incl. sub-points, fences, non-canonical headers
            buf.append(line)
    flush()
    return sections


def _excerpt(text: str, budget: int) -> str:
    """Compact head excerpt: collapse whitespace to one paragraph and cut at a word
    boundary. NOT an LLM summary — just a budget-bounded head, honestly elided."""
    flat = _WS.sub(" ", text).strip()
    if len(flat) <= budget:
        return flat
    return flat[:budget].rsplit(" ", 1)[0].rstrip() + " …"


def verdict_agreement(usable: list) -> tuple:
    """(per-seat verdict line, agreement summary). Pure over M1's parsed VERDICT token
    (r.verdict) — the structural agreement/conflict signal, never prose."""
    tokens = [(r.seat, r.verdict) for r in usable]
    line = "Verdicts: " + " · ".join(f"{seat}={tok or '—'}" for seat, tok in tokens)
    cast = [tok for _, tok in tokens if tok]
    missing = len(tokens) - len(cast)
    if not cast:
        summary = "(no machine `VERDICT:` tokens in these reviews — verdict agreement not measurable)"
    elif len(set(cast)) == 1:
        # every cast token agrees; flag a non-cast seat rather than calling it a split.
        summary = f"unanimous: {cast[0]}" if not missing else \
            f"all who cast a token agree: {cast[0]} ({missing} with no token)"
    else:
        counts = ", ".join(f"{n}×{tok}" for tok, n in Counter(cast).most_common())
        summary = "split — " + counts + (f" ({missing} with no token)" if missing else "")
    return line, summary


def shared_citations(usable: list) -> list:
    """Citations raised by ≥2 seats — concrete common ground (or contested points),
    pure over M1's citation set. Deterministic and rephrase-stable."""
    counter: Counter = Counter()
    for r in usable:
        counter.update(citations(r.stdout))   # each citation counted once per seat
    return sorted(c for c, n in counter.items() if n >= 2)


def build_structured_digest(usable: list, round_no: int = 2,
                            section_budget: int = DIGEST_SECTION_BUDGET) -> str:
    """The `summaries` board packet (M4): an agreement header (verdict tokens + shared
    citations) followed by each canonical topic with every seat's take side by side,
    head-excerpted. Deterministic and §11-safe — the conductor organizes by structure
    and machine tokens, it does not reason over the prose."""
    prev_round = round_no - 1
    verdict_line, agreement = verdict_agreement(usable)
    parts = [
        f"# Board packet — round {round_no} (cross-reading: summaries — structured digest)",
        "",
        f"## Where the board stands after round {prev_round}",
        "",
        verdict_line,
        f"Agreement: {agreement}",
    ]
    shared = shared_citations(usable)
    if shared:
        shown = shared[:_SHARED_CITATIONS_CAP]
        more = len(shared) - len(shown)
        line = "Shared evidence (raised by ≥2 seats): " + ", ".join(f"`{c}`" for c in shown)
        parts.append(line + (f" (+{more} more)" if more else ""))
    parts += ["", "## By topic", ""]

    seat_sections = [(r.seat, parse_sections(r.stdout)) for r in usable]
    for label, _kw in CANONICAL_SECTIONS:
        present = [(seat, secs[label]) for seat, secs in seat_sections if secs.get(label)]
        if not present:
            continue
        parts += [f"### {label}", ""]
        for seat, body in present:
            parts.append(f"- **{seat}:** {_excerpt(body, section_budget)}")
        parts.append("")

    # Graceful fallback: a review with no parseable headers is included as a head
    # excerpt rather than dropped (the digest never silently loses a whole seat).
    for r in usable:
        secs = dict(seat_sections).get(r.seat)
        if not secs:
            parts += [
                f"### {r.seat} — review (no section headers found; head excerpt)",
                "",
                _excerpt(r.stdout, section_budget * 3),
                "",
            ]
    return "\n".join(parts).rstrip() + "\n"


# The typed-JSON serialization of the SAME digest (`--digest-format json`). One
# schema id, bumped only if the shape changes.
DIGEST_JSON_SCHEMA = "advisory-board/board-packet-digest@1"


def build_structured_digest_data(usable: list, round_no: int = 2,
                                 section_budget: int = DIGEST_SECTION_BUDGET) -> dict:
    """The structured digest as TYPED data — the machine-readable twin of
    build_structured_digest, for `--digest-format json`.

    Serializes exactly the parsed signals the markdown digest already computes
    (§11: the conductor plumbs, the models reason — NO new reasoning, no semantic
    clustering): the per-seat VERDICT tokens and the agreement summary, the shared
    (≥2-seat) citation set, and each canonical topic with every seat's
    head-excerpted take, in the same order and with the same excerpt budgets as the
    markdown. Seats with no parseable headers land in `unparsed[]` (the markdown's
    graceful-fallback bucket). Deterministic: pure over the usable reviews."""
    prev_round = round_no - 1
    _line, agreement = verdict_agreement(usable)
    seat_sections = [(r.seat, parse_sections(r.stdout)) for r in usable]
    sections = []
    for label, _kw in CANONICAL_SECTIONS:
        takes = [{"seat": seat, "excerpt": _excerpt(secs[label], section_budget)}
                 for seat, secs in seat_sections if secs.get(label)]
        if takes:
            sections.append({"label": label, "takes": takes})
    unparsed = [{"seat": r.seat, "excerpt": _excerpt(r.stdout, section_budget * 3)}
                for r in usable if not dict(seat_sections).get(r.seat)]
    return {
        "schema": DIGEST_JSON_SCHEMA,
        "round": round_no,
        "built_from_round": prev_round,
        "cross_reading": "summaries",
        "verdicts": [{"seat": r.seat, "verdict": r.verdict} for r in usable],
        "agreement": agreement,
        "shared_citations": shared_citations(usable),
        "sections": sections,
        "unparsed": unparsed,
    }

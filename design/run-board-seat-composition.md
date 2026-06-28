# Advisory Board — Flexible Seat Composition (duplicate models + per-seat lenses)
> Let users seat the same provider/model more than once (2× Opus + 1× Codex, 3× Opus) with a distinct identity per seat, and give each seat its own lens — replacing the hidden invariant *"seat name == provider == unique board slot."*

- **Updated:** 2026-06-28
- **Source:** Tim's feature request ("2 Opus + 1 Codex, 2 Codex + 1 Opus, 3 Opus… and different lenses for all") + two architecture-mapping investigations (seat-identity flow across ~8 modules / ~15 call sites; lens system — per-seat lens is ~80% already built, assigned positionally)
- **Owner:** Tim
- **Baseline:** advisory-board @ `main` `837fb0d` (v1.8.0 line · 649 tests green)
- **Status:** APPROVED (Tim, 2026-06-28) — building. **Syntax:** auto-number + optional alias. **Per-seat lens value:** free-form focus string OR a preset name (→ its primary focus).

## Overview

Today the board assumes **one provider per seat and one seat per provider.** The seat *name* (`claude` / `codex` / `gemini`) is the de-facto primary key everywhere — dict keys, filesystem paths (`round-1/claude.md`), cross-reading lookups, render labels, the `verdict.json` `board[]` array. The board-wide `--lens PRESET` is secretly an *ordered trio* of focus strings assigned to seats **by position** (slot 0 → `First principles & economics`, slot 1 → `Execution & feasibility`, …) and already plumbed onto each seat's prompts.

Two consequences shape this plan:

1. **There is a latent data-loss bug today.** `--board claude,claude,codex` does **not** error — it *silently collapses* the two Claude seats into one (paths overwrite, name-keyed dicts dedup, the synthesizer merges them into a single `board[]` entry it then emits twice). Every failure is a silent overwrite, the dangerous kind. So a uniqueness guard is worth shipping **regardless** of the feature.
2. **Per-seat lenses are mostly built.** `SeatConfig.lens` is already a per-seat field that already drives each seat's round prompts and shows on each seat card. What's missing is (a) a unique seat **identity** so two same-provider seats don't collapse, and (b) a way to **explicitly choose** each seat's lens instead of taking the positional default.

This feature delivers both as one milestone. The decisive realization from the mapping: **the work is ~80% an identity refactor (replace seat-name-as-key with a unique seat id) and ~20% a thin per-seat-lens input surface** — the prompt/render plumbing for per-seat lenses already exists.

This markdown is the **source of truth**. The HTML view is rendered from it (`render_plan.py`) so the two never drift. Because the refactor touches the **egress/prompt path surface**, it gets an adversarial-review gate before merge (a correctness round + a focused identity/egress skeptic).

**Key design decisions.**

1. **Seat identity = a unique `id`, distinct from provider.** Each `--board` entry is either `provider` or `alias=provider`. The `id` is the alias when given; otherwise the provider name, **suffixed `#1`/`#2`/… only when a bare provider is repeated.** A board of unique bare providers (`claude,codex,gemini`) keeps `id == name` — so existing runs, recipes, and the default render are **byte-identical**. The provider/adapter/default-model still resolve from the provider part; only the *identity key* changes.
2. **The verdict stays one consensus voice.** Per-seat lenses steer each seat's **focus** (its prompt + its seat card). The **board-level lens** still selects the verdict's **vocabulary/disclaimer/headings** (SHIP-vs-plain, legal caveat, "What to resolve first"). This sidesteps the "what if seats disagree on lens" ambiguity entirely and requires **no `_verdict_labels.py` / renderer changes.**
3. **Targeting keys on the id.** `--model id=MODEL` and per-seat lens overrides address a seat by its id/alias (`--model risk=claude-opus-4-7`, `--model claude#2=…`). A bare provider name still works when that provider is unique on the board (backward-compatible).
4. **Loud failure replaces silent collapse.** Duplicate aliases, an unknown provider, or an override that targets a nonexistent id all `die` with a clear message — closing the data-loss bug above.

**Resolved — per-seat lens value (Tim, 2026-06-28).** Board-level `--lens PRESET` is unchanged (vocabulary + positional default trio). A per-seat override `--lens id=VALUE` accepts **either** a free-form custom focus string (`risk="Downside & tail risk — worst credible case"`, already blessed by `lens-presets.md`) **or** a known preset name, which expands to that preset's **primary** (first) focus. The verdict vocabulary always stays board-level.

```
Seat-id resolution (──> = "resolves to")
  --board claude,claude,codex
     claude (bare, provider repeated) ──> id "claude#1"   provider=Anthropic  lens=trio[0]
     claude (bare, provider repeated) ──> id "claude#2"   provider=Anthropic  lens=trio[1]
     codex  (bare, unique)            ──> id "codex"      provider=OpenAI     lens=trio[2]

  --board econ=claude,risk=claude,exec=codex
     econ=claude ──> id "econ"  provider=Anthropic  lens=trio[0] (or --lens econ=…)
     risk=claude ──> id "risk"  provider=Anthropic  lens=trio[1] (or --lens risk=…)
     exec=codex  ──> id "exec"  provider=OpenAI     lens=trio[2] (or --lens exec=…)

  --board claude,codex,gemini   (unique providers)
     ──> ids "claude","codex","gemini"  ← id == name, byte-identical to today
```

## Milestone: Flexible seat composition
status: planned

Seat the same provider multiple times with a distinct identity and an individually-aimed lens, while a single-provider-per-name board stays byte-identical. Replaces seat-name-as-identity with a unique seat `id` across the conductor, and exposes a per-seat lens input on top of the existing per-seat `SeatConfig.lens` plumbing.

**Invariants (must hold at every gate).** (1) A board of unique bare providers (`claude,codex,gemini`) is **byte-identical** to baseline — same ids, paths, `verdict.json`, render; this is the regression guard for the whole refactor. (2) **Consent stays byte-bound** — the egress sha256/disclosure surface is unchanged; provider-set disclosure lists each provider once for N same-provider seats; the D4 network-isolation posture is provider-level and inherited correctly. (3) The **verdict is one consensus voice** — board-level lens drives vocabulary/disclaimer/headings; per-seat lens never changes them. (4) **No silent collapse** — every malformed composition `die`s with a message.

### Phase 1 — Seat identity (`id`) and `--board` parsing
status: done
Give every seat a unique `id` distinct from its provider, parse the `alias=provider` / bare-with-auto-number syntax, and reject malformed boards loudly. This is the foundation; nothing else is safe until identity is unique.
- [x] DECISION: `id` is the alias when given, else the provider name, suffixed `#N` (board order) only when a bare provider repeats. Unique bare providers keep `id == name` (backward compat). *(Alt rejected: always suffix — breaks every existing recipe/test and the default render.)* — `assign_seat_ids` (pure) in `config.py`.
- [x] Parse `--board` entries as `alias=provider | provider`; validate each `provider ∈ REGISTRY`; assign ids; **reject duplicate ids / duplicate aliases / unknown provider** with a clear `die`. `parse_board` → `[(alias|None, provider)]`; `resolve_board` builds `SeatConfig(id, name, adapter, model, lens, …)` + the uniqueness guard. Alias chars restricted (`_ALIAS_RE`, no `#`).
- [x] Add `id` to `SeatConfig` (+ a `.label` for display); keep `name`/`provider` for adapter + egress. The provider-name literals (CLAUDE_OUTPUT_OVERRIDE, synth-seat pick) correctly stay on `.name`.
- [x] Add a uniqueness guard so even a *malformed* duplicate (same alias twice) fails loudly — closes today's silent-collapse bug.
- [x] `cmd_toolchain` migrated to the new `parse_board` shape (checks each distinct provider's CLI once).
Testing: `TestSeatComposition` (15 tests) — auto-number, aliases, byte-identical unique board, label disambiguation, positional lenses differ across duplicates, lens/model override by id, and every loud-reject path. **664 tests pass.**
Gate: `cd skills/advisory-board && python3 -m unittest discover -s tests -t tests`

### Phase 2 — Re-key the run onto `seat.id`
status: planned
Replace every seat-name key/path/lookup enumerated by the mapping with `seat.id`, so duplicate seats never collide. Provider-level egress logic (consent, provider-set disclosure, network-isolation posture) stays as-is — it is already provider-deduped and correct.
- [ ] **Paths:** `egress.py` prompt relpaths (`prompts/{id}-round-N.prompt`), `rounds.py` round artifacts (`round-N/{id}.md`, `.raw`, `logs/{id}-round-N.stderr`).
- [ ] **Round fan-out dicts:** `rounds.py` `by_seat` / `results[id]` / returned ordering; `egress.py` `build_round2` `by_name`/`own`.
- [ ] **Synthesizer:** `build_skeleton` `by_seat.setdefault(id)`, the re-emit loop, `tokens_by_seat`, `_lens_for` (match on id). `board[]` gets `id` + a display `seat_label`; `model` stays the provider model.
- [ ] **Convergence / digest:** `board_movement` `prev_by[id]`; `digest` `seat_sections` + `verdict_agreement` labels.
- [ ] **Run metadata / sensitivity:** `artifacts.py` preflight `pf={p.id:p}`, `network_isolation` keyed by id; run-card / metadata seat rows show id + provider.
- [ ] **Render glob:** `render_verdict.py` `_round_review` matches the id-based artifact filename, not the provider name; seat cards + `_seats_line` show the disambiguated label.
- [ ] Provider-level egress (`disclosure_line`, `render_sensitivity_json` provider set, D4 isolation gate) verified **unchanged** for N same-provider seats.
Testing: a 2×claude+codex run writes 3 distinct `round-*/*.md`, 3 distinct prompts, 3 distinct `board[]` entries, distinct seat cards; the default 3-provider board renders **byte-identical** to baseline (regression guard); egress consent still lists each provider once.
Gate: unittest (full suite) + a byte-identical diff check on a committed example re-render.

### Phase 3 — Targeting: `--model` / per-seat `--lens` by id + recipe round-trip
status: planned
Let users address a specific seat for model and lens, and make duplicate-seat / per-seat-lens runs **reproducible** under `--from-recipe` (today the recipe writes per-seat lens but never reads it back).
- [ ] `parse_model_overrides` + its consumption + the recipe restore key by **id** (`--model risk=…`, `--model claude#2=…`); a bare provider name still resolves when unique. Override targeting a nonexistent id → `die`.
- [ ] Per-seat lens override surface: `--lens` accepts the board-level preset (bare) **and/or** `id=VALUE` per-seat assignments. `VALUE` = a free-form focus string, or a preset name → its primary focus. `resolve_board` uses the override when present, else the positional default `trio[index]`.
- [ ] **Recipe round-trip:** persist + **restore** per-seat `{id, provider, model, lens}`; `config.py` `--from-recipe` path restores per-seat lens (currently ignored). `validate_recipe` enforces id uniqueness.
- [ ] Loud errors: duplicate alias, unknown provider, override → unknown id, malformed `--lens id=`.
Testing: `--model claude#1=…` and `--model claude#2=…` hit the right seats; `--lens risk=legal-contract` sets only that seat's lens; a per-seat-lens run round-trips identically through `--from-recipe`; each error case raises with a clear message.
Gate: unittest (full suite).

### Phase 4 — Docs, adversarial review, demo
status: planned
Document the new composition surface, prove it on a real run, and gate the merge with adversarial review (the refactor touches prompt/egress paths).
- [ ] Docs: `SKILL.md` (board choice + the syntax), `references/board-composition.md` (duplicate seats, ids, targeting), `references/lens-presets.md` (per-seat lens + custom focus). Keep frontier model IDs inline (memory: never abstract/downgrade them).
- [ ] Adversarial review: one correctness round (parallel finders) + a focused **identity/egress skeptic** (does any seat-id path still collide? does consent still bind every byte? any silent dedup left?). Fix confirmed findings + add regression tests.
- [ ] Demo (optional, off the gallery track): a `2× Opus + 1× Codex` run with three explicit lenses, rendered to confirm 3 distinct seat cards + dissent attribution reads cleanly.
- [ ] Release: skill-scoped semver tag once Tim signs off (memory: milestone merge → `advisory-board/vX.Y.Z`; outward-facing release needs Tim's explicit go).
Gate: full suite green + adversarial review clean + the default-board byte-identical regression holds.

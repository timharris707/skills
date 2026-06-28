# Board Composition

The default board is three seats — Claude, Codex, Gemini. That's a default, not a rule. A seat is a *role* (a lens), not a fixed provider, so you can resize and recompose the board to fit the subject and what's installed.

## Size

- **Minimum: 2 seats.** A board needs at least two independent voices; one model reviewing itself is not a board. Below two GO seats at preflight, stop.
- **Default: 3.** Enough perspectives to triangulate without ballooning cost.
- **Up to ~5.** Add seats for high-stakes or broad subjects. Past five, rounds get expensive and the synthesis gets noisy — prefer sharper lenses over more seats.

## Composition

- **Any provider in any seat.** Lenses come from `references/lens-presets.md`; assign them to whatever models you have.
- **Same provider twice is allowed** — e.g. two Claude seats with different lenses (architecture vs. security). Repeat the provider in `--board` (see *Naming & targeting* below). Note it in provenance; two seats on the same model are less independent than two different models.
- **A human seat** is valid: capture the person's review as that seat's `round-*/` artifact and let the board read it like any other.
- **A local/offline seat** is valid and is the lever for sensitive material — see `references/data-handling.md`. The `ollama` seat is registered and runnable: `--board claude,ollama` (or any lineup), with `--model ollama=<model>` to pick a pulled model (`ollama list`). It drives a local model headless (`ollama run <model>`, prompt on stdin), counts as `provider: local` — so it **never egresses** (excluded from the egress manifest and the disclosure) and needs no account. That on-machine-only property is exactly why a local board is the lever for must-not-leave material.
- **An Antigravity seat** (`--board claude,codex,antigravity`) is registered as Google's agent-first successor to gemini-cli, which was sunset for consumer tiers on 2026-06-18. The `antigravity` seat drives the `agy` CLI headless (`agy -p --model "<display name>" --sandbox`). Two cautions, both reflected in the adapter: pin an **exact** model display name from `agy models` (an unknown name is *silently substituted*, never rejected), and treat it as networked like gemini (an agentic harness whose web/grounding isn't removable). Keep gemini available while your gemini auth still works (enterprise / paid API key); prefer antigravity going forward.

## Naming & targeting seats

Each `--board` entry is a bare `provider` or an `alias=provider`. Every seat gets a unique **id** used for its artifacts, its seat card, and for targeting it:

- **Bare, unique** — `--board claude,codex,gemini` → ids `claude`, `codex`, `gemini` (unchanged from the single-provider default).
- **Bare, repeated** — `--board claude,claude,codex` → the duplicates auto-number to `claude#1`, `claude#2` (and `codex`).
- **Aliased** — `--board econ=claude,risk=claude,exec=codex` → ids `econ`, `risk`, `exec`. Aliases read better in the handoff and in dissent attribution than `claude#2`, so prefer them for same-provider boards.

Target a specific seat by its id:

- **Model** — `--model risk=claude-opus-4-7` (or `--model claude#2=…`). A bare provider name still works when that provider appears once.
- **Lens** — `--lens` is repeatable. A bare token sets the **board** lens (the verdict's vocabulary + the default per-seat focus trio); `id=lens` gives one seat its own focus — a free-form string (`--lens risk="Downside & tail risk"`) or a preset name, which uses that preset's primary focus. Seats you don't override keep the positional default, so a same-provider board already gets distinct lenses for free.

A malformed board fails loudly — duplicate aliases, an unknown provider, or an override aimed at a seat that isn't on the board all stop the run with a clear message rather than silently dropping a seat. A run's exact composition (ids, per-seat models and lenses) round-trips through `--from-recipe`.

## Works with what you have

Don't require three frontier subscriptions to get value:

- **Two seats** (e.g. Claude + Codex) is a real board. Run it and say it was a two-seat board.
- **API-key fallback.** If a subscription CLI isn't available, an API-key-backed call to the same provider is fine — record the auth mode in provenance (no secrets).
- **One paid + one local.** A frontier seat plus a strong local model still gives you cross-model challenge — e.g. `--board claude,ollama` (only the claude prompt egresses; the local seat stays on-machine).

Record the actual lineup and auth modes in `run-metadata.md`; the handoff should never imply more independence than the run had.

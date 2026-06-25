# Board Composition

The default board is three seats — Claude, Codex, Gemini. That's a default, not a rule. A seat is a *role* (a lens), not a fixed provider, so you can resize and recompose the board to fit the subject and what's installed.

## Size

- **Minimum: 2 seats.** A board needs at least two independent voices; one model reviewing itself is not a board. Below two GO seats at preflight, stop.
- **Default: 3.** Enough perspectives to triangulate without ballooning cost.
- **Up to ~5.** Add seats for high-stakes or broad subjects. Past five, rounds get expensive and the synthesis gets noisy — prefer sharper lenses over more seats.

## Composition

- **Any provider in any seat.** Lenses come from `references/lens-presets.md`; assign them to whatever models you have.
- **Same provider twice is allowed** — e.g. two Claude seats with different lenses (architecture vs. security). Note it in provenance; two seats on the same model are less independent than two different models.
- **A human seat** is valid: capture the person's review as that seat's `round-*/` artifact and let the board read it like any other.
- **A local/offline seat** (e.g. an Ollama model) is valid and is the lever for sensitive material — see `references/data-handling.md`.
- **An Antigravity seat** (`--board claude,codex,antigravity`) is registered as Google's agent-first successor to gemini-cli, which was sunset for consumer tiers on 2026-06-18. The `antigravity` seat drives the `agy` CLI headless (`agy -p --model "<display name>" --sandbox`). Two cautions, both reflected in the adapter: pin an **exact** model display name from `agy models` (an unknown name is *silently substituted*, never rejected), and treat it as networked like gemini (an agentic harness whose web/grounding isn't removable). Keep gemini available while your gemini auth still works (enterprise / paid API key); prefer antigravity going forward.

## Works with what you have

Don't require three frontier subscriptions to get value:

- **Two seats** (e.g. Claude + Codex) is a real board. Run it and say it was a two-seat board.
- **API-key fallback.** If a subscription CLI isn't available, an API-key-backed call to the same provider is fine — record the auth mode in provenance (no secrets).
- **One paid + one local.** A frontier seat plus a strong local model still gives you cross-model challenge.

Record the actual lineup and auth modes in `run-metadata.md`; the handoff should never imply more independence than the run had.

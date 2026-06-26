# Dogfood roundtables

Real advisory-board runs used to answer strategic questions about the skill itself — the board reasoning about its own direction. Each `*-run/` directory is a committed, **curated** subset of a real run: the board's output (`final-consensus.md` / `.html`, `verdict.json`), provenance (`run-metadata.md`), and the debate trail (`board-packet-round-*.md`, `round-*/<seat>.md`). The bulky/noisy pieces (`*.raw` seat stdout, `logs/*.stderr`, `prompts/`, egress/scope manifests) are omitted.

Both were run **grounded** (`--repo skills/advisory-board`), **3-seat** (Claude · Codex · Gemini), cross-provider, debating across rounds, then synthesized by a neutral seat.

| Run | Source brief | Verdict |
| --- | --- | --- |
| `fusion-response-run/` | [how-should-advisory-board-respond-to-openrouter-fusion.md](how-should-advisory-board-respond-to-openrouter-fusion.md) | Proceed with care — high, unanimous (2 rounds) |
| `executable-evidence-run/` | [should-advisory-board-add-a-sandboxed-execution-seat-mode.md](should-advisory-board-add-a-sandboxed-execution-seat-mode.md) | Build-with-constraints — high, unanimous (3 rounds) |

Context: [`../competitive-fusion-comparison.md`](../competitive-fusion-comparison.md) (the Fusion vs. advisory-board analysis) and [`../run-board-executable-evidence.md`](../run-board-executable-evidence.md) (the build plan the second run produced).

> Running the board on its own source also surfaced — and we fixed — a real self-review false-drop in the conductor's failure classifier ([skills#32](https://github.com/timharris707/skills/pull/32)): Codex echoed `registry.py`'s `_MODEL_NOT_FOUND_SIGNALS` to stderr and was wrongly dropped as `ModelNotFound`. Both runs above are post-fix, with all three seats live.

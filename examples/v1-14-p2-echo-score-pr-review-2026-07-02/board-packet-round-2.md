# Board packet — round 2 (cross-reading: summaries — structured digest)

## Where the board stands after round 1

Verdicts: claude=caution · codex=block
Agreement: split — 1×caution, 1×block
Shared evidence (raised by ≥2 seats): `--from-recipe`, `basis_line_instruction`, `cli.py`, `scripts/_conductor/cli.py:468`

## By topic

### Verdict

- **claude:** **CAUTION** — confidence **medium-high**. The metric is genuinely well-built and honest, byte-identity holds, the injection surface is closed, and no stale constants leaked. But the feature's *headline* honesty property — the same-provider …
- **codex:** BLOCK, confidence high. What would change it: a patch that makes pre-P2 `--from-recipe` replay exact or explicitly non-scoring, and fixes the dropped-seat/same-provider edge semantics with tests.

### Strongest objections

- **claude:** **① The same-provider discount reads the wrong seat population (the one real defect).** `cli.py:468` computes the honesty hook as `distinct_providers = len({s.provider for s in config.board})` — distinct providers over the **full …
- **codex:** - Pre-P2 recipe replay is not exact. `recipe.py` records `prompt_template`/`prompt_template_sha256`, but `resolve_config()` loads recipes without using those fields to select old prompt bytes or suppress P2 scoring. Current …

### Recommended execution sequence

- **claude:** 1. **Fix objection ①:** expose `provider` on `SeatRoundResult` (or pass the considered seats' provider *set* from `cli.py`), and base `_same_provider` on distinct providers **among the considered seats**. Then …
- **codex:** 1. Add prompt-template provenance handling for recipe replay: either preserve historical prompt bytes by version/sha or refuse/scoring-disable pre-P2 recipes loudly. 2. Gate echo sidecar/metadata rendering on “P2 signals were actually …

### Invariants & guardrails

- **claude:** - **Pure over parsed signals only** — `echo_score` reads only `parse_verdict`/`parse_basis` tokens + `citations` sets, never prose. ✓ - **Absent → not_computed / dropped pill / zero bytes, never fabricated** — `echo_score` <2-overlap …
- **codex:** - Never compute a real band from a run whose prompt did not request `BASIS:`. - Never let old recipe replay silently egress new prompt bytes. - A sidecar should mean “scored from valid P2 inputs,” not merely “two rounds happened.” - …

### Risks, stale assumptions & missing evidence

- **claude:** - **Primary:** `board_size` is a whole-board config fact used as a proxy for "are the scored seats duplicates?" — the proxy breaks under seat drops (`cli.py:468` ↔ `echo_score.considered`). - **Minor:** `_majority_verdict` counts only …
- **codex:** I did not rerun the 1395-test suite in this read-only review. The suite claim remains unverified here. Existing tests also appear to miss the exact old-recipe and partial-drop cases that carry the most risk.

### Concrete evidence

- **claude:** - `scripts/_conductor/cli.py:468` — `distinct_providers = len({s.provider for s in config.board})` (full configured board). - `scripts/_conductor/config.py:80-81` — `provider` is `self.adapter.provider`; `:108` — `board: list # …
- **codex:** - `scripts/_conductor/recipe.py:254` records `prompt_template`; `scripts/_conductor/recipe.py:255` records `prompt_template_sha256`. - `scripts/_conductor/config.py:505` loads a recipe, but `scripts/_conductor/config.py:512`-`517` only …

### Challenges to the board

- **claude:** - **Codex/generalist:** is objection ① worth a code fix now, or acceptable as a documented limit given it only over-flags on a nichey board-plus-drop? Push back on my CAUTION if you think the edge doesn't justify it. - **Windowing:** for …
- **codex:** - Whether old recipe replay should preserve historical prompt bytes or refuse stale recipes instead. - Whether any dropped seat should suppress scoring, or only fewer-than-two overlapping seats. - Whether a single parsed verdict among …

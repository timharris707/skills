**1. Verdict**

BLOCK, confidence high. What would change it: a patch that makes pre-P2 `--from-recipe` replay exact or explicitly non-scoring, and fixes the dropped-seat/same-provider edge semantics with tests.

**2. Strongest Objections**

- Pre-P2 recipe replay is not exact. `recipe.py` records `prompt_template`/`prompt_template_sha256`, but `resolve_config()` loads recipes without using those fields to select old prompt bytes or suppress P2 scoring. Current `ROUND2_TEMPLATE` now always includes `BASIS:`, and `cli.py` writes `echo-score.json` for any run with >=2 rounds. That violates the stated `--from-recipe` and pre-P2 degradation contract.
- Dropped-seat degradation is not implemented as claimed. `echo_score()` filters to usable overlapping seats and computes whenever at least two remain; a 3-seat board with one dropped seat can still get a real band.
- Same-provider detection can be wrong after drops. `cli.py` passes distinct providers for the configured board, not the actually considered seats, so a `claude,claude,codex` run where only the two Claude seats remain is treated as mixed-provider.
- Manual docs drift: `references/prompt-templates.md` says the line is round-2+, but the Round 3 reference prompt lacks both the `BASIS:` and final `VERDICT:` token tail.

**3. Recommended Execution Sequence**

1. Add prompt-template provenance handling for recipe replay: either preserve historical prompt bytes by version/sha or refuse/scoring-disable pre-P2 recipes loudly.
2. Gate echo sidecar/metadata rendering on “P2 signals were actually requested” and sufficient parsed final-transition inputs.
3. Change same-provider logic to derive from considered seats’ providers, not configured board provider count.
4. Add tests for old `round2@2` recipe replay, 3-seat-with-one-dropped, and duplicate-provider-after-drop.
5. Update `references/prompt-templates.md` Round 3 prompt to include the same final two machine-token lines.

**4. Invariants And Guardrails**

- Never compute a real band from a run whose prompt did not request `BASIS:`.
- Never let old recipe replay silently egress new prompt bytes.
- A sidecar should mean “scored from valid P2 inputs,” not merely “two rounds happened.”
- Same-provider discount must apply to the seats actually scored.
- HTML may add optional pills only when source data is valid and intentional.

**5. Risks / Missing Evidence**

I did not rerun the 1395-test suite in this read-only review. The suite claim remains unverified here. Existing tests also appear to miss the exact old-recipe and partial-drop cases that carry the most risk.

**6. Concrete Evidence**

- `scripts/_conductor/recipe.py:254` records `prompt_template`; `scripts/_conductor/recipe.py:255` records `prompt_template_sha256`.
- `scripts/_conductor/config.py:505` loads a recipe, but `scripts/_conductor/config.py:512`-`517` only reconstructs source/board; no prompt version/sha drives prompt selection.
- `scripts/_conductor/prompts.py:417`-`439` defines the current round-2+ template with unconditional `BASIS_LINE_INSTRUCTION`.
- `scripts/_conductor/cli.py:466`-`475` computes and writes `echo-score.json` for every run with at least two rounds.
- `scripts/_conductor/echo_score.py:126`-`131` drops unusable seats and computes if two overlap, so “any dropped seat => not computed” is false.
- `scripts/_conductor/cli.py:468` uses distinct providers from `config.board`; `scripts/_conductor/echo_score.py:184`-`188` only compares that count to considered seats.
- `references/prompt-templates.md:95`-`115` documents Round 3 without the new final token lines.

**7. Ask Other Seats To Challenge**

- Whether old recipe replay should preserve historical prompt bytes or refuse stale recipes instead.
- Whether any dropped seat should suppress scoring, or only fewer-than-two overlapping seats.
- Whether a single parsed verdict among otherwise usable seats can ever define an “emerging majority.”
- Whether renderer-side schema validation for `echo-score.json` should be stricter before showing the pill.

VERDICT: block

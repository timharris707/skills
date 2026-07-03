All three verifications are in. Agent 2 confirms codex's recipe-replay objection against the real code, and — importantly — surfaces a nuance neither round-1 seat stated precisely. Here is my complete round-2 review.

---

# Round-2 review — v1.14 P2 (independence / echo score)

## 1. Updated verdict

**CAUTION**, confidence **high** (round-1 was medium-high; the two live objections are now verified against the real code, not just the diff).

*What flips me to SHIP:* a patch that (a) bases the same-provider discount on the **considered seats'** providers rather than the whole board's, and (b) makes the recipe-replay / `not_computed` **documentation match the actual code** (plus a provenance warning on sha mismatch) — each with a test. Both are small and localized; neither is architectural.

## 2. Where I changed my mind, where I still dissent

- **Changed (toward codex):** In round 1 I treated the pre-P2 `--from-recipe` question as a documented-limit footnote and led only with my same-provider objection. Codex was right to make it co-primary. I verified codex's exact citations — `recipe.py:254-255` records `prompt_template_sha256`, and the `resolve_config()` / `recipe_to_config()` load path (`config.py:505-517`) **never reads it back** — and they hold. `--from-recipe` re-runs the board with the *current* templates (`egress.py:53-58,103-104` unconditionally call `build_round2_prompt`), and there is only one round-2 template, now BASIS-bearing (`prompts.py:439`). So a pre-P2 recipe replayed post-P2 egresses **new** `round2@3` bytes and a new sha. I now carry this as a co-equal must-fix.

- **Still dissent from codex (BLOCK):** codex's BLOCK rests on "replay is not exact" read as a **regression**. It is not a regression — recipe replay has *always* used current template code; no historical-bytes path has ever existed (`prompts.py` keeps exactly one round-2 template, and prior bumps only stayed byte-stable via **conditional** empty-fill placeholders — the P4 grounding pattern at `prompts.py:240-242,265`). P2 is the first change to move the **unconditional** round-2 bytes, so it ends a *coincidental* byte-stability rather than removing a guaranteed capability. Egress is also **consented at the gate** (§8/§12), so nothing is silently sent. That is a doc over-claim plus a missing provenance warning — proceed-with-changes, not do-not-proceed. I hold CAUTION.

- **Correction to *both* seats' framing (my own read):** codex prescribed "scoring-disable pre-P2 recipes" and the implementer's docs promise pre-P2 replay → `not_computed`. **Both are wrong in the same direction.** On replay the current template genuinely *does* request BASIS, so the re-run is a legitimate P2 run and scoring it is correct — suppressing it would blank a valid result. `echo_score` is only ever called at run time on freshly-run rounds (`cli.py:467-469`); nothing re-scores stored BASIS-less files (re-render reads the frozen sidecar, never re-invokes the metric). So the metric does **not** fabricate a band from BASIS-less inputs in any real path. The defect is the *docs*, not the behavior. Fix the docs to the (defensible) real behavior; don't add suppression.

## 3. Strongest remaining objections

**① [correctness] The same-provider discount reads the wrong seat population.** `cli.py:468` computes `board_size = len({s.provider for s in config.board})` — distinct providers over the **full** board — but `_same_provider(board_size, considered)` (`echo_score.py:184-188`) compares it to `considered`, the final-round overlap set. These populations diverge under seat drops, so the discount both **under-** and **over-**applies:
  - Board `[claude, claude, codex]`, codex drops in the final round → `board_size=2`, `considered=2` → `2 < 2` is False → discount does **not** fire, yet both considered seats are `claude`. High overlap between two same-provider seats is then **wrongly flagged as echo**.
  - Board `[claude, codex, gemini, gemini]`, all considered → `board_size=3`, `considered=4` → fires, discounting overlap as "expected" even though three of four seats are genuinely cross-provider.
  `SeatRoundResult` already exposes `.provider` (`rounds.py:49`), so the honesty hook can be computed directly over `overlap_seats` — no new plumbing.

**② [honesty / doc-vs-code] The DECISION doc claims a degradation the code does not perform.** `epistemics.md` states "an old run dir, or a pre-P2 recipe replayed via `--from-recipe` all produce **not computed**"; `echo_score.py:33-34` and the CHANGELOG echo it, and the CHANGELOG separately asserts "`--from-recipe` replay stays exact." Verified false: `echo_score`'s only `not_computed` path is `len(overlap_seats) < 2` (`echo_score.py:131-140`) — there is no pre-P2 / all-unknown-basis branch — and the recorded template sha is never validated on load. This violates the phase's own hard discipline that "epistemics.md's published definition must match the code EXACTLY," and it's the DECISION document making the false claim.

## 4. Recommended execution sequence

1. **Fix ①:** drop the `board_size` proxy; inside `echo_score`, derive `same_provider` from `len({r.provider for r in overlap_seats}) < len(overlap_seats)`. Add a test: `[claude, claude, codex]` with codex dropped → discount fires (band not driven by overlap); `[claude, codex, gemini, gemini]` → discount does not fire on the cross-provider majority.
2. **Fix ②:** rewrite the `epistemics.md` degradation sentence, the `echo_score.py` docstring, and the CHANGELOG to describe the real behavior — replay re-runs with the current BASIS-bearing template, so a pre-P2 recipe becomes a fresh P2 run scored normally; `not_computed` is reserved for `< 2` overlapping seats and single-round runs.
3. **Close the provenance gap ② surfaced:** on recipe load, compare the recorded `prompt_template_sha256` to the current template sha and **warn loudly** on mismatch (not a refusal — the run is still valid, but the user learns their pre-P2 recipe will not reproduce byte-for-byte). This makes the consented egress honest about drift. Add a test.
4. Re-run the full suite; confirm 1395→(new total) and that byte-identity goldens are untouched (they should be — none of these touch the pill/section rendering).

## 5. Invariants and guardrails

- **Pure over parsed signals only** — upheld: `echo_score` reads `parse_verdict`/`parse_basis` tokens + `citations` sets, never prose. ✓
- **No fabricated band** — upheld *in behavior* (the metric never runs on BASIS-less stored files; unknown basis is honest, not fabricated), but **the docs claim a `not_computed` degradation the code doesn't implement** — Fix ②.
- **Injection closed** — upheld: `_explain` emits only band/majority enums + int counts + fixed phrasing; `parse_basis` yields an enum-or-`None`; the pill is HTML-escaped at the render boundary and `echo_class` is a fixed `echo-<band>`. ✓ (verified)
- **Body byte-identity when the pill is absent** — upheld: drop regex + `setdefault` defaults; head CSS may evolve, body must not, and the golden compares body only. ✓ (verified)
- **DECISION matches code EXACTLY** — **violated** by ②; this is the one hard guardrail currently broken.
- New guardrail to add: **replay must either reproduce recorded bytes or announce the drift** — item 3.

## 6. Risks, stale assumptions, missing evidence

- **Primary residual risk:** the same-provider proxy (`cli.py:468` ↔ `echo_score.considered`) is a config fact standing in for a parsed-population question; it breaks precisely when seats drop. Advisory-only (never gates), so impact is a misleading band in niche board+drop configs — real but bounded.
- **Assumption retired:** "recipe replay pins bytes." It pins *config*; the sha is provenance and is never checked. Any future unconditional template change inherits this — worth a standing note in the recipe docs.
- **Verified, not assumed:** no stale sha/version constants (old `round2@2`/`27f5d18e` survive only in a comment; the grounded sha is inequality-asserted); the +40 tests and "1355 → 1395" match; epistemics.md correctly omits the 0.60/0.30 numbers per the no-pseudo-precision DECISION.
- **Still unverified by me:** I did not execute the 1395-count suite; I trust the diff's test bodies but not the runtime tally. Metric logic for ties / flip-away / empty-Jaccard / 2-seat majority I traced by hand and found sound.

## 7. Concrete evidence

- `scripts/_conductor/cli.py:468` — `distinct_providers = len({s.provider for s in config.board})` (full board, not considered).
- `scripts/_conductor/echo_score.py:184-188` — `_same_provider` returns `board_size < considered`; `:131-140` — the sole `not_computed` path (`len(overlap_seats) < 2`); `:33-34` — docstring claiming pre-P2/old-dir → `not_computed`.
- `scripts/_conductor/rounds.py:49` — `SeatRoundResult.provider` exists (enables the clean fix).
- `scripts/_conductor/recipe.py:254-255` — records `prompt_template` / `prompt_template_sha256`; `scripts/_conductor/config.py:505-517` — the `--from-recipe` load path, which never reads the sha back.
- `scripts/_conductor/egress.py:53-58,103-104` — packet build calls the current `build_round2_prompt` unconditionally; `scripts/_conductor/prompts.py:439` — round-2 template appends `BASIS_LINE_INSTRUCTION`; `:245-249` — "added UNCONDITIONALLY … changes the round-2 bytes on EVERY run."
- `references/epistemics.md` (echo section) — "a pre-P2 recipe replayed via `--from-recipe` … produce **not computed**"; CHANGELOG — "`--from-recipe` replay stays exact." Both contradict the code above.

BASIS: evidence
VERDICT: caution

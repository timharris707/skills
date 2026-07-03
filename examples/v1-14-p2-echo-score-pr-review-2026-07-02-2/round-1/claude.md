I've now verified the substance against the actual staged tree (not just the diff). Here is my review.

---

## Claude seat review — v1.14 P2 (independence / echo score), revised

### 1. Verdict

**CAUTION** — confidence **medium-high**. All three prior blockers are genuinely resolved (I verified each against the real tree, not the diff's word), and I could not find a substantive new defect of the class the pattern predicts. What holds this back from SHIP is small but real: one doc-vs-reality inaccuracy of exactly the kind this board blocked on last round (the CHANGELOG suite count), plus I was prevented (plan-mode sandbox) from independently running the suite/goldens, so "1403 OK" and the byte-identity goldens remain the author's claim, mechanism-verified but not execution-verified by me.

**What flips it to SHIP:** correct `CHANGELOG.md:23` to the real shipped count, and an independent confirmation that the full suite + byte-identity goldens are green (the run I was blocked from doing).

### 2. Prior blockers — cleared / remaining (verified in the real files)

**Blocker 1 (same-provider discount read the config board, not the scored seats) — CLEARED.** This is a true fix, not a diff claim:
- `SeatRoundResult` carries a real `provider: str` field (`rounds.py:49`) and `_run_seat_round` populates it from `seat.provider` (`rounds.py:151`). So the discount reads real, per-seat provider data on real runs — *not* an all-`None` population, which was my worst-case hypothesis (it would have made **every** real board read as same-provider and silently suppress the overlap signal). It does not happen.
- `_same_provider(overlap_seats)` reads `getattr(r, "provider", None)` over the scored population only (`echo_score.py:208-219`), and `echo_score` computes it *after* `overlap_seats` is derived (`echo_score.py:186`). `board_size` is gone from the signature and the call site (`cli.py:469` passes two args); `grep` confirms **zero** `board_size` references remain anywhere in `scripts/` or `tests/`.
- The three regression cases assert the right bands: codex-dropped `[claude,claude,codex]` → `considered==2`, discount fires, `moderate` (strong flip, no deference); `[claude,codex,gemini,gemini]` → discount fires on the gemini pair with the note; `None`-provider pair → distinct → `high`. I traced each through `_band` by hand and they land where asserted.

**Blocker 2 (docs claimed `not_computed` degradations the code never performs) — CLEARED.** The code degrades to `not_computed` in exactly two places — `< 2` overlap seats (`echo_score.py:151`) and, structurally, single-round runs (never invoked; `cli.py:467` gates on `len(rounds_done) >= 2`). The reconciled prose now matches that cell-for-cell: `echo_score.py:43-53`, `artifacts.py:358-374` (the `render_echo_lines` docstring + the `not_computed` branch), and the epistemics.md degradation paragraph all say the same thing — old dir → *absent*, pre-P2 recipe → *scores normally with all-`unknown` BASIS*. No residual over-claim.

**Blocker 3 (pre-P2 `--from-recipe` silently egresses new bytes; recorded sha never validated) — CLEARED (via the warning remedy).** `_warn_on_template_drift` (`config.py:481-517`) is called once, on the recipe path only (`config.py:546`), writes to **stderr** (so it never pollutes a gate/JSON stdout consumer), and never refuses or changes exit codes. The sha comparison is genuinely like-for-like: the recipe records `prompt_template_sha(config.grounded, bool(config.revise_of))` (`recipe.py:257`), and the warn reconstructs `grounded = bool(recipe.get("repo"))` / `revised = bool(recipe.get("revise_of"))` (`config.py:507-508`). I checked the two invariants that make that sound — `config.grounded` *is* `bool(self.repo)` (`config.py:151-153`), and the recipe writes `repo`/`revise_of` iff those config values are truthy (`recipe.py:284,292`). So a fresh grounded or revise recipe will **not** false-warn, and a genuine template drift is what surfaces. The additive `round2_template`/`round2_template_sha256` keys (`recipe.py:258-263`) are load-optional and don't feed the drift check. Concern 2 is also addressed.

### 3. New-defect hunt (the project pattern) — what I found

I looked hard for the introduced-by-this-pass defect. I did not find a blocking one. The closest candidates, in descending severity:

1. **Stale suite count in the CHANGELOG — `CHANGELOG.md:23` says "Suite 1355 → 1395."** The State section says the suite is now **1403** after the fix pass (+8 regression tests). The fix pass added `TestRecipeTemplateDrift` + the same-provider regressions but left the feature's own changelog line at 1395. This is precisely the "docs don't match reality" category the board spent Blocker 2 on last round, so I hold it to the same bar: it should read 1403.

2. **`None → token` verdict is counted as a "flip toward the majority" (`echo_score.py:167-173`).** If a seat's round-(N-1) reply was unparseable (`verdict is None`) and its round-N token is the majority, `prev_v != curr_v` is true → it's tallied as a flip *and* as flip-toward-majority. On a 2-seat mixed board that alone is `frac_flip == 0.5` → `strong_flip`, and with the (common) high citation overlap it reaches **`high`**. That's echo risk manufactured from a *parse failure*, not a mind-change, and the explanation will say "1/2 seats flipped toward the majority" when no one changed their mind. Finding #6's "caps at moderate without corroboration" is technically true (without overlap it's moderate), but the corroborated case is the normal one. It's advisory-only and consistent with `board_movement`'s own movement definition, so I flag it as a correctness nuance to tighten, not a blocker (cheap guard: require `prev_v is not None` before counting a flip-toward-majority).

3. **The same-provider discount is board-global, not pair-scoped (`echo_score.py:208-219`).** On `[claude, codex, codex]` a *single* duplicate pair discounts the *whole* board, masking claude's genuinely independent flip. This is the exact formula the prior board prescribed and endorsed, so it's the agreed design — noting it only as future coarseness, not a regression.

4. **Nit — the echo-pill authoring comment leads with `{{ECHO_PILL}}` (`references/handoff-template.html`).** On a *present*-pill render the drop regex doesn't fire, so `render()`'s global token substitution injects the (escaped, machine-generated) pill text into the HTML comment too. Invisible and HTML-safe (the explanation is enum bands + counts + fixed phrasing, no `-->`), but sloppy; other optional slots avoid leading their comment with the token name.

### 4. Recommended execution sequence
1. Correct `CHANGELOG.md:23` to the real shipped suite count (1403), and re-scan the P2 changelog block for any other count/version drift.
2. Independently run the full suite **and** the byte-identity goldens on the exact staged tree; confirm 1403 OK and zero body-diff on the absent-echo HTML + old-dir run-metadata goldens (I could not run these under plan-mode).
3. (Optional, low-risk) guard the flip-toward-majority tally with `prev_v is not None` so a malformed prior token can't read as a social flip; add a 2-seat `None→majority` case asserting it does not reach `high`.
4. (Optional nit) don't lead the echo-pill authoring comment with `{{ECHO_PILL}}`.
5. Merge.

### 5. Invariants & guardrails to keep green
- **Byte-identity for old dirs**: `render_echo_lines(None) == []` (`artifacts.py:369`) and the pill-drop regex covers the trailing-space class form. Keep the goldens as the enforcement.
- **`VERDICT:` stays the only gating token**: `basis` feeds the metric only (`rounds.py:86-91`), never the verdict chain — preserve.
- **Sidecar read stays realpath-confined + symlink-refused** (`render_verdict.py:795-816`) and renderer-independent of any validator.
- **Same-provider = scored population only**: the discount must never again read `config.board`.
- **Drift warning is stderr-only, non-fatal, fires once** — don't let it migrate onto stdout or into an exit code.

### 6. Concrete evidence
- Discount over scored seats: `echo_score.py:208-219`, `echo_score.py:186`; provider is real: `rounds.py:49,151`.
- Two-arg call, `board_size` removed: `cli.py:467-469` (+ empty `grep board_size`).
- Like-for-like sha: `config.py:507-509` vs `recipe.py:257`; `config.py:151-153` (`grounded == bool(repo)`); `recipe.py:284,292` (conditional keys).
- `parse_basis` faithfully mirrors `parse_verdict` (same `_is_quoted_verdict_line` guard, single-hit + first-word-leads + last-clean-line-wins): `convergence.py:127-151` vs `90-112`.
- Doc reconciliation: `echo_score.py:43-53`, `artifacts.py:358-374`, epistemics.md degradation paragraph.
- Stale count: `CHANGELOG.md:23` ("Suite 1355 → 1395") vs stated 1403.
- `None→flip`: `echo_score.py:170-173`.

### 7. What I'd ask the other seats to challenge
- **Codex (who blocked hardest last round):** does the *warning* remedy actually discharge your Blocker 3, or do you still want the recorded sha to gate/refuse a pre-P2 replay? If a warning is enough, say so on the record so it isn't re-litigated.
- **Anyone who can run code:** please execute the suite + byte-identity goldens and post the real count — I was sandbox-blocked, and my SHIP-vs-CAUTION split hinges only on that confirmation plus the CHANGELOG integer.
- **On the `None→flip` edge:** is counting a parse-failure→token as a "social flip toward the majority" acceptable as-documented, or worth the one-line `prev_v is not None` guard before it can reach `high`?
- **On the board-global discount:** are we comfortable that one duplicate pair discounts an otherwise cross-provider board, or is pair-scoped discounting a v1.15 item?

VERDICT: caution

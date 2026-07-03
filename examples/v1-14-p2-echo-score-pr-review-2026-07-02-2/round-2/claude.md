I've completed my independent verification. Both of Codex's findings check out (with one severity correction), the three fix-pass items I was told to scrutinize hold, and I found no additional live defect. Here is my complete round-2 review.

---

# Claude seat — round 2 (v1.14 P2 / #9, independence / echo score)

## 1. Updated verdict

**CAUTION — confidence medium-high.** The three round-1 blockers are genuinely resolved and I re-confirmed the sha-drift remedy is sound, but Codex surfaced a real defect I missed in round 1 (`_same_provider` collapses two `None` providers, contradicting its own thrice-stated "None counts as distinct" contract), plus a doc-reconciliation miss the Blocker-2 pass left behind in `render_verdict.py`. Neither gates anything; both are fixable in minutes.

**What would flip it to SHIP:** make `_same_provider` treat each `None` as distinct (matching the documented rule) + add the missing two-`None` regression test, and reconcile the two stale "pre-P2 recipe" comments in `render_verdict.py`. What would flip it to BLOCK: a live correctness or byte-identity break — I found none.

## 2. Where I changed my mind / where I still dissent

- **Changed, toward Codex (evidence, not deference):** In round 1 I wrote that I "could not find a substantive new defect of the class the pattern predicts." **Codex found it** — `_same_provider()` at `echo_score.py:219` uses `len(set(providers)) < len(providers)`, and Python collapses `{None, None}` → `{None}` (len 1 < 2), so two missing-provider seats read as *same-provider* and fire the discount. That directly contradicts the rule stated at `echo_score.py:214`, the module docstring, and the `echo_score` docstring ("a seat with a missing/None provider counts as DISTINCT"). I verified it against the diff and the runtime — it is real, and it is this fix pass's new defect (the function is brand-new this pass). I retract my round-1 "no new defect" claim.

- **Still dissent from Codex, on severity:** Codex says this "can downgrade a mixed/unknown-provider high-risk case to moderate." On a **real run it cannot** — `SeatRoundResult.provider` is a non-optional `str` (`rounds.py:49`) populated from `seat.provider` (`rounds.py:151`), which is `self.adapter.provider`, always a REGISTRY-supplied string (`config.py:80-81`). `.provider` is never `None` outside hand-built fixtures. So the live blast radius is nil; the real defect is (a) code contradicting its own documented contract, (b) a latent bug the defensive `getattr(r, "provider", None)` explicitly anticipates, and (c) a test hole. We agree it must be fixed; I disagree it is currently reachable on a real board.

## 3. Strongest remaining objections

1. **`_same_provider` contradicts its own contract (`echo_score.py:208-219`).** The headline says "counts as a DISTINCT provider"; the parenthetical at `:215` half-admits the opposite ("two `None`-provider seats DO share the same unknown"); the code implements the parenthetical. Pick one — and the module/`echo_score` docstrings and `epistemics.md` all assert *distinct*, so the code is the outlier. Fix: `providers = [getattr(r, "provider", None) or object() for r in overlap_seats]` — no wait, that also swallows empty strings; cleaner is to drop `None`s before the duplicate check (`known = [p for p in providers if p is not None]; return len(set(known)) < len(known)`) or map each `None` to a unique sentinel.

2. **The regression suite has a hole exactly at the bug.** `test_none_provider_counts_as_distinct_no_discount` only exercises **one** `None` seat (`{Anthropic, None}` → len 2, so it happens to pass). There is no `[None, None]` case — which under the current code would fire the discount and **fail** the stated rule. Add it; it's the test that would have caught this.

3. **Blocker-2 reconciliation is incomplete in `render_verdict.py`.** Codex flagged stale "pre-P2 recipe → no echo-score.json" claims. `epistemics.md`, the `echo_score` docstring, `CHANGELOG`, and `artifacts.py` were fixed, but two spots survive: `_echo_pill_fields` docstring (`render_verdict.py:821`) lists "pre-P2 recipe" among the empty-pill cases, and the `build_handoff_data` comment (`render_verdict.py:1282`) says "old run dir / pre-P2 recipe with no echo-score.json." A pre-P2 recipe **replayed** scores normally and renders a real pill — that's the whole Blocker-2 correction. Runtime is correct (the code keys off `echo-score.json` presence + band, not off "is this a pre-P2 recipe"), but the review's own bar was "doc-vs-code EXACTNESS after the reconciliation," and these two miss it.

## 4. Recommended execution sequence

1. Fix `_same_provider` so each `None`/missing provider is distinct; keep the docstring's headline, delete the self-contradicting parenthetical at `echo_score.py:215`.
2. Add the `[None, None] → distinct → no discount → high` regression case beside `test_none_provider_counts_as_distinct_no_discount`.
3. Reconcile `render_verdict.py:821` and `:1282` to the Blocker-2 story (a pre-P2 recipe *replayed* scores normally; the empty-pill cases are single-round run, old run dir, unreadable/absent sidecar, or `not_computed`).
4. Fold the fix-pass tests into the CHANGELOG P2 count ("Suite 1355 → 1403", not 1395) and re-scan that block for other count/version drift.
5. Re-run the full suite **and** the byte-identity goldens on the staged tree; confirm still-green.

## 5. Invariants and guardrails

- **`VERDICT:` stays the only gating token.** `basis` feeds the metric only (`rounds.py` `basis` property; `parse_basis` mirrors `parse_verdict`'s failure-tolerance including the quoted-line skip) — verified it never reaches the verdict chain.
- **The score never gates.** Advisory-only; a `high` band is not a verdict. Keep it that way — this is what makes both open defects CAUTION and not BLOCK.
- **Byte-identity for old dirs.** `render_echo_lines(None) == []` (`artifacts.py`), the pill-drop regex absorbs the trailing-space class form (`render_handoff.py`), and the goldens (`test_absent_echo_body_byte_identical_to_pre_p2`, `test_byte_identity_no_echo_vs_none`) enforce it. Do not let the `_same_provider` fix touch any of this.
- **Scored population = overlap seats, everywhere.** The discount now reads `.provider` off the same population every sub-signal scores (`echo_score.py`), and `board_size` is gone from the call sites (`cli.py` two-arg call). Preserve that coupling — the fix must stay inside `_same_provider`.

## 6. Risks, stale assumptions, missing evidence

- **Assumption to make explicit:** `.provider` is never `None` on a real run today. If a future adapter or a partial-init path can yield `None`, defect #1 becomes live — so fixing it now is cheap insurance, not just doc hygiene.
- **Verified sound (no action):** `_warn_on_template_drift` — `sys` is imported (`config.py:8`); it receives a dict (`recipe_to_config -> dict`, `recipe.py:401`); the like-for-like sha is faithful because `config.grounded == bool(config.repo)` (`config.py:153`) and the recipe stores `repo` only when grounded (`recipe.py:284`); it fires once per load; the missing-field path returns cleanly. Codex's Blocker-3 remedy is discharged by the warning.
- **Missing evidence I did not independently reproduce:** the "1403 OK" suite run and the full HTML byte-identity golden on the *exact* staged tree — hence step 5. My reads were of the staged files, not a live run.

## 7. Concrete evidence

- None-collapse defect: `echo_score.py:219` (`len(set(providers)) < len(providers)`) vs. the "counts as a DISTINCT provider" claim at `echo_score.py:214` and the self-contradicting `:215`.
- Provider is never `None` at runtime: `rounds.py:49` (`provider: str`), `rounds.py:151` (`provider=seat.provider`), `config.py:80-81` (`return self.adapter.provider`).
- Test hole: `test_none_provider_counts_as_distinct_no_discount` covers `{Anthropic, None}` only (len 2 — passes by accident); no `[None, None]` case.
- Stale reconciliation: `render_verdict.py:821` and `render_verdict.py:1282`.
- Drift warning verified sound: `config.py:8` (`import sys`), `config.py:153` (`grounded = bool(self.repo)`), `recipe.py:284` (`recipe["repo"] = config.repo`), `recipe.py:401` (`recipe_to_config(...) -> dict`).
- CHANGELOG count drift: P2 bullet "Suite 1355 → 1395" vs. shipped 1403.

BASIS: evidence
VERDICT: caution

# Board packet — round 2 (cross-reading: summaries — structured digest)

## Where the board stands after round 1

Verdicts: claude=caution · codex=caution
Agreement: unanimous: caution
Shared evidence (raised by ≥2 seats): `not_computed`

## By topic

### Verdict

- **claude:** **CAUTION** — confidence **medium-high**. All three prior blockers are genuinely resolved (I verified each against the real tree, not the diff's word), and I could not find a substantive new defect of the class the pattern predicts. What …

### Recommended execution sequence

- **claude:** 1. Correct `CHANGELOG.md:23` to the real shipped suite count (1403), and re-scan the P2 changelog block for any other count/version drift. 2. Independently run the full suite **and** the byte-identity goldens on the exact staged tree; …

### Invariants & guardrails

- **claude:** - **Byte-identity for old dirs**: `render_echo_lines(None) == []` (`artifacts.py:369`) and the pill-drop regex covers the trailing-space class form. Keep the goldens as the enforcement. - **`VERDICT:` stays the only gating token**: `basis` …

### Concrete evidence

- **claude:** - Discount over scored seats: `echo_score.py:208-219`, `echo_score.py:186`; provider is real: `rounds.py:49,151`. - Two-arg call, `board_size` removed: `cli.py:467-469` (+ empty `grep board_size`). - Like-for-like sha: `config.py:507-509` …

### Challenges to the board

- **claude:** - **Codex (who blocked hardest last round):** does the *warning* remedy actually discharge your Blocker 3, or do you still want the recorded sha to gate/refuse a pre-P2 replay? If a warning is enough, say so on the record so it isn't …

### codex — review (no section headers found; head excerpt)

1. **Verdict: CAUTION, medium confidence.** What would change it: fix the `None` provider duplicate case, update the stale “pre-P2 recipe” comments/docstrings, add regression coverage, and rerun the suite. 2. **Strongest Objections** - The same-provider fix is not fully correct for the stated `None` rule. The docs say missing/`None` provider counts as distinct, but `_same_provider()` uses `set(providers)`, so two `None` providers collapse into one provider and trigger the discount. That can downgrade a mixed/unknown-provider high-risk case to moderate. - Some reconciliation comments still say pre-P2 recipes have no `echo-score.json`, which is now false for replayed pre-P2 recipes. Runtime behavior is okay, but …

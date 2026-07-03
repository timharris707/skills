I have what I need. Both verification agents reported back, and I've confirmed the critical claims against the actual staged tree. Here is my review.

---

# Claude seat review — v1.14 P2 (#9): independence / echo score

## 1. Verdict

**CAUTION** — confidence **medium-high**. The metric is genuinely well-built and honest, byte-identity holds, the injection surface is closed, and no stale constants leaked. But the feature's *headline* honesty property — the same-provider discount — is computed from the wrong population and can emit a confident, un-caveated **"high echo risk"** on two same-provider seats in a reachable edge case. That is exactly the kind of misleading artifact this skill must not produce.

**What would change it to SHIP:** derive the same-provider signal from the providers of the seats actually *considered* (usable in both final rounds), not the full configured board — or, if the team judges the edge too narrow to fix, add it explicitly to the `epistemics.md` limits list and soften the claim. Either is cheap.

## 2. Strongest objections

**① The same-provider discount reads the wrong seat population (the one real defect).**
`cli.py:468` computes the honesty hook as `distinct_providers = len({s.provider for s in config.board})` — distinct providers over the **full configured board**. `echo_score` then decides same-provider via `_same_provider(board_size, considered)` → `board_size < considered`, where `considered` = seats **usable in both final rounds** (`overlap_seats`). These are two different populations. Concretely, on `--board claude,claude,codex`, if the `codex` seat is unusable in one of the two final rounds, then `considered = 2` (the two `claude` seats) but `board_size = 2` (distinct providers `{claude, codex}` over the *configured* board). `2 < 2` is **False**, so:
- the two same-provider seats are scored as a *mixed* board — their structurally-expected citation overlap is allowed to corroborate a `strong_flip` into a **false HIGH** (`_band`: `echo_signal and high_overlap`), and
- `_explain` **omits** the "same-provider board, where high citation overlap is expected and is not counted as echo on its own" caveat (it too is gated on `_same_provider(...)`).

So the artifact says *"High echo risk … 78% citation overlap"* about two clones, with the one sentence that would explain it stripped out — in precisely the scenario the discount exists to handle. It over-flags (the safe direction) and the trigger is narrow, but it's a correctness gap in the differentiator, and the fix is principled. Note the common case (`--board claude,claude`, 2 seats, no drop) works correctly (`1 < 2`), which is why the tests pass.

**② The unconditional template bump silently changes replay for *every* pre-P2 recipe.** The stale-constant sweep confirmed prompts are **regenerated from the current in-code templates on every run, including `--from-recipe`** (`prompt_template_sha()` recomputes; no raw bytes are stored), and nothing compares the recipe's recorded sha against the recomputed one. Unlike P4's grounding clause (conditional — non-`--repo` recipes replayed byte-identically), the `BASIS` line is added to **every** round-2, so any recipe saved before this PR now replays with BASIS-injected prompts, different seat behavior, and a different sha — with no drift warning. This is not a defect *in the diff* (replay code is untouched) and "replay stays exact" holds *within* a version, but it is a broader compatibility break than P4 and worth an explicit acknowledgement for recipe users.

**③ Final-transition-only is a real blind spot, not just a limit line.** `cli.py:469` scores `rounds_done[-2] → [-1]` only. A 3-round board that echoed hard in 1→2 and then diverged 2→3 reads **LOW** — a confident-but-incomplete signal. It's documented in `epistemics.md` ("reads only the final transition"), but a "low echo" pill on a settled-after-echo board is the failure mode a reader is least equipped to catch.

**④ Suite-green (1395) is unverified in this environment.** Plan mode blocked me from running `pytest`. The version/sha test assertions are internally consistent with the code (verified statically), but the "1355 → 1395 OK" claim remains the implementer's own.

## 3. Recommended execution sequence

1. **Fix objection ①:** expose `provider` on `SeatRoundResult` (or pass the considered seats' provider *set* from `cli.py`), and base `_same_provider` on distinct providers **among the considered seats**. Then `claude,claude,codex`-with-codex-dropped correctly discounts.
2. **Add the regression test that would have caught it:** a 3-seat mixed board where a distinct-provider seat drops from one final round → the two same-provider seats must **not** reach HIGH from overlap alone, and the explanation **must** carry the same-provider caveat. (The existing `TestEchoScoreSameProvider` only covers the clean `board_size=1` path.)
3. **If deferring the fix:** add the edge to the `epistemics.md` limits list and drop the confidence of the "does not count overlap as echo there" claim.
4. **One line for recipe users** (CHANGELOG/epistemics): the unconditional round-2 bump means pre-P2 recipes replay *differently*, not identically — distinguish "old-run **re-render** stays byte-identical" (true, preserved) from "old-recipe **replay** stays identical" (now false across this bump).
5. Re-run the full suite and paste the count.

## 4. Invariants & guardrails (verified)

- **Pure over parsed signals only** — `echo_score` reads only `parse_verdict`/`parse_basis` tokens + `citations` sets, never prose. ✓
- **Absent → not_computed / dropped pill / zero bytes, never fabricated** — `echo_score` <2-overlap degradation; `_echo_pill_fields` returns `("","")` for not_computed/missing; `render_echo_lines([])`. ✓
- **Body byte-identity when the pill is absent** — the template diff is purely additive (comment + pill + blank line), and `render_handoff.py`'s drop regex `\s*(?:<!--…-->\s*)?<p class="echo-pill[^"]*">\s*</p>` consumes the leading whitespace + comment + pill and leaves the following `\n\n  <!-- DELTA -->` exactly as the pre-P2 template had it. Traced by hand; the golden test covers the isolated case. ✓
- **Injection closed** — the explanation embeds only enum bands, the majority *verdict* enum, integer counts, and fixed phrasing (no model prose); `ECHO_PILL` is **not** in `RAW_TOKENS` (`render_handoff.py:112`) so it is HTML-escaped; `ECHO_CLASS` is our own `echo-<band>` literal; `_plain` neutralizes braces. ✓
- **Sidecar read is realpath-confined and refuses a symlink at the file** before opening (`_read_echo_score` → `_confined_path` + `os.path.islink`). ✓
- **Band honesty invariants hold** — overlap-alone can never reach HIGH (`echo_signal` required); any deference is never LOW (≥ MODERATE); a seat flipping *away* from the majority is not counted as echo; `parse_basis` never guesses (omitted → `unknown`). ✓
- **Guardrail to add:** the same-provider signal must track the *scored* population, not the configured board (objection ①).

## 5. Risks, stale assumptions, missing evidence

- **Primary:** `board_size` is a whole-board config fact used as a proxy for "are the scored seats duplicates?" — the proxy breaks under seat drops (`cli.py:468` ↔ `echo_score.considered`).
- **Minor:** `_majority_verdict` counts only non-`None` verdicts, but `considered` (the `frac_flip` denominator) includes usable-but-no-clean-verdict seats, slightly diluting `frac_flip`. Benign, but the denominator and the majority basis differ.
- **Assumption:** "1395 OK" — unverified here (execution blocked). Recommend the implementer re-run and paste.
- **Assumption:** recipe users expect replay to reproduce the recorded run (objection ②).
- **No stale constants** — swept `round2@2/@3/@4`, `round1@2/@3`, `27f5d18e…`, `db40e538…`, `11f5fae2…`, `ROUND2_TEMPLATE_VERSION`: every hit is either correctly updated or a labeled historical comment. No `examples/` goldens carry template shas.

## 6. Concrete evidence

- `scripts/_conductor/cli.py:468` — `distinct_providers = len({s.provider for s in config.board})` (full configured board).
- `scripts/_conductor/config.py:80-81` — `provider` is `self.adapter.provider`; `:108` — `board: list # list[SeatConfig]` (unfiltered by usability).
- `scripts/_conductor/echo_score.py` — `overlap_seats = [r for r in curr if r.seat in prev_by]`; `considered = len(overlap_seats)`; `_same_provider(...): return board_size is not None and board_size < considered`; `_band` mixed branch `if echo_signal and high_overlap: return "high"`; `_explain` gates the caveat on `if _same_provider(board_size, considered):`.
- `scripts/_conductor/prompts.py:456` `ROUND2_TEMPLATE_VERSION = "advisory-board/round2@3"`, `:249` grounded `round2@4`; `BASIS_LINE_INSTRUCTION` spliced *before* `VERDICT_LINE_INSTRUCTION` (VERDICT stays genuinely last).
- `scripts/render_handoff.py:112` `RAW_TOKENS = {…}` — `ECHO_PILL` absent ⇒ escaped slot.
- `parse_basis` mirrors `parse_verdict` byte-for-byte (shared `_is_quoted_verdict_line`, `_FIRST_WORD = [A-Za-z]+`), confirmed against `convergence.py`.
- Quote worth pinning, `epistemics.md`: *"a same-provider board … the metric does not count overlap alone as echo there and says so in the explanation."* — true only when `board_size < considered`, which is what objection ① breaks.

## 7. What I'd ask the other seats to challenge

- **Codex/generalist:** is objection ① worth a code fix now, or acceptable as a documented limit given it only over-flags on a nichey board-plus-drop? Push back on my CAUTION if you think the edge doesn't justify it.
- **Windowing:** for N>2 runs, is scoring only the final transition right, or should the metric report per-transition (or the max echo across transitions)? Does a "low echo" pill on an echoed-then-diverged board mislead more than it helps?
- **Replay stance:** given the *unconditional* bump makes every pre-P2 recipe replay differently, does "`--from-recipe` replay stays exact" now warrant a recorded-sha-vs-recomputed drift warning?
- **Should same-provider boards be scored at all?** Or degrade to `not_computed` — is `flip + deference` on clones really strong echo evidence, or just noise?
- **The 50% `strong_flip` threshold on 2-seat boards:** one seat converging = 0.5 = `strong_flip`. Is a single seat joining the other "board-wide echo," or an artifact of small-N?

VERDICT: caution

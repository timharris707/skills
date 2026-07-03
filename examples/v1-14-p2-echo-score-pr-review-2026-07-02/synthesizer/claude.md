```json
{
  "verdict": "block",
  "confidence": "low",
  "blockers": [
    {
      "title": "Same-provider discount reads the wrong seat population",
      "body": "The same-provider echo discount is derived from the distinct providers across the FULL configured board (cli.py computes `len({s.provider for s in config.board})`), but `_same_provider` compares that count against the CONSIDERED / final-round overlap seats. Under seat drops the two populations diverge, so the discount both under-applies and over-applies: a `[claude, claude, codex]` board with codex dropped yields board_size=2, considered=2, so the discount does not fire and two same-provider seats' high overlap is wrongly flagged as echo; a `[claude, codex, gemini, gemini]` board with all considered fires the discount and treats a genuinely cross-provider majority as expected overlap. Claude raised this as a correctness must-fix with tests; Codex corroborated it as a concern it viewed as downstream of the dropped-seat policy. `SeatRoundResult.provider` is already exposed, so same-provider can be computed directly over the overlap seats without new plumbing.",
      "evidence": [
        { "kind": "code", "path": "scripts/_conductor/cli.py", "line": 468 },
        { "kind": "code", "path": "scripts/_conductor/echo_score.py", "symbol": "_same_provider" },
        { "kind": "code", "path": "scripts/_conductor/rounds.py", "line": 49 },
        { "kind": "judgment", "detail": "Board-traced counterexamples: [claude, claude, codex] with codex dropped -> discount does not fire and two same-provider seats are flagged as echo; [claude, codex, gemini, gemini] all considered -> discount fires on a cross-provider majority." }
      ]
    },
    {
      "title": "DECISION docs claim `not_computed` degradations the code never performs",
      "body": "epistemics.md, the CHANGELOG, and the echo_score docstring state that an old run dir and a pre-P2 recipe replayed via `--from-recipe` produce `not computed`, and that `--from-recipe` replay 'stays exact'. Both seats verified this is false: echo_score's only `not_computed` path is `len(overlap_seats) < 2`, with no pre-P2 / all-unknown-basis branch, and whenever >=2 seats overlap the code computes a real band (Codex: it filters to usable overlapping seats and scores; cli.py writes the sidecar regardless of whether a final-round seat dropped). Claude names this the one hard guardrail currently broken — the phase's discipline that 'epistemics.md's published definition must match the code EXACTLY' — and stresses it is a DECISION document making the false claim.",
      "evidence": [
        { "kind": "source", "url": "references/epistemics.md", "quote": "a pre-P2 recipe replayed via `--from-recipe` all produce not computed" },
        { "kind": "source", "url": "CHANGELOG.md", "quote": "--from-recipe replay stays exact" },
        { "kind": "code", "path": "scripts/_conductor/echo_score.py", "line": 33 },
        { "kind": "code", "path": "scripts/_conductor/echo_score.py", "line": 131 },
        { "kind": "code", "path": "scripts/_conductor/echo_score.py", "line": 126 },
        { "kind": "code", "path": "scripts/_conductor/cli.py", "line": 466 }
      ]
    },
    {
      "title": "Pre-P2 `--from-recipe` replay is not byte-exact and the recorded template sha is never validated",
      "body": "`--from-recipe` loads recipe config, but egress always rebuilds round-2 prompts from the CURRENT template, which now appends the BASIS line unconditionally, so a pre-P2 recipe replayed post-P2 egresses new round-2 bytes and a new sha; the recorded `prompt_template_sha256` is never read back on load, so the drift is silent, and cli.py writes `echo-score.json` for any two-round replay. The seats agree on the mechanism but split on severity and remedy (see dissent): Codex reads it as a contract regression and wants old bytes preserved or pre-P2 recipes refused/scoring-disabled; Claude reads it as a doc over-claim plus a missing provenance warning — replay has always used current templates and egress is consented at the gate — and wants the docs corrected and a loud sha-mismatch warning rather than suppression.",
      "evidence": [
        { "kind": "code", "path": "scripts/_conductor/config.py", "line": 505 },
        { "kind": "code", "path": "scripts/_conductor/egress.py", "line": 53 },
        { "kind": "code", "path": "scripts/_conductor/prompts.py", "line": 439 },
        { "kind": "code", "path": "scripts/_conductor/prompts.py", "line": 245 },
        { "kind": "code", "path": "scripts/_conductor/recipe.py", "line": 254 },
        { "kind": "code", "path": "scripts/_conductor/cli.py", "line": 466 }
      ]
    }
  ],
  "dissent": [
    {
      "who": "Codex",
      "body": "Holds BLOCK. Reads the recipe-replay defect as a regression and contract violation — the contract says `--from-recipe` replay stays exact, yet current code rebuilds current round-2 prompts and still scores the replay — which is do-not-proceed, not a caution-level edge. Requires, before ship: preserve old prompt bytes by recorded template/sha or refuse/scoring-disable pre-P2 recipes loudly, and implement the claimed dropped-seat degradation (no sidecar/section or `not_computed`) consistently."
    },
    {
      "who": "Claude",
      "body": "Holds CAUTION. Argues the replay is NOT a regression: recipe replay has always used the current template code, there has never been a historical-bytes path (one round-2 template; prior bumps stayed byte-stable only via conditional placeholders), so P2 merely ends a coincidental byte-stability rather than removing a guaranteed capability, and egress is consented at the gate so nothing is silently sent. Concludes the defect is the docs, not the behavior — scoring a replayed pre-P2 recipe is correct because the current template genuinely requests BASIS — so the fix is to correct the docs and add a sha-mismatch provenance warning, NOT to suppress or scoring-disable (which would blank a valid P2 result). Proceed-with-changes, not do-not-proceed."
    }
  ],
  "concerns": [
    {
      "title": "The mis-populated same-provider band is advisory-only",
      "body": "Claude notes the same-provider proxy never gates, so the blast radius of a wrong band is a misleading advisory in niche board-plus-drop configurations — real but bounded.",
      "evidence": [
        { "kind": "judgment", "detail": "Claude: the echo score is advisory-only (never gates), so a misleading band's impact is limited to niche board+drop configs." }
      ]
    },
    {
      "title": "Recipe provenance records only the round-1 template id",
      "body": "Codex flags that recipe.py records only the round-1 template id/sha while the surface changed by P2 is round 2, so the provenance record does not even name the template that actually drifts on replay.",
      "evidence": [
        { "kind": "code", "path": "scripts/_conductor/recipe.py", "line": 254 }
      ]
    }
  ],
  "caveats": [
    "Neither seat executed the test suite in this read-only review; the reported 1355 -> 1395 test count and green state are trusted from the diff, not run.",
    "Existing tests do not cover pre-P2 `--from-recipe` replay or the three-seat one-dropped-final-round case.",
    "Claude traced the metric's tie / flip-away / empty-Jaccard / 2-seat-majority logic by hand rather than executing it."
  ],
  "open_questions": [
    "Dropped-seat policy: when a final-round seat drops, should echo degrade to `not_computed` / emit no section (as the docs claim), or score the remaining >=2 overlapping seats normally (as the code does)? The seats disagree.",
    "Pre-P2 `--from-recipe` replay: should it be scored as a fresh, now-BASIS-bearing P2 run (Claude), or refused / scoring-disabled (Codex) — and should replay preserve recorded template bytes or only warn on sha drift?"
  ],
  "next_actions": [
    "Fix the same-provider population: drop the config.board proxy and derive same-provider from the overlap seats' own `.provider` (`len({r.provider for r in overlap_seats}) < len(overlap_seats)`); add tests for [claude, claude, codex] with codex dropped (discount fires) and [claude, codex, gemini, gemini] (discount does not fire).",
    "Reconcile docs vs code — either correct epistemics.md, the echo_score docstring, and the CHANGELOG to the real behavior so `not_computed` is reserved for <2 overlapping seats / single-round runs (Claude), or make the code perform the claimed pre-P2/dropped-seat degradation (Codex).",
    "Add recipe provenance handling: on load, compare the recorded `prompt_template_sha256` to the current template sha and warn loudly on mismatch (Claude), or preserve old bytes / refuse / scoring-disable pre-P2 recipes loudly (Codex).",
    "Decide and enforce the dropped-seat policy consistently across cli.py and echo_score.",
    "Add regression tests for pre-P2 recipe replay, a three-seat run with one seat dropped before the final round, and duplicate-provider-with-dropped-other-provider.",
    "Re-run the full suite, confirm the new total, and verify the byte-identity goldens are untouched."
  ]
}
```

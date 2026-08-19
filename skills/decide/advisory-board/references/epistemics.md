# Epistemics: keeping the verdict honest

A multi-model board fails the same way a human panel does: once the seats read each other, they drift toward agreement. A confident, unanimous, *wrong* verdict is worse than three honest disagreements. These rules keep convergence earned, not social.

## Confidence (every seat, every round)

Each seat tags its verdict with a confidence, **low / medium / high**, plus one line on what would change it. Surface it in the handoff (the HTML round head supports a confidence chip). A "block" at low confidence and a "block" at high confidence are different messages; don't flatten them.

## Independence check (round 2+)

When a seat changes position after reading the others, it must say *why*:

- **evidence**: a specific argument, file, or fact another seat surfaced; or
- **deference**: "the others agreed."

Deference is not a reason. If a seat can only cite deference, it should hold its prior position and mark the point unresolved. Record evidence-driven changes in the seat's rebuttal and in the verdict-change highlight.

The round-2+ template makes this check machine-parseable: each seat emits a `BASIS:` line naming what its revised position rests on: **independent** (its own evidence, or it held its prior view), **evidence** (it changed toward another seat because of a specific argument/file/fact *they* surfaced), or **deference** (it changed only because the others agreed). It is a self-reported, advisory token: it feeds the echo score below, it never gates, and it never overrides the one `VERDICT:` token. A seat that omits the line parses as *unknown*, never guessed.

## Independence / echo score (round 2+)

A convergent board can be convergent for two very different reasons: the seats each did the work and independently reached the same answer, or they read each other and drifted into agreement. The second is *echo*: three voices that collapsed into one, reading as authority while carrying one voice's information. The echo score is a coarse, honest flag for that risk.

**What it is.** A pure function over signals the conductor already parses; nothing here reads a seat's prose (principle #1 / §11). Over the **final** round transition (where echo shows, on the settled board) it combines three explainable sub-signals:

- **flip-toward-majority**: of the seats that changed their `VERDICT:` token in the final round, how many moved *onto* the emerging majority verdict (the convergence fingerprint);
- **citation overlap**: the mean pairwise Jaccard overlap of the seats' concrete citation sets (the same inline-code-span + slash-path citations the convergence movement uses);
- **deference count**: how many seats' `BASIS:` line is `deference`, versus `evidence`/`independent`/`unknown`.

These roll up to a **coarse band: low / moderate / high echo risk**, never a false-precision 0–100 number. The one-line explanation always names the sub-signals that drove the band (e.g. "2/2 seats flipped toward the majority with 78% citation overlap and 1 deference declaration"), so the call is auditable. It surfaces in `run-metadata.md` (inside the Convergence section) and as an optional pill in the HTML handoff.

**What it is NOT: the limits.** The score **flags possible echo; it does not prove independence**, and a `high` band is not a verdict on the board. It cannot distinguish echo from these honest cases, so read it as a prompt to look, not a finding:

- Seats can **converge honestly on strong evidence**: the right answer is often singular, and three independent reviewers landing on it looks exactly like echo by these signals.
- **Citation overlap is expected when the source is small**: if there are only a handful of files or lines to cite, every seat cites them; on a **same-provider board** (e.g. `--board claude,claude`) overlap is expected structurally, so the metric does not count overlap alone as echo there and says so in the explanation.
- The **deference token is self-reported**: it records a seat's own account of why it moved, which a seat can misreport (over- or under-claiming); an omitted token is `unknown`, never inferred.
- It reads only the **final** transition and only **parsed** signals: a seat that echoed in prose while keeping its token and citations is invisible to it.

Because it is a metric, it degrades honestly. **`not computed`** is reserved for exactly two cases, a run with no final transition to score: a **single-round run** (no round N-1 → N transition, so no sidecar and no section at all), and a run where **fewer than two seats are usable in both final rounds**. Two related cases are *not* `not computed`: an **old run dir** re-rendered has no `echo-score.json`, so the pill/section are simply **absent**: nothing is computed or claimed; and a **pre-P2 recipe replayed via `--from-recipe`** runs with the *current* round-2 template (which carries the `BASIS:` line), so it **scores normally** like any fresh run; if its seats state no basis it scores with an all-`unknown` BASIS tally (the deference sub-signal contributes nothing and the explanation names how many seats did not state a basis), an honest band, never a fabricated one.

## Minority report (when the board converges)

If the board reaches a **unanimous** verdict, it must still produce the strongest case *against* that verdict before the handoff is final. Assign one seat (or the neutral synthesizer) to argue the other side in good faith. Put it in the handoff's dissent section, flagged as the minority report. If the steelman survives scrutiny, the verdict wasn't as settled as it looked: add a round or lower the confidence.

## Known vs. inferred vs. unverified (shared blind spots)

The minority report attacks the verdict from *inside* the board's knowledge. The larger danger sits outside it: a fact every seat assumed and none checked. Three models sharing one blind spot converge confidently and are still wrong, and the convergence reads as authority. The mitigation is to make the boundary of what was actually checked explicit, so the synthesis separates three things:

- **Evidence-backed**: tied to a specific file, fact, run, or citation a seat produced.
- **Judgment calls**: reasoned positions the board holds but can't prove in this run.
- **Couldn't-verify**: claims the board *relied on* but did not check: assumptions taken on faith, anything outside what any seat could see (live data, production config, the real code when only a plan was reviewed), and what would flip the verdict if it turned out false.

A handoff that can't name a single thing it couldn't verify is usually overconfident, not thorough. The HTML handoff carries a dedicated "What the board couldn't verify" section; fill it. Drop it only when the board genuinely verified everything load-bearing; and then say so explicitly rather than deleting it silently.

## Neutral synthesizer

The chair (the orchestrating agent) should not both debate and write the final verdict. Prefer one of:

1. **Separate synthesizer.** A model/seat that did not debate writes the synthesis from the seats' artifacts.
2. **Blind merge.** Each seat drafts the consensus independently; the chair merges mechanically, preferring points that multiple seats reached.

If the chair must also synthesize, say so in the handoff and lean on the minority report to counter chair bias.

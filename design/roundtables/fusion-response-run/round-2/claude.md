I have what I need. I've verified the load-bearing claims against the tree; writing my round-2 review now.

---

# Round 2 — Claude seat (Market & user value lens)

## 1. Updated verdict

**CAUTION — proceed, but only with the reframing and sequencing below. Confidence: high.**

What would change it: hard demand evidence that buyers want an *inline answer-improver* (Fusion's job) more than a *gateable decision artifact* (our job). If that showed up, I'd flip from "differentiate" to "compete," and much of my dissent with Codex would dissolve. Absent that evidence, competing on Fusion's turf is the losing move.

The board is unanimous caution and I keep that. My round-1 framing objection survives contact with the other reviews, but I've narrowed where I actually disagree with Codex — see §2.

## 2. Where I changed my mind / where I still dissent

**Changed my mind (toward Codex, partially).** In round 1 I called candidate #1 ("biggest capability gap") a *category error* and treated it as near-distraction. Reading **Codex**'s exact construction — "a thin local tool/CLI/MCP wrapper over existing conductor, **not a new hosted API**" — I concede the inline mode is worth building **now**, because it's the feature that makes the positioning *true* rather than aspirational. A buyer can't "escalate to your board from inside your agent on your subscription" today: I verified there is **no inline/MCP/server-tool surface in the tree** — the conductor exposes only `init, preflight, toolchain, run, render, consensus, verify, validate` (`scripts/_conductor/cli.py:592-644`). So the gap is real; I was wrong to wave it off.

**Still dissent — with Codex, on framing and on rank order.** I do **not** accept "biggest GTM gap *versus Fusion*." That frame casts us as a follower closing a gap on a competitor's product. The local-MCP board is a *differentiator to seize* (subscription, gate, privacy — none of which Fusion has), not a *parity feature to ship*. The distinction is not pedantic: it decides whether marketing says "we also do inline now" (commodity, we lose) or "escalate to a board your CI can gate, on your own subscription, that never ships your code anywhere" (category of one). And on rank: Codex makes inline *the* milestone; I rank **#6 positioning first**, because shipping the MCP wrapper without the reframe just produces a worse, free Fusion.

**Still dissent — with the implicit pro-benchmark lean (#5).** A DRACO-style "debate beats solo" number is a market *liability* risk, not just an asset — see §3 and §6.

**Agree with Gemini**, fully, on the CLI-background-execution DX problem (§5) and on read-XOR-network as inviolable.

## 3. Strongest remaining objections

**A. The jobs-to-be-done are different products; conflating them is the core risk.** Fusion's JTBD: *"I'm an agent mid-task, being wrong is expensive, give me a better answer now"* — an answer-improver priced per call, one team owns the gateway. Our JTBD: *"I have a high-stakes plan/architecture/decision and I want a defensible, debated verdict my CI can gate and that I can trust against my own code, at ~$0 marginal, without the code leaving my machine."* Those are **different buyers**. Every candidate should be scored against *our* JTBD, not Fusion's feature list. Most of the packet's framing scores against Fusion's.

**B. The "+6.7 from 2×Opus" result quietly threatens our entire pitch.** The packet's own number says most of the lift is **synthesis / test-time compute, not model diversity and not debate**. We have **no evidence** our cross-read-and-revise loop beats Fusion's cheaper *compare-don't-merge*. If we publish a deep-research accuracy benchmark (#5) and it shows debate ≈ compare, we've spent credibility to disprove our own headline. The benchmark is a coin-flip we don't need to call yet.

**C. Our differentiators have a demand-side crack: the three-frontier-model promise is fragile.** I verified `isolates_network=false` for both Google seats (`registry.py:449,475`) and the auth hint: *"Google account; consumer tiers sunset 2026-06-18 — enterprise/API only"* (`registry.py:455`). For a buyer without enterprise Google auth, the default "three frontier models" board silently becomes two, and the gemini seat can't be de-networked so it can't even sit on a gate+`--repo` run. The "panel of frontier models on your subscription" pitch is partly true today. That's a positioning honesty constraint, not just an ops bug.

## 4. Recommended execution sequence (ranked by leverage-per-cost, market lens)

1. **#6 Positioning — ADOPT NOW (week 1, ~$0).** Rewrite the one-liner to: *"a deliberation **workflow** with a gateable, abstaining verdict — runs on your subscriptions at ~$0 marginal, and can review your own code without it leaving the machine."* Name the moat explicitly: debate + economics + privacy/local + a verdict CI can gate. This is the cheapest, highest-leverage move and it's the precondition for #1 landing as a differentiator instead of a me-too.
2. **#1 Inline escalation — ADOPT NOW, but built as a *local, gate-preserving MCP/CLI wrapper over `run_board.py`*, no metered path.** Rationale: it's what makes the positioning real and is a genuine wedge (Fusion has no gate, no subscription economics, no local mode). Main risk: an inline mode that bypasses the egress/consent gate (`scripts/_conductor/egress.py`) or the read-XOR-network rule to "feel fast" — that forfeits the exact moat #6 sells. Evidence that would change rank: if the existing conductor *can't* be wrapped without a new metered path or gate weakening, demote it.
3. **#4 Crisper structured output — DEFER, informational-only.** One-line rationale: our `caveats[]` couldn't-verify bucket plus typed `evidence[]` (`references/verdict-schema.md:73-92`) already serve the decision JTBD; `partial_coverage`/`unique_insights` are *comparison* fields for an *answer* artifact. Adopt only as display sugar that **never** becomes a gate input. Risk: schema bloat that dilutes the gate's legibility. Evidence to change: users asking for the side-by-side coverage map specifically.
4. **#5 Published benchmark — DEFER, and reframe the metric.** Don't benchmark deep-research accuracy (Fusion's turf, and objection B says we might lose). Benchmark **gate precision/recall** — does the abstaining gate catch decisions a solo model would ship that turn out wrong? That's a number *no competitor can match because they have no gate*. Risk: building Fusion's benchmark by reflex and handing them a favorable comparison.
5. **#3 MCP/domain-tool pass-through — REJECT for the gate path, DEFER for advisory-only.** Collides head-on with read-XOR-network (`SKILL.md:86`). Low market value relative to the invariant risk it imports.
6. **#2 Sandboxed execution seats — DEFER** (separate deep-dive run owns it; from the market lens it's not load-bearing for the Fusion response).

**Single highest-leverage move:** ship #6 + #1-as-local-MCP **together** — "the board you escalate to from your own agent, on your subscription, that returns a verdict your CI can gate and never sends your code anywhere." That sentence is both the positioning and the product.

**The one thing to refuse:** a **metered, hosted inline API** that competes with `openrouter/fusion` on its own pass-through-priced, server-side terms. It trades our three structural moats (≈$0 marginal, local/private, gateable) for a commodity slot in someone else's gateway. Equivalently: never let a gate-bearing run go networked to feel inline.

## 5. Invariants & guardrails

- **The gate never reads soft signals.** Verified: `gate_outcome` reads each seat's `round_verdicts[-1]` and the docstring states *"never the gameable `confidence`"* (`board_verdict.py:239,244-245`). Any #4 field must be informational-only; it must not enter `gate_outcome`.
- **Abstain semantics stay sacred.** A refuted citation → abstain (exit 3), and a declared verdict that de-escalates below a majority-tripping board → abstain (`board_verdict.py:240-242,257-264`). The inline mode must preserve exit-3 abstain, not collapse it into a binary answer to look like a model.
- **Read XOR network on any gate-bearing/`--repo` run** (`SKILL.md:86`; enforced by `isolates_network` in `registry.py`). The inline wrapper inherits this unconditionally.
- **Inline mode reuses the egress/consent gate** (`scripts/_conductor/egress.py`) — no new path that ships bytes without the hash-bound pre-spawn stop and data-handling disclosure (`SKILL.md:17`).
- **A board is still ≥2 seats that actually ran** (`board_verdict.py:172-174`); an inline "one-shot board" must not quietly become a one-seat call dressed as a board.

## 6. Risks, stale assumptions, missing evidence

- **Missing — the core market datum:** do buyers want an inline answer-improver or a gateable decision artifact? Everything above hinges on it and we have only inference. This is the thing to go learn before over-investing in #1.
- **Missing — any proof debate > compare.** See objection B. We're asserting a value prop the packet's own 2×Opus number undercuts.
- **Stale/internal drift:** `SKILL.md:49` advertises the Gemini seat as "Gemini 3.1 Pro," but the registry default is `gemini-3.5-flash` (`registry.py:440`). Couldn't-verify which is canonical from here; either way the public-facing model claim and the code disagree, which is a positioning-honesty bug.
- **Demand risk:** the Google-tier sunset (`registry.py:455`) means the marquee "three frontier models on your subscription" is, for many users, two — and the third can't sit on a gated repo run. Positioning must not oversell the default lineup.
- **DX risk (Gemini's, endorsed):** the seats are interactive subscription CLIs; an inline/MCP mode that spawns them in the background is the hard part, and getting it wrong produces a worse experience than the full run it's meant to shortcut.

## 7. Concrete evidence

- `scripts/_conductor/cli.py:592-644` — subcommands are `init/preflight/toolchain/run/render/consensus/verify/validate`; **no inline/MCP/server-tool surface exists**. The capability gap is real. **[verified]**
- `scripts/board_verdict.py:239` — *"The decision reads each seat's final-round verdict, never the gameable `confidence`."* The gate is uncontaminated by soft fields. **[verified]**
- `scripts/board_verdict.py:240-242, 257-264` — abstain (exit 3) on a refuted citation and on a verdict that de-escalates below a majority-tripping board. **[verified]**
- `scripts/board_verdict.py:172-174` — *"a board needs >= 2 seats that ran; … dropped seats don't count."* **[verified]**
- `scripts/_conductor/registry.py:449,475` — `isolates_network=False` for gemini and antigravity, *"no known flag disables GoogleSearch grounding — surfaced loudly."* **[verified]**
- `scripts/_conductor/registry.py:455` — gemini auth hint: *"consumer tiers sunset 2026-06-18 — enterprise/API only."* **[verified]**
- `SKILL.md:86` — *"the safety policy is **read XOR network** … Seats that can't be de-networked (today gemini, antigravity) make a gate+`--repo` run **refuse**."* **[verified]**
- `references/verdict-schema.md:73-92` — `blockers/dissent/concerns` carry typed `evidence[]` (`code|source|command|judgment`); `caveats[]` is the couldn't-verify bucket. No `partial_coverage`/`unique_insights` today — #4 would be additive. **[verified]**
- `scripts/_conductor/egress.py:1-3` — the hash-bound, tiered-consent *"pre-spawn hard stop"* that any inline mode must reuse. **[verified]**
- Fusion benchmark / "+6.7 from 2×Opus," pass-through pricing, server-tool beta — **[packet-only]** (not checkable against this tree).

VERDICT: caution

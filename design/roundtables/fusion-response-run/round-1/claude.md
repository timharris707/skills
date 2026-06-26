I have enough grounding. Producing the review directly as my reply, per the task instructions (read-only, no files).

---

# Claude seat — Market & User Value lens

## 1. Verdict

**CAUTION — proceed, but only with the reframing below.** Confidence: **medium-high.**

The plan's instincts are mostly right, but its headline framing is wrong in a way that matters commercially. Candidate #1 ("inline escalation mode") is the right priority, but the brief calls it our "biggest capability gap vs Fusion" and frames it as catching up to Fusion's product. That's the trap. **The gap is real; closing it by imitating Fusion's hosted-metered inline model would forfeit the only moat we have.** Adopt the inline wedge in its *local, subscription-backed, gate-bearing* form — and lead with positioning (#6), not as a consolation prize but as the load-bearing move.

**What would change the verdict:** if a quick internal eval (a stripped DRACO-style run) showed our multi-round *debate* does **not** beat a cheaper *compare-and-synthesize* of the same seats, the whole differentiation story collapses to "expensive single-model with extra steps," and I'd downgrade to block-and-rethink. The DRACO 2×Opus result in the packet is a live warning shot at exactly this. See §5.

## 2. Strongest objections (market lens)

**A. "Biggest capability gap" is a category error.** Fusion's inline model id is the *commodified* version of this idea — pass-through priced, one team owns the gateway. If we ship a metered inline API to match it, we compete on their turf, with their cost structure, against the team that controls routing. We lose that race. Our latent advantage is the *opposite* shape: ~$0 marginal on subscription CLIs (verified: `registry.py:23`, `auth_hint` fields show subscription auth across seats), a local-only board for sensitive material (`registry.py:494`, `provider="local"`), and a **gateable verdict that abstains** (`board_verdict.py:223`). The job-to-be-done Fusion serves — "give an agent a deeper second opinion mid-task, when being wrong is expensive" — we can serve *better* at the moment of escalation, because we attach a CI-gradeable verdict to the answer, not just prose. Reframe #1 as "the escalation an agent can wire into a gate for free," not "our answer to Fusion's model id."

**B. The DRACO 2×Opus finding undercuts our core marketing claim, and the plan doesn't reckon with it.** The packet's own benchmark says 2× Opus + Opus judge beats solo Opus by +6.7 — "much of the lift is the synthesis / test-time-compute step, not model diversity." If that's true, then "multi-*model*, multi-*provider*" is **not** the differentiator a buyer should pay attention to — more compute on one model gets most of the way. Our headline cannot be "three frontier models." It has to be the things compute-stacking does *not* give you: genuine cross-reading revision (seats read each other and *change their minds* — `SKILL.md:101`), provider-diverse blind-spot coverage, the abstaining gate, and privacy. The plan lists these but still calls multi-model the moat in #6. Demote model-diversity in the pitch.

**C. There is no demand evidence in the packet — only a competitor sighting.** The entire decision is reactive to OpenRouter shipping Fusion. That's a reason to clarify positioning; it is *not* evidence that users want an inline board. Before building #1's full surface, we need one signal that the JTBD exists for *our* users (agent-in-the-loop developers running CI gates), not Fusion's (deep-research API consumers). Those may be different segments.

**D. Stale proof point.** `SKILL.md:140` advertises "a real run is in the repo-root `examples/payments-idempotency-review/`" as the credibility anchor — but **there is no `examples/` directory in the tree** (verified: `ls examples` → NONE). Positioning (#6) and a benchmark (#5) both lean on showable artifacts. We are currently shipping a dead pointer to our flagship demo. Fix this before any positioning push, or the differentiation story has a broken first link.

## 3. Recommended execution sequence

Ranked by leverage-per-cost for the next milestone:

1. **#6 Positioning — ADOPT NOW (week 1, near-zero cost).** Rewrite the one-liner: "a deliberation *workflow* with a gateable, abstaining verdict — runs on your subscriptions at ~$0 marginal, locally when needed," not "an inline model." Demote multi-model; promote debate + gate + economics + privacy. This is the cheapest, highest-leverage move and it *constrains every later decision*, so it goes first.
2. **Fix the dead demo pointer (week 1).** Either restore `examples/payments-idempotency-review/` or strike the claim at `SKILL.md:140`. Non-negotiable hygiene before #5/#6 go public.
3. **#1 Inline escalation — ADOPT NOW, but *local form only* (milestone 1).** A thin MCP/subprocess wrapper over the existing conductor (`scripts/run_board.py`) that another agent calls as a tool: one question → quick 1-round board → `verdict.json`. No new metered API. The deliverable that distinguishes us is that the tool call returns a *gateable* result, not prose. Verified that no such surface exists today: `grep -i mcp` hits only a CSS font name; `escalat` hits only the gate's internal "synthesis escalation."
4. **#4 Crisper structured output — ADOPT NOW as additive fields (milestone 1, low cost), behind a hard guardrail (§4).** `partial_coverage` / `unique_insights` improve the synthesis artifact's usefulness. Cheap, and they make our output legible next to Fusion's.
5. **#5 Benchmark — DEFER the *published* number; commission a small *internal honest* eval now.** We need the de-risking signal (does debate beat compare?) before we bet positioning on it. Publishing a number is a later, separate decision gated on the internal result coming out favorable.
6. **#2 Sandboxed execution seats — DEFER.** Being deep-dived elsewhere; from the market lens it's an internal accuracy lever, not a buyer-visible differentiator, and it collides head-on with the read-XOR-network invariant (`SKILL.md:86`, `data-handling.md:37-39`). Rank below #4.
7. **#3 MCP/domain-tool pass-through to seats — DEFER, leaning REJECT for now.** Narrow segment, large attack-surface and safety-invariant cost, no demand signal. Lowest priority.

## 4. Invariants and guardrails

- **The gate stays uncontaminated.** `board_verdict.py:68-69` already enforces "**The gate never reads** [confidence]." Any #4 field (`partial_coverage`, `unique_insights`) must be **informational only** — never a gate input. The abstain logic must keep reading *observed cross-seat agreement* (`board_verdict.py:244-264`), nothing self-reported. This is our most defensible feature; do not dilute it to look like Fusion's richer JSON.
- **Read-XOR-network is sacrosolid** (`data-handling.md:37-39`; `SKILL.md:86`). Any inline/embeddable mode (#1) that runs in gate posture must inherit the same refusal — a grounded *and* networked seat is the exfil channel. Don't let "lightweight one-shot" become a quiet bypass of D4.
- **Local-only must survive the inline mode.** The `ollama` seat / `provider="local"` egress exclusion (`registry.py:494`, `data-handling.md:25`) is a literal moat Fusion (a hosted gateway) structurally *cannot* match. The inline wedge must support a local board, or we've thrown away the one thing they can't copy.
- **No silent metering.** If #1 ever grows an API-key path, it must be opt-in and loudly disclosed — never the default — or "~$0 marginal" stops being true and the positioning is a lie.

## 5. Risks, stale assumptions, missing evidence

- **Missing: any proof debate > compare.** Fusion's judge *explicitly does not merge* (packet) and still wins benchmarks; the 2×Opus result says synthesis-compute is most of the lift. **We have no evidence our cross-reading-and-revise loop beats a cheap compare.** This is the single biggest hole. Cheap to test internally; expensive to be wrong about publicly.
- **Stale claim in our own skill:** `SKILL.md:140` → non-existent `examples/` dir (verified). Undermines #5/#6.
- **Unverified demand:** no user-side signal that the inline JTBD exists for *our* segment vs Fusion's. The plan treats competitor existence as demand.
- **Segment assumption:** the brief assumes one market. Fusion's buyer (deep-research API caller) and ours (agentic-dev running CI gates) may not overlap; "respond to Fusion" may be defending a hill they aren't attacking.
- **Risk of feature-chasing:** #2/#3/#4 collectively add surface and cost; each nudges us toward "Fusion with more knobs" and away from "the one with the gate." The discipline of *refusing* most of them is itself the strategy.

## Per-candidate scorecard

| # | Candidate | Verdict | One-line rationale | Main risk | Evidence that flips it |
|---|---|---|---|---|---|
| 1 | Inline escalation | **ADOPT NOW (local form only)** | Real JTBD gap; close it with a gate-bearing local tool, not a metered API | Becomes a metered Fusion-clone and forfeits the moat | Demand signal showing users want hosted/metered, not local |
| 2 | Sandboxed exec seats | **DEFER** | Accuracy lever, not buyer-visible; collides with read-XOR-network | Safety-invariant erosion | Eval showing execution-grounding materially lifts verdict correctness |
| 3 | MCP domain-tool pass-through | **DEFER → REJECT for now** | Narrow segment, big attack surface, no demand | Surface/safety cost with no buyer | A concrete design-partner asking for domain boards |
| 4 | Crisper structured output | **ADOPT NOW (informational only)** | Cheap, legible, additive | A new field leaks into the gate | n/a — guardrail is the answer |
| 5 | Published benchmark | **DEFER number; run internal eval now** | Need the de-risk before betting positioning on it | Eval shows debate ≈ compare → claim dies | Internal eval shows debate clearly beats compare/solo |
| 6 | Positioning | **ADOPT NOW** | Cheapest, highest-leverage; reframes everything else | Leaning on "multi-model" when compute is the real lift | DRACO-style data proving provider-diversity (not just compute) is load-bearing |

## The single highest-leverage move
Ship **#1 in its local, gate-bearing form** — a callable one-shot board that returns a `verdict.json`, runs on subscriptions at ~$0, and supports a local seat. It is the *product manifestation* of #6: it converts our latent moat (free, gateable, private deliberation) into something an agent actually reaches for at a high-stakes fork — answering Fusion's wedge without adopting Fusion's economics. Positioning (#6) is the narrative that must ship alongside it, not after.

## The one thing to refuse
**A metered, hosted, API-keyed inline model id that competes with Fusion on pass-through pricing.** It forfeits subscription/local/verifiable advantages, drops us into a routing-economics race against the team that owns the gateway, and dilutes the gate. Refuse it explicitly. (Secondary refusal: letting any Fusion-style field become a gate input.)

## Grounding of load-bearing claims

- "No inline/MCP/escalation surface exists today" — **[verified]** `grep -ri mcp` over the tree hits only `references/plan-fonts.css` (a font name); `escalat` hits only `scripts/board_verdict.py` (internal "synthesis escalation") and `references/verdict-schema.md`.
- "The gate never reads self-reported confidence; reads observed agreement; abstains when torn or a citation is refuted" — **[verified]** `board_verdict.py:68-69` ("The gate never reads it"), `gate_outcome` `board_verdict.py:223-268`, refuted path `:240-242`.
- "~$0 marginal / subscription CLIs" and "local-only board is a real lever" — **[verified]** `SKILL.md:23`; `registry.py` `auth_hint` fields; `provider="local"` `registry.py:494`; `data-handling.md:25`.
- "Read-XOR-network safety, gemini/antigravity force refuse" — **[verified]** `SKILL.md:86`, `data-handling.md:37-39`, `registry.py:449`/`:475` (`isolates_network=False`).
- "verdict.json has no partial_coverage/unique_insights today; buckets are blockers/dissent/concerns/caveats" — **[verified]** `verdict-schema.md:53-75`, `board_verdict.py:39` (`EVIDENCE_CONTAINERS`).
- "Flagship example run is advertised but absent" — **[verified]** `SKILL.md:140` claims `examples/payments-idempotency-review/`; `ls examples` → NONE.
- "DRACO: 2×Opus self-fusion = +6.7 over solo; lift is mostly synthesis-compute, not diversity" — **[packet-only]** stated in the brief; not checkable in this tree. This is the claim most worth independently verifying before we set positioning, because it cuts *against* the multi-model pitch.
- "Fusion is pass-through priced ~4–5×, judge does not merge, server-tool layer beta" — **[packet-only]** from the brief; not verifiable here.

## What I'd ask the other seats to challenge

- **Codex (execution/repo lens):** Can the existing conductor (`run_board.py`) be wrapped as a local MCP/server-tool with *no* new metered path and *no* weakening of D4's read-XOR-network gate? If the inline mode can't preserve the gate cheaply, my #1 ranking is wrong.
- **Gemini (product/rollout/user-workflow lens):** Is the inline JTBD real for *our* segment (agentic-dev/CI) or am I projecting Fusion's deep-research-API segment onto our users? Challenge my segment assumption in §5.
- **Both / synthesizer:** Stress-test objection B — if a cheap compare-and-synthesize of two Opus runs matches our multi-round debate, what in the positioning survives? I claim the gate + provider-diverse blind-spot coverage + privacy do; I want that contested, because the whole CAUTION verdict hinges on debate being worth more than compute.
- **Whoever owns #5:** Is an honest internal eval that *might disprove our own pitch* something we're willing to run before marketing the claim? If not, we shouldn't make the claim at all.

VERDICT: caution

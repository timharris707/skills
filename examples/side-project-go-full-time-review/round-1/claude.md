This is an advisory-board review task, and the brief is explicit: return the full review as my reply, write no files, and end with a single machine-readable verdict token. I'll do that directly rather than run the code-planning workflow, since there's no code involved. My seat is first principles & economics, so I'll put the weight on whether the math actually holds.

---

# Claude seat review — "Quit to go full-time on Tally"

## 1. Verdict
**CAUTION — confidence: medium.** This is a *recoverable* bet, not a reckless one: the downside is ~12 months and a chunk of savings, with a re-employable senior engineer and a working partner income behind it. But three things in the plan are economically unsound as written — the burn omits a major cost (health insurance), the headline targets are misframed as "salary replacement" when they aren't, and the two growth planks the whole thesis rests on (paid acquisition at $15 ARPU, and ARPU expansion) are entirely *unproven*. Proceed only after the §3 changes.

**One line that would change it:** If, in the next 3 months, he proves (a) a repeatable acquisition channel with CAC payback under ~6 months and (b) that ARPU can rise materially (Team/annual plans actually convert), this moves to **ship**. If neither lands, it moves to **block**.

## 2. Strongest objections

**(A) "Salary replacement" is the wrong frame — $12k MRR doesn't replace what he's giving up.** He's leaving $165k/yr *plus* ~$22k/yr equity *plus* employer-paid health insurance and likely a 401k match — call it ~$200k+ total comp. $12k MRR is **revenue, not take-home**. After Stripe (~5% on a $15 ticket: $0.30 + 2.9%), hosting, tooling, and especially self-employment tax (he now pays *both* halves of FICA), $12k MRR nets maybe ~$9–10k/mo personally. That's below his current solo take-home (~$9.5k/mo) and far below total comp. The plan only "works" because partner income ($4k/mo) backfills it. That's fine — but he should call it **partner-subsidized lifestyle break-even**, not salary replacement. The romanticizing he's worried about lives precisely in this word.

**(B) The $15 ARPU + paid acquisition combination is the central economic flaw.** At 5% monthly churn, average lifetime is 1/0.05 = **20 months**, so revenue LTV ≈ $15 × 20 = **$300** (~$270 contribution at high margin). A healthy LTV:CAC of 3 means he needs blended CAC **under ~$90**. Paid SaaS CAC routinely runs $100–300+. A $15/mo product is one of the *hardest* price points to make paid acquisition profitable — it's the classic ARPU trap. He has **never run paid** and is budgeting a core plank on it. This is the single weakest assumption in the plan and it's untested.

**(C) The growth target requires acceleration, not continuation — but the floor requires almost nothing.** The math:
- At sustained 8% MoM: $4,200 × 1.08⁹ = **~$8,400 at month 9** — *not* the $12k target. Hitting $12k in 9 months needs **~12.4% MoM**, i.e. growth must *accelerate ~50%* the moment he goes full-time. Possible, but it's an assumption dressed as a plan.
- The $8k floor: $4,200 × 1.08¹² = **~$10,600 at month 12**, and $8k is crossed around **month 8–9** at current 8%. Even a degraded ~5.5% MoM clears $8k by month 12. **So the hard-stop gate is met by roughly the hobby trajectory** — it tests "did Tally keep limping forward," not "did quitting accelerate it." A floor that the no-quit baseline already clears is not a real decision gate.

**(D) 8% MoM gets harder, not easier, as the base grows.** That 8% *net* number was earned at a small base (≤$4.2k) off SEO + a couple of one-time Reddit/IH spikes. Net 8% at 5% churn means **~13% of base in gross new MRR every month** — and the absolute dollars of new MRR must roughly double as the base doubles. SEO can compound; Reddit/IH posts are non-repeatable spikes. The historical rate is not safely extrapolable to a 2–3x larger base.

## 3. Recommended execution sequence (what I'd change before pulling the trigger)

1. **Re-cost the burn with health insurance.** Leaving the job almost certainly ends employer health coverage. A family marketplace/COBRA plan with a kid is realistically **$1,500–2,200/mo** unsubsidized. If the $6,500 household burn doesn't include this, true gap = ($6,500 + ~$1,800) − $4,000 partner = **~$4,300/mo before any Tally contribution**, not the $2,500 implied. Recompute runway honestly: $70k against a $4,300 gap (net of partner, before Tally profit) ≈ 16 months; Tally's net profit extends that, but paid-acquisition spend shortens it. Get the real number on paper.

2. **Use the 3 pre-quit months to attack the two unproven planks — not just to bank vesting.** This is the highest-leverage change. Both crux risks are testable *while still employed*:
   - **Ship the Team plan and an annual plan now, nights/weekends.** The thin $15 ARPU is his own #1 stated worry and it's the cheapest thing to de-risk. If a Team tier and annual prepay don't lift blended ARPU, the entire thesis weakens — better to learn that with a paycheck.
   - **Run one small paid-acquisition test (a few hundred dollars).** Measure real CAC and payback. If CAC payback is >12 months on $15 ARPU, kill paid as a plank *before* it's load-bearing.

3. **Reset the gates to test the actual hypothesis.** Replace "$8k MRR by month 12" (baseline-clearing, soft) with a *trajectory + composition* gate: e.g. **sustained ≥10% MoM net for 3 consecutive months AND blended ARPU up ≥30% AND ≥1 channel with payback <6 months by month 6.** That tests whether *quitting bought acceleration*, which is the only thing that justifies the opportunity cost.

4. **Keep the re-entry option explicit and dated.** A 12-month gap is easily explained for a senior engineer, but bake in a month-9 "start interviewing if month-6 gate missed" trigger so the hard stop isn't a cliff.

## 4. Invariants and guardrails
- **Never let savings fall below a hard floor** (e.g. 4 months of true burn, ~$17k) — that's the re-entry buffer, not spendable runway.
- **Paid acquisition is gated on proven payback.** No scaling spend until a test shows CAC payback < ~6 months. Cap monthly paid spend until then.
- **Health insurance funded from day one** — non-negotiable line item, not an afterthought.
- **ARPU is the north-star metric, not MRR.** A $15 product growing logos is more fragile than a rising-ARPU product. Track blended ARPU and net revenue retention monthly.
- **The month-6 gate is a real decision, pre-committed in writing** so it isn't renegotiated under sunk-cost pressure.

## 5. Risks, stale assumptions, missing evidence
- **Missing: health insurance cost** (likely $1.5–2.2k/mo) — material omission from burn.
- **Missing: Tally's actual cost structure and net margin.** MRR is quoted; COGS, payment fees, tooling, and *post-quit self-employment tax* are not. Take-home ≠ MRR.
- **Stale/optimistic: 8% MoM extrapolated from a small base** earned partly via non-repeatable one-time posts.
- **Unproven: paid acquisition viability at $15 ARPU**, and **ARPU expansion** (Team/integrations) — both are *assumed* to work and both are load-bearing.
- **Unquantified: the integrations marketplace** — marketplaces need two-sided liquidity and rarely move revenue inside 9 months; treat as a long bet, not a month-9 lever.
- **Re-entry risk:** assumes the senior-eng market in 12 months is as strong as today.
- **5% monthly churn (~46% annual) is high** — at scale it becomes a leaky bucket that paid spend pours into. Churn reduction may be higher-ROI than acquisition.

## 6. Concrete evidence from the source material
- "$4,200 MRR across ~280 paying customers (a $15/mo plan)" — confirms ARPU = exactly $15; 280 × $15 = $4,200 ✓. This pins the LTV math in §2(B): 20-month lifetime → ~$300 LTV.
- "growing ~8% month-over-month for the last 5 months" — drives §2(C): 1.08⁹ ≈ 2.0 → ~$8.4k at month 9, *short of* the "$12k MRR within 9 months" target stated under **The plan**.
- "Hard stop: if I'm not at $8k MRR by month 12" vs. "Monthly churn is ~5%" + 8% growth — 1.08¹² ≈ 2.52 → ~$10.6k at month 12; the $8k floor is crossed ~month 8–9 on the existing trajectory. The gate is below baseline.
- "Household burn: ~$6,500/mo (mortgage, groceries, one kid in daycare at $1,600/mo)" + "My partner works and brings in $4,000/mo after tax" — the list contains **no health-insurance line**, which is the §3(1) gap once employment ends.
- "Cash savings: $70k" + "the runway math tighter than the $70k headline suggests" — he already senses §3(1); the fix is to quantify it, not just worry about it.
- "$15/mo is a thin plan" and "am I extrapolating a hobby?" — his own two best instincts; they are exactly objections §2(A) and §2(B). The plan doesn't yet act on them.

## 7. What I'd ask the other board seats to challenge
- **Go-to-market / growth seat:** Is sub-$90 CAC realistically achievable for a freelancer-invoicing tool on any paid channel? Which channel, and what's the evidence? Pressure-test whether 8% net is sustainable off a 2–3x larger base.
- **Product/pricing seat:** Can ARPU actually move? Is there willingness-to-pay for a Team plan among freelancers (a notoriously price-sensitive segment), or is $15 a ceiling? Should churn reduction outrank acquisition?
- **Personal-finance/risk seat:** Stress the real post-quit burn (health insurance, self-employment tax, end of 401k match) and the true runway. Is the partner's $4k income itself stable enough to be the backstop the whole plan leans on?
- **Behavioral seat:** Is the "one shot at good-terms vesting" framing a genuine constraint or sunk-cost reasoning that's rushing the timing? Future vesting exists; the channel/ARPU proof does not yet.

My net: the *structure* of the bet is sound and recoverable, but it's being made before the two questions that determine its outcome have been answered — and both can be answered in the next 3 months without quitting. Don't pull the trigger on faith in 8%; pull it on proof of ARPU and a channel.

VERDICT: caution

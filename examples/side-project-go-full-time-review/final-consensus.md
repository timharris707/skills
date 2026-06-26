# Advisory Board — Final Consensus
Should I go full-time on my side project?
Board: Claude (First principles & economics/claude-opus-4-8) · Codex (Execution & feasibility/gpt-5.5) · Gemini (Second-order & downside/gemini-3-pro-preview). Rounds: 2.

## Verdict: Proceed with care — unanimous (high confidence)
Workable, but address the flagged concerns before you go ahead.

## Consensus blockers (must fix before ship)
1. Income case never closes: $12k MRR ≠ replacing a $165k salary — All three seats converged in the final round that the financial model is a gating item, not background. Claude quantified that $12k MRR = ~$144k/yr gross revenue, and once payment fees, self-employment tax, lost 401k match, forgone equity, and especially self-paid family health insurance are stripped out, net personal economic value at the target is ~$100–110k versus ~$200k+ current total comp — a trade down to ~50% even if the plan fully succeeds. Codex now treats the same point as a gating item; Gemini conceded the health-insurance omission is catastrophic and pegs the true savings draw closer to ~$4,800/mo, roughly halving runway.
   - evidence: proposal — “stable job paying $165k/year” (source) — unchecked
   - evidence: proposal — “$4,200 MRR across ~280 paying customers (a $15/mo plan)” (source) — unchecked
   - evidence: proposal — “one kid in daycare at $1,600/mo” (source) — unchecked
   - evidence: judgment — Source quotes gross MRR and burn but omits health insurance (~$18–26k/yr), self-employment tax, Tally net margin, and business costs — understating true burn by roughly 25% per the board.
2. Growth math is flawed: 8% MoM does not reach the $12k target — The board found the founder is projecting unjustified acceleration. At the observed 8% MoM net rate, $4,200 reaches only ~$8,395 at month 9 and ~$10,577 at month 12. Hitting $12k by month 9 requires ~12.3% MoM (+54% faster) on a 2–3× larger base, after the non-repeating Reddit/Indie Hackers spikes are spent. Gemini and Codex both explicitly conceded this math in round 2.
   - evidence: proposal — “growing ~8% month-over-month for the last 5 months” (source) — unchecked
   - evidence: proposal — “Target $12k MRR within 9 months” (source) — unchecked
   - evidence: proposal — “Target $12k MRR within 9 months by shipping a Team plan, ...” (source) — unchecked
3. Quit is triggered by the vesting date, not by evidence — Claude and Codex both held that the vesting date is financially attractive but logically irrelevant to business readiness. The recommendation: take the vest regardless, but make quitting conditional on 3-month gates passing — not on the calendar. Claude called decoupling the trigger from the vest the single most important fix.
   - evidence: proposal — “right after my next vesting date (~$22k)” (source) — unchecked
4. Plan spends the scarcest resource (founder hours) on the non-bottleneck — Claude, Codex, and Gemini agreed the plan is product-build heavy (Team plan, integrations marketplace, paid acquisition — three major tracks for a solo founder) when the binding constraint is distribution and economics, not engineering output. Claude framed the marginal return on 25 extra coding hours/week as near-zero if growth is distribution-bound; Codex and Gemini flagged the same stale 'time = revenue' assumption.
   - evidence: proposal — “Growth is almost entirely organic (SEO + a few well-recei...” (source) — unchecked
   - evidence: judgment — Board judgment: 40+ more founder coding hours/week have low marginal return if the bottleneck is repeatable acquisition or retention rather than capacity.
5. 5% churn at $15 ARPA makes paid acquisition structurally hard — At a $15/mo plan, 5% monthly churn implies a ~20-month lifetime and ~$300 gross LTV, leaving little room for CAC. Codex and Claude set a CAC ceiling around $80–100; the board agreed retention/ARPA must improve before scaling spend. Gemini went further (see dissent), arguing no ad channel will deliver sub-$50 CAC for an inexperienced solo founder.
   - evidence: proposal — “Monthly churn is ~5%” (source) — unchecked
   - evidence: proposal — “$4,200 MRR across ~280 paying customers (a $15/mo plan)” (source) — unchecked

## Hard dissent (preserved)
- Gemini: Dissents from Claude's proposal to GATE paid acquisition on proven CAC payback: as the downside seat, Gemini argues paid acquisition should be completely BLOCKED, not gated. A $300 LTV with 5% churn means no realistic channel delivers sub-$50 CAC for an inexperienced solo founder, so any attempt simply incinerates the household safety net.
- Claude: Dissents from Gemini calling 5% monthly churn 'toxic': Claude holds it is mediocre-but-normal for freelancer SaaS (20-month lifetime), a ceiling on LTV rather than a disqualifier, and notes the 8% growth figure is already net of that churn.
- Codex: Dissents from Gemini's 'do not write a line of code': Codex agrees not to speculatively build the Team plan or marketplace, but holds that small code work for pricing tests, instrumentation, onboarding, retention, and a manually sold Pro/Team stub is justified.

## What the board couldn't verify
- The board could not price true burn without an actual marketplace/COBRA family health-insurance quote and SE-tax treatment.
- Sub-$90 (or sub-$50) CAC is unproven on any paid channel; no CAC evidence exists yet.
- There is zero evidence that organic SEO / Indie Hackers posts will scale to the 40+ net-new customers a month needed to offset churn and grow.

## Open questions
- What is the actual unsubsidized family health-insurance / COBRA cost, and what is the resulting true monthly savings draw and runway?
- Can a tier above $15 (Pro/Team at ~$49–99) be pre-sold to existing customers for real money before any code is written?
- Is there a repeatable acquisition channel with measured CAC < ~$90 and payback < ~6 months?
- How does the 5% churn decompose into voluntary vs involuntary (failed-card) and by cohort?

## Next actions
- Re-cost true burn: get an actual marketplace/COBRA family quote plus SE-tax delta, retirement/401k loss, and business costs; expect ~$8,000–8,500/mo, and agree a written non-spendable savings floor with the partner.
- Pre-sell ARPA instead of building it: secure paid commitments/LOIs from existing customers for a higher tier ($49–99 Team) before writing the Team plan or marketplace.
- Run a small capped paid-acquisition probe ($1–2k) on 1–2 channels to measure real CAC; continue only if payback is under ~6 months on gross margin.
- Instrument the business: gross vs net churn, cohorts, activation, churned vs new MRR, and source attribution; decompose the 5% churn into voluntary vs involuntary.
- Decouple the trigger from the vest: bank the ~$22k regardless, and gate quitting on the 3-month gates passing, not on the calendar.
- Establish a dual re-entry trigger (savings floor OR month-12 MRR < $8k, whichever first) and a written partner agreement on runway and floor.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

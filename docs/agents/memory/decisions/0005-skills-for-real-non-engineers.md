# 0005 — The catalog is positioned as Skills For Real Non-Engineers

- Date: 2026-09-05
- Links: the walk-and-talk positioning conversation (ChatGPT share, 2026-09-05) and the
  in-session follow-up with the decider; PR "Position the catalog for real non-engineers"

**The headline mirrors Matt Pocock's "Skills For Real Engineers" on purpose**: the catalog
is mostly his skills, adapted, and the audience should place it in one glance. What the
catalog adds is the lead: one orchestrator session that takes the idea, decides what gets
grilled, mapped, prototyped, built, and reviewed, and runs the other skills to do it. The
decider talks to that one session the way he has talked to a dev lead for over twenty years.

Copy of record, used verbatim on the README opening, the site hero, and llms.txt:

> **Skills For Real Non-Engineers**
>
> I've led dev teams for over twenty years. I never wrote the code. These skills give me a
> lead developer who runs the team, so all I have to bring is the idea. Four shipped products
> so far.
>
> Most of these skills started as someone else's. Fifteen are adapted from Matt Pocock's
> Skills For Real Engineers, three from Lauren Tan (linked to pstack, as Matt is linked), five are mine. I rewrote nearly all of
> them for someone who won't read the code, then tied them together under one orchestrator
> session that takes the idea, decides what gets grilled, mapped, prototyped, built, and
> reviewed, and runs the rest. That's what lets a non-engineer ship at production quality. I
> talk to that one session the way I've always talked to a dev lead.

Second paragraph revised the same day (decider, on reflection): the first version read as
"took Matt's skills and dropped an orchestrator in the middle," which is neither true nor
fair. The rewrite of nearly every skill and the work of tying them together carry equal
weight with the seat. The per-source counts are derived at build time from each skill's
Attribution section (site/src/lib/lineage.ts; scripts/check_lineage_counts.py holds the
README's static sentence to the same numbers), so they cannot rot when a skill is added or
moved. The numbers above are the values on the day of the ruling. A skill that names a source
without deriving from it declares `<!-- lineage: own -->` in its Attribution section; huh does,
because it shares only the trigger with Matt's wait-what and the review caught it counted as his.

Rulings that shape every surface:

- **Sell the seat, not the skill.** "Start here" is the orchestrator seat (install the pack,
  run setup once, open one session in orchestration mode), never a featured skill card and
  never "learn one skill and it teaches you the rest". Orchestrate is the payoff, setup is the
  on-ramp.
- **Matt is named in the second paragraph**, above the fold, not only in Acknowledgements.
  Honesty about the lineage reads as confidence; the same paragraph names what he doesn't
  have.
- **No "AI" leading the headline, no "vibe coding" anywhere, no "I direct agents".** The
  decider rejected each: "AI" cheapens the lead word, "vibe coding" is Matt's term and puts
  down the work even when denied, and "I direct agents" describes an air-traffic controller
  where the real shape is one lead the decider talks to.
- **No company name in the twenty-years claim.** The decider led developers for over twenty
  years across employers; naming one would overclaim.
- **No "evaluate this skill first" text inside any skill body.** Evaluating agents skipped
  orchestrate because its description read as niche infrastructure ("routing items to working
  sessions"). The fix is an honest description that names the benefit, plus the hierarchy
  stated in llms.txt and the README's agent section, the surfaces evaluating agents actually
  read. Text aimed at evaluators inside a skill body loads into every real session and reads
  as manipulation.
- **Setup asks one more question, in working-mode terms, not identity terms**: "Will you read
  the code your agents write, or lead from outside it?" A "lead" answer records a default
  working mode in the binding doc so new sessions open in the orchestrator seat. One setup,
  one pack; never two libraries or an "are you an engineer?" gate.
- **The old hero line survives below the fold.** "Stop re-explaining your workflow every
  session" is a true pain line in Matt's style; it moves down to head the failure-modes
  section rather than being deleted.

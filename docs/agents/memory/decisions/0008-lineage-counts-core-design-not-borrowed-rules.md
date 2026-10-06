# 0008: Lineage counts follow a skill's core design, not its borrowed rules

- Date: 2026-10-06
- Links: the #297/#298/#299 wave (Matt Pocock video-skills review) and its close-out
  review; decider ruling in session; extends the lineage-marker paragraph of 0005-skills-for-real-non-engineers

**A skill counts as adapted from a source when its core design comes from that source.**
A skill whose design is the repo's own counts as the maker's own, even when it borrows
individual rules from a source. Those rules are credited by name in the skill's Attribution
section, and crediting them does not change the count.

The case that set this is orchestrate. It borrows three rules from Matt Pocock's
`implement-spec` (briefing by context pointer, lane catch-up, the integration branch idea),
but the seat itself, the single-orchestrator rule, the close-out audit, and the binding slots
are this repo's design. The decider ruled that borrowing those rules does not make
orchestrate adapted: it stays in the "mine" count and keeps its `<!-- lineage: own -->`
marker. Its Attribution says so in plain words ("This skill is the repo's own"), credits
`implement-spec` (MIT) for the borrowed rules, and notes that the per-spec opt-in is ours
while Matt's integration branch is always on.

What follows:

- **The `own` marker has a second use.** Under 0005-skills-for-real-non-engineers it covered a skill that names a source
  without deriving from it (huh). It now also covers a skill that credits a source for
  specific borrowed rules without taking its core design from it. The marker still wins over
  the link rule, and the check script and site code keep the same logic; only their header
  comments changed.
- **A skill whose core design does come from a source** (most of the catalog) keeps linking
  that source and counts as adapted, whatever it changed on top.
- **Credit is never dropped to protect a count.** Borrowed rules stay named and linked in
  Attribution; the count answers a different question, which is where the skill's design
  came from.
- **The numbers on the day of the ruling:** Matt 15, Lauren Tan 3, own 5, unchanged.
  `scripts/check_lineage_counts.py` holds the README sentence to them.

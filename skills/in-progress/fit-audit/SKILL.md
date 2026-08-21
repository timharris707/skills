---
name: fit-audit
description: "Rank this catalog's skills by what each would have saved this specific adopter, every top pick citing a real incident from their own history, and for a team judge each skill against the incumbent stack as well. Use when someone is considering the catalog and has not run setup, when the user asks which skills would help them most, when recommending a starting subset to a new adopter, or when auditing the catalog for a team that already runs house skills, guidelines, or recorded review decisions."
---

# Fit audit

Before anyone installs anything, answer the question they actually have: which of these skills would have saved *me* time, on work I actually did? The audit reads real evidence of how the person works, scores every promoted skill against it, and returns a short ranked report in which every top pick names a concrete incident it would have prevented or shortened. The ranking earns trust through those citations: a recommendation that says "on Tuesday your deploy broke and this skill's check would have caught it" beats any description of features.

This audit belongs to the not-yet-adopted state: nothing installed, nothing bound. [setup](../../orient/setup/SKILL.md) binds the discipline to a repo, and in a repo where that has already happened the router governs the session; there the audit's only job is ranking what to adopt next. For everyone earlier than that, the audit comes first and setup follows it.

The audit runs in one of two modes. **Individual mode**, the steps below as written, serves a person with no incumbent stack: the question is only which skills to adopt first. **Team mode** serves an adopter that already runs its own skills, guidelines, and recorded decisions: the same steps run, plus the additions under "Team mode" below, because for a team "would this have saved us" is only half the question; the other half is "does the house already do this, or forbid it."

## Evidence rules

Two rules govern everything below:

- **Nothing invented.** Every incident cited traces to a transcript line, a commit, a CI run, an issue or review thread, or the person's own words. A skill with no evidence behind it ranks low with "no evidence found" stated, never with a plausible-sounding story.
- **Permission first.** Session transcripts and chat history are read only after the person agrees. Name what you want to read before reading it.

## Steps

1. **Gather the evidence.** With permission, read what shows how this person actually works: recent session transcripts or chat history where the harness can reach them, git log and CI history of the repos they name as active, and open issues or review threads that show recurring pain. Where no history is reachable, interview instead: ask for the last three times work went sideways, what it cost, and what they wish had existed. Done when each evidence source is either read or explicitly unavailable, and you hold a written list of concrete incidents with dates.

2. **Inventory the catalog.** The bucket registry ([skills/buckets.json](../../buckets.json)) is the source of truth for which buckets are promoted: list every skill directory in a promoted bucket, and read each skill's description from its SKILL.md frontmatter. When only the public README is reachable, use its catalog rows and say so in the report. In-progress skills stay out unless the person asks. Done when every skill in a promoted bucket is on your scoring list.

3. **Score each skill against the evidence.** Two numbers and a tier:
   - **Fit (0–10):** how often situations this skill covers appear in the evidence.
   - **Benefit (0–10):** what the covered incidents cost in time, rework, or risk.
   - **Tier (S/A/B/C/D):** from the scores and the evidence, by bands two auditors would apply the same way. **S**: a cited incident exists and Fit + Benefit totals 14 or more. **A**: a cited incident exists and the total is 10 or more. **B**: evidence exists but no single costly incident, and the total is 7 or more. **C**: evidence exists and the total is below 7. **D**: no evidence found.

   Done when every skill on the list carries both scores, a tier, and either an incident citation or "no evidence found."

4. **Report.** One line per skill, grouped by tier, best first. The S and A picks each carry their incident citation in one plain sentence: what happened, when, and what the skill would have changed. Close with the try-first move: install only the top picks by name, or run setup for the full discipline, and say which of the two the evidence argues for. Done when the report is delivered and every S/A line cites its incident.

## Team mode: auditing against an incumbent stack

When the adopter is a team with house skills, guidelines, or recorded review decisions, run the four steps above with one step added and the verdict widened. Everything in this section is additive; individual mode never reaches it.

**Incumbent inventory (between steps 2 and 3).** Before scoring anything, read what the house already runs: the team's own skills, their standing rules files (CLAUDE.md, AGENTS.md, contribution guidelines), and their recorded review or design decisions. Where the house keeps an index that names where its records live (a binding document, a memory home, a glossary or canonical-terms file), follow its pointers rather than guessing paths, and treat each artifact it names as part of the inventory. Done when each incumbent document, including every artifact a house index names, is read or recorded as unreachable, and you hold a written map of what the house already covers, naming the covering document for each area.

**Verdicts (replaces the tier as the top-level answer in step 4).** Each catalog skill gets exactly one of four verdicts, written with exactly these names: `adopt`, `redundant-with`, `conflicts-with`, `adapt`. Tiers attach to `adopt` verdicts only; the other three carry their named counterpart, quotation, or change list instead.

- **`adopt`.** Nothing in the house covers or contradicts it. Score and tier exactly as in step 3, citation and all.
- **`redundant-with` [house equivalent].** Name the specific house skill or rule that already covers the ground. If the catalog version is meaningfully stronger, say in one sentence what it adds; otherwise the house keeps its incumbent and the line says so.
- **`conflicts-with` [house rule].** Quote the specific rule, guideline line, or decision record it contradicts. A conflict is a finding to evaluate on mechanics, never an auto-disqualifier: compare what each side's mechanism would have caught or cost against the cited evidence, then either say which mechanism the evidence favors or state plainly that the call belongs to the team.
- **`adapt`.** The idea earns its place but the text does not fit the house: name what changes in the rewrite (the house format it moves into, vocabulary swapped for house terms, pointers rewired to house documents, parts the house makes unnecessary).

The evidence rules above govern every verdict, not just tiers. An `adopt` pick with no incident ranks D. A `redundant-with` or `conflicts-with` verdict must quote or link the actual house document; one that cannot is a guess, and the skill goes back through `adopt` scoring instead. An `adapt` verdict names the concrete changes, never just "tailor it."

The team-mode report groups by verdict: `adopt` picks ranked by tier and carrying their citations as in step 4, then the `redundant-with`, `conflicts-with`, and `adapt` lines each carrying their named house counterpart, quoted rule, or change list.

## What this skill does not do

It does not install anything, bind anything, or run setup. It ends at the report and the recommendation; acting on it is the person's call.

## Done when (checkable: verify each line before reporting complete)

- Every evidence source was read with permission or recorded as unavailable; none silently skipped.
- Every promoted skill carries Fit, Benefit, and a tier.
- Every S and A pick cites an incident traceable to a transcript, commit, CI run, issue or review thread, or the person's own words; no citation is invented.
- Every tier assignment follows the stated bands; no skill carries a tier its scores and evidence do not support.
- Skills with no supporting evidence say "no evidence found" rather than carrying a story.
- In team mode: every incumbent document, including every artifact a house index names, was read or recorded as unreachable before scoring began.
- In team mode: every skill carries exactly one of the four verdicts by its exact name, and the Fit-Benefit-tier line above applies to `adopt` verdicts only.
- In team mode: every `redundant-with` verdict names its house equivalent and either states in one sentence what the catalog adds or states that the house keeps its incumbent; every `conflicts-with` verdict quotes the contradicted rule and states which mechanism the cited evidence favors or that the call belongs to the team; every `adapt` verdict names the concrete rewrite changes.
- The report ends with a named next move: a minimal install list or setup.

## Attribution

The grading frame (S/A/B/C/D tiers with Fit and Benefit out of 10, and audit-your-real-usage as the way into a skills catalog) follows the onboarding audit Theo demonstrated on camera while reviewing this catalog's texts (2026-08-19), where he told every viewer to start that way. The evidence-citation rule was validated independently the same week: an unprompted audit by a catalog user surfaced blast-radius as their top pick precisely because the agent tied it to specific incidents that would have saved them real time.

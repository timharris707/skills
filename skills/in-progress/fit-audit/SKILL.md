---
name: fit-audit
description: "Rank this catalog's skills by what each would have saved this specific person, every top pick citing a real incident from their own history. Use when someone is considering the catalog and has not run setup, when the user asks which skills would help them or their team most, or when recommending a starting subset to a new adopter."
---

# Fit audit

Before anyone installs anything, answer the question they actually have: which of these skills would have saved *me* time, on work I actually did? The audit reads real evidence of how the person works, scores every promoted skill against it, and returns a short ranked report in which every top pick names a concrete incident it would have prevented or shortened. The ranking earns trust through those citations: a recommendation that says "on Tuesday your deploy broke and this skill's check would have caught it" beats any description of features.

Run this before [setup](../../orient/setup/SKILL.md). Setup binds the discipline to a repo; the fit audit decides whether and where it is worth binding at all.

## Evidence rules

Two rules govern everything below:

- **Nothing invented.** Every incident cited traces to a transcript line, a commit, a CI run, or the person's own words. A skill with no evidence behind it ranks low with "no evidence found" stated, never with a plausible-sounding story.
- **Permission first.** Session transcripts and chat history are read only after the person agrees. Name what you want to read before reading it.

## Steps

1. **Gather the evidence.** With permission, read what shows how this person actually works: recent session transcripts or chat history where the harness can reach them, git log and CI history of the repos they name as active, and open issues or review threads that show recurring pain. Where no history is reachable, interview instead: ask for the last three times work went sideways, what it cost, and what they wish had existed. Done when each evidence source is either read or explicitly unavailable, and you hold a written list of concrete incidents with dates.

2. **Inventory the catalog.** Read the name and description of every promoted skill (the [router](../../orient/router/SKILL.md) and the README rows carry them). In-progress skills stay out unless the person asks. Done when every promoted skill is on your scoring list.

3. **Score each skill against the evidence.** Two numbers and a tier:
   - **Fit (0–10):** how often situations this skill covers appear in the evidence.
   - **Benefit (0–10):** what the covered incidents cost in time, rework, or risk.
   - **Tier (S/A/B/C/D):** judgment from the pair, not a formula. S means "an incident in the evidence would have gone materially better"; D means "nothing in this person's work reaches for it."

   Done when every skill on the list carries both scores, a tier, and either an incident citation or "no evidence found."

4. **Report.** One line per skill, grouped by tier, best first. The S and A picks each carry their incident citation in one plain sentence: what happened, when, and what the skill would have changed. Close with the try-first move: install only the top picks by name, or run setup for the full discipline, and say which of the two the evidence argues for. Done when the report is delivered and every S/A line cites its incident.

## What this skill does not do

It does not install anything, bind anything, or run setup. It ends at the report and the recommendation; acting on it is the person's call.

## Done when (checkable: verify each line before reporting complete)

- Every evidence source was read with permission or recorded as unavailable; none silently skipped.
- Every promoted skill carries Fit, Benefit, and a tier.
- Every S and A pick cites an incident traceable to a transcript, commit, CI run, or the person's own words; no citation is invented.
- Skills with no supporting evidence say "no evidence found" rather than carrying a story.
- The report ends with a named next move: a minimal install list or setup.

## Attribution

The grading frame (S/A/B/C/D tiers with Fit and Benefit out of 10, and audit-your-real-usage as the way into a skills catalog) follows the onboarding audit Theo demonstrated on camera while reviewing this catalog's texts (2026-08-19), where he told every viewer to start that way. The evidence-citation rule was validated independently the same week: an unprompted audit by a catalog user surfaced blast-radius as their top pick precisely because the agent tied it to specific incidents that would have saved them real time.

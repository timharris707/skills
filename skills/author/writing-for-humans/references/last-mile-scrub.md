# The last-mile scrub — an AI-tell pass for finished drafts

The final pass over human-facing copy, run from [SKILL.md](../SKILL.md) after structure and voice are settled. Scrubbing an unfinished draft produces *clean nothing*. Do the content work first.

## The catalog lives elsewhere

The tells themselves, and the method for hunting them (judge clusters rather than isolated words, redraft the passage whole rather than swapping a word), live in the repo's single merged catalog: [plainspoken's tell catalog](../../../in-progress/plainspoken/references/tell-catalog.md). Read it there; this file adds only what shipped artifacts need on top.

## Artifact-only additions (read before hunting)

- **A voice sample outranks every catalog pattern.** When the author's real writing uses em dashes, triads, or any listed pattern, match the sample's frequency instead of scrubbing the tell. Matching the author beats scrubbing the tell. (The standing voice rules in [SKILL.md](../SKILL.md) are never outranked.)
- **No fabrication.** The scrub rewrites; it never adds facts, names, numbers, or anecdotes the source didn't carry.
- **A dash budget, not the ban.** The catalog drops em dashes from agent prose outright. Shipped pages keep [SKILL.md](../SKILL.md)'s budget instead: roughly a handful per page, each one earning its place, with density alone enough to fire the tell. When a page runs over, restructure — split the sentence, subordinate the aside with a comma, or cut it. A mechanical in-place swap of a dash for any other mark (comma, semicolon, colon, or parentheses) preserves the exact rhythm the budget exists to break, which is the anti-pattern the catalog's redraft rule already names.

## The pass

1. Read the draft aloud (or as if aloud). Mark every passage where two or more catalog tells stack. Judge the dash count per page; when it runs over budget, mark the stretches carrying the least-earned dashes; that tell needs no company.
2. Redraft each marked passage whole, keeping its facts and its next-action.
3. Reread once end-to-end for rhythm: sentence lengths should vary, and no two adjacent paragraphs should open the same way.

## Done when

- Every passage where tells clustered was redrafted whole, and no new facts entered.
- The page ends inside its dash budget: a handful at most, and no over-budget dash was fixed by an in-place swap.
- The voice sample, when one exists, won every conflict with the catalog.
- One read-through end-to-end found varied rhythm and no chatbot artifacts.

## Future tooling

[Aboudjem/humanizer-skill](https://github.com/Aboudjem/humanizer-skill) (MIT) scores a draft 0–100 on AI tells with a zero-dependency CLI and a `--fail-above` CI gate. Adopting a scored gate for this repo's public copy is an open idea, not a step in this pass.

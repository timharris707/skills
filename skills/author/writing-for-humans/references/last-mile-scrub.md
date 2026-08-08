# The last-mile scrub — an AI-tell pass for finished drafts

The final pass over human-facing copy, run from [SKILL.md](../SKILL.md) after structure and voice are settled. Scrubbing an unfinished draft produces *clean nothing* — do the content work first.

## Guardrails (read before hunting)

- **Clusters, not isolated tells.** A single em dash means nothing; several tells stacking in one passage is what to fix. Judge passages, never words in isolation. (This rule and the next follow [blader/humanizer](https://github.com/blader/humanizer).)
- **A voice sample outranks every rule below.** When the author's real writing uses em dashes, triads, or any listed pattern, match the sample's frequency instead of scrubbing the tell. Matching the author beats scrubbing the tell.
- **No fabrication.** The scrub rewrites; it never adds facts, names, numbers, or anecdotes the source didn't carry.
- **Rewrite sentences, not words.** Swapping "leverage" for "use" leaves the AI sentence standing. When a cluster fires, redraft the passage in the piece's voice.

## The pass

1. Read the draft aloud (or as if aloud). Mark every passage where two or more tells from the table stack.
2. Redraft each marked passage whole, keeping its facts and its next-action.
3. Reread once end-to-end for rhythm: sentence lengths should vary, and no two adjacent paragraphs should open the same way.

## Tell clusters

Condensed from the patterns Wikipedia's "Signs of AI writing" documents and blader/humanizer catalogs; consult that catalog's 33 numbered patterns with before/after examples when a passage fails and the reason won't surface.

| Cluster | What it looks like |
| --- | --- |
| Significance inflation | "stands as a testament", "plays a vital role", "marks a significant step" — importance asserted, never shown |
| Promotional gloss | "seamless", "robust", "comprehensive", "cutting-edge" — adjectives doing a claim's job |
| AI vocabulary | "delve", "leverage", "landscape", "tapestry", "journey", "unlock" |
| Rule of three | Triads in every list and sentence — "fast, simple, and powerful" — regardless of whether three things exist |
| Contrast scaffold | "It's not just X, it's Y", "more than a tool" |
| Essay endings | "In conclusion", "Ultimately," — a summary paragraph restating what the reader just read |
| Empty transitions | "Moreover," "Furthermore," "Additionally," opening consecutive paragraphs |
| Hedging stacks | "could potentially", "it's important to note that" — two hedges where zero belong |
| Uniform rhythm | Every sentence the same length and shape; no short one anywhere |
| Chatbot artifacts | "Certainly!", "I hope this helps", "Let's dive in" |
| Formatting litter | Bold terms scattered mid-prose, headers for two-sentence sections, emoji bullets |

## Done when

- Every passage where tells clustered was redrafted whole, and no new facts entered.
- The voice sample, when one exists, won every conflict with the table.
- One read-through end-to-end found varied rhythm and no chatbot artifacts.

## Future tooling

[Aboudjem/humanizer-skill](https://github.com/Aboudjem/humanizer-skill) (MIT) scores a draft 0–100 on AI tells with a zero-dependency CLI and a `--fail-above` CI gate. Adopting a scored gate for this repo's public copy is an open idea, not a step in this pass.

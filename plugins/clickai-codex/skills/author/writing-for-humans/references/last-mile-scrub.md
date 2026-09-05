# The last-mile scrub: an AI-tell pass for finished drafts

The final pass over human-facing copy, run from [SKILL.md](../SKILL.md) after structure and voice are settled. Scrubbing an unfinished draft produces *clean nothing*. Do the content work first.

## The catalog lives elsewhere

The tells themselves, and the method for hunting them (judge clusters rather than isolated words, redraft the passage whole rather than swapping a word), live in the repo's single merged catalog: [plainspoken's tell catalog](../../plainspoken/references/tell-catalog.md). Read it there; this file adds only what shipped artifacts need on top.

## Artifact-only additions (read before hunting)

- **The catalog's voice-sample rule does the artifact work here.** Its precedence over every pattern is defined in the catalog; this pass adds one clarification: the standing voice rules in [SKILL.md](../SKILL.md) are never outranked, even by a sample.
- **Follow the selected voice.** The default voice avoids em dashes. When a project-specific voice sample was explicitly selected, follow its punctuation. Restructure a flagged sentence rather than mechanically swapping punctuation; preserve the facts and intended action.

## The pass

1. Read the draft aloud (or as if aloud). Mark passages the catalog flags and punctuation that conflicts with the selected voice.
2. Redraft each marked passage per the catalog's redraft rule, keeping its facts and its next-action.
3. Reread once end-to-end for rhythm: sentence lengths should vary, and no two adjacent paragraphs should open the same way.

## Done when

- Every passage where tells clustered was redrafted whole, and no new facts entered.
- Punctuation matches the selected voice, and flagged passages were restructured rather than mechanically swapped.
- The voice sample, when one exists, won every conflict with the catalog.
- One read-through end-to-end found varied rhythm and no chatbot artifacts.

## Future tooling

[Aboudjem/humanizer-skill](https://github.com/Aboudjem/humanizer-skill) (MIT) scores a draft 0–100 on AI tells with a zero-dependency CLI and a `--fail-above` CI gate. Adopting a scored gate for this repo's public copy is an open idea, not a step in this pass.

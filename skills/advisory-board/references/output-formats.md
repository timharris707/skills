# Output Formats

The Markdown + HTML handoff is the default deliverable. From the same run you can derive lighter formats for where the decision actually gets read — without re-running the board.

## Derived from `verdict.json` (deterministic)

`scripts/format_output.py` turns `verdict.json` (see `references/verdict-schema.md`) into:

| Format  | Command                                          | For |
| ------- | ------------------------------------------------ | --- |
| `tldr`  | `format_output.py verdict.json --format tldr`    | One-paragraph answer for chat or a commit message |
| `pr`    | `format_output.py verdict.json --format pr`      | A Markdown PR review comment |
| `slack` | `format_output.py verdict.json --format slack`   | A Slack-ready message |
| `json`  | `format_output.py verdict.json --format json`    | Normalized JSON for other tools |

These are mechanical transforms of structured fields — no model call, so they're fast and reproducible.

## Print / PDF

`final-consensus.html` carries a print stylesheet, so **Print → Save as PDF** produces a clean, shareable handoff with no extra tooling. Use it to attach the review to a ticket or send it to someone who won't open a repo.

## Prose summaries (model-written)

For a tailored write-up beyond the deterministic TL;DR — an exec summary, a note to a specific stakeholder — have the chair write it from `final-consensus.md`. Keep it a *view* of the handoff: it must not introduce conclusions the board didn't reach.

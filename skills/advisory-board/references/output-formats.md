# Output Formats

The Markdown + HTML handoff is the default deliverable. From the same run you can derive lighter formats for where the decision actually gets read — without re-running the board.

## HTML shapes (`--shape`)

`scripts/render_verdict.py` renders the self-contained HTML handoff from `verdict.json`. The same `verdict.json` gives you two shapes — pick by how the reader will use it:

| Shape | Command | For |
| ----- | ------- | --- |
| `full-handoff` (default) | `render_verdict.py verdict.json --run <run-dir> -o final-consensus.md --handoff-data handoff-data.json --html final-consensus.html` | The complete record — verdict banner, consensus blockers, per-round seat reviews, dissent, what the board couldn't verify, open questions, next steps. The deliverable you archive. |
| `quick-verdict` | `render_verdict.py verdict.json --run <run-dir> --html quick-verdict.html --shape quick-verdict` | A skim brief, roughly a quarter the size — masthead, verdict banner, blocker one-liners, trimmed dissent, top next steps. The teaser you lead with; link the full handoff from it. |

Both render from the same `verdict.json` (plus the optional `--run <run-dir>` for per-round prose), so the two shapes never disagree. `--shape` defaults to `full-handoff` and only affects the `--html` output.

> The intake menu (SKILL.md "Upfront Choices") also lists an **implementation sequence** framing. That isn't a distinct `--shape` yet — selecting it renders the full handoff for now.

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

# Output Formats

The Markdown + HTML handoff is the default deliverable. From the same run you can derive lighter formats for where the decision actually gets read — without re-running the board.

## Output shapes (`--shape`)

`scripts/render_verdict.py` renders the self-contained HTML handoff from `verdict.json`. The same `verdict.json` gives you three shapes — pick by how the reader will use it:

| Shape | Command | For |
| ----- | ------- | --- |
| `full-handoff` (default) | `render_verdict.py verdict.json --run <run-dir> -o final-consensus.md --handoff-data handoff-data.json --html final-consensus.html` | The complete record — verdict banner, consensus blockers, per-round seat reviews, dissent, what the board couldn't verify, open questions, next steps. The deliverable you archive. |
| `quick-verdict` | `render_verdict.py verdict.json --run <run-dir> --html quick-verdict.html --shape quick-verdict` | A skim brief, roughly a quarter the size — masthead, verdict banner, blocker one-liners, trimmed dissent, top next steps. The teaser you lead with; link the full handoff from it. |
| `implementation-sequence` | `render_verdict.py verdict.json --shape implementation-sequence --html implementation-sequence.html` | The sequence-first view for whoever executes — the verdict banner for context, then **every** `next_actions[]` step as one ordered do-this-then-that list (owner named where the verdict carries one), backed by the blockers each step must clear with their evidence trails. No round-by-round reviews, dissent, or open questions — link the full handoff for those. |

All render from the same `verdict.json` (plus the optional `--run <run-dir>` for per-round prose), so the shapes never disagree. `--shape` defaults to `full-handoff`. For `full-handoff`/`quick-verdict` it picks the `--html` template only; `implementation-sequence` also switches the Markdown to the sequence view (default filename `implementation-sequence.md`, so it never masquerades as `final-consensus.md`).

An owner on a step comes from the verdict itself: a `next_actions[]` entry may be either a plain string or `{"action": "...", "owner": "..."}` — the renderer adds nothing the board didn't say.

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

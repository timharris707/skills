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

## Severity filter (`--filter`, v1.14)

`--filter blockers|blockers+dissent|all` on `render_verdict.py` **and** `format_output.py` trims the **findings** sections by severity. `all` (default) is the full output, **byte-identical to no flag**; `blockers` shows blockers only; `blockers+dissent` adds dissent. The verdict banner and confidence are **never** filtered, and a dropped section is stated with counts (a loud elision line, e.g. `(filtered: 2 dissents, 4 couldn't-verify lines — --filter blockers)`) — never a silent truncation. The count names the **honest buckets that shape actually renders**: dissent *entries* and couldn't-verify *lines* (caveats + unverified/refuted evidence). It is not a raw `len(concerns)`/`len(caveats)` — concerns are never rendered as items in these shapes, so the note never claims a dropped "concern". Each shape filters only the findings it actually renders: the consensus md and full-handoff HTML filter dissent + the couldn't-verify bucket; the quick-verdict HTML and `format_output`'s `pr` render dissent but no couldn't-verify bucket, so their note reports only dropped dissent; `implementation-sequence` (actions + blockers only) is unchanged by any filter — rendered output *and* handoff-data; `tldr`/`slack` are unaffected. The same shape-owned rule governs a filtered `--handoff-data` file (a view feeding the HTML, never a machine echo): a slot is emptied only when that shape renders the bucket and the in-file `filter_note` counts it, so the artifact never silently loses content. **`--format json` refuses a non-`all` `--filter` (exit `2`)** — the JSON stays the faithful, unfiltered machine echo a gate reads.

For the CI side, `board_verdict.py --gate --min-severity blocker|concern` (v1.14) narrows a **fail**: it composes with `--fail-on` so a fail must also rest on a finding at/above that tier (a caution whose only findings are concerns/dissent then passes under `blocker`), and never affects the `abstain` outcome. See `scripts/README.md` → *Severity filters* and `references/verdict-schema.md` → *Using it as a gate*.

## Print / PDF

`final-consensus.html` carries a print stylesheet, so **Print → Save as PDF** produces a clean, shareable handoff with no extra tooling. Use it to attach the review to a ticket or send it to someone who won't open a repo.

## Prose summaries (model-written)

For a tailored write-up beyond the deterministic TL;DR — an exec summary, a note to a specific stakeholder — have the chair write it from `final-consensus.md`. Keep it a *view* of the handoff: it must not introduce conclusions the board didn't reach.

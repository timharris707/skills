# Intake Interview

Instead of running on static defaults, open a board with a short structured interview so the run fits the user's intent and material. This is optional — if the user says "use defaults," skip it and run.

## Engine

If the `grilling` or `grill-with-docs` skills are available, use one as the interview engine — they're built for exactly this kind of focused, adversarial Q&A. Otherwise run the question flow below directly. Ask only what you can't already infer from the request or the material; don't interrogate.

## What to settle

1. **Source** — what's under review (files, repo @ commit, URL, or a goal)? Is it complete, or is context missing?
2. **Stakes** — quick gut-check or high-stakes decision? Drives rounds and seat count.
3. **Sensitivity** — can this material go to external providers? (→ `references/data-handling.md`; may force local-only.)
4. **Subject & lens preset** — which preset fits (`references/lens-presets.md`), or custom lenses?
5. **Board** — default three seats, or resize / recompose (`references/board-composition.md`)? What's actually installed?
6. **Rounds & cross-reading** — `1` / `2` / `3` / `auto`; `none` / `summaries` / `full`.
7. **Output** — quick verdict, full handoff, implementation sequence; plus any derived format (PR comment, Slack, gate `verdict.json`)?
8. **Decision owner** — who reads the result, and what would make it actionable for them?

## Close

Play back the resulting run plan in one or two lines — board, rounds, cross-reading, sensitivity handling, output — and confirm before spending tokens. Then run preflight (`references/preflight.md`).

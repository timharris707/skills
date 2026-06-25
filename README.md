# Skills

Reusable AI workflow skills for planning, review, orchestration, and execution support.

This repository is provider-agnostic. A skill may include adapter metadata for a specific runtime, but the source-of-truth format should stay readable, portable, and easy to adapt.

## Current Skills

| Skill | Purpose |
| --- | --- |
| [Advisory Board Review](./skills/advisory-board-review/SKILL.md) | Runs a multi-model adversarial review process for plans, architecture, and execution handoffs. |

## Advisory Board Review

`advisory-board-review` is built for situations where a plan needs a rigorous architectural review before anyone starts implementing it. The workflow uses several model seats with different perspectives, asks them to critique the same source material independently, then gives them a second round to read and rebut each other's findings before a final consensus handoff is produced.

Default behavior:

- two rounds;
- read-only review unless edits are explicitly requested;
- cross-reading via summaries by default;
- no OpenClaw dependency;
- subscription-backed CLI usage where available;
- highest available reasoning settings for each provider at run time.

The skill is useful for:

- architectural reviews before a build;
- adversarial plan review;
- implementation sequencing;
- identifying risks, stale assumptions, and missing evidence;
- turning several model opinions into a single working handoff.

## Repository Layout

```text
skills/
  advisory-board-review/
    SKILL.md
    agents/
      openai.yaml
    references/
      prompt-templates.md
docs/
  index.md
  advisory-board-review.md
```

## Using A Skill

Each skill lives in `skills/<skill-name>/`.

For Codex-compatible runtimes, copy or sync an individual skill directory into your local skills folder. Other agent runtimes can read `SKILL.md` directly and adapt the templates in `references/`.

## Public Docs

This repository includes GitHub Pages-ready documentation in [`docs/`](./docs/). The first public page documents the Advisory Board Review workflow and how it is intended to be used.

## License

No open-source license has been selected yet. Public visibility does not automatically grant reuse rights beyond what GitHub's terms allow.

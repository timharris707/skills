# Contributing

This is a personal skills repository. Keep additions portable and provider-agnostic unless a runtime adapter file is explicitly needed.

## Skill Structure

One directory per skill, inside a **bucket**:

```text
skills/<bucket>/<skill-name>/
  SKILL.md
  references/
  scripts/
  agents/
```

`SKILL.md` should contain the core behavior and should be understandable without a specific provider runtime. Put longer reusable prompts, examples, or reference material in `references/`. Optional executable helpers go in `scripts/` — keep them dependency-free (e.g. Python 3 standard library) and make sure the skill still works without them.

The repository root and the tracked `skills/` catalog are intentionally separate. A checkout may
be named anything (`agent-skills/` is less visually repetitive than `skills/`); do not flatten the
catalog into the repository root because release automation and multi-skill paths depend on
`skills/<bucket>/<skill-name>/`.

## Buckets and Promotion

Buckets are declared in [`skills/buckets.json`](./skills/buckets.json), and each is either **promoted** or not. Promoted buckets ship in the marketplace and appear on the site; unpromoted ones (`in-progress/`, `misc/`, `deprecated/`) do neither.

**Start a new skill in `in-progress/`.** It is a real directory with a real `SKILL.md`, it just isn't claimed by any plugin and isn't listed anywhere. When it earns its place:

1. `git mv skills/in-progress/<name> skills/<bucket>/<name>`
2. Claim it in `.claude-plugin/marketplace.json`; the version bump itself happens later, in the
   release commit per [`RELEASING.md`](./RELEASING.md)'s per-PR habit (bump + changelog section
   rename together) — bumping here without that changelog section would fail auto-release
3. Add it to `.codex-plugin/plugin.json` so Codex ships it too
4. Write `agents/openai.yaml` with a `display_name` and `short_description`
5. Add it to the router roster if it joins the `team-workflow` pack
6. Give it a position in `site/src/lib/catalog.ts` so the hero chart can draw it

Retiring one is the same in reverse. Run the freshness check and it names whichever step you missed:

```bash
python3 scripts/check_router_freshness.py
```

Adding a bucket means adding it to `buckets.json` *and* creating the directory — CI fails on either half alone.

## Quality Bar

- Keep instructions concise and operational.
- Avoid storing secrets, account details, tokens, cookies, or private environment values.
- Prefer clear defaults over vague configuration.
- Document what the skill should do, when to use it, and when to stop.
- Keep provider-specific metadata in adapter files such as `agents/openai.yaml`.

## Validation

When a skill is Codex-compatible, check its `agents/openai.yaml` adapter against the SKILL.md before
publishing changes. Pull requests must also pass `.github/workflows/ci.yml`, including Python
compilation, shell-mock syntax checks, router freshness, and the complete advisory-board test suite.

## Releases

Skills are published as GitHub releases cut from **skill-scoped semver tags** (`<skill>/vX.Y.Z`,
e.g. `advisory-board/v0.5.0`). Pushing a version tag triggers the `release` workflow, which
publishes the release from that skill's `CHANGELOG.md`. Cut a release when a **milestone PR merges
to `main`** — not on every PR. Keep the skill's `CHANGELOG.md` current as you work. See
[`RELEASING.md`](./RELEASING.md) for the scheme, cadence, and exact commands.

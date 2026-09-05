# Click AI for Codex

The full Click AI catalog for Codex desktop, tuned for Astra at medium
and extra high. The workflows respect the model and effort you select. This is
a harness adaptation, not a measured claim of better model performance.

Install with a current Codex CLI that supports plugins, then start a new task:

```sh
codex plugin marketplace add timharris707/skills
codex plugin add clickai-codex@clickai
```

In Codex desktop, open Plugins, select the Click AI marketplace, and install
**Click AI for Codex**. If your workspace manages plugins centrally, its admin
can import the same GitHub marketplace. Use one Click AI edition in each Codex
profile: disable the legacy `clickai-skills` plugin in that profile when choosing
this edition, so duplicate skill names do not compete. Claude plugins are separate.

All templates and helpers are bundled. Ask for `clickai-codex:setup` in a project
to record its workflow bindings. Keep team rules in that project's `AGENTS.md`
and binding document. Installation does not change your global instructions,
model settings, accounts, credentials, hooks, or another harness's configuration.
For several Codex homes, install this same version in each; billing-account
rotation does not require different skill content.

The [desktop binding](CODEX.md) explains task ownership, delegation, question
tools, validation, and model selection. [Checkpoint recovery](runtime/CONTINUITY.md)
keeps work in the same task through compaction. A new task is an explicit transfer,
not a routine response to a half-full context window.

Python 3 and Git are needed for the checkpoint helper. Individual tools such as
Advisory Board and Ingest explain their additional requirements in their own
skills. Installing this plugin starts no provider calls. A multi-model board
requires approval for its participants, shared material, and expected usage.

Source and updates: https://github.com/timharris707/skills

The original Claude edition and legacy Codex plugin retain their existing paths
and versions. This edition releases independently as `clickai-codex/vX.Y.Z`.

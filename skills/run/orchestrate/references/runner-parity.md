# Runner parity — what a conforming lane launcher owes any runner

Guidance, not machinery: the pack ships no launcher scripts. A repo that runs lanes on more than one runner — Claude, Codex, a human — builds its own launchers (a `launch-codex-lane.sh`, a checklist a human follows) against this reference, so that whichever runner takes an item, the lane starts on identical terms. The [orchestrate skill](../SKILL.md)'s lane-launch slot (§7) records the runner inventory and the decider's policy; this file is the standard a launcher meets for every runner it can start. The runner-fallback protocol itself lives in §4 — this reference is about making launches succeed, so fallback stays a decision rather than a habit.

## The launch chain, in order

A conforming launcher runs these stages in this order, each gating the next (confirmed in practice by a working multi-runner launcher, 2026-08):

1. **Eligibility gates** — the item is on the frontier, unclaimed, unblocked, and the collision checks pass.
2. **Claim, preview → apply, with proof** — the claim is stamped on the tracker per the tracker discipline (read-before-write), and the launcher verifies the claim actually landed rather than assuming it did.
3. **Conforming workspace + branch** — fresh and item-named per the repo's convention, so tracker, workspace, and picker speak one name.
4. **Environment** — whatever the lane needs to run its verification commands: dependencies, env vars, per-lane resources (recorded in the workspace-provisioning slot, pruned with the lane).
5. **Generated prompt with the claim authority baked in** — the brief states that the claim is already made and who holds it, so the lane never re-claims or second-guesses its mandate.

## What the launched lane must have, whichever runner takes it

- A conforming workspace and branch (stage 3 above).
- The claim stamped on the tracker item — runner, model, workspace, branch.
- The session titled by the launcher, per the titling protocol (orchestrate §8), where a title surface exists. Where the binding records `no titling surface` — the binding-doc template's documented option — launch reports and handoffs carry the lane's identity instead (§8's degrade path).
- **An issue-as-spec brief readable by any runner.** The tracked item is the spec, cited by reference — the item id plus the tracker command that fetches it — beside any verbatim paste, so any runner can re-pull the authoritative text. The brief carries no harness-specific assumptions: no one harness's tool names, session mechanics, or file conventions.
- The environment and sandbox provisioned (next section).
- **Preflight.** The lane can run its named verification commands before handover — the launcher proves this rather than the lane discovering a broken environment mid-item. A lane that cannot run its own "done" test was never launched, only started.

## Sandbox: fix the invocation, not the policy

Agent runners ship protective sandboxes, and the tempting wrong fix for a sandbox failure is a blanket "run relaxed". The right order:

1. **Diagnose the violation to its mechanism first.** Sandbox denials often have technical causes unrelated to what the check actually needs. Empirically: macOS's sandbox counts *sockets* as network access, so a script runner that opens an internal IPC socket before user code runs fails "network" for verifiers that touch no network — fixing the runner invocation made every verifier pass inside the default sandbox, no relaxation.
2. **Relax last, and surgically.** Only after the mechanism is named, and only for the checks that genuinely need the blocked capability (a database-touching test needs network; a formatter does not). Blanket relaxation is a policy change that belongs to the decider, not a launch-time convenience.

## Every failure mode loud, with the fix printed

Each way the launcher can fail prints what went wrong AND the remedy — the launch-time analogue of §4's loud-fallback rule. A launcher that prints its own fix turns the diagnose-first step of the launch-failure protocol into a read. A partial launch (claim stamped but no workspace, workspace but no title) reports exactly which stage failed and how to finish or roll back, so the chain's proof discipline survives the failure.

## Documented in-repo

A conforming launcher ships with a recipe doc in the repo — what it does, stage by stage, and how to run it — so the knowledge stops living in session memory. The doc is what a setup re-run checks still exists and still matches the launcher it describes.

---
name: adversarial-review
description: "Run an adversarial review of a change before it ships: isolated finders trying to break it, a skeptic pass that kills unproven findings, and a gate on confirmed blockers. Use before committing substantial work, at lane close-out, when the user asks for an adversarial or red-team review of a diff/branch/PR, or before external reviewers see the change."
---

# Adversarial review

Reviewers whose job is to find what is **wrong** with a change before it ships, not to summarize it, not to appreciate it. This skill is the portable protocol: isolated finders, a skeptic pass that separates proven defects from plausible ones, and a gate that only skeptic-confirmed blockers may hold. Everything a repo does differently (its defect history, its probe policy, its stakes) lives in **binding slots** the team-workflow setup interview fills.

Read the team-workflow binding doc first. The review runs **before external reviewers** (CodeRabbit, Copilot, human PR review) see the change: they are the safety net, not the review.

## 1. The two layers

1. **The floor: before committing substantial work.** The implementing session reviews its own change before the commit. Every repo bound to the pack has this layer.
2. **The close-out layer: the orchestrator reviews the lane.** In repos running orchestration, the orchestrator (or its delegated verifier) runs the review against a lane's branch at close-out, per the orchestrate skill's audit rule; the implementer never has the last word on its own work. The executor's model and effort come from the repo's review-tier policy (the orchestrate skill's verification-executor binding slot), never habit. Bound per repo; a repo without lanes simply has no second layer.

**What counts as substantial:** the implementing session judges, biased toward reviewing when unsure: a skipped review is a silent decision that the change couldn't bite. The repo binding may pin hard rules ("any migration or money-path change is always substantial"); those are never overridable by the implementer's judgment.

## 2. Composition: three finders, isolated

Three reviewers that **never see each other's reasoning**: isolation is what makes agreement between finders meaningful. Each loads the diff, the repo's defect-class checklist (§5), the repo's decision records where [domain-memory](../../orient/domain-memory/SKILL.md) is bound, and nothing of the others' output. The execution shape follows where the review runs: a reviewer in the harness's main loop launches the finders as parallel subagents, whose completions re-invoke it; a review that itself runs as a delegated subagent runs the finder passes **sequentially in one context**: nested subagents' completions do not re-invoke a parent subagent, so a spawn-and-wait reviewer there stalls. Sequential passes keep the isolation between passes rather than between processes: a fresh perspective per pass, no shared candidate list until the skeptic.

1. **The correctness finder.** Logic, edge cases, error paths, invariants; the defect-class checklist is its opening moves, not its limit.
2. **The fitting lens.** One perspective chosen to match the change, from the menu:
   - **security**: inputs, authz, secrets, injection, egress; anything reaching a trust boundary.
   - **compatibility / migration**: schemas, serialized formats, public APIs, upgrade paths; anything an old client or old data can disagree with.
   - **money / ledger**: balances, idempotency, rounding, double-entry; anything that moves or records value.
   - **concurrency**: races, ordering, retries, partial failure; anything with two writers or a queue.
   - **performance**: hot paths, N+1, unbounded growth; anything multiplied by scale.
   - **UI / accessibility**: states the pixels can lie about, spoken output, keyboard paths; anything a person operates.
   - **conventions / standards**: the diff against the repo's *own* documented standards, style guides, ADRs, contribution rules, naming and layout conventions the repo wrote down. Available only where such documents exist (the finder reads the repo's documents, never an imported checklist), and it joins the menu as one more fitting lens beside the adversarial ones, never in place of the correctness finder or the spec axis.

   The invoker picks and **states the pick in the report**; the repo binding may pin mandatory lenses for named paths (a money lens on payment code is not optional there). A change fitting no lens well still gets its best fit: a second pair of eyes with a stated angle beats a second correctness pass.
3. **The spec axis.** Checks the diff against the originating ticket/spec: requirements missing, half-done, or wrongly done, and scope the spec never asked for. **No ticket or spec? The gap itself is a line in the report** (in a repo with tracker discipline, untracked substantial work is worth flagging), and the other two finders proceed normally. The spec axis never invents requirements to check against.

Finders **read code and run proofs** (tests, focused scripts, repro snippets) but modify nothing: no source edits, no commits, no state mutation beyond what a test run inherently does. Live probes against real services, seeded databases, or running apps are a **binding slot**: the repo names where they are mandatory (and safe), the protocol never assumes them.

## 3. The skeptic pass

Findings from a finder are hypotheses, not evidence. **Every finding above a NIT goes to an independent skeptic whose brief is to kill it**: re-read the code, run the disproof, find the guard the finder missed. Only findings the skeptic fails to kill stand in the report; killed ones drop to the dismissed bucket (§4) with the reason they died. A NIT skips the skeptic and reports as style-level advice, with no skeptic outcome and no rung.

**BLOCKER rank requires a runnable reproduction the skeptic confirmed.** No repro, no blocker: it ranks MAJOR at most, stated as unproven. This keeps the gate honest: nothing blocks a merge on a hunch, and a blocker in the report is a defect you can watch happen.

### The evidence ladder

Finders and skeptics grade every claim, finding and clean bill alike, in one language: how far down this ladder the proof got.

1. **Asserted.** The reviewer said so. Worthless on its own.
2. **Cited.** A real `file:line`, or the library's own source.
3. **Traced.** The failure path (or the guard that stops it) walked step by step, and it holds.
4. **Run.** A script or test that calls the real code and fails loud if the claim is wrong.
5. **Reproduced.** Watched happen in the running app.

Every finding and every skeptic verdict states its rung, and nothing gets rounded up: a claim whose proof stopped at rung 3 is reported at rung 3, never written up as settled. The existing bars translate directly. The citation a finding must carry is rung 2, the floor to count at all; BLOCKER's runnable reproduction is rung 4 or 5. The ladder adds the shared grading language, not a new gate. Moving a load-bearing claim one rung further is usually one small script that calls the exact code in question, so a verdict that stops at "plausible" without trying that script has stopped early.

### Skeptic judgment

Disproof runs are the skeptic's first move, not its whole brief. Three filters catch the findings that survive a re-read but still are not defects:

- **Nitpick gravity.** Reviewers fill their review: a finder short on real defects inflates nits to fill the space. A pass whose findings are all nits and style preferences is evidence the change is probably fine, and the report says so plainly instead of dressing the nits up.
- **Hypothetical vs. actual.** "What if the caller passes null" is a finding only if a caller actually can. Trace the call site: input validated upstream, or ruled out by the type system, kills the finding at the trace (rung 3), except at a trust boundary. HTTP, JSON, user input, and untyped callers are not closed by type annotations; there the kill needs runtime validation on the path, or a call graph the checker fully covers.
- **"I would have done it differently."** The most common false positive in review. A preference for another approach is not a defect; it dies unless it names a concrete problem with the code as written.

A kill under any filter is recorded with its reason and lands in the dismissed bucket, same as a kill by disproof.

## 4. The report and the gate

The report lands **on the driving ticket or PR** (session output only when no tracked item exists) and carries:

- Findings ranked **BLOCKER / MAJOR / MINOR / NIT**, each with a citation (file:line and the failing scenario, plus the repro for blockers), its skeptic outcome (confirmed, or surviving-unproven for a downgraded would-be blocker), and the evidence-ladder rung its proof reached. A finding without a citation does not count.
- The finder composition: which lens ran and why, and whether the spec axis had a spec.
- **The clean bill**: what was specifically checked and found correct, each claim with the rung its proof reached. A clean bill on a named hazard is as durable as a finding: it prevents the next reviewer from re-litigating settled ground.
- **The dismissed bucket**: every finding the skeptic killed, one line each: the claim, what killed it, and the rung the kill reached. This is a trust mechanism, not residue. The decider sees what was rejected and why, and can override a kill they disagree with; a dismissed finding carries no weight at the gate unless they do.

Axes are reported separately and **never blended into one verdict**: a passing lens must not soften a failing correctness axis, and there is no overall score to hide behind.

**The gate:** a confirmed BLOCKER must be fixed before the commit (floor layer) or merge (close-out layer). Only **the decider** may waive one, with the reason recorded where the report lives. The implementer never waives its own blocker; the orchestrator surfaces it to the decider, never absorbs it. Everything below BLOCKER advises: the implementer or orchestrator dispositions each finding, fixed or declined with a reason, at their own judgment. Where the repo binds [domain-memory](../../orient/domain-memory/SKILL.md), a declined finding lands as a decision record with its reason, which is what stops the next review from re-raising settled ground.

**Do not loop the review until "clean."** Re-run after fixing what was found; a review re-run on an unchanged diff generates new plausible-sounding findings indefinitely. Two consecutive runs with nothing new confirmed is a stop signal, not a challenge.

## 5. The defect-class checklist (binding slot)

Each repo keeps one file of **defect classes proven in that repo**: the distilled record of what has actually shipped-and-been-caught there. Every finder loads it. The rules that keep it honest:

- **A class is admitted only via a live reproduction**: a defect that actually occurred, reproduced, in this repo. A checklist imported from someone else's war record checks for their bugs, not yours; a hunch dressed as a class bloats the file until nobody reads it.
- **The fixing session proposes the class in the same PR that fixes the defect**, so the class lands with its proof and rides normal review.
- **A class is removed only by an extinction sweep**: evidence the whole pattern is gone from the codebase, never "we haven't seen it lately."

A new repo starts with an empty checklist and that is correct: it fills at the speed real defects escape. A repo with an existing review-standards document adopts it as this binding unchanged.

## 6. Binding slots (the setup interview fills these per-repo)

- **Defect-class file**: where the checklist lives (seeded from the setup template if the repo has none).
- **Layers**: floor only, or floor + orchestrator close-out.
- **Mandatory lenses**: path patterns that pin a lens ("`payments/` always runs the money lens").
- **Live-probe policy**: where proofs may/must touch real services or seeded data, and what is off-limits.
- **Substantiality rules**: changes that are always substantial, regardless of the implementer's judgment.

## Done when (checkable)

- Three isolated finders ran; the spec axis either ran against a spec or reported no-spec; the lens pick is stated; and every finding above NIT went through the skeptic.
- Every reported finding carries its citation and its evidence-ladder rung, no claim reported above the rung its proof reached; every BLOCKER carries its confirmed repro.
- The dismissed bucket lists every skeptic kill with its reason and rung; clean-bill claims state theirs.
- The report (findings, composition, clean bill) is posted on the driving ticket/PR, or delivered in-session when none exists.
- Confirmed blockers are fixed, or waived by the decider on the record. Lesser findings are each dispositioned.
- Any new defect class earned by this review is queued for the fixing PR, with its repro.
- Where domain-memory is bound: finders loaded the decision records, and every declined finding landed there as a record with its reason.

## Attribution

The spec axis, finder isolation, and the refusal to blend axes into one verdict are adapted from Matt Pocock's [`/code-review`](https://github.com/mattpocock/skills) (MIT); the conventions lens derives from its Standards axis, narrowed to repos that document their own standards. The evidence ladder is adapted from Lauren Tan's pstack [`blast-radius`](https://github.com/cursor/plugins/tree/main/pstack/skills/blast-radius) (MIT); the skeptic-judgment filters and the dismissed bucket are adapted from pstack [`interrogate`](https://github.com/cursor/plugins/tree/main/pstack/skills/interrogate)'s lead-judgment guidance, minus its consensus signal: here survival of the skeptic is the only grade, and agreement between finders never outranks it. The skeptic pass, the repro-or-it's-not-a-blocker bar, the clean bill, and the defect-class checklist rules are distilled from review practice that predates this skill: protocols proven in production repos where every one of those rules exists because its absence shipped a defect.

---
name: diagnose
description: The disciplined bug-fixing loop — no fix ships without a cause the fixer can state in one plain sentence, with evidence. Use when any fix is about to ship without a nameable cause, when a bug resists its first fix attempt, or when a bug-shaped lane brief points here.
---

# Diagnose

A fix may not ship without a **named cause**: one plain sentence stating what was wrong, backed by evidence, readable by a non-engineer decider. This skill is the discipline a working lane follows inline when fixing bugs — not a lane type of its own, and deliberately without binding slots: everything repo-specific already arrived in the lane's brief.

**The named-cause test is the trigger, and it binds on every fix.** If you can already state the cause in one sentence and point at the evidence, the loop is satisfied — ship. If you cannot, the loop runs, however small the bug looks. "Hard bugs only" is the wrong gate, because the first fix attempt is where the vibes-fix ships: a change that makes the symptom go away for reasons nobody can state.

## The loop

Six steps, in order. A failed fix re-enters at the step whose output it disproved — usually the hypothesis list, sometimes the repro itself.

1. **Reproduce red.** Write a failing automated test that catches the user's exact symptom, **before any fix attempt** — it is the loop you iterate against now and the regression test you keep after. Where test infra genuinely cannot reach the bug (timing, a third-party boundary), the recorded fallback is a documented manual repro with exact steps, flagged as a fallback at close-out — never silently substituted.
2. **Minimize proportionately.** Shrink the repro until it is **tight** — fast and deterministic enough to iterate against, cutting one element at a time and re-running after each cut. Tight is the purpose and the stopping point: a two-second deterministic loop is the tool; shrinking past it is polishing the repro instead of finding the cause. Non-deterministic bugs minimize toward a reproduction *rate* high enough to debug against.
3. **Hypothesize falsifiably.** Generate several ranked hypotheses before testing any — a single hypothesis anchors on the first plausible idea. Each is stated so evidence could kill it, skeptic-style: "if X is the cause, then changing Y makes the bug disappear." A hypothesis with no prediction is a vibe; sharpen it or discard it.
4. **Instrument.** Evidence gathering precedes any fix attempt. Each probe maps to one hypothesis's prediction, changing one variable at a time — a breakpoint beats ten logs, targeted logs beat logging everything and grepping. Tag every debug probe with one unique prefix so cleanup is a single grep.
5. **Fix.** Only against the hypothesis the instrumentation confirmed. Watch the red test go green.
6. **Regression-test.** Re-run the original, un-minimized repro; keep the failing test from step 1 in the suite as the regression test; grep the probe tag out. Then write the closing artifact.

## The closing artifact

Two things, and close-out audits check for both:

- **The named cause** — one plain sentence a non-engineer decider reads without translation ("the cache key omitted the locale, so two languages shared one entry"), with the evidence that confirmed it.
- **The regression test** — the step-1 test, now green in the suite; or the recorded manual-repro fallback with its exact steps, flagged as a fallback.

An unnamed cause is not done, whatever the symptom is doing.

## Structural causes feed the friction gate

Sometimes the named cause says the bug is a **symptom** — a missing seam, a rule duplicated in N places and updated in N−1. The lane still fixes the instance under this skill's own bar, then reports the structural cause as **friction** — [codebase-review](../../investigate/codebase-review/SKILL.md)'s third entry gate — in its close-out summary. The diagnosing lane never expands its own scope to fix the structure: that is a review-and-disposition matter, decided with more information than the lane has.

## Where it sits in the pack

- **Lane briefs** — [orchestrate](../orchestrate/SKILL.md) points bug-shaped items here, so the discipline arrives with the work.
- **Close-out audit** — the orchestrator's audit checks the two closing artifacts on every bug fix; the named cause is what it reads first.
- **Domain memory** — where the repo binds [domain-memory](../../orient/domain-memory/SKILL.md), a root cause that reveals a **standing fact** (an assumption the repo held that the bug just proved wrong) is offered to it as a fact record: the same correction class as a decider correcting a session, with reality as the corrector.
- **Deliberately not hooked: handoff GOTCHAS.** The durable copy of a diagnosis's lesson is the domain-memory record; writing it into [handoff](../handoff/SKILL.md) GOTCHAS too would be the same meaning in two places.

## Done when (checkable — verify each line before reporting complete)

- The cause is stated in one plain sentence with its confirming evidence, readable by a non-engineer decider — or no fix shipped.
- A failing automated test existed before the fix, caught the user's exact symptom, passes after, and stays in the suite as the regression test; where one genuinely could not reach the bug, the recorded manual repro carries exact steps and is flagged as the fallback at close-out.
- The repro was minimized until tight — fast and deterministic enough to iterate against — and no further.
- Every hypothesis tested carried a falsifiable prediction, and the fix answers the hypothesis the instrumentation confirmed, not a hunch that survived by making the symptom vanish.
- The original un-minimized repro no longer reproduces, and a grep of the probe tag comes back empty.
- A structural cause, where the diagnosis revealed one, is reported as friction toward codebase-review's entry gate, with the instance fixed and the lane's scope unexpanded.
- Where the repo binds domain-memory: a standing fact revealed by the root cause was offered as a record, or there was none.

## Attribution

Adapted from Matt Pocock's [`diagnosing-bugs`](https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnosing-bugs) (MIT). The six-step spine is his: build a tight feedback loop and watch it go red, minimize by cutting one element at a time, generate ranked falsifiable hypotheses each stating its prediction (his format and several of these phrasings, near-verbatim), instrument one variable at a time with tagged probes rather than logging everything, write the regression test before the fix and re-run the original repro after, and state the confirmed cause so the next debugger learns. So are *tight* as the loop's quality bar, the reproduction-rate framing for flaky bugs, and the post-mortem handoff of architectural causes to his `improve-codebase-architecture` — the seed of the friction-gate escalation here.

What this pack changes: the named-cause test as the binding trigger (any fix shipping without a nameable cause, not hard bugs only), the failing-automated-test-first bar with the documented manual repro as a recorded, flagged fallback, proportionate minimize (tight enough to iterate against is the stopping point, not load-bearing minimality for its own sake), the plain-sentence closing artifact audited at lane close-out, the domain-memory feed for standing facts, and the friction-gate rewiring into codebase-review's entry gate with the diagnosing lane's scope pinned.

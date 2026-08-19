---
name: blast-radius
description: Find what a change breaks somewhere else before it ships, beyond the diff and past where grep stops, and prove the one fact it is safe because of by running real code. Use when asked for the blast radius of a change, when deciding whether an in-flight change is safe to merge, or when reviewing a small diff you do not trust yet.
---

# Blast radius

Find what a change breaks somewhere else, before it ships. Listing the callers is not the job: any agent can grep those in a second. The job is the breakage grep will not show you.

This is the implementing session's own discipline, run before or during the change, pre-merge. [adversarial-review](../adversarial-review/SKILL.md) is the other side of the line: it reviews a finished change with isolated finders and a skeptic gate. Blast radius is what you run on your own work while it is still yours.

## The writeup is not the deliverable

A blast-radius writeup that sounds right is worth nothing on its own. It reads as convincing whether or not it is true, and that is the trap. The deliverable is the proof: find the one fact the change's safety depends on (occasionally a change rests on two; then each gets the same treatment) and get it proven by running code. Words are where you start, not what you hand back.

## The evidence ladder

For each fact the change's safety depends on, push it as far down this ladder as is cheap, and say where it stopped.

1. **You said so.** Worthless on its own.
2. **You pointed at the line.** A real `file:line`, or the library's own source.
3. **You walked the failure.** Step by step, and the bad case does not reach.
4. **You ran it.** A script or test that calls the real code and fails loud if you are wrong.
5. **You reproduced it in the running app.**

Any safety fact that stops short of rung 4 is said out loud as unproven, never written up as settled. Rung 4 is usually one small script that imports the same library the app ships and calls the exact function you are worried about.

## Steps

1. **Read the change.** The diff, the symbols it adds, changes, and deletes, and what it now does differently, including the part the diff does not spell out. When a PR exists, pull it and its commits for the stated intent; mid-change, before any PR, read the working diff and the branch's commit messages instead.
2. **Find the one fact it is safe because of.** Most changes that look scary are safe because of a single fact, like "this call only drops already-dead cache entries and does nothing else". Find that fact. If it holds, most of the scary cases die at once. Spend your time here, not on a long list of maybes.
3. **Look where grep stops.** Read the source of the library you call, at its pinned version, plus any local patch. Work out when things run: microtasks, unmount and teardown, one framework's scheduling versus another's. Follow what a symbol search misses: the JSON an API returns, a DB column, a wire format, another language reading the same bytes, a feature flag, code three hops downstream.
4. **Grade each risk honestly.** Give it a real chance of happening and a real cost if it does. Keep the risks you confirmed; list the ones you checked and cleared separately. Cite a real `file:line`, treat a search that finds nothing as an answer worth recording, and never invent a caller or an API.
5. **Prove the one fact.** Write a script or test that runs the real code, run it, and paste what happened. If you cannot prove it cheaply, mark it unproven. Never round up.
6. **Escalate a wide change.** When the change is big or touches many seams, finish your own pass first, then hand the change to [adversarial-review](../adversarial-review/SKILL.md): isolated finders catch real bugs a single perspective misses.

## What to hand back

- **What it does.** What changed, including the part that is not obvious.
- **The one fact it is safe because of.** State it, name the rung it reached, and show the proof. If you could not prove it, write unproven.
- **Risks.** Only the real ones. Each names how it breaks, the `file:line`, how likely, how bad, and how to check. Paste the proof for the ones that matter.
- **Cleared.** What you checked and why it is fine.
- **Before you merge.** The cheapest test or repro that catches the real bug, including the script you wrote.

Run the prose through [plainspoken](../../author/plainspoken/SKILL.md), and strip anything private before the writeup goes anywhere public.

## Done when (checkable: verify each line before reporting complete)

- The one fact the change is safe because of is stated in a single sentence, with the ladder rung it reached; when the change rests on two facts, each has its own sentence and rung.
- Every safety fact that stopped short of rung 4 is labeled unproven; none reads as settled.
- Every kept risk carries a real `file:line`, a likelihood, a cost, and a way to check it.
- Cleared items sit in their own list, apart from confirmed risks.
- At least one place grep stops was actually read (library source at the pinned version, timing, a wire format, a flag, or a downstream hop), or the writeup says why none applies.
- The rung-4 script, where one exists, appears in the writeup with its pasted output.

## Attribution

Adapted from Lauren Tan's [blast-radius](https://github.com/cursor/plugins/tree/main/pstack/skills/blast-radius) in pstack (MIT). The evidence ladder, the one-fact discipline, the steps, and the hand-back shape are hers, kept intact. What changed: pstack's sibling references were removed or remapped to this catalog (the `how`/`why` companions dropped, `arena` remapped to adversarial-review for wide-change escalation, `unslop` remapped to plainspoken for the prose pass); the skill is agent-invoked here rather than user-only; and the body was re-expressed in house idiom with a checkable Done-when section.

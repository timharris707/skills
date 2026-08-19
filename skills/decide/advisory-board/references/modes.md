# Board Modes

A **mode** is the board's interaction topology — who sees whom, in what order, and how the run ends. It is orthogonal to every other axis: any mode composes with any board size, lens preset, tier, or output shape. The vocabulary is shared with panely.ai, so one set of names covers both products.

| Mode | One-liner | Reach for it when |
| --- | --- | --- |
| **Formal Board Review** (default) | Independent first round, rebuttal, and a structured verdict. | The stakes are real and you want positions formed *before* anyone can anchor anyone else — plan reviews, red-teams, go/no-go calls. |
| **Roundtable** | Collaborative judgment and synthesis. | You want the models building on each other — diagnosis, planning, everyday decisions where cross-pollination beats isolation. |
| **Competitive** | Rival proposals, critique, and voting. | You want *options*, not a verdict — ideation, naming, alternative designs, "pitch me three ways to do this." |

The guided intake recommends a mode from the user's stated goal (`references/intake-interview.md`) and the user confirms it — a mode is always chosen on the record, never assumed.

## Formal Board Review

The skill's core protocol, defined once in `SKILL.md` §Round Protocol and fully supported by the conductor (`run_board.py`): every seat reviews the source packet blind in round 1, reads the board packet and rebuts in round 2, optionally converges in round 3 while preserving dissent, and a neutral synthesizer writes the handoff with a `ship`/`caution`/`block` verdict. Nothing about it changes by having a name; the name exists so the intake can offer it beside the other two.

## Roundtable

Everyone sees everything; the value is accumulation, not independence.

**Mechanics.** Seats speak in a fixed order, one at a time, for N rounds (default 2). Every seat's prompt carries the full transcript so far — the source packet plus every prior contribution, attributed by seat. An optional **moderator** seat opens the session by framing the agenda (it then leaves the turn order) and closes it by writing the synthesis; without one, the orchestrator synthesizes.

**Run it by hand** (the conductor does not drive this topology yet — run each seat as its own CLI subprocess per `SKILL.md` §CLI Execution Notes):

1. Build the source packet as for any run; data-handling consent applies unchanged.
2. If a moderator is set, prompt it first: frame the question, name the 2–4 sub-questions the panel should cover, take no position.
3. Each round, prompt seats in order. Seat prompt skeleton:

   > You are one voice at a roundtable of AI advisors. Role emphasis: {{LENS}}.
   > The question: {{SOURCE PACKET}}
   > The conversation so far: {{TRANSCRIPT — every prior turn, attributed}}
   > Add what is missing: agree or push back on specific prior points by name, bring evidence no one has brought, and advance the group toward an answer. Do not restate what has been said. End with `POSITION: <one sentence>`.

4. After the last round, the moderator (or you) writes the synthesis: where the panel converged, the strongest unresolved disagreement, and the recommendation — labeled as a roundtable synthesis, not a formal verdict.

**Artifacts.** `turn-<round>-<order>-<seat>.md` per contribution, `synthesis.md` at the end, and `run-metadata.md` as always. A seat that drops mid-run is recorded in `run-metadata.md` (status: dropped) and named in `synthesis.md` — the smaller panel is never presented as full. A roundtable produces no `verdict.json` — it is a conversation record, not a gate input.

**Honesty rule.** A roundtable's agreement is social by construction — later seats read earlier ones. Never present roundtable convergence as independent corroboration; that property belongs to Formal Board Review round 1 only.

## Competitive

Three fixed phases, plus an optional graft-and-verify close (below); the output is a ranked field of ideas, not a consensus.

**Minimum three seats — through the pitch phase.** With two pitches, each voter has exactly one eligible pitch (its own is excluded), so every tally is 1–1 by construction. The intake refuses a two-seat Competitive run and offers a third seat or Formal Board Review instead; and if drops leave fewer than three pitches in the field at the end of the pitch phase, stop and report rather than vote. A seat that drops *after* pitching leaves its pitch votable, so the run continues — its missing critique and vote are stated in `results.md`.

**Mechanics.**

1. **Pitch** — each seat, blind to the others, pitches its strongest proposal for the brief (with its reasoning and the strongest objection it anticipates).
2. **Critique** — each seat reads all pitches and stress-tests the others *by name*: what breaks, what is derivative, what survives. A seat does not defend its own pitch in this phase.
3. **Vote** — each seat votes for the best proposal **excluding its own**, with one paragraph of reasoning. Votes are blind: no seat sees another's vote before casting. Tally decides the winner; ties are reported as ties.

**Run it by hand:** phase 1 prompts carry only the brief + lens; phase 2 prompts carry the brief + all pitches; phase 3 prompts carry the brief, pitches, and critiques — but no votes. Collect votes before revealing any.

**Artifacts.** `pitch-<seat>.md`, `critique-<seat>.md`, `vote-<seat>.md`, and `results.md` (the tally, the winning pitch, and the strongest surviving objections to it). A seat that drops mid-run is recorded in `run-metadata.md` (status: dropped) and named in `results.md` — its pitch stays in the field, its missing votes are stated, never imputed. No `verdict.json`.

**Variant.** Vote on individual *ideas* rather than whole pitches when pitches each contain several separable options; say which variant ran in `results.md`.

### Graft and verify (optional close)

Off by default. The user opts in at intake, on the record, never mid-run. Flag the cost on the intake card before the yes: this close adds a synthesis pass, a per-graft endorsement vote across the losing seats, and a verification pass on top of the three phases, so an opted-in run spends meaningfully more model calls and time than a plain Competitive run.

**Read the field first.** After the tally, before any grafting, judge the shape of the field. When the pitches converge on one shape, that convergence is the answer: record it in `results.md` and ship the consensus shape, with no graft pass and no `synthesis.md` (the file exists only when grafting ran). When the pitches wildly diverge, the brief was under-specified; recommend reframing and re-running the tournament rather than averaging the divergence into a synthesis nobody pitched. A re-run is a new tournament at full tournament cost: it goes back through intake for the user's consent and never auto-launches. Graft-and-verify earns its cost only in the middle ground, where distinct pitches each carry something the winner lacks.

**Mechanics.** The tally still decides the winner; this close starts from that result and never reopens the vote. A tied tally has no graft base: report the tie as the tally rules already require and skip this close entirely, noting in `results.md` that it was skipped for the tie.

1. **Graft.** Take the winning pitch as the base. Walk each losing pitch once, looking for its strongest separable ideas; the signal is usually one or two things per pitch, not most of it. Fold each graft in so the result stays coherent under one mental model, never by mechanical pasting. Treat each graft the way the `--output revised-draft` machinery treats an edit (`SKILL.md` §Artifact Standard): a discrete, attributable change put to the non-winning seats for a per-graft `ENDORSE`/`OBJECT`/`ABSTAIN` vote. The vote informs, never gates: the conductor folds or drops each graft on its own judgment, and the full tally travels with the graft in `synthesis.md` so the human sees where seats objected. A seat that dropped before the close, or returns no vote, is recorded as `NO VOTE`, distinct from `ABSTAIN`. Objections are recorded for a human to read, never resolved by another model loop.
2. **Record.** Write down what was grafted and from which seat, and what was considered and rejected and why. The rejection notes are the highest-signal part of the record: future readers learn from what was weighed and dropped, not just from what was kept.
3. **Verify.** The synthesis faces the same scrutiny as any seat output; winning the tournament earns no pass. Re-run the critique shape against the synthesized pitch (each seat stress-tests it by name), fold confirmed problems back in or record them as open, and record the outcome. A problem no pitch caught means the brief was wrong: reframe. A problem one losing pitch caught means the graft walk missed it: go back to step 1.

**Artifacts.** One additional file, `synthesis.md`: the synthesized pitch, the graft record (each graft with its source seat and its endorsement tally), the rejection notes, and the verification outcome. `results.md` and the tally are unchanged, and there is still no `verdict.json`; the synthesis is a record for the human, never a gate input.

**Attribution.** This close is adapted from phases E and F of Lauren Tan's [`arena`](https://github.com/cursor/plugins/tree/main/pstack/skills/arena) (MIT): the winner-as-base grafting, the rejection notes as the highest-signal part of the record, verification that grants no pass, and the convergence and divergence heuristics are hers. The per-graft endorsement vote is this skill's addition, reusing its revised-draft convention.

## Choosing a mode

The intake maps the user's goal to a recommendation — always shown as a recommendation the user confirms, never auto-applied:

| Intent (what the user wants) | Recommended mode | Default lens preset |
| --- | --- | --- |
| **Decision** — help me decide between real stakes | Formal Board Review | by subject (`business-decision`, `software-architecture`, …) |
| **Stress-test** — attack this plan / design / draft | Formal Board Review | `red-team` for hostile review, else by subject |
| **Compare** — weigh these named options against each other | Formal Board Review | by subject |
| **Ideation** — generate and rank alternatives | Competitive | by subject |
| **Explore** — think this through with me, no verdict needed | Roundtable | by subject |

When the goal straddles intents, recommend the mode matching the *deliverable* the user described (a verdict → formal; a shortlist → competitive; understanding → roundtable) and say why.

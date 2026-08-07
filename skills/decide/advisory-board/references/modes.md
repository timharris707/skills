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

**Artifacts.** `turn-<round>-<order>-<seat>.md` per contribution, `synthesis.md` at the end, and `run-metadata.md` as always. A roundtable produces no `verdict.json` — it is a conversation record, not a gate input.

**Honesty rule.** A roundtable's agreement is social by construction — later seats read earlier ones. Never present roundtable convergence as independent corroboration; that property belongs to Formal Board Review round 1 only.

## Competitive

Three fixed phases; the output is a ranked field of ideas, not a consensus.

**Mechanics.**

1. **Pitch** — each seat, blind to the others, pitches its strongest proposal for the brief (with its reasoning and the strongest objection it anticipates).
2. **Critique** — each seat reads all pitches and stress-tests the others *by name*: what breaks, what is derivative, what survives. A seat does not defend its own pitch in this phase.
3. **Vote** — each seat votes for the best proposal **excluding its own**, with one paragraph of reasoning. Votes are blind: no seat sees another's vote before casting. Tally decides the winner; ties are reported as ties.

**Run it by hand:** phase 1 prompts carry only the brief + lens; phase 2 prompts carry the brief + all pitches; phase 3 prompts carry the brief, pitches, and critiques — but no votes. Collect votes before revealing any.

**Artifacts.** `pitch-<seat>.md`, `critique-<seat>.md`, `vote-<seat>.md`, and `results.md` (the tally, the winning pitch, and the strongest surviving objections to it). No `verdict.json`.

**Variant.** Vote on individual *ideas* rather than whole pitches when pitches each contain several separable options; say which variant ran in `results.md`.

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

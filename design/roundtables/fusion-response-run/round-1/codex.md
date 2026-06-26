**Verdict**
Caution, high confidence. Proceed, but narrow the response to one milestone: ship an inline/local escalation mode plus clearer structured output and positioning. What would change my view: credible user evidence that customers care more about domain-tool pass-through or a public benchmark than about invoking the board from their existing agent workflow.

**Candidate Calls**
| Candidate | Call | Rationale | Main Risk | Would Change If |
|---|---:|---|---|---|
| 1. Inline / embeddable escalation | ADOPT NOW, rank 1 | Biggest GTM gap versus Fusion. Build as a thin local tool/CLI/MCP wrapper over existing conductor, not a new hosted API. | Bypassing egress, provenance, or gate rules to feel “lightweight.” | If users mostly run planned full reviews and rarely need selective escalation. |
| 2. Sandboxed execution-grounded seats | DEFER, rank 4 | Valuable, but heavier than inline. Existing command re-execution is post-verdict and allowlisted, not seat-level test execution. | False security, arbitrary execution, secret leakage. | If a separate deep dive proves a strong sandbox story with low UX cost. |
| 3. MCP / domain-tool pass-through | DEFER, rank 6 | High enterprise upside, but it blows up the consent and exfiltration model. Needs capability manifests first. | Credentials/internal data leaking through peer rounds or artifacts. | If one concrete buyer use case requires DB/API grounding and accepts a read-only capability policy. |
| 4. Crisper structured output | ADOPT NOW, rank 2 | Add `partial_coverage`, `unique_insights`, `blind_spots` as optional verdict fields. This strengthens the inline mode. | Schema/render churn and duplicated caveats. | If schema consumers are too brittle for an additive `@3`; then add as render-only first. |
| 5. Published benchmark | DEFER, rank 5 | Useful for credibility, but premature until the inline contract and schema are stable. | A weak benchmark damages trust more than no benchmark. | If sales/adoption stalls specifically on proof that debate beats solo. |
| 6. Positioning / differentiation | ADOPT NOW, rank 3 | Make the moat explicit: subscription/local economics, debate, evidence verification, and gateable verdicts. | Overclaiming privacy or verification. | If Fusion also ships local, repo-grounded, gateable provenance at similar economics. |

**Recommended Execution Sequence**
1. Add an `ask` or `one-shot` mode: one command takes a question/source, runs 2 to 3 seats in parallel, optionally runs the neutral synthesizer, prints compact JSON to stdout, and still writes minimal `/tmp` provenance.
2. Add optional verdict fields: `partial_coverage`, `unique_insights`, `blind_spots`, maybe `raw_seat_summaries`.
3. Ship positioning docs and examples around “deliberation workflow with a gateable verdict,” not “another model endpoint.”
4. Then pursue execution-grounded seats by extending the existing allowlisted command verification model.
5. Build an internal benchmark harness before publishing numbers.
6. Only then design MCP/domain-tool pass-through with explicit read-only scopes, credential policy, and per-tool egress disclosure.

**Invariants**
Do not bypass data handling for convenience. Do not run a one-seat “board.” Do not silently substitute models. Do not weaken read-XOR-network for repo-grounded gate mode. Do not claim verification proves reasoning correctness. Keep artifacts/provenance even for inline mode. Refuse a metered hosted API clone that gives up subscription CLIs, local-only mode, and gateable evidence.

**Strongest Objections**
Inline mode can dilute the product if it becomes a shallow Fusion clone. The answer is to make it a local escalation wrapper around the conductor, not a server-side model id.

Privacy positioning is fragile: the default board sends data to external providers. The honest moat is controllable egress, local-only option, and provenance, not “private by default.”

Benchmarks are tempting but dangerous now. Without stable output fields and a frozen runner, a public DRACO-style number will be hard to defend.

**Evidence**
- [verified: opened the file in the repository and read the line] `SKILL.md:23`: “Use subscription CLIs by default, not provider API keys.”
- [verified] `SKILL.md:98-101`: round 2 is a rebuttal pass where seats read the prior board packet and revise.
- [verified] `SKILL.md:117-119`: the current design already calls for neutral synthesis, evidence-backed/judgment/couldn’t-verify buckets, and `verdict.json`.
- [verified] `scripts/_conductor/cli.py:592-646`: current public surface is CLI subcommands, not an embeddable server/tool interface.
- [verified] `references/verdict-schema.md:131-140`: gate abstains when the board is torn or a citation is refuted.
- [verified] `references/data-handling.md:37-40`: repo gate mode is read-XOR-network, and snapshot scope is consent/verify, not physical read confinement.
- [verified] `scripts/verify_evidence.py:42-81`: command re-execution is opt-in, allowlisted, and “not a kernel sandbox.”
- [verified] `references/board-composition.md:16`: `ollama` local seats are registered for must-not-leave material.
- [packet-only] Fusion’s 1 to 8 model panel, JSON judge fields, pass-through pricing, server-tool beta, and DRACO claim are supported by the provided packet, not by files in this repo.

**Ask Other Seats To Challenge**
Challenge whether inline should be CLI-only first or MCP-first. Challenge whether `partial_coverage` and `blind_spots` should be schema fields or derived renderer sections. Challenge whether MCP/domain tools should be rejected outright until sandboxed execution exists.

VERDICT: caution

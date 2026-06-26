**1. Updated Verdict**

Caution, high confidence. Proceed, but only by narrowing the response to a local, embeddable escalation workflow plus positioning and additive schema clarity, not a hosted Fusion clone. I would change to `block` if the next milestone requires a metered API/model-id product or weakens egress, provenance, or gate abstention.

**2. Changed Mind / Dissent**

Changed with Claude: I now agree “biggest capability gap” is too broad. Inline is only valuable if it is a local wrapper over the conductor; chasing Fusion’s hosted model-id shape is a category error.

Changed with Gemini: I take the background CLI DX risk more seriously. The inline tool should behave like an async local job with preflight/status/artifact paths, not promise a fast synchronous answer.

Still dissent with Claude: I would not put positioning alone as the next milestone. GTM needs a callable surface so other agents can actually escalate to the board.

Still dissent with Gemini: CLI DX is a scoping constraint, not a blocker. The repo already has preflight, timeouts, failure classification, and `--synthesize`; packaging that behind a local tool is feasible.

**3. Candidate Calls**

| Candidate | Call | Rationale | Main Risk | Would Change If |
|---|---|---|---|---|
| 1. Inline / embeddable escalation | ADOPT NOW | Build a thin local CLI/MCP-style wrapper over `run_board.py`, not a hosted API. | Bypassing consent, provenance, or gate semantics to feel “instant.” | Wrapper cannot preserve egress hash, read-XOR-network, and artifact bundle. |
| 2. Sandboxed execution-grounded seats | DEFER | Valuable, but broader than command-evidence verification and security-heavy. | Turning seats into arbitrary code runners. | A real kernel sandbox + safe test-run profile is proven. |
| 3. MCP / domain-tool pass-through | DEFER, and reject for gate+repo by default | Useful for bespoke advisory boards, dangerous for gateable verdicts. | Tool outputs become exfil and prompt-injection channels. | Tools are local/read-only/capability-scoped with output redaction and no network conflict. |
| 4. Crisper structured output | ADOPT NOW | Add `partial_coverage`, `unique_insights`, `blind_spots` as informational fields. | New fields accidentally move the gate. | Existing `caveats`/`open_questions` prove sufficient in real runs. |
| 5. Published benchmark | DEFER | Needed for credibility, not the first response to Fusion. | Slow, noisy benchmark distracts from distribution. | Buyers/users ask for proof before trying the tool. |
| 6. Positioning / differentiation | ADOPT NOW | Make the moat explicit: deliberation workflow, gateable verdict, subscription economics, privacy/local, verifiability. | Overclaiming debate without benchmark evidence. | Users clearly prefer fast single-call answers over verifiable workflow. |

**4. Strongest Remaining Objections**

The Fusion trap is real: becoming a metered inline model product discards the board’s strongest advantages.

The CLI integration path can be brittle: auth, stale model names, long latency, and hanging CLIs have to be handled as product surface, not hidden internals.

Domain-tool pass-through is the highest-risk candidate. It can violate the read-XOR-network model unless scoped to advisory mode or local-only tools.

There is still no verified benchmark here proving cross-reading debate beats a judge/synthesis-only panel. Treat “debate is better” as positioning hypothesis until measured.

**5. Recommended Execution Sequence**

1. Rewrite positioning now: “local deliberation workflow with a gateable, abstaining verdict,” not “Fusion-compatible model.”
2. Ship a local one-shot escalation surface: `advisory-board ask` or MCP tool that runs preflight, one quick board, optional `--synthesize --strict-exit`, and returns `verdict.json` plus artifact paths.
3. Add additive schema/render support for `partial_coverage`, `unique_insights`, and `blind_spots`; keep them out of gate logic.
4. Design execution-grounded seats separately, starting from command-evidence constraints rather than general bash access.
5. Defer MCP/domain-tool pass-through to advisory/local-only profiles.
6. Benchmark after the integration exists, using logs from real one-shot escalations.

Single highest-leverage move: the local embeddable escalation milestone, with positioning included in the same release notes/docs.

One thing to refuse: a hosted metered `advisory-board/fusion`-style model id that bypasses local subscriptions, local-only mode, provenance artifacts, or the abstaining gate.

**6. Invariants And Guardrails**

No gateable run may weaken read-XOR-network.

New structured fields are informational only; the gate continues to read observed verdicts and refuted citations, not confidence or narrative fields.

At least two seats must actually run; degraded/dropped seats stay visible.

No silent model substitution.

No prompt, packet, artifact, or metadata may store secrets.

Domain tools are off by default for gate+repo and must be capability-scoped before advisory use.

The conductor should plumb facts and tokens; models reason. Do not add semantic claim clustering in deterministic code.

**7. Risks, Stale Assumptions, Missing Evidence**

Model names are volatile and there is apparent doc/code drift: the skill text names Gemini 3.1 Pro while the registry default is Gemini 3.5 Flash. Treat model IDs as a preflight concern, not a promise.

I could not verify Fusion’s public claims against the web in this read-only repo review; those remain packet-only.

The snapshot does not substantiate a DRACO-style benchmark for this skill. “Debate beats solo” remains unproven here.

Execution-grounded seats are riskier than current command-evidence re-execution because they let the debating agent run code before synthesis.

**8. Concrete Evidence**

`SKILL.md:23` [verified: opened the file in the repository and read the line] says the default is subscription CLIs, not provider API keys. This grounds the economics/moat claim.

`SKILL.md:82` [verified: opened the file in the repository and read the line] describes repo-grounding as a read-only snapshot with scope hash and manifest. This grounds the provenance/consent advantage.

`SKILL.md:86` [verified: opened the file in the repository and read the line] says gate+repo refuses non-network-isolatable seats such as Gemini/Antigravity. This grounds the read-XOR-network guardrail.

`references/data-handling.md:37-40` [verified: opened the file in the repository and read the line] states exfil control is network isolation, not read confinement. This is why domain-tool pass-through is risky.

`scripts/_conductor/registry.py:177-186` [verified: opened the file in the repository and read the line] builds Codex with read-only sandbox, `--ephemeral`, and `-C` workdir. This grounds feasibility for local wrapping.

`scripts/_conductor/registry.py:194-206` [verified: opened the file in the repository and read the line] says Gemini has no reliable flag to disable GoogleSearch grounding. This grounds the gate refusal.

`scripts/_conductor/egress.py:274-297` [verified: opened the file in the repository and read the line] implements the hard-stop refusal for gate+repo with unisolatable seats.

`references/verdict-schema.md:68-69` [verified: opened the file in the repository and read the line] says confidence is informational and the gate never reads it. New fields should follow this pattern.

`scripts/board_verdict.py:223-239` [verified: opened the file in the repository and read the line] defines abstain conditions from observed seat agreement and refuted citations, not prose.

`scripts/_conductor/cli.py:531-619` [verified: opened the file in the repository and read the line] shows the current surface is CLI subcommands and flags, including `--synthesize`, not an embeddable server/tool yet.

`scripts/_conductor/synthesizer.py:1-20` [verified: opened the file in the repository and read the line] shows a neutral synthesizer already exists and validates merged output, supporting a thin one-shot wrapper.

`references/verdict-schema.md:73-75` [verified: opened the file in the repository and read the line] lists current verdict fields; Fusion-style `partial_coverage` and `unique_insights` are not present in the schema section.

Fusion facts in the prompt, including one API call, 1-8 models, judge JSON, and DRACO claims, are [packet-only: supported by the material above but not checked against the tree].

VERDICT: caution

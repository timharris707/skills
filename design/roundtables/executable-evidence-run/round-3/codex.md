1. **Updated Verdict**  
Build with constraints. Confidence: high. What would change it: a prototype that proves real read confinement, network denial, CPU/memory/pid caps, and output redaction against malicious-repo fixtures before any model-driven seat-time execution is allowed.

2. **Changed Mind / Dissent**  
Changed toward Claude: execution output is itself an egress bus. The repo persists seat stdout/stderr into round artifacts, and later rounds read prior outputs, so “network off” is insufficient if command output can carry secrets.

Changed toward Gemini: latency and operational drag argue for brokered deterministic receipts first, not a VM/container seat-time free-for-all first.

Still dissent: I would not make provider-native execution the abstraction. Codex can already execute, Gemini cannot, and Gemini’s network cannot be removed. A uniform broker should execute commands and give all seats receipts.

3. **Strongest Remaining Objections**  
Prompt-injection-driven execution remains the main risk. Prompt text correctly says repo files are data, but that is model hygiene, not a security boundary.

Codex read-only is not read confinement. The repo explicitly says Codex can read outside the snapshot; an execution mode must not claim snapshot-only reads unless it actually enforces them.

`--allow-program` is a useful receipt discipline, not a kernel sandbox. The tool itself warns an allowlisted process can read accessible files and persist output.

Current resource control evidence is thin: I verified timeouts/process-group kill, but not CPU, memory, pid, disk, or network-namespace enforcement.

4. **Recommended Execution Sequence**  
P1: Build deterministic brokered execution receipts. Commands are user/config declared, not chosen freely by a seat. Reuse the existing no-shell, program-pinned, curated-PATH, scrubbed-env, isolated-cwd pattern. Add output scanning/redaction before any receipt enters round artifacts.

P2: Add execution consent/disclosure: exact commands, programs, args policy, repo scope, network posture, writable dirs, output recipients, and retention. Execution output must be treated as provider-egressed material.

P3: For repo-touching commands, move from subprocess discipline to a real sandbox: read-only repo snapshot mount, no network, separate tmp/HOME, CPU/memory/pid/file/output caps, and destroyed-after-run state.

P4: Let seats request commands only through the broker policy. Rejected requests become advisory notes, not executed shell text.

P5: Gate mode may consume brokered receipts, but open-ended model-chosen execution stays advisory-only.

5. **Invariants And Guardrails**  
No repo-grounded execution with network. No shell. No path-based executable. No cwd PATH resolution. No inherited secrets. No writes to the source tree. No dependency install/postinstall/network fetch in gate mode. No unredacted stdout/stderr into artifacts. No gate-bearing claim based on a sandbox that lacks real read confinement.

The one thing that must never be allowed: a poisoned in-scope repo file causing a seat to run attacker-chosen code with both repo read access and any egress path, including cross-provider artifact egress.

6. **Risks / Missing Evidence**  
Stale assumption: CLI isolation flags were grounded on June 25, 2026, and must be rechecked before relying on them.

Missing evidence: I found no tests in this snapshot via `rg --files -g '*test*' -g 'tests/**'`, despite `scripts/README.md` saying the test suite exists. Treat safety tests as unverified here.

Couldn’t verify: actual network namespace behavior, read confinement, CPU/memory/pid caps, output secret scanning after command execution, and malicious-repo execution fixtures.

7. **Concrete Evidence**  
- Adapter isolation is centralized in `registry.py`; it lists read-only and network-removal flags at `scripts/_conductor/registry.py:56-65` [verified: opened the file in the repository and read the line].
- Codex uses `codex exec --sandbox read-only`, adds `--ephemeral`, and sets `-C` when a workdir exists at `scripts/_conductor/registry.py:169-186` [verified].
- Codex network isolation is a registry claim, “DNS fails inside,” at `scripts/_conductor/registry.py:412-431` [verified].
- Gemini uses `--approval-mode plan --skip-trust`, but comments say network is not enforceable at `scripts/_conductor/registry.py:194-206`; the adapter sets `isolates_network=False` at `scripts/_conductor/registry.py:434-449` [verified].
- Read-XOR-network and R9 are explicit: `references/data-handling.md:37-40` says gate mode relies on network isolation, not read confinement, and Codex can read outside the snapshot [verified].
- Gate + repo refuses unisolatable network seats at `scripts/_conductor/egress.py:274-297` [verified].
- Command re-execution is opt-in, program-pinned, no-shell, curated-PATH, isolated-cwd/HOME, scrubbed-env, but “not a kernel sandbox” at `scripts/verify_evidence.py:42-81` [verified].
- The implementation enforces bare program allowlisting and regex arg refinement at `scripts/verify_evidence.py:231-273` [verified].
- Command execution uses curated PATH, closed stdin, captured output, and process-group start at `scripts/verify_evidence.py:298-327` [verified].
- Seat subprocesses have process-group timeouts at `scripts/_conductor/spawn.py:78-114`, and the adapter default cap is 900s at `scripts/_conductor/registry.py:80-86` [verified].
- Seat stdout/stderr are persisted into artifacts at `scripts/_conductor/rounds.py:267-276` [verified].
- Later-round prompts include prior reviews as data under review at `scripts/_conductor/prompts.py:250-267` [verified].
- A `verified` stamp proves receipt resolution, not inference soundness, at `references/verdict-schema.md:92-101` [verified].

VERDICT: caution

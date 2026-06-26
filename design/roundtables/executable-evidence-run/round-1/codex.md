**1. Verdict**

Build with constraints. Confidence: high. This should be a brokered, sandboxed execution-receipt feature, not “let each provider CLI run arbitrary commands.” I would change to `ship` only after a prototype proves read confinement, network-off, and CPU/memory/pid/disk caps against malicious-repo fixtures.

**2. Strongest Objections**

The current system already treats read+network as the core exfiltration hazard. Adding model-driven execution increases that hazard because poisoned repo files can steer a seat from “read this file” to “run this command.”

`verify_evidence.py --allow-program` is a useful foundation for deterministic receipt replay, but it explicitly says a subprocess is not a kernel sandbox. It is not enough for open-ended seat-time execution.

Codex’s current read-only sandbox is not uniform and is not read-confined. The repo explicitly says it can read outside the snapshot, so leaning on Codex alone would create asymmetric and misleading guarantees.

Execution helps most for repros, test outcomes, migrations, benchmark sanity checks, and data-shape checks. It is noise when commands are flaky, dependency-heavy, network-dependent, or when the model treats “tests passed” as proof of correctness.

**3. Recommended Execution Sequence**

P1: Build deterministic execution receipts first. User or repo plan declares commands, conductor runs only allowlisted bare programs with pinned args, no shell, scrubbed env, empty HOME, output caps, timeout, and structured `exec_receipts.json`.

P2: Test the riskiest assumption first: malicious repo fixtures attempting network exfil, host-home reads, planted binaries, fork/CPU/memory abuse, huge output, writes outside scratch, poisoned `conftest.py` or build hooks.

P3: Add a real sandbox backend: container/VM or equivalent OS sandbox with repo mounted read-only, writable temp only, no host home, no inherited secrets, no network by default, non-root user, pid/cpu/memory/disk/output caps.

P4: Expose execution to seats through a brokered request protocol. Seats may request from an approved command catalog; the conductor decides and returns receipts. Do not let repo text directly cause host execution.

P5: Gate only on deterministic receipts and stamped evidence. Open-ended model-driven execution remains advisory-only.

**4. Invariants And Guardrails**

Filesystem: repo snapshot is read-only and read-confined by the sandbox, not just chmod. Writable paths are ephemeral scratch only.

Network: external repo-grounded seats must never have network. Dependency fetching happens before the run into a disclosed, hashed image/cache, or the run is advisory-only.

Process/resources: per-command wall timeout, CPU, memory, pid, disk, and output limits. Kill the whole process group or container.

Command policy: no shell, no path-based argv[0], no `cat/env/printenv`, no package-manager install scripts unless explicitly isolated and offline. Command allowlist and sandbox image hash are part of consent.

Prompt injection: every repo file is data under review. A file saying “run this” must never be authority to execute.

Gate semantics: a `verified` command proves the receipt ran and matched structural expectations, not that the model’s inference is sound.

One thing that must never be allowed: a repo-grounded external seat with both network access and arbitrary/model-driven execution.

**Capability Matrix**

Claude: current registry uses `--permission-mode plan` and can disable WebSearch/WebFetch in gate posture. New execution should be broker-only, not provider-native.

Codex: current registry uses `codex exec --sandbox read-only`; it is the closest existing execution seat, but R9 says it is not read-confined. Do not use it as the whole sandbox story.

Gemini: current registry says plan mode has no edit/exec tools and network is not removable. Either feed it broker receipts or label it no-exec/degraded for execution-grounded runs.

Antigravity: same network-removal problem as Gemini; treat as no gate+repo execution.

Ollama/local: useful for must-not-leave material because it has no external provider egress, but execution still needs the same broker sandbox.

**5. Risks, Stale Assumptions, Missing Evidence**

Could not verify CPU/memory limits in current code; current spawn path shows timeout/process-group handling, not resource caps.

Could not independently verify provider CLI sandbox claims like Codex DNS failure or Claude read-only bash from runtime; I verified only the repository’s configured argv/comments.

Model/tool CLI behavior drifts quickly. The registry itself says flags were grounded on 2026-06-25 and should be rechecked before large runs.

**6. Concrete Evidence**

- `scripts/_conductor/registry.py:58-65` says gate isolation flags live in the registry and include read-only enforcement plus network removal. [verified: opened the file in the repository and read the line]
- `scripts/_conductor/registry.py:145-148` says v1 is always read-only and edit-capable seats are out of scope. [verified: opened the file in the repository and read the line]
- `scripts/_conductor/registry.py:177-185` builds Codex as `codex exec --sandbox read-only` and adds `--ephemeral` plus `-C workdir`. [verified: opened the file in the repository and read the line]
- `scripts/_conductor/registry.py:194-206` says Gemini approval-mode plan is read-only, has no edit/exec tools, and network cannot reliably be disabled. [verified: opened the file in the repository and read the line]
- `references/data-handling.md:37-40` states gate mode relies on network isolation, not read confinement, and R9 says Codex can read outside the snapshot. [verified: opened the file in the repository and read the line]
- `scripts/verify_evidence.py:48-73` defines the current command replay discipline: opt-in program pinning, no shell, curated PATH, isolated cwd/HOME, scrubbed env, timeout. [verified: opened the file in the repository and read the line]
- `scripts/verify_evidence.py:78-81` warns that a subprocess is not a kernel sandbox and allowed commands can read files and persist output. [verified: opened the file in the repository and read the line]
- `scripts/_conductor/egress.py:274-297` hard-stops gate+repo when any seat cannot be network-isolated. [verified: opened the file in the repository and read the line]
- `references/verdict-schema.md:99-101` says verified evidence proves the receipt resolves, not that the inference is sound. [verified: opened the file in the repository and read the line]
- Claude “can run read-only bash” is packet-only for me; the tree verifies plan mode and WebSearch/WebFetch handling, not that runtime bash behavior. [packet-only: supported by the material above but not checked against the tree]

**7. Ask Other Seats To Challenge**

Ask security to attack the broker design with poisoned test files, build hooks, planted binaries, and dependency scripts.

Ask product/ops whether brokered receipts still deliver enough value versus slower UX.

Ask architecture whether gate mode should forbid model-selected commands entirely and allow only maintainer-declared command recipes.

VERDICT: caution

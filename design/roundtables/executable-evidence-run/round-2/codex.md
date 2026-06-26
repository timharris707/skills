**1. Updated Verdict**

Build with constraints. Confidence: high.

What would change it: a prototype that proves real read confinement, network denial, resource caps, and artifact/output redaction under malicious-repo tests would move this toward `ship`; failure to prove those in a provider-independent sandbox should move it to `block`.

**2. Changed My Mind / Dissent**

Changed toward Claude: Claude’s persisted-artifact objection is stronger than I weighted in round 1. Even with network off, command stdout/stderr and `observed.output` can become an egress channel. The repo itself acknowledges this for command reruns: allowlisted commands can read files and persist them into `verdict.json` [verified: opened the file in the repository and read the line: `scripts/verify_evidence.py:78-81`].

Changed toward Gemini: I now agree more strongly that provider-native execution should not be the abstraction. Codex can already run commands, but R9 says its read-only sandbox does not physically confine reads to the snapshot [verified: `references/data-handling.md:40`]. That disqualifies “just use each CLI’s native execution” as the safe envelope.

Still dissent with Gemini: “Standardized local container driver” is right directionally, but Docker alone is not a sufficient claim on macOS unless verified with adversarial tests. The requirement is a proved boundary: no network, no host sockets, read-only snapshot mount, ephemeral scratch, CPU/memory/pid limits, and artifact controls.

**3. Strongest Remaining Objections**

The largest unresolved risk is prompt-injection-driven execution from poisoned repo files. Current prompts tell seats repo files are data, not instructions [verified: `scripts/_conductor/prompts.py:112-121`], but prompt hygiene is not a sandbox.

Second, artifacts are egress. A malicious command can print secrets or huge sensitive output into receipts, even if the process has no network.

Third, current subprocess machinery has timeouts and process-group cleanup, but I found no CPU or memory limit in the spawn path [verified: `scripts/_conductor/spawn.py:78-114`]. That is not enough for arbitrary code.

Fourth, the capability matrix is uneven today: Codex executes in read-only sandbox, Gemini is explicitly plan/no tools with non-removable network, and Antigravity is also networked [verified: `scripts/_conductor/registry.py:177-206`, `scripts/_conductor/registry.py:448-475`].

**4. Recommended Execution Sequence**

P1: Build deterministic execution receipts before model-driven execution. Commands must be declared by user/config, not chosen freely by a seat. Reuse `--allow-program` ideas: bare program allowlist, no shell, pinned args, curated PATH, scrubbed env, isolated cwd, timeout, output cap.

P2: Add a real sandbox driver and test the boundary first. Mount the approved repo snapshot read-only, provide only ephemeral writable scratch, no network, no host home, no Docker socket, no SSH agent, no cloud creds, no package-manager network fetches, hard CPU/memory/pid/file/output caps.

P3: Add malicious-repo tests: planted `pytest`, malicious `conftest.py`, dependency hooks, symlink escapes, secret files, huge output, fork bombs, localhost/network attempts, and attempts to read outside the snapshot.

P4: Integrate with seats as receipt-grounding, not seat autonomy. A seat can request/suggest a run, but the conductor/broker decides whether it matches policy. Gemini should be labeled honestly as “receipt-fed, no native execution,” not equivalent execution.

P5: Gate policy. Execution-capable model reasoning must be advisory-only. Deterministic broker receipts may feed `verify_evidence`, but a model-driven execution seat must not carry a CI gate until the schema and gate logic can refuse/abstain on `exec_used`.

**5. Invariants And Guardrails**

No read+network for repo-grounded execution. Existing gate mode already refuses grounded runs when a seat cannot be network-isolated [verified: `scripts/_conductor/egress.py:274-297`].

No provider-native arbitrary command execution as the safety boundary.

No shell, no path executables, no cwd-planted binaries, no inherited secrets, no inherited HOME, no package installs unless pre-fetched outside the seat run and explicitly consented.

Filesystem must be read-confined by the sandbox, not just chmod. The existing snapshot is useful but explicitly not enough as the primary write/read boundary [verified: `scripts/_conductor/grounding.py:294-301`].

Every receipt must include command, allowed program policy, sandbox image/version, source/scope hash, network status, exit code, duration, truncated output, and redaction/secret-scan status.

**6. Risks, Stale Assumptions, Missing Evidence**

Codex network isolation is currently a registry comment grounded on 2026-06-25, not a permanent guarantee [verified: `scripts/_conductor/registry.py:423`]. Reverify per release.

The current `--allow-program` mechanism states plainly that subprocess reruns are “not a kernel sandbox” [verified: `scripts/verify_evidence.py:78-81`]. It is a good receipt discipline, not a seat-time sandbox.

I could not verify any existing test suite in this snapshot; `tests/` is absent from the read-only tree. That makes sandbox boundary tests a prerequisite, not a follow-up.

`board_verdict.py` gates on final-round verdicts and refuted citations [verified: `scripts/board_verdict.py:223-268`]. I did not find schema support for “this verdict used execution,” so adding execution without schema/gate changes would create false confidence.

**7. Concrete Evidence**

`scripts/_conductor/registry.py:58-65` says isolation flags live in the adapter registry, including read-only enforcement and network removal [verified: opened the file in the repository and read the line].

`scripts/_conductor/registry.py:145-148` says v1 is always read-only and edit-capable seats are out of scope [verified].

`scripts/_conductor/registry.py:177-186` builds Codex with `codex exec --sandbox read-only`, `--ephemeral`, and optional `-C workdir` [verified].

`scripts/_conductor/registry.py:194-206` says Gemini approval-mode plan is read-only/no edit-exec tools, but its GoogleSearch network cannot be reliably disabled [verified].

`references/data-handling.md:37-40` states the core model: gate mode uses network isolation, not read confinement, and R9 says Codex can read outside the snapshot [verified].

`scripts/verify_evidence.py:42-81` defines command re-execution as opt-in, program-pinned, no-shell, scrubbed-env, but explicitly not a kernel sandbox [verified].

`scripts/_conductor/egress.py:257-260` says no board subprocess may run before the egress gate passes [verified].

`scripts/_conductor/rounds.py:168-189` points grounded seats at the snapshot and otherwise uses an ephemeral tempdir in gate mode [verified].

VERDICT: caution

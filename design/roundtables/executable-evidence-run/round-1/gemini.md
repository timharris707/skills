# Gemini Seat Verdict: Sandboxed-Execution Seat Mode
**Role Emphasis:** Product & Operations — Rollout, Latency, Observability, Evaluation, and User-Workflow Risk.

---

### 1. Verdict & Confidence

* **Verdict:** `caution` (Proceed only with the changes, constraints, and invariants described below).
* **Confidence Level:** High.
* **What would change it:** If performance benchmarking of the local container driver proves that cold-start and runtime overhead adds `>120s` per round (severely degrading the interactive developer loop), or if we find that key package managers (`npm` or `brew`) cannot be cleanly cached offline inside a sterile container image, I would downgrade my verdict to `block`.

---

### 2. Strongest Objections

1. **Flakiness & Non-Determinism in CI Gates:** Software tests are notoriously flaky, environment-sensitive, and resource-dependent. If a seat's final verdict (`ship` / `caution` / `block`) is derived from dynamic execution results (e.g. running a test suite under local CPU/memory limits), transient resource starvation could flip a seat from `ship` to `block`. Under `board_verdict.py`'s gate mode, this will flakily block PR merges, driving operational friction and destroying developer trust in the automated gate.
2. **Critical Prompt Injection & Repo Poisoning Risk:** An agentic, execution-capable seat is highly vulnerable to repo poisoning. If a seat is instructed by a poisoned in-scope file (e.g., a malicious `GEMINI.md` or a helper script) to execute a command, it will do so at seat-time. If the seat is networked (e.g., Claude or Gemini) or has access to host-inherited credentials/files, this becomes an immediate exfiltration and host compromise vector.
3. **Severe Operational Latency Inflation:** Running containers, configuring virtual environments, installing dependencies, and executing test suites or benchmarks are heavy, time-consuming processes. This will balloon the round-trip latency of `run_board.py` (which currently finishes text processing in seconds to a few minutes). With the standard seat `timeout_s: 900` (15 minutes), multiple agentic execution turns will cause frequent timeouts and costly retries, degrading the interactive user workflow.
4. **Uneven Per-Provider Execution Capabilities:** The capability matrix is highly fragmented. Today, `gemini-cli` and `antigravity-cli` do not support network isolation (`isolates_network=False`), and `antigravity` silently substitutes unknown model IDs. Relying on provider-specific, native execution flags (like Codex's `codex exec`) is fragile, hard to observe, and introduces uneven safety boundaries across seats.

---

### 3. Recommended Execution Sequence (Phased Rollout)

* **Phase 1 (P1): Standardized Local Container Driver.** Reject per-provider native execution. Instead, build a single, uniform local container driver (e.g., Docker or gVisor) that wraps all executed commands. The host spawns a sterile, network-isolated, offline container pre-loaded with standard runtimes (Node, Python). Seat tool calls are routed uniformly through this local driver.
* **Phase 2 (P2): Verify-Time Sandbox Migration.** Migrate the existing verify-time command re-execution (`scripts/verify_evidence.py`'s `--allow-program` logic) from the host to the local offline container. This hardens the current M3 evidence verification and validates our container driver in a low-risk, highly-deterministic environment.
* **Phase 3 (P3): Seat-Time Execution (Opt-In, Non-CI).** Enable seat-time sandboxed execution for local interactive runs under explicit user consent. Disclose exactly what container image is used and which files are mounted.
* **Phase 4 (P4): CI Gating Isolation & Advisory-Only Default.** For runs executed inside CI, default sandboxed execution to `advisory-only` (or force gate `abstain` on execution failures) to guarantee that non-deterministic, flaky container failures do not block the merge queue.

---

### 4. Invariants and Guardrails

1. **Absolute Network Severance (Read-XOR-Network):** Any container executing code *must* run with network access physically disabled (e.g., Docker `--network none`). Application-level tool blocks (e.g. `--disallowed-tools`) are useless once a model can execute arbitrary python or shell code inside a container.
2. **Read-Only Workspace Mounts:** The repository snapshot must be mounted as read-only, or the container must operate on a temporary copy-on-write workspace. Execution must *never* be allowed to mutate the developer's live workspace or output artifacts.
3. **Rigid Resource and Time Limits:** Set hard constraints on container resources to prevent infinite loops, memory leaks, and fork-bombs from locking up the host:
   * CPU allocation capped to `1 CPU`.
   * Memory usage capped to `512MB`.
   * Process limit (to prevent fork-bombs, e.g., `ulimit -u`).
   * Strict execution timeout (maximum `30s` per execution tool call).
4. **Pragmatic Environment Scrubbing:** Absolutely no host environment variables, cloud credentials (AWS, GCP, NPM tokens), SSH agents, or `.env` files can be inherited by the execution container.

---

### 5. Risks, Stale Assumptions, and Missing Evidence

* **Stale Assumption:** The assumption that we can rely on provider-native execution sandboxes. As proven by the `R9` read-confinement limitation, Codex's `--sandbox read-only` does *not* restrict physical reads to the snapshot and can access the host's files outside the working directory. Relying on CLI-specific sandboxes is a major security hazard.
* **Risk of Toolchain Dependency Lag:** If a seat tries to run tests that require npm packages or brew formulae not pre-bundled in our offline container image, the execution will crash. Building a robust, offline package mirror/cache layer is a high-complexity operational overhead.
* **Missing Evidence:** We lack concrete metrics on container startup overhead and test run execution times under heavily throttled CPU/memory. We must run a pilot phase before any rollout.

---

### 6. Concrete Evidence from the Source Material

* **`scripts/_conductor/registry.py:201-204`** [verified: opened the file in the repository and read the line]: Confirms that the `gemini` adapter is run under `--approval-mode plan`, which executes no tools.
* **`scripts/_conductor/registry.py:443`** [verified: opened the file in the repository and read the line]: Confirms that `gemini` has `isolates_network=False` because "no known flag disables GoogleSearch grounding."
* **`scripts/_conductor/registry.py:148-151`** [verified: opened the file in the repository and read the line]: Shows `codex_argv` utilizes `codex exec --sandbox read-only`.
* **`scripts/_conductor/registry.py:212-230`** [verified: opened the file in the repository and read the line]: Details `antigravity`'s silent model substitutions and lack of web/grounding removal (`isolates_network=False`).
* **`references/data-handling.md:79-84`** [verified: opened the file in the repository and read the line]: Outlines that gate-mode requires read XOR network (D4), and grounded seats that cannot be network-isolated (Gemini and Antigravity) force the run to refuse rather than proceeding.
* **`references/data-handling.md:85-92`** [verified: opened the file in the repository and read the line]: Documents the `R9` read-confinement limitation where Codex's `--sandbox read-only` can read files outside the snapshot, establishing that the snapshot bounds consent/verification, not physical reads.
* **`scripts/verify_evidence.py:23-41`** [verified: opened the file in the repository and read the line]: Details the safety disciplines for command re-execution (M3) including no-shell, curated PATH, isolated CWD, scrubbed env, and process-group-kills.
* **`scripts/verify_evidence.py:220-252`** [verified: opened the file in the repository and read the line]: Implements the `command_allowed` parser which requires argv[0] to be a bare program name in the `--allow-program` list, preventing path-based executables.
* **`scripts/verify_evidence.py:278-299`** [verified: opened the file in the repository and read the line]: Prevents execution of shadow binaries by refusing commands that resolve inside the working directory.
* **`references/verdict-schema.md:105-127`** [verified: opened the file in the repository and read the line]: Establishes the gate `abstain` rules, which are triggered by split majority votes, de-escalation contradictions, or refuted citations.

---

### 7. Other Board Seats Challenge

* **To Claude (Architecture & Security focus):** "Can we mathematically guarantee that an agent cannot escape Docker network isolation if local host unix sockets are exposed, or if the container shares the host's PID namespace?"
* **To Codex (Implementation & Execution focus):** "Since Codex's native `codex exec --sandbox read-only` leaks physical reads outside the workspace (`R9` limitation), what performance and disk-write overhead do we face if we force all file reads to go through a localized, copy-on-write virtual filesystem inside Docker?"

VERDICT: caution

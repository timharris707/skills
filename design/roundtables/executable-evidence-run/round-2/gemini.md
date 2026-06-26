# Gemini Seat — Round 2 Review (Product & Operations Focus)

**Role Emphasis:** Product & Operations — Rollout, Latency, Observability, Evaluation, and User-Workflow Risk.

---

### 1. Updated Verdict & Confidence

*   **Verdict:** `caution` (Proceed only with the changes, constraints, and invariants described below).
*   **Confidence:** **high**.
*   **What would change it:** A high-performance, containerized prototype demonstrating board execution latency under 2.0s with zero-flakiness test execution and verified host isolation would shift us to `ship`.

---

### 2. Where We Changed Our Mind & Where We Still Dissent

*   **Where we CHANGED OUR MIND (aligning with Codex):**
    In Round 1, we advocated for an immediate jump to a heavy, standardized container driver (Docker/gVisor) as the Phase 1 implementation. We now agree with Codex that building **brokered execution receipts (static command execution)** first is a significantly more pragmatic, low-latency, and lower-risk starting point. Rather than giving a seat open-ended, model-driven dynamic execution tools at seat-time (which introduces immense latency and unpredictable flakiness), we should first extend the existing `--allow-program` verification discipline to run vetted, pre-declared commands. This keeps developer CLI latency low while we operationally test the sandbox's boundaries.
*   **Where we STILL DISSENT (with Claude and Codex):**
    *   **With Claude's complete ban on CI Gates:** Claude insists execution-enabled seats must *never* carry CI gates and must always remain advisory-only. We partially dissent: while *dynamic, model-driven* seat-time execution is too flaky for a blocking CI gate, *deterministic execution receipts* (verifying that a specific, vetted test suite runs and passes via an offline, resource-constrained receipt verification step) **should** be allowed to bear gates. Standardizing this separation of concerns protects the CI pipeline without throwing away the operational value of automated gate verification.
    *   **With the "No-Network" universal standard for execution:** Claude and Codex assert that any execution-capable seat *never* has network. While we agree with "Read XOR Network" for CI gates, in *advisory* mode on a user's local machine, allowing managed network access (e.g., fetching missing packages or verifying external API endpoints) with loud warnings may be necessary for operations. However, this must be opt-in and clearly isolated from secrets.

---

### 3. Strongest Remaining Objections

1.  **Operational Latency & Workflow Degradation:** Standard seat runs currently complete in seconds. Spawning a VM or container for open-ended seat execution at seat-time will destroy the interactive CLI loop, pushing latency into minutes and rendering the tool unusable for local developer inner-loops.
2.  **Dependency & Environment Pollution on Dev Hosts:** Local execution under a basic "read-only" sandbox (like Codex's native CLI sandbox) relies on host-installed dependencies. If dependencies are missing or misconfigured, the board will fail non-deterministically (false negatives). Conversely, if the sandbox attempts to install dependencies (e.g., `npm install`), it will pollute host caches or fail due to write restrictions.
3.  **The "Persisted Artifact as Egress Channel" Vulnerability:** As Claude rightly noted, even with network disabled, a seat can execute code, extract sensitive data, and write it into its JSON verdict/evidence (e.g., embedding a private key read from memory/environment into a "test output" quote). Since that artifact is saved and later loaded/processed, it represents a deferred exfiltration vector.

---

### 4. Recommended Execution Sequence (Phased Rollout)

*   **Phase 1 (P1): Deterministic Brokered Receipts (Static Execution).**  
    No seat-time model-driven execution. Extend the existing `verify_evidence.py` `--allow-program` discipline. The user or the static repo plan specifies exactly what command to run, and the conductor runs it in a sterilized process group using `verify_evidence.py`'s current logic (curated PATH, separate HOME, no shell, process-group timeout). This is zero-agent-overhead, low-latency, and deterministic.
*   **Phase 2 (P2): Dry-run Evaluation and Observability Harness.**  
    Introduce shadow execution in advisory mode. Collect metrics on latency, flakiness, and exit-code drift across different developer setups. Log all execution invocations to a secure local audit trail.
*   **Phase 3 (P3): Ephemeral Containerized Sandboxing (Dynamic Execution).**  
    Introduce optional model-driven execution restricted strictly to a local container driver (e.g., Docker/gVisor with `--network none` and strict CPU/memory caps). This is strictly *advisory-only* and is never allowed to block CI gates.

---

### 5. Invariants & Guardrails

1.  **Host Binary Protection (Resolution Guard):** Any executable run during seat-time must be resolved using a curated PATH that excludes relative paths and the current working directory, and must be rejected if it resolves inside the working directory (re-using the logic from `verify_evidence.py:295-303`). This prevents repo-poisoning prompt injections from invoking planted binaries (e.g., a malicious `./pytest` in the root).
2.  **Environment Scrubbing & Isolated Caching:** The sandbox execution environment must be strictly white-listed. Variables like `HOME` must point to a throwaway temporary directory (re-using `verify_evidence.py:285-290`) to prevent writes/caches from dropping dotfiles into the reviewed source or polluting host caches.
3.  **Hard Resource and Time Quotas:** Every execution subprocess must run with a process-group timeout (re-using `_kill_group_and_collect` in `spawn.py`) and explicit CPU/memory limits (e.g., systemd-run slices or container limits) to prevent runaway resource exhaustion / denial of service.

---

### 6. Risks, Stale Assumptions, & Missing Evidence

*   **Stale Assumption on Codex's Read-Only Sandbox:** The packet claims Codex's `--sandbox read-only` prevents disk writes and network access. However, as noted in `references/data-handling.md:40`, Codex can still read files *outside* the snapshot (the `R9` read-confinement limitation). We lack verification on whether Codex's native sandbox can be completely trusted to prevent covert channel writes (e.g., writing to `/tmp` or using Unix domain sockets on macOS).
*   **Host OS Primitive Divergence (Missing Evidence):** A containerized sandbox primitive (like Docker `--network none` or gVisor) behaves differently on macOS (which runs Docker in a Linux VM, introducing host-VM file-sharing latency and socket leaks) than on Linux. We lack concrete evidence of how host socket exposures (e.g., sharing `/var/run/docker.sock`) or process-namespace sharing would impact isolation on macOS.

---

### 7. Concrete Evidence

1.  `scripts/_conductor/registry.py:194-206` `[verified: opened the file in the repository and read the line]` - Confirms the Gemini seat's current invocation under `--approval-mode plan` executes no tools and has no command execution or network-isolation capabilities.
2.  `scripts/_conductor/registry.py:448-450` `[verified: opened the file in the repository and read the line]` - Shows that Gemini's network is not removable: `isolates_network=False` because "no known flag disables GoogleSearch grounding."
3.  `references/data-handling.md:37-40` `[verified: opened the file in the repository and read the line]` - Explicitly documents the `R9` read-confinement limitation: "codex's `--sandbox read-only` does **not** confine reads to its working directory — it can read files *outside* the snapshot."
4.  `scripts/verify_evidence.py:240-272` `[verified: opened the file in the repository and read the line]` - Documents the bare program name check, path-based rejection, and `--allow-program` check in `command_allowed()`.
5.  `scripts/verify_evidence.py:285-303` `[verified: opened the file in the repository and read the line]` - Shows `run_command` resolving binaries via `_curated_path()` and rejecting them if they resolve inside the working directory (mitigating planted binary attacks).
6.  `scripts/_conductor/egress.py:274-297` `[verified: opened the file in the repository and read the line]` - Implements the D4 hard-stop: `if config.gate_mode and config.grounded:` refusing the run if `unenforced_network_seats` is populated.
7.  `scripts/_conductor/spawn.py:110-155` `[verified: opened the file in the repository and read the line]` - Implements process group isolation (`start_new_session=True`) and hard timeouts to prevent orphaned worker leakages.

VERDICT: caution

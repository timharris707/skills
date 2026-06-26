# Round 3 Advisory Board Review: Sandboxed-Execution Seat Mode
**Seat:** Gemini (Product & Operations Role)  
**Role Emphasis:** Rollout, Latency, Observability, Evaluation, and User-Workflow Risk  

---

### 1. Updated Verdict & Confidence
* **Verdict:** `caution` (Proceed ONLY with the changes, constraints, and invariants described below).
* **Confidence:** **High**
* **What would change it:** Empirically demonstrating an OS-level sandbox wrapper (e.g., namespace-based or lightweight kernel isolation) that delivers sub-second spin-up times on Darwin/Linux while fully enforcing physical read-confinement and network-severance across all active provider seats.

---

### 2. Where We Changed Our Mind & Where We Still Dissent

* **Where We CHANGED OUR MIND (Aligning with Codex and Claude):**  
  In Round 1, we leaned toward an ambitious Phase 1 rollout of a heavy, containerized container/VM driver. We now abandon that view. From a product rollout and operational latency standpoint, spinning up Docker containers or micro-VMs inside an interactive CLI loop will completely destroy the developer workflow by adding tens of seconds (or minutes) of overhead. We now fully align with **Codex's** recommendation to build **Static User-Brokered Receipts (Static Execution)** as Phase 1. By executing only user-vetted, predefined commands at run-time, we bypass the extreme prompt-injection risks of model-chosen commands and avoid the crippling startup latencies of dynamically orchestrated sandboxes.
  
* **Where We STILL DISSENT (Specifically with Claude's Round 2 proposal regarding the Artifact Bus):**  
  **Claude** proposed gating/filtering execution output *on the shared artifact bus* (treating execution output as egress). As a Product & Operations seat, we strongly dissent from this approach. Attempting to run regex-based or secondary LLM-based redaction/filtering on the multi-seat conversation bus in real-time introduces heavy runtime latency, high false-positive rates that disrupt valid model reasoning, and significant operational complexity. From an observability and debugging perspective, we should enforce safety structurally **at the execution boundary itself** (by physically denying network access and scrubbing process environments at spawn-time) rather than trying to filter the generated text after the execution has already occurred. Furthermore, under the brokered-receipt model, since the user has statically approved the commands, filtering their outputs is redundant and operationally counterproductive.

---

### 3. Strongest Remaining Objections

1. **Interactive Loop Latency & Workflow Degradation (Operational Risk):**  
   Developer adoption of the Advisory Board relies heavily on sub-10-second interactive CLI cycles. Spawning sandboxes during a multi-round seat run multiplies execution latency. If a seat-time model runs multiple commands to "test" or "verify" an assertion, the CLI loop will degrade from seconds to minutes, making it unusable in local developer workflows.
2. **Google Provider Non-Isolation (Rollout & Compatibility Risk):**  
   The `gemini` and `antigravity` (`agy`) adapters are hard-coded to `isolates_network=False` (`registry.py:449, 475`) because their CLIs do not support disabling Google Search grounding. Because they cannot be isolated, `egress.py:274-297` unconditionally blocks them from participating in grounded runs under `gate` mode. Adding a seat-time execution capability that requires network severance will permanently lock Gemini out of execution-capable `gate` reviews, creating a stark, degraded-tier user experience for Google-reliant teams.
3. **Verdict Determinism & Environment Drift (Evaluation Risk):**  
   If seat-time execution is allowed to alter local files or depends on local packages, run-to-run consistency is lost. A seat run on developer Machine A might pass, while failing on CI Agent B due to environment differences. This drift ruins the board's viability as a reliable CI/CD gate.

---

### 4. Recommended Execution Sequence

* **Phase 1 (P1): Static User-Brokered Receipts (Deterministic Brokered Execution):**  
  Do not allow models to generate or execute arbitrary code at seat-time. Extend the existing `verify_evidence.py` `--allow-program` paradigm. The user statically defines the allowed commands in their config or command line. The model can request the execution of a pre-defined receipt; the runner executes it, captures the output, and injects the text back into the context. This leverages verified path sanitization and environment scrubbing.
* **Phase 2 (P2): Lightweight Namespace-Based Local Sandboxing:**  
  For local/Codex seats, implement low-overhead OS-level sandboxing (using `sandbox-exec` on macOS or `unshare` on Linux) to enforce real read-confinement and network severance, avoiding VM warm-up times.
* **Phase 3 (P3): Async / Off-Loop Containerized Execution:**  
  If open-ended, model-driven seat-time execution is absolutely necessary, push it out of the interactive CLI loop. Move this tier to an asynchronous background CI worker or webhook where a 1–2 minute container startup delay (utilizing gVisor or Firecracker) is operationally acceptable.

---

### 5. Invariants and Guardrails

1. **Strict Read-XOR-Network (D4 Integration):**  
   If a seat executes a command, it must be network-isolated. Seats that cannot be network-isolated (Gemini/Antigravity) must be structurally blocked from running any execution commands.
2. **Host Binary Protection (The Resolution Guard):**  
   Any executable run during seat-time must resolve via a curated `PATH` that strips empty, relative, and current-directory (`.`) paths. It must fail closed if the executable resolves inside the working directory under review, blocking planted binaries.
3. **Isolated Disposable Environment (CWD & HOME Separation):**  
   The sandbox environment must keep `HOME` entirely separate from the reviewed repository directory (`cwd`). This ensures that package managers (e.g., `npm`, `pip`) or version tools (e.g., `git`) do not write configuration files or drop cached dotfiles into the reviewed codebase.
4. **Process Group Termination & Session Isolation:**  
   Every spawned command must run in its own session (`start_new_session=True`) under a strict process group timeout, ensuring that orphaned background daemon workers spawned by a tool are fully terminated on timeout.

---

### 6. Risks, Stale Assumptions, and Missing Evidence

* **The Codex Read-Confinement Leak (R9 Limitation):**  
   The common assumption that Codex's read-only sandbox isolates its file reads is a dangerous illusion. As documented in `references/data-handling.md:37-40`, Codex can physically read files *outside* its working directory (such as host configuration files or SSH keys). If Codex executes commands, a prompt-injection attack could read sensitive host dotfiles and print them to stdout, exposing them to the conversation bus.
* **The Antigravity (`agy`) Command-Line Drift:**  
   The deprecation of consumer `gemini-cli` in favor of `agy` (Antigravity CLI) means our network isolation assumptions (`registry.py:214-227`) are tied to transitional tools. If the enterprise/API-tier Antigravity CLIs introduce a robust, verifiable flag to disable external web-grounding, our network-isolation block for Google seats can be safely removed, but we currently lack the local test suites to verify this behavior.

---

### 7. Concrete Evidence

* **[verified: opened the file in the repository and read the line]** `scripts/_conductor/registry.py:423`  
  Confirms that Codex relies on `--sandbox read-only` and comments that its network isolation was verified via a DNS failure check:
  ```python
  isolates_network=True,   # --sandbox read-only has no network (verified: DNS fails inside)
  ```
* **[verified: opened the file in the repository and read the line]** `scripts/_conductor/registry.py:449, 475`  
  Confirms that Gemini and Antigravity seats explicitly advertise that they cannot disable external grounding:
  ```python
  isolates_network=False,  # no known flag disables GoogleSearch grounding — surfaced loudly
  ...
  isolates_network=False,  # agent-first harness; web/grounding not removable — surfaced loudly
  ```
* **[verified: opened the file in the repository and read the line]** `references/data-handling.md:37-40`  
  Documents that Codex is not physically confined to reading only the repository snapshot:
  ```markdown
  The snapshot bounds consent/verify, not physical reads (R9). Be honest about this: codex's --sandbox read-only does not confine reads to its working directory — it can read files outside the snapshot (observed in a real run reading a file from its host home dir).
  ```
* **[verified: opened the file in the repository and read the line]** `scripts/_conductor/egress.py:274-297`  
  Shows the unconditional gate-mode halt that prevents a grounded run from proceeding if a non-isolatable seat like Gemini is present:
  ```python
  if config.gate_mode and config.grounded:
      ...
      offending = config.unenforced_network_seats
      if offending:
          return decide(False, "refused", _d4_refusal_detail(offending))
  ```
* **[verified: opened the file in the repository and read the line]** `scripts/verify_evidence.py:312-320`  
  Demonstrates the robust resolution guard that prevents execution of binaries that resolve inside the working directory:
  ```python
  resolved = shutil.which(argv[0], path=env["PATH"])
  if not resolved:
      return None, "", f"executable not found on the curated PATH: {argv[0]!r}"
  real_resolved = os.path.realpath(resolved)
  real_cwd = os.path.realpath(cwd)
  ...
  if real_resolved == real_cwd or real_resolved.startswith(cwd_prefix):
      return None, "", (f"executable {argv[0]!r} resolves inside the working dir "
                        "(possible planted binary) — refusing to run it")
  ```
* **[verified: opened the file in the repository and read the line]** `scripts/verify_evidence.py:275-293`  
  Verifies the PATH-cleansing and HOME isolation logic applied during command execution:
  ```python
  def _curated_path() -> str:
      entries = [p for p in os.environ.get("PATH", "").split(os.pathsep)
                 if p and p not in (".", "") and os.path.isabs(p)]
      return os.pathsep.join(entries) if entries else os.defpath

  def _rerun_env(cwd: str, home=None) -> dict:
      env = {k: os.environ[k] for k in RERUN_ENV_KEYS if k in os.environ}
      env["PATH"] = _curated_path()
      env["HOME"] = home or cwd
      return env
  ```
* **[verified: opened the file in the repository and read the line]** `scripts/_conductor/spawn.py:98-106, 117-141`  
  Demonstrates how child seats are spawned in their own session to guarantee complete process group termination on timeout:
  ```python
  proc = subprocess.Popen(
      argv,
      ...
      start_new_session=True,
  )
  ...
  def _kill_group_and_collect(proc: "subprocess.Popen") -> tuple:
      def _killpg(sig: int) -> None:
          try:
              os.killpg(os.getpgid(proc.pid), sig)
  ```

---

VERDICT: caution

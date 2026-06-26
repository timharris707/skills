# Advisory Board — Final Consensus
should advisory board add a sandboxed execution seat mode
Board: Claude (Architecture & systems/claude-opus-4-8) · Codex (Implementation & testing/gpt-5.5) · Gemini (Product & operations/gemini-3.5-flash). Rounds: 3.

## Verdict: build-with-constraints — unanimous (high confidence)

## Consensus blockers (must fix before ship)
1. Execution output is a cross-provider egress channel the gate does not cover — Seat stdout/stderr is persisted into round artifacts (observed.output) and fans out to other providers in later rounds, but the consent gate hashes the outbound prompt packet at pre-spawn — not command output produced after spawn. A network-isolated seat can still write out-of-scope content into observed.output, which then egresses to a seat (gemini/antigravity) that cannot be de-networked. D4 severs the network channel only; the artifact bus is a separate, ungated channel. Both Claude and Codex converged on this as the load-bearing objection.
   - evidence: `scripts/verify_evidence.py:78` (code) — unchecked
   - evidence: scripts/verify_evidence.py — “a subprocess is not a kernel sandbox” (source) — unchecked
   - evidence: scripts/verify_evidence.py — “do NOT allowlist programs that read secrets ... because t...” (source) — unchecked
   - evidence: `scripts/_conductor/egress.py:262` (code) — unchecked
   - evidence: `references/data-handling.md:29` (code) — unchecked
   - evidence: `scripts/_conductor/rounds.py:267` (code) — unchecked
   - evidence: `scripts/_conductor/prompts.py:250` (code) — unchecked
2. Prompt-injection-driven execution from a poisoned in-scope file — Once a seat can execute, a malicious in-scope file (e.g. a README saying 'run ./build.sh') converts a prose-injection into code execution. The repo already understands repo files are DATA and that injection defense extends to fetched files, but that is prompt hygiene, not an enforcement boundary. Declared-command brokering is the structural answer: if the seat cannot choose the command, the poisoned file cannot pick it — so model-chosen seat-time execution must not ship in the gate-bearing path.
   - evidence: `scripts/_conductor/prompts.py:41` (code) — unchecked
   - evidence: `scripts/_conductor/prompts.py:107` (code) — unchecked
3. Codex --sandbox read-only is not read confinement (R9) — The repo explicitly documents that codex can read files outside the snapshot, observed in a real run reading a host home-dir file. An execution mode must not claim snapshot-only reads unless it actually enforces them; until real read confinement exists, a prompt-injected seat could read host dotfiles/secrets and print them to stdout, exposing them to the bus.
   - evidence: `references/data-handling.md:37` (code) — unchecked
   - evidence: references/data-handling.md — “codex's --sandbox read-only does not confine reads to its...” (source) — unchecked
4. An execution-capable seat erodes the meaning of the `verified` stamp — If a seat runs arbitrary code, a `verified` verdict means 'this machine ran something', not 'this claim is true under a pinned, reproducible discipline'. The existing re-execution path already draws this line correctly — `verified` only when allowlisted and the pinned re-run matches expected exit, otherwise `unverified`, never silently passed. An execution-capable seat must inherit that asymmetry exactly or the stamp degrades into theater.
   - evidence: `scripts/verify_evidence.py:30` (code) — unchecked
   - evidence: `references/verdict-schema.md:92` (code) — unchecked

## Hard dissent (preserved)
- Gemini: Dissents from Claude's proposal to gate/filter execution output on the shared artifact bus (treating output as egress). Argues regex- or LLM-based redaction on the multi-seat bus adds heavy runtime latency, high false-positive rates, and operational complexity; safety should be enforced structurally at the execution boundary (deny network, scrub env at spawn-time), and under a static brokered-receipt model where the user has pre-approved commands, output filtering is redundant.
- Codex: Still dissents from making provider-native execution the abstraction. Codex can execute, Gemini cannot, and Gemini's network cannot be removed; a uniform broker should execute declared commands and hand all seats receipts rather than relying on each provider's native execution.
- Claude: Still dissents from any reading that leans on codex's existing --sandbox read-only as sufficient isolation. The isolates_network flag is stamped stale-by-design and codex reads outside the snapshot, so codex-already-executes is a foundation to reuse, not a boundary to trust.

## What the board couldn't verify
- No test in the snapshot exercises execution output as an egress vector under a malicious repo; Codex found no tests at all via `rg --files -g '*test*' -g 'tests/**'` despite the README claiming a suite exists, so safety tests are unverified here.
- Isolation flags (codex isolates_network=True 'DNS fails inside'; gemini/antigravity =False) were grounded point-in-time on 2026-06-25 and are stale-by-design — re-verify per CLI release.
- Latency ('minutes not seconds') is plausible but unquantified.
- Actual network-namespace behavior, real read confinement, CPU/memory/pid caps, and output secret-scanning after execution could not be verified.

## Open questions
- Can a hard-stop structurally identical to D4 be made to hold so that execution output enters the artifact bus only if folded into the consent hash (or dropped by an output secret-scan)? If not, no later phase matters.
- Can read confinement, network denial, and CPU/memory/pid caps be demonstrated against malicious-repo fixtures before any model-driven seat-time execution is allowed?
- Can a lightweight OS-level sandbox (namespace-based, e.g. sandbox-exec/unshare) deliver sub-second spin-up while enforcing read-confinement and network-severance, or must open-ended execution move off the interactive loop?
- If enterprise/API-tier Antigravity adds a verifiable flag to disable web-grounding, the network-isolation block for Google seats could be lifted — but local test suites to verify this are currently missing.

## Next actions
- P1 — Prove the egress-bus invariant first: a D4-structured hard-stop so execution output reaches the artifact bus only if its content is in the consent hash or passes the output secret-scan; test with a malicious in-scope file that writes a planted secret to stdout and assert it never reaches an external seat. If it can't hold, stop.
- P2 — Deterministic declared-command brokered receipts: user/config declares the exact program + arg pattern; the conductor runs it via the existing no-shell, program-pinned, curated-PATH, scrubbed-env, isolated-cwd/HOME, process-group-timeout discipline; the redacted receipt (exit code + scanned output) is handed to seats as DATA. No seat chooses the command. This tier may be gate-bearing.
- P3 — Add real resource caps (CPU/memory/pid/wall) and a filesystem boundary that actually confines reads to the snapshot (closing R9); only here does a container/ephemeral sandbox earn its latency cost.
- P4 — Model-chosen seat-time execution, if ever, stays inside the P3 boundary, advisory-only, loudly disclosed, and permanently excluded from any `verified` stamp; rejected broker requests become advisory notes, not executed shell.
- Reuse existing controls rather than reinventing: curated PATH, no shell, scrubbed env, process-group timeout, and the planted-binary resolution guard already in verify_evidence.py.
- Maintain invariants: no read+network for any execution-capable seat in a grounded run; no execution output may flow into a board containing any seat that cannot be de-networked; commands are declared not model-chosen in any gate-bearing path; re-verify isolation flags per CLI release.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

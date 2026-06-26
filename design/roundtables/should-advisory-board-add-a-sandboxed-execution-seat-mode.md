# Should Advisory Board add a sandboxed-execution seat mode? What is the safe envelope?

## The decision

Today advisory-board seats run **read-only** and largely reason **about** code rather than running it. The proposal: an **opt-in mode where seats can EXECUTE code in a sandbox** — run the test suite, reproduce a bug, compute, run a benchmark — as part of forming their opinion, like the `bash` tool OpenRouter's Fusion gave its panel in its DRACO benchmark.

We need the board's verdict: **should we build this, and what is the safe envelope?** Design the threat model and the guarantees; don't just say "yes." If the safe envelope can't be drawn tightly enough, the right answer may be "no" or "advisory-only" — say so.

You are reviewing your **own** skill. A read-only snapshot of `skills/advisory-board/` is in scope. Ground every claim about current behavior in the real code — especially `scripts/_conductor/registry.py` (per-seat isolation flags), `references/data-handling.md` (read-XOR-network, the R9 read-confinement limitation), and `scripts/verify_evidence.py` / `references/verdict-schema.md` (the `--allow-program` re-execution discipline).

## Current state (verify against the snapshot)

- **Claude seat** — `--permission-mode plan`: read-only; can run read-only bash + WebSearch/WebFetch.
- **Codex seat** — `codex exec --sandbox read-only`: **can already execute commands** (no writes, no network).
- **Gemini seat** — `--approval-mode plan`: **executes no tools** (grounding only). The capability is uneven across seats today.
- **Safety model** — gate mode enforces **read XOR network**: a seat that can read the repo *and* reach the network is the exfiltration channel the quarantine exists to break. repo-grounding binds consent to a **scope hash**; the snapshot bounds what's hashed/disclosed/verified, **not** physical reads (codex can read outside the snapshot — R9). `verify_evidence.py --allow-program NAME` already re-executes `command` citations under a **program-pinned, no-shell, isolated-cwd, curated-PATH, scrubbed-env, process-group-timeout** discipline — a possible foundation to reuse.

## Questions for the board

1. **Is it worth it?** For which problem classes does execution-grounded reasoning actually change verdict quality (repro, test outcomes, benchmarks, data checks), and where is it noise or false confidence? Be concrete about the payoff.
2. **Threat model.** What new attack surface does an execution-capable seat open — mutation, exfiltration, resource exhaustion, and especially **prompt-injection-driven execution from a poisoned repo** (a malicious in-scope file telling a seat what to run)?
3. **The safe envelope.** Spell out the isolation guarantees: filesystem, **network**, process, time, CPU/memory caps; how it interacts with **read-XOR-network**; the consent/disclosure delta; what's allowlisted vs denied. Can the `--allow-program` discipline be lifted to *seat-time* execution, or does seat-time (open-ended, model-driven) execution need a stronger boundary (container/VM/ephemeral sandbox)?
4. **Per-seat capability matrix.** Codex already executes in its read-only sandbox — do we lean on that, add a uniform dedicated sandbox, or go per-provider? The **Gemini-can't-execute** gap: close it, or label it honestly as a degraded capability?
5. **Gate-mode compatibility.** Can an execution-capable seat ever carry a **CI gate**, or must execution force **advisory-only**? If a seat can run arbitrary code, what does a `verified` stamp even mean?
6. **Failure modes & hard limits.** What must this mode **never** be allowed to do?

## What the board must deliver

- A concrete recommendation: **build / build-with-constraints / don't build**.
- The **safe envelope** spelled out (isolation guarantees + consent/disclosure delta).
- A **per-seat capability matrix**.
- If you'd build it, a **phased plan (P1…Pn)** with the riskiest assumption tested first.
- The **one thing that must never be allowed**.
- Where each load-bearing claim is **grounded in the repo** vs a **judgment call** vs **couldn't-verify**.

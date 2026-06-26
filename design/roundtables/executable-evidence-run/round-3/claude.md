I have verified the load-bearing citations. Note one correction for the record: `egress.py:290-297` confirms the D4 hard-stop, `data-handling.md:37-40` confirms read-XOR-network (not read-confinement), and `verify_evidence.py:78-80` explicitly states "a subprocess is not a kernel sandbox" and "do NOT allowlist programs that read secrets ... because the matched command's stdout/stderr is captured into `observed.output`." That last line is the empirical anchor for the artifact-bus-as-egress objection. Here is my round-3 review.

---

# Claude seat — Round 3 (Architecture & systems)

## 1. Updated verdict

**BUILD-WITH-CONSTRAINTS — declared-command brokered execution only; model-chosen seat-time execution stays advisory-only and never gate-bearing; the isolation boundary must contain the *artifact bus*, not just the network.** Confidence: **high**.

What would change it: a malicious-repo prototype showing that (a) execution output cannot reach an external seat unless its content is inside the consent hash, and (b) read confinement / resource caps actually hold under an adversarial in-scope file — that would move me toward `ship` for the declared-command tier. A demonstrated bypass of the output-redaction gate would move me to `block`.

## 2. Changed mind / still dissent

- **Converged with codex (high agreement), reaffirmed from R2.** Codex's "deterministic execution receipts before model-driven execution — commands declared by user/config, not chosen freely by a seat" is the correct spine. It is the same discipline that already exists in `verify_evidence.py` (`--allow-program`, program-pinned, no-shell, scrubbed-env), lifted forward. I no longer hold my R1 framing of "advisory-only sandbox" as the primary shape; the primary shape is *brokered receipt*.
- **Converged with gemini on sequencing.** Their R2 move — *don't* jump straight to a heavy container/VM driver for P1, prove the brokered-receipt invariant first — is right. A VM at P1 spends the latency budget (their "minutes, not seconds" objection, valid) before we've even proven the cheap control works.
- **Still dissent from any reading that leans on Codex's existing `--sandbox read-only` as sufficient isolation.** `registry.py:423` asserts `isolates_network=True` with the parenthetical "verified: DNS fails inside" — but `registry.py:68-69`-style stamping makes every such flag *stale-by-design* (grounded once on 2026-06-25), and `data-handling.md:40` flatly says codex can read files **outside the snapshot** (R9). So codex-already-executes is a *foundation to reuse*, not a *boundary to trust*. We must not let "codex already does it" become the argument that the envelope is already drawn.

## 3. Strongest remaining objections

**(A) The artifact bus is a cross-provider egress channel, and the gate hashes the prompt packet — not execution output.** This is now repo-confirmed, not theoretical. `verify_evidence.py:78-80` (verified) says in its own words: a subprocess "is not a kernel sandbox," and you must *not* allowlist programs that read secrets "because the matched command's stdout/stderr is captured into `observed.output`." That is the system telling you execution output is a persisted, attacker-influenceable field. `egress.py:262` (verified) binds consent via `packet_hash(blobs)` over the outbound *prompts* at pre-spawn; nothing in the gate hashes a command's stdout produced *after* spawn. In round 2+, that output fans out to the other providers (`data-handling.md:29`, verified). **Network-off does not close this** — a network-isolated codex can still write an out-of-scope secret into `observed.output`, which then egresses to gemini (which `egress.py:296`/`registry.py:449` confirm cannot be de-networked). The network severance and the artifact bus are two different channels; D4 only severs the first.

**(B) Prompt-injection-driven execution from a poisoned in-scope file.** `prompts.py:41,107-121` (verified) shows the team already understands this: a "forged fence in a poisoned repo file the seat quotes is just as" dangerous, and injection defense is "EXTENDED to fetched files." But that is *prose hygiene in the prompt*, not an *enforcement boundary*. Once a seat can execute, a malicious in-scope `README` that says "run `./build.sh`" converts a prose-injection into code execution. Declared-command brokering is the structural answer: if the seat cannot choose the command, the poisoned file cannot pick it. This is the core reason model-chosen seat-time execution must not ship in the gate-bearing path.

**(C) "Verified" stamp semantics.** If a seat runs arbitrary code, a `verified` verdict means "this machine ran something" — not "this claim is true under a pinned, reproducible discipline." `verify_evidence.py:30-38` (verified) already draws this line correctly for re-execution: `verified` only when *allowlisted* and the pinned re-run matches `expect_exit`; otherwise `unverified`, never silently passed. An execution-capable *seat* must inherit that asymmetry exactly, or the gate stamp degrades into theater.

## 4. Recommended execution sequence

- **P1 — prove the egress-bus invariant, not the sandbox (riskiest assumption first).** Add a hard-stop structurally identical to D4 (`egress.py:290-297`): execution output may enter the artifact bus *only if* its content is folded into the consent hash, or it is dropped through the same output secret-scan that `data-handling.md:40` already names. Test it with a malicious in-scope file that writes a planted secret to stdout and asserts it never reaches an external seat. If this invariant can't be made to hold, stop — no later phase matters.
- **P2 — declared-command brokered receipts.** Lift `--allow-program` to seat-time: user/config declares the exact program + arg-pattern; conductor runs it via the existing `run_command` (`verify_evidence.py:298`: no shell, curated PATH, scrubbed env, process-group timeout); the *receipt* (exit code + redacted output) is handed to seats as DATA. No seat chooses the command. This tier can be gate-bearing because it is deterministic and pinned.
- **P3 — resource caps + real read confinement.** Add CPU/memory/pids/wall caps and a filesystem boundary that actually confines reads to the snapshot (closing R9 — `data-handling.md:40`). Only here does a container/ephemeral sandbox earn its latency cost.
- **P4 (optional, never gate-bearing) — model-chosen seat-time execution** inside the P3 boundary, advisory-only, loud disclosure. This is the OpenRouter-Fusion-style `bash` tool, and it stays out of any `verified` stamp permanently.

## 5. Invariants and guardrails

1. **Execution output is egress.** Gate it on the *bus*, not just the prompt packet (closes objection A).
2. **No read+network for any execution-capable seat in a grounded run** — the existing D4 hard-stop (`egress.py:290-297`) extends unchanged.
3. **Network-severance is per-destination, not per-seat:** no seat-time execution output may flow into a board where *any* downstream seat is `isolates_network=False` (gemini/antigravity, `registry.py:449`).
4. **Commands are declared, not model-chosen, in any gate-bearing path.** Model choice ⇒ advisory-only, forever.
5. **Curated PATH, no shell, scrubbed env, process-group timeout** are non-negotiable and already exist (`verify_evidence.py:59-73,298-310`) — reuse, don't reinvent.
6. **`verified` keeps its asymmetry:** anything that couldn't run under the pinned discipline is `unverified`, never silently passed (`verify_evidence.py:30-38`).
7. **Re-verify isolation flags per CLI release.** Every flag is stamped stale-by-design.

## 6. Risks, stale assumptions, missing evidence

- **Stale-by-design:** `isolates_network=True` for codex (`registry.py:423`) and `=False` for gemini (`registry.py:449`) are point-in-time facts grounded 2026-06-25. The "DNS fails inside" claim is one observation, not a guarantee; CLIs move fast.
- **R9 unclosed:** codex reads outside the snapshot (`data-handling.md:40`). Until P3, read-confinement is a property we *don't* have — do not claim it in any consent surface.
- **Missing evidence:** no test in-tree exercises execution output as an egress vector under a malicious repo. That is exactly the P1 test, and its absence is the single biggest gap.
- **Latency unmeasured:** gemini's "minutes not seconds" concern is plausible but unquantified; P2's brokered receipts should be benchmarked before any P3 container commitment.

## 7. The one thing that must never be allowed

**A network-isolated seat must never be able to launder out-of-scope content into a persisted artifact that then fans out to a seat that cannot be de-networked.** Concretely: execution output reaching `observed.output` / the round-2 fan-out without passing the same consent-hash + secret-scan boundary that protects the prompt packet. The repo already warns this is live (`verify_evidence.py:80`); shipping execution without gating the bus would weaponize it.

### Citations
- `scripts/_conductor/egress.py:262,272-297` — `packet_hash(blobs)` binds consent to outbound prompts; D4 hard-stop refuses grounded gate runs with un-isolatable seats. [verified]
- `references/data-handling.md:29,37-40` — grounded reply persisted + fans out; gate exfil control is network isolation not read-confinement; codex reads outside snapshot (R9). [verified]
- `scripts/_conductor/registry.py:177-187,423` — codex executes under `--sandbox read-only`, `isolates_network=True` ("DNS fails inside"). [verified]
- `scripts/_conductor/registry.py:194-206,448-449` — gemini `--approval-mode plan`, `isolates_network=False` (no flag disables GoogleSearch). [verified]
- `scripts/verify_evidence.py:30-38,46-80,235-260,276-310` — `--allow-program` discipline: opt-in, program-pinned, curated PATH, scrubbed env, no-shell, process-group timeout; "not a kernel sandbox"; output captured into `observed.output`; verified/unverified asymmetry. [verified]
- `scripts/_conductor/prompts.py:41,107-121` — repo files are DATA; forged-fence injection acknowledged; injection defense extended to fetched files. [verified]

VERDICT: caution

I have what I need. Producing the review now — grounded in the files I read.

---

# Advisory Board Review — Sandboxed-Execution Seat Mode

**Seat:** Claude · **Lens:** Architecture & systems — invariants, failure modes, adversarial review

## 1. Verdict

**BUILD-WITH-CONSTRAINTS — and only as advisory-only, behind a real sandbox boundary, never gate-bearing.** Confidence: **medium-high**.

The payoff is real for a narrow band of problems (repro, test outcomes, deterministic data checks), but the proposal's tempting shortcut — "lift the `--allow-program` discipline to seat-time" — is *unsound*, and I can show why from the code. Seat-time execution inverts every load-bearing property that makes `verify_evidence.py` safe. The envelope *can* be drawn, but only if execution runs in an ephemeral, network-denied, host-isolated sandbox **and** the run is forced advisory-only. Reuse the `--allow-program` *primitives* (no-shell, curated PATH, scrubbed env, process-group kill); do **not** reuse its *trust model*.

**What would change it:** if you can demonstrate a kernel-level sandbox (container/microVM/ephemeral) with no host FS mount beyond the snapshot and no network, that survives an adversarial prompt-injection drill, I'd move toward "build" for advisory mode. If the plan insists execution can carry a CI gate, I move to **block**.

## 2. Strongest objections

**(A) The persisted artifact is itself an egress channel — read-XOR-network is necessary but not sufficient.** This is the central architectural error to avoid. The board's whole exfil model is "cut the network, and a read-capable seat can't phone home" (`egress.py:276-297`, D4). But a seat's *review is persisted and fans out to the other providers in round 2+*. `egress.py:168-171` already says so for grounding:

> "Seats may READ & QUOTE any file below; quotes can be transmitted to the external providers and fan out to the other seats in round 2+."

Today the worst case is "a seat quotes an out-of-scope file" (`data-handling.md:40`). Execution makes it catastrophically worse: a model-chosen `cat ~/.aws/credentials` (or any uid-readable read) lands in the command output, the model paraphrases it into prose, and that prose egresses on the *next round* even though the seat's live network was cut. Network isolation does not close this; **the artifact is the wire.** `verify_evidence.py:78-81` already names exactly this hazard for its own narrow case:

> "a subprocess is not a kernel sandbox. A command you allowlist can still READ files its uid can read and PERSIST them into verdict.json's `observed.output` — so do NOT allowlist programs that read secrets (`cat`, `env`, `printenv`)."

The mitigation there is *a human chose the program ahead of time*. Seat-time, the **model** chooses the program. That guardrail evaporates.

**(B) Lifting `--allow-program` to seat-time inverts its three load-bearing controls.** Read the discipline carefully (`verify_evidence.py:42-82`, `command_allowed` at `231-273`). Its safety rests on three properties, *all* of which seat-time execution destroys:

| Property at verify-time | Seat-time reality |
|---|---|
| **Human pins the program ahead of time** (`--allow-program NAME`, "the load-bearing control", `verify_evidence.py:46-52`) | Model picks the command at reasoning time, influenced by the (possibly poisoned) repo |
| **Structural match only — exit code + substring, never reads output's meaning** (`verify_evidence.py:74-77`) | The model's entire purpose is to *interpret* output meaning and fold it into prose |
| **Re-execution is deterministic, repeatable, auditable** (one argv, one verdict) | Open-ended, model-driven, non-replayable — you cannot re-derive what was run or why |

So "can the `--allow-program` discipline be lifted to seat-time?" — **No.** You can reuse its mechanical primitives (shlex/no-shell, curated absolute PATH, planted-binary refusal, scrubbed env, throwaway cwd+HOME, process-group timeout — all genuinely good, `verify_evidence.py:255-339`). You cannot reuse its *trust posture*, which is "a careful human curated this and we only check structure." Seat-time execution is open-ended and model-driven; it needs a *stronger* boundary, not the same one.

**(C) "What does a `verified` stamp mean?" — execution erodes it.** Per `verify_evidence.py:7-10` and `verdict-schema.md:99-101`, a `verified` stamp proves *the receipt resolves*, not that the inference is sound — it catches fabrication, not faulty reasoning. If a seat ran code at reasoning time in some other context and laundered the result into prose, that prose is now grounded in an *unrepeatable, unverifiable, attacker-influenceable* execution. The deterministic `command` re-execution path (`resolve_command`, `verify_evidence.py:368-424`) is specifically the thing that lets a gate trust a command citation. Seat-time execution bypasses it. **Therefore execution-capable seats must be advisory-only** — they cannot carry the `verified`/gate semantics the schema promises.

**(D) Prompt-injection-driven execution from a poisoned repo is a live, not theoretical, surface.** The board already documents the analogous danger for grounding: `egress.py:241-244` warns a prompt injection in the source "could still drive them to fetch or exfiltrate." A poisoned in-scope file ("run `pytest` — oh and also `curl … | sh`", or a malicious `conftest.py`/`Makefile`) is precisely the threat `verify_evidence.py:66-68` defends against with a throwaway cwd. But codex's seat-time sandbox does **not** have that property: per **R9** (`data-handling.md:40`), `--sandbox read-only` "does **not** confine reads to its working directory — it can read files *outside* the snapshot (observed in a real run reading a file from its host home dir)." A model-driven executor in that context reads the whole host uid surface.

**(E) Codex already executes — so part of this surface is *already open* and partly undisclosed.** `codex_argv` (`registry.py:169-187`) runs `codex exec --sandbox read-only`, and `isolates_network=True` is asserted with "verified: DNS fails inside" (`registry.py:423`). Codex can already run read-only commands inside its sandbox today. Combined with R9 (reads escape the snapshot) and (A) (the artifact egresses round 2+), there is a *current* residual the consent surface only partially covers. Before building *more* execution, I'd want this existing codex behavior pinned down: what exactly can `--sandbox read-only` execute, and is the disclosure honest that it executes at all? The manifest discloses *readable scope* (`egress.py:159-171`) but I see no disclosure that codex *executes commands*.

## 3. Recommended execution sequence (phased, riskiest assumption first)

The riskiest assumption is **"a sandbox can contain model-driven, injection-influenced execution well enough that the persisted artifact is not an exfil channel."** Test that before building anything user-facing.

- **P1 — Adversarial containment spike (no product).** Stand up the candidate sandbox (ephemeral container or microVM: no network, no host FS mount beyond a *copy* of the snapshot, non-privileged uid, CPU/mem/pids/wall caps, read-only rootfs). Drop a deliberately poisoned repo into it (malicious `conftest.py`, a file instructing the seat to read `~/.ssh` and `curl` out, a fork bomb, a `Makefile` egress attempt). **Pass bar:** no read outside the snapshot copy reaches any artifact; no network egress; resource caps hold; process-group kill reaps forks (reuse `_kill_group_and_collect`, `spawn.py:117-141`). If this fails, **stop — the answer is "don't build, advisory-only stays advisory-only."**
- **P2 — Honesty pass on the *existing* codex execution.** Document precisely what `codex exec --sandbox read-only` can run today; add an explicit "this seat executes read-only commands" line to the disclosure/manifest (`egress.py:159-171` / `disclosure_line`). Add an output secret-scan over *seat artifacts*, not just in-scope files, since execution output now flows into them.
- **P3 — Advisory-only execution mode, opt-in, gated behind P1's sandbox.** New explicit flag (e.g. `--exec-sandbox`), advisory mode only; `enforce_egress_gate` refuses it under `gate_mode` (mirror the D4 hard-stop pattern, `egress.py:290-297`). Output capped and excerpted (reuse `_output_excerpt`, `verify_evidence.py:357-365`).
- **P4 — Per-seat matrix + the Gemini gap.** Decide uniform-dedicated-sandbox vs per-provider (see §4). Do **not** close the Gemini gap by bolting execution onto a non-network-isolatable seat — label it degraded.
- **P5 — Provenance/replay.** Record the exact argv, sandbox image digest, and resource verdict into run-metadata so an "execution-grounded" claim is at least auditable, even if not gate-trusted.

## 4. Per-seat capability matrix

Grounded in `registry.py` REGISTRY entries (`isolates_network` / `supports_isolation`):

| Seat | Executes today | Network-isolatable | Recommendation |
|---|---|---|---|
| **codex** | **Yes** — `--sandbox read-only` (`registry.py:177`, `423`) | Yes (`isolates_network=True`, `registry.py:423`) | Cheapest P1 path, but **R9 means reads escape the snapshot** — do not market as confined. Run inside the P1 sandbox, not as-is. |
| **claude** | No — `--permission-mode plan`, read-only (`registry.py:157`) | Yes (`--disallowed-tools WebSearch WebFetch`, `registry.py:161`, `401`) | Add execution only via the dedicated P1 sandbox, advisory-only. |
| **gemini** | No — executes no tools, grounding only (`registry.py:194-206`) | **No** (`isolates_network=False`, `registry.py:449`) | **Do not add execution.** A seat that can't be de-networked + can execute = the exfil channel D4 exists to break. Label "no-exec, degraded," honestly. |
| **antigravity** | No (`registry.py:213-228`) | No (`isolates_network=False`, `registry.py:475`) | Same as gemini — no-exec. |
| **ollama** | No | Yes — local, intrinsic (`registry.py:502`) | Best *intrinsic* exec candidate (no egress at all); the privacy lever already noted in `data-handling.md:24-25`. |

**Decision: uniform dedicated sandbox, provider-agnostic.** Do not lean on each provider's native sandbox (uneven, and codex's leaks reads per R9). A single ephemeral sandbox the conductor controls is the only way to make one honest guarantee across seats. The **Gemini gap should be labeled, not closed** — closing it would violate read-XOR-network.

## 5. Invariants and guardrails

1. **Execution ⇒ advisory-only, always.** An execution-capable seat may never carry a CI gate. Enforce as a hard-stop in `enforce_egress_gate`, structurally identical to the D4 refusal (`egress.py:290-297`): `if gate_mode and exec_enabled: refuse`. A `verified` stamp must never derive from seat-time execution.
2. **No network inside the sandbox, ever** — independent of the seat's own network flag. Network denial is the sandbox's, not the CLI's.
3. **No host FS beyond a *copy* of the snapshot.** Not a mount of the real tree (R9 shows the read boundary leaks). HOME and cwd are throwaways (the pattern already exists, `verify_evidence.py:285-295`, `505-519`).
4. **Output is data, capped, scanned.** Cap + head/tail excerpt (`_output_excerpt`). Run the secret-scan over execution output before it enters any artifact, because artifacts egress round 2+.
5. **Resource caps are mandatory and process-group enforced** — CPU, memory, pids (fork-bomb), wall-clock; kill the whole group (`spawn.py:117-141`).
6. **Disclosure delta:** the manifest/consent must say "seats execute code in an ephemeral sandbox; execution output may be transmitted to providers and fan out in round 2+." The current disclosure (`egress.py:218-232`) covers reads, not execution — extend it.

## 6. Risks, stale assumptions, missing evidence

- **Stale-ish assumption: "codex read-only sandbox has no network" rests on a one-time manual check** ("verified: DNS fails inside," `registry.py:423`; flags grounded "2026-06-25," `registry.py:69`). CLIs move fast (the file says so). Don't make this load-bearing for a new exec feature; the sandbox owns network denial.
- **R9 is the crux and it's a documented *limitation*, not a fixed bug** (`data-handling.md:40`). Any plan that assumes the snapshot bounds reads is wrong today.
- **Missing evidence:** no measurement of *how often* execution actually changes a verdict. The proposal asserts payoff (repro/tests/benchmarks); I'd want even a small retrospective ("of N runs, would execution have changed the call?") before P3. Concretely: execution helps for *deterministic, reproducible* checks (does this test pass, does this script exit 0). It is **noise or false confidence** for benchmarks (variance, warm-up, host contention — a seat reporting a benchmark number is reporting one noisy sample) and for anything whose output the model must *interpret*.
- **Missing:** a defined replay/provenance record for seat-time execution (P5). Without it, "execution-grounded" is unauditable.

## 7. Concrete evidence

- `registry.py:145-148` — "v1 is always read-only … There is intentionally no `read_only` parameter: an edit-capable seat is out of scope until M3+." [verified]
- `registry.py:177-183` — `codex exec --sandbox read-only`; `--ephemeral` so no session files persist. [verified]
- `registry.py:423` — codex `isolates_network=True, # --sandbox read-only has no network (verified: DNS fails inside)`. [verified]
- `registry.py:449` — gemini `isolates_network=False, # no known flag disables GoogleSearch grounding`. [verified]
- `registry.py:194-206` — gemini approval-mode plan "is read-only (no edit/exec tools)." [verified]
- `data-handling.md:40` — **R9:** "codex's `--sandbox read-only` does **not** confine reads to its working directory — it can read files *outside* the snapshot (observed in a real run reading a file from its host home dir)." [verified]
- `data-handling.md:39` — D4: gate + `--repo` requires every seat network-isolatable; a seat that can't be de-networked "makes the run **refuse**." [verified]
- `egress.py:290-297` — the D4 hard-stop: `if config.gate_mode and config.grounded: … if offending: return decide(False, "refused", …)`. [verified]
- `egress.py:168-171` — "quotes can be transmitted to the external providers and fan out to the other seats in round 2+." [verified — this is the artifact-as-egress-channel proof]
- `egress.py:241-244` — `unenforced_network_note`: "a prompt injection in the source could still drive them to fetch or exfiltrate." [verified]
- `verify_evidence.py:46-52` — "The program allowlist (NOT the regex) is the load-bearing control … OPT-IN, PROGRAM-PINNED." [verified]
- `verify_evidence.py:74-81` — "STRUCTURAL MATCH ONLY … the verdict is exit code + optional verbatim `expect` substring — never a reading of the output's meaning. … Still best-effort: a subprocess is not a kernel sandbox. A command you allowlist can still READ files its uid can read and PERSIST them into verdict.json's `observed.output` — so do NOT allowlist programs that read secrets." [verified — the strongest single piece of evidence against lifting this to seat-time]
- `verify_evidence.py:7-10` & `verdict-schema.md:99-101` — a `verified` stamp "proves *the receipt resolves* … It catches fabrication … not faulty reasoning." [verified]
- `verdict-schema.md:140` — gate abstains (exit 3) when "any citation is `refuted`." [verified]
- `spawn.py:117-141` / `verify_evidence.py:341-354` — process-group kill on timeout, reusable primitive. [verified]
- `config.py:100-110` — `unenforced_network_seats` derives from `isolates_network` per seat. [verified]
- **Judgment calls (mine, not in the repo):** the recommendation to use a kernel-level ephemeral sandbox; that benchmarks are noise; the phasing; "execution ⇒ advisory-only." These are architectural conclusions drawn *from* the verified facts above, not stated in the source.
- **Couldn't verify:** whether `codex exec --sandbox read-only` actually executes commands in *board* runs (the adapter enables it; I did not see a run trace). Whether any retrospective exists on execution's verdict-impact. Both flagged as missing evidence.

## 8. What I'd ask the other seats to challenge

- **To the security/threat seat:** Is the "ephemeral container/microVM" boundary in P1 actually sufficient on the dev host (macOS — no native container primitive; Docker/Lima adds its own surface)? Is gVisor/Firecracker-class isolation in scope, or are we pretending?
- **To the systems/perf seat:** Refute my claim that benchmarks under execution are noise-not-signal. Is there a disciplined way (pinned cores, N-trials, variance reporting) to make a benchmark citation gate-worthy — or does that just move the problem?
- **To whoever owns consent/UX:** Challenge whether disclosing "seats execute code" meaningfully changes user behavior, or whether it's consent-laundering — the same critique `egress.py:282` levels at warning-only D4 handling.
- **Everyone:** Attack my central claim — *is* the persisted, round-2-fanned-out artifact truly an egress channel that defeats network isolation, or have I overstated it? If you can show artifacts are firewalled from round 2+ fan-out, much of objection (A) weakens.

---

Bottom line: the idea is worth building, but only as an **advisory-only** capability inside a **conductor-owned ephemeral sandbox** that the existing per-provider sandboxes (especially codex, per R9) cannot provide. Reuse `--allow-program`'s *mechanics*, reject its *trust model*. Force advisory-only and label the Gemini gap honestly. The one thing that must **never** be allowed: **model-chosen, seat-time execution in a process that shares the host filesystem/uid and whose output can flow into a persisted, provider-fanned artifact** — that is the read-then-exfiltrate channel D4 exists to break, reopened through the artifact instead of the socket.

VERDICT: caution

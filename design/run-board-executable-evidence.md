# Advisory Board — Executable Evidence Plan

> Let the board ground claims by **running declared commands** in a sandbox and handing seats **redacted receipts** — closing the read-and-reason gap vs OpenRouter Fusion's benchmark `bash` — **without** opening a model-chosen shell or a new ungated egress channel. Verdict from a 3-seat / 3-round dogfood board: **build-with-constraints**.

- **Updated:** 2026-06-26
- **Source:** the OpenRouter Fusion comparison (`design/competitive-fusion-comparison.md`) + the dogfood roundtable `design/roundtables/should-advisory-board-add-a-sandboxed-execution-seat-mode.md` — a **grounded, 3-seat (Claude·Codex·Gemini), 3-round** board, verdict **build-with-constraints / high / unanimous**
- **Owner:** Tim
- **Baseline:** advisory-board on `main` @ `c5a61ab` · 604 tests green · builds on **repo-grounding** (`--repo`, D4 read-XOR-network) and **`verify_evidence.py --allow-program`** (the existing no-shell, program-pinned, scrubbed-env re-execution discipline)
- **Status:** PROPOSED — design synthesized from the roundtable verdict; **not yet approved to build**. Like repo-grounding, this is an **execution/egress surface**: it gets the security-sensitive convention (two adversarial-review rounds + a security-review pass) before any merge.

## Overview

Today the board **reasons about** code; it cannot **run** it. For "does this actually reproduce / what does the test suite say / what does this benchmark return," a read-only seat is weaker than one that can execute — the capability gap the OpenRouter Fusion comparison surfaced (Fusion's benchmark gave panel models a `bash` tool). The question this plan answers: *should the board add a sandboxed-execution mode, and what is the safe envelope?*

The board's answer reframes the feature. **It is not "execution-grounded seats with bash."** Model-chosen shell access turns every prompt-injection in an in-scope file into code execution and shreds the `verified` stamp. The board's design is a **declared-command broker**: the user/config declares the exact program + argument pattern; the **conductor** (never a seat) runs it under the existing pinned discipline; each seat receives a **redacted receipt** (exit code + scanned output) as **DATA**. No seat chooses the command, so a poisoned file cannot pick one.

Three findings shape the whole design (all grounded against the current code in the roundtable):

1. **The load-bearing crux — execution output is an ungated egress channel.** The consent gate hashes the **outbound prompt packet at pre-spawn**; it does **not** cover command output produced **after** spawn. But that output is persisted into round artifacts and **fans out to the other providers in round 2+** — including seats that cannot be de-networked (gemini/antigravity). D4 (read-XOR-network) severs the *network* channel; the **artifact bus is a separate, ungated channel.** So Phase 1 must prove a D4-structured hard-stop: execution output reaches the bus **only if** its content is folded into the consent hash or passes an output secret-scan. *If that invariant can't hold, the feature stops there.*
2. **The structural safety answer is brokering, not sandboxing alone.** "Deny network + scrub env" protects the host, but only **declared, non-model-chosen commands** prevent a poisoned in-scope file from choosing what runs. Model-chosen seat-time execution must **never** ship in a gate-bearing path.
3. **The `verified` stamp must not degrade.** `verify_evidence.py` already draws the line correctly: a `command` citation is `verified` only when allowlisted **and** the pinned re-run matches the expected exit/`expect`, else `unverified`, never silently passed. An execution-capable mode must inherit that asymmetry exactly, or `verified` decays from "true under a reproducible discipline" into "this machine ran something."

This plan is the **source of truth**; the HTML view is rendered from it (`render_plan.py`) so the two never drift.

## Milestone: Executable evidence via a declared-command broker
status: planned

An opt-in mode where the **conductor** runs **declared** commands in a hardened sandbox and hands every seat a **redacted receipt** as data, so seats can ground claims in real execution. Built in risk-first order: prove the egress-bus invariant before anything else, then the deterministic broker (which may be gate-bearing), then real OS-level isolation, and only last — if ever — any model-chosen execution (advisory-only, never `verified`).

### Phase 1 — Prove the egress-bus invariant (the gate; if it can't hold, stop)
status: planned

The board's first and load-bearing objection: command output is a cross-provider egress channel the consent gate does not cover. Before building any execution, prove that execution output cannot reach the artifact bus unless it is consented-to or scrubbed. This phase is a **spike + invariant**, not a feature — it decides whether the rest of the plan is viable.
- [ ] DECISION: execution output (stdout/stderr captured post-spawn) is **egress** and must obey the §8 invariant — *consent binds to the bytes that leave.* It is not covered today (the hash is pre-spawn; output is post-spawn). *(Alt rejected: treat output as "internal" — it is persisted to `observed.output` and fans out in round 2+, so it leaves.)*
- [ ] Build a **D4-structured hard-stop**: receipt content reaches the cross-reading packet / round artifacts **only if** (a) its bytes are folded into the consent hash, **or** (b) it passes an **output secret-scan** (reuse `grounding.scan_secrets`), else it is dropped/redacted and the drop is recorded — never silently forwarded.
- [ ] **Adversarial fixture:** a malicious in-scope file whose declared command writes a planted secret to stdout; assert the secret **never** reaches an external seat (and never an un-de-networkable seat) — the planted-secret test is the acceptance gate for the whole milestone.
- [ ] Decide the seam: does the receipt egress-check live in `egress.py` (packet assembly) or `rounds.py` (round-2 fan-out, where bodies already get content-stripped per D8)? Wire it where repo-grounding already strips verbatim in-scope bodies.
- [ ] **Stop-gate:** if the invariant cannot be made to hold structurally (only "best-effort filtering"), record the result and **halt the milestone** — do not proceed to P2. (Gemini dissent, preserved: bus-level output filtering adds latency/false-positives; if so, the answer is a *static brokered-receipt* model where there is nothing to filter — which P2 provides — not a heavier filter.)
Testing: planted-secret-to-stdout fixture never egresses; receipt with in-hash content passes; receipt failing the secret-scan is dropped + recorded; a round-2 packet built from a receipt elides non-consented bytes.
Gate: `python3 -m unittest discover -s tests -t tests`

### Phase 2 — Deterministic declared-command brokered receipts (may be gate-bearing)
status: planned

The actual capability, in its safe form. The user/config **declares** the exact program + argument pattern; the **conductor** runs it once via the existing pinned discipline and hands all seats the same **redacted receipt** as DATA. Because no seat chooses the command, a poisoned in-scope file cannot turn prose into a chosen execution — so this tier **may be gate-bearing**.
- [ ] DECISION: commands are **declared, not model-chosen**, in any gate-bearing path (closes the prompt-injection-to-execution channel — board blocker #2). A seat may *request* a command in advisory mode; an undeclared request becomes an **advisory note, not an executed shell**.
- [ ] DECISION: reuse `verify_evidence.py`'s execution discipline verbatim — **no shell, program-pinned `argv[0]`, curated PATH, scrubbed env, isolated cwd/HOME, process-group timeout, planted-binary resolution guard.** Lift it from verify-time to a shared broker callable at seat-time. *(Don't reinvent; the board explicitly said reuse.)*
- [ ] The **receipt** schema: `{program, arg-pattern, exit_code, expect-match, redacted_output, duration}` — handed to seats inside the source/packet as clearly-delimited DATA (same "material under review, not instructions" framing as repo files).
- [ ] DECISION: the broker runs **once** per declared command and shares the receipt across seats (not per-seat execution) — deterministic, one egress event, and sidesteps the codex-can / gemini-can't asymmetry (Codex dissent, adopted: a uniform broker beats provider-native execution).
- [ ] `verified` integrity: a brokered receipt feeds the **existing** `command`-citation path — `verified` only on allowlist + exit/`expect` match, else `unverified` (board blocker #4). No new stamp semantics.
- [ ] Gate-mode policy: brokered receipts are permitted on a gate-bearing run **only** with P1's egress hard-stop active and every seat network-isolatable (the existing D4 rule); name any un-isolatable seat as a labeled NO-GO, never silently drop.
Testing: a declared `pytest -q` / `go test` receipt flows to all seats identically; an **undeclared** command request is refused → advisory note (never executed); a receipt drives a `verified`/`unverified` stamp correctly; gate-mode refuses when a seat can't be de-networked.
Gate: `python3 -m unittest discover -s tests -t tests`

### Phase 3 — Real resource caps + read confinement (close R9)
status: planned

Only now does a heavier sandbox earn its latency. Add real OS-level isolation: CPU/memory/pid/wall caps and a filesystem boundary that **actually confines reads** to the snapshot — closing R9 (codex's `--sandbox read-only` reads outside its cwd, observed reading a host home-dir file). Until this exists, the broker must not claim snapshot-only reads.
- [ ] Evaluate a namespace-based sandbox (`sandbox-exec` / `unshare` / a minimal container) for **sub-second** spin-up while enforcing read-confinement + network-severance; if open-ended execution can't meet interactive latency, it moves off the interactive loop. (Board open question — answer empirically against fixtures.)
- [ ] Enforce **read confinement** to the snapshot (close R9) — verify against a malicious-repo fixture that tries to read host dotfiles/secrets and assert it cannot.
- [ ] Real **resource caps**: CPU, memory, pid count, wall-clock — verify against fork-bomb / memory-balloon / spin fixtures.
- [ ] Re-verify the isolation flags per CLI release (the `isolates_network` stamps are **stale-by-design**, grounded point-in-time 2026-06-25); add a check that flags drift.
- [ ] DECISION (record): do **not** trust codex's existing `--sandbox read-only` as the isolation boundary (Claude dissent, preserved) — it is a foundation to reuse, not a boundary to rely on; the P3 sandbox is the boundary.
Testing: malicious-repo read-confinement fixture (host-secret read fails); CPU/mem/pid/wall caps each enforced against an abuse fixture; latency measured + recorded.
Gate: `python3 -m unittest discover -s tests -t tests`

### Phase 4 — Model-chosen seat-time execution (advisory-only, never `verified`, if ever)
status: planned

The most powerful and most dangerous tier — and the board's clear "only if ever, and heavily fenced." A seat proposes and runs its own commands inside the P3 boundary. It is **advisory-only**, loudly disclosed, and **permanently excluded** from any `verified` stamp.
- [ ] DECISION: model-chosen execution is **never gate-bearing** and its output is **never** `verified` (board blocker #2 + #4). A rejected/undeclared model command becomes an advisory note, not executed shell.
- [ ] Requires the full P3 boundary (read confinement + caps + network severance) — no model-chosen execution without it.
- [ ] Loud disclosure in the run-card + handoff: "this run let a seat choose and run commands inside a sandbox; treat its execution-derived claims as advisory, unverifiable."
- [ ] Re-evaluate whether this tier is worth building at all once P2 (declared receipts) is in use — declared brokering may cover the real value without the risk. (Defer the build decision to data from P2 usage.)
Testing: model-chosen execution refuses to run in gate mode; its output can never reach a `verified` stamp; disclosure present; runs only inside the P3 boundary.
Gate: `python3 -m unittest discover -s tests -t tests`

## Decisions

- **D1** Executable evidence is a **declared-command broker**, not seat bash — the conductor runs declared commands and hands seats redacted receipts as DATA; no seat chooses a command in any gate-bearing path. *(Board verdict: build-with-constraints; blockers #2, the structural answer.)*
- **D2** Execution output is **egress** — it must be folded into the consent hash or pass an output secret-scan before reaching the artifact bus; the bus is a channel D4 doesn't cover. P1 proves this or the milestone halts. *(Board blocker #1, load-bearing.)*
- **D3** **Reuse `verify_evidence.py`'s discipline** (no-shell, program-pinned, curated PATH, scrubbed env, isolated cwd/HOME, process-group timeout, planted-binary guard) rather than reinventing — lift it to a shared seat-time broker. *(Board: explicit reuse.)*
- **D4** `verified` keeps its **asymmetry** — verified only on allowlist + pinned exit/`expect` match, else unverified; an execution-capable mode inherits it unchanged. *(Board blocker #4.)*
- **D5** One **uniform broker**, run once per declared command, shared across seats — not provider-native execution (codex-can / gemini-can't asymmetry). *(Codex dissent, adopted.)*
- **D6** Do **not** treat codex `--sandbox read-only` as the isolation boundary; the P3 OS-level sandbox is the boundary. *(Claude dissent, preserved.)*
- **D7** Bus-level output filtering is a fallback, not the primary control; the **static brokered-receipt** model (P2) is preferred so there is little to filter. *(Gemini dissent, reconciled.)*

## Risks

- **R1** Egress-bus leak — a network-isolated seat writes out-of-scope content (a planted secret, a host file) into `observed.output`, which fans out to an un-de-networkable seat. *Mitigation: P1's hard-stop + planted-secret fixture; halt if it can't hold.*
- **R2** Prompt-injection-to-execution — a poisoned in-scope file drives a seat to run code. *Mitigation: declared (not model-chosen) commands in any gate-bearing path (D1).*
- **R3** R9 read leak — until real read confinement (P3), a seat could read host dotfiles/secrets and print them to stdout. *Mitigation: P3 read confinement; until then the broker must not claim snapshot-only reads.*
- **R4** `verified` theater — execution makes `verified` mean "ran something." *Mitigation: D4 asymmetry, enforced; model-chosen output never `verified`.*
- **R5** Latency — a real sandbox may blow the interactive budget ("minutes not seconds," unquantified). *Mitigation: P3 measures it; open-ended execution moves off the interactive loop if needed.*
- **R6** Stale isolation flags — `isolates_network` is grounded point-in-time and drifts per CLI release. *Mitigation: per-release re-verification check (P3).*
- **R7** Missing safety tests — the roundtable found **no** test exercising execution-output-as-egress under a malicious repo. *Mitigation: the malicious-repo fixtures are acceptance gates in P1/P3, not afterthoughts.*

## Dependency order

P1 (prove the egress-bus invariant) **gates everything** — if it can't hold, stop. P2 (declared brokered receipts) is the shippable capability and depends on P1. P3 (real caps + read confinement) hardens P2 and is required before P4. P4 (model-chosen execution) is last, optional, advisory-only, and may never be built if P2 covers the value.

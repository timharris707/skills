I have enough verified grounding. Producing the review directly, as the task requires (no plan file; the round-2 instructions explicitly override the plan-mode scaffold and forbid writing files).

---

# Round 2 — Claude seat (Architecture & systems)

## 1. Updated verdict

**BUILD-WITH-CONSTRAINTS — and only as a *brokered, declared-command* feature; model-chosen seat-time execution stays advisory-only, never gate-bearing, behind a boundary that also contains the *artifact bus*, not just the network.** Confidence: **medium-high**.

What would change it: a working demonstration that execution output entering the round-2+ packet can be hard-bound to the same network-isolation invariant the D4 quarantine already enforces — i.e. that we can gate the *output bus*, not just the *prompt packet*. If that hard-stop can't be drawn as cleanly as the existing D4 refusal, drop to "don't build the model-driven variant."

The framing shift from round 1: this is not a greenfield "should seats execute" question. **One seat already executes** — `codex exec --sandbox read-only` (`registry.py:177` [verified]). So "don't build" is not an honest option; we already have an un-standardized, provider-trusted execution surface. The real decision is *standardize-and-bound* vs *leave it as a per-provider accident*. That asymmetry pushes me off "advisory-only sandbox" and toward codex's **broker** model.

## 2. Where I changed my mind / where I still dissent

**Changed — toward codex (high agreement).** Codex's "brokered execution-receipt, not let-each-CLI-run-arbitrary-commands" is architecturally stronger than my round-1 "advisory-only sandbox." The reason is precise and grounded: the safety of the existing re-execution path rests entirely on the command being **human-declared and the program pinned**, with the regex able only to *narrow* — `command_allowed` pins `argv[0]` to `--allow-program` *before* any pattern runs (`verify_evidence.py:258-272` [verified]: "argv[0] is pinned to an explicit program allowlist FIRST so the regex … can never choose the executable"). A broker preserves that property at seat-time (seat *proposes* a typed `command`; conductor *disposes* via the pinned allowlist). Model-direct execution destroys it. I'm adopting the broker as P2.

**Changed — on the cross-provider egress bus being the crux, not a side note.** My round-1 objection (A) was right but I under-weighted that the existing code already fans prior-round stdout forward: `build_round2 → build_round2_packet(..., repo_lines=...)` carries each usable seat's output into the next packet (`egress.py:46-58` [verified]), and the manifest itself states quotes "fan out to the other seats in round 2+" (`egress.py:168-170` [verified]). Execution output would ride that same bus. So read-XOR-network being *per-seat* is the architectural defect: a sandboxed-but-isolated seat's command output can still reach gemini, whose `isolates_network=False` (`registry.py:449` [verified]) — a networked relay.

**Still dissent — from gemini.** Gemini's P1 ("Standardized Local Container Driver … Docker or gVisor … reject per-provider native execution") fixes *containment* but not the *egress invariant*, and it puts the wrong thing first. A `--network none` container stops the executing seat from dialing out, but it does nothing about that seat's stdout being fanned to a non-isolated seat on the bus. And on this host the assumption is shakier than gemini admits: the platform is `darwin` (macOS) with no native container primitive — Docker/Lima/gVisor each add a VM and their own surface, and the `--network none` guarantee then rides on that VM's correctness. Containment is necessary for the *model-driven* variant (my P3), but it is **not** the first risk to retire. The egress-bus hard-stop is.

**Still dissent — from any reading that "codex already executes, so seat-time exec is low-marginal-risk."** R9 says we do *not* fully trust codex's sandbox: `--sandbox read-only` "does **not** confine reads to its working directory — it can read files *outside* the snapshot" (`data-handling.md:40` [verified]). Leaning harder on that same provider sandbox for *more* capability is exactly the move data-handling.md warns against.

## 3. Strongest remaining objections (architecture)

**(A) The persisted artifact is a cross-provider egress bus, and the gate only covers the prompt packet.** `enforce_egress_gate` hashes and binds consent to `blobs` — the outbound *prompts* — at pre-spawn (`egress.py:262, packet_hash` over blobs, `egress.py:109-118` [verified]). Nothing gates a seat's *output* before that output becomes the next round's input to networked seats. Execution stdout would join the bus ungated. **This is the invariant to add before anything else.**

**(B) Model-driven command choice under injection inverts the trust model.** The whole `--allow-program` discipline assumes a human named the program. Seat-time, a poisoned in-scope file — readable because R9 means reads aren't snapshot-confined — picks the command. The structural defenses (`run_command` refuses a binary resolving inside cwd, `verify_evidence.py:316-320`; curated absolute-only PATH, `:276-282` [verified]) protect *executable identity*, not the *decision to run* nor a legitimately-dangerous program over readable files.

**(C) No resource caps exist anywhere today.** Both execution paths are timeout-only: `spawn` does process-group SIGTERM→SIGKILL on timeout (`spawn.py:112-141` [verified]); `run_command` does process-group-kill on timeout (`verify_evidence.py:333-339` [verified]). There is **no** rlimit, no memory/pids/CPU cap, no cgroup anywhere in the tree. Output size is the only bounded resource (`RERUN_OUTPUT_LIMIT = 4000`, `verify_evidence.py:112` [verified]). Any execution-bearing mode is a trivial fork-bomb/OOM DoS until caps exist.

**(D) `verified` would lose its meaning.** Today a green stamp means "the receipt *resolves*" — structural match only, exit code + verbatim `expect` substring, explicitly "never a reading of the output's meaning" (`verify_evidence.py:10-11, 74-81` [verified]). A model-chosen seat-time run conflates "receipt resolves" with "the model's live, injection-reachable run said so." That must never earn a gate.

## 4. Recommended execution sequence

- **P1 — retire the riskiest assumption first: prove the egress-bus invariant, not the sandbox.** Add a hard-stop structurally identical to D4 (`egress.py:290-297` [verified]): execution output may enter the artifact bus only if the producing seat *and every downstream seat it fans to* are network-isolatable; otherwise refuse the whole run with a labeled NO-GO. Test: a board of `{exec-seat, gemini}` in gate mode must **refuse**. If we can't draw this line as cleanly as the existing `unenforced_network_seats` check (`config.py:101-110` [verified]), stop here.
- **P2 — generalize `--allow-program` to seat-time as a broker.** Seat proposes typed `command` citations; the conductor runs only declared, allowlisted, bare-program commands under the *existing* discipline (no shell, scrubbed env, throwaway cwd+HOME, planted-binary refusal). Model never executes directly. Cheapest reuse of proven code.
- **P3 — only if open-ended model-driven exec is genuinely needed:** add a real boundary (ephemeral microVM / gVisor) **plus** resource caps (rlimit/cgroup) — advisory-only, never gate-bearing.
- **P4 — close or honestly label the matrix.** Do not fake gemini execution; mark it degraded as the code already does honestly elsewhere.

## 5. Invariants and guardrails

1. **Execution output is egress.** Gate it on the *bus*, not just the prompt packet (new; closes objection A).
2. **Network-severance is per-destination, not per-seat.** No seat-time execution if any seat the artifact reaches isn't network-isolatable (generalize D4 / `unenforced_network_seats`).
3. **Model proposes, allowlist disposes.** Never lift the program allowlist into a model-chosen command. The bare-name pin (`command_allowed`) is load-bearing and must stay human-set.
4. **Execution ⇒ advisory for the gate.** A model-driven run never yields `verified`; only deterministic re-execution of a declared citation does.
5. **Hard resource caps mandatory** (mem/pids/CPU/wallclock) before any new exec path — none exist today.

## 6. Risks, stale assumptions, missing evidence

- **Stale-by-design:** every isolation flag was "grounded against the installed CLIs' --help on 2026-06-25 … re-verify before a large run, they move fast" (`registry.py:68-69` [verified]). The codex "DNS fails inside" claim is a one-time manual check (`registry.py:423` [verified]). Today is 2026-06-26 — one day on, still fresh, but the load-bearing `isolates_network=True` for codex rests on that single observation.
- **Missing evidence:** no CPU/memory caps in the codebase (searched; only timeout/process-group handling found in `spawn.py` and `verify_evidence.py`). Confirms objection C is real, not hypothetical.
- **Couldn't verify:** the provider-CLI sandbox claims themselves (codex read-only network behavior, gemini grounding non-removability) are asserted in comments, not independently testable from the tree.
- **R9 residual:** reads are not snapshot-confined (`data-handling.md:40` [verified]); the broker's throwaway-cwd discipline (`verify_evidence.py:64-68` [verified]) mitigates *cwd-based* attacker files but not a command that reads `$HOME`-adjacent or absolute paths its uid can reach — hence "allowlist only programs you trust to be read-only over public material" (`verify_evidence.py:79-81` [verified]) stays a human judgment, not a guarantee.

## 7. The one thing that must never be allowed

**A model-chosen, seat-time execution must never produce output that (a) carries a `verified`/CI gate or (b) crosses to any seat that is not network-isolated.** Execution may inform an advisory opinion; it may never become a gate stamp, and its output may never reach a networked relay. Both halves reduce to: seat-time execution output is subject to the *same* read-XOR-network quarantine the D4 hard-stop already enforces for reads — applied to the *output bus*, which today it is not.

## 8. Concrete evidence

- `registry.py:177` — `codex exec --sandbox read-only` — codex already executes [verified].
- `registry.py:449`, `config.py:101-110` — `gemini isolates_network=False`; `unenforced_network_seats` is the existing per-seat network-isolation check [verified].
- `egress.py:290-297` — the D4 unconditional hard-stop (`if config.gate_mode and config.grounded … return decide(False, "refused", _d4_refusal_detail(offending))`) — the structural template P1 reuses [verified].
- `egress.py:46-58, 168-170` — prior-round output fans into round-2+ packets and to other providers (the egress bus) [verified].
- `egress.py:109-118, 262` — consent binds to the *prompt packet* hash, not seat output [verified].
- `verify_evidence.py:255-273, 276-282, 316-320` — `command_allowed` bare-name pin + curated PATH + planted-binary refusal (the broker discipline to reuse) [verified].
- `verify_evidence.py:10-11, 74-81` — `verified` = structural match only, "never a reading of the output's meaning" [verified].
- `spawn.py:112-141`, `verify_evidence.py:112, 333-339` — timeout/process-group kill and 4000-char output cap are the *only* resource bounds; no mem/CPU/pids caps [verified].
- `data-handling.md:37-40` — exfil control is network-isolation, not read-confinement; R9 (codex reads outside the snapshot) [verified].

VERDICT: caution

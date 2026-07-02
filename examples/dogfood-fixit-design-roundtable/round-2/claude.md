Confirmed the linchpin: `rounds.py:232-234` fans seats out concurrently via `ThreadPoolExecutor(max_workers=len(seats))`. The endorsement pass is a dependency-free per-seat fan-out — structurally a review round — so it reuses that machinery and costs ~one extra round of wall-clock, not N sequential spawns. That directly rebuts Gemini's latency objection. I have what I need.

A note on process: this is an advisory-board review task, and the conductor parses the `VERDICT:` token on my last line. I'm therefore returning the review as my reply rather than writing a plan file or calling ExitPlanMode — the task explicitly says "Do not write any files and do not return a plan-mode summary," and doing so would break the pipeline. All my actions this turn were read-only.

---

# Claude seat — Round 2 review

**Role: architecture & systems — invariants, failure modes, adversarial review.** Every factual claim below is re-verified against `main`-lineage code in this worktree; citations are exact.

## 1. Updated verdict

**CAUTION — proceed only with the changes below. Confidence: HIGH.**

The architecture is sound and the reuse-the-synthesizer-substrate instinct is correct. But three strawmen are *wrong as specified* (not merely under-refined), and each is backed by code, not taste: Q1 title-only identity, Q8's header inside the clean draft, and the `caveats` container that does not exist. Two more (Q5 truncation, Q6 latency) are right in intent but ship a defect without a named mechanism.

**What flips this to SHIP:** (1) Q1 → composite `{list, index, title}` locator, conductor-validated; (2) Q8 → `revised-draft.*` is byte-clean, zero metadata header; (3) Q3 → fix `caveats`→`dissent` before any schema is written; (4) Q6 → dispatch endorsement concurrently (keep it ON by default); (5) Q5 → add a source-size preflight so oversized sources refuse rather than truncate. All five are specification tightenings; none touch the architecture.

**Q-by-Q ledger (for D9+):** Q1 **CAUTION** (composite locator, not title-only) · Q2 **SHIP-b** with non-circular pin + amend's write-guard (moved) · Q3 **SHIP** with 3 tightenings · Q4 **SHIP-c** · Q5 **SHIP-a** with truncation-defense trio · Q6 **SHIP-i** (ON) but *must parallelize* — dissent from Gemini's OFF · Q7 **SHIP-c** · Q8 **SHIP** with byte-clean-draft correction + verdict-required.

## 2. Where I changed my mind / where I still dissent

**Changed — Q2, toward codex.** In round 1 I insisted on (a) file-only, resting on verdict.json's "write-once" purity. That objection is weaker than I framed it: **`amend` already reopens and rewrites `verdict.json` post-synthesis** (`board_verdict.py:535-537`, "Append ONE human amendment to a run's verdict.json"). Write-once is already gone as of v1.12. So a conductor-authored `changes` pointer is not a new category of mutation — it's the same append-style write. I adopt codex's (b) **conditioned on** its own guardrail (non-circular pin: verdict→changes→{source,revised}, never mutual) plus reuse of amend's lost-update guard. Reason: codex, "write it atomically with the same lost-update discipline as amend… include a non-circular verdict pin."

**Changed — Q1, toward codex.** Round 1 I treated within-run title matching as tolerable. Codex is right that `changes.json` is *machine* provenance, not the human-in-the-loop `amend`, and the code backs the risk: `_finding_titles` (`:525-532`) appends every title **with no uniqueness guard**, and it only covers `blockers`+`concerns` (dissent is excluded). Two same-titled findings make an edit's `resolves` ambiguous with nothing to disambiguate. I move to codex's minimum: `{list, index, title}`, conductor-asserting `data[list][index].title == title`. I still **decline** codex's stronger option — a real `id` on verdict@2 — as premature (a second schema evolution in two releases for a within-run consumer).

**Still dissent — Q6, against Gemini.** Gemini's flip-to-ship is "endorsement OFF-by-default or parallelized." I reject OFF-by-default: it converts "board-endorsed" into marketing and lets R4 bite (one seat's rewrite wearing the board's name). Gemini's "+40–60%" is a **spawn-count** figure (token cost — real) miscast as **latency**. The endorsement pass is dependency-free per-seat fan-out, structurally a review round, and rounds already fan out concurrently (`rounds.py:232-234`, `ThreadPoolExecutor(max_workers=len(seats))`). Reused, its **wall-clock cost is ~one extra round**, not N sequential spawns. So I adopt Gemini's *parallelize* as mandatory and reject its *default*. `--no-endorse` remains the escape valve for the genuine token-cost axis.

**Agree, strengthened — Q8, with codex.** Codex's "no metadata header inside the clean revised draft" is not a nit — it's a correctness bug in the strawman. See §3.

## 3. Strongest remaining objections

1. **The clean draft must be byte-clean (Q8).** The strawman says `revised-draft.md` carries a "header noting run title, seat, unresolved count." That artifact is *the thing a human applies*. A header means applying it prepends board metadata to the user's document — and for **code**, `revised-draft.<ext>` with a header is a syntax-corrupt or semantically-wrong file the moment it's saved. Metadata belongs in `changes.json`, the HTML handoff, and the run card — **never in the applied file.** Invariant, not preference.

2. **Silent truncation still ships a corrupted "board-endorsed" copy (Q5).** Still the highest-severity failure. One-spawn coupling (mapping can't drift from text) is worth keeping, but the retry set only catches *timeout*. Truncation produces a *plausible-looking* short reply. Defense must be three-layered (§5 INV-2). Gemini's instinct here is right even though its remedy (line-numbered patch instructions) trades one failure for a worse one — models computing their own line numbers is a fresh error class. Keep full-text emission; gate size instead.

3. **Title-only `resolves` is ambiguous by construction (Q1).** No dup-title guard exists anywhere; `changes.json` has no human to disambiguate. Composite `{list, index, title}` with a conductor equality-assert is the cheap fix.

4. **`caveats` is a phantom container (Q3).** The brief names `blockers/concerns/caveats`; the schema is `blockers/dissent/concerns`. Every `resolves.list` enum, the completeness rule, and the "best-effort" carve-out inherit this error. Fix the vocabulary before a line of schema is written or the validator and the artifact will disagree on day one.

## 4. Recommended execution sequence

1. **Pre-work (blocking, no code):** reconcile `caveats`→`dissent` across brief + schema; lock Q1 composite locator and Q2 pin direction. These change `changes@1` before it's authored.
2. **Phase 2a — schema + validator:** `advisory-board/changes@1` with its own strict validator (mirror `board_verdict.py`), `resolves.list ∈ {blockers,dissent,concerns}`, model-authored fields limited to `summary`/`resolves`/`note`; conductor computes `n`, `status`, shas, locator-validation. Compat test: old verdicts still validate; `changes`-key refusal at `:142-144` stays for the *key on verdict.json* while `verdict.json.changes` *pointer* is separately, explicitly allowed (they are not the same object — call this out or the reservation test contradicts Q2).
3. **Phase 2b — revision seat:** generalize the synthesizer spawn path; `_run_revision_step()` after `_run_synthesis_step()` (`cli.py:497`); single spawn, DATA-fence + neutralizer; verdict-required and size preflight enforced at resolve time; reconciliation invariant on parse.
4. **Phase 3 — renders:** `get_opcodes` word-level redline (new machinery — golden-file tested) for prose; `unified_diff` patch for code; **byte-clean** `revised-draft.*`.
5. **Phase 4 — endorsement (concurrent) + release:** endorsement pass on the `rounds.py:232` `ThreadPoolExecutor`, ON by default, `--no-endorse` opt-out; `unresolved` entries are endorsement targets too (§5 INV-4).

## 5. Invariants and guardrails

- **INV-1 (reconciliation spine):** every `edits[]` locator must fall inside a real hunk of the mechanical `original→revised` diff, and every diff hunk must be claimed by ≥1 edit. `status:"applied"` is **conductor-computed from the diff**, never model-asserted. Reconciliation failure ⇒ reject path (retry, then `changes-rejected.json` + exit 0 / exit 4 under `--strict-exit`). This is why embedded before/after text is unnecessary and undesirable — it would duplicate, and could contradict, the ground-truth diff.
- **INV-2 (anti-truncation, three layers):** (a) an opened DATA fence with no matching close ⇒ classified `invalid` ⇒ retry; (b) INV-1 reconciliation; (c) **source-size preflight** — refuse `--output revised-draft` loudly when source exceeds the single-spawn reliable-output budget (defer huge sources to a future per-hunk mode). Better a loud refusal at resolve time than a silently short board-endorsed copy.
- **INV-3 (byte-clean applied artifact):** `revised-draft.*` contains only the revised source bytes. Its sha256 in `changes.json.revised` must match the file on disk exactly. Any header/banner lives elsewhere.
- **INV-4 (endorsement integrity):** endorsement ON by default, dispatched concurrently; per-edit `ENDORSE/OBJECT/ABSTAIN` recorded as `{seat, edit_n, position, note}`; **`unresolved` entries are also endorsement targets** so a seat can object to how a conflict was characterized. Objections recorded, never auto-resolved (D6).
- **INV-5 (provenance):** revision + endorsement outputs merge into conductor-authored skeletons; `n`, shas, statuses, and the `verdict.json.changes` pointer are conductor-written and synthesizer-stripped if model-supplied (D8). Pin direction is acyclic: verdict → changes → {source, revised}.
- **Preserved:** D5 byte-identity of the no-flags default; D6 source never written; failure never discards successful rounds.

## 6. Risks, stale assumptions, missing evidence

- **Stale (confirmed):** `caveats[]` is not a container — `EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")` (`board_verdict.py:45`). Narrows/renames `resolves.list`.
- **Code-backed gap (Q1):** `_finding_titles` covers `blockers`+`concerns` only (`:528`) and has no dup-title guard. If `changes.json` must resolve **dissent** findings, it goes *beyond* the `amend` precedent — fine, but state it; the "amend sets the join-key precedent" claim is only 2/3 true.
- **Reservation ambiguity (Q2):** the validator refuses a top-level `changes` **key** (`:142-144`); Q2(b) adds a `changes` **pointer object**. The compat test must encode that these are distinct, or Phase-2b will read the refusal as forbidding the pointer.
- **Concurrency audit (Q2):** if both `amend` and the revision pointer-write can mutate `verdict.json`, the lost-update guard must be verified to cover both writers. Missing evidence: I did not audit amend's guard mechanism this round — Phase-2 task.
- **New machinery risk (Q8):** `get_opcodes()` appears **nowhere** in the repo; word-level-in-changed-lines redline is genuinely new — mandate golden files, and accept that paragraph *moves* render as delete+insert in v1.13.

## 7. Concrete evidence

- Containers: `scripts/board_verdict.py:45` — `EVIDENCE_CONTAINERS = ("blockers", "dissent", "concerns")` (no `caveats`).
- Amend join set + no dup guard: `scripts/board_verdict.py:525-532` — `_finding_titles` loops `("blockers", "concerns")`, appends every `item["title"]` unconditionally.
- `changes` reservation is a top-level *key* refusal on verdict data: `scripts/board_verdict.py:142-144` — `if "changes" in data: die("changes is reserved for the revision artifact (v1.13)…")`.
- verdict.json already mutated post-synthesis (write-once is gone): `scripts/board_verdict.py:535-537` — `cmd_amend` "Append ONE human amendment to a run's verdict.json."
- `--output` decorative; `--shape` drives rendering: parsed at `_conductor/cli.py:706`, resolved/persisted at `_conductor/config.py:99,427` and `ask.py:297`; render branch is `render_verdict.py:897 if shape == "quick-verdict"`. `revised-draft` is absent from the `cli.py:706` choices — new plumbing, confirmed.
- Diff substrate: `_conductor/revise.py:259` `difflib.unified_diff`; `_conductor/delta.py:15,82` `SequenceMatcher.ratio()`; **`get_opcodes` occurs nowhere** — redline is new.
- Concurrent fan-out (rebuts Gemini's latency framing): `_conductor/rounds.py:232-234` — `ThreadPoolExecutor(max_workers=len(seats))`, `pool.submit(_one, s)` per seat. (Synthesizer's `for seat in config.board` at `synthesizer.py:230,302` is single-spawn iteration, not the fan-out the endorsement pass should use.)

VERDICT: caution

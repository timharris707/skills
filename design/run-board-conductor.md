# Design: `run_board.py` — the Advisory Board conductor

**Status:** Proposal / design doc (not yet implemented)
**Author:** Claude (Opus 4.8), at Tim's request
**Date:** 2026-06-25
**Source:** Implements the winning recommendation from the 2026-06-25 competitive review (the "conductor" pitch), folding in the consent gate (Safety Counsel) and the one-card consent UX (Product Reviewer, amended). Builds directly on the batch-1/2 hardening already merged (`board_verdict.py`, `render_handoff.py`, `execution-harness.md`, the verdict schema, the run-metadata template).

---

## 1. Problem

The advisory-board skill is a twelve-file orchestration protocol with **no orchestrator**. Its own `preflight.md` says "most board failures are environmental — a CLI not installed, expired auth, a renamed model, a hung process — not reasoning." It then hands every one of those failure modes back to an LLM to re-improvise from Markdown on each run: the `</dev/null` that stops Codex hanging, `--skip-git-repo-check`, `--permission-mode plan` silently returning a plan-summary instead of a review, Gemini's stderr noise, silent model fallback, the exact artifact tree, hand-transcribed provenance. A protocol that runs differently every time isn't a protocol.

`execution-harness.md` (merged in batch 2) documented the run mechanics as copy-pasteable shell — but documentation is still re-interpreted each run. This proposal turns that spec into an executable conductor so the run happens the same way twice.

## 2. Goals (v1) / Non-goals

**Goals**
- Deterministic spawn / capture / timeout / classification per seat.
- A **seat-adapter registry**: CLI drift (a flag change, a renamed model) is a one-line edit, not a scavenger hunt.
- A **consent gate enforced before the first subprocess spawns** — not prose, not advisory.
- **Auto-captured provenance**: the model that *actually answered*, not the one requested.
- **Reuse, don't replace** the existing scripts (`board_verdict.py`, `render_handoff.py`, `format_output.py`).
- **Preserve seat agency** — orchestrate the process, don't cage the seats.
- Standard-library Python only; subscription CLIs by default.

**Non-goals (explicitly out of v1)**
- Resume-after-failure across a partial multi-round run (the single hardest item; deferred — see §14).
- The `claims.jsonl` ledger (v3).
- A full `board_contract.py` CI harness (v2; but the artifact schema is locked now so v2 needs no rewrite).
- "Smart intake" that auto-infers everything and demotes the interview (incremental UX layer; see §8).
- Replacing the synthesis *reasoning* with code (synthesis stays a model call; see §10).

## 3. Design principles

1. **Models reason; the conductor plumbs.** The script owns spawn, capture, gating, provenance, artifact layout. The models do the only thing models should — write the reviews and the synthesis. Glass box, not black box.
2. **Don't cage the seats.** The skill's doctrine is "seats are agentic — they may web-search and read their working directory, which usually *helps*." The conductor controls *how seats are invoked and captured*, not *what they're allowed to do*. Agentic flags pass through the adapter; the conductor never sandboxes away live grounding unless the run explicitly asks for isolation.
3. **One source of truth for mechanics.** The registry owns the flags and gotchas. `SKILL.md` stops *documenting* CLI mechanics in prose and points at the conductor as the executable spec (see §11). This resolves the prose-vs-code drift before it starts.
4. **Fail safe on consent.** No `subprocess.run()` touches a provider until a classification is acknowledged. The default path is the safe one.
5. **Build on what's merged.** The conductor calls `board_verdict.py` to validate, `render_handoff.py` to render HTML, `format_output.py` for shares. It does not reimplement them.

## 4. Architecture

```
                 ┌─────────────────────────────────────────────┐
  --source ─────▶│ 1. Resolve config (flags + inferred defaults)│
                 └───────────────────────┬─────────────────────┘
                                         ▼
                 ┌─────────────────────────────────────────────┐
                 │ 2. Preflight  →  GO/NO-GO table  (≥2 GO?)    │  per-adapter
                 └───────────────────────┬─────────────────────┘
                                         ▼
                 ┌─────────────────────────────────────────────┐
                 │ 3. Consent gate  →  sensitivity.json         │  ◀── HARD STOP
                 │    + run-card confirmation (Proceed?)        │      (no spawn until
                 └───────────────────────┬─────────────────────┘       acknowledged)
                                         ▼
                 ┌─────────────────────────────────────────────┐
                 │ 4. Round 1 fan-out  (spawn each seat)        │  adapter registry
                 │    → round-1/<seat>.md  + logs + provenance  │
                 └───────────────────────┬─────────────────────┘
                                         ▼
                 ┌─────────────────────────────────────────────┐
                 │ 5. Build board-packet-round-2.md             │
                 │ 6. Round 2 fan-out → round-2/<seat>.md       │   [Round 3 / auto: v1.x]
                 └───────────────────────┬─────────────────────┘
                                         ▼
                 ┌─────────────────────────────────────────────┐
                 │ 7. Synthesis step (neutral seat OR agent)    │  reasoning = model
                 │    → final-consensus.md + handoff-data.json  │
                 │      + verdict.json                          │
                 └───────────────────────┬─────────────────────┘
                                         ▼
                 ┌─────────────────────────────────────────────┐
                 │ 8. render_handoff.py → final-consensus.html  │  reuse existing
                 │    board_verdict.py  → validate/gate         │  scripts
                 │    run-metadata.md   → auto-provenance       │
                 └─────────────────────────────────────────────┘
```

## 5. The seat-adapter registry (the load-bearing idea)

An **adapter** is a small, declarative spec — one per seat type. It is the only place that knows a provider's CLI quirks. Sketch (stdlib `dataclass`):

```python
@dataclass(frozen=True)
class SeatAdapter:
    name: str                       # "claude" | "codex" | "gemini" | ...
    default_model: str              # "claude-opus-4-8"  (overridable per run)
    reasoning_flag: tuple           # ("--config", "model_reasoning_effort=xhigh") etc.
    build_argv: Callable            # (model, prompt_path, read_only, workdir) -> list[str]
    stdin_mode: str                 # "devnull" (codex) | "prompt" (claude/gemini) | "none"
    model_answered: Callable        # (stdout, stderr) -> str | None   (parse the REAL id)
    stderr_is_fatal: bool           # False for Gemini (router noise on stderr is normal)
    timeout_s: int = 600
```

A run builds its lineup from `REGISTRY: dict[str, SeatAdapter]`. Consequences:

- **CLI drift** (`gpt-5.5` → `gpt-5.6`, a renamed flag) = edit one registry entry. Today it's six files.
- **A new seat** (a fourth provider, a local Ollama seat for `local-only` runs) = add one entry, not a new code path.
- The gotchas live in code where they're testable: `stdin_mode="devnull"` *is* the `</dev/null` fix; `stderr_is_fatal=False` *is* the "judge Gemini by content, not exit code" rule; `model_answered` *is* the anti-silent-fallback provenance capture.

The three default adapters encode exactly the flags `execution-harness.md` already documents (`codex exec --sandbox read-only --skip-git-repo-check … </dev/null`; `claude -p … --permission-mode plan` on stdin; `gemini -p … -m …` tolerant of stderr).

## 6. Preflight and a written definition of "GO"

Henry's verdict flagged that "GO" is currently implicit. Pin it down. A seat is **GO** iff, in order:

1. **Binary present** — `<cli> --version` exits 0.
2. **Auth active** — the CLI's own status/whoami reports an authenticated, non-expired session (subscription-backed where detectable). Never print the token.
3. **Model resolves** — the requested model is accepted (listed, or not rejected as unknown by the smoke ping).
4. **Smoke ping** — a one-token read-only prompt returns non-empty within a short timeout.

The conductor runs all four per adapter and prints the GO/NO-GO table from `preflight.md` — now executable. **≥ 2 GO → proceed**; otherwise stop and report which check failed and how to fix it. Degraded/dropped seats are labeled, never silently dropped.

## 7. Consent gate — enforced, pre-spawn

This is the one safety gap that prose cannot close (and that batch-1's wording change only softened). The gate is structural:

- The conductor classifies the source: `public` | `redacted` | `local-only`, against a **tight rubric** (see open questions, §15) so operators can't reflexively click through.
- It emits `sensitivity.json`: `{classification, providers[], stripped[], acknowledged_at, acknowledged_by, skip_reason?}`.
- **Hard stop:** no adapter's `subprocess.run()` is reachable until `sensitivity.json` exists with a non-null `acknowledged_at` (or the run is switched to a `local-only` board). The gate lives *before* prompt construction, structurally — not as a check the LLM is asked to remember.
- Non-interactive escape hatch for CI: `--skip-sensitivity-gate` is allowed **only** with an explicit `--sensitivity=<class>` already set, and is logged verbatim into `run-metadata.md` (`skip_reason`). Explicit and auditable, never silent.
- `local-only` swaps the lineup for local model adapters (e.g. Ollama) and records the mode; nothing leaves the machine.

## 8. The run-card (consent + config in one confirmation)

The confirmation surface for the gate. A single pre-filled card the conductor prints (or the orchestrating agent renders) before any spawn:

```
┌── Advisory Board — run card ───────────────────────────────┐
│ Source   : ./design/payments-idempotency.md  (~1.2k words) │
│ Lens     : software-architecture   (inferred from source)  │
│ Rounds   : 2     Cross-reading: summaries                  │
│ Board    : Claude · Codex · Gemini                         │
│ Data     : classification = PUBLIC.  This sends your        │
│            source to Anthropic, OpenAI, and Google.        │
│ Proceed? [y / edit / no]                                   │
└────────────────────────────────────────────────────────────┘
```

**v1:** the card always shows config **and** the explicit data disclosure, and requires one confirmation. The data line is never auto-accepted — that is the fix for Gemini Pro's original footgun.
**Incremental (post-v1):** the conductor gets better at *inferring* the config (lens/rounds/output) from the source so the card is more often right on the first try, demoting the 7-question interview to "edit / advanced mode." Consent stays explicit in the card at every step.

## 9. Deterministic artifact tree + auto-provenance

```
<out>/
  run-card.txt              sensitivity.json
  prompts/<seat>-round-N.prompt
  round-1/<seat>.md         logs/<seat>-round-1.stderr
  round-2/<seat>.md         logs/<seat>-round-2.stderr
  board-packet-round-2.md
  final-consensus.md  handoff-data.json  final-consensus.html  verdict.json
  run-metadata.md           run-metadata.tsv   (machine row per seat-round)
```

`run-metadata.md` is auto-filled from what actually happened (per `run-metadata-template.md`): the model that **answered** (parsed via the adapter's `model_answered`, not the requested id), redacted commands, wall-clock per stage, auth mode, and `ran`/`degraded`/`dropped` status. The verdict is only as trustworthy as knowing exactly who voted — so the conductor captures it instead of asking a human to transcribe it.

## 10. Synthesis and reuse of existing scripts

The conductor produces the per-seat artifacts and the board packets deterministically. The **synthesis itself stays a reasoning task** (consensus, dissent, minority report, the evidence/judgment/couldn't-verify split from `epistemics.md`) — so it is a *model call*, not hardcoded logic:

- **v1:** the conductor stops at clean packets + artifacts and hands off to the orchestrating agent (or a single neutral-synthesizer seat) to write `final-consensus.md` + `handoff-data.json` + `verdict.json`. The flaky part (spawning CLIs correctly) is now automated; the reasoning stays with a model.
- The conductor then **calls** `render_handoff.py` (→ `final-consensus.html`) and `board_verdict.py` (→ validate/gate). `format_output.py` produces PR/Slack/TL;DR shares on demand.
- **v1.x:** promote the synthesizer to a defined neutral seat the conductor spawns, so the whole chain is one command.

## 11. Resolving the prose ↔ code drift (before it starts)

The risk named in the review: "`run_board.py` quietly becomes the real source of truth while `SKILL.md` rots into decoration." Decision, taken up front:

- The **registry is canonical for execution mechanics** (flags, stdin, stderr policy, model parsing). The "CLI Execution Notes" prose in `SKILL.md` is removed and replaced by a pointer to the conductor + registry. Mechanics are documented in exactly one place.
- `SKILL.md` remains canonical for **intent, the round protocol, epistemics, lenses, data handling, and the portable fallback** — the conductor is the dependable path; the prose is what an agent follows when no conductor is available. Nothing is lost.
- Optional hardening: generate the human-readable "CLI notes" section from the registry so the two can never disagree.

## 12. CLI surface (adopt the reviewed spec verbatim)

```
python3 scripts/run_board.py \
  --source PATH|URL|- \
  --rounds 1|2|3|auto      (default 2) \
  --cross-reading none|summaries|full   (default summaries) \
  --lens <preset>          (default: inferred, fallback software-architecture) \
  --board claude,codex,gemini  \
  --sensitivity public|redacted|local-only \
  --out DIR                (default /tmp/advisory-board-<ts>) \
  [--dry-run] [--yes] [--skip-sensitivity-gate]
```

`--dry-run` prints the resolved config, the run-card, the preflight plan, and the artifact tree it *would* create — without spawning anything. It is the cheapest way to review a run and the backbone of testing (§13).

## 13. Testing (without burning tokens)

- **Mock CLIs:** tiny stub executables (shell scripts on `PATH` in the test env) named `claude`/`codex`/`gemini` that echo canned, banner-accurate output. The full pipeline runs in CI with zero real model calls.
- **Per-adapter integration test:** spawn each adapter against its stub; assert capture, timeout handling, `ran/degraded/dropped` classification, and `model_answered` parsing. This is the test Henry's "Open Risks" demands — otherwise the registry is "just another Markdown table."
- **Gate tests:** consent gate blocks when `sensitivity.json` is absent/unacknowledged; `--skip-sensitivity-gate` requires an explicit class and logs a reason.
- **`--dry-run` golden test:** stable plan output for a fixture source.
- **v2:** `board_contract.py` validates a produced run directory (shape, metadata parity, Markdown/HTML agreement, no leftover `{{TOKENS}}`, no remote HTML assets) and runs against the regenerated example.

## 14. Scope / phasing

| Phase | Contents |
|-------|----------|
| **v1** (this proposal) | registry + preflight(GO defined) + consent gate + run-card + R1→R2 fan-out + artifact tree + auto-provenance + reuse render/validate + mock-CLI tests |
| **v1.x** | Round 3 / `auto` adaptive rounds; promote synthesis to a spawned neutral seat |
| **v2** | `board_contract.py` CI harness (artifact schema is locked in v1 so no rewrite) |
| **v3** | `claims.jsonl` ledger — per-seat prompt changes + resolver in synthesis |
| **Deferred** | resume-after-partial-failure (hardest item; design the artifact tree to *allow* it — idempotent per-seat writes — without building it yet) |

**Honest effort.** The pitch's "one PR, one day" is fiction, and the panel said so. The core — spawn/capture/provenance/consent (Milestones 1–3 below) — is the real work; Milestones 4–6 are mostly mechanical. Budget a focused **~3–5 working days** for a solid, tested v1, not an afternoon.

## 15. Risks & open questions

- **Agency vs. determinism.** The registry must pass agentic flags through; the conductor must *not* over-sandbox by default (only when a run asks for isolation). Get this wrong and we strip the live grounding the skill values.
- **"GO" is now defined (§6) — but auth detection differs per CLI.** Each adapter needs a real `auth_ok` probe; "subscription vs API key" may not be detectable everywhere — degrade gracefully and record what was detected.
- **Provenance parsing is per-provider and brittle.** `model_answered` is a regex over a banner today; banners change. Treat a parse miss as "unknown — flag it," never as "assume requested."
- **Consent rubric tightness.** If the rubric is loose, operators learn to click through and we're back to theater; if too strict, it blocks benign public runs. Needs a real first-pass rubric and iteration.
- **Synthesizer neutrality.** A spawned synthesizer seat (v1.x) must be a seat that didn't debate, or a blind merge, per `epistemics.md` — or the chair grades its own work.
- **Portability.** `timeout` isn't on macOS by default (`gtimeout`); large packets blow `ARG_MAX` (pass via file/stdin). Both are already noted in `execution-harness.md` and move into the adapter layer.

## 16. Implementation plan

Each milestone is an independently reviewable PR.

- **M0 — Design freeze.** This doc approved; artifact schema (§9) and `sensitivity.json` shape locked. *(no code)*
- **M1 — Skeleton + `--dry-run`.** Arg parsing, config resolution, the registry with 3 adapters, run-card rendering, and `--dry-run` that prints config + card + preflight plan + artifact tree. Mock-CLI stubs land here. *No spawning yet.* → testable immediately.
- **M2 — Preflight + consent gate.** Executable GO/NO-GO (§6); `sensitivity.json` emission + pre-spawn hard stop (§7); `≥2-GO`. Gate + preflight tests against stubs.
- **M3 — Spawn + capture + Round 1.** Real `subprocess.run` per adapter, timeout, stderr policy, `ran/degraded/dropped`, `round-1/` artifacts + provenance capture. Per-adapter integration tests (the load-bearing tests).
- **M4 — Round 2 fan-out + packets.** `board-packet-round-2.md` generation, Round-2 fan-out, `run-metadata.md` auto-fill.
- **M5 — Synthesis hook + reuse.** Hand-off contract for synthesis → `final-consensus.md`/`handoff-data.json`/`verdict.json`; conductor calls `render_handoff.py` + `board_verdict.py`.
- **M6 — Docs + drift resolution + reference run.** Update `SKILL.md` (point at the conductor; remove duplicated CLI mechanics per §11); update `scripts/README.md`; **regenerate `examples/payments-idempotency-review/` via the conductor** as the proof-of-life reference run.

A reasonable first PR is **M1 + M2** together (skeleton, registry, dry-run, preflight, consent gate, mock CLIs) — it's the spine, fully testable, and lands the safety-critical gate before any real spawn exists.

---

## Appendix: how this maps to the competition

| Pitch | Disposition here |
|-------|------------------|
| Opus — conductor + adapter registry | **The spine.** §4–§5, §11. |
| Max — `BoardRunner` (`--source/--rounds/...`) | CLI surface adopted verbatim (§12); resume mode deferred (§14). |
| Sonnet — consent checkpoint | **v1 hard requirement**, re-placed pre-spawn (§7), surfaced via the run-card (§8). |
| Gemini Pro — smart intake | Amended to the run-card; consent-explicit (§8). UX magic is incremental, not v1. |
| Workflow Critic — `board_preflight.py` | A conductor *module*, not a sibling script (§6). |
| Test Harness — `board_contract.py` | v2; artifact schema locked now so it needs no rewrite (§13). |
| Prompt Auditor — `claims.jsonl` ledger | v3; parked (§14). |

---
name: advisory-board
description: Convene a multi-model advisory board (a round table) where subscription-backed Claude, Codex, and Gemini CLIs each review the same material independently, debate across rounds by reading one another's findings, and converge on a single working handoff. Use when the user asks for an advisory board, round table, or panel; a multi-model or multi-provider review; a skilled debate among models; an adversarial review of a plan, design, architecture, document, decision, or strategy; an Opus/GPT/Gemini cross-check; or a consensus handoff from several frontier models.
---

# Advisory Board

Bring an idea, problem, plan, or architecture to a board of frontier models sitting in different roles. Each reviews it independently, then they read and challenge each other across one or more rounds, and you leave with the strongest conclusion the board can reach together and a clean takeaway — not three disconnected opinions.

## Must Not

Hard rules, collected here so they are never missed (each is elaborated in context below). Violating one invalidates the run.

- **Never write files or make edits** unless the user explicitly asked for edits — the board is read-only by default.
- **Never write artifacts into a tracked git tree** without naming the location first; default to the persistent runs root (`~/.advisory-board/runs/<slug>-<date>/`), or a throwaway `/tmp/advisory-board-*` folder with `--ephemeral`.
- **Never substitute a model silently** — if a requested model is unavailable, use the nearest same-provider frontier model and say so.
- **Never skip the data-handling disclosure** for non-public material — not even when the user says "use defaults." Disclose what leaves the machine and to whom, and get a go-ahead, before any external seat runs (`references/data-handling.md`).
- **Never present a degraded or dropped seat as a full board** — label it on the seat card and in `verdict.json` (`dropped: true`); a board needs at least two seats that actually ran.
- **Never print or store secrets** — keys, tokens, cookies, or private environment values — in prompts, packets, artifacts, logs, or metadata.

## Core Defaults

- Use subscription CLIs by default, not provider API keys.
- Run read-only unless the user explicitly asks for edits.
- Rounds: 2. Cross-reading: summaries. Final artifact: full handoff (Markdown plus a self-contained HTML view).
- Write run artifacts to the **persistent runs root** by default — `~/.advisory-board/runs/<slug>-<date>/` (slug from the run title, date from the run date; a same-day rerun gets a `-2` suffix, never an overwrite) — so runs stop evaporating and `run_board.py history` can list them. Override the root with `$ADVISORY_BOARD_RUNS_ROOT` or `--runs-root DIR`; name an exact dir with `--out DIR`; or opt back into a throwaway timestamped `/tmp/advisory-board-*` folder with `--ephemeral`. Every real run announces where its artifacts land on its first output line (a `--from-recipe` re-run reuses — and rewrites — the recipe's recorded dir unless you point it somewhere fresh). Persistence changes only the disk location — artifacts inherit the run's sensitivity handling (`references/data-handling.md`).
- Writing artifacts into the reviewed project is itself a write, even on a read-only review: do that only when the user asks or agrees, prefer a dedicated `advisory-board/<timestamp>/` (or `docs/advisory-board/<timestamp>/`) folder, and never write into a tracked git tree without naming the location first.
- One flag sets the whole cost/depth posture: **`--tier quick|standard|deep`**. `quick` — 1 round, `summaries` cross-reading, reduced per-seat reasoning (claude `high`, codex `medium`; model ids never change, and seats without an effort knob are untouched). `standard` — today's defaults, a deliberate no-op. `deep` — 3 rounds, `full` cross-reading at the registry's max-tier reasoning (codex stays at `xhigh`, its hard ceiling). The tier is a **base**: explicit flags (`--rounds`, `--cross-reading`) always override it, the run's `run-metadata.md` notes the tier when one was given, and `run-recipe.yaml` records the **resolved values**, never the tier name — so `--from-recipe` replays exactly (the pair is refused as contradictory). Three frontier models at high reasoning across several rounds can take minutes and meaningful tokens — flag a large run to the user before launching it, with numbers: `run_board.py run … --dry-run` prints a best-effort token/cost/time **estimate** for the exact run shape (an estimate, never a gate; subscription-backed CLIs may bill nothing per token). After the run, `run-metadata.md` records what each seat CLI actually reported, where known.

## Upfront Choices

Optionally open with the intake interview (`references/intake-interview.md`) — a short structured Q&A, using the `grilling` or `grill-with-docs` skills as the engine when available — to settle the run. Otherwise ask only for whatever the user hasn't already given:

1. Source material: file(s), repo, URL, or goal to review.
2. Rounds: `1`, `2`, `3`, or `auto` (default `2`; `auto` adapts — see Round Protocol).
3. Cross-reading: `none`, `summaries`, or `full` (default `summaries`).
4. Output: `quick verdict`, `full handoff`, or `implementation sequence` (default `full handoff`).
5. Lens preset: the seat lineup's focus, from `references/lens-presets.md` (default: inferred from the material, falling back to `software-architecture`).
6. Sensitivity: can the material go to external providers? (`references/data-handling.md` — may force a local-only board.)
7. Board: seats and size, from `references/board-composition.md` (default: three seats — Claude, Codex, Gemini).

If the user says "use defaults", stop asking the *optional* setup questions and run with the defaults — with one exception. The data-handling check (choice 6) is mandatory: if the material isn't clearly public, still disclose which providers will receive it and get an explicit go-ahead before launching any external seat (`references/data-handling.md`). "Use defaults" settles the optional choices; it never waives that consent.

## Model Lineup

Target the strongest reasoning model each provider offers:

- Claude seat: `claude-fable-5` (Anthropic's most capable model) at max effort — `--effort max`. Fable 5 is a premium tier (priced above Opus) and max effort means longer, costlier runs; the sanctioned swap when Claude usage matters more than depth is `--model claude=claude-opus-4-8` (also the seat's registered fallback if Fable is unavailable — Opus 4.8 runs the same `--effort max`). To conserve Claude usage entirely, seat a board without the Claude seat (`--board codex,gemini`) — the other seats bill their own subscriptions.
- Codex seat: `gpt-5.5` with `model_reasoning_effort="xhigh"` (or the highest Codex reasoning setting available).
- Gemini seat: Google's latest frontier reasoning model via the Gemini CLI (currently Gemini 3.1 Pro) with `thinkingLevel: HIGH` (or the highest available).

Model names and flags move fast — verify them against the installed CLIs or official docs before a large run. If a named model is unavailable, use the nearest same-provider frontier model and say so; never substitute silently.

Preflight — run `references/preflight.md` before launching: for each seat, check the CLI is present, auth is active (subscription-backed where possible), the requested model resolves, and a one-token smoke ping returns. Proceed only with at least two seats GO; label any degraded or dropped seat in the handoff. In summary:

- **First run? `run_board.py doctor`** — a guided setup check that sweeps **every** registered provider (installed → version currency → auth → default model resolves), prints per-provider fix-it steps (install command, auth command, model fallback), and summarizes which boards are viable today (≥ 2 seats GO) plus a suggested first command. Probes and smoke-pings only — it never reads or sends your material.
- **Toolchain currency first** — `run_board.py toolchain` checks each CLI against its latest release and (`--update`, consent-gated) upgrades stale ones; `--install` installs absent ones (account/auth still required). A stale CLI is the usual reason a freshly-renamed frontier model id 404s; updating first keeps the board from half-failing. Model ids stay pinned — if one still won't resolve, preflight *proposes* a working fallback rather than swapping silently.
- **Graceful degradation** — if fewer than two seats are usable (a downloaded skill on a machine with only one provider's CLI/account), preflight doesn't dead-end: it distinguishes *not installed* (prints the install command) from *installed-but-unauthed*, and points to the fallbacks — a same-provider multi-lens board or a local/human seat (`references/board-composition.md`). You never need all three providers to get value.
- Confirm Claude subscription auth is active.
- Confirm Codex is on ChatGPT/subscription auth, not API-key-only, when possible.
- Confirm Gemini auth and model/config support.
- Never print secrets, tokens, cookies, or private environment values.

## Seats

Give each seat a distinct lens so the board covers more ground than any single reviewer, and match the lenses to the subject. Pick a ready-made lens set from `references/lens-presets.md` — `software-architecture` (default), `product-strategy`, `research-paper`, `legal-contract`, `business-decision`, `writing-editing` — or compose your own. For software and technical work, the default split:

- Claude: architecture, systems, and adversarial design review.
- Codex: repo-grounded implementation, migration, testing, and execution.
- Gemini: product, operations, rollout, latency, evaluation, and user-workflow risk.

For non-software subjects (strategy, research, writing, business, policy), assign comparable lenses — e.g. one seat on first-principles soundness, one on execution and feasibility, one on second-order consequences and stakeholder or user risk.

Every seat still answers the full brief; the lens reduces blind spots, it doesn't narrow responsibility.

The board defaults to three seats but isn't fixed at three — for sizing (2–5), the same provider in multiple seats (`--board claude,claude,codex` auto-numbers, or `--board econ=claude,risk=claude` aliases — each seat takes its own lens via a repeated `--lens id=…`), a human or local-model seat, an **Antigravity** seat (Google's `agy` CLI, the successor to the sunset gemini-cli), and minimal "works with what you have" lineups, see `references/board-composition.md`.

## Data Handling

A board sends the same source material to every seat's provider. Before the first call, if the material isn't already public, tell the user what will leave the machine and to whom, and get a go-ahead. For sensitive material, redact the shared source packet; for must-not-leave material, run a local-only board or don't run it. Full guidance: `references/data-handling.md`.

### Repo-grounding & verification

By default a board reviews the **text you hand it** and is blind to the codebase that text is about — so findings come back "conditional on the cited factual base," none confirmed by a seat that read the code. The optional `--repo PATH` closes that gap: it augments `--source` (the source file still frames the question; the repo is the evidence base) by handing every seat a **read-only snapshot** of the repository so they verify claims against real code and cite real `path:line` instead of critiquing prose. The snapshot is `.gitignore`-respecting, `.git`-excluded, secret-denylisted, and symlink-confined; consent binds to its **scope hash** alongside the source-packet hash, and `repo-scope-manifest.json` records exactly what was in scope at approval. Repo-grounding details and the egress story: `references/data-handling.md`.

Grounding then makes the verdict chain trustworthy on **code**, not just prose: once seats cite real lines, `verify --source <repo> --run <out>` resolves those citations against the tree and stamps each `verified`/`unverified`/`refuted` — a fabricated citation stamps `refuted` and `validate --gate` abstains. No change to `verify_evidence.py`/`board_verdict.py`; the feature is entirely upstream (D7).

In **gate mode** (`--repo` on a gate-bearing run), the safety policy is **read XOR network**: every seat must be network-isolatable, because a grounded seat that is also networked can read a secret and exfiltrate it (or be driven to by an injected repo file). Seats that can't be de-networked (today **gemini**, **antigravity**) make a gate+`--repo` run **refuse** — the offending seat is named as a labeled NO-GO, never silently dropped (D4). **Advisory + `--repo`** is the home for casual self-review of your own repo (network on, you own the risk) with a loud disclosure; a gate-bearing run never silently falls back to advisory.

**Caveat — what "verified against the repo" does and doesn't mean (§9).** A `verified` stamp means the **receipt resolves** — the cited `path:line` exists and the quoted text is there — **not** that the inference drawn from it is sound. The gate catches fabrication, not grounded-but-wrong reasoning. Two limits follow and must be stated honestly: (1) a **poisoned repo** can make a wrong claim cite a real line, so `verified` on an attacker-controlled tree is not trust; and (2) because the snapshot is **cleaned up after the run**, later re-verification points `--source` at the **live repo**, so a citation that was real at approval can refute later if the tree drifted — `verified` is a statement about the snapshot at approval time, not a standing guarantee. This system also does **not** physically confine a seat's reads to the snapshot — codex's read-only sandbox can read files outside its working directory (R9) — so the snapshot bounds what is **consented to / hashed / verified against**, not what a seat can read; exfil is blocked by D4's network isolation, not by read-confinement.

## Round Protocol

**Round 1 — independent.**

- Give each seat the same source packet and its role lens, nothing else.
- No other seat's opinions.
- Require: verdict (with a confidence level — low/medium/high), strongest objections, revised sequence, invariants, risks, and concrete evidence.

**Round 2 — rebuttal (default).**

- Build a board packet from Round 1: a structured digest (`summaries`, the default) that puts every seat's take on each topic side by side under a verdict/citation agreement header — where the board agrees and where it splits — or the full prior responses when the token budget allows (`full`). `run_board.py` builds this deterministically from each review's own section structure plus the `VERDICT:` tokens; it never clusters claims by meaning (principle #1). Add `--digest-format json` to also write each round's digest as typed JSON (`board-packet-round-N.json` — the same parsed signals, machine-readable) next to the markdown.
- Ask each seat: what another seat caught that you missed, what changed your view (and whether the change is driven by evidence or mere deference — see `references/epistemics.md`), what you still dispute, what should become consensus, and what stays unresolved.

**Round 3 — convergence (optional).**

- Give each seat the Round 2 packet.
- Ask for the final position, hard dissent, and the smallest viable plan.

**Adaptive rounds (`auto`).**

- Stop early when the board has converged — a shared verdict, high confidence, and no material dissent after a round — rather than spending a round to rubber-stamp.
- Add a round when material dissent or low confidence remains and another exchange could plausibly resolve it, up to the `--max-rounds` ceiling (default 3).
- `run_board.py --rounds auto` makes this concrete: each seat ends its review with a `VERDICT: ship|caution|block` line, and the conductor measures **movement** between rounds as a pure function over that token plus the seat's concrete citations — never the prose (the model reasons; the conductor diffs tokens). It keeps going while the board is still moving and stops the moment it goes quiet; the per-round movement and the stop reason are recorded in `run-metadata.md` (`## Convergence`).

**Final synthesis.**

- After the last round, write the handoff: consensus, dissent (and why it matters), revised plan, risks, invariants, evidence, and next actions.
- Prefer a neutral synthesizer — a seat that didn't debate, or a blind merge — so the chair doesn't grade its own work (`references/epistemics.md`). If the board is unanimous, include a minority report: the strongest case against the verdict.
- Label model and round provenance (the model that actually answered, not just the one requested), and split the findings into three explicit buckets: **evidence-backed** (tied to a file, fact, run, or citation), **judgment calls** (reasoned but unproven here), and **couldn't-verify** (claims the board leaned on but didn't check, plus the shared blind spots no seat could see). For each load-bearing conclusion, note what would change it. The couldn't-verify bucket is the main guard against a confident, unanimous, *wrong* call — three models can converge on the same missing fact (`references/epistemics.md`).
- Emit `verdict.json` alongside the prose (`references/verdict-schema.md`) so the result can drive a gate or other tooling.

## Artifact Standard

Write:

- `round-1/<seat>.md` (and `round-2/`, `round-3/` as rounds run)
- `board-packet-round-2.md` (and `board-packet-round-3.md` when needed)
- `final-consensus.md` — the handoff in Markdown
- `final-consensus.html` — a self-contained, human-readable view of the handoff. Render it deterministically with `scripts/render_handoff.py` from a `handoff-data.json` (recommended — guarantees no leftover placeholders or template drift), or fill `references/handoff-template.html` by hand. Choose the **shape** with `scripts/render_verdict.py --html … --shape full-handoff` (default — the complete record), `--shape quick-verdict` (a slim skim brief to lead with), or `--shape implementation-sequence` (the sequence-first view for whoever executes: every next action in order with owners where named, backed by the blockers and their evidence — md + HTML); see `references/output-formats.md`. Trim by severity with **`--filter blockers|blockers+dissent|all`** (v1.14) on `render_verdict.py`/`format_output.py`: `all` is the full record (default, unchanged); `blockers` shows blockers only; `blockers+dissent` adds dissent. A dropped section is stated with counts (loud elision — never silent), the verdict banner/confidence are never filtered, and `--filter` is refused with `format_output.py --format json` (the JSON stays a faithful, unfiltered echo).
- `verdict.json` — the machine-readable verdict (`references/verdict-schema.md`); gate or reformat it with `scripts/`
- `changes.json` + `revised-draft.md`/`.<orig-ext>` — **only with `run --output revised-draft`** (v1.13): a board-derived, **board-endorsed** **revised copy** of the source, each edit mapped by the model to the board finding it resolves, mechanically validated (coverage reconciliation + index/title cross-assert), then voted on by the board — the per-edit **endorsement pass** (v1.13 P4, D13) runs by default: after the revision succeeds, each non-revision seat is fanned out concurrently to record `ENDORSE`/`OBJECT`/`ABSTAIN` on every edit and unresolved conflict in `changes.json.endorsements` (objections are recorded, never resolved — a human reads them). `--no-endorse` opts out (the token-cost axis); such a run is *findings-mapped*, not board-endorsed, and `endorsements` stays empty. The draft is **byte-clean** (the revised source bytes and nothing else — no header, so saved code stays valid) and **LF-normalized UTF-8** (the whole revision pipeline is LF-normalized end to end, so a CR/CRLF source is refused up front rather than silently re-terminated); `changes.json` (`advisory-board/changes@1`, `references/changes-schema.md`) is the edit→finding mapping (plus endorsements) of record and `verdict.json` gains a `{artifact, sha256}` pointer to it. The source file is **never written** — applying the revision is your act. Conflicting findings are surfaced as `unresolved` entries, never silently reconciled. A **code** source also gets a git-apply-able `revised-draft.patch` (`git apply -p1`); a **prose** source instead gets a word-level `<ins>`/`<del>` **redline** section in the full-handoff HTML (v1.13 P3, D12) — the two are siblings, at most one renders. Both are pure *views*, derived from the same sha-pinned strings `changes.json` already certifies (no new trust surface): the renderer walks verdict → `changes.json` → `{source-material.txt, revised-draft.*}`, re-verifying every hop's sha256 before diffing a byte, and drops the section with one stderr warning on any mismatch rather than showing something unverified.
- **Grounded citation snippets (v1.13 P3, #12).** When a `verify --repo`/`--source`-grounded run resolves a `code` citation, it captures the cited lines onto the evidence entry (`snippet: {from, to, text}`) so `final-consensus.md` and the sequence view embed the receipt as a fenced `path:from-to` block — the handoff is self-contained even though a grounded run's repo snapshot is cleaned up afterward. A citation that only resolved (no snippet) still renders as before.
- `run-metadata.md` — provenance: commands, the model that actually answered per seat, auth mode (no secrets), per-seat status (ran / degraded / dropped), timings, and source paths. Use `references/run-metadata-template.md`. When a seat CLI reports its own token usage, the conductor also records per-seat tokens and a best-effort cost/time line ("if known" — most CLIs report nothing, and nothing is ever guessed).

When a seat is degraded or dropped, show it on its HTML seat card (status pill) and in `verdict.json` (`dropped: true`) — never let a smaller board look like a full one. Derive lighter shares (TL;DR, PR comment, Slack, print/PDF) per `references/output-formats.md`.

**Output contract for the HTML.** It is a *view* of `final-consensus.md`, not a second source of truth — the two must not disagree. The rendered file must contain no leftover `{{tokens}}` and no template scaffolding comments, and must stay self-contained (inline CSS only; no external fonts, CDNs, scripts, or remote `<link>`/`<script src>`) so it opens offline on a double-click. Follow the template's two-placeholder convention: replace each single `{{TOKEN}}` in place, and duplicate each `BEGIN`/`END` block once per item (delete the sample block if there are none).

Never store secrets. Redact keys, tokens, cookies, and private environment values.

## How A Run Executes

**The conductor — `scripts/run_board.py` — is the canonical way to drive a board.** It owns the load-bearing mechanics in code: a seat-adapter **registry** (the one place that knows each CLI's flags, isolation, and model-id self-heal), an executable **preflight** (GO/NO-GO), a hash-bound **egress/quarantine gate** before any byte leaves, the **round-1 + round-2 fan-out** with the failure protocol, the **verdict chain** (`verify` evidence → `consensus` md/html → `validate`/gate), and the **run history** (`history` — a table of past runs read from each run's `verdict.json` under the persistent runs root; a partial or legacy run lists as `incomplete`). Run `scripts/run_board.py run …` (see `scripts/README.md`); a real run is in the repo-root `examples/payments-idempotency-review/`. Useful run controls: `--timeout SECONDS` caps every seat and `--timeout SEAT=SECONDS` caps one (ids as in `--model`/`--lens`; a slow local seat shouldn't set the whole board's clock), and `--digest-format json` also emits each round's structured digest as typed JSON. **Re-review a revised draft with `--revise <prior run dir>`** (v1.12): `--source` is the revised draft, and the round-1 prompts additionally carry a mechanical digest of the prior verdict plus the diff from the previously reviewed draft (recovered from the prior run dir, sha-verified; omitted loudly when unrecoverable) — every injected byte inside the consent packet hash. The new verdict records `previous_run` lineage, and the consensus render leads with the cleared / still-open / new delta and the verdict trajectory. **Ask a follow-up after the verdict with `ask "<question>" --run <dir> [--seat <id>]`** (v1.12): post-verdict cross-examination — the board answers a follow-up in one round, from a context packet built ONLY from that run's own artifacts (the reviewed material, a mechanical verdict digest, and each addressed seat's own prior review), bounded to the run and re-consented like any egress (public discloses; non-public needs `--yes`/approval; the sensitivity floor is the strictest of the recipe, the run's `sensitivity.json`, and a tighten-only `--sensitivity` flag — never looser, and a run missing its `sensitivity.json` never floats down to public); it writes `addendum-N.md` and refreshes the handoff. **Tune a completed verdict by hand with `board_verdict.py amend --run <dir> --author … --reason … <effect>`** (v1.12): append-only human tuning that never rewrites the board's own words — one effect per call (`--confidence`, `--caveat`, or `--severity-note [--on "<finding>"]`), recorded with provenance; renderers then show the effective value marked as amended, and a no-amendments verdict is unchanged. **Get a board-endorsed fixed copy with `run --output revised-draft`** (v1.13): after synthesis, a revision seat produces a revised copy of the source (each edit mapped by the model to the finding it resolves, mechanically validated — coverage reconciliation + index/title cross-assert) plus `changes.json` — the edit→finding mapping of record. Then the **endorsement pass** (v1.13 P4, D13) runs by default: once the revision succeeds, every non-revision seat is fanned out concurrently (≈ one extra round) to vote `ENDORSE`/`OBJECT`/`ABSTAIN` on each edit and unresolved conflict, recorded as `changes.json.endorsements` rows — objections are recorded, never resolved by another model loop (a human reads them, D6). `--no-endorse` opts out (the token-cost axis; that run is findings-mapped, not board-endorsed); a failed endorsement spawn records that seat as `ABSTAIN`/`dropped` and never fails the run or moves the exit code. It **requires** a verdict (`--synthesize`), takes `--source-type prose|code` to pick the redline format (the extension heuristic decides otherwise; a stdin or unknown-extension source must pass the flag) and `--revision-seat`; the revised draft is **byte-clean** with no header, the source file is **never written** (applying it is your act), conflicts surface as `unresolved` entries (never fatal), and a revision failure leaves the verdict/rounds intact (`changes-rejected.json` + exit 0, `--strict-exit` → 4). A code source additionally gets a `revised-draft.patch`; a prose source instead gets a redline section in the full-handoff HTML — see Artifact Standard above (v1.13 P3). Synthesis stays your reasoning task — the conductor stops at clean per-round packets and hands them to you (or one neutral seat) to fill `verdict.json`, then you call the chain.

The rest of this section and the **CLI Execution Notes** below are the **portable, script-free fallback** — the same protocol an agent runs by hand where the conductor isn't available. The principles hold either way:

- Run every seat as its own CLI subprocess — including the Claude seat as a separate `claude` process — so each reviews the source independently rather than reusing the orchestrator's context. That independence is what makes Round 1 worth anything.
- Keep the orchestrator and the chair neutral: assemble packets and synthesize, but don't also count yourself as a debating seat. If you must, say so in the handoff and use a minority report to check chair bias (`references/epistemics.md`).
- When the source is a repo or local files, decide once how seats reach it and record it in `run-metadata.md`: either every CLI reads the same shared path, or you build one source packet and hand identical bytes to each seat. Use one method for all seats so they review the same thing.
- Seats are agentic — they may web-search and read their working directory, which usually *helps* (live grounding). When you need a clean outside view or isolation, control the working directory and network and hand each seat one neutral source packet. (Running seats from a non-git folder also requires Codex's `--skip-git-repo-check`.)

For a concrete, copy-pasteable capture pattern — prompts written to files, stdout/stderr/exit-code/timeout capture, and `ran` / `degraded` / `dropped` classification folded into `run-metadata.md` — use `references/execution-harness.md`.

## CLI Execution Notes

> The conductor's seat-adapter **registry** (`scripts/_conductor/registry.py`) is the **canonical, self-healing** source for these mechanics — exact flags, gate-mode isolation, stdin handling, and model-id self-heal — kept current and asserted by tests. When a flag drifts, fix it there, in one place. The templates below are the **portable fallback** for running a seat by hand without the conductor; they are illustrative and not guaranteed current.

Prefer read-only modes. Confirm every flag against the installed CLI (`<cli> --help`) before a large run — or just use the conductor, which does.

Claude seat:

```
claude -p "<seat prompt>" --model claude-fable-5 --effort max --permission-mode plan
```

`-p` runs non-interactively; `--permission-mode plan` keeps it read-only. `--effort max` runs the deepest reasoning the build exposes (the flag accepts `low|medium|high|xhigh|max`; on Fable 5 thinking is always-on and effort scales how hard it thinks). On long analytic prompts, `--permission-mode plan` can make the seat return a plan-style *summary* (and even claim it wrote a file) instead of the full review — so append the `{{CLAUDE_OUTPUT_OVERRIDE}}` block from `references/prompt-templates.md` verbatim to the Claude seat's prompt, and treat a short or plan-shaped artifact as a degraded seat to re-run.

Codex seat:

```
codex exec --sandbox read-only --skip-git-repo-check \
  --config model="gpt-5.5" \
  --config model_reasoning_effort="xhigh" \
  "<seat prompt>" </dev/null
```

`codex exec` is the non-interactive form; `--sandbox read-only` blocks edits. Close stdin with `</dev/null`: `codex exec` reads stdin until EOF, so without it the call hangs when orchestrated in the background or any non-interactive pipeline. Pass `--skip-git-repo-check` so the run doesn't abort with "Not inside a trusted directory" when a seat runs from a neutral, non-git source folder.

Gemini seat:

```
gemini -p "<seat prompt>" -m "<latest-frontier-gemini-model>"
```

Run in a read-only / non-auto-approval mode so the seat can't make edits, and select the highest available thinking level. The Gemini CLI may print internal errors to stderr (e.g. model-router retries) yet still return a valid review — judge a seat by whether usable content came back, not by stderr noise or a non-zero exit; treat that as a degraded-but-ran seat, not a failure.

### Gemini thinking level

Prefer a CLI flag or environment variable if the installed Gemini CLI exposes one. Edit settings files only as a last resort — and if you do, back up the existing file first and restore it in a cleanup step that runs even on failure, so a crash can't leave the user's config mutated. Verify the schema against the current Gemini CLI configuration reference first; the shape below is illustrative, not guaranteed current:

```json
{
  "modelConfigs": {
    "customAliases": {
      "<alias>": {
        "modelConfig": {
          "model": "<latest-frontier-gemini-model>",
          "generateContentConfig": {
            "thinkingConfig": { "thinkingLevel": "HIGH" }
          }
        }
      }
    }
  }
}
```

## Prompt Templates

Load `references/prompt-templates.md` when running a board. Use the templates as a starting point, then adapt them to the source material, output type, and project constraints.

## Scripts

Optional helpers in `scripts/` (Python 3 stdlib, no install): `board_verdict.py` validates `verdict.json` and gates CI on the verdict (`--gate`; exit `1` block / `3` abstain when the board is torn or a citation is refuted; **`--min-severity blocker|concern`** (v1.14) narrows a fail — it composes with `--fail-on` so a fail must ALSO rest on a finding at/above that tier, e.g. a caution whose only findings are concerns/dissent passes under `blocker` — never affecting abstain), and appends append-only human tuning with `board_verdict.py amend` (a confidence change, caveat, or severity note, each with provenance — the board's own words stay untouched); `board_changes.py` validates a `changes.json` (the v1.13 `run --output revised-draft` artifact of record — the edit→finding mapping plus the per-edit board `endorsements` — `references/changes-schema.md`); `verify_evidence.py` resolves a verdict's typed evidence and stamps each `verified`/`unverified`/`refuted` (incl. opt-in, program-pinned re-execution of `command` citations via `--allow-program`); `render_verdict.py` renders `final-consensus.md` from the verdict; `format_output.py` renders it as a TL;DR, PR comment, Slack message, or JSON; `render_handoff.py` renders `final-consensus.html` deterministically from a `handoff-data.json`; and `render_plan.py` renders a **planning-document HTML view** deterministically from its markdown (`design/<plan>.md` is the source of truth — the HTML is regenerated, never hand-edited), the same render-from-source discipline, for following along as a multi-milestone plan is built. The skill runs fine without them — they're for wiring a board into CI and other tooling. See `scripts/README.md`.

## When To Stop

Stop and ask or report if:

- no source material is given and none is inferable from an obvious file or repo;
- fewer than two seats can authenticate or run — a board needs at least two voices;
- a step would need write access but the user asked for review only;
- full cross-reading would blow the context budget — fall back to summaries and say so;
- the material is too sensitive to send to external providers and no local-only board is available (`references/data-handling.md`).

If a provider is unavailable, or fails partway through, but at least two seats remain, continue as a smaller board and label the missing seat (and the round it dropped out) in the handoff rather than silently omitting it.

# Verdict Schema — `verdict.json`

Alongside the prose handoff, a run emits `verdict.json`: the **canonical, machine-readable
source of truth** for the board's conclusion. The Markdown (`final-consensus.md`) and HTML
render *from* it — `scripts/render_verdict.py` renders the Markdown directly; the HTML renders
via `scripts/render_handoff.py`. It drives tooling — most usefully a **CI / launch gate**
("block the merge when the board says block"; "ask a human when the board is torn").

## Schema (`advisory-board/verdict@2`)

```json
{
  "schema": "advisory-board/verdict@2",
  "title": "Payments API idempotency keys",
  "date": "2026-06-25",
  "verdict": "block",
  "confidence": "high",
  "unanimous": true,
  "lens_preset": "software-architecture",
  "rounds": 2,
  "board": [
    {
      "seat": "Claude",
      "model": "claude-fable-5",
      "lens": "architecture",
      "round_verdicts": ["block", "block"],
      "dropped": false
    }
  ],
  "blockers": [
    {
      "title": "Atomic dedup",
      "body": "Without an atomic SET NX claim two concurrent same-key requests double-charge.",
      "evidence": [
        { "kind": "code", "path": "src/charges.py", "line": 42, "status": "verified" },
        { "kind": "code", "path": "src/charges.py", "symbol": "charge_idempotent", "status": "verified" },
        { "kind": "source", "url": "https://internal/plan", "quote": "store the key-to-response mapping in Redis", "status": "verified" }
      ]
    }
  ],
  "dissent": [
    { "who": "Codex", "body": "The rollout aggressiveness is debatable; the correctness blockers are not." }
  ],
  "concerns": [
    { "title": "TTL vs retry window", "body": "...", "evidence": [ { "kind": "judgment", "detail": "no client data" } ] }
  ],
  "caveats": ["Reviewed the plan, not the code — re-check against the actual handler."],
  "open_questions": ["..."],
  "next_actions": ["..."]
}
```

### Fields

- `verdict` — `ship` | `caution` | `block`. The board's substantive position, and the canonical
  gate axis. (`abstain` is **not** a `verdict` value — it is a *gate outcome* computed at gate
  time from observed agreement; see below. It can't be self-asserted, by design.)
- `decision` (optional) — the native call when the decision isn't software-shipping (e.g.
  `invest` / `hold` / `wind-down`). Map it onto `verdict`; tooling reads `verdict`. When set,
  it's the human label verbatim — it wins over the lens-derived label below.
- `lens_preset` (optional) — the board-level lens preset name the run used (e.g.
  `software-architecture`, `business-decision`, `research-paper`). The conductor writes it; it
  picks the **human-facing** verdict label only — the machine `verdict` token is untouched. A
  `software-architecture` board (and an old file with no `lens_preset`) keeps the legacy
  `SHIP` / `SHIP WITH CHANGES` / `DO NOT SHIP YET` labels; every other preset (and any unknown
  one) renders plain language — `Go ahead` / `Proceed with care` / `Stop and rethink` — plus a
  one-line "what this means" note. An explicit `decision` overrides all of this.
- `confidence` — `low` | `medium` | `high`. A self-reported number; informational. **The gate
  never reads it** — a gameable confidence must not move a gate.
- `unanimous` — did every seat land on `verdict` in the final round.
- `board[]` — one entry per seat; `round_verdicts` is per-round, `dropped` flags a seat that
  didn't finish (see `references/run-metadata-template.md`).
- `blockers[]` / `dissent[]` / `concerns[]` — verdict-moving claims; each may carry `evidence[]`.
- `caveats[]` — the couldn't-verify bucket (strings, or `{claim, impact}`); rendered first-class.
- `open_questions[]` / `next_actions[]` — the same content the handoff shows. A `next_actions[]`
  entry is a string, or optionally `{action, owner}` — the `implementation-sequence` output shape
  names the owner on its step; every renderer accepts both forms (a plain string renders unchanged).

### Typed `evidence[]` (new in @2)

Each verdict-moving claim may cite structured, resolvable evidence. A claim citing no
external referent stays a *concern*, not a *blocker* (a synthesis judgment, not a validator
rule). Each item has a `kind`:

- `code` — `path` plus either `line` (positive int) or `symbol` (string).
- `source` — `url` plus a verbatim `quote`.
- `command` — a `command` string, plus optional `expect_exit` (int, default 0) and a verbatim
  `expect` substring. Re-execution is **opt-in** (M3): `verify_evidence.py --allow-program NAME`
  (+ optional `--allow-command REGEX` to pin args) re-runs a command whose argv[0] is `NAME` with
  no shell, a curated PATH, an isolated cwd, and a scrubbed env, then attaches the observed
  exit/output under `observed`.
- `judgment` — no external referent, by design; carries optional `detail`.

`scripts/verify_evidence.py` **resolves** a verdict's citations and stamps each with a
`status`: `verified` (the cited line exists / the quoted text is in the captured packet / an
allowlisted command re-ran with the expected exit + `expect` substring), `unverified` (couldn't
check — no source/packet, a missing file, or a `command` that wasn't allowlisted / couldn't run),
or `refuted` (we have the material and the line/quote is **not** there, or a re-run command
contradicted its expectation — a fabrication / wrong-claim signal).
`code` resolves against the source tree; `source` quotes resolve against the **captured
packet, never a live URL fetch** (that would breach quarantine in gate mode). **Honesty
(§9):** a `verified` stamp proves *the receipt resolves*, not that the inference is sound — it
catches fabrication, not faulty reasoning.

## What `board_verdict.py` enforces

Validation is strict so a malformed verdict can't quietly pass a gate. `scripts/board_verdict.py`
accepts both `advisory-board/verdict@1` (the original; evidence-optional) and `@2` (which makes
typed evidence first-class). Evidence is validated identically under either schema id — an `@1`
file *may* carry `evidence[]`, and a malformed item is rejected regardless of version. It checks:

- `schema` ∈ {`advisory-board/verdict@1`, `advisory-board/verdict@2`}.
- `verdict` ∈ {ship, caution, block}; `confidence` ∈ {low, medium, high}; `rounds` a positive int.
- each `board[]` seat has `seat`, `model`, a non-empty `round_verdicts` (every entry a valid
  verdict); `lens`/`dropped` type-checked when present.
- `lens_preset` is a string when present (it selects the human label; it never moves a gate).
- at least **two** seats actually ran (a `dropped` seat doesn't count — a one-voice board isn't a board).
- if `unanimous` is present, it matches the seats' final-round verdicts.
- every `evidence[]` item (on blockers/dissent/concerns or at the top level) is well-formed for
  its `kind`, and any `status` ∈ {verified, unverified, refuted}.

A schema violation exits `2`, distinct from a clean file that simply fails the gate (`1`).

## Using it as a gate

```
python3 scripts/board_verdict.py verdict.json --gate                    # fail on block
python3 scripts/board_verdict.py verdict.json --gate --fail-on caution  # fail on caution or block
```

Exit codes: **`0`** pass · **`1`** gate fail · **`2`** usage/schema error · **`3`** abstain.

**`abstain` ("human required").** A stochastic gate is safe when the board is decisive and
dangerous exactly when it is torn. `--gate` returns the neutral exit `3` — neither pass nor
fail — when:

- the seats that ran **straddle the `--fail-on` threshold** (some would trip the gate, some
  wouldn't) **and no single verdict holds a strict majority**; or
- the **declared `verdict` clears the gate while a majority of seats trip it** — the verdict
  contradicts the board it summarizes (an injected or fabricated "ship" over a block-leaning
  board is exactly this case); or
- **any citation is `refuted`** (a fabricated receipt in the decision document).

Synthesis *escalation* is honored: a declared verdict that **trips** the gate fails it even if
the seats lean the other way (blocking on a minority-but-correct concern is a legitimate, safe
call) — only **de-escalation** below the observed board is distrusted. The decision reads
**observed cross-seat agreement** (the `round_verdicts`), never the self-reported `confidence`.
In CI, treat `3` as "don't auto-merge — a human must decide," distinct from a clean `block` (`1`).

## The chain

Synthesis stays a reasoning task (§11): the conductor produces clean per-round packets and hands
them to the orchestrating agent (or one neutral seat) to fill `verdict.json` — it does **not**
generate the verdict in code. When you let the conductor spawn the neutral seat (`run --synthesize`),
a synth that fails to produce a usable `verdict.json` exits `0` by default (with a loud warning, so a
synth hiccup never discards the successful rounds). **In CI, pass `run --synthesize --strict-exit`** so
that failure exits non-zero (`4`, `EXIT_NO_VERDICT`) and the gate can't misread a missing verdict as a
pass. Then the deterministic chain runs:

```
run_board.py verify    verdict.json --source <src-tree> --run <run-dir>   # stamp evidence
run_board.py consensus verdict.json --run <run-dir> -o final-consensus.md # md (+ --html) from the verdict
run_board.py validate  verdict.json --gate                                # ship / block / ABSTAIN
```

See `references/output-formats.md` for turning the same file into a PR comment, Slack message,
or TL;DR (`scripts/format_output.py`).

# Run Metadata — v1.15 rubric first design brief

Date: 2026-07-02   ·   Rounds: 2   ·   Cross-reading: summaries
Mode: advisory   ·   Sensitivity: redacted   ·   Output: full-handoff
Lens preset: software-architecture

## Seats

| Seat   | Lens | Model requested | Reasoning | Auth | Preflight |
| ------ | ---- | --------------- | --------- | ---- | --------- |
| claude | Architecture & systems | claude-opus-4-8 | max | reachable (smoke-verified; not independently probed) | GO |
| codex  | Implementation & testing | gpt-5.5 | xhigh | reachable (smoke-verified; not independently probed) | GO |
| gemini | Product & operations | gemini-3.5-flash | HIGH | reachable (smoke-verified; not independently probed) | GO |

## Source

Access method: single source packet
Source: design/v1.15-rubric-first-design-brief.md (sha256:784353c06d2cfd356f2653012e8fb73000638e6ff2e786a328a49c44073d2d9e)
Sensitivity & handling: redacted

## Egress approval

- Decision     : APPROVED (hash-bound)
- Content hash : sha256:11d214bd9b1f3229d989821732138eb760f24bcb21cb5728f279fb3b4f8a4496
- Timestamp    : 2026-07-02T19:44:02
- Providers    : Anthropic, Google, OpenAI
- Detail       : approved via --yes (bound to the content hash)

## Round 1

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 689.2s | - |
| codex  | ran      | gpt-5.5 | 1 | 165.9s | - |
| gemini | ran      | unknown | 1 | 56.3s | - |

Tokens as reported by the seat CLIs (if known; capture is best-effort):
- codex: total 221,018 (combined count; the CLI reports no in/out split)

## Round 2

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 2 | 698.0s | - |
| codex  | ran      | gpt-5.5 | 1 | 156.3s | - |
| gemini | ran      | unknown | 1 | 72.2s | - |

Tokens as reported by the seat CLIs (if known; capture is best-effort):
- codex: total 171,908 (combined count; the CLI reports no in/out split)

## Convergence

Stop reason: round-count   ·   Rounds run: 2   ·   Ceiling (--max-rounds): 3   ·   Rounds mode: fixed (2)

| Transition | Seats moved | Considered | Per-seat movement |
| ---------- | ----------- | ---------- | ----------------- |
| 1 → 2 | 3 | 3 | claude +24 cites; codex +34 cites; gemini +16 cites |

Movement is a pure function over each seat's parsed `VERDICT:` token and its concrete citation set (inline-code spans + slash paths) — never its prose (principle #1 / §11). A seat moved if its verdict token shifted or it added a new citation; `auto` stops when board-wide movement falls below the threshold.

### Independence / echo

Low echo risk: 0/3 seats changed verdict in the final round, 11% mean citation overlap. Flags possible echo — it does not prove independence.

A pure, self-reported-signal metric (v1.14 #9): it FLAGS possible echo — seats drifting toward agreement for social rather than evidential reasons — over the final round's parsed signals (verdict flips toward the majority, citation-set overlap, and each seat's `BASIS:` line). It does NOT prove independence, and a `high` band is not a verdict on the board — see `references/epistemics.md` for the metric's limits and failure modes.

## Synthesizer

Seat: claude   ·   Model requested: claude-opus-4-8   ·   Model answered: unknown
Status: ran
Elapsed: 326.28s   ·   Attempts: 1   ·   Packet sha256: 3912ab45784da242…
Accepted (passed advisory-board/verdict@2 validation): yes

The synthesizer is a no-lens reasoning seat (§11): briefed only on the final-round reviews + the conductor-extracted VERDICT tokens, never the source. The conductor merges its content fields into an authoritative skeleton (schema/title/date/rounds/board[]) and runs `board_verdict.validate` before writing verdict.json — the human still gates ship/abstain.

## Cost & time (best effort)

- Tokens reported by the seat CLIs: 392,926 across 2 of 6 seat-round(s); the rest reported nothing and are counted as unknown, never guessed.
- Estimated cost of the reported tokens: ~$1.96–$11.79 at list prices dated 2026-07-01 (an ESTIMATE — subscription-backed CLIs may bill nothing per token; unknown/unpriced seat-rounds excluded).
- Wall clock (measured): 23.1 min across 2 round(s) — seats fan out in parallel, so each round costs its slowest seat.

## Notes

- 'Model answered' is what the CLI *reported*; 'unknown' means it reported nothing parseable (never assume the requested model answered).
- Round 2+ egresses round-1 reviews (derivatives of already-approved source) to the same providers under the disclosed multi-round plan; each round's packet hash is recorded in round-N/<seat>.raw and run-metadata.tsv.
- Never record secrets, tokens, cookies, or private environment values.

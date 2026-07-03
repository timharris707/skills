# Run Metadata — v1.13 p4 endorsement pass pr review

Date: 2026-07-02   ·   Rounds: 2   ·   Cross-reading: summaries
Mode: advisory   ·   Sensitivity: redacted   ·   Output: full-handoff
Lens preset: software-architecture
Revises: ~/.advisory-board/runs/v1-13-p4-endorsement-pass-pr-review-2026-07-02   ·   injected: prior verdict digest + source diff (prior source: source-material.txt, sha-verified)

## Seats

| Seat   | Lens | Model requested | Reasoning | Auth | Preflight |
| ------ | ---- | --------------- | --------- | ---- | --------- |
| claude | Architecture & systems | claude-opus-4-8 | max | reachable (smoke-verified; not independently probed) | GO |
| codex  | Implementation & testing | gpt-5.5 | xhigh | reachable (smoke-verified; not independently probed) | GO |

## Source

Access method: single source packet
Source: ~/.advisory-board/v1.13-p4-endorsement-pass-pr-review.md (sha256:e8dc58f7b7096a8e6dac8cc89d4c32205735d8e88477da8cd00762ae186a7314)
Sensitivity & handling: redacted

## Egress approval

- Decision     : APPROVED (hash-bound)
- Content hash : sha256:18a394615170c3d842dafa78e065ae51890feb091baad62ed6fb135e20069c9e
- Timestamp    : 2026-07-02T12:16:09
- Providers    : Anthropic, OpenAI
- Detail       : approved via --yes (bound to the content hash)

## Round 1

2 of 2 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 510.7s | - |
| codex  | ran      | gpt-5.5 | 1 | 166.8s | - |

Tokens as reported by the seat CLIs (if known; capture is best-effort):
- codex: total 168,312 (combined count; the CLI reports no in/out split)

## Round 2

2 of 2 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 274.2s | - |
| codex  | ran      | gpt-5.5 | 1 | 101.2s | - |

Tokens as reported by the seat CLIs (if known; capture is best-effort):
- codex: total 110,487 (combined count; the CLI reports no in/out split)

## Convergence

Stop reason: round-count   ·   Rounds run: 2   ·   Ceiling (--max-rounds): 3   ·   Rounds mode: fixed (2)

| Transition | Seats moved | Considered | Per-seat movement |
| ---------- | ----------- | ---------- | ----------------- |
| 1 → 2 | 2 | 2 | claude ship→caution; codex +23 cites |

Movement is a pure function over each seat's parsed `VERDICT:` token and its concrete citation set (inline-code spans + slash paths) — never its prose (principle #1 / §11). A seat moved if its verdict token shifted or it added a new citation; `auto` stops when board-wide movement falls below the threshold.

## Synthesizer

Seat: claude   ·   Model requested: claude-opus-4-8   ·   Model answered: unknown
Status: ran
Elapsed: 157.73s   ·   Attempts: 1   ·   Packet sha256: e9b5587d2cad9643…
Accepted (passed advisory-board/verdict@2 validation): yes

The synthesizer is a no-lens reasoning seat (§11): briefed only on the final-round reviews + the conductor-extracted VERDICT tokens, never the source. The conductor merges its content fields into an authoritative skeleton (schema/title/date/rounds/board[]) and runs `board_verdict.validate` before writing verdict.json — the human still gates ship/abstain.

## Cost & time (best effort)

- Tokens reported by the seat CLIs: 278,799 across 2 of 4 seat-round(s); the rest reported nothing and are counted as unknown, never guessed.
- Estimated cost of the reported tokens: ~$1.39–$8.36 at list prices dated 2026-07-01 (an ESTIMATE — subscription-backed CLIs may bill nothing per token; unknown/unpriced seat-rounds excluded).
- Wall clock (measured): 13.1 min across 2 round(s) — seats fan out in parallel, so each round costs its slowest seat.

## Notes

- 'Model answered' is what the CLI *reported*; 'unknown' means it reported nothing parseable (never assume the requested model answered).
- Round 2+ egresses round-1 reviews (derivatives of already-approved source) to the same providers under the disclosed multi-round plan; each round's packet hash is recorded in round-N/<seat>.raw and run-metadata.tsv.
- Never record secrets, tokens, cookies, or private environment values.

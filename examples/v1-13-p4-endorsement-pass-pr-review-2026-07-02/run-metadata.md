# Run Metadata — v1.13 p4 endorsement pass pr review

Date: 2026-07-02   ·   Rounds: 2   ·   Cross-reading: summaries
Mode: advisory   ·   Sensitivity: redacted   ·   Output: full-handoff
Lens preset: software-architecture

## Seats

| Seat   | Lens | Model requested | Reasoning | Auth | Preflight |
| ------ | ---- | --------------- | --------- | ---- | --------- |
| claude | Architecture & systems | claude-opus-4-8 | max | reachable (smoke-verified; not independently probed) | GO |
| codex  | Implementation & testing | gpt-5.5 | xhigh | reachable (smoke-verified; not independently probed) | GO |

## Source

Access method: single source packet
Source: ~/.advisory-board/v1.13-p4-endorsement-pass-pr-review.md (sha256:ce0c4ec77f9247554b550903d76efe6542d6efecff804751a588cbac7618cb0d)
Sensitivity & handling: redacted

## Egress approval

- Decision     : APPROVED (hash-bound)
- Content hash : sha256:88ed82ebf1087e9848b403e54e0b53804a2edfb7265a4e20fbc9b18d27acea6b
- Timestamp    : 2026-07-02T11:26:47
- Providers    : Anthropic, OpenAI
- Detail       : approved via --yes (bound to the content hash)

## Round 1

2 of 2 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 684.9s | - |
| codex  | ran      | gpt-5.5 | 1 | 233.3s | - |

Tokens as reported by the seat CLIs (if known; capture is best-effort):
- codex: total 174,442 (combined count; the CLI reports no in/out split)

## Round 2

2 of 2 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 413.1s | - |
| codex  | ran      | gpt-5.5 | 1 | 148.9s | - |

Tokens as reported by the seat CLIs (if known; capture is best-effort):
- codex: total 132,359 (combined count; the CLI reports no in/out split)

## Convergence

Stop reason: round-count   ·   Rounds run: 2   ·   Ceiling (--max-rounds): 3   ·   Rounds mode: fixed (2)

| Transition | Seats moved | Considered | Per-seat movement |
| ---------- | ----------- | ---------- | ----------------- |
| 1 → 2 | 2 | 2 | claude +44 cites; codex +8 cites |

Movement is a pure function over each seat's parsed `VERDICT:` token and its concrete citation set (inline-code spans + slash paths) — never its prose (principle #1 / §11). A seat moved if its verdict token shifted or it added a new citation; `auto` stops when board-wide movement falls below the threshold.

## Synthesizer

Seat: claude   ·   Model requested: claude-opus-4-8   ·   Model answered: unknown
Status: ran
Elapsed: 202.22s   ·   Attempts: 1   ·   Packet sha256: d1ff911c324e804a…
Accepted (passed advisory-board/verdict@2 validation): yes

The synthesizer is a no-lens reasoning seat (§11): briefed only on the final-round reviews + the conductor-extracted VERDICT tokens, never the source. The conductor merges its content fields into an authoritative skeleton (schema/title/date/rounds/board[]) and runs `board_verdict.validate` before writing verdict.json — the human still gates ship/abstain.

## Cost & time (best effort)

- Tokens reported by the seat CLIs: 306,801 across 2 of 4 seat-round(s); the rest reported nothing and are counted as unknown, never guessed.
- Estimated cost of the reported tokens: ~$1.53–$9.20 at list prices dated 2026-07-01 (an ESTIMATE — subscription-backed CLIs may bill nothing per token; unknown/unpriced seat-rounds excluded).
- Wall clock (measured): 18.3 min across 2 round(s) — seats fan out in parallel, so each round costs its slowest seat.

## Notes

- 'Model answered' is what the CLI *reported*; 'unknown' means it reported nothing parseable (never assume the requested model answered).
- Round 2+ egresses round-1 reviews (derivatives of already-approved source) to the same providers under the disclosed multi-round plan; each round's packet hash is recorded in round-N/<seat>.raw and run-metadata.tsv.
- Never record secrets, tokens, cookies, or private environment values.

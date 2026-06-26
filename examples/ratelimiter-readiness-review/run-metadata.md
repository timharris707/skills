# Run Metadata — review packet

Date: 2026-06-25   ·   Rounds: auto   ·   Cross-reading: summaries
Mode: gate   ·   Sensitivity: public   ·   Output: full-handoff
Lens preset: software-architecture

## Seats

| Seat   | Lens | Model requested | Reasoning | Auth | Preflight |
| ------ | ---- | --------------- | --------- | ---- | --------- |
| claude | Architecture & systems | claude-opus-4-8 | xhigh | reachable (smoke-verified; not independently probed) | GO |
| codex  | Implementation & testing | gpt-5.5 | xhigh | unknown (no smoke response) | NO-GO |
| gemini | Product & operations | gemini-3.5-flash | HIGH | reachable (smoke-verified; not independently probed) | GO |

## Source

Access method: single source packet
Source: examples/ratelimiter-readiness-review/source/review-packet.md (sha256:06457237f46bec318a3b6cb24bd63d00a04fcd6d2451ebb8bbb000661252fc57)
Sensitivity & handling: public

## Egress approval

- Decision     : APPROVED (disclosure)
- Content hash : sha256:2ca8c659997d8d3344f6fdd6800706cc76d706492123b210d76cfc1f783f3525
- Timestamp    : 2026-06-25T20:12:51
- Providers    : Anthropic, Google, OpenAI
- Detail       : clearly-public material; proceeded after disclosure

## Round 1

2 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 107.8s | - |
| codex  | dropped  | unknown | 1 | 2.6s | NoOutput |
| gemini | ran      | unknown | 1 | 56.0s | - |

## Round 2

2 of 2 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 88.6s | - |
| gemini | ran      | unknown | 1 | 34.7s | - |

## Round 3

2 of 2 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 72.5s | - |
| gemini | ran      | unknown | 1 | 40.3s | - |

## Convergence

Stop reason: max-rounds   ·   Rounds run: 3   ·   Ceiling (--max-rounds): 3   ·   Rounds mode: auto

| Transition | Seats moved | Considered | Per-seat movement |
| ---------- | ----------- | ---------- | ----------------- |
| 1 → 2 | 2 | 2 | claude +9 cites; gemini +8 cites |
| 2 → 3 | 2 | 2 | claude +3 cites; gemini block→caution |

Movement is a pure function over each seat's parsed `VERDICT:` token and its concrete citation set (inline-code spans + slash paths) — never its prose (principle #1 / §11). A seat moved if its verdict token shifted or it added a new citation; `auto` stops when board-wide movement falls below the threshold.

## Synthesizer

Seat: claude   ·   Model requested: claude-opus-4-8   ·   Model answered: unknown
Status: ran
Elapsed: 52.09s   ·   Attempts: 1   ·   Packet sha256: 575d2bd248de6d1f…
Accepted (passed advisory-board/verdict@2 validation): no
Schema error: schema validation failed: concerns[3].evidence[0]: code evidence needs 'line' or 'symbol'

The synthesizer is a no-lens reasoning seat (§11): briefed only on the final-round reviews + the conductor-extracted VERDICT tokens, never the source. The conductor merges its content fields into an authoritative skeleton (schema/title/date/rounds/board[]) and runs `board_verdict.validate` before writing verdict.json — the human still gates ship/abstain.

## Notes

- 'Model answered' is what the CLI *reported*; 'unknown' means it reported nothing parseable (never assume the requested model answered).
- Round 2+ egresses round-1 reviews (derivatives of already-approved source) to the same providers under the disclosed multi-round plan; each round's packet hash is recorded in round-N/<seat>.raw and run-metadata.tsv.
- Never record secrets, tokens, cookies, or private environment values.
- ⚠ Network NOT isolated for: gemini (no CLI flag removes their web/grounding tools); treat as networked despite gate mode.

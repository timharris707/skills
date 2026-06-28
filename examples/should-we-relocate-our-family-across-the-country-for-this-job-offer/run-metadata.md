# Run Metadata — Should we relocate our family across the country for this job offer?

Date: 2026-06-27   ·   Rounds: 2   ·   Cross-reading: full
Mode: advisory   ·   Sensitivity: public   ·   Output: full-handoff
Lens preset: business-decision

## Seats

| Seat   | Lens | Model requested | Reasoning | Auth | Preflight |
| ------ | ---- | --------------- | --------- | ---- | --------- |
| claude | First principles & economics | claude-opus-4-8 | xhigh | reachable (smoke-verified; not independently probed) | GO |
| codex  | Execution & feasibility | gpt-5.5 | xhigh | reachable (smoke-verified; not independently probed) | GO |
| gemini | Second-order & downside | gemini-3-pro-preview | HIGH | reachable (smoke-verified; not independently probed) | GO |

## Source

Access method: single source packet
Source: examples/should-we-relocate-our-family-across-the-country-for-this-job-offer/decision.md (sha256:bacbbb899846fd2b907bfe4f6094953cad0b181a44944065dc872fa36f353f96)
Sensitivity & handling: public

## Egress approval

- Decision     : APPROVED (disclosure)
- Content hash : sha256:4e41da0b627e9d57c48570a69623d2d72015e0f6eb6821c4ec0c89ec881daf2f
- Timestamp    : 2026-06-27T08:08:16
- Providers    : Anthropic, Google, OpenAI
- Detail       : clearly-public material; proceeded after disclosure

## Round 1

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 162.3s | - |
| codex  | ran      | gpt-5.5 | 1 | 67.4s | - |
| gemini | ran      | unknown | 1 | 36.4s | - |

## Round 2

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 91.6s | - |
| codex  | ran      | gpt-5.5 | 1 | 99.8s | - |
| gemini | ran      | unknown | 1 | 34.8s | - |

## Convergence

Stop reason: round-count   ·   Rounds run: 2   ·   Ceiling (--max-rounds): 3   ·   Rounds mode: fixed (2)

| Transition | Seats moved | Considered | Per-seat movement |
| ---------- | ----------- | ---------- | ----------------- |
| 1 → 2 | 1 | 3 | claude —; codex +4 cites; gemini — |

Movement is a pure function over each seat's parsed `VERDICT:` token and its concrete citation set (inline-code spans + slash paths) — never its prose (principle #1 / §11). A seat moved if its verdict token shifted or it added a new citation; `auto` stops when board-wide movement falls below the threshold.

## Synthesizer

Seat: claude   ·   Model requested: claude-opus-4-8   ·   Model answered: unknown
Status: ran
Elapsed: 85.88s   ·   Attempts: 1   ·   Packet sha256: 364f7426c7f0ca02…
Accepted (passed advisory-board/verdict@2 validation): yes

The synthesizer is a no-lens reasoning seat (§11): briefed only on the final-round reviews + the conductor-extracted VERDICT tokens, never the source. The conductor merges its content fields into an authoritative skeleton (schema/title/date/rounds/board[]) and runs `board_verdict.validate` before writing verdict.json — the human still gates ship/abstain.

## Notes

- 'Model answered' is what the CLI *reported*; 'unknown' means it reported nothing parseable (never assume the requested model answered).
- Round 2+ egresses round-1 reviews (derivatives of already-approved source) to the same providers under the disclosed multi-round plan; each round's packet hash is recorded in round-N/<seat>.raw and run-metadata.tsv.
- Never record secrets, tokens, cookies, or private environment values.

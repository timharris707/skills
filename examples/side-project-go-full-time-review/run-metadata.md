# Run Metadata — Should I go full-time on my side project?

Date: 2026-06-26   ·   Rounds: 2   ·   Cross-reading: summaries
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
Source: /Users/timharris/projects/skills/.claude/worktrees/marketing-refresh/examples/side-project-go-full-time-review/proposal.md (sha256:15ac5d99ef4cd3d42aafd524e6ee3e185ee6b44b980d82e3e65f97d1196d9d2c)
Sensitivity & handling: public

## Egress approval

- Decision     : APPROVED (disclosure)
- Content hash : sha256:b1d8923a075edab1887a2f1d8086d5d63538beb134428370fc37fc0c40b88911
- Timestamp    : 2026-06-26T07:49:20
- Providers    : Anthropic, Google, OpenAI
- Detail       : clearly-public material; proceeded after disclosure

## Round 1

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 127.5s | - |
| codex  | ran      | gpt-5.5 | 1 | 118.0s | - |
| gemini | ran      | unknown | 1 | 37.2s | - |

## Round 2

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 128.3s | - |
| codex  | ran      | gpt-5.5 | 1 | 121.7s | - |
| gemini | ran      | unknown | 1 | 31.9s | - |

## Convergence

Stop reason: round-count   ·   Rounds run: 2   ·   Ceiling (--max-rounds): 3   ·   Rounds mode: fixed (2)

| Transition | Seats moved | Considered | Per-seat movement |
| ---------- | ----------- | ---------- | ----------------- |
| 1 → 2 | 1 | 3 | claude —; codex +6 cites; gemini — |

Movement is a pure function over each seat's parsed `VERDICT:` token and its concrete citation set (inline-code spans + slash paths) — never its prose (principle #1 / §11). A seat moved if its verdict token shifted or it added a new citation; `auto` stops when board-wide movement falls below the threshold.

## Synthesizer

Seat: claude   ·   Model requested: claude-opus-4-8   ·   Model answered: unknown
Status: ran
Elapsed: 57.64s   ·   Attempts: 1   ·   Packet sha256: 171d0d48178e023d…
Accepted (passed advisory-board/verdict@2 validation): yes

The synthesizer is a no-lens reasoning seat (§11): briefed only on the final-round reviews + the conductor-extracted VERDICT tokens, never the source. The conductor merges its content fields into an authoritative skeleton (schema/title/date/rounds/board[]) and runs `board_verdict.validate` before writing verdict.json — the human still gates ship/abstain.

## Notes

- 'Model answered' is what the CLI *reported*; 'unknown' means it reported nothing parseable (never assume the requested model answered).
- Round 2+ egresses round-1 reviews (derivatives of already-approved source) to the same providers under the disclosed multi-round plan.
- Never record secrets, tokens, cookies, or private environment values.

# Run Metadata — v1.13 fixit revision artifact design brief

Date: 2026-07-02   ·   Rounds: 2   ·   Cross-reading: summaries
Mode: advisory   ·   Sensitivity: redacted   ·   Output: full-handoff
Lens preset: software-architecture

## Seats

| Seat   | Lens | Model requested | Reasoning | Auth | Preflight |
| ------ | ---- | --------------- | --------- | ---- | --------- |
| claude | Architecture & systems | claude-opus-4-8 | max | reachable (smoke-verified; not independently probed) | GO |
| codex  | Implementation & testing | gpt-5.5 | xhigh | reachable (smoke-verified; not independently probed) | GO |
| gemini | Product & operations | gemini-3.5-flash | HIGH | unknown (smoke timed out) | NO-GO |

## Source

Access method: single source packet
Source: examples/dogfood-fixit-design-roundtable/design-brief.md (sha256:db1db9c0d38bf9d906ace77f019270e5ecb8ace39334513e263ca51153360044)
Sensitivity & handling: redacted

## Egress approval

- Decision     : APPROVED (hash-bound)
- Content hash : sha256:40f3be4a4eff26a3e07d256c4975f9d444228839d52984583ddc1ead7c27759b
- Timestamp    : 2026-07-02T03:45:11
- Providers    : Anthropic, Google, OpenAI
- Detail       : approved via --yes (bound to the content hash)

## Round 1

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 554.0s | - |
| codex  | ran      | gpt-5.5 | 1 | 208.4s | - |
| gemini | ran      | unknown | 1 | 225.2s | - |

Tokens as reported by the seat CLIs (if known; capture is best-effort):
- codex: total 133,581 (combined count; the CLI reports no in/out split)

## Round 2

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 323.6s | - |
| codex  | ran      | gpt-5.5 | 1 | 229.2s | - |
| gemini | ran      | unknown | 1 | 104.3s | - |

Tokens as reported by the seat CLIs (if known; capture is best-effort):
- codex: total 210,265 (combined count; the CLI reports no in/out split)

## Convergence

Stop reason: round-count   ·   Rounds run: 2   ·   Ceiling (--max-rounds): 3   ·   Rounds mode: fixed (2)

| Transition | Seats moved | Considered | Per-seat movement |
| ---------- | ----------- | ---------- | ----------------- |
| 1 → 2 | 3 | 3 | claude +42 cites; codex +6 cites; gemini +19 cites |

Movement is a pure function over each seat's parsed `VERDICT:` token and its concrete citation set (inline-code spans + slash paths) — never its prose (principle #1 / §11). A seat moved if its verdict token shifted or it added a new citation; `auto` stops when board-wide movement falls below the threshold.

## Synthesizer

Seat: claude   ·   Model requested: claude-opus-4-8   ·   Model answered: unknown
Status: ran
Elapsed: 208.17s   ·   Attempts: 1   ·   Packet sha256: b3cd02dec4e299b2…
Accepted (passed advisory-board/verdict@2 validation): yes

The synthesizer is a no-lens reasoning seat (§11): briefed only on the final-round reviews + the conductor-extracted VERDICT tokens, never the source. The conductor merges its content fields into an authoritative skeleton (schema/title/date/rounds/board[]) and runs `board_verdict.validate` before writing verdict.json — the human still gates ship/abstain.

## Cost & time (best effort)

- Tokens reported by the seat CLIs: 343,846 across 2 of 6 seat-round(s); the rest reported nothing and are counted as unknown, never guessed.
- Estimated cost of the reported tokens: ~$1.72–$10.32 at list prices dated 2026-07-01 (an ESTIMATE — subscription-backed CLIs may bill nothing per token; unknown/unpriced seat-rounds excluded).
- Wall clock (measured): 14.6 min across 2 round(s) — seats fan out in parallel, so each round costs its slowest seat.

## Notes

- 'Model answered' is what the CLI *reported*; 'unknown' means it reported nothing parseable (never assume the requested model answered).
- Round 2+ egresses round-1 reviews (derivatives of already-approved source) to the same providers under the disclosed multi-round plan; each round's packet hash is recorded in round-N/<seat>.raw and run-metadata.tsv.
- Never record secrets, tokens, cookies, or private environment values.

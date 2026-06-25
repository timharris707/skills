# Run Metadata — Payments API idempotency keys

Date: 2026-06-25   ·   Rounds: 2   ·   Cross-reading: full
Mode: gate   ·   Sensitivity: public   ·   Output: full-handoff
Lens preset: software-architecture

## Seats

| Seat   | Lens | Model requested | Reasoning | Auth | Preflight |
| ------ | ---- | --------------- | --------- | ---- | --------- |
| claude | Architecture & systems | claude-opus-4-8 | xhigh | reachable (smoke-verified; not independently probed) | GO |
| codex  | Implementation & testing | gpt-5.5 | xhigh | reachable (smoke-verified; not independently probed) | GO |
| gemini | Product & operations | gemini-3.5-flash | HIGH | reachable (smoke-verified; not independently probed) | GO |

## Source

Access method: single source packet
Source: examples/payments-idempotency-review/plan.md (sha256:4a6a493f42d27563a064af44daf996513122c04df0ab76cb1a3d04e0003da272)
Sensitivity & handling: public

## Egress approval

- Decision     : APPROVED (disclosure)
- Content hash : sha256:56d6bf7af7a3ae9d5c7da1149a2f54a1001518a917a6fd9e41f562b2db37a607
- Timestamp    : 2026-06-25T12:16:39
- Providers    : Anthropic, Google, OpenAI
- Detail       : clearly-public material; proceeded after disclosure

## Round 1

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 82.3s | - |
| codex  | ran      | gpt-5.5 | 1 | 33.8s | - |
| gemini | ran      | unknown | 1 | 48.2s | - |

## Round 2

3 of 3 seats produced a usable review.

| Seat   | Status   | Model answered | Attempts | Elapsed | Failure |
| ------ | -------- | -------------- | -------- | ------- | ------- |
| claude | ran      | unknown | 1 | 81.9s | - |
| codex  | ran      | gpt-5.5 | 1 | 33.5s | - |
| gemini | ran      | unknown | 1 | 56.0s | - |

## Notes

- 'Model answered' is what the CLI *reported*; 'unknown' means it reported nothing parseable (never assume the requested model answered).
- Round 2+ egresses round-1 reviews (derivatives of already-approved source) to the same providers under the disclosed multi-round plan; each round's packet hash is recorded in run-metadata.tsv (and each seat's round-N/<seat>.raw black-box record in a full run dir).
- Never record secrets, tokens, cookies, or private environment values.
- ⚠ Network NOT isolated for: gemini (no CLI flag removes their web/grounding tools); treat as networked despite gate mode.

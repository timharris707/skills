# Advisory Board — Final Consensus
Plan: Add idempotency keys to the payments API (Idempotency-Key on POST /charges; key->response in Redis 24h; optional; enable for all clients at once next sprint).
Board: Claude (architecture) · Codex/gpt-5.5 (impl/testing) · Gemini (product/ops). Rounds: 2.

## Verdict: DO NOT SHIP YET — unanimous
Round 1 was 2x "do not ship" + 1x "ship with changes" (Codex). In Round 2, after reading the others, **Codex moved to "do not ship yet."** No seat dissents from the verdict.

## Consensus blockers (must fix before ship)
1. Atomic dedup — SET NX claim with an in-progress sentinel that completes only after a durable charge result. Without it, two concurrent same-key requests both miss the cache and double-charge — the exact failure the feature exists to prevent.
2. Request-fingerprint binding — bind key -> hash(request); a reused key with a different payload returns 409/422 conflict, never a replayed/unrelated charge.
3. Redis failure policy + kill switch — Redis is now in the critical payment path. Decide fail-open (lost idempotency) vs fail-closed (outage) explicitly, with a kill switch.
4. Never cache transient failures — do not store 5xx/timeouts as the authoritative response; a cached 500 poisons the key and blocks legitimate retries for 24h.
5. Replay fidelity — replay status code, body, and headers consistently.
6. Phased rollout + observability — dark-launch then cohort/percentage ramp; alert on Redis latency and cache-hit rate. Replace the big-bang enablement.

## Hard dissent (preserved)
- Codex: "all clients at once" is not *inherently* impossible given optional keys + backwards-compatible server behavior — but only with a kill switch, metrics, and staged enablement by route/client cohort. (The rollout *aggressiveness* is debatable; the correctness blockers above are not.)

## What the board couldn't verify
- Reviewed the written plan, not the code. If the implementation already does an atomic `SET NX` claim and request-fingerprint binding, blockers 1–2 may already be satisfied — re-check against the actual handler before treating them as gaps.
- The downstream processor's own idempotency guarantees are unknown. If it already dedupes on a client reference, the double-charge blast radius is smaller than assumed; confirm before sizing the fix.
- Retry behavior after the 24h TTL is unverified — whether a legitimate retry after expiry double-charges depends on real client retry/settlement windows no seat could see. Verify against actual client behavior; it could add or remove a blocker.

## Open questions
- 24h TTL vs client retry/settlement windows — does a legitimate retry after expiry double-charge?
- Alignment with the downstream payment processor's own idempotency guarantees.
- Dispute/audit retention needs vs the 24h window.

## Next actions
Spec the atomic state machine + fingerprint; decide Redis failure policy + kill switch; enumerate non-cacheable status codes; design the phased rollout + dashboards; then re-review.

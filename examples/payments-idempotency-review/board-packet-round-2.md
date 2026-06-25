# Board Packet — Round 1 findings
Plan: add idempotency keys to a payments API (Idempotency-Key header on POST /charges; key->response in Redis 24h TTL; keys optional; enable for all clients at once next sprint).

## Claude (architecture) — DO NOT SHIP YET
- In-flight duplicates: store-on-completion races; two same-key requests both miss cache and double-charge. Need atomic SET NX reserve + in-progress sentinel.
- Key collision: caching on header alone ignores body; bind key to request fingerprint, 422 on mismatch.
- Big-bang rollout; define Redis-down behavior (fail-open = lost idempotency; fail-closed = outage).

## Gemini (product/ops) — DO NOT SHIP YET
- Operational blast radius of all-at-once rollout on a core payments path.
- Concurrency double-charge: no locking strategy.
- Undefined Redis failure modes. Insist: phased rollout + alerting on Redis latency/cache-hit.

## Codex (impl/testing) — SHIP WITH CHANGES
- "Cache the response" underspecified: replay status/body/headers; do not cache transient 5xx as authoritative.
- No request fingerprinting: same key + different payload must conflict, not replay.
- Race handling: atomic claim -> in-progress -> completed. Define in-flight retry behavior.

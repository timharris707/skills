# Advisory Board — Final Consensus
Payments API idempotency keys
Board: Claude (architecture/claude-opus-4-8) · Codex (implementation/testing/gpt-5.5) · Gemini (product/ops/gemini-3.5-flash). Rounds: 2.

## Verdict: DO NOT SHIP YET — unanimous (high confidence)

## Consensus blockers (must fix before ship)
1. Concurrency window → double charge (no atomic reserve-before-charge) — Storing the response only after the charge completes leaves a race: two same-key requests arriving concurrently (retry storm, double-click, client-timeout-and-retry) both miss the cache and both charge. Atomically reserve the key (durable INSERT … ON CONFLICT, or SET NX) BEFORE the side effect; the loser blocks-and-polls for the original result. All three seats raised this independently.
   - evidence: plan.md — “on a duplicate key it returns the cached response” (source) — verified
   - evidence: judgment — the plan specifies no reservation/lock step, so the concurrency window is unhandled — inferred from the absence, not stated
2. No key→payload binding (same key, different body served stale) — Nothing binds the key to the request. A client reusing a key with a different amount/recipient/currency gets the prior cached response — a silent under-charge or a replay of an unrelated charge. Bind the key to a hash of the canonicalized request body; same-key/different-payload must return 409/422, never a cached success.
   - evidence: plan.md — “on a duplicate key it returns the cached response” (source) — verified
3. No per-tenant scoping → cross-tenant response leak — Keys are client-supplied strings with no stated namespace. Enabling a single shared keyspace for all clients means Client B sending a key Client A already used receives Client A's cached charge response — a cross-tenant data leak. The lookup key must be (account_id, idempotency_key), never the raw header.
   - evidence: plan.md — “Clients may send an Idempotency-Key header on POST /charges” (source) — verified
   - evidence: plan.md — “We will enable it for all clients at once next sprint” (source) — verified
4. Redis as sole system of record → non-durable idempotency — Redis is not durable by default; failover, restart without AOF, or maxmemory eviction can drop idempotency records early, after which a retry re-charges. The durable transactional DB must be the system of record; Redis, if used, is a fast-path cache in front of it. (Gemini's noeviction does not make Redis durable — it trades the double-charge for a write-availability cliff.)
   - evidence: plan.md — “The server stores the key-to-response mapping in Redis wi...” (source) — verified
5. Indeterminate downstream outcome + non-idempotent processor — API-layer idempotency cannot make a non-idempotent money movement exactly-once. A processor timeout leaves the charge state unknown; on retry you must neither replay a fabricated success nor blind-recharge — you must propagate the key to the processor and reconcile by it. Claude elevated this above the concurrency window as the requirement the plan is furthest from.
   - evidence: judgment — the plan is silent on the downstream payment processor and on partial-failure/reconciliation — a gap inferred from omission, with no source line to quote
6. Caching of transient / indeterminate failures — An unqualified 'cached response' pins every retry to a cached 5xx/timeout for 24h, turning a brief downstream glitch into a prolonged checkout outage — and caching an indeterminate result as terminal is unsafe. Cache only KNOWN-terminal outcomes; never cache in-flight or indeterminate-failure states (deterministic pre-side-effect validation errors are a documented exception).
   - evidence: plan.md — “on a duplicate key it returns the cached response” (source) — verified
7. Big-bang rollout on the money path (no shadow/canary/kill switch) — Flipping a correctness-critical charge-path interceptor on for everyone at once is volatile: existing clients sending static/placeholder keys would have their checkout funnels break on enforcement. Ship staged — shadow → canary → percentage ramp behind a kill switch — with hit/miss/payload-mismatch/conflict/Redis-latency metrics wired up before the canary.
   - evidence: plan.md — “We will enable it for all clients at once next sprint” (source) — verified

## Hard dissent (preserved)
- Gemini: Returning a raw 409 to a duplicate in-flight request is dangerous for naive client SDKs: on a client-side timeout retry the SDK shows 'Payment Failed', the consumer retries on another card, and the original charge then succeeds. Prefer block-and-poll (≈3–5s) or a 202 + Retry-After, plus a published client retry-integration guide. (Claude and Codex favor 409 for the in-flight loser.)
- Claude: Dissents from Gemini's resiliency mechanics — fail-closed (503) on Redis-down and noeviction — and from any short-TTL auto-expiring lock as the primary guarantee: a lock that expires while the side effect is still in flight re-opens the exact double-charge it exists to prevent. These problems largely dissolve once the durable store, not Redis, holds the invariant; then a Redis outage is a fast-path degradation, not a payments outage.

## What the board couldn't verify
- The board reviewed the written plan, not the implementation. If the actual handler already does an atomic reserve + request-fingerprint binding, the concurrency and payload-binding blockers may already be satisfied — re-check against the code before treating them as gaps.
- The downstream processor's own idempotency support is unknown. If it already dedupes on a client reference, the double-charge blast radius is smaller than assumed.
- Retry behavior after the 24h TTL is unverified — whether a legitimate post-expiry retry double-charges depends on real client retry/settlement windows no seat could observe.

## Open questions
- Does the downstream payment processor support idempotency keys, and do we propagate the client's key to it?
- What is the current baseline double-charge rate (to size rollout gates and prove the change works)?
- Redis durability/eviction/failover and memory-sizing config (volume × avg response size × buffer)?
- Do existing clients already send static, low-entropy, or reused Idempotency-Key headers that enforcement would break?
- Client SDK default timeouts vs the processor's worst-case latency (mismatch drives duplicate storms).
- PCI/PII compliance for caching full charge responses (encryption-at-rest, retention).

## Next actions
- Write the contract first: scope (account_id, key); key format/length; what 24h expiry means to clients; same-key/different-payload behavior; Redis-down policy; which outcomes are cached.
- Add a durable idempotency record in the primary DB — unique on (account_id, endpoint, key) — storing request fingerprint, state (in_flight|completed|failed_terminal), and the response.
- Reserve-then-process: atomic durable insert of in_flight BEFORE charging; loser polls for the terminal result or returns a deterministic conflict.
- Propagate the key to the processor; on an indeterminate outcome, reconcile by the key — never finalize as success or re-charge blindly.
- Wire observability + a reconciliation job + a standing duplicate-charge-per-key detector before any enforcement.
- Roll out shadow → canary → ramp behind a kill switch, then re-review.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

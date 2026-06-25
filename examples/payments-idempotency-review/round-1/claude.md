# Advisory Board Review — Idempotency Keys for Payments API
*Claude seat · Architecture & systems*

## 1. Verdict

**REVISE — do not execute as specified. Confidence: high.**

The intent is correct and the storage primitive (keyed response cache with TTL) is industry-standard. But as written the design does not actually guarantee idempotency on the money path: it has an unhandled concurrency window, no key→payload binding, no per-client scoping, and relies on a non-durable store as the source of truth. Each of these can produce a double charge or a cross-tenant data leak — the exact failures the feature exists to prevent.

**What would change the verdict to APPROVE:** a revised design that (a) atomically *reserves* the key before processing, (b) binds the key to a request fingerprint, (c) scopes keys per account/API credential, (d) treats a durable store (not Redis alone) as the system of record, (e) defines partial-failure and Redis-down behavior, and (f) replaces the big-bang rollout with a staged one.

## 2. Strongest objections

**A. Concurrency window → double charge (critical).** "stores the key-to-response mapping in Redis ... on a duplicate key it returns the cached response." This only protects against duplicates that arrive *after* the first request completes and writes its response. Two requests with the same key arriving concurrently (the common retry-storm / double-click / client-timeout-and-retry case) both miss the cache, both execute the charge. The plan has no reservation/lock step. You must atomically claim the key *before* doing the work (e.g. `SET key <in-flight> NX`), and the loser must block-and-poll or return `409 Conflict`.

**B. No key→request binding (critical).** Nothing stops a client from reusing a key with a *different* body (different amount, currency, recipient). The current rule "return the cached response" would silently swallow the second, semantically-different charge — or, depending on implementation, return a response for the wrong operation. The record must store a hash of the canonical request; a same-key/different-payload request must be rejected (`422`/`409`), not served from cache.

**C. Keys not scoped per client → cross-tenant leak (critical).** Keys are client-supplied strings. "enable it for all clients at once" with a single shared keyspace means Client B sending a key Client A already used gets Client A's cached charge response back — another tenant's data, and confusion about whether a charge occurred. Keys must be namespaced by account / API credential: the lookup key is `(account_id, idempotency_key)`, never the raw header.

**D. Redis as system of record for money (high).** Redis is not durable by default. Failover, restart without AOF, or `maxmemory` eviction can drop idempotency records early — after which a retry re-charges. For a payments correctness guarantee, the durable store (your transactional DB) should be the source of truth; Redis, if used, is a fast-path cache in front of it. At minimum: AOF on, replication, and an eviction policy that cannot evict these keys.

**E. Atomicity of side effect + record (high).** The response is cached *after* the charge succeeds. A crash between "money moved at the processor" and "record written" loses the key → next retry double-charges. The idempotency key must be propagated *to the downstream processor* so the actual money movement dedupes there too; API-layer idempotency alone cannot make a non-idempotent downstream call exactly-once.

**F. Caching of failures (medium).** "returns the cached response" — does this include errors? Caching a transient `500` pins every retry to that `500` forever, even if the charge state is actually unknown or recoverable. You must distinguish *completed* (cache and replay) from *in-flight* and *failed-indeterminate* (do not cache a terminal failure; allow re-processing with the same key).

**G. Big-bang rollout on the money path (medium).** "enable it for all clients at once next sprint." A correctness-critical change to the charge path should ship staged: shadow/dual-write, then canary, then percentage ramp, watching double-charge and conflict metrics — not flipped globally in one step.

## 3. Recommended execution sequence

1. **Specify the contract first** (write it down before code): key scope = `(account_id, key)`; max key length and charset; retention window = 24h and what expiry *means* to clients; behavior for same-key/different-payload; behavior when Redis is unavailable (fail-open vs fail-closed); which response statuses are cached.
2. **Schema**: durable idempotency record `{account_id, key, request_fingerprint, status(in_flight|completed|failed), response_blob, created_at, expires_at}` with a unique constraint on `(account_id, key)`.
3. **Reserve-then-process**: atomic insert/`SETNX` of an `in_flight` record *before* charging; lose → poll/return 409. This is the core correctness step.
4. **Propagate the key downstream** to the payment processor so money movement is itself idempotent.
5. **Finalize**: write `completed` + response transactionally with (or immediately tied to) the charge result; on indeterminate failure leave it retryable.
6. **Observability**: metrics for hit rate, in-flight conflicts, fingerprint-mismatch rejections, and a reconciliation job that detects duplicate charges per key.
7. **Rollout**: shadow → canary → ramp, with a kill switch.

Note steps 3–5 are the load-bearing ones; the original plan effectively jumps to a simplified version of step 5 only.

## 4. Invariants and guardrails

- **I1 — Exactly-once effect:** for a given `(account_id, key)` within the retention window, at most one charge side effect occurs.
- **I2 — Stable mapping:** a key maps to exactly one request fingerprint; a conflicting payload is rejected, never served stale.
- **I3 — Concurrency safety:** concurrent same-key requests → at most one executes the side effect; others wait or get a deterministic conflict.
- **I4 — Tenant isolation:** a cached response is only ever returned to the same account that created the key.
- **I5 — Only deterministic outcomes are replayed:** in-flight and indeterminate failures are never cached as terminal.
- **I6 — Durability:** an acknowledged charge implies a durable idempotency record (no record loss that re-opens the double-charge window).
- Guardrails: input validation on key length/charset; explicit Redis-down policy; double-charge detector/alert; documented client-facing semantics for 409 and for expiry.

## 5. Risks, stale assumptions, missing evidence

- **Assumption that "store mapping + return cached" is sufficient** — it omits the reserve step; this is the central gap.
- **Assumption that 24h TTL fits client retry behavior** — undefended. Batch/offline retries may exceed it; after expiry, replays silently re-charge. 24h is a reasonable default (matches common provider practice) but must be a stated contract, not an implicit TTL.
- **Assumption Redis is durable enough** — not established; eviction/failover behavior unspecified.
- **PCI/PII**: caching full charge responses may persist sensitive data in Redis — storage, encryption, and TTL need a compliance check. Missing from the plan.
- **Missing evidence**: no load/concurrency estimate, no current double-charge incident rate (the baseline this is meant to improve), no statement of downstream processor's own idempotency capability, no rollback/kill-switch plan.

## 6. Concrete evidence from the source material

- "The server stores the key-to-response mapping in Redis with a 24h TTL; on a duplicate key it returns the cached response." → store-after-complete with no reservation = objection **A** (concurrency window) and **E** (atomicity); "cached response" unqualified = objection **F** (caching failures).
- "Clients may send an Idempotency-Key header on POST /charges." → no per-client scoping stated = objection **C** (cross-tenant); no payload-binding stated = objection **B**.
- "Redis with a 24h TTL" → durability/eviction/expiry concerns = objections **D** and the TTL-contract risk in §5.
- "Keys are optional." → feature gives zero protection to non-adopting clients; acceptable as transitional, but means it does not reduce duplicate charges until clients adopt — state this expectation.
- "We will enable it for all clients at once next sprint." → big-bang on the money path = objection **G**.

## 7. What I'd ask the other board seats to challenge

- **Reliability/SRE seat:** When Redis is unavailable, do we fail open (risk double charge) or fail closed (reject charges)? Is the durability story (AOF, replication, no-evict) real, or should the DB be the source of truth?
- **API/product seat:** What does key expiry mean to clients, and is 24h the right window? What's the documented behavior for same-key/different-body and for the 409 conflict path?
- **Security/compliance seat:** Are we storing card/PII in cached responses, and does that pass PCI? Are client-supplied keys validated and namespaced to prevent enumeration or cross-tenant collisions?
- **Data/analytics seat:** What's the *current* double-charge rate, so we can prove this change works and size the rollout gates?
- **Downstream-payments seat:** Does the processor accept and honor an idempotency key itself? If not, API-layer idempotency cannot deliver exactly-once on the actual money movement.

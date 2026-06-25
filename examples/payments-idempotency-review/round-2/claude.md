# Advisory Board Review — Idempotency Keys for Payments API — Round 2
*Claude seat · Architecture & systems · cross-read of codex, gemini*

## 1. Updated verdict

**REVISE — do not execute as specified. Confidence: high.** (Unchanged in direction; sharpened in substance.)

All three seats independently converged on the same five load-bearing defects — concurrency window, no key→payload binding, no per-tenant scoping, transient-error caching, big-bang rollout — plus durability concerns. Convergence across three independent reviews with no seat defending the original raises my confidence that these are real, not stylistic.

**What would change the verdict to APPROVE:** a revised design where (a) the key is atomically *reserved* in a **durable** store before the charge runs, (b) the reservation only transitions on a *known terminal outcome* (with explicit handling of the processor-timeout / unknown-state case via reconciliation, not blind retry or blind success-replay), (c) keys are scoped to `(account_id, key)` and bound to a canonical request fingerprint, and (d) rollout is staged behind a kill switch.

## 2. Where I changed my mind / where I still dissent

**Changed / refined:**
- **I now treat the "unknown downstream state" case as the single hardest requirement, above the concurrency window.** In round 1 I folded it into objection E (atomicity). Reading codex ("durable outbox/recovery path") and gemini's lock model crystallized it: the genuinely dangerous state isn't the duplicate that races — it's the charge whose processor result is *indeterminate* (timeout/network drop). On retry you must neither blind-replay a cached success nor blind-recharge; you must reconcile against the processor by the same key. This is the requirement the original plan is furthest from.

**Still dissent — naming the seat and the exact reason:**
- **Against gemini, on "fail-closed (503) when Redis is unavailable" + Redis `noeviction` as the resiliency story.** Both prescriptions are artifacts of treating Redis as the system of record. `noeviction` does not make Redis durable — it converts the eviction-double-charge risk into a *write-failure availability cliff*: once `maxmemory` is hit, key reservation fails and you can't create charges at all. And "fail-closed on Redis down" means an idempotency-cache outage takes down the entire money path. Both problems mostly *dissolve* if you accept the durable-store-as-source-of-truth design (my objection D, codex's points 2 & 5): then Redis-down is a fast-path degradation, not a correctness or availability emergency. So I dissent from gemini's specific resiliency mechanics while agreeing with gemini's diagnosis. The disagreement is *which layer holds the invariant*, and it materially changes the operational design.
- **Against gemini's 60s in-flight lock TTL (and any auto-expiring lock as the primary mechanism).** If the charge takes longer than the lock TTL — slow processor, GC pause — the lock expires *while the side effect is still in flight*, a duplicate acquires it, and you double-charge: the exact failure the lock exists to prevent. A short-TTL Redis lock is acceptable as a *liveness* optimization but must not be the thing the exactly-once guarantee rests on. The durable reservation record should transition only on terminal outcome, not silently expire into a re-charge window.

**No dissent from codex.** codex's seven-step sequence and my round-1 sequence are the same design; I'd merge them.

## 3. Strongest remaining objections

In priority order:

- **A. Indeterminate downstream outcome (critical, under-addressed by all three seats).** Processor timeout leaves the reservation `in_flight` with money state *unknown*. Required behavior: on the retry, query the processor by the propagated idempotency key and reconcile; never cache-replay a fabricated success, never blind-recharge. API-layer idempotency cannot deliver exactly-once unless the key reaches the money movement itself.
- **B. Concurrency window → double charge (critical).** No reserve-before-process step. Atomic claim (`INSERT ... ON CONFLICT` durable, or `SET NX`) before charging; loser blocks-and-polls for the original result, returning 409 *only* for payload mismatch (see C), not for an honest retry.
- **C. No key→payload binding (critical).** Same key + different body must be rejected (`422`/`409`), not served stale. Fingerprint over a *canonicalized* body (stable field ordering; exclude volatile fields like client timestamps).
- **D. No per-tenant scoping → cross-tenant leak (critical).** Lookup key is `(account_id, key)`, never the raw client-supplied header.
- **E. Durability / source of truth (high).** Redis alone is non-durable; failover/restart/eviction drops records and re-opens the double-charge window. Durable store is the system of record; Redis is the cache.
- **F. Caching of failures (medium, with a nuance the seats split on).** gemini says "never cache 5xx" — agreed for indeterminate/transient errors. But *do* cache deterministic, pre-side-effect terminal errors (e.g. a `422` validation failure), or retries of a malformed request slip through inconsistently. The discriminator is not the status class — it's whether the side-effect's terminal state is *known*.
- **G. Big-bang rollout (medium).** Shadow → canary → ramp, kill switch, with the `idempotency.payload.mismatch` / `lock.conflict` / `redis.error` metrics gemini listed wired up *before* the canary.

## 4. Recommended execution sequence

1. **Contract first (written):** scope `(account_id, key)`; key length/charset limits; TTL=24h and what expiry *means* to clients (post-expiry replays re-charge — state it); same-key/different-payload → deterministic conflict; Redis-down policy; which outcomes are cached.
2. **Durable schema:** `{account_id, key, request_fingerprint, status(in_flight|completed|failed_terminal), response_blob, created_at, expires_at}`, unique constraint on `(account_id, key)`.
3. **Reserve-then-process:** atomic durable insert of `in_flight` *before* charging; loser polls for the terminal result or, on fingerprint mismatch, returns conflict.
4. **Propagate the key to the processor** so money movement dedupes at the source.
5. **Finalize on terminal outcome only;** on indeterminate processor result, run a **reconciliation/recovery path** (query processor by key) — do not finalize as success or re-charge blindly.
6. **Observability + reconciliation job:** hit rate, in-flight conflicts, fingerprint mismatches, and a standing duplicate-charge-per-key detector/alert.
7. **Rollout:** shadow → canary → ramp, kill switch.

Steps 3–5 are load-bearing; the original plan jumps to a simplified step-5-only.

## 5. Invariants and guardrails

- **I1 — Exactly-once effect:** for `(account_id, key)` within retention, at most one charge side effect.
- **I2 — Stable mapping:** a key binds to one fingerprint; conflicting payload rejected, never served stale.
- **I3 — Concurrency safety:** concurrent same-key → at most one executes; others wait or get deterministic conflict; the reservation must not auto-expire into a re-charge window while the side effect is in flight.
- **I4 — Tenant isolation:** cached response returned only to the account that created the key.
- **I5 — Only known-terminal outcomes are replayed:** in-flight and indeterminate-failure states are never cached as terminal; indeterminate states route to reconciliation.
- **I6 — Durability:** an acknowledged charge implies a durable idempotency record.
- Guardrails: key length/charset validation; explicit (and DB-backed, not Redis-dependent) availability story; reconciliation against processor by key; documented client semantics for conflict and for expiry.

## 6. Risks, stale assumptions, missing evidence

- **Stale assumption "store mapping + return cached" is sufficient** — omits both the reserve step and the reconciliation step. Central gap, all seats agree.
- **Stale assumption Redis is durable / `noeviction` fixes it** — it does not; it trades silent double-charge for a write-availability cliff. Resolve by moving the invariant to the durable store.
- **Stale assumption a short lock TTL is safe** — false if charge latency can exceed it.
- **Missing evidence (carried from round 1, still open):** current double-charge baseline rate (to size gates and prove the change works); downstream processor's own idempotency support; Redis durability/eviction/failover config; Redis memory sizing — gemini's `volume × (avg response size) × buffer` calc is the right ask; PCI/PII exposure from caching full charge responses (storage, encryption-at-rest, TTL compliance); compatibility check for clients already sending `Idempotency-Key`.
- **New risk surfaced by cross-reading:** the seats disagree on Redis-down behavior (gemini: fail-closed; me: degrade-to-DB). This disagreement must be *resolved and documented*, not left to the implementer — it determines whether an idempotency-store outage is a degradation or a payments outage.

## 7. Concrete evidence (quoted)

- *"The server stores the key-to-response mapping in Redis with a 24h TTL; on a duplicate key it returns the cached response."* → store-after-complete, no reservation = objections A/B; "cached response" unqualified = objection F; Redis-as-record = objection E.
- *"Clients may send an Idempotency-Key header on POST /charges."* → no scoping stated = objection D; no payload binding stated = objection C.
- *"Keys are optional."* → zero protection until clients adopt; acceptable as transitional, but state that it does not reduce duplicate charges on its own.
- *"We will enable it for all clients at once next sprint."* → big-bang on the money path = objection G.

**Bottom line:** Three independent reviews converged with no defense of the original; the design as written can produce the exact double-charge and cross-tenant-leak failures it exists to prevent. REVISE. My one sharpening over round 1 and over my co-reviewers: the hardest case is not the racing duplicate but the charge whose processor outcome is *unknown* — get reconciliation and durable reservation right, and gemini's fail-closed/noeviction mechanics become unnecessary.

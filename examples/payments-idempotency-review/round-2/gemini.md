# Advisory Board Review (Round 2) · Gemini Seat
**Role Focus:** Product & Operations — rollout, latency, observability, evaluation, and user-workflow risk

---

## 1. Updated Verdict

* **Verdict:** **REVISE — DO NOT EXECUTE AS SPECIFIED**
* **Confidence Level:** **High**
* **One line on what would change it:** A revised plan replacing the big-bang rollout with a phased shadow-then-canary deployment, establishing concrete service level objectives (SLOs) for Redis latency overhead on the money path, addressing client-side timeout mismatches, and providing a durable database-backed audit trail for support teams.

---

## 2. Where We Changed Our Mind & Where We Still Dissent

### Where We Changed Our Mind (Refining Our Round-1 Stance)
* **Against Our Own Round-1 "Fail-Closed" Recommendation on Redis Outages:** 
  In Round 1, we advocated that if Redis goes down, the API should fail-closed (reject payments with a `503 Service Unavailable`) to prevent double charges. 
  * *Reconsideration:* Looking at this from a **Product & User-Workflow Risk** perspective, failing closed on a cache infrastructure outage would completely halt credit card processing, devastating merchant conversion rates. We now align with **Claude** and **Codex** that Redis must not be the sole system of record. Instead of a blunt fail-closed posture, the primary transactional database (SQL/NoSQL) must act as the ultimate source of truth. If Redis is down, the system must fallback to checking the primary database for an idempotency record. If both are down, only then do we fail-closed with a high-severity SRE alert.
* **Storage Optimization (Redis Memory Management):** 
  We initially assumed caching full response bodies in Redis was acceptable. However, from an operational efficiency standpoint, storing verbose JSON responses for high-volume transactions in RAM is expensive and risks eviction. We now recommend **storing only the `charge_id` and the request payload hash in Redis**. On a cache hit, the server can retrieve the full response from the primary database. This drastically reduces Redis memory usage and keeps RAM footprint minimal.

### Where We Still Dissent (Challenging the Other Seats)
* **Dissent with Claude & Codex on Concurrency Resolution (`409 Conflict` vs. User-Workflow Risk):** 
  Both Claude and our previous review suggest returning an immediate `409 Conflict` when a duplicate request arrives while the first is still processing. 
  * *Reason for Dissent:* From a user-experience standpoint, returning a raw `409` to naive client integrations during a client-side timeout retry is highly dangerous. If a client SDK receives a `409`, the client app will likely display "Payment Failed" to the consumer. The consumer might then try another card or click purchase again, while the original payment actually succeeds moments later. 
  * *Resolution:* For concurrent duplicate requests, the server should **block-and-poll** (up to a brief threshold, e.g., 3-5 seconds) waiting for the active process to finish, or return a specialized `202 Accepted` status with a `Retry-After` header. We must provide a standardized Client Retry Integration Guide.
* **Dissent with the "Optional Keys" Assumption:** 
  The original proposal and Codex treat "optional keys" as a permanent API state. 
  * *Reason for Dissent:* Making keys permanently optional means the clients who are most prone to buggy retry behavior will never adopt them, failing to solve the core double-charge problem. We must mandate a product roadmap where `Idempotency-Key` is initially optional but transitions to **mandatory** for all high-volume integrations and all new API versions after a defined migration window.

---

## 3. Strongest Remaining Objections (Product & Operations)

1. **Blind "Big-Bang" Rollout of Payment Middleware:** Enabling this globally next sprint is highly volatile. If external clients are already sending malformed, static, or placeholder `Idempotency-Key` headers (e.g., `"null"`, `"12345"`, or `"undefined"`), active enforcement will instantly break their checkout funnels.
2. **Missing Latency SLOs on the Critical Path:** `POST /charges` is our most latency-sensitive route. Adding synchronous network hops to Redis/DB on every charge request adds overhead. Without a strict budget (e.g., <5ms p95 overhead) and VPC-colocated Redis clustering, this change could degrade checkout conversion rates.
3. **Lack of Operational Audit Trail (Support Visibility):** Redis keys expire in 24 hours. If a merchant disputes a duplicate charge 3 days later, support agents and finance operators have zero visibility into whether a charge was a legitimate secondary transaction or a deduplicated API call. We must store the `idempotency_key` and `request_hash` directly on the durable `charges` table.
4. **Failure to Profile Key Entropy & Mismatches:** If a client reuses an idempotency key with a *different* transaction body (e.g., changing the amount from $10 to $100), returning the cached $10 success response (as the original plan implies) is a silent under-charging bug. We must enforce strict SHA-256 payload hashing and return a clear client error on payload mismatch.

---

## 4. Recommended Execution Sequence

```
 ┌────────────────────────────────────────────────────────┐
 │ Phase 1: Telemetry & Baseline Evaluation (Sprint N)     │
 │ - Measure current header usage and collision rates     │
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ Phase 2: Schema Implementation & Lock Handling (N+1)   │
 │ - Store keys in DB, use Redis as fast-path cache      │
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ Phase 3: Shadow Execution & Latency Profiling (N+2)    │
 │ - Run validation in dry-run, log matches/overhead      │
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ Phase 4: Phased Canary Rollout (N+3)                  │
 │ - Scale enforcement: Internal -> 1% -> 10% -> 100%     │
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ Phase 5: Post-Rollout Evaluation & Migration Roadmap   │
 │ - Compare double-charge rates; enforce mandatory keys  │
 └────────────────────────────────────────────────────────┘
```

1. **Phase 1: Telemetry & Baseline Evaluation (Sprint N)**
   * Deploy silent instrumentation to log all incoming `Idempotency-Key` headers.
   * Analyze the logs to check for existing collisions (clients sending static/broken headers) and establish baseline network latency.
   * Run a query on historical transaction tables to calculate the baseline duplicate charge rate (e.g., same card, amount, and account within 5 minutes) to evaluate the success of this feature post-rollout.
2. **Phase 2: Schema Implementation & Client Contract Definition (Sprint N+1)**
   * Add `idempotency_key` and `request_hash` columns to the primary `charges` database table with a unique index on `(account_id, idempotency_key)`.
   * Implement a block-and-poll locking mechanism in Redis (`SET lock_key NX PX 10000`) for concurrent duplicate requests.
   * Publish client documentation outlining the key retention contract (24h), required UUIDv4 format, and error schemas.
3. **Phase 3: Shadow Execution (Sprint N+2)**
   * Run the full middleware checks (payload hashing, collision detection, and DB fallbacks) in **Shadow Mode**.
   * Log discrepancies and latency overhead without altering the API's response behavior. Ensure Redis is configured with `noeviction` and set up alerts for high memory utilization.
4. **Phase 4: Phased Canary Rollout (Sprint N+3)**
   * Roll out active enforcement behind a feature flag: starting with internal test accounts, scaling to a 1% canary group, then progressively to 10%, 50%, and 100% over a two-week period.
   * Monitor metrics: `idempotency.hit`, `idempotency.miss`, `idempotency.payload_mismatch`, and `idempotency.redis.latency`.
5. **Phase 5: Post-Rollout Evaluation & Mandatory Transition**
   * Compare post-rollout duplicate charge rates against Phase 1 baselines.
   * Begin a deprecation timeline to make `Idempotency-Key` mandatory for all new API integrations.

---

## 5. Invariants and Guardrails

* **Tenant Isolation Invariant:** The cache lookup namespace must be strongly sandboxed to prevent cross-tenant data leaks: `LookupKey = f"idempotency:{account_id}:{idempotency_key}"`.
* **Payload Integrity Invariant:** A cached response is only returned if `SHA256(IncomingPayload) == CachedPayloadHash`. If the key matches but the payload does not, return `409 Conflict` or `422 Unprocessable Entity` immediately.
* **Transient Error Exclusion Invariant:** Do *never* cache transient system errors (`5xx`, `429`). The key must remain retryable if the system was unable to safely process the transaction downstream.
* **Redis Fail-Safe Fallback Guardrail:** If Redis is down, look up the transaction state directly in the primary database. Do not fail-closed unless both storage layers are unavailable.
* **Support Traceability Guardrail:** The database record of the charge must permanently store the `idempotency_key` used to create it, ensuring auditability beyond the 24-hour Redis cache TTL.

---

## 6. Risks, Stale Assumptions, and Missing Evidence

* **Risk of Memory Exhaustion in Redis:** Storing verbose JSON responses in Redis will trigger memory issues at scale.
  * *Missing Evidence:* We need a projection of `Daily Charges Volume * Average Response Size` to size the Redis cluster. *(Mitigation: Store only `charge_id` and payload hash in Redis; pull response from primary DB on cache hit).*
* **Stale Assumption on Client Timeout Resilience:** Assuming client applications will wait for long payment processing times or handle raw `409` conflict responses gracefully is highly risky.
  * *Missing Evidence:* What is the default timeout on our official client SDKs? If it is shorter than our payment processor's worst-case processing time, client-side timeouts will trigger duplicate storms.
* **Downstream Alignment Risk:** If our API is idempotent but our payment processor (e.g., Stripe, Adyen) is not, we still risk double charges if a network partition occurs between our API and the processor.
  * *Missing Evidence:* Do we propagate the client's `Idempotency-Key` downstream to our gateway? If not, our API-level idempotency is incomplete.

---

## 7. Concrete Evidence from the Source Material

* **"POST /charges"**: Confirms this is our critical revenue path where latency, operational stability, and conversion rates are paramount.
* **"stores the key-to-response mapping in Redis"**: Proves the plan relies on an ephemeral, non-durable store as the sole system of record, presenting a severe risk of early key eviction or failover loss.
* **"on a duplicate key it returns the cached response"**: Highlights the lack of request payload fingerprint validation (creating potential under-charging risks) and lack of concurrent in-flight locking (creating double-charge risks).
* **"Keys are optional."**: Underlines that buggy clients will not adopt the safety benefits of this feature without an operational plan to eventually mandate its use.
* **"We will enable it for all clients at once next sprint."**: Confirms a highly volatile, instant release model on our critical payment path, lacking shadow-mode or canarying stages.

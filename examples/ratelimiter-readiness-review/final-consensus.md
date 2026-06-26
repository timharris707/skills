# Advisory Board — Final Consensus
review packet
Board: Claude (Architecture & systems/claude-opus-4-8) · Codex (Implementation & testing/gpt-5.5) · Gemini (Product & operations/gemini-3.5-flash). Rounds: 3.

## Verdict: SHIP WITH CHANGES — unanimous (high confidence)

## Consensus blockers (must fix before ship)
1. Wall-clock source on the refill hot path — All three seats agree the use of time.time() on the refill path is a correctness bug under the stated operating context: a backward clock step makes elapsed negative, so self._tokens + elapsed*rate subtracts tokens and the min() clamp only bounds the top, never zero. Result is spurious denials / a multi-second denial window after an NTP or operator clock correction — exactly the traffic conditions the limiter exists to handle. Fix: switch to time.monotonic() (injectable), and clamp elapsed = max(0.0, now - self._last).
   - evidence: `tokenbucket.py::__init__` (code) — verified
   - evidence: `tokenbucket.py:24` (code) — verified
   - evidence: `tokenbucket.py:30` (code) — verified
   - evidence: `tokenbucket.py:31` (code) — verified
   - evidence: tokenbucket.py — “Hosts run `ntpd`; wall-clock corrections (and operator cl...” (source) — verified
2. allow(n) accepts invalid request costs — All three seats flag that allow(n) performs no validation on n. A negative n (e.g. allow(-5)) executes self._tokens -= n, which mints tokens and returns True — a caller can refill the bucket by asking. Non-finite values have undefined behavior and n is never bounded against capacity. Fix: require finite, positive n and define behavior for n > capacity.
   - evidence: `tokenbucket.py:35` (code) — verified
   - evidence: `tokenbucket.py::allow` (code) — verified
3. Per-process / deployment enforcement semantics unresolved — Claude and Codex flag that one bucket per worker process means the globally enforced rate is roughly rate × worker_count, so advertised limit ≠ enforced limit. Claude treats this as a must-decide operational caveat (acceptable as a soft abuse cap, not as a hard ceiling) rather than a code fix; Codex states that if a fixed per-client RPS must be enforced globally across processes/hosts this becomes a block unless moved to a shared limiter or upstream gateway. The seats did not settle whether 'per-client' is global or local. Requires an explicit, recorded operator decision.
   - evidence: tokenbucket.py — “Workers are multi-threaded; a single `TokenBucket` instan...” (source) — verified
   - evidence: judgment — No packet evidence states whether 'per-client' means globally across the API fleet or locally within a worker, nor whether the configured limit is a soft abuse cap or a hard contractual ceiling.
4. Tests are timing-dependent and prove none of the failure modes — Claude and Codex find the tests use time.sleep() and real wall-clock, making them flaky on loaded CI. No test injects a clock, exercises a backward clock jump, asserts the 0 ≤ _tokens ≤ capacity invariant, covers n ≤ 0, or exercises concurrent access — so they cannot deterministically reproduce the primary failure mode. The suite does pass clean — the command citation below re-runs it (exit 0, `OK`) — which is exactly the point: a green suite is a verified receipt that the tests pass, not evidence that the failure modes are covered. Fix: rewrite around a fake/injected clock and add the missing cases.
   - evidence: `test_tokenbucket.py::test_refills_over_time` (code) — verified
   - evidence: `test_tokenbucket.py::test_caps_at_capacity` (code) — verified
   - evidence: `python3 -m unittest` (command) — verified
   - evidence: judgment — Tests use time.sleep(0.05)/time.sleep(0.02) with no injected clock; no backward-jump, concurrency, invariant, or n ≤ 0 coverage.

## Hard dissent (preserved)
- Claude: Dissents from Gemini on two named points: (1) 'migrate to an API Gateway / centralized store instead' is a recommendation to build a different system, not a defect in the artifact under review — per-process and centralized limiting are both legitimate, and a block must rest on an unfixable in-scope defect; (2) the GIL/lock-contention latency-spike rationale is overstated to the point of being wrong as a blocking reason — the critical section is ~four arithmetic ops with no I/O or allocation, sub-microsecond, and the GIL already serializes the workers, so the lock adds negligible marginal contention. If contention ever mattered, the fix is sharding buckets, not abandoning the design.
- Codex: Dissents from Gemini: Python lock contention alone does not justify an unconditional block on the provided evidence. It is a real risk needing load testing, but the packet gives no peak RPS, thread count, latency SLO, or contention benchmark.
- Gemini: Dissents from Codex for focusing narrowly on code correctness while ignoring operational risk: deploying to the hot path of every public request without built-in observability, dry-run/shadow mode, and a fail-open circuit breaker is a critical operational risk regardless of clock correctness. Also dissents from Claude's structural acceptance of per-process limits without operational remediation, insisting on explicit configuration scaling guidelines (e.g. dividing limits by active worker count) to prevent SLA drift.

## What the board couldn't verify
- Whether per-process multiplication is tolerable cannot be judged without peak RPS and worker/process count per host, which are absent from the packet.
- Whether 'per-client' means globally across the fleet or locally within a worker is not stated, so the block-vs-caution boundary on enforcement semantics cannot be resolved from the reviews.
- The lock-contention / GIL latency risk cannot be confirmed or dismissed without load/benchmark data, which the packet does not provide.
- There is no production baseline of client request volumes, so the false-positive-block rate of active blocking mode cannot be predicted from the packet.

## Open questions
- Does 'per-client' mean a hard limit enforced globally across all processes/hosts, or a local per-worker soft cap?
- Is the configured limit a soft abuse cap (per-process multiplication acceptable) or a hard contractual/security ceiling (requires a shared store or upstream gateway)?
- What are the expected peak RPS, worker/process count, thread count, and latency SLO needed to judge per-process multiplication and lock contention?

## Next actions
- Replace time.time() with an injectable clock defaulting to time.monotonic() in __init__ and allow().
- Clamp elapsed = max(0.0, now - self._last) so refill math never goes negative; never move _last backward.
- Validate n in allow(): require finite, positive values and define behavior for n > capacity.
- Constructor already rejects rate ≤ 0 / capacity ≤ 0 (tested by test_rejects_nonpositive_config); additionally reject non-finite rate/capacity (NaN/inf) per Codex, and preserve the invariant 0 ≤ _tokens ≤ capacity after every call.
- Rewrite tests around a fake/injected clock; add cases for backward time, invalid n (≤ 0 and non-finite), capacity caps, denied-request no-consumption, the invariant assertion, and concurrent callers.
- Decide and record enforcement semantics (per-worker, per-host, or global per-client); if global enforcement is required, move to a shared store / upstream gateway / sticky routing, and document per-worker limit partitioning (e.g. local_limit = global_limit / worker_count).
- Add stress/load testing for abusive single-client and normal multi-client traffic before hot-path rollout.
- (Gemini) Add operational safeguards: dry-run/shadow mode emitting metrics while returning True, allow/reject telemetry tagged by client ID, a fail-open try/except around allow() in the caller, and a canary rollout via feature flag.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

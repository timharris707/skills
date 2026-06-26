# Advisory Board — Final Consensus
review packet
Board: Claude (Architecture & systems/claude-opus-4-8) · Codex (Implementation & testing/gpt-5.5) · Gemini (Product & operations/gemini-3.5-flash). Rounds: 3.

## Verdict: SHIP WITH CHANGES — unanimous (high confidence)

## Consensus blockers (must fix before ship)
1. Wall-clock on the refill path causes over-throttle / DoS — Both seats that ran agree this is the primary ship-gating defect. `__init__` seeds `self._last = time.time()` and `allow()` computes `elapsed = now - self._last` with `now = time.time()`. On a backward NTP step or operator clock change `elapsed < 0`, so the refill step `self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)` (line 33) adds a *negative* quantity — and because the expression has no lower clamp, the bucket drains arbitrarily negative — so every shared bucket silently over-throttles legitimate traffic until real time catches up, an immediate denial of service for legitimate API clients. A forward jump is the mirror image: the `min(self.capacity, ...)` cap masks it as an instant one-time refill-to-capacity burst. This contradicts the stated operating context that wall-clock corrections happen in production. Mandatory fix: switch to `time.monotonic()` and clamp `elapsed = max(0.0, now - self._last)`.
   - evidence: `tokenbucket.py::time.time` (code) — verified
   - evidence: `tokenbucket.py:24` (code) — verified
   - evidence: `tokenbucket.py:30` (code) — verified
   - evidence: `tokenbucket.py:31` (code) — verified
   - evidence: `tokenbucket.py:33` (code) — verified
   - evidence: review packet — “wall-clock corrections (and operator clock changes) do ha...” (source) — verified
2. Stated job not met — single bucket with no bounded per-client registry (OOM/DoS surface) — Both seats hold that the proposal's stated job is "per-client rate limiting," but the delivered artifact is one shared `TokenBucket` instance with no `client_id -> bucket` map. Without a memory-bounded registry (thread-safe LRU/TTL cache with a size cap and an eviction policy), naive middleware mapping arbitrary client IDs into an unevicted `dict` is an unbounded-allocation DoS surface for a public, unauthenticated endpoint — an attacker rotating client IDs exhausts memory. Both seats converged on keeping the bucket a low-level primitive and moving the registry into the calling middleware, but the bounded-storage requirement must be specified before this is on the hot path.
   - evidence: review packet — “per-client rate limiting” (source) — verified
   - evidence: judgment — The delivered artifact is a single TokenBucket instance with no client_id -> bucket registry or eviction; the integration that owns the OOM/DoS risk is entirely absent from the packet.

## Hard dissent (preserved)
- Claude: Dissents from Gemini that lock-serialization on the hot path should gate ship: under CPython's GIL the per-bucket critical section is a handful of arithmetic ops and is effectively free, and per-client buckets make lock contention per-client, not global. The real performance hazard would be a single global lock across all clients — but that lives in the registry design, not in this class. Would not gate ship on lock cost.
- Gemini: Holds that even with the clock fix the class is not operationally production-ready: deploying without telemetry to construct rate-limit HTTP headers (Retry-After / X-RateLimit-*), and without operator documentation on local vs. global limits in multi-process WSGI deployments, is an unacceptable rollout and user-workflow risk. This is why Gemini sat at block through rounds 1-2 before moving to caution.

## What the board couldn't verify
- Codex (gpt-5.5 / OpenAI) dropped at preflight on an account usage limit and contributed no review; this is a 2-seat board (Claude + Gemini), labeled as such — not a full three-provider panel.
- Thread-safety is asserted but untested — the lock looks correct by inspection but the property is unproven without a concurrency test.
- The registry integration that turns one bucket into "per-client" — and that owns the OOM/DoS risk — is entirely absent from the packet and cannot be reviewed from what was provided.
- Residual after fixes: a forward clock jump still grants a one-time burst-to-capacity even with monotonic time; acceptable but worth a comment.

## Open questions
- Is there a per-client registry layer, or does the team intend to ship this single shared instance as "per-client" limiting? (Claude: would move to block if the latter.)
- How are local vs. global rate limits documented and reconciled in multi-process WSGI deployments?

## Next actions
- Switch to time.monotonic() in both __init__ (self._last) and allow() (now). Mandatory; gates ship.
- Inject the clock via constructor (e.g. now_fn=time.monotonic) so tests are deterministic and don't rely on time.sleep().
- Add elapsed = max(0.0, now - self._last) as a belt-and-suspenders clamp.
- Validate n (raise ValueError on n <= 0) and document the n > capacity always-deny behavior.
- Add a bounded per-client registry (bucket factory + thread-safe LRU/TTL eviction + size cap) as a sibling component with its own test.
- Add a concurrency test: N threads x M iterations against one bucket; assert no over-spend (granted <= capacity + rate x interval) and 0 <= _tokens <= capacity at the end.
- Expose rate-limiting metadata (e.g. remaining_tokens, retry_after) so middleware can write Retry-After / X-RateLimit-* headers.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

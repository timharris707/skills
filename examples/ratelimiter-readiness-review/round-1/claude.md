# Architecture & Systems Review — `TokenBucket` rate limiter

## 1. Verdict

**Ship with changes (caution).** Confidence: **high.**

The core algorithm and the lock discipline are correct, but the implementation reads `time.time()` (wall clock) on a system the proposal explicitly says runs `ntpd` with operator clock changes. Under the stated operating context this is a real defect, not a theoretical one. The fixes are small and well-understood, so this is "ship with changes," not "block."

**What would change it:** Switch to `time.monotonic()` and add input validation on `n` → moves to **ship**. Conversely, if the board confirms a true *global* (cross-worker) RPS cap is a hard requirement, the per-process design gap pushes this toward **block** until the coordination story is defined.

## 2. Strongest objections

**A. Wall-clock time source contradicts the operating context (must-fix gate).**
`self._last = time.time()` (init) and `now = time.time()` (in `allow`) read the wall clock. The proposal states: *"Hosts run `ntpd`; wall-clock corrections (and operator clock changes) do happen in production"* and lists *"clock source"* as a top concern.

- **Backward jump** (NTP step, operator sets clock back): `elapsed = now - self._last` goes **negative**, so `self._tokens + elapsed * self.rate` *subtracts* tokens. There is no lower clamp — `min(capacity, …)` only bounds the top — so `_tokens` can go **negative**, and the bucket then refuses all traffic for an arbitrary recovery window. That is a **self-inflicted throttling / partial outage** on the public API, triggered by a routine clock correction. This is the most serious issue in the packet.
- **Forward jump:** `elapsed` spikes, tokens jump straight to `capacity`. Bounded by the cap, so milder, but it grants an unearned burst right after a correction.

`time.monotonic()` is immune to NTP slew and steps and is the correct source for measuring elapsed intervals. This is essentially mandatory given the stated environment.

**B. `n` is unvalidated — and negative `n` mints tokens.**
`allow(n)` has no guard. `allow(0)` always returns `True` without consuming. `allow(-5)` hits `self._tokens -= n`, *adding* tokens and pushing `_tokens` **above capacity** — a state the class otherwise guarantees can't happen. Even though the hot path uses the default `n=1`, this is an invariant violation reachable from the public signature. Validate `n > 0` (and arguably reject `n > capacity` as a permanent-fail config error, or document that it can never succeed).

**C. Per-process design means the configured rate is not the enforced rate.**
The context says `allow()` runs *"in every API worker process"* and a `TokenBucket` is shared across *a worker's* threads — i.e. **one bucket per process**, no cross-process state. With *W* workers the effective global limit is **`rate × W`**, not `rate`. If the goal is "cap abusive traffic at a fixed RPS" globally, this silently over-admits by the worker multiple. Either divide `rate` by worker count, document the limit as per-worker, or move shared state to Redis/equivalent. The board must decide whether per-worker enforcement is acceptable.

**D. The per-client bucket registry is missing — and it's the real DoS surface.**
The proposal is *per-client* rate limiting, but the packet shows a single bucket and no client→bucket map, eviction, or TTL. In production that map is where the danger lives: an attacker rotating source IPs/keys creates **unbounded buckets → memory exhaustion**, turning a rate limiter into a DoS amplifier. The registry also needs its own lock for concurrent insert. "Failure modes during traffic spikes" is a named top concern, and this is the dominant one — yet it's entirely absent from the artifact under review.

**E. Tests can't exercise the failure modes that matter, and are timing-fragile.**
`time` is not injectable, so there is no way to deterministically test backward/forward clock jumps, and `test_refills_over_time` / `test_caps_at_capacity` depend on real `time.sleep` (flaky under CI load). There is **no concurrency test** despite thread-safety being the headline claim, and no test for negative/zero `n`. Inject a `time_fn` (default `time.monotonic`) to make all of this testable.

## 3. Recommended execution sequence

1. **Swap `time.time()` → `time.monotonic()`** in `__init__` and `allow()`. (Gate; one line each.)
2. **Validate `n`** at the top of `allow()`: `if n <= 0: raise ValueError`. Decide policy on `n > capacity`.
3. **Inject the clock**: constructor arg `time_fn=time.monotonic`, store and call it, so tests are deterministic.
4. **Define the client registry** (separate from this file but in scope): bounded size + LRU/TTL eviction, its own lock, documented memory ceiling.
5. **Decide and document the enforcement scope**: per-worker vs global. If global is required, design the shared-state coordination before shipping.
6. **Add tests**: backward-jump (tokens must not go negative / not over-grant), forward-jump cap, `n<=0` rejection, and a concurrency test asserting no over-spend under N threads.

## 4. Invariants and guardrails

- **`0 ≤ _tokens ≤ capacity` at all times.** Currently violated by backward clock jumps (can go < 0) and by negative `n` (can exceed capacity). After fixes, assert/clamp `elapsed = max(0, now - self._last)` as defense-in-depth even with monotonic time.
- **Monotonic non-decreasing time source** — guaranteed by `time.monotonic()`, not by `time.time()`.
- **No token is spent twice under concurrency** — the single lock around refill-and-consume holds; this is correct as written.
- **Bounded memory** for the (missing) registry — hard cap on live buckets.
- **At-most `capacity` burst, then ≤ `rate` sustained** per bucket — holds once the clock is fixed.

## 5. Risks, stale assumptions, missing evidence

- **Stale assumption:** that `time.time()` is monotonic. It isn't, and the packet itself supplies the counter-evidence (ntpd in prod).
- **Risk:** per-process semantics mean published/configured limits won't match observed behavior — an operational footgun during incident response.
- **Missing evidence:** no benchmark of lock contention on the hot path. For a per-client bucket, contention is scoped to threads hitting the same client, so likely fine — but unmeasured, and it's a named concern ("behavior under concurrency").
- **Missing:** registry lifecycle, eviction policy, and the global-vs-per-worker decision — all declared in scope, none present.
- **Minor:** float accumulation drift is bounded by the `min(capacity, …)` cap; acceptable, no action needed.
- **Note (not a bug):** starting full (`_tokens = capacity`) permits an initial burst up to `capacity`. Standard token-bucket behavior; just make sure `capacity` is chosen as the intended max burst, not equal to `rate` by reflex.

## 6. Concrete evidence from the source

- Wall clock source: `self._last = time.time()` (`__init__`) and `now = time.time()` (`allow`).
- No lower clamp on refill: `self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)` — bounds the top only; negative `elapsed` drives tokens down with no floor.
- No `n` validation: `def allow(self, n: float = 1)` proceeds directly to `if self._tokens >= n: self._tokens -= n` — negative `n` increases `_tokens` past `capacity`.
- Lock scope is correct: `with self._lock:` wraps the entire refill-and-consume — matches the docstring claim *"a single lock guards the refill-and-consume step."*
- Operating context, quoted: *"Hosts run `ntpd`; wall-clock corrections (and operator clock changes) do happen in production"* and *"`allow()` runs once per inbound request, in every API worker process."*
- Tests bind real time: `time.sleep(0.05)` / `time.sleep(0.02)` with no injectable clock; no concurrency or clock-jump test exists in `test_tokenbucket.py`.

## 7. What I'd ask the other board seats to challenge

- **Concurrency/runtime seat:** Is per-bucket lock contention acceptable at peak RPS for the hottest clients, or do we need lock-free/sharded buckets? Does the GIL make the lock cost negligible here, or not under free-threaded builds?
- **Reliability/SRE seat:** Is per-worker enforcement (effective limit `rate × W`) acceptable, or is a true global cap a hard requirement that mandates shared state? What's the blast radius of the backward-clock self-throttle in a real incident?
- **Security seat:** Confirm the unbounded client-registry growth is the primary DoS vector and pressure-test the eviction policy against IP/key rotation.
- **Testing seat:** Push for a deterministic, injected-clock test matrix (jumps, concurrency, boundary `n`) as a merge gate — the current suite passing "clean" is not evidence the failure modes are handled.

VERDICT: caution

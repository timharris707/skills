# Review packet: `TokenBucket` rate limiter — production-readiness review

This is the single source packet handed to every board seat. It contains the
proposal, the implementation, and its test suite. Review the **implementation**
against the proposal's operating context and give a verdict: ship as-is, ship
with changes, or block.

---

## Proposal

We need per-client rate limiting in front of our public HTTP API to cap abusive
traffic at a fixed requests-per-second. `tokenbucket.py` (below) is the proposed
implementation; `test_tokenbucket.py` is its suite and currently passes clean
(`python3 -m unittest`, run from the source directory).

**The decision for the board:** is this implementation production-ready to put on
the hot path of every public request? Recommend **ship as-is**, **ship with
changes**, or **block**.

Operating context (all in scope):

- `allow()` runs once per inbound request, in every API worker process.
- Workers are multi-threaded; a single `TokenBucket` instance is shared across a
  worker's threads.
- Hosts run `ntpd`; wall-clock corrections (and operator clock changes) do happen
  in production.
- Clock source, behavior under concurrency, refill-math correctness, and failure
  modes during traffic spikes are the things we care about most.

---

## `tokenbucket.py`

```python
"""A minimal token-bucket rate limiter.

Proposed for gating our public HTTP API at a fixed requests-per-second per
client. One bucket instance is shared across a worker's threads; ``allow()`` is
called once per inbound request on the hot path.
"""
import threading
import time


class TokenBucket:
    """Allow up to ``capacity`` tokens, refilled at ``rate`` tokens/second.

    Thread-safe: a single lock guards the refill-and-consume step so two
    concurrent callers cannot both spend the same token.
    """

    def __init__(self, rate: float, capacity: float):
        if rate <= 0 or capacity <= 0:
            raise ValueError("rate and capacity must be positive")
        self.rate = rate
        self.capacity = float(capacity)
        self._tokens = float(capacity)
        self._last = time.time()
        self._lock = threading.Lock()

    def allow(self, n: float = 1) -> bool:
        """Consume ``n`` tokens if available; return whether the request passes."""
        with self._lock:
            now = time.time()
            elapsed = now - self._last
            self._last = now
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            if self._tokens >= n:
                self._tokens -= n
                return True
            return False
```

---

## `test_tokenbucket.py`

```python
import time
import unittest

from tokenbucket import TokenBucket


class TokenBucketTest(unittest.TestCase):
    def test_starts_full(self):
        b = TokenBucket(rate=10, capacity=3)
        self.assertTrue(b.allow())
        self.assertTrue(b.allow())
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())  # capacity exhausted

    def test_refills_over_time(self):
        b = TokenBucket(rate=100, capacity=2)
        self.assertTrue(b.allow())
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())
        time.sleep(0.05)             # 0.05s * 100/s = 5 tokens earned
        self.assertTrue(b.allow())   # refilled enough for one more

    def test_caps_at_capacity(self):
        b = TokenBucket(rate=1000, capacity=2)
        time.sleep(0.02)             # would earn 20 tokens, but the cap is 2
        self.assertTrue(b.allow())
        self.assertTrue(b.allow())
        self.assertFalse(b.allow())  # refill never exceeds capacity

    def test_rejects_nonpositive_config(self):
        with self.assertRaises(ValueError):
            TokenBucket(rate=0, capacity=1)
        with self.assertRaises(ValueError):
            TokenBucket(rate=1, capacity=0)


if __name__ == "__main__":
    unittest.main()
```

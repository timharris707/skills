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

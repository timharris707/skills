# A tiny stand-in source file for evidence-resolution tests.
# Deterministic: 15 lines, one named symbol `charge_idempotent`.
import redis

STORE = redis.Redis()


def charge_idempotent(key, request):
    """Claim the key atomically, then charge."""
    claimed = STORE.set(key, "in-progress", nx=True)
    if not claimed:
        return STORE.get(key)
    result = do_charge(request)
    STORE.set(key, result)
    return result

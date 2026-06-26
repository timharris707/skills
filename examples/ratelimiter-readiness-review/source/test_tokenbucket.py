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

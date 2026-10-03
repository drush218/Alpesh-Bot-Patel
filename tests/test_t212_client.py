"""T212 response sharing: concurrent and back-to-back calls make one request (rate limit)."""

import os
import sys
import threading
import time
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.services import t212_client


class _Resp:
    ok, status_code, text = True, 200, ""

    def json(self):
        return [{"ticker": "BROS_US_EQ"}]


class TestT212Cache(unittest.TestCase):
    def setUp(self):
        t212_client._cache.clear()
        self.calls = 0

    def fake_get(self, *a, **k):
        self.calls += 1
        time.sleep(0.05)   # long enough for the other thread to arrive mid-request
        return _Resp()

    def test_concurrent_calls_share_one_request(self):
        with mock.patch.object(t212_client.requests, "get", self.fake_get):
            threads = [threading.Thread(target=t212_client.get_positions, args=("k", "s")) for _ in range(3)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(t212_client.get_positions("k", "s"), [{"ticker": "BROS_US_EQ"}])
        self.assertEqual(self.calls, 1)

    def test_expired_entry_refetched(self):
        with mock.patch.object(t212_client.requests, "get", self.fake_get), \
             mock.patch.object(t212_client, "CACHE_TTL", 0.0):
            t212_client.get_positions("k", "s")
            t212_client.get_positions("k", "s")
        self.assertEqual(self.calls, 2)


if __name__ == "__main__":
    unittest.main()

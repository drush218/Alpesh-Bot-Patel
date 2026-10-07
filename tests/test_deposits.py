"""Deposit stats: full scan, incremental top-up, cache reuse, and the CAGR maths."""

import os
import sys
import unittest
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from app.services import benchmarks, deposits, t212_client
from fakes import FakeSupabase

NOW = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
UID = "user-1"

# Newest first, as T212 returns them.
PAGE_1 = {"items": [
    {"type": "DEPOSIT", "amount": 500, "dateTime": "2026-09-01T09:00:00.000Z"},
    {"type": "DEPOSIT", "amount": 0.42, "dateTime": "2026-08-31T00:00:00.000Z"},   # interest
    {"type": "WITHDRAW", "amount": -200, "dateTime": "2026-08-01T09:00:00.000Z"},
], "nextPagePath": "limit=50&cursor=abc"}
PAGE_2 = {"items": [
    {"type": "TRANSFER", "amount": -100, "dateTime": "2025-01-01T09:00:00.000Z"},
    {"type": "FEE", "amount": -3, "dateTime": "2024-12-01T09:00:00.000Z"},
    {"type": "DEPOSIT", "amount": 1000, "dateTime": "2023-07-04T09:00:00.000Z"},
], "nextPagePath": None}


class FakeHistory:
    def __init__(self, pages):
        self.pages, self.paths = pages, []

    def __call__(self, key, secret, path):
        self.paths.append(path)
        return self.pages[len(self.paths) - 1], {"x-ratelimit-remaining": "5"}


def _stats(db, fetch):
    return deposits.get_deposit_stats(db, UID, "k", "s", now=NOW, fetch_page=fetch, sleep=lambda s: None)


class TestDepositStats(unittest.TestCase):
    def test_full_scan_nets_deposits_withdrawals_transfers(self):
        db, fetch = FakeSupabase(), FakeHistory([PAGE_1, PAGE_2])
        db.tables["user_settings"] = [{"id": UID, "t212_api_key": "enc"}]   # row exists once credentials are saved
        stats = _stats(db, fetch)
        self.assertEqual(stats["total_deposited"], 500 - 200 - 100 + 1000)
        self.assertEqual(stats["first_deposit_date"], "2023-07-04T09:00:00.000Z")
        self.assertEqual(fetch.paths[1], "/api/v0/equity/history/transactions?limit=50&cursor=abc")
        self.assertEqual(db.rows("user_settings", id=UID)[0]["deposit_total"], 1200)

    def test_fresh_cache_skips_t212(self):
        db = FakeSupabase()
        db.tables["user_settings"] = [{"id": UID, "deposit_total": 900, "first_deposit_date": "2023-07-04",
                                       "deposit_stats_cached_at": "2026-10-05T06:00:00+00:00",
                                       "last_tx_fetched_at": "2026-10-05T06:00:00+00:00"}]
        fetch = FakeHistory([])
        self.assertEqual(_stats(db, fetch)["total_deposited"], 900)
        self.assertEqual(fetch.paths, [])

    def test_stale_cache_adds_only_newer_transactions(self):
        db = FakeSupabase()
        db.tables["user_settings"] = [{"id": UID, "deposit_total": 700, "first_deposit_date": "2023-07-04T09:00:00.000Z",
                                       "deposit_stats_cached_at": "2026-08-15T00:00:00+00:00",
                                       "last_tx_fetched_at": "2026-08-15T00:00:00+00:00"}]
        fetch = FakeHistory([PAGE_1, PAGE_2])
        stats = _stats(db, fetch)
        self.assertEqual(stats["total_deposited"], 700 + 500)   # stops at the Aug 1 withdrawal
        self.assertEqual(len(fetch.paths), 1)
        self.assertEqual(stats["first_deposit_date"], "2023-07-04T09:00:00.000Z")

    def test_t212_error_falls_back_to_stale_cache(self):
        db = FakeSupabase()
        db.tables["user_settings"] = [{"id": UID, "deposit_total": 700, "first_deposit_date": "2023-07-04",
                                       "deposit_stats_cached_at": "2026-08-15T00:00:00+00:00",
                                       "last_tx_fetched_at": "2026-08-15T00:00:00+00:00"}]

        def failing(*_):
            raise t212_client.T212Error("429")

        self.assertEqual(_stats(db, failing)["total_deposited"], 700)


class TestCagr(unittest.TestCase):
    def test_cagr(self):
        self.assertAlmostEqual(deposits.cagr_pct(121, 100, 2), 10.0)
        self.assertIsNone(deposits.cagr_pct(121, 100, None))

    def test_index_cagrs_cached_per_day(self):
        benchmarks._cache.clear()
        calls = []

        def fetch(symbol, start):
            calls.append(symbol)
            return (100.0, 121.0) if symbol == "^GSPC" else None

        rows = benchmarks.index_cagrs("2024-10-05", 2, fetch=fetch, today=date(2026, 10, 5))
        self.assertAlmostEqual(rows[0]["cagr_pct"], 10.0)
        self.assertIsNone(rows[1]["cagr_pct"])
        benchmarks.index_cagrs("2024-10-05", 2, fetch=fetch, today=date(2026, 10, 5))
        self.assertEqual(len(calls), len(benchmarks.INDICES))


if __name__ == "__main__":
    unittest.main()

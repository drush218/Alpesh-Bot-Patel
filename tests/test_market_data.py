"""
Price / FX refresh (backend/app/services/market_data.py) against the in-memory fake client.
Quotes are stubbed, so no network.

Run with: python -m unittest discover tests -v
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.services import market_data
from fakes import FakeSupabase

NOW = datetime(2026, 10, 2, 14, 0, tzinfo=timezone.utc)
QUOTES = {"BROS": (64.67, "USD"), "HSBA.L": (900.0, "GBp"),
          "USDGBP=X": (0.80, "GBP"), "GBPUSD=X": (1.25, "USD")}


class TestParseT212Ticker(unittest.TestCase):
    def test_cases(self):
        self.assertEqual(market_data.parse_t212_ticker("BROS_US_EQ"), ("BROS", "BROS"))
        self.assertEqual(market_data.parse_t212_ticker("HSBAl_EQ"), ("HSBA", "HSBA.L"))
        self.assertEqual(market_data.parse_t212_ticker("BRK_B_US_EQ"), ("BRK_B", "BRK-B"))
        self.assertEqual(market_data.parse_t212_ticker("ASMLa_EQ"), ("ASML", None))   # unconfirmed suffix
        self.assertEqual(market_data.parse_t212_ticker("IPOE_US_EQ"), ("SOFI", "SOFI"))  # T212 kept the SPAC symbol


class _Case(unittest.TestCase):
    def setUp(self):
        self.db = FakeSupabase()
        self.calls = []

    def quote(self, sym):
        self.calls.append(sym)
        return QUOTES.get(sym)


class TestSyncInstruments(_Case):
    def test_creates_and_fills_without_overwriting(self):
        self.db.tables["instruments"] = [{"id": 50, "ticker": "HSBA", "t212_ticker": None, "yahoo_symbol": "HSBA.L"}]
        market_data.sync_instruments(self.db, ["BROS_US_EQ", "HSBAl_EQ"])
        bros = self.db.rows("instruments", ticker="BROS")[0]
        self.assertEqual((bros["t212_ticker"], bros["yahoo_symbol"]), ("BROS_US_EQ", "BROS"))
        hsba = self.db.rows("instruments", ticker="HSBA")
        self.assertEqual(len(hsba), 1)
        self.assertEqual((hsba[0]["t212_ticker"], hsba[0]["yahoo_symbol"]), ("HSBAl_EQ", "HSBA.L"))


class TestRefresh(_Case):
    def setUp(self):
        super().setUp()
        self.db.tables["instruments"] = [
            {"id": 1, "ticker": "BROS", "yahoo_symbol": "BROS"},
            {"id": 2, "ticker": "HSBA", "yahoo_symbol": "HSBA.L"},
            {"id": 3, "ticker": "ASML", "yahoo_symbol": None},
        ]
        self.db.tables["analyses"] = [
            {"id": 10, "instrument_id": 2, "is_current": True, "reporting_currency": "USD", "price_currency": "GBp"},
        ]

    def test_fetches_prices_and_needed_fx(self):
        s = market_data.refresh_market_data(self.db, self.quote, NOW)
        self.assertEqual((s["prices_updated"], s["unmapped"], s["failed"]), (2, ["ASML"], []))
        hsba = self.db.rows("prices", instrument_id=2)[0]
        self.assertEqual((hsba["close"], hsba["currency"], hsba["price_date"]), (900.0, "GBp", "2026-10-02"))
        # USD quote -> GBP (portfolio), and HSBA's USD EPS -> GBP quote; GBp->GBP is the same major ccy.
        self.assertEqual({(r["from_ccy"], r["to_ccy"]) for r in self.db.tables["fx_rates"]}, {("USD", "GBP")})
        self.assertEqual(s["fx_updated"], 1)

    def test_second_call_within_max_age_skips(self):
        market_data.refresh_market_data(self.db, self.quote, NOW)
        self.calls.clear()
        s = market_data.refresh_market_data(self.db, self.quote, NOW + timedelta(minutes=5))
        self.assertEqual(self.calls, [])
        self.assertEqual((s["prices_fresh"], s["fx_fresh"]), (2, 1))

    def test_stale_row_overwritten_in_place(self):
        market_data.refresh_market_data(self.db, self.quote, NOW)
        QUOTES["BROS"] = (70.0, "USD")
        try:
            market_data.refresh_market_data(self.db, self.quote, NOW + timedelta(minutes=20))
        finally:
            QUOTES["BROS"] = (64.67, "USD")
        rows = self.db.rows("prices", instrument_id=1)
        self.assertEqual([r["close"] for r in rows], [70.0])

    def test_failed_quote_reported_not_raised(self):
        self.db.tables["instruments"].append({"id": 4, "ticker": "GONE", "yahoo_symbol": "GONE"})
        s = market_data.refresh_market_data(self.db, self.quote, NOW)
        self.assertIn("GONE", s["failed"])
        self.assertEqual(self.db.rows("prices", instrument_id=4), [])


if __name__ == "__main__":
    unittest.main()

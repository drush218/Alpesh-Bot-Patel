"""Macro: 1-month moves from a series, link scoring with the down-move flip, verdict bands, tilt."""

import os
import sys
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
for k in ("SUPABASE_URL", "SUPABASE_KEY", "FERNET_KEY"):
    os.environ.setdefault(k, "test")

from app.services import macro_data, macro_view
from fakes import FakeSupabase


class TestMoves(unittest.TestCase):
    def test_level_series_relative_change(self):
        obs = [("2026-08-01", 100.0), ("2026-08-15", 101.0), ("2026-09-02", 104.0)]
        rows = macro_data.moves(obs, "level")
        self.assertEqual([r["as_of"] for r in rows], ["2026-09-02"])     # first month has no comparison
        self.assertAlmostEqual(rows[0]["change"], 4.0)
        self.assertEqual(rows[0]["move"], "up")

    def test_rate_series_absolute_points_and_flat_band(self):
        rows = macro_data.moves([("2026-08-01", 4.20), ("2026-09-05", 4.25)], "rate")
        self.assertEqual(rows[0]["move"], "flat")                       # 5bp is inside the 10bp band
        rows = macro_data.moves([("2026-08-01", 4.20), ("2026-09-05", 3.90)], "rate")
        self.assertEqual(rows[0]["move"], "down")

    def test_refresh_stores_and_skips_same_day(self):
        macro_data._fetched_on.clear()
        db = FakeSupabase()
        db.tables["macro_factors"] = [{"code": "rates_10y", "name": "10y yield"}, {"code": "custom_x", "name": "x"}]
        fetch = lambda series, start: [("2026-08-01", 4.0), ("2026-09-03", 4.4)]
        s = macro_data.refresh_macro(db, fetch=fetch, today=date(2026, 10, 5))
        self.assertEqual((s["updated"], s["no_source"]), (["rates_10y"], ["custom_x"]))
        self.assertEqual(db.rows("macro_factor_moves", factor_code="rates_10y")[0]["move"], "up")
        self.assertEqual(macro_data.refresh_macro(db, fetch=fetch, today=date(2026, 10, 5))["skipped"], ["rates_10y"])


class TestMacroView(unittest.TestCase):
    def setUp(self):
        self.db = FakeSupabase()
        self.db.tables["macro_factors"] = [{"code": "rates_10y", "name": "10y yield"}, {"code": "labour", "name": "Labour"}]
        self.db.tables["macro_factor_moves"] = [
            {"factor_code": "rates_10y", "as_of": "2026-10-01", "value": 4.4, "change": 0.3, "move": "up"},
            {"factor_code": "labour", "as_of": "2026-09-01", "value": 31.0, "change": -0.5, "move": "down"},
        ]
        self.db.tables["analyses"] = [{"id": 10, "is_current": True, "instruments": {"ticker": "BROS", "company": "Dutch Bros"}}]
        self.db.tables["analysis_macro"] = [
            {"analysis_id": 10, "factor_code": "rates_10y", "channel": "valuation", "direction": "bear", "strength": "strong"},
            {"analysis_id": 10, "factor_code": "labour", "channel": "cost", "direction": "bear", "strength": "mild"},
            {"analysis_id": 10, "factor_code": "us_gasoline_retail", "channel": "demand", "direction": "bear", "strength": "medium"},
        ]
        self._holdings = macro_view._holdings
        macro_view._holdings = lambda db, uid: ([{"ticker": "BROS", "weight_pct": 7.0}, {"ticker": "MSFT", "weight_pct": 10.0}], [])

    def tearDown(self):
        macro_view._holdings = self._holdings

    def test_scores_flip_on_down_move_and_skip_pending(self):
        v = macro_view.macro_view(self.db, "u")
        bros = next(h for h in v["holdings"] if h["ticker"] == "BROS")
        # rates up x bear strong = -3; labour down flips bear mild to +1; pending gasoline excluded
        self.assertEqual(bros["factor_scores"], {"rates_10y": -3, "labour": 1})
        self.assertEqual((bros["score"], bros["verdict"]), (-2, "headwind"))
        msft = next(h for h in v["holdings"] if h["ticker"] == "MSFT")
        self.assertFalse(msft["modelled"])
        self.assertEqual(v["tilt"]["verdict"], "headwind")
        self.assertEqual(v["matrix_factors"], ["labour", "rates_10y"])

    def test_state_line(self):
        up = lambda d, c: {"as_of": d, "change": c, "move": "up" if c > 0 else "down"}
        self.assertEqual(macro_view._state([up("2026-08-20", 1.0), up("2026-09-25", 3.0)]), "Accelerating up")
        self.assertEqual(macro_view._state([up("2026-08-20", 3.0), up("2026-09-25", 1.0)]), "Moving up")
        self.assertEqual(macro_view._state([up("2026-09-25", -1.0)]), "No data yet")

    def test_bands(self):
        self.assertEqual([macro_view.verdict(s) for s in (-3, -1, 0, 1, 3)],
                         ["strong headwind", "headwind", "neutral", "tailwind", "strong tailwind"])


if __name__ == "__main__":
    unittest.main()

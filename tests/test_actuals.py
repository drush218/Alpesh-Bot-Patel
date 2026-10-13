"""Base-year actuals: net income and EPS calculated like a forecast year, for current PE."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
for k in ("SUPABASE_URL", "SUPABASE_KEY", "FERNET_KEY"):
    os.environ.setdefault(k, "test")

from app.services import actuals


def inputs(**a):
    return {
        "meta": {"base_year": "FY2025"},
        "revenue": {"segments": [{"name": "A", "base": 600.0}, {"name": "B", "base": 400.0}]},
        "shares": {"base_diluted": 100.0},
        **({"actuals": a} if a else {}),
    }


class ComputeTest(unittest.TestCase):
    def test_same_maths_as_a_forecast_year(self):
        r = actuals.compute(inputs(
            operating_margin={"pct": 10.0}, net_interest={"value": -20.0}, tax_rate={"pct": 25.0},
            nci_pct={"pct": 10.0}, reported_eps={"value": 0.50},
        ))
        # EBIT 100, pretax 80, tax 20, NI 60, less 10% NCI = 54; 100 shares
        self.assertAlmostEqual(r["costs"], 900.0)
        self.assertAlmostEqual(r["net_income"], 54.0)
        self.assertAlmostEqual(r["eps"], 0.54)
        self.assertAlmostEqual(r["eps_check_pct"], 8.0)
        self.assertEqual(r["year"], "FY2025")

    def test_no_tax_on_a_loss(self):
        r = actuals.compute(inputs(operating_margin={"pct": 1.0}, net_interest={"value": -30.0}, tax_rate={"pct": 25.0}))
        self.assertAlmostEqual(r["net_income"], -20.0)

    def test_incomplete_leaves_eps_blank(self):
        r = actuals.compute(inputs(operating_margin={"pct": 10.0}))
        self.assertAlmostEqual(r["costs"], 900.0)
        self.assertIsNone(r["eps"])
        self.assertIsNone(actuals.compute(inputs())["eps"])


class SkeletonTest(unittest.TestCase):
    def test_skeleton_round_trip(self):
        m = actuals.with_skeleton(inputs(tax_rate={"pct": 25.0, "source": "filing"}))
        self.assertEqual(m["actuals"]["operating_margin"], {"pct": None})
        self.assertEqual(m["actuals"]["reported_eps"], {"value": None})
        stripped = actuals.strip_empty(m)
        self.assertEqual(stripped["actuals"], {"tax_rate": {"pct": 25.0, "source": "filing"}})
        self.assertNotIn("actuals", actuals.strip_empty(actuals.with_skeleton(inputs())))


if __name__ == "__main__":
    unittest.main()

"""Expected-move model on synthetic data: recovers the beta, flags a shock, labels results days."""

import os
import sys
import unittest
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.services.expected_move import fit_and_explain


def _series(n=300, shock=0.0, seed=1):
    rng = np.random.default_rng(seed)
    r_idx = rng.normal(0, 0.01, n)
    r_oil = rng.normal(0, 0.02, n)
    d_rates = rng.normal(0, 0.03, n)
    r_stock = 1.5 * r_idx - 0.2 * r_oil - 0.05 * d_rates + rng.normal(0, 0.005, n)
    r_stock[-1] += shock
    idx = 100 * np.cumprod(1 + r_idx)
    oil = 80 * np.cumprod(1 + r_oil)
    rates = 4 + np.cumsum(d_rates)
    stock = 50 * np.cumprod(1 + r_stock)
    dates = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(n)]
    flat = np.full(n, 1.0)
    factors = {"rates": ("diff", rates), "oil": ("ret", oil), "usd": ("ret", flat), "credit": ("ret", flat * 2)}
    return stock, idx, factors, dates


class TestExpectedMove(unittest.TestCase):
    def test_recovers_beta_and_quiet_day_not_flagged(self):
        stock, idx, factors, dates = _series()
        r = fit_and_explain(stock, idx, factors, dates, set())
        self.assertAlmostEqual(r["betas"]["index"], 1.5, delta=0.1)
        self.assertGreater(r["r2"], 0.8)
        self.assertEqual(r["n"], 250)
        self.assertEqual(r["category"], "none")

    def test_shock_is_unexplained_unless_results_day(self):
        stock, idx, factors, dates = _series(shock=0.05)
        r = fit_and_explain(stock, idx, factors, dates, set())
        self.assertEqual(r["category"], "unexplained")
        self.assertGreater(r["z"], 2)
        self.assertAlmostEqual(r["residual_pct"], 5.0, delta=1.0)
        # reported after the previous close -> today's move is the results reaction
        self.assertEqual(fit_and_explain(stock, idx, factors, dates, {dates[-2]})["category"], "earnings")

    def test_too_little_history(self):
        stock, idx, factors, dates = _series(n=50)
        self.assertIsNone(fit_and_explain(stock, idx, factors, dates, set()))


if __name__ == "__main__":
    unittest.main()

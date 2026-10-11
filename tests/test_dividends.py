"""Annual dividend per share from the user's dividend input."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.services.dividends import annual_dps


class TestAnnualDps(unittest.TestCase):
    def test_modes(self):
        self.assertIsNone(annual_dps(None))
        self.assertEqual(annual_dps({"mode": "per_payment", "amount": 5, "frequency": 4}), 20)
        self.assertEqual(annual_dps({"mode": "half", "amount": 23}), 46)
        self.assertEqual(annual_dps({"mode": "annual", "amount": 69}), 69)
        self.assertEqual(annual_dps({"mode": "uneven", "payments": [23, 46]}), 69)
        self.assertIsNone(annual_dps({"mode": "annual", "amount": None}))


if __name__ == "__main__":
    unittest.main()

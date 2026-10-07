"""User scorecard: starts empty (no prefill), every save is a new version, rows are per user."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from app.services import scorecard
from fakes import FakeSupabase
from test_model_v2 import _load_fixture, _model_block

ME, OTHER = "user-1", "user-2"
CARD = {"growth": 4, "value": 3, "income": 1,
        "bull_catalysts": [{"text": "Q2 comps ≥ +6%", "date": "2026-08-05", "status": "open"}],
        "bear_catalysts": [], "note": None}


class TestScorecard(unittest.TestCase):
    def setUp(self):
        self.db = FakeSupabase()
        self.db.tables["instruments"] = [{"id": 1, "ticker": "BROS"}]
        self.db.tables["analyses"] = [{"id": 10, "instrument_id": 1, "is_current": True,
                                       "model": _model_block(_load_fixture())}]

    def test_empty_until_saved_with_suggestion_alongside(self):
        res = scorecard.get_scorecard(self.db, ME, "BROS")
        self.assertIsNone(res["current"])
        self.assertEqual(res["versions"], 0)
        self.assertEqual(res["suggested"]["growth"]["score"], 5)
        self.assertEqual(res["suggested"]["as_of"], "2026-07-28")

    def test_each_save_is_a_new_version(self):
        scorecard.save_scorecard(self.db, ME, "BROS", CARD)
        res = scorecard.save_scorecard(self.db, ME, "BROS", {**CARD, "value": 2})
        self.assertEqual(res["versions"], 2)
        self.assertEqual(res["current"]["value"], 2)
        self.assertEqual(res["current"]["bull_catalysts"][0]["date"], "2026-08-05")
        self.assertEqual(len(self.db.rows("scorecards")), 2)

    def test_other_users_card_not_visible(self):
        scorecard.save_scorecard(self.db, ME, "BROS", CARD)
        self.assertIsNone(scorecard.get_scorecard(self.db, OTHER, "BROS")["current"])


if __name__ == "__main__":
    unittest.main()

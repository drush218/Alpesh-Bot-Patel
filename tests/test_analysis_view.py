"""Analysis screen payload: upcoming calendar only, what-changed against the previous analysis."""

import copy
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
for k in ("SUPABASE_URL", "SUPABASE_KEY", "FERNET_KEY"):
    os.environ.setdefault(k, "test")

from app.services import analysis_view
from fakes import FakeSupabase
from test_model_v2 import _load_fixture, _model_block


class TestAnalysisView(unittest.TestCase):
    def setUp(self):
        self.db = FakeSupabase()
        self.model = _model_block(_load_fixture())
        self.db.tables["instruments"] = [{"id": 1, "ticker": "BROS"}]
        self.db.tables["analyses"] = [{"id": 10, "instrument_id": 1, "is_current": True, "model": self.model,
                                       "data_as_of": "2026-07-28", "created_at": "2026-10-03T00:00:00+00:00"}]
        self._creds = analysis_view.get_t212_credentials
        analysis_view.get_t212_credentials = lambda db, uid: (None, None)   # no T212 -> no position

    def tearDown(self):
        analysis_view.get_t212_credentials = self._creds

    def test_first_analysis_has_no_what_changed(self):
        v = analysis_view.analysis_view(self.db, "u", "bros")
        self.assertIsNone(v["what_changed"])
        self.assertIsNone(v["position"])
        self.assertEqual(len(v["macro"]), 5)

    def test_what_changed_against_previous(self):
        old = copy.deepcopy(self.model)
        old["outputs"]["scenarios"]["bau"][2]["eps"] = 1.70
        self.db.tables["analyses"].append({"id": 9, "instrument_id": 1, "is_current": False, "model": old,
                                           "data_as_of": "2026-04-30", "created_at": "2026-05-01T00:00:00+00:00"})
        wc = analysis_view.analysis_view(self.db, "u", "BROS")["what_changed"]
        self.assertEqual(wc["previous_as_of"], "2026-04-30")
        fy28 = [r for r in wc["rows"] if r["year"] == "FY2028"][0]
        self.assertEqual((fy28["eps_was"], round(fy28["eps_now"], 2)), (1.70, 1.87))


class TestStaleness(unittest.TestCase):
    CAL = {"calendar": [{"date": "2026-08-05", "type": "earnings"}, {"date": "2026-11-04", "type": "earnings"}]}

    def test_results_after_data_date_make_it_stale(self):
        s = analysis_view.staleness(self.CAL, "2026-07-28", today="2026-10-05")
        self.assertEqual(s, {"is_stale": True, "last_earnings": "2026-08-05"})

    def test_not_stale_before_next_results(self):
        self.assertFalse(analysis_view.staleness(self.CAL, "2026-08-10", today="2026-10-05")["is_stale"])


if __name__ == "__main__":
    unittest.main()

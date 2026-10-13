"""Save as base: workspace edits become a new analysis version through the ingest path."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import analysis_db
from markdown_to_json import parse_analysis
from app.services import base_edit
from app.services.analysis_view import macro_summary, score_links
from fakes import FakeSupabase
from test_model_v2 import _load_fixture, _model_block


class TestSaveAsBase(unittest.TestCase):
    def setUp(self):
        self.db = FakeSupabase()
        self.md = _load_fixture()
        analysis_db.confirm_ingest(parse_analysis(self.md, "BROS_v2_fixture.md"), supabase=self.db)
        self.year = _model_block(self.md)["meta"]["forecast_years"][0]

    def current(self):
        return [r for r in self.db.rows("analyses") if r["is_current"]]

    def test_edit_becomes_new_current_analysis(self):
        path = f"operating_margin[{self.year}].pct"
        old_id = self.current()[0]["id"]
        res = base_edit.save_as_base(self.db, "BROS", [{"path": path, "value": 12.5}])
        cur = self.current()
        self.assertEqual(len(cur), 1)
        self.assertNotEqual(cur[0]["id"], old_id)
        self.assertEqual(res["analysis_id"], cur[0]["id"])
        cell = cur[0]["model"]["operating_margin"][0]
        self.assertEqual(cell["pct"], 12.5)
        self.assertEqual(cell["source"], "assumption")
        self.assertIn("Edited in Portfolio Terminal", cell["ref"])
        self.assertIn("Base edited in Portfolio Terminal", cur[0]["raw_markdown"])
        self.assertEqual(len(self.db.rows("analyses")), 2)  # old version kept as history

    def test_no_change_is_rejected(self):
        old = _model_block(self.md)["operating_margin"][0]["pct"]
        with self.assertRaises(base_edit.BaseEditError):
            base_edit.save_as_base(self.db, "BROS", [{"path": f"operating_margin[{self.year}].pct", "value": old}])

    def test_actuals_keep_their_sources(self):
        cells = {
            "operating_margin": {"pct": 9.84, "source": "filing", "ref": "10-K"},
            "net_interest": {"value": -25.6, "source": "filing"},
            "tax_rate": {"pct": 13.5, "source": "filing"},
        }
        dry = base_edit.save_actuals(self.db, "BROS", cells, dry_run=True)
        self.assertIsNotNone(dry["actual"]["eps"])
        self.assertEqual(len(self.db.rows("analyses")), 1)  # dry run stores nothing
        base_edit.save_actuals(self.db, "BROS", cells)
        stored = self.current()[0]["model"]["actuals"]
        self.assertEqual(stored["operating_margin"], {"pct": 9.84, "source": "filing", "ref": "10-K"})
        self.assertNotIn("reported_eps", stored)  # empty skeleton fields aren't written back

    def test_actuals_reject_unknown_fields(self):
        with self.assertRaises(base_edit.BaseEditError):
            base_edit.save_actuals(self.db, "BROS", {"ebitda": {"value": 1}})


class TestMacroSummary(unittest.TestCase):
    def test_sensitivity_times_move_medium_counts_as_strong(self):
        links = [
            {"factor": "a", "direction": "bull", "strength": "strong"},   # rises, helps: +2
            {"factor": "b", "direction": "bear", "strength": "medium"},   # falls, bear: +2 (a falling cost is a tailwind)
            {"factor": "a", "direction": "bear", "strength": "mild"},     # rises, hurts: -1
            {"factor": "c", "direction": "bull", "strength": "strong"},   # flat: 0
            {"factor": "d", "direction": "bull", "strength": "strong"},   # no data: excluded
        ]
        scored = score_links(links, {"a": "up", "b": "down", "c": "flat", "d": None})
        self.assertEqual([m["effect"] for m in scored], [2, 2, -1, 0, None])
        s = macro_summary(scored)
        self.assertEqual((s["tailwind"], s["tailwind_links"]), (4, 2))
        self.assertEqual((s["headwind"], s["headwind_links"]), (-1, 1))
        self.assertEqual((s["neutral_links"], s["no_data_links"]), (1, 1))
        self.assertEqual((s["net"], s["verdict"]), (3, "strong tailwind"))


if __name__ == "__main__":
    unittest.main()

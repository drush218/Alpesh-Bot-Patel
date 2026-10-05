"""Scenario save / load / delete and workspace preview against the current analysis."""

import copy
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

from app.services import scenarios, workspace
from fakes import FakeSupabase
from test_model_v2 import _load_fixture, _model_block

PATH = "revenue.segments[Company-operated].growth[FY2027].pct"
ME, OTHER = "user-1", "user-2"


def _bau_fy27_growth(outputs):
    return outputs["scenarios"]["bau"][1]["segments"]["Company-operated"]["growth_pct"]


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.db = FakeSupabase()
        self.model = _model_block(_load_fixture())
        self.db.tables["instruments"] = [{"id": 1, "ticker": "BROS"}]
        self.db.tables["analyses"] = [{"id": 10, "instrument_id": 1, "is_current": True, "model": self.model}]

    def rebase(self, delta):
        """Add a newer current analysis where the overridden cell moved by delta."""
        newer = copy.deepcopy(self.model)
        newer["revenue"]["segments"][0]["growth"][1]["pct"] += delta
        self.db.tables["analyses"][0]["is_current"] = False
        self.db.tables["analyses"].append({"id": 11, "instrument_id": 1, "is_current": True, "model": newer})

    def test_preview_applies_edits_and_keeps_base(self):
        res = workspace.preview(self.db, "bros", [{"path": PATH, "value": 30.0}])
        self.assertEqual(res["errors"], [])
        self.assertEqual(_bau_fy27_growth(res["outputs"]), 30.0)
        self.assertEqual(res["base_outputs"], self.model["outputs"])

    def test_preview_reports_unknown_path(self):
        res = workspace.preview(self.db, "BROS", [{"path": "revenue.segments[Nope].growth[FY2027].pct", "value": 1}])
        self.assertEqual(res["could_not_apply"], ["revenue.segments[Nope].growth[FY2027].pct"])

    def test_save_rejects_unknown_path(self):
        with self.assertRaises(scenarios.PathError):
            workspace.save_scenario(self.db, ME, "BROS", "x", None, [{"path": "nope", "value": 1}])

    def test_save_list_load_delete(self):
        saved = workspace.save_scenario(self.db, ME, "BROS", "Fast growth", "note", [{"path": PATH, "value": 30.0}])
        row = self.db.rows("user_scenarios", id=saved["id"])[0]
        self.assertEqual(row["overrides"][0]["base_value"], scenarios.get_at(self.model, PATH))
        self.assertEqual(row["base_analysis_id"], 10)

        listed = workspace.list_scenarios(self.db, ME, "BROS")
        self.assertEqual([(s["name"], s["override_count"], s["on_current_base"]) for s in listed],
                         [("Fast growth", 1, True)])
        self.assertEqual(workspace.list_scenarios(self.db, OTHER, "BROS"), [])

        loaded = workspace.load_scenario(self.db, ME, "BROS", saved["id"])
        self.assertFalse(loaded["scenario"]["rebased"])
        self.assertEqual(_bau_fy27_growth(loaded["outputs"]), 30.0)

        with self.assertRaises(workspace.NotFound):
            workspace.delete_scenario(self.db, OTHER, "BROS", saved["id"])
        workspace.delete_scenario(self.db, ME, "BROS", saved["id"])
        self.assertEqual(self.db.rows("user_scenarios"), [])

    def test_resave_same_name_replaces(self):
        workspace.save_scenario(self.db, ME, "BROS", "A", None, [{"path": PATH, "value": 30.0}])
        workspace.save_scenario(self.db, ME, "BROS", "A", None, [{"path": PATH, "value": 28.0}])
        rows = self.db.rows("user_scenarios")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["overrides"][0]["value"], 28.0)

    def test_load_on_newer_base_flags_and_keeps_base_id(self):
        saved = workspace.save_scenario(self.db, ME, "BROS", "A", None, [{"path": PATH, "value": 30.0}])
        self.rebase(-2)
        loaded = workspace.load_scenario(self.db, ME, "BROS", saved["id"])
        self.assertTrue(loaded["scenario"]["rebased"])
        self.assertEqual(loaded["analysis_id"], 11)
        self.assertEqual(len(loaded["base_moved"]), 1)
        self.assertEqual(_bau_fy27_growth(loaded["outputs"]), 30.0)
        self.assertEqual(self.db.rows("user_scenarios")[0]["base_analysis_id"], 10)   # until re-saved
        self.assertFalse(workspace.list_scenarios(self.db, ME, "BROS")[0]["on_current_base"])

    def test_no_current_analysis(self):
        with self.assertRaises(workspace.NotFound):
            workspace.preview(self.db, "MSFT", [])


if __name__ == "__main__":
    unittest.main()

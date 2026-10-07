"""Webapp analysis upload: preview says new / replaces / duplicate; store goes through confirm_ingest."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
# settings_status imports app.config, which needs these; nothing here talks to Supabase.
for k in ("SUPABASE_URL", "SUPABASE_KEY", "FERNET_KEY"):
    os.environ.setdefault(k, "test")

from app.services import ingest, settings_status
from fakes import FakeSupabase
from test_model_v2 import _load_fixture, _model_block, _with_model


class TestIngestApi(unittest.TestCase):
    def setUp(self):
        self.db = FakeSupabase()
        self.md = _load_fixture()

    def test_preview_new_then_store_then_duplicate(self):
        p = ingest.preview(self.db, self.md, "BROS.md")
        self.assertTrue(p["ok"])
        self.assertEqual((p["ticker"], p["status"]), ("BROS", "new"))
        self.assertAlmostEqual(p["bau_eps"][-1]["eps"], 1.87, places=2)
        self.assertEqual(self.db.rows("analyses"), [])   # preview writes nothing

        res = ingest.store(self.db, self.md, "BROS.md")
        self.assertFalse(res["already_existed"])
        self.assertEqual(ingest.preview(self.db, self.md, "BROS.md")["status"], "duplicate")

    def test_changed_file_replaces_current(self):
        ingest.store(self.db, self.md, "BROS.md")
        model = _model_block(self.md)
        model["bottom_line"] = "Updated view."
        p = ingest.preview(self.db, _with_model(self.md, model), "BROS v2.md")
        self.assertEqual((p["status"], p["replaces_as_of"]), ("replaces", "2026-07-28"))

    def test_invalid_file_reports_errors(self):
        p = ingest.preview(self.db, "# Not an analysis\n\nhello", "x.md")
        self.assertFalse(p["ok"])
        self.assertTrue(p["errors"])
        with self.assertRaises(ingest.IngestError):
            ingest.store(self.db, "# Not an analysis", "x.md")

    def test_approve_proposal_adds_factor(self):
        ingest.store(self.db, self.md, "BROS.md")   # fixture proposes us_gasoline_retail
        settings_status.decide_proposal(self.db, "us_gasoline_retail", approve=True)
        self.assertEqual(self.db.rows("macro_factor_proposals", code="us_gasoline_retail")[0]["status"], "approved")
        self.assertTrue(self.db.rows("macro_factors", code="us_gasoline_retail"))


if __name__ == "__main__":
    unittest.main()

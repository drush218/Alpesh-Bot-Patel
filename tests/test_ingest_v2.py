"""
v2 ingest / workspace tests (claude-code-handoff/handoff/CLAUDE_CODE_PROMPT_model_v2.md section 8).

Covers 7 (scenario rebase flags "base moved"), 8 (re-ingest leaves the user scorecard alone),
and the ingest half of 9 (pending us_gasoline_retail proposal). analysis_db runs against an
in-memory fake of the supabase client, so no network.

The database halves of 4 (v_live_pe USD/USD and GBp-vs-USD) and 9 (pending code excluded
from the cross) are SQL views: see supabase/tests/v2_views.sql.

Run with: python -m unittest discover tests -v
"""

import copy
import itertools
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

import analysis_db
from markdown_to_json import parse_analysis
from app.services import scenarios, stock_model
from test_model_v2 import _load_fixture, _model_block, _with_model

FIXED_FACTORS = ["rates_policy", "rates_10y", "fx_usd", "oil", "natgas", "labour",
                 "consumer_spend", "credit_spreads", "inflation", "china_activity"]


# ---------------------------------------------------------------- fake supabase

class _Query:
    def __init__(self, db, table):
        self.db, self.table, self.filters, self.op, self.payload = db, table, [], "select", None
        self.on_conflict = None

    def select(self, *_):
        self.op = "select"
        return self

    def insert(self, rows):
        self.op, self.payload = "insert", rows
        return self

    def upsert(self, row, on_conflict=None):
        self.op, self.payload, self.on_conflict = "upsert", row, on_conflict
        return self

    def update(self, values):
        self.op, self.payload = "update", values
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, val):
        self.filters.append((col, val))
        return self

    def _match(self, row):
        return all(row.get(c) == v for c, v in self.filters)

    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        if self.op == "select":
            data = [dict(r) for r in rows if self._match(r)]
        elif self.op == "insert":
            new = self.payload if isinstance(self.payload, list) else [self.payload]
            data = []
            for r in new:
                r = copy.deepcopy(r)
                r.setdefault("id", next(self.db.ids))
                rows.append(r)
                data.append(dict(r))
        elif self.op == "upsert":
            key = self.on_conflict
            hit = [r for r in rows if r.get(key) == self.payload[key]]
            if hit:
                hit[0].update(self.payload)
                data = [dict(hit[0])]
            else:
                r = {**self.payload, "id": next(self.db.ids)}
                rows.append(r)
                data = [dict(r)]
        elif self.op == "update":
            data = []
            for r in rows:
                if self._match(r):
                    r.update(self.payload)
                    data.append(dict(r))
        else:  # delete, cascading to analysis children
            gone = [r for r in rows if self._match(r)]
            self.db.tables[self.table] = [r for r in rows if not self._match(r)]
            if self.table == "analyses":
                ids = {r["id"] for r in gone}
                for t, trs in self.db.tables.items():
                    self.db.tables[t] = [r for r in trs if r.get("analysis_id") not in ids]
            data = gone
        return type("Resp", (), {"data": data})()


class FakeSupabase:
    def __init__(self):
        self.ids = itertools.count(1)
        self.tables = {"macro_factors": [{"code": c, "name": c} for c in FIXED_FACTORS]}

    def table(self, name):
        return _Query(self, name)

    def rows(self, name, **where):
        return [r for r in self.tables.get(name, []) if all(r.get(k) == v for k, v in where.items())]


class _FakeDBCase(unittest.TestCase):
    def setUp(self):
        self.db = FakeSupabase()
        self._orig = analysis_db.init_supabase
        analysis_db.init_supabase = lambda: self.db

    def tearDown(self):
        analysis_db.init_supabase = self._orig

    def ingest(self, md):
        return analysis_db.confirm_ingest(parse_analysis(md, "BROS_v2_fixture.md"))


# ---------------------------------------------------------------- tests

class TestIngestWrites(_FakeDBCase):
    def test_children_written_and_promoted(self):
        aid, existed = self.ingest(_load_fixture())
        self.assertFalse(existed)
        self.assertEqual(len(self.db.rows("analysis_forecast", analysis_id=aid)), 9)
        self.assertTrue(self.db.rows("analyses", id=aid)[0]["is_current"])
        macro = self.db.rows("analysis_macro", analysis_id=aid)
        self.assertEqual(len(macro), len(_model_block(_load_fixture())["macro"]))
        levers = self.db.rows("analysis_levers", analysis_id=aid)
        self.assertEqual(len(levers), len(_model_block(_load_fixture())["levers"]))
        self.assertEqual(set(levers[0]) - {"id", "analysis_id"}, set(analysis_db.LEVER_COLUMNS))

    def test_same_file_twice_dedupes(self):
        aid, _ = self.ingest(_load_fixture())
        aid2, existed = self.ingest(_load_fixture())
        self.assertEqual((aid2, existed), (aid, True))
        self.assertEqual(len(self.db.rows("analyses")), 1)

    def test_legacy_payload_rejected(self):
        with open(os.path.join(ROOT, "tests", "fixtures", "BROS_DutchBros.md"), encoding="utf-8") as f:
            payload = parse_analysis(f.read())
        with self.assertRaisesRegex(ValueError, "Only v2"):
            analysis_db.confirm_ingest(payload)


class TestScenarioRebase(unittest.TestCase):
    """Test 7: an override survives a re-ingest where the base cell moved, and is flagged."""

    PATH = "revenue.segments[Company-operated].growth[FY2027].pct"

    def _inputs(self, model):
        return {k: v for k, v in model.items() if k not in ("outputs", "schema_version")}

    def test_override_kept_and_flagged_base_moved(self):
        base = self._inputs(_model_block(_load_fixture()))
        saved = [scenarios.make_override(base, self.PATH, 30.0)]
        saved_base = saved[0]["base_value"]

        newer = copy.deepcopy(base)
        newer["revenue"]["segments"][0]["growth"][1]["pct"] = saved_base - 2
        newer["revenue"]["segments"].reverse()       # reordering must not misapply by-name paths

        inputs, dropped, moved = scenarios.apply_overrides(newer, saved)
        self.assertEqual(dropped, [])
        self.assertEqual(scenarios.get_at(inputs, self.PATH), 30.0)
        self.assertEqual(len(moved), 1)
        self.assertEqual(moved[0]["note"], f"base moved: {saved_base} → {saved_base - 2}")

        model, errors, _ = stock_model.run(inputs)
        self.assertEqual(errors, [])
        fy27 = model["outputs"]["scenarios"]["bau"][1]
        self.assertEqual(fy27["segments"]["Company-operated"]["growth_pct"], 30.0)

    def test_unchanged_base_not_flagged(self):
        base = self._inputs(_model_block(_load_fixture()))
        _, dropped, moved = scenarios.apply_overrides(base, [scenarios.make_override(base, self.PATH, 30.0)])
        self.assertEqual((dropped, moved), ([], []))

    def test_missing_path_listed_as_could_not_apply(self):
        base = self._inputs(_model_block(_load_fixture()))
        saved = [scenarios.make_override(base, self.PATH, 30.0)]
        renamed = copy.deepcopy(base)
        renamed["revenue"]["segments"][0]["name"] = "Company shops"
        rolled = copy.deepcopy(base)
        rolled["meta"]["forecast_years"] = ["FY2028", "FY2029", "FY2030"]
        for newer in (renamed, rolled):
            inputs, dropped, moved = scenarios.apply_overrides(newer, saved)
            self.assertEqual(dropped, [self.PATH])
            self.assertEqual(inputs, newer)


class TestScorecardSurvivesReingest(_FakeDBCase):
    """Test 8: re-ingest leaves the user scorecard unchanged; scorecard_suggested updates."""

    def test_reingest(self):
        md = _load_fixture()
        aid1, _ = self.ingest(md)
        instrument_id = self.db.rows("analyses", id=aid1)[0]["instrument_id"]
        user_row = {"id": 999, "user_id": "u1", "instrument_id": instrument_id,
                    "growth": 3, "value": 2, "income": 1, "bull_catalysts": [], "bear_catalysts": []}
        self.db.tables["scorecards"] = [copy.deepcopy(user_row)]

        model = _model_block(md)
        model["scorecard_suggested"]["growth"]["score"] = 4
        aid2, existed = self.ingest(_with_model(md, model))

        self.assertFalse(existed)
        self.assertEqual(self.db.tables["scorecards"], [user_row])
        current = self.db.rows("analyses", instrument_id=instrument_id, is_current=True)
        self.assertEqual([a["id"] for a in current], [aid2])
        self.assertEqual(current[0]["model"]["scorecard_suggested"]["growth"]["score"], 4)
        self.assertFalse(self.db.rows("analyses", id=aid1)[0]["is_current"])


class TestProposedFactor(_FakeDBCase):
    """Test 9 (ingest half): BROS creates a pending us_gasoline_retail proposal; its macro row is stored."""

    def test_pending_proposal_created(self):
        aid, _ = self.ingest(_load_fixture())
        props = self.db.rows("macro_factor_proposals", code="us_gasoline_retail")
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0].get("status", "pending"), "pending")   # db default
        self.assertEqual(props[0]["first_proposed_by"], aid)
        self.assertEqual(props[0]["proposed_by_tickers"], ["BROS"])
        self.assertNotIn("us_gasoline_retail", [r["code"] for r in self.db.tables["macro_factors"]])
        self.assertEqual(len(self.db.rows("analysis_macro", analysis_id=aid, factor_code="us_gasoline_retail")), 1)

    def test_second_ticker_appended_not_duplicated(self):
        md = _load_fixture()
        self.ingest(md)
        model = _model_block(md)
        model["meta"]["ticker"] = "CAVA"
        self.ingest(_with_model(md, model))
        props = self.db.rows("macro_factor_proposals", code="us_gasoline_retail")
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0]["proposed_by_tickers"], ["BROS", "CAVA"])


if __name__ == "__main__":
    unittest.main()

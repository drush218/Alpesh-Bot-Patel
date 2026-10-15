"""
v2 stock-model ingest tests (stock-model v2 spec, section 8).

Covers the DB-free tests: 2 (v2 fixture parses), 3 (bad enum rejected), 5 (split macro rows kept
apart), 6 (vendored engine reproduces stored outputs). Test 1 (legacy byte-identical) is
tests/test_parser.py.

Run with: python -m unittest discover tests -v
"""

import copy
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

from markdown_to_json import AnalysisValidationError, parse_analysis
from app.services import stock_model

FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def _load_fixture():
    with open(os.path.join(FIXTURES, "BROS_v2_fixture.md"), encoding="utf-8") as f:
        return f.read()


def _model_block(md):
    return json.loads(re.search(r"```json stock-model\s*\n(.*?)\n```", md, re.S).group(1))


def _with_model(md, model):
    """Swap the json block in md for a modified model."""
    return re.sub(r"(```json stock-model\s*\n)(.*?)(\n```)",
                  lambda m: m.group(1) + json.dumps(model, indent=1) + m.group(3), md, flags=re.S)


class V2FixtureParses(unittest.TestCase):
    """Test 2."""

    @classmethod
    def setUpClass(cls):
        cls.payload = parse_analysis(_load_fixture(), "BROS_v2_fixture.md")

    def test_schema_version(self):
        self.assertEqual(self.payload["schema_version"], 2)
        self.assertEqual(self.payload["analysis"]["ticker"], "BROS")

    def test_forecast_has_nine_rows(self):
        self.assertEqual(len(self.payload["forecast"]), 9)
        self.assertEqual({(r["scenario"], r["fiscal_year"]) for r in self.payload["forecast"]},
                         {(s, y) for s in ("low", "bau", "high") for y in ("FY2026", "FY2027", "FY2028")})

    def test_bau_fy2028_eps(self):
        row = next(r for r in self.payload["forecast"]
                   if r["scenario"] == "bau" and r["fiscal_year"] == "FY2028")
        self.assertAlmostEqual(row["eps"], 1.87, places=2)

    def test_revenue_equals_sum_of_segments_every_row(self):
        for r in self.payload["forecast"]:
            segs = [s["revenue"] for s in self.payload["segment_forecast"]
                    if s["scenario"] == r["scenario"] and s["fiscal_year"] == r["fiscal_year"]]
            self.assertEqual(len(segs), 2)
            # segment revenues are rounded to 0.1 individually, so allow rounding slack
            self.assertAlmostEqual(sum(segs), r["revenue"], delta=0.1 * len(segs),
                                   msg=f"{r['scenario']} {r['fiscal_year']}")

    def test_tables_not_scraped(self):
        for legacy_key in ("bridge", "pe_basis", "forward_pe", "sensitivities"):
            self.assertNotIn(legacy_key, self.payload)

    def test_lever_factor_code_populated(self):
        self.assertEqual(self.payload["levers"][0]["macro_factor_code"], "labour")
        # only one lever uses 'labour', so no channel group
        self.assertIsNone(self.payload["levers"][0]["channel_group"])


class InvalidEnumRejected(unittest.TestCase):
    """Test 3."""

    def test_bad_strength_rejected_with_clear_error(self):
        md = _load_fixture()
        model = _model_block(md)
        model["macro"][0]["strength"] = "huge"
        with self.assertRaises(AnalysisValidationError) as ctx:
            parse_analysis(_with_model(md, model))
        self.assertIn("macro[0].strength", str(ctx.exception))
        self.assertIn("'huge'", str(ctx.exception))

    def test_unknown_factor_rejected_unless_proposed(self):
        md = _load_fixture()
        model = _model_block(md)
        model["proposed_factors"] = []   # us_gasoline_retail no longer declared
        with self.assertRaises(AnalysisValidationError) as ctx:
            parse_analysis(_with_model(md, model))
        self.assertIn("us_gasoline_retail", str(ctx.exception))


class SplitMacroRowsKeptApart(unittest.TestCase):
    """Test 5: two oil rows (demand, cost) are both stored and never summed."""

    def test_two_oil_rows(self):
        md = _load_fixture()
        model = _model_block(md)
        model["macro"].append({"factor": "oil", "channel": "demand", "direction": "bear",
                               "strength": "mild", "speed": "lagged", "ref": "Pump price → traffic"})
        payload = parse_analysis(_with_model(md, model))
        oil = [x for x in payload["macro"] if x["factor_code"] == "oil"]
        self.assertEqual(sorted(x["channel"] for x in oil), ["cost", "demand"])
        self.assertEqual({x["strength"] for x in oil}, {"mild"})

    def test_duplicate_factor_channel_rejected(self):
        md = _load_fixture()
        model = _model_block(md)
        model["macro"].append(dict(next(x for x in model["macro"] if x["factor"] == "oil")))
        with self.assertRaises(AnalysisValidationError):
            parse_analysis(_with_model(md, model))

    def test_shared_factor_levers_get_channel_group(self):
        md = _load_fixture()
        model = _model_block(md)
        extra = copy.deepcopy(model["levers"][0])
        extra["lever_name"] = "Distribution labour"
        model["levers"].append(extra)
        payload = parse_analysis(_with_model(md, model))
        self.assertEqual([l["channel_group"] for l in payload["levers"]], ["labour", "labour"])


class EngineParity(unittest.TestCase):
    """Test 6: stock_model.run(base inputs) reproduces the stored outputs exactly."""

    def test_run_reproduces_outputs(self):
        stored = _model_block(_load_fixture())
        inputs = {k: v for k, v in stored.items() if k not in ("outputs", "schema_version")}
        model, errors, _ = stock_model.run(inputs)
        self.assertEqual(errors, [])
        self.assertEqual(model["outputs"], stored["outputs"])


if __name__ == "__main__":
    unittest.main()

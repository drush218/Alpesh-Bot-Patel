"""
Golden-fixture test for markdown_to_json.py.

Re-parses tests/fixtures/BROS_DutchBros.md and asserts the result matches
tests/fixtures/BROS_parsed_sample.json exactly (aside from parsed_at, which is
a timestamp). This is what stops a future refactor from silently breaking the
_FACTOR_CODES ordering rules (see HandoverFiles/HANDOFF_claude_code.md section 4)
or any other part of the parser.

Run with: python -m unittest tests.test_parser -v
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from markdown_to_json import parse_analysis

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class GoldenFixtureTest(unittest.TestCase):
    def test_bros_matches_reference_output(self):
        with open(os.path.join(FIXTURES, "BROS_DutchBros.md"), encoding="utf-8") as f:
            md = f.read()
        with open(os.path.join(FIXTURES, "BROS_parsed_sample.json"), encoding="utf-8") as f:
            expected = json.load(f)

        actual = parse_analysis(md, expected.get("source_name"))

        for key in expected:
            if key == "parsed_at":
                continue
            self.assertEqual(
                actual.get(key), expected[key],
                msg=f"mismatch in payload['{key}']",
            )


if __name__ == "__main__":
    unittest.main()

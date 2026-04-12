"""T-201 / T-204 — mapper statistics[] SM → processed (sin DB)."""

from __future__ import annotations

import unittest

from apps.api.bt2_dsr_sm_statistics import (
    merge_sm_statistics_into_processed_statistics,
    sm_fixture_statistics_block,
)


class TestSmFixtureStatisticsBlock(unittest.TestCase):
    def test_corners_type_34(self) -> None:
        payload = {
            "statistics": [
                {"type_id": 34, "location": "home", "data": {"value": 6}},
                {"type_id": 34, "location": "away", "data": {"value": 2}},
            ]
        }
        b = sm_fixture_statistics_block(payload)
        assert b is not None
        self.assertTrue(b.get("available"))
        self.assertEqual(b.get("corners_count_home"), 6)
        self.assertEqual(b.get("corners_count_away"), 2)

    def test_merge_nested(self) -> None:
        st: dict = {"available": True, "home_form_last5": "WWD"}
        inner = {"available": True, "corners_count_home": 1, "corners_count_away": 1}
        merge_sm_statistics_into_processed_statistics(st, inner)
        self.assertIn("from_sm_fixture", st)
        self.assertEqual(st["from_sm_fixture"]["corners_count_home"], 1)


if __name__ == "__main__":
    unittest.main()

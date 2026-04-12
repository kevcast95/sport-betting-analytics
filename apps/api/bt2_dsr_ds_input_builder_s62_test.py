"""S6.2 — T-203/T-204: diagnostics.raw_fixture_missing y merge SM (mock cursor)."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from apps.api.bt2_dsr_ds_input_builder import apply_postgres_context_to_ds_item, build_ds_input_item
from apps.api.bt2_dsr_odds_aggregation import aggregate_odds_for_event


class TestApplyPostgresRawDiagnostics(unittest.TestCase):
    def _base_item(self):
        ko = datetime.now(tz=timezone.utc)
        agg = aggregate_odds_for_event(
            [
                ("b", "1x2", "1", 2.1, ko),
                ("b", "1x2", "X", 3.2, ko),
                ("b", "1x2", "2", 3.5, ko),
            ]
        )
        return build_ds_input_item(
            event_id=42,
            selection_tier="A",
            kickoff_utc=ko,
            event_status="scheduled",
            league_name="L",
            country=None,
            league_tier="S",
            home_team="H",
            away_team="A",
            agg=agg,
        )

    def test_raw_fixture_missing_when_no_row(self) -> None:
        item = self._base_item()
        cur = MagicMock()
        cur.fetchone.side_effect = [
            (None, None, None),
            None,
        ]
        apply_postgres_context_to_ds_item(
            cur,
            item,
            event_id=42,
            home_team_id=None,
            away_team_id=None,
            sportmonks_fixture_id=999,
            kickoff_utc=datetime.now(tz=timezone.utc),
        )
        self.assertTrue(item["diagnostics"]["raw_fixture_missing"])

    def test_raw_present_lineups_and_corners(self) -> None:
        item = self._base_item()
        payload = {
            "participants": [
                {"id": 10, "name": "H", "meta": {"location": "home"}},
                {"id": 20, "name": "A", "meta": {"location": "away"}},
            ],
            "lineups": [
                {"team_id": 10, "type_id": 11},
                {"team_id": 10, "type_id": 11},
                {"team_id": 20, "type_id": 11},
            ],
            "statistics": [
                {"type_id": 34, "location": "home", "data": {"value": 4}},
                {"type_id": 34, "location": "away", "data": {"value": 5}},
            ],
        }
        cur = MagicMock()
        cur.fetchone.side_effect = [
            (None, None, None),
            (payload,),
        ]
        apply_postgres_context_to_ds_item(
            cur,
            item,
            event_id=42,
            home_team_id=None,
            away_team_id=None,
            sportmonks_fixture_id=1001,
            kickoff_utc=datetime.now(tz=timezone.utc),
        )
        self.assertFalse(item["diagnostics"]["raw_fixture_missing"])
        self.assertTrue(item["diagnostics"]["lineups_ok"])
        self.assertTrue(item["diagnostics"]["statistics_ok"])
        fs = item["processed"]["statistics"].get("from_sm_fixture") or {}
        self.assertEqual(fs.get("corners_count_home"), 4)
        self.assertEqual(fs.get("corners_count_away"), 5)


if __name__ == "__main__":
    unittest.main()

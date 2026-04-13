"""Tests T-189 / T-190 — agregados histórico e ingest_meta (sin DB)."""

from __future__ import annotations

import unittest

from apps.api.bt2_dsr_context_queries import extract_lineups_summary_from_raw_payload, streaks_from_form


class TestStreaksFromForm(unittest.TestCase):
    def test_winning_run_trailing(self) -> None:
        s = streaks_from_form("DLLWWW")
        self.assertEqual(s["winning_run"], 3)
        self.assertEqual(s["unbeaten_run"], 3)
        self.assertEqual(s["winless_run"], 0)

    def test_winless_run(self) -> None:
        s = streaks_from_form("WWLL")
        self.assertEqual(s["winless_run"], 2)


class TestLineupsExtract(unittest.TestCase):
    def test_empty_payload(self) -> None:
        self.assertIsNone(extract_lineups_summary_from_raw_payload(None))
        self.assertIsNone(extract_lineups_summary_from_raw_payload({}))

    def test_counts_teams(self) -> None:
        lu = extract_lineups_summary_from_raw_payload(
            {
                "lineups": [
                    {"team_id": 1, "player_id": 10},
                    {"team_id": 1, "player_id": 11},
                    {"team_id": 2, "player_id": 20},
                ]
            }
        )
        assert lu is not None
        self.assertTrue(lu.get("available"))
        self.assertEqual(lu.get("teams_distinct"), 2)

    def test_starting_xi_per_side(self) -> None:
        lu = extract_lineups_summary_from_raw_payload(
            {
                "participants": [
                    {"id": 10, "meta": {"location": "home"}},
                    {"id": 20, "meta": {"location": "away"}},
                ],
                "lineups": [
                    {"team_id": 10, "type_id": 11},
                    {"team_id": 10, "type_id": 11},
                    {"team_id": 20, "type_id": 11},
                ],
            }
        )
        assert lu is not None
        self.assertEqual(lu.get("starting_xi_rows_home"), 2)
        self.assertEqual(lu.get("starting_xi_rows_away"), 1)


if __name__ == "__main__":
    unittest.main()

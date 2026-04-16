import unittest
from datetime import datetime, timezone

from apps.api.bt2_sofascore_map_match import match_sofa_event_for_sm_fixture


class SofaMapMatchTest(unittest.TestCase):
    def test_single_match(self) -> None:
        ko = datetime(2026, 4, 16, 17, 0, tzinfo=timezone.utc)
        stubs = [
            {
                "sofascore_event_id": 999001,
                "kickoff_utc": ko,
                "unique_tournament_id": 17,
                "home_name": "Arsenal",
                "away_name": "Chelsea",
            }
        ]
        sid, rev, note = match_sofa_event_for_sm_fixture(
            kickoff_utc=ko,
            home_name="Arsenal",
            away_name="Chelsea",
            expected_unique_tournament_id=17,
            sofa_stubs=stubs,
        )
        self.assertEqual(sid, 999001)
        self.assertFalse(rev)
        self.assertEqual(note, "")

    def test_ambiguous(self) -> None:
        ko = datetime(2026, 4, 16, 17, 0, tzinfo=timezone.utc)
        stub = {
            "kickoff_utc": ko,
            "unique_tournament_id": 17,
            "home_name": "Arsenal",
            "away_name": "Chelsea",
        }
        stubs = [
            {**stub, "sofascore_event_id": 1},
            {**stub, "sofascore_event_id": 2},
        ]
        sid, rev, note = match_sofa_event_for_sm_fixture(
            kickoff_utc=ko,
            home_name="Arsenal",
            away_name="Chelsea",
            expected_unique_tournament_id=17,
            sofa_stubs=stubs,
        )
        self.assertIsNone(sid)
        self.assertTrue(rev)
        self.assertEqual(note, "ambiguous")


if __name__ == "__main__":
    unittest.main()

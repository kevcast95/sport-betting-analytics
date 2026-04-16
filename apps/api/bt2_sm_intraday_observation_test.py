import unittest
from datetime import datetime, timedelta, timezone

from apps.api.bt2_sm_intraday_observation import (
    lineup_flags_from_sm_payload,
    market_flags_from_sm_payload,
    sm_observation_poll_interval_seconds,
    sm_observation_should_poll,
)


class SmObservationCadenceTest(unittest.TestCase):
    def test_too_early_no_interval(self) -> None:
        k = datetime(2026, 4, 16, 18, 0, tzinfo=timezone.utc)
        now = k - timedelta(hours=25)
        self.assertIsNone(sm_observation_poll_interval_seconds(now, k))

    def test_after_window(self) -> None:
        k = datetime(2026, 4, 16, 18, 0, tzinfo=timezone.utc)
        now = k + timedelta(minutes=20)
        self.assertIsNone(sm_observation_poll_interval_seconds(now, k))

    def test_60m_segment(self) -> None:
        k = datetime(2026, 4, 16, 18, 0, tzinfo=timezone.utc)
        now = k - timedelta(hours=10)
        self.assertEqual(sm_observation_poll_interval_seconds(now, k), 3600)

    def test_15m_segment(self) -> None:
        k = datetime(2026, 4, 16, 18, 0, tzinfo=timezone.utc)
        now = k - timedelta(hours=2)
        self.assertEqual(sm_observation_poll_interval_seconds(now, k), 900)

    def test_5m_pre_ko(self) -> None:
        k = datetime(2026, 4, 16, 18, 0, tzinfo=timezone.utc)
        now = k - timedelta(minutes=30)
        self.assertEqual(sm_observation_poll_interval_seconds(now, k), 300)

    def test_should_poll_first_time(self) -> None:
        k = datetime(2026, 4, 16, 18, 0, tzinfo=timezone.utc)
        now = k - timedelta(hours=8)
        self.assertTrue(sm_observation_should_poll(now, k, None))

    def test_should_poll_respects_interval(self) -> None:
        k = datetime(2026, 4, 16, 18, 0, tzinfo=timezone.utc)
        now = k - timedelta(hours=8)
        last = now - timedelta(minutes=30)
        self.assertFalse(sm_observation_should_poll(now, k, last))
        last2 = now - timedelta(hours=1, seconds=1)
        self.assertTrue(sm_observation_should_poll(now, k, last2))


class LineupFlagsTest(unittest.TestCase):
    def test_lineup_both_sides(self) -> None:
        home_id, away_id = 10, 20
        participants = [
            {"id": home_id, "meta": {"location": "home"}},
            {"id": away_id, "meta": {"location": "away"}},
        ]
        lineups = []
        for _ in range(11):
            lineups.append({"team_id": home_id, "type_id": 11})
        for _ in range(11):
            lineups.append({"team_id": away_id, "type_id": 11})
        hu, au, lav = lineup_flags_from_sm_payload({"participants": participants, "lineups": lineups})
        self.assertTrue(hu)
        self.assertTrue(au)
        self.assertTrue(lav)

    def test_lineup_one_side_only(self) -> None:
        home_id, away_id = 10, 20
        participants = [
            {"id": home_id, "meta": {"location": "home"}},
            {"id": away_id, "meta": {"location": "away"}},
        ]
        lineups = [{"team_id": home_id, "type_id": 11}] * 11
        hu, au, lav = lineup_flags_from_sm_payload({"participants": participants, "lineups": lineups})
        self.assertTrue(hu)
        self.assertFalse(au)
        self.assertFalse(lav)


class MarketFlagsTest(unittest.TestCase):
    def test_ft_ou_btts(self) -> None:
        payload = {
            "odds": [
                {"market_id": 1, "label": "1", "value": 2.1},
                {"market_id": 1, "label": "X", "value": 3.2},
                {"market_id": 1, "label": "2", "value": 3.5},
                {"market_id": 80, "label": "Over", "total": "2.5", "value": 1.9},
                {"market_id": 80, "label": "Under", "total": "2.5", "value": 2.0},
                {
                    "market_id": 999,
                    "market_description": "Both Teams To Score",
                    "label": "Yes",
                    "value": 1.8,
                },
                {
                    "market_id": 999,
                    "market_description": "Both Teams To Score",
                    "label": "No",
                    "value": 2.0,
                },
            ]
        }
        ft, ou, bt = market_flags_from_sm_payload(payload)
        self.assertTrue(ft)
        self.assertTrue(ou)
        self.assertTrue(bt)


if __name__ == "__main__":
    unittest.main()

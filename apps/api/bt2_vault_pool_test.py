"""Tests US-BE-030 — franjas locales y composición de pool (stdlib unittest)."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from apps.api.bt2_vault_pool import (
    VAULT_POOL_TARGET,
    VAULT_VALUE_POOL_UNIVERSE_MAX,
    compose_vault_daily_picks,
    is_event_available_for_pick_strict,
    kickoff_utc_to_time_band,
    time_band_from_local_time,
)


class TestTimeBandBoundaries(unittest.TestCase):
    def test_morning_afternoon_boundary(self) -> None:
        self.assertEqual(
            time_band_from_local_time(datetime(2026, 4, 7, 11, 59).time()),
            "morning",
        )
        self.assertEqual(
            time_band_from_local_time(datetime(2026, 4, 7, 12, 0).time()),
            "afternoon",
        )

    def test_afternoon_evening_boundary(self) -> None:
        self.assertEqual(
            time_band_from_local_time(datetime(2026, 4, 7, 17, 59).time()),
            "afternoon",
        )
        self.assertEqual(
            time_band_from_local_time(datetime(2026, 4, 7, 18, 0).time()),
            "evening",
        )

    def test_evening_overnight(self) -> None:
        self.assertEqual(
            time_band_from_local_time(datetime(2026, 4, 7, 22, 59).time()),
            "evening",
        )
        self.assertEqual(
            time_band_from_local_time(datetime(2026, 4, 7, 23, 0).time()),
            "evening",
        )
        self.assertEqual(
            time_band_from_local_time(datetime(2026, 4, 7, 23, 59).time()),
            "evening",
        )
        self.assertEqual(
            time_band_from_local_time(datetime(2026, 4, 7, 7, 59).time()),
            "morning",
        )
        self.assertEqual(
            time_band_from_local_time(datetime(2026, 4, 7, 5, 59).time()),
            "overnight",
        )


class TestKickoffToBand(unittest.TestCase):
    def test_utc_kickoff_bogota(self) -> None:
        tz = ZoneInfo("America/Bogota")
        # 2026-04-07 13:00 UTC = 08:00 Bogota → morning edge (08:00 inclusive)
        ko = datetime(2026, 4, 7, 13, 0, tzinfo=timezone.utc)
        self.assertEqual(kickoff_utc_to_time_band(ko, tz), "morning")


class TestComposePool(unittest.TestCase):
    def test_caps_at_universe_max_with_synthetic_rows(self) -> None:
        tz = ZoneInfo("America/Bogota")
        base = datetime(2026, 4, 7, 14, 0, tzinfo=timezone.utc)
        rows = [(i, base + timedelta(hours=(i % 6)), float(i)) for i in range(1, 40)]
        out = compose_vault_daily_picks(rows, tz)
        self.assertLessEqual(len(out), VAULT_VALUE_POOL_UNIVERSE_MAX)
        self.assertGreater(len(out), 0)

    def test_below_target_when_few_events(self) -> None:
        tz = ZoneInfo("UTC")
        rows = [(1, datetime(2026, 4, 7, 15, 0, tzinfo=timezone.utc), 0.1)]
        out = compose_vault_daily_picks(rows, tz)
        self.assertEqual(len(out), 1)
        self.assertLess(len(out), VAULT_POOL_TARGET)

    def test_t178_empty_premium_set_forces_standard(self) -> None:
        tz = ZoneInfo("UTC")
        ko = datetime(2026, 4, 7, 15, 0, tzinfo=timezone.utc)
        rows = [(1, ko, 0.1), (2, ko + timedelta(hours=1), 0.1)]
        out = compose_vault_daily_picks(rows, tz, premium_eligible_event_ids=set())
        for _eid, tier, _b in out:
            self.assertEqual(tier, "standard")


class TestStrictKickoff(unittest.TestCase):
    def test_after_kickoff_not_available(self) -> None:
        ko = datetime(2026, 4, 7, 10, 0, tzinfo=timezone.utc)
        now = datetime(2026, 4, 7, 10, 1, tzinfo=timezone.utc)
        self.assertFalse(
            is_event_available_for_pick_strict(
                event_status="scheduled",
                kickoff_utc=ko,
                now_utc=now,
            )
        )

    def test_before_kickoff_available(self) -> None:
        ko = datetime(2026, 4, 7, 10, 0, tzinfo=timezone.utc)
        now = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)
        self.assertTrue(
            is_event_available_for_pick_strict(
                event_status="scheduled",
                kickoff_utc=ko,
                now_utc=now,
            )
        )


if __name__ == "__main__":
    unittest.main()

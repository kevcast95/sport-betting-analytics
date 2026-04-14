"""Tests mínimos del job de evaluación oficial (T-232 helpers)."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from apps.api.bt2_official_evaluation_job import (
    apply_resolution_for_storage,
    hit_rate_on_scored_pct,
)
from apps.api.bt2_official_truth_resolver import OfficialEvaluationResolution


class TestHitRateOnScored(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(hit_rate_on_scored_pct(1, 1), 50.0)

    def test_empty(self) -> None:
        self.assertIsNone(hit_rate_on_scored_pct(0, 0))


class TestApplyResolutionForStorage(unittest.TestCase):
    def test_pending_clears_evaluated_at(self) -> None:
        now = datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc)
        r = OfficialEvaluationResolution(
            "pending_result",
            None,
            None,
            {"event_status": "scheduled"},
        )
        d = apply_resolution_for_storage(r, now)
        self.assertIsNone(d["evaluated_at"])

    def test_hit_sets_evaluated_at(self) -> None:
        now = datetime(2026, 4, 9, 12, 0, tzinfo=timezone.utc)
        r = OfficialEvaluationResolution(
            "evaluated_hit",
            None,
            "bt2_events_cdm",
            {"result_home": 1, "result_away": 0},
        )
        d = apply_resolution_for_storage(r, now)
        self.assertEqual(d["evaluated_at"], now)
        self.assertIsNone(d["no_evaluable_reason"])


if __name__ == "__main__":
    unittest.main()

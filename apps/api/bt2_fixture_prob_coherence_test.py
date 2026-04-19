"""Tests §1.3 — coherencia probabilística MVP sobre consensus."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from apps.api.bt2_fixture_prob_coherence import evaluate_fixture_prob_coherence, proportional_devig_three_way
from apps.api.bt2_dsr_contract import DsProbCoherenceDiagnostics, validate_ds_input_item_dict
from apps.api.bt2_dsr_ds_input_builder import build_ds_input_item
from apps.api.bt2_dsr_odds_aggregation import aggregate_odds_for_event


class TestProbCoherence(unittest.TestCase):
    def test_proportional_devig_three_way_sums_one(self) -> None:
        a, b, c = proportional_devig_three_way(2.0, 3.0, 5.0)
        self.assertAlmostEqual(a + b + c, 1.0, places=9)

    def test_na_without_1x2(self) -> None:
        diag = evaluate_fixture_prob_coherence({"BTTS": {"yes": 1.9, "no": 1.9}})
        self.assertEqual(diag.flag, "coherence_na")
        self.assertIn("missing_or_invalid_ft_1x2_consensus", diag.notes)

    def test_ok_when_thresholds_relaxed(self) -> None:
        consensus = {
            "FT_1X2": {"home": 2.5, "draw": 3.2, "away": 3.4},
            "OU_GOALS_2_5": {"over_2_5": 2.0, "under_2_5": 2.0},
        }
        diag = evaluate_fixture_prob_coherence(
            consensus,
            max_raw_overround_1x2=99.0,
            max_ft_1x2_spread=99.0,
            max_raw_overround_ou25=99.0,
        )
        self.assertEqual(diag.flag, "coherence_ok")
        self.assertEqual(diag.notes, [])
        self.assertIsNotNone(diag.ft_1x2_implied_sum_raw)


class TestProbCoherenceInDsInput(unittest.TestCase):
    def test_build_ds_input_includes_prob_coherence(self) -> None:
        ko = datetime.now(tz=timezone.utc)
        agg = aggregate_odds_for_event(
            [
                ("b", "1x2", "1", 2.1, ko),
                ("b", "1x2", "X", 3.2, ko),
                ("b", "1x2", "2", 3.5, ko),
            ]
        )
        item = build_ds_input_item(
            event_id=1,
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
        pc = item["diagnostics"]["prob_coherence"]
        validate_ds_input_item_dict(item)
        self.assertIsInstance(pc, dict)
        DsProbCoherenceDiagnostics.model_validate(pc)


if __name__ == "__main__":
    unittest.main()

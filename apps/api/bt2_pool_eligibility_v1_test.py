"""T-237 — Tests por causa principal de descarte (elegibilidad pool v1)."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds
from apps.api.bt2_pool_eligibility_v1 import (
    ELIGIBILITY_RULE_VERSION_V1,
    evaluate_pool_eligibility_v1,
    assert_pool_eligibility_discard_code,
)


def _agg_ft_only() -> AggregatedOdds:
    return AggregatedOdds(
        consensus={
            "FT_1X2": {"home": 2.0, "draw": 3.2, "away": 3.5},
        },
        market_coverage={"FT_1X2": True},
        markets_available=["FT_1X2"],
        by_bookmaker=[],
    )


def _agg_two_families() -> AggregatedOdds:
    return AggregatedOdds(
        consensus={
            "FT_1X2": {"home": 2.0, "draw": 3.2, "away": 3.5},
            "OU_GOALS_2_5": {"over_2_5": 1.95, "under_2_5": 1.95},
        },
        market_coverage={"FT_1X2": True, "OU_GOALS_2_5": True},
        markets_available=["FT_1X2", "OU_GOALS_2_5"],
        by_bookmaker=[],
    )


def _base_kw(agg: AggregatedOdds):
    return dict(
        sportmonks_fixture_id=12345,
        home_team_id=1,
        away_team_id=2,
        kickoff_utc=datetime(2026, 4, 10, 18, 0, tzinfo=timezone.utc),
        home_team_name="A",
        away_team_name="B",
        agg=agg,
        ds_fetch_errors=[],
        raw_fixture_missing=False,
    )


class TestPoolEligibilityV1(unittest.TestCase):
    def test_eligible_two_families_clean_ds(self) -> None:
        r = evaluate_pool_eligibility_v1(**_base_kw(_agg_two_families()))
        self.assertTrue(r.is_eligible)
        self.assertIsNone(r.primary_discard_reason)
        self.assertEqual(r.detail.get("rule_version"), ELIGIBILITY_RULE_VERSION_V1)

    def test_missing_fixture_no_sm_id(self) -> None:
        kw = _base_kw(_agg_two_families())
        kw["sportmonks_fixture_id"] = None
        r = evaluate_pool_eligibility_v1(**kw)
        self.assertFalse(r.is_eligible)
        self.assertEqual(r.primary_discard_reason, "MISSING_FIXTURE_CORE")

    def test_missing_fixture_no_teams(self) -> None:
        kw = _base_kw(_agg_two_families())
        kw["home_team_id"] = None
        r = evaluate_pool_eligibility_v1(**kw)
        self.assertEqual(r.primary_discard_reason, "MISSING_FIXTURE_CORE")

    def test_missing_fixture_no_kickoff(self) -> None:
        kw = _base_kw(_agg_two_families())
        kw["kickoff_utc"] = None
        r = evaluate_pool_eligibility_v1(**kw)
        self.assertEqual(r.primary_discard_reason, "MISSING_FIXTURE_CORE")

    def test_missing_fixture_bad_names(self) -> None:
        kw = _base_kw(_agg_two_families())
        kw["home_team_name"] = "unknown"
        r = evaluate_pool_eligibility_v1(**kw)
        self.assertEqual(r.primary_discard_reason, "MISSING_FIXTURE_CORE")

    def test_missing_valid_odds(self) -> None:
        agg = AggregatedOdds(
            consensus={},
            market_coverage={},
            markets_available=[],
            by_bookmaker=[],
        )
        r = evaluate_pool_eligibility_v1(**_base_kw(agg))
        self.assertEqual(r.primary_discard_reason, "MISSING_VALID_ODDS")

    def test_insufficient_market_families(self) -> None:
        r = evaluate_pool_eligibility_v1(**_base_kw(_agg_ft_only()))
        self.assertEqual(r.primary_discard_reason, "INSUFFICIENT_MARKET_FAMILIES")

    def test_missing_ds_input_critical_raw_flag(self) -> None:
        kw = {**_base_kw(_agg_two_families()), "raw_fixture_missing": True}
        r = evaluate_pool_eligibility_v1(**kw)
        self.assertEqual(r.primary_discard_reason, "MISSING_DS_INPUT_CRITICAL")

    def test_missing_ds_input_critical_fetch_error(self) -> None:
        kw = {
            **_base_kw(_agg_two_families()),
            "ds_fetch_errors": ["lineups:no_raw_sportmonks_row"],
        }
        r = evaluate_pool_eligibility_v1(**kw)
        self.assertEqual(r.primary_discard_reason, "MISSING_DS_INPUT_CRITICAL")

    def test_assert_discard_code_rejects_unknown(self) -> None:
        with self.assertRaises(ValueError):
            assert_pool_eligibility_discard_code("FOO")


if __name__ == "__main__":
    unittest.main()

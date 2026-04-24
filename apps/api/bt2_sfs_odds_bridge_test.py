"""Tests puente SM+SFS → tuplas agregador."""

from __future__ import annotations

import unittest

from apps.api.bt2_dsr_odds_aggregation import aggregate_odds_for_event
from apps.api.bt2_sfs_odds_bridge import canonical_sfs_rows_to_snapshot_tuples


class TestSfsOddsBridge(unittest.TestCase):
    def test_merged_rows_aggregate_to_non_1x2(self) -> None:
        manual = [
            {"family": "FT_1X2", "selection": "1", "price": 2.0},
            {"family": "OU_GOALS_2_5", "selection": "OVER", "price": 1.9},
            {"family": "OU_GOALS_2_5", "selection": "UNDER", "price": 1.9},
            {"family": "BTTS", "selection": "yes", "price": 1.8},
            {"family": "BTTS", "selection": "no", "price": 2.0},
            {"family": "DOUBLE_CHANCE", "selection": "1X", "price": 1.3},
        ]
        tuples = canonical_sfs_rows_to_snapshot_tuples(manual)
        agg = aggregate_odds_for_event(tuples, min_decimal=1.30)
        self.assertIn("OU_GOALS_2_5", agg.markets_available)
        self.assertIn("BTTS", agg.markets_available)


if __name__ == "__main__":
    unittest.main()

"""Tests mezcla de mercados en slate (bt2_vault_market_mix)."""

from __future__ import annotations

import unittest

from apps.api.bt2_vault_market_mix import (
    market_diversity_family,
    order_indices_for_top_slate_diversity,
)


class TestMarketDiversityFamily(unittest.TestCase):
    def test_ft_1x2(self) -> None:
        self.assertEqual(market_diversity_family("FT_1X2"), "FT_1X2")

    def test_ou_goals_collapsed(self) -> None:
        self.assertEqual(market_diversity_family("OU_GOALS_2_5"), "OU_GOALS")
        self.assertEqual(market_diversity_family("OU_GOALS_1_5"), "OU_GOALS")

    def test_btts(self) -> None:
        self.assertEqual(market_diversity_family("BTTS"), "BTTS")

    def test_double_chance(self) -> None:
        self.assertEqual(market_diversity_family("DOUBLE_CHANCE_1X"), "DOUBLE_CHANCE")


class TestOrderIndicesForTopSlateDiversity(unittest.TestCase):
    def test_prefers_distinct_families_in_top_k(self) -> None:
        mmcs = [
            "FT_1X2",
            "FT_1X2",
            "FT_1X2",
            "OU_GOALS_2_5",
            "BTTS",
            "FT_1X2",
        ]
        perm = order_indices_for_top_slate_diversity(mmcs, top_k=5)
        self.assertEqual(perm[:3], [0, 3, 4])
        self.assertEqual(set(perm), set(range(6)))

    def test_tie_break_by_original_index(self) -> None:
        mmcs = ["FT_1X2", "FT_1X2", "FT_1X2"]
        perm = order_indices_for_top_slate_diversity(mmcs, top_k=5)
        self.assertEqual(perm, [0, 1, 2])

    def test_empty_and_single(self) -> None:
        self.assertEqual(order_indices_for_top_slate_diversity([], top_k=5), [])
        self.assertEqual(order_indices_for_top_slate_diversity(["FT_1X2"], top_k=5), [0])


if __name__ == "__main__":
    unittest.main()

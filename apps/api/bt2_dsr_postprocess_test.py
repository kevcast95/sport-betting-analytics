"""Tests Post-DSR T-181."""

from __future__ import annotations

import unittest

from apps.api.bt2_dsr_postprocess import narrative_contradicts_ft_1x2, postprocess_dsr_pick


class TestPostDsr(unittest.TestCase):
    def test_narrative_contradicts_home_when_away_win_claimed(self) -> None:
        self.assertTrue(
            narrative_contradicts_ft_1x2(
                "home",
                "Victoria visitante clara por mejor momento.",
            )
        )

    def test_narrative_contradicts_home_when_visitor_value_framing_opens(self) -> None:
        """Regresión: pick local pero razon abre elogiando línea del visitante (caso Carabobo / Bragantino)."""
        self.assertTrue(
            narrative_contradicts_ft_1x2(
                "home",
                "Visitante con cuota con buen valor en comparación cruzada.",
            )
        )

    def test_omits_pick_when_razon_contradicts_selection(self) -> None:
        consensus = {"FT_1X2": {"home": 2.0, "draw": 3.0, "away": 3.5}}
        cov = {"FT_1X2": True}
        r = postprocess_dsr_pick(
            narrative_es="Empate muy probable; reparten puntos.",
            confidence_label="high",
            market_canonical="FT_1X2",
            selection_canonical="home",
            model_declared_odds=2.0,
            consensus=consensus,
            market_coverage=cov,
            event_id=9,
        )
        self.assertIsNone(r)

    def test_omits_pick_visitor_value_framing_vs_home_selection(self) -> None:
        consensus = {"FT_1X2": {"home": 2.0, "draw": 3.0, "away": 3.5}}
        cov = {"FT_1X2": True}
        r = postprocess_dsr_pick(
            narrative_es="Visitante con cuota con buen valor en comparación cruzada.",
            confidence_label="medium",
            market_canonical="FT_1X2",
            selection_canonical="home",
            model_declared_odds=3.55,
            consensus=consensus,
            market_coverage=cov,
            event_id=38,
        )
        self.assertIsNone(r)

    def test_omits_when_market_not_in_coverage(self) -> None:
        consensus = {"FT_1X2": {"home": 2.0, "draw": 3.0, "away": 3.5}}
        cov = {"FT_1X2": False}
        r = postprocess_dsr_pick(
            narrative_es="x",
            confidence_label="high",
            market_canonical="FT_1X2",
            selection_canonical="home",
            model_declared_odds=2.0,
            consensus=consensus,
            market_coverage=cov,
            event_id=9,
        )
        self.assertIsNone(r)

    def test_persists_aligned_pick(self) -> None:
        consensus = {"FT_1X2": {"home": 2.0, "draw": 3.0, "away": 3.5}}
        cov = {"FT_1X2": True}
        r = postprocess_dsr_pick(
            narrative_es="lectura",
            confidence_label="medium",
            market_canonical="FT_1X2",
            selection_canonical="home",
            model_declared_odds=2.5,
            consensus=consensus,
            market_coverage=cov,
            event_id=9,
        )
        self.assertIsNotNone(r)
        assert r is not None
        self.assertEqual(r[2], "FT_1X2")
        self.assertEqual(r[3], "home")

    def test_caps_high_conf_when_model_odds_extreme(self) -> None:
        consensus = {"FT_1X2": {"home": 2.0, "draw": 3.0, "away": 3.5}}
        cov = {"FT_1X2": True}
        r = postprocess_dsr_pick(
            narrative_es="x",
            confidence_label="high",
            market_canonical="FT_1X2",
            selection_canonical="home",
            model_declared_odds=20.0,
            consensus=consensus,
            market_coverage=cov,
            event_id=9,
        )
        self.assertIsNotNone(r)
        assert r is not None
        self.assertEqual(r[1], "medium")


if __name__ == "__main__":
    unittest.main()

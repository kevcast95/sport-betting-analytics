"""T-230 — Resolver oficial: hit, miss, void, no_evaluable, pending (ACTA T-244)."""

from __future__ import annotations

import unittest

from apps.api.bt2_official_truth_resolver import (
    TRUTH_SOURCE_BT2_EVENTS_CDM,
    normalize_official_eval_market,
    normalize_official_eval_selection,
    resolve_official_evaluation_from_cdm_truth,
)


class TestNormalizeMarketActaAliases(unittest.TestCase):
    def test_acta_1x2(self) -> None:
        self.assertEqual(normalize_official_eval_market("1X2"), "FT_1X2")
        self.assertEqual(normalize_official_eval_market("FT_1X2"), "FT_1X2")

    def test_acta_ou25(self) -> None:
        self.assertEqual(normalize_official_eval_market("TOTAL_GOALS_OU_2_5"), "OU_GOALS_2_5")
        self.assertEqual(normalize_official_eval_market("OU_GOALS_2_5"), "OU_GOALS_2_5")

    def test_btts_supported(self) -> None:
        self.assertEqual(normalize_official_eval_market("BTTS"), "BTTS")


class TestResolveOfficialEvaluation(unittest.TestCase):
    def test_hit_1x2_home(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="FT_1X2",
            selection_canonical="home",
            result_home=2,
            result_away=1,
            event_status="finished",
        )
        self.assertEqual(r.evaluation_status, "evaluated_hit")
        self.assertIsNone(r.no_evaluable_reason)
        self.assertEqual(r.truth_source, TRUTH_SOURCE_BT2_EVENTS_CDM)
        self.assertEqual(r.truth_payload_ref["result_home"], 2)
        self.assertEqual(r.truth_payload_ref["result_away"], 1)

    def test_miss_1x2_home(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="1X2",
            selection_canonical="home",
            result_home=0,
            result_away=1,
            event_status="finished",
        )
        self.assertEqual(r.evaluation_status, "evaluated_miss")

    def test_hit_ou_over(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="OU_GOALS_2_5",
            selection_canonical="over_2_5",
            result_home=2,
            result_away=2,
            event_status="finished",
        )
        self.assertEqual(r.evaluation_status, "evaluated_hit")

    def test_void_cancelled_event(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="FT_1X2",
            selection_canonical="home",
            result_home=None,
            result_away=None,
            event_status="cancelled",
        )
        self.assertEqual(r.evaluation_status, "void")
        self.assertEqual(r.truth_payload_ref["void_catalog_code"], "VOID_OFFICIAL_EVENT")

    def test_hit_btts_yes_both_scored(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="BTTS",
            selection_canonical="yes",
            result_home=1,
            result_away=2,
            event_status="finished",
        )
        self.assertEqual(r.evaluation_status, "evaluated_hit")

    def test_miss_btts_yes_not_both(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="BTTS",
            selection_canonical="yes",
            result_home=1,
            result_away=0,
            event_status="finished",
        )
        self.assertEqual(r.evaluation_status, "evaluated_miss")

    def test_hit_btts_no_nil_nil(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="BTTS",
            selection_canonical="no",
            result_home=0,
            result_away=0,
            event_status="finished",
        )
        self.assertEqual(r.evaluation_status, "evaluated_hit")

    def test_no_evaluable_bad_selection(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="FT_1X2",
            selection_canonical="over_2_5",
            result_home=1,
            result_away=1,
            event_status="finished",
        )
        self.assertEqual(r.evaluation_status, "no_evaluable")
        self.assertEqual(r.no_evaluable_reason, "MARKET_MAPPING_UNRESOLVED")

    def test_pending_scheduled_no_scores(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="FT_1X2",
            selection_canonical="draw",
            result_home=None,
            result_away=None,
            event_status="scheduled",
        )
        self.assertEqual(r.evaluation_status, "pending_result")
        self.assertIsNone(r.truth_source)

    def test_pending_scheduled_with_scores_stale_cdm(self) -> None:
        """CDM puede tener marcador (p. ej. CURRENT) con status aún no `finished`."""
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="FT_1X2",
            selection_canonical="home",
            result_home=2,
            result_away=1,
            event_status="scheduled",
        )
        self.assertEqual(r.evaluation_status, "pending_result")
        self.assertIsNone(r.truth_source)

    def test_pending_live_with_scores(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="FT_1X2",
            selection_canonical="home",
            result_home=1,
            result_away=0,
            event_status="live",
        )
        self.assertEqual(r.evaluation_status, "pending_result")
        self.assertIsNone(r.truth_source)

    def test_void_postponed_with_scores(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="FT_1X2",
            selection_canonical="home",
            result_home=2,
            result_away=1,
            event_status="postponed",
        )
        self.assertEqual(r.evaluation_status, "void")
        self.assertEqual(r.truth_source, TRUTH_SOURCE_BT2_EVENTS_CDM)

    def test_no_evaluable_finished_missing_scores(self) -> None:
        r = resolve_official_evaluation_from_cdm_truth(
            market_canonical="FT_1X2",
            selection_canonical="away",
            result_home=None,
            result_away=None,
            event_status="finished",
        )
        self.assertEqual(r.evaluation_status, "no_evaluable")
        self.assertEqual(r.no_evaluable_reason, "MISSING_TRUTH_SOURCE")


class TestSelectionNormalization(unittest.TestCase):
    def test_btts_yes_no(self) -> None:
        self.assertEqual(normalize_official_eval_selection("BTTS", "yes"), "yes")
        self.assertEqual(normalize_official_eval_selection("BTTS", "no"), "no")
        self.assertIsNone(normalize_official_eval_selection("BTTS", "home"))

    def test_ou_aliases(self) -> None:
        self.assertEqual(
            normalize_official_eval_selection("OU_GOALS_2_5", "over_2_5"),
            "over_2_5",
        )
        self.assertIsNone(
            normalize_official_eval_selection("OU_GOALS_2_5", "over_1_5"),
        )


if __name__ == "__main__":
    unittest.main()

"""Tests T-228 — literales ACTA T-244 y validadores de evaluación oficial."""

from __future__ import annotations

import unittest

from apps.api.bt2_official_evaluation import (
    NO_EVALUABLE_REASON_CODES_V1,
    OFFICIAL_EVALUATION_STATUSES_V1,
    Bt2OfficialEvaluationStatus,
    assert_no_evaluable_reason_code,
    assert_official_evaluation_status,
)


class TestOfficialEvaluationStatuses(unittest.TestCase):
    def test_enum_matches_tuple_and_acta(self) -> None:
        expected = (
            "pending_result",
            "evaluated_hit",
            "evaluated_miss",
            "void",
            "no_evaluable",
        )
        self.assertEqual(OFFICIAL_EVALUATION_STATUSES_V1, expected)
        self.assertEqual(
            {s.value for s in Bt2OfficialEvaluationStatus},
            set(expected),
        )

    def test_assert_status_accepts_all_v1(self) -> None:
        for s in OFFICIAL_EVALUATION_STATUSES_V1:
            assert_official_evaluation_status(s)

    def test_assert_status_rejects_alias(self) -> None:
        with self.assertRaises(ValueError):
            assert_official_evaluation_status("evaluated_void_or_push")


class TestNoEvaluableReasonCatalog(unittest.TestCase):
    def test_catalog_size_acta(self) -> None:
        self.assertEqual(len(NO_EVALUABLE_REASON_CODES_V1), 9)

    def test_assert_reason_accepts_known_code(self) -> None:
        assert_no_evaluable_reason_code("OUTSIDE_SUPPORTED_MARKET_V1")

    def test_assert_reason_rejects_unknown(self) -> None:
        with self.assertRaises(ValueError):
            assert_no_evaluable_reason_code("CUSTOM_REASON")


if __name__ == "__main__":
    unittest.main()

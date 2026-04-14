"""Tests US-BE-052 — resumen Fase 1 y contrato JSON de ejemplo (T-240)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from apps.api.bt2_admin_fase1_summary import compute_pool_coverage_block
from apps.api.bt2_schemas import Bt2AdminFase1OperationalSummaryOut


class TestComputePoolCoverageBlock(unittest.TestCase):
    def test_counts_and_no_audit_bucket(self) -> None:
        cands = [1, 2, 3]
        latest = {1: (True, None), 2: (False, "MISSING_VALID_ODDS")}
        b = compute_pool_coverage_block(cands, latest)
        self.assertEqual(b["candidate_events_count"], 3)
        self.assertEqual(b["eligible_events_count"], 1)
        self.assertEqual(b["events_with_latest_audit"], 2)
        self.assertEqual(b["pool_discard_reason_breakdown"]["MISSING_VALID_ODDS"], 1)
        self.assertEqual(b["pool_discard_reason_breakdown"]["(sin auditoría reciente)"], 1)


class TestFase1ExampleFixture(unittest.TestCase):
    def test_example_json_validates(self) -> None:
        path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "bt2_admin_fase1_operational_summary.example.json"
        )
        raw = json.loads(path.read_text(encoding="utf-8"))
        m = Bt2AdminFase1OperationalSummaryOut.model_validate(raw)
        self.assertEqual(m.operating_day_key, "2026-04-09")
        self.assertEqual(len(m.precision_by_market), 2)


if __name__ == "__main__":
    unittest.main()

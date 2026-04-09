"""Tests Sprint 06 — DSR contrato, mercados canónicos, reglas, DeepSeek por lote (T-170)."""

from __future__ import annotations

import io
import json
import unittest
import urllib.error

from apps.api.bt2_dsr_contract import (
    PIPELINE_VERSION_DEFAULT,
    assert_no_forbidden_ds_keys,
)
from apps.api import bt2_dsr_deepseek as dsr_deepseek
from apps.api.bt2_dsr_deepseek import DsrBatchCandidate, deepseek_suggest_batch
from apps.api.bt2_dsr_suggest import (
    PIPELINE_VERSION_DEEPSEEK,
    suggest_for_snapshot_row,
    suggest_from_candidate_row,
)
from apps.api.bt2_market_canonical import evaluate_model_vs_result, normalized_pick_to_canonical


class TestDsrAntiLeak(unittest.TestCase):
    def test_rejects_result_home(self) -> None:
        with self.assertRaises(ValueError):
            assert_no_forbidden_ds_keys({"odds": {"result_home": 2}})

    def test_allows_safe_odds(self) -> None:
        assert_no_forbidden_ds_keys({"event_id": 1, "odds": {"home": 2.1}})


class TestCanonical(unittest.TestCase):
    def test_normalized_1x2(self) -> None:
        self.assertEqual(
            normalized_pick_to_canonical("1X2", "1"),
            ("FT_1X2", "home"),
        )

    def test_model_hit_home(self) -> None:
        def det(m: str, s: str, rh: int, ra: int) -> str:
            if rh > ra and s == "1":
                return "won"
            return "lost"

        self.assertEqual(
            evaluate_model_vs_result("FT_1X2", "home", 2, 1, det),
            "hit",
        )


class TestDsrStub(unittest.TestCase):
    def test_stub_prefers_1x2(self) -> None:
        narr, conf, mmc, msc, _pv, src, _h = suggest_from_candidate_row(
            1,
            2.5,
            3.0,
            2.8,
            None,
            None,
            "A",
            "B",
            "Test League",
        )
        self.assertIn("Señal", narr)
        self.assertEqual(mmc, "FT_1X2")
        self.assertIn(msc, ("home", "draw", "away"))
        self.assertEqual(src, "rules_fallback")


class TestDsrDeepseekBatchMock(unittest.TestCase):
    def tearDown(self) -> None:
        dsr_deepseek._http_post = None

    def _picks_by_event_body(self, rows: list[dict]) -> bytes:
        content = json.dumps({"picks_by_event": rows}, ensure_ascii=False)
        resp = {"choices": [{"message": {"content": content}}]}
        return json.dumps(resp).encode("utf-8")

    def test_batch_two_events_maps_dsr_api_fields(self) -> None:
        def _post(
            url: str,
            headers: dict[str, str],
            body: bytes,
            timeout: float,
        ) -> bytes:
            self.assertIn(b"ds_input", body)
            return self._picks_by_event_body(
                [
                    {
                        "event_id": 10,
                        "motivo_sin_pick": "",
                        "picks": [
                            {
                                "market": "1X2",
                                "selection": "1",
                                "odds": 2.1,
                                "edge_pct": 3.0,
                                "confianza": "Media",
                                "razon": "Cuota local atractiva.",
                            }
                        ],
                    },
                    {
                        "event_id": 20,
                        "motivo_sin_pick": "",
                        "picks": [
                            {
                                "market": "Over/Under 2.5",
                                "selection": "Over 2.5",
                                "odds": 1.9,
                                "edge_pct": 2.0,
                                "confianza": "Baja",
                                "razon": "Se espera ritmo alto.",
                            }
                        ],
                    },
                ]
            )

        dsr_deepseek._http_post = _post
        cands = [
            DsrBatchCandidate(10, "L1", "H1", "A1", 2.1, 3.2, 3.5, None, None),
            DsrBatchCandidate(20, "L2", "H2", "A2", 2.0, 3.0, 3.0, 1.85, 1.95),
        ]
        out = deepseek_suggest_batch(
            cands,
            operating_day_key="2026-04-08",
            api_key="k",
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
            timeout_sec=30,
            max_retries=0,
        )
        self.assertIsNotNone(out[10])
        assert out[10] is not None
        self.assertIn("atractiva", out[10][0])
        self.assertEqual(out[10][2], "FT_1X2")
        self.assertEqual(out[10][3], "home")
        self.assertIsNotNone(out[20])
        assert out[20] is not None
        self.assertEqual(out[20][2], "OU_GOALS_2_5")
        self.assertEqual(out[20][3], "over_2_5")

    def test_batch_http_error_all_degrade(self) -> None:
        def _post(
            url: str,
            headers: dict[str, str],
            body: bytes,
            timeout: float,
        ) -> bytes:
            raise urllib.error.HTTPError(
                url, 500, "err", hdrs={}, fp=io.BytesIO(b"{}"),
            )

        dsr_deepseek._http_post = _post
        cands = [
            DsrBatchCandidate(1, "L", "H", "A", 2.0, 3.0, 3.0, None, None),
        ]
        out = deepseek_suggest_batch(
            cands,
            operating_day_key="2026-04-08",
            api_key="k",
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
            timeout_sec=5,
            max_retries=0,
        )
        self.assertIsNone(out[1])

    def test_suggest_for_snapshot_row_is_rules_only(self) -> None:
        narr, conf, mmc, msc, pv, src, h = suggest_for_snapshot_row(
            42,
            2.1,
            3.2,
            4.0,
            None,
            None,
            "A",
            "B",
            "Liga",
        )
        self.assertEqual(src, "rules_fallback")
        self.assertEqual(pv, PIPELINE_VERSION_DEFAULT)
        self.assertEqual(len(h), 64)


class TestPipelineVersionConstant(unittest.TestCase):
    def test_deepseek_pipeline_v1_batch(self) -> None:
        self.assertEqual(PIPELINE_VERSION_DEEPSEEK, "s6-deepseek-v1")


if __name__ == "__main__":
    unittest.main()

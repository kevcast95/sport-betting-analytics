"""
T-229 — Resolver canónico pick sugerido → verdad oficial CDM (ACTA T-244).

Mercados v1: `1X2` / `FT_1X2`, `TOTAL_GOALS_OU_2_5` / `OU_GOALS_2_5`, `BTTS` (ambos marcan).
Sin mapeo reproducible → `no_evaluable` con código de catálogo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from apps.api.bt2_market_canonical import (
    MODEL_PREDICTION_HIT,
    MODEL_PREDICTION_MISS,
    MODEL_PREDICTION_NA,
    MODEL_PREDICTION_VOID,
    determine_settlement_outcome,
    evaluate_model_vs_result,
)
# Fuente alineada al acta: resultado persistido en CDM (`bt2_events` + cadena SportMonks).
TRUTH_SOURCE_BT2_EVENTS_CDM: Literal["bt2_events_cdm"] = "bt2_events_cdm"

OfficialEvalStatus = Literal[
    "pending_result",
    "evaluated_hit",
    "evaluated_miss",
    "void",
    "no_evaluable",
]


@dataclass(frozen=True)
class OfficialEvaluationResolution:
    """Resultado único del resolver; listo para persistir en `bt2_pick_official_evaluation`."""

    evaluation_status: OfficialEvalStatus
    no_evaluable_reason: Optional[str]
    truth_source: Optional[str]
    truth_payload_ref: Optional[dict[str, Any]]


def normalize_official_eval_market(market_canonical: Optional[str]) -> Optional[str]:
    """
    Acta §2 (`1X2`, `TOTAL_GOALS_OU_2_5`, `BTTS`) + aliases de bóveda (`FT_1X2`, `OU_GOALS_2_5`).
    Retorna mercado interno único o None si fuera de soporte v1.
    """
    if not market_canonical:
        return None
    m = market_canonical.strip().upper()
    if m in ("1X2", "FT_1X2"):
        return "FT_1X2"
    if m in ("TOTAL_GOALS_OU_2_5", "OU_GOALS_2_5"):
        return "OU_GOALS_2_5"
    if m == "BTTS":
        return "BTTS"
    return None


_FT_SEL = frozenset({"home", "draw", "away"})
_OU_SEL = frozenset({"over_2_5", "under_2_5"})
_BTT_SEL = frozenset({"yes", "no"})

# Whitelist de estados CDM desde los que se permite liquidar hit/miss con marcador.
# Conservador: cualquier otro valor (p. ej. scheduled con scores materializados) → pending_result.
# Literales de cierre alineados con `FINISHEDISH_STATUSES` en
# scripts/bt2_phase2_lineage_audit.py; el CDM suele persistir `finished`
# (scripts/bt2_cdm/normalize_fixtures._parse_status).
_OFFICIAL_TRUTH_SCORING_ALLOWED_STATUSES: frozenset[str] = frozenset(
    {
        "finished",
        "ft",
        "after penalties",
        "aet",
        "fulltime",
        "full_time",
    }
)


def normalize_event_status_for_official_truth(event_status: Optional[str]) -> str:
    return (event_status or "").lower().strip()


def is_event_status_open_for_official_evaluation(event_status: Optional[str]) -> bool:
    """True si el evento no está en estado de cierre deportivo admitido para evaluación oficial."""
    st = normalize_event_status_for_official_truth(event_status)
    return st not in _OFFICIAL_TRUTH_SCORING_ALLOWED_STATUSES


def normalize_official_eval_selection(
    internal_market: str,
    selection_canonical: Optional[str],
) -> Optional[str]:
    """Selección mínima reproducible para mercados v1; None si no mapea."""
    if not selection_canonical:
        return None
    s = selection_canonical.strip().lower()
    if internal_market == "FT_1X2":
        return s if s in _FT_SEL else None
    if internal_market == "OU_GOALS_2_5":
        return s if s in _OU_SEL else None
    if internal_market == "BTTS":
        return s if s in _BTT_SEL else None
    return None


def _map_model_pred_to_status(pred: str) -> OfficialEvalStatus:
    if pred == MODEL_PREDICTION_HIT:
        return "evaluated_hit"
    if pred == MODEL_PREDICTION_MISS:
        return "evaluated_miss"
    if pred == MODEL_PREDICTION_VOID:
        return "void"
    return "no_evaluable"


def resolve_official_evaluation_from_cdm_truth(
    *,
    market_canonical: Optional[str],
    selection_canonical: Optional[str],
    result_home: Optional[int],
    result_away: Optional[int],
    event_status: Optional[str],
) -> OfficialEvaluationResolution:
    """
    Entrada típica: columnas `bt2_daily_picks` + `bt2_events` (scores y status CDM).

    - Fuera de mercados v1 → `no_evaluable` / OUTSIDE_SUPPORTED_MARKET_V1.
    - Selección no canónica para el mercado → MARKET_MAPPING_UNRESOLVED.
    - Evento anulado/aplazado oficialmente → `void` / VOID_OFFICIAL_EVENT.
    - Sin goles finales y evento aún no cerrado → `pending_result`.
    - Partido finished sin scores → MISSING_TRUTH_SOURCE.
    - Marcador presente pero estado CDM distinto de cierre deportivo (`finished`/sinónimos) →
      `pending_result` (no liquida aunque existan scores).
    - Tras paso anterior: scores + estado cerrado → hit / miss / void según `determine_settlement_outcome`.
    """
    m = normalize_official_eval_market(market_canonical)
    if m is None:
        return OfficialEvaluationResolution(
            "no_evaluable",
            "OUTSIDE_SUPPORTED_MARKET_V1",
            None,
            {"market_canonical": market_canonical},
        )

    sel = normalize_official_eval_selection(m, selection_canonical)
    if sel is None:
        return OfficialEvaluationResolution(
            "no_evaluable",
            "MARKET_MAPPING_UNRESOLVED",
            None,
            {
                "internal_market": m,
                "selection_canonical": selection_canonical,
            },
        )

    st = normalize_event_status_for_official_truth(event_status)
    if st in ("cancelled", "canceled", "postponed", "abandoned"):
        return OfficialEvaluationResolution(
            "void",
            None,
            TRUTH_SOURCE_BT2_EVENTS_CDM,
            {"event_status": st, "void_catalog_code": "VOID_OFFICIAL_EVENT"},
        )

    scores_missing = result_home is None or result_away is None
    if scores_missing:
        if st in ("scheduled", "live", "inplay", "in_play", ""):
            return OfficialEvaluationResolution(
                "pending_result",
                None,
                None,
                {"event_status": st or "unknown"},
            )
        if st == "finished":
            return OfficialEvaluationResolution(
                "no_evaluable",
                "MISSING_TRUTH_SOURCE",
                TRUTH_SOURCE_BT2_EVENTS_CDM,
                {"event_status": st},
            )
        return OfficialEvaluationResolution(
            "no_evaluable",
            "MISSING_TRUTH_SOURCE",
            TRUTH_SOURCE_BT2_EVENTS_CDM,
            {"event_status": st},
        )

    # Marcador presente pero evento no cerrado en CDM → no liquidar oficialmente (integridad).
    if is_event_status_open_for_official_evaluation(st):
        return OfficialEvaluationResolution(
            "pending_result",
            None,
            None,
            {"event_status": st or "unknown"},
        )

    rh = int(result_home)
    ra = int(result_away)
    pred = evaluate_model_vs_result(
        m, sel, rh, ra, determine_settlement_outcome
    )
    if pred == MODEL_PREDICTION_NA:
        return OfficialEvaluationResolution(
            "no_evaluable",
            "MARKET_MAPPING_UNRESOLVED",
            TRUTH_SOURCE_BT2_EVENTS_CDM,
            {"result_home": rh, "result_away": ra, "event_status": st},
        )

    out_status = _map_model_pred_to_status(pred)
    payload: dict[str, Any] = {
        "result_home": rh,
        "result_away": ra,
        "event_status": st or "finished",
    }
    return OfficialEvaluationResolution(
        out_status,
        None,
        TRUTH_SOURCE_BT2_EVENTS_CDM,
        payload,
    )

"""
US-BE-025 — sugerencia DSR sobre candidatos CDM.

- Reglas locales → dsr_source=rules_fallback (T-157).
- DeepSeek en vivo → lotes v1-equivalentes en router (**T-170 / D-06-019**); `suggest_for_snapshot_row` solo reglas.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple

from apps.api.bt2_dsr_contract import (
    PIPELINE_VERSION_DEFAULT,
    assert_no_forbidden_ds_keys,
    hash_dsr_input_payload,
)

logger = logging.getLogger(__name__)

# Persistencia cuando la señal viene del lote DeepSeek (una o varias llamadas/día).
PIPELINE_VERSION_DEEPSEEK: str = "s6-deepseek-v1"

_CONFIDENCE_MEDIUM = "medium"
_CONFIDENCE_LOW = "low"


def _implied_prob(odds: float) -> float:
    if odds is None or odds <= 1.0:
        return 0.0
    return 1.0 / odds


def suggest_from_candidate_row(
    event_id: int,
    odds_home: Optional[float],
    odds_draw: Optional[float],
    odds_away: Optional[float],
    odds_over25: Optional[float],
    odds_under25: Optional[float],
    home_team: str,
    away_team: str,
    tournament: str,
) -> Tuple[str, str, str, str, str, str, str]:
    """
    Retorna:
      narrative_es, confidence_label, model_market_canonical, model_selection_canonical,
      pipeline_version, dsr_source, dsr_input_hash
    """
    payload: dict[str, Any] = {
        "event_id": event_id,
        "odds": {
            "home": odds_home,
            "draw": odds_draw,
            "away": odds_away,
            "over25": odds_over25,
            "under25": odds_under25,
        },
    }
    assert_no_forbidden_ds_keys(payload)
    h = hash_dsr_input_payload(payload)

    # Regla simple: mayor valor esperado implícito en 1X2; si no hay 1X2, O/U 2.5
    probs = [
        ("home", _implied_prob(odds_home or 0.0), odds_home),
        ("draw", _implied_prob(odds_draw or 0.0), odds_draw),
        ("away", _implied_prob(odds_away or 0.0), odds_away),
    ]
    probs = [(k, p, o) for k, p, o in probs if o and o > 1.0]
    if probs:
        best = max(probs, key=lambda x: x[1])
        side = best[0]
        edge = best[1] - (1.0 / 3.0)  # vs uniforme
        conf = _CONFIDENCE_MEDIUM if edge > 0.05 else _CONFIDENCE_LOW
        label_es = {"home": "local", "draw": "empate", "away": "visitante"}[side]
        narrative = (
            f"En {tournament}, {home_team} frente a {away_team}, el equilibrio del 1X2 en "
            f"las cuotas del mercado inclina la lectura hacia el {label_es}."
        )
        return (
            narrative,
            conf,
            "FT_1X2",
            side,
            PIPELINE_VERSION_DEFAULT,
            "rules_fallback",
            h,
        )

    ou = []
    if odds_over25 and odds_over25 > 1.0:
        ou.append(("over_2_5", _implied_prob(odds_over25), odds_over25))
    if odds_under25 and odds_under25 > 1.0:
        ou.append(("under_2_5", _implied_prob(odds_under25), odds_under25))
    if ou:
        best = max(ou, key=lambda x: x[1])
        conf = _CONFIDENCE_LOW
        narrative = (
            f"En {tournament}, {home_team} frente a {away_team}, las cuotas del mercado "
            f"destacan el tercio de goles 2.5 ({best[0].replace('_', ' ')})."
        )
        return (
            narrative,
            conf,
            "OU_GOALS_2_5",
            best[0],
            PIPELINE_VERSION_DEFAULT,
            "rules_fallback",
            h,
        )

    narrative = (
        f"No hay cuotas suficientes en el mercado mostrado para comparar con claridad "
        f"a {home_team} y {away_team} ({tournament})."
    )
    return (
        narrative,
        _CONFIDENCE_LOW,
        "UNKNOWN",
        "unknown_side",
        PIPELINE_VERSION_DEFAULT,
        "rules_fallback",
        h,
    )


def consensus_to_legacy_odds(
    consensus: dict[str, dict[str, float]],
) -> tuple[
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
    Optional[float],
]:
    """Extrae 1X2 + O/U 2.5 desde consensus para `suggest_from_candidate_row`."""
    x = consensus.get("FT_1X2") or {}
    ou = consensus.get("OU_GOALS_2_5") or {}
    return (
        x.get("home"),
        x.get("draw"),
        x.get("away"),
        ou.get("over_2_5"),
        ou.get("under_2_5"),
    )


def suggest_sql_stat_fallback_from_consensus(
    event_id: int,
    consensus: dict[str, dict[str, float]],
    market_coverage: dict[str, bool],
    home_team: str,
    away_team: str,
    tournament: str,
) -> Tuple[str, str, str, str, str, str, str]:
    """
    D-06-022 — fallback cuando DSR no entrega señal: mayor probabilidad implícita (cuota más baja)
    entre outcomes de mercados completos en el input.
    """
    best_mc: Optional[str] = None
    best_sc: Optional[str] = None
    best_odds = 9999.0
    for mc, ok in market_coverage.items():
        if not ok:
            continue
        sub = consensus.get(mc) or {}
        for sc, od in sub.items():
            try:
                f = float(od)
            except (TypeError, ValueError):
                continue
            if f >= 1.30 and f < best_odds:
                best_odds = f
                best_mc, best_sc = mc, sc
    if best_mc is None or best_sc is None:
        return suggest_from_candidate_row(
            event_id,
            None,
            None,
            None,
            None,
            None,
            home_team,
            away_team,
            tournament,
        )
    payload: dict[str, Any] = {
        "event_id": event_id,
        "fallback_pick": {"mc": best_mc, "sc": best_sc, "odds": best_odds},
    }
    assert_no_forbidden_ds_keys(payload)
    h = hash_dsr_input_payload(payload)
    narrative = (
        f"Sin señal suficiente del modelo estadístico para este partido; se muestra una opción real "
        f"del CDM ({best_mc}) por criterio de mayor probabilidad implícita — {home_team} vs {away_team}."
    )
    return (
        narrative,
        _CONFIDENCE_MEDIUM,
        best_mc,
        best_sc,
        PIPELINE_VERSION_DEFAULT,
        "sql_stat_fallback",
        h,
    )


def suggest_for_snapshot_row(
    event_id: int,
    odds_home: Optional[float],
    odds_draw: Optional[float],
    odds_away: Optional[float],
    odds_over25: Optional[float],
    odds_under25: Optional[float],
    home_team: str,
    away_team: str,
    tournament: str,
) -> Tuple[str, str, str, str, str, str, str]:
    """
    Una fila snapshot con **reglas locales** + hash DSR (mismo criterio que degradación por evento).
    DeepSeek (`BT2_DSR_PROVIDER=deepseek`) se resuelve en **lotes** en `bt2_router._generate_daily_picks_snapshot`.
    """
    payload: dict[str, Any] = {
        "event_id": event_id,
        "odds": {
            "home": odds_home,
            "draw": odds_draw,
            "away": odds_away,
            "over25": odds_over25,
            "under25": odds_under25,
        },
    }
    assert_no_forbidden_ds_keys(payload)
    h = hash_dsr_input_payload(payload)

    narr, conf, mmc, msc, pv, src, _inner_h = suggest_from_candidate_row(
        event_id,
        odds_home,
        odds_draw,
        odds_away,
        odds_over25,
        odds_under25,
        home_team,
        away_team,
        tournament,
    )
    return narr, conf, mmc, msc, pv, src, h

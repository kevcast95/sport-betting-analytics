#!/usr/bin/env python3
"""
statistics_processor.py

Processor puro para el endpoint:
  /api/v1/event/{eventId}/statistics

Entrada: JSON crudo con estructura:
  {
    "statistics": [
      { "period": "ALL", "groups": [ { "statisticsItems": [ ... ] } ] },
      ...
    ]
  }

Salida (limpia, ultra-específica) - v2.0:
  {
    "match_performance": {
      "xg": {"home": float|null, "away": float|null},
      "shots": {
        "total": {"home": float|null, "away": float|null},
        "on_target": {"home": float|null, "away": float|null}
      },
      "chances": {
        "big_created": {"home": int|null, "away": int|null},
        "big_missed": {"home": int|null, "away": int|null}
      },
      "defensive_pressure": {
        "goalkeeper_saves": {"home": int|null, "away": int|null},
        "possession": {"home": float|null, "away": float|null}
      },
      "efficiency": {
        "penalty_area_touches": {"home": int|null, "away": int|null},
        "errors_lead_to_shot": {"home": int|null, "away": int|null},
        "errors_lead_to_goal": {"home": int|null, "away": int|null}
      }
    },
    "pressure_and_volume": {
      "possession": {"home": float|null, "away": float|null},
      "penalty_area_touches": {"home": int|null, "away": int|null},
      "corners": {"home": int|null, "away": int|null},
      "final_third_entries": {"home": int|null, "away": int|null}
    },
    "defensive_reliability": {
      "goalkeeper_saves": {"home": int|null, "away": int|null},
      "errors_lead_to_shot": {"home": int|null, "away": int|null},
      "errors_lead_to_goal": {"home": int|null, "away": int|null},
      "duels_won_pct": {"home": float|null, "away": float|null},
      "recoveries": {"home": int|null, "away": int|null}
    }
  }
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


def _to_number(x: Any) -> Optional[float]:
    """Convierte a float si es posible. Devuelve None si falla."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return None
    # Quitar % si viene
    s = s.replace("%", "")
    # Mantener solo número decimal
    m = re.search(r"-?\d+(?:[.,]\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except Exception:
        return None


def _pick_period(statistics: list, period_name: str = "ALL") -> list:
    """Devuelve la lista de items para un periodo específico."""
    if not isinstance(statistics, list):
        return []
    target = str(period_name).upper()
    for period in statistics:
        if not isinstance(period, dict):
            continue
        p = str(period.get("period", "")).upper()
        if p == target:
            groups = period.get("groups") or []
            items = []
            for g in groups:
                if not isinstance(g, dict):
                    continue
                items.extend(g.get("statisticsItems") or [])
            return items
    return []


def _build_item_map(items: list) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for it in items or []:
        if not isinstance(it, dict):
            continue
        key = it.get("key")
        if not key:
            continue
        out[str(key)] = it
    return out


def _home_away(item_map: Dict[str, Dict[str, Any]], key: str) -> Tuple[Optional[float], Optional[float]]:
    it = item_map.get(key) or {}
    home = _to_number(it.get("homeValue"))
    away = _to_number(it.get("awayValue"))
    return home, away


def process_statistics(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {"match_performance": {}}

    statistics = raw.get("statistics")
    items_all = _pick_period(statistics, "ALL")
    item_map = _build_item_map(items_all)

    # Keys según tu endpoint/txt
    xg_home, xg_away = _home_away(item_map, "expectedGoals")

    shots_total_home, shots_total_away = _home_away(item_map, "totalShotsOnGoal")
    shots_on_home, shots_on_away = _home_away(item_map, "shotsOnGoal")

    big_created_home, big_created_away = _home_away(item_map, "bigChanceCreated")
    big_missed_home, big_missed_away = _home_away(item_map, "bigChanceMissed")

    gk_saves_home, gk_saves_away = _home_away(item_map, "goalkeeperSaves")

    possession_home, possession_away = _home_away(item_map, "ballPossession")

    pen_area_touches_home, pen_area_touches_away = _home_away(item_map, "touchesInOppBox")
    errors_shot_home, errors_shot_away = _home_away(item_map, "errorsLeadToShot")
    errors_goal_home, errors_goal_away = _home_away(item_map, "errorsLeadToGoal")

    corners_home, corners_away = _home_away(item_map, "cornerKicks")
    final_third_entries_home, final_third_entries_away = _home_away(item_map, "finalThirdEntries")

    duels_won_pct_home, duels_won_pct_away = _home_away(item_map, "duelWonPercent")
    recoveries_home, recoveries_away = _home_away(item_map, "ballRecovery")

    return {
        "match_performance": {
            "xg": {"home": xg_home, "away": xg_away},
            "shots": {
                "total": {"home": shots_total_home, "away": shots_total_away},
                "on_target": {"home": shots_on_home, "away": shots_on_away},
            },
            "chances": {
                "big_created": {"home": big_created_home, "away": big_created_away},
                "big_missed": {"home": big_missed_home, "away": big_missed_away},
            },
            "defensive_pressure": {
                "goalkeeper_saves": {"home": gk_saves_home, "away": gk_saves_away},
                "possession": {"home": possession_home, "away": possession_away},
            },
            "efficiency": {
                "penalty_area_touches": {"home": pen_area_touches_home, "away": pen_area_touches_away},
                "errors_lead_to_shot": {"home": errors_shot_home, "away": errors_shot_away},
                "errors_lead_to_goal": {"home": errors_goal_home, "away": errors_goal_away},
            },
        },
        "pressure_and_volume": {
            "possession": {"home": possession_home, "away": possession_away},
            "penalty_area_touches": {"home": pen_area_touches_home, "away": pen_area_touches_away},
            "corners": {"home": corners_home, "away": corners_away},
            "final_third_entries": {
                "home": final_third_entries_home,
                "away": final_third_entries_away,
            },
        },
        "defensive_reliability": {
            "goalkeeper_saves": {"home": gk_saves_home, "away": gk_saves_away},
            "errors_lead_to_shot": {"home": errors_shot_home, "away": errors_shot_away},
            "errors_lead_to_goal": {"home": errors_goal_home, "away": errors_goal_away},
            "duels_won_pct": {"home": duels_won_pct_home, "away": duels_won_pct_away},
            "recoveries": {"home": recoveries_home, "away": recoveries_away},
        },
    }


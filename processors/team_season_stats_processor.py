"""
Normaliza GET /team/{teamId}/unique-tournament/{utId}/season/{seasonId}/statistics/overall
Respaldo cuando /event/{id}/statistics falla (Tier B): contexto de temporada en la misma liga.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Subconjunto útil para LLM; el crudo puede traer 100+ campos.
_TOTAL_KEYS: List[str] = [
    "matches",
    "goalsScored",
    "goalsConceded",
    "shots",
    "shotsOnTarget",
    "shotsOffTarget",
    "bigChances",
    "bigChancesMissed",
    "bigChancesAgainst",
    "bigChancesMissedAgainst",
    "averageBallPossession",
    "accuratePassesPercentage",
    "corners",
    "cleanSheets",
    "avgRating",
    "yellowCards",
    "redCards",
    "saves",
]


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _int(x: Any) -> int:
    if x is None:
        return 0
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def process_team_season_stats(raw: Dict[str, Any], *, side: str) -> Dict[str, Any]:
    """
    side: "home" | "away" (solo metadato en salida).
    """
    if not isinstance(raw, dict):
        return {"ok": False, "side": side, "reason": "not_a_dict"}

    if raw.get("_error"):
        return {"ok": False, "side": side, "reason": "fetch_error"}

    stats = raw.get("statistics")
    if not isinstance(stats, dict):
        return {"ok": False, "side": side, "reason": "missing_statistics"}

    matches = _int(stats.get("matches"))
    if matches <= 0:
        return {"ok": False, "side": side, "reason": "matches_zero"}

    totals: Dict[str, Any] = {}
    for k in _TOTAL_KEYS:
        if k in stats and stats[k] is not None:
            totals[k] = stats[k]

    per_match: Dict[str, Optional[float]] = {}
    for k in (
        "goalsScored",
        "goalsConceded",
        "shots",
        "shotsOnTarget",
        "bigChances",
        "bigChancesAgainst",
        "corners",
        "cleanSheets",
    ):
        if k not in totals:
            continue
        v = _num(totals.get(k))
        if v is not None:
            per_match[k] = round(v / matches, 3)

    return {
        "ok": True,
        "side": side,
        "matches": matches,
        "totals": totals,
        "per_match": per_match,
    }

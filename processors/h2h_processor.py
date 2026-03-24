"""
Normaliza el payload de GET /event/{eventId}/h2h (SofaScore).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _int_or_none(x: Any) -> Optional[int]:
    if x is None:
        return None
    if isinstance(x, int):
        return x
    try:
        s = str(x).strip()
        if not s:
            return None
        return int(float(s.replace(",", ".")))
    except Exception:
        return None


def _team_block(team: Any) -> Dict[str, Any]:
    if not isinstance(team, dict):
        return {}
    return {
        "id": team.get("id"),
        "name": team.get("name"),
        "short_name": team.get("shortName"),
        "slug": team.get("slug"),
    }


def process_h2h(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entrada: JSON crudo del endpoint h2h (o dict con _error).
    Salida: estructura estable + ok bool para contrato/diagnostics.
    """
    if not isinstance(raw, dict):
        return {"ok": False, "reason": "not_a_dict"}

    if raw.get("_error"):
        return {"ok": False, "reason": "fetch_error"}

    team_duel = raw.get("teamDuel")
    if not isinstance(team_duel, dict):
        return {"ok": False, "reason": "missing_team_duel"}

    home_team = team_duel.get("homeTeam") or team_duel.get("home")
    away_team = team_duel.get("awayTeam") or team_duel.get("away")

    out: Dict[str, Any] = {
        "ok": True,
        "team_duel": {
            "home_wins": _int_or_none(team_duel.get("homeWins")),
            "away_wins": _int_or_none(team_duel.get("awayWins")),
            "draws": _int_or_none(team_duel.get("draws")),
            "home_team": _team_block(home_team if isinstance(home_team, dict) else {}),
            "away_team": _team_block(away_team if isinstance(away_team, dict) else {}),
        },
    }

    mgr = raw.get("managerDuel")
    if isinstance(mgr, dict):
        out["manager_duel"] = {
            "home_wins": _int_or_none(mgr.get("homeWins")),
            "away_wins": _int_or_none(mgr.get("awayWins")),
            "draws": _int_or_none(mgr.get("draws")),
        }

    return out

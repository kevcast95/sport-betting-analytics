#!/usr/bin/env python3
"""
lineups_processor.py

Processor puro para el endpoint de lineups:
  /api/v1/event/{eventId}/lineups

Convierte el JSON crudo en un objeto ultra-específico y limpio:
  {
    "lineup_summary": {
      "is_confirmed": bool,
      "home": {"formation": str, "avg_rating": float, "key_player": str, "missing": [...]},
      "away": {...}
    }
  }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _clean_name(name: str) -> str:
    if not name:
        return ""
    # Limpieza ligera de espacios / saltos de línea
    return " ".join(str(name).split())


def _extract_missing(missing_players: list) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for mp in missing_players or []:
        if not isinstance(mp, dict):
            continue
        player = mp.get("player") or {}
        name = _clean_name(player.get("name") or "")
        # En el txt, el campo útil para razón es "description"
        reason = mp.get("description") or ""
        reason = _clean_name(reason)
        if name:
            out.append({"name": name, "reason": reason})
    return out


def _extract_key_player(players: list) -> str:
    """
    El feedback de valor indica que el key_player se alinea con:
    - rating (calificación)
    - expectedGoals individual (xG)

    Regla:
    - elegir el jugador con mayor statistics.expectedGoals
    - si no existe expectedGoals, usar mayor statistics.rating
    """
    best_name = ""
    best_xg = None
    best_rating = None

    for p in players or []:
        if not isinstance(p, dict):
            continue
        player = p.get("player") or {}
        name = _clean_name(player.get("name") or "")
        stats = p.get("statistics") or {}

        xg = _to_float(stats.get("expectedGoals"))
        rating = _to_float(stats.get("rating"))

        # Preferimos xG; si no hay xG, fallback a rating
        if xg is not None:
            if best_xg is None or xg > best_xg:
                best_xg = xg
                best_name = name
        else:
            if rating is not None:
                if best_rating is None or rating > best_rating:
                    best_rating = rating
                    best_name = name

    return best_name


def _extract_avg_rating(players: list) -> float:
    """
    Calcula avg_rating:
    - Promedio de statistics.rating de los jugadores NO substitute.
    - Si no hay starters (o ratings faltan), usa todos los players con rating.
    """
    starters = []
    for p in players or []:
        if not isinstance(p, dict):
            continue
        if p.get("substitute") is False:
            starters.append(p)

    def collect_ratings(pls: list) -> List[float]:
        rs: List[float] = []
        for p in pls or []:
            stats = p.get("statistics") or {}
            r = _to_float(stats.get("rating"))
            if r is not None:
                rs.append(r)
        return rs

    r_starters = collect_ratings(starters)
    if r_starters:
        return sum(r_starters) / len(r_starters)

    r_all = collect_ratings(players or [])
    if r_all:
        return sum(r_all) / len(r_all)

    return 0.0


def process_lineups(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point puro.
    input : dict (JSON crudo del endpoint /lineups)
    output: dict (lineup_summary limpio)
    """
    if not isinstance(raw, dict):
        return {"lineup_summary": {"is_confirmed": False, "home": {}, "away": {}}}

    confirmed = bool(raw.get("confirmed"))

    home = raw.get("home") or {}
    away = raw.get("away") or {}

    home_players = home.get("players") or []
    away_players = away.get("players") or []

    home_formation = home.get("formation") or ""
    away_formation = away.get("formation") or ""

    home_missing = _extract_missing(home.get("missingPlayers") or [])
    away_missing = _extract_missing(away.get("missingPlayers") or [])

    home_key = _extract_key_player(home_players)
    away_key = _extract_key_player(away_players)

    home_avg = _extract_avg_rating(home_players)
    away_avg = _extract_avg_rating(away_players)

    return {
        "lineup_summary": {
            "is_confirmed": confirmed,
            "home": {
                "formation": _clean_name(home_formation),
                "avg_rating": round(home_avg, 2),
                "key_player": home_key,
                "missing": home_missing,
            },
            "away": {
                "formation": _clean_name(away_formation),
                "avg_rating": round(away_avg, 2),
                "key_player": away_key,
                "missing": away_missing,
            },
        }
    }


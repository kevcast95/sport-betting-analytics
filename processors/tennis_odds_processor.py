#!/usr/bin/env python3
"""
Processor para mercados de cuotas tenis en GET /event/{id}/odds/1/all (SofaScore).

El processor de fútbol (odds_all) busca mercados con nombres fijos (Double chance, etc.);
aquí indexamos nombres reales y extraemos ganador de partido cuando aparece.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _fractional_to_decimal(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if "/" in s:
        parts = s.split("/", 1)
        try:
            num = float(parts[0].strip())
            den = float(parts[1].strip())
            if den == 0:
                return None
            return round((num / den) + 1.0, 3)
        except Exception:
            return None
    try:
        return round(float(s), 3)
    except Exception:
        return None


def _choice_by_names(market: Dict[str, Any], names: List[str]) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    choices = market.get("choices") or []
    if not isinstance(choices, list):
        return out
    lower_map = {str(c.get("name", "")).strip().lower(): c for c in choices if isinstance(c, dict)}
    for n in names:
        key = n.lower()
        ch = lower_map.get(key)
        if ch is None:
            out[n] = None
        else:
            out[n] = _fractional_to_decimal(ch.get("fractionalValue"))
    return out


def _find_market_by_keywords(markets: List[Any], keywords: tuple[str, ...]) -> Optional[Dict[str, Any]]:
    for m in markets:
        if not isinstance(m, dict):
            continue
        name = str(m.get("marketName", "")).lower()
        if all(kw in name for kw in keywords):
            return m
    return None


def process_tennis_odds_all(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Salida estable para el bundle procesado (processed.tennis_odds) y diagnóstico de cobertura.
    """
    if not isinstance(raw, dict) or raw.get("_error"):
        return {
            "has_any_odds": False,
            "market_names": [],
            "match_winner": {},
            "note": "fetch_error_or_empty",
        }

    markets = raw.get("markets") or []
    if not isinstance(markets, list):
        markets = []

    names = [str(m.get("marketName", "")).strip() for m in markets if isinstance(m, dict) and m.get("marketName")]

    # Nombres habituales SofaScore / casas: "Match winner", "Winner", "To win match"
    mw = (
        _find_market_by_keywords(markets, ("match", "winner"))
        or _find_market_by_keywords(markets, ("win", "match"))
        or _find_market_by_keywords(markets, ("winner",))
    )

    match_winner: Dict[str, Any] = {}
    if isinstance(mw, dict):
        # En tenis suelen ser dos choices con nombres de jugadores; también "1"/"2" en algunos mercados.
        c1 = _choice_by_names(mw, ["1", "Home"])
        c2 = _choice_by_names(mw, ["2", "Away"])
        choices = mw.get("choices") or []
        player_odds: List[Dict[str, Any]] = []
        if isinstance(choices, list):
            for ch in choices[:3]:
                if not isinstance(ch, dict):
                    continue
                nm = str(ch.get("name", "")).strip()
                if nm in ("1", "2", "Home", "Away"):
                    continue
                player_odds.append(
                    {
                        "name": nm,
                        "decimal": _fractional_to_decimal(ch.get("fractionalValue")),
                    }
                )
        match_winner = {
            "market_name": mw.get("marketName"),
            "by_slot": {**c1, **c2},
            "players": player_odds,
        }

    return {
        "has_any_odds": len(markets) > 0,
        "market_count": len(markets),
        "market_names": names[:40],
        "match_winner": match_winner,
    }

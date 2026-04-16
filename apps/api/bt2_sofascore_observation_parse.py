"""
T-284 — flags D-06-068 §4–§5 desde payloads SofaScore + `processed` de processors.

Solo benchmark; no rutas productivas.
"""

from __future__ import annotations

from typing import Any, Optional

from processors.odds_all_processor import process_odds_all
from processors.odds_feature_processor import process_odds_feature


_MIN_STARTING_PLAYERS = 11


def _starter_count(players: Any) -> int:
    if not isinstance(players, list):
        return 0
    n = 0
    for p in players:
        if not isinstance(p, dict):
            continue
        if p.get("substitute") is False:
            n += 1
    return n


def sofa_lineup_flags_from_lineups_raw(raw: dict[str, Any]) -> tuple[bool, bool, bool]:
    """(home_usable, away_usable, both) — §4 alineado a once no suplente."""
    if not isinstance(raw, dict):
        return (False, False, False)
    home = raw.get("home") or {}
    away = raw.get("away") or {}
    if not isinstance(home, dict) or not isinstance(away, dict):
        return (False, False, False)
    hp = home.get("players") or []
    ap = away.get("players") or []
    hu = _starter_count(hp) >= _MIN_STARTING_PLAYERS
    au = _starter_count(ap) >= _MIN_STARTING_PLAYERS
    return (hu, au, hu and au)


def _pos_decimal(v: Any) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x > 1.0:
        return x
    return None


def sofa_market_flags_from_processed(processed: dict[str, Any]) -> tuple[bool, bool, bool]:
    """
    FT_1X2 desde odds_featured (full_time_1x2); OU 2.5 y BTTS desde odds_all extended_markets.
    """
    if not isinstance(processed, dict):
        return (False, False, False)
    ft = False
    snap = ((processed.get("odds_featured") or {}).get("market_snapshot") or {})
    ft_block = snap.get("full_time_1x2") or {}
    if isinstance(ft_block, dict):
        h = _pos_decimal((ft_block.get("home") or {}).get("current"))
        d = _pos_decimal((ft_block.get("draw") or {}).get("current"))
        a = _pos_decimal((ft_block.get("away") or {}).get("current"))
        ft = bool(h and d and a)

    ext = ((processed.get("odds_all") or {}).get("extended_markets") or {})
    if not isinstance(ext, dict):
        ext = {}
    gd = ext.get("goals_depth") or {}
    if not isinstance(gd, dict):
        gd = {}
    ou = gd.get("over_under_2.5") or {}
    ou_ok = bool(_pos_decimal(ou.get("over")) and _pos_decimal(ou.get("under"))) if isinstance(
        ou, dict
    ) else False
    btts = gd.get("btts") or {}
    bt_ok = bool(_pos_decimal(btts.get("yes")) and _pos_decimal(btts.get("no"))) if isinstance(
        btts, dict
    ) else False
    return (ft, ou_ok, bt_ok)


def sofa_flags_from_fetched_payloads(
    lineups_raw: dict[str, Any],
    odds_all_raw: dict[str, Any],
    odds_featured_raw: dict[str, Any],
) -> tuple[bool, bool, bool, bool, bool, bool]:
    """
    Devuelve
      lineup_home, lineup_away, lineup_avail, ft, ou, btts
    """
    hu, au, lav = sofa_lineup_flags_from_lineups_raw(lineups_raw)
    proc = {
        "odds_all": process_odds_all(odds_all_raw),
        "odds_featured": process_odds_feature(odds_featured_raw),
    }
    f1, ou, bt = sofa_market_flags_from_processed(proc)
    return (hu, au, lav, f1, ou, bt)

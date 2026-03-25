"""
Extrae cuota decimal del snapshot SofaScore en `processed` (odds_all / odds_featured)
para mercados que el modelo puede emitir. Si falta data scrapeada, devuelve None.
"""

from __future__ import annotations

from typing import Any, Optional


def _positive_decimal(v: Any) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x > 1.0:
        return round(x, 3)
    return None


def scraped_decimal_odds_for_pick(
    processed: Any,
    *,
    market: str,
    selection_code: str,
) -> Optional[float]:
    if not isinstance(processed, dict):
        return None
    mk = str(market).strip()
    sel = str(selection_code).strip()

    if mk == "1X2":
        snap = (processed.get("odds_featured") or {}).get("market_snapshot") or {}
        ft = snap.get("full_time_1x2") or {}
        u = sel.upper()
        if u == "1":
            return _positive_decimal((ft.get("home") or {}).get("current"))
        if u == "X":
            return _positive_decimal((ft.get("draw") or {}).get("current"))
        if u == "2":
            return _positive_decimal((ft.get("away") or {}).get("current"))
        return None

    ext = ((processed.get("odds_all") or {}).get("extended_markets") or {})

    if mk == "Double Chance":
        dc = ((ext.get("safety") or {}).get("double_chance") or {})
        key = sel.upper().replace(" ", "")
        if key in ("1X", "X2", "12"):
            return _positive_decimal(dc.get(key))
        return None

    if mk == "BTTS":
        btts = ((ext.get("goals_depth") or {}).get("btts") or {})
        sl = sel.strip().lower()
        if sl == "yes":
            return _positive_decimal(btts.get("yes"))
        if sl == "no":
            return _positive_decimal(btts.get("no"))
        return None

    if mk == "Over/Under 2.5":
        ou = ((ext.get("goals_depth") or {}).get("over_under_2.5") or {})
        sl = sel.strip().lower()
        if sl.startswith("over"):
            return _positive_decimal(ou.get("over"))
        if sl.startswith("under"):
            return _positive_decimal(ou.get("under"))
        return None

    to = (processed.get("tennis_odds") or {}).get("match_winner") or {}
    by_slot = (to.get("by_slot") or {}) if isinstance(to, dict) else {}
    if mk in ("Match winner", "Winner", "To win match"):
        u = sel.strip().upper()
        if u == "1":
            return _positive_decimal(
                by_slot.get("1") or by_slot.get("Home"))
        if u == "2":
            return _positive_decimal(
                by_slot.get("2") or by_slot.get("Away"))
        return None

    return None


def recompute_edge_pct_at_new_odds(
    *,
    model_odds: float,
    edge_pct_model: float,
    new_odds: float,
) -> Optional[float]:
    """
    Mantiene la probabilidad implícita "real" que asumió el modelo:
    p_real ≈ 100/model_odds + edge_pct_model (puntos porcentuales),
    y recalcula el edge contra la nueva cuota: p_real - 100/new_odds.
    """
    if model_odds <= 1.0 or new_odds <= 1.0:
        return None
    p_real = 100.0 / float(model_odds) + float(edge_pct_model)
    return round(p_real - 100.0 / float(new_odds), 2)


def confianza_from_edge(edge_pct: float) -> str:
    """Mismos umbrales que el prompt DeepSeek en deepseek_batches_to_telegram_payload_parts."""
    if edge_pct >= 5:
        return "Alta"
    if edge_pct >= 3:
        return "Media-Alta"
    if edge_pct >= 1.5:
        return "Media"
    return "Baja"

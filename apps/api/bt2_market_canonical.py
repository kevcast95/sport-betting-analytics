"""
US-BE-027 / D-06-003 — códigos de mercado canónico y etiquetas ES (Sprint 06).

No exponer datos crudos de proveedor; el FE consume estos códigos + label_es.
"""

from __future__ import annotations

from typing import Literal, Optional, Tuple

MarketCanonical = Literal[
    "FT_1X2",
    "OU_GOALS_2_5",
    "UNKNOWN",
]

MODEL_PREDICTION_HIT: str = "hit"
MODEL_PREDICTION_MISS: str = "miss"
MODEL_PREDICTION_VOID: str = "void"
MODEL_PREDICTION_NA: str = "n_a"

_MARKET_LABEL_ES: dict[str, str] = {
    "FT_1X2": "Resultado final (1X2)",
    "OU_GOALS_2_5": "Más / menos goles 2.5",
    "UNKNOWN": "Mercado",
}


def market_canonical_label_es(code: Optional[str]) -> str:
    if not code:
        return _MARKET_LABEL_ES["UNKNOWN"]
    return _MARKET_LABEL_ES.get(code, _MARKET_LABEL_ES["UNKNOWN"])


def normalized_pick_to_canonical(
    norm_market: str,
    norm_selection: str,
) -> Tuple[str, str]:
    """
    A partir de salida `_normalize_market_selection_for_pick` → (market_canonical, selection_canonical).
    selection_canonical: home | draw | away | over_2_5 | under_2_5
    """
    mu = norm_market.upper()
    s = norm_selection.strip()
    sl = s.lower()

    if any(k in mu for k in ("TOTAL", "GOALS", "OVER", "UNDER")):
        if "over" in sl:
            return ("OU_GOALS_2_5", "over_2_5")
        if "under" in sl:
            return ("OU_GOALS_2_5", "under_2_5")
        return ("OU_GOALS_2_5", "unknown_side")

    # 1X2
    if s in ("1", "Home", "home"):
        return ("FT_1X2", "home")
    if s in ("X", "Draw", "draw", "x"):
        return ("FT_1X2", "draw")
    if s in ("2", "Away", "away"):
        return ("FT_1X2", "away")
    return ("UNKNOWN", "unknown_side")


def canonical_to_settle_strings(
    market_canonical: str,
    selection_canonical: str,
) -> Tuple[str, str]:
    """Traduce canónico a strings entendidos por `_determine_outcome`."""
    if market_canonical == "FT_1X2":
        m = {"home": ("1X2", "1"), "draw": ("1X2", "X"), "away": ("1X2", "2")}.get(
            selection_canonical.lower() if selection_canonical else "",
            ("1X2", "1"),
        )
        return m
    if market_canonical == "OU_GOALS_2_5":
        if selection_canonical == "over_2_5":
            return ("TOTAL GOALS", "OVER 2.5")
        if selection_canonical == "under_2_5":
            return ("TOTAL GOALS", "UNDER 2.5")
    return ("UNKNOWN", "")


def evaluate_model_vs_result(
    market_canonical: Optional[str],
    selection_canonical: Optional[str],
    result_home: int,
    result_away: int,
    determine_outcome_fn,
) -> str:
    """
    ¿Habría ganado la sugerencia del modelo con el marcador final?
    Retorna hit | miss | void | n_a
    """
    if not market_canonical or not selection_canonical:
        return MODEL_PREDICTION_NA
    if market_canonical == "UNKNOWN" or selection_canonical in ("unknown_side", "", None):
        return MODEL_PREDICTION_NA
    m, s = canonical_to_settle_strings(market_canonical, selection_canonical)
    if m == "UNKNOWN" or not s:
        return MODEL_PREDICTION_NA
    out = determine_outcome_fn(m, s, result_home, result_away)
    if out == "won":
        return MODEL_PREDICTION_HIT
    if out == "lost":
        return MODEL_PREDICTION_MISS
    return MODEL_PREDICTION_VOID

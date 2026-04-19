"""
US-BE-027 / D-06-003 — códigos de mercado canónico y etiquetas ES (Sprint 06).

No exponer datos crudos de proveedor; el FE consume estos códigos + label_es.
"""

from __future__ import annotations

import re
from typing import Literal, Optional, Tuple

MarketCanonical = Literal[
    "FT_1X2",
    "OU_GOALS_2_5",
    "OU_GOALS_1_5",
    "OU_GOALS_3_5",
    "BTTS",
    "DOUBLE_CHANCE_1X",
    "DOUBLE_CHANCE_X2",
    "DOUBLE_CHANCE_12",
    "UNKNOWN",
]

MODEL_PREDICTION_HIT: str = "hit"
MODEL_PREDICTION_MISS: str = "miss"
MODEL_PREDICTION_VOID: str = "void"
MODEL_PREDICTION_NA: str = "n_a"

_MARKET_LABEL_ES: dict[str, str] = {
    "FT_1X2": "Resultado final (1X2)",
    "OU_GOALS_2_5": "Más / menos goles 2.5",
    "OU_GOALS_1_5": "Más / menos goles 1.5",
    "OU_GOALS_3_5": "Más / menos goles 3.5",
    "BTTS": "Ambos marcan",
    "DOUBLE_CHANCE_1X": "Doble oportunidad 1X",
    "DOUBLE_CHANCE_X2": "Doble oportunidad X2",
    "DOUBLE_CHANCE_12": "Doble oportunidad 12",
    "UNKNOWN": "Mercado",
}


def market_canonical_label_es(code: Optional[str]) -> str:
    if not code:
        return _MARKET_LABEL_ES["UNKNOWN"]
    return _MARKET_LABEL_ES.get(code, _MARKET_LABEL_ES["UNKNOWN"])


def selection_canonical_summary_es(
    market_canonical: Optional[str],
    selection_canonical: Optional[str],
    *,
    home_team: str,
    away_team: str,
) -> str:
    """Texto corto ES para la línea del pick alineado a (mmc, msc) — bóveda / settlement."""
    mmc = (market_canonical or "").strip().upper()
    msc = (selection_canonical or "").strip().lower()
    if not mmc or mmc == "UNKNOWN":
        return ""
    if msc in ("", "unknown_side"):
        return ""

    if mmc == "FT_1X2":
        if msc == "home":
            return f"Victoria {home_team}"
        if msc == "away":
            return f"Victoria {away_team}"
        if msc == "draw":
            return "Empate"
        return ""

    if mmc == "BTTS":
        if msc == "yes":
            return "Sí (ambos marcan)"
        if msc == "no":
            return "No (ambos marcan)"
        return ""

    if mmc == "OU_GOALS_2_5":
        if msc == "over_2_5":
            return "Más de 2.5 goles"
        if msc == "under_2_5":
            return "Menos de 2.5 goles"
        return ""
    if mmc == "OU_GOALS_1_5":
        if msc == "over_1_5":
            return "Más de 1.5 goles"
        if msc == "under_1_5":
            return "Menos de 1.5 goles"
        return ""
    if mmc == "OU_GOALS_3_5":
        if msc == "over_3_5":
            return "Más de 3.5 goles"
        if msc == "under_3_5":
            return "Menos de 3.5 goles"
        return ""

    if mmc == "DOUBLE_CHANCE_1X" and msc == "yes":
        return f"Empate o {home_team}"
    if mmc == "DOUBLE_CHANCE_X2" and msc == "yes":
        return f"Empate o {away_team}"
    if mmc == "DOUBLE_CHANCE_12" and msc == "yes":
        return f"{home_team} o {away_team}"

    return ""


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

    if "BTTS" in mu or "BTTS" in sl or "AMBOS" in mu:
        if sl in ("yes", "sí", "si"):
            return ("BTTS", "yes")
        if sl == "no":
            return ("BTTS", "no")
        return ("BTTS", "unknown_side")

    if "DOUBLE" in mu or "DOBLE" in mu:
        if "1X" in mu or "1/X" in mu or "1 OR X" in mu:
            return ("DOUBLE_CHANCE_1X", "yes")
        if "X2" in mu or "X/2" in mu:
            return ("DOUBLE_CHANCE_X2", "yes")
        if "12" in mu or "1/2" in mu:
            return ("DOUBLE_CHANCE_12", "yes")
        return ("UNKNOWN", "unknown_side")

    if any(k in mu for k in ("TOTAL", "GOALS", "OVER", "UNDER", "O/U")):
        if "1.5" in mu or "1,5" in mu:
            if "over" in sl:
                return ("OU_GOALS_1_5", "over_1_5")
            if "under" in sl:
                return ("OU_GOALS_1_5", "under_1_5")
        if "3.5" in mu or "3,5" in mu:
            if "over" in sl:
                return ("OU_GOALS_3_5", "over_3_5")
            if "under" in sl:
                return ("OU_GOALS_3_5", "under_3_5")
        if "over" in sl:
            return ("OU_GOALS_2_5", "over_2_5")
        if "under" in sl:
            return ("OU_GOALS_2_5", "under_2_5")
        return ("OU_GOALS_2_5", "unknown_side")

    # Códigos canónicos directos (salida modelo alineada a builder)
    if mu.startswith("FT_1X2"):
        if sl in ("home", "1"):
            return ("FT_1X2", "home")
        if sl in ("draw", "x"):
            return ("FT_1X2", "draw")
        if sl in ("away", "2"):
            return ("FT_1X2", "away")
    if mu.startswith("OU_GOALS_2_5"):
        if "over" in sl:
            return ("OU_GOALS_2_5", "over_2_5")
        if "under" in sl:
            return ("OU_GOALS_2_5", "under_2_5")
    if mu.startswith("OU_GOALS_1_5"):
        if "over" in sl:
            return ("OU_GOALS_1_5", "over_1_5")
        if "under" in sl:
            return ("OU_GOALS_1_5", "under_1_5")
    if mu.startswith("OU_GOALS_3_5"):
        if "over" in sl:
            return ("OU_GOALS_3_5", "over_3_5")
        if "under" in sl:
            return ("OU_GOALS_3_5", "under_3_5")

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
    if market_canonical == "OU_GOALS_1_5":
        if selection_canonical == "over_1_5":
            return ("TOTAL GOALS", "OVER 1.5")
        if selection_canonical == "under_1_5":
            return ("TOTAL GOALS", "UNDER 1.5")
    if market_canonical == "OU_GOALS_3_5":
        if selection_canonical == "over_3_5":
            return ("TOTAL GOALS", "OVER 3.5")
        if selection_canonical == "under_3_5":
            return ("TOTAL GOALS", "UNDER 3.5")
    if market_canonical == "BTTS":
        if selection_canonical == "yes":
            return ("BTTS", "YES")
        if selection_canonical == "no":
            return ("BTTS", "NO")
    return ("UNKNOWN", "")


def determine_settlement_outcome(
    market: str, selection: str, result_home: int, result_away: int
) -> str:
    """
    Determina won | lost | void — misma semántica que `bt2_router._determine_outcome`
    (US-DX-001, mercados mínimos settle).
    """
    m = market.upper()
    s = selection.strip()
    total = result_home + result_away

    if any(k in m for k in ("MATCH WINNER", "1X2", "WINNER")):
        if s in ("1", "Home", "home"):
            return "won" if result_home > result_away else "lost"
        if s in ("X", "Draw", "draw", "Empate", "empate"):
            return "won" if result_home == result_away else "lost"
        if s in ("2", "Away", "away"):
            return "won" if result_away > result_home else "lost"
        return "void"

    if any(k in m for k in ("OVER", "UNDER", "GOALS", "TOTAL")):
        num = re.search(r"(\d+\.?\d*)", s)
        threshold = float(num.group(1)) if num else 2.5
        if "OVER" in s.upper():
            return "won" if total > threshold else "lost"
        if "UNDER" in s.upper():
            return "won" if total < threshold else "lost"
        return "void"

    if m == "BTTS":
        su = s.upper().strip()
        both_scored = result_home > 0 and result_away > 0
        if su == "YES":
            return "won" if both_scored else "lost"
        if su == "NO":
            return "won" if not both_scored else "lost"
        return "void"

    return "void"


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

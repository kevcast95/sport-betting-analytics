#!/usr/bin/env python3
"""
validate_1x2_processor.py

Processor puro para validar una selección 1X2 contra el marcador final.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def _to_int(x: Any) -> Optional[int]:
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


def _normalize_selection(sel: Any) -> Optional[str]:
    if sel is None:
        return None
    s = str(sel).strip().upper()
    if s in ("1", "X", "2"):
        return s
    # Alias comunes
    if s in ("HOME", "H", "HOME_WIN", "WIN_HOME"):
        return "1"
    if s in ("AWAY", "A", "AWAY_WIN", "WIN_AWAY"):
        return "2"
    if s in ("DRAW", "D"):
        return "X"
    return None


def process_validate_1x2(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input esperado:
      {
        "selection": "1"|"X"|"2" (o alias),
        "match_state": "finished"|"live"|... (opcional),
        "home_score": int|null,
        "away_score": int|null
      }

    Output:
      {
        "selection": "1"|"X"|"2"|null,
        "result_1x2": "1"|"X"|"2"|null,
        "outcome": "win"|"loss"|"pending",
        "score": {"home": int|null, "away": int|null}
      }
    """
    if not isinstance(raw, dict):
        return {"selection": None, "result_1x2": None, "outcome": "pending", "score": {"home": None, "away": None}}

    selection = _normalize_selection(raw.get("selection"))
    home_score = _to_int(raw.get("home_score"))
    away_score = _to_int(raw.get("away_score"))
    match_state = str(raw.get("match_state") or "").lower()

    # Pending si aún no termina o no hay marcador.
    if match_state != "finished" or home_score is None or away_score is None:
        return {
            "selection": selection,
            "result_1x2": None,
            "outcome": "pending",
            "score": {"home": home_score, "away": away_score},
        }

    result_1x2: Optional[str] = None
    if home_score > away_score:
        result_1x2 = "1"
    elif home_score < away_score:
        result_1x2 = "2"
    else:
        result_1x2 = "X"

    # En 1X2 no existe "push": si eliges un lado distinto al marcador final => loss.
    outcome = "win" if selection and result_1x2 == selection else "loss"

    return {
        "selection": selection,
        "result_1x2": result_1x2,
        "outcome": outcome,
        "score": {"home": home_score, "away": away_score},
    }


#!/usr/bin/env python3
"""
Liquidación de picks contra un snapshot de evento (marcador final + periodos si existen).

Principio (importante para quien lea el código):
  No hace falta que SofaScore exponga un “campo de resultado por mercado” (BTTS, O/U, etc.).
  Para la mayoría de mercados la respuesta se **deriva** del marcador agregado que sí suele venir:
  - **BTTS**: sí si home_score > 0 y away_score > 0; no si alguno es 0 (tras partido terminado).
  - **Over/Under goles**: total = home_score + away_score vs la línea (del texto del mercado o picked_value).
  - **1X2 / ML / doble chance**: del mismo par de goles (o sets en tenis cuando homeScore/awayScore son el conteo final).

  El pick queda **pending** solo cuando falta algo imprescindible que **no** se puede inferir solo con ese
  marcador (partido no terminado, goles faltantes, empate exacto en O/U = push, o mercados que exigen
  desglose por periodo sin el cual no hay veredicto, p. ej. 1er set sin period1 en el JSON).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


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
    except (TypeError, ValueError):
        return None


def _extract_score(score_obj: Any) -> Optional[int]:
    if isinstance(score_obj, dict):
        for k in ("current", "value", "display", "total"):
            if k in score_obj:
                v = _to_int(score_obj.get(k))
                if v is not None:
                    return v
        return _to_int(score_obj.get("current"))
    return _to_int(score_obj)


def _norm_sel(s: Any) -> str:
    return str(s or "").strip().lower()


def _norm_market(m: Any) -> str:
    return str(m or "").strip().lower()


def _result_1x2_from_goals(home: int, away: int) -> str:
    if home > away:
        return "1"
    if away > home:
        return "2"
    return "X"


def _normalize_1x2_selection(sel: str) -> Optional[str]:
    s = str(sel).strip().upper()
    if s in ("1", "X", "2"):
        return "X" if s == "X" else s
    if s in ("HOME", "H", "HOME_WIN", "WIN_HOME", "LOCAL"):
        return "1"
    if s in ("AWAY", "A", "AWAY_WIN", "WIN_AWAY", "VISITANTE"):
        return "2"
    if s in ("DRAW", "D", "EMPATE"):
        return "X"
    m = re.match(r"^([12xX])(\s|\(|$)", str(sel).strip(), flags=re.IGNORECASE)
    if m:
        ch = m.group(1).upper()
        return "X" if ch == "X" else ch
    return None


def _normalize_moneyline_selection(sel: str) -> Optional[str]:
    """Match winner tenis / ML: 1 o 2 (sin empate operativo)."""
    return _normalize_1x2_selection(sel) if _normalize_1x2_selection(sel) in ("1", "2") else None


def _normalize_double_chance(sel: str) -> Optional[str]:
    s = re.sub(r"\s+", "", str(sel).strip().upper())
    if s in ("1X", "1-X", "HOMEORDRAW", "HOME/DRAW", "1ORX"):
        return "1X"
    if s in ("X2", "X-2", "DRAWORAWAY", "DRAW/AWAY", "XOR2"):
        return "X2"
    if s in ("12", "1-2", "HOMEORAWAY", "HOME/AWAY", "1OR2"):
        return "12"
    s_lo = str(sel).strip().lower()
    if "home" in s_lo and "draw" in s_lo:
        return "1X"
    if "draw" in s_lo and ("away" in s_lo or "visit" in s_lo):
        return "X2"
    if "home" in s_lo and ("away" in s_lo or "visit" in s_lo) and "draw" not in s_lo:
        return "12"
    return None


def _normalize_yes_no(sel: str) -> Optional[str]:
    s = _norm_sel(sel)
    if s in ("yes", "y", "si", "sí", "s", "over", "o"):
        return "yes"
    if s in ("no", "n", "under", "u"):
        return "no"
    return None


def _parse_total_line(market: str, picked_value: Optional[float]) -> Optional[float]:
    m = re.search(r"(\d+(?:[.,]\d+)?)", str(market or ""))
    if m:
        try:
            return float(m.group(1).replace(",", "."))
        except ValueError:
            pass
    if picked_value is not None:
        try:
            return float(picked_value)
        except (TypeError, ValueError):
            pass
    return None


def _normalize_ou_side(sel: str) -> Optional[str]:
    s = _norm_sel(sel)
    if s in ("over", "o", "mas", "más", "+", "alta"):
        return "over"
    if s in ("under", "u", "menos", "-", "baja"):
        return "under"
    return None


def settle_pick(
    *,
    market: str,
    selection: str,
    picked_value: Optional[float],
    snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """
    snapshot esperado (de parse_sofascore_event_payload):
      match_state, home_score, away_score,
      period1_home, period1_away (opcional, games del 1er set tenis),
      _error (opcional)
    """
    if snapshot.get("_error"):
        return {
            "outcome": "pending",
            "result_key": None,
            "detail": "fetch_error",
            "evidence_tail": snapshot,
        }

    ms = str(snapshot.get("match_state") or "").lower()
    hs = snapshot.get("home_score")
    aw = snapshot.get("away_score")
    home = _to_int(hs)
    away = _to_int(aw)

    mk = _norm_market(market)

    # --- First set winner (tenis): requiere games del periodo 1 ---
    if "first set" in mk or mk in ("first set winner", "winner first set"):
        p1h = _to_int(snapshot.get("period1_home"))
        p1a = _to_int(snapshot.get("period1_away"))
        sel = _normalize_moneyline_selection(selection)
        if sel not in ("1", "2"):
            return {
                "outcome": "pending",
                "result_key": None,
                "detail": "bad_selection_first_set",
                "score": {"home": home, "away": away},
                "period1": {"home": p1h, "away": p1a},
            }
        if p1h is None or p1a is None:
            return {
                "outcome": "pending",
                "result_key": None,
                "detail": "first_set_scores_unavailable",
                "score": {"home": home, "away": away},
                "period1": {"home": p1h, "away": p1a},
            }
        if p1h == p1a:
            return {
                "outcome": "pending",
                "result_key": None,
                "detail": "first_set_tied_or_incomplete",
                "period1": {"home": p1h, "away": p1a},
            }
        winner = "1" if p1h > p1a else "2"
        return {
            "outcome": "win" if winner == sel else "loss",
            "result_key": winner,
            "detail": "first_set_winner",
            "period1": {"home": p1h, "away": p1a},
            "score": {"home": home, "away": away},
        }

    # Resto requiere partido terminado y marcador final agregado (goles o sets)
    if ms != "finished" or home is None or away is None:
        return {
            "outcome": "pending",
            "result_key": None,
            "detail": "match_not_final_or_scores_missing",
            "match_state": ms,
            "score": {"home": home, "away": away},
        }

    res = _result_1x2_from_goals(home, away)

    # --- 1X2 ---
    if mk == "1x2" or mk.endswith(" 1x2"):
        sel = _normalize_1x2_selection(selection)
        if not sel:
            return {
                "outcome": "pending",
                "result_key": res,
                "detail": "bad_selection_1x2",
                "score": {"home": home, "away": away},
            }
        return {
            "outcome": "win" if sel == res else "loss",
            "result_key": res,
            "detail": "1x2",
            "result_1x2": res,
            "score": {"home": home, "away": away},
        }

    # --- Match winner / ML (tenis o fútbol sin empate) ---
    if mk in (
        "match winner",
        "winner",
        "to win match",
        "moneyline",
        "ml",
    ) or "match winner" in mk:
        sel = _normalize_moneyline_selection(selection)
        if sel not in ("1", "2"):
            return {
                "outcome": "pending",
                "result_key": res,
                "detail": "bad_selection_ml",
                "score": {"home": home, "away": away},
            }
        if res == "X":
            return {
                "outcome": "pending",
                "result_key": res,
                "detail": "draw_unexpected_for_ml",
                "score": {"home": home, "away": away},
            }
        return {
            "outcome": "win" if sel == res else "loss",
            "result_key": res,
            "detail": "moneyline",
            "result_1x2": res,
            "score": {"home": home, "away": away},
        }

    # --- Double chance ---
    if "double chance" in mk or mk in ("1x", "x2", "12"):
        dc = _normalize_double_chance(selection)
        if not dc:
            dc = _normalize_double_chance(mk.replace("double chance", "").strip())
        if not dc:
            return {
                "outcome": "pending",
                "result_key": res,
                "detail": "bad_selection_double_chance",
                "score": {"home": home, "away": away},
            }
        covers = False
        if dc == "1X":
            covers = res in ("1", "X")
        elif dc == "X2":
            covers = res in ("X", "2")
        elif dc == "12":
            covers = res in ("1", "2")
        return {
            "outcome": "win" if covers else "loss",
            "result_key": res,
            "detail": f"double_chance_{dc}",
            "result_1x2": res,
            "score": {"home": home, "away": away},
        }

    # --- BTTS ---
    if "both teams" in mk or "btts" in mk or "ambos anotan" in mk:
        yn = _normalize_yes_no(selection)
        if yn not in ("yes", "no"):
            return {
                "outcome": "pending",
                "result_key": res,
                "detail": "bad_selection_btts",
                "score": {"home": home, "away": away},
            }
        btts_yes = home > 0 and away > 0
        hit = (yn == "yes" and btts_yes) or (yn == "no" and not btts_yes)
        return {
            "outcome": "win" if hit else "loss",
            "result_key": "btts_yes" if btts_yes else "btts_no",
            "detail": "btts",
            "result_1x2": res,
            "score": {"home": home, "away": away},
        }

    # --- Over / Under goles (línea en mercado o picked_value) ---
    if ("game" in mk or "games" in mk) and ("over" in mk or "under" in mk or "o/u" in mk):
        return {
            "outcome": "pending",
            "result_key": res,
            "detail": "tennis_total_games_not_implemented",
            "score": {"home": home, "away": away},
        }

    if "over" in mk or "under" in mk or "o/u" in mk or "total" in mk or "más de" in mk or "menos de" in mk:
        line = _parse_total_line(market, picked_value)
        side = _normalize_ou_side(selection)
        if line is None or side is None:
            return {
                "outcome": "pending",
                "result_key": res,
                "detail": "bad_line_or_side_ou",
                "score": {"home": home, "away": away},
            }
        total = float(home + away)
        if total == line:
            return {
                "outcome": "pending",
                "result_key": res,
                "detail": "push_line_exact",
                "line": line,
                "total_goals": total,
                "score": {"home": home, "away": away},
            }
        over_hit = total > line
        win = (side == "over" and over_hit) or (side == "under" and not over_hit)
        return {
            "outcome": "win" if win else "loss",
            "result_key": "over" if over_hit else "under",
            "detail": "over_under",
            "line": line,
            "total_goals": total,
            "result_1x2": res,
            "score": {"home": home, "away": away},
        }

    return {
        "outcome": "pending",
        "result_key": res,
        "detail": "unsupported_market",
        "market": market,
        "score": {"home": home, "away": away},
    }

#!/usr/bin/env python3
"""
odds_all_processor.py

Processor puro para:
  /api/v1/event/{eventId}/odds/1/all

Salida objetivo:
{
  "extended_markets": {
    "safety": {
      "double_chance": {"1X": 1.07, "X2": 3.40, "12": 1.14},
      "draw_no_bet": {"home": 1.10, "away": 7.0}
    },
    "goals_depth": {
      "btts": {"yes": 2.05, "no": 1.70},
      "over_under_2.5": {"over": 1.61, "under": 2.30}
    },
    "discipline_and_set_pieces": {
      "total_cards_3.5": {"over": 1.72, "under": 2.0},
      "total_corners_9.5": {"over": 1.83, "under": 1.83}
    }
  }
}
"""

from __future__ import annotations

from typing import Any, Dict, Optional


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


def _find_market(markets: list, market_name: str, choice_group: Optional[str] = None) -> Dict[str, Any]:
    for m in markets or []:
        if not isinstance(m, dict):
            continue
        if str(m.get("marketName", "")).lower() != market_name.lower():
            continue
        if choice_group is not None:
            if str(m.get("choiceGroup", "")) != str(choice_group):
                continue
        return m
    return {}


def _choice_odds(market: Dict[str, Any], choice_name: str) -> Optional[float]:
    for ch in market.get("choices") or []:
        if not isinstance(ch, dict):
            continue
        if str(ch.get("name", "")).lower() == choice_name.lower():
            return _fractional_to_decimal(ch.get("fractionalValue"))
    return None


def process_odds_all(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {"extended_markets": {}}

    markets = raw.get("markets") or []
    if not isinstance(markets, list):
        markets = []

    double_chance = _find_market(markets, "Double chance")
    draw_no_bet = _find_market(markets, "Draw no bet")
    btts = _find_market(markets, "Both teams to score")
    match_goals_25 = _find_market(markets, "Match goals", "2.5")
    cards_35 = _find_market(markets, "Cards in match", "3.5")
    corners_95 = _find_market(markets, "Corners 2-Way", "9.5")

    return {
        "extended_markets": {
            "safety": {
                "double_chance": {
                    "1X": _choice_odds(double_chance, "1X"),
                    "X2": _choice_odds(double_chance, "X2"),
                    "12": _choice_odds(double_chance, "12"),
                },
                "draw_no_bet": {
                    "home": _choice_odds(draw_no_bet, "1"),
                    "away": _choice_odds(draw_no_bet, "2"),
                },
            },
            "goals_depth": {
                "btts": {
                    "yes": _choice_odds(btts, "Yes"),
                    "no": _choice_odds(btts, "No"),
                },
                "over_under_2.5": {
                    "over": _choice_odds(match_goals_25, "Over"),
                    "under": _choice_odds(match_goals_25, "Under"),
                },
            },
            "discipline_and_set_pieces": {
                "total_cards_3.5": {
                    "over": _choice_odds(cards_35, "Over"),
                    "under": _choice_odds(cards_35, "Under"),
                },
                "total_corners_9.5": {
                    "over": _choice_odds(corners_95, "Over"),
                    "under": _choice_odds(corners_95, "Under"),
                },
            },
        }
    }


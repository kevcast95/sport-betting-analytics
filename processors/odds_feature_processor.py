#!/usr/bin/env python3
"""
odds_feature_processor.py

Processor puro para:
  /api/v1/event/{eventId}/odds/1/featured
"""

from __future__ import annotations

import re
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


def _get_featured_market(featured: Dict[str, Any], keys: list) -> Dict[str, Any]:
    for key in keys:
        m = featured.get(key)
        if isinstance(m, dict) and m:
            return m
    return {}


def _find_choice(market: Dict[str, Any], name: str) -> Dict[str, Any]:
    for ch in market.get("choices") or []:
        if not isinstance(ch, dict):
            continue
        if str(ch.get("name", "")).lower() == name.lower():
            return ch
    return {}


def _normalize_asian_line(name: str) -> str:
    s = str(name or "").strip()
    # "(-1.5) Arsenal" -> "-1.5 Arsenal"
    return re.sub(r"^\(([^)]+)\)\s*", r"\1 ", s).strip()


def process_odds_feature(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {"market_snapshot": {}}

    featured = raw.get("featured") or {}
    if not isinstance(featured, dict):
        featured = {}

    full_time = _get_featured_market(featured, ["fullTime", "default"])
    asian = _get_featured_market(featured, ["asian"])

    c1 = _find_choice(full_time, "1")
    cx = _find_choice(full_time, "X")
    c2 = _find_choice(full_time, "2")

    asian_choices = asian.get("choices") or []
    asian_home = asian_choices[0] if len(asian_choices) > 0 and isinstance(asian_choices[0], dict) else {}
    asian_away = asian_choices[1] if len(asian_choices) > 1 and isinstance(asian_choices[1], dict) else {}

    return {
        "market_snapshot": {
            "full_time_1x2": {
                "home": {
                    "current": _fractional_to_decimal(c1.get("fractionalValue")),
                    "initial": _fractional_to_decimal(c1.get("initialFractionalValue")),
                    "trend": c1.get("change"),
                },
                "draw": {
                    "current": _fractional_to_decimal(cx.get("fractionalValue")),
                    "initial": _fractional_to_decimal(cx.get("initialFractionalValue")),
                    "trend": cx.get("change"),
                },
                "away": {
                    "current": _fractional_to_decimal(c2.get("fractionalValue")),
                    "initial": _fractional_to_decimal(c2.get("initialFractionalValue")),
                    "trend": c2.get("change"),
                },
            },
            "asian_handicap": {
                "line": _normalize_asian_line(asian_home.get("name", "")),
                "home_odds": _fractional_to_decimal(asian_home.get("fractionalValue")),
                "away_odds": _fractional_to_decimal(asian_away.get("fractionalValue")),
            },
        }
    }


"""
Contrato de candidatos (Tier A/B) por deporte para select_candidates y API inspector.

Fútbol: alineado con jobs/select_candidates.py (lineups + h2h + rachas + cuotas; estadísticas para Tier A).
Tenis: sin alineaciones ni rachas de equipo; cuotas obligatorias; Tier A si hay estadísticas o H2H útil.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def normalize_sport(s: Any) -> str:
    x = str(s or "football").strip().lower()
    return x if x else "football"


def diagnostics_flags(d: Any) -> Dict[str, bool]:
    base = d if isinstance(d, dict) else {}
    return {
        "event_ok": bool(base.get("event_ok")),
        "lineups_ok": bool(base.get("lineups_ok")),
        "statistics_ok": bool(base.get("statistics_ok")),
        "h2h_ok": bool(base.get("h2h_ok")),
        "team_streaks_ok": bool(base.get("team_streaks_ok")),
        "team_season_stats_ok": bool(base.get("team_season_stats_ok")),
        "odds_all_ok": bool(base.get("odds_all_ok")),
        "odds_featured_ok": bool(base.get("odds_featured_ok")),
    }


def base_contract_ok(flags: Dict[str, bool], *, sport: str) -> bool:
    sp = normalize_sport(sport)
    if sp == "tennis":
        return bool(flags["event_ok"]) and bool(flags["odds_all_ok"] or flags["odds_featured_ok"])
    return (
        bool(flags["event_ok"])
        and bool(flags["lineups_ok"])
        and bool(flags["h2h_ok"])
        and bool(flags["team_streaks_ok"])
        and bool(flags["odds_all_ok"] or flags["odds_featured_ok"])
    )


def classify_tier(flags: Dict[str, bool], *, sport: str) -> Optional[str]:
    """
    None si no cumple contrato base.
    'A' / 'B' según deporte.
    """
    if not base_contract_ok(flags, sport=sport):
        return None
    sp = normalize_sport(sport)
    if sp == "tennis":
        if flags["statistics_ok"] or flags["h2h_ok"]:
            return "A"
        return "B"
    return "A" if flags["statistics_ok"] else "B"


def reject_reason(flags: Dict[str, bool], match_state: str, *, sport: str) -> Optional[str]:
    ms = str(match_state or "").lower()
    if ms == "finished":
        return "match_finished"
    sp = normalize_sport(sport)
    if not flags["event_ok"]:
        return "event_not_ok"
    if sp == "tennis":
        if not (flags["odds_all_ok"] or flags["odds_featured_ok"]):
            return "no_odds"
        return None
    if not flags["lineups_ok"]:
        return "lineups_not_ok"
    if not flags["h2h_ok"]:
        return "h2h_not_ok"
    if not flags["team_streaks_ok"]:
        return "team_streaks_not_ok"
    if not (flags["odds_all_ok"] or flags["odds_featured_ok"]):
        return "no_odds"
    return None


def contract_description(*, sport: str) -> Dict[str, str]:
    sp = normalize_sport(sport)
    if sp == "tennis":
        return {
            "base": "event_ok + (odds_all_ok | odds_featured_ok)",
            "tier_A": "base + (statistics_ok | h2h_ok)",
            "tier_B": "base sin statistics ni h2h (solo cuotas + contexto mínimo)",
        }
    return {
        "base": "event_ok + lineups_ok + h2h_ok + team_streaks_ok + (odds_all_ok | odds_featured_ok)",
        "tier_A": "base + statistics_ok",
        "tier_B": "base sin statistics_ok (fallback)",
    }

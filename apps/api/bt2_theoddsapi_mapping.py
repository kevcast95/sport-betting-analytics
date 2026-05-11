"""
The Odds API league/sport-key mappings used by BT2 offline and lab tooling.

Keep provider identifiers centralized here so scripts do not drift into stale
sport keys. In particular, TOA uses ``soccer_france_ligue_one`` for Ligue 1.
"""

from __future__ import annotations

from typing import Final

TOA_LIGUE_1_SPORT_KEY: Final[str] = "soccer_france_ligue_one"

TOA_SPORT_KEYS_BY_SM_LEAGUE_ID: Final[dict[int, str]] = {
    8: "soccer_epl",
    82: "soccer_germany_bundesliga",
    301: TOA_LIGUE_1_SPORT_KEY,
    384: "soccer_italy_serie_a",
    564: "soccer_spain_la_liga",
}

TOA_TIER_S_SPORT_KEYS: Final[tuple[str, ...]] = (
    TOA_SPORT_KEYS_BY_SM_LEAGUE_ID[8],
    TOA_SPORT_KEYS_BY_SM_LEAGUE_ID[82],
    TOA_SPORT_KEYS_BY_SM_LEAGUE_ID[301],
    TOA_SPORT_KEYS_BY_SM_LEAGUE_ID[384],
    TOA_SPORT_KEYS_BY_SM_LEAGUE_ID[564],
)

TOA_SPORT_LABELS: Final[dict[str, str]] = {
    "soccer_epl": "EPL",
    "soccer_spain_la_liga": "La Liga",
    "soccer_germany_bundesliga": "Bundesliga",
    "soccer_italy_serie_a": "Serie A",
    TOA_LIGUE_1_SPORT_KEY: "Ligue 1",
    "soccer_netherlands_eredivisie": "Eredivisie",
    "soccer_turkey_super_league": "Super Lig",
    "soccer_portugal_primeira_liga": "Liga Portugal",
    "soccer_colombia_primera_a": "Liga BetPlay",
}


def toa_sport_key_for_sm_league_id(sm_league_id: int | str) -> str | None:
    """Return the TOA sport_key for a SportMonks league id when BT2 has a closed mapping."""
    try:
        key = int(sm_league_id)
    except (TypeError, ValueError):
        return None
    return TOA_SPORT_KEYS_BY_SM_LEAGUE_ID.get(key)

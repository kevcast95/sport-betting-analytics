"""
T-283 / US-BE-062 — `uniqueTournament` SofaScore por liga F2 (misma nómina que S6.3).

IDs tomados de URLs públicas sofascore.com (tournament/.../id). Override opcional por env
`BT2_F2_SOFASCORE_UNIQUE_TOURNAMENT_IDS` = JSON objeto sportmonks_id -> unique_tournament_id.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from apps.api.bt2_f2_league_constants import F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS

# sportmonks_id de liga → uniqueTournament.id en API SofaScore v1
_DEFAULT_UT: dict[int, int] = {
    F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["premier_league"]: 17,
    F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["la_liga"]: 8,
    F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["serie_a"]: 23,
    F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["bundesliga"]: 35,
    F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["ligue_1"]: 34,
}


def f2_sofascore_unique_tournament_by_sm_league_id() -> dict[int, int]:
    raw = (os.getenv("BT2_F2_SOFASCORE_UNIQUE_TOURNAMENT_IDS") or "").strip()
    if not raw:
        return dict(_DEFAULT_UT)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return dict(_DEFAULT_UT)
    if not isinstance(data, dict):
        return dict(_DEFAULT_UT)
    out = dict(_DEFAULT_UT)
    for k, v in data.items():
        try:
            out[int(k)] = int(v)
        except (TypeError, ValueError):
            continue
    return out


def sofascore_ut_id_for_sm_league(sm_league_id: Optional[int]) -> Optional[int]:
    if sm_league_id is None:
        return None
    return f2_sofascore_unique_tournament_by_sm_league_id().get(int(sm_league_id))

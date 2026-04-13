"""
T-198 — UPSERT de `raw_sportmonks_fixtures` (payload fresco, sin DO NOTHING silencioso).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any, Optional


def _extract_team_names(participants: Any) -> tuple[Optional[str], Optional[str]]:
    home_team = away_team = None
    if not isinstance(participants, list):
        return home_team, away_team
    for p in participants:
        if not isinstance(p, dict):
            continue
        loc = (p.get("meta") or {}).get("location", "")
        name = p.get("name", "")
        if loc == "home":
            home_team = name
        elif loc == "away":
            away_team = name
    return home_team, away_team


def raw_fixture_upsert_params(fx: dict) -> Optional[dict[str, Any]]:
    """
    Parámetros nombrados para SQLAlchemy `text()` + CAST jsonb.
    Retorna None si falta `id` del fixture.
    """
    fixture_id = fx.get("id")
    if not fixture_id:
        return None

    fixture_date: Optional[date] = None
    starting_at = fx.get("starting_at") or fx.get("starting_at_timestamp")
    if starting_at and isinstance(starting_at, str):
        try:
            fixture_date = datetime.fromisoformat(
                starting_at.replace("Z", "+00:00")
            ).date()
        except ValueError:
            pass

    league_id = fx.get("league_id")
    home_team, away_team = _extract_team_names(fx.get("participants", []))

    return {
        "fixture_id": int(fixture_id),
        "fixture_date": fixture_date,
        "league_id": league_id,
        "home_team": home_team,
        "away_team": away_team,
        "payload": json.dumps(fx, ensure_ascii=False),
    }


UPSERT_RAW_FIXTURE_SQL = """
INSERT INTO raw_sportmonks_fixtures
    (fixture_id, fixture_date, league_id, home_team, away_team, payload)
VALUES
    (:fixture_id, :fixture_date, :league_id,
     :home_team, :away_team, CAST(:payload AS jsonb))
ON CONFLICT (fixture_id) DO UPDATE SET
    fixture_date = EXCLUDED.fixture_date,
    league_id = EXCLUDED.league_id,
    home_team = EXCLUDED.home_team,
    away_team = EXCLUDED.away_team,
    payload = EXCLUDED.payload,
    fetched_at = NOW()
"""

UPSERT_RAW_FIXTURE_SQL_PSYCOPG2 = """
INSERT INTO raw_sportmonks_fixtures
    (fixture_id, fixture_date, league_id, home_team, away_team, payload)
VALUES
    (%s, %s, %s, %s, %s, %s::jsonb)
ON CONFLICT (fixture_id) DO UPDATE SET
    fixture_date = EXCLUDED.fixture_date,
    league_id = EXCLUDED.league_id,
    home_team = EXCLUDED.home_team,
    away_team = EXCLUDED.away_team,
    payload = EXCLUDED.payload,
    fetched_at = NOW()
"""


def raw_fixture_upsert_tuple_psycopg2(fx: dict) -> Optional[tuple[Any, ...]]:
    p = raw_fixture_upsert_params(fx)
    if p is None:
        return None
    return (
        p["fixture_id"],
        p["fixture_date"],
        p["league_id"],
        p["home_team"],
        p["away_team"],
        p["payload"],
    )


def upsert_raw_sportmonks_fixture_psycopg2(cur, fx: dict) -> bool:
    """UPSERT síncrono (psycopg2). True si ejecutó fila."""
    tup = raw_fixture_upsert_tuple_psycopg2(fx)
    if tup is None:
        return False
    cur.execute(UPSERT_RAW_FIXTURE_SQL_PSYCOPG2, tup)
    return True

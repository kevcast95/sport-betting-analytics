"""
T-283 — lectura defensiva de `sport/football/scheduled-events/{date}` (SofaScore v1).

Solo benchmark US-BE-062; no productivo.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from core.sofascore_http import sofascore_get_json


def sofascore_fetch_football_scheduled_payload(date_yyyy_mm_dd: str) -> Any:
    url = f"https://www.sofascore.com/api/v1/sport/football/scheduled-events/{date_yyyy_mm_dd}"
    return sofascore_get_json(url)


def _events_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        ev = payload.get("events") or payload.get("scheduledEvents") or payload.get("scheduled_events")
        if isinstance(ev, list):
            return [x for x in ev if isinstance(x, dict)]
    return []


def sofascore_football_event_stubs_for_date(date_yyyy_mm_dd: str) -> list[dict[str, Any]]:
    """
    Devuelve lista de dicts con:
      sofascore_event_id, kickoff_utc, unique_tournament_id, home_name, away_name
    """
    payload = sofascore_fetch_football_scheduled_payload(date_yyyy_mm_dd)
    out: list[dict[str, Any]] = []
    for ev in _events_list(payload):
        eid = ev.get("id")
        if eid is None:
            continue
        try:
            eid_i = int(eid)
        except (TypeError, ValueError):
            continue
        ts = ev.get("startTimestamp")
        if ts is None:
            continue
        try:
            kick = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            continue
        tinfo = ev.get("tournament") or {}
        ut = (tinfo.get("uniqueTournament") or {}) if isinstance(tinfo, dict) else {}
        ut_id = ut.get("id")
        try:
            ut_i = int(ut_id) if ut_id is not None else -1
        except (TypeError, ValueError):
            ut_i = -1
        ht = ev.get("homeTeam") or {}
        at = ev.get("awayTeam") or {}
        if not isinstance(ht, dict) or not isinstance(at, dict):
            continue
        hn = str(ht.get("name") or ht.get("shortName") or "").strip()
        an = str(at.get("name") or at.get("shortName") or "").strip()
        if not hn or not an:
            continue
        out.append(
            {
                "sofascore_event_id": eid_i,
                "kickoff_utc": kick,
                "unique_tournament_id": ut_i,
                "home_name": hn,
                "away_name": an,
            }
        )
    return out

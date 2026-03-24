"""Metadatos de partido (A vs B, liga, hora) desde event_features del mismo run."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo


def _label_from_context(ec: Dict[str, Any]) -> str:
    home = ec.get("home_team") or "?"
    away = ec.get("away_team") or "?"
    return f"{home} vs {away}"


def load_event_meta_for_daily_run(
    conn: sqlite3.Connection, *, daily_run_id: int
) -> Dict[int, Dict[str, Optional[str]]]:
    """
    Mapa event_id -> {event_label, league, kickoff_display, kickoff_at_utc, match_state}.
    Usa el created_at_utc del daily_run como captured_at de features (convención ingest).
    """
    run = conn.execute(
        "SELECT created_at_utc FROM daily_runs WHERE daily_run_id = ?",
        (daily_run_id,),
    ).fetchone()
    if run is None:
        return {}
    cap = str(run["created_at_utc"])
    cur = conn.execute(
        """
        SELECT event_id, features_json
        FROM event_features
        WHERE captured_at_utc = ?
        """,
        (cap,),
    )
    out: Dict[int, Dict[str, Optional[str]]] = {}
    for row in cur.fetchall():
        eid = int(row["event_id"])
        raw = row["features_json"]
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        ec = data.get("event_context") or {}
        if not isinstance(ec, dict):
            continue
        label = _label_from_context(ec)
        league = ec.get("tournament")
        league_s = str(league) if league is not None else None
        match_state = ec.get("match_state")
        match_state_s = str(match_state).strip().lower() if match_state is not None else None
        kickoff: Optional[str] = None
        kickoff_at_utc: Optional[str] = None
        ts = ec.get("start_timestamp")
        try:
            if ts is not None:
                sec = int(ts)
                dt_utc = datetime.fromtimestamp(sec, tz=timezone.utc)
                dt_bo = dt_utc.astimezone(ZoneInfo("America/Bogota"))
                kickoff = dt_bo.strftime("%H:%M") + " · hora Colombia"
                kickoff_at_utc = dt_utc.isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError, OSError):
            pass
        out[eid] = {
            "event_label": label,
            "league": league_s,
            "kickoff_display": kickoff,
            "kickoff_at_utc": kickoff_at_utc,
            "match_state": match_state_s,
        }
    return out


def merge_meta_into_odds_ref(
    odds_reference: Any,
    meta: Optional[Dict[str, Optional[str]]],
) -> Any:
    """Devuelve odds_reference enriquecido con event_label si falta (solo para respuesta API)."""
    if not meta:
        return odds_reference
    base: Dict[str, Any] = {}
    if isinstance(odds_reference, dict):
        base = dict(odds_reference)
    if base.get("event_label") is None and meta.get("event_label"):
        base["event_label"] = meta["event_label"]
    if base.get("league") is None and meta.get("league"):
        base["league"] = meta["league"]
    if base.get("kickoff_display") is None and meta.get("kickoff_display"):
        base["kickoff_display"] = meta["kickoff_display"]
    if base.get("kickoff_at_utc") is None and meta.get("kickoff_at_utc"):
        base["kickoff_at_utc"] = meta["kickoff_at_utc"]
    if base.get("match_state") is None and meta.get("match_state"):
        base["match_state"] = meta["match_state"]
    return base if base else odds_reference


def is_stake_taken_locked_now(
    conn: sqlite3.Connection, *, daily_run_id: int, event_id: int
) -> bool:
    """
    True solo si el partido ya terminó (match_state=finished).
    Sin match_state → no se bloquea.
    """
    meta = load_event_meta_for_daily_run(conn, daily_run_id=daily_run_id).get(
        int(event_id)
    )
    if not meta:
        return False
    return str(meta.get("match_state") or "").strip().lower() == "finished"

"""Metadatos de partido (A vs B, liga, hora) desde event_features del mismo run."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _label_from_context(ec: Dict[str, Any]) -> str:
    home = ec.get("home_team") or "?"
    away = ec.get("away_team") or "?"
    return f"{home} vs {away}"


def load_event_meta_for_daily_run(
    conn: sqlite3.Connection, *, daily_run_id: int
) -> Dict[int, Dict[str, Optional[str]]]:
    """
    Mapa event_id -> {event_label, league, kickoff_display}.
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
        kickoff: Optional[str] = None
        ts = ec.get("start_timestamp")
        try:
            if ts is not None:
                sec = int(ts)
                dt = datetime.fromtimestamp(sec, tz=timezone.utc)
                kickoff = dt.strftime("%Y-%m-%d %H:%M UTC")
        except (TypeError, ValueError, OSError):
            pass
        out[eid] = {
            "event_label": label,
            "league": league_s,
            "kickoff_display": kickoff,
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
    return base if base else odds_reference

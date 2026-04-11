"""
T-189 / T-190 / D-06-028 — Contexto histórico y meta de ingesta de cuotas desde Postgres/CDM.

No serializa marcadores ni claves prohibidas (D-06-002): solo agregados y forma W/D/L.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def _utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _outcome_for_team(
    home_team_id: int,
    away_team_id: int,
    result_home: int,
    result_away: int,
    team_id: int,
) -> Optional[str]:
    if team_id == home_team_id:
        if result_home > result_away:
            return "W"
        if result_home < result_away:
            return "L"
        return "D"
    if team_id == away_team_id:
        if result_away > result_home:
            return "W"
        if result_away < result_home:
            return "L"
        return "D"
    return None


def fetch_h2h_aggregate(
    cur,
    *,
    current_home_team_id: int,
    current_away_team_id: int,
    before_kickoff: datetime,
    limit: int = 15,
) -> Optional[dict[str, Any]]:
    """
    Duelos directos previos entre los dos equipos (cualquier localía).
    """
    cur.execute(
        """
        SELECT home_team_id, away_team_id, result_home, result_away
        FROM bt2_events
        WHERE status = 'finished'
          AND kickoff_utc IS NOT NULL
          AND kickoff_utc < %s
          AND result_home IS NOT NULL
          AND result_away IS NOT NULL
          AND home_team_id IS NOT NULL
          AND away_team_id IS NOT NULL
          AND (
            (home_team_id = %s AND away_team_id = %s)
            OR (home_team_id = %s AND away_team_id = %s)
          )
        ORDER BY kickoff_utc DESC
        LIMIT %s
        """,
        (
            before_kickoff,
            current_home_team_id,
            current_away_team_id,
            current_away_team_id,
            current_home_team_id,
            limit,
        ),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    hw = dr = aw = 0
    for ht, at, rh, ra in rows:
        try:
            rih, ria = int(rh), int(ra)
        except (TypeError, ValueError):
            continue
        if ht == current_home_team_id and at == current_away_team_id:
            if rih > ria:
                hw += 1
            elif rih < ria:
                aw += 1
            else:
                dr += 1
        elif ht == current_away_team_id and at == current_home_team_id:
            if ria > rih:
                hw += 1
            elif ria < rih:
                aw += 1
            else:
                dr += 1
    meetings = len(rows)
    return {
        "available": True,
        "meetings_in_sample": meetings,
        "current_home_wins": hw,
        "draws": dr,
        "current_away_wins": aw,
    }


def fetch_team_form_string(
    cur,
    *,
    team_id: int,
    before_kickoff: datetime,
    max_matches: int = 5,
) -> Optional[str]:
    cur.execute(
        """
        SELECT home_team_id, away_team_id, result_home, result_away
        FROM bt2_events
        WHERE status = 'finished'
          AND kickoff_utc IS NOT NULL
          AND kickoff_utc < %s
          AND result_home IS NOT NULL
          AND result_away IS NOT NULL
          AND home_team_id IS NOT NULL
          AND away_team_id IS NOT NULL
          AND (home_team_id = %s OR away_team_id = %s)
        ORDER BY kickoff_utc DESC
        LIMIT %s
        """,
        (before_kickoff, team_id, team_id, max_matches * 2),
    )
    parts: list[str] = []
    for ht, at, rh, ra in cur.fetchall():
        try:
            rih, ria = int(rh), int(ra)
        except (TypeError, ValueError):
            continue
        o = _outcome_for_team(int(ht), int(at), rih, ria, team_id)
        if o:
            parts.append(o)
        if len(parts) >= max_matches:
            break
    if not parts:
        return None
    return "".join(parts)


def streaks_from_form(form: str) -> dict[str, int]:
    """Rachas simples desde cadena W/D/L (último partido al final de la cadena)."""

    def unbeaten_run(s: str) -> int:
        n = 0
        for ch in reversed(s):
            if ch in ("W", "D"):
                n += 1
            else:
                break
        return n

    def winless_run(s: str) -> int:
        n = 0
        for ch in reversed(s):
            if ch != "W":
                n += 1
            else:
                break
        return n

    def winning_run(s: str) -> int:
        n = 0
        for ch in reversed(s):
            if ch == "W":
                n += 1
            else:
                break
        return n

    return {
        "unbeaten_run": unbeaten_run(form),
        "winless_run": winless_run(form),
        "winning_run": winning_run(form),
    }


def fetch_odds_ingest_meta(cur, event_id: int) -> Optional[dict[str, Any]]:
    """T-190 — ventana temporal de filas en bt2_odds_snapshot (no serie completa por selección)."""
    cur.execute(
        """
        SELECT
            MIN(fetched_at) AS mn,
            MAX(fetched_at) AS mx,
            COUNT(DISTINCT date_trunc('minute', fetched_at)) AS batches
        FROM bt2_odds_snapshot
        WHERE event_id = %s
        """,
        (event_id,),
    )
    row = cur.fetchone()
    if not row or row[0] is None or row[1] is None:
        return None
    mn, mx, batches = row[0], row[1], row[2]
    try:
        b = int(batches)
    except (TypeError, ValueError):
        b = 1
    return {
        "first_fetched_at_iso": _utc_iso(mn if isinstance(mn, datetime) else datetime.now(tz=timezone.utc)),
        "last_fetched_at_iso": _utc_iso(mx if isinstance(mx, datetime) else datetime.now(tz=timezone.utc)),
        "distinct_fetch_batches": max(1, b),
    }


def extract_lineups_summary_from_raw_payload(payload: Any) -> Optional[dict[str, Any]]:
    """
    Lectura defensiva de payload SportMonks en raw_sportmonks_fixtures.
    Solo agregados; sin nombres de jugador en fase 1 (reduce tokens y PII).
    """
    if not isinstance(payload, dict):
        return None
    lu = payload.get("lineups")
    if not isinstance(lu, list) or not lu:
        return None
    n = min(len(lu), 200)
    team_counts: dict[str, int] = {}
    for row in lu[:200]:
        if not isinstance(row, dict):
            continue
        tid = row.get("team_id")
        if tid is None:
            continue
        key = str(int(tid)) if isinstance(tid, (int, float)) else str(tid)
        team_counts[key] = team_counts.get(key, 0) + 1
    if not team_counts:
        return {"available": True, "lineup_rows_observed": n, "teams_distinct": 0}
    return {
        "available": True,
        "lineup_rows_observed": n,
        "teams_distinct": len(team_counts),
        "max_rows_per_team_side": max(team_counts.values()),
    }

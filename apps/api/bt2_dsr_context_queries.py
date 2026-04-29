"""
T-189 / T-190 / D-06-028 — Contexto histórico y meta de ingesta de cuotas desde Postgres/CDM.

No serializa marcadores ni claves prohibidas (D-06-002): solo agregados y forma W/D/L.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional


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


def fetch_team_form_string_same_league(
    cur,
    *,
    team_id: int,
    league_id: int,
    before_kickoff: datetime,
    max_matches: int = 5,
) -> Optional[str]:
    """Últimos partidos terminados del equipo en una liga concreta (`league_id`)."""
    cur.execute(
        """
        SELECT home_team_id, away_team_id, result_home, result_away
        FROM bt2_events
        WHERE status = 'finished'
          AND league_id = %s
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
        (league_id, before_kickoff, team_id, team_id, max_matches * 4),
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


def fetch_team_form_string_designated_role(
    cur,
    *,
    team_id: int,
    before_kickoff: datetime,
    max_matches: int = 5,
    only_as_home: bool = False,
    only_as_away: bool = False,
) -> Optional[str]:
    """Forma donde el equipo solo cuenta como local o solo como visitante."""
    if only_as_home == only_as_away:
        return None
    if only_as_home:
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
              AND home_team_id = %s
            ORDER BY kickoff_utc DESC
            LIMIT %s
            """,
            (before_kickoff, team_id, max_matches * 4),
        )
    else:
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
              AND away_team_id = %s
            ORDER BY kickoff_utc DESC
            LIMIT %s
            """,
            (before_kickoff, team_id, max_matches * 4),
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


def fetch_scored_conceded_last_matches(
    cur,
    *,
    team_id: int,
    before_kickoff: datetime,
    max_matches: int = 5,
    league_id: Optional[int] = None,
    only_as_home: bool = False,
    only_as_away: bool = False,
) -> Optional[tuple[int, int, int]]:
    """
    Suma goles a favor / en contra del equipo en los últimos partidos terminados.
    Devuelve (partidos_usados, scored_sum, conceded_sum).
    """
    if only_as_home:
        if league_id is not None:
            cur.execute(
                """
                SELECT home_team_id, away_team_id, result_home, result_away
                FROM bt2_events
                WHERE status = 'finished'
                  AND league_id = %s
                  AND kickoff_utc IS NOT NULL
                  AND kickoff_utc < %s
                  AND result_home IS NOT NULL
                  AND result_away IS NOT NULL
                  AND home_team_id IS NOT NULL
                  AND away_team_id IS NOT NULL
                  AND home_team_id = %s
                ORDER BY kickoff_utc DESC
                LIMIT %s
                """,
                (league_id, before_kickoff, team_id, max_matches * 4),
            )
        else:
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
                  AND home_team_id = %s
                ORDER BY kickoff_utc DESC
                LIMIT %s
                """,
                (before_kickoff, team_id, max_matches * 4),
            )
    elif only_as_away:
        if league_id is not None:
            cur.execute(
                """
                SELECT home_team_id, away_team_id, result_home, result_away
                FROM bt2_events
                WHERE status = 'finished'
                  AND league_id = %s
                  AND kickoff_utc IS NOT NULL
                  AND kickoff_utc < %s
                  AND result_home IS NOT NULL
                  AND result_away IS NOT NULL
                  AND home_team_id IS NOT NULL
                  AND away_team_id IS NOT NULL
                  AND away_team_id = %s
                ORDER BY kickoff_utc DESC
                LIMIT %s
                """,
                (league_id, before_kickoff, team_id, max_matches * 4),
            )
        else:
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
                  AND away_team_id = %s
                ORDER BY kickoff_utc DESC
                LIMIT %s
                """,
                (before_kickoff, team_id, max_matches * 4),
            )
    elif league_id is not None:
        cur.execute(
            """
            SELECT home_team_id, away_team_id, result_home, result_away
            FROM bt2_events
            WHERE status = 'finished'
              AND league_id = %s
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
            (league_id, before_kickoff, team_id, team_id, max_matches * 4),
        )
    else:
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
            (before_kickoff, team_id, team_id, max_matches * 4),
        )

    scored = conceded = 0
    used = 0
    for ht, at, rh, ra in cur.fetchall():
        if used >= max_matches:
            break
        try:
            ht_i, at_i = int(ht), int(at)
            rih, ria = int(rh), int(ra)
        except (TypeError, ValueError):
            continue
        if team_id == ht_i:
            scored += rih
            conceded += ria
        elif team_id == at_i:
            scored += ria
            conceded += rih
        else:
            continue
        used += 1
    if used == 0:
        return None
    return used, scored, conceded


def fetch_rest_days_before_kickoff(
    cur,
    *,
    team_id: int,
    before_kickoff: datetime,
) -> Optional[int]:
    """Días calendario entre el último partido terminado del equipo y `before_kickoff`."""
    cur.execute(
        """
        SELECT kickoff_utc
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
        LIMIT 1
        """,
        (before_kickoff, team_id, team_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    prev = row["kickoff_utc"] if isinstance(row, Mapping) else row[0]
    if not isinstance(prev, datetime):
        return None
    if prev.tzinfo is None:
        prev = prev.replace(tzinfo=timezone.utc)
    bk = before_kickoff
    if bk.tzinfo is None:
        bk = bk.replace(tzinfo=timezone.utc)
    delta = bk.date() - prev.date()
    return int(delta.days)


def fetch_h2h_aggregate_fixed_orientation(
    cur,
    *,
    host_team_id: int,
    guest_team_id: int,
    before_kickoff: datetime,
    limit: int = 15,
) -> Optional[dict[str, Any]]:
    """
    Enfrentamientos previos con **la misma orientación** que el partido actual:
    `home_team_id` histórico = `host_team_id`, visita = `guest_team_id`.
    """
    cur.execute(
        """
        SELECT result_home, result_away
        FROM bt2_events
        WHERE status = 'finished'
          AND kickoff_utc IS NOT NULL
          AND kickoff_utc < %s
          AND result_home IS NOT NULL
          AND result_away IS NOT NULL
          AND home_team_id = %s
          AND away_team_id = %s
        ORDER BY kickoff_utc DESC
        LIMIT %s
        """,
        (before_kickoff, host_team_id, guest_team_id, limit),
    )
    rows = cur.fetchall()
    if not rows:
        return None
    hw = dr = gw = 0
    for rh, ra in rows:
        try:
            rih, ria = int(rh), int(ra)
        except (TypeError, ValueError):
            continue
        if rih > ria:
            hw += 1
        elif rih < ria:
            gw += 1
        else:
            dr += 1
    meetings = len(rows)
    return {
        "available": True,
        "meetings_in_sample": meetings,
        "fixed_orientation_note": "solo_partidos_donde_el_local_actual_fue_local_en_bt2_events",
        "host_side_wins": hw,
        "draws": dr,
        "guest_side_wins": gw,
    }


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
    if not row:
        return None
    if isinstance(row, Mapping):
        mn = row.get("mn")
        mx = row.get("mx")
        batches = row.get("batches")
    else:
        mn, mx, batches = row[0], row[1], row[2]
    if mn is None or mx is None:
        return None
    try:
        b = int(batches)
    except (TypeError, ValueError):
        b = 1
    return {
        "first_fetched_at_iso": _utc_iso(mn if isinstance(mn, datetime) else datetime.now(tz=timezone.utc)),
        "last_fetched_at_iso": _utc_iso(mx if isinstance(mx, datetime) else datetime.now(tz=timezone.utc)),
        "distinct_fetch_batches": max(1, b),
    }


def _sm_home_away_team_ids(payload: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    participants = payload.get("participants") or []
    home_id = away_id = None
    if not isinstance(participants, list):
        return home_id, away_id
    for p in participants:
        if not isinstance(p, dict):
            continue
        loc = (p.get("meta") or {}).get("location", "")
        pid = p.get("id")
        if pid is None:
            continue
        try:
            tid = int(pid)
        except (TypeError, ValueError):
            continue
        if loc == "home":
            home_id = tid
        elif loc == "away":
            away_id = tid
    return home_id, away_id


def extract_lineups_summary_from_raw_payload(payload: Any) -> Optional[dict[str, Any]]:
    """
    Lectura defensiva de payload SportMonks en raw_sportmonks_fixtures.
    Solo agregados; sin nombres de jugador en fase 1 (reduce tokens y PII).
    Cuenta filas `type_id` 11 (once inicial típico SM) por bando cuando hay participants.
    """
    if not isinstance(payload, dict):
        return None
    lu = payload.get("lineups")
    if not isinstance(lu, list) or not lu:
        return None
    n = min(len(lu), 200)
    team_counts: dict[str, int] = {}
    xi_home = xi_away = 0
    home_id, away_id = _sm_home_away_team_ids(payload)
    for row in lu[:200]:
        if not isinstance(row, dict):
            continue
        tid = row.get("team_id")
        if tid is None:
            continue
        key = str(int(tid)) if isinstance(tid, (int, float)) else str(tid)
        team_counts[key] = team_counts.get(key, 0) + 1
        if row.get("type_id") == 11:
            try:
                tnum = int(tid) if isinstance(tid, (int, float)) else int(key)
            except (TypeError, ValueError):
                continue
            if home_id is not None and tnum == home_id:
                xi_home += 1
            elif away_id is not None and tnum == away_id:
                xi_away += 1
    base: dict[str, Any] = {
        "available": True,
        "lineup_rows_observed": n,
        "teams_distinct": len(team_counts),
    }
    if team_counts:
        base["max_rows_per_team_side"] = max(team_counts.values())
    if xi_home:
        base["starting_xi_rows_home"] = xi_home
    if xi_away:
        base["starting_xi_rows_away"] = xi_away
    if not team_counts and not xi_home and not xi_away:
        base["teams_distinct"] = 0
    return base


def sm_participant_sportmonks_team_ids(payload: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    """
    IDs de equipo en el namespace SportMonks tomados de `participants[]` (meta.location home/away).

    Usado por el carril shadow-native para enlazar con `bt2_teams.sportmonks_id` cuando el CDM
    no tiene `home_team_id` / `away_team_id` poblados.
    """
    return _sm_home_away_team_ids(payload)

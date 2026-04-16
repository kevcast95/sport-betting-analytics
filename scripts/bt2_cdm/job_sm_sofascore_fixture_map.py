#!/usr/bin/env python3
"""
T-283 / US-BE-062 — Construye/actualiza mapeo SM ↔ SofaScore (D-06-068 §6).

Persistencia: `bt2_nonprod_sm_sofascore_fixture_map_s64`. No aborta por filas
`needs_review` o sin candidato.

Uso:
  python3 scripts/bt2_cdm/job_sm_sofascore_fixture_map.py
  python3 scripts/bt2_cdm/job_sm_sofascore_fixture_map.py --operating-day 2026-04-16 --dry-run

Env: BT2_DATABASE_URL, opcional BT2_SOFASCORE_MAP_SKEW_SEC (default 720).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv

load_dotenv(Path(_repo_root) / ".env")

import psycopg2
import psycopg2.extras

from apps.api.bt2_benchmark_team_name_normalize import normalize_benchmark_team_name
from apps.api.bt2_f2_league_constants import resolve_f2_official_league_bt2_ids
from apps.api.bt2_f2_sofascore_constants import sofascore_ut_id_for_sm_league
from apps.api.bt2_sofascore_football_schedule import sofascore_football_event_stubs_for_date
from apps.api.bt2_sofascore_map_match import match_sofa_event_for_sm_fixture

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
logger = logging.getLogger("job_sm_sofascore_fixture_map")


def _conn():
    url = (os.getenv("BT2_DATABASE_URL") or "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        raise SystemExit("Falta BT2_DATABASE_URL")
    return psycopg2.connect(url)


def _utc_day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def main() -> int:
    p = argparse.ArgumentParser(description="Mapeo SM ↔ SofaScore benchmark S6.4")
    p.add_argument("--operating-day", type=str, default=None, help="YYYY-MM-DD UTC")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.operating_day:
        y, m, d = (int(x) for x in args.operating_day.split("-"))
        op_day = date(y, m, d)
    else:
        op_day = datetime.now(timezone.utc).date()

    day_s = op_day.isoformat()
    skew = int(os.getenv("BT2_SOFASCORE_MAP_SKEW_SEC", "720"))

    logger.info("Cargando agenda SofaScore %s …", day_s)
    try:
        stubs = sofascore_football_event_stubs_for_date(day_s)
    except Exception as e:
        logger.exception("Fallo HTTP SofaScore: %s", e)
        return 3
    logger.info("Stubs SofaScore: %s eventos", len(stubs))

    conn = _conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        f2_ids = resolve_f2_official_league_bt2_ids(cur)
        d0, d1 = _utc_day_bounds(op_day)
        cur.execute(
            """
            SELECT e.sportmonks_fixture_id, e.kickoff_utc, e.league_id,
                   th.name AS home_name, ta.name AS away_name,
                   l.sportmonks_id AS sm_league_id
            FROM bt2_events e
            JOIN bt2_leagues l ON l.id = e.league_id
            LEFT JOIN bt2_teams th ON th.id = e.home_team_id
            LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
            WHERE e.league_id = ANY(%s)
              AND e.kickoff_utc >= %s AND e.kickoff_utc < %s
              AND e.status IN ('scheduled', 'live')
            ORDER BY e.kickoff_utc
            """,
            (f2_ids, d0, d1),
        )
        rows = cur.fetchall()
        logger.info("Fixtures CDM F2 en día UTC: %s", len(rows))

        n_ok = n_review = 0
        for row in rows:
            sm_fid = int(row["sportmonks_fixture_id"])
            ko = row["kickoff_utc"]
            if isinstance(ko, datetime) and ko.tzinfo is None:
                ko = ko.replace(tzinfo=timezone.utc)
            sm_lid = row.get("sm_league_id")
            ut = sofascore_ut_id_for_sm_league(int(sm_lid) if sm_lid is not None else None)
            if ut is None:
                sid, review, note = None, True, "unknown_league_ut"
            else:
                sid, review, note = match_sofa_event_for_sm_fixture(
                    kickoff_utc=ko,
                    home_name=str(row.get("home_name") or ""),
                    away_name=str(row.get("away_name") or ""),
                    expected_unique_tournament_id=int(ut),
                    sofa_stubs=stubs,
                    max_skew_seconds=skew,
                )
            hnorm = normalize_benchmark_team_name(str(row.get("home_name") or ""))
            anorm = normalize_benchmark_team_name(str(row.get("away_name") or ""))
            if review:
                n_review += 1
            else:
                n_ok += 1
            if args.dry_run:
                logger.info(
                    "dry-run sm=%s sofa=%s needs_review=%s note=%r",
                    sm_fid,
                    sid,
                    review,
                    note,
                )
                continue
            cur.execute(
                """
                INSERT INTO bt2_nonprod_sm_sofascore_fixture_map_s64 (
                    operating_day_utc, sm_fixture_id, kickoff_utc, bt2_league_id,
                    home_name_norm, away_name_norm, sofascore_event_id, needs_review, map_note
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (sm_fixture_id, operating_day_utc) DO UPDATE SET
                    kickoff_utc = EXCLUDED.kickoff_utc,
                    bt2_league_id = EXCLUDED.bt2_league_id,
                    home_name_norm = EXCLUDED.home_name_norm,
                    away_name_norm = EXCLUDED.away_name_norm,
                    sofascore_event_id = EXCLUDED.sofascore_event_id,
                    needs_review = EXCLUDED.needs_review,
                    map_note = EXCLUDED.map_note,
                    updated_at = now()
                """,
                (
                    op_day,
                    sm_fid,
                    ko,
                    row.get("league_id"),
                    hnorm,
                    anorm,
                    sid,
                    review,
                    (note or "")[:200] or None,
                ),
            )
        if not args.dry_run:
            conn.commit()
        logger.info("Listo: mapped_ok=%s needs_review_or_empty=%s", n_ok, n_review)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

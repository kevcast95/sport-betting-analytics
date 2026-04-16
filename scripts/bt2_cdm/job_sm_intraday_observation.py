#!/usr/bin/env python3
"""
T-281 / US-BE-061 — Job de observación intradía SportMonks (D-06-068).

Universo: fixtures del día operativo (UTC) en las 5 ligas F2; cadencia §2;
persistencia en `bt2_nonprod_sm_fixture_observation_s64` (T-287).

Sin DSR productivo, sin SofaScore. Reutiliza `fetch_sportmonks_fixture_dict` (includes SM + 429).

Uso:
  python3 scripts/bt2_cdm/job_sm_intraday_observation.py
  python3 scripts/bt2_cdm/job_sm_intraday_observation.py --operating-day 2026-04-16
  python3 scripts/bt2_cdm/job_sm_intraday_observation.py --dry-run
  python3 scripts/bt2_cdm/job_sm_intraday_observation.py --ignore-cadence  # solo prueba / smoke

Env:
  BT2_DATABASE_URL
  SPORTMONKS_API_KEY
  BT2_SM_OBS_SLEEP_S — pausa entre fixtures (default 0.35)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv

load_dotenv(Path(_repo_root) / ".env")

import psycopg2
import psycopg2.extras

from apps.api.bt2_dev_sm_refresh import fetch_sportmonks_fixture_dict
from apps.api.bt2_f2_league_constants import resolve_f2_official_league_bt2_ids
from apps.api.bt2_sm_intraday_observation import (
    lineup_flags_from_sm_payload,
    market_flags_from_sm_payload,
    sm_observation_poll_interval_seconds,
    sm_observation_should_poll,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger("job_sm_intraday_observation")


def _conn():
    url = (os.getenv("BT2_DATABASE_URL") or "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        raise SystemExit("Falta BT2_DATABASE_URL")
    return psycopg2.connect(url)


def _utc_day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def main() -> int:
    p = argparse.ArgumentParser(description="Observación SM intradía F3 S6.4 (T-281)")
    p.add_argument(
        "--operating-day",
        type=str,
        default=None,
        help="YYYY-MM-DD en UTC para filtrar kickoff_utc (default: hoy UTC)",
    )
    p.add_argument("--dry-run", action="store_true", help="No escribe en Postgres")
    p.add_argument(
        "--ignore-cadence",
        action="store_true",
        help="Ignora D-06-068 §2 (una pasada por fixture del día; solo smoke)",
    )
    args = p.parse_args()

    if args.operating_day:
        y, m, d2 = (int(x) for x in args.operating_day.split("-"))
        op_day = date(y, m, d2)
    else:
        op_day = datetime.now(timezone.utc).date()

    day_start, day_end = _utc_day_bounds(op_day)
    now = datetime.now(timezone.utc)
    api_key = (os.getenv("SPORTMONKS_API_KEY") or "").strip()
    if not api_key:
        logger.error("Falta SPORTMONKS_API_KEY")
        return 2

    sleep_s = float(os.getenv("BT2_SM_OBS_SLEEP_S", "0.35"))

    conn = _conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        f2_ids = resolve_f2_official_league_bt2_ids(cur)
        if len(f2_ids) < 5:
            logger.warning("Solo %s ligas F2 resueltas en CDM (esperado 5): %s", len(f2_ids), f2_ids)

        cur.execute(
            """
            SELECT e.sportmonks_fixture_id AS sm_id, e.kickoff_utc, e.status
            FROM bt2_events e
            WHERE e.league_id = ANY(%s)
              AND e.kickoff_utc >= %s
              AND e.kickoff_utc < %s
              AND e.status IN ('scheduled', 'live')
            ORDER BY e.kickoff_utc
            """,
            (f2_ids, day_start, day_end),
        )
        rows = cur.fetchall()
        logger.info(
            "Día UTC %s — %s fixtures F2 (scheduled|live)",
            op_day.isoformat(),
            len(rows),
        )

        polled = 0
        skipped = 0
        errors = 0

        for i, row in enumerate(rows):
            sm_id = int(row["sm_id"])
            kick = row["kickoff_utc"]
            if kick is None:
                skipped += 1
                continue
            if isinstance(kick, datetime) and kick.tzinfo is None:
                kick = kick.replace(tzinfo=timezone.utc)

            cur.execute(
                """
                SELECT max(observed_at) AS mx
                FROM bt2_nonprod_sm_fixture_observation_s64
                WHERE sm_fixture_id = %s
                """,
                (sm_id,),
            )
            last_row = cur.fetchone()
            last_obs = last_row["mx"] if last_row else None

            if sm_observation_poll_interval_seconds(now, kick) is None:
                skipped += 1
                continue
            if not args.ignore_cadence and not sm_observation_should_poll(now, kick, last_obs):
                skipped += 1
                continue

            if i > 0 and sleep_s > 0:
                time.sleep(sleep_s)

            payload = fetch_sportmonks_fixture_dict(sm_id, api_key)
            if not isinstance(payload, dict):
                logger.warning("SM sin payload sm_fixture_id=%s", sm_id)
                errors += 1
                continue

            hu, au, lav = lineup_flags_from_sm_payload(payload)
            ft, ou, bt = market_flags_from_sm_payload(payload)

            if args.dry_run:
                logger.info(
                    "dry-run sm=%s lineup=%s ft=%s ou=%s btts=%s",
                    sm_id,
                    lav,
                    ft,
                    ou,
                    bt,
                )
                polled += 1
                continue

            cur.execute(
                """
                INSERT INTO bt2_nonprod_sm_fixture_observation_s64 (
                    sm_fixture_id, observed_at,
                    lineup_home_usable, lineup_away_usable, lineup_available,
                    ft_1x2_available, ou_goals_2_5_available, btts_available
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (sm_id, now, hu, au, lav, ft, ou, bt),
            )
            polled += 1

        if not args.dry_run:
            conn.commit()
        logger.info("Listo: polled=%s skipped=%s errors=%s", polled, skipped, errors)
        return 0 if errors == 0 else 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

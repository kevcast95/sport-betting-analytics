#!/usr/bin/env python3
"""
T-284 / US-BE-062 — Observación intradía SofaScore (D-06-068 §2) → `bt2_nonprod_sofascore_fixture_observation_s64`.

No re-poll SM. Solo fixtures con mapeo resuelto (`sofascore_event_id` no nulo y `needs_review` false).

Uso:
  python3 scripts/bt2_cdm/job_sofascore_intraday_observation.py
  python3 scripts/bt2_cdm/job_sofascore_intraday_observation.py --ignore-cadence --dry-run

Env: BT2_DATABASE_URL, BT2_SOFA_OBS_SLEEP_S (default 0.45).
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

from apps.api.bt2_f2_league_constants import resolve_f2_official_league_bt2_ids
from apps.api.bt2_sm_intraday_observation import sm_observation_poll_interval_seconds, sm_observation_should_poll
from apps.api.bt2_sofascore_observation_parse import sofa_flags_from_fetched_payloads
from core.sofascore_http import sofascore_get_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
logger = logging.getLogger("job_sofascore_intraday_observation")


def _conn():
    url = (os.getenv("BT2_DATABASE_URL") or "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        raise SystemExit("Falta BT2_DATABASE_URL")
    return psycopg2.connect(url)


def _utc_day_bounds(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _fetch_json(path_suffix: str) -> dict:
    url = f"https://www.sofascore.com/api/v1{path_suffix}"
    raw = sofascore_get_json(url)
    return raw if isinstance(raw, dict) else {}


def main() -> int:
    p = argparse.ArgumentParser(description="Observación SofaScore benchmark S6.4")
    p.add_argument("--operating-day", type=str, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--ignore-cadence", action="store_true")
    args = p.parse_args()

    if args.operating_day:
        y, m, d = (int(x) for x in args.operating_day.split("-"))
        op_day = date(y, m, d)
    else:
        op_day = datetime.now(timezone.utc).date()

    d0, d1 = _utc_day_bounds(op_day)
    now = datetime.now(timezone.utc)
    sleep_s = float(os.getenv("BT2_SOFA_OBS_SLEEP_S", "0.45"))

    conn = _conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        f2_ids = resolve_f2_official_league_bt2_ids(cur)
        cur.execute(
            """
            SELECT e.sportmonks_fixture_id AS sm_id, e.kickoff_utc,
                   m.sofascore_event_id AS ss_id
            FROM bt2_events e
            JOIN bt2_nonprod_sm_sofascore_fixture_map_s64 m
              ON m.sm_fixture_id = e.sportmonks_fixture_id
             AND m.operating_day_utc = %s
            WHERE e.league_id = ANY(%s)
              AND e.kickoff_utc >= %s AND e.kickoff_utc < %s
              AND e.status IN ('scheduled', 'live')
              AND m.needs_review = false
              AND m.sofascore_event_id IS NOT NULL
            ORDER BY e.kickoff_utc
            """,
            (op_day, f2_ids, d0, d1),
        )
        rows = cur.fetchall()
        logger.info("Fixtures con mapeo SofaScore utilizable: %s", len(rows))

        polled = skipped = errors = 0
        for i, row in enumerate(rows):
            sm_id = int(row["sm_id"])
            ss_id = int(row["ss_id"])
            kick = row["kickoff_utc"]
            if isinstance(kick, datetime) and kick.tzinfo is None:
                kick = kick.replace(tzinfo=timezone.utc)

            if sm_observation_poll_interval_seconds(now, kick) is None:
                skipped += 1
                continue
            cur.execute(
                """
                SELECT max(observed_at) AS mx
                FROM bt2_nonprod_sofascore_fixture_observation_s64
                WHERE sm_fixture_id = %s
                """,
                (sm_id,),
            )
            lr = cur.fetchone()
            last_obs = lr["mx"] if lr else None
            if not args.ignore_cadence and not sm_observation_should_poll(now, kick, last_obs):
                skipped += 1
                continue

            if i > 0 and sleep_s > 0:
                time.sleep(sleep_s)

            try:
                lu = _fetch_json(f"/event/{ss_id}/lineups")
                oa = _fetch_json(f"/event/{ss_id}/odds/1/all")
                of = _fetch_json(f"/event/{ss_id}/odds/1/featured")
            except Exception as e:
                logger.warning("SofaScore sm=%s ss=%s error %s", sm_id, ss_id, e)
                errors += 1
                continue

            hu, au, lav, ft, ou, bt = sofa_flags_from_fetched_payloads(lu, oa, of)
            if args.dry_run:
                logger.info("dry-run sm=%s ss=%s lineup=%s ft=%s ou=%s btts=%s", sm_id, ss_id, lav, ft, ou, bt)
                polled += 1
                continue

            cur.execute(
                """
                INSERT INTO bt2_nonprod_sofascore_fixture_observation_s64 (
                    sm_fixture_id, sofascore_event_id, observed_at,
                    lineup_home_usable, lineup_away_usable, lineup_available,
                    ft_1x2_available, ou_goals_2_5_available, btts_available
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (sm_id, ss_id, now, hu, au, lav, ft, ou, bt),
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

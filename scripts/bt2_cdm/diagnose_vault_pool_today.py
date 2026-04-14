#!/usr/bin/env python3
"""
Diagnóstico: ¿por qué la bóveda muestra vacío operativo?
Misma ventana y pool que el snapshot (build_value_pool_for_snapshot).

Uso (desde raíz del repo):
  PYTHONPATH=apps/api:. python3 scripts/bt2_cdm/diagnose_vault_pool_today.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_repo = Path(__file__).resolve().parents[2]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from zoneinfo import ZoneInfo

from apps.api.bt2_settings import bt2_settings
from apps.api.bt2_value_pool import (
    build_value_pool_for_snapshot,
    count_future_events_window,
    parse_priority_league_ids,
    _fetch_odds_grouped,
    _sql_prefilter_event_rows,
)
from apps.api.bt2_dsr_odds_aggregation import aggregate_odds_for_event, event_passes_value_pool
import psycopg2


def main() -> int:
    url = (bt2_settings.bt2_database_url or "").replace(
        "postgresql+asyncpg://", "postgresql://", 1
    )
    conn = psycopg2.connect(url)
    cur = conn.cursor()

    cur.execute("SELECT timezone::text FROM bt2_user_settings LIMIT 1")
    r = cur.fetchone()
    tz_name = (r[0] if r else None) or "America/Bogota"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
        tz_name = "UTC"

    local_today = datetime.now(tz=tz).date()
    day_start_utc = datetime.combine(local_today, datetime.min.time(), tzinfo=tz).astimezone(
        timezone.utc
    )
    day_end_utc = day_start_utc + timedelta(hours=24)
    league_filter = parse_priority_league_ids(bt2_settings.bt2_priority_league_ids or "")

    print(f"TZ: {tz_name} | día local: {local_today}")
    print(f"Ventana UTC: {day_start_utc} .. {day_end_utc}")
    print(f"BT2_PRIORITY_LEAGUE_IDS: {repr(bt2_settings.bt2_priority_league_ids or '')}")
    print(f"BT2_DSR_ENABLED: {bt2_settings.bt2_dsr_enabled}")

    fut = count_future_events_window(cur, day_start_utc, day_end_utc)
    pool, pre_n = build_value_pool_for_snapshot(
        cur, day_start_utc, day_end_utc, league_filter=league_filter
    )
    print(f"\nEventos scheduled en ventana: {fut}")
    print(f"Prefilter candidatos: {pre_n} | Pool elegible: {len(pool)}")

    if pre_n > 0 and len(pool) == 0:
        pre = _sql_prefilter_event_rows(cur, day_start_utc, day_end_utc, league_filter)
        eids = [int(r[0]) for r in pre[:20]]
        odds_by = _fetch_odds_grouped(cur, eids)
        print("\nMuestra (¿pasan value pool?):")
        for row in pre[:20]:
            eid = int(row[0])
            rows = odds_by.get(eid, [])
            agg = aggregate_odds_for_event(rows, min_decimal=1.30)
            ok = event_passes_value_pool(agg, min_decimal=1.30)
            true_mc = [k for k, v in agg.market_coverage.items() if v]
            print(f"  event_id={eid} pasa={ok} mercados_ok={true_mc} odds_rows={len(rows)}")

    cur.execute(
        """SELECT MAX(kickoff_utc) FROM bt2_events WHERE status = 'scheduled'"""
    )
    mx = cur.fetchone()[0]
    print(f"\nMAX kickoff_utc (scheduled en CDM): {mx}")

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

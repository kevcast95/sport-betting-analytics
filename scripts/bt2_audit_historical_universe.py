#!/usr/bin/env python3
"""
Auditoría read-only: universo de bt2_daily_picks vs bt2_events vs bt2_odds_snapshot (corte ex-ante).

Uso: desde la raíz del repo, con .env (BT2_DATABASE_URL).
No modifica datos. Sirve para repetir Fase 2025 / ampliación de muestra.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import psycopg2.extras  # noqa: E402

from apps.api.bt2_settings import bt2_settings  # noqa: E402


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def main() -> None:
    conn = psycopg2.connect(_dsn())
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        out: dict = {}

        cur.execute(
            """
            SELECT
              COUNT(*)::bigint AS n_daily_picks,
              MIN(operating_day_key)::text AS dp_day_min,
              MAX(operating_day_key)::text AS dp_day_max
            FROM bt2_daily_picks
            """
        )
        out["bt2_daily_picks"] = dict(cur.fetchone() or {})

        cur.execute(
            """
            SELECT
              COUNT(DISTINCT dp.id)::bigint AS n_usable,
              MIN(dp.operating_day_key)::text AS day_min,
              MAX(dp.operating_day_key)::text AS day_max
            FROM bt2_daily_picks dp
            INNER JOIN bt2_pick_official_evaluation e ON e.daily_pick_id = dp.id
            WHERE e.evaluation_status IN ('evaluated_hit', 'evaluated_miss')
              AND dp.reference_decimal_odds IS NOT NULL
              AND dp.reference_decimal_odds::float > 1
            """
        )
        out["usable_picks_frozen_definition"] = dict(cur.fetchone() or {})

        cur.execute(
            """
            SELECT
              date_trunc('year', operating_day_key::date)::date AS y,
              COUNT(*)::bigint AS n
            FROM bt2_daily_picks
            GROUP BY 1 ORDER BY 1
            """
        )
        out["daily_picks_by_year_operating_day"] = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT
              date_trunc('year', kickoff_utc AT TIME ZONE 'UTC')::date AS y,
              COUNT(*)::bigint AS n
            FROM bt2_events
            GROUP BY 1 ORDER BY 1
            """
        )
        out["bt2_events_by_kickoff_year"] = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT
              date_trunc('year', e.kickoff_utc AT TIME ZONE 'UTC')::date AS y,
              MIN(o.fetched_at) AS fmin,
              MAX(o.fetched_at) AS fmax,
              COUNT(DISTINCT o.event_id)::bigint AS events_with_odds,
              COUNT(*)::bigint AS n_odds_rows
            FROM bt2_odds_snapshot o
            INNER JOIN bt2_events e ON e.id = o.event_id
            GROUP BY 1
            ORDER BY 1
            """
        )
        out["bt2_odds_snapshot_by_kickoff_year"] = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """
            SELECT COUNT(*)::bigint AS n
            FROM bt2_odds_snapshot o
            INNER JOIN bt2_events e ON e.id = o.event_id
            WHERE e.kickoff_utc >= '2025-01-01' AND e.kickoff_utc < '2026-01-01'
              AND o.fetched_at < '2026-01-01'
            """
        )
        n_pass = cur.fetchone() or {}
        out["2025_kickoff_events_odds_rows_with_fetched_at_before_2026"] = int(
            n_pass.get("n") or 0
        )

        cur.execute(
            """
            SELECT pipeline_version, dsr_source, COUNT(*)::int AS n
            FROM bt2_daily_picks
            GROUP BY 1, 2 ORDER BY 3 DESC
            """
        )
        out["pipeline_x_dsr_on_all_daily_picks"] = [dict(r) for r in cur.fetchall()]

        print(json.dumps(out, indent=2, default=str))
    finally:
        conn.close()


if __name__ == "__main__":
    main()

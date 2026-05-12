#!/usr/bin/env python3
"""
MM-3.0A — Local DB Market/Data Universe Audit (read-only).

Artifact-only: SELECT sobre Postgres BT2. Sin APIs externas, sin escrituras.

Salidas (scripts/outputs/):
  mm3_0a_table_inventory.csv
  mm3_0a_historical_range_summary.json
  mm3_0a_historical_range_inventory.csv
  mm3_0a_event_result_coverage.csv
  mm3_0a_market_outcome_feasibility.csv
  mm3_0a_odds_market_coverage.csv
  mm3_0a_market_training_candidate_matrix.csv
  mm3_0a_league_coverage_120_sm.csv
  mm3_0a_recommended_markets.json

Genera además:
  docs/bettracker2/audits/MM3_0A_LOCAL_DB_MARKET_DATA_UNIVERSE_AUDIT.md

Uso (desde la raíz del repo):
  python3 scripts/mm3_0a_local_db_market_data_universe_audit.py
  python3 scripts/mm3_0a_local_db_market_data_universe_audit.py --db-url postgresql://...
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "scripts" / "outputs"
AUDIT_PATH = REPO / "docs" / "bettracker2" / "audits" / "MM3_0A_LOCAL_DB_MARKET_DATA_UNIVERSE_AUDIT.md"


def _load_bt2_database_url() -> str:
    url = (os.environ.get("BT2_DATABASE_URL") or "").strip().strip('"').strip("'")
    if url:
        return url
    env_path = REPO / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("BT2_DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not url:
        print("Falta BT2_DATABASE_URL en entorno o .env", file=sys.stderr)
        sys.exit(1)
    return url


def _sync_dsn(url: str) -> str:
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", url, flags=re.I)


def _ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h) for h in headers})


def _json_safe(obj: Any) -> Any:
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]
    return obj


def main() -> None:
    import psycopg2
    import psycopg2.extras

    p = argparse.ArgumentParser(description="MM-3.0A local DB audit")
    p.add_argument("--db-url", default="", help="Override BT2_DATABASE_URL")
    args = p.parse_args()
    dsn = _sync_dsn(args.db_url.strip() or _load_bt2_database_url())

    _ensure_out_dir()
    print("MM3_0A: conectando a Postgres…", flush=True)
    conn = psycopg2.connect(dsn, connect_timeout=30)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET statement_timeout TO 0")

    generated_at = datetime.now(timezone.utc).isoformat()
    print(f"MM3_0A: inicio audit (UTC {generated_at})", flush=True)
    cur.execute(
        """
        SELECT
          n.nspname AS schema_name,
          c.relname AS table_name,
          COALESCE(s.n_live_tup, 0)::bigint AS row_estimate,
          pg_total_relation_size(c.oid)::bigint AS total_bytes,
          (
            SELECT COUNT(*)::int
            FROM pg_attribute a
            WHERE a.attrelid = c.oid
              AND a.attnum > 0
              AND NOT a.attisdropped
          ) AS column_count
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_stat_all_tables s ON s.relid = c.oid
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
        ORDER BY pg_total_relation_size(c.oid) DESC, c.relname
        """
    )
    inv_rows = [dict(r) for r in cur.fetchall()]
    _write_csv(
        OUT_DIR / "mm3_0a_table_inventory.csv",
        [
            "schema_name",
            "table_name",
            "row_estimate",
            "total_bytes",
            "column_count",
        ],
        inv_rows,
    )

    # Exact counts (tablas núcleo — puede tardar)
    exact: dict[str, int] = {}
    for tbl in (
        "bt2_events",
        "raw_sportmonks_fixtures",
        "bt2_odds_snapshot",
        "bt2_leagues",
        "bt2_teams",
        "bt2_daily_picks",
    ):
        try:
            cur.execute(f"SELECT COUNT(*)::bigint AS c FROM {tbl}")
            exact[tbl] = int((cur.fetchone() or {}).get("c") or 0)
        except Exception:
            exact[tbl] = -1

    # ------------------------------------------------------------------ historical range
    cur.execute(
        """
        SELECT
          MIN(kickoff_utc) AS earliest_kickoff_bt2,
          MAX(kickoff_utc) AS latest_kickoff_bt2,
          COUNT(*)::bigint AS n_bt2_events,
          COUNT(*) FILTER (WHERE kickoff_utc IS NOT NULL)::bigint AS n_with_kickoff,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
          )::bigint AS n_with_final_score_goals
        FROM bt2_events
        """
    )
    bt2_span = dict(cur.fetchone() or {})

    cur.execute(
        """
        SELECT
          MIN(fixture_date) AS min_fixture_date,
          MAX(fixture_date) AS max_fixture_date,
          MIN((payload->>'starting_at')::timestamptz) AS min_starting_at_payload,
          MAX((payload->>'starting_at')::timestamptz) AS max_starting_at_payload,
          COUNT(*)::bigint AS n_raw_rows,
          COUNT(DISTINCT fixture_id)::bigint AS n_distinct_fixture_id,
          COUNT(DISTINCT league_id)::bigint AS n_distinct_league_id_column
        FROM raw_sportmonks_fixtures
        WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
        """
    )
    raw_span = dict(cur.fetchone() or {})

    cur.execute(
        """
        SELECT DISTINCT EXTRACT(YEAR FROM kickoff_utc AT TIME ZONE 'UTC')::int AS y
        FROM bt2_events
        WHERE kickoff_utc IS NOT NULL
        ORDER BY 1
        """
    )
    years_bt2 = [int(r["y"]) for r in cur.fetchall() if r.get("y") is not None]

    cur.execute(
        """
        SELECT season, COUNT(*)::bigint AS n
        FROM bt2_events
        WHERE season IS NOT NULL AND TRIM(season) <> ''
        GROUP BY season
        ORDER BY n DESC, season
        LIMIT 500
        """
    )
    seasons_top = [dict(r) for r in cur.fetchall()]

    hist_summary = {
        "generated_at_utc": generated_at,
        "bt2_events_kickoff": {
            "earliest": bt2_span.get("earliest_kickoff_bt2"),
            "latest": bt2_span.get("latest_kickoff_bt2"),
            "n_rows": bt2_span.get("n_bt2_events"),
            "n_with_kickoff": bt2_span.get("n_with_kickoff"),
            "n_with_final_score_goals": bt2_span.get("n_with_final_score_goals"),
        },
        "raw_sportmonks_fixtures": {
            "fixture_date_min": raw_span.get("min_fixture_date"),
            "fixture_date_max": raw_span.get("max_fixture_date"),
            "payload_starting_at_min": raw_span.get("min_starting_at_payload"),
            "payload_starting_at_max": raw_span.get("max_starting_at_payload"),
            "n_rows": raw_span.get("n_raw_rows"),
            "n_distinct_fixture_id": raw_span.get("n_distinct_fixture_id"),
        },
        "calendar_years_by_kickoff_utc": years_bt2,
        "seasons_non_null_top": seasons_top,
        "exact_row_counts_core_tables": exact,
    }

    print("MM3_0A: keyset prematch (una sola pasada odds×events)…", flush=True)
    cur.execute(
        """
        SELECT DISTINCT o.event_id
        FROM bt2_odds_snapshot o
        INNER JOIN bt2_events e ON e.id = o.event_id
        WHERE e.kickoff_utc IS NOT NULL
          AND o.fetched_at < e.kickoff_utc
        """
    )
    prematch_list = [int(r["event_id"]) for r in cur.fetchall()]
    if not prematch_list:
        prematch_list = [-1]
    hist_summary["prematch_event_keyset"] = {
        "n_distinct_events_with_any_prematch_odds_row": len(prematch_list)
        if prematch_list != [-1]
        else 0,
        "sentinel_minus_one_only": prematch_list == [-1],
    }

    cur.execute(
        """
        WITH prem AS (SELECT unnest(%s::int[]) AS event_id)
        SELECT
          'bt2_events'::text AS source,
          EXTRACT(YEAR FROM e.kickoff_utc AT TIME ZONE 'UTC')::int AS calendar_year,
          l.sportmonks_id AS sm_league_id,
          COALESCE(l.name, '') AS league_name,
          COALESCE(l.tier, '') AS tier,
          COUNT(*)::bigint AS n_events,
          MIN(e.kickoff_utc) AS earliest_kickoff,
          MAX(e.kickoff_utc) AS latest_kickoff,
          COUNT(*) FILTER (
            WHERE e.result_home IS NOT NULL AND e.result_away IS NOT NULL
          )::bigint AS n_with_final_score,
          COUNT(*) FILTER (WHERE p.event_id IS NOT NULL)::bigint AS n_with_any_prematch_odds
        FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN prem p ON p.event_id = e.id
        WHERE e.kickoff_utc IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY calendar_year, sm_league_id NULLS LAST
        """,
        (prematch_list,),
    )
    hist_inv_bt2 = [dict(r) for r in cur.fetchall()]

    cur.execute(
        """
        SELECT
          'raw_sportmonks_fixtures'::text AS source,
          EXTRACT(
            YEAR FROM COALESCE(
              (r.payload->>'starting_at')::timestamptz,
              r.fixture_date::timestamptz AT TIME ZONE 'UTC'
            )
          )::int AS calendar_year,
          r.league_id AS sm_league_id,
          COALESCE(l.name, '') AS league_name,
          COALESCE(l.tier, '') AS tier,
          COUNT(*)::bigint AS n_events,
          MIN(
            COALESCE(
              (r.payload->>'starting_at')::timestamptz,
              r.fixture_date::timestamptz AT TIME ZONE 'UTC'
            )
          ) AS earliest_kickoff,
          MAX(
            COALESCE(
              (r.payload->>'starting_at')::timestamptz,
              r.fixture_date::timestamptz AT TIME ZONE 'UTC'
            )
          ) AS latest_kickoff,
          NULL::bigint AS n_with_final_score,
          NULL::bigint AS n_with_any_prematch_odds
        FROM raw_sportmonks_fixtures r
        LEFT JOIN bt2_leagues l ON l.sportmonks_id = r.league_id
        WHERE r.league_id IS NOT NULL
          AND COALESCE(
            (r.payload->>'starting_at')::timestamptz,
            r.fixture_date::timestamptz AT TIME ZONE 'UTC'
          ) IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY calendar_year, sm_league_id NULLS LAST
        """
    )
    hist_inv_raw = [dict(r) for r in cur.fetchall()]
    hist_inv = hist_inv_bt2 + hist_inv_raw

    # ------------------------------------------------------------------ events x year/league/month
    cur.execute(
        """
        WITH prem AS (SELECT unnest(%s::int[]) AS event_id)
        SELECT
          EXTRACT(YEAR FROM e.kickoff_utc AT TIME ZONE 'UTC')::int AS calendar_year,
          EXTRACT(MONTH FROM e.kickoff_utc AT TIME ZONE 'UTC')::int AS calendar_month,
          l.sportmonks_id AS sm_league_id,
          COALESCE(l.name, '') AS league_name,
          COALESCE(l.tier, '') AS tier,
          COUNT(*)::bigint AS n_events,
          COUNT(*) FILTER (
            WHERE e.result_home IS NOT NULL AND e.result_away IS NOT NULL
          )::bigint AS n_with_final_score,
          COUNT(*) FILTER (WHERE p.event_id IS NOT NULL)::bigint AS n_with_any_prematch_odds
        FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN prem p ON p.event_id = e.id
        WHERE e.kickoff_utc IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5
        ORDER BY calendar_year, calendar_month, sm_league_id NULLS LAST
        """,
        (prematch_list,),
    )
    ev_cov = [dict(r) for r in cur.fetchall()]
    _write_csv(
        OUT_DIR / "mm3_0a_event_result_coverage.csv",
        [
            "calendar_year",
            "calendar_month",
            "sm_league_id",
            "league_name",
            "tier",
            "n_events",
            "n_with_final_score",
            "n_with_any_prematch_odds",
        ],
        ev_cov,
    )

    # raw vs bt2 by year/league (join sm league from raw.league_id = sportmonks league id)
    cur.execute(
        """
        SELECT
          EXTRACT(YEAR FROM COALESCE(r.fixture_date, (r.payload->>'starting_at')::date))::int AS calendar_year,
          r.league_id AS sm_league_id,
          COUNT(*)::bigint AS n_raw_fixtures
        FROM raw_sportmonks_fixtures r
        WHERE r.league_id IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    )
    raw_by_yl = {(int(r["calendar_year"]), int(r["sm_league_id"])): int(r["n_raw_fixtures"]) for r in cur.fetchall()}

    cur.execute(
        """
        SELECT
          EXTRACT(YEAR FROM e.kickoff_utc AT TIME ZONE 'UTC')::int AS calendar_year,
          l.sportmonks_id AS sm_league_id,
          COUNT(*)::bigint AS n_bt2_events
        FROM bt2_events e
        INNER JOIN bt2_leagues l ON l.id = e.league_id
        WHERE e.kickoff_utc IS NOT NULL AND l.sportmonks_id IS NOT NULL
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    )
    bt2_by_yl = {(int(r["calendar_year"]), int(r["sm_league_id"])): int(r["n_bt2_events"]) for r in cur.fetchall()}

    keys = sorted(set(raw_by_yl.keys()) | set(bt2_by_yl.keys()))
    hist_summary["comparison_raw_vs_bt2_fixtures_by_year_league"] = [
        {
            "calendar_year": y,
            "sm_league_id": lid,
            "n_raw_sportmonks_fixtures": raw_by_yl.get((y, lid), 0),
            "n_bt2_events": bt2_by_yl.get((y, lid), 0),
        }
        for y, lid in keys
    ]
    hist_summary["comparison_totals"] = {
        "pairs_year_league": len(keys),
        "sum_raw_fixtures_raw_query": sum(raw_by_yl.values()),
        "sum_bt2_events_joined_league": sum(bt2_by_yl.values()),
    }
    (OUT_DIR / "mm3_0a_historical_range_summary.json").write_text(
        json.dumps(_json_safe(hist_summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    _write_csv(
        OUT_DIR / "mm3_0a_historical_range_inventory.csv",
        [
            "source",
            "calendar_year",
            "sm_league_id",
            "league_name",
            "tier",
            "n_events",
            "earliest_kickoff",
            "latest_kickoff",
            "n_with_final_score",
            "n_with_any_prematch_odds",
        ],
        hist_inv,
    )

    # ------------------------------------------------------------------ outcome feasibility
    cur.execute(
        """
        SELECT
          COUNT(*)::bigint AS n_total,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
          )::bigint AS n_final_score,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
              AND result_home >= 0 AND result_away >= 0
          )::bigint AS n_score_nonneg,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
              AND (result_home + result_away) > 0.5
          )::bigint AS n_total_goals_gt_0_5,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
              AND (result_home + result_away) > 1.5
          )::bigint AS n_total_goals_gt_1_5,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
              AND (result_home + result_away) > 2.5
          )::bigint AS n_total_goals_gt_2_5,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
              AND (result_home + result_away) > 3.5
          )::bigint AS n_total_goals_gt_3_5,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
              AND (result_home + result_away) > 4.5
          )::bigint AS n_total_goals_gt_4_5,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
              AND result_home > 0 AND result_away > 0
          )::bigint AS n_btts_yes_outcome,
          COUNT(*) FILTER (
            WHERE result_home IS NOT NULL AND result_away IS NOT NULL
              AND (result_home = 0 OR result_away = 0)
          )::bigint AS n_btts_no_outcome
        FROM bt2_events
        """
    )
    oc = dict(cur.fetchone() or {})

    cur.execute(
        """
        SELECT COUNT(*)::bigint AS n
        FROM raw_sportmonks_fixtures r
        WHERE jsonb_typeof(r.payload->'statistics') = 'array'
          AND jsonb_array_length(COALESCE(r.payload->'statistics', '[]'::jsonb)) > 0
        """
    )
    n_raw_with_statistics = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        """
        SELECT COUNT(*)::bigint AS n
        FROM raw_sportmonks_fixtures r
        WHERE r.payload::text ILIKE '%corner%'
        """
    )
    n_raw_payload_text_cornerish = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        """
        SELECT COUNT(*)::bigint AS n
        FROM raw_sportmonks_fixtures r
        WHERE r.payload::text ILIKE '%yellow%'
           OR r.payload::text ILIKE '%red card%'
           OR r.payload::text ILIKE '%booking%'
        """
    )
    n_raw_payload_text_cardish = int((cur.fetchone() or {}).get("n") or 0)

    feasibility_rows = [
        {
            "outcome_key": "FT_1X2",
            "definition": "result_home/away no nulos — clase 1/X/2 desde goles",
            "n_events_usable": oc.get("n_final_score"),
            "pct_of_all_bt2_events": round(
                (oc.get("n_final_score") or 0) / max((oc.get("n_total") or 1), 1) * 100, 4
            ),
            "notes": "Modelado de probabilidad sobre marcador final.",
        },
        {
            "outcome_key": "OU_GOALS_0_5",
            "definition": "total goles vs línea 0.5",
            "n_events_usable": oc.get("n_score_nonneg"),
            "pct_of_all_bt2_events": round(
                (oc.get("n_score_nonneg") or 0) / max((oc.get("n_total") or 1), 1) * 100, 4
            ),
            "notes": "Binario sobre suma de goles.",
        },
        {
            "outcome_key": "OU_GOALS_1_5",
            "definition": "total goles vs línea 1.5",
            "n_events_usable": oc.get("n_score_nonneg"),
            "pct_of_all_bt2_events": round(
                (oc.get("n_score_nonneg") or 0) / max((oc.get("n_total") or 1), 1) * 100, 4
            ),
            "notes": "",
        },
        {
            "outcome_key": "OU_GOALS_2_5",
            "definition": "total goles vs línea 2.5",
            "n_events_usable": oc.get("n_score_nonneg"),
            "pct_of_all_bt2_events": round(
                (oc.get("n_score_nonneg") or 0) / max((oc.get("n_total") or 1), 1) * 100, 4
            ),
            "notes": "Mercado histórico principal en CDM normalize (OU 2.5).",
        },
        {
            "outcome_key": "OU_GOALS_3_5",
            "definition": "total goles vs línea 3.5",
            "n_events_usable": oc.get("n_score_nonneg"),
            "pct_of_all_bt2_events": round(
                (oc.get("n_score_nonneg") or 0) / max((oc.get("n_total") or 1), 1) * 100, 4
            ),
            "notes": "",
        },
        {
            "outcome_key": "OU_GOALS_4_5",
            "definition": "total goles vs línea 4.5",
            "n_events_usable": oc.get("n_score_nonneg"),
            "pct_of_all_bt2_events": round(
                (oc.get("n_score_nonneg") or 0) / max((oc.get("n_total") or 1), 1) * 100, 4
            ),
            "notes": "",
        },
        {
            "outcome_key": "BTTS",
            "definition": "ambos marcan — derivado de goles >0 por equipo",
            "n_events_usable": oc.get("n_final_score"),
            "pct_of_all_bt2_events": round(
                (oc.get("n_final_score") or 0) / max((oc.get("n_total") or 1), 1) * 100, 4
            ),
            "notes": "Clases yes/no observables si marcador completo.",
        },
        {
            "outcome_key": "CORNERS_TOTAL_PROXY",
            "definition": "proxy: payload JSON contiene texto 'corner' (no parsing de tipo 34)",
            "n_events_usable": n_raw_payload_text_cornerish,
            "pct_of_all_bt2_events": None,
            "notes": "Auditoría burda de presencia en raw; entrenamiento fino requiere statistics tipadas.",
        },
        {
            "outcome_key": "CARDS_PROXY",
            "definition": "proxy: payload contiene booking/yellow/red",
            "n_events_usable": n_raw_payload_text_cardish,
            "pct_of_all_bt2_events": None,
            "notes": "Proxy textual; odds de tarjetas ver tabla de mercados.",
        },
        {
            "outcome_key": "RAW_STATISTICS_ARRAY",
            "definition": "payload.statistics es array no vacío",
            "n_events_usable": n_raw_with_statistics,
            "pct_of_all_bt2_events": None,
            "notes": "Base para corners/corners markets si type_id presente.",
        },
    ]
    _write_csv(
        OUT_DIR / "mm3_0a_market_outcome_feasibility.csv",
        [
            "outcome_key",
            "definition",
            "n_events_usable",
            "pct_of_all_bt2_events",
            "notes",
        ],
        feasibility_rows,
    )

    # ------------------------------------------------------------------ odds market coverage
    print("MM3_0A: odds por año/liga/mercado (consulta pesada)…", flush=True)
    cur.execute("SET statement_timeout = 180000")
    try:
        cur.execute(
            """
            SELECT
              EXTRACT(YEAR FROM e.kickoff_utc AT TIME ZONE 'UTC')::int AS calendar_year,
              l.sportmonks_id AS sm_league_id,
              COALESCE(l.name, '') AS league_name,
              o.market,
              COUNT(*)::bigint AS n_odds_rows,
              COUNT(DISTINCT o.event_id)::bigint AS n_distinct_events_with_row,
              COUNT(DISTINCT o.bookmaker)::bigint AS n_bookmakers,
              MIN(o.fetched_at) AS min_fetched_at,
              MAX(o.fetched_at) AS max_fetched_at,
              COUNT(*) FILTER (WHERE o.fetched_at < e.kickoff_utc)::bigint AS n_rows_prematch_vs_kickoff,
              COUNT(DISTINCT o.event_id) FILTER (
                WHERE o.fetched_at < e.kickoff_utc
              )::bigint AS n_events_any_prematch_row_for_this_market
            FROM bt2_odds_snapshot o
            INNER JOIN bt2_events e ON e.id = o.event_id
            LEFT JOIN bt2_leagues l ON l.id = e.league_id
            WHERE e.kickoff_utc IS NOT NULL
            GROUP BY 1, 2, 3, 4
            ORDER BY calendar_year, sm_league_id NULLS LAST, n_odds_rows DESC
            """
        )
        odds_cov = [dict(r) for r in cur.fetchall()]
    except Exception as ex:
        odds_cov = [
            {
                "calendar_year": "",
                "sm_league_id": "",
                "league_name": "",
                "market": f"__QUERY_FAILED__: {ex}",
                "n_odds_rows": 0,
                "n_distinct_events_with_row": 0,
                "n_bookmakers": 0,
                "min_fetched_at": "",
                "max_fetched_at": "",
                "n_rows_prematch_vs_kickoff": 0,
                "n_events_any_prematch_row_for_this_market": 0,
            }
        ]
    finally:
        cur.execute("SET statement_timeout = 0")

    _write_csv(
        OUT_DIR / "mm3_0a_odds_market_coverage.csv",
        [
            "calendar_year",
            "sm_league_id",
            "league_name",
            "market",
            "n_odds_rows",
            "n_distinct_events_with_row",
            "n_bookmakers",
            "min_fetched_at",
            "max_fetched_at",
            "n_rows_prematch_vs_kickoff",
            "n_events_any_prematch_row_for_this_market",
        ],
        odds_cov,
    )

    # Distinct markets global (for appendix)
    cur.execute(
        """
        SELECT market, COUNT(*)::bigint AS n
        FROM bt2_odds_snapshot
        GROUP BY market
        ORDER BY n DESC
        LIMIT 200
        """
    )
    distinct_markets = [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------ training matrix (prob vs ROI)
    print("MM3_0A: matriz entrenamiento / ROI…", flush=True)
    cur.execute("SET statement_timeout = 180000")
    try:
        cur.execute(
        """
        WITH ev AS (
          SELECT
            id AS event_id,
            kickoff_utc,
            (result_home IS NOT NULL AND result_away IS NOT NULL) AS has_final_score
          FROM bt2_events
          WHERE kickoff_utc IS NOT NULL
        ),
        joined AS (
          SELECT
            ev.event_id,
            ev.kickoff_utc,
            ev.has_final_score,
            o.fetched_at,
            UPPER(TRIM(COALESCE(o.market, ''))) AS mu,
            UPPER(TRIM(COALESCE(o.selection, ''))) AS su,
            UPPER(TRIM(COALESCE(o.market, ''))) || ' ' || UPPER(TRIM(COALESCE(o.selection, ''))) AS ms
          FROM ev
          INNER JOIN bt2_odds_snapshot o ON o.event_id = ev.event_id
        ),
        flags AS (
          SELECT
            event_id,
            MAX(CASE WHEN fetched_at < kickoff_utc THEN 1 ELSE 0 END) AS pre_any,
            MAX(CASE WHEN fetched_at < kickoff_utc AND (
              TRIM(mu) IN ('1X2', 'FT_1X2')
              OR (mu LIKE '%1X2%' AND mu NOT LIKE '%DOUBLE CHANCE%')
              OR mu LIKE '%MATCH WINNER%'
              OR mu LIKE '%FULL TIME RESULT%'
              OR mu LIKE '%FULLTIME RESULT%'
            ) THEN 1 ELSE 0 END) AS pre_ft,
            MAX(CASE WHEN fetched_at < kickoff_utc AND (
              ms LIKE '%0.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR (mu LIKE '%GOALS OVER%' AND ms LIKE '%0.5%')
            ) THEN 1 ELSE 0 END) AS pre_ou05,
            MAX(CASE WHEN fetched_at < kickoff_utc AND (
              ms LIKE '%1.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR (mu LIKE '%GOALS OVER%' AND ms LIKE '%1.5%')
            ) THEN 1 ELSE 0 END) AS pre_ou15,
            MAX(CASE WHEN fetched_at < kickoff_utc AND (
              ms LIKE '%2.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR mu LIKE '%GOALS OVER%'
              OR mu LIKE '%OVER/UNDER 2.5%'
            ) THEN 1 ELSE 0 END) AS pre_ou25,
            MAX(CASE WHEN fetched_at < kickoff_utc AND (
              ms LIKE '%3.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR (mu LIKE '%GOALS OVER%' AND ms LIKE '%3.5%')
            ) THEN 1 ELSE 0 END) AS pre_ou35,
            MAX(CASE WHEN fetched_at < kickoff_utc AND (
              ms LIKE '%4.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR (mu LIKE '%GOALS OVER%' AND ms LIKE '%4.5%')
            ) THEN 1 ELSE 0 END) AS pre_ou45,
            MAX(CASE WHEN fetched_at < kickoff_utc AND (
              mu LIKE '%BTTS%' OR mu LIKE '%BOTH TEAMS%' OR mu LIKE '%BOTH TEAM%'
              OR mu LIKE '%AMBOS%' OR ms LIKE '% BTTS %'
            ) THEN 1 ELSE 0 END) AS pre_btts,
            MAX(CASE WHEN fetched_at < kickoff_utc AND mu LIKE '%CORNER%' THEN 1 ELSE 0 END)
              AS pre_corners,
            MAX(CASE WHEN fetched_at < kickoff_utc AND (
              mu LIKE '%CARD%' OR mu LIKE '%BOOKING%' OR mu LIKE '%YELLOW%'
            ) THEN 1 ELSE 0 END) AS pre_cards,
            MAX(1) AS snap_any,
            MAX(CASE WHEN (
              TRIM(mu) IN ('1X2', 'FT_1X2')
              OR (mu LIKE '%1X2%' AND mu NOT LIKE '%DOUBLE CHANCE%')
              OR mu LIKE '%MATCH WINNER%'
              OR mu LIKE '%FULL TIME RESULT%'
              OR mu LIKE '%FULLTIME RESULT%'
            ) THEN 1 ELSE 0 END) AS snap_ft,
            MAX(CASE WHEN (
              ms LIKE '%0.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR (mu LIKE '%GOALS OVER%' AND ms LIKE '%0.5%')
            ) THEN 1 ELSE 0 END) AS snap_ou05,
            MAX(CASE WHEN (
              ms LIKE '%1.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR (mu LIKE '%GOALS OVER%' AND ms LIKE '%1.5%')
            ) THEN 1 ELSE 0 END) AS snap_ou15,
            MAX(CASE WHEN (
              ms LIKE '%2.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR mu LIKE '%GOALS OVER%'
              OR mu LIKE '%OVER/UNDER 2.5%'
            ) THEN 1 ELSE 0 END) AS snap_ou25,
            MAX(CASE WHEN (
              ms LIKE '%3.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR (mu LIKE '%GOALS OVER%' AND ms LIKE '%3.5%')
            ) THEN 1 ELSE 0 END) AS snap_ou35,
            MAX(CASE WHEN (
              ms LIKE '%4.5%' AND (mu LIKE '%GOAL%' OR mu LIKE '%OVER%' OR mu LIKE '%UNDER%' OR mu LIKE '%O/U%')
              OR (mu LIKE '%GOALS OVER%' AND ms LIKE '%4.5%')
            ) THEN 1 ELSE 0 END) AS snap_ou45,
            MAX(CASE WHEN (
              mu LIKE '%BTTS%' OR mu LIKE '%BOTH TEAMS%' OR mu LIKE '%BOTH TEAM%'
              OR mu LIKE '%AMBOS%'
            ) THEN 1 ELSE 0 END) AS snap_btts,
            MAX(CASE WHEN mu LIKE '%CORNER%' THEN 1 ELSE 0 END) AS snap_corners,
            MAX(CASE WHEN (
              mu LIKE '%CARD%' OR mu LIKE '%BOOKING%' OR mu LIKE '%YELLOW%'
            ) THEN 1 ELSE 0 END) AS snap_cards
          FROM joined
          GROUP BY event_id
        )
        SELECT
          COUNT(*)::bigint AS n_events_all,
          COUNT(*) FILTER (WHERE e.has_final_score)::bigint AS a_prob_ft_all_markets,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_any, 0) = 1
          )::bigint AS b_roi_any_market,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_ft, 0) = 1
          )::bigint AS b_roi_ft,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_ou05, 0) = 1
          )::bigint AS b_roi_ou05,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_ou15, 0) = 1
          )::bigint AS b_roi_ou15,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_ou25, 0) = 1
          )::bigint AS b_roi_ou25,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_ou35, 0) = 1
          )::bigint AS b_roi_ou35,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_ou45, 0) = 1
          )::bigint AS b_roi_ou45,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_btts, 0) = 1
          )::bigint AS b_roi_btts,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_corners, 0) = 1
          )::bigint AS b_roi_corners,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.pre_cards, 0) = 1
          )::bigint AS b_roi_cards,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_any, 0) = 1
          )::bigint AS snap_any_market,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_ft, 0) = 1
          )::bigint AS snap_ft,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_ou25, 0) = 1
          )::bigint AS snap_ou25,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_btts, 0) = 1
          )::bigint AS snap_btts,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_ou05, 0) = 1
          )::bigint AS snap_ou05,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_ou15, 0) = 1
          )::bigint AS snap_ou15,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_ou35, 0) = 1
          )::bigint AS snap_ou35,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_ou45, 0) = 1
          )::bigint AS snap_ou45,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_corners, 0) = 1
          )::bigint AS snap_corners,
          COUNT(*) FILTER (
            WHERE e.has_final_score AND COALESCE(f.snap_cards, 0) = 1
          )::bigint AS snap_cards
        FROM ev e
        LEFT JOIN flags f ON f.event_id = e.event_id
        """
        )
        mx = dict(cur.fetchone() or {})
    except Exception:
        mx = {
            "n_events_all": 0,
            "a_prob_ft_all_markets": 0,
            "b_roi_any_market": 0,
            "b_roi_ft": 0,
            "b_roi_ou05": 0,
            "b_roi_ou15": 0,
            "b_roi_ou25": 0,
            "b_roi_ou35": 0,
            "b_roi_ou45": 0,
            "b_roi_btts": 0,
            "b_roi_corners": 0,
            "b_roi_cards": 0,
            "snap_any_market": 0,
            "snap_ft": 0,
            "snap_ou25": 0,
            "snap_btts": 0,
            "snap_ou05": 0,
            "snap_ou15": 0,
            "snap_ou35": 0,
            "snap_ou45": 0,
            "snap_corners": 0,
            "snap_cards": 0,
        }
    finally:
        cur.execute("SET statement_timeout = 0")

    cur.execute(
        """
        SELECT COUNT(*) FILTER (
            WHERE e.result_home IS NOT NULL AND e.result_away IS NOT NULL
          )::bigint AS n_prob_base
        FROM bt2_events e
        WHERE e.kickoff_utc IS NOT NULL
        """
    )
    apple = dict(cur.fetchone() or {})
    n_prob_base = int(apple.get("n_prob_base") or 0)

    matrix_rows = [
        {
            "target_key": "FT_1X2",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_ft"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_ft"),
            "prematch_rule": "fetched_at < kickoff_utc AND mercado FT/1X2/Match Winner",
            "notes": "Columna snap: filas en snapshot sin filtro temporal (audita presencia de mercado).",
        },
        {
            "target_key": "OU_GOALS_0_5",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_ou05"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_ou05"),
            "prematch_rule": "market+selection contienen 0.5 y familia goles O/U",
            "notes": "",
        },
        {
            "target_key": "OU_GOALS_1_5",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_ou15"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_ou15"),
            "prematch_rule": "market+selection contienen 1.5 y familia goles O/U",
            "notes": "",
        },
        {
            "target_key": "OU_GOALS_2_5",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_ou25"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_ou25"),
            "prematch_rule": "market+selection contienen 2.5 y familia goles O/U",
            "notes": "CDM v1 suele persistir Goals Over/Under + Over/Under.",
        },
        {
            "target_key": "OU_GOALS_3_5",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_ou35"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_ou35"),
            "prematch_rule": "market+selection contienen 3.5 y familia goles O/U",
            "notes": "",
        },
        {
            "target_key": "OU_GOALS_4_5",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_ou45"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_ou45"),
            "prematch_rule": "market+selection contienen 4.5 y familia goles O/U",
            "notes": "",
        },
        {
            "target_key": "BTTS",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_btts"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_btts"),
            "prematch_rule": "BTTS / Both teams / AMBOS",
            "notes": "",
        },
        {
            "target_key": "CORNERS_ODDS",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_corners"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_corners"),
            "prematch_rule": "market ILIKE %CORNER%",
            "notes": "Outcome corners desde marcador no está en bt2_events — ROI aquí es sobre mercado cuotas.",
        },
        {
            "target_key": "CARDS_ODDS",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_cards"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_cards"),
            "prematch_rule": "card/booking/yellow",
            "notes": "",
        },
        {
            "target_key": "ANY_ODDS_PREMATCH",
            "probability_modeling_events_with_final_score": n_prob_base,
            "roi_backtest_events_final_score_plus_prematch_odds_for_target": mx.get("b_roi_any_market"),
            "odds_rows_exist_final_score_events_ignore_time": mx.get("snap_any_market"),
            "prematch_rule": "cualquier fila con fetched_at < kickoff",
            "notes": "snap_any = cualquier fila odds (sin filtro temporal).",
        },
    ]
    _write_csv(
        OUT_DIR / "mm3_0a_market_training_candidate_matrix.csv",
        [
            "target_key",
            "probability_modeling_events_with_final_score",
            "roi_backtest_events_final_score_plus_prematch_odds_for_target",
            "odds_rows_exist_final_score_events_ignore_time",
            "prematch_rule",
            "notes",
        ],
        matrix_rows,
    )

    # ------------------------------------------------------------------ league panel (top 120 from catalog by volume)
    cur.execute("SELECT COUNT(*)::int AS n FROM bt2_leagues")
    n_leagues_catalog = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        """
        WITH prem AS (SELECT unnest(%s::int[]) AS event_id)
        SELECT
          l.id AS bt2_league_id,
          l.sportmonks_id AS sm_league_id,
          l.name AS league_name,
          l.tier,
          l.is_active,
          COUNT(e.id)::bigint AS n_events_total,
          COUNT(e.id) FILTER (
            WHERE e.result_home IS NOT NULL AND e.result_away IS NOT NULL
          )::bigint AS n_with_final_score,
          COUNT(e.id) FILTER (WHERE p.event_id IS NOT NULL)::bigint AS n_with_any_prematch_odds,
          MIN(e.kickoff_utc) AS first_kickoff,
          MAX(e.kickoff_utc) AS last_kickoff
        FROM bt2_leagues l
        LEFT JOIN bt2_events e ON e.league_id = l.id
        LEFT JOIN prem p ON p.event_id = e.id
        GROUP BY l.id, l.sportmonks_id, l.name, l.tier, l.is_active
        ORDER BY n_events_total DESC NULLS LAST, l.sportmonks_id
        LIMIT 120
        """,
        (prematch_list,),
    )
    league120 = [dict(r) for r in cur.fetchall()]
    _write_csv(
        OUT_DIR / "mm3_0a_league_coverage_120_sm.csv",
        [
            "bt2_league_id",
            "sm_league_id",
            "league_name",
            "tier",
            "is_active",
            "n_events_total",
            "n_with_final_score",
            "n_with_any_prematch_odds",
            "first_kickoff",
            "last_kickoff",
        ],
        league120,
    )

    # ------------------------------------------------------------------ recommendations JSON
    n_prob = n_prob_base
    n_roi_ft = int(mx.get("b_roi_ft") or 0)
    n_roi_ou25 = int(mx.get("b_roi_ou25") or 0)
    n_roi_any = int(mx.get("b_roi_any_market") or 0)
    n_snap_ft = int(mx.get("snap_ft") or 0)
    n_snap_ou25 = int(mx.get("snap_ou25") or 0)
    n_snap_any = int(mx.get("snap_any_market") or 0)

    hist_summary["odds_temporal_vs_snapshot_presence"] = {
        "prematch_rule": "bt2_odds_snapshot.fetched_at < bt2_events.kickoff_utc",
        "note": "Si casi todos los fetched_at son posteriores al kickoff (ingesta batch), "
        "la columna ROI ex-ante será baja aunque existan filas de mercado.",
        "events_final_score_with_prematch_any_odds": n_roi_any,
        "events_final_score_with_prematch_ft_pattern": n_roi_ft,
        "events_final_score_with_prematch_ou25_pattern": n_roi_ou25,
        "events_final_score_with_odds_rows_ft_ignore_time": n_snap_ft,
        "events_final_score_with_odds_rows_ou25_ignore_time": n_snap_ou25,
        "events_final_score_with_any_odds_row_ignore_time": n_snap_any,
    }
    (OUT_DIR / "mm3_0a_historical_range_summary.json").write_text(
        json.dumps(_json_safe(hist_summary), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    reco = {
        "generated_at_utc": generated_at,
        "definitions": {
            "probability_modeling_base": "bt2_events con result_home/result_away no nulos",
            "roi_prematch_odds": "bt2_odds_snapshot.fetched_at < bt2_events.kickoff_utc",
            "league_panel": "Top 120 filas de bt2_leagues por COUNT(bt2_events) DESC",
            "n_leagues_in_catalog": n_leagues_catalog,
        },
        "coverage_snapshot_counts": {
            "n_events_probability_base": n_prob,
            "n_events_roi_ft_1x2": n_roi_ft,
            "n_events_roi_ou25_pattern": n_roi_ou25,
            "n_events_roi_any_prematch_market": n_roi_any,
            "n_events_snapshot_ft_ignore_time": n_snap_ft,
            "n_events_snapshot_ou25_ignore_time": n_snap_ou25,
            "n_events_snapshot_any_odds_ignore_time": n_snap_any,
        },
        "recommended_first_mm3_targets": [
            {
                "priority": 1,
                "market": "FT_1X2",
                "rationale": "Mayor soporte en bt2_odds_snapshot (mercados 1X2/Match Winner) y outcomes binarios/ternarios limpios desde marcador.",
            },
            {
                "priority": 2,
                "market": "OU_GOALS_2_5",
                "rationale": "Históricamente materializado en ingesta CDM; validar cobertura vs FT en años tempranos en mm3_0a_odds_market_coverage.csv.",
            },
        ],
        "non_claim": "Sin afirmación de edge; solo cobertura de datos locales.",
        "distinct_markets_top": distinct_markets[:40],
        "comparison_totals": hist_summary.get("comparison_totals"),
    }
    (OUT_DIR / "mm3_0a_recommended_markets.json").write_text(
        json.dumps(_json_safe(reco), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ------------------------------------------------------------------ Audit markdown
    audit_body = f"""# MM-3.0A — Auditoría del universo market/data (DB local BT2)

**Modo:** solo lectura (`SELECT`). Sin APIs externas, SportMonks, TOA, DSR ni escrituras.

**Generado (UTC):** `{generated_at}`

## Resumen ejecutivo

| Métrica | Valor |
|--------|-------|
| Eventos `bt2_events` | {bt2_span.get('n_bt2_events')} |
| Kickoff min / max | `{bt2_span.get('earliest_kickoff_bt2')}` / `{bt2_span.get('latest_kickoff_bt2')}` |
| Con marcador final (goles home/away) | {bt2_span.get('n_with_final_score_goals')} |
| Filas `raw_sportmonks_fixtures` (payload objeto) | {raw_span.get('n_raw_rows')} |
| Fixture date min/max (raw) | `{raw_span.get('min_fixture_date')}` / `{raw_span.get('max_fixture_date')}` |
| Cobertura probabilística base (marcador) | **{n_prob}** eventos |
| Cobertura ROI FT (prematch + marcador) | **{n_roi_ft}** eventos |
| Cobertura ROI OU2.5 (ex-ante, patrón texto) | **{n_roi_ou25}** eventos |
| Cobertura ROI cualquier mercado prematch | **{n_roi_any}** eventos |
| Filas FT en snapshot (ignora `fetched_at`; solo presencia) | **{n_snap_ft}** eventos con marcador |
| Filas OU 2.5 en snapshot (ignora tiempo) | **{n_snap_ou25}** eventos con marcador |
| Cualquier fila odds (ignora tiempo) | **{n_snap_any}** eventos con marcador |

**Interpretación:** si `n_snap_*` ≫ `n_roi_*`, las cuotas están materializadas pero **no** como capturas pre-partido en `fetched_at` (típico de backfill batch). Para ROI ex-ante estricto, MM-3.1 puede necesitar timestamps de libro en `raw_sportmonks_fixtures` (LBU) u otra fuente temporal — fuera del alcance de este script read-only.

Base operativa: **partidos con `result_home` y `result_away` no nulos** en `bt2_events` (ver `mm3_0a_market_outcome_feasibility.csv`). Derivados OU/BTTS son deterministas desde el marcador.

### B. ROI / backtest

Regla temporal auditada: **filas en `bt2_odds_snapshot` con `fetched_at < kickoff_utc`** (corte pre-partido simple). No se aplicó T-60 aquí; si MM-3 exige T-60, refinar en MM-3.1 con la misma DB.

Corners/tarjetas como **outcome de modelo**: no hay columnas dedicadas en `bt2_events`; proxies sobre `raw_sportmonks_fixtures.payload` en `mm3_0a_market_outcome_feasibility.csv`. Mercados de corners/tarjetas en cuotas: ver patrones en `mm3_0a_odds_market_coverage.csv`.

## Artefactos

| Archivo | Descripción |
|---------|-------------|
| `scripts/outputs/mm3_0a_table_inventory.csv` | Inventario tablas `public` + estimates |
| `scripts/outputs/mm3_0a_historical_range_summary.json` | earliest/latest kickoff, años, seasons |
| `scripts/outputs/mm3_0a_historical_range_inventory.csv` | Por año y `sm_league_id`: filas `bt2_events` + `raw_sportmonks_fixtures`; comparación raw vs bt2 en el JSON resumen |
| `scripts/outputs/mm3_0a_event_result_coverage.csv` | Por año/mes/liga |
| `scripts/outputs/mm3_0a_market_outcome_feasibility.csv` | Factibilidad de outcomes |
| `scripts/outputs/mm3_0a_odds_market_coverage.csv` | Odds por año/liga/mercado |
| `scripts/outputs/mm3_0a_market_training_candidate_matrix.csv` | Matriz prob vs ROI |
| `scripts/outputs/mm3_0a_league_coverage_120_sm.csv` | Top 120 ligas del catálogo por volumen |
| `scripts/outputs/mm3_0a_recommended_markets.json` | Recomendación conservadora |

## Conteos exactos (tablas núcleo)

```json
{json.dumps(exact, indent=2)}
```

## Respuesta a la pregunta MM-3.0A

Con **esta** instantánea de la DB local:

1. **Años:** ver lista `calendar_years_by_kickoff_utc` en `mm3_0a_historical_range_summary.json` y granularidad en los CSV por año/mes.
2. **Ligas:** `mm3_0a_league_coverage_120_sm.csv` prioriza las 120 ligas del catálogo con más eventos en `bt2_events` (si el catálogo tiene menos de 120 filas, habrá menos filas).
3. **Mercados para modelo de probabilidad:** cualquier outcome derivable del marcador (FT, OU líneas, BTTS) donde haya muestra en **A**; proxies corners/cards desde estadísticas raw si aplica.
4. **Mercados para ROI:** subconjunto de **A** donde existan filas prematch en `bt2_odds_snapshot` para el mercado objetivo (matriz en `mm3_0a_market_training_candidate_matrix.csv`).
5. **Primer target sugerido MM-3:** **`FT_1X2`** (mayor solidez outcome + presencia histórica de mercados 1X2 / Match Winner en snapshots); **`OU_GOALS_2_5`** como segundo eje por alineación con CDM histórico — validar año por año en cobertura de odds.

**Limitación:** esta auditoría no evalúa calidad de cuotas ni fugas temporales más allá del corte `fetched_at < kickoff_utc`.
"""
    AUDIT_PATH.write_text(audit_body, encoding="utf-8")

    cur.close()
    conn.close()

    print(f"MM-3.0A audit OK — outputs in {OUT_DIR}", flush=True)
    print(f"Audit doc: {AUDIT_PATH}", flush=True)


if __name__ == "__main__":
    main()

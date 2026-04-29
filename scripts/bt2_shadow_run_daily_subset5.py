#!/usr/bin/env python3
"""
Corrida diaria real del carril shadow (subset5, h2h, us, T-60).
No toca tablas productivas; persiste en bt2_shadow_*.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_settings import bt2_settings


def _import_shadow_backfill() -> Any:
    p = ROOT / "scripts" / "bt2_shadow_backfill_subset5.py"
    spec = importlib.util.spec_from_file_location("bt2_shadow_backfill_daily", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["bt2_shadow_backfill_daily"] = mod
    spec.loader.exec_module(mod)
    return mod


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _build_rows_for_day(cur: Any, day_key: str) -> list[dict[str, str]]:
    d0 = datetime.fromisoformat(day_key).replace(tzinfo=timezone.utc)
    d1 = d0 + timedelta(days=1)
    shadow_backfill = _import_shadow_backfill()
    rows = shadow_backfill._build_rows_for_window(
        cur,
        year=d0.year,
        month_from=d0.month,
        month_to=d0.month,
        per_league_cap=300,
    )
    out: list[dict[str, str]] = []
    for r in rows:
        ko = str(r.get("kickoff_utc") or "")
        if ko[:10] != day_key:
            continue
        out.append(r)
    return out


def _build_rows_for_day_from_sm(day_key: str) -> list[dict[str, str]]:
    shadow_backfill = _import_shadow_backfill()
    sm_api = (bt2_settings.sportmonks_api_key or "").strip()
    if not sm_api:
        return []
    year = int(day_key[:4])
    month = int(day_key[5:7])
    rows = shadow_backfill._sm_fetch_between_subset5(
        year=year,
        month_from=month,
        month_to=month,
        sm_api_key=sm_api,
        per_league_cap=300,
    )
    return [r for r in rows if str(r.get("kickoff_utc") or "")[:10] == day_key]


def main() -> None:
    ap = argparse.ArgumentParser(description="Corrida diaria shadow subset5")
    ap.add_argument("--day", default=datetime.now(timezone.utc).date().isoformat(), help="YYYY-MM-DD UTC")
    ap.add_argument("--run-key", default="", help="Opcional; default shadow-daily-YYYY-MM-DD")
    args = ap.parse_args()

    shadow_backfill = _import_shadow_backfill()
    run_key = (args.run_key or "").strip() or f"shadow-daily-{args.day}"
    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        rows = _build_rows_for_day(cur, args.day)
    finally:
        cur.close()
        conn.close()
    if not rows:
        rows = _build_rows_for_day_from_sm(args.day)

    paid = shadow_backfill._import_paid_lab()
    api_toa = (bt2_settings.theoddsapi_key or "").strip()
    if not api_toa:
        raise SystemExit("Falta THEODDSAPI_KEY / theoddsapi_key para corrida daily_shadow.")
    matching_rows, odds_rows, credits = (
        paid.run_toa_phase(rows, api_toa)
        if rows
        else ([], [], {"estimated_total_cost_from_headers_sum": 0.0, "calls": []})
    )
    vp_map = shadow_backfill._compute_value_pool_pass([r for r in rows if int(r.get("bt2_event_id") or 0) > 0]) if rows else {}
    for r in rows:
        vp_map.setdefault(str(r.get("sm_fixture_id") or ""), "")

    conn2 = psycopg2.connect(_dsn(), connect_timeout=12)
    cur2 = conn2.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        persist_counts = shadow_backfill._persist_run(
            cur2,
            run_key=run_key,
            rows=rows,
            matching_rows=matching_rows,
            odds_rows=odds_rows,
            credit_summary=credits,
            vp_map=vp_map,
        )
        conn2.commit()
    except Exception:
        conn2.rollback()
        raise
    finally:
        cur2.close()
        conn2.close()

    summary = shadow_backfill._summary_from_results(
        run_key=run_key,
        year=int(args.day[:4]),
        month_from=int(args.day[5:7]),
        month_to=int(args.day[5:7]),
        rows=rows,
        matching_rows=matching_rows,
        odds_rows=odds_rows,
        credits=credits,
        vp_map=vp_map,
        persist_counts=persist_counts,
    )
    print(json.dumps({"ok": True, "day": args.day, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


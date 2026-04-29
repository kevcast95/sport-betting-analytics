#!/usr/bin/env python3
"""
Consolidado pre-Fase 4: 2025 backfills + 2026 YTD mensual + daily_shadow (DB).
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_performance"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE_RUNS = [
    "shadow-subset5-backfill-2025-01-05",
    "shadow-subset5-recovery-2025-07-12",
    "shadow-subset5-backfill-2026-01",
    "shadow-subset5-backfill-2026-02",
    "shadow-subset5-backfill-2026-03",
    "shadow-subset5-backfill-2026-04",
]


def _dsn() -> str:
    from apps.api.bt2_settings import bt2_settings

    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def _empty_metrics() -> dict[str, Any]:
    return {
        "picks_total": 0,
        "scored": 0,
        "hit": 0,
        "miss": 0,
        "void": 0,
        "pending_result": 0,
        "no_evaluable": 0,
        "roi_flat_stake_units": 0.0,
    }


def _finalize(m: dict[str, Any]) -> dict[str, Any]:
    scored = int(m["scored"])
    hit = int(m["hit"])
    roi = float(m["roi_flat_stake_units"])
    out = dict(m)
    out["hit_rate_on_scored"] = round(hit / scored, 6) if scored else 0.0
    out["roi_flat_stake_units"] = round(roi, 4)
    out["roi_flat_stake_pct"] = round((roi / scored) * 100.0, 6) if scored else 0.0
    return out


def main() -> None:
    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT run_key
            FROM bt2_shadow_runs
            WHERE run_key LIKE 'shadow-daily-%'
            ORDER BY created_at ASC
            """
        )
        daily_runs = [str(r["run_key"]) for r in (cur.fetchall() or [])]
        runs = BASE_RUNS + daily_runs

        cur.execute(
            """
            SELECT
                r.run_key,
                COALESCE(l.sportmonks_id, -1) AS sm_league_id,
                COALESCE(l.name, 'Unknown') AS league_name,
                pe.eval_status,
                pe.roi_flat_stake_units
            FROM bt2_shadow_daily_picks dp
            INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
            LEFT JOIN bt2_leagues l ON l.id = dp.league_id
            LEFT JOIN bt2_shadow_pick_eval pe ON pe.shadow_daily_pick_id = dp.id
            WHERE r.run_key = ANY(%s)
            """,
            (runs,),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        conn.close()

    per_run: dict[str, dict[str, Any]] = {rk: _empty_metrics() for rk in runs}
    per_league: dict[tuple[int, str], dict[str, Any]] = defaultdict(_empty_metrics)
    total = _empty_metrics()

    for r in rows:
        rk = str(r.get("run_key") or "")
        lg_id = int(r.get("sm_league_id") or -1)
        lg_name = str(r.get("league_name") or "Unknown")
        st = str(r.get("eval_status") or "")
        roi = float(r.get("roi_flat_stake_units") or 0.0)

        buckets = [per_run[rk], per_league[(lg_id, lg_name)], total]
        for b in buckets:
            b["picks_total"] += 1
            if st in ("hit", "miss"):
                b["scored"] += 1
            if st in ("hit", "miss", "void", "pending_result", "no_evaluable"):
                b[st] += 1
            b["roi_flat_stake_units"] += roi

    per_run_final = [{"run_key": rk, **_finalize(per_run[rk])} for rk in runs]
    per_league_final = [
        {"sm_league_id": lg_id, "league_name": lg_name, **_finalize(m)}
        for (lg_id, lg_name), m in sorted(per_league.items(), key=lambda x: x[0][0])
    ]
    total_final = _finalize(total)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "constraints": {
            "subset": "subset5",
            "market": "h2h",
            "region": "us",
            "snapshot_policy": "T-60",
            "lane": "shadow",
        },
        "runs_included": runs,
        "runs_base_2025": BASE_RUNS[:2],
        "runs_backfill_2026_monthly": BASE_RUNS[2:6],
        "runs_daily_shadow": daily_runs,
        "total": total_final,
        "by_run": per_run_final,
        "by_league": per_league_final,
    }
    (OUT_DIR / "shadow_backtest_pre_fase4_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fn_run = [
        "run_key",
        "picks_total",
        "scored",
        "hit",
        "miss",
        "void",
        "pending_result",
        "no_evaluable",
        "hit_rate_on_scored",
        "roi_flat_stake_units",
        "roi_flat_stake_pct",
    ]
    with (OUT_DIR / "shadow_backtest_pre_fase4_by_run.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn_run)
        w.writeheader()
        for rr in per_run_final:
            w.writerow({k: rr.get(k) for k in fn_run})

    fn_lg = [
        "sm_league_id",
        "league_name",
        "picks_total",
        "scored",
        "hit",
        "miss",
        "void",
        "pending_result",
        "no_evaluable",
        "hit_rate_on_scored",
        "roi_flat_stake_units",
        "roi_flat_stake_pct",
    ]
    with (OUT_DIR / "shadow_backtest_pre_fase4_by_league.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn_lg)
        w.writeheader()
        for rl in per_league_final:
            w.writerow({k: rl.get(k) for k in fn_lg})

    readme_path = OUT_DIR / "README.md"
    prev = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    extra = """

## Pre-Fase 4 (consolidado ampliado)

- `shadow_backtest_pre_fase4_summary.json`
- `shadow_backtest_pre_fase4_by_run.csv`
- `shadow_backtest_pre_fase4_by_league.csv`

Incluye backfills 2025, mensuales 2026-01..04 y corridas `shadow-daily-*` presentes en DB.
"""
    readme_path.write_text(prev + extra, encoding="utf-8")

    print(
        json.dumps(
            {"ok": True, "total": total_final, "runs_included": runs},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

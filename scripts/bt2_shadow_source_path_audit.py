#!/usr/bin/env python3
"""
Auditoría baseline shadow por source path (comparabilidad pre-Fase 4).
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
OUT = ROOT / "scripts" / "outputs" / "bt2_shadow_performance"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Meses 2026 construidos explícitamente con SM `fixtures/between` (sin filas CDM ese mes).
SM_FALLBACK_RUN_KEYS = frozenset(
    {
        "shadow-subset5-backfill-2026-01",
        "shadow-subset5-backfill-2026-02",
        "shadow-subset5-backfill-2026-03",
    }
)

CONSOLIDADO_BASE_RUNS = [
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


def _classify(run_key: str) -> str:
    if run_key.startswith("shadow-daily-"):
        return "daily_shadow_sm_toa"
    if run_key in SM_FALLBACK_RUN_KEYS:
        return "sportmonks_between_subset5_fallback"
    return "cdm_shadow"


def _empty() -> dict[str, Any]:
    return {
        "picks_total": 0,
        "scored": 0,
        "hit": 0,
        "miss": 0,
        "roi_flat_stake_units": 0.0,
    }


def main() -> None:
    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT run_key FROM bt2_shadow_runs WHERE run_key LIKE 'shadow-daily-%' ORDER BY created_at
            """
        )
        daily = [str(x["run_key"]) for x in (cur.fetchall() or [])]
        run_keys = CONSOLIDADO_BASE_RUNS + daily
        cur.execute(
            """
            SELECT r.run_key, pe.eval_status, pe.roi_flat_stake_units
            FROM bt2_shadow_daily_picks dp
            INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
            LEFT JOIN bt2_shadow_pick_eval pe ON pe.shadow_daily_pick_id = dp.id
            WHERE r.run_key = ANY(%s)
            """,
            (run_keys,),
        )
        rows = cur.fetchall() or []
    finally:
        cur.close()
        conn.close()

    by_path: dict[str, dict[str, Any]] = defaultdict(_empty)
    total_picks = 0
    for r in rows:
        rk = str(r.get("run_key") or "")
        path = _classify(rk)
        st = str(r.get("eval_status") or "")
        roi = float(r.get("roi_flat_stake_units") or 0.0)
        b = by_path[path]
        b["picks_total"] += 1
        total_picks += 1
        if st == "hit":
            b["scored"] += 1
            b["hit"] += 1
        elif st == "miss":
            b["scored"] += 1
            b["miss"] += 1
        b["roi_flat_stake_units"] += roi

    rows_out = []
    for path, m in sorted(by_path.items()):
        scored = int(m["scored"])
        hit = int(m["hit"])
        roi = float(m["roi_flat_stake_units"])
        pct_of_picks = round(m["picks_total"] / total_picks, 6) if total_picks else 0.0
        hit_rate = round(hit / scored, 6) if scored else 0.0
        roi_pct = round((roi / scored) * 100.0, 6) if scored else 0.0
        rows_out.append(
            {
                "source_path": path,
                "picks_total": m["picks_total"],
                "pct_of_all_shadow_picks": pct_of_picks,
                "scored": scored,
                "hit": hit,
                "miss": int(m["miss"]),
                "hit_rate_on_scored": hit_rate,
                "roi_flat_stake_units": round(roi, 4),
                "roi_flat_stake_pct": roi_pct,
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "runs_filtered": run_keys,
        "definitions": {
            "cdm_shadow": "Runs mensuales/2025 construidos desde bt2_events (CDM) en _build_rows_for_window; incluye shadow-subset5-backfill-2026-04.",
            "sportmonks_between_subset5_fallback": "Meses 2026-01/02/03 sin cohorte CDM ese mes; filas desde SportMonks fixtures/between (subset5).",
            "daily_shadow_sm_toa": "Corridas shadow-daily-* (SM + TOA histórico según runner diario).",
        },
        "total_shadow_picks_in_db": total_picks,
        "by_source_path": rows_out,
    }
    (OUT / "shadow_source_path_audit.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (OUT / "shadow_source_path_audit.csv").open("w", encoding="utf-8", newline="") as f:
        fn = list(rows_out[0].keys()) if rows_out else ["source_path"]
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for row in rows_out:
            w.writerow(row)

    print(json.dumps({"ok": True, "out": str(OUT.relative_to(ROOT)), "rows": rows_out}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

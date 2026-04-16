#!/usr/bin/env python3
"""
T-285 / US-BE-062 — Informe benchmark SM vs SofaScore desde tablas T-287, T-288, T-283.

Escribe `out/bt2_benchmark_sm_sofa_s64_<operating_day>.json` y `.md` (crea `out/` si hace falta).

Env: BT2_DATABASE_URL
"""

from __future__ import annotations

import argparse
import json
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

SQL_SUMMARY = """
SELECT
  COUNT(*) FILTER (WHERE m.needs_review) AS map_needs_review,
  COUNT(*) FILTER (WHERE NOT m.needs_review AND m.sofascore_event_id IS NOT NULL) AS map_resolved,
  COUNT(*) AS map_rows
FROM bt2_nonprod_sm_sofascore_fixture_map_s64 m
WHERE m.operating_day_utc = %s;
"""

SQL_SM_FIRST = """
SELECT sm_fixture_id, min(observed_at) FILTER (WHERE lineup_available) AS first_lineup
FROM bt2_nonprod_sm_fixture_observation_s64
WHERE observed_at >= %s AND observed_at < %s
GROUP BY 1 ORDER BY 1 LIMIT 20;
"""

SQL_SOFA_FIRST = """
SELECT sm_fixture_id, min(observed_at) FILTER (WHERE lineup_available) AS first_lineup
FROM bt2_nonprod_sofascore_fixture_observation_s64
WHERE observed_at >= %s AND observed_at < %s
GROUP BY 1 ORDER BY 1 LIMIT 20;
"""

SQL_COMPARE = """
SELECT m.sm_fixture_id,
       min(s.observed_at) FILTER (WHERE s.lineup_available) AS sm_first,
       min(f.observed_at) FILTER (WHERE f.lineup_available) AS sofa_first
FROM bt2_nonprod_sm_sofascore_fixture_map_s64 m
LEFT JOIN bt2_nonprod_sm_fixture_observation_s64 s
  ON s.sm_fixture_id = m.sm_fixture_id
 AND s.observed_at >= %s AND s.observed_at < %s
LEFT JOIN bt2_nonprod_sofascore_fixture_observation_s64 f
  ON f.sm_fixture_id = m.sm_fixture_id
 AND f.observed_at >= %s AND f.observed_at < %s
WHERE m.operating_day_utc = %s
  AND m.sofascore_event_id IS NOT NULL
  AND NOT m.needs_review
GROUP BY 1
ORDER BY 1
LIMIT 50;
"""


def _conn():
    url = (os.getenv("BT2_DATABASE_URL") or "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        raise SystemExit("Falta BT2_DATABASE_URL")
    return psycopg2.connect(url)


def _day_bounds(d: date) -> tuple[datetime, datetime]:
    a = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return a, a + timedelta(days=1)


def main() -> int:
    p = argparse.ArgumentParser(description="Informe benchmark SM vs SofaScore S6.4")
    p.add_argument("--operating-day", type=str, required=True, help="YYYY-MM-DD UTC")
    args = p.parse_args()
    y, m, d = (int(x) for x in args.operating_day.split("-"))
    op = date(y, m, d)
    t0, t1 = _day_bounds(op)

    conn = _conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(SQL_SUMMARY, (op,))
        summary = dict(cur.fetchone() or {})
        cur.execute(SQL_SM_FIRST, (t0, t1))
        sm_first = [dict(r) for r in cur.fetchall()]
        cur.execute(SQL_SOFA_FIRST, (t0, t1))
        sofa_first = [dict(r) for r in cur.fetchall()]
        cur.execute(SQL_COMPARE, (t0, t1, t0, t1, op))
        compare = [dict(r) for r in cur.fetchall()]
        for r in sm_first + sofa_first + compare:
            for k, v in list(r.items()):
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        out_dir = Path(_repo_root) / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = f"bt2_benchmark_sm_sofa_s64_{op.isoformat()}"
        payload = {
            "operating_day_utc": op.isoformat(),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "sm_first_lineup_sample": sm_first,
            "sofa_first_lineup_sample": sofa_first,
            "compare_lineup_first_sample": compare,
        }
        json_path = out_dir / f"{stem}.json"
        md_path = out_dir / f"{stem}.md"
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = [
            f"# Benchmark SM vs SofaScore — {op.isoformat()} (UTC)",
            "",
            "## Resumen mapeo (T-283)",
            "",
            "```json",
            json.dumps(summary, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Muestra primera lineup disponible (SM)",
            "",
            f"Ver JSON `{json_path.name}` → `sm_first_lineup_sample`.",
            "",
            "## Muestra primera lineup disponible (SofaScore)",
            "",
            f"Ver JSON → `sofa_first_lineup_sample`.",
            "",
            "## Comparativo lineup (misma ventana día)",
            "",
            f"Ver JSON → `compare_lineup_first_sample`.",
            "",
            "SofaScore solo benchmark / discovery (**D-06-066**).",
            "",
        ]
        md_path.write_text("\n".join(lines), encoding="utf-8")
        print(json.dumps({"ok": True, "json": str(json_path), "md": str(md_path)}, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

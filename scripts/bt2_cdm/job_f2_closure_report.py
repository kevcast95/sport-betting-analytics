#!/usr/bin/env python3
"""
T-264 — Reporte de cierre F2: ventana 30d (configurable), 5 ligas, umbrales 60% / 40% por liga.

Salida: JSON a stdout y opcionalmente Markdown para pegar en `EJECUCION_CIERRE_F2_S6_3.md`.

  BT2_DATABASE_URL=... python3 scripts/bt2_cdm/job_f2_closure_report.py
  python3 scripts/bt2_cdm/job_f2_closure_report.py --days 30 --write-md docs/.../snippet.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv

load_dotenv(Path(_repo_root) / ".env")

import psycopg2.extras

from apps.api.bt2_f2_metrics import build_f2_pool_eligibility_metrics, f2_closure_report_markdown


def main() -> int:
    p = argparse.ArgumentParser(description="Reporte cierre F2 (T-264)")
    p.add_argument("--days", type=int, default=30, help="Ventana rolling si no hay --day")
    p.add_argument(
        "--day",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Un solo operating_day_key (opcional)",
    )
    p.add_argument(
        "--write-md",
        type=str,
        default=None,
        help="Ruta opcional para escribir Markdown",
    )
    args = p.parse_args()

    url = os.getenv("BT2_DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        print("[job_f2_closure_report] FATAL: BT2_DATABASE_URL", file=sys.stderr)
        return 1

    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        payload = build_f2_pool_eligibility_metrics(
            cur,
            operating_day_key=args.day,
            days=args.days,
        )
    finally:
        cur.close()
        conn.close()

    print(json.dumps(payload, indent=2, default=str))
    md = f2_closure_report_markdown(payload)
    if args.write_md:
        Path(args.write_md).write_text(md, encoding="utf-8")
        print("\n--- Markdown ---\n", file=sys.stderr)
        print(md, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

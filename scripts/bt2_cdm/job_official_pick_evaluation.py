#!/usr/bin/env python3
"""
T-231 / T-232 — Job batch: backfill `bt2_pick_official_evaluation` + evaluar `pending_result` vs CDM.

Uso típico (cron o manual):
  BT2_DATABASE_URL=postgresql://... python3 scripts/bt2_cdm/job_official_pick_evaluation.py

Opciones:
  --dry-run     Cuenta filas afectadas sin COMMIT (backfill “would insert”, evaluate counts).
  --limit-backfill N   Máximo de daily_picks a enrolar por corrida.
  --limit-evaluate N   Máximo de filas pending a examinar por corrida.
  --backfill-only / --evaluate-only  Fases aisladas.
  --metrics-only       Solo métricas T-233 (opc. --metrics-day YYYY-MM-DD).

Idempotencia: no inserta dos veces el mismo `daily_pick_id`; no reescribe filas ya fuera de
`pending_result`.

Exit: 0 OK, 1 error fatal.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv

load_dotenv(Path(_repo_root) / ".env")

import psycopg2.extras


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluación oficial de picks sugeridos vs bt2_events (S6.3)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-backfill", type=int, default=None)
    parser.add_argument("--limit-evaluate", type=int, default=None)
    parser.add_argument("--backfill-only", action="store_true")
    parser.add_argument("--evaluate-only", action="store_true")
    parser.add_argument(
        "--metrics-only",
        action="store_true",
        help="Solo imprime métricas T-233 (sin backfill ni evaluate)",
    )
    parser.add_argument(
        "--metrics-day",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Con --metrics-only: filtra por operating_day_key",
    )
    args = parser.parse_args()
    if args.backfill_only and args.evaluate_only:
        print(
            "[job_official_pick_evaluation] FATAL: elija solo una de --backfill-only / --evaluate-only",
            file=sys.stderr,
        )
        return 1
    if args.metrics_only and (args.backfill_only or args.evaluate_only):
        print(
            "[job_official_pick_evaluation] FATAL: --metrics-only no combina con --backfill-only / --evaluate-only",
            file=sys.stderr,
        )
        return 1

    url = os.getenv("BT2_DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        print("[job_official_pick_evaluation] FATAL: BT2_DATABASE_URL", file=sys.stderr)
        return 1

    from apps.api.bt2_official_evaluation_job import (  # noqa: E402
        fetch_official_evaluation_loop_metrics,
        job_summary_dict,
        run_official_evaluation_job,
    )

    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        if args.metrics_only:
            m = fetch_official_evaluation_loop_metrics(
                cur, operating_day_key=args.metrics_day
            )
            print(f"[job_official_pick_evaluation] metrics {m}")
            return 0
        stats = run_official_evaluation_job(
            cur,
            limit_backfill=args.limit_backfill,
            limit_evaluate=args.limit_evaluate,
            dry_run=args.dry_run,
            skip_backfill=args.evaluate_only,
            skip_evaluate=args.backfill_only,
        )
        summary = job_summary_dict(stats)
        summary["dry_run"] = args.dry_run
        print(f"[job_official_pick_evaluation] {summary}")
        m = fetch_official_evaluation_loop_metrics(cur)
        print(f"[job_official_pick_evaluation] metrics_global {m}")
        if not args.dry_run:
            conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"[job_official_pick_evaluation] FATAL: {exc}", file=sys.stderr)
        return 1
    finally:
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

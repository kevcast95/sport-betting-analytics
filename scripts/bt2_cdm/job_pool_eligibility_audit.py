#!/usr/bin/env python3
"""
T-235 / T-236 — Job batch: evalúa elegibilidad pool y persiste `bt2_pool_eligibility_audit`.

Persistencia **siempre** con umbral oficial de familias = 2 (`min_distinct_market_families=2`),
independiente de `BT2_POOL_ELIGIBILITY_MIN_FAMILIES` (ese env solo afecta pruebas/KPI relajado
en memoria, no la verdad append-only en BD).

Append-only: cada corrida inserta filas nuevas; métricas “último estado” vía DISTINCT ON en consultas admin.

Exit: 0 OK, 1 fatal.
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

import psycopg2


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoría elegibilidad pool BT2 (S6.3)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Máximo de eventos a procesar (orden id descendente si no hay --event-id)",
    )
    parser.add_argument(
        "--event-id",
        type=int,
        default=None,
        help="Solo este bt2_events.id",
    )
    parser.add_argument(
        "--operating-day-key",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help=(
            "Restringe a event_id distintos en bt2_daily_picks para ese día "
            "(orden por event_id; respeta --limit)."
        ),
    )
    args = parser.parse_args()

    url = os.getenv("BT2_DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        print("[job_pool_eligibility_audit] FATAL: BT2_DATABASE_URL", file=sys.stderr)
        return 1

    from apps.api.bt2_pool_eligibility_v1 import (  # noqa: E402
        POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63,
        evaluate_pool_eligibility_v1_from_db,
        insert_pool_eligibility_audit_row,
    )

    conn = psycopg2.connect(url)
    # Cursor estándar (tuplas): el builder DSR y elegibilidad v1 usan row[i], no RealDictRow.
    cur = conn.cursor()
    n_ok = n_skip = 0
    try:
        if args.event_id is not None:
            ids = [int(args.event_id)]
        elif args.operating_day_key:
            cur.execute(
                """
                SELECT DISTINCT event_id
                FROM bt2_daily_picks
                WHERE operating_day_key = %s
                ORDER BY event_id
                LIMIT %s
                """,
                (args.operating_day_key, max(1, args.limit)),
            )
            ids = [int(r[0]) for r in cur.fetchall()]
        else:
            cur.execute(
                """
                SELECT id FROM bt2_events
                ORDER BY id DESC
                LIMIT %s
                """,
                (max(1, args.limit),),
            )
            ids = [int(r[0]) for r in cur.fetchall()]

        for eid in ids:
            res = evaluate_pool_eligibility_v1_from_db(
                cur,
                eid,
                min_distinct_market_families=POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63,
            )
            if res is None:
                n_skip += 1
                continue
            n_ok += 1
            if args.dry_run:
                print(
                    f"dry-run event_id={eid} eligible={res.is_eligible} "
                    f"reason={res.primary_discard_reason}"
                )
            else:
                insert_pool_eligibility_audit_row(cur, event_id=eid, result=res)

        if not args.dry_run:
            conn.commit()
        print(
            f"[job_pool_eligibility_audit] processed={n_ok} missing_event={n_skip} "
            f"dry_run={args.dry_run}"
        )
    except Exception as exc:
        conn.rollback()
        print(f"[job_pool_eligibility_audit] FATAL: {exc}", file=sys.stderr)
        return 1
    finally:
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

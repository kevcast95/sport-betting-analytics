#!/usr/bin/env python3
"""
T-235 / T-236 — Job batch: evalúa elegibilidad pool v1 y persiste `bt2_pool_eligibility_audit`.

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

import psycopg2.extras


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
    args = parser.parse_args()

    url = os.getenv("BT2_DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        print("[job_pool_eligibility_audit] FATAL: BT2_DATABASE_URL", file=sys.stderr)
        return 1

    from apps.api.bt2_pool_eligibility_v1 import (  # noqa: E402
        evaluate_pool_eligibility_v1_from_db,
        insert_pool_eligibility_audit_row,
    )

    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    n_ok = n_skip = 0
    try:
        if args.event_id is not None:
            ids = [int(args.event_id)]
        else:
            cur.execute(
                """
                SELECT id FROM bt2_events
                ORDER BY id DESC
                LIMIT %s
                """,
                (max(1, args.limit),),
            )
            ids = [int(r["id"]) for r in cur.fetchall()]

        for eid in ids:
            res = evaluate_pool_eligibility_v1_from_db(cur, eid)
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

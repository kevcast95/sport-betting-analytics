#!/usr/bin/env python3
"""
T-211 / D-06-033 — Job programado: materializa snapshot de bóveda por usuario (idempotente).

No sustituye `session/open` ni POST refresh admin: solo asegura filas en `bt2_daily_picks`
cuando aún no existen para el `operating_day_key` actual de cada usuario (misma lógica que
`_generate_daily_picks_snapshot`).

Exit: 0 OK, 1 error fatal.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv

load_dotenv(Path(_repo_root) / ".env")

import psycopg2
import psycopg2.extras


def main() -> int:
    parser = argparse.ArgumentParser(description="Materializar snapshots vault BT2 (cron)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Lista usuarios y odk calculado sin escribir",
    )
    args = parser.parse_args()

    url = os.getenv("BT2_DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        print("[job_vault_snapshot] FATAL: BT2_DATABASE_URL", file=sys.stderr)
        return 1

    from zoneinfo import ZoneInfo

    from apps.api import bt2_router  # noqa: E402

    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT u.id::text AS uid, COALESCE(s.timezone, 'America/Bogota') AS tz
            FROM bt2_users u
            LEFT JOIN bt2_user_settings s ON s.user_id = u.id
            """
        )
        rows = list(cur.fetchall())
        total_ins = 0
        for r in rows:
            uid = str(r["uid"])
            tz_name = (r["tz"] or "America/Bogota").strip() or "America/Bogota"
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = ZoneInfo("America/Bogota")
                tz_name = "America/Bogota"
            odk = datetime.now(tz=tz).date().isoformat()
            if args.dry_run:
                print(f"dry-run user={uid} odk={odk} tz={tz_name}")
                continue
            ins = bt2_router._generate_daily_picks_snapshot(cur, uid, odk, tz_name)
            total_ins += int(ins or 0)
        if not args.dry_run:
            conn.commit()
        print(
            f"[job_vault_snapshot] usuarios={len(rows)} "
            f"filas_insertadas_esta_corrida={total_ins}"
            + (" (dry-run)" if args.dry_run else "")
        )
    except Exception as exc:
        conn.rollback()
        print(f"[job_vault_snapshot] FATAL: {exc}", file=sys.stderr)
        return 1
    finally:
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

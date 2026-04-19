#!/usr/bin/env python3
"""
Rellena `bt2_daily_picks.reference_decimal_odds` desde el consenso CDM actual
(`aggregated_odds_for_event_psycopg`), para picks históricos sin cuota persistida.

Uso:
  BT2_DATABASE_URL=postgresql://... python3 scripts/bt2_cdm/backfill_daily_pick_reference_odds.py --days 7
  python3 ... --operating-day-from 2026-04-11 --operating-day-to 2026-04-18

Idempotente: solo actualiza filas con reference_decimal_odds IS NULL y valor resuelto > 1.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv

load_dotenv(Path(_repo_root) / ".env")

import psycopg2.extras

from apps.api.bt2_dsr_ds_input_builder import aggregated_odds_for_event_psycopg
from apps.api.bt2_dsr_odds_aggregation import consensus_decimal_for_canonical_pick


def _add_days_iso(iso_day: str, delta: int) -> str:
    d = date.fromisoformat(iso_day)
    return (d + timedelta(days=delta)).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill reference_decimal_odds en bt2_daily_picks")
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Ventana hacia atrás desde hoy (TZ servidor) si no pasás from/to",
    )
    parser.add_argument("--operating-day-from", type=str, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--operating-day-to", type=str, default=None, metavar="YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=5000, help="Máximo filas a procesar")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    url = os.getenv("BT2_DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        print("[backfill_reference_odds] FATAL: BT2_DATABASE_URL", file=sys.stderr)
        return 1

    if args.operating_day_from and args.operating_day_to:
        d0, d1 = args.operating_day_from, args.operating_day_to
    elif args.days is not None and args.days > 0:
        d1 = date.today().isoformat()
        d0 = _add_days_iso(d1, -(args.days - 1))
    else:
        print("Indicá --days N o --operating-day-from / --operating-day-to", file=sys.stderr)
        return 1

    conn = psycopg2.connect(url)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    updated = 0
    examined = 0
    try:
        cur.execute(
            """
            SELECT id, event_id, model_market_canonical, model_selection_canonical
            FROM bt2_daily_picks
            WHERE operating_day_key >= %s AND operating_day_key <= %s
              AND reference_decimal_odds IS NULL
            ORDER BY id
            LIMIT %s
            """,
            (d0, d1, max(1, args.limit)),
        )
        rows = cur.fetchall()
        cache: dict[int, dict[str, dict[str, float]]] = {}
        for r in rows:
            examined += 1
            eid = int(r["event_id"])
            mmc = str(r.get("model_market_canonical") or "")
            msc = str(r.get("model_selection_canonical") or "")
            if eid not in cache:
                agg, _ = aggregated_odds_for_event_psycopg(cur, eid)
                cache[eid] = agg.consensus
            val = consensus_decimal_for_canonical_pick(cache[eid], mmc, msc)
            if val is None:
                continue
            if args.dry_run:
                updated += 1
                continue
            cur.execute(
                """
                UPDATE bt2_daily_picks
                SET reference_decimal_odds = %s
                WHERE id = %s AND reference_decimal_odds IS NULL
                """,
                (val, int(r["id"])),
            )
            updated += int(cur.rowcount or 0)
        if not args.dry_run:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    mode = "dry-run" if args.dry_run else "commit"
    print(
        f"[backfill_reference_odds] {mode} rango {d0}…{d1}: "
        f"examinadas {examined}, actualizadas {updated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

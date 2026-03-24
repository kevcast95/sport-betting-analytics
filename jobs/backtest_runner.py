import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.config import get_db_config  # noqa: E402
from db.db import connect, transaction  # noqa: E402
from db.init_db import init_db  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backtest simple basico sobre pick_results validados.")
    p.add_argument("--db", required=True)
    p.add_argument("--range-start", required=True, help="YYYY-MM-DD")
    p.add_argument("--range-end", required=True, help="YYYY-MM-DD")
    p.add_argument("--strategy-version", required=True)
    return p.parse_args()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _metrics_for_range(conn, *, range_start: str, range_end: str) -> Dict[str, Any]:
    # Profit unit-stake:
    # - win: (picked_value - 1)
    # - loss: -1
    # Nota: si picked_value es NULL -> se asume 0 para no romper.
    cur = conn.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN pr.outcome='win' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN pr.outcome='loss' THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN pr.outcome='pending' THEN 1 ELSE 0 END) AS pendings,
            SUM(CASE
                WHEN pr.outcome='win' THEN COALESCE(p.picked_value, 0) - 1
                WHEN pr.outcome='loss' THEN -1
                ELSE 0
            END) AS profit_unit_stake
        FROM pick_results pr
        JOIN picks p ON p.pick_id = pr.pick_id
        JOIN daily_runs dr ON dr.daily_run_id = p.daily_run_id
        WHERE dr.run_date >= ? AND dr.run_date <= ?
        """,
        (range_start, range_end),
    )
    row = cur.fetchone()
    total = int(row["total"] or 0)
    wins = int(row["wins"] or 0)
    losses = int(row["losses"] or 0)
    pendings = int(row["pendings"] or 0)
    profit = float(row["profit_unit_stake"] or 0)

    win_rate = wins / total if total else None
    return {
        "range_start": range_start,
        "range_end": range_end,
        "total": total,
        "wins": wins,
        "losses": losses,
        "pendings": pendings,
        "win_rate": win_rate,
        "profit_unit_stake": profit,
    }


def _get_or_create_backtest_run_id(conn, *, range_start: str, range_end: str, strategy_version: str) -> int:
    # Schema no fuerza UNIQUE por estos campos, así que lo hacemos a nivel aplicación.
    cur = conn.execute(
        """
        SELECT backtest_run_id FROM backtest_runs
        WHERE range_start = ? AND range_end = ? AND strategy_version = ?
        ORDER BY backtest_run_id DESC
        LIMIT 1
        """,
        (range_start, range_end, strategy_version),
    )
    row = cur.fetchone()
    if row is not None:
        return int(row["backtest_run_id"])

    created_at = _utc_now_iso()
    cur2 = conn.execute(
        """
        INSERT INTO backtest_runs (range_start, range_end, strategy_version, created_at_utc)
        VALUES (?, ?, ?, ?)
        """,
        (range_start, range_end, strategy_version, created_at),
    )
    return int(cur2.lastrowid)


def main() -> None:
    args = parse_args()
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)

    metrics = _metrics_for_range(conn, range_start=args.range_start, range_end=args.range_end)
    backtest_run_id = _get_or_create_backtest_run_id(
        conn,
        range_start=args.range_start,
        range_end=args.range_end,
        strategy_version=args.strategy_version,
    )

    with transaction(conn):
        # Upsert simple por backtest_run_id
        conn.execute(
            """
            INSERT OR REPLACE INTO backtest_metrics (backtest_run_id, metrics_json, created_at_utc)
            VALUES (?, ?, ?)
            """,
            (
                backtest_run_id,
                json.dumps(metrics, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
                _utc_now_iso(),
            ),
        )

    print(f"OK backtest_run_id={backtest_run_id}")


if __name__ == "__main__":
    main()


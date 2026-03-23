#!/usr/bin/env python3
"""
reset_db.py

Elimina todos los datos de SQLite. Reinicia desde 0.
Las tablas se mantienen (esquema intacto) pero vacías.
"""

import argparse
import os
import sqlite3
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.config import get_db_config  # noqa: E402
from db.db import connect  # noqa: E402
from db.init_db import init_db  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Vaciar todas las tablas de SQLite.")
    p.add_argument("--db", required=True)
    p.add_argument("--yes", "-y", action="store_true", help="No pedir confirmación")
    return p.parse_args()


def run(args: argparse.Namespace) -> None:
    cfg = get_db_config(args.db)
    conn = connect(cfg.path)
    init_db(conn)  # asegura que existan las tablas

    if not args.yes:
        confirm = input(f"¿Vaciar TODOS los datos de {cfg.path}? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelado.")
            return

    # Orden por FK: hijos primero
    tables = [
        "pick_results",
        "picks",
        "backtest_metrics",
        "backtest_runs",
        "event_features",
        "event_snapshots",
        "daily_runs",
    ]

    counts = {}
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        for t in tables:
            cur = conn.execute(f"DELETE FROM {t}")
            counts[t] = cur.rowcount
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
    # Reinicia secuencias AUTOINCREMENT (p. ej. daily_run_id = 1 en el próximo run)
    try:
        conn.execute("DELETE FROM sqlite_sequence")
    except sqlite3.OperationalError:
        pass  # tabla aún no existe si nunca hubo inserts AUTOINCREMENT
    conn.commit()

    result = {
        "status": "ok",
        "db": cfg.path,
        "tables_cleared": counts,
        "total_rows_deleted": sum(counts.values()),
    }

    print("\n=== RESET DB ===")
    print(f"DB: {result['db']}")
    print(f"Filas eliminadas por tabla: {result['tables_cleared']}")
    print(f"Total: {result['total_rows_deleted']} filas")
    print("=== OK Base de datos vacía. Lista para ingest. ===\n")


def main() -> None:
    args = parse_args()
    run(args)


if __name__ == "__main__":
    main()

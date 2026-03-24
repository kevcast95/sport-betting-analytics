"""
Migraciones aditivas SQLite (ALTER TABLE) para bases ya existentes.
Ejecutar tras init_db.
"""

from __future__ import annotations

import sqlite3
from typing import Iterable, Tuple


def _picks_table_has_legacy_selection_check(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='picks'"
    ).fetchone()
    if not row or not row[0]:
        return False
    sql_upper = row[0].upper()
    return "SELECTION IN ('1','X','2')" in sql_upper or 'SELECTION IN ("1","X","2")' in sql_upper


def relax_picks_selection_constraint(conn: sqlite3.Connection) -> bool:
    """
    SQLite no permite quitar CHECK en columnas; recrea `picks` sin el CHECK de 1X2
    para permitir mercados compuestos (Over 2.5, BTTS, etc.).
    """
    if not _picks_table_has_legacy_selection_check(conn):
        return False

    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        conn.executescript(
            """
            BEGIN;
            CREATE TABLE picks__migration (
              pick_id INTEGER PRIMARY KEY AUTOINCREMENT,
              daily_run_id INTEGER NOT NULL,
              event_id INTEGER NOT NULL,
              market TEXT NOT NULL,
              selection TEXT NOT NULL,
              picked_value REAL,
              odds_reference TEXT,
              status TEXT NOT NULL CHECK (status IN ('pending','validated','void')),
              created_at_utc TEXT NOT NULL,
              idempotency_key TEXT NOT NULL UNIQUE,
              FOREIGN KEY (daily_run_id) REFERENCES daily_runs(daily_run_id)
            );
            INSERT INTO picks__migration SELECT * FROM picks;
            DROP TABLE picks;
            ALTER TABLE picks__migration RENAME TO picks;
            COMMIT;
            """
        )
    finally:
        conn.execute("PRAGMA foreign_keys=ON")
    return True


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {str(r[1]) for r in cur.fetchall()}


def _add_column(conn: sqlite3.Connection, table: str, ddl: str) -> None:
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def apply_migrations(conn: sqlite3.Connection) -> list[str]:
    """Aplica migraciones pendientes. Retorna lista de descripciones aplicadas."""
    applied: list[str] = []
    if relax_picks_selection_constraint(conn):
        applied.append("picks.selection (relax CHECK)")

    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_pick_decisions'"
    ).fetchone()
    if not exists:
        return applied
    if not _columns(conn, "user_pick_decisions"):
        return applied

    specs: Iterable[Tuple[str, str]] = (
        ("risk_category", "risk_category TEXT"),
        ("decision_origin", "decision_origin TEXT"),
        ("stake_amount", "stake_amount REAL"),
        ("user_outcome", "user_outcome TEXT"),
        ("user_outcome_updated_at_utc", "user_outcome_updated_at_utc TEXT"),
    )
    existing = _columns(conn, "user_pick_decisions")
    for name, ddl in specs:
        if name not in existing:
            _add_column(conn, "user_pick_decisions", ddl)
            applied.append(f"user_pick_decisions.{name}")
    return applied

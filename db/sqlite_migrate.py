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


def _backfill_bankroll_delta_applied_cop(conn: sqlite3.Connection) -> None:
    """
    Evita doble contabilidad: filas existentes quedan marcadas con el delta lógico
    ya asumido antes de existir la columna (sin tocar users.bankroll_cop).
    """
    from db.repositories.dashboard_repo import _effective_outcome

    rows = conn.execute(
        """
        SELECT d.user_id, d.pick_id, d.taken, d.stake_amount, d.user_outcome,
               p.picked_value, pr.outcome AS pr_outcome
        FROM user_pick_decisions d
        JOIN picks p ON p.pick_id = d.pick_id
        LEFT JOIN pick_results pr ON pr.pick_id = d.pick_id
        """
    ).fetchall()
    for r in rows:
        eff = _effective_outcome(r["user_outcome"], r["pr_outcome"])
        taken = bool(r["taken"])
        stake = r["stake_amount"]
        odds = r["picked_value"]
        desired = 0.0
        if taken and stake is not None and float(stake) > 0:
            sf = float(stake)
            if eff == "win" and odds is not None:
                o = float(odds)
                if o > 1:
                    desired = round(sf * (o - 1.0), 2)
            elif eff == "loss":
                desired = round(-sf, 2)
        conn.execute(
            """
            UPDATE user_pick_decisions
            SET bankroll_delta_applied_cop = ?
            WHERE user_id = ? AND pick_id = ?
            """,
            (desired, int(r["user_id"]), int(r["pick_id"])),
        )


def apply_migrations(conn: sqlite3.Connection) -> list[str]:
    """Aplica migraciones pendientes. Retorna lista de descripciones aplicadas."""
    applied: list[str] = []
    if relax_picks_selection_constraint(conn):
        applied.append("picks.selection (relax CHECK)")

    upd_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_pick_decisions'"
    ).fetchone()
    if upd_exists and _columns(conn, "user_pick_decisions"):
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

        upd_cols = _columns(conn, "user_pick_decisions")
        if "realized_return_cop" not in upd_cols:
            _add_column(conn, "user_pick_decisions", "realized_return_cop REAL")
            applied.append("user_pick_decisions.realized_return_cop")
        if "bankroll_delta_applied_cop" not in upd_cols:
            _add_column(
                conn, "user_pick_decisions", "bankroll_delta_applied_cop REAL"
            )
            applied.append("user_pick_decisions.bankroll_delta_applied_cop")
            _backfill_bankroll_delta_applied_cop(conn)
            applied.append("user_pick_decisions.bankroll_delta_applied_cop (backfill)")

    users_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    if users_exists and _columns(conn, "users"):
        uc = _columns(conn, "users")
        if "bankroll_cop" not in uc:
            _add_column(conn, "users", "bankroll_cop REAL")
            applied.append("users.bankroll_cop")

    combo_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_combo_decisions'"
    ).fetchone()
    if combo_exists:
        combo_cols = _columns(conn, "user_combo_decisions")
        combo_specs: Iterable[Tuple[str, str]] = (
            ("stake_amount", "stake_amount REAL"),
            ("user_outcome", "user_outcome TEXT"),
            ("user_outcome_updated_at_utc", "user_outcome_updated_at_utc TEXT"),
        )
        for name, ddl in combo_specs:
            if name not in combo_cols:
                _add_column(conn, "user_combo_decisions", ddl)
                applied.append(f"user_combo_decisions.{name}")
    return applied

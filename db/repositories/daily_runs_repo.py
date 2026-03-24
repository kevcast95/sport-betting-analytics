import sqlite3
from datetime import datetime, timezone
from typing import Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_daily_run_by_date_sport(
    conn: sqlite3.Connection, run_date: str, sport: str
) -> Optional[sqlite3.Row]:
    cur = conn.execute(
        "SELECT * FROM daily_runs WHERE run_date = ? AND sport = ?",
        (run_date, sport),
    )
    return cur.fetchone()


def ensure_daily_run(conn: sqlite3.Connection, run_date: str, sport: str) -> Tuple[int, str]:
    """
    Idempotente:
    - si existe status=complete => retorna id existente
    - si existe running/failed => reintenta con status=running (mismo id)
    - si no existe => crea con status=running
    """
    existing = get_daily_run_by_date_sport(conn, run_date, sport)
    if existing is not None:
        daily_run_id = int(existing["daily_run_id"])
        status = str(existing["status"])
        if status == "complete":
            return daily_run_id, status
        if status != "complete":
            conn.execute(
                "UPDATE daily_runs SET status = ? WHERE daily_run_id = ?",
                ("running", daily_run_id),
            )
            conn.commit()
            status = "running"
        return daily_run_id, status

    created_at = _utc_now_iso()
    cur = conn.execute(
        """
        INSERT INTO daily_runs (run_date, sport, created_at_utc, status)
        VALUES (?, ?, ?, ?)
        """,
        (run_date, sport, created_at, "running"),
    )
    conn.commit()
    return int(cur.lastrowid), "running"


def update_status(conn: sqlite3.Connection, daily_run_id: int, status: str) -> None:
    # Compatibilidad defensiva: si alguien pasa "completed", normalizamos a "complete".
    if status == "completed":
        status = "complete"
    conn.execute(
        "UPDATE daily_runs SET status = ? WHERE daily_run_id = ?",
        (status, daily_run_id),
    )
    conn.commit()


def get_daily_run(conn: sqlite3.Connection, daily_run_id: int) -> sqlite3.Row:
    cur = conn.execute("SELECT * FROM daily_runs WHERE daily_run_id = ?", (daily_run_id,))
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"daily_run_id no existe: {daily_run_id}")
    return row


import sqlite3
from datetime import datetime, timezone
from typing import List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_users(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT user_id, slug, display_name, created_at_utc, bankroll_cop
        FROM users ORDER BY user_id ASC
        """
    )
    return cur.fetchall()


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT user_id, slug, display_name, created_at_utc, bankroll_cop
        FROM users WHERE user_id = ?
        """,
        (user_id,),
    )
    return cur.fetchone()


def set_user_bankroll_cop(
    conn: sqlite3.Connection, *, user_id: int, bankroll_cop: Optional[float]
) -> None:
    conn.execute(
        "UPDATE users SET bankroll_cop = ? WHERE user_id = ?",
        (bankroll_cop, user_id),
    )


def insert_user(conn: sqlite3.Connection, *, slug: str, display_name: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO users (slug, display_name, created_at_utc)
        VALUES (?, ?, ?)
        """,
        (slug.strip(), display_name.strip(), _utc_now_iso()),
    )
    return int(cur.lastrowid)


def ensure_default_test_users(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Crea dos usuarios de prueba si la tabla está vacía."""
    cur = conn.execute("SELECT COUNT(*) AS c FROM users")
    if int(cur.fetchone()["c"]) > 0:
        return list_users(conn)
    insert_user(conn, slug="kevin", display_name="Kevin")
    insert_user(conn, slug="spouse", display_name="Esposa")
    conn.commit()
    return list_users(conn)

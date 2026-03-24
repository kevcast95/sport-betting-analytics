import sqlite3
from typing import Any, Optional

from db.repositories.json_utils import dumps_json_stable


def upsert_event_snapshot(
    conn: sqlite3.Connection,
    event_id: int,
    dataset: str,
    captured_at_utc: str,
    payload_raw: Any,
    source: Optional[str],
    *,
    sport: str = "football",
) -> None:
    """
    Inserta idempotente por UNIQUE(sport, event_id, dataset, captured_at_utc).
    Si ya existe, no duplica (INSERT OR IGNORE).
    """
    payload_text = dumps_json_stable(payload_raw)
    sp = (sport or "football").strip().lower()
    conn.execute(
        """
        INSERT OR IGNORE INTO event_snapshots (
            sport, event_id, dataset, captured_at_utc, payload_raw, source
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (sp, event_id, dataset, captured_at_utc, payload_text, source),
    )
    # No commit aquí para permitir transacciones por batch.


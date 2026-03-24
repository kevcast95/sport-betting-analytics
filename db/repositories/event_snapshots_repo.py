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
) -> None:
    """
    Inserta idempotente por UNIQUE(event_id, dataset, captured_at_utc).
    Si ya existe, no duplica (INSERT OR IGNORE).
    """
    payload_text = dumps_json_stable(payload_raw)
    conn.execute(
        """
        INSERT OR IGNORE INTO event_snapshots (
            event_id, dataset, captured_at_utc, payload_raw, source
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (event_id, dataset, captured_at_utc, payload_text, source),
    )
    # No commit aquí para permitir transacciones por batch.


import sqlite3
from typing import Any, Dict, List, Optional

from db.repositories.json_utils import dumps_json_stable


def fetch_event_features_by_captured_at(
    conn: sqlite3.Connection,
    captured_at_utc: str,
    *,
    sport: str,
) -> List[sqlite3.Row]:
    sp = (sport or "football").strip().lower()
    cur = conn.execute(
        """
        SELECT event_id, captured_at_utc, features_json
        FROM event_features
        WHERE captured_at_utc = ? AND sport = ?
        ORDER BY event_id ASC
        """,
        (captured_at_utc, sp),
    )
    return cur.fetchall()


def insert_event_features(
    conn: sqlite3.Connection,
    event_id: int,
    captured_at_utc: str,
    features_json: Any,
    processor_versions_json: Any,
    *,
    sport: str = "football",
) -> None:
    """
    Idempotente por UNIQUE(sport, event_id, captured_at_utc) -> INSERT OR IGNORE.
    """
    sp = (sport or "football").strip().lower()
    features_text = dumps_json_stable(features_json)
    proc_text = dumps_json_stable(processor_versions_json)
    conn.execute(
        """
        INSERT OR IGNORE INTO event_features (
            sport, event_id, captured_at_utc, features_json, processor_versions_json
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (sp, event_id, captured_at_utc, features_text, proc_text),
    )


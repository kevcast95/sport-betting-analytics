import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from db.repositories.json_utils import dumps_json_stable


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_pick_result(
    conn: sqlite3.Connection,
    *,
    pick_id: int,
    validated_at_utc: Optional[str] = None,
    home_score: Optional[int],
    away_score: Optional[int],
    result_1x2: Optional[str],
    outcome: str,
    evidence_json: Any,
) -> None:
    """
    Idempotente por UNIQUE(pick_id) vía UPSERT:
    - Si existe, actualiza (por ejemplo, pending -> win/loss).
    """
    validated = validated_at_utc or _utc_now_iso()
    evidence_text = dumps_json_stable(evidence_json)
    conn.execute(
        """
        INSERT INTO pick_results (
            pick_id, validated_at_utc, home_score, away_score, result_1x2, outcome, evidence_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(pick_id) DO UPDATE SET
            validated_at_utc = excluded.validated_at_utc,
            home_score = excluded.home_score,
            away_score = excluded.away_score,
            result_1x2 = excluded.result_1x2,
            outcome = excluded.outcome,
            evidence_json = excluded.evidence_json
        """,
        (
            pick_id,
            validated,
            home_score,
            away_score,
            result_1x2,
            outcome,
            evidence_text,
        ),
    )


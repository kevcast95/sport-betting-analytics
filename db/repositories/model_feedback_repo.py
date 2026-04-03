"""Feedback por evento tras análisis LLM (motivo sin pick / filtros de pipeline)."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional, Tuple


def fetch_feedback_map(
    conn: sqlite3.Connection, *, daily_run_id: int
) -> Dict[int, Tuple[Optional[str], Optional[str]]]:
    cur = conn.execute(
        """
        SELECT event_id, model_skip_reason, pipeline_skip_summary
        FROM daily_run_event_model_feedback
        WHERE daily_run_id = ?
        """,
        (int(daily_run_id),),
    )
    out: Dict[int, Tuple[Optional[str], Optional[str]]] = {}
    for row in cur.fetchall():
        eid = int(row["event_id"])
        mr = row["model_skip_reason"]
        ps = row["pipeline_skip_summary"]
        out[eid] = (
            str(mr) if mr is not None and str(mr).strip() else None,
            str(ps) if ps is not None and str(ps).strip() else None,
        )
    return out


def upsert_feedback_for_run(
    conn: sqlite3.Connection,
    *,
    daily_run_id: int,
    rows: List[Dict[str, Any]],
    updated_at_utc: str,
) -> int:
    """
    Inserta o actualiza feedback por (daily_run_id, event_id).
    No borra filas de otros eventos del mismo run (varias ventanas pueden persistir en el mismo DR).
    """
    dr = int(daily_run_id)
    n = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            eid = int(r["event_id"])
        except (TypeError, ValueError, KeyError):
            continue
        mr = r.get("model_skip_reason")
        ps = r.get("pipeline_skip_summary")
        mr_s = str(mr).strip() if mr is not None and str(mr).strip() else None
        ps_s = str(ps).strip() if ps is not None and str(ps).strip() else None
        if mr_s is None and ps_s is None:
            continue
        conn.execute(
            """
            INSERT INTO daily_run_event_model_feedback (
              daily_run_id, event_id, model_skip_reason, pipeline_skip_summary, updated_at_utc
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(daily_run_id, event_id) DO UPDATE SET
              model_skip_reason = excluded.model_skip_reason,
              pipeline_skip_summary = excluded.pipeline_skip_summary,
              updated_at_utc = excluded.updated_at_utc
            """,
            (dr, eid, mr_s, ps_s, updated_at_utc),
        )
        n += 1
    return n

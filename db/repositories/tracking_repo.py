import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_user_pick_decision(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    pick_id: int,
    taken: bool,
    notes: Optional[str] = None,
    risk_category: Optional[str] = None,
    decision_origin: Optional[str] = None,
    stake_amount: Optional[float] = None,
    user_outcome: Optional[str] = None,
) -> None:
    if user_outcome is not None and user_outcome not in ("win", "loss", "pending"):
        raise ValueError(f"user_outcome inválido: {user_outcome!r}")
    uo_ts = _utc_now_iso() if user_outcome is not None else None
    conn.execute(
        """
        INSERT INTO user_pick_decisions (
            user_id, pick_id, taken, updated_at_utc, notes,
            risk_category, decision_origin, stake_amount,
            user_outcome, user_outcome_updated_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, pick_id) DO UPDATE SET
            taken = excluded.taken,
            updated_at_utc = excluded.updated_at_utc,
            notes = COALESCE(excluded.notes, user_pick_decisions.notes),
            risk_category = COALESCE(excluded.risk_category, user_pick_decisions.risk_category),
            decision_origin = COALESCE(excluded.decision_origin, user_pick_decisions.decision_origin),
            stake_amount = COALESCE(excluded.stake_amount, user_pick_decisions.stake_amount),
            user_outcome = excluded.user_outcome,
            user_outcome_updated_at_utc = excluded.user_outcome_updated_at_utc
        """,
        (
            user_id,
            pick_id,
            1 if taken else 0,
            _utc_now_iso(),
            notes,
            risk_category,
            decision_origin,
            stake_amount,
            user_outcome,
            uo_ts,
        ),
    )


def get_pick_decisions_for_run(
    conn: sqlite3.Connection, *, user_id: int, daily_run_id: int
) -> Dict[int, bool]:
    cur = conn.execute(
        """
        SELECT d.pick_id, d.taken
        FROM user_pick_decisions d
        JOIN picks p ON p.pick_id = d.pick_id
        WHERE d.user_id = ? AND p.daily_run_id = ?
        """,
        (user_id, daily_run_id),
    )
    return {int(r["pick_id"]): bool(r["taken"]) for r in cur.fetchall()}


def get_pick_decision_rows_for_run(
    conn: sqlite3.Connection, *, user_id: int, daily_run_id: int
) -> Dict[int, sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT d.pick_id, d.taken, d.risk_category, d.decision_origin, d.stake_amount,
               d.user_outcome
        FROM user_pick_decisions d
        JOIN picks p ON p.pick_id = d.pick_id
        WHERE d.user_id = ? AND p.daily_run_id = ?
        """,
        (user_id, daily_run_id),
    )
    return {int(r["pick_id"]): r for r in cur.fetchall()}


def upsert_user_combo_decision(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    suggested_combo_id: int,
    taken: bool,
) -> None:
    conn.execute(
        """
        INSERT INTO user_combo_decisions (user_id, suggested_combo_id, taken, updated_at_utc)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, suggested_combo_id) DO UPDATE SET
            taken = excluded.taken,
            updated_at_utc = excluded.updated_at_utc
        """,
        (user_id, suggested_combo_id, 1 if taken else 0, _utc_now_iso()),
    )


def get_combo_decisions_for_run(
    conn: sqlite3.Connection, *, user_id: int, daily_run_id: int
) -> Dict[int, bool]:
    cur = conn.execute(
        """
        SELECT d.suggested_combo_id, d.taken
        FROM user_combo_decisions d
        JOIN suggested_combos c ON c.suggested_combo_id = d.suggested_combo_id
        WHERE d.user_id = ? AND c.daily_run_id = ?
        """,
        (user_id, daily_run_id),
    )
    return {int(r["suggested_combo_id"]): bool(r["taken"]) for r in cur.fetchall()}


def ensure_pick_baselines_for_run(conn: sqlite3.Connection, *, daily_run_id: int) -> int:
    """Copia odds_reference + picked_value en baseline si aún no existe."""
    cur = conn.execute(
        """
        SELECT pick_id, picked_value, odds_reference
        FROM picks
        WHERE daily_run_id = ?
        """,
        (daily_run_id,),
    )
    rows = cur.fetchall()
    inserted = 0
    for r in rows:
        pid = int(r["pick_id"])
        exists = conn.execute(
            "SELECT 1 FROM pick_baseline_snapshots WHERE pick_id = ?",
            (pid,),
        ).fetchone()
        if exists:
            continue
        baseline: Dict[str, Any] = {
            "picked_value": r["picked_value"],
            "odds_reference": None,
        }
        raw = r["odds_reference"]
        if raw:
            try:
                baseline["odds_reference"] = json.loads(raw)
            except json.JSONDecodeError:
                baseline["odds_reference"] = {"_raw": raw[:2000]}
        conn.execute(
            """
            INSERT INTO pick_baseline_snapshots (pick_id, captured_at_utc, baseline_json)
            VALUES (?, ?, ?)
            """,
            (pid, _utc_now_iso(), json.dumps(baseline, ensure_ascii=False)),
        )
        inserted += 1
    return inserted


def insert_signal_check(
    conn: sqlite3.Connection,
    *,
    pick_id: int,
    slot: str,
    status: str,
    detail: Optional[Any] = None,
) -> int:
    if status not in ("ok", "degraded", "unknown"):
        raise ValueError("status inválido")
    detail_text = json.dumps(detail, ensure_ascii=False) if detail is not None else None
    cur = conn.execute(
        """
        INSERT INTO pick_signal_checks (pick_id, slot, checked_at_utc, status, detail_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (pick_id, slot, _utc_now_iso(), status, detail_text),
    )
    return int(cur.lastrowid)

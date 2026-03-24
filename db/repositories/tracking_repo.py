import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from db.repositories.dashboard_repo import _effective_outcome


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
            user_outcome, user_outcome_updated_at_utc, realized_return_cop,
            bankroll_delta_applied_cop
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
        ON CONFLICT(user_id, pick_id) DO UPDATE SET
            taken = excluded.taken,
            updated_at_utc = excluded.updated_at_utc,
            notes = COALESCE(excluded.notes, user_pick_decisions.notes),
            risk_category = COALESCE(excluded.risk_category, user_pick_decisions.risk_category),
            decision_origin = COALESCE(excluded.decision_origin, user_pick_decisions.decision_origin),
            stake_amount = COALESCE(excluded.stake_amount, user_pick_decisions.stake_amount),
            user_outcome = excluded.user_outcome,
            user_outcome_updated_at_utc = excluded.user_outcome_updated_at_utc,
            realized_return_cop = user_pick_decisions.realized_return_cop,
            bankroll_delta_applied_cop = user_pick_decisions.bankroll_delta_applied_cop
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
               d.user_outcome, d.realized_return_cop
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
    stake_amount: Optional[float] = None,
    user_outcome: Optional[str] = None,
) -> None:
    if user_outcome is not None and user_outcome not in ("win", "loss", "pending"):
        raise ValueError(f"user_outcome inválido: {user_outcome!r}")
    uo_ts = _utc_now_iso() if user_outcome is not None else None
    conn.execute(
        """
        INSERT INTO user_combo_decisions (
            user_id, suggested_combo_id, taken, updated_at_utc,
            stake_amount, user_outcome, user_outcome_updated_at_utc
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, suggested_combo_id) DO UPDATE SET
            taken = excluded.taken,
            updated_at_utc = excluded.updated_at_utc,
            stake_amount = excluded.stake_amount,
            user_outcome = excluded.user_outcome,
            user_outcome_updated_at_utc = excluded.user_outcome_updated_at_utc
        """,
        (
            user_id,
            suggested_combo_id,
            1 if taken else 0,
            _utc_now_iso(),
            stake_amount,
            user_outcome,
            uo_ts,
        ),
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


def get_combo_decision_rows_for_run(
    conn: sqlite3.Connection, *, user_id: int, daily_run_id: int
) -> Dict[int, sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT d.suggested_combo_id, d.taken, d.stake_amount, d.user_outcome
        FROM user_combo_decisions d
        JOIN suggested_combos c ON c.suggested_combo_id = d.suggested_combo_id
        WHERE d.user_id = ? AND c.daily_run_id = ?
        """,
        (user_id, daily_run_id),
    )
    return {int(r["suggested_combo_id"]): r for r in cur.fetchall()}


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


def sync_user_pick_realized_return(
    conn: sqlite3.Connection, *, user_id: int, pick_id: int
) -> None:
    """
    - realized_return_cop: ganancia bruta si efectivo es win; si no, NULL.
    - users.bankroll_cop: + ganancia en win, − stake en loss (solo pick tomado);
      idempotente vía bankroll_delta_applied_cop.
    """
    row = conn.execute(
        """
        SELECT d.taken, d.stake_amount, d.user_outcome, d.bankroll_delta_applied_cop,
               p.picked_value, pr.outcome AS pr_outcome
        FROM user_pick_decisions d
        JOIN picks p ON p.pick_id = d.pick_id
        LEFT JOIN pick_results pr ON pr.pick_id = d.pick_id
        WHERE d.user_id = ? AND d.pick_id = ?
        """,
        (user_id, pick_id),
    ).fetchone()
    if row is None:
        return
    eff = _effective_outcome(row["user_outcome"], row["pr_outcome"])
    stake = row["stake_amount"]
    odds = row["picked_value"]
    taken = bool(row["taken"])
    ret: Optional[float] = None
    if eff == "win" and stake is not None and float(stake) > 0 and odds is not None:
        o = float(odds)
        if o > 1:
            ret = round(float(stake) * (o - 1.0), 2)

    desired_bank_delta = 0.0
    if taken and stake is not None and float(stake) > 0:
        sf = float(stake)
        if eff == "win" and odds is not None:
            o = float(odds)
            if o > 1:
                desired_bank_delta = round(sf * (o - 1.0), 2)
        elif eff == "loss":
            desired_bank_delta = round(-sf, 2)

    prev_raw = row["bankroll_delta_applied_cop"]
    prev_applied = float(prev_raw) if prev_raw is not None else 0.0
    adjustment = round(desired_bank_delta - prev_applied, 2)
    if adjustment != 0.0:
        conn.execute(
            """
            UPDATE users
            SET bankroll_cop = ROUND(COALESCE(bankroll_cop, 0) + ?, 2)
            WHERE user_id = ?
            """,
            (adjustment, user_id),
        )

    conn.execute(
        """
        UPDATE user_pick_decisions
        SET realized_return_cop = ?,
            bankroll_delta_applied_cop = ?
        WHERE user_id = ? AND pick_id = ?
        """,
        (ret, desired_bank_delta, user_id, pick_id),
    )


def sync_realized_returns_for_pick(conn: sqlite3.Connection, *, pick_id: int) -> None:
    cur = conn.execute(
        "SELECT user_id FROM user_pick_decisions WHERE pick_id = ?",
        (pick_id,),
    )
    for r in cur.fetchall():
        sync_user_pick_realized_return(
            conn, user_id=int(r["user_id"]), pick_id=pick_id
        )

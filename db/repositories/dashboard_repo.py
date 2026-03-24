"""Agregados para el dashboard (picks = apuestas del modelo)."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional


def _effective_outcome(u_outcome: Any, pr_outcome: Any) -> str:
    """Prioriza cierre declarado por el usuario; si no, resultado en pick_results."""
    if u_outcome in ("win", "loss", "pending"):
        return str(u_outcome)
    if pr_outcome in ("win", "loss"):
        return str(pr_outcome)
    if pr_outcome == "pending":
        return "pending"
    return "pending"


def _rows_for_date(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    user_id: Optional[int],
) -> List[sqlite3.Row]:
    if user_id is None:
        sql = """
            SELECT
                p.pick_id,
                p.daily_run_id,
                p.picked_value,
                p.market,
                p.selection,
                p.event_id,
                p.created_at_utc,
                p.odds_reference,
                pr.outcome AS pr_outcome,
                NULL AS u_taken,
                NULL AS u_stake,
                NULL AS u_risk,
                NULL AS u_origin,
                NULL AS u_outcome
            FROM picks p
            INNER JOIN daily_runs dr ON dr.daily_run_id = p.daily_run_id
            LEFT JOIN pick_results pr ON pr.pick_id = p.pick_id
            WHERE dr.run_date = ?
        """
        return list(conn.execute(sql, (run_date,)).fetchall())
    sql = """
        SELECT
            p.pick_id,
            p.daily_run_id,
            p.picked_value,
            p.market,
            p.selection,
            p.event_id,
            p.created_at_utc,
            p.odds_reference,
            pr.outcome AS pr_outcome,
            d.taken AS u_taken,
            d.stake_amount AS u_stake,
            d.risk_category AS u_risk,
            d.decision_origin AS u_origin,
            d.user_outcome AS u_outcome
        FROM picks p
        INNER JOIN daily_runs dr ON dr.daily_run_id = p.daily_run_id
        LEFT JOIN pick_results pr ON pr.pick_id = p.pick_id
        LEFT JOIN user_pick_decisions d ON d.pick_id = p.pick_id AND d.user_id = ?
        WHERE dr.run_date = ?
    """
    return list(conn.execute(sql, (user_id, run_date)).fetchall())


def daily_picks_summary(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    rows = _rows_for_date(conn, run_date=run_date, user_id=user_id)
    total = len(rows)
    wins = losses = pending = 0
    taken_ct = 0
    taken_wins = taken_losses = taken_pending = 0
    net_pl = 0.0
    has_any_stake = False

    for r in rows:
        uo = r["u_outcome"]
        pr_o = r["pr_outcome"]
        eff = _effective_outcome(uo, pr_o)
        if eff == "win":
            wins += 1
        elif eff == "loss":
            losses += 1
        else:
            pending += 1

        is_taken = r["u_taken"] == 1
        if is_taken:
            taken_ct += 1
            if eff == "win":
                taken_wins += 1
            elif eff == "loss":
                taken_losses += 1
            else:
                taken_pending += 1
            stake = r["u_stake"]
            odds = r["picked_value"]
            if stake is not None and odds is not None and eff in ("win", "loss"):
                has_any_stake = True
                stake_f = float(stake)
                odds_f = float(odds)
                if eff == "win":
                    net_pl += stake_f * (odds_f - 1.0)
                else:
                    net_pl -= stake_f

    return {
        "run_date": run_date,
        "picks_total": total,
        "outcome_wins": wins,
        "outcome_losses": losses,
        "outcome_pending": pending,
        "picks_taken_count": taken_ct,
        "taken_outcome_wins": taken_wins,
        "taken_outcome_losses": taken_losses,
        "taken_outcome_pending": taken_pending,
        "net_pl_estimate": round(net_pl, 2) if has_any_stake else None,
        "has_stake_data": has_any_stake,
    }


def recent_picks_for_date(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    user_id: Optional[int],
    limit: int = 12,
) -> List[sqlite3.Row]:
    rows = _rows_for_date(conn, run_date=run_date, user_id=user_id)
    # ya ordenados por created_at desc en query — re-sort por si acaso
    sorted_rows = sorted(
        rows,
        key=lambda x: str(x["created_at_utc"] or ""),
        reverse=True,
    )
    return sorted_rows[:limit]

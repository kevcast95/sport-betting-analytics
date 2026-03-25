"""Agregados para el dashboard (picks = apuestas del modelo)."""

from __future__ import annotations

import json
import os
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


def _selection_stats_from_artifact(
    run_date: str, sport: Optional[str] = None
) -> Dict[str, Any]:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    s = str(sport).strip().lower() if sport else ""
    if s and s != "football":
        p = os.path.join(
            repo_root, "out", f"candidates_{run_date}_select_{s}.json"
        )
        if not os.path.exists(p):
            return {}
    else:
        p = os.path.join(repo_root, "out", f"candidates_{run_date}_select.json")
        if not os.path.exists(p):
            return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    reasons = data.get("rejection_reasons")
    reasons_d = reasons if isinstance(reasons, dict) else {}
    top_reason = None
    top_reason_count = 0
    for k, v in reasons_d.items():
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n > top_reason_count:
            top_reason = str(k)
            top_reason_count = n
    out: Dict[str, Any] = {
        "selection_total_events": int(data.get("total_events") or 0),
        "selection_passed_filters": int(data.get("passed_filters") or 0),
        "selection_rejected": int(data.get("rejected") or 0),
        "selection_top_reject_reason": top_reason,
        "selection_top_reject_reason_count": top_reason_count,
    }
    selected = data.get("selected")
    if isinstance(selected, list):
        out["selection_selected_events"] = len(selected)
    return out


def _rows_for_date(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    user_id: Optional[int],
    sport: Optional[str] = None,
) -> List[sqlite3.Row]:
    sport_clause = ""
    sport_norm: Optional[str] = None
    if sport is not None and str(sport).strip() != "":
        sport_norm = str(sport).strip().lower()
        sport_clause = " AND LOWER(TRIM(dr.sport)) = ?"

    if user_id is None:
        sql = f"""
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
            WHERE dr.run_date = ?{sport_clause}
        """
        params: List[Any] = [run_date]
        if sport_norm is not None:
            params.append(sport_norm)
        return list(conn.execute(sql, tuple(params)).fetchall())
    sql = f"""
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
        WHERE dr.run_date = ?{sport_clause}
    """
    params2: List[Any] = [user_id, run_date]
    if sport_norm is not None:
        params2.append(sport_norm)
    return list(conn.execute(sql, tuple(params2)).fetchall())


def daily_picks_summary(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    user_id: Optional[int] = None,
    sport: Optional[str] = None,
) -> Dict[str, Any]:
    sport_f = (
        str(sport).strip().lower()
        if sport is not None and str(sport).strip()
        else None
    )
    selection = _selection_stats_from_artifact(run_date, sport=sport_f)
    rows = _rows_for_date(
        conn, run_date=run_date, user_id=user_id, sport=sport_f
    )
    if sport_f:
        events_row = conn.execute(
            """
            SELECT COUNT(DISTINCT ef.event_id) AS n
            FROM daily_runs dr
            INNER JOIN event_features ef
              ON ef.captured_at_utc = dr.created_at_utc
            WHERE dr.run_date = ? AND LOWER(TRIM(dr.sport)) = ?
            """,
            (run_date, sport_f),
        ).fetchone()
        run_id_row = conn.execute(
            """
            SELECT daily_run_id
            FROM daily_runs
            WHERE run_date = ? AND LOWER(TRIM(sport)) = ?
            ORDER BY daily_run_id DESC
            LIMIT 1
            """,
            (run_date, sport_f),
        ).fetchone()
    else:
        events_row = conn.execute(
            """
            SELECT COUNT(DISTINCT ef.event_id) AS n
            FROM daily_runs dr
            INNER JOIN event_features ef
              ON ef.captured_at_utc = dr.created_at_utc
            WHERE dr.run_date = ?
            """,
            (run_date,),
        ).fetchone()
        run_id_row = conn.execute(
            """
            SELECT daily_run_id
            FROM daily_runs
            WHERE run_date = ?
            ORDER BY daily_run_id DESC
            LIMIT 1
            """,
            (run_date,),
        ).fetchone()
    events_total = (
        int(events_row["n"])
        if events_row and events_row["n"] is not None
        else 0
    )
    primary_daily_run_id = (
        int(run_id_row["daily_run_id"])
        if run_id_row and run_id_row["daily_run_id"] is not None
        else None
    )
    total = len(rows)
    wins = losses = pending = 0
    taken_ct = 0
    taken_wins = taken_losses = taken_pending = 0
    not_taken_wins = not_taken_losses = not_taken_pending = 0
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
        elif user_id is not None:
            if eff == "win":
                not_taken_wins += 1
            elif eff == "loss":
                not_taken_losses += 1
            else:
                not_taken_pending += 1

    if user_id is None:
        not_taken_wins, not_taken_losses, not_taken_pending = wins, losses, pending

    return {
        "run_date": run_date,
        "sport": sport_f,
        "primary_daily_run_id": primary_daily_run_id,
        "events_total": events_total,
        "selection_total_events": int(selection.get("selection_total_events") or 0),
        "selection_passed_filters": int(selection.get("selection_passed_filters") or 0),
        "selection_rejected": int(selection.get("selection_rejected") or 0),
        "selection_selected_events": int(selection.get("selection_selected_events") or 0),
        "selection_top_reject_reason": selection.get("selection_top_reject_reason"),
        "selection_top_reject_reason_count": int(
            selection.get("selection_top_reject_reason_count") or 0
        ),
        "selection_analyzed_without_pick": max(
            int(selection.get("selection_passed_filters") or 0) - len({int(r["event_id"]) for r in rows}),
            0,
        ),
        "picks_total": total,
        "outcome_wins": wins,
        "outcome_losses": losses,
        "outcome_pending": pending,
        "picks_taken_count": taken_ct,
        "taken_outcome_wins": taken_wins,
        "taken_outcome_losses": taken_losses,
        "taken_outcome_pending": taken_pending,
        "not_taken_outcome_wins": not_taken_wins,
        "not_taken_outcome_losses": not_taken_losses,
        "not_taken_outcome_pending": not_taken_pending,
        "net_pl_estimate": round(net_pl, 2) if has_any_stake else None,
        "has_stake_data": has_any_stake,
    }


def recent_picks_for_date(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    user_id: Optional[int],
    limit: int = 12,
    sport: Optional[str] = None,
) -> List[sqlite3.Row]:
    sport_f = (
        str(sport).strip().lower()
        if sport is not None and str(sport).strip()
        else None
    )
    rows = _rows_for_date(
        conn, run_date=run_date, user_id=user_id, sport=sport_f
    )
    # ya ordenados por created_at desc en query — re-sort por si acaso
    sorted_rows = sorted(
        rows,
        key=lambda x: str(x["created_at_utc"] or ""),
        reverse=True,
    )
    return sorted_rows[:limit]

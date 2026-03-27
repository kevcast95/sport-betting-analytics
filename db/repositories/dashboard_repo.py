"""Agregados para el dashboard (picks = apuestas del modelo)."""

from __future__ import annotations

import glob
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


def _safe_float(v: Any) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _confidence_bucket(odds_reference_raw: Any) -> str:
    if not odds_reference_raw:
        return "sin_confianza"
    ref: Any = None
    if isinstance(odds_reference_raw, dict):
        ref = odds_reference_raw
    elif isinstance(odds_reference_raw, str):
        try:
            ref = json.loads(odds_reference_raw)
        except json.JSONDecodeError:
            ref = None
    if isinstance(ref, dict):
        c = ref.get("confianza")
        if c is not None and str(c).strip():
            return str(c).strip()
    return "sin_confianza"


def _edge_bucket(odds_reference_raw: Any) -> str:
    if not odds_reference_raw:
        return "sin_edge"
    ref: Any = None
    if isinstance(odds_reference_raw, dict):
        ref = odds_reference_raw
    elif isinstance(odds_reference_raw, str):
        try:
            ref = json.loads(odds_reference_raw)
        except json.JSONDecodeError:
            ref = None
    if not isinstance(ref, dict):
        return "sin_edge"
    e = _safe_float(ref.get("edge_pct"))
    if e is None:
        return "sin_edge"
    if e < 1.0:
        return "0-1%"
    if e < 2.0:
        return "1-2%"
    if e < 4.0:
        return "2-4%"
    return "4%+"


def _effective_outcome(u_outcome: Any, pr_outcome: Any) -> str:
    """Prioriza cierre declarado por el usuario; si no, resultado en pick_results."""
    if u_outcome in ("win", "loss", "pending"):
        return str(u_outcome)
    if pr_outcome in ("win", "loss"):
        return str(pr_outcome)
    if pr_outcome == "pending":
        return "pending"
    return "pending"


def _execution_slot_from_created_at_utc(created_at_utc: Any) -> tuple[str, str]:
    tz_name = os.environ.get("COPA_FOXKIDS_TZ", "America/Bogota")
    tz = ZoneInfo(tz_name)
    t = str(created_at_utc or "").strip()
    if not t:
        return "unknown", "sin franja"
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    dt = datetime.fromisoformat(t)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(tz)
    h = local.hour
    min_m = int(os.environ.get("ALTEA_VALIDATE_MORNING_HOUR_MIN", "8"))
    max_m = int(os.environ.get("ALTEA_VALIDATE_MORNING_HOUR_MAX_EXCL", "16"))
    min_e = int(os.environ.get("ALTEA_VALIDATE_AFTERNOON_HOUR_MIN", "16"))
    max_e = int(os.environ.get("ALTEA_VALIDATE_AFTERNOON_HOUR_MAX_EXCL", "24"))
    if min_m <= h < max_m:
        return "morning", "mañana"
    if min_e <= h < max_e:
        return "evening", "tarde/noche"
    return "night", "madrugada"


def _selection_stats_from_artifact(
    run_date: str, sport: Optional[str] = None
) -> Dict[str, Any]:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out_dir = os.path.join(repo_root, "out")
    s = str(sport).strip().lower() if sport else ""

    def _pick_top_reason(reasons: Dict[str, Any]) -> tuple[Optional[str], int]:
        top_reason: Optional[str] = None
        top_reason_count = 0
        for k, v in reasons.items():
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            if n > top_reason_count:
                top_reason = str(k)
                top_reason_count = n
        return top_reason, top_reason_count

    def _dict_from_one_file(data: Dict[str, Any]) -> Dict[str, Any]:
        reasons = data.get("rejection_reasons")
        reasons_d = reasons if isinstance(reasons, dict) else {}
        top_reason, top_reason_count = _pick_top_reason(reasons_d)
        selected = data.get("selected")
        selected_n = len(selected) if isinstance(selected, list) else 0
        return {
            "selection_total_events": int(data.get("total_events") or 0),
            "selection_passed_filters": int(data.get("passed_filters") or 0),
            "selection_rejected": int(data.get("rejected") or 0),
            "selection_top_reject_reason": top_reason,
            "selection_top_reject_reason_count": top_reason_count,
            "selection_selected_events": selected_n,
        }

    if s and s != "football":
        p = os.path.join(out_dir, f"candidates_{run_date}_select_{s}.json")
        if not os.path.exists(p):
            return {}
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}
        return _dict_from_one_file(data)

    paths: list[str] = []
    legacy = os.path.join(out_dir, f"candidates_{run_date}_select.json")
    if os.path.exists(legacy):
        paths.append(legacy)
    for p in sorted(glob.glob(os.path.join(out_dir, f"candidates_{run_date}_*_select.json"))):
        if p in paths:
            continue
        if s == "football" and p.endswith("_select_tennis.json"):
            continue
        paths.append(p)

    seen: set[str] = set()
    agg_reasons: Dict[str, int] = {}
    total_events = passed = rejected = 0
    selected_n = 0
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        total_events += int(data.get("total_events") or 0)
        passed += int(data.get("passed_filters") or 0)
        rejected += int(data.get("rejected") or 0)
        reasons = data.get("rejection_reasons")
        if isinstance(reasons, dict):
            for k, v in reasons.items():
                try:
                    agg_reasons[str(k)] = agg_reasons.get(str(k), 0) + int(v)
                except (TypeError, ValueError):
                    continue
        sel = data.get("selected")
        if isinstance(sel, list):
            selected_n += len(sel)

    top_reason = None
    top_reason_count = 0
    for k, v in agg_reasons.items():
        if v > top_reason_count:
            top_reason = k
            top_reason_count = v
    return {
        "selection_total_events": total_events,
        "selection_passed_filters": passed,
        "selection_rejected": rejected,
        "selection_top_reject_reason": top_reason,
        "selection_top_reject_reason_count": top_reason_count,
        "selection_selected_events": selected_n,
    }


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
                dr.created_at_utc AS run_created_at_utc,
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
            dr.created_at_utc AS run_created_at_utc,
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
    raw_floor = os.environ.get("ALTEA_MIN_TRADABLE_ODDS", "1.30").strip()
    try:
        min_tradable_odds = max(1.0, float(raw_floor))
    except ValueError:
        min_tradable_odds = 1.30
    sport_f = (
        str(sport).strip().lower()
        if sport is not None and str(sport).strip()
        else None
    )
    selection = _selection_stats_from_artifact(run_date, sport=sport_f)
    rows = _rows_for_date(
        conn, run_date=run_date, user_id=user_id, sport=sport_f
    )
    ef_sport_join = (
        "ef.captured_at_utc = dr.created_at_utc "
        "AND LOWER(TRIM(ef.sport)) = LOWER(TRIM(dr.sport))"
    )
    if sport_f:
        events_row = conn.execute(
            f"""
            SELECT COUNT(DISTINCT ef.event_id) AS n
            FROM daily_runs dr
            INNER JOIN event_features ef
              ON {ef_sport_join}
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
            f"""
            SELECT COUNT(DISTINCT ef.event_id) AS n
            FROM daily_runs dr
            INNER JOIN event_features ef
              ON {ef_sport_join}
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
    settled = 0
    profit_unit = 0.0
    settled_tradable = 0
    profit_unit_tradable = 0.0
    settled_below_min_odds = 0
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
            settled += 1
            pv = float(r["picked_value"]) if r["picked_value"] is not None else 0.0
            profit_unit += pv - 1.0
            if pv >= min_tradable_odds:
                settled_tradable += 1
                profit_unit_tradable += pv - 1.0
            else:
                settled_below_min_odds += 1
        elif eff == "loss":
            losses += 1
            settled += 1
            profit_unit += -1.0
            pv = float(r["picked_value"]) if r["picked_value"] is not None else 0.0
            if pv >= min_tradable_odds:
                settled_tradable += 1
                profit_unit_tradable += -1.0
            else:
                settled_below_min_odds += 1
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
        "settled_count": settled,
        "roi_unit": round(profit_unit / settled, 4) if settled > 0 else None,
        "settled_count_tradable": settled_tradable,
        "settled_count_below_min_odds": settled_below_min_odds,
        "min_tradable_odds": round(min_tradable_odds, 2),
        "roi_unit_tradable": (
            round(profit_unit_tradable / settled_tradable, 4)
            if settled_tradable > 0
            else None
        ),
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
    offset: int = 0,
    limit: int = 10,
    only_taken: bool = False,
    sport: Optional[str] = None,
) -> tuple[List[sqlite3.Row], int]:
    raw_floor = os.environ.get("ALTEA_MIN_TRADABLE_ODDS", "1.30").strip()
    try:
        min_tradable_odds = max(1.0, float(raw_floor))
    except ValueError:
        min_tradable_odds = 1.30

    def _is_tradable_row(row: sqlite3.Row) -> bool:
        pv_raw = row["picked_value"]
        pv = float(pv_raw) if pv_raw is not None else 0.0
        if pv >= min_tradable_odds:
            return True
        ref_raw = row["odds_reference"]
        if not ref_raw:
            return False
        try:
            ref = json.loads(str(ref_raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return False
        if isinstance(ref, dict):
            tv = ref.get("tradable")
            if isinstance(tv, bool):
                return tv
        return False

    sport_f = (
        str(sport).strip().lower()
        if sport is not None and str(sport).strip()
        else None
    )
    rows = _rows_for_date(
        conn, run_date=run_date, user_id=user_id, sport=sport_f
    )
    sorted_rows = sorted(
        rows,
        key=lambda x: str(x["created_at_utc"] or ""),
        reverse=True,
    )
    if only_taken:
        filtered = [r for r in sorted_rows if r["u_taken"] == 1]
    else:
        filtered = sorted_rows
    filtered = [r for r in filtered if _is_tradable_row(r)]
    total = len(filtered)
    page_rows = filtered[offset : offset + limit]
    return page_rows, total


def dashboard_insights(
    conn: sqlite3.Connection,
    *,
    run_date: str,
    sport: str,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    if user_id is None:
        rows = list(
            conn.execute(
                """
                SELECT
                    p.pick_id,
                    d.sport,
                    d.run_date,
                    p.market,
                    p.picked_value,
                    p.odds_reference,
                    r.outcome,
                    NULL AS u_taken
                FROM picks p
                INNER JOIN daily_runs d ON d.daily_run_id = p.daily_run_id
                INNER JOIN pick_results r ON r.pick_id = p.pick_id
                WHERE r.outcome IN ('win','loss')
                  AND d.run_date <= ?
                """,
                (run_date,),
            ).fetchall()
        )
    else:
        rows = list(
            conn.execute(
                """
                SELECT
                    p.pick_id,
                    d.sport,
                    d.run_date,
                    p.market,
                    p.picked_value,
                    p.odds_reference,
                    r.outcome,
                    ud.taken AS u_taken
                FROM picks p
                INNER JOIN daily_runs d ON d.daily_run_id = p.daily_run_id
                INNER JOIN pick_results r ON r.pick_id = p.pick_id
                LEFT JOIN user_pick_decisions ud
                  ON ud.pick_id = p.pick_id AND ud.user_id = ?
                WHERE r.outcome IN ('win','loss')
                  AND d.run_date <= ?
                """,
                (user_id, run_date),
            ).fetchall()
        )

    raw_floor = os.environ.get("ALTEA_MIN_TRADABLE_ODDS", "1.30").strip()
    try:
        min_tradable_odds = max(1.0, float(raw_floor))
    except ValueError:
        min_tradable_odds = 1.30

    def _roi(items: List[sqlite3.Row]) -> Optional[float]:
        if not items:
            return None
        prof = 0.0
        for rr in items:
            pv = float(rr["picked_value"]) if rr["picked_value"] is not None else 0.0
            if rr["outcome"] == "win":
                prof += pv - 1.0
            else:
                prof += -1.0
        return round(prof / len(items), 4)

    def _hit(items: List[sqlite3.Row]) -> Optional[float]:
        if not items:
            return None
        wins = sum(1 for rr in items if rr["outcome"] == "win")
        return round(wins / len(items), 4)

    def _tradable(items: List[sqlite3.Row]) -> List[sqlite3.Row]:
        out: List[sqlite3.Row] = []
        for rr in items:
            pv = float(rr["picked_value"]) if rr["picked_value"] is not None else 0.0
            if pv >= min_tradable_odds:
                out.append(rr)
        return out

    def _drawdown_units(items: List[sqlite3.Row]) -> float:
        eq = peak = 0.0
        max_dd = 0.0
        for rr in sorted(items, key=lambda x: str(x["run_date"])):
            pv = float(rr["picked_value"]) if rr["picked_value"] is not None else 0.0
            delta = (pv - 1.0) if rr["outcome"] == "win" else -1.0
            eq += delta
            if eq > peak:
                peak = eq
            dd = peak - eq
            if dd > max_dd:
                max_dd = dd
        return round(max_dd, 2)

    sport_norm = str(sport).strip().lower()
    rows_sport = [r for r in rows if str(r["sport"]).strip().lower() == sport_norm]

    if user_id is None:
        issued_rows = list(
            conn.execute(
                """
                SELECT
                    d.run_date,
                    COUNT(*) AS picks_total,
                    SUM(
                        CASE
                            WHEN COALESCE(p.picked_value, 0) >= ? THEN 1
                            ELSE 0
                        END
                    ) AS picks_tradable
                FROM picks p
                INNER JOIN daily_runs d ON d.daily_run_id = p.daily_run_id
                WHERE LOWER(TRIM(d.sport)) = ?
                  AND d.run_date <= ?
                GROUP BY d.run_date
                ORDER BY d.run_date ASC
                """,
                (min_tradable_odds, sport_norm, run_date),
            ).fetchall()
        )
    else:
        issued_rows = list(
            conn.execute(
                """
                SELECT
                    d.run_date,
                    COUNT(*) AS picks_total,
                    SUM(
                        CASE
                            WHEN COALESCE(p.picked_value, 0) >= ? THEN 1
                            ELSE 0
                        END
                    ) AS picks_tradable,
                    SUM(
                        CASE
                            WHEN ud.taken = 1 THEN 1
                            ELSE 0
                        END
                    ) AS picks_taken
                FROM picks p
                INNER JOIN daily_runs d ON d.daily_run_id = p.daily_run_id
                LEFT JOIN user_pick_decisions ud
                  ON ud.pick_id = p.pick_id AND ud.user_id = ?
                WHERE LOWER(TRIM(d.sport)) = ?
                  AND d.run_date <= ?
                GROUP BY d.run_date
                ORDER BY d.run_date ASC
                """,
                (min_tradable_odds, user_id, sport_norm, run_date),
            ).fetchall()
        )
    issued_daily: List[Dict[str, Any]] = []
    for rr in issued_rows[-7:]:
        issued_daily.append(
            {
                "run_date": str(rr["run_date"]),
                "picks_total": int(rr["picks_total"] or 0),
                "picks_tradable": int(rr["picks_tradable"] or 0),
                "picks_taken": int(rr["picks_taken"] or 0)
                if "picks_taken" in rr.keys()
                else None,
            }
        )

    rolling_by_sport: List[Dict[str, Any]] = []
    for sp in ("football", "tennis"):
        rs = [r for r in rows if str(r["sport"]).strip().lower() == sp]
        rt = _tradable(rs)
        rolling_by_sport.append(
            {
                "sport": sp,
                "settled_total": len(rs),
                "settled_tradable": len(rt),
                "roi_tradable_50": _roi(rt[-50:]) if rt else None,
                "roi_tradable_100": _roi(rt[-100:]) if rt else None,
                "hit_rate_tradable_50": _hit(rt[-50:]) if rt else None,
                "hit_rate_tradable_100": _hit(rt[-100:]) if rt else None,
                "drawdown_units_30d": _drawdown_units(rt),
            }
        )

    conf_groups: Dict[str, List[sqlite3.Row]] = {}
    conf_groups_taken: Dict[str, List[sqlite3.Row]] = {}
    edge_groups: Dict[str, List[sqlite3.Row]] = {}
    day_groups: Dict[str, List[sqlite3.Row]] = {}
    for rr in rows_sport:
        rr_pv = float(rr["picked_value"]) if rr["picked_value"] is not None else 0.0
        if rr_pv < min_tradable_odds:
            continue
        d = str(rr["run_date"])
        day_groups.setdefault(d, []).append(rr)
        c = _confidence_bucket(rr["odds_reference"])
        conf_groups.setdefault(c, []).append(rr)
        if rr["u_taken"] == 1:
            conf_groups_taken.setdefault(c, []).append(rr)
        e = _edge_bucket(rr["odds_reference"])
        edge_groups.setdefault(e, []).append(rr)

    confidence_rows: List[Dict[str, Any]] = []
    for b in sorted(conf_groups.keys()):
        items = conf_groups[b]
        confidence_rows.append(
            {
                "bucket": b,
                "settled": len(items),
                "hit_rate": _hit(items),
                "roi_unit": _roi(items),
            }
        )

    edge_order = {"0-1%": 0, "1-2%": 1, "2-4%": 2, "4%+": 3, "sin_edge": 4}
    confidence_taken_rows: List[Dict[str, Any]] = []
    for b in sorted(conf_groups_taken.keys()):
        items = conf_groups_taken[b]
        confidence_taken_rows.append(
            {
                "bucket": b,
                "settled": len(items),
                "hit_rate": _hit(items),
                "roi_unit": _roi(items),
            }
        )
    edge_rows: List[Dict[str, Any]] = []
    for b in sorted(edge_groups.keys(), key=lambda x: edge_order.get(x, 99)):
        items = edge_groups[b]
        edge_rows.append(
            {
                "bucket": b,
                "settled": len(items),
                "hit_rate": _hit(items),
                "roi_unit": _roi(items),
            }
        )
    daily_trend: List[Dict[str, Any]] = []
    for d in sorted(day_groups.keys())[-14:]:
        items = day_groups[d]
        daily_trend.append(
            {
                "run_date": d,
                "settled": len(items),
                "hit_rate": _hit(items),
                "roi_unit": _roi(items),
            }
        )

    return {
        "issued_daily": issued_daily,
        "rolling_by_sport": rolling_by_sport,
        "calibration": {
            "sport": sport_norm,
            "min_tradable_odds": round(min_tradable_odds, 2),
            "by_confidence": confidence_rows,
            "by_confidence_taken": confidence_taken_rows,
            "by_edge": edge_rows,
            "daily_trend": daily_trend,
        },
    }

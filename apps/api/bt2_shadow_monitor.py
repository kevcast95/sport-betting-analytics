"""
Monitor shadow BT2 (subset5) — lectura separada de `bt2_daily_picks`.

Fuente principal: SQL real sobre `bt2_shadow_*`.
Fallback opcional: artefactos de laboratorio (`scripts/outputs/bt2_vendor_lab_day1`).
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

_repo = Path(__file__).resolve().parents[2]
LAB_DIR = _repo / "scripts" / "outputs" / "bt2_vendor_lab_day1"


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _extract_decimal_and_selection(summary: str) -> tuple[Optional[float], Optional[str]]:
    # Ejemplo: "Everton:6.25;Liverpool:1.48;Draw:4.7"
    s = (summary or "").strip()
    if not s:
        return None, None
    first = s.split(";")[0].strip()
    if ":" not in first:
        return None, None
    sel, dec = first.split(":", 1)
    return _safe_float(dec.strip()), sel.strip() or None


def _build_shadow_monitor_payload_from_artifacts(
    *,
    operating_day_key_from: str,
    operating_day_key_to: str,
    rows_limit: int = 1500,
    rows_offset: int = 0,
    search: Optional[str] = None,
    market_substring: Optional[str] = None,
    classification_filter: Optional[str] = None,
) -> dict[str, Any]:
    lim = max(1, min(int(rows_limit or 1500), 3000))
    off = max(0, int(rows_offset or 0))
    q = (search or "").strip().lower()
    market_q = (market_substring or "").strip().lower()
    class_q = (classification_filter or "").strip().lower()

    manifest_rows = _read_csv(LAB_DIR / "day1_lab_manifest.csv")
    match_rows = _read_csv(LAB_DIR / "toa_event_matching_results.csv")
    odds_rows = _read_csv(LAB_DIR / "toa_h2h_t60_results.csv")
    cmp_rows = _read_csv(LAB_DIR / "bt2_vs_toa_exploration.csv")
    credit_json = {}
    if (LAB_DIR / "toa_credit_usage_summary.json").is_file():
        try:
            credit_json = json.loads((LAB_DIR / "toa_credit_usage_summary.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            credit_json = {}

    match_by_fixture = {str(r.get("sm_fixture_id", "")): r for r in match_rows}
    odds_by_fixture = {str(r.get("sm_fixture_id", "")): r for r in odds_rows}
    vp_by_fixture = {str(r.get("sm_fixture_id", "")): r for r in cmp_rows}

    rows_all: list[dict[str, Any]] = []
    for m in manifest_rows:
        fid = str(m.get("sm_fixture_id", "")).strip()
        if not fid:
            continue
        match = match_by_fixture.get(fid, {})
        odds = odds_by_fixture.get(fid, {})
        vp = vp_by_fixture.get(fid, {})

        kickoff = str(m.get("kickoff_utc") or "")
        op_day = kickoff[:10] if len(kickoff) >= 10 else ""
        if op_day and (op_day < operating_day_key_from or op_day > operating_day_key_to):
            continue

        cls = str(odds.get("classification") or match.get("classification") or "request_error")
        dec, sel = _extract_decimal_and_selection(str(odds.get("outcomes_decimal_summary") or ""))
        fixture_label = f"{m.get('home_team_sm') or '?'} vs {m.get('away_team_sm') or '?'}"
        market = str(m.get("market") or "h2h")
        dsr_src = "historical_sm_lbu_t60" if str(vp.get("value_pool_recomputed_sm_lbu_t60") or "") != "" else "unknown"
        status_shadow = "ready_for_shadow_pick" if cls == "matched_with_odds_t60" else "needs_review"

        row = {
            "operating_day_key": op_day,
            "bt2_event_id": int(m.get("bt2_event_id") or 0),
            "sm_fixture_id": int(fid),
            "fixture_event_label": fixture_label,
            "league_name": str(m.get("league_name") or ""),
            "market": market,
            "selection": sel,
            "status_shadow": status_shadow,
            "classification_taxonomy": cls,
            "decimal_odds": dec,
            "provider_source": "the_odds_api_historical_h2h",
            "provider_snapshot_time": str(odds.get("provider_snapshot_time") or ""),
            "provider_last_update": str(odds.get("provider_last_update") or ""),
            "ingested_at": str(odds.get("ingested_at") or ""),
            "region": str(m.get("region") or "us"),
            "snapshot_time_t60": str(m.get("snapshot_time_t60") or ""),
            "dsr_source": dsr_src,
            "value_pool_pass": str(vp.get("value_pool_recomputed_sm_lbu_t60") or ""),
            "toa_event_id": str(match.get("toa_event_id") or ""),
            "match_notes": str(match.get("match_notes") or ""),
            "raw_payload_summary": str(odds.get("payload_summary") or "")[:1200],
            "evaluation_status": None,
            "evaluation_reason": None,
            "result_score_text": None,
        }
        if q:
            blob = " ".join(
                [
                    row["fixture_event_label"],
                    row["league_name"],
                    row["selection"] or "",
                    row["classification_taxonomy"],
                ]
            ).lower()
            if q not in blob:
                continue
        if market_q and market_q not in market.lower():
            continue
        if class_q and class_q != "all" and class_q != row["classification_taxonomy"]:
            continue
        rows_all.append(row)

    rows_total = len(rows_all)
    rows_page = rows_all[off : off + lim]

    fixtures_seen = len(rows_all)
    fixtures_matched = sum(1 for r in rows_all if r.get("toa_event_id"))
    matched_with_odds = sum(1 for r in rows_all if r["classification_taxonomy"] == "matched_with_odds_t60")
    matched_without_odds = sum(
        1 for r in rows_all if r["classification_taxonomy"] == "matched_without_odds_t60"
    )
    unmatched_event = sum(1 for r in rows_all if r["classification_taxonomy"] == "unmatched_event")
    fixtures_with_h2h_t60 = matched_with_odds
    credits_used = _safe_float(credit_json.get("estimated_total_cost_from_headers_sum")) or 0.0
    vp_values = [
        str(r.get("value_pool_pass")).lower()
        for r in rows_all
        if str(r.get("value_pool_pass")).strip() != ""
    ]
    vp_true = sum(1 for x in vp_values if x == "true")
    value_pool_pass_rate = round(vp_true / len(vp_values), 6) if vp_values else 0.0
    match_rate = round(fixtures_matched / fixtures_seen, 6) if fixtures_seen else 0.0
    avg_credits = round(credits_used / fixtures_seen, 6) if fixtures_seen else 0.0

    today_key = date.today().isoformat()
    return {
        "mode": "shadow",
        "provider_stack": "sportmonks_fixture_master + theoddsapi_historical_h2h_t60",
        "timezone_label": "America/Bogota",
        "operating_day_key_from": operating_day_key_from,
        "operating_day_key_to": operating_day_key_to,
        "today_operating_day_key": today_key,
        "summary_human_es": (
            f"Shadow subset5 (rango {operating_day_key_from}..{operating_day_key_to}): "
            f"match_rate {round(match_rate*100, 2)}% · h2h_t60 {fixtures_with_h2h_t60}/{fixtures_seen} · "
            f"créditos {credits_used:.2f}"
        ),
        "kpis": {
            "fixtures_seen": fixtures_seen,
            "fixtures_matched": fixtures_matched,
            "match_rate": match_rate,
            "fixtures_with_h2h_t60": fixtures_with_h2h_t60,
            "value_pool_pass_rate": value_pool_pass_rate,
            "shadow_picks_generated": fixtures_with_h2h_t60,
            "matched_with_odds_t60": matched_with_odds,
            "matched_without_odds_t60": matched_without_odds,
            "unmatched_event": unmatched_event,
            "credits_used": round(credits_used, 4),
            "avg_credits_per_fixture": avg_credits,
            "scored_picks": 0,
            "evaluated_hit": 0,
            "evaluated_miss": 0,
            "void_count": 0,
            "pending_result": 0,
            "no_evaluable": 0,
            "hit_rate_on_scored": 0.0,
            "roi_flat_stake_units": 0.0,
            "roi_flat_stake_pct": 0.0,
        },
        "rows_total": rows_total,
        "rows_offset": off,
        "rows_limit": lim,
        "rows": rows_page,
    }


def _build_shadow_monitor_payload_from_sql(
    cur: Any,
    *,
    operating_day_key_from: str,
    operating_day_key_to: str,
    rows_limit: int = 1500,
    rows_offset: int = 0,
    search: Optional[str] = None,
    market_substring: Optional[str] = None,
    classification_filter: Optional[str] = None,
    run_kind: Optional[str] = None,
    run_key: Optional[str] = None,
    group_by_run: bool = False,
) -> dict[str, Any]:
    lim = max(1, min(int(rows_limit or 1500), 3000))
    off = max(0, int(rows_offset or 0))
    params: list[Any] = [operating_day_key_from, operating_day_key_to]
    where = [
        "dp.operating_day_key >= %s",
        "dp.operating_day_key <= %s",
    ]
    run_kind_expr = (
        "CASE "
        "WHEN r.run_key LIKE 'shadow-daily-%%' THEN 'daily_shadow' "
        "WHEN r.run_key LIKE 'shadow-subset5-backfill-%%' THEN 'backfill_window' "
        "WHEN r.run_key LIKE 'shadow-subset5-recovery-%%' THEN 'backfill_window' "
        "WHEN r.run_key LIKE 'shadow-subset5-day1-%%' THEN 'day1_lab' "
        "ELSE 'other' END"
    )
    sq = (search or "").strip()
    if sq:
        where.append(
            "("
            "COALESCE(ht.name, '') ILIKE %s OR "
            "COALESCE(at.name, '') ILIKE %s OR "
            "COALESCE(lg.name, '') ILIKE %s OR "
            "COALESCE(dp.classification_taxonomy, '') ILIKE %s"
            ")"
        )
        like = f"%{sq}%"
        params.extend([like, like, like, like])
    ms = (market_substring or "").strip()
    if ms:
        where.append("COALESCE(dp.market, '') ILIKE %s")
        params.append(f"%{ms}%")
    cf = (classification_filter or "").strip()
    if cf and cf != "all":
        where.append("COALESCE(dp.classification_taxonomy, '') = %s")
        params.append(cf)
    rk = (run_key or "").strip()
    if rk:
        where.append("COALESCE(r.run_key,'') = %s")
        params.append(rk)
    rkind = (run_kind or "").strip()
    if rkind:
        where.append(f"{run_kind_expr} = %s")
        params.append(rkind)
    where_sql = " AND ".join(where)

    cur.execute(
        f"""
        SELECT COUNT(*)::int AS c
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
        LEFT JOIN bt2_events ev ON ev.id = dp.bt2_event_id
        LEFT JOIN bt2_teams ht ON ht.id = ev.home_team_id
        LEFT JOIN bt2_teams at ON at.id = ev.away_team_id
        LEFT JOIN bt2_leagues lg ON lg.id = dp.league_id
        WHERE {where_sql}
        """,
        tuple(params),
    )
    crow = cur.fetchone()
    rows_total = int(crow.get("c") or 0) if crow else 0

    cur.execute(
        f"""
        SELECT
            COALESCE(r.run_key, '') AS run_key,
            COALESCE(r.selection_source, '') AS selection_source,
            dp.operating_day_key,
            COALESCE(dp.bt2_event_id, 0) AS bt2_event_id,
            COALESCE(dp.sm_fixture_id, 0) AS sm_fixture_id,
            COALESCE(
                NULLIF(ht.name, ''),
                NULLIF(ps.raw_payload->>'home_team_sm', ''),
                NULLIF(pi.payload_json->'manifest_row'->>'home_team_sm', ''),
                '?'
            ) AS home_team,
            COALESCE(
                NULLIF(at.name, ''),
                NULLIF(ps.raw_payload->>'away_team_sm', ''),
                NULLIF(pi.payload_json->'manifest_row'->>'away_team_sm', ''),
                '?'
            ) AS away_team,
            COALESCE(lg.name, 'Unknown') AS league_name,
            COALESCE(dp.market, 'h2h') AS market,
            dp.selection,
            COALESCE(dp.status_shadow, '') AS status_shadow,
            COALESCE(dp.classification_taxonomy, '') AS classification_taxonomy,
            dp.decimal_odds,
            COALESCE(dp.dsr_model, '') AS dsr_model,
            COALESCE(dp.dsr_prompt_version, '') AS dsr_prompt_version,
            COALESCE(dp.dsr_parse_status, '') AS dsr_parse_status,
            COALESCE(dp.dsr_failure_reason, '') AS dsr_failure_reason,
            COALESCE(dp.dsr_raw_summary_json->>'no_pick_reason', '') AS dsr_no_pick_reason,
            COALESCE(dp.dsr_raw_summary_json->>'market_canonical', '') AS dsr_market_canonical,
            COALESCE(dp.dsr_raw_summary_json->>'selection_canonical', '') AS dsr_selection_canonical,
            COALESCE(dp.dsr_raw_summary_json->>'selected_team', '') AS dsr_selected_team,
            COALESCE(dp.dsr_raw_summary_json->>'narrative_excerpt', '') AS dsr_response_excerpt,
            COALESCE(dp.dsr_raw_summary_json->>'confidence_label', '') AS dsr_confidence_label,
            COALESCE(dp.dsr_source, '') AS dsr_source,
            COALESCE(ps.provider_source, '') AS provider_source,
            ps.provider_snapshot_time,
            ps.provider_last_update,
            ps.ingested_at,
            COALESCE(ps.region, 'us') AS region,
            COALESCE(ps.raw_payload->>'snapshot_time_t60', '') AS snapshot_time_t60,
            COALESCE(ps.raw_payload->>'value_pool_pass', '') AS value_pool_pass,
            COALESCE(ps.raw_payload->>'toa_event_id', '') AS toa_event_id,
            COALESCE(ps.raw_payload->>'match_notes', '') AS match_notes,
            COALESCE(ps.raw_payload->>'payload_summary', '') AS raw_payload_summary,
            COALESCE(pe.eval_status, '') AS evaluation_status,
            COALESCE(pe.evaluation_reason, '') AS evaluation_reason,
            COALESCE(pe.eval_notes, '') AS evaluation_notes,
            pe.result_home AS result_home,
            pe.result_away AS result_away
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
        LEFT JOIN bt2_events ev ON ev.id = dp.bt2_event_id
        LEFT JOIN bt2_teams ht ON ht.id = ev.home_team_id
        LEFT JOIN bt2_teams at ON at.id = ev.away_team_id
        LEFT JOIN bt2_leagues lg ON lg.id = dp.league_id
        LEFT JOIN bt2_shadow_provider_snapshots ps ON ps.id = dp.provider_snapshot_id
        LEFT JOIN bt2_shadow_pick_inputs pi ON pi.shadow_daily_pick_id = dp.id
        LEFT JOIN bt2_shadow_pick_eval pe ON pe.shadow_daily_pick_id = dp.id
        WHERE {where_sql}
        ORDER BY dp.operating_day_key DESC, dp.id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params + [lim, off]),
    )
    raw_rows = cur.fetchall() or []
    rows = []
    for r in raw_rows:
        fixture_event_label = f"{r.get('home_team') or '?'} vs {r.get('away_team') or '?'}"
        ev_status = str(r.get("evaluation_status") or "").strip()
        has_score = r.get("result_home") is not None and r.get("result_away") is not None
        eval_notes = str(r.get("evaluation_notes") or "")
        if eval_notes.lower().find("manual") >= 0:
            settlement_stage = "cierre_manual_auditado"
        elif ev_status in {"hit", "miss", "void", "no_evaluable"}:
            settlement_stage = "cierre_oficial"
        elif ev_status == "pending_result" and has_score:
            settlement_stage = "resultado_visible_no_oficial"
        elif ev_status == "pending_result":
            settlement_stage = "pending_recheck"
        else:
            settlement_stage = "pending_recheck"
        rows.append(
            {
                "run_key": str(r.get("run_key") or ""),
                "selection_source": str(r.get("selection_source") or "") or None,
                "operating_day_key": str(r.get("operating_day_key") or ""),
                "bt2_event_id": int(r.get("bt2_event_id") or 0),
                "sm_fixture_id": int(r.get("sm_fixture_id") or 0),
                "fixture_event_label": fixture_event_label,
                "league_name": str(r.get("league_name") or ""),
                "market": str(r.get("market") or "h2h"),
                "selection": r.get("selection"),
                "status_shadow": str(r.get("status_shadow") or ""),
                "classification_taxonomy": str(r.get("classification_taxonomy") or ""),
                "decimal_odds": _safe_float(r.get("decimal_odds")),
                "dsr_model": str(r.get("dsr_model") or "") or None,
                "dsr_prompt_version": str(r.get("dsr_prompt_version") or "") or None,
                "dsr_parse_status": str(r.get("dsr_parse_status") or "") or None,
                "dsr_failure_reason": str(r.get("dsr_failure_reason") or "") or None,
                "dsr_no_pick_reason": str(r.get("dsr_no_pick_reason") or "") or None,
                "dsr_market_canonical": str(r.get("dsr_market_canonical") or "") or None,
                "dsr_selection_canonical": str(r.get("dsr_selection_canonical") or "") or None,
                "dsr_selected_team": str(r.get("dsr_selected_team") or "") or None,
                "dsr_response_excerpt": str(r.get("dsr_response_excerpt") or "") or None,
                "dsr_confidence_label": str(r.get("dsr_confidence_label") or "") or None,
                "provider_source": str(r.get("provider_source") or ""),
                "provider_snapshot_time": (
                    r.get("provider_snapshot_time").isoformat() if r.get("provider_snapshot_time") else None
                ),
                "provider_last_update": (
                    r.get("provider_last_update").isoformat() if r.get("provider_last_update") else None
                ),
                "ingested_at": r.get("ingested_at").isoformat() if r.get("ingested_at") else None,
                "region": str(r.get("region") or "us"),
                "snapshot_time_t60": str(r.get("snapshot_time_t60") or ""),
                "dsr_source": str(r.get("dsr_source") or "") or None,
                "value_pool_pass": str(r.get("value_pool_pass") or "") or None,
                "toa_event_id": str(r.get("toa_event_id") or "") or None,
                "match_notes": str(r.get("match_notes") or "") or None,
                "raw_payload_summary": str(r.get("raw_payload_summary") or "")[:1200] or None,
                "evaluation_status": str(r.get("evaluation_status") or "") or None,
                "evaluation_reason": str(r.get("evaluation_reason") or "") or None,
                "settlement_stage": settlement_stage,
                "result_score_text": (
                    f"{int(r.get('result_home'))}-{int(r.get('result_away'))}"
                    if r.get("result_home") is not None and r.get("result_away") is not None
                    else None
                ),
            }
        )

    cur.execute(
        f"""
        SELECT
            COUNT(*)::int AS fixtures_seen,
            COUNT(*) FILTER (WHERE COALESCE(ps.raw_payload->>'toa_event_id','') <> '')::int AS fixtures_matched,
            COUNT(*) FILTER (WHERE dp.classification_taxonomy = 'matched_with_odds_t60')::int AS matched_with_odds_t60,
            COUNT(*) FILTER (WHERE dp.classification_taxonomy = 'matched_without_odds_t60')::int AS matched_without_odds_t60,
            COUNT(*) FILTER (WHERE dp.classification_taxonomy = 'unmatched_event')::int AS unmatched_event,
            AVG(ps.credits_used)::float AS avg_credits_per_fixture,
            SUM(COALESCE(ps.credits_used, 0))::float AS credits_used,
            COUNT(*) FILTER (WHERE pe.eval_status IN ('hit','miss'))::int AS scored_picks,
            COUNT(*) FILTER (WHERE pe.eval_status = 'hit')::int AS evaluated_hit,
            COUNT(*) FILTER (WHERE pe.eval_status = 'miss')::int AS evaluated_miss,
            COUNT(*) FILTER (WHERE pe.eval_status = 'void')::int AS void_count,
            COUNT(*) FILTER (WHERE pe.eval_status = 'pending_result')::int AS pending_result,
            COUNT(*) FILTER (WHERE pe.eval_status = 'no_evaluable')::int AS no_evaluable,
            SUM(
                CASE
                    WHEN pe.eval_status = 'hit' AND pe.decimal_odds IS NOT NULL THEN pe.decimal_odds - 1.0
                    WHEN pe.eval_status = 'miss' THEN -1.0
                    ELSE 0.0
                END
            )::float AS roi_flat_stake_units
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
        LEFT JOIN bt2_shadow_provider_snapshots ps ON ps.id = dp.provider_snapshot_id
        LEFT JOIN bt2_shadow_pick_eval pe ON pe.shadow_daily_pick_id = dp.id
        WHERE {where_sql}
        """,
        tuple(params),
    )
    ag = cur.fetchone() or {}
    fixtures_seen = int(ag.get("fixtures_seen") or 0)
    fixtures_matched = int(ag.get("fixtures_matched") or 0)
    matched_with_odds = int(ag.get("matched_with_odds_t60") or 0)
    matched_without_odds = int(ag.get("matched_without_odds_t60") or 0)
    unmatched_event = int(ag.get("unmatched_event") or 0)
    credits_used = float(ag.get("credits_used") or 0.0)
    avg_credits = float(ag.get("avg_credits_per_fixture") or 0.0)
    match_rate = round(fixtures_matched / fixtures_seen, 6) if fixtures_seen else 0.0
    fixtures_with_h2h_t60 = matched_with_odds
    scored_picks = int(ag.get("scored_picks") or 0)
    evaluated_hit = int(ag.get("evaluated_hit") or 0)
    evaluated_miss = int(ag.get("evaluated_miss") or 0)
    void_count = int(ag.get("void_count") or 0)
    pending_result = int(ag.get("pending_result") or 0)
    no_evaluable = int(ag.get("no_evaluable") or 0)
    hit_rate_on_scored = round(evaluated_hit / scored_picks, 6) if scored_picks else 0.0
    roi_flat_stake_units = float(ag.get("roi_flat_stake_units") or 0.0)
    roi_flat_stake_pct = round((roi_flat_stake_units / scored_picks) * 100.0, 6) if scored_picks else 0.0

    cur.execute(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE ps.raw_payload->>'value_pool_pass' IN ('True','true'))::int AS vp_true,
            COUNT(*) FILTER (WHERE COALESCE(ps.raw_payload->>'value_pool_pass','') <> '')::int AS vp_total
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
        LEFT JOIN bt2_shadow_provider_snapshots ps ON ps.id = dp.provider_snapshot_id
        WHERE {where_sql}
        """,
        tuple(params),
    )
    vp = cur.fetchone() or {}
    vp_true = int(vp.get("vp_true") or 0)
    vp_total = int(vp.get("vp_total") or 0)
    value_pool_pass_rate = round(vp_true / vp_total, 6) if vp_total else 0.0

    run_groups: list[dict[str, Any]] = []
    if group_by_run:
        cur.execute(
            f"""
            SELECT
                r.run_key,
                {run_kind_expr} AS run_kind,
                MIN(dp.operating_day_key) AS day_from,
                MAX(dp.operating_day_key) AS day_to,
                COUNT(*)::int AS picks_count
            FROM bt2_shadow_daily_picks dp
            INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
            WHERE dp.operating_day_key >= %s AND dp.operating_day_key <= %s
            GROUP BY r.run_key
            ORDER BY MAX(r.created_at) DESC, r.run_key DESC
            """,
            (operating_day_key_from, operating_day_key_to),
        )
        for g in cur.fetchall() or []:
            run_groups.append(
                {
                    "runKey": str(g.get("run_key") or ""),
                    "runKind": str(g.get("run_kind") or "other"),
                    "picksCount": int(g.get("picks_count") or 0),
                    "dayFrom": str(g.get("day_from") or ""),
                    "dayTo": str(g.get("day_to") or ""),
                }
            )

    today_key = date.today().isoformat()
    if rkind == "daily_shadow" and fixtures_seen == 0:
        summary_msg = "No hay corridas daily_shadow todavía."
    else:
        summary_msg = (
            f"Shadow subset5 (SQL real {operating_day_key_from}..{operating_day_key_to}): "
            f"match_rate {round(match_rate*100, 2)}% · h2h_t60 {fixtures_with_h2h_t60}/{fixtures_seen} · "
            f"créditos {credits_used:.2f}"
        )
    return {
        "mode": "shadow",
        "provider_stack": "sportmonks_fixture_master + theoddsapi_historical_h2h_t60",
        "timezone_label": "America/Bogota",
        "operating_day_key_from": operating_day_key_from,
        "operating_day_key_to": operating_day_key_to,
        "today_operating_day_key": today_key,
        "summary_human_es": summary_msg,
        "kpis": {
            "fixtures_seen": fixtures_seen,
            "fixtures_matched": fixtures_matched,
            "match_rate": match_rate,
            "fixtures_with_h2h_t60": fixtures_with_h2h_t60,
            "value_pool_pass_rate": value_pool_pass_rate,
            "shadow_picks_generated": fixtures_with_h2h_t60,
            "matched_with_odds_t60": matched_with_odds,
            "matched_without_odds_t60": matched_without_odds,
            "unmatched_event": unmatched_event,
            "credits_used": round(credits_used, 4),
            "avg_credits_per_fixture": round(avg_credits, 6),
            "scored_picks": scored_picks,
            "evaluated_hit": evaluated_hit,
            "evaluated_miss": evaluated_miss,
            "void_count": void_count,
            "pending_result": pending_result,
            "no_evaluable": no_evaluable,
            "hit_rate_on_scored": hit_rate_on_scored,
            "roi_flat_stake_units": round(roi_flat_stake_units, 4),
            "roi_flat_stake_pct": roi_flat_stake_pct,
        },
        "rows_total": rows_total,
        "rows_offset": off,
        "rows_limit": lim,
        "rows": rows,
        "run_groups": run_groups,
        "selected_run_kind": rkind or None,
        "selected_run_key": rk or None,
    }


def build_shadow_monitor_payload(
    cur: Any,
    *,
    operating_day_key_from: str,
    operating_day_key_to: str,
    rows_limit: int = 1500,
    rows_offset: int = 0,
    search: Optional[str] = None,
    market_substring: Optional[str] = None,
    classification_filter: Optional[str] = None,
    run_kind: Optional[str] = None,
    run_key: Optional[str] = None,
    group_by_run: bool = False,
    allow_artifacts_fallback: bool = False,
) -> dict[str, Any]:
    cur.execute("SELECT to_regclass('public.bt2_shadow_daily_picks') AS t")
    t = cur.fetchone() or {}
    if t.get("t"):
        return _build_shadow_monitor_payload_from_sql(
            cur,
            operating_day_key_from=operating_day_key_from,
            operating_day_key_to=operating_day_key_to,
            rows_limit=rows_limit,
            rows_offset=rows_offset,
            search=search,
            market_substring=market_substring,
            classification_filter=classification_filter,
            run_kind=run_kind,
            run_key=run_key,
            group_by_run=group_by_run,
        )
    if allow_artifacts_fallback:
        return _build_shadow_monitor_payload_from_artifacts(
            operating_day_key_from=operating_day_key_from,
            operating_day_key_to=operating_day_key_to,
            rows_limit=rows_limit,
            rows_offset=rows_offset,
            search=search,
            market_substring=market_substring,
            classification_filter=classification_filter,
        )
    return {
        "mode": "shadow",
        "provider_stack": "sportmonks_fixture_master + theoddsapi_historical_h2h_t60",
        "timezone_label": "America/Bogota",
        "operating_day_key_from": operating_day_key_from,
        "operating_day_key_to": operating_day_key_to,
        "today_operating_day_key": date.today().isoformat(),
        "summary_human_es": "Sin datos shadow persistidos en DB para el rango solicitado.",
        "kpis": {
            "fixtures_seen": 0,
            "fixtures_matched": 0,
            "match_rate": 0.0,
            "fixtures_with_h2h_t60": 0,
            "value_pool_pass_rate": 0.0,
            "shadow_picks_generated": 0,
            "matched_with_odds_t60": 0,
            "matched_without_odds_t60": 0,
            "unmatched_event": 0,
            "credits_used": 0.0,
            "avg_credits_per_fixture": 0.0,
            "scored_picks": 0,
            "evaluated_hit": 0,
            "evaluated_miss": 0,
            "void_count": 0,
            "pending_result": 0,
            "no_evaluable": 0,
            "hit_rate_on_scored": 0.0,
            "roi_flat_stake_units": 0.0,
            "roi_flat_stake_pct": 0.0,
        },
        "rows_total": 0,
        "rows_offset": rows_offset,
        "rows_limit": rows_limit,
        "rows": [],
        "run_groups": [],
        "selected_run_kind": (run_kind or "").strip() or None,
        "selected_run_key": (run_key or "").strip() or None,
    }


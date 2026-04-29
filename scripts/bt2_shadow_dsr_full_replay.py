#!/usr/bin/env python3
"""
Replay completo DSR sobre universo shadow DSR-ready (sin fallback).

- No toca tablas productivas.
- Persiste en carril separado `shadow_dsr_replay`.
- selection_source fijo: dsr_api_only.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_admin_backtest_replay import BLIND_LOT_OPERATING_DAY_KEY, blind_ds_input_item  # noqa: E402
from apps.api.bt2_dsr_contract import CONTRACT_VERSION_PUBLIC  # noqa: E402
from apps.api.bt2_dsr_deepseek import deepseek_suggest_batch_with_trace  # noqa: E402
from apps.api.bt2_dsr_ds_input_builder import (  # noqa: E402
    aggregated_odds_for_event_psycopg,
    apply_postgres_context_to_ds_item,
    build_ds_input_item,
)
from apps.api.bt2_dsr_odds_aggregation import consensus_decimal_for_canonical_pick, event_passes_value_pool  # noqa: E402
from apps.api.bt2_dsr_postprocess import postprocess_dsr_pick  # noqa: E402
from apps.api.bt2_settings import bt2_settings  # noqa: E402
from apps.api.bt2_value_pool import MIN_ODDS_DECIMAL_DEFAULT  # noqa: E402

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
SELECTION_SOURCE = "dsr_api_only"
RUN_FAMILY = "shadow_dsr_replay"
MODEL = "deepseek-v4-pro"
SUBSET5_SPORTMONKS = {8, 82, 301, 384, 564}
FROZEN_RUN_KEYS: tuple[str, ...] = (
    "shadow-subset5-backfill-2025-01-05",
    "shadow-subset5-recovery-2025-07-12",
    "shadow-subset5-backfill-2026-01",
    "shadow-subset5-backfill-2026-02",
    "shadow-subset5-backfill-2026-03",
    "shadow-subset5-backfill-2026-04",
)


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _is_void_status(status: str) -> bool:
    s = (status or "").strip().lower()
    return s in {
        "abandoned",
        "cancelled",
        "canceled",
        "postponed",
        "suspended",
        "interrupted",
        "deleted",
        "walkover",
    }


def _selection_side(selection: str, home: str, away: str) -> str | None:
    s = (selection or "").strip().lower()
    if not s:
        return None
    if s in {"draw", "empate", "x"}:
        return "draw"
    if s in {"home", "local", "1", (home or "").strip().lower()}:
        return "home"
    if s in {"away", "visitante", "2", (away or "").strip().lower()}:
        return "away"
    return None


def _evaluate_prediction(
    *,
    selection: str,
    home_name: str,
    away_name: str,
    event_status: str,
    result_home: Optional[int],
    result_away: Optional[int],
    decimal_odds: Optional[float],
) -> tuple[str, Optional[float]]:
    if _is_void_status(event_status):
        return ("void", None)
    if result_home is None or result_away is None:
        return ("pending_result", None)
    side = _selection_side(selection, home_name, away_name)
    if side is None:
        return ("no_evaluable", None)
    home_win = result_home > result_away
    away_win = result_away > result_home
    draw = result_home == result_away
    hit = (side == "home" and home_win) or (side == "away" and away_win) or (side == "draw" and draw)
    if hit:
        return ("hit", ((float(decimal_odds) - 1.0) if decimal_odds is not None else None))
    return ("miss", -1.0)


def _fetch_universe_rows(cur: Any) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            dp.id AS source_shadow_pick_id,
            dp.run_id AS source_run_id,
            sr.run_key AS source_run_key,
            dp.operating_day_key,
            dp.bt2_event_id,
            dp.sm_fixture_id,
            dp.league_id,
            COALESCE(l.sportmonks_id, 0) AS sm_league_id,
            COALESCE(l.name, '') AS league_name,
            dp.provider_snapshot_id
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs sr ON sr.id = dp.run_id
        LEFT JOIN bt2_leagues l ON l.id = dp.league_id
        WHERE (
            sr.run_key = ANY(%s)
            OR sr.run_key LIKE 'shadow-daily-%%'
        )
          AND dp.classification_taxonomy = 'matched_with_odds_t60'
          AND COALESCE(l.sportmonks_id, 0) = ANY(%s)
        ORDER BY dp.operating_day_key ASC, dp.id ASC
        """,
        (list(FROZEN_RUN_KEYS), list(SUBSET5_SPORTMONKS)),
    )
    return [dict(r) for r in (cur.fetchall() or [])]


def _load_event_row(cur: Any, event_id: int) -> Optional[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            e.id,
            e.kickoff_utc,
            e.status,
            e.result_home,
            e.result_away,
            COALESCE(l.name, '') AS league_name,
            l.country AS league_country,
            l.tier AS league_tier,
            COALESCE(th.name, '') AS home_team_name,
            COALESCE(ta.name, '') AS away_team_name,
            e.home_team_id,
            e.away_team_id,
            e.sportmonks_fixture_id
        FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE e.id = %s
        """,
        (event_id,),
    )
    r = cur.fetchone()
    return dict(r) if r else None


def _eligible_with_agg(cur: Any, universe_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible: list[dict[str, Any]] = []
    for r in universe_rows:
        eid = r.get("bt2_event_id")
        if not eid:
            continue
        er = _load_event_row(cur, int(eid))
        if not er:
            continue
        ko = er.get("kickoff_utc")
        if not isinstance(ko, datetime):
            continue
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        cutoff = ko - timedelta(minutes=60)
        agg, _ = aggregated_odds_for_event_psycopg(
            cur,
            int(eid),
            min_decimal=MIN_ODDS_DECIMAL_DEFAULT,
            odds_cutoff_utc=cutoff,
            skip_sfs_fusion=True,
        )
        if not event_passes_value_pool(agg, min_decimal=MIN_ODDS_DECIMAL_DEFAULT):
            continue
        eligible.append({**r, "_event": er, "_kickoff_utc": ko, "_agg": agg})
    return eligible


def _create_shadow_run(cur: Any, *, run_key: str, eligible: list[dict[str, Any]]) -> int:
    days = sorted({str(r.get("operating_day_key") or "") for r in eligible if r.get("operating_day_key")})
    d_from = days[0] if days else datetime.now(timezone.utc).date().isoformat()
    d_to = days[-1] if days else d_from
    cur.execute(
        """
        INSERT INTO bt2_shadow_runs (
            run_key, operating_day_key_from, operating_day_key_to, mode,
            provider_stack, is_shadow, run_family, selection_source, notes
        )
        VALUES (%s,%s,%s,'shadow',%s,true,%s,%s,%s)
        RETURNING id
        """,
        (
            run_key,
            d_from,
            d_to,
            "shadow_dsr_replay_deepseek_v4_pro_contract_v5",
            RUN_FAMILY,
            SELECTION_SOURCE,
            "full_universe_dsr_ready_replay_no_fallback",
        ),
    )
    return int(cur.fetchone()["id"])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dkey = (bt2_settings.deepseek_api_key or "").strip()
    if not dkey:
        raise SystemExit("Falta deepseek_api_key en settings/.env para ejecutar replay DSR completo.")

    run_key = f"shadow-dsr-replay-full-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    summary: dict[str, Any] = {
        "run_key": run_key,
        "selection_source": SELECTION_SOURCE,
        "run_family": RUN_FAMILY,
        "model": MODEL,
        "contract_version": CONTRACT_VERSION_PUBLIC,
        "frozen_run_keys": list(FROZEN_RUN_KEYS),
        "subset5_sportmonks_ids": sorted(SUBSET5_SPORTMONKS),
    }

    conn = psycopg2.connect(_dsn(), connect_timeout=20)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        universe = _fetch_universe_rows(cur)
        eligible = _eligible_with_agg(cur, universe)
        summary["universe_rows_matched_taxonomy"] = len(universe)
        summary["eligible_after_t60_value_pool"] = len(eligible)
        summary["universe_executed_with_dsr"] = len(eligible)

        run_id = _create_shadow_run(cur, run_key=run_key, eligible=eligible)

        configured_bs = max(1, int(getattr(bt2_settings, "bt2_dsr_batch_size", 15) or 15))
        bs = configured_bs
        total_prompt_tokens = 0
        total_completion_tokens = 0
        parse_status_counts = defaultdict(int)
        trace_samples: list[dict[str, Any]] = []
        dsr_rows: list[dict[str, Any]] = []

        prepared: list[dict[str, Any]] = []
        for r in eligible:
            er = r["_event"]
            eid = int(r["bt2_event_id"])
            ko = r["_kickoff_utc"]
            item = build_ds_input_item(
                event_id=eid,
                selection_tier="A",
                kickoff_utc=ko,
                event_status=str(er.get("status") or ""),
                league_name=str(er.get("league_name") or ""),
                country=er.get("league_country"),
                league_tier=str(er.get("league_tier") or "") or None,
                home_team=str(er.get("home_team_name") or ""),
                away_team=str(er.get("away_team_name") or ""),
                agg=r["_agg"],
                sfs_fusion_applied=False,
                sfs_fusion_synthetic_rows=0,
            )
            apply_postgres_context_to_ds_item(
                cur,
                item,
                event_id=eid,
                home_team_id=int(er["home_team_id"]) if er.get("home_team_id") is not None else None,
                away_team_id=int(er["away_team_id"]) if er.get("away_team_id") is not None else None,
                sportmonks_fixture_id=int(er["sportmonks_fixture_id"])
                if er.get("sportmonks_fixture_id") is not None
                else None,
                kickoff_utc=ko,
            )
            prepared.append({"row": r, "blind": blind_ds_input_item(item)})

        for i in range(0, len(prepared), bs):
            chunk = prepared[i : i + bs]
            ds_map, trace = deepseek_suggest_batch_with_trace(
                [c["blind"] for c in chunk],
                operating_day_key=BLIND_LOT_OPERATING_DAY_KEY,
                api_key=dkey,
                base_url=str(bt2_settings.bt2_dsr_deepseek_base_url),
                model=MODEL,
                timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
                max_retries=int(bt2_settings.bt2_dsr_max_retries),
            )
            usage = trace.usage or {}
            total_prompt_tokens += int(usage.get("prompt_tokens") or 0)
            total_completion_tokens += int(usage.get("completion_tokens") or 0)
            trace_samples.append(asdict(trace))

            for c in chunk:
                r0 = c["row"]
                er = r0["_event"]
                eid = int(r0["bt2_event_id"])
                raw = ds_map.get(eid)
                parse_status = ""
                failure_reason = ""
                market_canonical = ""
                selection_canonical = ""
                narrative = ""
                confidence_label = ""
                declared_odds: Optional[float] = None

                if raw is None:
                    parse_status = "dsr_failed"
                    failure_reason = trace.last_error or "deepseek_batch_degraded"
                else:
                    narrative, confidence_label, mmc, msc, declared_odds = raw
                    if mmc in ("", "UNKNOWN") or msc in ("", "unknown_side"):
                        parse_status = "dsr_empty_signal"
                        failure_reason = "no_canonical_pick"
                    else:
                        ppc = postprocess_dsr_pick(
                            narrative_es=narrative,
                            confidence_label=confidence_label,
                            market_canonical=mmc,
                            selection_canonical=msc,
                            model_declared_odds=declared_odds,
                            consensus=r0["_agg"].consensus,
                            market_coverage=r0["_agg"].market_coverage,
                            event_id=eid,
                            home_team=str(er.get("home_team_name") or ""),
                            away_team=str(er.get("away_team_name") or ""),
                        )
                        if not ppc:
                            parse_status = "dsr_postprocess_reject"
                            failure_reason = "postprocess_dsr_pick_returned_none"
                        else:
                            _n2, _c2, mmc_f, msc_f = ppc
                            if mmc_f != "FT_1X2":
                                parse_status = "dsr_non_h2h_canonical"
                                failure_reason = f"market={mmc_f}"
                            else:
                                parse_status = "ok"
                                market_canonical = mmc_f
                                selection_canonical = msc_f

                parse_status_counts[parse_status or "unknown"] += 1
                selection = None
                selected_side = None
                dec = None
                if parse_status == "ok":
                    if selection_canonical == "home":
                        selection = str(er.get("home_team_name") or "")
                        selected_side = "home"
                    elif selection_canonical == "away":
                        selection = str(er.get("away_team_name") or "")
                        selected_side = "away"
                    elif selection_canonical == "draw":
                        selection = "Draw"
                        selected_side = "draw"
                    dec = consensus_decimal_for_canonical_pick(
                        r0["_agg"].consensus,
                        market_canonical,
                        selection_canonical,
                    )

                cur.execute(
                    """
                    INSERT INTO bt2_shadow_daily_picks (
                        run_id, operating_day_key, bt2_event_id, sm_fixture_id, league_id,
                        market, selection, status_shadow, classification_taxonomy, decimal_odds, dsr_source,
                        dsr_parse_status, dsr_failure_reason, dsr_model, dsr_prompt_version, dsr_response_id,
                        dsr_usage_json, dsr_raw_summary_json, selected_side_canonical, provider_snapshot_id
                    )
                    VALUES (%s,%s,%s,%s,%s,'h2h',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        run_id,
                        r0["operating_day_key"],
                        int(r0["bt2_event_id"]) if r0.get("bt2_event_id") is not None else None,
                        int(r0["sm_fixture_id"]) if r0.get("sm_fixture_id") is not None else None,
                        int(r0["league_id"]) if r0.get("league_id") is not None else None,
                        selection,
                        ("ready_for_shadow_pick" if parse_status == "ok" else "needs_review"),
                        ("matched_with_odds_t60" if parse_status == "ok" else parse_status),
                        dec,
                        SELECTION_SOURCE,
                        parse_status,
                        failure_reason or None,
                        MODEL,
                        CONTRACT_VERSION_PUBLIC,
                        trace.response_id,
                        psycopg2.extras.Json(trace.usage or {}),
                        psycopg2.extras.Json(
                            {
                                "market_canonical": market_canonical,
                                "selection_canonical": selection_canonical,
                                "confidence_label": confidence_label,
                                "narrative_excerpt": (narrative or "")[:500],
                            }
                        ),
                        selected_side,
                        int(r0["provider_snapshot_id"]) if r0.get("provider_snapshot_id") is not None else None,
                    ),
                )
                new_pick_id = int(cur.fetchone()["id"])

                eval_status = "no_evaluable"
                roi_units = None
                if parse_status == "ok":
                    eval_status, roi_units = _evaluate_prediction(
                        selection=selection or "",
                        home_name=str(er.get("home_team_name") or ""),
                        away_name=str(er.get("away_team_name") or ""),
                        event_status=str(er.get("status") or ""),
                        result_home=(int(er["result_home"]) if er.get("result_home") is not None else None),
                        result_away=(int(er["result_away"]) if er.get("result_away") is not None else None),
                        decimal_odds=dec,
                    )
                cur.execute(
                    """
                    INSERT INTO bt2_shadow_pick_eval (
                        shadow_daily_pick_id, eval_status, classification_taxonomy, eval_notes,
                        evaluation_reason, evaluated_at, truth_source, result_home, result_away,
                        event_status, decimal_odds, roi_flat_stake_units
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (shadow_daily_pick_id) DO NOTHING
                    """,
                    (
                        new_pick_id,
                        eval_status,
                        ("matched_with_odds_t60" if parse_status == "ok" else parse_status),
                        f"run_key={run_key}",
                        f"dsr_parse_status={parse_status}",
                        datetime.now(timezone.utc),
                        "bt2_events_cdm_v1",
                        (int(er["result_home"]) if er.get("result_home") is not None else None),
                        (int(er["result_away"]) if er.get("result_away") is not None else None),
                        str(er.get("status") or ""),
                        dec,
                        roi_units,
                    ),
                )
                dsr_rows.append(
                    {
                        "run_key": run_key,
                        "league_name": str(r0.get("league_name") or ""),
                        "source_run_key": str(r0.get("source_run_key") or ""),
                        "source_shadow_pick_id": int(r0["source_shadow_pick_id"]),
                        "shadow_daily_pick_id": new_pick_id,
                        "operating_day_key": str(r0.get("operating_day_key") or ""),
                        "bt2_event_id": int(r0["bt2_event_id"]),
                        "parse_status": parse_status,
                        "eval_status": eval_status,
                        "roi_flat_stake_units": roi_units,
                        "decimal_odds": dec,
                    }
                )

        conn.commit()

        ok_total = int(parse_status_counts.get("ok", 0))
        scored = sum(1 for r in dsr_rows if r["eval_status"] in {"hit", "miss"})
        hit = sum(1 for r in dsr_rows if r["eval_status"] == "hit")
        miss = sum(1 for r in dsr_rows if r["eval_status"] == "miss")
        void = sum(1 for r in dsr_rows if r["eval_status"] == "void")
        pending_result = sum(1 for r in dsr_rows if r["eval_status"] == "pending_result")
        no_evaluable = sum(1 for r in dsr_rows if r["eval_status"] == "no_evaluable")
        roi_units = float(sum(float(r["roi_flat_stake_units"] or 0.0) for r in dsr_rows if r["eval_status"] in {"hit", "miss"}))
        hit_rate = (hit / scored) if scored else 0.0
        roi_pct = ((roi_units / scored) * 100.0) if scored else 0.0
        dsr_failed = int(parse_status_counts.get("dsr_failed", 0))
        prompts_built = len(eligible)
        evaluable = ok_total

        # baseline no-DSR, mismo slice elegible
        baseline_rows = []
        for r in eligible:
            er = r["_event"]
            cur.execute(
                """
                SELECT selection, decimal_odds
                FROM bt2_shadow_daily_picks
                WHERE id = %s
                """,
                (int(r["source_shadow_pick_id"]),),
            )
            br = cur.fetchone() or {}
            eval_status_b, roi_b = _evaluate_prediction(
                selection=str(br.get("selection") or ""),
                home_name=str(er.get("home_team_name") or ""),
                away_name=str(er.get("away_team_name") or ""),
                event_status=str(er.get("status") or ""),
                result_home=(int(er["result_home"]) if er.get("result_home") is not None else None),
                result_away=(int(er["result_away"]) if er.get("result_away") is not None else None),
                decimal_odds=(float(br["decimal_odds"]) if br.get("decimal_odds") is not None else None),
            )
            baseline_rows.append(
                {
                    "source_shadow_pick_id": int(r["source_shadow_pick_id"]),
                    "eval_status": eval_status_b,
                    "roi_flat_stake_units": roi_b,
                }
            )

        b_scored = sum(1 for r in baseline_rows if r["eval_status"] in {"hit", "miss"})
        b_hit = sum(1 for r in baseline_rows if r["eval_status"] == "hit")
        b_miss = sum(1 for r in baseline_rows if r["eval_status"] == "miss")
        b_void = sum(1 for r in baseline_rows if r["eval_status"] == "void")
        b_pending = sum(1 for r in baseline_rows if r["eval_status"] == "pending_result")
        b_no_eval = sum(1 for r in baseline_rows if r["eval_status"] == "no_evaluable")
        b_roi_units = float(sum(float(r["roi_flat_stake_units"] or 0.0) for r in baseline_rows if r["eval_status"] in {"hit", "miss"}))
        b_hit_rate = (b_hit / b_scored) if b_scored else 0.0
        b_roi_pct = ((b_roi_units / b_scored) * 100.0) if b_scored else 0.0

        summary["metrics"] = {
            "prompts_built": prompts_built,
            "dsr_failed": dsr_failed,
            "ok_total": ok_total,
            "evaluable": evaluable,
            "parse_status_counts": dict(parse_status_counts),
            "usage_prompt_tokens_sum": total_prompt_tokens,
            "usage_completion_tokens_sum": total_completion_tokens,
            "estimated_cost_usd": None,
            "picks_total": len(dsr_rows),
            "scored": scored,
            "hit": hit,
            "miss": miss,
            "void": void,
            "pending_result": pending_result,
            "no_evaluable": no_evaluable,
            "hit_rate_on_scored": round(hit_rate, 6),
            "roi_flat_stake_units": round(roi_units, 6),
            "roi_flat_stake_pct": round(roi_pct, 6),
            "baseline_non_dsr_same_slice": {
                "picks_total": len(baseline_rows),
                "scored": b_scored,
                "hit": b_hit,
                "miss": b_miss,
                "void": b_void,
                "pending_result": b_pending,
                "no_evaluable": b_no_eval,
                "hit_rate_on_scored": round(b_hit_rate, 6),
                "roi_flat_stake_units": round(b_roi_units, 6),
                "roi_flat_stake_pct": round(b_roi_pct, 6),
            },
        }
        summary["batch_traces_sample"] = trace_samples[:10]

        # Artefactos
        (OUT_DIR / "dsr_full_replay_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        with (OUT_DIR / "dsr_full_replay_by_run.csv").open("w", encoding="utf-8", newline="") as f:
            fn = [
                "run_key",
                "selection_source",
                "model",
                "contract_version",
                "universe_rows_matched_taxonomy",
                "eligible_after_t60_value_pool",
                "universe_executed_with_dsr",
                "prompts_built",
                "dsr_failed",
                "ok_total",
                "evaluable",
                "usage_prompt_tokens_sum",
                "usage_completion_tokens_sum",
                "picks_total",
                "scored",
                "hit",
                "miss",
                "void",
                "pending_result",
                "no_evaluable",
                "hit_rate_on_scored",
                "roi_flat_stake_units",
                "roi_flat_stake_pct",
            ]
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            w.writerow(
                {
                    "run_key": run_key,
                    "selection_source": SELECTION_SOURCE,
                    "model": MODEL,
                    "contract_version": CONTRACT_VERSION_PUBLIC,
                    "universe_rows_matched_taxonomy": summary["universe_rows_matched_taxonomy"],
                    "eligible_after_t60_value_pool": summary["eligible_after_t60_value_pool"],
                    "universe_executed_with_dsr": summary["universe_executed_with_dsr"],
                    **{k: summary["metrics"][k] for k in fn if k in summary["metrics"]},
                }
            )

        by_league: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "picks_total": 0,
                "scored": 0,
                "hit": 0,
                "miss": 0,
                "void": 0,
                "pending_result": 0,
                "no_evaluable": 0,
                "roi_flat_stake_units": 0.0,
            }
        )
        for r in dsr_rows:
            lg = r["league_name"] or "unknown"
            acc = by_league[lg]
            acc["picks_total"] += 1
            es = r["eval_status"]
            if es in {"hit", "miss"}:
                acc["scored"] += 1
            acc[es] = acc.get(es, 0) + 1
            if es in {"hit", "miss"} and r["roi_flat_stake_units"] is not None:
                acc["roi_flat_stake_units"] += float(r["roi_flat_stake_units"])

        with (OUT_DIR / "dsr_full_replay_by_league.csv").open("w", encoding="utf-8", newline="") as f:
            fn = [
                "league_name",
                "picks_total",
                "scored",
                "hit",
                "miss",
                "void",
                "pending_result",
                "no_evaluable",
                "hit_rate_on_scored",
                "roi_flat_stake_units",
                "roi_flat_stake_pct",
            ]
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            for lg, acc in sorted(by_league.items(), key=lambda x: x[0]):
                scored_l = int(acc["scored"])
                hit_l = int(acc["hit"])
                roi_u = float(acc["roi_flat_stake_units"])
                w.writerow(
                    {
                        "league_name": lg,
                        "picks_total": acc["picks_total"],
                        "scored": scored_l,
                        "hit": hit_l,
                        "miss": acc["miss"],
                        "void": acc["void"],
                        "pending_result": acc["pending_result"],
                        "no_evaluable": acc["no_evaluable"],
                        "hit_rate_on_scored": round(hit_l / scored_l, 6) if scored_l else 0.0,
                        "roi_flat_stake_units": round(roi_u, 6),
                        "roi_flat_stake_pct": round((roi_u / scored_l) * 100.0, 6) if scored_l else 0.0,
                    }
                )

        with (OUT_DIR / "dsr_full_vs_non_dsr_eligible_slice.csv").open("w", encoding="utf-8", newline="") as f:
            fn = [
                "slice",
                "variant",
                "picks_total",
                "scored",
                "hit",
                "miss",
                "void",
                "pending_result",
                "no_evaluable",
                "hit_rate_on_scored",
                "roi_flat_stake_units",
                "roi_flat_stake_pct",
            ]
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            w.writerow(
                {
                    "slice": "same_dsr_ready_eligible",
                    "variant": "dsr_replay",
                    "picks_total": len(dsr_rows),
                    "scored": scored,
                    "hit": hit,
                    "miss": miss,
                    "void": void,
                    "pending_result": pending_result,
                    "no_evaluable": no_evaluable,
                    "hit_rate_on_scored": round(hit_rate, 6),
                    "roi_flat_stake_units": round(roi_units, 6),
                    "roi_flat_stake_pct": round(roi_pct, 6),
                }
            )
            w.writerow(
                {
                    "slice": "same_dsr_ready_eligible",
                    "variant": "baseline_non_dsr",
                    "picks_total": len(baseline_rows),
                    "scored": b_scored,
                    "hit": b_hit,
                    "miss": b_miss,
                    "void": b_void,
                    "pending_result": b_pending,
                    "no_evaluable": b_no_eval,
                    "hit_rate_on_scored": round(b_hit_rate, 6),
                    "roi_flat_stake_units": round(b_roi_units, 6),
                    "roi_flat_stake_pct": round(b_roi_pct, 6),
                }
            )

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    print(
        json.dumps(
            {
                "ok": True,
                "run_key": run_key,
                "out_dir": str(OUT_DIR.relative_to(ROOT)),
                "summary": "scripts/outputs/bt2_shadow_dsr_replay/dsr_full_replay_summary.json",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

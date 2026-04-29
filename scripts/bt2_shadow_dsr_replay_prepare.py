#!/usr/bin/env python3
"""
Preparación y piloto DSR (carril shadow, no productivo).

- Universo congelado: mismas run_key / shadow-daily que el baseline no-DSR.
- Selección oficial: dsr_api_only (DeepSeek vía `deepseek_suggest_batch_with_trace`).
- Sin rules_fallback / sql_stat_fallback: fallas explícitas.
- T-60: `odds_cutoff_utc = kickoff_utc - 60 min` al agregar `bt2_odds_snapshot` (mismo criterio que DSR CDM).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
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

from apps.api.bt2_admin_backtest_replay import (  # noqa: E402
    BLIND_LOT_OPERATING_DAY_KEY,
    blind_ds_input_item,
)
from apps.api.bt2_dsr_contract import CONTRACT_VERSION_PUBLIC  # noqa: E402
from apps.api.bt2_dsr_deepseek import deepseek_suggest_batch_with_trace  # noqa: E402
from apps.api.bt2_dsr_ds_input_builder import (  # noqa: E402
    aggregated_odds_for_event_psycopg,
    apply_postgres_context_to_ds_item,
    build_ds_input_item,
)
from apps.api.bt2_dsr_odds_aggregation import event_passes_value_pool  # noqa: E402
from apps.api.bt2_dsr_postprocess import postprocess_dsr_pick  # noqa: E402
from apps.api.bt2_settings import bt2_settings  # noqa: E402
from apps.api.bt2_value_pool import MIN_ODDS_DECIMAL_DEFAULT  # noqa: E402

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
SUBSET5_SPORTMONKS = {8, 82, 301, 384, 564}

# Universo congelado (no mezclar con interpretación ROI del baseline no-DSR).
FROZEN_RUN_KEYS: tuple[str, ...] = (
    "shadow-subset5-backfill-2025-01-05",
    "shadow-subset5-recovery-2025-07-12",
    "shadow-subset5-backfill-2026-01",
    "shadow-subset5-backfill-2026-02",
    "shadow-subset5-backfill-2026-03",
    "shadow-subset5-backfill-2026-04",
)

SELECTION_SOURCE = "dsr_api_only"
RUN_FAMILY = "shadow_dsr_replay"
DEFAULT_MODEL = "deepseek-v4-pro"


_ST_MARK = re.compile(r"\[selected_team\](.*?)\[/selected_team\]", re.DOTALL)
_NP_MARK = re.compile(r"\[no_pick_reason\](.*?)\[/no_pick_reason\]", re.DOTALL)


def _extract_marked(text: str, rx: re.Pattern[str]) -> str:
    m = rx.search(text or "")
    return (m.group(1) if m else "").strip()


def _normalize_str(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _infer_team_side_from_selected_team(*, selected_team: str, home_team: str, away_team: str) -> str:
    st = _normalize_str(selected_team)
    ht = _normalize_str(home_team)
    at = _normalize_str(away_team)
    if not st:
        return ""
    if st == ht:
        return "home"
    if st == at:
        return "away"
    return ""


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def _fetch_universe_rows(cur: Any) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            dp.id AS shadow_pick_id,
            sr.id AS shadow_run_id,
            sr.run_key,
            dp.operating_day_key,
            dp.bt2_event_id,
            dp.sm_fixture_id,
            l.sportmonks_id AS sm_league_id,
            l.name AS league_name
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs sr ON sr.id = dp.run_id
        LEFT JOIN bt2_leagues l ON l.id = dp.league_id
        WHERE (
            sr.run_key = ANY(%s)
            OR sr.run_key LIKE 'shadow-daily-%%'
        )
          AND dp.classification_taxonomy = 'matched_with_odds_t60'
          AND l.sportmonks_id = ANY(%s)
        ORDER BY dp.operating_day_key ASC, l.sportmonks_id ASC, dp.id ASC
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


def _odds_ok_t60(cur: Any, event_id: int, kickoff_utc: Optional[datetime]) -> bool:
    if kickoff_utc is None:
        return False
    ko = kickoff_utc
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    cutoff = ko - timedelta(minutes=60)
    agg, _fm = aggregated_odds_for_event_psycopg(
        cur,
        event_id,
        min_decimal=MIN_ODDS_DECIMAL_DEFAULT,
        odds_cutoff_utc=cutoff,
        skip_sfs_fusion=True,
    )
    return event_passes_value_pool(agg, min_decimal=MIN_ODDS_DECIMAL_DEFAULT)


def _stratified_sample(
    rows: list[dict[str, Any]], *, n: int, seed: int
) -> list[dict[str, Any]]:
    """Máxima dispersión por (sm_league_id, YYYY-MM)."""
    rng = random.Random(seed)
    buckets: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        yk = (r.get("operating_day_key") or "")[:7]  # YYYY-MM
        lid = int(r.get("sm_league_id") or 0)
        buckets[(yk, lid)].append(r)
    for k in buckets:
        rng.shuffle(buckets[k])
    keys = list(buckets.keys())
    rng.shuffle(keys)
    out: list[dict[str, Any]] = []
    round_idx = 0
    while len(out) < n and buckets:
        progressed = False
        for k in list(keys):
            if len(out) >= n:
                break
            b = buckets.get(k) or []
            if round_idx < len(b):
                out.append(b[round_idx])
                progressed = True
        if not progressed:
            break
        round_idx += 1
    if len(out) < n:
        rest = [x for x in rows if x not in out]
        rng.shuffle(rest)
        for x in rest:
            if len(out) >= n:
                break
            out.append(x)
    return out[:n]


def _load_fixed_sample_from_csv(
    rows_by_event: dict[int, dict[str, Any]], *, csv_path: Path
) -> list[dict[str, Any]]:
    if not csv_path.exists():
        return []
    out: list[dict[str, Any]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        for row in rd:
            try:
                eid = int(str(row.get("bt2_event_id") or "").strip())
            except (TypeError, ValueError):
                continue
            if eid in rows_by_event:
                out.append(rows_by_event[eid])
    return out


def _truth_hit(
    *,
    market_canonical: str,
    selection_canonical: str,
    rh: Optional[int],
    ra: Optional[int],
) -> Optional[bool]:
    if rh is None or ra is None:
        return None
    if market_canonical != "FT_1X2":
        return None
    if rh > ra:
        win = "home"
    elif ra > rh:
        win = "away"
    else:
        win = "draw"
    return selection_canonical == win


def main() -> None:
    ap = argparse.ArgumentParser(description="BT2 shadow — piloto DSR (dsr_api_only)")
    ap.add_argument("--sample-size", type=int, default=32, help="Filas objetivo (20–40 recomendado).")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", type=str, default="", help="Por defecto scripts/outputs/bt2_shadow_dsr_replay")
    ap.add_argument("--run-dsr", action="store_true", help="Invocar DeepSeek sobre la muestra (coste API real).")
    ap.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Modelo DeepSeek explícito.")
    ap.add_argument(
        "--dsr-batch-size",
        type=int,
        default=0,
        help="Override batch size DeepSeek para el piloto (0 = usar settings).",
    )
    ap.add_argument(
        "--fixed-sample-csv",
        type=str,
        default="scripts/outputs/bt2_shadow_dsr_replay/dsr_pilot_sample.csv",
        help="CSV de muestra fija a reutilizar (mismo orden).",
    )
    ap.add_argument(
        "--output-tag",
        type=str,
        default="",
        help="Sufijo opcional para artefactos, p.ej. after_fix.",
    )
    args = ap.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = psycopg2.connect(_dsn(), connect_timeout=15)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    eligible: list[dict[str, Any]] = []
    universe: list[dict[str, Any]] = []
    try:
        universe = _fetch_universe_rows(cur)
        for r in universe:
            eid = r.get("bt2_event_id")
            if not eid:
                continue
            er = _load_event_row(cur, int(eid))
            if not er:
                continue
            ko = er.get("kickoff_utc")
            if isinstance(ko, datetime) and ko.tzinfo is None:
                ko = ko.replace(tzinfo=timezone.utc)
            if not _odds_ok_t60(cur, int(eid), ko if isinstance(ko, datetime) else None):
                continue
            eligible.append({**r, "_kickoff_utc": ko, "_event_row": er})
    finally:
        cur.close()
        conn.close()

    n = max(20, min(int(args.sample_size), 40))
    by_event = {int(r["bt2_event_id"]): r for r in eligible if r.get("bt2_event_id") is not None}
    fixed_csv = (ROOT / str(args.fixed_sample_csv)).resolve()
    fixed_sample = _load_fixed_sample_from_csv(by_event, csv_path=fixed_csv)
    if fixed_sample:
        sample = fixed_sample[: min(n, len(fixed_sample))]
    else:
        sample = _stratified_sample(eligible, n=min(n, len(eligible)), seed=int(args.seed))

    pilot_csv = out_dir / "dsr_pilot_sample.csv"
    fields = [
        "shadow_pick_id",
        "run_key",
        "operating_day_key",
        "bt2_event_id",
        "sm_fixture_id",
        "sm_league_id",
        "league_name",
        "cdm_odds_t60_ok",
        "selection_source",
        "run_family",
    ]
    with pilot_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sample:
            w.writerow(
                {
                    "shadow_pick_id": r.get("shadow_pick_id"),
                    "run_key": r.get("run_key"),
                    "operating_day_key": r.get("operating_day_key"),
                    "bt2_event_id": r.get("bt2_event_id"),
                    "sm_fixture_id": r.get("sm_fixture_id"),
                    "sm_league_id": r.get("sm_league_id"),
                    "league_name": r.get("league_name"),
                    "cdm_odds_t60_ok": "true",
                    "selection_source": SELECTION_SOURCE,
                    "run_family": RUN_FAMILY,
                }
            )

    summary: dict[str, Any] = {
        "selection_source": SELECTION_SOURCE,
        "run_family": RUN_FAMILY,
        "frozen_run_keys": list(FROZEN_RUN_KEYS),
        "subset5_sportmonks_ids": sorted(SUBSET5_SPORTMONKS),
        "universe_rows_matched_taxonomy": len(universe),
        "eligible_after_t60_value_pool": len(eligible),
        "pilot_sample_size_requested": n,
        "pilot_sample_size_actual": len(sample),
        "dsr_prompt_version_contract": CONTRACT_VERSION_PUBLIC,
        "operating_day_key_batch": BLIND_LOT_OPERATING_DAY_KEY,
        "run_dsr_requested": bool(args.run_dsr),
        "model_requested": str(args.model or "").strip() or DEFAULT_MODEL,
        "dsr_batch_size_effective": None,
        "fixed_sample_csv": str(fixed_csv.relative_to(ROOT)) if fixed_csv.exists() else str(fixed_csv),
        "metrics": {},
    }

    pilot_results: list[dict[str, Any]] = []

    if args.run_dsr:
        dkey = (bt2_settings.deepseek_api_key or "").strip()
        if not dkey:
            summary["metrics"]["error"] = "missing_deepseek_api_key"
            summary_path = out_dir / "dsr_pilot_summary.json"
            summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
            raise SystemExit(
                "Falta DEEPSEEK_API_KEY / deepseek_api_key para --run-dsr "
                "(solo carril shadow; configure .env local)."
            )

        conn = psycopg2.connect(_dsn(), connect_timeout=15)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        prepared_blinds: list[dict[str, Any]] = []
        try:
            for r in sample:
                er = r["_event_row"]
                eid = int(r["bt2_event_id"])
                ko = r["_kickoff_utc"]
                cutoff = ko - timedelta(minutes=60)
                agg, _fm = aggregated_odds_for_event_psycopg(
                    cur,
                    eid,
                    min_decimal=MIN_ODDS_DECIMAL_DEFAULT,
                    odds_cutoff_utc=cutoff,
                    skip_sfs_fusion=True,
                )
                item = build_ds_input_item(
                    event_id=eid,
                    selection_tier="A",
                    kickoff_utc=ko if isinstance(ko, datetime) else None,
                    event_status=str(er.get("status") or ""),
                    league_name=str(er.get("league_name") or ""),
                    country=er.get("league_country"),
                    league_tier=str(er.get("league_tier") or "") or None,
                    home_team=str(er.get("home_team_name") or ""),
                    away_team=str(er.get("away_team_name") or ""),
                    agg=agg,
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
                    kickoff_utc=ko if isinstance(ko, datetime) else None,
                )
                blind = blind_ds_input_item(item)
                prepared_blinds.append(
                    {
                        "sample_row": r,
                        "agg": agg,
                        "blind": blind,
                        "home_team": str(er.get("home_team_name") or ""),
                        "away_team": str(er.get("away_team_name") or ""),
                    }
                )

            configured_bs = max(1, int(getattr(bt2_settings, "bt2_dsr_batch_size", 15) or 15))
            bs = max(1, int(args.dsr_batch_size)) if int(args.dsr_batch_size or 0) > 0 else configured_bs
            summary["dsr_batch_size_effective"] = bs
            total_prompt_tokens = 0
            total_completion_tokens = 0
            prompts_ok = 0
            parse_ok_events = 0
            evaluable_ft_1x2 = 0
            hits = 0
            misses = 0
            unresolved = 0
            status_counts = {
                "dsr_failed": 0,
                "dsr_empty_signal": 0,
                "dsr_postprocess_reject": 0,
                "dsr_non_h2h_canonical": 0,
                "ok": 0,
            }

            for i in range(0, len(prepared_blinds), bs):
                chunk = prepared_blinds[i : i + bs]
                blinds = [c["blind"] for c in chunk]
                ds_map, trace = deepseek_suggest_batch_with_trace(
                    blinds,
                    operating_day_key=BLIND_LOT_OPERATING_DAY_KEY,
                    api_key=dkey,
                    base_url=str(bt2_settings.bt2_dsr_deepseek_base_url),
                    model=str(args.model or "").strip() or DEFAULT_MODEL,
                    timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
                    max_retries=int(bt2_settings.bt2_dsr_max_retries),
                )
                usage = trace.usage or {}
                try:
                    total_prompt_tokens += int(usage.get("prompt_tokens") or 0)
                    total_completion_tokens += int(usage.get("completion_tokens") or 0)
                except (TypeError, ValueError):
                    pass

                for c in chunk:
                    prompts_ok += 1
                    r0 = c["sample_row"]
                    eid = int(r0["bt2_event_id"])
                    er = r0["_event_row"]
                    agg = c["agg"]
                    raw = ds_map.get(eid)

                    row_metric: dict[str, Any] = {
                        "bt2_event_id": eid,
                        "run_key": r0.get("run_key"),
                        "dsr_response_id": trace.response_id,
                        "parse_status": "",
                        "failure_reason": "",
                        "market_canonical": "",
                        "selection_canonical": "",
                        "raw_model_market": "",
                        "raw_model_selection": "",
                        "raw_selected_team": "",
                        "raw_no_pick_reason": "",
                        "empty_bucket": "",
                        "truth_hit": None,
                    }

                    if raw is None:
                        row_metric["parse_status"] = "dsr_failed"
                        row_metric["failure_reason"] = trace.last_error or "deepseek_batch_degraded"
                        status_counts["dsr_failed"] += 1
                        pilot_results.append(row_metric)
                        continue

                    narr, conf, mmc, msc, mod_o = raw
                    raw_selected_team = _extract_marked(narr, _ST_MARK)
                    raw_no_pick_reason = _extract_marked(narr, _NP_MARK)
                    row_metric["raw_model_market"] = mmc
                    row_metric["raw_model_selection"] = msc
                    row_metric["raw_selected_team"] = raw_selected_team
                    row_metric["raw_no_pick_reason"] = raw_no_pick_reason

                    if mmc in ("", "UNKNOWN") and msc in ("", "unknown_side"):
                        inferred = _infer_team_side_from_selected_team(
                            selected_team=raw_selected_team,
                            home_team=c["home_team"],
                            away_team=c["away_team"],
                        )
                        if inferred:
                            mmc = "FT_1X2"
                            msc = inferred
                            row_metric["empty_bucket"] = "recover_team_name_mapping"

                    if mmc in ("", "UNKNOWN") or msc in ("", "unknown_side"):
                        row_metric["parse_status"] = "dsr_empty_signal"
                        row_metric["failure_reason"] = "no_canonical_pick"
                        if not row_metric["empty_bucket"]:
                            if raw_no_pick_reason:
                                row_metric["empty_bucket"] = "explicit_model_abstention"
                            elif raw_selected_team:
                                row_metric["empty_bucket"] = "team_name_not_mappable"
                            elif mmc == "FT_1X2":
                                row_metric["empty_bucket"] = "market_ok_selection_missing"
                            else:
                                row_metric["empty_bucket"] = "no_structured_pick_fields"
                        status_counts["dsr_empty_signal"] += 1
                        pilot_results.append(row_metric)
                        continue

                    parse_ok_events += 1
                    ppc = postprocess_dsr_pick(
                        narrative_es=narr,
                        confidence_label=conf,
                        market_canonical=mmc,
                        selection_canonical=msc,
                        model_declared_odds=mod_o,
                        consensus=agg.consensus,
                        market_coverage=agg.market_coverage,
                        event_id=eid,
                        home_team=c["home_team"],
                        away_team=c["away_team"],
                    )
                    if not ppc:
                        row_metric["parse_status"] = "dsr_postprocess_reject"
                        row_metric["failure_reason"] = "postprocess_dsr_pick_returned_none"
                        status_counts["dsr_postprocess_reject"] += 1
                        pilot_results.append(row_metric)
                        continue

                    _n2, _c2, mmc_f, msc_f = ppc
                    row_metric["market_canonical"] = mmc_f
                    row_metric["selection_canonical"] = msc_f

                    if mmc_f != "FT_1X2":
                        row_metric["parse_status"] = "dsr_non_h2h_canonical"
                        row_metric["failure_reason"] = f"market={mmc_f} (piloto contract h2h→FT_1X2)"
                        status_counts["dsr_non_h2h_canonical"] += 1
                        pilot_results.append(row_metric)
                        continue

                    evaluable_ft_1x2 += 1
                    row_metric["parse_status"] = "ok"
                    status_counts["ok"] += 1
                    rh = er.get("result_home")
                    ra = er.get("result_away")
                    hit = _truth_hit(
                        market_canonical=mmc_f,
                        selection_canonical=msc_f,
                        rh=int(rh) if rh is not None else None,
                        ra=int(ra) if ra is not None else None,
                    )
                    row_metric["truth_hit"] = hit
                    if hit is None:
                        unresolved += 1
                    elif hit:
                        hits += 1
                    else:
                        misses += 1
                    pilot_results.append(row_metric)

            summary["metrics"] = {
                "prompts_built_ok": prompts_ok,
                "events_parseable_canonical": parse_ok_events,
                "evaluable_ft_1x2_after_postprocess": evaluable_ft_1x2,
                "truth_pending_or_non_ft": unresolved,
                "truth_hit_preliminary": hits,
                "truth_miss_preliminary": misses,
                "usage_prompt_tokens_sum": total_prompt_tokens,
                "usage_completion_tokens_sum": total_completion_tokens,
                "parse_status_counts": status_counts,
                "batch_traces_sample": asdict(trace) if prepared_blinds else {},
            }
        finally:
            cur.close()
            conn.close()

        details_name = "dsr_pilot_run_details.json"
        if str(args.output_tag or "").strip():
            details_name = f"dsr_pilot_run_details_{str(args.output_tag).strip()}.json"
        (out_dir / details_name).write_text(
            json.dumps(pilot_results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    summary_name = "dsr_pilot_summary.json"
    if str(args.output_tag or "").strip():
        summary_name = f"dsr_pilot_summary_{str(args.output_tag).strip()}.json"
    summary_path = out_dir / summary_name
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out_dir": str(out_dir.relative_to(ROOT)),
                "pilot_csv": str(pilot_csv.relative_to(ROOT)),
                "summary": str(summary_path.relative_to(ROOT)),
                "eligible": len(eligible),
                "sample": len(sample),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

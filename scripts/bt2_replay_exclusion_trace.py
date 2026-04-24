#!/usr/bin/env python3
"""
Trazabilidad read-only: primera causa de exclusión por evento en el funnel de replay BT2.

- Reutiliza el mismo SQL de candidatos, `bogota_operating_day_utc_window`,
  `_load_event_row_for_replay`, `aggregated_odds_for_event_psycopg` (corte + skip_sfs),
  `event_passes_value_pool`, `build_ds_input_item`, `apply_postgres_context_to_ds_item`,
  `_resolve_pick_tuple_from_dsr_or_fallback` (ds_out=None → SQL fallback) y
  `postprocess_dsr_pick` — sin DeepSeek ni rutas HTTP.

Uso (desde la raíz del repo):
  PYTHONPATH=. python3 scripts/bt2_replay_exclusion_trace.py \\
    --operating-day-from 2026-04-13 --operating-day-to 2026-04-19 --format json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Raíz repo en sys.path si se ejecuta como archivo
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import psycopg2
import psycopg2.extras

from apps.api.bt2_admin_backtest_replay import (  # noqa: E402
    USEFUL_INPUT_MIN_SCORE,
    _load_event_row_for_replay,
    _resolve_pick_tuple_from_dsr_or_fallback,
    bogota_operating_day_utc_window,
)
from apps.api.bt2_dsr_ds_input_builder import (  # noqa: E402
    apply_postgres_context_to_ds_item,
    build_ds_input_item,
    fetch_event_odds_rows_for_aggregation,
    aggregated_odds_for_event_psycopg,
)
from apps.api.bt2_dsr_odds_aggregation import (  # noqa: E402
    data_completeness_score,
    event_passes_value_pool,
)
from apps.api.bt2_dsr_postprocess import (  # noqa: E402
    narrative_contradicts_ft_1x2,
    postprocess_dsr_pick,
    _input_odds,
)
from apps.api.bt2_settings import bt2_settings  # noqa: E402
from apps.api.bt2_value_pool import MIN_ODDS_DECIMAL_DEFAULT  # noqa: E402


def _pg_dsn() -> str:
    u = bt2_settings.bt2_database_url
    if u.startswith("postgresql+asyncpg://"):
        return u.replace("postgresql+asyncpg://", "postgresql://", 1)
    return u


def _list_all_candidate_event_ids(cur: Any, day_start_utc: datetime, day_end_utc: datetime) -> list[int]:
    """Misma consulta que `_list_event_ids_for_replay_day` sin LIMIT (universo completo)."""
    cur.execute(
        """
        SELECT e.id
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        WHERE e.kickoff_utc >= %s
          AND e.kickoff_utc < %s
          AND l.is_active = true
          AND lower(coalesce(e.status, '')) NOT IN (
              'cancelled', 'canceled', 'postponed', 'abandoned', 'awarded'
          )
        ORDER BY
            CASE l.tier WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 ELSE 4 END ASC,
            e.kickoff_utc ASC
        """,
        (day_start_utc, day_end_utc),
    )
    return [int(r["id"]) for r in cur.fetchall()]


def _postprocess_omit_detail(
    *,
    narrative_es: str,
    confidence_label: str,
    market_canonical: str,
    selection_canonical: str,
    model_declared_odds: Optional[float],
    consensus: dict[str, Any],
    market_coverage: dict[str, Any],
    event_id: int,
    home_team: str,
    away_team: str,
) -> str:
    """Solo diagnóstico (no altera reglas); refleja orden de guardas en postprocess_dsr_pick."""
    if not market_canonical or market_canonical == "UNKNOWN":
        return "bad_market"
    if not selection_canonical or selection_canonical == "unknown_side":
        return "bad_selection"
    if not market_coverage.get(market_canonical):
        return "no_input_coverage"

    if market_canonical == "FT_1X2" and narrative_contradicts_ft_1x2(
        selection_canonical,
        narrative_es,
        home_team=home_team,
        away_team=away_team,
    ):
        return "incoherent_narrative_ft_1x2"
    if _input_odds(consensus, market_canonical, selection_canonical) is None:
        return "no_input_odds"
    return "unknown_none"


def classify_operating_day(
    cur: Any,
    *,
    operating_day_key: str,
    max_events_per_day: int,
    min_decimal: float,
) -> list[dict[str, Any]]:
    day_start_utc, day_end_utc = bogota_operating_day_utc_window(operating_day_key)
    odds_cutoff_utc = day_end_utc
    scan_limit = max(1, int(max_events_per_day) * 3)

    ordered = _list_all_candidate_event_ids(cur, day_start_utc, day_end_utc)
    scan_set = set(ordered[:scan_limit])

    rows_out: list[dict[str, Any]] = []
    prepared_count = 0

    for rank, eid in enumerate(ordered, start=1):
        base: dict[str, Any] = {
            "operating_day_key": operating_day_key,
            "event_id": eid,
            "candidate_rank": rank,
            "exclusion_reason": "",
            "detail": "",
            "odds_rows_before_cutoff": None,
            "data_completeness_score": None,
            "league_tier": None,
            "event_status": None,
        }

        if eid not in scan_set:
            base["exclusion_reason"] = "beyond_scan_cap"
            base["detail"] = json.dumps(
                {"scan_limit": scan_limit, "max_events_per_day": max_events_per_day},
                separators=(",", ":"),
            )
            rows_out.append(base)
            continue

        if prepared_count >= max_events_per_day:
            base["exclusion_reason"] = "prepare_cap_exhausted"
            base["detail"] = json.dumps(
                {"prepared_before_this_in_scan": max_events_per_day},
                separators=(",", ":"),
            )
            rows_out.append(base)
            continue

        er = _load_event_row_for_replay(cur, eid)
        if not er:
            base["exclusion_reason"] = "event_row_missing"
            base["detail"] = "{}"
            rows_out.append(base)
            continue

        base["league_tier"] = (str(er.get("league_tier") or "").strip().upper() or None)
        base["event_status"] = str(er.get("status") or "")

        snap_rows = fetch_event_odds_rows_for_aggregation(cur, eid, max_fetched_at=odds_cutoff_utc)
        base["odds_rows_before_cutoff"] = len(snap_rows)

        agg, _fm = aggregated_odds_for_event_psycopg(
            cur,
            eid,
            min_decimal=min_decimal,
            odds_cutoff_utc=odds_cutoff_utc,
            skip_sfs_fusion=True,
        )

        if not snap_rows:
            base["exclusion_reason"] = "no_odds_before_cutoff"
            base["detail"] = json.dumps(
                {"odds_cutoff_utc": odds_cutoff_utc.isoformat()},
                separators=(",", ":"),
            )
            rows_out.append(base)
            continue

        if not event_passes_value_pool(agg, min_decimal=min_decimal):
            dcs = data_completeness_score(agg)
            base["data_completeness_score"] = dcs
            base["exclusion_reason"] = "value_pool_fail"
            cov = {k: bool(v) for k, v in (agg.market_coverage or {}).items() if v or k in ("FT_1X2", "OU_GOALS_2_5", "BTTS")}
            base["detail"] = json.dumps(
                {
                    "market_coverage_true": cov,
                    "markets_available": list(agg.markets_available or [])[:12],
                },
                separators=(",", ":"),
            )
            rows_out.append(base)
            continue

        dcs = data_completeness_score(agg)
        base["data_completeness_score"] = dcs
        # Igual que `replay_single_operating_day`: el cupo `max_events` se consume al pasar value pool
        # (entrada a `prepared`), no al pasar postprocess.
        prepared_count += 1

        kickoff_utc = er.get("kickoff_utc")
        item = build_ds_input_item(
            event_id=eid,
            selection_tier="A",
            kickoff_utc=kickoff_utc if isinstance(kickoff_utc, datetime) else None,
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
            kickoff_utc=kickoff_utc if isinstance(kickoff_utc, datetime) else None,
        )

        narr, conf, mmc, msc, mod_o = _resolve_pick_tuple_from_dsr_or_fallback(
            event_id=eid,
            ds_out=None,
            agg=agg,
            league_name=str(er.get("league_name") or ""),
            home_team=str(er.get("home_team_name") or ""),
            away_team=str(er.get("away_team_name") or ""),
        )
        consensus = item["processed"]["odds_featured"]["consensus"]
        m_cov = item["diagnostics"]["market_coverage"]
        ctx = item["event_context"]
        ppc = postprocess_dsr_pick(
            narrative_es=narr,
            confidence_label=conf,
            market_canonical=mmc,
            selection_canonical=msc,
            model_declared_odds=mod_o,
            consensus=consensus,
            market_coverage=m_cov,
            event_id=eid,
            home_team=str(ctx.get("home_team") or ""),
            away_team=str(ctx.get("away_team") or ""),
        )
        if not ppc:
            base["exclusion_reason"] = "postprocess_omit"
            base["detail"] = json.dumps(
                {
                    "subreason": _postprocess_omit_detail(
                        narrative_es=narr,
                        confidence_label=conf,
                        market_canonical=mmc,
                        selection_canonical=msc,
                        model_declared_odds=mod_o,
                        consensus=consensus,
                        market_coverage=m_cov,
                        event_id=eid,
                        home_team=str(ctx.get("home_team") or ""),
                        away_team=str(ctx.get("away_team") or ""),
                    ),
                    "mmc": mmc,
                    "msc": msc,
                    "useful_input": dcs >= USEFUL_INPUT_MIN_SCORE,
                },
                separators=(",", ":"),
            )
            rows_out.append(base)
            continue

        base["exclusion_reason"] = "prepared_for_dsr"
        base["detail"] = json.dumps(
            {
                "useful_input": dcs >= USEFUL_INPUT_MIN_SCORE,
                "ds_path": "sql_fallback_no_llm",
            },
            separators=(",", ":"),
        )
        rows_out.append(base)

    return rows_out


def main() -> int:
    p = argparse.ArgumentParser(description="Trazabilidad exclusiones replay BT2 (read-only, sin LLM).")
    p.add_argument("--operating-day-from", required=True, help="YYYY-MM-DD inclusive (Bogota operating day).")
    p.add_argument("--operating-day-to", required=True, help="YYYY-MM-DD inclusive.")
    p.add_argument(
        "--max-events-per-day",
        type=int,
        default=None,
        help="Default: BT2_BACKTEST_MAX_EVENTS_PER_DAY del settings.",
    )
    p.add_argument("--format", choices=("json", "jsonl", "csv"), default="json")
    p.add_argument(
        "--output",
        default="",
        help="Archivo de salida (default: stdout).",
    )
    args = p.parse_args()

    d0 = date.fromisoformat(args.operating_day_from.strip())
    d1 = date.fromisoformat(args.operating_day_to.strip())
    if d0 > d1:
        print("operating-day-from > operating-day-to", file=sys.stderr)
        return 2

    max_ev = int(args.max_events_per_day) if args.max_events_per_day is not None else int(
        getattr(bt2_settings, "bt2_backtest_max_events_per_day", 20) or 20
    )
    min_dec = float(MIN_ODDS_DECIMAL_DEFAULT)

    conn = psycopg2.connect(_pg_dsn())
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    all_rows: list[dict[str, Any]] = []
    try:
        d = d0
        while d <= d1:
            all_rows.extend(
                classify_operating_day(
                    cur,
                    operating_day_key=d.isoformat(),
                    max_events_per_day=max_ev,
                    min_decimal=min_dec,
                )
            )
            d += timedelta(days=1)
    finally:
        cur.close()
        conn.close()

    summary = Counter(r["exclusion_reason"] for r in all_rows)
    meta = {
        "operating_day_from": d0.isoformat(),
        "operating_day_to": d1.isoformat(),
        "max_events_per_day": max_ev,
        "scan_limit_per_day": max(1, max_ev * 3),
        "row_count": len(all_rows),
        "summary_by_reason": dict(sorted(summary.items(), key=lambda x: (-x[1], x[0]))),
    }

    out_fp = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    try:
        if args.format == "json":
            json.dump({"meta": meta, "rows": all_rows}, out_fp, indent=2, default=str)
            out_fp.write("\n")
        elif args.format == "jsonl":
            out_fp.write(json.dumps({"type": "meta", **meta}, default=str) + "\n")
            for r in all_rows:
                out_fp.write(json.dumps(r, default=str) + "\n")
        else:
            w = csv.DictWriter(
                out_fp,
                fieldnames=[
                    "operating_day_key",
                    "event_id",
                    "candidate_rank",
                    "exclusion_reason",
                    "detail",
                    "odds_rows_before_cutoff",
                    "data_completeness_score",
                    "league_tier",
                    "event_status",
                ],
                extrasaction="ignore",
            )
            w.writeheader()
            for r in all_rows:
                w.writerow(r)
    finally:
        if args.output:
            out_fp.close()

    # Resumen en stderr para no mezclar con CSV/JSON piping
    print(json.dumps(meta, indent=2, default=str), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

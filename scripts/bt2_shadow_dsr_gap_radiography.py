#!/usr/bin/env python3
"""
Radiografía operacional del gap universo shadow -> DSR-ready.

Produce:
- scripts/outputs/bt2_shadow_dsr_replay/dsr_ready_gap_278_to_41.csv
- scripts/outputs/bt2_shadow_dsr_replay/dsr_ready_gap_summary.json
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_dsr_ds_input_builder import aggregated_odds_for_event_psycopg, fetch_event_odds_rows_for_aggregation  # noqa: E402
from apps.api.bt2_dsr_odds_aggregation import event_passes_value_pool  # noqa: E402
from apps.api.bt2_settings import bt2_settings  # noqa: E402
from apps.api.bt2_value_pool import MIN_ODDS_DECIMAL_DEFAULT  # noqa: E402

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
CSV_OUT = OUT_DIR / "dsr_ready_gap_278_to_41.csv"
JSON_OUT = OUT_DIR / "dsr_ready_gap_summary.json"

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


def _fetch_universe_rows(cur: Any) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            dp.id AS source_shadow_pick_id,
            sr.run_key AS source_run_key,
            dp.operating_day_key,
            dp.bt2_event_id,
            dp.sm_fixture_id,
            COALESCE(l.sportmonks_id, 0) AS sm_league_id,
            COALESCE(l.name, '') AS league_name
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
            e.home_team_id,
            e.away_team_id,
            COALESCE(th.name, '') AS home_team_name,
            COALESCE(ta.name, '') AS away_team_name
        FROM bt2_events e
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE e.id = %s
        """,
        (event_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = psycopg2.connect(_dsn(), connect_timeout=20)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        universe = _fetch_universe_rows(cur)
        rows_out: list[dict[str, Any]] = []
        causes = Counter()
        for r in universe:
            eid = r.get("bt2_event_id")
            out: dict[str, Any] = {
                "source_shadow_pick_id": int(r["source_shadow_pick_id"]),
                "source_run_key": str(r.get("source_run_key") or ""),
                "operating_day_key": str(r.get("operating_day_key") or ""),
                "bt2_event_id": int(eid) if eid is not None else 0,
                "sm_fixture_id": int(r["sm_fixture_id"]) if r.get("sm_fixture_id") is not None else 0,
                "sm_league_id": int(r["sm_league_id"]) if r.get("sm_league_id") is not None else 0,
                "league_name": str(r.get("league_name") or ""),
                "eligibility_status": "excluded",
                "exclusion_cause": "",
                "kickoff_utc": "",
                "event_status": "",
                "has_home_team": False,
                "has_away_team": False,
                "raw_odds_rows_t60": 0,
                "canonical_markets_available_count": 0,
                "canonical_markets_available": "",
                "covered_markets_count": 0,
                "covered_markets": "",
            }

            if not eid:
                out["exclusion_cause"] = "missing_bt2_event_id"
                causes[out["exclusion_cause"]] += 1
                rows_out.append(out)
                continue

            ev = _load_event_row(cur, int(eid))
            if not ev:
                out["exclusion_cause"] = "event_not_found_in_cdm"
                causes[out["exclusion_cause"]] += 1
                rows_out.append(out)
                continue

            ko = ev.get("kickoff_utc")
            out["event_status"] = str(ev.get("status") or "")
            out["has_home_team"] = bool(str(ev.get("home_team_name") or "").strip())
            out["has_away_team"] = bool(str(ev.get("away_team_name") or "").strip())
            if not isinstance(ko, datetime):
                out["exclusion_cause"] = "missing_kickoff_utc"
                causes[out["exclusion_cause"]] += 1
                rows_out.append(out)
                continue
            if ko.tzinfo is None:
                ko = ko.replace(tzinfo=timezone.utc)
            out["kickoff_utc"] = ko.isoformat()
            cutoff = ko - timedelta(minutes=60)

            raw_rows = fetch_event_odds_rows_for_aggregation(cur, int(eid), max_fetched_at=cutoff)
            out["raw_odds_rows_t60"] = len(raw_rows)
            if len(raw_rows) == 0:
                out["exclusion_cause"] = "no_local_snapshot_before_t60"
                causes[out["exclusion_cause"]] += 1
                rows_out.append(out)
                continue

            agg, _ = aggregated_odds_for_event_psycopg(
                cur,
                int(eid),
                min_decimal=MIN_ODDS_DECIMAL_DEFAULT,
                odds_cutoff_utc=cutoff,
                skip_sfs_fusion=True,
            )
            markets_available = sorted(list(agg.markets_available or []))
            covered_markets = sorted([k for k, v in (agg.market_coverage or {}).items() if bool(v)])
            out["canonical_markets_available_count"] = len(markets_available)
            out["canonical_markets_available"] = "|".join(markets_available)
            out["covered_markets_count"] = len(covered_markets)
            out["covered_markets"] = "|".join(covered_markets)

            if len(markets_available) == 0:
                out["exclusion_cause"] = "canonicalization_yielded_no_market"
                causes[out["exclusion_cause"]] += 1
                rows_out.append(out)
                continue

            if not event_passes_value_pool(agg, min_decimal=MIN_ODDS_DECIMAL_DEFAULT):
                out["exclusion_cause"] = "value_pool_failed_no_complete_market_family"
                causes[out["exclusion_cause"]] += 1
                rows_out.append(out)
                continue

            out["eligibility_status"] = "dsr_ready"
            out["exclusion_cause"] = "eligible_dsr_ready"
            causes[out["exclusion_cause"]] += 1
            rows_out.append(out)

        with CSV_OUT.open("w", encoding="utf-8", newline="") as f:
            fn = [
                "source_shadow_pick_id",
                "source_run_key",
                "operating_day_key",
                "bt2_event_id",
                "sm_fixture_id",
                "sm_league_id",
                "league_name",
                "eligibility_status",
                "exclusion_cause",
                "kickoff_utc",
                "event_status",
                "has_home_team",
                "has_away_team",
                "raw_odds_rows_t60",
                "canonical_markets_available_count",
                "canonical_markets_available",
                "covered_markets_count",
                "covered_markets",
            ]
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            for rr in rows_out:
                w.writerow({k: rr.get(k) for k in fn})

        total = len(rows_out)
        summary_rows = []
        for cause, n in sorted(causes.items(), key=lambda x: (-x[1], x[0])):
            summary_rows.append(
                {
                    "cause": cause,
                    "count": n,
                    "pct_over_total": round((n / total) * 100.0, 4) if total else 0.0,
                }
            )

        summary = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "frozen_run_keys": list(FROZEN_RUN_KEYS),
            "subset5_sportmonks_ids": sorted(SUBSET5_SPORTMONKS),
            "universe_rows_matched_taxonomy": total,
            "eligible_after_t60_value_pool": causes.get("eligible_dsr_ready", 0),
            "excluded_before_dsr": total - causes.get("eligible_dsr_ready", 0),
            "by_cause": summary_rows,
            "csv_path": str(CSV_OUT.relative_to(ROOT)),
        }
        JSON_OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    finally:
        cur.close()
        conn.close()

    print(
        json.dumps(
            {
                "ok": True,
                "csv": str(CSV_OUT.relative_to(ROOT)),
                "summary": str(JSON_OUT.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

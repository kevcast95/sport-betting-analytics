#!/usr/bin/env python3
"""
BT2 Phase 1 — data quality audit around replay, official evaluation and provider trust.

Purpose
-------
Answer this question before changing predictor logic:

    "¿BT2 predice mal o estamos midiendo mal por culpa de datos sucios/incompletos?"

Scope
-----
Read-only audit over the BT2 slice that directly affects replay, official evaluation,
and confidence in SportMonks / provider data:

1. bt2_events closure summary
2. pending lag by day
3. finished events without final score
4. official evaluation status summary
5. no_evaluable reason breakdown
6. quality by market_canonical
7. quality by tiers
8. raw SportMonks coverage vs bt2_events
9. provider odds coverage
10. SFS join quality
11. ds_input shadow coverage
12. bt2_odds_snapshot completeness

Design notes
------------
- Read-only: no schema changes, no writes to DB, no migrations.
- Runs from repo root.
- Reads BT2_DATABASE_URL from env or .env in repo root.
- Filters by event kickoff day in America/Bogota to keep one stable date lens across blocks.
- Writes review-friendly CSV and JSON artifacts into out/bt2_phase1_audit/<timestamp>/.

Usage
-----
From repo root:

    python3 scripts/bt2_phase1_data_audit.py --from 2026-04-12 --to 2026-04-19
    python3 scripts/bt2_phase1_data_audit.py --from 2026-04-12 --to 2026-04-19 \
      --providers sportmonks,sofascore --sample-limit 100

Expected environment
--------------------
- BT2_DATABASE_URL in env, or in repo-root .env
- psycopg2 available in the same environment used by the repo scripts
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence
from urllib.parse import urlsplit


REPO = Path(__file__).resolve().parents[1]
DEFAULT_TIMEZONE = "America/Bogota"
PENDING_STATUSES = ("scheduled", "live", "inplay", "in_play", "")
VOIDISH_STATUSES = ("cancelled", "canceled", "postponed", "abandoned")


@dataclass(frozen=True)
class BlockResult:
    name: str
    ok: bool
    files: list[str]
    summary: dict[str, Any]
    warning: Optional[str] = None


# ---------------------------------------------------------------------------
# Env / DB helpers
# ---------------------------------------------------------------------------


def _load_bt2_database_url() -> str:
    url = (os.environ.get("BT2_DATABASE_URL") or "").strip().strip('"').strip("'")
    if url:
        return url

    env_path = REPO / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("BT2_DATABASE_URL="):
                url = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    if not url:
        print("Falta BT2_DATABASE_URL en entorno o .env", file=sys.stderr)
        sys.exit(1)
    return url


def _sync_dsn(url: str) -> str:
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", url, flags=re.I)


def _sanitize_dsn(url: str) -> str:
    try:
        parsed = urlsplit(url)
        netloc = parsed.netloc
        if "@" in netloc:
            creds, host = netloc.rsplit("@", 1)
            user = creds.split(":", 1)[0]
            netloc = f"{user}:***@{host}"
        return f"{parsed.scheme}://{netloc}{parsed.path}"
    except Exception:
        return "postgresql://***"


# ---------------------------------------------------------------------------
# Serialization / file helpers
# ---------------------------------------------------------------------------


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (datetime, date)):
            out[key] = value.isoformat()
        elif isinstance(value, Decimal):
            out[key] = float(value)
        elif isinstance(value, (dict, list)):
            out[key] = json.dumps(value, ensure_ascii=False, default=_json_default)
        else:
            out[key] = value
    return out


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Optional[Sequence[str]] = None) -> None:
    normalized = [_normalize_row(r) for r in rows]
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in normalized:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(fieldnames or []))
        if fieldnames:
            writer.writeheader()
        for row in normalized:
            writer.writerow(row)


def _relative_to_repo(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------


def _fetchall(cur: Any, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    return [dict(r) if not isinstance(r, dict) else r for r in rows]


def _fetchone(cur: Any, sql: str, params: Sequence[Any] = ()) -> dict[str, Any]:
    cur.execute(sql, tuple(params))
    row = cur.fetchone()
    if row is None:
        return {}
    return dict(row) if not isinstance(row, dict) else row


def _providers_sql_filter(column_name: str, providers: Sequence[str]) -> tuple[str, list[Any]]:
    cleaned = [p.strip() for p in providers if p and p.strip()]
    if not cleaned:
        return "", []
    return f" AND {column_name} = ANY(%s) ", [cleaned]


def _base_events_cte() -> str:
    return f"""
    WITH base_events AS (
      SELECT
        e.id,
        e.sportmonks_fixture_id,
        e.sofascore_event_id,
        e.league_id,
        e.home_team_id,
        e.away_team_id,
        e.kickoff_utc,
        e.status,
        e.result_home,
        e.result_away,
        (e.kickoff_utc AT TIME ZONE '{DEFAULT_TIMEZONE}')::date AS event_day_local
      FROM bt2_events e
      WHERE e.kickoff_utc IS NOT NULL
        AND (e.kickoff_utc AT TIME ZONE '{DEFAULT_TIMEZONE}')::date BETWEEN %s AND %s
    )
    """


def _build_output_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = base / stamp
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


# ---------------------------------------------------------------------------
# Audit blocks
# ---------------------------------------------------------------------------


def block_01_closure_summary(cur: Any, date_from: str, date_to: str, outdir: Path) -> BlockResult:
    sql = _base_events_cte() + """
    SELECT
      event_day_local,
      COUNT(*)::int AS events_total,
      COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) = 'finished')::int AS status_finished,
      COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) = ANY(%s))::int AS status_pending_like,
      COUNT(*) FILTER (WHERE LOWER(COALESCE(status, '')) = ANY(%s))::int AS status_voidish,
      COUNT(*) FILTER (
        WHERE LOWER(COALESCE(status, '')) = 'finished'
          AND result_home IS NOT NULL
          AND result_away IS NOT NULL
      )::int AS finished_with_score,
      COUNT(*) FILTER (
        WHERE LOWER(COALESCE(status, '')) = 'finished'
          AND (result_home IS NULL OR result_away IS NULL)
      )::int AS finished_without_score,
      COUNT(*) FILTER (WHERE result_home IS NOT NULL AND result_away IS NOT NULL)::int AS events_with_any_score
    FROM base_events
    GROUP BY event_day_local
    ORDER BY event_day_local;
    """
    rows = _fetchall(cur, sql, [date_from, date_to, list(PENDING_STATUSES), list(VOIDISH_STATUSES)])

    overall_sql = _base_events_cte() + """
    SELECT
      LOWER(COALESCE(status, '')) AS status,
      COUNT(*)::int AS events_count,
      COUNT(*) FILTER (WHERE result_home IS NOT NULL AND result_away IS NOT NULL)::int AS events_with_score,
      COUNT(*) FILTER (WHERE result_home IS NULL OR result_away IS NULL)::int AS events_without_score
    FROM base_events
    GROUP BY LOWER(COALESCE(status, ''))
    ORDER BY events_count DESC, status;
    """
    overall_rows = _fetchall(cur, overall_sql, [date_from, date_to])

    files = []
    p1 = outdir / "01_bt2_events_closure_summary_by_day.csv"
    _write_csv(p1, rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "01_bt2_events_closure_status_breakdown.csv"
    _write_csv(p2, overall_rows)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "01_bt2_events_closure_summary.json"
    _write_json(p3, {"by_day": rows, "by_status": overall_rows})
    files.append(_relative_to_repo(p3))

    totals = Counter()
    for row in rows:
        totals.update({
            "events_total": int(row.get("events_total") or 0),
            "finished_without_score": int(row.get("finished_without_score") or 0),
            "status_pending_like": int(row.get("status_pending_like") or 0),
        })

    return BlockResult(
        name="closure_summary",
        ok=True,
        files=files,
        summary={
            "events_total": totals["events_total"],
            "finished_without_score": totals["finished_without_score"],
            "status_pending_like": totals["status_pending_like"],
        },
    )


def block_02_pending_lag(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int) -> BlockResult:
    sql = _base_events_cte() + """
    , pending_base AS (
      SELECT
        *,
        ROUND(EXTRACT(EPOCH FROM (NOW() - kickoff_utc)) / 3600.0, 2) AS age_hours,
        CASE
          WHEN LOWER(COALESCE(status, '')) = ANY(%s) THEN true
          WHEN LOWER(COALESCE(status, '')) = 'finished' AND (result_home IS NULL OR result_away IS NULL) THEN true
          WHEN LOWER(COALESCE(status, '')) NOT = ANY(%s) AND (result_home IS NULL OR result_away IS NULL) THEN true
          ELSE false
        END AS unresolved_flag
      FROM base_events
    )
    SELECT
      event_day_local,
      COUNT(*) FILTER (WHERE unresolved_flag)::int AS unresolved_events,
      COUNT(*) FILTER (WHERE unresolved_flag AND age_hours >= 12)::int AS unresolved_ge_12h,
      COUNT(*) FILTER (WHERE unresolved_flag AND age_hours >= 24)::int AS unresolved_ge_24h,
      COUNT(*) FILTER (WHERE unresolved_flag AND age_hours >= 48)::int AS unresolved_ge_48h,
      COUNT(*) FILTER (WHERE unresolved_flag AND age_hours >= 72)::int AS unresolved_ge_72h,
      ROUND(AVG(age_hours) FILTER (WHERE unresolved_flag), 2) AS avg_age_hours_unresolved,
      ROUND(MAX(age_hours) FILTER (WHERE unresolved_flag), 2) AS max_age_hours_unresolved
    FROM pending_base
    GROUP BY event_day_local
    ORDER BY event_day_local;
    """
    rows = _fetchall(
        cur,
        sql,
        [date_from, date_to, list(PENDING_STATUSES), list(VOIDISH_STATUSES)],
    )

    sample_sql = _base_events_cte() + """
    SELECT
      id AS event_id,
      sportmonks_fixture_id,
      sofascore_event_id,
      event_day_local,
      kickoff_utc,
      status,
      result_home,
      result_away,
      ROUND(EXTRACT(EPOCH FROM (NOW() - kickoff_utc)) / 3600.0, 2) AS age_hours
    FROM base_events
    WHERE (
      LOWER(COALESCE(status, '')) = ANY(%s)
      OR (LOWER(COALESCE(status, '')) = 'finished' AND (result_home IS NULL OR result_away IS NULL))
      OR (LOWER(COALESCE(status, '')) NOT = ANY(%s) AND (result_home IS NULL OR result_away IS NULL))
    )
    ORDER BY age_hours DESC NULLS LAST, kickoff_utc ASC
    LIMIT %s;
    """
    sample_rows = _fetchall(
        cur,
        sample_sql,
        [date_from, date_to, list(PENDING_STATUSES), list(VOIDISH_STATUSES), sample_limit],
    )

    files = []
    p1 = outdir / "02_pending_lag_by_day.csv"
    _write_csv(p1, rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "02_pending_lag_samples.csv"
    _write_csv(p2, sample_rows)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "02_pending_lag_summary.json"
    _write_json(p3, {"by_day": rows, "samples": sample_rows})
    files.append(_relative_to_repo(p3))

    unresolved = sum(int(r.get("unresolved_events") or 0) for r in rows)
    ge24 = sum(int(r.get("unresolved_ge_24h") or 0) for r in rows)
    ge72 = sum(int(r.get("unresolved_ge_72h") or 0) for r in rows)

    return BlockResult(
        name="pending_lag",
        ok=True,
        files=files,
        summary={
            "unresolved_events": unresolved,
            "unresolved_ge_24h": ge24,
            "unresolved_ge_72h": ge72,
            "sample_rows": len(sample_rows),
        },
    )


def block_03_finished_without_score(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int) -> BlockResult:
    summary_sql = _base_events_cte() + """
    SELECT
      event_day_local,
      COUNT(*)::int AS finished_without_score_count
    FROM base_events
    WHERE LOWER(COALESCE(status, '')) = 'finished'
      AND (result_home IS NULL OR result_away IS NULL)
    GROUP BY event_day_local
    ORDER BY event_day_local;
    """
    rows = _fetchall(cur, summary_sql, [date_from, date_to])

    sample_sql = _base_events_cte() + """
    SELECT
      id AS event_id,
      sportmonks_fixture_id,
      sofascore_event_id,
      event_day_local,
      kickoff_utc,
      status,
      result_home,
      result_away,
      ROUND(EXTRACT(EPOCH FROM (NOW() - kickoff_utc)) / 3600.0, 2) AS age_hours
    FROM base_events
    WHERE LOWER(COALESCE(status, '')) = 'finished'
      AND (result_home IS NULL OR result_away IS NULL)
    ORDER BY kickoff_utc ASC
    LIMIT %s;
    """
    sample_rows = _fetchall(cur, sample_sql, [date_from, date_to, sample_limit])

    files = []
    p1 = outdir / "03_finished_without_score_by_day.csv"
    _write_csv(p1, rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "03_finished_without_score_samples.csv"
    _write_csv(p2, sample_rows)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "03_finished_without_score_summary.json"
    _write_json(p3, {"by_day": rows, "samples": sample_rows})
    files.append(_relative_to_repo(p3))

    total = sum(int(r.get("finished_without_score_count") or 0) for r in rows)
    return BlockResult(
        name="finished_without_score",
        ok=True,
        files=files,
        summary={"finished_without_score": total, "sample_rows": len(sample_rows)},
    )


def block_04_evaluation_summary(cur: Any, date_from: str, date_to: str, outdir: Path) -> BlockResult:
    sql = _base_events_cte() + """
    SELECT
      be.event_day_local,
      COUNT(DISTINCT dp.id)::int AS suggested_picks_count,
      COUNT(DISTINCT oe.id)::int AS official_evaluation_rows,
      COUNT(DISTINCT dp.id) - COUNT(DISTINCT oe.id) AS missing_official_eval_rows,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'pending_result')::int AS pending_result,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_hit')::int AS evaluated_hit,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_miss')::int AS evaluated_miss,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'void')::int AS void_count,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'no_evaluable')::int AS no_evaluable,
      ROUND(
        100.0 * COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_hit')
        / NULLIF(
            COUNT(*) FILTER (WHERE oe.evaluation_status IN ('evaluated_hit', 'evaluated_miss')),
            0
          ),
        2
      ) AS hit_rate_on_scored_pct
    FROM base_events be
    LEFT JOIN bt2_daily_picks dp ON dp.event_id = be.id
    LEFT JOIN bt2_pick_official_evaluation oe ON oe.daily_pick_id = dp.id
    GROUP BY be.event_day_local
    ORDER BY be.event_day_local;
    """
    rows = _fetchall(cur, sql, [date_from, date_to])

    overall = {
        "suggested_picks_count": sum(int(r.get("suggested_picks_count") or 0) for r in rows),
        "official_evaluation_rows": sum(int(r.get("official_evaluation_rows") or 0) for r in rows),
        "pending_result": sum(int(r.get("pending_result") or 0) for r in rows),
        "evaluated_hit": sum(int(r.get("evaluated_hit") or 0) for r in rows),
        "evaluated_miss": sum(int(r.get("evaluated_miss") or 0) for r in rows),
        "void_count": sum(int(r.get("void_count") or 0) for r in rows),
        "no_evaluable": sum(int(r.get("no_evaluable") or 0) for r in rows),
        "missing_official_eval_rows": sum(int(r.get("missing_official_eval_rows") or 0) for r in rows),
    }
    scored = overall["evaluated_hit"] + overall["evaluated_miss"]
    overall["hit_rate_on_scored_pct"] = round(100.0 * overall["evaluated_hit"] / scored, 2) if scored else None

    files = []
    p1 = outdir / "04_official_evaluation_summary_by_day.csv"
    _write_csv(p1, rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "04_official_evaluation_summary.json"
    _write_json(p2, {"by_day": rows, "overall": overall})
    files.append(_relative_to_repo(p2))

    return BlockResult(name="evaluation_summary", ok=True, files=files, summary=overall)


def block_05_no_evaluable(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int) -> BlockResult:
    reason_sql = _base_events_cte() + """
    SELECT
      COALESCE(oe.no_evaluable_reason, '(sin código)') AS no_evaluable_reason,
      COUNT(*)::int AS picks_count
    FROM base_events be
    INNER JOIN bt2_daily_picks dp ON dp.event_id = be.id
    INNER JOIN bt2_pick_official_evaluation oe ON oe.daily_pick_id = dp.id
    WHERE oe.evaluation_status = 'no_evaluable'
    GROUP BY COALESCE(oe.no_evaluable_reason, '(sin código)')
    ORDER BY picks_count DESC, no_evaluable_reason;
    """
    reason_rows = _fetchall(cur, reason_sql, [date_from, date_to])

    market_sql = _base_events_cte() + """
    SELECT
      COALESCE(oe.market_canonical, '(null)') AS market_canonical,
      COALESCE(oe.no_evaluable_reason, '(sin código)') AS no_evaluable_reason,
      COUNT(*)::int AS picks_count
    FROM base_events be
    INNER JOIN bt2_daily_picks dp ON dp.event_id = be.id
    INNER JOIN bt2_pick_official_evaluation oe ON oe.daily_pick_id = dp.id
    WHERE oe.evaluation_status = 'no_evaluable'
    GROUP BY COALESCE(oe.market_canonical, '(null)'), COALESCE(oe.no_evaluable_reason, '(sin código)')
    ORDER BY picks_count DESC, market_canonical, no_evaluable_reason;
    """
    market_rows = _fetchall(cur, market_sql, [date_from, date_to])

    sample_sql = _base_events_cte() + """
    SELECT
      be.id AS event_id,
      be.sportmonks_fixture_id,
      be.sofascore_event_id,
      be.event_day_local,
      be.kickoff_utc,
      be.status AS event_status,
      be.result_home,
      be.result_away,
      dp.id AS daily_pick_id,
      dp.operating_day_key,
      dp.access_tier,
      dp.action_tier,
      oe.market_canonical,
      oe.selection_canonical,
      oe.no_evaluable_reason,
      oe.truth_source,
      oe.truth_payload_ref
    FROM base_events be
    INNER JOIN bt2_daily_picks dp ON dp.event_id = be.id
    INNER JOIN bt2_pick_official_evaluation oe ON oe.daily_pick_id = dp.id
    WHERE oe.evaluation_status = 'no_evaluable'
    ORDER BY oe.no_evaluable_reason NULLS LAST, be.kickoff_utc ASC
    LIMIT %s;
    """
    sample_rows = _fetchall(cur, sample_sql, [date_from, date_to, sample_limit])

    files = []
    p1 = outdir / "05_no_evaluable_breakdown.csv"
    _write_csv(p1, reason_rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "05_no_evaluable_by_market.csv"
    _write_csv(p2, market_rows)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "05_no_evaluable_samples.csv"
    _write_csv(p3, sample_rows)
    files.append(_relative_to_repo(p3))
    p4 = outdir / "05_no_evaluable_summary.json"
    _write_json(p4, {"by_reason": reason_rows, "by_market": market_rows, "samples": sample_rows})
    files.append(_relative_to_repo(p4))

    return BlockResult(
        name="no_evaluable_breakdown",
        ok=True,
        files=files,
        summary={
            "no_evaluable_total": sum(int(r.get("picks_count") or 0) for r in reason_rows),
            "top_reason": reason_rows[0]["no_evaluable_reason"] if reason_rows else None,
        },
    )


def block_06_market_quality(cur: Any, date_from: str, date_to: str, outdir: Path) -> BlockResult:
    sql = _base_events_cte() + """
    SELECT
      COALESCE(oe.market_canonical, dp.model_market_canonical, '(null)') AS market_canonical,
      COUNT(DISTINCT dp.id)::int AS suggested_picks_count,
      COUNT(DISTINCT oe.id)::int AS official_eval_rows,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'pending_result')::int AS pending_result,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_hit')::int AS evaluated_hit,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_miss')::int AS evaluated_miss,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'void')::int AS void_count,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'no_evaluable')::int AS no_evaluable,
      ROUND(
        100.0 * COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_hit')
        / NULLIF(COUNT(*) FILTER (WHERE oe.evaluation_status IN ('evaluated_hit', 'evaluated_miss')), 0),
        2
      ) AS hit_rate_on_scored_pct
    FROM base_events be
    INNER JOIN bt2_daily_picks dp ON dp.event_id = be.id
    LEFT JOIN bt2_pick_official_evaluation oe ON oe.daily_pick_id = dp.id
    GROUP BY COALESCE(oe.market_canonical, dp.model_market_canonical, '(null)')
    ORDER BY suggested_picks_count DESC, market_canonical;
    """
    rows = _fetchall(cur, sql, [date_from, date_to])
    p1 = outdir / "06_market_canonical_quality.csv"
    _write_csv(p1, rows)
    p2 = outdir / "06_market_canonical_quality.json"
    _write_json(p2, rows)
    return BlockResult(
        name="market_quality",
        ok=True,
        files=[_relative_to_repo(p1), _relative_to_repo(p2)],
        summary={"markets": len(rows)},
    )


def block_07_tier_quality(cur: Any, date_from: str, date_to: str, outdir: Path) -> BlockResult:
    combo_sql = _base_events_cte() + """
    SELECT
      COALESCE(dp.access_tier, '(null)') AS access_tier,
      COALESCE(dp.action_tier, '(null)') AS action_tier,
      COUNT(DISTINCT dp.id)::int AS suggested_picks_count,
      COUNT(DISTINCT oe.id)::int AS official_eval_rows,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'pending_result')::int AS pending_result,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_hit')::int AS evaluated_hit,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_miss')::int AS evaluated_miss,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'void')::int AS void_count,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'no_evaluable')::int AS no_evaluable,
      ROUND(
        100.0 * COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_hit')
        / NULLIF(COUNT(*) FILTER (WHERE oe.evaluation_status IN ('evaluated_hit', 'evaluated_miss')), 0),
        2
      ) AS hit_rate_on_scored_pct
    FROM base_events be
    INNER JOIN bt2_daily_picks dp ON dp.event_id = be.id
    LEFT JOIN bt2_pick_official_evaluation oe ON oe.daily_pick_id = dp.id
    GROUP BY COALESCE(dp.access_tier, '(null)'), COALESCE(dp.action_tier, '(null)')
    ORDER BY suggested_picks_count DESC, access_tier, action_tier;
    """
    combo_rows = _fetchall(cur, combo_sql, [date_from, date_to])

    access_sql = _base_events_cte() + """
    SELECT
      COALESCE(dp.access_tier, '(null)') AS access_tier,
      COUNT(DISTINCT dp.id)::int AS suggested_picks_count,
      COUNT(DISTINCT oe.id)::int AS official_eval_rows,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'pending_result')::int AS pending_result,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_hit')::int AS evaluated_hit,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_miss')::int AS evaluated_miss,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'void')::int AS void_count,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'no_evaluable')::int AS no_evaluable,
      ROUND(
        100.0 * COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_hit')
        / NULLIF(COUNT(*) FILTER (WHERE oe.evaluation_status IN ('evaluated_hit', 'evaluated_miss')), 0),
        2
      ) AS hit_rate_on_scored_pct
    FROM base_events be
    INNER JOIN bt2_daily_picks dp ON dp.event_id = be.id
    LEFT JOIN bt2_pick_official_evaluation oe ON oe.daily_pick_id = dp.id
    GROUP BY COALESCE(dp.access_tier, '(null)')
    ORDER BY suggested_picks_count DESC, access_tier;
    """
    access_rows = _fetchall(cur, access_sql, [date_from, date_to])

    p1 = outdir / "07_tier_quality_by_access_action.csv"
    _write_csv(p1, combo_rows)
    p2 = outdir / "07_tier_quality_by_access.csv"
    _write_csv(p2, access_rows)
    p3 = outdir / "07_tier_quality.json"
    _write_json(p3, {"by_access_action": combo_rows, "by_access": access_rows})
    return BlockResult(
        name="tier_quality",
        ok=True,
        files=[_relative_to_repo(p1), _relative_to_repo(p2), _relative_to_repo(p3)],
        summary={"tier_groups": len(combo_rows), "access_tiers": len(access_rows)},
    )


def block_08_raw_sm_coverage(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int) -> BlockResult:
    summary_sql = _base_events_cte() + """
    , raw_latest AS (
      SELECT fixture_id, fixture_date, fetched_at, payload
      FROM (
        SELECT
          r.*,
          ROW_NUMBER() OVER (PARTITION BY r.fixture_id ORDER BY r.fetched_at DESC NULLS LAST, r.fixture_date DESC NULLS LAST) AS rn
        FROM raw_sportmonks_fixtures r
      ) q
      WHERE q.rn = 1
    )
    SELECT
      be.event_day_local,
      COUNT(*)::int AS events_total,
      COUNT(*) FILTER (WHERE rl.fixture_id IS NOT NULL)::int AS events_with_raw_latest,
      COUNT(*) FILTER (WHERE rl.fixture_id IS NULL)::int AS events_missing_raw_latest,
      COUNT(*) FILTER (
        WHERE rl.payload IS NOT NULL AND jsonb_typeof(rl.payload) = 'object'
      )::int AS events_with_payload_object,
      MAX(rl.fetched_at) AS latest_raw_fetched_at
    FROM base_events be
    LEFT JOIN raw_latest rl ON rl.fixture_id = be.sportmonks_fixture_id
    GROUP BY be.event_day_local
    ORDER BY be.event_day_local;
    """
    summary_rows = _fetchall(cur, summary_sql, [date_from, date_to])

    sample_sql = _base_events_cte() + """
    SELECT
      be.id AS event_id,
      be.sportmonks_fixture_id,
      be.sofascore_event_id,
      be.event_day_local,
      be.kickoff_utc,
      be.status,
      be.result_home,
      be.result_away
    FROM base_events be
    LEFT JOIN raw_sportmonks_fixtures r ON r.fixture_id = be.sportmonks_fixture_id
    WHERE r.fixture_id IS NULL
    ORDER BY be.kickoff_utc ASC
    LIMIT %s;
    """
    sample_rows = _fetchall(cur, sample_sql, [date_from, date_to, sample_limit])

    duplicates_sql = _base_events_cte() + """
    SELECT
      be.sportmonks_fixture_id,
      COUNT(*)::int AS raw_rows,
      MIN(r.fetched_at) AS first_fetched_at,
      MAX(r.fetched_at) AS last_fetched_at
    FROM base_events be
    INNER JOIN raw_sportmonks_fixtures r ON r.fixture_id = be.sportmonks_fixture_id
    GROUP BY be.sportmonks_fixture_id
    ORDER BY raw_rows DESC, be.sportmonks_fixture_id
    LIMIT %s;
    """
    duplicate_rows = _fetchall(cur, duplicates_sql, [date_from, date_to, sample_limit])

    p1 = outdir / "08_raw_sportmonks_coverage_by_day.csv"
    _write_csv(p1, summary_rows)
    p2 = outdir / "08_raw_sportmonks_missing_samples.csv"
    _write_csv(p2, sample_rows)
    p3 = outdir / "08_raw_sportmonks_fixture_row_counts.csv"
    _write_csv(p3, duplicate_rows)
    p4 = outdir / "08_raw_sportmonks_coverage.json"
    _write_json(p4, {"by_day": summary_rows, "missing_samples": sample_rows, "fixture_row_counts": duplicate_rows})

    missing_total = sum(int(r.get("events_missing_raw_latest") or 0) for r in summary_rows)
    return BlockResult(
        name="raw_sm_coverage",
        ok=True,
        files=[_relative_to_repo(p1), _relative_to_repo(p2), _relative_to_repo(p3), _relative_to_repo(p4)],
        summary={"events_missing_raw_latest": missing_total},
    )


def block_09_provider_odds(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int, providers: Sequence[str]) -> BlockResult:
    provider_filter_sql, provider_params = _providers_sql_filter("pos.provider", providers)

    summary_sql = _base_events_cte() + f"""
    SELECT
      pos.provider,
      pos.source_scope,
      COUNT(*)::int AS snapshot_rows,
      COUNT(DISTINCT pos.bt2_event_id)::int AS distinct_events,
      MIN(pos.ingested_at_utc) AS first_ingested_at,
      MAX(pos.ingested_at_utc) AS last_ingested_at,
      COUNT(*) FILTER (WHERE pos.provider_event_ref IS NULL OR pos.provider_event_ref = '')::int AS rows_missing_provider_event_ref
    FROM bt2_provider_odds_snapshot pos
    INNER JOIN base_events be ON be.id = pos.bt2_event_id
    WHERE 1=1 {provider_filter_sql}
    GROUP BY pos.provider, pos.source_scope
    ORDER BY distinct_events DESC, pos.provider, pos.source_scope;
    """
    summary_rows = _fetchall(cur, summary_sql, [date_from, date_to, *provider_params])

    any_cov_sql = _base_events_cte() + f"""
    SELECT
      be.event_day_local,
      COUNT(DISTINCT be.id)::int AS events_total,
      COUNT(DISTINCT CASE WHEN pos.bt2_event_id IS NOT NULL THEN be.id END)::int AS events_with_provider_odds,
      COUNT(DISTINCT CASE WHEN pos.bt2_event_id IS NULL THEN be.id END)::int AS events_missing_provider_odds
    FROM base_events be
    LEFT JOIN bt2_provider_odds_snapshot pos
      ON pos.bt2_event_id = be.id
      {provider_filter_sql.replace('pos.provider', 'pos.provider')}
    GROUP BY be.event_day_local
    ORDER BY be.event_day_local;
    """
    by_day_rows = _fetchall(cur, any_cov_sql, [date_from, date_to, *provider_params])

    missing_sql = _base_events_cte() + f"""
    SELECT
      be.id AS event_id,
      be.sportmonks_fixture_id,
      be.sofascore_event_id,
      be.event_day_local,
      be.kickoff_utc,
      be.status,
      be.result_home,
      be.result_away
    FROM base_events be
    LEFT JOIN bt2_provider_odds_snapshot pos
      ON pos.bt2_event_id = be.id
      {provider_filter_sql.replace('pos.provider', 'pos.provider')}
    WHERE pos.bt2_event_id IS NULL
    ORDER BY be.kickoff_utc ASC
    LIMIT %s;
    """
    missing_rows = _fetchall(cur, missing_sql, [date_from, date_to, *provider_params, sample_limit])

    p1 = outdir / "09_provider_odds_coverage.csv"
    _write_csv(p1, summary_rows)
    p2 = outdir / "09_provider_odds_coverage_by_day.csv"
    _write_csv(p2, by_day_rows)
    p3 = outdir / "09_provider_odds_missing_samples.csv"
    _write_csv(p3, missing_rows)
    p4 = outdir / "09_provider_odds_coverage.json"
    _write_json(p4, {"coverage": summary_rows, "by_day": by_day_rows, "missing_samples": missing_rows})

    missing_total = sum(int(r.get("events_missing_provider_odds") or 0) for r in by_day_rows)
    return BlockResult(
        name="provider_odds_coverage",
        ok=True,
        files=[_relative_to_repo(p1), _relative_to_repo(p2), _relative_to_repo(p3), _relative_to_repo(p4)],
        summary={"events_missing_provider_odds": missing_total, "providers_in_scope": len(summary_rows)},
    )


def block_10_sfs_join(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int) -> BlockResult:
    latest_sql = _base_events_cte() + """
    , latest_join AS (
      SELECT *
      FROM (
        SELECT
          s.*,
          ROW_NUMBER() OVER (PARTITION BY s.bt2_event_id ORDER BY s.created_at DESC, s.id DESC) AS rn
        FROM bt2_sfs_join_audit s
        INNER JOIN base_events be ON be.id = s.bt2_event_id
      ) q
      WHERE q.rn = 1
    )
    SELECT
      COALESCE(match_status, '(null)') AS match_status,
      COALESCE(match_layer::text, '(null)') AS match_layer,
      COUNT(*)::int AS events_count,
      COUNT(*) FILTER (WHERE sofascore_event_id IS NOT NULL)::int AS events_with_sofascore_id,
      MAX(created_at) AS latest_created_at
    FROM latest_join
    GROUP BY COALESCE(match_status, '(null)'), COALESCE(match_layer::text, '(null)')
    ORDER BY events_count DESC, match_status, match_layer;
    """
    latest_rows = _fetchall(cur, latest_sql, [date_from, date_to])

    run_sql = _base_events_cte() + """
    SELECT
      s.run_id,
      COUNT(*)::int AS rows_count,
      COUNT(DISTINCT s.bt2_event_id)::int AS distinct_events,
      MAX(s.created_at) AS latest_created_at
    FROM bt2_sfs_join_audit s
    INNER JOIN base_events be ON be.id = s.bt2_event_id
    GROUP BY s.run_id
    ORDER BY latest_created_at DESC NULLS LAST, run_id;
    """
    run_rows = _fetchall(cur, run_sql, [date_from, date_to])

    sample_sql = _base_events_cte() + """
    , latest_join AS (
      SELECT *
      FROM (
        SELECT
          s.*,
          ROW_NUMBER() OVER (PARTITION BY s.bt2_event_id ORDER BY s.created_at DESC, s.id DESC) AS rn
        FROM bt2_sfs_join_audit s
        INNER JOIN base_events be ON be.id = s.bt2_event_id
      ) q
      WHERE q.rn = 1
    )
    SELECT
      bt2_event_id AS event_id,
      sofascore_event_id,
      run_id,
      match_status,
      match_layer,
      detail_json,
      created_at
    FROM latest_join
    WHERE sofascore_event_id IS NULL OR LOWER(COALESCE(match_status, '')) <> 'matched'
    ORDER BY created_at DESC, event_id
    LIMIT %s;
    """
    sample_rows = _fetchall(cur, sample_sql, [date_from, date_to, sample_limit])

    p1 = outdir / "10_sfs_join_quality_latest.csv"
    _write_csv(p1, latest_rows)
    p2 = outdir / "10_sfs_join_run_summary.csv"
    _write_csv(p2, run_rows)
    p3 = outdir / "10_sfs_join_nonmatched_samples.csv"
    _write_csv(p3, sample_rows)
    p4 = outdir / "10_sfs_join_quality.json"
    _write_json(p4, {"latest": latest_rows, "runs": run_rows, "samples": sample_rows})

    return BlockResult(
        name="sfs_join_quality",
        ok=True,
        files=[_relative_to_repo(p1), _relative_to_repo(p2), _relative_to_repo(p3), _relative_to_repo(p4)],
        summary={"latest_status_groups": len(latest_rows), "nonmatched_samples": len(sample_rows)},
    )


def block_11_ds_input_shadow(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int) -> BlockResult:
    coverage_sql = _base_events_cte() + """
    SELECT
      be.event_day_local,
      COUNT(DISTINCT be.id)::int AS events_total,
      COUNT(DISTINCT CASE WHEN ds.bt2_event_id IS NOT NULL THEN be.id END)::int AS events_with_shadow,
      COUNT(DISTINCT CASE WHEN ds.bt2_event_id IS NULL THEN be.id END)::int AS events_missing_shadow,
      MAX(ds.created_at) AS latest_shadow_created_at
    FROM base_events be
    LEFT JOIN bt2_dsr_ds_input_shadow ds ON ds.bt2_event_id = be.id
    GROUP BY be.event_day_local
    ORDER BY be.event_day_local;
    """
    coverage_rows = _fetchall(cur, coverage_sql, [date_from, date_to])

    run_sql = _base_events_cte() + """
    SELECT
      ds.run_id,
      COUNT(*)::int AS rows_count,
      COUNT(DISTINCT ds.bt2_event_id)::int AS distinct_events,
      MAX(ds.created_at) AS latest_created_at
    FROM bt2_dsr_ds_input_shadow ds
    INNER JOIN base_events be ON be.id = ds.bt2_event_id
    GROUP BY ds.run_id
    ORDER BY latest_created_at DESC NULLS LAST, run_id;
    """
    run_rows = _fetchall(cur, run_sql, [date_from, date_to])

    missing_sql = _base_events_cte() + """
    SELECT
      be.id AS event_id,
      be.sportmonks_fixture_id,
      be.sofascore_event_id,
      be.event_day_local,
      be.kickoff_utc,
      be.status,
      be.result_home,
      be.result_away
    FROM base_events be
    LEFT JOIN bt2_dsr_ds_input_shadow ds ON ds.bt2_event_id = be.id
    WHERE ds.bt2_event_id IS NULL
    ORDER BY be.kickoff_utc ASC
    LIMIT %s;
    """
    missing_rows = _fetchall(cur, missing_sql, [date_from, date_to, sample_limit])

    p1 = outdir / "11_ds_input_shadow_coverage_by_day.csv"
    _write_csv(p1, coverage_rows)
    p2 = outdir / "11_ds_input_shadow_run_summary.csv"
    _write_csv(p2, run_rows)
    p3 = outdir / "11_ds_input_shadow_missing_samples.csv"
    _write_csv(p3, missing_rows)
    p4 = outdir / "11_ds_input_shadow_coverage.json"
    _write_json(p4, {"by_day": coverage_rows, "runs": run_rows, "missing_samples": missing_rows})

    missing_total = sum(int(r.get("events_missing_shadow") or 0) for r in coverage_rows)
    return BlockResult(
        name="ds_input_shadow_coverage",
        ok=True,
        files=[_relative_to_repo(p1), _relative_to_repo(p2), _relative_to_repo(p3), _relative_to_repo(p4)],
        summary={"events_missing_shadow": missing_total, "run_count": len(run_rows)},
    )


def block_12_odds_snapshot(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int) -> BlockResult:
    event_sql = _base_events_cte() + """
    SELECT
      be.id AS event_id,
      be.sportmonks_fixture_id,
      be.sofascore_event_id,
      be.event_day_local,
      be.kickoff_utc,
      be.status,
      be.result_home,
      be.result_away,
      COUNT(os.id)::int AS odds_rows,
      COUNT(DISTINCT os.bookmaker)::int AS bookmakers,
      COUNT(DISTINCT os.market)::int AS markets,
      COUNT(DISTINCT (os.market || '|' || os.selection))::int AS market_selection_pairs,
      MIN(os.fetched_at) AS first_odds_fetched_at,
      MAX(os.fetched_at) AS last_odds_fetched_at
    FROM base_events be
    LEFT JOIN bt2_odds_snapshot os ON os.event_id = be.id
    GROUP BY
      be.id, be.sportmonks_fixture_id, be.sofascore_event_id, be.event_day_local,
      be.kickoff_utc, be.status, be.result_home, be.result_away
    ORDER BY be.event_day_local, be.kickoff_utc, be.id;
    """
    event_rows = _fetchall(cur, event_sql, [date_from, date_to])

    summary_by_day: list[dict[str, Any]] = []
    bucket: dict[str, list[dict[str, Any]]] = {}
    for row in event_rows:
        bucket.setdefault(str(row["event_day_local"]), []).append(row)
    for day_key in sorted(bucket.keys()):
        rows = bucket[day_key]
        total = len(rows)
        with_any = sum(1 for r in rows if int(r.get("odds_rows") or 0) > 0)
        lt3 = sum(1 for r in rows if int(r.get("odds_rows") or 0) < 3)
        lt6 = sum(1 for r in rows if int(r.get("odds_rows") or 0) < 6)
        summary_by_day.append(
            {
                "event_day_local": day_key,
                "events_total": total,
                "events_with_any_odds": with_any,
                "events_missing_odds": total - with_any,
                "events_with_lt3_rows": lt3,
                "events_with_lt6_rows": lt6,
                "avg_odds_rows": round(sum(float(r.get("odds_rows") or 0) for r in rows) / total, 2) if total else 0,
                "avg_bookmakers": round(sum(float(r.get("bookmakers") or 0) for r in rows) / total, 2) if total else 0,
                "avg_markets": round(sum(float(r.get("markets") or 0) for r in rows) / total, 2) if total else 0,
            }
        )

    weak_rows = [
        row
        for row in event_rows
        if int(row.get("odds_rows") or 0) == 0 or int(row.get("markets") or 0) < 2 or int(row.get("bookmakers") or 0) < 1
    ]
    weak_rows = sorted(
        weak_rows,
        key=lambda r: (int(r.get("odds_rows") or 0), int(r.get("markets") or 0), str(r.get("kickoff_utc") or "")),
    )[:sample_limit]

    market_sql = _base_events_cte() + """
    SELECT
      os.market,
      COUNT(*)::int AS odds_rows,
      COUNT(DISTINCT os.event_id)::int AS distinct_events,
      COUNT(DISTINCT os.bookmaker)::int AS distinct_bookmakers,
      MAX(os.fetched_at) AS last_fetched_at
    FROM bt2_odds_snapshot os
    INNER JOIN base_events be ON be.id = os.event_id
    GROUP BY os.market
    ORDER BY distinct_events DESC, os.market;
    """
    market_rows = _fetchall(cur, market_sql, [date_from, date_to])

    p1 = outdir / "12_odds_snapshot_event_metrics.csv"
    _write_csv(p1, event_rows)
    p2 = outdir / "12_odds_snapshot_completeness_by_day.csv"
    _write_csv(p2, summary_by_day)
    p3 = outdir / "12_odds_snapshot_weak_samples.csv"
    _write_csv(p3, weak_rows)
    p4 = outdir / "12_odds_snapshot_market_coverage.csv"
    _write_csv(p4, market_rows)
    p5 = outdir / "12_odds_snapshot_completeness.json"
    _write_json(p5, {"event_metrics": event_rows, "by_day": summary_by_day, "weak_samples": weak_rows, "by_market": market_rows})

    missing_total = sum(int(r.get("events_missing_odds") or 0) for r in summary_by_day)
    return BlockResult(
        name="odds_snapshot_completeness",
        ok=True,
        files=[_relative_to_repo(p1), _relative_to_repo(p2), _relative_to_repo(p3), _relative_to_repo(p4), _relative_to_repo(p5)],
        summary={"events_missing_odds": missing_total, "weak_samples": len(weak_rows)},
    )


# ---------------------------------------------------------------------------
# Findings / runbook helpers
# ---------------------------------------------------------------------------


def _build_findings(results: Sequence[BlockResult]) -> list[dict[str, Any]]:
    idx = {r.name: r for r in results}
    findings: list[dict[str, Any]] = []

    closure = idx.get("closure_summary")
    if closure and closure.summary.get("finished_without_score", 0) > 0:
        findings.append(
            {
                "severity": "high",
                "code": "FINISHED_WITHOUT_SCORE_PRESENT",
                "message": "Hay eventos marked as finished sin score final persistido en bt2_events. Eso puede inflar pending/no_evaluable y sesgar la medición oficial.",
                "evidence_hint": "Revisar bloque 03 y 01.",
            }
        )

    pending = idx.get("pending_lag")
    if pending and pending.summary.get("unresolved_ge_24h", 0) > 0:
        findings.append(
            {
                "severity": "high",
                "code": "PENDING_LAG_OVER_24H",
                "message": "Hay eventos todavía unresolved más de 24h después del kickoff. Esto apunta a atraso de cierre, atraso del proveedor o cadena de verdad incompleta.",
                "evidence_hint": "Revisar bloque 02.",
            }
        )

    raw_cov = idx.get("raw_sm_coverage")
    if raw_cov and raw_cov.summary.get("events_missing_raw_latest", 0) > 0:
        findings.append(
            {
                "severity": "medium",
                "code": "BT2_EVENT_WITHOUT_RAW_SM",
                "message": "Existen bt2_events en rango sin cobertura raw SportMonks visible en raw_sportmonks_fixtures.",
                "evidence_hint": "Revisar bloque 08.",
            }
        )

    provider = idx.get("provider_odds_coverage")
    if provider and provider.summary.get("events_missing_provider_odds", 0) > 0:
        findings.append(
            {
                "severity": "medium",
                "code": "EVENT_WITHOUT_PROVIDER_ODDS",
                "message": "Hay eventos en rango sin snapshot raw por proveedor. Si estos eventos entran al replay o a la lógica de elegibilidad, la medición puede degradarse.",
                "evidence_hint": "Revisar bloque 09.",
            }
        )

    ds_shadow = idx.get("ds_input_shadow_coverage")
    if ds_shadow and ds_shadow.summary.get("events_missing_shadow", 0) > 0:
        findings.append(
            {
                "severity": "medium",
                "code": "EVENT_WITHOUT_DS_INPUT_SHADOW",
                "message": "Faltan fragmentos experimentales de ds_input para algunos eventos. Esto limita la trazabilidad del experimento S6.5.",
                "evidence_hint": "Revisar bloque 11.",
            }
        )

    odds = idx.get("odds_snapshot_completeness")
    if odds and odds.summary.get("events_missing_odds", 0) > 0:
        findings.append(
            {
                "severity": "high",
                "code": "EVENT_WITHOUT_BT2_ODDS_SNAPSHOT",
                "message": "Hay eventos sin filas en bt2_odds_snapshot dentro del rango. Eso puede explicar candidateEvents > 0 pero eligibleEvents bajos o nulos en replay.",
                "evidence_hint": "Revisar bloque 12.",
            }
        )

    evals = idx.get("evaluation_summary")
    if evals and evals.summary.get("missing_official_eval_rows", 0) > 0:
        findings.append(
            {
                "severity": "high",
                "code": "DAILY_PICKS_WITHOUT_OFFICIAL_EVAL_ROW",
                "message": "Hay picks sugeridos sin fila en bt2_pick_official_evaluation. Antes de discutir edge, primero hay que cerrar la trazabilidad de evaluación oficial.",
                "evidence_hint": "Revisar bloque 04.",
            }
        )

    no_eval = idx.get("no_evaluable_breakdown")
    if no_eval and no_eval.summary.get("top_reason") == "MISSING_TRUTH_SOURCE":
        findings.append(
            {
                "severity": "high",
                "code": "TOP_NO_EVALUABLE_IS_MISSING_TRUTH_SOURCE",
                "message": "El principal motivo de no_evaluable en el rango es MISSING_TRUTH_SOURCE. Eso apoya la hipótesis de problema de medición/datos antes que falta de edge pura.",
                "evidence_hint": "Revisar bloque 05 y 03.",
            }
        )

    return findings


def _write_runbook(outdir: Path, args: argparse.Namespace, results: Sequence[BlockResult], findings: Sequence[dict[str, Any]]) -> Path:
    lines = [
        "# BT2 Phase 1 Audit — guía rápida de lectura",
        "",
        f"Rango auditado (kickoff local {DEFAULT_TIMEZONE}): {args.date_from} → {args.date_to}",
        f"Providers filter: {', '.join(args.providers) if args.providers else '(todos)'}",
        "",
        "## Orden sugerido de revisión",
        "1. 04_official_evaluation_summary.json",
        "2. 05_no_evaluable_breakdown.csv",
        "3. 03_finished_without_score_samples.csv",
        "4. 02_pending_lag_samples.csv",
        "5. 12_odds_snapshot_completeness_by_day.csv",
        "6. 08_raw_sportmonks_coverage_by_day.csv",
        "7. 09_provider_odds_coverage.csv",
        "8. 10_sfs_join_quality_latest.csv",
        "9. 11_ds_input_shadow_coverage_by_day.csv",
        "",
        "## Qué significa cada bloque",
        "- 01: cierre operativo de bt2_events.",
        "- 02: eventos aún unresolved y cuánto llevan envejeciendo.",
        "- 03: casos finished sin score final.",
        "- 04: estado oficial de evaluación de picks.",
        "- 05: por qué hay no_evaluable.",
        "- 06: calidad de medición por mercado.",
        "- 07: calidad de medición por tiers.",
        "- 08: si el raw de SportMonks realmente existe para esos eventos.",
        "- 09: si existen snapshots raw por proveedor para esos eventos.",
        "- 10: salud del join SFS más reciente por evento.",
        "- 11: trazabilidad del experimento ds_input shadow.",
        "- 12: completitud del snapshot de odds que alimenta replay/elegibilidad.",
        "",
        "## Findings automáticos",
    ]
    if findings:
        for f in findings:
            lines.append(f"- [{f['severity']}] {f['code']}: {f['message']} ({f['evidence_hint']})")
    else:
        lines.append("- No se detectaron flags automáticos por umbral simple. Igual revisa los CSV/JSON.")

    lines.extend(
        [
            "",
            "## Artefactos generados",
        ]
    )
    for result in results:
        lines.append(f"- {result.name}: {', '.join(result.files)}")

    path = outdir / "README.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BT2 Phase 1 read-only data quality audit")
    parser.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
    parser.add_argument("--outdir", default="out/bt2_phase1_audit", help="Output base dir (default: out/bt2_phase1_audit)")
    parser.add_argument("--providers", default="", help="Comma-separated provider filter for bt2_provider_odds_snapshot")
    parser.add_argument("--sample-limit", type=int, default=50, help="Max sample rows per anomaly file")
    args = parser.parse_args()

    try:
        d_from = datetime.strptime(args.date_from, "%Y-%m-%d").date()
        d_to = datetime.strptime(args.date_to, "%Y-%m-%d").date()
    except ValueError as exc:
        raise SystemExit(f"Formato inválido de fecha: {exc}")
    if d_from > d_to:
        raise SystemExit("--from no puede ser mayor que --to")
    args.providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    return args


def main() -> None:
    args = parse_args()
    db_url = _sync_dsn(_load_bt2_database_url())

    out_base = Path(args.outdir)
    if not out_base.is_absolute():
        out_base = REPO / out_base
    outdir = _build_output_dir(out_base)

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError as exc:
        raise SystemExit(f"No se pudo importar psycopg2: {exc}")

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET statement_timeout TO 0")

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO),
        "timezone_lens": DEFAULT_TIMEZONE,
        "date_filter_kind": "bt2_events.kickoff_utc rendered as local date in America/Bogota",
        "range": {"from": args.date_from, "to": args.date_to},
        "providers_filter": args.providers,
        "sample_limit": args.sample_limit,
        "db": _sanitize_dsn(db_url),
        "notes": [
            "All blocks are read-only.",
            "The common date lens is event kickoff local day, not bt2_daily_picks.operating_day_key.",
            "Provider filter only affects bt2_provider_odds_snapshot blocks.",
        ],
    }
    _write_json(outdir / "00_manifest.json", manifest)

    blocks: list[tuple[str, Any]] = [
        ("closure_summary", lambda: block_01_closure_summary(cur, args.date_from, args.date_to, outdir)),
        ("pending_lag", lambda: block_02_pending_lag(cur, args.date_from, args.date_to, outdir, args.sample_limit)),
        ("finished_without_score", lambda: block_03_finished_without_score(cur, args.date_from, args.date_to, outdir, args.sample_limit)),
        ("evaluation_summary", lambda: block_04_evaluation_summary(cur, args.date_from, args.date_to, outdir)),
        ("no_evaluable_breakdown", lambda: block_05_no_evaluable(cur, args.date_from, args.date_to, outdir, args.sample_limit)),
        ("market_quality", lambda: block_06_market_quality(cur, args.date_from, args.date_to, outdir)),
        ("tier_quality", lambda: block_07_tier_quality(cur, args.date_from, args.date_to, outdir)),
        ("raw_sm_coverage", lambda: block_08_raw_sm_coverage(cur, args.date_from, args.date_to, outdir, args.sample_limit)),
        ("provider_odds_coverage", lambda: block_09_provider_odds(cur, args.date_from, args.date_to, outdir, args.sample_limit, args.providers)),
        ("sfs_join_quality", lambda: block_10_sfs_join(cur, args.date_from, args.date_to, outdir, args.sample_limit)),
        ("ds_input_shadow_coverage", lambda: block_11_ds_input_shadow(cur, args.date_from, args.date_to, outdir, args.sample_limit)),
        ("odds_snapshot_completeness", lambda: block_12_odds_snapshot(cur, args.date_from, args.date_to, outdir, args.sample_limit)),
    ]

    results: list[BlockResult] = []
    for idx_num, (expected_name, runner) in enumerate(blocks, start=1):
        try:
            result = runner()
        except Exception as exc:  # pragma: no cover - defensive ops path
            error_payload = {
                "block": expected_name,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
            err_path = outdir / f"{idx_num:02d}_{expected_name}_ERROR.json"
            _write_json(err_path, error_payload)
            result = BlockResult(
                name=expected_name,
                ok=False,
                files=[_relative_to_repo(err_path)],
                summary={},
                warning=str(exc),
            )
        results.append(result)

    findings = _build_findings(results)
    findings_path = outdir / "99_findings.json"
    _write_json(findings_path, findings)
    readme_path = _write_runbook(outdir, args, results, findings)

    summary_payload = {
        "manifest": manifest,
        "results": [
            {
                "name": r.name,
                "ok": r.ok,
                "files": r.files,
                "summary": r.summary,
                "warning": r.warning,
            }
            for r in results
        ],
        "findings": findings,
        "readme": _relative_to_repo(readme_path),
    }
    summary_path = outdir / "99_summary.json"
    _write_json(summary_path, summary_payload)

    print("=== BT2 PHASE 1 DATA AUDIT ===")
    print(f"Rango (kickoff local {DEFAULT_TIMEZONE}): {args.date_from} -> {args.date_to}")
    print(f"Salida: {_relative_to_repo(outdir)}")
    print(f"DB: {_sanitize_dsn(db_url)}")
    print()
    for r in results:
        print(f"- {r.name}: ok={r.ok} | files={len(r.files)} | summary={json.dumps(r.summary, ensure_ascii=False, default=_json_default)}")
    print()
    if findings:
        print("Findings automáticos:")
        for f in findings:
            print(f"  - [{f['severity']}] {f['code']}: {f['message']}")
    else:
        print("Findings automáticos: ninguno por umbral simple.")
    print()
    print(f"README: {_relative_to_repo(readme_path)}")
    print(f"Summary JSON: {_relative_to_repo(summary_path)}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()

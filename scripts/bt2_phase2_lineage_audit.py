#!/usr/bin/env python3
"""
BT2 Phase 2 — lineage audit across raw → CDM → picks/evaluation.

Purpose
-------
Answer this question after Phase 1:

    "¿Dónde nace el drift real: en raw, en bt2_events, en odds/materialización,
     en evaluation, o en la forma en que estamos leyendo la ventana?"

This script is read-only and operator-oriented. It audits lineage and consistency
instead of only counting closure symptoms.

Scope
-----
The script focuses on the chain that matters for BT2 trust:

1. Range coverage on both lenses:
   - bt2_events by kickoff local day
   - bt2_daily_picks by operating_day_key
2. Event/raw lineage universe summary
3. Raw latest freshness + drift hints
4. Raw latest vs bt2_events consistency
5. Pick operating_day alignment vs event kickoff local day
6. Official evaluation vs lineage state
7. Provider raw odds vs consolidated odds parity
8. SFS / ds_input shadow lineage support

Design notes
------------
- Read-only: no schema changes, no writes, no migrations.
- Runs from repo root.
- Reads BT2_DATABASE_URL from env or .env in repo root.
- Main date lens for event lineage is bt2_events.kickoff_utc rendered in America/Bogota.
- Also audits bt2_daily_picks.operating_day_key separately to avoid false conclusions
  when a range is empty on the event lens but not on the pick-day lens.
- Writes CSV/JSON artifacts into out/bt2_phase2_audit/<timestamp>/.

Usage
-----
From repo root:

    python3 scripts/bt2_phase2_lineage_audit.py --from 2026-04-13 --to 2026-04-19
    python3 scripts/bt2_phase2_lineage_audit.py --from 2026-04-13 --to 2026-04-19 \
      --providers sportmonks,sofascore --sample-limit 100

Expected environment
--------------------
- BT2_DATABASE_URL in env, or in repo-root .env
- psycopg2 available in the same environment used by repo scripts
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parents[1]
DEFAULT_TIMEZONE = "America/Bogota"
PENDING_STATUSES = ("scheduled", "live", "inplay", "in_play", "")
VOIDISH_STATUSES = ("cancelled", "canceled", "postponed", "abandoned")
FINISHEDISH_STATUSES = ("finished", "ft", "after penalties", "aet", "fulltime", "full_time")


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
    if isinstance(obj, timedelta):
        return obj.total_seconds()
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
        e.updated_at,
        (e.kickoff_utc AT TIME ZONE '{DEFAULT_TIMEZONE}')::date AS event_day_local
      FROM bt2_events e
      WHERE e.kickoff_utc IS NOT NULL
        AND (e.kickoff_utc AT TIME ZONE '{DEFAULT_TIMEZONE}')::date BETWEEN %s AND %s
    )
    """


def _latest_raw_cte() -> str:
    return """
    , raw_ranked AS (
      SELECT
        r.fixture_id,
        r.fixture_date,
        r.fetched_at,
        r.payload,
        ROW_NUMBER() OVER (
          PARTITION BY r.fixture_id
          ORDER BY r.fetched_at DESC NULLS LAST, r.fixture_date DESC NULLS LAST
        ) AS rn,
        COUNT(*) OVER (PARTITION BY r.fixture_id) AS raw_row_count
      FROM raw_sportmonks_fixtures r
      INNER JOIN base_events be ON be.sportmonks_fixture_id = r.fixture_id
    ),
    raw_latest AS (
      SELECT *
      FROM raw_ranked
      WHERE rn = 1
    )
    """


def _latest_sfs_join_cte() -> str:
    return """
    , sfs_ranked AS (
      SELECT
        s.*,
        ROW_NUMBER() OVER (
          PARTITION BY s.bt2_event_id
          ORDER BY s.created_at DESC, s.id DESC
        ) AS rn
      FROM bt2_sfs_join_audit s
      INNER JOIN base_events be ON be.id = s.bt2_event_id
    ),
    sfs_latest AS (
      SELECT *
      FROM sfs_ranked
      WHERE rn = 1
    )
    """


def _build_output_dir(base: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = base / stamp
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def _coerce_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, Decimal):
        try:
            return int(value)
        except Exception:
            return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if re.fullmatch(r"-?\d+", s):
            try:
                return int(s)
            except Exception:
                return None
    return None


def _walk_json(obj: Any, path: str = "$", depth: int = 0, max_depth: int = 8) -> Iterable[tuple[str, Any]]:
    yield path, obj
    if depth >= max_depth:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            next_path = f"{path}.{k}" if path else str(k)
            yield from _walk_json(v, next_path, depth + 1, max_depth)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):
            next_path = f"{path}[{i}]"
            yield from _walk_json(v, next_path, depth + 1, max_depth)


def _unwrap_payload(payload: Any) -> Any:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return payload
    if isinstance(payload, dict) and "data" in payload:
        data = payload.get("data")
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        if isinstance(data, dict):
            return data
    return payload


def _top_keys(payload: Any) -> list[str]:
    obj = _unwrap_payload(payload)
    if isinstance(obj, dict):
        return list(obj.keys())[:20]
    return []


def _extract_raw_status(payload: Any) -> tuple[Optional[str], Optional[str]]:
    obj = _unwrap_payload(payload)
    exact_priority = [
        "$.status",
        "$.state",
        "$.status.short",
        "$.status.short_code",
        "$.status.long",
        "$.status.description",
        "$.state.short",
        "$.state.name",
        "$.fixture.status",
        "$.fixture.status.short",
        "$.fixture.status.long",
        "$.fixture.state",
    ]
    scalars: list[tuple[str, str]] = []
    for path, value in _walk_json(obj):
        if isinstance(value, str) and value.strip():
            scalars.append((path, value.strip()))

    path_map = {p: v for p, v in scalars}
    for p in exact_priority:
        if p in path_map:
            return path_map[p], p

    statusish = []
    for p, v in scalars:
        last = p.lower().split(".")[-1]
        if any(tok in last for tok in ("status", "state", "short_code", "description")):
            statusish.append((p, v))
    if statusish:
        return statusish[0][1], statusish[0][0]
    return None, None


def _extract_raw_score_pair(payload: Any) -> tuple[Optional[int], Optional[int], Optional[str]]:
    obj = _unwrap_payload(payload)
    pair_candidates = [
        ("home_score", "away_score"),
        ("score_home", "score_away"),
        ("home_goals", "away_goals"),
        ("localteam_score", "visitorteam_score"),
        ("home_ft_score", "away_ft_score"),
        ("home_current", "away_current"),
        ("local", "visitor"),
    ]

    for path, value in _walk_json(obj):
        if isinstance(value, dict):
            lowered = {str(k).lower(): v for k, v in value.items()}
            for hk, ak in pair_candidates:
                if hk in lowered and ak in lowered:
                    home = _coerce_int(lowered[hk])
                    away = _coerce_int(lowered[ak])
                    if home is not None and away is not None:
                        return home, away, f"{path}.{hk}|{ak}"

    home_cands: list[tuple[str, int]] = []
    away_cands: list[tuple[str, int]] = []
    for path, value in _walk_json(obj):
        iv = _coerce_int(value)
        if iv is None:
            continue
        lp = path.lower()
        if not any(tok in lp for tok in ("score", "goal", "result")):
            continue
        if any(tok in lp for tok in ("home", "local", "participant_1", "participant1")):
            home_cands.append((path, iv))
        elif any(tok in lp for tok in ("away", "visitor", "visitorteam", "participant_2", "participant2")):
            away_cands.append((path, iv))
    if home_cands and away_cands:
        return home_cands[0][1], away_cands[0][1], f"{home_cands[0][0]}|{away_cands[0][0]}"
    return None, None, None


def _normalized_status(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = str(value).strip().lower()
    if not v:
        return None
    mapping = {
        "ft": "finished",
        "full time": "finished",
        "full_time": "finished",
        "fulltime": "finished",
        "finished": "finished",
        "after penalties": "finished",
        "aet": "finished",
        "not started": "scheduled",
        "ns": "scheduled",
        "scheduled": "scheduled",
        "live": "live",
        "inplay": "live",
        "in_play": "live",
        "postponed": "postponed",
        "cancelled": "cancelled",
        "canceled": "cancelled",
        "abandoned": "abandoned",
    }
    return mapping.get(v, v)


def _event_unresolved_flag(event_status: Optional[str], result_home: Any, result_away: Any) -> bool:
    st = _normalized_status(event_status) or ""
    if st in PENDING_STATUSES:
        return True
    if st == "finished" and (_coerce_int(result_home) is None or _coerce_int(result_away) is None):
        return True
    if st not in VOIDISH_STATUSES and st != "finished" and (_coerce_int(result_home) is None or _coerce_int(result_away) is None):
        return True
    return False


def _days_delta(a: Optional[str], b: Optional[date]) -> Optional[int]:
    if not a or b is None:
        return None
    try:
        aa = datetime.strptime(a, "%Y-%m-%d").date()
    except Exception:
        return None
    return (aa - b).days


def _bucket_delta(delta: Optional[int]) -> str:
    if delta is None:
        return "unknown"
    if delta == 0:
        return "same_day"
    if delta == -1:
        return "event_day_plus_1"
    if delta == 1:
        return "event_day_minus_1"
    if delta < -1:
        return "event_day_much_later"
    return "event_day_much_earlier"


def _score_relation(raw_h: Optional[int], raw_a: Optional[int], ev_h: Any, ev_a: Any) -> str:
    ev_hi = _coerce_int(ev_h)
    ev_ai = _coerce_int(ev_a)
    raw_has = raw_h is not None and raw_a is not None
    ev_has = ev_hi is not None and ev_ai is not None
    if raw_has and ev_has:
        return "match" if (raw_h == ev_hi and raw_a == ev_ai) else "mismatch"
    if raw_has and not ev_has:
        return "raw_only"
    if not raw_has and ev_has:
        return "event_only"
    return "neither"


def _status_relation(raw_status: Optional[str], event_status: Optional[str]) -> str:
    rs = _normalized_status(raw_status)
    es = _normalized_status(event_status)
    if rs and es:
        return "match" if rs == es else "mismatch"
    if rs and not es:
        return "raw_only"
    if not rs and es:
        return "event_only"
    return "neither"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def load_event_lineage_rows(cur: Any, date_from: str, date_to: str) -> list[dict[str, Any]]:
    sql = _base_events_cte() + _latest_raw_cte() + """
    SELECT
      be.id AS event_id,
      be.sportmonks_fixture_id,
      be.sofascore_event_id,
      be.league_id,
      be.home_team_id,
      be.away_team_id,
      be.kickoff_utc,
      be.event_day_local,
      be.status AS event_status,
      be.result_home AS event_result_home,
      be.result_away AS event_result_away,
      be.updated_at AS event_updated_at,
      rl.raw_row_count,
      rl.fixture_date AS raw_fixture_date,
      rl.fetched_at AS raw_latest_fetched_at,
      rl.payload AS raw_latest_payload
    FROM base_events be
    LEFT JOIN raw_latest rl ON rl.fixture_id = be.sportmonks_fixture_id
    ORDER BY be.event_day_local, be.kickoff_utc, be.id;
    """
    rows = _fetchall(cur, sql, [date_from, date_to])

    enriched: list[dict[str, Any]] = []
    for row in rows:
        payload = row.get("raw_latest_payload")
        raw_status, raw_status_path = _extract_raw_status(payload)
        raw_h, raw_a, raw_score_path = _extract_raw_score_pair(payload)
        kickoff_utc = row.get("kickoff_utc")
        raw_latest_fetched_at = row.get("raw_latest_fetched_at")
        event_updated_at = row.get("event_updated_at")
        minutes_kickoff_to_raw = None
        minutes_raw_to_event_update = None
        if isinstance(kickoff_utc, datetime) and isinstance(raw_latest_fetched_at, datetime):
            minutes_kickoff_to_raw = round((raw_latest_fetched_at - kickoff_utc).total_seconds() / 60.0, 2)
        if isinstance(event_updated_at, datetime) and isinstance(raw_latest_fetched_at, datetime):
            minutes_raw_to_event_update = round((event_updated_at - raw_latest_fetched_at).total_seconds() / 60.0, 2)

        event_status = row.get("event_status")
        ev_h = row.get("event_result_home")
        ev_a = row.get("event_result_away")

        enriched.append(
            {
                **row,
                "raw_payload_top_keys": _top_keys(payload),
                "raw_status_guess": raw_status,
                "raw_status_path": raw_status_path,
                "raw_score_home_guess": raw_h,
                "raw_score_away_guess": raw_a,
                "raw_score_path": raw_score_path,
                "raw_has_score_guess": raw_h is not None and raw_a is not None,
                "raw_has_status_guess": raw_status is not None,
                "event_has_score": _coerce_int(ev_h) is not None and _coerce_int(ev_a) is not None,
                "event_unresolved_flag": _event_unresolved_flag(event_status, ev_h, ev_a),
                "score_relation": _score_relation(raw_h, raw_a, ev_h, ev_a),
                "status_relation": _status_relation(raw_status, event_status),
                "minutes_kickoff_to_raw_latest": minutes_kickoff_to_raw,
                "minutes_raw_latest_to_event_update": minutes_raw_to_event_update,
            }
        )
    return enriched


def load_pick_lineage_rows(cur: Any, date_from: str, date_to: str) -> list[dict[str, Any]]:
    sql = _base_events_cte() + """
    SELECT
      be.id AS event_id,
      be.event_day_local,
      be.kickoff_utc,
      be.status AS event_status,
      be.result_home AS event_result_home,
      be.result_away AS event_result_away,
      dp.id AS daily_pick_id,
      dp.user_id,
      dp.operating_day_key,
      dp.access_tier,
      dp.action_tier,
      dp.suggested_at,
      dp.pipeline_version,
      oe.id AS official_eval_id,
      oe.market_canonical,
      oe.selection_canonical,
      oe.suggested_at AS eval_suggested_at,
      oe.evaluation_status,
      oe.no_evaluable_reason,
      oe.truth_source,
      oe.truth_payload_ref,
      oe.evaluated_at
    FROM base_events be
    INNER JOIN bt2_daily_picks dp ON dp.event_id = be.id
    LEFT JOIN bt2_pick_official_evaluation oe ON oe.daily_pick_id = dp.id
    ORDER BY dp.operating_day_key, dp.id;
    """
    return _fetchall(cur, sql, [date_from, date_to])


def load_range_coverage_rows(cur: Any, date_from: str, date_to: str) -> dict[str, list[dict[str, Any]]]:
    events_sql = f"""
    SELECT
      (e.kickoff_utc AT TIME ZONE '{DEFAULT_TIMEZONE}')::date AS event_day_local,
      COUNT(*)::int AS events_total
    FROM bt2_events e
    WHERE e.kickoff_utc IS NOT NULL
      AND (e.kickoff_utc AT TIME ZONE '{DEFAULT_TIMEZONE}')::date BETWEEN %s AND %s
    GROUP BY 1
    ORDER BY 1;
    """
    picks_sql = """
    SELECT
      dp.operating_day_key,
      COUNT(*)::int AS picks_total,
      COUNT(DISTINCT dp.event_id)::int AS distinct_events
    FROM bt2_daily_picks dp
    WHERE dp.operating_day_key BETWEEN %s AND %s
    GROUP BY 1
    ORDER BY 1;
    """
    eval_sql = """
    SELECT
      dp.operating_day_key,
      COUNT(*) FILTER (WHERE oe.id IS NOT NULL)::int AS official_eval_rows,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'pending_result')::int AS pending_result,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_hit')::int AS evaluated_hit,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'evaluated_miss')::int AS evaluated_miss,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'void')::int AS void_count,
      COUNT(*) FILTER (WHERE oe.evaluation_status = 'no_evaluable')::int AS no_evaluable
    FROM bt2_daily_picks dp
    LEFT JOIN bt2_pick_official_evaluation oe ON oe.daily_pick_id = dp.id
    WHERE dp.operating_day_key BETWEEN %s AND %s
    GROUP BY 1
    ORDER BY 1;
    """
    return {
        "events_by_day": _fetchall(cur, events_sql, [date_from, date_to]),
        "picks_by_day": _fetchall(cur, picks_sql, [date_from, date_to]),
        "eval_by_day": _fetchall(cur, eval_sql, [date_from, date_to]),
    }


# ---------------------------------------------------------------------------
# Audit blocks
# ---------------------------------------------------------------------------


def block_00_range_coverage(outdir: Path, coverage: Mapping[str, list[dict[str, Any]]]) -> BlockResult:
    files = []
    p1 = outdir / "00_range_coverage_events_by_kickoff_day.csv"
    _write_csv(p1, coverage["events_by_day"])
    files.append(_relative_to_repo(p1))
    p2 = outdir / "00_range_coverage_picks_by_operating_day.csv"
    _write_csv(p2, coverage["picks_by_day"])
    files.append(_relative_to_repo(p2))
    p3 = outdir / "00_range_coverage_eval_by_operating_day.csv"
    _write_csv(p3, coverage["eval_by_day"])
    files.append(_relative_to_repo(p3))
    p4 = outdir / "00_range_coverage_summary.json"
    _write_json(p4, coverage)
    files.append(_relative_to_repo(p4))
    return BlockResult(
        name="range_coverage",
        ok=True,
        files=files,
        summary={
            "event_days_with_rows": len(coverage["events_by_day"]),
            "operating_days_with_picks": len(coverage["picks_by_day"]),
            "events_total": sum(int(r.get("events_total") or 0) for r in coverage["events_by_day"]),
            "picks_total": sum(int(r.get("picks_total") or 0) for r in coverage["picks_by_day"]),
        },
    )


def block_01_lineage_universe(outdir: Path, event_rows: Sequence[Mapping[str, Any]], pick_rows: Sequence[Mapping[str, Any]]) -> BlockResult:
    picks_by_event: Counter[int] = Counter()
    eval_by_event: Counter[int] = Counter()
    for r in pick_rows:
        eid = int(r["event_id"])
        picks_by_event[eid] += 1
        if r.get("official_eval_id") is not None:
            eval_by_event[eid] += 1

    by_day: dict[str, Counter[str]] = defaultdict(Counter)
    for r in event_rows:
        day = str(r["event_day_local"])
        c = by_day[day]
        c["events_total"] += 1
        if r.get("raw_latest_fetched_at") is not None:
            c["events_with_raw_latest"] += 1
        if int(r.get("raw_row_count") or 0) > 1:
            c["events_with_multiple_raw_rows"] += 1
        if r.get("raw_has_score_guess"):
            c["events_with_raw_score_guess"] += 1
        if r.get("event_has_score"):
            c["events_with_event_score"] += 1
        if r.get("score_relation") == "raw_only":
            c["events_raw_score_only"] += 1
        if r.get("score_relation") == "event_only":
            c["events_event_score_only"] += 1
        if r.get("score_relation") == "mismatch":
            c["events_score_mismatch"] += 1
        if r.get("status_relation") == "mismatch":
            c["events_status_mismatch"] += 1
        if r.get("event_unresolved_flag"):
            c["events_unresolved"] += 1
        if picks_by_event.get(int(r["event_id"]), 0) > 0:
            c["events_with_picks"] += 1
            c["picks_total"] += picks_by_event[int(r["event_id"])]
        if eval_by_event.get(int(r["event_id"]), 0) > 0:
            c["events_with_official_eval"] += 1
            c["official_eval_rows"] += eval_by_event[int(r["event_id"])]

    rows = [{"event_day_local": k, **dict(v)} for k, v in sorted(by_day.items())]

    overall = Counter()
    for r in rows:
        overall.update({k: int(v or 0) for k, v in r.items() if k != "event_day_local"})

    files = []
    p1 = outdir / "01_lineage_universe_by_day.csv"
    _write_csv(p1, rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "01_lineage_universe_summary.json"
    _write_json(p2, {"by_day": rows, "overall": dict(overall)})
    files.append(_relative_to_repo(p2))

    return BlockResult(
        name="lineage_universe",
        ok=True,
        files=files,
        summary={
            "events_total": overall["events_total"],
            "events_with_raw_latest": overall["events_with_raw_latest"],
            "events_unresolved": overall["events_unresolved"],
            "events_score_mismatch": overall["events_score_mismatch"],
            "picks_total": overall["picks_total"],
            "official_eval_rows": overall["official_eval_rows"],
        },
    )


def block_02_raw_freshness(outdir: Path, event_rows: Sequence[Mapping[str, Any]], sample_limit: int) -> BlockResult:
    by_day: dict[str, Counter[str]] = defaultdict(Counter)
    samples: list[dict[str, Any]] = []
    for r in event_rows:
        day = str(r["event_day_local"])
        c = by_day[day]
        c["events_total"] += 1
        raw_at = r.get("raw_latest_fetched_at")
        if raw_at is None:
            c["raw_missing"] += 1
            samples.append({**r, "anomaly_code": "RAW_MISSING"})
            continue
        c["raw_present"] += 1
        if int(r.get("raw_row_count") or 0) > 1:
            c["raw_multirow"] += 1
        mk = r.get("minutes_kickoff_to_raw_latest")
        mr = r.get("minutes_raw_latest_to_event_update")
        if isinstance(mk, (int, float)) and mk >= 0:
            c["raw_after_kickoff"] += 1
        if isinstance(mk, (int, float)) and mk >= 60:
            c["raw_after_kickoff_ge_60m"] += 1
        if isinstance(mr, (int, float)) and mr >= 60:
            c["event_update_ge_60m_after_raw"] += 1
            samples.append({**r, "anomaly_code": "EVENT_UPDATED_LONG_AFTER_RAW"})
        elif isinstance(mr, (int, float)) and mr <= -60:
            c["raw_newer_than_event_ge_60m"] += 1
            samples.append({**r, "anomaly_code": "RAW_NEWER_THAN_EVENT"})

    rows = [{"event_day_local": k, **dict(v)} for k, v in sorted(by_day.items())]
    samples = samples[:sample_limit]

    files = []
    p1 = outdir / "02_raw_latest_freshness_by_day.csv"
    _write_csv(p1, rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "02_raw_latest_freshness_samples.csv"
    _write_csv(p2, samples)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "02_raw_latest_freshness_summary.json"
    _write_json(p3, {"by_day": rows, "samples": samples})
    files.append(_relative_to_repo(p3))

    raw_missing = sum(int(r.get("raw_missing") or 0) for r in rows)
    lagged_updates = sum(int(r.get("event_update_ge_60m_after_raw") or 0) for r in rows)
    return BlockResult(
        name="raw_latest_freshness",
        ok=True,
        files=files,
        summary={"raw_missing": raw_missing, "event_update_ge_60m_after_raw": lagged_updates, "sample_rows": len(samples)},
    )


def block_03_raw_vs_events_consistency(outdir: Path, event_rows: Sequence[Mapping[str, Any]], sample_limit: int) -> BlockResult:
    by_day: dict[str, Counter[str]] = defaultdict(Counter)
    samples: list[dict[str, Any]] = []
    interesting_codes = {"raw_only", "event_only", "mismatch"}
    for r in event_rows:
        day = str(r["event_day_local"])
        c = by_day[day]
        c["events_total"] += 1
        c[f"score_relation__{r['score_relation']}"] += 1
        c[f"status_relation__{r['status_relation']}"] += 1
        if r["score_relation"] in interesting_codes or r["status_relation"] == "mismatch":
            sample = dict(r)
            sample["anomaly_code"] = ",".join(
                part
                for part in [
                    f"SCORE_{r['score_relation'].upper()}" if r["score_relation"] in interesting_codes else "",
                    "STATUS_MISMATCH" if r["status_relation"] == "mismatch" else "",
                ]
                if part
            )
            samples.append(sample)

    rows = [{"event_day_local": k, **dict(v)} for k, v in sorted(by_day.items())]
    samples = samples[:sample_limit]

    files = []
    p1 = outdir / "03_raw_vs_bt2_events_consistency_by_day.csv"
    _write_csv(p1, rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "03_raw_vs_bt2_events_consistency_samples.csv"
    _write_csv(p2, samples)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "03_raw_vs_bt2_events_consistency_summary.json"
    _write_json(p3, {"by_day": rows, "samples": samples})
    files.append(_relative_to_repo(p3))

    counter = Counter()
    for r in event_rows:
        counter[f"score_relation__{r['score_relation']}"] += 1
        counter[f"status_relation__{r['status_relation']}"] += 1
    return BlockResult(
        name="raw_vs_events_consistency",
        ok=True,
        files=files,
        summary={
            "score_raw_only": counter["score_relation__raw_only"],
            "score_event_only": counter["score_relation__event_only"],
            "score_mismatch": counter["score_relation__mismatch"],
            "status_mismatch": counter["status_relation__mismatch"],
            "sample_rows": len(samples),
        },
    )


def block_04_pick_operating_day_alignment(outdir: Path, pick_rows: Sequence[Mapping[str, Any]], sample_limit: int) -> BlockResult:
    by_day: dict[str, Counter[str]] = defaultdict(Counter)
    by_bucket: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []

    for r in pick_rows:
        delta = _days_delta(r.get("operating_day_key"), r.get("event_day_local"))
        bucket = _bucket_delta(delta)
        op_day = str(r.get("operating_day_key"))
        by_day[op_day]["picks_total"] += 1
        by_day[op_day][f"delta_bucket__{bucket}"] += 1
        by_bucket[bucket] += 1

        if bucket != "same_day":
            sample = dict(r)
            sample["delta_days"] = delta
            sample["delta_bucket"] = bucket
            samples.append(sample)

    rows = [{"operating_day_key": k, **dict(v)} for k, v in sorted(by_day.items())]
    bucket_rows = [{"delta_bucket": k, "picks_count": v} for k, v in sorted(by_bucket.items())]
    samples = samples[:sample_limit]

    files = []
    p1 = outdir / "04_pick_operating_day_alignment_by_operating_day.csv"
    _write_csv(p1, rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "04_pick_operating_day_alignment_buckets.csv"
    _write_csv(p2, bucket_rows)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "04_pick_operating_day_alignment_samples.csv"
    _write_csv(p3, samples)
    files.append(_relative_to_repo(p3))
    p4 = outdir / "04_pick_operating_day_alignment_summary.json"
    _write_json(p4, {"by_operating_day": rows, "by_bucket": bucket_rows, "samples": samples})
    files.append(_relative_to_repo(p4))

    return BlockResult(
        name="pick_operating_day_alignment",
        ok=True,
        files=files,
        summary={
            "picks_total": len(pick_rows),
            "same_day": by_bucket["same_day"],
            "not_same_day": len(pick_rows) - by_bucket["same_day"],
            "sample_rows": len(samples),
        },
    )


def block_05_eval_vs_lineage_state(outdir: Path, pick_rows: Sequence[Mapping[str, Any]], event_index: Mapping[int, Mapping[str, Any]], sample_limit: int) -> BlockResult:
    by_status: dict[str, Counter[str]] = defaultdict(Counter)
    samples: list[dict[str, Any]] = []

    for r in pick_rows:
        status = str(r.get("evaluation_status") or "(missing)")
        c = by_status[status]
        c["picks_total"] += 1

        ev = event_index.get(int(r["event_id"]))
        if ev:
            if ev.get("event_unresolved_flag"):
                c["event_unresolved"] += 1
            if ev.get("score_relation") == "raw_only":
                c["raw_has_score_event_missing_score"] += 1
            if ev.get("score_relation") == "mismatch":
                c["raw_event_score_mismatch"] += 1
            if ev.get("raw_latest_fetched_at") is None:
                c["raw_missing"] += 1

            weird = False
            if status in ("evaluated_hit", "evaluated_miss", "void") and ev.get("event_unresolved_flag"):
                weird = True
            if status == "pending_result" and ev.get("raw_has_score_guess"):
                weird = True
            if status == "no_evaluable" and ev.get("raw_has_score_guess"):
                weird = True
            if weird:
                sample = dict(r)
                sample.update(
                    {
                        "event_unresolved_flag": ev.get("event_unresolved_flag"),
                        "score_relation": ev.get("score_relation"),
                        "status_relation": ev.get("status_relation"),
                        "raw_has_score_guess": ev.get("raw_has_score_guess"),
                        "raw_status_guess": ev.get("raw_status_guess"),
                        "raw_score_home_guess": ev.get("raw_score_home_guess"),
                        "raw_score_away_guess": ev.get("raw_score_away_guess"),
                    }
                )
                sample["anomaly_code"] = (
                    "EVAL_DONE_ON_UNRESOLVED_EVENT"
                    if status in ("evaluated_hit", "evaluated_miss", "void") and ev.get("event_unresolved_flag")
                    else "PENDING_OR_NO_EVALUABLE_WHILE_RAW_HAS_SCORE"
                )
                samples.append(sample)

    rows = [{"evaluation_status": k, **dict(v)} for k, v in sorted(by_status.items())]
    samples = samples[:sample_limit]

    files = []
    p1 = outdir / "05_official_eval_vs_lineage_state.csv"
    _write_csv(p1, rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "05_official_eval_vs_lineage_state_samples.csv"
    _write_csv(p2, samples)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "05_official_eval_vs_lineage_state_summary.json"
    _write_json(p3, {"by_status": rows, "samples": samples})
    files.append(_relative_to_repo(p3))

    weird_total = len(samples)
    return BlockResult(
        name="official_eval_vs_lineage_state",
        ok=True,
        files=files,
        summary={
            "evaluation_status_groups": len(rows),
            "sample_rows": weird_total,
            "scored_statuses": sum(int(r.get("picks_total") or 0) for r in rows if r["evaluation_status"] in ("evaluated_hit", "evaluated_miss")),
        },
    )



def block_06_provider_vs_consolidated(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int, providers: Sequence[str]) -> BlockResult:
    provider_filter_sql, provider_params = _providers_sql_filter("pos.provider", providers)

    inventory_sql = _base_events_cte() + """
    SELECT
      COALESCE(pos.provider, '(null)') AS provider,
      COALESCE(pos.source_scope, '(null)') AS source_scope,
      COUNT(*)::int AS rows_count,
      COUNT(DISTINCT pos.bt2_event_id)::int AS distinct_events
    FROM bt2_provider_odds_snapshot pos
    INNER JOIN base_events be ON be.id = pos.bt2_event_id
    GROUP BY COALESCE(pos.provider, '(null)'), COALESCE(pos.source_scope, '(null)')
    ORDER BY distinct_events DESC, provider, source_scope;
    """
    inventory_rows = _fetchall(cur, inventory_sql, [date_from, date_to])

    sql = _base_events_cte() + f"""
    , provider_cov AS (
      SELECT
        pos.bt2_event_id AS event_id,
        COUNT(*)::int AS provider_rows,
        COUNT(DISTINCT pos.provider)::int AS provider_count,
        ARRAY_AGG(DISTINCT pos.provider) FILTER (WHERE pos.provider IS NOT NULL) AS providers_seen
      FROM bt2_provider_odds_snapshot pos
      INNER JOIN base_events be ON be.id = pos.bt2_event_id
      WHERE 1=1 {provider_filter_sql}
      GROUP BY pos.bt2_event_id
    ),
    snapshot_cov AS (
      SELECT
        os.event_id,
        COUNT(*)::int AS snapshot_rows,
        COUNT(DISTINCT os.bookmaker)::int AS bookmaker_count,
        COUNT(DISTINCT os.market)::int AS market_count
      FROM bt2_odds_snapshot os
      INNER JOIN base_events be ON be.id = os.event_id
      GROUP BY os.event_id
    )
    SELECT
      be.id AS event_id,
      be.event_day_local,
      be.kickoff_utc,
      be.status,
      be.result_home,
      be.result_away,
      COALESCE(pc.provider_rows, 0) AS provider_rows,
      COALESCE(pc.provider_count, 0) AS provider_count,
      pc.providers_seen,
      COALESCE(sc.snapshot_rows, 0) AS snapshot_rows,
      COALESCE(sc.bookmaker_count, 0) AS bookmaker_count,
      COALESCE(sc.market_count, 0) AS market_count
    FROM base_events be
    LEFT JOIN provider_cov pc ON pc.event_id = be.id
    LEFT JOIN snapshot_cov sc ON sc.event_id = be.id
    ORDER BY be.event_day_local, be.kickoff_utc, be.id;
    """
    rows = _fetchall(cur, sql, [date_from, date_to, *provider_params])

    inventory_total_rows = sum(int(r.get("rows_count") or 0) for r in inventory_rows)
    inventory_total_events = sum(int(r.get("distinct_events") or 0) for r in inventory_rows)
    filter_has_any_rows = any(int(r.get("provider_rows") or 0) > 0 for r in rows)

    by_day: dict[str, Counter[str]] = defaultdict(Counter)
    samples: list[dict[str, Any]] = []
    filter_empty_samples: list[dict[str, Any]] = []

    for r in rows:
        day = str(r["event_day_local"])
        c = by_day[day]
        c["events_total"] += 1
        provider_rows = int(r.get("provider_rows") or 0)
        snapshot_rows = int(r.get("snapshot_rows") or 0)

        if provider_rows > 0 and snapshot_rows > 0:
            c["both_present"] += 1
        elif provider_rows == 0 and snapshot_rows == 0:
            c["both_missing"] += 1
        elif provider_rows == 0 and snapshot_rows > 0:
            if not providers or filter_has_any_rows:
                c["snapshot_without_provider_raw"] += 1
                samples.append({**r, "anomaly_code": "SNAPSHOT_WITHOUT_PROVIDER_RAW"})
            else:
                c["snapshot_without_provider_raw_filter_empty"] += 1
                filter_empty_samples.append({**r, "anomaly_code": "SNAPSHOT_WITHOUT_PROVIDER_RAW_FILTER_EMPTY"})
        elif provider_rows > 0 and snapshot_rows == 0:
            c["provider_raw_without_snapshot"] += 1
            samples.append({**r, "anomaly_code": "PROVIDER_RAW_WITHOUT_SNAPSHOT"})

    by_day_rows = [{"event_day_local": k, **dict(v)} for k, v in sorted(by_day.items())]
    samples = samples[:sample_limit]
    filter_empty_samples = filter_empty_samples[:sample_limit]

    files = []
    p1 = outdir / "06_provider_vs_consolidated_by_day.csv"
    _write_csv(p1, by_day_rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "06_provider_vs_consolidated_event_samples.csv"
    _write_csv(p2, samples)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "06_provider_inventory_for_base_events.csv"
    _write_csv(p3, inventory_rows)
    files.append(_relative_to_repo(p3))
    p4 = outdir / "06_provider_vs_consolidated_summary.json"
    _write_json(
        p4,
        {
            "provider_inventory": inventory_rows,
            "filter_values": list(providers),
            "filter_has_any_rows": filter_has_any_rows,
            "by_day": by_day_rows,
            "samples": samples,
            "filter_empty_samples": filter_empty_samples,
        },
    )
    files.append(_relative_to_repo(p4))

    return BlockResult(
        name="provider_vs_consolidated_odds",
        ok=True,
        files=files,
        summary={
            "events_total": len(rows),
            "provider_inventory_rows_total": inventory_total_rows,
            "provider_inventory_events_total": inventory_total_events,
            "filter_has_any_rows": filter_has_any_rows,
            "snapshot_without_provider_raw": sum(int(r.get("snapshot_without_provider_raw") or 0) for r in by_day_rows),
            "snapshot_without_provider_raw_filter_empty": sum(int(r.get("snapshot_without_provider_raw_filter_empty") or 0) for r in by_day_rows),
            "provider_raw_without_snapshot": sum(int(r.get("provider_raw_without_snapshot") or 0) for r in by_day_rows),
            "sample_rows": len(samples),
        },
    )

def block_07_sfs_shadow_lineage(cur: Any, date_from: str, date_to: str, outdir: Path, sample_limit: int, pick_rows: Sequence[Mapping[str, Any]]) -> BlockResult:
    sql = _base_events_cte() + _latest_sfs_join_cte() + """
    , shadow_cov AS (
      SELECT
        ds.bt2_event_id AS event_id,
        COUNT(*)::int AS shadow_rows,
        MAX(ds.created_at) AS latest_shadow_created_at
      FROM bt2_dsr_ds_input_shadow ds
      INNER JOIN base_events be ON be.id = ds.bt2_event_id
      GROUP BY ds.bt2_event_id
    )
    SELECT
      be.id AS event_id,
      be.event_day_local,
      be.kickoff_utc,
      be.sofascore_event_id,
      COALESCE(sl.match_status, '(missing)') AS sfs_match_status,
      sl.match_layer,
      sl.run_id AS sfs_run_id,
      sl.created_at AS sfs_created_at,
      COALESCE(sc.shadow_rows, 0) AS shadow_rows,
      sc.latest_shadow_created_at
    FROM base_events be
    LEFT JOIN sfs_latest sl ON sl.bt2_event_id = be.id
    LEFT JOIN shadow_cov sc ON sc.event_id = be.id
    ORDER BY be.event_day_local, be.kickoff_utc, be.id;
    """
    rows = _fetchall(cur, sql, [date_from, date_to])

    pick_counts: Counter[int] = Counter(int(r["event_id"]) for r in pick_rows)
    by_day: dict[str, Counter[str]] = defaultdict(Counter)
    samples: list[dict[str, Any]] = []

    for r in rows:
        day = str(r["event_day_local"])
        c = by_day[day]
        c["events_total"] += 1
        if r.get("sofascore_event_id") is not None:
            c["events_with_sofascore_id_on_event"] += 1
        if r.get("sfs_match_status") != "(missing)":
            c["events_with_sfs_join_record"] += 1
        if str(r.get("sfs_match_status") or "").lower() == "matched":
            c["events_sfs_matched_latest"] += 1
        if int(r.get("shadow_rows") or 0) > 0:
            c["events_with_shadow"] += 1
        if pick_counts.get(int(r["event_id"]), 0) > 0:
            c["events_with_picks"] += 1
            if str(r.get("sfs_match_status") or "").lower() != "matched":
                c["events_with_picks_but_sfs_not_matched"] += 1
                samples.append({**r, "pick_count": pick_counts[int(r["event_id"])], "anomaly_code": "PICKS_WITHOUT_STRONG_SFS_SUPPORT"})
            elif int(r.get("shadow_rows") or 0) == 0:
                c["events_with_picks_but_no_shadow"] += 1

    by_day_rows = [{"event_day_local": k, **dict(v)} for k, v in sorted(by_day.items())]
    samples = samples[:sample_limit]

    files = []
    p1 = outdir / "07_sfs_shadow_lineage_by_day.csv"
    _write_csv(p1, by_day_rows)
    files.append(_relative_to_repo(p1))
    p2 = outdir / "07_sfs_shadow_lineage_samples.csv"
    _write_csv(p2, samples)
    files.append(_relative_to_repo(p2))
    p3 = outdir / "07_sfs_shadow_lineage_summary.json"
    _write_json(p3, {"by_day": by_day_rows, "samples": samples})
    files.append(_relative_to_repo(p3))

    return BlockResult(
        name="sfs_shadow_lineage",
        ok=True,
        files=files,
        summary={
            "events_total": len(rows),
            "events_sfs_matched_latest": sum(int(r.get("events_sfs_matched_latest") or 0) for r in by_day_rows),
            "events_with_shadow": sum(int(r.get("events_with_shadow") or 0) for r in by_day_rows),
            "sample_rows": len(samples),
        },
    )


# ---------------------------------------------------------------------------
# Findings / runbook helpers
# ---------------------------------------------------------------------------


def _build_findings(results: Sequence[BlockResult]) -> list[dict[str, Any]]:
    idx = {r.name: r for r in results}
    findings: list[dict[str, Any]] = []

    coverage = idx.get("range_coverage")
    if coverage and coverage.summary.get("events_total", 0) == 0 and coverage.summary.get("picks_total", 0) > 0:
        findings.append(
            {
                "severity": "medium",
                "code": "RANGE_EMPTY_ON_EVENT_LENS_BUT_HAS_PICKS",
                "message": "El rango está vacío en bt2_events por kickoff local, pero sí tiene bt2_daily_picks por operating_day_key. Esa ventana no debe interpretarse solo desde el lente de kickoff.",
                "evidence_hint": "Revisar bloque 00.",
            }
        )

    consistency = idx.get("raw_vs_events_consistency")
    if consistency and consistency.summary.get("score_raw_only", 0) > 0:
        findings.append(
            {
                "severity": "high",
                "code": "RAW_HAS_SCORE_BUT_BT2_EVENT_DOES_NOT",
                "message": "Hay eventos donde el latest raw parece traer marcador pero bt2_events no lo materializó. Eso apunta a drift de CDM/materialización más que a ausencia de proveedor.",
                "evidence_hint": "Revisar bloque 03.",
            }
        )
    if consistency and consistency.summary.get("score_mismatch", 0) > 0:
        findings.append(
            {
                "severity": "high",
                "code": "RAW_AND_BT2_EVENT_SCORE_MISMATCH",
                "message": "Hay eventos con score raw y score CDM, pero no coinciden. Antes de discutir edge, hay que resolver la fuente de verdad y la cadena de actualización.",
                "evidence_hint": "Revisar bloque 03.",
            }
        )
    if consistency and consistency.summary.get("status_mismatch", 0) > 0:
        findings.append(
            {
                "severity": "medium",
                "code": "RAW_AND_BT2_EVENT_STATUS_MISMATCH",
                "message": "Hay drift de estado entre latest raw y bt2_events. Eso puede explicar scheduled stale o finished sin score.",
                "evidence_hint": "Revisar bloque 03.",
            }
        )

    eval_state = idx.get("official_eval_vs_lineage_state")
    if eval_state and eval_state.summary.get("sample_rows", 0) > 0:
        findings.append(
            {
                "severity": "high",
                "code": "OFFICIAL_EVAL_WEIRD_VS_LINEAGE_STATE",
                "message": "Existen picks con evaluation_status difícil de reconciliar con el estado/score del evento o del raw latest. Eso sugiere revisar cuándo y cómo se está resolviendo la evaluación oficial.",
                "evidence_hint": "Revisar bloque 05.",
            }
        )

    align = idx.get("pick_operating_day_alignment")
    if align and align.summary.get("not_same_day", 0) > 0:
        findings.append(
            {
                "severity": "medium",
                "code": "OPERATING_DAY_AND_EVENT_DAY_DRIFT",
                "message": "Hay picks cuyo operating_day_key no coincide con el día local de kickoff del evento. Eso importa para comparar replay, bóveda y ventanas históricas.",
                "evidence_hint": "Revisar bloque 04 y bloque 00.",
            }
        )

    odds = idx.get("provider_vs_consolidated_odds")
    if odds and odds.summary.get("provider_raw_without_snapshot", 0) > 0:
        findings.append(
            {
                "severity": "high",
                "code": "PROVIDER_RAW_EXISTS_BUT_CONSOLIDATED_SNAPSHOT_MISSING",
                "message": "Hay eventos con raw odds por proveedor pero sin bt2_odds_snapshot consolidado. Eso apunta a problema de materialización/transformación, no necesariamente a falta de proveedor.",
                "evidence_hint": "Revisar bloque 06.",
            }
        )
    if (
        odds
        and odds.summary.get("snapshot_without_provider_raw", 0) > 0
        and odds.summary.get("filter_has_any_rows", True)
    ):
        findings.append(
            {
                "severity": "medium",
                "code": "SNAPSHOT_EXISTS_WITHOUT_PROVIDER_RAW",
                "message": "Hay eventos con bt2_odds_snapshot pero sin evidencia raw por proveedor en staging. Eso sugiere una ruta paralela o staging incompleto; útil para decidir si provider_odds es crítico o secundario.",
                "evidence_hint": "Revisar bloque 06.",
            }
        )

    sfs = idx.get("sfs_shadow_lineage")
    if sfs and sfs.summary.get("events_with_shadow", 0) == 0:
        findings.append(
            {
                "severity": "medium",
                "code": "NO_DS_INPUT_SHADOW_IN_RANGE",
                "message": "No hay ds_input shadow útil en el rango. El experimento S6.5 no aporta trazabilidad suficiente para diagnosticar esta ventana.",
                "evidence_hint": "Revisar bloque 07.",
            }
        )

    return findings


def _write_runbook(outdir: Path, args: argparse.Namespace, results: Sequence[BlockResult], findings: Sequence[dict[str, Any]]) -> Path:
    lines = [
        "# BT2 Phase 2 Lineage Audit — guía rápida de lectura",
        "",
        f"Rango auditado: {args.date_from} → {args.date_to}",
        f"Lente principal de evento: kickoff local {DEFAULT_TIMEZONE}",
        f"Providers filter: {', '.join(args.providers) if args.providers else '(todos)'}",
        "",
        "## Qué responde esta fase",
        "- ¿El problema nace en el raw latest, en bt2_events, en la materialización de odds, en la evaluación oficial o en el lente de fechas?",
        "- ¿Hay drift entre raw latest y bt2_events?",
        "- ¿El operating_day_key de picks se alinea con el kickoff local del evento?",
        "- ¿Hay picks ya evaluados aunque el evento siga unresolved en CDM?",
        "- ¿Hay raw provider odds sin snapshot consolidado, o snapshot consolidado sin staging raw?",
        "",
        "## Orden sugerido de revisión",
        "1. 00_range_coverage_summary.json",
        "2. 03_raw_vs_bt2_events_consistency_summary.json",
        "3. 05_official_eval_vs_lineage_state_summary.json",
        "4. 04_pick_operating_day_alignment_summary.json",
        "5. 06_provider_vs_consolidated_summary.json",
        "6. 07_sfs_shadow_lineage_summary.json",
        "7. 02_raw_latest_freshness_summary.json",
        "",
        "## Qué significa cada bloque",
        "- 00: cobertura del rango en ambos lentes (event kickoff vs operating_day).",
        "- 01: universo de eventos y cuánta trazabilidad real tienen.",
        "- 02: frescura raw latest y señales de lag entre raw y actualización CDM.",
        "- 03: consistencia raw latest vs bt2_events.",
        "- 04: drift entre operating_day_key y kickoff local del evento.",
        "- 05: evaluación oficial comparada contra el estado real de lineage.",
        "- 06: paridad entre raw odds por proveedor y bt2_odds_snapshot consolidado.",
        "- 07: cuánto aporta realmente SFS/shadow a la trazabilidad del rango.",
        "",
        "## Findings automáticos",
    ]
    if findings:
        for f in findings:
            lines.append(f"- [{f['severity']}] {f['code']}: {f['message']} ({f['evidence_hint']})")
    else:
        lines.append("- No se detectaron flags automáticos por umbral simple. Igual revisa los CSV/JSON.")
    lines.extend(["", "## Artefactos generados"])
    for result in results:
        lines.append(f"- {result.name}: {', '.join(result.files)}")

    path = outdir / "README.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BT2 Phase 2 read-only lineage audit")
    parser.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD")
    parser.add_argument("--outdir", default="out/bt2_phase2_audit", help="Output base dir (default: out/bt2_phase2_audit)")
    parser.add_argument("--providers", default="", help="Comma-separated provider filter for provider-odds parity block")
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
        "range": {"from": args.date_from, "to": args.date_to},
        "providers_filter": args.providers,
        "sample_limit": args.sample_limit,
        "db": _sanitize_dsn(db_url),
        "notes": [
            "All blocks are read-only.",
            "Main event lens = bt2_events.kickoff_utc rendered as local date in America/Bogota.",
            "Block 00 also audits bt2_daily_picks.operating_day_key to avoid false conclusions on empty event windows.",
            "Provider filter only affects block 06.",
        ],
    }
    _write_json(outdir / "00_manifest.json", manifest)

    coverage = load_range_coverage_rows(cur, args.date_from, args.date_to)
    event_rows = load_event_lineage_rows(cur, args.date_from, args.date_to)
    pick_rows = load_pick_lineage_rows(cur, args.date_from, args.date_to)
    event_index = {int(r["event_id"]): r for r in event_rows}

    blocks: list[tuple[str, Any]] = [
        ("range_coverage", lambda: block_00_range_coverage(outdir, coverage)),
        ("lineage_universe", lambda: block_01_lineage_universe(outdir, event_rows, pick_rows)),
        ("raw_latest_freshness", lambda: block_02_raw_freshness(outdir, event_rows, args.sample_limit)),
        ("raw_vs_events_consistency", lambda: block_03_raw_vs_events_consistency(outdir, event_rows, args.sample_limit)),
        ("pick_operating_day_alignment", lambda: block_04_pick_operating_day_alignment(outdir, pick_rows, args.sample_limit)),
        ("official_eval_vs_lineage_state", lambda: block_05_eval_vs_lineage_state(outdir, pick_rows, event_index, args.sample_limit)),
        ("provider_vs_consolidated_odds", lambda: block_06_provider_vs_consolidated(cur, args.date_from, args.date_to, outdir, args.sample_limit, args.providers)),
        ("sfs_shadow_lineage", lambda: block_07_sfs_shadow_lineage(cur, args.date_from, args.date_to, outdir, args.sample_limit, pick_rows)),
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

    print("=== BT2 PHASE 2 LINEAGE AUDIT ===")
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

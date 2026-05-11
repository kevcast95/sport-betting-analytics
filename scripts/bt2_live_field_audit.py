#!/usr/bin/env python3
"""
BT2 live field audit, shadow-only.

Writes artifacts only:
- scripts/outputs/live_field_coverage_YYYY-MM-DD.json
- scripts/outputs/live_field_ds_inputs_YYYY-MM-DD.json
- scripts/outputs/live_field_dsr_outputs_YYYY-MM-DD.json
- docs/bettracker2/audits/LIVE_FIELD_AUDIT_YYYY-MM-DD.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_dsr_context_queries import extract_lineups_summary_from_raw_payload
from apps.api.bt2_dsr_shadow_native_prompt_v6 import (
    DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
    SYSTEM_PROMPT_SHADOW_NATIVE_V6,
    build_user_prompt_shadow_native_v6,
)
from apps.api.bt2_dsr_shadow_native_deepseek_v6 import (
    deepseek_suggest_batch_shadow_native_v6_with_trace,
    narrative_extract_rationale_v6,
)
from apps.api.bt2_dsr_ds_input_builder import build_ds_input_item
from apps.api.bt2_dsr_contract import PIPELINE_VERSION_DEFAULT
from apps.api.bt2_dsr_ds_input_sm_fixture_blocks import merge_sm_optional_fixture_blocks
from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds, aggregate_odds_for_event
from apps.api.bt2_dsr_postprocess import postprocess_dsr_pick
from apps.api.bt2_dsr_sm_statistics import (
    merge_sm_statistics_into_processed_statistics,
    sm_fixture_statistics_block,
)
from apps.api.bt2_f2_league_constants import F2_OFFICIAL_LEAGUE_DISPLAY_ORDER
from apps.api.bt2_fixture_prob_coherence import prob_coherence_dict_for_ds_input
from apps.api.bt2_settings import bt2_settings


TOA_BASE = "https://api.the-odds-api.com/v4"
MARKET_KEYS = (
    "FT_1X2",
    "BTTS",
    "OU_GOALS_2_5",
    "OU_GOALS_1_5",
    "OU_GOALS_3_5",
    "DOUBLE_CHANCE_1X",
    "DOUBLE_CHANCE_X2",
    "DOUBLE_CHANCE_12",
)
TOA_SPORT_KEYS = {
    8: "soccer_epl",
    564: "soccer_spain_la_liga",
    384: "soccer_italy_serie_a",
    82: "soccer_germany_bundesliga",
    301: "soccer_france_ligue_one",
}
ALT_TOA_SPORT_KEYS = {301: "soccer_france_ligue_1"}
LEAKAGE_TERMS = (
    "score",
    "scores",
    "result_home",
    "result_away",
    "fulltime",
    "full_time",
    "finished",
    "corners",
    "statistics",
    "pressure",
    "matchfacts",
)


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1)


def _jsonable(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, AggregatedOdds):
        return {
            "consensus": v.consensus,
            "market_coverage": v.market_coverage,
            "markets_available": sorted(v.markets_available),
        }
    if isinstance(v, dict):
        return {str(k): _jsonable(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def _norm(s: Any) -> str:
    x = unicodedata.normalize("NFKD", str(s or "").strip())
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = re.sub(r"[^a-zA-Z0-9]+", " ", x).strip().lower()
    return re.sub(r"\s+", " ", x)


def _parse_dt(raw: Any) -> Optional[datetime]:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _http_json(url: str, params: dict[str, Any], external_calls: list[dict[str, Any]]) -> tuple[Any, dict[str, str], int]:
    qs = urlencode(params, doseq=True)
    full_url = f"{url}?{qs}"
    safe_params = {k: ("<redacted>" if "key" in k.lower() or "token" in k.lower() else v) for k, v in params.items()}
    call = {"method": "GET", "url": url, "params": safe_params, "status": None, "error": None}
    external_calls.append(call)
    req = Request(full_url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(req, timeout=50) as resp:
            raw = resp.read().decode("utf-8")
            headers = {k.lower(): v for k, v in resp.headers.items()}
            call["status"] = int(resp.status)
            call["response_headers_subset"] = {
                k: headers.get(k)
                for k in ("x-requests-used", "x-requests-remaining", "x-requests-last")
                if headers.get(k) is not None
            }
            return json.loads(raw), headers, int(resp.status)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:800]
        call["status"] = int(exc.code)
        call["error"] = body
        return {"_http_error": exc.code, "body": body}, {}, int(exc.code)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        call["error"] = type(exc).__name__ + ": " + str(exc)
        return {"_error": str(exc)}, {}, 0


def _resolve_operating_leagues(cur: Any) -> list[dict[str, Any]]:
    sm_ids = [x[2] for x in F2_OFFICIAL_LEAGUE_DISPLAY_ORDER]
    cur.execute(
        """
        SELECT id, name, country, tier, is_active, sportmonks_id
        FROM bt2_leagues
        WHERE sportmonks_id = ANY(%s::int[])
        ORDER BY sportmonks_id
        """,
        (sm_ids,),
    )
    by_sm = {int(r["sportmonks_id"]): dict(r) for r in cur.fetchall()}
    out: list[dict[str, Any]] = []
    for key, display, sm_id in F2_OFFICIAL_LEAGUE_DISPLAY_ORDER:
        row = by_sm.get(sm_id)
        out.append(
            {
                "key": key,
                "configured_display_name": display,
                "sportmonks_id": sm_id,
                "toa_sport_key": TOA_SPORT_KEYS.get(sm_id),
                "bt2_league_id": int(row["id"]) if row else None,
                "db_name": row.get("name") if row else "UNKNOWN",
                "country": row.get("country") if row else None,
                "tier": row.get("tier") if row else None,
                "is_active": bool(row.get("is_active")) if row else None,
                "resolved": bool(row),
                "resolution_source": "apps/api/bt2_f2_league_constants.py + bt2_leagues.sportmonks_id",
            }
        )
    return out


def _fixture_participants(payload: dict[str, Any]) -> tuple[str, str]:
    home = away = ""
    parts = payload.get("participants")
    if isinstance(parts, list):
        for p in parts:
            if not isinstance(p, dict):
                continue
            loc = str((p.get("meta") or {}).get("location") or p.get("location") or "").lower()
            if loc == "home":
                home = str(p.get("name") or p.get("display_name") or home)
            elif loc == "away":
                away = str(p.get("name") or p.get("display_name") or away)
    return home, away


def _included_payload_keys(payload: dict[str, Any]) -> list[str]:
    keys = []
    for k in (
        "league",
        "participants",
        "state",
        "venue",
        "weatherReport",
        "lineups",
        "statistics",
        "referees",
        "coaches",
        "sidelined",
        "formations",
        "expectedLineups",
        "predictions",
        "pressure",
        "matchfacts",
        "xGFixture",
        "AIOverviews",
    ):
        v = payload.get(k)
        if v not in (None, [], {}):
            keys.append(k)
    return keys


def _fetch_sm_fixtures(day: date, external_calls: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    notes: list[str] = []
    key = (bt2_settings.sportmonks_api_key or "").strip()
    if not key:
        return [], ["sm:missing_api_key"]
    url = f"https://api.sportmonks.com/v3/football/fixtures/between/{day.isoformat()}/{day.isoformat()}"
    include = (
        "league;participants;state;venue;weatherReport;lineups;statistics;"
        "referees;coaches;sidelined;formations;expectedLineups;predictions;"
        "pressure;matchfacts;xGFixture;AIOverviews"
    )
    data, _headers, status = _http_json(url, {"api_token": key, "include": include, "page": 1}, external_calls)
    if status == 403:
        notes.append("sm:full_include_403_retry_core")
        data, _headers, status = _http_json(
            url,
            {"api_token": key, "include": "league;participants;state;venue", "page": 1},
            external_calls,
        )
    if status != 200 or not isinstance(data, dict):
        return [], notes + [f"sm:http_or_parse_error_status_{status}"]
    out: list[dict[str, Any]] = []
    raw = data.get("data") or []
    if isinstance(raw, list):
        out.extend([x for x in raw if isinstance(x, dict)])
    pagination = data.get("pagination") if isinstance(data.get("pagination"), dict) else {}
    page = 1
    while pagination.get("has_more"):
        page += 1
        data, _headers, status = _http_json(url, {"api_token": key, "include": include, "page": page}, external_calls)
        if status != 200 or not isinstance(data, dict):
            notes.append(f"sm:page_{page}_failed_status_{status}")
            break
        raw = data.get("data") or []
        if isinstance(raw, list):
            out.extend([x for x in raw if isinstance(x, dict)])
        pagination = data.get("pagination") if isinstance(data.get("pagination"), dict) else {}
    notes.append(f"sm:fixtures_fetched_{len(out)}")
    return out, notes


def _fetch_toa_events(external_calls: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    key = (bt2_settings.theoddsapi_key or "").strip()
    if not key:
        return {}, ["toa:missing_api_key"]
    notes: list[str] = []
    out: dict[str, list[dict[str, Any]]] = {}
    for sm_id, sport_key in TOA_SPORT_KEYS.items():
        url = f"{TOA_BASE}/sports/{sport_key}/odds"
        params = {
            "apiKey": key,
            "regions": "us",
            "markets": "h2h,totals,btts",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        }
        data, _headers, status = _http_json(url, params, external_calls)
        if status in (400, 404, 422) and sm_id in ALT_TOA_SPORT_KEYS:
            alt_key = ALT_TOA_SPORT_KEYS[sm_id]
            notes.append(f"toa:{sport_key}_failed_{status}_retry_{alt_key}")
            sport_key = alt_key
            url = f"{TOA_BASE}/sports/{sport_key}/odds"
            data, _headers, status = _http_json(url, params | {"apiKey": key}, external_calls)
        if status in (400, 422):
            notes.append(f"toa:{sport_key}_btts_request_failed_{status}_retry_h2h_totals")
            data, _headers, status = _http_json(url, params | {"markets": "h2h,totals"}, external_calls)
        if status == 200 and isinstance(data, list):
            out[sport_key] = [x for x in data if isinstance(x, dict)]
            notes.append(f"toa:{sport_key}:events_{len(out[sport_key])}")
        else:
            out[sport_key] = []
            notes.append(f"toa:{sport_key}:status_{status}_events_0")
    return out, notes


def _market_rows_from_toa_event(ev: dict[str, Any], fetched_at: datetime) -> tuple[list[tuple[Any, ...]], dict[str, Any]]:
    rows: list[tuple[Any, ...]] = []
    market_presence = {k: False for k in MARKET_KEYS}
    market_counts: Counter[str] = Counter()
    home = str(ev.get("home_team") or "")
    away = str(ev.get("away_team") or "")
    for bm in ev.get("bookmakers") or []:
        if not isinstance(bm, dict):
            continue
        bkey = str(bm.get("key") or bm.get("title") or "unknown")
        for m in bm.get("markets") or []:
            if not isinstance(m, dict):
                continue
            key = str(m.get("key") or "").lower()
            last = _parse_dt(m.get("last_update") or bm.get("last_update")) or fetched_at
            outcomes = m.get("outcomes") if isinstance(m.get("outcomes"), list) else []
            if key == "h2h":
                for oc in outcomes:
                    if not isinstance(oc, dict):
                        continue
                    name = str(oc.get("name") or "")
                    sel = None
                    if _norm(name) == "draw":
                        sel = "Draw"
                    elif _norm(name) == _norm(home):
                        sel = "Home"
                    elif _norm(name) == _norm(away):
                        sel = "Away"
                    if sel and oc.get("price") is not None:
                        rows.append((bkey, "match winner", sel, float(oc["price"]), last))
                        market_counts["FT_1X2"] += 1
                if market_counts["FT_1X2"]:
                    market_presence["FT_1X2"] = True
            elif key == "btts":
                market_presence["BTTS"] = bool(outcomes)
                market_counts["BTTS"] += len(outcomes)
            elif key == "totals":
                points = {str(oc.get("point")) for oc in outcomes if isinstance(oc, dict)}
                for p, mk in (("1.5", "OU_GOALS_1_5"), ("2.5", "OU_GOALS_2_5"), ("3.5", "OU_GOALS_3_5")):
                    market_presence[mk] = p in points
                    if p in points:
                        market_counts[mk] += sum(1 for oc in outcomes if isinstance(oc, dict) and str(oc.get("point")) == p)
            elif key in ("double_chance", "doublechance"):
                names = {_norm(oc.get("name")) for oc in outcomes if isinstance(oc, dict)}
                market_presence["DOUBLE_CHANCE_1X"] = bool({"home draw", "home or draw", "1x"} & names)
                market_presence["DOUBLE_CHANCE_X2"] = bool({"away draw", "away or draw", "x2"} & names)
                market_presence["DOUBLE_CHANCE_12"] = bool({"home away", "home or away", "12"} & names)
                market_counts["DOUBLE_CHANCE"] += len(outcomes)
    return rows, {"market_presence": market_presence, "market_counts": dict(market_counts)}


def _match_fixture_to_toa(fx: dict[str, Any], toa_by_sport: dict[str, list[dict[str, Any]]], sport_key: str) -> tuple[Optional[dict[str, Any]], dict[str, Any]]:
    home, away = _fixture_participants(fx)
    ko = _parse_dt(fx.get("starting_at"))
    candidates = toa_by_sport.get(sport_key, [])
    best: tuple[float, Optional[dict[str, Any]], dict[str, Any]] = (0.0, None, {})
    for ev in candidates:
        ev_ko = _parse_dt(ev.get("commence_time"))
        if ko and ev_ko:
            diff_min = abs((ev_ko - ko).total_seconds()) / 60
            time_score = max(0.0, 1.0 - diff_min / 720.0)
        else:
            diff_min = None
            time_score = 0.25
        hs = SequenceMatcher(None, _norm(home), _norm(ev.get("home_team"))).ratio()
        aas = SequenceMatcher(None, _norm(away), _norm(ev.get("away_team"))).ratio()
        cross = (
            SequenceMatcher(None, _norm(home), _norm(ev.get("away_team"))).ratio()
            + SequenceMatcher(None, _norm(away), _norm(ev.get("home_team"))).ratio()
        ) / 2
        team_score = (hs + aas) / 2
        score = 0.75 * team_score + 0.25 * time_score
        method = "exact_team_time" if hs >= 0.98 and aas >= 0.98 and (diff_min is None or diff_min <= 90) else "fuzzy_team_time"
        if cross > team_score and cross > 0.86:
            method = "crossed_team_names"
            score *= 0.65
        if score > best[0]:
            best = (
                score,
                ev,
                {
                    "match_method": method,
                    "match_confidence": round(score, 4),
                    "home_similarity": round(hs, 4),
                    "away_similarity": round(aas, 4),
                    "kickoff_diff_minutes": round(diff_min, 1) if diff_min is not None else None,
                },
            )
    if best[0] >= 0.72:
        return best[1], best[2]
    return None, best[2] | {"missing_reason": "no_toa_event_above_confidence_threshold"}


def _find_bt2_event(cur: Any, sm_fixture_id: int) -> Optional[int]:
    cur.execute("SELECT id FROM bt2_events WHERE sportmonks_fixture_id = %s LIMIT 1", (sm_fixture_id,))
    r = cur.fetchone()
    return int(r["id"]) if r else None


def _signal_flags(item: dict[str, Any], sm_payload: dict[str, Any]) -> dict[str, Any]:
    proc = item.get("processed") or {}
    diag = item.get("diagnostics") or {}
    flags = {
        "odds_featured_available": bool((proc.get("odds_featured") or {}).get("consensus")),
        "lineups_available": bool((proc.get("lineups") or {}).get("available")),
        "h2h_available": bool((proc.get("h2h") or {}).get("available")),
        "statistics_available": bool((proc.get("statistics") or {}).get("available")),
        "team_streaks_available": bool((proc.get("team_streaks") or {}).get("available")),
        "team_season_stats_available": bool((proc.get("team_season_stats") or {}).get("available")),
        "fixture_conditions_available": bool((proc.get("fixture_conditions") or {}).get("available")),
        "match_officials_available": bool((proc.get("match_officials") or {}).get("available")),
        "squad_availability_available": bool((proc.get("squad_availability") or {}).get("available")),
        "tactical_shape_available": bool((proc.get("tactical_shape") or {}).get("available")),
        "prediction_signals_available": bool((proc.get("prediction_signals") or {}).get("available")),
        "fixture_advanced_sm_available": bool((proc.get("fixture_advanced_sm") or {}).get("available")),
        "market_coverage": diag.get("market_coverage") or {},
        "possible_leakage_fields": [],
        "leakage_risk": "LOW",
    }
    possible: list[str] = []
    for term in LEAKAGE_TERMS:
        if term in json.dumps(sm_payload, ensure_ascii=False).lower():
            possible.append(term)
    state = sm_payload.get("state") if isinstance(sm_payload.get("state"), dict) else {}
    state_label = str(state.get("name") or state.get("short_name") or state.get("state") or "").lower()
    if any(x in state_label for x in ("full", "finished", "ft")):
        possible.append("full time status")
    if sm_payload.get("lineups") and not any(k in json.dumps(sm_payload.get("lineups"), default=str).lower() for k in ("updated_at", "confirmed_at", "created_at")):
        possible.append("lineups_without_availability_timestamp")
    flags["possible_leakage_fields"] = sorted(set(possible))
    high_terms = {
        "score",
        "scores",
        "fulltime",
        "full_time",
        "full time status",
        "corners",
        "statistics",
        "pressure",
        "matchfacts",
        "lineups_without_availability_timestamp",
    }
    if high_terms & set(flags["possible_leakage_fields"]):
        flags["leakage_risk"] = "HIGH_RISK_LEAKAGE"
    return flags


def _build_ds_input(
    idx: int,
    fx: dict[str, Any],
    audit_row: dict[str, Any],
    agg: AggregatedOdds,
    fetched_at: datetime,
) -> dict[str, Any]:
    home, away = _fixture_participants(fx)
    ko = _parse_dt(fx.get("starting_at"))
    state = fx.get("state") if isinstance(fx.get("state"), dict) else {}
    item = build_ds_input_item(
        event_id=idx,
        selection_tier="A",
        kickoff_utc=ko,
        event_status=str(state.get("name") or state.get("short_name") or "scheduled"),
        league_name=str(audit_row.get("league") or ""),
        country=None,
        league_tier="S",
        home_team=home or str(audit_row.get("home_team") or "unknown"),
        away_team=away or str(audit_row.get("away_team") or "unknown"),
        agg=agg,
        sfs_fusion_applied=False,
        sfs_fusion_synthetic_rows=0,
    )
    processed = item["processed"]
    diag = item["diagnostics"]
    processed["odds_featured"]["ingest_meta"] = {
        "first_fetched_at_iso": fetched_at.isoformat(),
        "last_fetched_at_iso": fetched_at.isoformat(),
        "distinct_fetch_batches": 1,
    }
    lu = extract_lineups_summary_from_raw_payload(fx)
    if lu:
        processed["lineups"] = lu
        diag["lineups_ok"] = True
    sm_stats = sm_fixture_statistics_block(fx)
    if sm_stats:
        st = processed.get("statistics")
        if not isinstance(st, dict):
            st = {"available": False}
            processed["statistics"] = st
        if not st.get("available"):
            st["available"] = True
        merge_sm_statistics_into_processed_statistics(st, sm_stats)
        diag["statistics_ok"] = True
    merge_sm_optional_fixture_blocks(processed, fx)
    diag["market_coverage"] = {k: bool(audit_row.get("markets_available", {}).get(k)) for k in MARKET_KEYS}
    diag["markets_available"] = [k for k, v in diag["market_coverage"].items() if v]
    diag["prob_coherence"] = prob_coherence_dict_for_ds_input(agg.consensus)
    return item


def _consensus_favorite(consensus: dict[str, Any]) -> Optional[str]:
    ft = consensus.get("FT_1X2") if isinstance(consensus, dict) else None
    if not isinstance(ft, dict):
        return None
    vals: dict[str, float] = {}
    for k in ("home", "draw", "away"):
        try:
            vals[k] = float(ft[k])
        except (KeyError, TypeError, ValueError):
            return None
    return min(vals, key=vals.get)


def _odds_tier(consensus: dict[str, Any], side: str) -> str:
    ft = consensus.get("FT_1X2") if isinstance(consensus, dict) else None
    if not isinstance(ft, dict) or side not in ("home", "draw", "away"):
        return "n/a"
    try:
        order = sorted(("home", "draw", "away"), key=lambda k: float(ft[k]))
    except (KeyError, TypeError, ValueError):
        return "n/a"
    return ("favorite", "middle", "longshot")[order.index(side)]


def _mentions_non_odds(rationale: str) -> bool:
    s = _norm(rationale)
    return any(x in s for x in ("racha", "h2h", "lineup", "alineacion", "baja", "lesion", "estadistica", "forma", "venue", "localia", "squad", "tactical"))


def _write_markdown(path: Path, coverage: dict[str, Any], ds_inputs: dict[str, Any], dsr: dict[str, Any]) -> None:
    cov_rows = coverage.get("fixtures", [])
    pred = ds_inputs.get("predictive_clean_slice", [])
    dsr_rows = dsr.get("outputs", [])
    leagues = coverage.get("operating_leagues", [])
    market_counts = Counter()
    for r in cov_rows:
        for k, v in (r.get("markets_available") or {}).items():
            if v:
                market_counts[k] += 1
    sig_counts = Counter()
    leak_counts = Counter()
    for r in pred:
        flags = r.get("signal_flags") or {}
        for k, v in flags.items():
            if k.endswith("_available") and v:
                sig_counts[k] += 1
        leak_counts[str(flags.get("leakage_risk") or "UNKNOWN")] += 1
    fav_n = sum(1 for r in dsr_rows if r.get("favorite_benchmark", {}).get("dsr_pick_matches_favorite") is True)
    pick_n = sum(1 for r in dsr_rows if r.get("parse_status") == "ok")
    non_odds_n = sum(1 for r in dsr_rows if r.get("favorite_benchmark", {}).get("rationale_mentions_non_odds_signal"))
    lines = [
        f"# Live Field Audit 2026-04-30",
        "",
        "## 1. Executive summary",
        f"- Operating day: `{coverage.get('operating_day')}` / timezone `{coverage.get('timezone')}`.",
        f"- Fixtures SM candidatos en 5 ligas: `{len(cov_rows)}`; future al corte: `{len(coverage.get('coverage_full_day_future', []))}`; predictive clean slice: `{len(pred)}`.",
        f"- Eventos con match TOA: `{sum(1 for r in cov_rows if r.get('matched_to_toa'))}`.",
        f"- DSR outputs OK: `{pick_n}/{len(dsr_rows)}`; picks que siguen favorito: `{fav_n}/{pick_n}`.",
        f"- Racionales con señal no-cuota detectada: `{non_odds_n}/{pick_n}`.",
        "",
        "## 2. Scope and safety rules",
        "- SHADOW MODE only. No production tables written. No Telegram. No betting. No tennis.",
        "- DB access used with read-only session. Persistence is limited to this markdown and JSON artifacts.",
        f"- External calls executed: `{len(coverage.get('external_calls', []))}`; full sanitized list is in the coverage JSON.",
        "",
        "## 3. Operating leagues resolved",
    ]
    for lg in leagues:
        lines.append(f"- {lg.get('configured_display_name')}: bt2 `{lg.get('bt2_league_id')}`, SM `{lg.get('sportmonks_id')}`, TOA `{lg.get('toa_sport_key')}`, resolved `{lg.get('resolved')}`.")
    lines += [
        "",
        "## 4. SM fixture coverage",
        f"- Candidate fixtures: `{len(cov_rows)}`.",
        f"- Raw SportMonks rows available in DB before refresh: `{sum(1 for r in cov_rows if r.get('raw_sportmonks_row_available_before'))}`.",
        f"- Raw SportMonks rows available from live fetch: `{sum(1 for r in cov_rows if r.get('raw_sportmonks_row_available_live'))}`.",
        "",
        "## 5. TOA matching coverage",
        f"- Matched: `{sum(1 for r in cov_rows if r.get('matched_to_toa'))}/{len(cov_rows)}`.",
        f"- Missing odds: `{sum(1 for r in cov_rows if not r.get('matched_to_toa'))}`.",
        "",
        "## 6. Market coverage",
    ]
    for k in MARKET_KEYS:
        lines.append(f"- {k}: `{market_counts.get(k, 0)}` fixtures.")
    lines += [
        "",
        "## 7. ds_input signal coverage",
    ]
    for k, v in sorted(sig_counts.items()):
        lines.append(f"- {k}: `{v}/{len(pred)}`.")
    lines += [
        "",
        "## 8. DSR output summary",
        f"- Requested: `{dsr.get('requested')}`. Called: `{dsr.get('called')}`. Prompt version: `{dsr.get('prompt_version')}`. Model: `{dsr.get('model')}`.",
        f"- Parse status counts: `{dict(Counter(r.get('parse_status') for r in dsr_rows))}`.",
        "",
        "## 9. Favorite benchmark comparison",
        f"- DSR matched consensus favorite on `{fav_n}/{pick_n}` parsed picks.",
        "",
        "## 10. Non-odds signal usage in rationales",
        f"- Non-odds signal mentions detected on `{non_odds_n}/{pick_n}` parsed picks.",
        "",
        "## 11. Leakage risks",
        f"- Leakage flags: `{dict(leak_counts)}`.",
        "- HIGH_RISK_LEAKAGE rows should not be interpreted as clean pre-match evidence until timestamp availability is verified.",
        "",
        "## 12. Exploratory markets: BTTS / OU2.5 / Double Chance",
        f"- BTTS available in TOA payload: `{market_counts.get('BTTS', 0)}`.",
        f"- OU_GOALS_2_5 available in TOA payload: `{market_counts.get('OU_GOALS_2_5', 0)}`.",
        f"- Double Chance available in current adapter: `{market_counts.get('DOUBLE_CHANCE_1X', 0) + market_counts.get('DOUBLE_CHANCE_X2', 0) + market_counts.get('DOUBLE_CHANCE_12', 0)}` legs.",
        "- Current DSR prompt remains FT_1X2 only; other markets are exploratory availability, not forced picks.",
        "",
        "## 13. What this proves",
        "- This proves whether the live shadow flow can assemble same-day SM fixtures, TOA market coverage, ds_input structure, DSR traces, and favorite benchmark artifacts without production writes.",
        "",
        "## 14. What this does NOT prove",
        "- It does not prove betting edge, ROI, production readiness, or final model performance.",
        "- It does not validate events already started as predictive evidence.",
        "",
        "## 15. Recommended next action",
        "- Review HIGH_RISK_LEAKAGE rows and market canonicalization gaps, then rerun a clean pre-match slice with timestamped signal availability before any benchmark claims.",
        "",
        "## Central Question",
        f"- Answer: `{coverage.get('central_answer', 'See JSON artifacts')}`",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--operating-day", default="2026-04-30")
    ap.add_argument("--timezone", default="America/Bogota")
    ap.add_argument("--call-dsr", action="store_true")
    ap.add_argument("--cutoff-bogota")
    args = ap.parse_args()

    op_day = date.fromisoformat(args.operating_day)
    tz = ZoneInfo(args.timezone)
    if args.cutoff_bogota:
        cutoff_local = datetime.fromisoformat(args.cutoff_bogota).replace(tzinfo=tz)
    else:
        cutoff_local = datetime.now(tz)
    day_start_local = datetime.combine(op_day, time.min, tzinfo=tz)
    day_end_local = day_start_local + timedelta(days=1)
    day_start_utc = day_start_local.astimezone(timezone.utc)
    day_end_utc = day_end_local.astimezone(timezone.utc)
    cutoff_utc = cutoff_local.astimezone(timezone.utc)
    clean_cutoff_utc = cutoff_utc + timedelta(minutes=90)
    variant_1040_utc = datetime.combine(op_day, time(10, 40), tzinfo=tz).astimezone(timezone.utc)
    generated_at = datetime.now(timezone.utc)
    external_calls: list[dict[str, Any]] = []

    conn = psycopg2.connect(_dsn(), connect_timeout=30)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        leagues = _resolve_operating_leagues(cur)
        by_sm = {int(l["sportmonks_id"]): l for l in leagues}

        sm_payloads, sm_notes = _fetch_sm_fixtures(op_day, external_calls)
        toa_by_sport, toa_notes = _fetch_toa_events(external_calls)
        fetched_at = datetime.now(timezone.utc)

        fixtures: list[dict[str, Any]] = []
        ds_input_rows: list[dict[str, Any]] = []
        variant_rows: list[dict[str, Any]] = []
        event_seq = 1
        for fx in sm_payloads:
            sm_fid = fx.get("id")
            try:
                sm_fid_i = int(sm_fid)
            except (TypeError, ValueError):
                continue
            league_obj = fx.get("league") if isinstance(fx.get("league"), dict) else {}
            sm_league_id = fx.get("league_id") or league_obj.get("id")
            try:
                sm_league_id_i = int(sm_league_id)
            except (TypeError, ValueError):
                continue
            if sm_league_id_i not in by_sm:
                continue
            ko = _parse_dt(fx.get("starting_at"))
            if not ko or not (day_start_utc <= ko < day_end_utc):
                continue
            home, away = _fixture_participants(fx)
            state = fx.get("state") if isinstance(fx.get("state"), dict) else {}
            cur.execute("SELECT 1 FROM raw_sportmonks_fixtures WHERE fixture_id = %s LIMIT 1", (sm_fid_i,))
            raw_before = bool(cur.fetchone())
            bt2_event_id = _find_bt2_event(cur, sm_fid_i)
            sport_key = TOA_SPORT_KEYS.get(sm_league_id_i, "")
            toa_event, match_meta = _match_fixture_to_toa(fx, toa_by_sport, sport_key)
            rows: list[tuple[Any, ...]] = []
            agg = aggregate_odds_for_event([])
            toa_cov: dict[str, Any] = {"market_presence": {k: False for k in MARKET_KEYS}, "market_counts": {}}
            if toa_event:
                rows, toa_cov = _market_rows_from_toa_event(toa_event, fetched_at)
                agg = aggregate_odds_for_event(rows)
            included = _included_payload_keys(fx)
            audit_row: dict[str, Any] = {
                "sm_fixture_id": sm_fid_i,
                "bt2_event_id": bt2_event_id,
                "league": by_sm[sm_league_id_i]["configured_display_name"],
                "sm_league_id": sm_league_id_i,
                "bt2_league_id": by_sm[sm_league_id_i]["bt2_league_id"],
                "home_team": home,
                "away_team": away,
                "kickoff_utc": ko.isoformat(),
                "kickoff_bogota": ko.astimezone(tz).isoformat(),
                "fixture_status": str(state.get("name") or state.get("short_name") or "unknown"),
                "raw_sportmonks_row_available_before": raw_before,
                "raw_sportmonks_row_available_live": True,
                "included_payloads_available": included,
                "matched_to_toa": bool(toa_event),
                "match_method": match_meta.get("match_method"),
                "match_confidence": match_meta.get("match_confidence"),
                "toa_event_id": toa_event.get("id") if toa_event else None,
                "toa_sport_key": sport_key,
                "toa_event_bookmaker_coverage": len(toa_event.get("bookmakers") or []) if toa_event else 0,
                "odds_snapshot_rows": len(rows),
                "fetched_at": fetched_at.isoformat(),
                "markets_available": toa_cov["market_presence"],
                "market_row_counts": toa_cov["market_counts"],
                "missing_reason": None if toa_event else match_meta.get("missing_reason", "no_toa_match"),
                "consensus": agg.consensus,
            }
            fixtures.append(audit_row)
            if ko >= variant_1040_utc:
                variant_rows.append(audit_row)
            if ko >= clean_cutoff_utc and toa_event and rows:
                item = _build_ds_input(event_seq, fx, audit_row, agg, fetched_at)
                sig = _signal_flags(item, fx)
                ds_input_rows.append(
                    {
                        "event_sequence_id": event_seq,
                        "sm_fixture_id": sm_fid_i,
                        "bt2_event_id": bt2_event_id,
                        "kickoff_utc": ko.isoformat(),
                        "kickoff_bogota": ko.astimezone(tz).isoformat(),
                        "ds_input": item,
                        "signal_flags": sig,
                        "source_coverage_row": audit_row,
                    }
                )
                event_seq += 1

        coverage_future = [r for r in fixtures if _parse_dt(r["kickoff_utc"]) and _parse_dt(r["kickoff_utc"]) >= cutoff_utc]
        central_answer = "Insufficient clean signal evidence: no DSR slice was available."

        dsr_outputs: dict[str, Any] = {
            "generated_at_utc": generated_at.isoformat(),
            "operating_day": op_day.isoformat(),
            "requested": bool(args.call_dsr),
            "called": False,
            "model": "deepseek-v4-pro" if args.call_dsr else None,
            "prompt_version": DSR_PROMPT_VERSION_SHADOW_NATIVE_V6 if args.call_dsr else None,
            "system_prompt": SYSTEM_PROMPT_SHADOW_NATIVE_V6 if args.call_dsr else None,
            "outputs": [],
            "trace": None,
            "external_call_note": "DeepSeek /chat/completions via bt2_dsr_shadow_native_deepseek_v6" if args.call_dsr else "not_called",
        }

        if args.call_dsr and ds_input_rows:
            api_key = (bt2_settings.deepseek_api_key or "").strip()
            if not api_key:
                dsr_outputs["error"] = "missing_deepseek_api_key"
            else:
                ds_items = [r["ds_input"] for r in ds_input_rows]
                user_prompt = build_user_prompt_shadow_native_v6(
                    operating_day_key=op_day.isoformat(),
                    batch={
                        "operating_day_key": op_day.isoformat(),
                        "pipeline_version": PIPELINE_VERSION_DEFAULT,
                        "sport": "football",
                        "ds_input": ds_items,
                    },
                )
                ds_map, trace = deepseek_suggest_batch_shadow_native_v6_with_trace(
                    ds_items,
                    operating_day_key=op_day.isoformat(),
                    api_key=api_key,
                    base_url=str(bt2_settings.bt2_dsr_deepseek_base_url),
                    model="deepseek-v4-pro",
                    timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
                    max_retries=int(bt2_settings.bt2_dsr_max_retries),
                )
                dsr_outputs["called"] = True
                tr = asdict(trace)
                dsr_outputs["trace"] = {k: v for k, v in tr.items() if k != "raw_content_full"}
                dsr_outputs["raw_response"] = tr.get("raw_content_full")
                dsr_outputs["user_prompt"] = user_prompt
                for row in ds_input_rows:
                    item = row["ds_input"]
                    eid = int(item["event_id"])
                    raw = ds_map.get(eid)
                    agg_consensus = item["processed"]["odds_featured"]["consensus"]
                    favorite = _consensus_favorite(agg_consensus)
                    out = {
                        "event_id": eid,
                        "sm_fixture_id": row["sm_fixture_id"],
                        "bt2_event_id": row["bt2_event_id"],
                        "prompt_version": DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
                        "system_prompt": SYSTEM_PROMPT_SHADOW_NATIVE_V6,
                        "user_prompt": user_prompt,
                        "ds_input": item,
                        "raw_response": tr.get("raw_content_full"),
                        "parsed_response": None,
                        "parse_status": "dsr_failed",
                        "postprocess_status": "not_run",
                        "selected_market": None,
                        "selected_side": None,
                        "selected_team": None,
                        "confidence": None,
                        "rationale": None,
                        "no_pick_reason": None,
                        "favorite_benchmark": {
                            "consensus_home_odds": (agg_consensus.get("FT_1X2") or {}).get("home"),
                            "consensus_draw_odds": (agg_consensus.get("FT_1X2") or {}).get("draw"),
                            "consensus_away_odds": (agg_consensus.get("FT_1X2") or {}).get("away"),
                            "consensus_favorite_side": favorite,
                            "dsr_pick_matches_favorite": None,
                            "odds_tier": "n/a",
                            "rationale_mentions_odds_or_favorite": None,
                            "rationale_mentions_non_odds_signal": None,
                        },
                    }
                    if raw is not None:
                        narrative, conf, mmc, msc, _od = raw
                        rationale = narrative_extract_rationale_v6(narrative)
                        ec = item["event_context"]
                        pp = postprocess_dsr_pick(
                            narrative_es=rationale,
                            confidence_label=conf,
                            market_canonical=mmc,
                            selection_canonical=msc,
                            model_declared_odds=None,
                            consensus=agg_consensus,
                            market_coverage=item["diagnostics"]["market_coverage"],
                            event_id=eid,
                            home_team=str(ec.get("home_team") or ""),
                            away_team=str(ec.get("away_team") or ""),
                        )
                        out["parsed_response"] = {
                            "narrative": narrative,
                            "confidence_label": conf,
                            "market_canonical": mmc,
                            "selection_canonical": msc,
                        }
                        out["confidence"] = conf
                        out["rationale"] = rationale
                        out["no_pick_reason"] = re.search(r"\[no_pick_reason\](.*?)\[/no_pick_reason\]", narrative or "", re.S).group(1).strip() if re.search(r"\[no_pick_reason\](.*?)\[/no_pick_reason\]", narrative or "", re.S) else ""
                        if pp:
                            _n, _c, mmc_f, msc_f = pp
                            out["parse_status"] = "ok"
                            out["postprocess_status"] = "ok"
                            out["selected_market"] = mmc_f
                            out["selected_side"] = msc_f
                            out["selected_team"] = ec["home_team"] if msc_f == "home" else ec["away_team"] if msc_f == "away" else ""
                            out["favorite_benchmark"]["dsr_pick_matches_favorite"] = msc_f == favorite
                            out["favorite_benchmark"]["odds_tier"] = _odds_tier(agg_consensus, msc_f)
                            out["favorite_benchmark"]["rationale_mentions_odds_or_favorite"] = any(x in _norm(rationale) for x in ("cuota", "odds", "favorito", "consensus"))
                            out["favorite_benchmark"]["rationale_mentions_non_odds_signal"] = _mentions_non_odds(rationale)
                        else:
                            out["parse_status"] = "postprocess_reject"
                            out["postprocess_status"] = "rejected"
                    dsr_outputs["outputs"].append(out)

        if ds_input_rows:
            enough_non_odds = sum(1 for r in ds_input_rows if any(v for k, v in (r["signal_flags"] or {}).items() if k.endswith("_available") and k != "odds_featured_available"))
            high_leak = sum(1 for r in ds_input_rows if r["signal_flags"].get("leakage_risk") == "HIGH_RISK_LEAKAGE")
            parsed = [r for r in dsr_outputs["outputs"] if r.get("parse_status") == "ok"]
            non_odds_rat = sum(1 for r in parsed if r.get("favorite_benchmark", {}).get("rationale_mentions_non_odds_signal"))
            central_answer = (
                f"Clean pre-match slice has {len(ds_input_rows)} matched events; "
                f"{enough_non_odds} include at least one non-odds processed block, "
                f"{high_leak} carry high-risk leakage flags, and DSR rationales mention non-odds signals in "
                f"{non_odds_rat}/{len(parsed)} parsed outputs."
            )

        coverage = {
            "generated_at_utc": generated_at.isoformat(),
            "operating_day": op_day.isoformat(),
            "timezone": args.timezone,
            "declared_start_bogota_from_request": f"{op_day.isoformat()}T00:25:00-05:00",
            "actual_cutoff_bogota": cutoff_local.isoformat(),
            "actual_cutoff_utc": cutoff_utc.isoformat(),
            "predictive_clean_cutoff_bogota": clean_cutoff_utc.astimezone(tz).isoformat(),
            "variant_1040_cutoff_bogota": variant_1040_utc.astimezone(tz).isoformat(),
            "operating_window_utc": {"start": day_start_utc.isoformat(), "end": day_end_utc.isoformat()},
            "operating_leagues": leagues,
            "external_calls": external_calls,
            "refresh_notes": sm_notes + toa_notes,
            "tables_read": [
                "bt2_leagues",
                "bt2_events",
                "raw_sportmonks_fixtures",
            ],
            "tables_written": [],
            "artifacts_written": [
                f"scripts/outputs/live_field_coverage_{op_day.isoformat()}.json",
                f"scripts/outputs/live_field_ds_inputs_{op_day.isoformat()}.json",
                f"scripts/outputs/live_field_dsr_outputs_{op_day.isoformat()}.json",
                f"docs/bettracker2/audits/LIVE_FIELD_AUDIT_{op_day.isoformat()}.md",
            ],
            "fixtures": fixtures,
            "coverage_full_day_future": coverage_future,
            "predictive_clean_slice_fixture_refs": [
                {"sm_fixture_id": r["sm_fixture_id"], "event_sequence_id": r["event_sequence_id"]}
                for r in ds_input_rows
            ],
            "predictive_clean_slice_1040_variant": variant_rows,
            "central_answer": central_answer,
        }
        ds_inputs = {
            "generated_at_utc": generated_at.isoformat(),
            "operating_day": op_day.isoformat(),
            "timezone": args.timezone,
            "predictive_clean_slice": ds_input_rows,
            "predictive_clean_slice_1040_variant_fixture_refs": [
                {"sm_fixture_id": r["sm_fixture_id"], "kickoff_bogota": r["kickoff_bogota"]}
                for r in variant_rows
            ],
        }

        out_dir = ROOT / "scripts" / "outputs"
        docs_dir = ROOT / "docs" / "bettracker2" / "audits"
        out_dir.mkdir(parents=True, exist_ok=True)
        docs_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"live_field_coverage_{op_day.isoformat()}.json").write_text(
            json.dumps(_jsonable(coverage), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (out_dir / f"live_field_ds_inputs_{op_day.isoformat()}.json").write_text(
            json.dumps(_jsonable(ds_inputs), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (out_dir / f"live_field_dsr_outputs_{op_day.isoformat()}.json").write_text(
            json.dumps(_jsonable(dsr_outputs), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        _write_markdown(docs_dir / f"LIVE_FIELD_AUDIT_{op_day.isoformat()}.md", coverage, ds_inputs, dsr_outputs)
        print(json.dumps({"ok": True, "fixtures": len(fixtures), "ds_inputs": len(ds_input_rows), "dsr_outputs": len(dsr_outputs["outputs"])}, indent=2))
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

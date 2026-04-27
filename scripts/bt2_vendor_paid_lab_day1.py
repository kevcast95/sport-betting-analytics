#!/usr/bin/env python3
"""
Fase 3F — Laboratorio pagado día 1 (subset5): SportMonks Starter + The Odds API histórico.

- No SM Odds en includes del smoke test SM (solo fixture master + contexto).
- Sin persistencia productiva; CSV/JSON bajo scripts/outputs/bt2_vendor_lab_day1/.

Ejecutar desde raíz del repo con .env (SPORTMONKS_API_KEY, THEODDSAPI_KEY, BT2_DATABASE_URL):

  python3 scripts/bt2_vendor_paid_lab_day1.py --all

Opciones:
  --freeze-only   Solo congela day1_lab_manifest.csv (15 fixtures por defecto).
  --limit N       N fixtures (10–20 recomendado).
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
import psycopg2
import psycopg2.extras

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from apps.api.bt2_settings import bt2_settings

OUT_DIR = _repo / "scripts" / "outputs" / "bt2_vendor_lab_day1"
PILOT_MANIFEST = _repo / "scripts" / "outputs" / "bt2_vendor_pilot_prep" / "pilot_fixture_manifest.csv"
VENDOR_SAMPLE = _repo / "scripts" / "outputs" / "bt2_vendor_readiness" / "vendor_validation_sample.csv"

SM_BASE = "https://api.sportmonks.com/v3/football/fixtures"
TOA_BASE = "https://api.the-odds-api.com/v4"

# Includes SM laboratorio: sin odds / inplay / premium (no SM Odds).
SM_LAB_INCLUDES = (
    "sport;participants;state;scores;league;season;round;stage;group;venue;"
    "referees;coaches;metadata;comments;events;statistics;formations;lineups;matchfacts"
)

DEFAULT_DAY1_LIMIT = 15

SUBSET5 = frozenset({8, 82, 301, 384, 564})


def _norm_team(s: str) -> str:
    t = (s or "").lower().strip()
    t = re.sub(r"[\.\'\`´]", "", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for tok in (" fc", " cf", " sc", " afc", " fk", " ac"):
        if t.endswith(tok):
            t = t[: -len(tok)].strip()
    return t


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def _parse_any_dt(s: str) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    x = str(s).strip()
    try:
        if x.endswith("Z"):
            x = x.replace("Z", "+00:00")
        dt = datetime.fromisoformat(x)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _load_hist_proto() -> Any:
    name = "bt2_historical_sm_lbu_replay_prototype_lab"
    if name in sys.modules:
        return sys.modules[name]
    p = _repo / "scripts" / "bt2_historical_sm_lbu_replay_prototype.py"
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_normalize() -> Any:
    p = _repo / "scripts" / "bt2_cdm" / "normalize_fixtures.py"
    spec = importlib.util.spec_from_file_location("bt2_nf_lab", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _read_pilot_manifest_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with PILOT_MANIFEST.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(row["sm_league_id"]) not in SUBSET5:
                continue
            rows.append(row)
    return rows


def _pick_day1_rows(all_rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    by_l: dict[int, list[dict[str, str]]] = defaultdict(list)
    for r in all_rows:
        by_l[int(r["sm_league_id"])].append(r)
    for lid in by_l:
        by_l[lid].sort(key=lambda x: int(x["sm_fixture_id"]))
    leagues = sorted(by_l.keys())
    picked: list[dict[str, str]] = []
    seen: set[str] = set()
    round_idx = 0
    while len(picked) < limit:
        added_round = False
        for lid in leagues:
            if len(picked) >= limit:
                break
            pool = by_l[lid]
            if round_idx >= len(pool):
                continue
            row = pool[round_idx]
            fid = row["sm_fixture_id"]
            if fid in seen:
                continue
            seen.add(fid)
            picked.append(row)
            added_round = True
        if not added_round:
            break
        round_idx += 1
    return picked[:limit]


def _enrich_teams_from_db(rows: list[dict[str, str]]) -> None:
    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    for row in rows:
        eid = int(row["bt2_event_id"])
        cur.execute(
            """
            SELECT th.name AS home_name, ta.name AS away_name
            FROM bt2_events e
            LEFT JOIN bt2_teams th ON th.id = e.home_team_id
            LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
            WHERE e.id = %s
            """,
            (eid,),
        )
        one = cur.fetchone()
        row["_home_name"] = str(one["home_name"] or "") if one else ""
        row["_away_name"] = str(one["away_name"] or "") if one else ""
    cur.close()
    conn.close()


def _load_vendor_vp_map() -> dict[str, str]:
    out: dict[str, str] = {}
    if not VENDOR_SAMPLE.is_file():
        return out
    with VENDOR_SAMPLE.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[str(r.get("fixture_id", ""))] = str(r.get("value_pool_sm_lbu_t60", ""))
    return out


def _value_pool_from_db(bt2_event_id: int, hist: Any) -> Optional[bool]:
    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT e.kickoff_utc, r.payload
        FROM bt2_events e
        INNER JOIN raw_sportmonks_fixtures r ON r.fixture_id = e.sportmonks_fixture_id
        WHERE e.id = %s
        """,
        (bt2_event_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row or not row.get("payload"):
        return None
    pl = row["payload"]
    if isinstance(pl, str):
        pl = json.loads(pl)
    ko = row["kickoff_utc"]
    if ko and getattr(ko, "tzinfo", None) is None:
        ko = ko.replace(tzinfo=timezone.utc)
    t_cut = hist.cutoff_t60(ko) if ko else None
    extract = hist.extract_cdm_rows
    agg_fn = hist.aggregate_odds_for_event
    to_t = hist.to_agg_tuples
    vp_fn = hist.event_passes_value_pool
    min_dec = hist.MIN_DEC
    before = extract(pl)
    t60 = [t for t in before if t[4] is not None and t_cut and t[4] <= t_cut]
    agg = agg_fn(to_t(t60), min_decimal=min_dec)
    return bool(vp_fn(agg, min_decimal=min_dec))


def freeze_manifest(limit: int) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_r = _read_pilot_manifest_rows()
    picked = _pick_day1_rows(all_r, limit)
    _enrich_teams_from_db(picked)
    path = OUT_DIR / "day1_lab_manifest.csv"
    fn = [
        "bt2_event_id",
        "sm_fixture_id",
        "sm_league_id",
        "league_name",
        "home_team_sm",
        "away_team_sm",
        "kickoff_utc",
        "the_odds_api_sport_key_expected",
        "market",
        "region",
        "snapshot_time_t60",
        "pilot_group",
        "inclusion_reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for r in picked:
            w.writerow(
                {
                    "bt2_event_id": r["bt2_event_id"],
                    "sm_fixture_id": r["sm_fixture_id"],
                    "sm_league_id": r["sm_league_id"],
                    "league_name": r["league_name"],
                    "home_team_sm": r.get("_home_name", ""),
                    "away_team_sm": r.get("_away_name", ""),
                    "kickoff_utc": r["kickoff_utc"],
                    "the_odds_api_sport_key_expected": r["the_odds_api_sport_key_expected"],
                    "market": r.get("market", "h2h"),
                    "region": r.get("region", "us"),
                    "snapshot_time_t60": r["snapshot_time_t60"],
                    "pilot_group": "paid_lab_day1_subset5",
                    "inclusion_reason": r.get("pilot_inclusion_reason", ""),
                }
            )
    return path


def _sm_fetch_fixture(fixture_id: int, api_key: str) -> tuple[int, Optional[dict], str]:
    url = f"{SM_BASE}/{fixture_id}"
    params = {"api_token": api_key, "include": SM_LAB_INCLUDES}
    try:
        with httpx.Client(timeout=45) as client:
            r = client.get(url, params=params)
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            return r.status_code, body if isinstance(body, dict) else {}, r.text[:4000]
    except Exception as e:
        return 0, None, str(e)


def _classify_include(payload: dict[str, Any], key: str, list_min: int = 1) -> tuple[str, str]:
    v = payload.get(key)
    if v is None:
        return "absent_or_unreliable", "clave ausente"
    if isinstance(v, list):
        if len(v) >= list_min:
            return "present_usable", f"n={len(v)}"
        if len(v) > 0:
            return "present_inconsistent", f"pocos items n={len(v)}"
        return "absent_or_unreliable", "lista vacía"
    if isinstance(v, dict):
        return ("present_usable", "dict") if v else ("absent_or_unreliable", "dict vacío")
    return "present_usable", type(v).__name__


def run_sm_phase(rows: list[dict[str, str]], api_key: str) -> tuple[list[dict], list[dict]]:
    fm_rows: list[dict[str, Any]] = []
    ctx_rows: list[dict[str, Any]] = []
    keys_ctx = (
        "events",
        "statistics",
        "lineups",
        "formations",
        "referees",
        "coaches",
        "metadata",
    )
    for row in rows:
        fid = int(row["sm_fixture_id"])
        status, body, raw_tail = _sm_fetch_fixture(fid, api_key)
        data = (body or {}).get("data") if body else None
        pl = data if isinstance(data, dict) else {}
        scores = ""
        if isinstance(pl.get("scores"), list) and pl["scores"]:
            scores = json.dumps(pl["scores"][:2], ensure_ascii=False)[:500]
        state = pl.get("state") if isinstance(pl.get("state"), dict) else {}
        state_id = state.get("state") if isinstance(state, dict) else ""
        participants_ok = bool(pl.get("participants"))
        lg = pl.get("league") if isinstance(pl.get("league"), dict) else {}
        season = pl.get("season") if isinstance(pl.get("season"), dict) else {}
        rnd = pl.get("round") if isinstance(pl.get("round"), dict) else {}
        stg = pl.get("stage") if isinstance(pl.get("stage"), dict) else {}
        meta_note = f"league_id={lg.get('id')} season_id={season.get('id')} round={rnd.get('name') or rnd.get('id')} stage={stg.get('name') or stg.get('id')}"
        fm_rows.append(
            {
                "sm_fixture_id": fid,
                "http_status": status,
                "kickoff_payload": pl.get("starting_at") or pl.get("starting_at_timestamp") or "",
                "state_status": str(state_id),
                "scores_summary": scores[:800],
                "participants_ok": participants_ok,
                "league_season_round_notes": meta_note[:500],
                "response_error_tail": raw_tail if status != 200 else "",
            }
        )
        for k in keys_ctx:
            cls, note = _classify_include(pl, k, 2 if k in ("lineups", "events") else 1)
            ctx_rows.append(
                {
                    "sm_fixture_id": fid,
                    "include_name": k,
                    "availability": cls,
                    "detail": note[:300],
                }
            )
    return fm_rows, ctx_rows


def _headers_credit(h: httpx.Headers) -> dict[str, str]:
    out = {}
    for name in ("x-requests-remaining", "x-requests-used", "x-requests-last"):
        if name in h:
            out[name] = h[name]
    return out


def _match_toa_event(
    events_payload: dict[str, Any],
    kickoff: datetime,
    home: str,
    away: str,
) -> tuple[Optional[str], str]:
    data = events_payload.get("data") if isinstance(events_payload.get("data"), list) else []
    nh, na = _norm_team(home), _norm_team(away)
    best_id: Optional[str] = None
    best_delta = 9e15
    best_reason = "sin candidatos"
    for ev in data:
        if not isinstance(ev, dict):
            continue
        ct = _parse_any_dt(str(ev.get("commence_time") or ""))
        if not ct:
            continue
        eh = _norm_team(str(ev.get("home_team") or ""))
        ea = _norm_team(str(ev.get("away_team") or ""))
        teams_ok = (eh == nh and ea == na) or (eh == na and ea == nh)
        if not teams_ok:
            continue
        delta = abs((ct - kickoff).total_seconds())
        if delta < best_delta:
            best_delta = delta
            best_id = str(ev.get("id") or "")
            best_reason = f"teams_match delta_s={int(delta)}"
    if best_id:
        return best_id, best_reason
    return None, "unmatched_team_or_time"


def run_toa_phase(rows: list[dict[str, str]], api_key: str) -> tuple[list[dict], list[dict], dict[str, Any]]:
    matching: list[dict[str, Any]] = []
    odds_rows: list[dict[str, Any]] = []
    credits_log: list[dict[str, Any]] = []
    total_cost_est = 0.0

    with httpx.Client(timeout=60) as client:
        for row in rows:
            sport = row["the_odds_api_sport_key_expected"].strip()
            snap = row["snapshot_time_t60"].strip()
            ko = _parse_any_dt(row["kickoff_utc"])
            home = row.get("home_team_sm") or ""
            away = row.get("away_team_sm") or ""
            fid = row["sm_fixture_id"]
            beid = row["bt2_event_id"]

            # Normalizar fecha a ISO Z para TOA
            snap_dt = _parse_any_dt(snap)
            date_param = snap_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if snap_dt else snap

            url_ev = f"{TOA_BASE}/historical/sports/{sport}/events"
            r1 = client.get(
                url_ev,
                params={"apiKey": api_key, "date": date_param, "dateFormat": "iso"},
            )
            h1 = _headers_credit(r1.headers)
            try:
                j1 = r1.json()
            except Exception:
                j1 = {}
            try:
                cost1 = float(h1.get("x-requests-last") or 1)
            except (TypeError, ValueError):
                cost1 = 1.0
            total_cost_est += cost1
            credits_log.append({"step": "historical_events", "fixture": fid, **h1})

            cls_m = "unmatched_event"
            toa_eid = ""
            note_m = ""
            if r1.status_code == 401 or r1.status_code == 403:
                cls_m = "auth_or_plan_error"
                note_m = r1.text[:300]
            elif r1.status_code >= 400:
                cls_m = "request_error"
                note_m = r1.text[:300]
            else:
                toa_eid, note_m = _match_toa_event(j1 if isinstance(j1, dict) else {}, ko or datetime.now(timezone.utc), home, away)
                if toa_eid:
                    cls_m = "matched_event"
                else:
                    cls_m = "unmatched_event"

            matching.append(
                {
                    "bt2_event_id": beid,
                    "sm_fixture_id": fid,
                    "sport_key": sport,
                    "request_url": url_ev,
                    "params_date": date_param,
                    "http_status": r1.status_code,
                    "toa_event_id": toa_eid,
                    "match_notes": note_m,
                    "classification": cls_m,
                    "usage_headers_json": json.dumps(h1, ensure_ascii=False),
                }
            )

            if not toa_eid:
                odds_rows.append(
                    {
                        "sm_fixture_id": fid,
                        "bt2_event_id": beid,
                        "toa_event_id": "",
                        "request_url": "",
                        "http_status": "",
                        "provider_snapshot_time": "",
                        "provider_last_update": "",
                        "ingested_at": "",
                        "market": "h2h",
                        "region": row.get("region", "us"),
                        "bookmaker_sample": "",
                        "outcomes_decimal_summary": "",
                        "classification": cls_m,
                        "payload_summary": "",
                    }
                )
                continue

            url_odds = f"{TOA_BASE}/historical/sports/{sport}/events/{toa_eid}/odds"
            r2 = client.get(
                url_odds,
                params={
                    "apiKey": api_key,
                    "regions": row.get("region", "us"),
                    "markets": "h2h",
                    "oddsFormat": "decimal",
                    "dateFormat": "iso",
                    "date": date_param,
                },
            )
            h2 = _headers_credit(r2.headers)
            try:
                cost2 = float(h2.get("x-requests-last") or 10)
            except (TypeError, ValueError):
                cost2 = 10.0
            total_cost_est += cost2
            credits_log.append({"step": "historical_event_odds", "fixture": fid, **h2})

            ingested = datetime.now(timezone.utc).isoformat()
            cls_o = "matched_without_odds_t60"
            prov_snap = ""
            prov_lu = ""
            bk_sample = ""
            out_sum = ""
            snap_payload = ""

            if r2.status_code == 401 or r2.status_code == 403:
                cls_o = "auth_or_plan_error"
            elif r2.status_code >= 400:
                cls_o = "request_error"
            else:
                try:
                    j2 = r2.json()
                except Exception:
                    j2 = {}
                snap_payload = json.dumps(j2, ensure_ascii=False)[:8000]
                if isinstance(j2, dict):
                    prov_snap = str(j2.get("timestamp") or j2.get("previous_timestamp") or "")
                    data_o = j2.get("data")
                    if isinstance(data_o, dict):
                        bookmakers = data_o.get("bookmakers") or []
                        if isinstance(bookmakers, list) and bookmakers:
                            cls_o = "matched_with_odds_t60"
                            b0 = bookmakers[0] if bookmakers else {}
                            bk_sample = str(b0.get("key") or b0.get("title") or "")
                            mk = (b0.get("markets") or [{}])[0] if b0.get("markets") else {}
                            outcomes = mk.get("outcomes") if isinstance(mk, dict) else []
                            if isinstance(outcomes, list):
                                parts = []
                                for o in outcomes[:6]:
                                    if isinstance(o, dict):
                                        parts.append(f"{o.get('name')}:{o.get('price')}")
                                        if o.get("last_update"):
                                            prov_lu = str(o.get("last_update"))
                                out_sum = ";".join(parts)
                        else:
                            cls_o = "bookmaker_gap"
                    else:
                        cls_o = "market_not_supported"

            odds_rows.append(
                {
                    "sm_fixture_id": fid,
                    "bt2_event_id": beid,
                    "toa_event_id": toa_eid,
                    "request_url": url_odds,
                    "http_status": r2.status_code,
                    "provider_snapshot_time": prov_snap,
                    "provider_last_update": prov_lu,
                    "ingested_at": ingested,
                    "market": "h2h",
                    "region": row.get("region", "us"),
                    "bookmaker_sample": bk_sample,
                    "outcomes_decimal_summary": out_sum[:1200],
                    "classification": cls_o,
                    "payload_summary": snap_payload[:8000],
                }
            )

    summary_credits = {
        "estimated_total_cost_from_headers_sum": round(total_cost_est, 2),
        "note": "Coste por llamada según headers x-requests-last cuando existan.",
        "calls": credits_log,
    }
    return matching, odds_rows, summary_credits


def run_bt2_compare(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    hist = _load_hist_proto()
    vp_map = _load_vendor_vp_map()
    out: list[dict[str, Any]] = []
    for row in rows:
        fid = str(row["sm_fixture_id"])
        beid = int(row["bt2_event_id"])
        vp_sample = vp_map.get(fid)
        vp_db: Optional[bool] = None
        try:
            vp_db = _value_pool_from_db(beid, hist)
        except Exception as e:
            vp_db = None
            vp_err = str(e)
        else:
            vp_err = ""
        out.append(
            {
                "sm_fixture_id": fid,
                "bt2_event_id": beid,
                "value_pool_from_vendor_sample_csv": vp_sample,
                "value_pool_recomputed_sm_lbu_t60": "" if vp_db is None else str(vp_db),
                "recompute_error": vp_err,
                "diagnosis_hint": "comparar con toa_h2h_t60_results para matching/timestamp/market",
            }
        )
    return out


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def cmd_all(args: argparse.Namespace) -> None:
    api_sm = (os.environ.get("SPORTMONKS_API_KEY") or bt2_settings.sportmonks_api_key or "").strip()
    api_toa = (os.environ.get("THEODDSAPI_KEY") or bt2_settings.theoddsapi_key or "").strip()
    if not api_sm:
        raise SystemExit("Falta SPORTMONKS_API_KEY / sportmonks_api_key en .env")
    if not api_toa:
        raise SystemExit("Falta THEODDSAPI_KEY / theoddsapi_key en .env")

    limit = max(10, min(args.limit, 28))
    path_m = freeze_manifest(limit)
    print(json.dumps({"frozen_manifest": str(path_m.relative_to(_repo)), "limit": limit}, indent=2))

    with path_m.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fm, ctx = run_sm_phase(rows, api_sm)
    write_csv(
        OUT_DIR / "sm_day1_fixture_master_check.csv",
        list(fm[0].keys()) if fm else ["sm_fixture_id"],
        fm,
    )
    write_csv(
        OUT_DIR / "sm_day1_contextual_includes_check.csv",
        list(ctx[0].keys()) if ctx else ["sm_fixture_id"],
        ctx,
    )

    mat, odds, cred = run_toa_phase(rows, api_toa)
    write_csv(
        OUT_DIR / "toa_event_matching_results.csv",
        list(mat[0].keys()) if mat else ["sm_fixture_id"],
        mat,
    )
    write_csv(
        OUT_DIR / "toa_h2h_t60_results.csv",
        list(odds[0].keys()) if odds else ["sm_fixture_id"],
        odds,
    )
    (OUT_DIR / "toa_credit_usage_summary.json").write_text(
        json.dumps(cred, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    cmp_rows = run_bt2_compare(rows)
    write_csv(
        OUT_DIR / "bt2_vs_toa_exploration.csv",
        list(cmp_rows[0].keys()) if cmp_rows else ["sm_fixture_id"],
        cmp_rows,
    )

    n_ok = sum(1 for r in odds if "matched_with_odds" in str(r.get("classification", "")))
    n_match = sum(1 for r in mat if r.get("toa_event_id"))
    n_unmatched = len(rows) - n_match
    match_rate = round(n_match / max(len(rows), 1), 4)
    verdict_toa = (
        "pasa"
        if (match_rate >= 0.85 and n_ok >= n_match * 0.85)
        else "pasa_con_caveats"
        if (match_rate >= 0.5)
        else "no_pasa"
    )
    verdict = {
        "phase": "3f_vendor_paid_lab_day1_subset5",
        "fixtures_run": len(rows),
        "distinct_leagues": len({int(r["sm_league_id"]) for r in rows}),
        "sm_fixture_master_http_200_rate": round(
            sum(1 for x in fm if int(x.get("http_status") or 0) == 200) / max(len(fm), 1),
            4,
        ),
        "toa_events_matched": n_match,
        "toa_events_unmatched": n_unmatched,
        "toa_match_rate": match_rate,
        "toa_h2h_with_odds_t60": n_ok,
        "estimated_credit_sum_from_headers": cred.get("estimated_total_cost_from_headers_sum"),
        "pilot_prep_estimated_credits_reference": "15 fixtures × ~11 créditos/último coste cabecera ≈ 165 vs real sum(headers)",
        "verdict_sm_starter_fixture_master": "pasa" if sm_pass(fm) else "pasa_con_caveats",
        "verdict_toa_initial": verdict_toa,
        "matching_gap_note": "Si unmatched_team_or_time: revisar nombres TOA vs SM (acentos, FC), o snapshot date vs lista events.",
        "next_steps_days_2_5": "Mejorar heurística matching y/o aliases equipos; repetir muestra; luego ampliar a 20–28 fixtures si match_rate sube.",
    }
    (OUT_DIR / "lab_day1_summary.json").write_text(
        json.dumps(verdict, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    readme = f"""# BT2 — Laboratorio pagado día 1 (subset5)

Ejecutado con `scripts/bt2_vendor_paid_lab_day1.py --all`.

## Entradas

- Manifiesto piloto: `scripts/outputs/bt2_vendor_pilot_prep/pilot_fixture_manifest.csv`
- Congelado día 1: `day1_lab_manifest.csv`

## Salidas clave

- `sm_day1_fixture_master_check.csv` — smoke SportMonks (sin includes de odds).
- `sm_day1_contextual_includes_check.csv` — events/statistics/lineups/…
- `toa_event_matching_results.csv` — discovery histórico + match.
- `toa_h2h_t60_results.csv` — odds h2h T-60; `ingested_at` es solo auditoría (no tiempo de mercado).
- `toa_credit_usage_summary.json` — headers de uso.
- `bt2_vs_toa_exploration.csv` — value pool BT2 vs muestra.
- `lab_day1_summary.json`

## Regenerar solo manifiesto día 1

```bash
python3 scripts/bt2_vendor_paid_lab_day1.py --freeze-only --limit 15
```
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({"ok": True, "out_dir": str(OUT_DIR.relative_to(_repo))}, indent=2))


def sm_pass(fm: list[dict]) -> bool:
    if not fm:
        return False
    ok = sum(1 for x in fm if int(x.get("http_status") or 0) == 200)
    return ok >= len(fm) * 0.8


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="Congela manifiesto y ejecuta SM + TOA + compare")
    ap.add_argument("--freeze-only", action="store_true")
    ap.add_argument("--limit", type=int, default=DEFAULT_DAY1_LIMIT)
    args = ap.parse_args()
    if args.freeze_only:
        p = freeze_manifest(max(10, min(args.limit, 28)))
        print(json.dumps({"frozen": str(p)}, indent=2))
        return
    if args.all:
        cmd_all(args)
        return
    ap.print_help()


if __name__ == "__main__":
    main()

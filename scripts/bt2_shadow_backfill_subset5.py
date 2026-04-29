#!/usr/bin/env python3
"""
Backfill controlado subset5 sobre carril shadow (no productivo).

Ventanas objetivo:
- 2025-01..05
- 2025-07..12

Persistencia por run_key en:
- bt2_shadow_runs
- bt2_shadow_provider_snapshots
- bt2_shadow_daily_picks
- bt2_shadow_pick_inputs
- bt2_shadow_pick_eval
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras
import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_settings import bt2_settings

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_backfill_subset5"
SUBSET5 = frozenset({8, 82, 301, 384, 564})
SM_BASE_URL = "https://api.sportmonks.com/v3"
def _norm_team(s: str) -> str:
    t = unicodedata.normalize("NFKD", (s or "").strip().lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"[\.\'`´]", "", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for tok in (" fc", " cf", " sc", " afc", " fk", " ac"):
        if t.endswith(tok):
            t = t[: -len(tok)].strip()
    return t


def _canon_team(s: str) -> str:
    aliases = {
        "afc bournemouth": "bournemouth",
        "bayer 04 leverkusen": "bayer leverkusen",
        "losc lille": "lille",
        "celta de vigo": "celta vigo",
        "deportivo alaves": "alaves",
    }
    n = _norm_team(s)
    return aliases.get(n, n)


def _normalize_selection_for_h2h(selection: str | None, home_name: str, away_name: str) -> str | None:
    s_raw = (selection or "").strip()
    if not s_raw:
        return None
    s = _canon_team(s_raw)
    if s in {"draw", "empate", "x"}:
        return "draw"
    home = _canon_team(home_name)
    away = _canon_team(away_name)
    if home and (s == home or home in s or s in home):
        return home_name
    if away and (s == away or away in s or s in away):
        return away_name
    return s_raw




def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def _import_paid_lab() -> Any:
    p = ROOT / "scripts" / "bt2_vendor_paid_lab_day1.py"
    spec = importlib.util.spec_from_file_location("bt2_paid_lab_shadow_backfill", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _import_hist_proto() -> Any:
    p = ROOT / "scripts" / "bt2_historical_sm_lbu_replay_prototype.py"
    spec = importlib.util.spec_from_file_location("bt2_hist_shadow_backfill", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["bt2_hist_shadow_backfill"] = mod
    spec.loader.exec_module(mod)
    return mod


def _import_vr3d() -> Any:
    p = ROOT / "scripts" / "bt2_vendor_readiness_phase3d.py"
    spec = importlib.util.spec_from_file_location("bt2_vr3d_shadow_backfill", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


@dataclass
class PersistCounts:
    runs: int = 0
    snapshots: int = 0
    picks: int = 0
    inputs: int = 0
    evals: int = 0


def _window_dt(year: int, month_from: int, month_to: int) -> tuple[datetime, datetime]:
    d0 = datetime(year, month_from, 1, tzinfo=timezone.utc)
    if month_to == 12:
        d1 = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        d1 = datetime(year, month_to + 1, 1, tzinfo=timezone.utc)
    return d0, d1


def _build_rows_for_window(
    cur: Any,
    *,
    year: int,
    month_from: int,
    month_to: int,
    per_league_cap: int,
) -> list[dict[str, str]]:
    vr3d = _import_vr3d()
    d0, d1 = _window_dt(year, month_from, month_to)
    cur.execute(
        """
        SELECT
            e.id AS bt2_event_id,
            e.sportmonks_fixture_id AS sm_fixture_id,
            e.kickoff_utc,
            l.id AS league_id,
            l.sportmonks_id AS sm_league_id,
            l.name AS league_name,
            l.tier AS league_tier,
            l.country AS league_country,
            COALESCE(th.name, '') AS home_name,
            COALESCE(ta.name, '') AS away_name
        FROM bt2_events e
        INNER JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE l.sportmonks_id = ANY(%s)
          AND e.kickoff_utc >= %s
          AND e.kickoff_utc < %s
        ORDER BY e.kickoff_utc ASC, e.id ASC
        """,
        (list(SUBSET5), d0, d1),
    )
    by_league: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for r in cur.fetchall() or []:
        lid = int(r["sm_league_id"])
        lm = vr3d.resolve_league_mapping(
            lid,
            str(r.get("league_name") or ""),
            str(r.get("league_country") or ""),
            str(r.get("league_tier") or ""),
        )
        if lm.get("pilot_tier") != "priority_pilot_now":
            continue
        if lm.get("mapping_status") != "mapped_expected":
            continue
        sk = (lm.get("the_odds_api_sport_key_expected") or "").strip()
        if not sk:
            continue
        by_league[lid].append(
            {
                "bt2_event_id": str(int(r["bt2_event_id"])),
                "sm_fixture_id": str(int(r["sm_fixture_id"])),
                "sm_league_id": str(lid),
                "league_name": str(r.get("league_name") or ""),
                "home_team_sm": str(r.get("home_name") or ""),
                "away_team_sm": str(r.get("away_name") or ""),
                "kickoff_utc": r["kickoff_utc"].astimezone(timezone.utc).isoformat(),
                "the_odds_api_sport_key_expected": sk,
                "market": "h2h",
                "region": "us",
                "snapshot_time_t60": (r["kickoff_utc"] - timedelta(minutes=60))
                .astimezone(timezone.utc)
                .isoformat(),
                "pilot_group": f"shadow_backfill_{year}_{month_from:02d}_{month_to:02d}",
                "inclusion_reason": "subset5_priority_pilot_now_mapped_expected_h2h_us_t60",
            }
        )
    out: list[dict[str, str]] = []
    for lid in sorted(by_league.keys()):
        out.extend(by_league[lid][: max(1, per_league_cap)])
    return out


def _parse_any_dt(s: str) -> Optional[datetime]:
    x = (s or "").strip()
    if not x:
        return None
    if x.endswith("Z"):
        x = x.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(x)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _sm_fetch_between_subset5(
    *, year: int, month_from: int, month_to: int, sm_api_key: str, per_league_cap: int
) -> list[dict[str, str]]:
    d0, d1 = _window_dt(year, month_from, month_to)
    include = "participants;league;scores;state"
    out: list[dict[str, str]] = []
    vr3d = _import_vr3d()
    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        with httpx.Client(timeout=45) as client:
            # SportMonks entre-fechas admite máximo 100 días por request.
            chunk_start = d0
            while chunk_start < d1:
                chunk_end = min(chunk_start + timedelta(days=100), d1)
                start_str = chunk_start.date().isoformat()
                end_str = (chunk_end - timedelta(days=1)).date().isoformat()
                url = f"{SM_BASE_URL}/football/fixtures/between/{start_str}/{end_str}"
                page = 1
                while True:
                    r = client.get(url, params={"api_token": sm_api_key, "include": include, "page": page})
                    if r.status_code != 200:
                        break
                    payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                    data = payload.get("data") if isinstance(payload.get("data"), list) else []
                    if not data:
                        break
                    for fx in data:
                        if not isinstance(fx, dict):
                            continue
                        lid = int(fx.get("league_id") or 0)
                        if lid not in SUBSET5:
                            continue
                        league = fx.get("league") if isinstance(fx.get("league"), dict) else {}
                        lm = vr3d.resolve_league_mapping(
                            lid,
                            str(league.get("name") or ""),
                            str(league.get("country_name") or ""),
                            str(league.get("tier") or ""),
                        )
                        sk = (lm.get("the_odds_api_sport_key_expected") or "").strip()
                        if lm.get("pilot_tier") != "priority_pilot_now" or lm.get("mapping_status") != "mapped_expected" or not sk:
                            continue
                        participants = fx.get("participants") if isinstance(fx.get("participants"), list) else []
                        home = away = ""
                        for p in participants:
                            if not isinstance(p, dict):
                                continue
                            meta = p.get("meta") if isinstance(p.get("meta"), dict) else {}
                            loc = str(meta.get("location") or "").lower()
                            if loc == "home":
                                home = str(p.get("name") or "")
                            elif loc == "away":
                                away = str(p.get("name") or "")
                        kickoff = _parse_any_dt(str(fx.get("starting_at") or ""))
                        if not kickoff:
                            continue
                        snap = (kickoff - timedelta(minutes=60)).isoformat()
                        sm_fixture_id = int(fx.get("id") or 0)
                        cur.execute("SELECT id FROM bt2_events WHERE sportmonks_fixture_id = %s", (sm_fixture_id,))
                        er = cur.fetchone()
                        bt2_event_id = int(er["id"]) if er else 0
                        out.append(
                            {
                                "bt2_event_id": str(bt2_event_id),
                                "sm_fixture_id": str(sm_fixture_id),
                                "sm_league_id": str(lid),
                                "league_name": str(league.get("name") or ""),
                                "home_team_sm": home,
                                "away_team_sm": away,
                                "kickoff_utc": kickoff.isoformat(),
                                "the_odds_api_sport_key_expected": sk,
                                "market": "h2h",
                                "region": "us",
                                "snapshot_time_t60": snap,
                                "pilot_group": f"shadow_recovery_{year}_{month_from:02d}_{month_to:02d}",
                                "inclusion_reason": "sm_starter_fixture_master_recovery_subset5_h2h_us_t60",
                            }
                        )
                    pag = payload.get("pagination") or {}
                    if not pag.get("has_more"):
                        break
                    page += 1
                chunk_start = chunk_end
                if chunk_start >= d1:
                    break
    finally:
        cur.close()
        conn.close()
    ded: dict[str, dict[str, str]] = {}
    for r in out:
        ded[r["sm_fixture_id"]] = r
    by_league: dict[int, list[dict[str, str]]] = defaultdict(list)
    for r in ded.values():
        by_league[int(r["sm_league_id"])].append(r)
    picked: list[dict[str, str]] = []
    for lid in sorted(by_league.keys()):
        rows = sorted(by_league[lid], key=lambda x: x["kickoff_utc"])
        picked.extend(rows[: max(1, per_league_cap)])
    return picked


def _compute_value_pool_pass(rows: list[dict[str, str]]) -> dict[str, str]:
    hist = _import_hist_proto()
    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    out: dict[str, str] = {}
    try:
        for r in rows:
            beid = int(r["bt2_event_id"])
            cur.execute(
                """
                SELECT e.kickoff_utc, rf.payload
                FROM bt2_events e
                INNER JOIN raw_sportmonks_fixtures rf ON rf.fixture_id = e.sportmonks_fixture_id
                WHERE e.id = %s
                """,
                (beid,),
            )
            one = cur.fetchone()
            if not one or not one.get("payload"):
                out[r["sm_fixture_id"]] = ""
                continue
            pl = one["payload"]
            if isinstance(pl, str):
                pl = json.loads(pl)
            ko = one["kickoff_utc"]
            if ko and ko.tzinfo is None:
                ko = ko.replace(tzinfo=timezone.utc)
            t_cut = hist.cutoff_t60(ko) if ko else None
            before = hist.extract_cdm_rows(pl)
            t60 = [t for t in before if t[4] is not None and t_cut and t[4] <= t_cut]
            agg = hist.aggregate_odds_for_event(hist.to_agg_tuples(t60), min_decimal=hist.MIN_DEC)
            out[r["sm_fixture_id"]] = str(bool(hist.event_passes_value_pool(agg, min_decimal=hist.MIN_DEC)))
    finally:
        cur.close()
        conn.close()
    return out


def _persist_run(
    cur: Any,
    *,
    run_key: str,
    rows: list[dict[str, str]],
    matching_rows: list[dict[str, Any]],
    odds_rows: list[dict[str, Any]],
    credit_summary: dict[str, Any],
    vp_map: dict[str, str],
) -> PersistCounts:
    if not rows:
        return PersistCounts()
    dkeys = [r["kickoff_utc"][:10] for r in rows if len(r.get("kickoff_utc", "")) >= 10]
    d_from = min(dkeys) if dkeys else datetime.now(timezone.utc).date().isoformat()
    d_to = max(dkeys) if dkeys else d_from
    cur.execute(
        """
        INSERT INTO bt2_shadow_runs (
            run_key, operating_day_key_from, operating_day_key_to, mode, provider_stack, is_shadow, notes
        )
        VALUES (%s,%s,%s,'shadow','sportmonks_fixture_master + theoddsapi_historical_h2h_t60',true,%s)
        RETURNING id
        """,
        (run_key, d_from, d_to, "subset5_backfill_window"),
    )
    run_id = int(cur.fetchone()["id"])
    counts = PersistCounts(runs=1)

    m_by_f = {str(r.get("sm_fixture_id", "")): r for r in matching_rows}
    o_by_f = {str(r.get("sm_fixture_id", "")): r for r in odds_rows}
    calls = credit_summary.get("calls") or []
    credits_by_fixture: dict[str, float] = defaultdict(float)
    for c in calls:
        fid = str(c.get("fixture") or "").strip()
        if not fid:
            continue
        try:
            credits_by_fixture[fid] += float(c.get("x-requests-last") or 0.0)
        except (TypeError, ValueError):
            pass

    for r in rows:
        fid = r["sm_fixture_id"]
        mt = m_by_f.get(fid, {})
        od = o_by_f.get(fid, {})
        cls = str(od.get("classification") or mt.get("classification") or "request_error")
        selection = None
        out_sum = str(od.get("outcomes_decimal_summary") or "")
        if ":" in out_sum:
            selection = out_sum.split(";", 1)[0].split(":", 1)[0].strip() or None
            selection = _normalize_selection_for_h2h(
                selection,
                str(r.get("home_team_sm") or ""),
                str(r.get("away_team_sm") or ""),
            )
        dec = None
        if ":" in out_sum:
            try:
                dec = float(out_sum.split(";", 1)[0].split(":", 1)[1].strip())
            except (TypeError, ValueError):
                dec = None
        provider_snapshot_time = mtm = None
        provider_last_update = None
        ingested_at = datetime.now(timezone.utc)
        pss = str(od.get("provider_snapshot_time") or "")
        if pss:
            provider_snapshot_time = datetime.fromisoformat(pss.replace("Z", "+00:00"))
        plu = str(od.get("provider_last_update") or "")
        if plu:
            provider_last_update = datetime.fromisoformat(plu.replace("Z", "+00:00"))
        ia = str(od.get("ingested_at") or "")
        if ia:
            ingested_at = datetime.fromisoformat(ia.replace("Z", "+00:00"))

        raw_payload = {
            "snapshot_time_t60": r.get("snapshot_time_t60"),
            "toa_event_id": mt.get("toa_event_id"),
            "match_notes": mt.get("match_notes"),
            "value_pool_pass": vp_map.get(fid, ""),
            "home_team_sm": r.get("home_team_sm"),
            "away_team_sm": r.get("away_team_sm"),
            "payload_summary": od.get("payload_summary"),
            "request_url": od.get("request_url"),
            "http_status": od.get("http_status"),
        }
        cur.execute(
            """
            INSERT INTO bt2_shadow_provider_snapshots (
                run_id, bt2_event_id, sm_fixture_id, provider_source, sport_key, market, region,
                provider_snapshot_time, provider_last_update, ingested_at, credits_used, raw_payload
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                run_id,
                (int(r["bt2_event_id"]) if int(r["bt2_event_id"]) > 0 else None),
                int(fid),
                "the_odds_api_historical_h2h",
                r.get("the_odds_api_sport_key_expected"),
                "h2h",
                "us",
                provider_snapshot_time,
                provider_last_update,
                ingested_at,
                credits_by_fixture.get(fid, 0.0),
                psycopg2.extras.Json(raw_payload),
            ),
        )
        provider_snapshot_id = int(cur.fetchone()["id"])
        counts.snapshots += 1

        cur.execute("SELECT id FROM bt2_leagues WHERE sportmonks_id = %s", (int(r["sm_league_id"]),))
        lr = cur.fetchone()
        league_id = int(lr["id"]) if lr else None
        status_shadow = "ready_for_shadow_pick" if cls == "matched_with_odds_t60" else "needs_review"
        day_key = r["kickoff_utc"][:10]
        cur.execute(
            """
            INSERT INTO bt2_shadow_daily_picks (
                run_id, operating_day_key, bt2_event_id, sm_fixture_id, league_id,
                market, selection, status_shadow, classification_taxonomy, decimal_odds, dsr_source, provider_snapshot_id
            )
            VALUES (%s,%s,%s,%s,%s,'h2h',%s,%s,%s,%s,%s,%s)
            RETURNING id
            """,
            (
                run_id,
                day_key,
                (int(r["bt2_event_id"]) if int(r["bt2_event_id"]) > 0 else None),
                int(fid),
                league_id,
                selection,
                status_shadow,
                cls,
                dec,
                "historical_sm_lbu_t60",
                provider_snapshot_id,
            ),
        )
        shadow_pick_id = int(cur.fetchone()["id"])
        counts.picks += 1

        input_payload = {
            "manifest_row": r,
            "matching_row": mt,
            "odds_row": {k: v for k, v in od.items() if k != "payload_summary"},
        }
        cur.execute(
            """
            INSERT INTO bt2_shadow_pick_inputs (shadow_daily_pick_id, input_source, payload_json)
            VALUES (%s,'shadow_backfill_subset5_window',%s)
            """,
            (shadow_pick_id, psycopg2.extras.Json(input_payload)),
        )
        counts.inputs += 1

        eval_status = "shadow_pass" if cls == "matched_with_odds_t60" else "shadow_needs_review"
        cur.execute(
            """
            INSERT INTO bt2_shadow_pick_eval (shadow_daily_pick_id, eval_status, classification_taxonomy, eval_notes)
            VALUES (%s,%s,%s,%s)
            """,
            (shadow_pick_id, eval_status, cls, f"run_key={run_key}"),
        )
        counts.evals += 1
    return counts


def _summary_from_results(
    *,
    run_key: str,
    year: int,
    month_from: int,
    month_to: int,
    rows: list[dict[str, str]],
    matching_rows: list[dict[str, Any]],
    odds_rows: list[dict[str, Any]],
    credits: dict[str, Any],
    vp_map: dict[str, str],
    persist_counts: PersistCounts,
) -> dict[str, Any]:
    n = len(rows)
    matched = sum(1 for r in matching_rows if str(r.get("toa_event_id") or "").strip())
    m_with = sum(1 for r in odds_rows if r.get("classification") == "matched_with_odds_t60")
    m_without = sum(1 for r in odds_rows if r.get("classification") == "matched_without_odds_t60")
    unmatched = sum(1 for r in matching_rows if r.get("classification") == "unmatched_event")
    match_rate = round(matched / n, 6) if n else 0.0
    vp_vals = [v.lower() for v in vp_map.values() if str(v).strip() != ""]
    vp_true = sum(1 for v in vp_vals if v == "true")
    vp_rate = round(vp_true / len(vp_vals), 6) if vp_vals else 0.0
    leagues = sorted({int(r["sm_league_id"]) for r in rows})
    return {
        "run_key": run_key,
        "window": f"{year}-{month_from:02d}..{month_to:02d}",
        "fixtures_seen": n,
        "fixtures_matched": matched,
        "match_rate": match_rate,
        "fixtures_with_h2h_t60": m_with,
        "matched_with_odds_t60": m_with,
        "matched_without_odds_t60": m_without,
        "unmatched_event": unmatched,
        "credits_used": float(credits.get("estimated_total_cost_from_headers_sum") or 0.0),
        "shadow_picks_generated": m_with,
        "value_pool_pass_rate": vp_rate,
        "distinct_leagues": len(leagues),
        "sm_league_ids": leagues,
        "rows_persisted": {
            "bt2_shadow_runs": persist_counts.runs,
            "bt2_shadow_provider_snapshots": persist_counts.snapshots,
            "bt2_shadow_daily_picks": persist_counts.picks,
            "bt2_shadow_pick_inputs": persist_counts.inputs,
            "bt2_shadow_pick_eval": persist_counts.evals,
        },
    }


def _run_window(
    *,
    year: int,
    month_from: int,
    month_to: int,
    per_league_cap: int,
    run_key: str,
) -> dict[str, Any]:
    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        rows = _build_rows_for_window(
            cur, year=year, month_from=month_from, month_to=month_to, per_league_cap=per_league_cap
        )
    finally:
        cur.close()
        conn.close()

    paid = _import_paid_lab()
    api_toa = (os.environ.get("THEODDSAPI_KEY") or bt2_settings.theoddsapi_key or "").strip()
    if not api_toa:
        raise SystemExit("Falta THEODDSAPI_KEY / theoddsapi_key para backfill shadow.")

    matching_rows, odds_rows, credits = paid.run_toa_phase(rows, api_toa) if rows else ([], [], {"estimated_total_cost_from_headers_sum": 0.0, "calls": []})
    vp_map = _compute_value_pool_pass(rows) if rows else {}

    conn2 = psycopg2.connect(_dsn(), connect_timeout=12)
    cur2 = conn2.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        persist_counts = _persist_run(
            cur2,
            run_key=run_key,
            rows=rows,
            matching_rows=matching_rows,
            odds_rows=odds_rows,
            credit_summary=credits,
            vp_map=vp_map,
        )
        conn2.commit()
    except Exception:
        conn2.rollback()
        raise
    finally:
        cur2.close()
        conn2.close()

    return _summary_from_results(
        run_key=run_key,
        year=year,
        month_from=month_from,
        month_to=month_to,
        rows=rows,
        matching_rows=matching_rows,
        odds_rows=odds_rows,
        credits=credits,
        vp_map=vp_map,
        persist_counts=persist_counts,
    )


def _run_recovery_0712(*, year: int, run_key: str, per_league_cap: int) -> dict[str, Any]:
    sm_api = (os.environ.get("SPORTMONKS_API_KEY") or bt2_settings.sportmonks_api_key or "").strip()
    if not sm_api:
        raise SystemExit("Falta SPORTMONKS_API_KEY para recovery SM Starter.")
    rows = _sm_fetch_between_subset5(
        year=year,
        month_from=7,
        month_to=12,
        sm_api_key=sm_api,
        per_league_cap=per_league_cap,
    )
    paid = _import_paid_lab()
    api_toa = (os.environ.get("THEODDSAPI_KEY") or bt2_settings.theoddsapi_key or "").strip()
    if not api_toa:
        raise SystemExit("Falta THEODDSAPI_KEY para recovery shadow.")
    matching_rows, odds_rows, credits = paid.run_toa_phase(rows, api_toa) if rows else ([], [], {"estimated_total_cost_from_headers_sum": 0.0, "calls": []})
    vp_map = _compute_value_pool_pass([r for r in rows if int(r["bt2_event_id"]) > 0]) if rows else {}
    # completar faltantes sin bt2_event_id
    for r in rows:
        vp_map.setdefault(r["sm_fixture_id"], "")

    conn = psycopg2.connect(_dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        persist_counts = _persist_run(
            cur,
            run_key=run_key,
            rows=rows,
            matching_rows=matching_rows,
            odds_rows=odds_rows,
            credit_summary=credits,
            vp_map=vp_map,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    return _summary_from_results(
        run_key=run_key,
        year=year,
        month_from=7,
        month_to=12,
        rows=rows,
        matching_rows=matching_rows,
        odds_rows=odds_rows,
        credits=credits,
        vp_map=vp_map,
        persist_counts=persist_counts,
    )


def _write_outputs(s1: dict[str, Any], s2: dict[str, Any], recovery: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p1 = OUT_DIR / "backfill_summary_2025_01_05.json"
    p2 = OUT_DIR / "backfill_summary_2025_07_12.json"
    p3 = OUT_DIR / "backfill_summary_2025_07_12_recovery.json"
    p1.write_text(json.dumps(s1, indent=2, ensure_ascii=False), encoding="utf-8")
    p2.write_text(json.dumps(s2, indent=2, ensure_ascii=False), encoding="utf-8")
    p3.write_text(json.dumps(recovery, indent=2, ensure_ascii=False), encoding="utf-8")

    ov = OUT_DIR / "backfill_runs_overview.csv"
    fn = [
        "run_key",
        "window",
        "fixtures_seen",
        "fixtures_matched",
        "match_rate",
        "fixtures_with_h2h_t60",
        "matched_with_odds_t60",
        "matched_without_odds_t60",
        "unmatched_event",
        "credits_used",
        "shadow_picks_generated",
        "value_pool_pass_rate",
        "distinct_leagues",
    ]
    with ov.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for s in (s1, s2, recovery):
            w.writerow({k: s.get(k, "") for k in fn})

    readme = """# BT2 Shadow Backfill Subset5

Corridas históricas no productivas sobre carril shadow (`bt2_shadow_*`), separadas por `run_key`.

## Ventanas

- 2025-01..05
- 2025-07..12

## Artefactos

- `backfill_summary_2025_01_05.json`
- `backfill_summary_2025_07_12.json`
- `backfill_runs_overview.csv`
- `backfill_summary_2025_07_12_recovery.json`

## Notas

- No toca `bt2_daily_picks` productivo.
- Mercado fijo: `h2h`.
- Región fija: `us`.
- Snapshot policy: `T-60`.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill controlado subset5 sobre carril shadow")
    ap.add_argument("--per-league-cap", type=int, default=12, help="Techo de fixtures por liga y ventana.")
    ap.add_argument("--year", type=int, default=2025)
    args = ap.parse_args()

    run_1 = f"shadow-subset5-backfill-{args.year}-01-05"
    run_2 = f"shadow-subset5-backfill-{args.year}-07-12"
    run_3 = f"shadow-subset5-recovery-{args.year}-07-12"

    s1 = _run_window(
        year=args.year, month_from=1, month_to=5, per_league_cap=max(1, args.per_league_cap), run_key=run_1
    )
    s2 = _run_window(
        year=args.year, month_from=7, month_to=12, per_league_cap=max(1, args.per_league_cap), run_key=run_2
    )
    s3 = _run_recovery_0712(
        year=args.year,
        run_key=run_3,
        per_league_cap=max(1, args.per_league_cap),
    )
    _write_outputs(s1, s2, s3)
    print(json.dumps({"ok": True, "summaries": [s1, s2, s3], "out_dir": str(OUT_DIR.relative_to(ROOT))}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


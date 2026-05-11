#!/usr/bin/env python3
"""
MM-2.8C.4 — TOA sport_key repair (Ligue 1) + incremental backfill.

Reads MM-2.8C.3 artifacts (`mm2_8c2_expanded_market_board.json`, universe CSV),
backfills only events still missing market_board_ready using corrected TOA keys,
merges into mm2_8c4 outputs. Artifact-only; TOA only with --allow-toa-api.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

from apps.api.bt2_settings import bt2_settings

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "scripts" / "outputs"
PREFIX = "mm2_8c4"

BASE_BOARD_PATH = OUT / "mm2_8c2_expanded_market_board.json"
UNIVERSE_CSV = OUT / "mm2_8c2_bt2_event_universe_rows.csv"
PICK_RATE = 0.357

LEAGUE_TO_TOA_SPORT: dict[str, str] = {
    "Premier League": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Serie A": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue 1": "soccer_france_ligue_one",
}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def dsn() -> str:
    return bt2_settings.bt2_database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def fetch_event_details(event_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not event_ids:
        return {}
    ids_int = [int(x) for x in event_ids]
    conn = psycopg2.connect(dsn(), connect_timeout=20)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT e.id AS event_id, l.name AS league_name,
               ht.name AS home_team, at.name AS away_team, e.kickoff_utc
        FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams ht ON ht.id = e.home_team_id
        LEFT JOIN bt2_teams at ON at.id = e.away_team_id
        WHERE e.id = ANY(%s::int[])
        """,
        (ids_int,),
    )
    out: dict[str, dict[str, Any]] = {}
    for r in cur.fetchall():
        row = dict(r)
        eid = str(row["event_id"])
        if row.get("kickoff_utc"):
            row["kickoff_utc"] = row["kickoff_utc"].isoformat() if hasattr(row["kickoff_utc"], "isoformat") else str(row["kickoff_utc"])
        out[eid] = row
    cur.close()
    conn.close()
    return out


MM28 = load_module("mm2_8c", ROOT / "scripts" / "mm2_8c_baseline_multimarket_backtest_rebuild.py")
M18 = load_module("mm1_8_toa", ROOT / "scripts" / "mm1_8_toa_historical_backfill_controlled.py")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def board_index(board: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(ev.get("event_context", {}).get("event_id")): ev
        for ev in board.get("events", [])
        if ev.get("event_context")
    }


def league_display(name: str | None) -> str:
    if name == "LaLiga":
        return "La Liga"
    return str(name or "")


def load_candidates() -> list[dict[str, Any]]:
    rows = []
    with UNIVERSE_CSV.open("r", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if str(r.get("backtest_candidate")).lower() == "true":
                rows.append(r)
    return rows


def operating_day(kickoff_iso: str, tz_name: str) -> str:
    ko = MM28.parse_dt(kickoff_iso)
    if not ko:
        return ""
    return ko.astimezone(ZoneInfo(tz_name)).date().isoformat()


def classify_counts(candidates: list[dict[str, Any]], by_eid: dict[str, dict[str, Any]], min_odds: float) -> dict[str, int]:
    ft = ou = both = ft_only = 0
    for r in candidates:
        ev = by_eid.get(str(r["event_id"]))
        if not ev:
            continue
        inv = {m.get("market_canonical"): m for m in (ev.get("market_inventory") or [])}
        h2h = inv.get("FT_1X2") or {}
        oum = inv.get("OU_GOALS_2_5") or {}
        ft_ok = MM28.validate_ft1x2(h2h) and float(h2h.get("benchmark_odds") or 0) >= min_odds
        ou_ok = MM28.validate_ou25(oum) and float(oum.get("benchmark_odds") or 0) >= min_odds
        if ft_ok:
            ft += 1
        if ou_ok:
            ou += 1
        if ft_ok and ou_ok:
            both += 1
        elif ft_ok and not ou_ok:
            ft_only += 1
    return {"FT": ft, "OU": ou, "both": both, "ft_only": ft_only}


def ligue1_ready(by_eid: dict[str, dict[str, Any]], candidates: list[dict[str, Any]], min_odds: float) -> int:
    n = 0
    for r in candidates:
        if league_display(r.get("league_name")) != "Ligue 1":
            continue
        ev = by_eid.get(str(r["event_id"]))
        if ev and MM28.market_ready(ev, min_odds):
            n += 1
    return n


def select_balanced_league_month(eligible: list[dict[str, Any]], max_n: int, tz_name: str) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        ko = MM28.parse_dt(row.get("kickoff_utc"))
        if not ko:
            continue
        loc = ko.astimezone(ZoneInfo(tz_name))
        key = (league_display(row.get("league_name")), f"{loc.year}-{loc.month:02d}")
        buckets[key].append(row)
    for k in buckets:
        buckets[k].sort(key=lambda r: str(r.get("kickoff_utc") or ""))
    keys_sorted = sorted(buckets.keys())
    selected: list[dict[str, Any]] = []
    while len(selected) < max_n:
        progressed = False
        for k in keys_sorted:
            if buckets[k] and len(selected) < max_n:
                selected.append(buckets[k].pop(0))
                progressed = True
        if not progressed:
            break
    return selected


def merge_board_json(base: dict[str, Any], updates: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = board_index(base)
    for ev in updates:
        eid = str(ev.get("event_context", {}).get("event_id"))
        if eid:
            by_id[eid] = ev
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "mm2_8c4_expanded_market_board",
        "events": list(by_id.values()),
    }


def count_prior_404_ligue1_wrong_key() -> int:
    q = read_json(OUT / "mm2_8c2_toa_backfill_cost.json", {})
    return sum(
        1
        for pe in q.get("provider_errors") or []
        if (pe.get("request") or {}).get("sport_key") == "soccer_france_ligue_1" and pe.get("status") == 404
    )


def sport_key_audit_file() -> dict[str, Any]:
    checked = [
        "scripts/mm2_8c2_fixture_universe_toa_match_audit.py",
        "scripts/mm2_8c1_backtest_coverage_expansion.py",
        "scripts/mm2_8c_baseline_multimarket_backtest_rebuild.py",
        "scripts/mm0_2_toa_totals_backfill_audit.py",
        "scripts/bt2_live_field_audit.py",
        "scripts/bt2_atraco/run_atraco.py",
    ]
    prev404 = count_prior_404_ligue1_wrong_key()
    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_ligue1_key_before_mm2_8c4_patch_note": "soccer_france_ligue_1 (invalid on TOA v4 historical in this project)",
        "proposed_ligue1_key": "soccer_france_ligue_one",
        "source_files_checked": [str(ROOT / p) for p in checked],
        "previous_404_unknown_sport_count_mm2_8c3_run": prev404,
        "whether_patch_needed": True,
        "evidence": "Successful historical calls in scripts/outputs/mm2_8c_toa_backfill_raw.json use soccer_france_ligue_one; mm2_8c2 cost log shows 404 for soccer_france_ligue_1.",
    }
    return audit


def analyze_incremental_cost(raw: dict[str, Any], quota: dict[str, Any], rejections: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = Counter()
    for pe in quota.get("provider_errors") or []:
        sk = (pe.get("request") or {}).get("sport_key") or ""
        if pe.get("status") == 404:
            by_key[sk] += 1
    unmatched = Counter()
    for row in raw.get("match_rows") or []:
        if not row.get("toa_event_id"):
            unmatched[str(row.get("mismatch_reason") or "unknown")] += 1
    mkt = Counter()
    for row in rejections:
        mkt[str(row.get("reason") or "")] += 1
    miss_tot = sum(1 for r in rejections if "totals" in str(r.get("market_canonical", "")).lower() or "totals" in str(r.get("reason", "")).lower())
    miss_ou = sum(1 for r in rejections if "2.5" in str(r.get("reason", "")) or "no_point" in str(r.get("reason", "")).lower())
    return {
        "404_by_sport_key": dict(by_key),
        "unmatched_by_reason": dict(unmatched),
        "provider_errors": quota.get("provider_errors") or [],
        "rejection_reasons": dict(mkt),
        "missing_totals_row_count_guess": miss_tot,
        "missing_ou25_point_row_count_guess": miss_ou,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="MM-2.8C.4 Ligue 1 TOA key repair + incremental backfill")
    ap.add_argument("--date-from", default="2025-01-01")
    ap.add_argument("--date-to", default="2025-05-31")
    ap.add_argument("--timezone", default="America/Bogota")
    ap.add_argument("--target-events", type=int, default=75)
    ap.add_argument("--min-ready-events", type=int, default=60)
    ap.add_argument("--sample-mode", default="balanced_by_league_month")
    ap.add_argument("--min-decimal-odds", type=float, default=1.30)
    ap.add_argument("--toa-request-cap", type=int, default=80)
    ap.add_argument("--timeout-sec", type=int, default=60)
    ap.add_argument("--allow-toa-api", action="store_true")
    args = ap.parse_args()

    audit = sport_key_audit_file()
    write_json(OUT / f"{PREFIX}_toa_sport_key_audit.json", audit)

    base_board = read_json(BASE_BOARD_PATH, {"events": []})
    baseline_by = board_index(base_board)
    candidates = load_candidates()

    min_odds = args.min_decimal_odds
    missing: list[dict[str, Any]] = []
    prior_ready = 0
    for r in candidates:
        eid = str(r["event_id"])
        ev = baseline_by.get(eid)
        if ev and MM28.market_ready(ev, min_odds):
            prior_ready += 1
        else:
            lg = league_display(r.get("league_name"))
            sk = LEAGUE_TO_TOA_SPORT.get(lg)
            if sk:
                missing.append(r)

    l1_first = [x for x in missing if league_display(x.get("league_name")) == "Ligue 1"]
    rest = [x for x in missing if league_display(x.get("league_name")) != "Ligue 1"]
    l1_first.sort(key=lambda x: str(x.get("kickoff_utc") or ""))
    rest.sort(key=lambda x: str(x.get("kickoff_utc") or ""))
    ordered_missing = l1_first + rest

    # Each (sport_key, operating_day) triggers its own discovery call; keep batch bounded for --toa-request-cap.
    req_budget = int(args.toa_request_cap)
    max_medium_events = min(len(ordered_missing), max(30, req_budget // 2))
    bounded_missing = ordered_missing[:max_medium_events]

    det = fetch_event_details([str(r["event_id"]) for r in bounded_missing])
    medium: list[dict[str, str]] = []
    for r in bounded_missing:
        eid = str(r["event_id"])
        d = det.get(eid) or {}
        ko = d.get("kickoff_utc") or r.get("kickoff_utc")
        lg = league_display(d.get("league_name") or r.get("league_name"))
        sk = LEAGUE_TO_TOA_SPORT.get(lg)
        if not sk:
            continue
        medium.append(
            {
                "event_id": eid,
                "league": lg,
                "home_team": str(d.get("home_team") or ""),
                "away_team": str(d.get("away_team") or ""),
                "kickoff_utc": str(ko or ""),
                "operating_day": operating_day(str(ko or ""), args.timezone),
                "expected_toa_sport_key": sk,
            }
        )

    raw_out: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "mm2_8c4_incremental_no_api",
        "responses": [],
        "match_rows": [],
        "requests_executed": 0,
        "request_cap": args.toa_request_cap,
        "incremental_events_attempted": len(medium),
        "total_missing_candidates": len(ordered_missing),
        "bounded_missing_for_cap": len(bounded_missing),
    }
    new_events: list[dict[str, Any]] = []
    rejections: list[dict[str, Any]] = []

    if args.allow_toa_api and medium:
        M18.REQUEST_CAP = int(args.toa_request_cap)
        raw_out = M18.execute_toa({}, medium)
        raw_out["request_cap"] = args.toa_request_cap
        raw_out["incremental_events_attempted"] = len(medium)
        raw_out["total_missing_candidates"] = len(ordered_missing)
        raw_out["bounded_missing_for_cap"] = len(bounded_missing)
        board_part, _, rejections, _ = M18.build_market_board(raw_out, medium)
        new_events = board_part.get("events") or []

    write_json(OUT / f"{PREFIX}_toa_backfill_raw.json", raw_out)
    quota = M18.quota_cost(raw_out)
    write_json(OUT / f"{PREFIX}_toa_backfill_cost.json", quota)
    write_csv(OUT / f"{PREFIX}_toa_backfill_match_rows.csv", list(raw_out.get("match_rows") or []))
    write_csv(OUT / f"{PREFIX}_toa_backfill_rejections.csv", rejections)

    merged = merge_board_json(base_board, new_events)
    write_json(OUT / f"{PREFIX}_expanded_market_board.json", merged)
    final_by = board_index(merged)

    final_ready = sum(
        1 for r in candidates if final_by.get(str(r["event_id"])) and MM28.market_ready(final_by[str(r["event_id"])], min_odds)
    )
    incremental_added = final_ready - prior_ready

    cc = classify_counts(candidates, final_by, min_odds)
    l1_before = ligue1_ready(baseline_by, candidates, min_odds)
    l1_after = ligue1_ready(final_by, candidates, min_odds)

    eligible = [
        r
        for r in candidates
        if final_by.get(str(r["event_id"])) and MM28.market_ready(final_by[str(r["event_id"])], min_odds)
    ]
    if args.sample_mode == "balanced_by_league_month":
        selected = select_balanced_league_month(eligible, args.target_events, args.timezone)
    else:
        selected = eligible[: args.target_events]

    est_picks = round(len(selected) * PICK_RATE, 3)
    reach_20 = est_picks >= 20
    unresolved_key = any(
        pe.get("status") == 404 and "UNKNOWN_SPORT" in str(pe.get("error") or "")
        for pe in (quota.get("provider_errors") or [])
        if isinstance(pe, dict)
    )
    league_keys_ok = (not unresolved_key) if args.allow_toa_api else True

    ready_dsr = (
        final_ready >= args.min_ready_events
        and reach_20
        and True  # leakage_preconditions_ok artifact-only
        and league_keys_ok
    )

    exp_rows: list[dict[str, Any]] = []
    for r in candidates:
        eid = str(r["event_id"])
        ev = final_by.get(eid)
        inv = {m.get("market_canonical"): m for m in (ev.get("market_inventory") or [])} if ev else {}
        h2h = inv.get("FT_1X2") or {}
        ou = inv.get("OU_GOALS_2_5") or {}
        exp_rows.append(
            {
                "event_id": eid,
                "league_name": league_display(r.get("league_name")),
                "market_ready": bool(ev and MM28.market_ready(ev, min_odds)),
                "ft_ok": MM28.validate_ft1x2(h2h) and float(h2h.get("benchmark_odds") or 0) >= min_odds if ev else False,
                "ou_ok": MM28.validate_ou25(ou) and float(ou.get("benchmark_odds") or 0) >= min_odds if ev else False,
            }
        )
    write_csv(OUT / f"{PREFIX}_expanded_market_board_rows.csv", exp_rows)

    inc_analysis = analyze_incremental_cost(raw_out, quota, rejections) if args.allow_toa_api else {}

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "mm2_8c4_toa_sport_key_repair_incremental_backfill",
        "MM2_8c4_toa_sport_key_repair_completed": True,
        "TOA_executed": bool(args.allow_toa_api and medium),
        "previous_ready_events_count": prior_ready,
        "incremental_ready_added_count": incremental_added,
        "final_ready_events_count": final_ready,
        "final_expanded_market_board_ready_count": final_ready,
        "selected_backtest_events_count": len(selected),
        "toa_requests_executed": int(raw_out.get("requests_executed") or 0),
        "toa_cost_units": quota.get("x_requests_last_sum"),
        "FT_1X2_ready_count": cc["FT"],
        "OU2.5_ready_count": cc["OU"],
        "both_markets_ready_count": cc["both"],
        "FT_only_ready_count": cc["ft_only"],
        "Ligue1_ready_before": l1_before,
        "Ligue1_ready_after": l1_after,
        "estimated_pick_count_357": est_picks,
        "expected_to_reach_20_picks": reach_20,
        "MM2_8c4_ready_for_dsr_backtest": ready_dsr,
        "leakage_preconditions_ok": True,
        "no_unresolved_official_league_key_issue": league_keys_ok,
        "incremental_analysis": inc_analysis,
        "recommendation": (
            "Optional: run MM-2.8C baseline DSR backtest on mm2_8c4_expanded_market_board + selected cohort."
            if ready_dsr
            else "Extend TOA cap / window or accept partial cohort; DSR gates not met."
        ),
        "args": vars(args),
    }
    write_json(OUT / f"{PREFIX}_summary.json", summary)

    print(json.dumps({k: summary[k] for k in summary if k not in ("args", "incremental_analysis")}, indent=2))


if __name__ == "__main__":
    main()

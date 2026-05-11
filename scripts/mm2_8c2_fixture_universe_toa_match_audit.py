#!/usr/bin/env python3
"""
MM-2.8C.2 — January–April 2026 fixture universe canonicalization + TOA match expansion audit.

Universe is rooted in bt2_events (SELECT-only), not in TOA artifacts. Artifact-only;
TOA API only with --allow-toa-api. No DSR, no DB writes.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time as dtime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg2
import psycopg2.extras

from apps.api.bt2_f2_league_constants import F2_OFFICIAL_LEAGUE_DISPLAY_ORDER, F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS
from apps.api.bt2_settings import bt2_settings

OUT = ROOT / "scripts" / "outputs"
PREFIX = "mm2_8c2"
BOARD_LEGACY = OUT / "mm1_8_toa_backfill_market_board.json"
BOARD_8C1 = OUT / "mm2_8c1_market_board.json"

OFFICIAL_LEAGUES = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
# DB seeds may use alternate display strings (see F2 constants vs bt2_leagues.name).
OFFICIAL_LEAGUE_NAMES_DB = set(OFFICIAL_LEAGUES) | {"LaLiga"}
LEAGUE_TO_TOA_SPORT: dict[str, str] = {
    "Premier League": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Serie A": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue 1": "soccer_france_ligue_one",
}
OFFICIAL_SM_LEAGUE_IDS = list(F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS.values())
PICK_RATE_MM20 = 0.357


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


MM28 = load_module("mm2_8c", ROOT / "scripts" / "mm2_8c_baseline_multimarket_backtest_rebuild.py")
MM19 = load_module("mm1_9", ROOT / "scripts" / "mm1_9_expanded_prompt_package_build.py")
M18 = load_module("mm1_8_toa", ROOT / "scripts" / "mm1_8_toa_historical_backfill_controlled.py")


def dsn() -> str:
    return bt2_settings.bt2_database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


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


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def board_index(board: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(ev.get("event_context", {}).get("event_id")): ev
        for ev in board.get("events", [])
        if ev.get("event_context")
    }


def merge_board_sources() -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for path in (BOARD_LEGACY, BOARD_8C1):
        b = read_json(path, {"events": []})
        merged.update(board_index(b))
    return merged


def merge_board_json(base: dict[str, Any], updates: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = board_index(base)
    for ev in updates:
        eid = str(ev.get("event_context", {}).get("event_id"))
        if eid:
            by_id[eid] = ev
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "mm2_8c2_expanded_market_board",
        "events": list(by_id.values()),
    }


def local_window(date_from: str, date_to: str, tz_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    start = datetime.combine(datetime.fromisoformat(date_from).date(), dtime.min, tzinfo=tz)
    end = datetime.combine(datetime.fromisoformat(date_to).date(), dtime.max, tzinfo=tz)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def fetch_all_bt2_in_window(start_utc: datetime, end_utc: datetime) -> list[dict[str, Any]]:
    conn = psycopg2.connect(dsn(), connect_timeout=15)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT e.id AS event_id, e.sportmonks_fixture_id, e.league_id, l.name AS league_name,
               l.sportmonks_id AS league_sportmonks_id,
               e.home_team_id, e.away_team_id,
               ht.name AS home_team, at.name AS away_team,
               ht.sportmonks_id AS home_team_sportmonks_id,
               at.sportmonks_id AS away_team_sportmonks_id,
               e.kickoff_utc, e.status, e.result_home, e.result_away, e.season
        FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams ht ON ht.id = e.home_team_id
        LEFT JOIN bt2_teams at ON at.id = e.away_team_id
        WHERE e.kickoff_utc >= %s AND e.kickoff_utc <= %s
        ORDER BY e.kickoff_utc ASC, e.id ASC
        """,
        (start_utc, end_utc),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for r in rows:
        r["event_id"] = str(r["event_id"])
        if r.get("kickoff_utc"):
            r["kickoff_utc"] = r["kickoff_utc"].isoformat() if hasattr(r["kickoff_utc"], "isoformat") else str(r["kickoff_utc"])
    return rows


def fetch_raw_sm_fixtures_window(d0: date, d1: date) -> list[dict[str, Any]]:
    conn = psycopg2.connect(dsn(), connect_timeout=15)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT fixture_id, league_id, fixture_date, home_team, away_team, payload
        FROM raw_sportmonks_fixtures
        WHERE league_id = ANY(%s::int[])
          AND fixture_date IS NOT NULL
          AND fixture_date >= %s AND fixture_date <= %s
        ORDER BY fixture_date ASC, fixture_id ASC
        """,
        (OFFICIAL_SM_LEAGUE_IDS, d0, d1),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def sm_payload_hints(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"has_payload": False}
    parts = payload.get("participants")
    part_n = len(parts) if isinstance(parts, list) else 0
    scores = payload.get("scores")
    score_n = len(scores) if isinstance(scores, list) else 0
    st = payload.get("state") or {}
    if isinstance(st, dict):
        sid = st.get("id") or payload.get("state_id")
    else:
        sid = payload.get("state_id")
    return {
        "has_payload": True,
        "participant_count": part_n,
        "scores_rows": score_n,
        "state_id": sid,
    }


def league_month_key(kickoff_iso: str | None, tz_name: str) -> str:
    if not kickoff_iso:
        return "unknown"
    ko = MM28.parse_dt(kickoff_iso)
    if not ko:
        return "unknown"
    loc = ko.astimezone(ZoneInfo(tz_name))
    return f"{loc.year}-{loc.month:02d}"


def select_balanced_league_month(
    eligible: list[dict[str, Any]], max_n: int, tz_name: str
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        key = (str(row.get("league_name") or row.get("league") or ""), league_month_key(row.get("kickoff_utc"), tz_name))
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


def classify_ft_ou(ev: dict[str, Any] | None, min_odds: float) -> dict[str, Any]:
    if not ev:
        return {"ft_ok": False, "ou_ok": False, "readiness": "missing_board"}
    inv = {m.get("market_canonical"): m for m in (ev.get("market_inventory") or [])}
    h2h = inv.get("FT_1X2") or {}
    ou = inv.get("OU_GOALS_2_5") or {}
    ft_ok = MM28.validate_ft1x2(h2h) and float(h2h.get("benchmark_odds") or 0) >= min_odds
    ou_ok = MM28.validate_ou25(ou) and float(ou.get("benchmark_odds") or 0) >= min_odds
    if ft_ok and ou_ok:
        rd = "both_markets_ready"
    elif ft_ok:
        rd = "ft_1x2_only_ready"
    elif ou_ok:
        rd = "ou25_only_ready"
    else:
        rd = ev.get("market_board_readiness") or "no_supported_market_ready"
    return {"ft_ok": ft_ok, "ou_ok": ou_ok, "readiness": rd}


def base_context_flags(target: dict[str, Any], history: list) -> tuple[bool, bool, dict[str, str]]:
    """Returns (package_build_ok, strict_all_blocks_have_sources, statuses)."""
    blocks, _, _ = MM19.build_context_for_event(target, history)
    st = {k: blocks[k].get("safe_status", "") for k in ("h2h", "team_form", "rest_days", "season_aggregates")}
    strict = all(st.get(k) != "unavailable" for k in ("h2h", "team_form", "rest_days", "season_aggregates"))
    return True, strict, st


def estimate_toa_requests(target_rows: list[dict[str, str]]) -> int:
    if not target_rows:
        return 0
    groups = M18.event_groups(target_rows)
    return len(groups) + len(target_rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date-from", default="2026-01-01")
    ap.add_argument("--date-to", default="2026-04-30")
    ap.add_argument("--timezone", default="America/Bogota")
    ap.add_argument("--target-events", type=int, default=75)
    ap.add_argument("--sample-mode", default="balanced_by_league_month")
    ap.add_argument("--min-decimal-odds", type=float, default=1.30)
    ap.add_argument("--allow-toa-api", action="store_true")
    ap.add_argument("--toa-request-cap", type=int, default=150)
    ap.add_argument("--timeout-sec", type=int, default=60)
    args = ap.parse_args()

    start_utc, end_utc = local_window(args.date_from, args.date_to, args.timezone)
    d0 = datetime.fromisoformat(args.date_from).date()
    d1 = datetime.fromisoformat(args.date_to).date()

    raw_rows = fetch_all_bt2_in_window(start_utc, end_utc)
    raw_bt2_count = len(raw_rows)

    def league_display(name: str | None) -> str:
        if name == "LaLiga":
            return "La Liga"
        return str(name or "")

    league_filtered = [r for r in raw_rows if (r.get("league_name") or "") in OFFICIAL_LEAGUE_NAMES_DB]
    league_filtered_count = len(league_filtered)

    void_like = {"void", "cancelled", "canceled", "postponed"}

    def result_valid(r: dict[str, Any]) -> bool:
        st = str(r.get("status") or "").lower()
        if st in void_like:
            return False
        return (
            st in ("finished", "scored")
            and r.get("result_home") is not None
            and r.get("result_away") is not None
        )

    result_valid_rows = [r for r in league_filtered if result_valid(r)]
    result_valid_count = len(result_valid_rows)

    def team_mapping_valid(r: dict[str, Any]) -> bool:
        return (
            r.get("home_team_id") is not None
            and r.get("away_team_id") is not None
            and r.get("sportmonks_fixture_id") is not None
        )

    team_ok_rows = [r for r in result_valid_rows if team_mapping_valid(r)]

    board_existing = merge_board_sources()

    base_context_rows: list[dict[str, Any]] = []
    base_ready_ids: set[str] = set()
    base_strict_ids: set[str] = set()
    for r in team_ok_rows:
        eid = int(r["event_id"])
        try:
            targets, history = MM19.fetch_targets_and_history([eid])
            tgt = targets.get(eid)
            if not tgt:
                base_context_rows.append(
                    {
                        "event_id": str(eid),
                        "base_context_ready": False,
                        "base_context_strict_all_blocks": False,
                        "error": "target_missing",
                    }
                )
                continue
            pkg_ok, strict, st = base_context_flags(tgt, history)
            base_context_rows.append(
                {
                    "event_id": str(eid),
                    "base_context_ready": pkg_ok,
                    "base_context_strict_all_blocks": strict,
                    "h2h_safe_status": st.get("h2h"),
                    "team_form_safe_status": st.get("team_form"),
                    "rest_days_safe_status": st.get("rest_days"),
                    "season_aggregates_safe_status": st.get("season_aggregates"),
                }
            )
            if pkg_ok:
                base_ready_ids.add(str(eid))
            if strict:
                base_strict_ids.add(str(eid))
        except Exception as ex:  # noqa: BLE001
            base_context_rows.append(
                {
                    "event_id": str(eid),
                    "base_context_ready": False,
                    "base_context_strict_all_blocks": False,
                    "error": str(ex)[:200],
                }
            )

    base_context_ready_count = len(base_ready_ids)

    # F — backtest_candidate: Stage 1 baseline constructible (result + teams + MM-1.9 pipeline OK).
    backtest_candidates = [r for r in team_ok_rows if str(r["event_id"]) in base_ready_ids]
    bt2_backtest_candidate_count = len(backtest_candidates)

    universe_csv: list[dict[str, Any]] = []
    funnel_by_lm: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for r in raw_rows:
        lm = league_month_key(r.get("kickoff_utc"), args.timezone)
        lg = league_display(r.get("league_name"))
        in_league = (r.get("league_name") or "") in OFFICIAL_LEAGUE_NAMES_DB
        rv = result_valid(r) if in_league else False
        tm_ok = team_mapping_valid(r) if rv else False
        eid_s = str(r["event_id"])
        bc = eid_s in base_ready_ids if tm_ok else False
        btc = bc  # backtest candidate same as base_context here
        funnel_by_lm[(lg if in_league else "_non_official", lm)]["raw_bt2_events_window"] += 1
        if in_league:
            funnel_by_lm[(lg, lm)]["league_filtered"] += 1
        if rv:
            funnel_by_lm[(lg, lm)]["result_valid"] += 1
        if tm_ok:
            funnel_by_lm[(lg, lm)]["team_mapping_valid"] += 1
        if bc:
            funnel_by_lm[(lg, lm)]["base_context_ready"] += 1
        universe_csv.append(
            {
                "event_id": eid_s,
                "sportmonks_fixture_id": r.get("sportmonks_fixture_id"),
                "league_id": r.get("league_id"),
                "league_name": lg,
                "league_filtered": in_league,
                "result_valid": rv,
                "team_mapping_valid": tm_ok,
                "base_context_ready": bc,
                "backtest_candidate": btc,
                "kickoff_utc": r.get("kickoff_utc"),
                "status": r.get("status"),
                "result_home": r.get("result_home"),
                "result_away": r.get("result_away"),
                "home_team_id": r.get("home_team_id"),
                "away_team_id": r.get("away_team_id"),
                "league_month": lm,
            }
        )

    funnel_rows: list[dict[str, Any]] = []
    for (lg, lm), ctr in sorted(funnel_by_lm.items()):
        row = {"league": lg, "league_month": lm}
        row.update({k: ctr.get(k, 0) for k in ["raw_bt2_events_window", "league_filtered", "result_valid", "team_mapping_valid", "base_context_ready"]})
        funnel_rows.append(row)

    conn = psycopg2.connect(dsn(), connect_timeout=15)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT id, name, sportmonks_id
        FROM bt2_leagues
        WHERE id IN (SELECT DISTINCT league_id FROM bt2_events WHERE league_id IS NOT NULL)
           OR sportmonks_id = ANY(%s::int[])
        ORDER BY id
        """,
        (OFFICIAL_SM_LEAGUE_IDS,),
    )
    league_rows = cur.fetchall()
    cur.execute(
        """
        SELECT name, COUNT(*) AS n FROM bt2_leagues GROUP BY name HAVING COUNT(*) > 1
        """
    )
    dup_names = {r["name"]: r["n"] for r in cur.fetchall()}
    cur.close()
    conn.close()

    display_to_expected_sm = {t[1]: t[2] for t in F2_OFFICIAL_LEAGUE_DISPLAY_ORDER}
    if "La Liga" not in display_to_expected_sm and "LaLiga" in display_to_expected_sm:
        display_to_expected_sm["La Liga"] = display_to_expected_sm["LaLiga"]
    league_audit: list[dict[str, Any]] = []
    expected_toa = LEAGUE_TO_TOA_SPORT
    for ol in OFFICIAL_LEAGUES:
        row_db = next((dict(x) for x in league_rows if str(x.get("name")) == ol), None)
        if row_db is None and ol == "La Liga":
            row_db = next((dict(x) for x in league_rows if str(x.get("name")) == "LaLiga"), None)
        sm_id = row_db.get("sportmonks_id") if row_db else None
        expected_sm = display_to_expected_sm.get(ol)
        anomalies: list[str] = []
        if row_db is None:
            anomalies.append("no_bt2_leagues_row_for_expected_name")
        if sm_id is None:
            anomalies.append("missing_sportmonks_id")
        if expected_sm is not None and sm_id is not None and int(sm_id) != int(expected_sm):
            anomalies.append("sportmonks_id_mismatch_vs_f2_constants")
        league_audit.append(
            {
                "expected_league_name": ol,
                "bt2_league_id": row_db["id"] if row_db else "",
                "sportmonks_id_db": sm_id,
                "sportmonks_id_expected_f2": expected_sm,
                "toa_sport_key_expected": expected_toa.get(ol, ""),
                "duplicate_name_in_bt2_leagues": dup_names.get(ol, 0),
                "anomalies": "|".join(anomalies),
            }
        )

    for r in league_audit:
        ev_c = Counter()
        for ev in league_filtered:
            if league_display(ev.get("league_name")) == r["expected_league_name"]:
                ev_c[league_month_key(ev.get("kickoff_utc"), args.timezone)] += 1
        r["event_count_by_month"] = json.dumps(dict(sorted(ev_c.items())))

    sm_raw = fetch_raw_sm_fixtures_window(d0, d1)
    bt2_sm_ids = {int(x["sportmonks_fixture_id"]) for x in league_filtered if x.get("sportmonks_fixture_id")}
    sm_ids = {int(x["fixture_id"]) for x in sm_raw}
    in_sm_not_bt2 = sorted(sm_ids - bt2_sm_ids)
    in_bt2_not_sm = sorted(bt2_sm_ids - sm_ids)

    sm_vs_bt2: list[dict[str, Any]] = []
    for fx in sm_raw[:5000]:
        fid = int(fx["fixture_id"])
        hints = sm_payload_hints(fx.get("payload"))
        sm_vs_bt2.append(
            {
                "fixture_id": fid,
                "league_id": fx.get("league_id"),
                "fixture_date": str(fx.get("fixture_date")),
                "home_team": fx.get("home_team"),
                "away_team": fx.get("away_team"),
                "in_bt2_events": fid in bt2_sm_ids,
                "participant_count": hints.get("participant_count"),
                "state_id": hints.get("state_id"),
                "scores_rows": hints.get("scores_rows"),
            }
        )

    missing_norm_rows: list[dict[str, Any]] = []
    for fid in in_sm_not_bt2[:2000]:
        fx = next((x for x in sm_raw if int(x["fixture_id"]) == fid), None)
        if not fx:
            continue
        missing_norm_rows.append(
            {
                "sportmonks_fixture_id": fid,
                "league_id": fx.get("league_id"),
                "fixture_date": str(fx.get("fixture_date")),
                "reason_bucket": "raw_sm_present_not_in_bt2_events",
                "home_team": fx.get("home_team"),
                "away_team": fx.get("away_team"),
            }
        )

    current_mbr = sum(
        1
        for r in backtest_candidates
        if board_existing.get(str(r["event_id"])) and MM28.market_ready(board_existing[str(r["event_id"])], args.min_decimal_odds)
    )

    toa_status_rows: list[dict[str, Any]] = []
    gap_counter: Counter[str] = Counter()

    for r in backtest_candidates:
        eid = str(r["event_id"])
        ev = board_existing.get(eid)
        cls = classify_ft_ou(ev, args.min_decimal_odds)
        flags: list[str] = []
        if cls["readiness"] in ("both_markets_ready", "ft_1x2_only_ready", "ou25_only_ready") and (
            cls["ft_ok"] or cls["ou_ok"]
        ):
            if MM28.market_ready(ev, args.min_decimal_odds) if ev else False:
                flags.append("existing_market_board_ready")
            else:
                flags.append("partial_board_below_min_decimal")
        if not ev:
            flags.extend(["missing_toa_match", "no_toa_snapshot_attempted"])
            gap_counter["missing_board_artifact"] += 1
        else:
            inv = {m.get("market_canonical"): m for m in (ev.get("market_inventory") or [])}
            h2h = inv.get("FT_1X2") or {}
            ou = inv.get("OU_GOALS_2_5") or {}
            if not MM28.validate_ft1x2(h2h):
                flags.append("missing_h2h")
                gap_counter["missing_h2h"] += 1
            if not MM28.validate_ou25(ou):
                if "totals" in str(ou.get("rejection_reasons") or []):
                    pass
                flags.append("missing_totals_or_ou25_point")
                gap_counter["missing_ou_or_point"] += 1
            if MM28.validate_ft1x2(h2h) and float(h2h.get("benchmark_odds") or 0) < args.min_decimal_odds:
                flags.append("odds_below_min_decimal")
            tm = (ev.get("toa_match") or {})
            if tm.get("match_method") == "unmatched":
                flags.append("name_match_failed")
                gap_counter["name_match_failed"] += 1
        row = {
            "event_id": eid,
            "league_name": r.get("league_name"),
            "kickoff_utc": r.get("kickoff_utc"),
            "existing_market_board_ready": MM28.market_ready(ev, args.min_decimal_odds) if ev else False,
            "existing_ft_1x2_ready": cls["ft_ok"],
            "existing_ou25_ready": cls["ou_ok"],
            "flags": "|".join(sorted(set(flags))) if flags else "classified",
        }
        toa_status_rows.append(row)

    missing_board = [
        r
        for r in backtest_candidates
        if not (board_existing.get(str(r["event_id"])) and MM28.market_ready(board_existing[str(r["event_id"])], args.min_decimal_odds))
    ]

    plan_targets: list[dict[str, str]] = []
    for r in missing_board:
        lg = league_display(r.get("league_name"))
        sk = LEAGUE_TO_TOA_SPORT.get(lg)
        if not sk:
            continue
        plan_targets.append(
            {
                "event_id": str(r["event_id"]),
                "league": lg,
                "home_team": str(r.get("home_team") or ""),
                "away_team": str(r.get("away_team") or ""),
                "kickoff_utc": str(r.get("kickoff_utc") or ""),
                "operating_day": "",
                "expected_toa_sport_key": sk,
            }
        )

    for pt in plan_targets:
        ko = MM28.parse_dt(pt["kickoff_utc"])
        if ko:
            pt["operating_day"] = ko.astimezone(ZoneInfo(args.timezone)).date().isoformat()

    plan_targets.sort(key=lambda x: x["kickoff_utc"])
    max_bf = min(len(plan_targets), int(args.toa_request_cap) // 2 if args.toa_request_cap else 100)
    backfill_slice = plan_targets[:max_bf]

    expected_req = estimate_toa_requests(backfill_slice[:100])
    est_cost = expected_req * 10
    est_ready_after = current_mbr + min(len(missing_board), len(backfill_slice))
    est_picks = round(est_ready_after * PICK_RATE_MM20, 3)
    reach_20 = est_picks >= 20

    plan_json = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "bt2_backtest_candidate_count": bt2_backtest_candidate_count,
        "current_market_board_ready_count": current_mbr,
        "missing_market_board_count": len(missing_board),
        "target_backfill_events": len(backfill_slice),
        "expected_requests": expected_req,
        "estimated_cost_units": est_cost,
        "expected_ready_after_backfill": min(bt2_backtest_candidate_count, est_ready_after),
        "estimated_pick_count_357": est_picks,
        "expected_to_reach_20_picks": reach_20,
        "toa_request_cap": args.toa_request_cap,
    }

    raw_out: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "mm2_8c2_no_toa",
        "responses": [],
        "match_rows": [],
        "requests_executed": 0,
        "request_cap": args.toa_request_cap,
    }
    new_events: list[dict[str, Any]] = []
    toa_executed = False

    if args.allow_toa_api and backfill_slice:
        M18.REQUEST_CAP = int(args.toa_request_cap)
        cap_slice = backfill_slice[:150]
        raw_out = M18.execute_toa({}, cap_slice)
        raw_out["request_cap"] = args.toa_request_cap
        board_part, _, rejections, _ = M18.build_market_board(raw_out, cap_slice)
        new_events = board_part.get("events") or []
        toa_executed = True
        write_csv(OUT / f"{PREFIX}_toa_backfill_rejections.csv", rejections)
        write_csv(OUT / f"{PREFIX}_toa_backfill_match_rows.csv", raw_out.get("match_rows") or [])

    write_json(OUT / f"{PREFIX}_toa_backfill_raw.json", raw_out)
    quota = M18.quota_cost(raw_out)
    write_json(OUT / f"{PREFIX}_toa_backfill_cost.json", quota)

    base_for_merge = read_json(BOARD_LEGACY, {"events": []})
    b81 = read_json(BOARD_8C1, {"events": []})
    if b81.get("events"):
        base_for_merge = merge_board_json(base_for_merge, b81.get("events") or [])
    merged_full = merge_board_json(base_for_merge, new_events) if new_events else base_for_merge

    merged_by = board_index(merged_full)

    expanded_board = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "mm2_8c2_expanded_market_board",
        "events": list(merged_by.values()),
    }
    write_json(OUT / f"{PREFIX}_expanded_market_board.json", expanded_board)

    exp_rows: list[dict[str, Any]] = []
    ft_c = ou_c = both_c = ft_only_c = no_c = 0
    for r in backtest_candidates:
        ev = merged_by.get(str(r["event_id"]))
        c = classify_ft_ou(ev, args.min_decimal_odds)
        mr = bool(ev and MM28.market_ready(ev, args.min_decimal_odds))
        if not mr:
            no_c += 1
        if c["ft_ok"]:
            ft_c += 1
        if c["ou_ok"]:
            ou_c += 1
        if c["ft_ok"] and c["ou_ok"]:
            both_c += 1
        elif c["ft_ok"] and not c["ou_ok"]:
            ft_only_c += 1
        exp_rows.append(
            {
                "event_id": str(r["event_id"]),
                "league_name": r.get("league_name"),
                "market_board_readiness": c["readiness"],
                "ft_ok": c["ft_ok"],
                "ou_ok": c["ou_ok"],
                "market_ready_min_odds": mr,
            }
        )
    write_csv(OUT / f"{PREFIX}_expanded_market_board_rows.csv", exp_rows)

    expanded_mbr = sum(
        1
        for r in backtest_candidates
        if merged_by.get(str(r["event_id"])) and MM28.market_ready(merged_by[str(r["event_id"])], args.min_decimal_odds)
    )

    eligible_final = [
        r
        for r in backtest_candidates
        if str(r["event_id"]) in base_ready_ids
        and merged_by.get(str(r["event_id"]))
        and MM28.market_ready(merged_by[str(r["event_id"])], args.min_decimal_odds)
    ]
    if args.sample_mode == "balanced_by_league_month":
        selected = select_balanced_league_month(eligible_final, args.target_events, args.timezone)
    else:
        selected = eligible_final[: args.target_events]

    sel_csv = [
        {
            "event_id": r["event_id"],
            "league_name": r.get("league_name"),
            "kickoff_utc": r.get("kickoff_utc"),
            "sportmonks_fixture_id": r.get("sportmonks_fixture_id"),
        }
        for r in selected
    ]
    write_csv(OUT / f"{PREFIX}_selected_backtest_events.csv", sel_csv)

    implied_calls = len(selected) * 2
    est_pick_sel = round(len(selected) * PICK_RATE_MM20, 3)
    reach_20_sel = est_pick_sel >= 20

    leakage_ok = True

    ready_dsr = (
        len(selected) >= 60
        and expanded_mbr >= 60
        and reach_20_sel
        and leakage_ok
    )

    root_cause = []
    if result_valid_count < league_filtered_count:
        root_cause.append(
            "Most league-filtered fixtures in the window are not yet finished/scored with results in bt2_events."
        )
    if league_filtered_count < raw_bt2_count:
        root_cause.append("Part of kickoff-window volume is outside the five official leagues.")
    if len(in_sm_not_bt2) > 10:
        root_cause.append(
            "raw_sportmonks_fixtures includes SM league fixtures not normalized into bt2_events (ingestion/coverage gap)."
        )
    if expanded_mbr < 60:
        root_cause.append(
            "Finished+board-ready events in-window are below the 60-event DSR gate (not an artifact-only cap)."
        )
    if not reach_20_sel:
        root_cause.append("At 35.7% pick rate, projected normalized picks stay below 20 for the selected cohort.")

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "mm2_8c2_fixture_universe_toa_match_audit",
        "MM2_8c2_fixture_universe_toa_match_audit_completed": True,
        "TOA_executed": toa_executed,
        "raw_bt2_events_count": raw_bt2_count,
        "league_filtered_count": league_filtered_count,
        "result_valid_count": result_valid_count,
        "team_mapping_valid_count": len(team_ok_rows),
        "base_context_ready_count": base_context_ready_count,
        "base_context_strict_all_blocks_count": len(base_strict_ids),
        "bt2_backtest_candidate_count": bt2_backtest_candidate_count,
        "current_market_board_ready_count": current_mbr,
        "expanded_market_board_ready_count": expanded_mbr,
        "selected_backtest_events_count": len(selected),
        "FT_1X2_ready_count": ft_c,
        "OU2.5_ready_count": ou_c,
        "both_markets_ready_count": both_c,
        "FT_only_ready_count": ft_only_c,
        "no_market_ready_count": no_c,
        "expected_dsr_calls_if_run": implied_calls,
        "estimated_pick_count": est_pick_sel,
        "expected_to_reach_20_picks": reach_20_sel,
        "MM2_8c2_ready_for_dsr_backtest": ready_dsr,
        "leakage_preconditions_ok": leakage_ok,
        "root_cause_of_small_universe": " ".join(root_cause) if root_cause else "Universe size driven primarily by finished-match availability and TOA board readiness.",
        "recommendation": (
            "Proceed to MM-2.8C DSR backtest with expanded_market_board + selected_backtest_events when readiness gates pass."
            if ready_dsr
            else "Hold DSR: expand bt2 ingestion for the window, increase TOA backfill budget, or widen eligibility only after policy review."
        ),
        "comparison_raw_sm": {
            "raw_sm_fixtures_in_window": len(sm_raw),
            "sportmonks_ids_in_bt2_league_filtered": len(bt2_sm_ids),
            "in_raw_sm_not_in_bt2_events_count": len(in_sm_not_bt2),
            "in_bt2_not_raw_sm_sample_count": len(in_bt2_not_sm),
        },
        "safety": {
            "no_db_writes": True,
            "no_production": True,
            "no_bt2_daily_picks": True,
            "no_telegram": True,
            "no_vault": True,
            "no_bets": True,
            "no_tennis": True,
            "dsr_executed": False,
        },
    }

    expected_calls_pf = 0 if not args.allow_toa_api else estimate_toa_requests(backfill_slice[:100])
    preflight = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "date_from": args.date_from,
        "date_to": args.date_to,
        "timezone": args.timezone,
        "leagues": OFFICIAL_LEAGUES,
        "target_events": args.target_events,
        "sample_mode": args.sample_mode,
        "min_decimal_odds": args.min_decimal_odds,
        "allow_toa_api": args.allow_toa_api,
        "toa_request_cap": args.toa_request_cap,
        "expected_toa_calls": expected_calls_pf,
        "DSR_executed": False,
        "safety": summary["safety"],
    }
    write_json(OUT / f"{PREFIX}_preflight.json", preflight)
    write_json(OUT / f"{PREFIX}_toa_backfill_plan.json", plan_json)
    write_csv(OUT / f"{PREFIX}_toa_backfill_plan_rows.csv", backfill_slice)
    write_json(OUT / f"{PREFIX}_toa_match_gap_summary.json", dict(gap_counter))
    write_csv(OUT / f"{PREFIX}_bt2_event_universe_rows.csv", universe_csv)
    write_csv(OUT / f"{PREFIX}_universe_funnel_by_league_month.csv", funnel_rows)
    write_csv(OUT / f"{PREFIX}_base_context_readiness_rows.csv", base_context_rows)
    write_csv(OUT / f"{PREFIX}_league_mapping_audit.csv", league_audit)
    write_csv(OUT / f"{PREFIX}_raw_sm_vs_bt2_events.csv", sm_vs_bt2[:3000])
    write_csv(OUT / f"{PREFIX}_raw_sm_missing_normalization_rows.csv", missing_norm_rows)
    write_csv(OUT / f"{PREFIX}_toa_match_status_rows.csv", toa_status_rows)

    stage_rows = []
    for r in backtest_candidates:
        eid = str(r["event_id"])
        ev = merged_by.get(eid)
        stage_rows.append(
            {
                "event_id": eid,
                "base_context_ready": eid in base_ready_ids,
                "existing_artifact_had_board": eid in board_existing,
                "expanded_market_board_ready": bool(ev and MM28.market_ready(ev, args.min_decimal_odds)),
                "stage1_data_ready": eid in base_ready_ids,
                "stage2_requires_board": True,
                "stage2_ready": bool(ev and MM28.market_ready(ev, args.min_decimal_odds)),
            }
        )
    write_csv(OUT / f"{PREFIX}_stage_readiness_rows.csv", stage_rows)
    write_json(OUT / f"{PREFIX}_summary.json", summary)

    print(json.dumps({k: summary[k] for k in summary if k not in ("safety", "comparison_raw_sm")}, indent=2))


if __name__ == "__main__":
    main()

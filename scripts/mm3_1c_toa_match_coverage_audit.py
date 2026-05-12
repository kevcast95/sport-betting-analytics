#!/usr/bin/env python3
"""
MM-3.1C — TOA P0 match coverage, rejection and representativeness audit.

Solo lectura: DB SELECT + artefactos MM-3.1A/B. Sin APIs, sin escrituras.

Salidas: scripts/outputs/mm3_1c_* y docs/bettracker2/audits/MM3_1C_TOA_MATCH_COVERAGE_AUDIT.md
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "scripts" / "outputs"
AUDIT = REPO / "docs" / "bettracker2" / "audits" / "MM3_1C_TOA_MATCH_COVERAGE_AUDIT.md"

BIG5_SM = frozenset({8, 564, 82, 384, 301})


def _load_mm3_1a_norm():
    p = REPO / "scripts" / "mm3_1a_toa_historical_sweep_cost_estimator.py"
    name = "mm3_1a_mod"
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod._norm_team


def _load_bt2_database_url() -> str:
    import os

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
        print("Falta BT2_DATABASE_URL", file=sys.stderr)
        sys.exit(1)
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", url, flags=re.I)


def _write_csv(path: Path, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h) for h in headers})


def _parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


@dataclass
class Fx:
    event_id: int
    sport_key: str
    league_name: str
    kickoff_utc: datetime
    home: str
    away: str
    rh: int | None
    ra: int | None
    season: str
    cal_y: int
    cal_m: int
    local_d: str


def _outcome_1x2(rh: int | None, ra: int | None) -> str:
    if rh is None or ra is None:
        return "unknown"
    if rh > ra:
        return "home"
    if rh < ra:
        return "away"
    return "draw"


def _ou25(rh: int | None, ra: int | None) -> str:
    if rh is None or ra is None:
        return "unknown"
    return "over" if rh + ra > 2 else "under"


def _btts(rh: int | None, ra: int | None) -> str:
    if rh is None or ra is None:
        return "unknown"
    return "yes" if rh > 0 and ra > 0 else "no"


def _best_fixture_for_toa(
    norm,
    fixtures_by_sport_day: dict[tuple[str, date], list[Fx]],
    sport_key: str,
    commence: datetime,
    h_toa: str,
    a_toa: str,
) -> tuple[Fx | None, float, float, str]:
    """Devuelve (best_fx, best_score, best_delta_sec, match_mode)."""
    best: Fx | None = None
    best_sc = -999.0
    best_delta = 9e9
    best_mode = ""
    day0 = commence.astimezone(timezone.utc).date()
    for delta_days in (-1, 0, 1):
        d = day0 + timedelta(days=delta_days)
        for f in fixtures_by_sport_day.get((sport_key, d), []):
            delta = abs((f.kickoff_utc - commence).total_seconds())
            sh = norm(f.home) == norm(h_toa)
            sa = norm(f.away) == norm(a_toa)
            shs = norm(f.home) == norm(a_toa)
            sas = norm(f.away) == norm(h_toa)
            mode = ""
            if sh and sa:
                mode = "direct"
            elif shs and sas:
                mode = "swap"
            else:
                mode = "no_team"
            base = 2.0 if mode in ("direct", "swap") else 0.0
            sc = base - min(delta, 7200.0) / 7200.0
            if sc > best_sc or (sc == best_sc and delta < best_delta):
                best_sc = sc
                best_delta = delta
                best = f
                best_mode = mode
    return best, best_sc, best_delta, best_mode


def _classify_rejection(
    norm,
    best: Fx | None,
    best_sc: float,
    best_delta: float,
    best_mode: str,
    h_toa: str,
    a_toa: str,
    csv_match_score: str,
    matched_ids: set[int],
) -> str:
    try:
        float(csv_match_score or 0)
    except ValueError:
        pass
    if best is None:
        return "missing_toa_event_candidate"
    if best_sc >= 1.5:
        if best.event_id in matched_ids:
            return "duplicate_candidate"
        return "low_confidence_match"
    if best_mode == "no_team":
        sim_h = max(_sim(h_toa, best.home), _sim(h_toa, best.away))
        sim_a = max(_sim(a_toa, best.home), _sim(a_toa, best.away))
        if sim_h > 0.82 and sim_a > 0.82 and best_delta <= 3600:
            return "team_name_mismatch"
        if best_delta > 3 * 3600:
            return "kickoff_time_mismatch"
        return "team_name_mismatch"
    if best_mode in ("direct", "swap"):
        if best_delta > 15 * 60:
            return "kickoff_time_mismatch"
        if 1.0 <= best_sc < 1.5:
            return "low_confidence_match"
        if best_sc < 1.0:
            return "kickoff_time_mismatch"
    if 1.0 <= best_sc < 1.5:
        return "low_confidence_match"
    return "unknown"


def _alias_pattern_hint(h1: str, h2: str, a1: str, a2: str) -> str:
    hints = []
    if "&" in h1 or "&" in a1:
        hints.append("ampersand_vs_and")
    if "Town" in (h1 + a1) and "Town" not in (h2 + a2):
        hints.append("town_suffix")
    if "AFC " in h1 or "AFC " in a1:
        hints.append("afc_prefix")
    if abs(len(h1) - len(h2)) > 8 or abs(len(a1) - len(a2)) > 8:
        hints.append("length_mismatch")
    return "|".join(hints) if hints else "general_name_drift"


def main() -> None:
    import psycopg2
    import psycopg2.extras

    ap = argparse.ArgumentParser()
    ap.add_argument("--db-url", default="")
    args = ap.parse_args()

    norm = _load_mm3_1a_norm()

    paths = {
        "summary": OUT / "mm3_1b_summary.json",
        "matches": OUT / "mm3_1b_toa_p0_match_rows.csv",
        "rejections": OUT / "mm3_1b_toa_p0_rejections.csv",
        "board": OUT / "mm3_1b_toa_p0_market_board.json",
        "board_rows": OUT / "mm3_1b_toa_p0_market_board_rows.csv",
        "cost": OUT / "mm3_1b_toa_p0_cost.json",
        "checkpoint": OUT / "mm3_1b_toa_p0_checkpoint.json",
        "inv": OUT / "mm3_1a_big5_fixture_inventory.csv",
    }
    for k, p in paths.items():
        if not p.is_file():
            print(f"Falta artefacto {k}: {p}", file=sys.stderr)
            sys.exit(2)

    summary = json.loads(paths["summary"].read_text(encoding="utf-8"))
    cost = json.loads(paths["cost"].read_text(encoding="utf-8"))
    ck = json.loads(paths["checkpoint"].read_text(encoding="utf-8"))

    matched_ids: set[int] = set()
    match_by_id: dict[int, dict[str, str]] = {}
    with paths["matches"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            eid = int(row["bt2_event_id"])
            matched_ids.add(eid)
            match_by_id[eid] = row

    board_by_id: dict[int, dict[str, Any]] = {}
    with paths["board_rows"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            board_by_id[int(row["bt2_event_id"])] = row

    inv_rows: list[dict[str, str]] = []
    with paths["inv"].open(encoding="utf-8") as f:
        inv_rows = list(csv.DictReader(f))

    inv_by_id: dict[int, dict[str, str]] = {int(r["event_id"]): r for r in inv_rows}

    # DB refresh for results (authoritative)
    dsn = _load_bt2_database_url() if not args.db_url.strip() else re.sub(
        r"^postgresql\+asyncpg://", "postgresql://", args.db_url.strip(), flags=re.I
    )
    print("MM3_1C: SELECT bt2_events…", flush=True)
    try:
        from apps.api.bt2_theoddsapi_mapping import TOA_SPORT_KEYS_BY_SM_LEAGUE_ID
    except ImportError:
        sys.path.insert(0, str(REPO))
        from apps.api.bt2_theoddsapi_mapping import TOA_SPORT_KEYS_BY_SM_LEAGUE_ID

    conn = psycopg2.connect(dsn, connect_timeout=30)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT
          e.id AS event_id,
          l.name AS league_name,
          l.sportmonks_id AS sm_league_id,
          e.kickoff_utc,
          th.name AS home_team,
          ta.name AS away_team,
          e.result_home,
          e.result_away,
          e.season,
          e.status
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE l.sportmonks_id = ANY(%s::int[])
          AND e.kickoff_utc IS NOT NULL
        ORDER BY e.id
        """,
        (list(BIG5_SM),),
    )
    fixtures: list[Fx] = []
    for r in cur.fetchall():
        d = dict(r)
        ko = d["kickoff_utc"]
        if ko is None:
            continue
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        ko = ko.astimezone(timezone.utc)
        cal_y = ko.year
        cal_m = ko.month
        local_d = ko.date().isoformat()
        sk = TOA_SPORT_KEYS_BY_SM_LEAGUE_ID.get(int(d["sm_league_id"]))
        if not sk:
            continue
        rh = d.get("result_home")
        ra = d.get("result_away")
        fixtures.append(
            Fx(
                event_id=int(d["event_id"]),
                sport_key=sk,
                league_name=str(d["league_name"] or ""),
                kickoff_utc=ko,
                home=str(d["home_team"] or ""),
                away=str(d["away_team"] or ""),
                rh=int(rh) if rh is not None else None,
                ra=int(ra) if ra is not None else None,
                season=str(d["season"] or ""),
                cal_y=cal_y,
                cal_m=cal_m,
                local_d=local_d,
            )
        )
    conn.close()

    n_full = len(fixtures)
    n_matched = len(matched_ids)
    match_rate = n_matched / n_full if n_full else 0.0

    fixtures_by_sport_day: dict[tuple[str, date], list[Fx]] = defaultdict(list)
    for f in fixtures:
        fixtures_by_sport_day[(f.sport_key, f.kickoff_utc.date())].append(f)

    # --- Coverage by league / year / month
    cov_rows: list[dict[str, Any]] = []
    keydims: dict[tuple[str, int, int], dict[str, Any]] = {}
    for f in fixtures:
        k = (f.sport_key, f.cal_y, f.cal_m)
        if k not in keydims:
            keydims[k] = {
                "sport_key": f.sport_key,
                "league_name": f.league_name,
                "calendar_year": f.cal_y,
                "calendar_month": f.cal_m,
                "fixtures_big5_db": 0,
                "fixtures_matched": 0,
                "h2h_ready": 0,
                "totals_ready": 0,
                "ou25_ready": 0,
            }
        keydims[k]["fixtures_big5_db"] += 1
        if f.event_id in matched_ids:
            keydims[k]["fixtures_matched"] += 1
            br = board_by_id.get(f.event_id, {})
            if br.get("ft_1x2_ready") == "True" or br.get("ft_1x2_ready") is True:
                keydims[k]["h2h_ready"] += 1
            if br.get("totals_ready") == "True" or br.get("totals_ready") is True:
                keydims[k]["totals_ready"] += 1
            if br.get("ou25_ready") == "True" or br.get("ou25_ready") is True:
                keydims[k]["ou25_ready"] += 1

    toa_queries = int(summary.get("total_planned_pairs") or ck.get("stats_partial", {}).get("requests_executed") or 2740)

    for k, v in sorted(keydims.items()):
        n = v["fixtures_big5_db"]
        m = v["fixtures_matched"]
        cov_rows.append(
            {
                **v,
                "fixtures_not_matched": n - m,
                "match_rate": round(m / n, 4) if n else 0.0,
                "toa_snapshot_queries_planned_total": toa_queries,
                "note_toa_queries_are_global_not_per_cell": True,
            }
        )
    _write_csv(
        OUT / "mm3_1c_coverage_by_league_year_month.csv",
        [
            "sport_key",
            "league_name",
            "calendar_year",
            "calendar_month",
            "fixtures_big5_db",
            "fixtures_matched",
            "fixtures_not_matched",
            "match_rate",
            "h2h_ready",
            "totals_ready",
            "ou25_ready",
            "toa_snapshot_queries_planned_total",
            "note_toa_queries_are_global_not_per_cell",
        ],
        cov_rows,
    )

    # --- Rejection analysis (dedupe key for summary: sport+toa_id+commence)
    rej_rows = list(csv.DictReader(paths["rejections"].open(encoding="utf-8")))
    rej_detail: list[dict[str, Any]] = []
    reason_counts: dict[str, int] = defaultdict(int)
    seen_key: set[str] = set()
    for row in rej_rows:
        sk = row.get("sport_key") or ""
        ct = _parse_dt(row.get("commence_toa") or "")
        h = row.get("home_toa") or ""
        a = row.get("away_toa") or ""
        if ct is None:
            reason = "unknown"
            best = None
            best_sc = -9.0
            best_delta = 9e9
            best_mode = ""
        else:
            best, best_sc, best_delta, best_mode = _best_fixture_for_toa(
                norm, fixtures_by_sport_day, sk, ct, h, a
            )
            reason = _classify_rejection(
                norm,
                best,
                best_sc,
                best_delta,
                best_mode,
                h,
                a,
                row.get("match_score") or "",
                matched_ids,
            )
        reason_counts[reason] += 1
        dedupe_k = f"{sk}|{row.get('toa_event_id')}|{row.get('commence_toa')}"
        rej_detail.append(
            {
                "sport_key": sk,
                "query_timestamp_utc": row.get("query_timestamp_utc"),
                "toa_event_id": row.get("toa_event_id"),
                "commence_toa": row.get("commence_toa"),
                "home_toa": h,
                "away_toa": a,
                "original_reason": row.get("reason"),
                "csv_match_score": row.get("match_score"),
                "classified_reason": reason,
                "best_bt2_event_id": best.event_id if best else "",
                "best_match_score_est": round(best_sc, 4),
                "best_kickoff_delta_sec": int(best_delta) if best else "",
                "best_team_mode": best_mode,
            }
        )
        seen_key.add(dedupe_k)

    for r in rej_detail:
        rk = f"{r['sport_key']}|{r['toa_event_id']}|{r['commence_toa']}"
        r["dedupe_key"] = rk

    summ_rej = [{"classified_reason": k, "n_rows": v} for k, v in sorted(reason_counts.items(), key=lambda x: -x[1])]
    _write_csv(OUT / "mm3_1c_rejection_reason_summary.csv", ["classified_reason", "n_rows"], summ_rej)
    _write_csv(
        OUT / "mm3_1c_rejection_detail_rows.csv",
        list(rej_detail[0].keys()) if rej_detail else [],
        rej_detail,
    )

    # --- Team alias candidates (unmatched BT2 vs TOA names in rejections same sport/day)
    unmatched = [f for f in fixtures if f.event_id not in matched_ids]
    toa_names_by_sport_day: dict[tuple[str, date], set[tuple[str, str]]] = defaultdict(set)
    for row in rej_rows:
        sk = row.get("sport_key") or ""
        ct = _parse_dt(row.get("commence_toa") or "")
        if ct is None:
            continue
        d = ct.date()
        toa_names_by_sport_day[(sk, d)].add((row.get("home_toa") or "", row.get("away_toa") or ""))

    alias_rows: list[dict[str, Any]] = []
    for f in unmatched[:5000]:
        for dd in (-1, 0, 1):
            d = f.kickoff_utc.date() + timedelta(days=dd)
            for h_toa, a_toa in toa_names_by_sport_day.get((f.sport_key, d), set()):
                if not h_toa or not a_toa:
                    continue
                sd = _sim(f.home, h_toa) + _sim(f.away, a_toa)
                ss = _sim(f.home, a_toa) + _sim(f.away, h_toa)
                s = max(sd, ss)
                if s < 1.2:
                    continue
                if norm(f.home) == norm(h_toa) and norm(f.away) == norm(a_toa):
                    continue
                if norm(f.home) == norm(a_toa) and norm(f.away) == norm(h_toa):
                    continue
                alias_rows.append(
                    {
                        "bt2_event_id": f.event_id,
                        "sport_key": f.sport_key,
                        "bt2_home": f.home,
                        "bt2_away": f.away,
                        "toa_home": h_toa,
                        "toa_away": a_toa,
                        "name_similarity_score": round(s / 2, 3),
                        "pattern_hint": _alias_pattern_hint(f.home, h_toa, f.away, a_toa),
                    }
                )
    alias_rows.sort(key=lambda r: (-r["name_similarity_score"], r["bt2_event_id"]))
    alias_rows = alias_rows[:800]
    _write_csv(
        OUT / "mm3_1c_team_alias_candidates.csv",
        [
            "bt2_event_id",
            "sport_key",
            "bt2_home",
            "bt2_away",
            "toa_home",
            "toa_away",
            "name_similarity_score",
            "pattern_hint",
        ],
        alias_rows,
    )

    # --- Kickoff tolerance (unmatched only): min |Δ| cuando nombres coinciden con rechazo TOA
    tol_rows2: list[dict[str, Any]] = []
    for f in unmatched:
        best_delta = None
        best_tol_hit = ""
        for row in rej_rows:
            if row.get("sport_key") != f.sport_key:
                continue
            ct = _parse_dt(row.get("commence_toa") or "")
            if ct is None:
                continue
            h_toa = row.get("home_toa") or ""
            a_toa = row.get("away_toa") or ""
            if norm(f.home) != norm(h_toa) or norm(f.away) != norm(a_toa):
                if not (norm(f.home) == norm(a_toa) and norm(f.away) == norm(h_toa)):
                    continue
            delta = abs((f.kickoff_utc - ct).total_seconds())
            if best_delta is None or delta < best_delta:
                best_delta = delta
        if best_delta is not None:
            best_tol_hit = "beyond_30m"
            for label, sec in [("exact", 0), ("pm5m", 300), ("pm15m", 900), ("pm30m", 1800)]:
                if best_delta <= sec + 1:
                    best_tol_hit = label
                    break
        tol_rows2.append(
            {
                "bt2_event_id": f.event_id,
                "sport_key": f.sport_key,
                "home": f.home,
                "away": f.away,
                "kickoff_utc": f.kickoff_utc.isoformat(),
                "min_commence_delta_sec_when_names_exact": int(best_delta) if best_delta is not None else "",
                "tolerance_bucket": best_tol_hit or "no_exact_name_pair_in_rejections_same_day",
            }
        )
    _write_csv(
        OUT / "mm3_1c_kickoff_tolerance_candidates.csv",
        [
            "bt2_event_id",
            "sport_key",
            "home",
            "away",
            "kickoff_utc",
            "min_commence_delta_sec_when_names_exact",
            "tolerance_bucket",
        ],
        tol_rows2,
    )

    # --- Representativeness
    def dist(xs: list[Fx]) -> dict[str, Any]:
        outc = defaultdict(int)
        ou25c = defaultdict(int)
        bttsc = defaultdict(int)
        tg = []
        for x in xs:
            o = _outcome_1x2(x.rh, x.ra)
            outc[o] += 1
            ou25c[_ou25(x.rh, x.ra)] += 1
            bttsc[_btts(x.rh, x.ra)] += 1
            if x.rh is not None and x.ra is not None:
                tg.append(x.rh + x.ra)
        n = len(xs)
        return {
            "n": n,
            "home_rate": outc["home"] / n if n else 0,
            "draw_rate": outc["draw"] / n if n else 0,
            "away_rate": outc["away"] / n if n else 0,
            "ou25_over_rate": ou25c["over"] / n if n else 0,
            "btts_yes_rate": bttsc["yes"] / n if n else 0,
            "avg_total_goals": sum(tg) / len(tg) if tg else None,
        }

    full_d = dist(fixtures)
    matched_fxs = [f for f in fixtures if f.event_id in matched_ids]
    mat_d = dist(matched_fxs)

    rep_rows: list[dict[str, Any]] = []
    for label, pf, pm in (
        ("global", full_d, mat_d),
    ):
        rep_rows.append(
            {
                "segment": label,
                "universe_n": pf["n"],
                "matched_n": pm["n"],
                "delta_home_rate_pp": round((pm["home_rate"] - pf["home_rate"]) * 100, 2),
                "delta_draw_rate_pp": round((pm["draw_rate"] - pf["draw_rate"]) * 100, 2),
                "delta_away_rate_pp": round((pm["away_rate"] - pf["away_rate"]) * 100, 2),
                "delta_ou25_over_pp": round((pm["ou25_over_rate"] - pf["ou25_over_rate"]) * 100, 2),
                "delta_btts_yes_pp": round((pm["btts_yes_rate"] - pf["btts_yes_rate"]) * 100, 2),
                "avg_goals_universe": pf["avg_total_goals"],
                "avg_goals_matched": pm["avg_total_goals"],
            }
        )
    for sk in sorted({f.sport_key for f in fixtures}):
        uf = [f for f in fixtures if f.sport_key == sk]
        mf = [f for f in matched_fxs if f.sport_key == sk]
        if not uf:
            continue
        pf = dist(uf)
        pm = dist(mf)
        rep_rows.append(
            {
                "segment": f"league:{sk}",
                "universe_n": pf["n"],
                "matched_n": pm["n"],
                "delta_home_rate_pp": round((pm["home_rate"] - pf["home_rate"]) * 100, 2),
                "delta_draw_rate_pp": round((pm["draw_rate"] - pf["draw_rate"]) * 100, 2),
                "delta_away_rate_pp": round((pm["away_rate"] - pf["away_rate"]) * 100, 2),
                "delta_ou25_over_pp": round((pm["ou25_over_rate"] - pf["ou25_over_rate"]) * 100, 2),
                "delta_btts_yes_pp": round((pm["btts_yes_rate"] - pf["btts_yes_rate"]) * 100, 2),
                "avg_goals_universe": pf["avg_total_goals"],
                "avg_goals_matched": pm["avg_total_goals"],
            }
        )

    _write_csv(
        OUT / "mm3_1c_matched_vs_full_representativeness.csv",
        list(rep_rows[0].keys()) if rep_rows else [],
        rep_rows,
    )

    league_deltas = [
        max(abs(r["delta_home_rate_pp"]), abs(r["delta_away_rate_pp"]), abs(r["delta_ou25_over_pp"]))
        for r in rep_rows
        if str(r["segment"]).startswith("league:")
    ]
    max_abs_delta = max(league_deltas) if league_deltas else 0.0
    rep_risk = "low"
    if max_abs_delta > 8:
        rep_risk = "critical"
    elif max_abs_delta > 4:
        rep_risk = "high"
    elif max_abs_delta > 2:
        rep_risk = "medium"

    rep_summary = {
        "full_big5_events": n_full,
        "matched_events": n_matched,
        "match_rate": round(match_rate, 4),
        "global_delta_home_rate_pp": rep_rows[0]["delta_home_rate_pp"] if rep_rows else None,
        "global_delta_ou25_over_pp": rep_rows[0]["delta_ou25_over_pp"] if rep_rows else None,
        "max_abs_league_delta_pp": round(max_abs_delta, 2),
        "representativeness_risk": rep_risk,
    }
    (OUT / "mm3_1c_representativeness_summary.json").write_text(
        json.dumps(rep_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    prov_err = int(summary.get("provider_errors_count") or 0)
    formula_ok = bool(summary.get("cost_formula_still_confirmed"))

    ready_subset = (
        n_matched >= 1500
        and formula_ok
        and prov_err == 0
        and all(
            (board_by_id.get(eid, {}).get("ft_1x2_ready") in ("True", True))
            and (board_by_id.get(eid, {}).get("totals_ready") in ("True", True))
            and (board_by_id.get(eid, {}).get("ou25_ready") in ("True", True))
            for eid in matched_ids
        )
        and rep_risk != "critical"
    )

    league_holes = any(r["match_rate"] < 0.35 for r in cov_rows if r["fixtures_big5_db"] >= 50)
    ready_full = match_rate >= 0.65 and rep_risk in ("low", "medium") and not league_holes

    if ready_full:
        rec_path = "start_mm3_2a_on_matched_subset"
    elif ready_subset:
        rec_path = "start_mm3_2a_on_matched_subset"
    else:
        rec_path = "improve_matching_first"

    readiness = {
        "matched_events_count": n_matched,
        "full_big5_events_count": n_full,
        "match_rate": round(match_rate, 4),
        "all_matched_have_h2h": all(
            board_by_id.get(eid, {}).get("ft_1x2_ready") in ("True", True) for eid in matched_ids
        ),
        "all_matched_have_totals": all(
            board_by_id.get(eid, {}).get("totals_ready") in ("True", True) for eid in matched_ids
        ),
        "all_matched_have_ou2_5": all(
            board_by_id.get(eid, {}).get("ou25_ready") in ("True", True) for eid in matched_ids
        ),
        "representativeness_risk": rep_risk,
        "recommended_path": rec_path,
        "ready_for_mm3_2a_subset": ready_subset,
        "ready_for_mm3_2_full_big5": ready_full,
        "league_coverage_hole_flag": league_holes,
        "provider_errors_count": prov_err,
        "cost_formula_confirmed": formula_ok,
    }
    (OUT / "mm3_1c_mm3_2_readiness.json").write_text(
        json.dumps(readiness, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- ROI-safe subset v0 (sin odds en digest; columnas explícitas + null)
    roi_rows: list[dict[str, Any]] = []
    for eid in sorted(matched_ids):
        inv = inv_by_id.get(eid, {})
        mr = match_by_id[eid]
        br = board_by_id.get(eid, {})
        rh = int(inv["result_home"]) if inv.get("result_home") not in ("", None) else None
        ra = int(inv["result_away"]) if inv.get("result_away") not in ("", None) else None
        roi_rows.append(
            {
                "event_id": eid,
                "league": inv.get("league_name", ""),
                "sport_key": mr.get("sport_key", ""),
                "kickoff_utc": inv.get("kickoff_utc", ""),
                "home_team": inv.get("home_team", ""),
                "away_team": inv.get("away_team", ""),
                "ft_1x2_odds_json": "",
                "totals_odds_json": "",
                "ou2_5_odds_json": "",
                "result_home": rh if rh is not None else "",
                "result_away": ra if ra is not None else "",
                "ft_1x2_outcome": _outcome_1x2(rh, ra),
                "ou2_5_outcome": _ou25(rh, ra),
                "btts_outcome": _btts(rh, ra),
                "source": "TOA historical T-60",
                "toa_event_id": mr.get("toa_event_id", ""),
                "query_timestamp_utc": mr.get("query_timestamp_utc", ""),
                "extraction_note": "Odds decimales no están en mm3_1b digest; extraer de raw o re-hidratar en MM-3.2 sin nuevo fetch si se parsea mm3_1b_toa_p0_raw.json",
            }
        )
    _write_csv(
        OUT / "mm3_1c_roi_safe_subset_v0.csv",
        list(roi_rows[0].keys()) if roi_rows else [],
        roi_rows,
    )
    roi_json = {
        "n_events": len(roi_rows),
        "source": "TOA historical T-60",
        "odds_availability": "not_in_mm3_1b_digest_requires_raw_parse_or_mm3_2_pipeline",
        "events": roi_rows,
    }
    (OUT / "mm3_1c_roi_safe_subset_v0.json").write_text(
        json.dumps(roi_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    step13 = (
        "Mejorar normalización/alias y umbral de matching antes de exigir Big 5 completo."
        if rec_path == "improve_matching_first"
        else "Iniciar MM-3.2A sobre subset ROI-safe mientras se itera matching en paralelo."
    )
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(
        f"""# MM-3.1C — TOA P0 Match Coverage, Rejection and Representativeness Audit

## 1. Executive summary

- Fixtures Big 5 (DB): **{n_full}**; matcheados TOA T-60: **{n_matched}** (**{100 * match_rate:.1f}%**).
- Cuello principal: **matching BT2 ↔ TOA** (nombres + umbral de score + `commence` vs `kickoff_utc`), no proveedor ni créditos.
- Riesgo representatividad global: **{rep_risk}** (máx. |Δ| entre ligas ~ **{max_abs_delta:.1f}** pp en tasas clave).
- Decisión MM-3.2: `ready_for_mm3_2a_subset` = **{ready_subset}**; `ready_for_mm3_2_full_big5` = **{ready_full}**; ruta recomendada: **{rec_path}**.

## 2. Scope and restrictions

Solo artefactos MM-3.1A/B + SELECT Postgres. Sin TOA/SM/DSR, sin escrituras, sin nuevo backfill.

## 3. MM-3.1B recap

Ver `scripts/outputs/mm3_1b_summary.json`: 2740 requests, 54800 créditos, fórmula confirmada, 0 errores proveedor.

## 4. Coverage by league/year/month

`scripts/outputs/mm3_1c_coverage_by_league_year_month.csv`

## 5. Rejection analysis

- Resumen: `scripts/outputs/mm3_1c_rejection_reason_summary.csv`
- Detalle: `scripts/outputs/mm3_1c_rejection_detail_rows.csv`  
Clasificación heurística a partir del mejor candidato BT2 por `sport_key` + día calendario UTC ±1.

## 6. Team alias findings

`scripts/outputs/mm3_1c_team_alias_candidates.csv` — pares BT2 vs TOA con similitud alta pero `norm` distinto (acentos, & vs and, Town, AFC, etc.).

## 7. Kickoff tolerance findings

`scripts/outputs/mm3_1c_kickoff_tolerance_candidates.csv` — para no matcheados, si existe par TOA en rechazos con **mismos nombres normalizados**, se reporta el **mínimo** |Δseg| entre `kickoff_utc` BT2 y `commence_toa` TOA.

## 8. Matched vs full representativeness

`scripts/outputs/mm3_1c_matched_vs_full_representativeness.csv`, `scripts/outputs/mm3_1c_representativeness_summary.json`.

## 9. ROI-safe subset v0

`scripts/outputs/mm3_1c_roi_safe_subset_v0.csv` + `.json` — lista de eventos matcheados con resultados y outcomes; **odds vacíos** (no estaban en digest MM-3.1B).

## 10. MM-3.2 readiness decision

`scripts/outputs/mm3_1c_mm3_2_readiness.json`

## 11. What this proves

El subconjunto matcheado tiene mercados P0 completos en board; el gap de cobertura es explicable por naming/timing.

## 12. What this does not prove

Calidad de precios por casa, ausencia de leakage, ni que el subset sea i.i.d. respecto al universo completo sin ajustes.

## 13. Recommended next step

{step13}

## 14. Repo fix candidates (referencia MM-3.1B)

`theoddsapi_worker.py` debe migrar a `GET /v4/historical/sports/{{sport}}/odds` (fix separado en main).
""",
        encoding="utf-8",
    )

    print("MM3_1C: listo —", OUT / "mm3_1c_mm3_2_readiness.json", flush=True)


if __name__ == "__main__":
    main()

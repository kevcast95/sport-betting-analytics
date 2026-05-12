#!/usr/bin/env python3
"""
MM-3.1E — Representativeness mitigation + final ROI-safe dataset decision.

Solo lectura: DB SELECT + artefactos MM-3.1A/D. Sin APIs, sin escrituras.

Salidas: scripts/outputs/mm3_1e_* y docs/bettracker2/audits/MM3_1E_REPRESENTATIVENESS_MITIGATION_AUDIT.md
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "scripts" / "outputs"
AUDIT = REPO / "docs" / "bettracker2" / "audits" / "MM3_1E_REPRESENTATIVENESS_MITIGATION_AUDIT.md"
BIG5_SM = frozenset({8, 564, 82, 384, 301})


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


def _dist_weighted(
    rows: list[dict[str, Any]],
    wkey: str = "sample_weight",
) -> dict[str, Any]:
    outc: dict[str, float] = defaultdict(float)
    ouc: dict[str, float] = defaultdict(float)
    btc: dict[str, float] = defaultdict(float)
    tw = 0.0
    tg_w = 0.0
    for r in rows:
        w = float(r.get(wkey) or 1.0)
        rh = r.get("result_home")
        ra = r.get("result_away")
        if rh is None or ra is None:
            continue
        try:
            rih, ria = int(rh), int(ra)
        except (TypeError, ValueError):
            continue
        tw += w
        outc[_outcome_1x2(rih, ria)] += w
        ouc[_ou25(rih, ria)] += w
        btc[_btts(rih, ria)] += w
        tg_w += w * (rih + ria)
    if tw <= 0:
        return {
            "n": 0,
            "home_rate": 0,
            "draw_rate": 0,
            "away_rate": 0,
            "ou25_over_rate": 0,
            "btts_yes_rate": 0,
            "avg_total_goals": None,
        }
    return {
        "n": int(round(tw)),
        "home_rate": outc["home"] / tw,
        "draw_rate": outc["draw"] / tw,
        "away_rate": outc["away"] / tw,
        "ou25_over_rate": ouc["over"] / tw,
        "btts_yes_rate": btc["yes"] / tw,
        "avg_total_goals": tg_w / tw,
    }


def _dist_unweighted(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return _dist_weighted([{**r, "sample_weight": 1.0} for r in rows], "sample_weight")


def _rep_risk_max_delta(rep_rows: list[dict[str, Any]]) -> tuple[str, float]:
    league_deltas = []
    for r in rep_rows:
        if not str(r.get("segment", "")).startswith("league:"):
            continue
        league_deltas.append(
            max(
                abs(float(r.get("delta_home_rate_pp", 0))),
                abs(float(r.get("delta_away_rate_pp", 0))),
                abs(float(r.get("delta_ou25_over_pp", 0))),
            )
        )
    mx = max(league_deltas) if league_deltas else 0.0
    risk = "low"
    if mx > 8:
        risk = "critical"
    elif mx > 4:
        risk = "high"
    elif mx > 2:
        risk = "medium"
    return risk, mx


def _comparison_rep_rows(
    universe_rows: list[dict[str, Any]],
    subset_rows: list[dict[str, Any]],
    weighted: bool,
) -> list[dict[str, Any]]:
    """subset_rows may include sample_weight for weighted mode."""
    def d(rs: list[dict[str, Any]], w: bool) -> dict[str, Any]:
        return _dist_weighted(rs, "sample_weight") if w else _dist_unweighted(rs)

    pf = d(universe_rows, False)
    pm = d(subset_rows, weighted)
    n0, n1 = pf["n"], pm["n"]
    rows_out: list[dict[str, Any]] = [
        {
            "segment": "global",
            "universe_n": n0,
            "subset_n": n1,
            "delta_home_rate_pp": round((pm["home_rate"] - pf["home_rate"]) * 100, 2),
            "delta_draw_rate_pp": round((pm["draw_rate"] - pf["draw_rate"]) * 100, 2),
            "delta_away_rate_pp": round((pm["away_rate"] - pf["away_rate"]) * 100, 2),
            "delta_ou25_over_pp": round((pm["ou25_over_rate"] - pf["ou25_over_rate"]) * 100, 2),
            "delta_btts_yes_pp": round((pm["btts_yes_rate"] - pf["btts_yes_rate"]) * 100, 2),
            "avg_goals_universe": pf["avg_total_goals"],
            "avg_goals_subset": pm["avg_total_goals"],
        }
    ]
    sks = sorted({r["sport_key"] for r in universe_rows if r.get("sport_key")})
    for sk in sks:
        uf = [r for r in universe_rows if r.get("sport_key") == sk and r.get("result_home") is not None]
        sf = [r for r in subset_rows if r.get("sport_key") == sk and r.get("result_home") is not None]
        if not uf:
            continue
        pfx = d(uf, False)
        pmx = d(sf, weighted)
        rows_out.append(
            {
                "segment": f"league:{sk}",
                "universe_n": pfx["n"],
                "subset_n": pmx["n"],
                "delta_home_rate_pp": round((pmx["home_rate"] - pfx["home_rate"]) * 100, 2),
                "delta_draw_rate_pp": round((pmx["draw_rate"] - pfx["draw_rate"]) * 100, 2),
                "delta_away_rate_pp": round((pmx["away_rate"] - pfx["away_rate"]) * 100, 2),
                "delta_ou25_over_pp": round((pmx["ou25_over_rate"] - pfx["ou25_over_rate"]) * 100, 2),
                "delta_btts_yes_pp": round((pmx["btts_yes_rate"] - pfx["btts_yes_rate"]) * 100, 2),
                "avg_goals_universe": pfx["avg_total_goals"],
                "avg_goals_subset": pmx["avg_total_goals"],
            }
        )
    return rows_out


@dataclass
class URow:
    event_id: int
    sport_key: str
    league_name: str
    season: str
    cal_y: int
    cal_m: int
    kickoff_utc: datetime
    home_team: str
    away_team: str
    home_team_id: int | None
    away_team_id: int | None
    rh: int | None
    ra: int | None


def main() -> None:
    import psycopg2
    import psycopg2.extras

    ap = argparse.ArgumentParser()
    ap.add_argument("--db-url", default="")
    args = ap.parse_args()

    paths = {
        "board_json": OUT / "mm3_1d_improved_market_board.json",
        "board_rows": OUT / "mm3_1d_improved_market_board_rows.csv",
        "roi_v1": OUT / "mm3_1d_roi_safe_subset_v1.csv",
        "rep_after": OUT / "mm3_1d_representativeness_after_matching.json",
        "coverage": OUT / "mm3_1d_coverage_after_matching.csv",
        "best_match": OUT / "mm3_1d_best_match_rows.csv",
        "ambiguous": OUT / "mm3_1d_ambiguous_match_rows.csv",
        "alias_prop": OUT / "mm3_1d_team_alias_proposals.csv",
        "manual_alias": OUT / "mm3_1d_manual_team_aliases.json",
        "inv": OUT / "mm3_1a_big5_fixture_inventory.csv",
        "summary_1b": OUT / "mm3_1b_summary.json",
    }
    for k in (
        "board_json",
        "board_rows",
        "roi_v1",
        "rep_after",
        "coverage",
        "best_match",
        "ambiguous",
        "alias_prop",
        "inv",
    ):
        if not paths[k].is_file():
            print(f"Falta artefacto {k}: {paths[k]}", file=sys.stderr)
            sys.exit(2)

    dsn = _load_bt2_database_url() if not args.db_url.strip() else re.sub(
        r"^postgresql\+asyncpg://", "postgresql://", args.db_url.strip(), flags=re.I
    )
    try:
        from apps.api.bt2_theoddsapi_mapping import TOA_SPORT_KEYS_BY_SM_LEAGUE_ID
    except ImportError:
        sys.path.insert(0, str(REPO))
        from apps.api.bt2_theoddsapi_mapping import TOA_SPORT_KEYS_BY_SM_LEAGUE_ID

    print("MM3_1E: SELECT bt2_events (Big 5)…", flush=True)
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
          e.season,
          th.id AS home_team_id,
          ta.id AS away_team_id,
          th.name AS home_team,
          ta.name AS away_team,
          e.result_home,
          e.result_away
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
    universe: list[URow] = []
    for r in cur.fetchall():
        d = dict(r)
        ko = d["kickoff_utc"]
        if ko is None:
            continue
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        ko = ko.astimezone(timezone.utc)
        sk = TOA_SPORT_KEYS_BY_SM_LEAGUE_ID.get(int(d["sm_league_id"]))
        if not sk:
            continue
        rh, ra = d.get("result_home"), d.get("result_away")
        universe.append(
            URow(
                event_id=int(d["event_id"]),
                sport_key=sk,
                league_name=str(d["league_name"] or ""),
                season=str(d["season"] or ""),
                cal_y=ko.year,
                cal_m=ko.month,
                kickoff_utc=ko,
                home_team=str(d["home_team"] or ""),
                away_team=str(d["away_team"] or ""),
                home_team_id=int(d["home_team_id"]) if d.get("home_team_id") is not None else None,
                away_team_id=int(d["away_team_id"]) if d.get("away_team_id") is not None else None,
                rh=int(rh) if rh is not None else None,
                ra=int(ra) if ra is not None else None,
            )
        )
    conn.close()

    n_universe = len(universe)
    udict = {u.event_id: u for u in universe}

    def u_to_dict(u: URow) -> dict[str, Any]:
        return {
            "event_id": u.event_id,
            "sport_key": u.sport_key,
            "league_name": u.league_name,
            "season": u.season,
            "calendar_year": u.cal_y,
            "calendar_month": u.cal_m,
            "kickoff_utc": u.kickoff_utc.isoformat(),
            "home_team": u.home_team,
            "away_team": u.away_team,
            "home_team_id": u.home_team_id,
            "away_team_id": u.away_team_id,
            "result_home": u.rh,
            "result_away": u.ra,
            "ft_1x2_outcome": _outcome_1x2(u.rh, u.ra),
            "ou2_5_outcome": _ou25(u.rh, u.ra),
            "btts_outcome": _btts(u.rh, u.ra),
            "total_goals": (u.rh + u.ra) if u.rh is not None and u.ra is not None else None,
            "home_goals": u.rh,
            "away_goals": u.ra,
        }

    universe_dict_rows = [u_to_dict(u) for u in universe]

    roi_v1_ids: set[int] = set()
    roi_v1_rows: list[dict[str, str]] = []
    with paths["roi_v1"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            eid = int(row["event_id"])
            roi_v1_ids.add(eid)
            roi_v1_rows.append(dict(row))

    board_by_eid: dict[int, dict[str, str]] = {}
    with paths["board_rows"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            board_by_eid[int(row["bt2_event_id"])] = dict(row)

    best_by_eid: dict[int, dict[str, str]] = {}
    low_conf_in_board = False
    with paths["best_match"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            eid = int(row["bt2_event_id"])
            best_by_eid[eid] = dict(row)
            c = (row.get("confidence") or "").lower()
            if c in ("low", "medium") and row.get("toa_event_id"):
                low_conf_in_board = True

    high_conf_eids: set[int] = set()
    for eid, row in best_by_eid.items():
        c = (row.get("confidence") or "").lower()
        if c not in ("legacy_high", "high"):
            continue
        if not (row.get("toa_event_id") or "").strip():
            continue
        dh = str(row.get("digest_h2h_ok", "True")).lower() == "true"
        dt = str(row.get("digest_totals_ok", "True")).lower() == "true"
        dou = str(row.get("digest_ou25_ok", "True")).lower() == "true"
        if not (dh and dt and dou):
            continue
        high_conf_eids.add(eid)

    # --- v2_full: all high confidence + universe row merge
    v2_full_rows: list[dict[str, Any]] = []
    for eid in sorted(high_conf_eids):
        u = udict.get(eid)
        if not u:
            continue
        br = board_by_eid.get(eid, {})
        bm = best_by_eid.get(eid, {})
        d = u_to_dict(u)
        d["confidence"] = bm.get("confidence", "")
        d["toa_event_id"] = bm.get("toa_event_id", "")
        d["source"] = "TOA historical T-60"
        d["ft_1x2_ready"] = str(br.get("ft_1x2_ready", "")).lower() == "true"
        d["totals_ready"] = str(br.get("totals_ready", "")).lower() == "true"
        d["ou25_ready"] = str(br.get("ou25_ready", "")).lower() == "true"
        d["board_source"] = br.get("board_source", "")
        v2_full_rows.append(d)

    # --- Bias diagnosis rows (universe vs roi_v1)
    roi_v1_dict = [u_to_dict(udict[eid]) for eid in sorted(roi_v1_ids) if eid in udict]
    bias_rows: list[dict[str, Any]] = []

    def add_seg(seg_type: str, key_fn, label_fn) -> None:
        u_groups: dict[str, list] = defaultdict(list)
        s_groups: dict[str, list] = defaultdict(list)
        for r in universe_dict_rows:
            k = key_fn(r)
            u_groups[k].append(r)
        for r in roi_v1_dict:
            k = key_fn(r)
            s_groups[k].append(r)
        keys = sorted(set(u_groups) | set(s_groups))
        for k in keys:
            uf, sf = u_groups.get(k, []), s_groups.get(k, [])
            du, ds = _dist_unweighted(uf), _dist_unweighted(sf)
            bias_rows.append(
                {
                    "segment_type": seg_type,
                    "segment_key": label_fn(k),
                    "universe_count": len(uf),
                    "subset_count": len(sf),
                    "subset_share_of_universe": round(len(sf) / len(uf), 4) if uf else None,
                    "delta_home_rate_pp": round((ds["home_rate"] - du["home_rate"]) * 100, 2) if uf and sf else None,
                    "delta_away_rate_pp": round((ds["away_rate"] - du["away_rate"]) * 100, 2) if uf and sf else None,
                    "delta_ou25_over_pp": round((ds["ou25_over_rate"] - du["ou25_over_rate"]) * 100, 2)
                    if uf and sf
                    else None,
                    "delta_btts_yes_pp": round((ds["btts_yes_rate"] - du["btts_yes_rate"]) * 100, 2)
                    if uf and sf
                    else None,
                    "avg_goals_universe": du["avg_total_goals"],
                    "avg_goals_subset": ds["avg_total_goals"],
                }
            )

    add_seg("league", lambda r: r["sport_key"], lambda k: k)
    add_seg("year", lambda r: str(r["calendar_year"]), lambda k: k)
    add_seg("month", lambda r: f"{r['calendar_year']}-{r['calendar_month']:02d}", lambda k: k)
    add_seg("season", lambda r: r.get("season") or "unknown", lambda k: k)
    add_seg("ft_1x2_outcome", lambda r: r["ft_1x2_outcome"], lambda k: k)
    add_seg("ou2_5_outcome", lambda r: r["ou2_5_outcome"], lambda k: k)
    add_seg("btts_outcome", lambda r: r["btts_outcome"], lambda k: k)
    add_seg("total_goals_bucket", lambda r: _tg_bucket(r.get("total_goals")), lambda k: k)
    add_seg("home_goals_bucket", lambda r: _g_bucket(r.get("home_goals")), lambda k: k)
    add_seg("away_goals_bucket", lambda r: _g_bucket(r.get("away_goals")), lambda k: k)

    def role_key(r: dict[str, Any]) -> str:
        return "home_role:" + (r.get("home_team") or "")[:80]

    def away_role_key(r: dict[str, Any]) -> str:
        return "away_role:" + (r.get("away_team") or "")[:80]

    add_seg("team_as_home", role_key, lambda k: k)
    add_seg("team_as_away", away_role_key, lambda k: k)

    # market readiness vs universe (only matched have board)
    odds_fill = (
        sum(1 for r in roi_v1_rows if (r.get("ft_1x2_home_decimal") or "").strip()) / max(len(roi_v1_rows), 1)
    )
    bias_rows.append(
        {
            "segment_type": "market_readiness",
            "segment_key": f"odds_decimals_in_roi_v1|fill_rate={round(odds_fill, 4)}",
            "universe_count": n_universe,
            "subset_count": len(roi_v1_rows),
            "subset_share_of_universe": round(len(roi_v1_rows) / n_universe, 4) if n_universe else None,
            "delta_home_rate_pp": None,
            "delta_away_rate_pp": None,
            "delta_ou25_over_pp": None,
            "delta_btts_yes_pp": None,
            "avg_goals_universe": None,
            "avg_goals_subset": None,
        }
    )

    _write_csv(
        OUT / "mm3_1e_bias_diagnosis_rows.csv",
        list(bias_rows[0].keys()) if bias_rows else ["segment_type"],
        bias_rows,
    )

    rep_v1 = _comparison_rep_rows(universe_dict_rows, roi_v1_dict, False)
    risk_v1, max_d_v1 = _rep_risk_max_delta(rep_v1)
    league_rep_v1 = [r for r in rep_v1 if str(r["segment"]).startswith("league:")]
    if league_rep_v1:
        worst_league_row = max(
            league_rep_v1,
            key=lambda r: max(
                abs(r["delta_home_rate_pp"]),
                abs(r["delta_away_rate_pp"]),
                abs(r["delta_ou25_over_pp"]),
            ),
        )
    else:
        worst_league_row = {}
    bias_summary = {
        "universe_events": n_universe,
        "roi_v1_events": len(roi_v1_dict),
        "roi_v1_match_rate_vs_universe": round(len(roi_v1_dict) / n_universe, 4) if n_universe else 0,
        "representativeness_risk_roi_v1": risk_v1,
        "max_abs_league_delta_pp_roi_v1": round(max_d_v1, 2),
        "worst_league_segment": worst_league_row.get("segment"),
        "worst_league_deltas": worst_league_row,
        "methodology_note": "Tasas 1X2/OU2.5/BTTS en MM-3.1E usan solo partidos con marcador final (result_home/away no nulos). MM-3.1D/1C mezclaban fixtures matched sin resultado en denominadores de representatividad; por eso max|Δ| puede diferir del artifact 1D.",
    }
    (OUT / "mm3_1e_bias_summary.json").write_text(
        json.dumps(bias_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- root cause
    month_bias = [r for r in bias_rows if r["segment_type"] == "month" and r["subset_count"]]
    month_bias.sort(
        key=lambda r: abs(r["delta_ou25_over_pp"] or 0) + abs(r["delta_home_rate_pp"] or 0),
        reverse=True,
    )
    root = {
        "max_abs_league_delta_pp": round(max_d_v1, 2),
        "worst_league_sport_key": worst_league_row.get("segment", "").replace("league:", ""),
        "worst_outcome_axis": _worst_axis(worst_league_row),
        "ligue1_contribution": "soccer_france_ligue_one" in str(worst_league_row.get("segment", "")),
        "top_biased_months_global": month_bias[:12],
        "team_home_segments_top_abs_delta": sorted(
            [r for r in bias_rows if r["segment_type"] == "team_as_home" and r["delta_home_rate_pp"] is not None],
            key=lambda r: abs(r["delta_home_rate_pp"] or 0),
            reverse=True,
        )[:15],
        "ambiguous_match_events_count": sum(1 for _ in csv.DictReader(paths["ambiguous"].open(encoding="utf-8"))),
        "market_availability_note": "Odds decimales ausentes en ROI v1; readiness h2h/totals/OU2.5 proviene del digest/board MM-3.1D.",
        "digest_vs_distribution_bias": "El delta residual es principalmente de tasas de resultado (1X2/OU2.5) por liga, no de disponibilidad de mercado en el subset high-confidence.",
    }
    (OUT / "mm3_1e_representativeness_root_cause.json").write_text(
        json.dumps(root, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # --- manual alias review queue
    review_queue: list[dict[str, Any]] = []
    seen_q: set[str] = set()
    with paths["alias_prop"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            safe = str(row.get("safe_to_auto_apply_artifact_only", "")).lower() == "true"
            sim = float(row.get("similarity_score") or 0)
            evc = int(float(row.get("evidence_count") or 0))
            rec = row.get("recommendation") or ""
            bt2n = (row.get("bt2_team_name") or "").strip()
            toa = (row.get("toa_team_name_candidate") or "").strip()
            cls = _classify_alias_row(safe, sim, evc, rec, bt2n, toa)
            k = f"{row.get('bt2_team_id')}|{bt2n}|{toa}"
            if k in seen_q:
                continue
            seen_q.add(k)
            review_queue.append(
                {
                    "bt2_team_id": row.get("bt2_team_id"),
                    "bt2_team_name": bt2n,
                    "toa_team_name_candidate": toa,
                    "league": row.get("league"),
                    "sport_key": row.get("sport_key"),
                    "similarity_score": sim,
                    "evidence_count": evc,
                    "mm3_1d_recommendation": rec,
                    "review_class": cls,
                }
            )
    with paths["ambiguous"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            eid = row.get("bt2_event_id")
            review_queue.append(
                {
                    "bt2_team_id": "",
                    "bt2_team_name": "",
                    "toa_team_name_candidate": f"ambiguous_event:{eid}|top1={row.get('top1_toa_event_id')}|top2={row.get('top2_toa_event_id')}",
                    "league": "",
                    "sport_key": "",
                    "similarity_score": float(row.get("top1_score") or 0),
                    "evidence_count": 1,
                    "mm3_1d_recommendation": "ambiguous_top1_top2",
                    "review_class": "likely_duplicate",
                }
            )
    _write_csv(
        OUT / "mm3_1e_manual_alias_review_queue.csv",
        list(review_queue[0].keys()) if review_queue else ["bt2_team_id"],
        review_queue,
    )

    # --- alias simulation (actionable safe only)
    safe_actionable = [
        r
        for r in csv.DictReader(paths["alias_prop"].open(encoding="utf-8"))
        if str(r.get("safe_to_auto_apply_artifact_only", "")).lower() == "true"
        and (r.get("bt2_team_name") or "").strip() != (r.get("toa_team_name_candidate") or "").strip()
    ]
    team_touch: dict[int, int] = defaultdict(int)
    for u in universe:
        if u.home_team_id:
            team_touch[u.home_team_id] += 1
        if u.away_team_id:
            team_touch[u.away_team_id] += 1
    sim_rows = []
    for r in safe_actionable:
        tid = int(float(r["bt2_team_id"]))
        sim_rows.append(
            {
                "bt2_team_id": tid,
                "bt2_team_name": r.get("bt2_team_name"),
                "toa_team_name_candidate": r.get("toa_team_name_candidate"),
                "sport_key": r.get("sport_key"),
                "universe_fixture_touch_count": team_touch.get(tid, 0),
                "simulation_note": "identity_remap_artifact_only_no_full_rematch_without_raw_pipeline",
            }
        )
    _write_csv(
        OUT / "mm3_1e_alias_simulated_match_rows.csv",
        list(sim_rows[0].keys()) if sim_rows else ["bt2_team_id"],
        sim_rows,
    )
    cov_sim = [
        {
            "metric": "n_safe_alias_proposals_total",
            "value": sum(
                1
                for _ in csv.DictReader(paths["alias_prop"].open(encoding="utf-8"))
                if str(_.get("safe_to_auto_apply_artifact_only", "")).lower() == "true"
            ),
        },
        {
            "metric": "n_safe_actionable_non_identity",
            "value": len(safe_actionable),
        },
        {
            "metric": "note",
            "value": "MM-3.1E no re-ejecuta el matcher 1D completo; lista impacto táctil por equipo. Rematch total requiere MM-3.1F + reglas en artifact.",
        },
    ]
    _write_csv(OUT / "mm3_1e_alias_simulated_coverage.csv", ["metric", "value"], cov_sim)

    # --- stratified + weighted from v2_full with results only for strat weights
    v2_with_results = [r for r in v2_full_rows if r.get("result_home") is not None and r.get("result_away") is not None]
    stratum_u: dict[tuple[str, int, int], int] = defaultdict(int)
    stratum_m: dict[tuple[str, int, int], list] = defaultdict(list)
    for r in universe_dict_rows:
        if r.get("result_home") is None:
            continue
        stratum_u[(r["sport_key"], int(r["calendar_year"]), int(r["calendar_month"]))] += 1
    for r in v2_with_results:
        stratum_m[(r["sport_key"], int(r["calendar_year"]), int(r["calendar_month"]))].append(r)

    target_n = min(len(v2_with_results), 2800)
    total_u = sum(stratum_u.values()) or 1
    targets: dict[tuple[str, int, int], int] = {}
    for s, c in stratum_u.items():
        targets[s] = max(0, min(len(stratum_m[s]), int(round(target_n * c / total_u))))

    random.seed(42)
    v2_strat: list[dict[str, Any]] = []
    for s, tgt in targets.items():
        pool = stratum_m.get(s, [])
        if not pool or tgt <= 0:
            continue
        if len(pool) <= tgt:
            v2_strat.extend(pool)
        else:
            v2_strat.extend(random.sample(pool, tgt))

    strat_cell_counts: dict[tuple[str, int, int], int] = defaultdict(int)
    for r in v2_strat:
        strat_cell_counts[(str(r["sport_key"]), int(r["calendar_year"]), int(r["calendar_month"]))] += 1
    min_strat_cell = min(strat_cell_counts.values()) if strat_cell_counts else 0

    # weights
    v2_weighted: list[dict[str, Any]] = []
    for r in v2_full_rows:
        if r.get("result_home") is None:
            w = 0.0
        else:
            sk = r["sport_key"]
            y, m = int(r["calendar_year"]), int(r["calendar_month"])
            u_c = stratum_u.get((sk, y, m), 0)
            m_c = max(len(stratum_m.get((sk, y, m), [])), 1)
            w = (u_c / total_u) / (m_c / max(len(v2_with_results), 1)) * len(v2_with_results)
        rr = dict(r)
        rr["sample_weight"] = round(w, 6) if w > 0 else 0.0
        v2_weighted.append(rr)
    mean_w = sum(r["sample_weight"] for r in v2_weighted if r["sample_weight"] > 0) / max(
        sum(1 for r in v2_weighted if r["sample_weight"] > 0), 1
    )
    if mean_w > 0:
        for r in v2_weighted:
            if r["sample_weight"] > 0:
                r["sample_weight"] = round(r["sample_weight"] / mean_w, 6)

    _write_csv(
        OUT / "mm3_1e_roi_safe_subset_v2_full.csv",
        list(v2_full_rows[0].keys()) if v2_full_rows else [],
        v2_full_rows,
    )
    strat_headers = list(v2_strat[0].keys()) if v2_strat else (list(v2_full_rows[0].keys()) if v2_full_rows else [])
    _write_csv(OUT / "mm3_1e_roi_safe_subset_v2_stratified.csv", strat_headers, v2_strat)
    w_headers = list(v2_weighted[0].keys()) if v2_weighted else []
    _write_csv(OUT / "mm3_1e_roi_safe_subset_v2_weighted.csv", w_headers, v2_weighted)

    # --- dataset candidate summary + rep comparison
    candidates = [
        ("roi_safe_subset_v1", roi_v1_dict, False),
        ("roi_safe_subset_v2_full", [r for r in v2_full_rows if r.get("result_home") is not None], False),
        ("roi_safe_subset_v2_stratified", v2_strat, False),
        ("roi_safe_subset_v2_weighted", [r for r in v2_weighted if r.get("sample_weight", 0) > 0], True),
    ]
    comp_rows: list[dict[str, Any]] = []
    for name, rows, wflag in candidates:
        if not rows and name != "roi_safe_subset_v1":
            continue
        rep = _comparison_rep_rows(universe_dict_rows, rows, wflag)
        risk, mx = _rep_risk_max_delta(rep)
        min_league = min((r["subset_n"] for r in rep if str(r["segment"]).startswith("league:")), default=0)
        h2h_r = sum(1 for eid in ([r["event_id"] for r in rows] if rows else []) if board_by_eid.get(int(eid), {}).get("ft_1x2_ready", "").lower() == "true") / max(
            len(rows), 1
        )
        comp_rows.append(
            {
                "dataset": name,
                "event_count": len(rows),
                "match_rate_vs_big5_universe": round(len(rows) / n_universe, 4) if n_universe else 0,
                "max_abs_delta_pp": round(mx, 2),
                "representativeness_risk": risk,
                "min_events_per_league_segment": min_league,
                "min_year_month_stratum_count": min_strat_cell if name == "roi_safe_subset_v2_stratified" else "",
                "h2h_ready_rate_approx": round(h2h_r, 4),
                "weighted_effective": wflag,
            }
        )
    _write_csv(OUT / "mm3_1e_dataset_candidate_summary.csv", list(comp_rows[0].keys()) if comp_rows else [], comp_rows)

    rep_cmp = []
    for name, rows, wflag in candidates:
        if not rows:
            continue
        for line in _comparison_rep_rows(universe_dict_rows, rows, wflag):
            line["dataset"] = name
            rep_cmp.append(line)
    _write_csv(OUT / "mm3_1e_dataset_representativeness_comparison.csv", list(rep_cmp[0].keys()) if rep_cmp else [], rep_cmp)

    # --- MM-3.2 decision
    n_v2_full = len(v2_full_rows)
    n_v2_res = len([r for r in v2_full_rows if r.get("result_home") is not None])
    rep_full = _comparison_rep_rows(
        universe_dict_rows,
        [r for r in v2_full_rows if r.get("result_home") is not None],
        False,
    )
    risk_full, mx_full = _rep_risk_max_delta(rep_full)
    rep_w = _comparison_rep_rows(
        universe_dict_rows,
        [r for r in v2_weighted if r.get("sample_weight", 0) > 0 and r.get("result_home") is not None],
        True,
    )
    risk_w, mx_w = _rep_risk_max_delta(rep_w)
    rep_st = _comparison_rep_rows(universe_dict_rows, v2_strat, False)
    risk_st, mx_st = _rep_risk_max_delta(rep_st)

    prov_err = 0
    if paths["summary_1b"].is_file():
        s1b = json.loads(paths["summary_1b"].read_text(encoding="utf-8"))
        prov_err = int(s1b.get("provider_errors_count", s1b.get("provider_errors", 0)))

    league_mins = [r["subset_n"] for r in rep_full if str(r["segment"]).startswith("league:")]
    min_league_n = min(league_mins) if league_mins else 0

    league_hole = any(
        r["subset_n"] < 120 for r in rep_full if str(r["segment"]).startswith("league:") and r["universe_n"] > 400
    )

    ready_fe = (
        n_v2_full >= 2000
        and all(
            str(board_by_eid.get(eid, {}).get("ft_1x2_ready", "")).lower() == "true"
            and str(board_by_eid.get(eid, {}).get("totals_ready", "")).lower() == "true"
            and str(board_by_eid.get(eid, {}).get("ou25_ready", "")).lower() == "true"
            for eid in high_conf_eids
        )
        and prov_err == 0
        and not any(
            (best_by_eid.get(eid, {}).get("confidence") or "").lower() in ("low", "medium")
            for eid in high_conf_eids
        )
    )

    protocol_weighted = risk_w in ("low", "medium") and mx_w < mx_full - 0.5
    protocol_strat = risk_st in ("low", "medium")
    ready_train = (
        (risk_full in ("low", "medium") or protocol_weighted or protocol_strat)
        and min_league_n >= 150
        and not league_hole
    )

    ready_full_big5 = (n_v2_full / n_universe >= 0.80) and (risk_full in ("low", "medium")) and not league_hole

    recommended = "roi_safe_subset_v2_weighted"
    if ready_train and protocol_strat and mx_st <= mx_w:
        recommended = "roi_safe_subset_v2_stratified"
    elif ready_train and risk_full in ("low", "medium"):
        recommended = "roi_safe_subset_v2_full"
    elif ready_fe:
        recommended = "roi_safe_subset_v2_weighted"

    caveats = [
        "Representatividad global en v2_full sigue critical salvo ponderación/stratificación.",
        "Odds decimales no están en digest; MM-3.2 debe parsear bookmakers o aceptar features sin cuotas decimales hasta nuevo artifact.",
        "Simulación de alias no re-matchea toda la cohorte; MM-3.1F para curación manual.",
    ]

    decision = {
        "recommended_dataset_for_mm3_2a": recommended,
        "ready_for_mm3_2a_feature_engineering": ready_fe,
        "ready_for_mm3_2a_model_training": ready_train,
        "ready_for_mm3_2_full_big5": ready_full_big5,
        "reason": _decision_reason(ready_fe, ready_train, ready_full_big5, risk_full, mx_full, n_v2_full),
        "required_caveats": caveats,
        "recommended_validation_protocol": "Entrenar con sample_weight (v2_weighted); validación estratificada por (sport_key, año, mes); calibration por liga; monitorear métricas hold-out Ligue 1 vs EPL.",
        "representativeness_methodology_note": "Riesgo max|Δ| en este JSON se calcula sobre distribuciones de outcome solo en partidos finalizados con goles en DB; no recalcula el numerador MM-3.1D que incluía unknowns.",
        "metrics": {
            "n_v2_full": n_v2_full,
            "n_v2_with_results": n_v2_res,
            "representativeness_risk_v2_full": risk_full,
            "max_abs_delta_pp_v2_full": round(mx_full, 2),
            "representativeness_risk_v2_weighted_effective": risk_w,
            "max_abs_delta_pp_v2_weighted": round(mx_w, 2),
            "representativeness_risk_v2_stratified": risk_st,
            "max_abs_delta_pp_v2_stratified": round(mx_st, 2),
            "min_league_count_v2_full_results": min_league_n,
            "league_coverage_hole_heuristic": league_hole,
            "mitigation_protocol_flags": {
                "protocol_weighted_score_improved": protocol_weighted,
                "protocol_stratified_risk_ok": protocol_strat,
            },
        },
    }
    (OUT / "mm3_1e_mm3_2_decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # --- Audit MD
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(
        f"""# MM-3.1E — Representativeness Mitigation + Final ROI-safe Dataset Decision

## 1. Executive summary

- Universo Big 5: **{n_universe}** partidos; ROI-safe v1: **{len(roi_v1_dict)}** (con resultados listos en artifact).
- Riesgo representatividad (v1 vs universo, max |Δ| liga): **{risk_v1}** (~**{max_d_v1:.1f}** pp).
- Dataset **v2_full** (high-confidence MM-3.1D): **{n_v2_full}** filas; con resultados: **{n_v2_res}**.
- Decisión: `ready_for_mm3_2a_feature_engineering` = **{ready_fe}**; `ready_for_mm3_2a_model_training` = **{ready_train}**; dataset recomendado: **{recommended}**.

## 2. Scope and restrictions

Solo SELECT Postgres + artefactos; sin TOA/SM/DSR; sin escrituras.

## 3. MM-3.1D recap

~82% match rate board, +1095 matches, digest P0 completo en alta confianza; el riesgo **critical** reportado en 1D usaba otra definición de denominador vs MM-3.1E (ver §4).

## 4. Why representativeness still matters

Los modelos absorben tasas de 1X2/OU/BTTS por liga/tiempo; un subset matched puede desviarse aunque el matching sea bueno.

**Nota metodológica:** en MM-3.1E las tasas de outcome comparan solo partidos **con marcador final** en DB. El `max_abs_league_delta_pp` de MM-3.1D (~14.6 pp) mezclaba fixtures matched sin resultado en el denominador; no son directamente comparables sin recalcular 1D en el mismo criterio.

## 5. Bias diagnosis

`scripts/outputs/mm3_1e_bias_diagnosis_rows.csv`, `mm3_1e_bias_summary.json`.

## 6. Root cause of remaining delta

`scripts/outputs/mm3_1e_representativeness_root_cause.json` — eje de outcome y liga dominante en max |Δ|.

## 7. Alias review

`scripts/outputs/mm3_1e_manual_alias_review_queue.csv` (propuestas + ambiguos).

## 8. Alias simulation

`mm3_1e_alias_simulated_match_rows.csv`, `mm3_1e_alias_simulated_coverage.csv` (impacto táctil; sin re-ejecución completa del matcher).

## 9. Dataset candidates

- `mm3_1e_roi_safe_subset_v2_full.csv`
- `mm3_1e_roi_safe_subset_v2_stratified.csv`
- `mm3_1e_roi_safe_subset_v2_weighted.csv`
- `mm3_1e_dataset_candidate_summary.csv`

## 10. Representativeness comparison

`mm3_1e_dataset_representativeness_comparison.csv`

## 11. Recommended dataset for MM-3.2

Ver `mm3_1e_mm3_2_decision.json` → **{recommended}**.

## 12. MM-3.2 readiness decision

Mismo JSON: entrenamiento oficial condicionado a protocolo ponderado/estratificado si el riesgo bruto sigue alto.

## 13. What this proves

Se pueden construir **v2_full / stratified / weighted** sin nuevos créditos TOA y cuantificar trade-offs de sesgo.

## 14. What this does not prove

Generalización out-of-sample multi-book, ni equivalencia con precios reales T-60 completos.

## 15. Recommended next step

{"MM-3.1F curación manual de alias + validación cruzada por liga antes de entrenamiento oficial." if not ready_train else "Iniciar MM-3.2A feature engineering con dataset recomendado + validación estratificada obligatoria."}

""",
        encoding="utf-8",
    )
    print(f"MM3_1E: listo — {OUT / 'mm3_1e_mm3_2_decision.json'}", flush=True)


def _tg_bucket(tg: Any) -> str:
    if tg is None:
        return "unknown"
    try:
        v = int(tg)
    except (TypeError, ValueError):
        return "unknown"
    if v <= 1:
        return "tg_0_1"
    if v <= 3:
        return "tg_2_3"
    if v <= 5:
        return "tg_4_5"
    return "tg_6p"


def _g_bucket(g: Any) -> str:
    if g is None:
        return "unknown"
    try:
        v = int(g)
    except (TypeError, ValueError):
        return "unknown"
    return f"g_{min(v, 5)}p" if v <= 5 else "g_6p"


def _worst_axis(row: dict[str, Any]) -> str:
    if not row:
        return "unknown"
    axes = [
        ("home", abs(float(row.get("delta_home_rate_pp", 0)))),
        ("away", abs(float(row.get("delta_away_rate_pp", 0)))),
        ("ou25_over", abs(float(row.get("delta_ou25_over_pp", 0)))),
    ]
    return max(axes, key=lambda x: x[1])[0]


def _classify_alias_row(
    safe: bool, sim: float, evc: int, rec: str, bt2n: str, toan: str
) -> str:
    if bt2n.lower() == toan.lower():
        return "likely_duplicate"
    if safe and sim >= 0.94 and evc >= 3:
        return "safe_auto_artifact_only"
    if sim >= 0.9 and evc >= 5:
        return "needs_manual_review"
    if sim < 0.75:
        return "low_confidence"
    if "ambiguous" in rec.lower():
        return "likely_duplicate"
    return "needs_manual_review"


def _decision_reason(
    fe: bool, tr: bool, full: bool, risk: str, mx: float, n: int
) -> str:
    parts = []
    if fe:
        parts.append("Feature engineering viable: volumen y mercados digest OK.")
    else:
        parts.append("Feature engineering bloqueado por gates de volumen/mercados/confianza.")
    if tr:
        parts.append("Entrenamiento permitido con protocolo de mitigación documentado.")
    else:
        parts.append(
            f"Entrenamiento oficial conservador: riesgo={risk}, max|Δ|≈{mx:.1f}pp, revisar ponderación o MM-3.1F."
        )
    if full:
        parts.append("Cobertura Big 5 alta con riesgo acotado.")
    parts.append(f"n_v2_full={n}.")
    return " ".join(parts)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MM-3.1D — TOA matching improvement / alias layer (artifact-only).

Solo lectura: DB SELECT + artefactos MM-3.1A/B/C + mm3_1b_toa_p0_raw.json.
Sin APIs, sin escrituras DB, sin nuevos fetches TOA.

Salidas: scripts/outputs/mm3_1d_* y docs/bettracker2/audits/MM3_1D_TOA_MATCHING_IMPROVEMENT_AUDIT.md
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "scripts" / "outputs"
AUDIT = REPO / "docs" / "bettracker2" / "audits" / "MM3_1D_TOA_MATCHING_IMPROVEMENT_AUDIT.md"
BIG5_SM = frozenset({8, 564, 82, 384, 301})

# --- thresholds (documented in audit)
AMBIG_GAP = 0.035
HIGH_SCORE_MIN = 1.52
HIGH_TEAM_BLOCK = 0.86
MEDIUM_SCORE_MIN = 1.28
MEDIUM_TEAM_BLOCK = 0.72
ATTEMPT_MIN_SCORE = 1.02
MAX_ATTEMPTS_PER_FIXTURE = 18


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


def _fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


# --- MM-3.1D normalization (artifact rules export + runtime)

_SUFFIX_TOKENS = frozenset(
    {"fc", "cf", "ac", "sc", "afc", "club", "deportivo", "de", "la", "the", "as", "ud", "cd", "sv"}
)

_ABBREV_PHASES: list[tuple[str, str]] = [
    (r"\bman utd\b", "manchester united"),
    (r"\bman united\b", "manchester united"),
    (r"\bmanchester utd\b", "manchester united"),
    (r"\bman city\b", "manchester city"),
    (r"\bmanchester c\b\b", "manchester city"),
    (r"\bspurs\b", "tottenham hotspur"),
    (r"\btottenham\b(?!\s+hotspur)", "tottenham hotspur"),
    (r"\binter milan\b", "internazionale"),
    (r"\bfc inter milano\b", "internazionale"),
    (r"\bfc internazionale\b", "internazionale"),
    (r"\bpsg\b", "paris saint germain"),
    (r"\bparis sg\b", "paris saint germain"),
    (r"\bparis saint-germain\b", "paris saint germain"),
    (r"\b1\.?\s*fc\b", " "),
    (r"\b1\.?\s*fussballclub\b", " "),
]


def _apply_manual_patterns(s: str, patterns: list[dict[str, str]], key: str) -> str:
    out = s
    for p in patterns:
        pat = (p.get(key) or "").strip()
        rep = (p.get("replace_with") or "").strip()
        if not pat:
            continue
        try:
            out = re.sub(pat, rep, out, flags=re.I)
        except re.error:
            continue
    return out


def _norm_mm3_1d_core(s: str, manual_before: list[dict[str, str]]) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = _apply_manual_patterns(s, manual_before, "regex_bt2")
    for rx, rep in _ABBREV_PHASES:
        s = re.sub(rx, rep, s, flags=re.I)
    s = re.sub(r"[^\w\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    toks = [t for t in s.split() if t and t not in _SUFFIX_TOKENS]
    return " ".join(toks)


def _norm_mm3_1d(s: str, manual: dict[str, Any]) -> str:
    mb = list(manual.get("regex_bt2_substitutions") or [])
    return _norm_mm3_1d_core(s, mb)


def _tokens(s: str) -> set[str]:
    return {t for t in _norm_mm3_1d_core(s, []).split() if len(t) > 1}


def _token_jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _team_similarity(
    bt2_name: str,
    toa_name: str,
    norm_legacy,
    norm_d: str,
    norm_t: str,
) -> tuple[float, float, float]:
    """Returns (combined_sim, fuzzy, jaccard)."""
    if norm_legacy(bt2_name) == norm_legacy(toa_name):
        return 1.0, 1.0, 1.0
    if norm_d == norm_t:
        return 1.0, 1.0, 1.0
    fz = _fuzzy_ratio(norm_d, norm_t)
    jc = _token_jaccard(bt2_name, toa_name)
    comb = max(fz * 0.55 + jc * 0.45, fz, jc)
    return min(1.0, comb), fz, jc


def _tolerance_tier(delta_sec: float, team_block: float) -> str:
    if delta_sec <= 120:
        return "exact_kickoff"
    if delta_sec <= 300:
        return "pm5m"
    if delta_sec <= 900:
        return "pm15m"
    if delta_sec <= 1800:
        return "pm30m"
    if delta_sec <= 86400:
        d = int(delta_sec // 60)
        if team_block >= 0.9:
            return "same_day_high_sim"
        if team_block >= 0.82:
            return "same_day_med_sim"
    return "beyond_policy"


def _digest_market_flags(ev: dict[str, Any]) -> tuple[bool, bool, bool]:
    keys = set((ev.get("market_keys") or []) if isinstance(ev.get("market_keys"), list) else [])
    h2h = (ev.get("h2h_outcome_count_max") or 0) >= 2 or "h2h" in keys
    totals = (ev.get("totals_distinct_points") or 0) >= 1 or "totals" in keys
    pts = ev.get("totals_points_sample") or []
    ou25 = False
    for p in pts:
        try:
            if abs(float(p) - 2.5) < 0.06:
                ou25 = True
                break
        except (TypeError, ValueError):
            pass
    return h2h, totals, ou25


def _market_bonus(h2h: bool, totals: bool, ou25: bool) -> float:
    b = 0.0
    if h2h:
        b += 0.12
    if totals:
        b += 0.12
    if ou25:
        b += 0.06
    return b


def _composite_score(team_block: float, delta_sec: float, swapped: bool, h2h: bool, totals: bool, ou25: bool) -> float:
    time_pen = min(float(delta_sec), 7200.0) / 7200.0 * (0.35 if team_block > 0.93 else 0.55)
    base = 2.0 * team_block - time_pen + _market_bonus(h2h, totals, ou25)
    if swapped:
        base -= 0.06
    return base


def _confidence_from(top1: float, top2: float, team_block: float) -> str:
    gap = top1 - top2
    if top1 >= HIGH_SCORE_MIN and gap >= AMBIG_GAP and team_block >= HIGH_TEAM_BLOCK:
        return "high"
    if top1 >= MEDIUM_SCORE_MIN and gap >= AMBIG_GAP and team_block >= MEDIUM_TEAM_BLOCK:
        return "medium"
    if gap < AMBIG_GAP and top1 >= MEDIUM_SCORE_MIN:
        return "rejected_ambiguous"
    if top1 >= ATTEMPT_MIN_SCORE:
        return "low"
    return "rejected_ambiguous"


@dataclass
class Fx:
    event_id: int
    sport_key: str
    league_name: str
    sm_league_id: int
    kickoff_utc: datetime
    home: str
    away: str
    home_team_id: int | None
    away_team_id: int | None
    rh: int | None
    ra: int | None
    season: str
    cal_y: int
    cal_m: int


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


def _dist(xs: list[Fx]) -> dict[str, Any]:
    outc: dict[str, int] = defaultdict(int)
    ou25c: dict[str, int] = defaultdict(int)
    bttsc: dict[str, int] = defaultdict(int)
    tg: list[int] = []
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


def _rep_risk_from_league_deltas(rep_rows: list[dict[str, Any]]) -> tuple[str, float]:
    league_deltas = [
        max(abs(r["delta_home_rate_pp"]), abs(r["delta_away_rate_pp"]), abs(r["delta_ou25_over_pp"]))
        for r in rep_rows
        if str(r["segment"]).startswith("league:")
    ]
    max_abs = max(league_deltas) if league_deltas else 0.0
    risk = "low"
    if max_abs > 8:
        risk = "critical"
    elif max_abs > 4:
        risk = "high"
    elif max_abs > 2:
        risk = "medium"
    return risk, max_abs


def _load_raw_toa_events(raw_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Dedupe by (sport_key, toa_event_id); merge market hints."""
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for call in data.get("calls") or []:
        pair = str(call.get("pair") or "")
        if isinstance(pair, str) and "|" in pair:
            sk = pair.split("|", 1)[0].strip()
        else:
            continue
        if not sk:
            continue
        for ev in call.get("events_digest") or []:
            if not isinstance(ev, dict):
                continue
            eid = str(ev.get("id") or "").strip()
            if not eid:
                continue
            k = (sk, eid)
            h2h, totals, ou25 = _digest_market_flags(ev)
            prev = out.get(k)
            if prev is None:
                merged = dict(ev)
                merged["sport_key"] = sk
                merged["_digest_h2h"] = h2h
                merged["_digest_totals"] = totals
                merged["_digest_ou25"] = ou25
                out[k] = merged
            else:
                prev_keys = set(prev.get("market_keys") or [])
                prev_keys |= set(ev.get("market_keys") or [])
                prev["market_keys"] = sorted(prev_keys)
                prev["h2h_outcome_count_max"] = max(
                    int(prev.get("h2h_outcome_count_max") or 0),
                    int(ev.get("h2h_outcome_count_max") or 0),
                )
                prev["totals_distinct_points"] = max(
                    int(prev.get("totals_distinct_points") or 0),
                    int(ev.get("totals_distinct_points") or 0),
                )
                ps = set(prev.get("totals_points_sample") or [])
                ps |= set(ev.get("totals_points_sample") or [])
                prev["totals_points_sample"] = sorted(ps)[:12]
                p2, p3, p4 = _digest_market_flags(prev)
                prev["_digest_h2h"] = prev["_digest_h2h"] or p2
                prev["_digest_totals"] = prev["_digest_totals"] or p3
                prev["_digest_ou25"] = prev["_digest_ou25"] or p4
    return out


def main() -> None:
    import psycopg2
    import psycopg2.extras

    ap = argparse.ArgumentParser()
    ap.add_argument("--db-url", default="")
    args = ap.parse_args()

    paths = {
        "raw": OUT / "mm3_1b_toa_p0_raw.json",
        "matches": OUT / "mm3_1b_toa_p0_match_rows.csv",
        "board_rows": OUT / "mm3_1b_toa_p0_market_board_rows.csv",
        "inv": OUT / "mm3_1a_big5_fixture_inventory.csv",
        "readiness_1c": OUT / "mm3_1c_mm3_2_readiness.json",
        "rep_1c": OUT / "mm3_1c_representativeness_summary.json",
        "manual_aliases": OUT / "mm3_1d_manual_team_aliases.json",
    }
    for label in ("raw", "matches", "board_rows", "inv"):
        if not paths[label].is_file():
            print(f"Falta artefacto {label}: {paths[label]}", file=sys.stderr)
            sys.exit(2)

    norm_legacy = _load_mm3_1a_norm()
    manual: dict[str, Any] = {}
    if paths["manual_aliases"].is_file():
        manual = json.loads(paths["manual_aliases"].read_text(encoding="utf-8"))

    rules_doc = {
        "version": 1,
        "lowercase": True,
        "strip_accents": True,
        "remove_punctuation_to_space": True,
        "collapse_whitespace": True,
        "strip_suffix_tokens": sorted(_SUFFIX_TOKENS),
        "abbrev_regex_replacements": [{"pattern": p, "replace": r} for p, r in _ABBREV_PHASES],
        "manual_alias_file": str(paths["manual_aliases"]),
        "manual_loaded": bool(manual),
    }
    (OUT / "mm3_1d_team_name_normalization_rules.json").write_text(
        json.dumps(rules_doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("MM3_1D: parse raw.json…", flush=True)
    toa_by_key = _load_raw_toa_events(paths["raw"])

    by_sport_day: dict[tuple[str, date], list[tuple[str, str]]] = defaultdict(list)
    for (sk, eid), ev in toa_by_key.items():
        ct = _parse_dt(str(ev.get("commence_time") or ""))
        if ct is None:
            continue
        d = ct.astimezone(timezone.utc).date()
        for dd in (-1, 0, 1):
            by_sport_day[(sk, d + timedelta(days=dd))].append((sk, eid))

    prev_read = {}
    if paths["readiness_1c"].is_file():
        prev_read = json.loads(paths["readiness_1c"].read_text(encoding="utf-8"))
    previous_matched = int(prev_read.get("matched_events_count") or 2031)
    previous_rate = float(prev_read.get("match_rate") or 0.5336)
    prev_rep = str(prev_read.get("representativeness_risk") or "critical")
    prev_hole = bool(prev_read.get("league_coverage_hole_flag", True))

    original_rows: dict[int, dict[str, str]] = {}
    original_toa_by_bt2: dict[int, str] = {}
    with paths["matches"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            eid = int(row["bt2_event_id"])
            original_rows[eid] = row
            original_toa_by_bt2[eid] = str(row.get("toa_event_id") or "")

    board_orig: dict[int, dict[str, str]] = {}
    with paths["board_rows"].open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            board_orig[int(row["bt2_event_id"])] = row

    dsn = _load_bt2_database_url() if not args.db_url.strip() else re.sub(
        r"^postgresql\+asyncpg://", "postgresql://", args.db_url.strip(), flags=re.I
    )
    try:
        from apps.api.bt2_theoddsapi_mapping import TOA_SPORT_KEYS_BY_SM_LEAGUE_ID
    except ImportError:
        sys.path.insert(0, str(REPO))
        from apps.api.bt2_theoddsapi_mapping import TOA_SPORT_KEYS_BY_SM_LEAGUE_ID

    print("MM3_1D: SELECT bt2_events…", flush=True)
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
          th.id AS home_team_id,
          ta.id AS away_team_id,
          th.name AS home_team,
          ta.name AS away_team,
          e.result_home,
          e.result_away,
          e.season
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
        sk = TOA_SPORT_KEYS_BY_SM_LEAGUE_ID.get(int(d["sm_league_id"]))
        if not sk:
            continue
        rh, ra = d.get("result_home"), d.get("result_away")
        fixtures.append(
            Fx(
                event_id=int(d["event_id"]),
                sport_key=sk,
                league_name=str(d["league_name"] or ""),
                sm_league_id=int(d["sm_league_id"]),
                kickoff_utc=ko,
                home=str(d["home_team"] or ""),
                away=str(d["away_team"] or ""),
                home_team_id=int(d["home_team_id"]) if d.get("home_team_id") is not None else None,
                away_team_id=int(d["away_team_id"]) if d.get("away_team_id") is not None else None,
                rh=int(rh) if rh is not None else None,
                ra=int(ra) if ra is not None else None,
                season=str(d["season"] or ""),
                cal_y=ko.year,
                cal_m=ko.month,
            )
        )
    conn.close()

    n_full = len(fixtures)
    fixtures_by_id = {f.event_id: f for f in fixtures}

    # --- matching attempts + best candidate (algorithmic)
    attempt_rows: list[dict[str, Any]] = []
    best_candidates: dict[int, list[tuple[float, str, dict[str, Any]]]] = defaultdict(list)
    alias_evidence: dict[tuple[int, str, str], dict[str, Any]] = {}

    for fx in fixtures:
        sk = fx.sport_key
        day0 = fx.kickoff_utc.date()
        cand_keys: set[tuple[str, str]] = set()
        for dd in (-1, 0, 1):
            for key in by_sport_day.get((sk, day0 + timedelta(days=dd)), []):
                cand_keys.add(key)

        scored: list[tuple[float, str, dict[str, Any]]] = []
        for key in cand_keys:
            ev = toa_by_key.get(key)
            if not ev:
                continue
            ct = _parse_dt(str(ev.get("commence_time") or ""))
            if ct is None:
                continue
            ct = ct.astimezone(timezone.utc)
            delta_sec = abs((fx.kickoff_utc - ct).total_seconds())
            h_toa = str(ev.get("home_team") or "")
            a_toa = str(ev.get("away_team") or "")
            nd_h = _norm_mm3_1d(fx.home, manual)
            nd_a = _norm_mm3_1d(fx.away, manual)
            nt_h = _norm_mm3_1d(h_toa, manual)
            nt_a = _norm_mm3_1d(a_toa, manual)
            sh, fzh, jh = _team_similarity(fx.home, h_toa, norm_legacy, nd_h, nt_h)
            sa, fza, ja = _team_similarity(fx.away, a_toa, norm_legacy, nd_a, nt_a)
            direct = (sh + sa) / 2.0
            shs, _, _ = _team_similarity(fx.home, a_toa, norm_legacy, nd_h, nt_a)
            sas, _, _ = _team_similarity(fx.away, h_toa, norm_legacy, nd_a, nt_h)
            swap = (shs + sas) / 2.0
            swapped = swap > direct + 0.001
            team_block = max(direct, swap)
            h2h_d, tot_d, ou_d = _digest_market_flags(ev)
            score = _composite_score(team_block, delta_sec, swapped, h2h_d, tot_d, ou_d)
            tier = _tolerance_tier(delta_sec, team_block)
            if score < ATTEMPT_MIN_SCORE and tier.startswith("beyond"):
                continue
            if score < ATTEMPT_MIN_SCORE:
                continue
            row = {
                "bt2_event_id": fx.event_id,
                "sport_key": sk,
                "league_name": fx.league_name,
                "kickoff_bt2_utc": fx.kickoff_utc.isoformat(),
                "toa_event_id": key[1],
                "commence_toa": ct.isoformat().replace("+00:00", "Z"),
                "delta_sec": int(delta_sec),
                "tolerance_tier": tier,
                "home_bt2": fx.home,
                "away_bt2": fx.away,
                "home_toa": h_toa,
                "away_toa": a_toa,
                "orientation": "swapped" if swapped else "direct",
                "sim_team_block": round(team_block, 4),
                "sim_direct": round(direct, 4),
                "sim_swap": round(swap, 4),
                "digest_h2h_ok": h2h_d,
                "digest_totals_ok": tot_d,
                "digest_ou25_ok": ou_d,
                "composite_score": round(score, 4),
            }
            scored.append((score, key[1], row))
            # alias evidence: near-miss names
            if 0.75 <= team_block < 0.98:
                for tid, bname, tname in (
                    (fx.home_team_id, fx.home, h_toa),
                    (fx.away_team_id, fx.away, a_toa),
                ):
                    if tid is None:
                        continue
                    ak = (tid, bname, tname)
                    if ak not in alias_evidence:
                        alias_evidence[ak] = {
                            "bt2_team_id": tid,
                            "bt2_team_name": bname,
                            "toa_team_name_candidate": tname,
                            "league": fx.league_name,
                            "sport_key": sk,
                            "similarity_score": 0.0,
                            "evidence_count": 0,
                        }
                    alias_evidence[ak]["evidence_count"] += 1
                    alias_evidence[ak]["similarity_score"] = max(
                        float(alias_evidence[ak]["similarity_score"]),
                        _fuzzy_ratio(bname, tname),
                    )

        scored.sort(key=lambda x: -x[0])
        top = scored[:MAX_ATTEMPTS_PER_FIXTURE]
        for sc, _eid, row in top:
            attempt_rows.append(row)
        best_candidates[fx.event_id] = [(s, e, r) for s, e, r in top]

    _write_csv(
        OUT / "mm3_1d_matching_attempt_rows.csv",
        list(attempt_rows[0].keys()) if attempt_rows else [
            "bt2_event_id",
            "sport_key",
            "composite_score",
        ],
        attempt_rows,
    )

    # --- best / ambiguous
    best_rows: list[dict[str, Any]] = []
    amb_rows: list[dict[str, Any]] = []
    medium_diag = 0
    low_ct = 0
    amb_ct = 0
    unmatched_no_candidate = 0

    for fx in fixtures:
        eid = fx.event_id
        if eid in original_rows:
            o = original_rows[eid]
            best_rows.append(
                {
                    "bt2_event_id": eid,
                    "toa_event_id": o.get("toa_event_id"),
                    "sport_key": fx.sport_key,
                    "league_name": fx.league_name,
                    "source": "mm3_1b_original",
                    "confidence": "legacy_high",
                    "composite_score": float(o.get("match_score") or 0),
                    "top2_gap": "",
                    "team_block_est": "",
                    "digest_h2h_ok": True,
                    "digest_totals_ok": True,
                    "digest_ou25_ok": True,
                    "kickoff_bt2_utc": o.get("kickoff_bt2_utc"),
                    "commence_toa": o.get("commence_toa"),
                    "home_bt2": o.get("home_bt2"),
                    "away_bt2": o.get("away_bt2"),
                    "home_toa": o.get("home_toa"),
                    "away_toa": o.get("away_toa"),
                }
            )
            continue

        cand = best_candidates.get(eid, [])
        if len(cand) < 1:
            best_rows.append(
                {
                    "bt2_event_id": eid,
                    "toa_event_id": "",
                    "sport_key": fx.sport_key,
                    "league_name": fx.league_name,
                    "source": "mm3_1d_only",
                    "confidence": "rejected_ambiguous",
                    "composite_score": 0.0,
                    "top2_gap": "",
                    "team_block_est": "",
                    "digest_h2h_ok": False,
                    "digest_totals_ok": False,
                    "digest_ou25_ok": False,
                    "kickoff_bt2_utc": fx.kickoff_utc.isoformat(),
                    "commence_toa": "",
                    "home_bt2": fx.home,
                    "away_bt2": fx.away,
                    "home_toa": "",
                    "away_toa": "",
                }
            )
            unmatched_no_candidate += 1
            continue
        top1_s, top1_id, top1_row = cand[0]
        top2_s = cand[1][0] if len(cand) > 1 else -1.0
        gap = top1_s - top2_s if top2_s >= 0 else top1_s
        tb = float(top1_row["sim_team_block"])
        conf = _confidence_from(top1_s, top2_s, tb)
        h2h_d = bool(top1_row["digest_h2h_ok"])
        tot_d = bool(top1_row["digest_totals_ok"])
        ou_d = bool(top1_row["digest_ou25_ok"])
        if conf == "high" and not (h2h_d and tot_d and ou_d):
            conf = "medium"
        if conf == "medium" and not (h2h_d and tot_d):
            conf = "low"
        if conf == "medium":
            medium_diag += 1
        elif conf == "low":
            low_ct += 1
        elif conf == "rejected_ambiguous":
            amb_ct += 1
            amb_rows.append(
                {
                    "bt2_event_id": eid,
                    "top1_toa_event_id": top1_id,
                    "top1_score": round(top1_s, 4),
                    "top2_toa_event_id": cand[1][1] if len(cand) > 1 else "",
                    "top2_score": round(top2_s, 4) if top2_s >= 0 else "",
                    "gap": round(gap, 4),
                }
            )

        ev = toa_by_key.get((fx.sport_key, top1_id))
        ct_s = str(ev.get("commence_time")) if ev else ""
        h_toa = str(ev.get("home_team")) if ev else ""
        a_toa = str(ev.get("away_team")) if ev else ""

        best_rows.append(
            {
                "bt2_event_id": eid,
                "toa_event_id": top1_id if conf not in ("rejected_ambiguous", "low") else "",
                "sport_key": fx.sport_key,
                "league_name": fx.league_name,
                "source": "mm3_1d_only",
                "confidence": conf,
                "composite_score": round(top1_s, 4),
                "top2_gap": round(gap, 4),
                "team_block_est": round(tb, 4),
                "digest_h2h_ok": h2h_d,
                "digest_totals_ok": tot_d,
                "digest_ou25_ok": ou_d,
                "kickoff_bt2_utc": fx.kickoff_utc.isoformat(),
                "commence_toa": ct_s,
                "home_bt2": fx.home,
                "away_bt2": fx.away,
                "home_toa": h_toa,
                "away_toa": a_toa,
            }
        )

    _write_csv(
        OUT / "mm3_1d_best_match_rows.csv",
        list(best_rows[0].keys()) if best_rows else ["bt2_event_id"],
        best_rows,
    )
    _write_csv(
        OUT / "mm3_1d_ambiguous_match_rows.csv",
        ["bt2_event_id", "top1_toa_event_id", "top1_score", "top2_toa_event_id", "top2_score", "gap"],
        amb_rows,
    )

    # --- alias proposals CSV
    prop_rows: list[dict[str, Any]] = []
    for v in sorted(alias_evidence.values(), key=lambda x: (-x["evidence_count"], -x["similarity_score"])):
        sim = float(v["similarity_score"])
        evc = int(v["evidence_count"])
        rec = "review_manual"
        if sim >= 0.94 and evc >= 4:
            rec = "strong_alias_candidate"
        elif sim >= 0.88 and evc >= 2:
            rec = "probable_typo_or_locale"
        safe = sim >= 0.94 and evc >= 3
        prop_rows.append(
            {
                "bt2_team_id": v["bt2_team_id"],
                "bt2_team_name": v["bt2_team_name"],
                "toa_team_name_candidate": v["toa_team_name_candidate"],
                "league": v["league"],
                "sport_key": v["sport_key"],
                "similarity_score": round(sim, 4),
                "evidence_count": evc,
                "recommendation": rec,
                "safe_to_auto_apply_artifact_only": safe,
            }
        )
    prop_rows = prop_rows[:4000]
    _write_csv(
        OUT / "mm3_1d_team_alias_proposals.csv",
        [
            "bt2_team_id",
            "bt2_team_name",
            "toa_team_name_candidate",
            "league",
            "sport_key",
            "similarity_score",
            "evidence_count",
            "recommendation",
            "safe_to_auto_apply_artifact_only",
        ],
        prop_rows,
    )

    # --- board-eligible ids
    high_ids: set[int] = set()
    for br in best_rows:
        if br.get("confidence") in ("legacy_high", "high") and br.get("toa_event_id"):
            high_ids.add(int(br["bt2_event_id"]))

    def synth_board(evid: int) -> dict[str, str]:
        fx = fixtures_by_id[evid]
        toa_id = ""
        for br in best_rows:
            if int(br["bt2_event_id"]) == evid:
                toa_id = str(br.get("toa_event_id") or "")
                break
        ev = toa_by_key.get((fx.sport_key, toa_id)) if toa_id else None
        h2h, tot, ou = (False, False, False)
        pts: list[str] = []
        if ev:
            h2h, tot, ou = _digest_market_flags(ev)
            pts = [str(p) for p in (ev.get("totals_points_sample") or [])]
        return {
            "bt2_event_id": str(evid),
            "sport_key": fx.sport_key,
            "ft_1x2_ready": str(h2h),
            "totals_ready": str(tot),
            "ou_lines_count": str(len(pts)),
            "ou_lines_sorted": ",".join(sorted(pts, key=lambda x: float(x) if re.match(r"^-?\d", x) else 0)),
            "ou25_ready": str(ou),
            "board_source": "mm3_1d_digest_synth" if evid not in board_orig else "mm3_1b_original",
        }

    improved_board: dict[int, dict[str, str]] = {}
    for evid in sorted(high_ids):
        if evid in board_orig:
            r = dict(board_orig[evid])
            r["board_source"] = "mm3_1b_original"
            improved_board[evid] = r
        else:
            improved_board[evid] = synth_board(evid)

    board_list = list(improved_board.values())
    _write_csv(
        OUT / "mm3_1d_improved_market_board_rows.csv",
        list(board_list[0].keys()) if board_list else ["bt2_event_id"],
        board_list,
    )
    by_sk_board: dict[str, dict[str, int]] = defaultdict(lambda: {"fixtures": 0, "matched_bt2": 0})
    for f in fixtures:
        by_sk_board[f.sport_key]["fixtures"] += 1
        if f.event_id in high_ids:
            by_sk_board[f.sport_key]["matched_bt2"] += 1
    msum = {"ft_1x2_ready": 0, "totals_ready": 0, "ou2_5_ready": 0, "ou_lines_sum": 0}
    for evid in high_ids:
        brd = improved_board[evid]
        if str(brd.get("ft_1x2_ready")).lower() == "true":
            msum["ft_1x2_ready"] += 1
        if str(brd.get("totals_ready")).lower() == "true":
            msum["totals_ready"] += 1
        if str(brd.get("ou25_ready")).lower() == "true":
            msum["ou2_5_ready"] += 1
        try:
            msum["ou_lines_sum"] += int(float(str(brd.get("ou_lines_count") or "0")))
        except ValueError:
            pass
    board_json_payload = {
        "by_sport_key": {k: dict(v) for k, v in sorted(by_sk_board.items())},
        "matched_board": msum,
        "n_matched_bt2_distinct": len(high_ids),
        "schema_note": "Digest-derived flags for mm3_1d_only rows; legacy rows assumed P0-complete per MM-3.1B board.",
    }
    (OUT / "mm3_1d_improved_market_board.json").write_text(
        json.dumps(board_json_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    improved_matched = len(high_ids)
    newly = len(high_ids - set(original_rows.keys()))

    # --- coverage after
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
                "fixtures_matched_improved": 0,
                "h2h_ready": 0,
                "totals_ready": 0,
                "ou25_ready": 0,
            }
        keydims[k]["fixtures_big5_db"] += 1
        if f.event_id in high_ids:
            brd = improved_board.get(f.event_id, {})
            keydims[k]["fixtures_matched_improved"] += 1
            if str(brd.get("ft_1x2_ready")).lower() == "true":
                keydims[k]["h2h_ready"] += 1
            if str(brd.get("totals_ready")).lower() == "true":
                keydims[k]["totals_ready"] += 1
            if str(brd.get("ou25_ready")).lower() == "true":
                keydims[k]["ou25_ready"] += 1

    for k, v in sorted(keydims.items()):
        n = v["fixtures_big5_db"]
        m = v["fixtures_matched_improved"]
        cov_rows.append(
            {
                **v,
                "fixtures_not_matched": n - m,
                "match_rate": round(m / n, 4) if n else 0.0,
            }
        )
    _write_csv(
        OUT / "mm3_1d_coverage_after_matching.csv",
        list(cov_rows[0].keys()) if cov_rows else [],
        cov_rows,
    )

    # --- representativeness after
    matched_fxs = [f for f in fixtures if f.event_id in high_ids]
    full_d = _dist(fixtures)
    mat_d = _dist(matched_fxs)
    rep_rows: list[dict[str, Any]] = [
        {
            "segment": "global",
            "universe_n": full_d["n"],
            "matched_n": mat_d["n"],
            "delta_home_rate_pp": round((mat_d["home_rate"] - full_d["home_rate"]) * 100, 2),
            "delta_draw_rate_pp": round((mat_d["draw_rate"] - full_d["draw_rate"]) * 100, 2),
            "delta_away_rate_pp": round((mat_d["away_rate"] - full_d["away_rate"]) * 100, 2),
            "delta_ou25_over_pp": round((mat_d["ou25_over_rate"] - full_d["ou25_over_rate"]) * 100, 2),
            "delta_btts_yes_pp": round((mat_d["btts_yes_rate"] - full_d["btts_yes_rate"]) * 100, 2),
            "avg_goals_universe": full_d["avg_total_goals"],
            "avg_goals_matched": mat_d["avg_total_goals"],
        }
    ]
    for sk in sorted({f.sport_key for f in fixtures}):
        uf = [f for f in fixtures if f.sport_key == sk]
        mf = [f for f in matched_fxs if f.sport_key == sk]
        if not uf:
            continue
        pf, pm = _dist(uf), _dist(mf)
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
    rep_risk_after, max_abs_after = _rep_risk_from_league_deltas(rep_rows)

    league_rates_before: dict[str, float] = {}
    # approximate before from original matched per league
    orig_by_sk: dict[str, set[int]] = defaultdict(set)
    for eid in original_rows:
        fx = fixtures_by_id.get(eid)
        if fx:
            orig_by_sk[fx.sport_key].add(eid)
    full_by_sk: dict[str, int] = defaultdict(int)
    for f in fixtures:
        full_by_sk[f.sport_key] += 1
    for sk, sset in orig_by_sk.items():
        league_rates_before[sk] = len(sset) / full_by_sk[sk] if full_by_sk[sk] else 0.0
    league_rates_after: dict[str, float] = {}
    imp_by_sk: dict[str, set[int]] = defaultdict(set)
    for eid in high_ids:
        fx = fixtures_by_id.get(eid)
        if fx:
            imp_by_sk[fx.sport_key].add(eid)
    for sk in full_by_sk:
        league_rates_after[sk] = len(imp_by_sk[sk]) / full_by_sk[sk] if full_by_sk[sk] else 0.0

    rep_after = {
        "full_big5_events": n_full,
        "improved_matched_events": improved_matched,
        "previous_matched_events": previous_matched,
        "newly_matched_count": newly,
        "improved_match_rate": round(improved_matched / n_full, 4) if n_full else 0.0,
        "previous_match_rate": previous_rate,
        "representativeness_risk_before": prev_rep,
        "representativeness_risk_after": rep_risk_after,
        "max_abs_league_delta_pp_before": (
            float(json.loads(paths["rep_1c"].read_text(encoding="utf-8")).get("max_abs_league_delta_pp", 0))
            if paths["rep_1c"].is_file()
            else None
        ),
        "max_abs_league_delta_pp_after": round(max_abs_after, 2),
        "league_match_rate_before_by_sport_key": {k: round(v, 4) for k, v in sorted(league_rates_before.items())},
        "league_match_rate_after_by_sport_key": {k: round(v, 4) for k, v in sorted(league_rates_after.items())},
        "ligue1_before": round(league_rates_before.get("soccer_france_ligue_one", 0), 4),
        "ligue1_after": round(league_rates_after.get("soccer_france_ligue_one", 0), 4),
    }
    (OUT / "mm3_1d_representativeness_after_matching.json").write_text(
        json.dumps(rep_after, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- ROI subset v1
    roi_rows: list[dict[str, Any]] = []
    for evid in sorted(high_ids):
        fx = fixtures_by_id[evid]
        brd = improved_board[evid]
        if str(brd.get("ft_1x2_ready")).lower() != "true":
            continue
        if str(brd.get("totals_ready")).lower() != "true":
            continue
        if str(brd.get("ou25_ready")).lower() != "true":
            continue
        if fx.rh is None or fx.ra is None:
            continue
        conf = next((b["confidence"] for b in best_rows if int(b["bt2_event_id"]) == evid), "")
        if conf not in ("legacy_high", "high"):
            continue
        toa_id = ""
        for b in best_rows:
            if int(b["bt2_event_id"]) == evid:
                toa_id = str(b.get("toa_event_id") or "")
                break
        roi_rows.append(
            {
                "event_id": evid,
                "league": fx.league_name,
                "sport_key": fx.sport_key,
                "kickoff_utc": fx.kickoff_utc.isoformat(),
                "home_team": fx.home,
                "away_team": fx.away,
                "ft_1x2_home_decimal": "",
                "ft_1x2_draw_decimal": "",
                "ft_1x2_away_decimal": "",
                "totals_line_main": "",
                "totals_over_decimal": "",
                "totals_under_decimal": "",
                "ou2_5_over_decimal": "",
                "ou2_5_under_decimal": "",
                "result_home": fx.rh,
                "result_away": fx.ra,
                "ft_1x2_outcome": _outcome_1x2(fx.rh, fx.ra),
                "ou2_5_outcome": _ou25(fx.rh, fx.ra),
                "btts_outcome": _btts(fx.rh, fx.ra),
                "toa_event_id": toa_id,
                "source": "TOA historical T-60",
                "note": "Odds decimales no están en raw digest; MM-3.2 parseará bookmakers si se amplía artifact.",
            }
        )
    _write_csv(OUT / "mm3_1d_roi_safe_subset_v1.csv", list(roi_rows[0].keys()) if roi_rows else [], roi_rows)
    (OUT / "mm3_1d_roi_safe_subset_v1.json").write_text(
        json.dumps({"n_events": len(roi_rows), "events": roi_rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # --- league hole + readiness
    min_league_rate_after = min(league_rates_after.values()) if league_rates_after else 0.0
    worst_sk = min(league_rates_after, key=lambda k: league_rates_after[k]) if league_rates_after else ""
    league_hole = False
    for sk, n in full_by_sk.items():
        if n < 200:
            continue
        if league_rates_after.get(sk, 0) < 0.42:
            league_hole = True
            break

    high_conf_count = sum(1 for b in best_rows if b.get("confidence") in ("legacy_high", "high") and b.get("toa_event_id"))
    all_high_markets = True
    for evid in high_ids:
        brd = improved_board[evid]
        if str(brd.get("ft_1x2_ready")).lower() != "true":
            all_high_markets = False
            break
        if str(brd.get("totals_ready")).lower() != "true":
            all_high_markets = False
            break
        if str(brd.get("ou25_ready")).lower() != "true":
            all_high_markets = False
            break

    improved_rate = improved_matched / n_full if n_full else 0.0
    ready_subset = (
        high_conf_count >= 2000
        and all_high_markets
        and rep_risk_after in ("low", "medium")
        and not league_hole
    )
    balanced = True
    if league_rates_after:
        mx = max(league_rates_after.values())
        mn = min(league_rates_after.values())
        if mx - mn > 0.35:
            balanced = False
    ready_full = (
        improved_rate >= 0.65
        and rep_risk_after in ("low", "medium")
        and balanced
        and not league_hole
    )

    if ready_full:
        rec = "start_mm3_2a_on_matched_subset"
    elif ready_subset:
        rec = "start_mm3_2a_on_matched_subset"
    elif improved_matched > previous_matched + 50 and rep_risk_after != "critical":
        rec = "improve_matching_first"
    else:
        rec = "improve_matching_first"

    readiness = {
        "previous_match_rate": round(previous_rate, 4),
        "improved_match_rate": round(improved_rate, 4),
        "previous_matched_count": previous_matched,
        "improved_matched_events_count": improved_matched,
        "newly_matched_count": newly,
        "high_confidence_match_count": high_conf_count,
        "medium_confidence_diagnostic_count": medium_diag,
        "rejected_ambiguous_count": amb_ct,
        "unmatched_no_candidate_count": unmatched_no_candidate,
        "low_confidence_count": low_ct,
        "representativeness_risk": rep_risk_after,
        "representativeness_risk_previous": prev_rep,
        "league_coverage_hole_flag": league_hole,
        "league_coverage_hole_flag_previous": prev_hole,
        "min_league_match_rate_after": round(min_league_rate_after, 4),
        "worst_league_sport_key_after": worst_sk,
        "ready_for_mm3_2a_subset": ready_subset,
        "ready_for_mm3_2_full_big5": ready_full,
        "recommended_path": rec,
        "all_high_confidence_have_h2h_totals_ou25_digest": all_high_markets,
    }
    (OUT / "mm3_1d_mm3_2_readiness.json").write_text(
        json.dumps(readiness, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # --- Audit markdown
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(
        f"""# MM-3.1D — TOA Matching Improvement / Alias Layer Audit

## 1. Executive summary

- Partidos Big 5 en DB: **{n_full}**. Matched MM-3.1B: **{previous_matched}** ({100 * previous_rate:.1f}%).
- Tras reprocesar **solo** `mm3_1b_toa_p0_raw.json` con normalización extendida + similitud + tolerancias: matched de board **{improved_matched}** ({100 * improved_rate:.1f}%), nuevos **{newly}**.
- Riesgo representatividad (max |Δ| liga): **{prev_rep}** → **{rep_risk_after}** (max Δ ≈ **{max_abs_after:.1f}** pp).
- `ready_for_mm3_2a_subset`: **{ready_subset}**; `ready_for_mm3_2_full_big5`: **{ready_full}**; ruta: **{rec}**.

## 2. Scope and restrictions

Artifact-only + SELECT Postgres. Sin TOA/SM/DSR, sin escrituras, sin alias en DB.

## 3. Why MM-3.1D was needed

MM-3.1C mostró `team_name_mismatch` y sesgo por liga; el backfill MM-3.1B usó `_norm_team` estricto TOA↔BT2.

## 4. MM-3.1B / 1C recap

2031 matches, ~53% match rate, riesgo **critical**, `league_coverage_hole_flag` true (Ligue 1 baja vs EPL).

## 5. Name normalization strategy

Ver `scripts/outputs/mm3_1d_team_name_normalization_rules.json`. Opcional: `scripts/outputs/mm3_1d_manual_team_aliases.json` (lista `regex_bt2_substitutions`: `regex_bt2`, `replace_with`).

## 6. Alias proposals

`scripts/outputs/mm3_1d_team_alias_proposals.csv` (evidencia agregada; **no** aplicar a DB).

## 7. Kickoff tolerance strategy

Buckets en `mm3_1d_matching_attempt_rows.csv`: exact, ±5/15/30 min, mismo día con alta similitud de equipos.

## 8. Matching score design

`composite_score = 2 * team_block - time_pen + bonus_mercados_digest` con penalización swap leve; desempate por gap top1-top2 (**{AMBIG_GAP}**).

## 9. Improved match results

`mm3_1d_best_match_rows.csv`, `mm3_1d_ambiguous_match_rows.csv`.

## 10. Coverage before/after

`mm3_1d_coverage_after_matching.csv` + tasas por liga en `mm3_1d_representativeness_after_matching.json`.

## 11. Representativeness before/after

Riesgo previo: **{prev_rep}**. Tras matching: **{rep_risk_after}** (max |Δ| liga **{max_abs_after:.2f}** pp).

## 12. ROI-safe subset v1

`mm3_1d_roi_safe_subset_v1.csv` / `.json` — solo **high** + **legacy_high** con flags digest h2h/totals/OU2.5; odds decimales siguen vacías (no están en digest).

## 13. MM-3.2 readiness decision

`scripts/outputs/mm3_1d_mm3_2_readiness.json`.

## 14. What this proves

Se puede **re-scorar** el universo TOA ya descargado y proponer matches/alias sin créditos adicionales.

## 15. What this does not prove

Equivalencia con el matcher de producción MM-3.1B, calidad de precios, ni ausencia de colisiones TOA no vistas en digest.

## 16. Recommended next step

{"Curación manual de `mm3_1d_manual_team_aliases.json` + revisión de filas `safe_to_auto_apply_artifact_only` antes de MM-3.2." if not ready_subset else "Validar pipeline MM-3.2A sobre `mm3_1d_roi_safe_subset_v1` con ingest de odds desde artifact enriquecido si se parsea bookmakers."}

""",
        encoding="utf-8",
    )

    print(f"MM3_1D: listo — {OUT / 'mm3_1d_mm3_2_readiness.json'}", flush=True)


if __name__ == "__main__":
    main()

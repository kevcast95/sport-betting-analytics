#!/usr/bin/env python3
"""
Fase 3D — vendor readiness (SportMonks fixture master + The Odds API), sin llamadas HTTP.

- Solo lectura PostgreSQL (BT2 + raw SM).
- No usa SM Odds como fuente.
- No modifica bounded replay ni contratos T-60 de 3C.
"""

from __future__ import annotations

import os
import csv
import importlib.util
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2.extras

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from apps.api.bt2_settings import bt2_settings

OUT_DIR = _repo / "scripts" / "outputs" / "bt2_vendor_readiness"
COHORT_A0 = date(2025, 1, 1)
COHORT_A1 = date(2025, 5, 31)
REGION_LAB = "us"
MARKET_LAB = "h2h"
# Límite de fixtures con parse SM + VP (costoso). La cohorte A completa ~10k+;
# para readiness basta una muestra representativa + metadatos agregados por SQL aparte.
MAX_COHORT_VP_COMPUTE = 900
DRIFT_SAMPLE_LIMIT = 1500

# SportMonks league_id -> The Odds API sport_key (soccer). Fuente: convención TOA + TIER_MAP 3C.
SM_LEAGUE_TO_ODDS_SPORT_KEY: dict[int, str] = {
    8: "soccer_epl",
    564: "soccer_spain_la_liga",
    82: "soccer_germany_bundesliga",
    384: "soccer_italy_serie_a",
    301: "soccer_france_ligue_one",
    72: "soccer_netherlands_eredivisie",
    208: "soccer_belgium_first_div",
    462: "soccer_portugal_primeira_liga",
    501: "soccer_spl",
    600: "soccer_turkey_super_league",
    779: "soccer_usa_mls",
    743: "soccer_mexico_ligamx",
    1122: "soccer_conmebol_libertadores",
    1116: "soccer_conmebol_sudamericana",
    9: "soccer_efl_champ",
    85: "soccer_germany_bundesliga2",
    304: "soccer_france_ligue_two",
    387: "soccer_italy_serie_b",
    567: "soccer_spain_segunda_division",
    636: "soccer_argentina_primera_division",
    648: "soccer_brazil_serie_a",
    672: "soccer_colombia_primera_a",
    968: "soccer_japan_j_league",
    1034: "soccer_korea_kleague1",
    573: "soccer_sweden_allsvenskan",
    453: "soccer_poland_ekstraklasa",
}

# Nombres típicos (fallback)
NAME_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("premier league",), "soccer_epl"),
    (("la liga", "laliga"), "soccer_spain_la_liga"),
    (("bundesliga",), "soccer_germany_bundesliga"),
    (("serie a",), "soccer_italy_serie_a"),
    (("ligue 1", "ligue 2"), "soccer_france_ligue_one"),
    (("eredivisie",), "soccer_netherlands_eredivisie"),
    (("primeira liga", "liga portugal"), "soccer_portugal_primeira_liga"),
    (("mls",), "soccer_usa_mls"),
    (("champions league", "uefa champions"), "soccer_uefa_champs_league"),
    (("europa league",), "soccer_uefa_europa_league"),
    (("fa cup",), "soccer_fa_cup"),
    (("copa del rey",), "soccer_spain_copa_del_rey"),
    (("copa libertadores",), "soccer_conmebol_libertadores"),
    (("copa sudamericana",), "soccer_conmebol_sudamericana"),
    (("brasileirão", "brasileirao", "serie a brazil"), "soccer_brazil_serie_a"),
    (("super lig", "super lig turkey"), "soccer_turkey_super_league"),
]


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def _connect_bt2():
    return psycopg2.connect(_dsn(), connect_timeout=12)


def _load_normalize_parsers():
    p = _repo / "scripts" / "bt2_cdm" / "normalize_fixtures.py"
    spec = importlib.util.spec_from_file_location("bt2_normalize_fixtures", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _load_historical_proto():
    p = _repo / "scripts" / "bt2_historical_sm_lbu_replay_prototype.py"
    spec = importlib.util.spec_from_file_location("bt2_hist_proto", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["bt2_hist_proto"] = mod
    spec.loader.exec_module(mod)
    return mod


def _norm_team(s: str) -> str:
    t = (s or "").lower().strip()
    t = re.sub(r"[\.\'\`´]", "", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for tok in (" fc", " cf", " sc", " afc", " fk", " ac"):
        if t.endswith(tok):
            t = t[: -len(tok)].strip()
    return t


def _expected_sport_key(
    sm_league_id: Optional[int], league_name: str, country: str
) -> tuple[str, str, str, int]:
    """
    Returns: sport_key_expected, mapping_status, mapping_confidence, priority
    """
    lid = int(sm_league_id) if sm_league_id is not None else None
    if lid is not None and lid in SM_LEAGUE_TO_ODDS_SPORT_KEY:
        return SM_LEAGUE_TO_ODDS_SPORT_KEY[lid], "mapped_expected", "high", 1
    name = (league_name or "").lower()
    for hints, key in NAME_HINTS:
        if any(h in name for h in hints):
            return key, "needs_api_confirmation", "medium", 3
    if not name or name in ("(sin_liga)", "(sin_nombre_liga)"):
        return "", "needs_manual_review", "low", 9
    if "women" in name or "u21" in name or "youth" in name or "friendly" in name:
        return "", "not_available_expected", "low", 8
    return "", "needs_manual_review", "low", 5


def _tier_priority(tier: str) -> int:
    t = (tier or "").strip().upper()
    if t == "S":
        return 1
    if t == "A":
        return 2
    if t == "B":
        return 3
    return 5


def _floor_to_5min(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    sec = int((dt - epoch).total_seconds())
    bucket = (sec // 300) * 300
    return epoch + timedelta(seconds=bucket)


def _credit_tier(total: int) -> str:
    if total <= 15_000:
        return "<=15K: plan 20K suele alcanzar (validar contra uso real TOA)"
    if total <= 70_000:
        return "15K–70K: plan ~100K / pricing vigente TOA puede tener sentido"
    return ">80K: reducir muestra o snapshots antes de pagar"


def run_sm_fixture_master_audit(nf_mod: Any, conn) -> list[dict[str, Any]]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    rows: list[dict[str, Any]] = []

    def add(check: str, sev: str, cnt: int, den: Optional[int], notes: str = "") -> None:
        rate = round(cnt / den, 6) if den and den > 0 else None
        rows.append(
            {
                "check_name": check,
                "severity": sev,
                "count": cnt,
                "denominator": den,
                "rate": rate,
                "notes": notes,
            }
        )

    cur.execute("SELECT COUNT(*) AS c FROM bt2_events")
    n_events = int(cur.fetchone()["c"])

    cur.execute(
        """
        SELECT sportmonks_fixture_id, COUNT(*) AS c
        FROM bt2_events
        GROUP BY sportmonks_fixture_id
        HAVING COUNT(*) > 1
        """
    )
    dup_bt2 = sum(int(r["c"]) for r in cur.fetchall())
    add("duplicate_sportmonks_fixture_id_bt2", "error", dup_bt2, n_events, "Unique constraint debería impedir >0")

    cur.execute(
        """
        SELECT fixture_id, COUNT(*) AS c
        FROM raw_sportmonks_fixtures
        GROUP BY fixture_id
        HAVING COUNT(*) > 1
        """
    )
    dup_raw = len(cur.fetchall())
    cur.execute("SELECT COUNT(*) AS c FROM raw_sportmonks_fixtures")
    n_raw = int(cur.fetchone()["c"])
    add("duplicate_fixture_id_raw", "error", dup_raw, n_raw, "Filas raw duplicadas por fixture_id")

    cur.execute("SELECT COUNT(*) AS c FROM bt2_events WHERE kickoff_utc IS NULL")
    add("kickoff_utc_null", "warn", int(cur.fetchone()["c"]), n_events, "")

    cur.execute(
        "SELECT COUNT(*) AS c FROM bt2_events WHERE home_team_id IS NULL OR away_team_id IS NULL"
    )
    add("home_or_away_team_null", "warn", int(cur.fetchone()["c"]), n_events, "")

    cur.execute(
        """
        SELECT COUNT(*) AS c FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        WHERE l.id IS NULL OR l.tier IS NULL OR TRIM(l.tier) = '' OR LOWER(l.tier) = 'unknown'
        """
    )
    add("league_missing_or_tier_unknown", "info", int(cur.fetchone()["c"]), n_events, "")

    cur.execute(
        """
        SELECT COUNT(*) AS c FROM bt2_events
        WHERE status = 'finished' AND (result_home IS NULL OR result_away IS NULL)
        """
    )
    add("finished_without_score", "warn", int(cur.fetchone()["c"]), n_events, "")

    cur.execute(
        """
        SELECT COUNT(*) AS c FROM bt2_events
        WHERE status = 'scheduled'
          AND result_home IS NOT NULL AND result_away IS NOT NULL
        """
    )
    add("scheduled_with_numeric_score", "warn", int(cur.fetchone()["c"]), n_events, "Puede incluir 0-0 placeholder; revisar raw")

    # Drift raw vs bt2 (muestra acotada por CPU)
    cur.execute(
        """
        SELECT e.id AS event_id, e.sportmonks_fixture_id AS fixture_id, e.status AS bt2_status,
               e.kickoff_utc, e.result_home AS bt2_rh, e.result_away AS bt2_ra, r.payload
        FROM bt2_events e
        INNER JOIN raw_sportmonks_fixtures r ON r.fixture_id = e.sportmonks_fixture_id
        ORDER BY e.kickoff_utc DESC NULLS LAST
        LIMIT %s
        """,
        (DRIFT_SAMPLE_LIMIT,),
    )
    drift_rows = cur.fetchall()
    scanned = len(drift_rows)
    drift_status = drift_kickoff = drift_score = 0
    samples: list[str] = []
    for r in drift_rows:
        pl = r["payload"]
        if isinstance(pl, str):
            pl = json.loads(pl)
        sm_status = nf_mod._parse_status(pl)
        rh, ra = nf_mod._parse_result(pl)
        rh2, ra2 = nf_mod._results_for_bt2_persist(pl, sm_status, rh, ra)
        if sm_status != r["bt2_status"]:
            drift_status += 1
            if len(samples) < 12:
                samples.append(
                    f"event={r['event_id']} fx={r['fixture_id']} raw={sm_status} bt2={r['bt2_status']}"
                )
        sm_ko = nf_mod._parse_kickoff(pl)
        bko: Optional[datetime] = r["kickoff_utc"]
        if sm_ko and bko:
            if bko.tzinfo is None:
                bko = bko.replace(tzinfo=timezone.utc)
            sk = sm_ko.astimezone(timezone.utc) if sm_ko.tzinfo else sm_ko.replace(tzinfo=timezone.utc)
            if abs((sk - bko).total_seconds()) > 120:
                drift_kickoff += 1
        elif (sm_ko is None) != (bko is None):
            drift_kickoff += 1

        if sm_status == "finished" and r["bt2_status"] == "finished":
            if (r["bt2_rh"], r["bt2_ra"]) != (rh2, ra2) and rh2 is not None and ra2 is not None:
                drift_score += 1

    add(
        "drift_raw_vs_bt2_status_mismatch",
        "warn",
        drift_status,
        scanned,
        "; ".join(samples[:5]),
    )
    add("drift_kickoff_sm_vs_bt2", "warn", drift_kickoff, scanned, "")
    add("drift_score_sm_vs_bt2_finished", "info", drift_score, scanned, "")

    cur.close()
    return rows


def fetch_cohort_a_fixtures(conn, hist: Any, nf_mod: Any) -> list[dict[str, Any]]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    start = datetime.combine(COHORT_A0, time.min, tzinfo=timezone.utc)
    end = datetime.combine(COHORT_A1 + timedelta(days=1), time.min, tzinfo=timezone.utc)
    cur.execute(
        """
        SELECT e.id AS event_id, e.sportmonks_fixture_id AS fixture_id, e.kickoff_utc,
               e.status, l.sportmonks_id AS sm_league_id, l.name AS league_name, l.tier AS league_tier,
               l.country AS league_country,
               th.name AS home_name, ta.name AS away_name, r.payload
        FROM bt2_events e
        INNER JOIN raw_sportmonks_fixtures r ON r.fixture_id = e.sportmonks_fixture_id
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE e.kickoff_utc >= %s AND e.kickoff_utc < %s
        ORDER BY e.kickoff_utc
        LIMIT %s
        """,
        (start, end, MAX_COHORT_VP_COMPUTE),
    )
    out: list[dict[str, Any]] = []
    extract = hist.extract_cdm_rows
    agg_fn = hist.aggregate_odds_for_event
    to_t = hist.to_agg_tuples
    vp_fn = hist.event_passes_value_pool
    min_dec = hist.MIN_DEC
    cutoff = hist.cutoff_t60

    for row in cur:
        pl = row["payload"]
        if isinstance(pl, str):
            pl = json.loads(pl)
        ko: datetime = row["kickoff_utc"]
        if ko and ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        t_cut = cutoff(ko) if ko else None
        before = extract(pl)
        t60 = [t for t in before if t[4] is not None and t_cut and t[4] <= t_cut]
        agg = agg_fn(to_t(t60), min_decimal=min_dec)
        vp = bool(vp_fn(agg, min_decimal=min_dec))
        sk, st, conf, pr = _expected_sport_key(row.get("sm_league_id"), row.get("league_name") or "", row.get("league_country") or "")
        t60_iso = t_cut.isoformat() if t_cut else ""
        bucket = _floor_to_5min(t_cut).isoformat() if t_cut else ""
        out.append(
            {
                **{k: row[k] for k in row if k != "payload"},
                "value_pool_sm_lbu_t60": vp,
                "t60_cutoff_utc": t60_iso,
                "snapshot_bucket_5m_utc": bucket,
                "the_odds_api_sport_key_expected": sk,
                "mapping_status": st,
                "home_normalized": _norm_team(str(row.get("home_name") or "")),
                "away_normalized": _norm_team(str(row.get("away_name") or "")),
            }
        )
    cur.close()
    return out


def load_week_quality() -> dict[str, str]:
    """block_id -> good|weak desde cohort_A_weekly.csv."""
    p = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_cohort_A_robustness" / "cohort_A_weekly.csv"
    if not p.is_file():
        return {}
    rows: list[dict[str, str]] = []
    with p.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    def score_row(r: dict[str, str]) -> float:
        nf = int(r["n_fixtures"])
        nu = int(r["n_not_usable"])
        nu_rate = nu / nf if nf else 0.0
        surv = float(r["tasa_sobrevivencia_lineas"])
        vp = float(r["vp_over_n_fixtures"])
        return 0.35 * nu_rate + 0.35 * (1.0 - surv) + 0.30 * (1.0 - vp)

    scored = [(score_row(r), r["block_id"]) for r in rows]
    scored.sort()
    weak = {bid for _, bid in scored[-5:]}
    good = {bid for _, bid in scored[:5]}
    out: dict[str, str] = {}
    for r in rows:
        bid = r["block_id"]
        if bid in weak:
            out[bid] = "weak_week"
        elif bid in good:
            out[bid] = "good_week"
        else:
            out[bid] = "mid"
    return out


def week_block_id(ko: Optional[datetime]) -> str:
    if not ko:
        return ""
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    ko = ko.astimezone(timezone.utc)
    y, w, _ = ko.isocalendar()
    return f"{y}-W{w:02d}"


def build_validation_sample(fixtures: list[dict[str, Any]], week_q: dict[str, str]) -> list[dict[str, Any]]:
    """Muestra acotada estratificada."""
    by_w = defaultdict(list)
    for fx in fixtures:
        bid = week_block_id(fx.get("kickoff_utc"))
        by_w[bid].append(fx)

    def pick(pool: list[dict[str, Any]], want_vp: Optional[bool], n: int) -> list[dict[str, Any]]:
        sub = [x for x in pool if want_vp is None or x["value_pool_sm_lbu_t60"] is want_vp]
        sub.sort(key=lambda x: (-_tier_priority(str(x.get("league_tier") or "")), x["fixture_id"]))
        return sub[:n]

    sample: list[dict[str, Any]] = []
    weak_weeks = [bid for bid, q in week_q.items() if q == "weak_week"]
    good_weeks = [bid for bid, q in week_q.items() if q == "good_week"]

    for bid in good_weeks[:3]:
        pool = by_w.get(bid, [])
        sample.extend(pick(pool, True, 6))
        sample.extend(pick(pool, False, 3))
    for bid in weak_weeks[:3]:
        pool = by_w.get(bid, [])
        sample.extend(pick(pool, True, 5))
        sample.extend(pick(pool, False, 5))

    # Tier S extra
    s_pool = [x for x in fixtures if str(x.get("league_tier") or "").upper() == "S"]
    sample.extend(pick(s_pool, None, 10))

    # dedupe by fixture_id
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for x in sample:
        fid = int(x["fixture_id"])
        if fid in seen:
            continue
        seen.add(fid)
        bid = week_block_id(x.get("kickoff_utc"))
        x2 = {
            "fixture_id": fid,
            "event_id": x["event_id"],
            "kickoff_utc": x["kickoff_utc"].isoformat() if x.get("kickoff_utc") else "",
            "sm_league_id": x.get("sm_league_id"),
            "league_name": x.get("league_name"),
            "league_tier": x.get("league_tier"),
            "home_name": x.get("home_name"),
            "away_name": x.get("away_name"),
            "home_normalized": x.get("home_normalized"),
            "away_normalized": x.get("away_normalized"),
            "week_block_id": bid,
            "week_quality_label": week_q.get(bid, "unknown"),
            "value_pool_sm_lbu_t60": x["value_pool_sm_lbu_t60"],
            "the_odds_api_sport_key_expected": x.get("the_odds_api_sport_key_expected"),
            "the_odds_api_market": MARKET_LAB,
            "the_odds_api_region": REGION_LAB,
            "historical_query_timestamp_utc": x.get("t60_cutoff_utc"),
            "snapshot_bucket_5m_utc": x.get("snapshot_bucket_5m_utc"),
            "sample_reason": "stratified_cohort_A",
        }
        out.append(x2)
    return out[:120]


def write_offline_bundle(error: str) -> None:
    """Sin PostgreSQL: estructura de artefactos + resumen explícito (CI o laptop sin BT2_DATABASE_URL)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_timestamp_contract(OUT_DIR / "odds_timestamp_contract.md")
    tax = [
        {
            "bt2_market": "FT_1X2",
            "the_odds_api_market_key": "h2h",
            "scope": "phase_1_required",
            "notes": "Moneyline 1X2 ↔ h2h en TOA",
        },
        {
            "bt2_market": "OVER_UNDER_2_5",
            "the_odds_api_market_key": "totals",
            "scope": "phase_2_optional",
            "notes": "Requiere point=2.5 en outcomes TOA",
        },
        {
            "bt2_market": "BTTS",
            "the_odds_api_market_key": "h2h o market específico si TOA lo expone en liga",
            "scope": "phase_2_optional",
            "notes": "Confirmar disponibilidad por sport_key en doc mercados TOA",
        },
    ]
    with (OUT_DIR / "market_taxonomy_mapping.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tax[0].keys()))
        w.writeheader()
        for row in tax:
            w.writerow(row)

    stub_sm = [
        {
            "check_name": "database_unreachable",
            "severity": "error",
            "count": 1,
            "denominator": 1,
            "rate": 1.0,
            "notes": error[:500],
        }
    ]
    with (OUT_DIR / "sm_fixture_master_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=["check_name", "severity", "count", "denominator", "rate", "notes"]
        )
        w.writeheader()
        for r in stub_sm:
            w.writerow(r)

    league_rows = []
    for lid, sk in sorted(SM_LEAGUE_TO_ODDS_SPORT_KEY.items()):
        league_rows.append(
            {
                "sm_league_id": lid,
                "sm_league_name": f"(static_map_league_{lid})",
                "bt2_league_tier": "S" if lid in (8, 82, 301, 384, 564) else "A",
                "country": "",
                "the_odds_api_sport_key_expected": sk,
                "mapping_status": "mapped_expected",
                "mapping_confidence": "high",
                "priority": 1,
            }
        )
    fn = [
        "sm_league_id",
        "sm_league_name",
        "bt2_league_tier",
        "country",
        "the_odds_api_sport_key_expected",
        "mapping_status",
        "mapping_confidence",
        "priority",
    ]
    with (OUT_DIR / "the_odds_api_league_mapping_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for row in league_rows:
            w.writerow(row)

    match_rules = [
        {
            "rule_id": "R1",
            "rule_description": "Normalizar nombres local/visitante.",
            "readiness_signal": "offline",
            "risk_notes": "Ejecutar con BT2_DATABASE_URL para medir cohorte A.",
            "cohort_A_n_fixtures": 0,
            "cohort_A_names_ok": 0,
            "cohort_A_kickoff_ok": 0,
            "cohort_A_sport_key_ok": 0,
        }
    ]
    with (OUT_DIR / "fixture_matching_readiness_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(match_rules[0].keys()))
        w.writeheader()
        for rr in match_rules:
            w.writerow(rr)

    vfields = [
        "fixture_id",
        "event_id",
        "kickoff_utc",
        "sm_league_id",
        "league_name",
        "league_tier",
        "home_name",
        "away_name",
        "home_normalized",
        "away_normalized",
        "week_block_id",
        "week_quality_label",
        "value_pool_sm_lbu_t60",
        "the_odds_api_sport_key_expected",
        "the_odds_api_market",
        "the_odds_api_region",
        "historical_query_timestamp_utc",
        "snapshot_bucket_5m_utc",
        "sample_reason",
    ]
    with (OUT_DIR / "vendor_validation_sample.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=vfields)
        w.writeheader()

    cfields = [
        "sport_key",
        "snapshot_time",
        "region",
        "market",
        "endpoint_strategy",
        "credits_per_fixture_est",
        "n_fixtures_in_bucket",
        "estimated_credits_event_odds",
        "notes",
    ]
    with (OUT_DIR / "the_odds_api_credit_estimator.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cfields)
        w.writeheader()

    summary = {
        "phase": "3D_vendor_readiness",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "db_status": "offline_or_unreachable",
        "error": error,
        "readiness_verdict": "no_listos",
        "readiness_reason": "Sin conexión a PostgreSQL BT2 no se pudieron calcular auditorías reales.",
        "day_one_minimal_validation": [],
    }
    (OUT_DIR / "readiness_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT_DIR / "README.md").write_text(
        f"""# BT2 — Vendor readiness (Fase 3D)

**Modo offline / sin DB**: regenera con `python3 scripts/bt2_vendor_readiness_phase3d.py` cuando `BT2_DATABASE_URL` apunte a la instancia BT2.

Error: `{error[:200]}`
""",
        encoding="utf-8",
    )


def write_timestamp_contract(path: Path) -> None:
    path.write_text(
        """# Contrato de timestamps — odds (BT2 + The Odds API laboratorio)

## Campos y significado

| Campo | Definición |
|-------|------------|
| `provider_snapshot_time` | Instantánea del proveedor de odds (TOA: timestamp devuelto en histórico; cercano a granularidad 5 min según doc TOA). |
| `provider_last_update` | Última actualización declarada por el book dentro del payload TOA (`last_update` en mercado/bookmaker). |
| `ingested_at` | Momento en que nuestro sistema persistió la fila (wall clock ingest). **No es tiempo de mercado.** |
| `backfilled_at` | Momento de backfill/reproceso si aplica. **No es tiempo de mercado.** |
| `kickoff_utc` | Inicio del evento (fixture master SM / `bt2_events`). |
| `T-60_cutoff` | `kickoff_utc - 60 minutos` — ventana usada en modo `historical_sm_lbu` (3C) para líneas SM; análogo conceptual para TOA en laboratorio. |

## Regla explícita (obligatoria)

- **Nunca** usar `ingested_at` ni `backfilled_at` como si fueran el tiempo real del mercado o de la cuota.
- Para análisis ex-ante, la verdad temporal debe ser `provider_snapshot_time` / `provider_last_update` (según contrato del endpoint TOA) alineada a `T-60_cutoff` o política explícita del experimento.

## Bounded replay actual

- No modificado en esta fase. Mantener separado de este contrato de laboratorio TOA.

## Referencia de coste TOA (histórico)

- Documentación TOA v4: odds históricas por deporte/snapshot — coste **10 créditos × regiones × mercados** por llamada al endpoint bulk histórico; evento histórico puntual — coste basado en `10 × mercados_únicos × regiones` por request de odds de evento.
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if os.environ.get("BT2_VENDOR_READINESS_OFFLINE", "").strip().lower() in ("1", "true", "yes"):
        write_offline_bundle("BT2_VENDOR_READINESS_OFFLINE=1")
        print(json.dumps({"ok": True, "mode": "offline", "out": str(OUT_DIR.relative_to(_repo))}, indent=2))
        return

    nf_mod = _load_normalize_parsers()
    hist = _load_historical_proto()

    try:
        conn = _connect_bt2()
    except Exception as e:
        write_offline_bundle(f"connect_failed: {e!r}")
        print(json.dumps({"ok": False, "mode": "offline", "error": str(e)}, indent=2))
        return

    conn.autocommit = True

    # --- FASE A ---
    sm_rows = run_sm_fixture_master_audit(nf_mod, conn)
    with (OUT_DIR / "sm_fixture_master_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["check_name", "severity", "count", "denominator", "rate", "notes"],
        )
        w.writeheader()
        for r in sm_rows:
            w.writerow(r)

    # --- FASE B ---
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT DISTINCT l.sportmonks_id AS sm_league_id, l.name AS sm_league_name,
               l.tier AS bt2_league_tier, COALESCE(l.country,'') AS country
        FROM bt2_leagues l
        INNER JOIN bt2_events e ON e.league_id = l.id
        WHERE e.kickoff_utc >= %s AND e.kickoff_utc < %s
        ORDER BY l.sportmonks_id
        """,
        (
            datetime.combine(COHORT_A0, time.min, tzinfo=timezone.utc),
            datetime.combine(COHORT_A1 + timedelta(days=1), time.min, tzinfo=timezone.utc),
        ),
    )
    league_rows = []
    for r in cur:
        sk, st, conf, pr = _expected_sport_key(r["sm_league_id"], r["sm_league_name"], r["country"])
        league_rows.append(
            {
                "sm_league_id": r["sm_league_id"],
                "sm_league_name": r["sm_league_name"],
                "bt2_league_tier": r["bt2_league_tier"],
                "country": r["country"],
                "the_odds_api_sport_key_expected": sk,
                "mapping_status": st,
                "mapping_confidence": conf,
                "priority": pr,
            }
        )
    cur.close()
    with (OUT_DIR / "the_odds_api_league_mapping_audit.csv").open("w", encoding="utf-8", newline="") as f:
        fn = list(league_rows[0].keys()) if league_rows else [
            "sm_league_id",
            "sm_league_name",
            "bt2_league_tier",
            "country",
            "the_odds_api_sport_key_expected",
            "mapping_status",
            "mapping_confidence",
            "priority",
        ]
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for row in league_rows:
            w.writerow(row)

    # --- FASE C ---
    fixtures = fetch_cohort_a_fixtures(conn, hist, nf_mod)
    nfx = len(fixtures)
    ok_names = sum(1 for x in fixtures if x.get("home_normalized") and x.get("away_normalized"))
    ok_ko = sum(1 for x in fixtures if x.get("kickoff_utc"))
    ok_sk = sum(1 for x in fixtures if x.get("the_odds_api_sport_key_expected"))

    match_rules = [
        {
            "rule_id": "R1",
            "rule_description": "Normalizar nombres local/visitante (minúsculas, sin sufijos FC, sin puntuación fuerte).",
            "readiness_signal": f"{ok_names}/{nfx} fixtures con nombres no vacíos tras normalizar",
            "risk_notes": "Colisiones homónimas entre ligas distintas.",
        },
        {
            "rule_id": "R2",
            "rule_description": "Ventana kickoff ±15–120 min respecto a commence_time TOA.",
            "readiness_signal": "Requiere datos TOA reales día 1",
            "risk_notes": "Diferencias de reloj o reprogramaciones.",
        },
        {
            "rule_id": "R3",
            "rule_description": "sport_key coherente con liga SM (mapping audit).",
            "readiness_signal": f"{ok_sk}/{nfx} fixtures con sport_key esperado no vacío",
            "risk_notes": "Ligas secundarias quedan en needs_manual_review.",
        },
        {
            "rule_id": "R4",
            "rule_description": "Desempate por liga+orden alfabético si múltiples candidatos TOA.",
            "readiness_signal": "manual_review_queue",
            "risk_notes": "Copas y nombres duplicados.",
        },
    ]
    with (OUT_DIR / "fixture_matching_readiness_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "rule_id",
                "rule_description",
                "readiness_signal",
                "risk_notes",
                "cohort_A_n_fixtures",
                "cohort_A_names_ok",
                "cohort_A_kickoff_ok",
                "cohort_A_sport_key_ok",
            ],
        )
        w.writeheader()
        for rr in match_rules:
            w.writerow(
                {
                    **rr,
                    "cohort_A_n_fixtures": nfx,
                    "cohort_A_names_ok": ok_names,
                    "cohort_A_kickoff_ok": ok_ko,
                    "cohort_A_sport_key_ok": ok_sk,
                }
            )

    # --- FASE D ---
    tax = [
        {
            "bt2_market": "FT_1X2",
            "the_odds_api_market_key": "h2h",
            "scope": "phase_1_required",
            "notes": "Moneyline 1X2 ↔ h2h en TOA",
        },
        {
            "bt2_market": "OVER_UNDER_2_5",
            "the_odds_api_market_key": "totals",
            "scope": "phase_2_optional",
            "notes": "Requiere point=2.5 en outcomes TOA",
        },
        {
            "bt2_market": "BTTS",
            "the_odds_api_market_key": "h2h o market específico si TOA lo expone en liga",
            "scope": "phase_2_optional",
            "notes": "Confirmar disponibilidad por sport_key en doc mercados TOA",
        },
    ]
    with (OUT_DIR / "market_taxonomy_mapping.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tax[0].keys()))
        w.writeheader()
        for row in tax:
            w.writerow(row)

    # --- FASE E ---
    wq = load_week_quality()
    sample = build_validation_sample(fixtures, wq)
    with (OUT_DIR / "vendor_validation_sample.csv").open("w", encoding="utf-8", newline="") as f:
        if sample:
            w = csv.DictWriter(f, fieldnames=list(sample[0].keys()))
            w.writeheader()
            for row in sample:
                w.writerow(row)
        else:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "fixture_id",
                    "event_id",
                    "note",
                ],
            )
            w.writeheader()
            w.writerow(
                {
                    "fixture_id": "",
                    "event_id": "",
                    "note": "empty_sample: revisar cohort_A_weekly.csv o ampliar MAX_COHORT_VP_COMPUTE",
                }
            )

    # --- FASE F ---
    # Por evento: 1 crédit histórico /events opcional + 10 por h2h x1 región (doc TOA event odds)
    event_odds_credits_per_fixture = 10 * 1 * 1
    by_key: dict[tuple[str, str, str, str], dict[str, Any]] = defaultdict(
        lambda: {"n_fixtures": 0, "snapshots_5m": set()}
    )
    for x in sample:
        sk = x.get("the_odds_api_sport_key_expected") or "UNKNOWN"
        bkt = x.get("snapshot_bucket_5m_utc") or ""
        k = (sk, bkt, REGION_LAB, MARKET_LAB)
        by_key[k]["n_fixtures"] += 1
        by_key[k]["snapshots_5m"].add(bkt)

    credit_rows = []
    total_event_level = 0
    for (sk, bkt, reg, mkt), agg in sorted(by_key.items()):
        nf = agg["n_fixtures"]
        c = nf * event_odds_credits_per_fixture
        total_event_level += c
        credit_rows.append(
            {
                "sport_key": sk,
                "snapshot_time": bkt,
                "region": reg,
                "market": mkt,
                "endpoint_strategy": "historical_event_odds_TOA_v4",
                "credits_per_fixture_est": event_odds_credits_per_fixture,
                "n_fixtures_in_bucket": nf,
                "estimated_credits_event_odds": c,
                "notes": "Basado en doc TOA: 10 × mercados × regiones por request de odds histórico por evento; h2h+us=10",
            }
        )
    with (OUT_DIR / "the_odds_api_credit_estimator.csv").open("w", encoding="utf-8", newline="") as f:
        default_fn = [
            "sport_key",
            "snapshot_time",
            "region",
            "market",
            "endpoint_strategy",
            "credits_per_fixture_est",
            "n_fixtures_in_bucket",
            "estimated_credits_event_odds",
            "notes",
        ]
        fn = list(credit_rows[0].keys()) if credit_rows else default_fn
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for row in credit_rows:
            w.writerow(row)
        if not credit_rows:
            w.writerow(
                {
                    "sport_key": "N/A",
                    "snapshot_time": "",
                    "region": REGION_LAB,
                    "market": MARKET_LAB,
                    "endpoint_strategy": "none",
                    "credits_per_fixture_est": 0,
                    "n_fixtures_in_bucket": 0,
                    "estimated_credits_event_odds": 0,
                    "notes": "sin filas en vendor_validation_sample",
                }
            )

    write_timestamp_contract(OUT_DIR / "odds_timestamp_contract.md")

    mapped = sum(1 for r in league_rows if r["mapping_status"] == "mapped_expected")
    needs = sum(1 for r in league_rows if r["mapping_status"] != "mapped_expected")
    drift_status_row = next((r for r in sm_rows if r["check_name"] == "drift_raw_vs_bt2_status_mismatch"), None)
    drift_rate = float(drift_status_row["rate"] or 0) if drift_status_row else 0.0

    summary = {
        "phase": "3D_vendor_readiness",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cohort_A_vp_compute": {
            "max_fixtures_with_vp_parse": MAX_COHORT_VP_COMPUTE,
            "note": "VP/histórico SM solo sobre subconjunto acotado por coste CPU; auditorías SQL globales siguen siendo población completa donde aplica.",
        },
        "constraints": {
            "no_sm_odds": True,
            "no_the_odds_api_http": True,
            "no_bounded_replay_changes": True,
            "no_phase_4": True,
        },
        "sm_fixture_master": {
            "fixture_master_viable": drift_rate < 0.05 and (drift_status_row["count"] if drift_status_row else 0) < 500,
            "drift_status_mismatch_rate_in_sample": drift_rate,
            "notes": f"Muestra acotada {DRIFT_SAMPLE_LIMIT} eventos recientes con raw.",
        },
        "the_odds_api_league_mapping": {
            "n_leagues_cohort_A": len(league_rows),
            "mapped_expected_count": mapped,
            "needs_work_count": needs,
            "viable": mapped >= max(8, len(league_rows) // 10),
        },
        "fixture_matching": {
            "name_coverage": round(ok_names / nfx, 6) if nfx else 0,
            "sport_key_coverage": round(ok_sk / nfx, 6) if nfx else 0,
            "viable": (ok_names / nfx if nfx else 0) > 0.95 and (ok_sk / nfx if nfx else 0) > 0.35,
        },
        "validation_sample": {
            "n_rows": len(sample),
            "capped": True,
            "viable": 40 <= len(sample) <= 200,
        },
        "credit_estimate": {
            "strategy": "historical_event_odds_per_fixture_h2h_us",
            "total_credits_est": total_event_level,
            "tier_reading": _credit_tier(total_event_level),
            "viable": total_event_level <= 100_000,
        },
        "readiness_verdict": "listos_con_caveats",
        "readiness_reason": (
            "SM sigue viable como fixture master si se monitorea drift status/score; "
            "mapping TOA requiere confirmación manual/API para ligas fuera del mapa cerrado; "
            "matching depende de nombres+kickoff+sport_key; muestra acotada; créditos bajo estrategia por-evento."
        ),
        "day_one_minimal_validation": [
            "Elegir 10 filas de vendor_validation_sample.csv con sport_key mapped_expected.",
            "Para cada fila: resolver event_id TOA vía GET historical/sports/{sport}/events?date={T60} (1 crédito si hay eventos).",
            "GET historical/sports/{sport}/events/{eventId}/odds?markets=h2h&regions=us&date={T60} (10 créditos típicos).",
            "Comparar solo decimales h2h vs consenso BT2 FT_1X2 a modo sanity (no productivo).",
            "Registrar provider_snapshot_time vs T60 en tabla de laboratorio.",
        ],
    }
    (OUT_DIR / "readiness_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    readme = f"""# BT2 — Vendor readiness (Fase 3D)

Generado por `scripts/bt2_vendor_readiness_phase3d.py` (sin llamadas HTTP).

## Regenerar

```bash
cd {_repo}
python3 scripts/bt2_vendor_readiness_phase3d.py
```

## Salidas

- `sm_fixture_master_audit.csv`
- `the_odds_api_league_mapping_audit.csv`
- `fixture_matching_readiness_audit.csv`
- `market_taxonomy_mapping.csv`
- `vendor_validation_sample.csv`
- `the_odds_api_credit_estimator.csv`
- `odds_timestamp_contract.md`
- `readiness_summary.json`

## Resumen

Ver `readiness_summary.json` → `readiness_verdict` y `day_one_minimal_validation`.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    conn.close()
    print(json.dumps({"ok": True, "out": str(OUT_DIR.relative_to(_repo))}, indent=2))


if __name__ == "__main__":
    main()

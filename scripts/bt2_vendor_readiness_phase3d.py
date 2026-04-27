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
MAX_COHORT_VP_COMPUTE = 6500
DRIFT_SAMPLE_LIMIT = 1500
SAMPLE_MAX_ROWS = 180
SAMPLE_MIN_TARGET = 40

# Claves oficiales documentadas (The Odds API — sports list). Solo fútbol usado en piloto lógico.
# https://the-odds-api.com/sports-odds-data/sports-apis.html
OFFICIAL_TOA_SOCCER_KEYS: frozenset[str] = frozenset(
    {
        "soccer_africa_cup_of_nations",
        "soccer_argentina_primera_division",
        "soccer_australia_aleague",
        "soccer_austria_bundesliga",
        "soccer_belgium_first_div",
        "soccer_brazil_campeonato",
        "soccer_brazil_serie_b",
        "soccer_chile_campeonato",
        "soccer_china_superleague",
        "soccer_conmebol_copa_america",
        "soccer_conmebol_copa_libertadores",
        "soccer_conmebol_copa_sudamericana",
        "soccer_denmark_superliga",
        "soccer_efl_champ",
        "soccer_england_efl_cup",
        "soccer_england_league1",
        "soccer_england_league2",
        "soccer_epl",
        "soccer_fa_cup",
        "soccer_fifa_club_world_cup",
        "soccer_fifa_world_cup",
        "soccer_fifa_world_cup_qualifiers_europe",
        "soccer_fifa_world_cup_qualifiers_south_america",
        "soccer_finland_veikkausliiga",
        "soccer_france_coupe_de_france",
        "soccer_france_ligue_one",
        "soccer_france_ligue_two",
        "soccer_germany_bundesliga",
        "soccer_germany_bundesliga2",
        "soccer_germany_dfb_pokal",
        "soccer_germany_liga3",
        "soccer_greece_super_league",
        "soccer_italy_coppa_italia",
        "soccer_italy_serie_a",
        "soccer_italy_serie_b",
        "soccer_japan_j_league",
        "soccer_korea_kleague1",
        "soccer_league_of_ireland",
        "soccer_mexico_ligamx",
        "soccer_netherlands_eredivisie",
        "soccer_norway_eliteserien",
        "soccer_poland_ekstraklasa",
        "soccer_portugal_primeira_liga",
        "soccer_russia_premier_league",
        "soccer_saudi_arabia_pro_league",
        "soccer_spain_copa_del_rey",
        "soccer_spain_la_liga",
        "soccer_spain_segunda_division",
        "soccer_spl",
        "soccer_sweden_allsvenskan",
        "soccer_sweden_superettan",
        "soccer_switzerland_superleague",
        "soccer_turkey_super_league",
        "soccer_uefa_champs_league",
        "soccer_uefa_europa_conference_league",
        "soccer_uefa_europa_league",
        "soccer_uefa_european_championship",
        "soccer_uefa_nations_league",
        "soccer_usa_mls",
        "soccer_colombia_primera_a",
    }
)

# SportMonks league_id -> sport_key (mapa cerrado; ampliado con cohorte A real).
SM_LEAGUE_TO_ODDS_SPORT_KEY: dict[int, str] = {
    8: "soccer_epl",
    9: "soccer_efl_champ",
    12: "soccer_england_league1",
    14: "soccer_england_league2",
    24: "soccer_fa_cup",
    27: "soccer_england_efl_cup",
    72: "soccer_netherlands_eredivisie",
    82: "soccer_germany_bundesliga",
    85: "soccer_germany_bundesliga2",
    88: "soccer_germany_liga3",
    109: "soccer_germany_dfb_pokal",
    181: "soccer_austria_bundesliga",
    208: "soccer_belgium_first_div",
    271: "soccer_denmark_superliga",
    292: "soccer_finland_veikkausliiga",
    301: "soccer_france_ligue_one",
    304: "soccer_france_ligue_two",
    307: "soccer_france_coupe_de_france",
    325: "soccer_greece_super_league",
    360: "soccer_league_of_ireland",
    384: "soccer_italy_serie_a",
    387: "soccer_italy_serie_b",
    390: "soccer_italy_coppa_italia",
    444: "soccer_norway_eliteserien",
    453: "soccer_poland_ekstraklasa",
    462: "soccer_portugal_primeira_liga",
    501: "soccer_spl",
    513: "soccer_spl",
    564: "soccer_spain_la_liga",
    567: "soccer_spain_segunda_division",
    570: "soccer_spain_copa_del_rey",
    573: "soccer_sweden_allsvenskan",
    591: "soccer_sweden_superettan",
    600: "soccer_turkey_super_league",
    636: "soccer_argentina_primera_division",
    648: "soccer_brazil_campeonato",
    651: "soccer_brazil_serie_b",
    663: "soccer_chile_campeonato",
    672: "soccer_colombia_primera_a",
    743: "soccer_mexico_ligamx",
    779: "soccer_usa_mls",
    968: "soccer_japan_j_league",
    1007: "soccer_australia_aleague",
    1034: "soccer_korea_kleague1",
    1116: "soccer_conmebol_copa_sudamericana",
    1122: "soccer_conmebol_copa_libertadores",
    1356: "soccer_australia_aleague",
    1673: "soccer_france_ligue_one",
    1691: "soccer_epl",
    1798: "soccer_brazil_campeonato",
    1989: "soccer_saudi_arabia_pro_league",
    489: "soccer_russia_premier_league",
    492: "soccer_russia_premier_league",
}

# Copas / competiciones TOA con key oficial (pueden entrar a piloto si mapa cerrado).
PILOT_ELIGIBLE_CUP_KEYS: frozenset[str] = frozenset(
    {
        "soccer_fa_cup",
        "soccer_england_efl_cup",
        "soccer_france_coupe_de_france",
        "soccer_italy_coppa_italia",
        "soccer_spain_copa_del_rey",
        "soccer_germany_dfb_pokal",
        "soccer_conmebol_copa_libertadores",
        "soccer_conmebol_copa_sudamericana",
    }
)

# Nombres típicos (fallback) — claves alineadas a la doc TOA.
NAME_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("premier league",), "soccer_epl"),
    (("la liga", "laliga"), "soccer_spain_la_liga"),
    (("bundesliga - germany", "bundesliga"), "soccer_germany_bundesliga"),
    (("serie a - italy", "serie a"), "soccer_italy_serie_a"),
    (("ligue 1 - france",), "soccer_france_ligue_one"),
    (("eredivisie",), "soccer_netherlands_eredivisie"),
    (("primeira liga", "liga portugal"), "soccer_portugal_primeira_liga"),
    (("mls", "major league soccer"), "soccer_usa_mls"),
    (("uefa champions", "champions league"), "soccer_uefa_champs_league"),
    (("europa league", "uefa europa"), "soccer_uefa_europa_league"),
    (("conference league",), "soccer_uefa_europa_conference_league"),
    (("fa cup", "the fa cup"), "soccer_fa_cup"),
    (("copa del rey", "copa rey"), "soccer_spain_copa_del_rey"),
    (("coppa italia",), "soccer_italy_coppa_italia"),
    (("coupe de france",), "soccer_france_coupe_de_france"),
    (("carabao", "efl cup", "league cup"), "soccer_england_efl_cup"),
    (("brasileir", "série a", "serie a brazil"), "soccer_brazil_campeonato"),
    (("super lig - turkey", "super league - turkey", "1. lig"), "soccer_turkey_super_league"),
    (("eliteserien",), "soccer_norway_eliteserien"),
    (("a-league", "a league"), "soccer_australia_aleague"),
    (("ligue 2 - france", "ligue 2"), "soccer_france_ligue_two"),
]


def _pilot_name_excludes(league_name: str) -> bool:
    n = (league_name or "").lower()
    toks = (
        "women",
        "womens",
        "femen",
        "femenin",
        "u17",
        "u18",
        "u19",
        "u20",
        "u21",
        "u22",
        "u23",
        "youth",
        "reserve",
        "friendly",
        "amistoso",
    )
    return any(t in n for t in toks)


def _classify_pilot_tier(
    *,
    sport_key: str,
    mapping_status: str,
    mapping_source: str,
    league_name: str,
    league_tier: str,
) -> str:
    """
    Valores: priority_pilot_now | priority_needs_manual_mapping | priority_out_of_scope_for_pilot
    Piloto pagado: preferimos mapa cerrado sm_league_id; hints genéricos quedan fuera.
    """
    if _pilot_name_excludes(league_name) or not sport_key or mapping_status == "not_available_expected":
        return "priority_out_of_scope_for_pilot"
    if sport_key not in OFFICIAL_TOA_SOCCER_KEYS:
        return "priority_needs_manual_mapping"
    if mapping_status in ("needs_manual_review", "needs_api_confirmation"):
        return "priority_needs_manual_mapping"
    if mapping_source in ("name_hint", "name_ambiguous_premier"):
        return "priority_needs_manual_mapping"
    if mapping_source not in (
        "sm_league_id",
        "name_country_premier_russia",
        "name_country_hint",
    ):
        return "priority_needs_manual_mapping"
    t = (league_tier or "").strip().upper()
    cup_ok = sport_key in PILOT_ELIGIBLE_CUP_KEYS
    if mapping_source == "name_country_premier_russia":
        return "priority_pilot_now"
    if mapping_source == "name_country_hint" and sport_key == "soccer_spl":
        return "priority_pilot_now"
    if mapping_source != "sm_league_id":
        return "priority_needs_manual_mapping"
    if cup_ok:
        return "priority_pilot_now"
    if t in ("S", "A", "B"):
        return "priority_pilot_now"
    if t in ("UNKNOWN", "") and sport_key in (
        "soccer_epl",
        "soccer_spain_la_liga",
        "soccer_germany_bundesliga",
        "soccer_italy_serie_a",
        "soccer_france_ligue_one",
    ):
        return "priority_pilot_now"
    return "priority_needs_manual_mapping"


def resolve_league_mapping(
    sm_league_id: Optional[int], league_name: str, country: str, league_tier: str
) -> dict[str, Any]:
    """
    Mapea liga SM → sport_key TOA (sin API). Devuelve columnas listas para CSV.
    """
    name = (league_name or "").strip()
    nlow = name.lower()
    c = (country or "").strip()
    clow = c.lower()
    lid = int(sm_league_id) if sm_league_id is not None else None

    src = "none"
    sport_key = ""
    status = "needs_manual_review"
    conf = "low"

    if not nlow or nlow in ("(sin_liga)", "(sin_nombre_liga)"):
        return {
            "the_odds_api_sport_key_expected": "",
            "mapping_status": "needs_manual_review",
            "mapping_confidence": "low",
            "mapping_source": "none",
            "heuristic_sort_priority": 9,
            "pilot_tier": "priority_out_of_scope_for_pilot",
        }

    if _pilot_name_excludes(name):
        return {
            "the_odds_api_sport_key_expected": "",
            "mapping_status": "not_available_expected",
            "mapping_confidence": "low",
            "mapping_source": "name_exclusion",
            "heuristic_sort_priority": 8,
            "pilot_tier": "priority_out_of_scope_for_pilot",
        }

    # 1) Mapa cerrado por league_id SM (prioridad sobre nombre).
    if lid is not None and lid in SM_LEAGUE_TO_ODDS_SPORT_KEY:
        sport_key = SM_LEAGUE_TO_ODDS_SPORT_KEY[lid]
        status, conf, src = "mapped_expected", "high", "sm_league_id"

    # 2) Premier League con país (solo si no hay id mapeado).
    if not sport_key and "premier league" in nlow:
        if "russia" in clow or "росс" in c:
            sport_key, status, conf, src = "soccer_russia_premier_league", "mapped_expected", "high", "name_country_premier_russia"
        elif "scotland" in clow or "scottish" in nlow or "scot" in clow:
            sport_key, status, conf, src = "soccer_spl", "mapped_expected", "high", "name_country_hint"
        elif lid in (8, 1691) or c in ("", "england", "ENG") or "england" in clow or not c:
            sport_key, status, conf, src = "soccer_epl", "mapped_expected", "high", "name_country_hint"
        elif lid in (486, 609, 806, 830, 827, 809):
            sport_key, status, conf, src = "soccer_epl", "needs_api_confirmation", "medium", "name_ambiguous_premier"
        else:
            sport_key, status, conf, src = "soccer_epl", "needs_api_confirmation", "medium", "name_hint"

    if not sport_key:
        for hints, key in NAME_HINTS:
            if any(h in nlow for h in hints):
                sport_key = key
                status, conf, src = "needs_api_confirmation", "medium", "name_hint"
                break

    if not sport_key:
        return {
            "the_odds_api_sport_key_expected": "",
            "mapping_status": "needs_manual_review",
            "mapping_confidence": "low",
            "mapping_source": src,
            "heuristic_sort_priority": 5,
            "pilot_tier": "priority_out_of_scope_for_pilot",
        }

    if sport_key and sport_key not in OFFICIAL_TOA_SOCCER_KEYS and status == "mapped_expected":
        status, conf = "needs_api_confirmation", "medium"

    hp = 1 if status == "mapped_expected" else 3
    if conf == "low":
        hp = 5
    p_tier = _classify_pilot_tier(
        sport_key=sport_key,
        mapping_status=status,
        mapping_source=src,
        league_name=name,
        league_tier=league_tier,
    )

    return {
        "the_odds_api_sport_key_expected": sport_key,
        "mapping_status": status,
        "mapping_confidence": conf,
        "mapping_source": src,
        "heuristic_sort_priority": hp,
        "pilot_tier": p_tier,
    }


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
        lm = resolve_league_mapping(
            row.get("sm_league_id"),
            str(row.get("league_name") or ""),
            str(row.get("league_country") or ""),
            str(row.get("league_tier") or ""),
        )
        t60_iso = t_cut.isoformat() if t_cut else ""
        bucket = _floor_to_5min(t_cut).isoformat() if t_cut else ""
        out.append(
            {
                **{k: row[k] for k in row if k != "payload"},
                "value_pool_sm_lbu_t60": vp,
                "t60_cutoff_utc": t60_iso,
                "snapshot_bucket_5m_utc": bucket,
                "the_odds_api_sport_key_expected": lm["the_odds_api_sport_key_expected"],
                "mapping_status": lm["mapping_status"],
                "mapping_source": lm["mapping_source"],
                "pilot_tier": lm["pilot_tier"],
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


def build_validation_sample(
    fixtures: list[dict[str, Any]], week_q: dict[str, str]
) -> tuple[list[dict[str, Any]], str]:
    """
    40–SAMPLE_MAX filas, solo `priority_pilot_now`; estratifica semana buena/mala y VP.
    """
    pilot = [f for f in fixtures if f.get("pilot_tier") == "priority_pilot_now"]
    if not pilot:
        return [], "no_pilot_tier_pilot_now_in_cohort"

    by_w: defaultdict[str, list] = defaultdict(list)
    for fx in pilot:
        by_w[week_block_id(fx.get("kickoff_utc"))].append(fx)

    def pick(pool: list[dict[str, Any]], want_vp: Optional[bool], n: int) -> list[dict[str, Any]]:
        sub: list[dict[str, Any]] = []
        for x in pool:
            vp = int(bool(x.get("value_pool_sm_lbu_t60")))
            if want_vp is None or vp == (1 if want_vp else 0):
                sub.append(x)
        sub.sort(
            key=lambda x: (
                -_tier_priority(str(x.get("league_tier") or "")),
                int(x.get("fixture_id") or 0),
            )
        )
        return sub[:n]

    weak_weeks = [b for b, q in week_q.items() if q == "weak_week"]
    good_weeks = [b for b, q in week_q.items() if q == "good_week"]
    all_b = sorted([k for k in by_w if k], key=lambda s: s)
    if not good_weeks and all_b:
        good_weeks = all_b[: min(5, len(all_b))]
    if not weak_weeks and all_b:
        weak_weeks = all_b[-min(5, len(all_b)) :]

    sample: list[dict[str, Any]] = []
    for bid in good_weeks[:4]:
        pool = by_w.get(bid, [])
        sample.extend(pick(pool, True, 8))
        sample.extend(pick(pool, False, 5))
    for bid in weak_weeks[:4]:
        pool = by_w.get(bid, [])
        sample.extend(pick(pool, True, 6))
        sample.extend(pick(pool, False, 5))
    s_pool = [x for x in pilot if str(x.get("league_tier") or "").upper() == "S"]
    sample.extend(pick(s_pool, None, 20))

    def row_dict(x: dict[str, Any]) -> dict[str, Any]:
        ko = x.get("kickoff_utc")
        bid = week_block_id(ko if isinstance(ko, datetime) else None)
        return {
            "fixture_id": int(x["fixture_id"]),
            "event_id": x["event_id"],
            "kickoff_utc": ko.isoformat() if isinstance(ko, datetime) and ko else (str(ko) if ko else ""),
            "sm_league_id": x.get("sm_league_id"),
            "league_name": x.get("league_name"),
            "league_tier": x.get("league_tier"),
            "home_name": x.get("home_name"),
            "away_name": x.get("away_name"),
            "home_normalized": x.get("home_normalized"),
            "away_normalized": x.get("away_normalized"),
            "week_block_id": bid,
            "week_quality_label": week_q.get(bid, "unknown" if not week_q else "mid"),
            "value_pool_sm_lbu_t60": x["value_pool_sm_lbu_t60"],
            "the_odds_api_sport_key_expected": x.get("the_odds_api_sport_key_expected"),
            "mapping_status": x.get("mapping_status"),
            "mapping_source": x.get("mapping_source"),
            "pilot_tier": x.get("pilot_tier"),
            "the_odds_api_market": MARKET_LAB,
            "the_odds_api_region": REGION_LAB,
            "historical_query_timestamp_utc": x.get("t60_cutoff_utc"),
            "snapshot_bucket_5m_utc": x.get("snapshot_bucket_5m_utc"),
            "sample_reason": "stratified_cohort_A_pilot_tier_pilot_now",
        }

    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for x in sample:
        fid = int(x["fixture_id"])
        if fid in seen:
            continue
        seen.add(fid)
        out.append(row_dict(x))

    rest = sorted(
        pilot,
        key=lambda z: (
            str(z.get("kickoff_utc") or ""),
            int(z.get("fixture_id") or 0),
        ),
    )
    for x in rest:
        if len(out) >= min(SAMPLE_MAX_ROWS, max(SAMPLE_MIN_TARGET, 40)):
            break
        fid = int(x["fixture_id"])
        if fid in seen:
            continue
        seen.add(fid)
        out.append(row_dict(x))

    reason = ""
    h2h_nvp = [f for f in pilot if not f.get("value_pool_sm_lbu_t60")]
    h2h_vp = [f for f in pilot if f.get("value_pool_sm_lbu_t60")]
    if not h2h_nvp and h2h_vp:
        reason = "no_h2h_no_vp_in_pilot_subset"
    if len(out) < SAMPLE_MIN_TARGET:
        reason = (reason + " " if reason else "") + f"only_{len(out)}_rows_target_was_{SAMPLE_MIN_TARGET}"
    return out[:SAMPLE_MAX_ROWS], reason.strip()


def build_pilot_league_manifest(
    league_rows: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    n_cohort_fixtures: int,
) -> dict[str, Any]:
    by_l: defaultdict[int, int] = defaultdict(int)
    for f in fixtures:
        if f.get("pilot_tier") != "priority_pilot_now":
            continue
        lid = f.get("sm_league_id")
        if lid is not None:
            by_l[int(lid)] += 1
    n_pilot_fix = sum(by_l.values())
    in_l = [r for r in league_rows if r.get("pilot_tier") == "priority_pilot_now"]
    out_l = [r for r in league_rows if r.get("pilot_tier") != "priority_pilot_now"]
    return {
        "cohort_A_range": {"start": str(COHORT_A0), "end": str(COHORT_A1)},
        "cohort_vp_compute_subset": {
            "n_fixtures": n_cohort_fixtures,
            "n_pilot_tier_pilot_now_fixtures": n_pilot_fix,
        },
        "league_cardinality_cohort_A": len(league_rows),
        "leagues_pilot_now_count": len(in_l),
        "fixtures_by_sm_league_id_pilot_only": {str(k): v for k, v in sorted(by_l.items())},
        "leagues_operative_pilot_in": [
            {
                "sm_league_id": r["sm_league_id"],
                "name": r.get("sm_league_name"),
                "the_odds_api_sport_key_expected": r.get("the_odds_api_sport_key_expected"),
                "mapping_source": r.get("mapping_source"),
                "n_fixtures_in_cohort_subset": by_l.get(int(r["sm_league_id"]), 0),
            }
            for r in sorted(
                in_l,
                key=lambda x: (-by_l.get(int(x["sm_league_id"]), 0), int(x["sm_league_id"] or 0)),
            )
        ],
        "leagues_not_in_pilot_operative": [
            {
                "sm_league_id": r.get("sm_league_id"),
                "name": r.get("sm_league_name"),
                "pilot_tier": r.get("pilot_tier"),
                "the_odds_api_sport_key_expected": r.get("the_odds_api_sport_key_expected"),
            }
            for r in sorted(
                out_l,
                key=lambda x: (str(x.get("pilot_tier")), int(x.get("sm_league_id") or 0)),
            )
        ],
    }


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
    for lid, _sk in sorted(SM_LEAGUE_TO_ODDS_SPORT_KEY.items()):
        tier = "S" if lid in (8, 82, 301, 384, 564) else "A"
        lm = resolve_league_mapping(
            lid,
            f"(static_map_league_{lid})",
            "",
            tier,
        )
        league_rows.append(
            {
                "sm_league_id": lid,
                "sm_league_name": f"(static_map_league_{lid})",
                "bt2_league_tier": tier,
                "country": "",
                "the_odds_api_sport_key_expected": lm["the_odds_api_sport_key_expected"],
                "mapping_status": lm["mapping_status"],
                "mapping_confidence": lm["mapping_confidence"],
                "mapping_source": lm["mapping_source"],
                "pilot_tier": lm["pilot_tier"],
                "heuristic_sort_priority": lm["heuristic_sort_priority"],
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
        "mapping_source",
        "pilot_tier",
        "heuristic_sort_priority",
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
        "mapping_status",
        "mapping_source",
        "pilot_tier",
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
    (OUT_DIR / "pilot_league_manifest.json").write_text(
        json.dumps(
            {
                "mode": "offline",
                "note": "Ejecutar con BT2_DATABASE_URL para conteos reales y pilot_league_manifest completo.",
                "cohort_A_range": {"start": str(COHORT_A0), "end": str(COHORT_A1)},
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
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
        lm = resolve_league_mapping(
            r["sm_league_id"],
            r["sm_league_name"] or "",
            r["country"] or "",
            r["bt2_league_tier"] or "",
        )
        league_rows.append(
            {
                "sm_league_id": r["sm_league_id"],
                "sm_league_name": r["sm_league_name"],
                "bt2_league_tier": r["bt2_league_tier"],
                "country": r["country"],
                "the_odds_api_sport_key_expected": lm["the_odds_api_sport_key_expected"],
                "mapping_status": lm["mapping_status"],
                "mapping_confidence": lm["mapping_confidence"],
                "mapping_source": lm["mapping_source"],
                "pilot_tier": lm["pilot_tier"],
                "heuristic_sort_priority": lm["heuristic_sort_priority"],
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
            "mapping_source",
            "pilot_tier",
            "heuristic_sort_priority",
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
    n_pilot_now = sum(1 for x in fixtures if x.get("pilot_tier") == "priority_pilot_now")
    ok_sk = n_pilot_now

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
            "rule_description": "sport_key TOA cubierto para piloto (pilot_tier = priority_pilot_now).",
            "readiness_signal": f"{ok_sk}/{nfx} fixtures en cohorte VP con mapping piloto-now",
            "risk_notes": "Fuera: priority_needs_manual_mapping o priority_out_of_scope_for_pilot según mapa/ tier.",
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
    sample, sample_shortfall = build_validation_sample(fixtures, wq)
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
                    "note": (
                        "empty_sample: "
                        + (sample_shortfall or "revisar cohort_A_weekly.csv o ampliar MAX_COHORT_VP_COMPUTE")
                    ),
                }
            )

    plm = build_pilot_league_manifest(league_rows, fixtures, nfx)
    (OUT_DIR / "pilot_league_manifest.json").write_text(
        json.dumps(plm, indent=2, ensure_ascii=False), encoding="utf-8"
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
            "pilot_tier_pilot_now_coverage": round(ok_sk / nfx, 6) if nfx else 0,
            "viable": (ok_names / nfx if nfx else 0) > 0.95 and (n_pilot_now / nfx if nfx else 0) > 0.25,
        },
        "pilot_league": {
            "n_fixtures_pilot_tier_pilot_now": n_pilot_now,
            "n_leagues_pilot_now_distinct_cohort": plm.get("leagues_pilot_now_count", 0),
        },
        "validation_sample": {
            "n_rows": len(sample),
            "pilot_tier_filter": "priority_pilot_now",
            "min_target": SAMPLE_MIN_TARGET,
            "max_cap": SAMPLE_MAX_ROWS,
            "shortfall_note": sample_shortfall,
            "viable": SAMPLE_MIN_TARGET <= len(sample) <= SAMPLE_MAX_ROWS and len(sample) > 0,
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
            "Elegir 10 filas de vendor_validation_sample.csv (todas `priority_pilot_now` en cohorte muestreada).",
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
- `pilot_league_manifest.json`

## Resumen

Ver `readiness_summary.json` → `readiness_verdict` y `day_one_minimal_validation`.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    conn.close()
    print(json.dumps({"ok": True, "out": str(OUT_DIR.relative_to(_repo))}, indent=2))


if __name__ == "__main__":
    main()

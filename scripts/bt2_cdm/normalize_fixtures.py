"""
Normalizador CDM — Sprint 03 US-BE-005
Lee raw_sportmonks_fixtures (JSONB) y hace upsert en las 4 tablas CDM:
  bt2_leagues → bt2_teams → bt2_events → bt2_odds_snapshot

Estructura real del payload Sportmonks:
  - participants: lista con meta.location="home"/"away"
  - scores: lista con description="CURRENT"/"1ST_HALF"/"2ND_HALF"
  - state_id: 5=Finished, 6=Postponed, 7=Cancelled
  - result_info: texto (no None) = partido terminado
  - odds[]: market_id=1 (Match Winner), market_id=80 (Goals Over/Under)
             cada entry tiene: label, value (decimal), bookmaker_id, total

Uso:
    python scripts/bt2_cdm/normalize_fixtures.py
    python scripts/bt2_cdm/normalize_fixtures.py --batch-size 500
    python scripts/bt2_cdm/normalize_fixtures.py --dry-run
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv
load_dotenv(Path(_repo_root) / ".env")

import os
import psycopg2
import psycopg2.extras

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger("cdm_normalize")

# ── Configuración de ligas excluidas ─────────────────────────────────────────

EXCLUDED_LEAGUE_IDS = {
    # Amistosos y friendlies
    1082, 1101, 2450, 2451, 2452, 2453,
    # Copa del Mundo Qualifiers
    723, 729,
    # Ligas femeninas
    45, 1419, 1583, 1631,
    # Youth leagues
    1329,
    # NASL (histórica, sin valor predictivo)
    788,
    # Ligas de reserva / B
    983,
}

EXCLUDED_NAME_KEYWORDS = (
    "friendly", "amistoso", "youth", "u18", "u21", "u23",
    "women", "femenin", "reserve", "reserva",
)

# Mapeo de league_id (sportmonks) a (tier, is_active)
TIER_MAP: dict[int, tuple[str, bool]] = {
    8: ("S", True),    # Premier League
    82: ("S", True),   # Bundesliga
    301: ("S", True),  # Ligue 1
    384: ("S", True),  # Serie A
    564: ("S", True),  # La Liga
    72: ("A", True),   # Eredivisie
    208: ("A", True),  # Pro League Bélgica
    453: ("A", True),  # Ekstraklasa
    462: ("A", True),  # Liga Portugal
    501: ("A", True),  # Premiership Escocia
    573: ("A", True),  # Allsvenskan
    600: ("A", True),  # Super Lig Turquía
    636: ("A", True),  # Liga Profesional Argentina
    648: ("A", True),  # Serie A Brasil
    663: ("A", True),  # Primera División Chile
    672: ("A", True),  # Liga BetPlay Colombia
    743: ("A", True),  # Liga MX
    779: ("A", True),  # MLS
    968: ("A", True),  # J1 League
    1034: ("A", True), # K League 1
    1122: ("A", True), # Copa Libertadores
    9: ("B", True),    # Championship
    85: ("B", True),   # 2. Bundesliga
    304: ("B", True),  # Ligue 2
    387: ("B", True),  # Serie B Italia
    567: ("B", True),  # La Liga 2
    1116: ("B", True), # Copa Sudamericana
}

# Markets que extraemos para bt2_odds_snapshot
MARKET_1X2 = 1
MARKET_OVER_UNDER = 80


def should_exclude_league(league_id: Optional[int], league_name: str) -> bool:
    if league_id in EXCLUDED_LEAGUE_IDS:
        return True
    name_lower = league_name.lower()
    return any(kw in name_lower for kw in EXCLUDED_NAME_KEYWORDS)


def _get_db_conn():
    url = os.getenv("BT2_DATABASE_URL", "")
    url_sync = url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url_sync)


# ── Parsers de payload ────────────────────────────────────────────────────────

def _parse_kickoff(payload: dict) -> Optional[datetime]:
    raw = payload.get("starting_at")
    if not raw:
        ts = payload.get("starting_at_timestamp")
        if ts:
            try:
                return datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except (ValueError, TypeError):
                return None
        return None
    if isinstance(raw, str):
        try:
            # Formato "YYYY-MM-DD HH:MM:SS" sin timezone → asumir UTC
            raw = raw.replace("Z", "+00:00")
            if "T" not in raw and "+" not in raw and raw.count(":") == 2:
                raw += "+00:00"
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
    return None


def _parse_status(payload: dict) -> str:
    # result_info no nulo → partido terminado
    if payload.get("result_info"):
        return "finished"
    state_id = payload.get("state_id")
    if state_id in (6, 10):   # Postponed
        return "cancelled"
    if state_id in (7, 9):    # Cancelled / Abandoned
        return "cancelled"
    return "scheduled"


def _parse_result(payload: dict) -> tuple:
    """Extrae result_home, result_away del array scores description=CURRENT."""
    scores = payload.get("scores") or []
    home_goals = away_goals = None
    for s in scores:
        if not isinstance(s, dict):
            continue
        if s.get("description") != "CURRENT":
            continue
        score_data = s.get("score") or {}
        participant = score_data.get("participant", "")
        goals = score_data.get("goals")
        if participant == "home":
            home_goals = goals
        elif participant == "away":
            away_goals = goals
    return home_goals, away_goals


def _parse_season(payload: dict) -> Optional[str]:
    """Calcula la temporada a partir de la fecha del partido (ej: 2023/24)."""
    starting_at = payload.get("starting_at")
    if not starting_at:
        return None
    try:
        year = int(str(starting_at)[:4])
        month = int(str(starting_at)[5:7])
        # Temporada empieza en julio/agosto
        if month >= 7:
            return f"{year}/{str(year+1)[-2:]}"
        else:
            return f"{year-1}/{str(year)[-2:]}"
    except (ValueError, IndexError):
        return None


def _extract_odds(payload: dict) -> list[tuple]:
    """
    Extrae odds relevantes del payload.
    Retorna lista de (bookmaker, market, selection, odds_value).
    Solo market 1X2 y Over/Under 2.5. Mejor odd por selection.
    """
    odds_raw = payload.get("odds") or []
    if not isinstance(odds_raw, list):
        return []

    # best[market][selection] = (bookmaker_id, max_value)
    best: dict[str, dict[str, tuple]] = {}

    for o in odds_raw:
        if not isinstance(o, dict):
            continue
        market_id = o.get("market_id")
        if market_id not in (MARKET_1X2, MARKET_OVER_UNDER):
            continue

        # Para Over/Under solo 2.5 line
        if market_id == MARKET_OVER_UNDER:
            total = str(o.get("total") or "")
            if total != "2.5":
                continue

        try:
            val = float(o.get("value") or 0)
        except (ValueError, TypeError):
            continue
        if val <= 1.0:
            continue

        label = str(o.get("label") or o.get("name") or "").strip()
        if not label:
            continue

        bookmaker_id = o.get("bookmaker_id") or 0
        market_desc = o.get("market_description") or (
            "1X2" if market_id == MARKET_1X2 else "Over/Under 2.5"
        )

        key_market = str(market_desc)[:100]
        if key_market not in best:
            best[key_market] = {}
        prev = best[key_market].get(label)
        if prev is None or val > prev[1]:
            best[key_market][label] = (str(bookmaker_id), val)

    result = []
    for market_str, selections in best.items():
        for selection, (bookmaker_id_str, val) in selections.items():
            result.append((bookmaker_id_str, market_str, selection[:100], val))
    return result


# ── Upsert helpers ────────────────────────────────────────────────────────────

def upsert_league(cur, league_id: int, league_name: str, country: str) -> Optional[int]:
    tier, is_active = TIER_MAP.get(league_id, ("unknown", False))
    cur.execute("""
        INSERT INTO bt2_leagues (name, country, tier, is_active, sportmonks_id)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (sportmonks_id) DO UPDATE
            SET name = EXCLUDED.name,
                country = EXCLUDED.country,
                tier = EXCLUDED.tier,
                is_active = EXCLUDED.is_active
        RETURNING id
    """, (league_name[:200], (country or "")[:100] or None, tier, is_active, league_id))
    row = cur.fetchone()
    return row["id"] if row else None


def upsert_team(cur, sportmonks_team_id: int, name: str, league_internal_id: Optional[int]) -> Optional[int]:
    cur.execute("""
        INSERT INTO bt2_teams (name, sportmonks_id, league_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (sportmonks_id) DO UPDATE
            SET name = EXCLUDED.name,
                league_id = COALESCE(EXCLUDED.league_id, bt2_teams.league_id)
        RETURNING id
    """, (name[:200], sportmonks_team_id, league_internal_id))
    row = cur.fetchone()
    return row["id"] if row else None


def upsert_event(
    cur, fixture_id: int, league_internal_id, home_id, away_id,
    kickoff_utc, status: str, result_home, result_away, season,
) -> Optional[int]:
    cur.execute("""
        INSERT INTO bt2_events
            (sportmonks_fixture_id, league_id, home_team_id, away_team_id,
             kickoff_utc, status, result_home, result_away, season)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (sportmonks_fixture_id) DO UPDATE
            SET status      = EXCLUDED.status,
                result_home = COALESCE(EXCLUDED.result_home, bt2_events.result_home),
                result_away = COALESCE(EXCLUDED.result_away, bt2_events.result_away),
                updated_at  = now()
        RETURNING id
    """, (fixture_id, league_internal_id, home_id, away_id,
          kickoff_utc, status, result_home, result_away, season))
    row = cur.fetchone()
    return row["id"] if row else None


def insert_odds_bulk(cur, event_id: int, odds_entries: list, fetched_at: datetime) -> int:
    if not odds_entries:
        return 0
    args = [(event_id, bk, mkt, sel, val, fetched_at) for bk, mkt, sel, val in odds_entries]
    cur.executemany("""
        INSERT INTO bt2_odds_snapshot (event_id, bookmaker, market, selection, odds, fetched_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (event_id, market, selection, bookmaker)
        DO UPDATE SET odds = EXCLUDED.odds, fetched_at = EXCLUDED.fetched_at
    """, args)
    return len(args)


# ── Runner principal ──────────────────────────────────────────────────────────

def run_normalization(batch_size: int = 1000, dry_run: bool = False) -> dict:
    conn = _get_db_conn()
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    stats = {
        "fixtures_read": 0,
        "fixtures_skipped_excluded": 0,
        "fixtures_skipped_no_participants": 0,
        "leagues_upserted": 0,
        "teams_upserted": 0,
        "events_upserted": 0,
        "odds_inserted": 0,
        "errors": [],
    }

    cur.execute("SELECT COUNT(*) FROM raw_sportmonks_fixtures")
    total = cur.fetchone()["count"]
    logger.info("[CDM] Total fixtures en raw: %d | batch_size: %d | dry_run: %s",
                total, batch_size, dry_run)

    fetched_at = datetime.now(tz=timezone.utc)
    offset = 0

    while True:
        cur.execute(
            "SELECT fixture_id, payload FROM raw_sportmonks_fixtures ORDER BY fixture_id LIMIT %s OFFSET %s",
            (batch_size, offset)
        )
        rows = cur.fetchall()
        if not rows:
            break

        for row in rows:
            fixture_id = row["fixture_id"]
            payload = row["payload"]

            stats["fixtures_read"] += 1

            # Extraer liga
            league_id_raw = payload.get("league_id")
            league_obj = payload.get("league") or {}
            league_name = ""
            country = ""
            if isinstance(league_obj, dict):
                league_name = league_obj.get("name") or ""
                country_obj = league_obj.get("country") or {}
                if isinstance(country_obj, dict):
                    country = country_obj.get("name") or ""

            league_id_sm = int(league_id_raw) if league_id_raw else None

            # Filtro de exclusión
            if should_exclude_league(league_id_sm, league_name):
                stats["fixtures_skipped_excluded"] += 1
                continue

            # Extraer participantes (home/away)
            participants = payload.get("participants") or []
            home_team_raw = away_team_raw = None
            if isinstance(participants, list):
                for p in participants:
                    if not isinstance(p, dict):
                        continue
                    meta = p.get("meta") or {}
                    loc = meta.get("location", "") if isinstance(meta, dict) else ""
                    if loc == "home":
                        home_team_raw = p
                    elif loc == "away":
                        away_team_raw = p

            if not home_team_raw or not away_team_raw:
                stats["fixtures_skipped_no_participants"] += 1
                logger.debug("[CDM] Skipped fixture %d: missing participants", fixture_id)
                continue

            if dry_run:
                stats["events_upserted"] += 1
                continue

            try:
                cur.execute("SAVEPOINT sp_fixture")

                # 1) Upsert liga
                league_internal_id = None
                if league_id_sm and league_name:
                    league_internal_id = upsert_league(cur, league_id_sm, league_name, country)
                    stats["leagues_upserted"] += 1

                # 2) Upsert equipos
                home_sm_id = home_team_raw.get("id")
                away_sm_id = away_team_raw.get("id")
                home_name = home_team_raw.get("name") or "Unknown"
                away_name = away_team_raw.get("name") or "Unknown"

                home_internal_id = upsert_team(cur, int(home_sm_id), home_name, league_internal_id) if home_sm_id else None
                away_internal_id = upsert_team(cur, int(away_sm_id), away_name, league_internal_id) if away_sm_id else None
                if home_internal_id:
                    stats["teams_upserted"] += 1
                if away_internal_id:
                    stats["teams_upserted"] += 1

                # 3) Upsert evento
                event_internal_id = upsert_event(
                    cur, fixture_id, league_internal_id,
                    home_internal_id, away_internal_id,
                    _parse_kickoff(payload),
                    _parse_status(payload),
                    *_parse_result(payload),
                    _parse_season(payload),
                )
                if event_internal_id:
                    stats["events_upserted"] += 1

                # 4) Odds (solo 1X2 y Over/Under 2.5, mejor por selection)
                if event_internal_id:
                    odds_entries = _extract_odds(payload)
                    if odds_entries:
                        stats["odds_inserted"] += insert_odds_bulk(cur, event_internal_id, odds_entries, fetched_at)

                cur.execute("RELEASE SAVEPOINT sp_fixture")

            except Exception as exc:
                cur.execute("ROLLBACK TO SAVEPOINT sp_fixture")
                logger.error("[CDM] Error fixture %d: %s", fixture_id, exc)
                stats["errors"].append(f"fixture {fixture_id}: {exc}")
                continue

        if not dry_run:
            conn.commit()

        offset += batch_size
        read = stats["fixtures_read"]
        if read % 5000 < batch_size or offset >= total:
            logger.info(
                "[CDM] %d/%d | eventos: %d | odds: %d | excluidos: %d | sin equipo: %d | errores: %d",
                read, total,
                stats["events_upserted"], stats["odds_inserted"],
                stats["fixtures_skipped_excluded"], stats["fixtures_skipped_no_participants"],
                len(stats["errors"]),
            )

    cur.close()
    conn.close()

    logger.info(
        "[CDM] COMPLETO — eventos: %d | odds: %d | excluidos: %d | sin equipo: %d | errores: %d",
        stats["events_upserted"], stats["odds_inserted"],
        stats["fixtures_skipped_excluded"], stats["fixtures_skipped_no_participants"],
        len(stats["errors"]),
    )
    return stats


def _write_report(stats: dict, dry_run: bool) -> Path:
    recon_dir = Path(_repo_root) / "docs" / "bettracker2" / "recon_results"
    recon_dir.mkdir(parents=True, exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d")
    mode = "_dry" if dry_run else ""
    report_path = recon_dir / f"cdm_normalize_{fecha}{mode}.md"

    errors_md = "\n".join(f"  - {e}" for e in stats["errors"][:20]) or "  Ninguno"
    content = f"""# CDM Normalize — Reporte

**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Modo:** {'DRY-RUN' if dry_run else 'PRODUCCIÓN'}

## Resultados

| Métrica | Valor |
|---------|-------|
| Fixtures leídos | {stats['fixtures_read']:,} |
| Ligas upserted | {stats['leagues_upserted']:,} |
| Equipos upserted | {stats['teams_upserted']:,} |
| Eventos upserted | {stats['events_upserted']:,} |
| Odds insertados | {stats['odds_inserted']:,} |
| Excluidos (liga) | {stats['fixtures_skipped_excluded']:,} |
| Excluidos (sin equipos) | {stats['fixtures_skipped_no_participants']:,} |
| Errores | {len(stats['errors'])} |

## Errores (primeros 20)
{errors_md}

## Verificación SQL
```sql
SELECT COUNT(*) FROM bt2_events;
SELECT COUNT(*) FROM bt2_odds_snapshot;
SELECT tier, COUNT(*) FROM bt2_leagues GROUP BY tier ORDER BY tier;
SELECT status, COUNT(*) FROM bt2_events GROUP BY status ORDER BY status;
```
"""
    report_path.write_text(content, encoding="utf-8")
    logger.info("[CDM] Reporte: %s", report_path)
    return report_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Normaliza raw_sportmonks_fixtures al CDM BT2")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    stats = run_normalization(batch_size=args.batch_size, dry_run=args.dry_run)
    _write_report(stats, args.dry_run)

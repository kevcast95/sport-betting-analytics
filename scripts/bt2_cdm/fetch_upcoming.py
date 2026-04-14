"""
fetch_upcoming.py — Sprint 04 US-BE-013

Ingesta diaria de fixtures futuros desde Sportmonks.
Lee bt2_leagues (is_active=true), llama a la API por liga y hace upsert
en bt2_events + bt2_odds_snapshot + **raw_sportmonks_fixtures** (UPSERT, D-06-037 / T-198).

Uso:
    python scripts/bt2_cdm/fetch_upcoming.py
    python scripts/bt2_cdm/fetch_upcoming.py --hours-ahead 72
    python scripts/bt2_cdm/fetch_upcoming.py --dry-run

Costo estimado: ~27 requests Sportmonks (1 por liga activa). Correr 1x/día.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from dotenv import load_dotenv
load_dotenv(Path(_repo_root) / ".env")

import httpx
import psycopg2
import psycopg2.extras

# Reutilizamos parsers y upserts del normalizador
from apps.api.bt2_raw_sportmonks_store import upsert_raw_sportmonks_fixture_psycopg2
from apps.api.bt2_sportmonks_include_resolve import bt2_sm_next_include_on_forbidden
from apps.api.bt2_sportmonks_includes import (
    BT2_SM_FIXTURE_INCLUDES,
    BT2_SM_FIXTURE_INCLUDES_CORE,
)
from scripts.bt2_cdm.normalize_fixtures import (
    _extract_odds,
    _parse_kickoff,
    _parse_status,
    insert_odds_bulk,
    upsert_event,
    upsert_league,
    upsert_team,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
)
logger = logging.getLogger("fetch_upcoming")

SM_BASE_URL = "https://api.sportmonks.com/v3"
RATE_LIMIT_WAIT_S = 60
SM_INCLUDE_DEGRADE_MAX = 48
RECON_DIR = Path(_repo_root) / "docs" / "bettracker2" / "recon_results"


def _get_db_conn():
    url = os.getenv("BT2_DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url)


def _get_active_leagues(conn) -> list[dict]:
    """Retorna ligas con is_active=true ordenadas por tier S→A→B."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, name, sportmonks_id, tier
        FROM bt2_leagues
        WHERE is_active = true
        ORDER BY
            CASE tier WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 ELSE 4 END,
            name
    """)
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


def _fetch_all_upcoming_fixtures(
    start_date: date,
    end_date: date,
    api_key: str,
    client: httpx.Client,
    active_league_ids: set[int],
) -> tuple[list[dict], int]:
    """
    Descarga TODOS los fixtures del rango (una sola pasada paginada) y filtra
    por active_league_ids en Python. Retorna (fixtures_filtrados, n_requests).

    Nota: el endpoint /fixtures/between ignora el parámetro filters=leagueIds,
    por lo que el filtrado se hace en Python igual que sportmonks_worker.py.
    Si 429: espera 60s y reintenta una vez; si falla de nuevo, lanza RuntimeError.
    """
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    url = f"{SM_BASE_URL}/football/fixtures/between/{start_str}/{end_str}"

    all_fixtures: list[dict] = []
    n_requests = 0
    page = 1
    effective_include = BT2_SM_FIXTURE_INCLUDES
    core = BT2_SM_FIXTURE_INCLUDES_CORE
    sm_degrade_steps = 0

    while True:
        params = {
            "api_token": api_key,
            "include": effective_include,
            "page": page,
        }

        attempts_429 = 0
        r = None
        while True:
            n_requests += 1
            try:
                r = client.get(url, params=params, timeout=30)
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                logger.warning("[FU] Timeout/red página %d: %s", page, exc)
                raise

            if r.status_code == 429:
                attempts_429 += 1
                if attempts_429 > 1:
                    raise RuntimeError("429 persistente — rate limit agotado")
                logger.warning("[FU] 429 página %d — esperando %ds…", page, RATE_LIMIT_WAIT_S)
                time.sleep(RATE_LIMIT_WAIT_S)
                continue

            break  # salir del loop de reintentos 429

        if r is None:
            logger.error("[FU] Sin respuesta página %d", page)
            break

        if r.status_code == 403:
            sm_degrade_steps += 1
            if sm_degrade_steps > SM_INCLUDE_DEGRADE_MAX:
                logger.error("[FU] Demasiados 403 ajustando includes — abortando página %d", page)
                break
            try:
                body: dict | str = r.json()
            except Exception:
                body = r.text
            nxt = bt2_sm_next_include_on_forbidden(
                effective_include, core=core, response_body=body
            )
            if nxt is not None:
                logger.warning(
                    "[FU] SM 403 — includes opcionales no permitidos; reintentando con subset"
                )
                effective_include = nxt
                continue

        if r.status_code != 200:
            logger.error("[FU] HTTP %d página %d", r.status_code, page)
            break

        data = r.json()
        raw = data.get("data", [])
        if not raw:
            break

        # Filtrar solo ligas activas
        filtered = [f for f in raw if f.get("league_id") in active_league_ids]
        all_fixtures.extend(filtered)

        pagination = data.get("pagination", {}) or {}
        has_more = pagination.get("has_more", False)
        logger.info(
            "[FU] Página %d — raw=%d filtrados=%d has_more=%s",
            page, len(raw), len(filtered), has_more,
        )
        if not has_more:
            break
        page += 1

    return all_fixtures, n_requests


def _extract_participants(payload: dict) -> tuple:
    """Extrae (home_sm_id, home_name, away_sm_id, away_name) de participants."""
    participants = payload.get("participants") or []
    home_id = home_name = away_id = away_name = None
    for p in participants:
        if not isinstance(p, dict):
            continue
        loc = (p.get("meta") or {}).get("location", "")
        if loc == "home":
            home_id = p.get("id")
            home_name = p.get("name", "")
        elif loc == "away":
            away_id = p.get("id")
            away_name = p.get("name", "")
    return home_id, home_name, away_id, away_name


def _parse_season_from_fixture(payload: dict) -> str | None:
    raw = payload.get("starting_at", "")
    if not raw:
        return None
    try:
        year = int(str(raw)[:4])
        month = int(str(raw)[5:7])
        if month >= 7:
            return f"{year}/{str(year+1)[-2:]}"
        return f"{year-1}/{str(year)[-2:]}"
    except (ValueError, IndexError):
        return None


def process_league_fixtures(
    fixtures: list[dict],
    league_internal_id: int,
    league_name: str,
    league_sm_id: int,
    conn,
    dry_run: bool,
) -> tuple[int, int, int]:
    """
    Hace upsert de los fixtures de una liga en bt2_events + bt2_odds_snapshot.
    Retorna (nuevos, actualizados, odds_upserted).
    """
    if not fixtures:
        return 0, 0, 0

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    nuevos = actualizados = odds_total = 0

    for fx in fixtures:
        fixture_id = fx.get("id")
        if not fixture_id:
            continue

        try:
            cur.execute("SAVEPOINT sp_fx")

            # Detectar si ya existe
            cur.execute(
                "SELECT id FROM bt2_events WHERE sportmonks_fixture_id = %s",
                (fixture_id,)
            )
            exists = cur.fetchone() is not None

            home_sm_id, home_name, away_sm_id, away_name = _extract_participants(fx)
            if not home_sm_id or not away_sm_id:
                cur.execute("ROLLBACK TO SAVEPOINT sp_fx")
                continue

            if not dry_run:
                home_id = upsert_team(cur, home_sm_id, home_name or "?", league_internal_id)
                away_id = upsert_team(cur, away_sm_id, away_name or "?", league_internal_id)
            else:
                home_id = away_id = None

            kickoff = _parse_kickoff(fx)
            status = _parse_status(fx)
            season = _parse_season_from_fixture(fx)
            result_home = result_away = None

            if not dry_run:
                event_id = upsert_event(
                    cur, fixture_id, league_internal_id,
                    home_id, away_id, kickoff, status,
                    result_home, result_away, season,
                )
                if event_id:
                    odds_entries = _extract_odds(fx)
                    fetched_at = datetime.now(tz=timezone.utc)
                    odds_n = insert_odds_bulk(cur, event_id, odds_entries, fetched_at)
                    odds_total += odds_n
                upsert_raw_sportmonks_fixture_psycopg2(cur, fx)
            else:
                event_id = fixture_id  # dummy para dry-run

            if exists:
                actualizados += 1
            else:
                nuevos += 1

            cur.execute("RELEASE SAVEPOINT sp_fx")

        except Exception as exc:
            logger.warning("[FU] Error fixture %s: %s", fixture_id, exc)
            cur.execute("ROLLBACK TO SAVEPOINT sp_fx")

    if not dry_run:
        conn.commit()

    cur.close()
    return nuevos, actualizados, odds_total


def generate_report(
    stats: list[dict],
    start_date: date,
    end_date: date,
    dry_run: bool,
    elapsed_s: float,
    events_future_before: int,
    events_future_after: int,
) -> Path:
    RECON_DIR.mkdir(parents=True, exist_ok=True)
    today_str = date.today().isoformat()
    mode = "DRY-RUN" if dry_run else "PRODUCCIÓN"
    report_path = RECON_DIR / f"upcoming_{today_str}.md"

    total_new = sum(s["nuevos"] for s in stats)
    total_upd = sum(s["actualizados"] for s in stats)
    total_odds = sum(s["odds"] for s in stats)
    total_req = max((s["requests"] for s in stats), default=0)
    ligas_ok = sum(1 for s in stats if s["nuevos"] + s["actualizados"] > 0)

    lines = [
        f"# Upcoming Fetch — {today_str}",
        "",
        f"**Modo:** {mode}",
        f"**Rango:** {start_date} → {end_date}",
        f"**Duración:** {elapsed_s:.1f}s",
        f"**Créditos estimados:** {total_req} requests",
        "",
        "---",
        "",
        "## Resumen",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Ligas procesadas | {len(stats)} |",
        f"| Ligas con fixtures | {ligas_ok} |",
        f"| Fixtures nuevos | {total_new} |",
        f"| Fixtures actualizados | {total_upd} |",
        f"| Odds upserted | {total_odds} |",
        f"| Events futuros antes | {events_future_before} |",
        f"| Events futuros después | {events_future_after} |",
        "",
        "---",
        "",
        "## Por liga",
        "",
        "| Liga | Tier | Nuevos | Actualizados | Odds | Estado |",
        "|------|------|--------|--------------|------|--------|",
    ]
    for s in stats:
        estado = "✅" if s["nuevos"] + s["actualizados"] > 0 else "—"
        if s.get("error"):
            estado = "❌ " + s["error"]
        lines.append(
            f"| {s['name']} | {s['tier']} | {s['nuevos']} | {s['actualizados']} | {s['odds']} | {estado} |"
        )

    lines += [
        "",
        "---",
        "",
        "```sql",
        "SELECT COUNT(*) FROM bt2_events WHERE kickoff_utc > now();",
        "```",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run_fetch(hours_ahead: int = 48, dry_run: bool = False) -> dict:
    api_key = os.getenv("SPORTMONKS_API_KEY", "")
    if not api_key:
        raise RuntimeError("SPORTMONKS_API_KEY no configurado en .env")

    start_date = date.today()
    end_date = start_date + timedelta(hours=hours_ahead)

    conn = _get_db_conn()
    active_leagues = _get_active_leagues(conn)
    logger.info(
        "[FU] Modo=%s | %s → %s | ligas_activas=%d",
        "DRY-RUN" if dry_run else "PRODUCCIÓN",
        start_date, end_date, len(active_leagues),
    )

    # Snapshot eventos futuros antes
    cur_snap = conn.cursor()
    cur_snap.execute("SELECT COUNT(*) FROM bt2_events WHERE kickoff_utc > now()")
    events_before = int(cur_snap.fetchone()[0])
    cur_snap.close()

    t0 = time.time()
    stats: list[dict] = []

    active_sm_ids = {lg["sportmonks_id"] for lg in active_leagues}
    # Mapa: sportmonks_id → registro completo de la liga
    sm_id_to_league = {lg["sportmonks_id"]: lg for lg in active_leagues}

    download_ok = True
    with httpx.Client() as client:
        logger.info("[FU] Descargando todos los fixtures del rango en una sola pasada…")
        try:
            all_fixtures, n_requests = _fetch_all_upcoming_fixtures(
                start_date, end_date, api_key, client, active_sm_ids
            )
        except Exception as exc:
            download_ok = False
            logger.error("[FU] Error fatal al descargar fixtures: %s", exc)
            all_fixtures, n_requests = [], 0

    logger.info("[FU] Total fixtures filtrados de ligas activas: %d (%d requests)", len(all_fixtures), n_requests)

    # Agrupar fixtures por liga
    by_league: dict[int, list[dict]] = {}
    for fx in all_fixtures:
        sm_lid = fx.get("league_id")
        if sm_lid not in sm_id_to_league:
            continue
        by_league.setdefault(sm_lid, []).append(fx)

    # Procesar liga por liga
    for lg in active_leagues:
        lg_name = lg["name"]
        lg_tier = lg["tier"]
        lg_sm_id = lg["sportmonks_id"]
        lg_internal_id = lg["id"]

        fixtures = by_league.get(lg_sm_id, [])
        logger.info("[FU] Liga: %s (sm_id=%s tier=%s) → %d fixtures", lg_name, lg_sm_id, lg_tier, len(fixtures))

        nuevos, actualizados, odds_n = process_league_fixtures(
            fixtures, lg_internal_id, lg_name, lg_sm_id, conn, dry_run
        )

        stats.append({
            "name": lg_name, "tier": lg_tier,
            "nuevos": nuevos, "actualizados": actualizados,
            "odds": odds_n,
            "requests": n_requests if lg_sm_id == active_leagues[0]["sportmonks_id"] else 0,
            "error": None,
        })

    elapsed = time.time() - t0

    # Snapshot eventos futuros después
    cur_snap2 = conn.cursor()
    cur_snap2.execute("SELECT COUNT(*) FROM bt2_events WHERE kickoff_utc > now()")
    events_after = int(cur_snap2.fetchone()[0])
    cur_snap2.close()
    conn.close()

    report_path = generate_report(
        stats, start_date, end_date, dry_run, elapsed, events_before, events_after
    )

    total_new = sum(s["nuevos"] for s in stats)
    total_upd = sum(s["actualizados"] for s in stats)
    logger.info(
        "[FU] COMPLETO — nuevos=%d actualizados=%d events_fututos_ahora=%d reporte=%s",
        total_new, total_upd, events_after, report_path.name,
    )

    return {
        "nuevos": total_new,
        "actualizados": total_upd,
        "events_futuros_antes": events_before,
        "events_futuros_despues": events_after,
        "reporte": str(report_path),
        "download_ok": download_ok,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingesta diaria de fixtures futuros BT2")
    parser.add_argument("--hours-ahead", type=int, default=48)
    parser.add_argument("--dry-run", action="store_true", help="Solo imprime, no escribe en BD")
    args = parser.parse_args()

    result = run_fetch(hours_ahead=args.hours_ahead, dry_run=args.dry_run)
    print(f"\nResultado: {result}")

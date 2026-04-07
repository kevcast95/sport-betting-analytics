"""
The-Odds-API worker — Atraco Masivo BT2
Extrae snapshots históricos de odds de múltiples bookmakers.
Requiere plan pagado con acceso a /v4/historical/odds.
Ejecutar vía run_atraco.py, no directamente.
"""

import asyncio
import json
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List, Optional

import httpx

_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

logger = logging.getLogger("odds_worker")

ODDS_BASE_URL = "https://api.the-odds-api.com/v4"
CACHE_FILE = Path(__file__).parent / ".cache_theoddsapi.json"

# Mapeo sport_key → nombre legible para logs
SPORT_LABELS = {
    "soccer_epl": "EPL",
    "soccer_spain_la_liga": "La Liga",
    "soccer_germany_bundesliga": "Bundesliga",
    "soccer_italy_serie_a": "Serie A",
    "soccer_france_ligue_1": "Ligue 1",
    "soccer_netherlands_eredivisie": "Eredivisie",
    "soccer_turkey_super_league": "Super Lig",
    "soccer_portugal_primeira_liga": "Liga Portugal",
    "soccer_colombia_primera_a": "Liga BetPlay",
}


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def _cache_key(sport_key: str, date_str: str) -> str:
    return f"{sport_key}:{date_str}"


async def fetch_odds_snapshot(
    sport_key: str,
    date_str: str,
    client: httpx.AsyncClient,
    api_key: str,
) -> tuple:
    """
    GET /v4/historical/odds para un deporte y fecha.
    Retorna (eventos: list, requests_remaining: str | None).
    """
    # La API espera timestamp ISO — usamos mediodia UTC del día
    snapshot_time = f"{date_str}T12:00:00Z"

    try:
        r = await client.get(
            f"{ODDS_BASE_URL}/historical/odds",
            params={
                "apiKey": api_key,
                "sport": sport_key,
                "regions": "eu",
                "markets": "h2h,totals",
                "dateFormat": "iso",
                "date": snapshot_time,
            },
            timeout=30,
        )
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.warning("[ODDS-WORKER] Red error %s %s: %s", sport_key, date_str, exc)
        return [], None

    remaining = r.headers.get("x-requests-remaining")
    used = r.headers.get("x-requests-used")

    if remaining:
        logger.debug(
            "[ODDS-WORKER] %s %s — usado: %s | restante: %s",
            sport_key, date_str, used, remaining,
        )

    if r.status_code == 200:
        data = r.json()
        events = data.get("data", []) if isinstance(data, dict) else data
        return events, remaining

    if r.status_code in (401, 402, 403):
        logger.error(
            "[ODDS-WORKER] Sin acceso a historical/odds (%d) — verifica plan pagado",
            r.status_code,
        )
        return [], remaining

    if r.status_code == 404:
        # Sin eventos para ese deporte/fecha — comportamiento normal
        return [], remaining

    if r.status_code == 429:
        logger.warning("[ODDS-WORKER] Rate limit (429) — pausando 60s")
        await asyncio.sleep(60)
        return [], remaining

    logger.warning("[ODDS-WORKER] HTTP %d para %s %s", r.status_code, sport_key, date_str)
    return [], remaining


async def store_snapshots(events: List[dict], db_session, sport_key: str) -> int:
    """Inserta snapshots en raw_theoddsapi_snapshots con ON CONFLICT DO NOTHING."""
    if not events:
        return 0

    from sqlalchemy import text

    stored = 0
    fetched_at = datetime.utcnow()

    for ev in events:
        event_id = ev.get("id")
        if not event_id:
            continue

        commence_time = None
        ct = ev.get("commence_time")
        if ct:
            try:
                commence_time = datetime.fromisoformat(ct.replace("Z", "+00:00"))
            except ValueError:
                pass

        stmt = text("""
            INSERT INTO raw_theoddsapi_snapshots
                (event_id, sport_key, commence_time, home_team, away_team,
                 payload, fetched_at)
            VALUES
                (:event_id, :sport_key, :commence_time, :home_team, :away_team,
                 CAST(:payload AS jsonb), :fetched_at)
            ON CONFLICT DO NOTHING
        """)

        result = await db_session.execute(stmt, {
            "event_id": event_id,
            "sport_key": sport_key,
            "commence_time": commence_time,
            "home_team": ev.get("home_team"),
            "away_team": ev.get("away_team"),
            "payload": json.dumps(ev, ensure_ascii=False),
            "fetched_at": fetched_at,
        })
        stored += result.rowcount

    await db_session.commit()
    return stored


async def run_theoddsapi(
    start_date: date,
    end_date: date,
    sport_keys: List[str],
    api_key: str,
    db_engine,
    dry_run: bool = False,
) -> dict:
    """
    Worker principal: itera sports × fechas, descarga snapshots históricos y persiste.
    Usa caché local para evitar re-fetch de combinaciones ya procesadas.
    """
    if not api_key:
        logger.warning("[ODDS-WORKER] THEODDSAPI_KEY vacío — worker omitido")
        return {
            "provider": "theoddsapi",
            "skipped": True,
            "reason": "API key vacía — activa el plan pagado",
        }

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    AsyncSessionLocal = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    cache = _load_cache()

    stats = {
        "provider": "theoddsapi",
        "requests_made": 0,
        "snapshots_fetched": 0,
        "snapshots_stored": 0,
        "cache_hits": 0,
        "requests_remaining": None,
        "errors": [],
    }

    total_combos = len(sport_keys) * ((end_date - start_date).days + 1)
    processed = 0

    logger.info(
        "[ODDS-WORKER] Iniciando — %s → %s — %d deportes × %d días = %d combos — dry_run: %s",
        start_date, end_date, len(sport_keys),
        (end_date - start_date).days + 1, total_combos, dry_run,
    )

    async with httpx.AsyncClient(timeout=30) as client:
        for sport_key in sport_keys:
            current = start_date
            label = SPORT_LABELS.get(sport_key, sport_key)

            while current <= end_date:
                date_str = current.isoformat()
                ck = _cache_key(sport_key, date_str)
                processed += 1

                if ck in cache:
                    stats["cache_hits"] += 1
                    current += timedelta(days=1)
                    continue

                try:
                    events, remaining = await fetch_odds_snapshot(
                        sport_key, date_str, client, api_key
                    )

                    stats["requests_made"] += 1
                    stats["snapshots_fetched"] += len(events)
                    if remaining is not None:
                        stats["requests_remaining"] = remaining

                    if events:
                        if not dry_run:
                            async with AsyncSessionLocal() as session:
                                stored = await store_snapshots(events, session, sport_key)
                                stats["snapshots_stored"] += stored
                        else:
                            stats["snapshots_stored"] += len(events)

                    cache[ck] = True
                    if not dry_run:
                        _save_cache(cache)

                    if stats["requests_made"] % 20 == 0:
                        logger.info(
                            "[ODDS-WORKER] %s | progreso: %d/%d | fetched: %d | stored: %d | restantes: %s",
                            label, processed, total_combos,
                            stats["snapshots_fetched"], stats["snapshots_stored"],
                            stats["requests_remaining"],
                        )

                except Exception as exc:
                    msg = f"{sport_key} {date_str}: {exc}"
                    logger.error("[ODDS-WORKER] Error: %s", msg)
                    stats["errors"].append(msg)

                current += timedelta(days=1)
                await asyncio.sleep(0.3)

    logger.info(
        "[ODDS-WORKER] Terminado — requests: %d | fetched: %d | stored: %d | cache hits: %d | errores: %d",
        stats["requests_made"], stats["snapshots_fetched"],
        stats["snapshots_stored"], stats["cache_hits"], len(stats["errors"]),
    )
    return stats

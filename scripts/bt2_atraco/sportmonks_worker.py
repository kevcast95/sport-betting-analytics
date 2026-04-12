"""
Sportmonks worker — Atraco Masivo BT2
Extrae fixtures históricos con odds, estadísticas, eventos y scores.
Ejecutar vía run_atraco.py, no directamente.
"""

import asyncio
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

import httpx

# Repo root en sys.path para importar apps.*
_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from apps.api.bt2_raw_sportmonks_store import UPSERT_RAW_FIXTURE_SQL, raw_fixture_upsert_params
from apps.api.bt2_sportmonks_includes import BT2_SM_FIXTURE_INCLUDES

logger = logging.getLogger("sm_worker")

SM_BASE_URL = "https://api.sportmonks.com/v3"
SM_INCLUDES = BT2_SM_FIXTURE_INCLUDES
RATE_LIMIT_PAUSE_S = 3600
RETRY_BACKOFF = [2, 4, 8]


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
) -> Optional[dict]:
    """GET con manejo de 429 y reintentos 5xx. Retorna None si falla tras 3 intentos."""
    for attempt, backoff in enumerate([0] + RETRY_BACKOFF):
        if backoff:
            await asyncio.sleep(backoff)
        try:
            r = await client.get(url, params=params, timeout=30)
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.warning("[SM-WORKER] Red error intento %d: %s", attempt + 1, exc)
            continue

        if r.status_code == 429:
            logger.warning("[SM-WORKER] Rate limit (429) — pausando %ds", RATE_LIMIT_PAUSE_S)
            await asyncio.sleep(RATE_LIMIT_PAUSE_S)
            attempt = 0  # reset retries after pause
            continue

        if r.status_code >= 500:
            logger.warning("[SM-WORKER] Server error %d intento %d/3", r.status_code, attempt + 1)
            continue

        if r.status_code == 200:
            return r.json()

        logger.error("[SM-WORKER] HTTP %d — %s", r.status_code, url)
        return None

    logger.error("[SM-WORKER] Max reintentos alcanzados — %s", url)
    return None


async def fetch_fixtures_for_date(
    date_str: str,
    client: httpx.AsyncClient,
    api_key: str,
    league_ids: Optional[List[int]] = None,
) -> List[dict]:
    """
    Descarga todos los fixtures de una fecha, paginando.
    Filtra por league_ids en Python tras recibir la respuesta
    (la API v3 no soporta filtro multi-liga en este endpoint).
    """
    all_fixtures: List[dict] = []
    league_set = set(league_ids) if league_ids else None
    page = 1

    while True:
        params: dict = {
            "api_token": api_key,
            "include": SM_INCLUDES,
            "page": page,
        }

        data = await _get_with_retry(
            client,
            f"{SM_BASE_URL}/football/fixtures/date/{date_str}",
            params,
        )
        if data is None:
            break

        fixtures = data.get("data", [])
        if not fixtures:
            break

        if league_set:
            fixtures = [f for f in fixtures if f.get("league_id") in league_set]

        all_fixtures.extend(fixtures)

        pagination = data.get("pagination", {})
        if not pagination.get("has_more", False):
            break
        page += 1

    return all_fixtures


async def store_fixtures(fixtures: List[dict], db_session) -> int:
    """UPSERT en raw_sportmonks_fixtures (payload y metadatos frescos — T-198 / D-06-037)."""
    if not fixtures:
        return 0

    from sqlalchemy import text

    stored = 0
    stmt = text(UPSERT_RAW_FIXTURE_SQL)
    for fx in fixtures:
        params = raw_fixture_upsert_params(fx)
        if params is None:
            continue
        result = await db_session.execute(stmt, params)
        stored += result.rowcount

    await db_session.commit()
    return stored


async def run_sportmonks(
    start_date: date,
    end_date: date,
    league_ids: Optional[List[int]],
    api_key: str,
    db_engine,
    dry_run: bool = False,
) -> dict:
    """
    Worker principal: itera fechas en rango, descarga fixtures y los persiste.
    Retorna dict con estadísticas de la ejecución.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    AsyncSessionLocal = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    stats = {
        "provider": "sportmonks",
        "dates_processed": 0,
        "dates_with_fixtures": 0,
        "fixtures_fetched": 0,
        "fixtures_stored": 0,
        "errors": [],
    }

    total_days = (end_date - start_date).days + 1
    current = start_date

    logger.info(
        "[SM-WORKER] Iniciando — %s → %s (%d días) — ligas: %s — dry_run: %s",
        start_date, end_date, total_days, league_ids, dry_run,
    )

    async with httpx.AsyncClient(timeout=30) as client:
        while current <= end_date:
            date_str = current.isoformat()
            try:
                fixtures = await fetch_fixtures_for_date(
                    date_str, client, api_key, league_ids
                )

                stats["dates_processed"] += 1
                stats["fixtures_fetched"] += len(fixtures)

                if fixtures:
                    stats["dates_with_fixtures"] += 1
                    if not dry_run:
                        async with AsyncSessionLocal() as session:
                            stored = await store_fixtures(fixtures, session)
                            stats["fixtures_stored"] += stored
                    else:
                        stats["fixtures_stored"] += len(fixtures)

                if stats["dates_processed"] % 50 == 0:
                    logger.info(
                        "[SM-WORKER] Progreso: %d/%d días | fetched: %d | stored: %d",
                        stats["dates_processed"], total_days,
                        stats["fixtures_fetched"], stats["fixtures_stored"],
                    )

            except Exception as exc:
                msg = f"{date_str}: {exc}"
                logger.error("[SM-WORKER] Error: %s", msg)
                stats["errors"].append(msg)

            current += timedelta(days=1)
            await asyncio.sleep(0.25)  # cortesía entre requests

    logger.info(
        "[SM-WORKER] Terminado — %d días | %d fixtures fetched | %d stored | %d errores",
        stats["dates_processed"], stats["fixtures_fetched"],
        stats["fixtures_stored"], len(stats["errors"]),
    )
    return stats

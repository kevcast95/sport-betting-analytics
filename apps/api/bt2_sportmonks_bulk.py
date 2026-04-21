"""
GET masivo SportMonks — mismo endpoint que `scripts/bt2_cdm/fetch_upcoming.py`:
`/v3/football/fixtures/between/{start}/{end}`.

Muchos planes permiten listar por rango aunque `GET /fixtures/{id}` devuelva
``data: null`` / mensaje de suscripción para ese id.

Usado por el refresco admin Monitor → CDM para hidratar fixtures antes del
fallback por id (`fetch_sportmonks_fixture_dict`).
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import httpx

from apps.api.bt2_sportmonks_include_resolve import bt2_sm_next_include_on_forbidden
from apps.api.bt2_sportmonks_includes import (
    BT2_SM_FIXTURE_INCLUDES,
    BT2_SM_FIXTURE_INCLUDES_CORE,
)

logger = logging.getLogger(__name__)

SM_BASE_URL = "https://api.sportmonks.com/v3"
RATE_LIMIT_WAIT_S = 60
SM_INCLUDE_DEGRADE_MAX = 48


def fetch_fixtures_between_dates(
    start_date: date,
    end_date: date,
    api_key: str,
) -> tuple[dict[int, dict[str, Any]], list[str], int]:
    """
    Descarga todas las páginas del between y arma ``fixture_sm_id -> payload``
    (mismo objeto que ``data[]`` en cada fixture).

    Includes y degradación 403 alineados a ``fetch_upcoming._fetch_all_upcoming_fixtures``.
    """
    notes: list[str] = []
    key = api_key.strip()
    if not key:
        return {}, ["sm:bulk_sin_api_key"], 0

    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    url = f"{SM_BASE_URL}/football/fixtures/between/{start_str}/{end_str}"

    out: dict[int, dict[str, Any]] = {}
    n_requests = 0
    page = 1
    effective_include = BT2_SM_FIXTURE_INCLUDES
    core = BT2_SM_FIXTURE_INCLUDES_CORE
    sm_degrade_steps = 0

    with httpx.Client(timeout=45) as client:
        while True:
            params: dict[str, Any] = {
                "api_token": key,
                "include": effective_include,
                "page": page,
            }
            attempts_429 = 0
            r: httpx.Response | None = None
            while True:
                n_requests += 1
                try:
                    r = client.get(url, params=params)
                except (httpx.TimeoutException, httpx.ConnectError) as exc:
                    notes.append(f"sm:bulk_between_red_error:{exc}")
                    logger.warning("[SM bulk] Timeout/red página %d: %s", page, exc)
                    return out, notes, n_requests

                if r.status_code == 429:
                    attempts_429 += 1
                    if attempts_429 > 1:
                        notes.append("sm:bulk_between_429_abort")
                        return out, notes, n_requests
                    logger.warning(
                        "[SM bulk] 429 página %d — esperando %ds…", page, RATE_LIMIT_WAIT_S
                    )
                    time.sleep(RATE_LIMIT_WAIT_S)
                    continue
                break

            if r is None:
                notes.append("sm:bulk_between_sin_respuesta")
                break

            if r.status_code == 403:
                sm_degrade_steps += 1
                if sm_degrade_steps > SM_INCLUDE_DEGRADE_MAX:
                    notes.append("sm:bulk_between_403_demasiados_pasos")
                    logger.error("[SM bulk] Demasiados 403 ajustando includes — abort")
                    break
                try:
                    body: dict[str, Any] | str = r.json()
                except Exception:
                    body = r.text
                nxt = bt2_sm_next_include_on_forbidden(
                    effective_include, core=core, response_body=body
                )
                if nxt is not None:
                    logger.warning("[SM bulk] 403 — degradando includes y reintentando página %d", page)
                    effective_include = nxt
                    continue

            if r.status_code != 200:
                notes.append(f"sm:bulk_between_http_{r.status_code}_page_{page}")
                logger.error("[SM bulk] HTTP %s página %d", r.status_code, page)
                break

            try:
                data = r.json()
            except Exception as exc:
                notes.append(f"sm:bulk_between_json_error:{exc}")
                break

            raw = data.get("data") or []
            if not isinstance(raw, list):
                notes.append("sm:bulk_between_data_no_lista")
                break

            for f in raw:
                if not isinstance(f, dict):
                    continue
                fid = f.get("id")
                try:
                    fi = int(fid)
                except (TypeError, ValueError):
                    continue
                out[fi] = f

            pagination = data.get("pagination") or {}
            has_more = bool(pagination.get("has_more"))
            logger.info(
                "[SM bulk] página %d — fixtures_acum=%d has_more=%s",
                page,
                len(out),
                has_more,
            )
            if not has_more:
                break
            page += 1

    notes.insert(
        0,
        f"sm:bulk_between_{start_str}_{end_str}_fixtures_distintos_{len(out)}_req_{n_requests}",
    )
    return out, notes, n_requests

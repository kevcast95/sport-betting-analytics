"""
Solo desarrollo — refresco SM → raw antes de regenerar snapshot de bóveda.

Un GET por `sportmonks_fixture_id` de los eventos del pool valor del día (mismo
criterio que `_materialize_daily_picks_snapshot`), con `BT2_SM_FIXTURE_INCLUDES`,
y UPSERT en `raw_sportmonks_fixtures`.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from apps.api.bt2_raw_sportmonks_store import upsert_raw_sportmonks_fixture_psycopg2
from apps.api.bt2_sportmonks_includes import BT2_SM_FIXTURE_INCLUDES
from apps.api.bt2_value_pool import build_value_pool_for_snapshot, parse_priority_league_ids
from apps.api.bt2_vault_pool import VAULT_VALUE_POOL_UNIVERSE_MAX

logger = logging.getLogger(__name__)

SM_FIXTURE_URL = "https://api.sportmonks.com/v3/football/fixtures"


def _user_day_window_utc(tz_name: str) -> tuple[datetime, datetime]:
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    local_today = datetime.now(tz=tz).date()
    day_start_utc = datetime.combine(local_today, datetime.min.time(), tzinfo=tz).astimezone(
        timezone.utc
    )
    day_end_utc = day_start_utc + timedelta(hours=24)
    return day_start_utc, day_end_utc


def _fetch_sm_fixture_dict(fixture_id: int, api_key: str) -> dict[str, Any] | None:
    qs = urlencode({"api_token": api_key, "include": BT2_SM_FIXTURE_INCLUDES})
    url = f"{SM_FIXTURE_URL}/{int(fixture_id)}?{qs}"
    req = Request(url, headers={"Accept": "application/json"}, method="GET")
    data: dict[str, Any] | None = None
    for attempt in range(2):
        try:
            with urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
            break
        except HTTPError as e:
            if e.code == 429 and attempt == 0:
                time.sleep(2.0)
                continue
            logger.warning("[dev-sm-refresh] fixture %s HTTP %s", fixture_id, e.code)
            return None
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            logger.warning("[dev-sm-refresh] fixture %s error: %s", fixture_id, e)
            return None
    if not data:
        return None
    d = data.get("data")
    if isinstance(d, dict):
        return d
    return None


def refresh_raw_sportmonks_for_value_pool_today(
    cur,
    *,
    tz_name: str,
    sportmonks_api_key: str,
    priority_league_ids_csv: str,
) -> tuple[int, list[str]]:
    """
    Devuelve (cuántos payloads upsert OK, lista mensajes error / skip).
    """
    notes: list[str] = []
    if not (sportmonks_api_key or "").strip():
        notes.append("sm:sin_sportmonks_api_key_skip_refresh")
        return 0, notes

    day_start_utc, day_end_utc = _user_day_window_utc(tz_name)
    league_filter = parse_priority_league_ids(priority_league_ids_csv)
    pool, _pre = build_value_pool_for_snapshot(
        cur, day_start_utc, day_end_utc, league_filter=league_filter
    )
    if len(pool) > VAULT_VALUE_POOL_UNIVERSE_MAX:
        pool = pool[:VAULT_VALUE_POOL_UNIVERSE_MAX]

    if not pool:
        notes.append("sm:pool_vacio_nada_que_refrescar")
        return 0, notes

    eids = [int(t[0]) for t in pool]
    cur.execute(
        """
        SELECT id, sportmonks_fixture_id
        FROM bt2_events
        WHERE id = ANY(%s)
        """,
        (eids,),
    )
    sm_by_event: dict[int, int | None] = {}
    for row in cur.fetchall():
        eid = int(row[0])
        sm = row[1]
        sm_by_event[eid] = int(sm) if sm is not None else None

    seen_sm: set[int] = set()
    ordered_sm: list[int] = []
    for eid in eids:
        sid = sm_by_event.get(eid)
        if sid is None:
            notes.append(f"sm:event_{eid}_sin_sportmonks_fixture_id")
            continue
        if sid not in seen_sm:
            seen_sm.add(sid)
            ordered_sm.append(sid)

    if not ordered_sm:
        notes.append("sm:sin_fixture_ids_en_pool")
        return 0, notes

    key = sportmonks_api_key.strip()
    ok = 0
    for i, fid in enumerate(ordered_sm):
        if i > 0:
            time.sleep(0.25)
        fx = _fetch_sm_fixture_dict(fid, key)
        if fx is None:
            notes.append(f"sm:fixture_{fid}_fetch_fallo")
            continue
        if upsert_raw_sportmonks_fixture_psycopg2(cur, fx):
            ok += 1
        else:
            notes.append(f"sm:fixture_{fid}_upsert_params_invalidos")

    notes.insert(0, f"sm:refrescados_{ok}_de_{len(ordered_sm)}_fixtures_unicos")
    return ok, notes

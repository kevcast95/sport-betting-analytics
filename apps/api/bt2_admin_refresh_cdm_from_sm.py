"""
Admin (S6.3+) — Refresco SportMonks → raw → CDM para eventos con `bt2_daily_picks` en un día.

No usa snapshot de bóveda: consulta SM en vivo, UPSERT `raw_sportmonks_fixtures` y normaliza
a `bt2_events` (status / result_home / result_away), luego opcionalmente ejecuta la fase
evaluate del job oficial para cerrar `pending_result` con la verdad CDM actualizada.
"""

from __future__ import annotations

import importlib.util
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

from apps.api.bt2_dev_sm_refresh import fetch_sportmonks_fixture_dict
from apps.api.bt2_official_evaluation_job import job_summary_dict, run_official_evaluation_job
from apps.api.bt2_raw_sportmonks_store import upsert_raw_sportmonks_fixture_psycopg2

logger = logging.getLogger(__name__)


@runtime_checkable
class _DbCursor(Protocol):
    def execute(self, query: str, params: Any = None) -> None: ...
    def fetchall(self) -> list[Any]: ...


_normalize_mod: Any = None


def _refresh_distinct_fixtures_from_pick_event_rows(
    cur: _DbCursor,
    rows: list[Any],
    sportmonks_api_key: str,
) -> dict[str, Any]:
    """
    Para cada fila (event_id, sportmonks_fixture_id) distinta en `rows`: GET SM,
    UPSERT raw, normaliza CDM. Dedupe por `sportmonks_fixture_id`.

    Devuelve contadores + notes (sin evaluación oficial).
    """
    notes: list[str] = []
    targeted = len(rows)
    sm_ok = raw_ok = cdm_ok = cdm_skip = cdm_err = 0
    seen_sm: set[int] = set()
    norm = _normalize_module()
    normalize_single = norm.normalize_single_fixture_payload
    fetched_at = datetime.now(tz=timezone.utc)
    sm_requests = 0

    for row in rows:
        r = dict(row) if isinstance(row, dict) else {"event_id": row[0], "sm_fid": row[1]}
        eid = r.get("event_id")
        sm_fid = r.get("sm_fid")
        if sm_fid is None:
            notes.append(f"event_{eid}_sin_sportmonks_fixture_id")
            continue
        fid = int(sm_fid)
        if fid in seen_sm:
            continue
        seen_sm.add(fid)

        if sm_requests > 0:
            time.sleep(0.25)
        sm_requests += 1

        fx = fetch_sportmonks_fixture_dict(fid, sportmonks_api_key.strip())
        if fx is None:
            notes.append(f"sm:fixture_{fid}_fetch_fallo")
            continue
        sm_ok += 1

        if not upsert_raw_sportmonks_fixture_psycopg2(cur, fx):
            notes.append(f"sm:fixture_{fid}_raw_upsert_fallo")
            continue
        raw_ok += 1

        res = normalize_single(cur, fid, fx, fetched_at=fetched_at, dry_run=False)
        if res.get("error"):
            cdm_err += 1
            notes.append(f"cdm:fixture_{fid}_{res.get('error')}")
            continue
        if res.get("skipped"):
            cdm_skip += 1
            notes.append(f"cdm:fixture_{fid}_skipped_{res.get('skipped')}")
            continue
        if res.get("ok"):
            cdm_ok += 1

    return {
        "fixtures_targeted": targeted,
        "unique_sportmonks_fixtures_processed": len(seen_sm),
        "sm_fetch_ok": sm_ok,
        "raw_upsert_ok": raw_ok,
        "cdm_normalized_ok": cdm_ok,
        "cdm_skipped": cdm_skip,
        "cdm_errors": cdm_err,
        "notes": notes[:80],
    }


def _normalize_module() -> Any:
    global _normalize_mod
    if _normalize_mod is not None:
        return _normalize_mod
    root = Path(__file__).resolve().parents[2]
    path = root / "scripts" / "bt2_cdm" / "normalize_fixtures.py"
    spec = importlib.util.spec_from_file_location("bt2_normalize_fixtures_admin", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("normalize_fixtures: spec inválido")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _normalize_mod = mod
    return mod


def admin_refresh_cdm_from_sm_for_operating_day(
    cur: _DbCursor,
    *,
    operating_day_key: str,
    sportmonks_api_key: str,
    limit: int = 100,
    run_official_evaluation: bool = True,
) -> dict[str, Any]:
    """
    Para cada `event_id` distinto en `bt2_daily_picks` del día: GET SM, raw UPSERT, normalize CDM.

    `limit`: máximo de **eventos** (filas distintas) a procesar, orden `event_id`.
    """
    notes: list[str] = []
    lim = max(1, min(int(limit), 500))

    if not (sportmonks_api_key or "").strip():
        return {
            "ok": False,
            "operating_day_key": operating_day_key,
            "message_es": "Falta SPORTMONKS_API_KEY en el servidor.",
            "fixtures_targeted": 0,
            "unique_sportmonks_fixtures_processed": 0,
            "sm_fetch_ok": 0,
            "raw_upsert_ok": 0,
            "cdm_normalized_ok": 0,
            "cdm_skipped": 0,
            "cdm_errors": 0,
            "official_evaluation": None,
            "notes": ["sm:sin_api_key"],
        }

    cur.execute(
        """
        SELECT DISTINCT e.id AS event_id, e.sportmonks_fixture_id AS sm_fid
        FROM bt2_daily_picks dp
        INNER JOIN bt2_events e ON e.id = dp.event_id
        WHERE dp.operating_day_key = %s
        ORDER BY e.id
        LIMIT %s
        """,
        (operating_day_key, lim),
    )
    rows = cur.fetchall()
    core = _refresh_distinct_fixtures_from_pick_event_rows(cur, rows, sportmonks_api_key)
    sm_ok = int(core["sm_fetch_ok"])
    raw_ok = int(core["raw_upsert_ok"])
    cdm_ok = int(core["cdm_normalized_ok"])
    cdm_skip = int(core["cdm_skipped"])
    cdm_err = int(core["cdm_errors"])
    notes.extend(list(core["notes"]))
    targeted = int(core["fixtures_targeted"])

    eval_block: Optional[dict[str, Any]] = None
    if run_official_evaluation:
        stats = run_official_evaluation_job(
            cur,
            dry_run=False,
            skip_backfill=False,
            skip_evaluate=False,
            refresh_stale_no_evaluable=True,
            limit_refresh_ne=5000,
        )
        eval_block = job_summary_dict(stats)

    msg = (
        f"Día {operating_day_key}: SM {sm_ok} fetch OK, {raw_ok} raw UPSERT, "
        f"{cdm_ok} CDM OK, {cdm_skip} omitidos, {cdm_err} errores CDM."
    )
    if eval_block:
        msg += (
            f" Evaluación oficial: examinadas {eval_block.get('pending_rows_examined', 0)}, "
            f"cerradas a final {eval_block.get('closed_to_final_this_run', 0)}."
        )
        nr = int(eval_block.get("ne_refresh_updated_from_ne") or 0)
        if nr > 0:
            msg += f" Re-evaluadas desde N.E.: {nr}."

    return {
        "ok": True,
        "operating_day_key": operating_day_key,
        "message_es": msg,
        "fixtures_targeted": targeted,
        "unique_sportmonks_fixtures_processed": int(core["unique_sportmonks_fixtures_processed"]),
        "sm_fetch_ok": sm_ok,
        "raw_upsert_ok": raw_ok,
        "cdm_normalized_ok": cdm_ok,
        "cdm_skipped": cdm_skip,
        "cdm_errors": cdm_err,
        "official_evaluation": eval_block,
        "notes": notes[:80],
    }


def admin_refresh_cdm_from_sm_for_daily_pick_day_range(
    cur: _DbCursor,
    *,
    operating_day_key_from: str,
    operating_day_key_to: str,
    sportmonks_api_key: str,
    limit: int = 200,
    run_official_evaluation: bool = True,
) -> dict[str, Any]:
    """
    Para cada evento distinto con `bt2_daily_picks` en [from, to] inclusive: GET SM,
    UPSERT raw, normaliza `bt2_events`; opcionalmente evaluación oficial batch.
    """
    notes: list[str] = []
    lim = max(1, min(int(limit), 500))

    if not (sportmonks_api_key or "").strip():
        return {
            "ok": False,
            "operating_day_key_from": operating_day_key_from,
            "operating_day_key_to": operating_day_key_to,
            "message_es": "Falta SPORTMONKS_API_KEY en el servidor.",
            "fixtures_targeted": 0,
            "unique_sportmonks_fixtures_processed": 0,
            "sm_fetch_ok": 0,
            "raw_upsert_ok": 0,
            "cdm_normalized_ok": 0,
            "cdm_skipped": 0,
            "cdm_errors": 0,
            "official_evaluation": None,
            "notes": ["sm:sin_api_key"],
        }

    cur.execute(
        """
        SELECT DISTINCT e.id AS event_id, e.sportmonks_fixture_id AS sm_fid
        FROM bt2_daily_picks dp
        INNER JOIN bt2_events e ON e.id = dp.event_id
        WHERE dp.operating_day_key >= %s AND dp.operating_day_key <= %s
        ORDER BY e.id
        LIMIT %s
        """,
        (operating_day_key_from, operating_day_key_to, lim),
    )
    rows = cur.fetchall()
    core = _refresh_distinct_fixtures_from_pick_event_rows(cur, rows, sportmonks_api_key)
    sm_ok = int(core["sm_fetch_ok"])
    raw_ok = int(core["raw_upsert_ok"])
    cdm_ok = int(core["cdm_normalized_ok"])
    cdm_skip = int(core["cdm_skipped"])
    cdm_err = int(core["cdm_errors"])
    notes.extend(list(core["notes"]))
    targeted = int(core["fixtures_targeted"])

    eval_block: Optional[dict[str, Any]] = None
    if run_official_evaluation:
        stats = run_official_evaluation_job(
            cur,
            dry_run=False,
            skip_backfill=False,
            skip_evaluate=False,
            refresh_stale_no_evaluable=True,
            limit_refresh_ne=5000,
        )
        eval_block = job_summary_dict(stats)

    msg = (
        f"Rango {operating_day_key_from} … {operating_day_key_to}: SM {sm_ok} fetch OK, "
        f"{raw_ok} raw UPSERT, {cdm_ok} CDM OK, {cdm_skip} omitidos, {cdm_err} errores CDM."
    )
    if eval_block:
        msg += (
            f" Evaluación oficial: examinadas {eval_block.get('pending_rows_examined', 0)}, "
            f"cerradas a final {eval_block.get('closed_to_final_this_run', 0)}."
        )
        nr = int(eval_block.get("ne_refresh_updated_from_ne") or 0)
        if nr > 0:
            msg += f" Re-evaluadas desde N.E.: {nr}."

    return {
        "ok": True,
        "operating_day_key_from": operating_day_key_from,
        "operating_day_key_to": operating_day_key_to,
        "message_es": msg,
        "fixtures_targeted": targeted,
        "unique_sportmonks_fixtures_processed": int(core["unique_sportmonks_fixtures_processed"]),
        "sm_fetch_ok": sm_ok,
        "raw_upsert_ok": raw_ok,
        "cdm_normalized_ok": cdm_ok,
        "cdm_skipped": cdm_skip,
        "cdm_errors": cdm_err,
        "official_evaluation": eval_block,
        "notes": notes[:80],
    }

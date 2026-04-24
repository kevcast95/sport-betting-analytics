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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

from apps.api.bt2_dev_sm_refresh import fetch_sportmonks_fixture_dict
from apps.api.bt2_official_evaluation_job import job_summary_dict, run_official_evaluation_job
from apps.api.bt2_raw_sportmonks_store import upsert_raw_sportmonks_fixture_psycopg2
from apps.api.bt2_sportmonks_bulk import fetch_fixtures_between_dates

logger = logging.getLogger(__name__)


@runtime_checkable
class _DbCursor(Protocol):
    def execute(self, query: str, params: Any = None) -> None: ...
    def fetchall(self) -> list[Any]: ...


_normalize_mod: Any = None


def _bulk_between_range_for_monitor(
    operating_day_key_from: str,
    operating_day_key_to: str,
    *,
    pad_days: int = 3,
) -> tuple[date, date]:
    """
    Ventana **solo** para SM ``fixtures/between`` (llenar mapa bulk).

    Coincide con lo que la UI ya envía como ``operatingDayKeyFrom`` / ``To`` (Hoy, 7d…), ampliado
    ``±pad_days`` por cruces TZ. Los **picks** a refrescar siguen siendo sólo los del rango operativo
    en SQL; aquí no se piden «resultados futuros» en sentido BT2 — SM devuelve estado scheduled/live.
    """
    d0 = date.fromisoformat(str(operating_day_key_from).strip()[:10])
    d1 = date.fromisoformat(str(operating_day_key_to).strip()[:10])
    pad = timedelta(days=pad_days)
    return d0 - pad, d1 + pad


def _refresh_distinct_fixtures_from_pick_event_rows(
    cur: _DbCursor,
    rows: list[Any],
    sportmonks_api_key: str,
    *,
    fixture_payload_by_sm_id: Optional[Mapping[int, dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Para cada fila (event_id, sportmonks_fixture_id) distinta en `rows`:
    payload desde ``fixture_payload_by_sm_id`` si existe (GET **between**, mismos ``include`` que
    ``scripts/bt2_cdm/fetch_upcoming.py``); si no GET por id con **perfil completo**
    (``BT2_SM_FIXTURE_INCLUDES`` + degradación 403 — igual que el ingesta diaria). UPSERT raw,
    normaliza CDM. Dedupe por `sportmonks_fixture_id`.

    Devuelve contadores + notes (sin evaluación oficial).
    """
    notes: list[str] = []
    targeted = len(rows)
    sm_ok = raw_ok = cdm_ok = cdm_skip = cdm_err = 0
    seen_sm: set[int] = set()
    norm = _normalize_module()
    normalize_single = norm.normalize_single_fixture_payload
    fetched_at = datetime.now(tz=timezone.utc)
    id_fetch_count = 0

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

        fx: Optional[dict[str, Any]] = None
        if fixture_payload_by_sm_id is not None:
            hit = fixture_payload_by_sm_id.get(fid)
            if isinstance(hit, dict):
                fx = hit
        if fx is None:
            if id_fetch_count > 0:
                time.sleep(0.25)
            id_fetch_count += 1
            fx = fetch_sportmonks_fixture_dict(fid, sportmonks_api_key.strip(), profile="full")
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
    only_pending_official_evaluation: bool = True,
) -> dict[str, Any]:
    """
    Para cada `event_id` distinto en `bt2_daily_picks` del día: GET SM, raw UPSERT, normalize CDM.

    `limit`: máximo de **eventos** (filas distintas) a procesar, orden `event_id`.
    Si `only_pending_official_evaluation`: solo eventos con algún pick cuya evaluación oficial
    sigue en `pending_result` (ahorra llamadas SM cuando ya todo está cerrado).
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
            "only_pending_official_evaluation": only_pending_official_evaluation,
            "notes": ["sm:sin_api_key"],
        }

    pending_sql = ""
    if only_pending_official_evaluation:
        pending_sql = """
          AND EXISTS (
            SELECT 1 FROM bt2_daily_picks dp2
            LEFT JOIN bt2_pick_official_evaluation eoe ON eoe.daily_pick_id = dp2.id
            WHERE dp2.event_id = e.id AND dp2.operating_day_key = %s
              AND COALESCE(eoe.evaluation_status, 'pending_result') = 'pending_result'
          )
        """
    cur.execute(
        f"""
        SELECT DISTINCT e.id AS event_id, e.sportmonks_fixture_id AS sm_fid
        FROM bt2_daily_picks dp
        INNER JOIN bt2_events e ON e.id = dp.event_id
        WHERE dp.operating_day_key = %s
        {pending_sql}
        ORDER BY e.id
        LIMIT %s
        """,
        (operating_day_key, operating_day_key, lim) if only_pending_official_evaluation else (operating_day_key, lim),
    )
    rows = cur.fetchall()
    bf, bt = _bulk_between_range_for_monitor(operating_day_key, operating_day_key)
    bulk_map, bulk_notes, _bulk_req = fetch_fixtures_between_dates(bf, bt, sportmonks_api_key)
    notes.extend(bulk_notes)
    core = _refresh_distinct_fixtures_from_pick_event_rows(
        cur, rows, sportmonks_api_key, fixture_payload_by_sm_id=bulk_map
    )
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
        )
        eval_block = job_summary_dict(stats)

    msg = (
        f"Día {operating_day_key}"
        f"{' (solo eventos con pick en evaluación pending_result)' if only_pending_official_evaluation else ' (todos los eventos con pick, hasta límite)'}: "
        f"SM {sm_ok} fetch OK, {raw_ok} raw UPSERT, {cdm_ok} CDM OK, {cdm_skip} omitidos, {cdm_err} errores CDM."
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
        "only_pending_official_evaluation": only_pending_official_evaluation,
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
    only_pending_official_evaluation: bool = True,
) -> dict[str, Any]:
    """
    Para cada evento distinto con `bt2_daily_picks` en [from, to] inclusive: GET SM,
    UPSERT raw, normaliza `bt2_events`; opcionalmente evaluación oficial batch.

    Si `only_pending_official_evaluation`: solo eventos que tienen al menos un pick en el rango
    con evaluación oficial aún `pending_result` (menos llamadas SM al pulsar Actualizar en monitor).
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
            "only_pending_official_evaluation": only_pending_official_evaluation,
            "notes": ["sm:sin_api_key"],
        }

    pending_sql = ""
    if only_pending_official_evaluation:
        pending_sql = """
          AND EXISTS (
            SELECT 1 FROM bt2_daily_picks dp2
            LEFT JOIN bt2_pick_official_evaluation eoe ON eoe.daily_pick_id = dp2.id
            WHERE dp2.event_id = e.id
              AND dp2.operating_day_key >= %s AND dp2.operating_day_key <= %s
              AND COALESCE(eoe.evaluation_status, 'pending_result') = 'pending_result'
          )
        """
    cur.execute(
        f"""
        SELECT DISTINCT e.id AS event_id, e.sportmonks_fixture_id AS sm_fid
        FROM bt2_daily_picks dp
        INNER JOIN bt2_events e ON e.id = dp.event_id
        WHERE dp.operating_day_key >= %s AND dp.operating_day_key <= %s
        {pending_sql}
        ORDER BY e.id
        LIMIT %s
        """,
        (
            operating_day_key_from,
            operating_day_key_to,
            operating_day_key_from,
            operating_day_key_to,
            lim,
        )
        if only_pending_official_evaluation
        else (operating_day_key_from, operating_day_key_to, lim),
    )
    rows = cur.fetchall()
    bf, bt = _bulk_between_range_for_monitor(operating_day_key_from, operating_day_key_to)
    bulk_map, bulk_notes, _bulk_req = fetch_fixtures_between_dates(bf, bt, sportmonks_api_key)
    notes.extend(bulk_notes)
    core = _refresh_distinct_fixtures_from_pick_event_rows(
        cur, rows, sportmonks_api_key, fixture_payload_by_sm_id=bulk_map
    )
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
        )
        eval_block = job_summary_dict(stats)

    msg = (
        f"Rango {operating_day_key_from} … {operating_day_key_to}"
        f"{' (solo eventos con pick pending_result en el rango)' if only_pending_official_evaluation else ' (todos los eventos con pick, hasta límite)'}: "
        f"SM {sm_ok} fetch OK, {raw_ok} raw UPSERT, {cdm_ok} CDM OK, {cdm_skip} omitidos, {cdm_err} errores CDM."
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
        "only_pending_official_evaluation": only_pending_official_evaluation,
        "notes": notes[:80],
    }


def admin_refresh_cdm_from_sm_for_backtest_replay_window(
    cur: _DbCursor,
    *,
    operating_day_key_from: str,
    operating_day_key_to: str,
    sportmonks_api_key: str,
    max_events_per_day: int = 20,
    only_pending_cdm: bool = True,
) -> dict[str, Any]:
    """
    GET SportMonks → raw → CDM para los **mismos candidatos** que usa el replay admin
    (`bt2_admin_backtest_replay`): por cada día operativo Bogota, lista eventos con kickoff en
    esa ventana (ligas activas, mismo orden/límite que `_list_event_ids_for_replay_day`:
    hasta `max(1, max_events_per_day * 3)` IDs por día), deduplica y refresca fixtures.

    Si `only_pending_cdm` (default): solo consulta SM para eventos que aún **no tienen marcador
    completo en CDM** (`result_home` o `result_away` NULL), típico origen de «pendiente» en el
    replay aunque el partido ya haya jugado.

    Sirve para que `bt2_events` tenga marcadores/status antes de correr backtest-replay y no
    aparezcan falsos «pendiente» por CDM desactualizado.

    No ejecuta el job de evaluación oficial (solo actualiza CDM desde SM).
    """
    from apps.api.bt2_admin_backtest_replay import (
        _list_event_ids_for_replay_day,
        bogota_operating_day_utc_window,
    )

    notes: list[str] = []
    d0 = date.fromisoformat(operating_day_key_from.strip())
    d1 = date.fromisoformat(operating_day_key_to.strip())
    only_pending = bool(only_pending_cdm)

    if d0 > d1:
        return {
            "ok": False,
            "operating_day_key_from": operating_day_key_from,
            "operating_day_key_to": operating_day_key_to,
            "message_es": "operating_day_key_from > operating_day_key_to.",
            "distinct_event_ids": 0,
            "replay_pool_event_count": 0,
            "pending_cdm_event_count": 0,
            "only_pending_cdm": only_pending,
            "fixtures_targeted": 0,
            "unique_sportmonks_fixtures_processed": 0,
            "sm_fetch_ok": 0,
            "raw_upsert_ok": 0,
            "cdm_normalized_ok": 0,
            "cdm_skipped": 0,
            "cdm_errors": 0,
            "notes": ["rango_invalido"],
        }

    if not (sportmonks_api_key or "").strip():
        return {
            "ok": False,
            "operating_day_key_from": operating_day_key_from,
            "operating_day_key_to": operating_day_key_to,
            "message_es": "Falta SPORTMONKS_API_KEY.",
            "distinct_event_ids": 0,
            "replay_pool_event_count": 0,
            "pending_cdm_event_count": 0,
            "only_pending_cdm": only_pending,
            "fixtures_targeted": 0,
            "unique_sportmonks_fixtures_processed": 0,
            "sm_fetch_ok": 0,
            "raw_upsert_ok": 0,
            "cdm_normalized_ok": 0,
            "cdm_skipped": 0,
            "cdm_errors": 0,
            "notes": ["sm:sin_api_key"],
        }

    lim_ids = max(1, int(max_events_per_day) * 3)
    seen_eids: set[int] = set()
    scan = d0
    while scan <= d1:
        odk = scan.isoformat()
        ds, de = bogota_operating_day_utc_window(odk)
        for eid in _list_event_ids_for_replay_day(cur, ds, de, limit=lim_ids):
            seen_eids.add(int(eid))
        scan += timedelta(days=1)

    if not seen_eids:
        return {
            "ok": True,
            "operating_day_key_from": operating_day_key_from.strip(),
            "operating_day_key_to": operating_day_key_to.strip(),
            "message_es": (
                f"Rango {operating_day_key_from} … {operating_day_key_to}: sin eventos candidatos "
                f"(replay pool, hasta {lim_ids} IDs/día)."
            ),
            "distinct_event_ids": 0,
            "fixtures_targeted": 0,
            "unique_sportmonks_fixtures_processed": 0,
            "sm_fetch_ok": 0,
            "raw_upsert_ok": 0,
            "cdm_normalized_ok": 0,
            "cdm_skipped": 0,
            "cdm_errors": 0,
            "only_pending_cdm": only_pending,
            "replay_pool_event_count": 0,
            "pending_cdm_event_count": 0,
            "notes": [],
        }

    ids_sorted = sorted(seen_eids)
    pool_n = len(ids_sorted)
    placeholders = ",".join(["%s"] * len(ids_sorted))
    pending_sql = ""
    if only_pending:
        pending_sql = " AND (e.result_home IS NULL OR e.result_away IS NULL)"
    cur.execute(
        f"""
        SELECT e.id AS event_id, e.sportmonks_fixture_id AS sm_fid
        FROM bt2_events e
        WHERE e.id IN ({placeholders}){pending_sql}
        ORDER BY e.id
        """,
        ids_sorted,
    )
    rows = cur.fetchall()
    pending_n = len(rows)

    if only_pending and not rows:
        return {
            "ok": True,
            "operating_day_key_from": operating_day_key_from.strip(),
            "operating_day_key_to": operating_day_key_to.strip(),
            "message_es": (
                f"Backtest-window SM→CDM {operating_day_key_from} … {operating_day_key_to}: "
                f"pool replay {pool_n} event_ids únicos; ninguno sin marcador CDM completo "
                f"(result_home/result_away); no hubo llamadas SM."
            ),
            "distinct_event_ids": pool_n,
            "pending_cdm_event_count": 0,
            "replay_pool_event_count": pool_n,
            "only_pending_cdm": True,
            "fixtures_targeted": 0,
            "unique_sportmonks_fixtures_processed": 0,
            "sm_fetch_ok": 0,
            "raw_upsert_ok": 0,
            "cdm_normalized_ok": 0,
            "cdm_skipped": 0,
            "cdm_errors": 0,
            "notes": [],
        }

    bf, bt = _bulk_between_range_for_monitor(
        operating_day_key_from.strip(),
        operating_day_key_to.strip(),
    )
    bulk_map, bulk_notes, _bulk_req = fetch_fixtures_between_dates(bf, bt, sportmonks_api_key)
    notes.extend(bulk_notes)
    core = _refresh_distinct_fixtures_from_pick_event_rows(
        cur, rows, sportmonks_api_key, fixture_payload_by_sm_id=bulk_map
    )
    sm_ok = int(core["sm_fetch_ok"])
    raw_ok = int(core["raw_upsert_ok"])
    cdm_ok = int(core["cdm_normalized_ok"])
    cdm_skip = int(core["cdm_skipped"])
    cdm_err = int(core["cdm_errors"])
    notes.extend(list(core["notes"]))
    targeted = int(core["fixtures_targeted"])

    scope = (
        f"solo CDM pendiente ({pending_n}/{pool_n} sin marcador completo)"
        if only_pending
        else f"todos los candidatos ({pool_n} event_ids)"
    )
    msg = (
        f"Backtest-window SM→CDM {operating_day_key_from} … {operating_day_key_to} "
        f"({scope}; max_events_per_day={int(max_events_per_day)}, hasta {lim_ids} IDs/día en pool): "
        f"SM {sm_ok} fetch OK, {raw_ok} raw UPSERT, {cdm_ok} CDM OK, {cdm_skip} omitidos, {cdm_err} errores CDM."
    )

    return {
        "ok": True,
        "operating_day_key_from": operating_day_key_from.strip(),
        "operating_day_key_to": operating_day_key_to.strip(),
        "message_es": msg,
        "distinct_event_ids": pool_n,
        "replay_pool_event_count": pool_n,
        "pending_cdm_event_count": pending_n,
        "only_pending_cdm": only_pending,
        "fixtures_targeted": targeted,
        "unique_sportmonks_fixtures_processed": int(core["unique_sportmonks_fixtures_processed"]),
        "sm_fetch_ok": sm_ok,
        "raw_upsert_ok": raw_ok,
        "cdm_normalized_ok": cdm_ok,
        "cdm_skipped": cdm_skip,
        "cdm_errors": cdm_err,
        "notes": notes[:80],
    }

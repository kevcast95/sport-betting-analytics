"""
T-238 / T-239 — Resumen operativo Fase 1 (pool + loop oficial + precisión por bucket).

`pool_eligibility_rate_pct` usa última fila de `bt2_pool_eligibility_audit` por evento candidato
(distinct `event_id` en `bt2_daily_picks` para el día). Sin auditoría → no elegible en el numerador.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

import psycopg2.errors

from apps.api.bt2_official_evaluation_job import (
    fetch_official_evaluation_loop_metrics,
    hit_rate_on_scored_pct,
)
from apps.api.bt2_pool_eligibility_v1 import fetch_latest_eligibility_by_event_ids

logger = logging.getLogger(__name__)


@runtime_checkable
class _DbCursor(Protocol):
    def execute(self, query: str, params: Any = None) -> None: ...
    def fetchall(self) -> list[Any]: ...
    def fetchone(self) -> Any: ...

    @property
    def connection(self) -> Any: ...


FASE1_ACCUMULATED_DAY_KEY = "__ALL__"


def fetch_candidate_event_ids_for_day(cur: _DbCursor, operating_day_key: str) -> list[int]:
    cur.execute(
        """
        SELECT DISTINCT event_id
        FROM bt2_daily_picks
        WHERE operating_day_key = %s
        ORDER BY event_id
        """,
        (operating_day_key,),
    )
    return [int(r["event_id"]) for r in cur.fetchall()]


def fetch_candidate_event_ids_all(cur: _DbCursor) -> list[int]:
    """Todos los `event_id` distintos que alguna vez aparecieron en picks sugeridos."""
    cur.execute(
        """
        SELECT DISTINCT event_id
        FROM bt2_daily_picks
        ORDER BY event_id
        """
    )
    return [int(r["event_id"]) for r in cur.fetchall()]


def compute_pool_coverage_block(
    candidate_event_ids: list[int],
    latest_audit: dict[int, tuple[bool, Optional[str]]],
) -> dict[str, Any]:
    n = len(candidate_event_ids)
    eligible = 0
    with_audit = 0
    discard_breakdown: dict[str, int] = {}
    for eid in candidate_event_ids:
        t = latest_audit.get(eid)
        if t is not None:
            with_audit += 1
            if t[0]:
                eligible += 1
            else:
                reason = t[1] or "(sin código)"
                discard_breakdown[reason] = discard_breakdown.get(reason, 0) + 1
        else:
            k = "(sin auditoría reciente)"
            discard_breakdown[k] = discard_breakdown.get(k, 0) + 1
    rate = round(100.0 * eligible / n, 2) if n else None
    return {
        "candidate_events_count": n,
        "eligible_events_count": eligible,
        "events_with_latest_audit": with_audit,
        "pool_eligibility_rate_pct": rate,
        "pool_discard_reason_breakdown": discard_breakdown,
    }


def _precision_bucket_rows(
    cur: _DbCursor, operating_day_key: Optional[str], group_expr: str
) -> list[dict[str, Any]]:
    if operating_day_key:
        where_sql = "WHERE dp.operating_day_key = %s"
        params: tuple[Any, ...] = (operating_day_key,)
    else:
        where_sql = ""
        params = ()
    cur.execute(
        f"""
        SELECT {group_expr} AS bk,
               COUNT(*) FILTER (WHERE e.evaluation_status = 'evaluated_hit')::int AS evaluated_hit,
               COUNT(*) FILTER (WHERE e.evaluation_status = 'evaluated_miss')::int AS evaluated_miss,
               COUNT(*) FILTER (WHERE e.evaluation_status = 'pending_result')::int AS pending_result,
               COUNT(*) FILTER (WHERE e.evaluation_status = 'no_evaluable')::int AS no_evaluable,
               COUNT(*) FILTER (WHERE e.evaluation_status = 'void')::int AS void_count
        FROM bt2_pick_official_evaluation e
        INNER JOIN bt2_daily_picks dp ON dp.id = e.daily_pick_id
        {where_sql}
        GROUP BY 1
        ORDER BY 1
        """,
        params,
    )
    rows: list[dict[str, Any]] = []
    for raw in cur.fetchall():
        r = dict(raw) if isinstance(raw, Mapping) else {}
        bk = str(r.get("bk") or "(vacío)")
        hit = int(r.get("evaluated_hit") or 0)
        miss = int(r.get("evaluated_miss") or 0)
        rows.append(
            {
                "bucket_key": bk,
                "evaluated_hit": hit,
                "evaluated_miss": miss,
                "pending_result": int(r.get("pending_result") or 0),
                "no_evaluable": int(r.get("no_evaluable") or 0),
                "void_count": int(r.get("void_count") or 0),
                "hit_rate_on_scored_pct": hit_rate_on_scored_pct(hit, miss),
            }
        )
    return rows


def fetch_precision_by_market(
    cur: _DbCursor, operating_day_key: Optional[str]
) -> list[dict[str, Any]]:
    return _precision_bucket_rows(
        cur,
        operating_day_key,
        "COALESCE(NULLIF(TRIM(e.market_canonical), ''), '(vacío)')",
    )


def fetch_precision_by_confidence(
    cur: _DbCursor, operating_day_key: Optional[str]
) -> list[dict[str, Any]]:
    return _precision_bucket_rows(
        cur,
        operating_day_key,
        "COALESCE(NULLIF(TRIM(dp.dsr_confidence_label), ''), '(sin etiqueta)')",
    )


def _loop_metrics_when_official_eval_table_missing(
    cur: _DbCursor, operating_day_key: Optional[str]
) -> dict[str, Any]:
    """Tras rollback: solo conteo de `bt2_daily_picks` (evaluación oficial no migrada)."""
    if operating_day_key:
        cur.execute(
            """
            SELECT COUNT(*)::int AS n
            FROM bt2_daily_picks
            WHERE operating_day_key = %s
            """,
            (operating_day_key,),
        )
    else:
        cur.execute("SELECT COUNT(*)::int AS n FROM bt2_daily_picks")
    row = cur.fetchone()
    r = dict(row) if isinstance(row, Mapping) else {}
    suggested = int(r.get("n") or 0)
    summary_es = (
        f"Picks sugeridos (daily_picks): {suggested}. "
        "La tabla bt2_pick_official_evaluation no existe en esta base — ejecute "
        "`alembic upgrade head` en el entorno del API."
    )
    return {
        "suggested_picks_count": suggested,
        "official_evaluation_enrolled": 0,
        "pending_result": 0,
        "evaluated_hit": 0,
        "evaluated_miss": 0,
        "void_count": 0,
        "no_evaluable": 0,
        "hit_rate_on_scored_pct": None,
        "no_evaluable_by_reason": {},
        "summary_human_es": summary_es,
        "operating_day_key_filter": operating_day_key,
    }


def build_fase1_operational_summary(
    cur: _DbCursor,
    operating_day_key: Optional[str],
    *,
    accumulated: bool = False,
) -> dict[str, Any]:
    """
    Si `accumulated` es True, `operating_day_key` se ignora: pool sobre todos los eventos
    candidatos históricos; loop y precisión sin filtro de día (misma semántica que
    `fetch_official_evaluation_loop_metrics(..., operating_day_key=None)`).
    """
    if accumulated:
        odk_for_metrics: Optional[str] = None
        response_odk = FASE1_ACCUMULATED_DAY_KEY
        cands = fetch_candidate_event_ids_all(cur)
    else:
        if not operating_day_key:
            raise ValueError("operating_day_key es obligatorio si accumulated es False")
        odk_for_metrics = operating_day_key
        response_odk = operating_day_key
        cands = fetch_candidate_event_ids_for_day(cur, operating_day_key)

    latest = fetch_latest_eligibility_by_event_ids(cur, cands)
    pool = compute_pool_coverage_block(cands, latest)
    try:
        loop = fetch_official_evaluation_loop_metrics(
            cur, operating_day_key=odk_for_metrics
        )
        by_m = fetch_precision_by_market(cur, odk_for_metrics)
        by_c = fetch_precision_by_confidence(cur, odk_for_metrics)
    except psycopg2.errors.UndefinedTable:
        cur.connection.rollback()
        logger.warning(
            "bt2_pick_official_evaluation (u otra relación del loop) ausente: "
            "alembic upgrade head. Devolviendo métricas de loop/precisión vacías."
        )
        loop = _loop_metrics_when_official_eval_table_missing(cur, odk_for_metrics)
        by_m = []
        by_c = []

    pe = pool["pool_eligibility_rate_pct"]
    hr = loop.get("hit_rate_on_scored_pct")
    pe_s = f"{pe}%" if pe is not None else "n/d"
    hr_s = f"{hr}%" if hr is not None else "n/d"
    if accumulated:
        summary_es = (
            "Vista acumulada (todos los `operating_day_key` con picks en BT2): "
            f"pool elegibilidad {pe_s} "
            f"({pool['eligible_events_count']}/{pool['candidate_events_count']} eventos distintos). "
            f"Loop oficial — hit rate scored {hr_s} "
            f"({loop.get('evaluated_hit')} hit / {loop.get('evaluated_miss')} miss). "
            f"Pendientes evaluación: {loop.get('pending_result')}, no evaluable: {loop.get('no_evaluable')}."
        )
    else:
        summary_es = (
            f"Día operativo {response_odk}: "
            f"pool elegibilidad {pe_s} "
            f"({pool['eligible_events_count']}/{pool['candidate_events_count']} eventos). "
            f"Loop oficial — hit rate scored {hr_s} "
            f"({loop.get('evaluated_hit')} hit / {loop.get('evaluated_miss')} miss). "
            f"Pendientes evaluación: {loop.get('pending_result')}, no evaluable: {loop.get('no_evaluable')}."
        )

    return {
        "operating_day_key": response_odk,
        "pool_coverage": pool,
        "official_evaluation_loop": loop,
        "precision_by_market": by_m,
        "precision_by_confidence": by_c,
        "summary_human_es": summary_es,
    }

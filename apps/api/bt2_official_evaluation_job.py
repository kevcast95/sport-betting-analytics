"""
T-231 / T-232 — Cierre de loop: backfill + evaluación oficial batch (idempotente).

- Crea filas `bt2_pick_official_evaluation` para `bt2_daily_picks` sin fila (estado inicial `pending_result`).
- Solo actualiza filas aún en `pending_result`; estados finales no se sobrescriben.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

from psycopg2.extras import Json

from apps.api.bt2_official_truth_resolver import (
    OfficialEvaluationResolution,
    resolve_official_evaluation_from_cdm_truth,
)


@dataclass(frozen=True)
class OfficialEvaluationJobStats:
    backfill_inserted: int
    examined: int
    closed_final: int  # pasaron a hit/miss/void/no_evaluable en esta corrida
    still_pending: int  # siguen pending_result tras aplicar resolver


@runtime_checkable
class _DbCursor(Protocol):
    def execute(self, query: str, params: Any = None) -> None: ...
    def fetchall(self) -> list[Any]: ...
    def fetchone(self) -> Any: ...
    @property
    def rowcount(self) -> int: ...


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def apply_resolution_for_storage(
    resolution: OfficialEvaluationResolution, now: datetime
) -> dict[str, Any]:
    """Columnas a persistir; `evaluated_at` solo para estados distintos de `pending_result`."""
    ev_at: Optional[datetime] = None if resolution.evaluation_status == "pending_result" else now
    return {
        "evaluation_status": resolution.evaluation_status,
        "no_evaluable_reason": resolution.no_evaluable_reason,
        "truth_source": resolution.truth_source,
        "truth_payload_ref": resolution.truth_payload_ref,
        "evaluated_at": ev_at,
    }


def run_backfill_missing_evaluations(
    cur: _DbCursor,
    *,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> int:
    """
    Inserta una fila de evaluación por cada `bt2_daily_picks` sin `bt2_pick_official_evaluation`.
    Idempotente: no duplica `daily_pick_id`.
    """
    lim_sql = ""
    params: list[Any] = []
    if limit is not None:
        lim_sql = "LIMIT %s"
        params.append(limit)

    sub = f"""
        SELECT dp.id AS daily_pick_id,
               dp.event_id,
               COALESCE(NULLIF(TRIM(dp.model_market_canonical), ''), '') AS market_canonical,
               COALESCE(NULLIF(TRIM(dp.model_selection_canonical), ''), '') AS selection_canonical,
               dp.dsr_confidence_label,
               dp.suggested_at
        FROM bt2_daily_picks dp
        WHERE NOT EXISTS (
            SELECT 1 FROM bt2_pick_official_evaluation e
            WHERE e.daily_pick_id = dp.id
        )
        ORDER BY dp.id
        {lim_sql}
    """
    if dry_run:
        cur.execute(f"SELECT COUNT(*) AS n FROM ({sub}) x", tuple(params))
        row = cur.fetchone()
        return int(row["n"] if isinstance(row, Mapping) else row[0])

    cur.execute(
        f"""
        INSERT INTO bt2_pick_official_evaluation (
            daily_pick_id, event_id, market_canonical, selection_canonical,
            dsr_confidence_label, suggested_at, evaluation_status
        )
        SELECT daily_pick_id, event_id, market_canonical, selection_canonical,
               dsr_confidence_label, suggested_at, 'pending_result'
        FROM ({sub}) src
        """,
        tuple(params),
    )
    return cur.rowcount


def run_evaluate_pending_rows(
    cur: _DbCursor,
    *,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> tuple[int, int, int]:
    """
    Lee filas `pending_result`, aplica resolver con `bt2_events`, actualiza fila.

    Returns:
        (examined, closed_final, still_pending)
    """
    lim_sql = ""
    params: list[Any] = []
    if limit is not None:
        lim_sql = "LIMIT %s"
        params.append(limit)

    # BTTS pasó de “fuera de mercado v1” a soportado: reabrir para re-evaluar con marcador.
    if not dry_run:
        cur.execute(
            """
            UPDATE bt2_pick_official_evaluation
            SET evaluation_status = 'pending_result',
                no_evaluable_reason = NULL,
                truth_source = NULL,
                truth_payload_ref = NULL,
                evaluated_at = NULL,
                updated_at = NOW()
            WHERE evaluation_status = 'no_evaluable'
              AND no_evaluable_reason = 'OUTSIDE_SUPPORTED_MARKET_V1'
              AND UPPER(TRIM(COALESCE(market_canonical, ''))) = 'BTTS'
            """
        )

    cur.execute(
        f"""
        SELECT e.id AS eval_id,
               e.market_canonical,
               e.selection_canonical,
               ev.result_home,
               ev.result_away,
               ev.status AS event_status
        FROM bt2_pick_official_evaluation e
        INNER JOIN bt2_events ev ON ev.id = e.event_id
        WHERE e.evaluation_status = 'pending_result'
        ORDER BY e.id
        {lim_sql}
        """,
        tuple(params),
    )
    rows = cur.fetchall()
    examined = len(rows)
    closed_final = 0
    still_pending = 0
    now = _utcnow()

    for row in rows:
        r = dict(row) if isinstance(row, Mapping) else {
            "eval_id": row[0],
            "market_canonical": row[1],
            "selection_canonical": row[2],
            "result_home": row[3],
            "result_away": row[4],
            "event_status": row[5],
        }
        mc = (r.get("market_canonical") or "").strip() or None
        sc = (r.get("selection_canonical") or "").strip() or None
        resolution = resolve_official_evaluation_from_cdm_truth(
            market_canonical=mc,
            selection_canonical=sc,
            result_home=r.get("result_home"),
            result_away=r.get("result_away"),
            event_status=r.get("event_status"),
        )
        if resolution.evaluation_status == "pending_result":
            still_pending += 1
        else:
            closed_final += 1

        if dry_run:
            continue

        cols = apply_resolution_for_storage(resolution, now)
        cur.execute(
            """
            UPDATE bt2_pick_official_evaluation
            SET evaluation_status = %s,
                no_evaluable_reason = %s,
                truth_source = %s,
                truth_payload_ref = %s,
                evaluated_at = CASE
                    WHEN %s = 'pending_result' THEN NULL
                    ELSE %s
                END,
                updated_at = NOW()
            WHERE id = %s
              AND evaluation_status = 'pending_result'
            """,
            (
                cols["evaluation_status"],
                cols["no_evaluable_reason"],
                cols["truth_source"],
                Json(cols["truth_payload_ref"]) if cols["truth_payload_ref"] is not None else None,
                cols["evaluation_status"],
                now,
                r["eval_id"],
            ),
        )

    return examined, closed_final, still_pending


def run_official_evaluation_job(
    cur: _DbCursor,
    *,
    limit_backfill: Optional[int] = None,
    limit_evaluate: Optional[int] = None,
    dry_run: bool = False,
    skip_backfill: bool = False,
    skip_evaluate: bool = False,
) -> OfficialEvaluationJobStats:
    ins = 0
    if not skip_backfill:
        ins = run_backfill_missing_evaluations(
            cur, limit=limit_backfill, dry_run=dry_run
        )
    examined = closed = still_p = 0
    if not skip_evaluate:
        examined, closed, still_p = run_evaluate_pending_rows(
            cur, limit=limit_evaluate, dry_run=dry_run
        )
    return OfficialEvaluationJobStats(
        backfill_inserted=ins,
        examined=examined,
        closed_final=closed,
        still_pending=still_p,
    )


def job_summary_dict(stats: OfficialEvaluationJobStats) -> dict[str, Any]:
    """Salida estable para logs / T-233 (contadores básicos)."""
    return {
        "backfill_inserted_or_would": stats.backfill_inserted,
        "pending_rows_examined": stats.examined,
        "closed_to_final_this_run": stats.closed_final,
        "still_pending_after_run": stats.still_pending,
    }


def hit_rate_on_scored_pct(hit: int, miss: int) -> Optional[float]:
    """Hit rate solo sobre filas con resultado binario (excluye void, no_evaluable, pending)."""
    d = hit + miss
    if d <= 0:
        return None
    return round(100.0 * hit / d, 2)


def fetch_official_evaluation_loop_metrics(
    cur: _DbCursor,
    *,
    operating_day_key: Optional[str] = None,
) -> dict[str, Any]:
    """
    T-233 — Contadores del loop oficial (tabla `bt2_pick_official_evaluation`).

    Opcionalmente filtra por `operating_day_key` del pick sugerido (`bt2_daily_picks`).
    Incluye desglose de `no_evaluable` por `no_evaluable_reason` (base T-239).
    """
    params: tuple[Any, ...]
    if operating_day_key:
        join_e = """
            FROM bt2_pick_official_evaluation e
            INNER JOIN bt2_daily_picks dp ON dp.id = e.daily_pick_id
            WHERE dp.operating_day_key = %s
        """
        params = (operating_day_key,)
        dp_where = "WHERE operating_day_key = %s"
    else:
        join_e = "FROM bt2_pick_official_evaluation e"
        params = ()
        dp_where = ""

    cur.execute(
        f"""
        SELECT
            COUNT(*)::int AS official_eval_rows,
            COUNT(*) FILTER (WHERE e.evaluation_status = 'pending_result')::int AS pending_result,
            COUNT(*) FILTER (WHERE e.evaluation_status = 'evaluated_hit')::int AS evaluated_hit,
            COUNT(*) FILTER (WHERE e.evaluation_status = 'evaluated_miss')::int AS evaluated_miss,
            COUNT(*) FILTER (WHERE e.evaluation_status = 'void')::int AS void_count,
            COUNT(*) FILTER (WHERE e.evaluation_status = 'no_evaluable')::int AS no_evaluable
        {join_e}
        """,
        params,
    )
    agg = cur.fetchone()
    row = dict(agg) if isinstance(agg, Mapping) else {}

    cur.execute(
        f"SELECT COUNT(*)::int AS n FROM bt2_daily_picks {dp_where}",
        params,
    )
    spr = cur.fetchone()
    suggested = int(
        (spr["n"] if isinstance(spr, Mapping) else spr[0]) or 0
    )

    breakdown: dict[str, int] = {}
    if operating_day_key:
        cur.execute(
            """
            SELECT COALESCE(e.no_evaluable_reason, '') AS reason, COUNT(*)::int AS c
            FROM bt2_pick_official_evaluation e
            INNER JOIN bt2_daily_picks dp ON dp.id = e.daily_pick_id
            WHERE dp.operating_day_key = %s
              AND e.evaluation_status = 'no_evaluable'
            GROUP BY e.no_evaluable_reason
            """,
            (operating_day_key,),
        )
    else:
        cur.execute(
            """
            SELECT COALESCE(no_evaluable_reason, '') AS reason, COUNT(*)::int AS c
            FROM bt2_pick_official_evaluation
            WHERE evaluation_status = 'no_evaluable'
            GROUP BY no_evaluable_reason
            """,
        )
    for r in cur.fetchall():
        rr = dict(r) if isinstance(r, Mapping) else {"reason": r[0], "c": r[1]}
        key = (rr.get("reason") or "") or "(sin código)"
        breakdown[key] = int(rr["c"] or 0)

    hit = int(row.get("evaluated_hit") or 0)
    miss = int(row.get("evaluated_miss") or 0)
    rate = hit_rate_on_scored_pct(hit, miss)
    pend = int(row.get("pending_result") or 0)
    ne = int(row.get("no_evaluable") or 0)
    void_c = int(row.get("void_count") or 0)
    enrolled = int(row.get("official_eval_rows") or 0)

    summary_es = (
        f"Picks sugeridos (daily_picks): {suggested}. "
        f"Con fila de evaluación oficial: {enrolled}. "
        f"Pendientes de resultado: {pend}. "
        f"Hit {hit} / Miss {miss}"
        + (f" → hit rate {rate}% sobre scored." if rate is not None else " → sin hit rate (0 scored).")
        + f" Void {void_c}, no evaluable {ne}."
    )

    return {
        "suggested_picks_count": suggested,
        "official_evaluation_enrolled": enrolled,
        "pending_result": pend,
        "evaluated_hit": hit,
        "evaluated_miss": miss,
        "void_count": void_c,
        "no_evaluable": ne,
        "hit_rate_on_scored_pct": rate,
        "no_evaluable_by_reason": breakdown,
        "summary_human_es": summary_es,
        "operating_day_key_filter": operating_day_key,
    }

"""
Monitor de resultados — agregados y filas desde `bt2_daily_picks` + evaluación oficial.

- Sistema: todas las filas `bt2_daily_picks` en el rango [from, to] de `operating_day_key`.
- Tus picks (opcional): mismo criterio pero `dp.user_id = monitor_user_id` y existe `bt2_picks`
  abierto el mismo día operativo (timezone America/Bogota) para ese usuario y evento.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from apps.api.bt2_dsr_ds_input_builder import aggregated_odds_for_event_psycopg
from apps.api.bt2_dsr_odds_aggregation import consensus_decimal_for_canonical_pick
from apps.api.bt2_market_canonical import market_canonical_label_es, selection_canonical_summary_es
from apps.api.bt2_official_truth_resolver import normalize_official_eval_market

# Vista admin: incluir cuotas que en el pipeline de valor se filtran con min 1.30 — si no, muchas
# filas quedan sin mediana aunque exista snapshot CDM (p. ej. solo casas con cuota < 1.30 en una pierna).
_MONITOR_CONSENSUS_MIN_DECIMAL = 1.01


def _consensus_decimal_for_pick_row(
    consensus: dict[str, dict[str, float]],
    market_canonical: str,
    selection_canonical: str,
) -> Optional[float]:
    """Alinea claves de mercado al diccionario consensus (p. ej. 1X2 → FT_1X2)."""
    mc_in = (market_canonical or "").strip()
    key = normalize_official_eval_market(mc_in)
    if key is None:
        key = mc_in
    dec = consensus_decimal_for_canonical_pick(consensus, key, selection_canonical)
    if dec is not None:
        return dec
    if key != mc_in:
        return consensus_decimal_for_canonical_pick(consensus, mc_in, selection_canonical)
    return None


def _roi_flat_stake_accumulate(
    *,
    outcome_ui: str,
    decimal_odds: Optional[float],
    net_units: float,
    picks_counted: int,
    picks_missing_odds: int,
) -> tuple[float, int, int]:
    """Stake fijo 1 u: acierto +(O-1), fallo -1; sin cuota no cuenta."""
    if outcome_ui not in ("si", "no"):
        return net_units, picks_counted, picks_missing_odds
    if decimal_odds is None:
        return net_units, picks_counted, picks_missing_odds + 1
    ru = float(decimal_odds - 1.0) if outcome_ui == "si" else -1.0
    return net_units + ru, picks_counted + 1, picks_missing_odds


def _roi_flat_stake_payload(net: float, n_ok: int, n_missing: int) -> dict[str, Any]:
    roi_pct = round(100.0 * net / n_ok, 2) if n_ok > 0 else None
    return {
        "net_units": round(net, 4),
        "roi_pct": roi_pct,
        "picks_counted": n_ok,
        "picks_missing_odds": n_missing,
    }


def evaluation_status_to_outcome_ui(st: Optional[str]) -> str:
    """Frontend OutcomeBadge: si | no | pendiente | void | ne."""
    if not st or st == "pending_result":
        return "pendiente"
    if st == "evaluated_hit":
        return "si"
    if st == "evaluated_miss":
        return "no"
    if st == "void":
        return "void"
    if st == "no_evaluable":
        return "ne"
    return "pendiente"


def _agg_from_counts(
    *,
    n: int,
    hits: int,
    misses: int,
    pending: int,
    void_c: int,
    ne: int,
) -> dict[str, Any]:
    scored = hits + misses
    rate = round(100.0 * hits / scored, 2) if scored else None
    return {
        "total_picks": n,
        "hits": hits,
        "misses": misses,
        "pending": pending,
        "void_count": void_c,
        "no_evaluable": ne,
        "evaluated_scored": scored,
        "hit_rate_pct": rate,
    }


def _fetch_aggregate(
    cur: Any,
    *,
    sql_where: str,
    params: tuple[Any, ...],
) -> dict[str, Any]:
    cur.execute(
        f"""
        SELECT
            COUNT(*)::int AS n,
            COUNT(*) FILTER (WHERE COALESCE(e.evaluation_status, 'pending_result') = 'evaluated_hit')::int AS hits,
            COUNT(*) FILTER (WHERE COALESCE(e.evaluation_status, 'pending_result') = 'evaluated_miss')::int AS misses,
            COUNT(*) FILTER (
                WHERE COALESCE(e.evaluation_status, 'pending_result') = 'pending_result'
            )::int AS pending,
            COUNT(*) FILTER (WHERE COALESCE(e.evaluation_status, 'pending_result') = 'void')::int AS void_c,
            COUNT(*) FILTER (WHERE COALESCE(e.evaluation_status, 'pending_result') = 'no_evaluable')::int AS ne
        FROM bt2_daily_picks dp
        LEFT JOIN bt2_pick_official_evaluation e ON e.daily_pick_id = dp.id
        WHERE {sql_where}
        """,
        params,
    )
    row = cur.fetchone()
    if not row:
        return _agg_from_counts(n=0, hits=0, misses=0, pending=0, void_c=0, ne=0)
    return _agg_from_counts(
        n=int(row["n"] or 0),
        hits=int(row["hits"] or 0),
        misses=int(row["misses"] or 0),
        pending=int(row["pending"] or 0),
        void_c=int(row["void_c"] or 0),
        ne=int(row["ne"] or 0),
    )


def _today_block(cur: Any, *, today_key: str) -> dict[str, Any]:
    cur.execute(
        """
        SELECT
            COUNT(*)::int AS n,
            COUNT(*) FILTER (
                WHERE COALESCE(e.evaluation_status, 'pending_result') <> 'pending_result'
            )::int AS resolved,
            COUNT(*) FILTER (
                WHERE COALESCE(e.evaluation_status, 'pending_result') = 'pending_result'
            )::int AS pending
        FROM bt2_daily_picks dp
        LEFT JOIN bt2_pick_official_evaluation e ON e.daily_pick_id = dp.id
        WHERE dp.operating_day_key = %s
        """,
        (today_key,),
    )
    row = cur.fetchone() or {}
    return {
        "operating_day_key": today_key,
        "total_picks": int(row.get("n") or 0),
        "resolved": int(row.get("resolved") or 0),
        "pending": int(row.get("pending") or 0),
    }


def _monitor_outcome_filter_to_eval_status(ui: Optional[str]) -> Optional[str]:
    if not ui or ui == "all":
        return None
    return {
        "si": "evaluated_hit",
        "no": "evaluated_miss",
        "pendiente": "pending_result",
        "void": "void",
        "ne": "no_evaluable",
    }.get(ui.strip())


def build_monitor_resultados_payload(
    cur: Any,
    *,
    operating_day_key_from: str,
    operating_day_key_to: str,
    monitor_user_id: Optional[str] = None,
    rows_limit: int = 1500,
    rows_offset: int = 0,
    outcome_filter: Optional[str] = None,
    market_substring: Optional[str] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    """
    Construye el payload JSON-serializable para GET admin monitor-resultados.
    """
    tz = "America/Bogota"
    lim = max(1, min(int(rows_limit or 1500), 3000))
    off = max(0, int(rows_offset or 0))

    base_range = (
        "dp.operating_day_key >= %s AND dp.operating_day_key <= %s",
        (operating_day_key_from, operating_day_key_to),
    )
    system_base = _fetch_aggregate(cur, sql_where=base_range[0], params=base_range[1])

    monitor_uid_trimmed = str(monitor_user_id).strip() if monitor_user_id else ""
    yours_base: Optional[dict[str, Any]] = None
    if monitor_uid_trimmed:
        operated = (
            "dp.operating_day_key >= %s AND dp.operating_day_key <= %s "
            "AND dp.user_id = %s::uuid "
            "AND EXISTS ("
            " SELECT 1 FROM bt2_picks pk "
            " WHERE pk.user_id = dp.user_id AND pk.event_id = dp.event_id "
            f" AND (timezone('{tz}', pk.opened_at))::date = dp.operating_day_key::date"
            ")"
        )
        yours_base = _fetch_aggregate(
            cur,
            sql_where=operated,
            params=(operating_day_key_from, operating_day_key_to, monitor_uid_trimmed),
        )

    try:
        from zoneinfo import ZoneInfo

        tzinfo = ZoneInfo(tz)
    except Exception:
        tzinfo = timezone.utc
    calendar_today_key = datetime.now(tz=tzinfo).date().isoformat()
    # Tarjeta «hoy»: si el cliente pide un solo día (p. ej. preset Hoy), el resumen debe ser
    # ese día — no solo la fecha calendario del servidor (evita desalineación en ventana UTC).
    if operating_day_key_from == operating_day_key_to:
        focus_day_key = operating_day_key_from
    else:
        focus_day_key = calendar_today_key
    today_summary = _today_block(cur, today_key=focus_day_key)

    base_where = "dp.operating_day_key >= %s AND dp.operating_day_key <= %s"
    params_base: list[Any] = [operating_day_key_from, operating_day_key_to]
    extra_where: list[str] = []
    eval_st = _monitor_outcome_filter_to_eval_status(outcome_filter)
    if eval_st:
        extra_where.append("COALESCE(e.evaluation_status, 'pending_result') = %s")
        params_base.append(eval_st)
    ms = (market_substring or "").strip()
    if ms:
        extra_where.append(
            "COALESCE(e.market_canonical, dp.model_market_canonical, '') ILIKE %s"
        )
        params_base.append(f"%{ms}%")
    sq = (search or "").strip()
    if sq:
        extra_where.append(
            "(COALESCE(ht.name, '') ILIKE %s OR COALESCE(at2.name, '') ILIKE %s)"
        )
        like = f"%{sq}%"
        params_base.extend([like, like])

    where_sql = base_where + ((" AND " + " AND ".join(extra_where)) if extra_where else "")

    cur.execute(
        f"""
        SELECT COUNT(*)::int AS c
        FROM bt2_daily_picks dp
        LEFT JOIN bt2_pick_official_evaluation e ON e.daily_pick_id = dp.id
        INNER JOIN bt2_events ev ON ev.id = dp.event_id
        LEFT JOIN bt2_teams ht ON ht.id = ev.home_team_id
        LEFT JOIN bt2_teams at2 ON at2.id = ev.away_team_id
        WHERE {where_sql}
        """,
        tuple(params_base),
    )
    crow = cur.fetchone()
    rows_total = int(crow["c"] if isinstance(crow, Mapping) else crow[0]) if crow else 0

    cur.execute(
        f"""
        SELECT
            dp.id AS daily_pick_id,
            dp.operating_day_key,
            dp.user_id::text AS user_id,
            dp.event_id,
            dp.reference_decimal_odds AS reference_decimal_odds,
            COALESCE(e.market_canonical, dp.model_market_canonical, '') AS mmc,
            COALESCE(e.selection_canonical, dp.model_selection_canonical, '') AS msc,
            COALESCE(e.evaluation_status, 'pending_result') AS evaluation_status,
            ev.result_home,
            ev.result_away,
            COALESCE(ht.name, '') AS home_team,
            COALESCE(at2.name, '') AS away_team,
            EXISTS (
                SELECT 1 FROM bt2_picks pk
                WHERE pk.user_id = dp.user_id AND pk.event_id = dp.event_id
                  AND (timezone('{tz}', pk.opened_at))::date = dp.operating_day_key::date
            ) AS i_operated,
            (
                SELECT pk2.user_result_claim
                FROM bt2_picks pk2
                WHERE pk2.user_id = dp.user_id AND pk2.event_id = dp.event_id
                ORDER BY pk2.opened_at DESC NULLS LAST
                LIMIT 1
            ) AS user_result_claim
        FROM bt2_daily_picks dp
        LEFT JOIN bt2_pick_official_evaluation e ON e.daily_pick_id = dp.id
        INNER JOIN bt2_events ev ON ev.id = dp.event_id
        LEFT JOIN bt2_teams ht ON ht.id = ev.home_team_id
        LEFT JOIN bt2_teams at2 ON at2.id = ev.away_team_id
        WHERE {where_sql}
        ORDER BY dp.operating_day_key DESC, dp.id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params_base + [lim, off]),
    )
    raw_rows = cur.fetchall()

    consensus_cache: dict[int, dict[str, dict[str, float]]] = {}
    rows_out: list[dict[str, Any]] = []
    sys_net: float = 0.0
    sys_nc: int = 0
    sys_nm: int = 0
    your_net: float = 0.0
    your_nc: int = 0
    your_nm: int = 0

    for r in raw_rows:
        mmc = str(r.get("mmc") or "")
        msc = str(r.get("msc") or "")
        home = str(r.get("home_team") or "Local")
        away = str(r.get("away_team") or "Visitante")
        rh, ra = r.get("result_home"), r.get("result_away")
        if rh is not None and ra is not None:
            score_text = f"{int(rh)}-{int(ra)}"
        else:
            score_text = "—"

        sel_es = selection_canonical_summary_es(
            mmc or None,
            msc or None,
            home_team=home,
            away_team=away,
        )
        if not sel_es:
            sel_es = msc or "—"

        eid = int(r["event_id"])
        if eid not in consensus_cache:
            agg, _ = aggregated_odds_for_event_psycopg(
                cur, eid, min_decimal=_MONITOR_CONSENSUS_MIN_DECIMAL
            )
            consensus_cache[eid] = agg.consensus
        consensus = consensus_cache[eid]
        ref_p = r.get("reference_decimal_odds")
        dec: Optional[float] = None
        if ref_p is not None:
            try:
                fd = float(ref_p)
                dec = fd if fd > 1.0 else None
            except (TypeError, ValueError):
                dec = None
        if dec is None:
            dec = _consensus_decimal_for_pick_row(consensus, mmc, msc)
        outcome_ui = evaluation_status_to_outcome_ui(str(r.get("evaluation_status")))

        sys_net, sys_nc, sys_nm = _roi_flat_stake_accumulate(
            outcome_ui=outcome_ui,
            decimal_odds=dec,
            net_units=sys_net,
            picks_counted=sys_nc,
            picks_missing_odds=sys_nm,
        )

        row_uid = str(r["user_id"])
        if monitor_uid_trimmed and row_uid == monitor_uid_trimmed and bool(r.get("i_operated")):
            your_net, your_nc, your_nm = _roi_flat_stake_accumulate(
                outcome_ui=outcome_ui,
                decimal_odds=dec,
                net_units=your_net,
                picks_counted=your_nc,
                picks_missing_odds=your_nm,
            )

        ru: Optional[float]
        if outcome_ui == "si" and dec is not None:
            ru = round(float(dec) - 1.0, 4)
        elif outcome_ui == "no" and dec is not None:
            ru = -1.0
        else:
            ru = None

        rows_out.append(
            {
                "daily_pick_id": int(r["daily_pick_id"]),
                "operating_day_key": str(r["operating_day_key"]),
                "event_id": eid,
                "user_id": row_uid,
                "event_label": f"{home} vs {away}",
                "market_label_es": market_canonical_label_es(mmc or None),
                "selection_summary_es": sel_es,
                "score_text": score_text,
                "outcome": outcome_ui,
                "i_operated": bool(r.get("i_operated")),
                "decimal_odds": dec,
                "flat_stake_return_units": ru,
                "user_result_claim": r.get("user_result_claim"),
            }
        )

    roi_sys = _roi_flat_stake_payload(sys_net, sys_nc, sys_nm)
    system: dict[str, Any] = {**system_base, "roi_flat_stake": roi_sys}

    yours: Optional[dict[str, Any]]
    if yours_base is not None:
        yours = {**yours_base, "roi_flat_stake": _roi_flat_stake_payload(your_net, your_nc, your_nm)}
    else:
        yours = None

    sp = system_base["hits"] + system_base["misses"]
    summary_human_es = (
        f"Rango {operating_day_key_from} … {operating_day_key_to} (TZ ref {tz}). "
        f"Sistema: {system_base['total_picks']} filas en bóveda; "
        f"scored {sp} (hit {system_base['hits']}, miss {system_base['misses']}); "
        f"pendientes {system_base['pending']}, void {system_base['void_count']}, "
        f"N.E. {system_base['no_evaluable']}."
    )
    if system_base.get("hit_rate_pct") is not None:
        summary_human_es += f" Tasa hit/(hit+miss): {system_base['hit_rate_pct']} %."
    if roi_sys["picks_counted"] > 0 and roi_sys.get("roi_pct") is not None:
        summary_human_es += (
            f" ROI plano 1 u @ consenso (solo SI/NO con cuota): {roi_sys['roi_pct']} % "
            f"(net {roi_sys['net_units']} u sobre {roi_sys['picks_counted']} picks)."
        )
        if roi_sys.get("picks_missing_odds", 0) > 0:
            summary_human_es += f" Sin cuota en consenso: {roi_sys['picks_missing_odds']} scored."

    return {
        "operating_day_key_from": operating_day_key_from,
        "operating_day_key_to": operating_day_key_to,
        "timezone_label": tz,
        "today_operating_day_key": calendar_today_key,
        "focus_operating_day_key": focus_day_key,
        "system": system,
        "yours": yours,
        "today": today_summary,
        "rows": rows_out,
        "rows_total": rows_total,
        "rows_offset": off,
        "rows_limit": lim,
        "summary_human_es": summary_human_es,
        "sm_sync": {
            "attempted": False,
            "ok": True,
            "message_es": "",
            "pending_only": True,
            "fixtures_targeted": 0,
            "unique_fixtures_processed": 0,
            "closed_pending_to_final": None,
            "notes": [],
        },
    }


def filter_rows_for_mine(rows: list[Mapping[str, Any]], *, monitor_user_id: str) -> list[dict[str, Any]]:
    """Filas vista «Solo los que tomé»: usuario monitor y pick operado ese día."""
    uid = monitor_user_id.strip()
    out: list[dict[str, Any]] = []
    for r in rows:
        if str(r.get("user_id")) == uid and bool(r.get("i_operated")):
            out.append(dict(r))
    return out

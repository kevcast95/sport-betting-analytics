"""
Replay / backtest admin — reconstruye ds_input desde Postgres por día y ejecuta DSR en modo ciego.

- Odds: solo snapshots con `fetched_at` <= fin del día operativo America/Bogota (UTC).
- DSR: `schedule_display` y sellos temporales anonimizados; `operating_day_key` del lote = constante sintética.
- Post-DSR: comparación contra `bt2_events` (resultados CDM ya persistidos).
"""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from apps.api.bt2_dsr_ds_input_builder import (
    aggregated_odds_for_event_psycopg,
    apply_postgres_context_to_ds_item,
    build_ds_input_item,
)
from apps.api.bt2_dsr_deepseek import deepseek_suggest_batch
from apps.api.bt2_dsr_odds_aggregation import (
    data_completeness_score,
    event_passes_value_pool,
    premium_tier_eligible,
)
from apps.api.bt2_dsr_postprocess import postprocess_dsr_pick
from apps.api.bt2_dsr_suggest import suggest_sql_stat_fallback_from_consensus
from apps.api.bt2_market_canonical import market_canonical_label_es, selection_canonical_summary_es
from apps.api.bt2_official_truth_resolver import resolve_official_evaluation_from_cdm_truth
from apps.api.bt2_monitor_resultados import evaluation_status_to_outcome_ui
from apps.api.bt2_settings import bt2_settings
from apps.api.bt2_value_pool import MIN_ODDS_DECIMAL_DEFAULT

# Día sintético único en prompts DeepSeek / envelope (no revela calendario real).
BLIND_LOT_OPERATING_DAY_KEY = "2099-06-15"
# Cobertura “útil”: score de completitud de mercados en el input (0–100) >= umbral.
USEFUL_INPUT_MIN_SCORE = 50


def _tier_rank(tier: Optional[str]) -> int:
    t = (tier or "").upper()
    return {"S": 1, "A": 2, "B": 3}.get(t, 4)


def bogota_operating_day_utc_window(operating_day_key: str) -> tuple[datetime, datetime]:
    """Inicio/fin del día calendario America/Bogota como intervalo en UTC (fin exclusivo)."""
    try:
        from zoneinfo import ZoneInfo

        z = ZoneInfo("America/Bogota")
    except Exception:
        z = timezone.utc
    d = date.fromisoformat(operating_day_key)
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=z)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def kickoff_day_key_bogota(kickoff_utc: Optional[datetime]) -> str:
    if kickoff_utc is None:
        return ""
    try:
        from zoneinfo import ZoneInfo

        z = ZoneInfo("America/Bogota")
    except Exception:
        z = timezone.utc
    ko = kickoff_utc
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    return ko.astimezone(z).date().isoformat()


def blind_ds_input_item(item: dict[str, Any]) -> dict[str, Any]:
    """
    Elimina calendario real explícito para el modelo. Conserva equipos, liga, odds y diagnósticos.
    """
    out = copy.deepcopy(item)
    out["schedule_display"] = {
        "utc_iso": "2099-06-15T20:00:00Z",
        "timezone_reference": "UTC",
    }
    ec = dict(out.get("event_context") or {})
    ec.pop("start_timestamp_unix", None)
    out["event_context"] = ec
    return out


def _load_event_row_for_replay(cur: Any, event_id: int) -> Optional[Mapping[str, Any]]:
    cur.execute(
        """
        SELECT
            e.id,
            e.kickoff_utc,
            e.status,
            e.result_home,
            e.result_away,
            COALESCE(l.name, '') AS league_name,
            l.country AS league_country,
            l.tier AS league_tier,
            COALESCE(th.name, '') AS home_team_name,
            COALESCE(ta.name, '') AS away_team_name,
            e.home_team_id,
            e.away_team_id,
            e.sportmonks_fixture_id
        FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE e.id = %s
        """,
        (event_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _count_candidate_events(cur: Any, day_start_utc: datetime, day_end_utc: datetime) -> int:
    cur.execute(
        """
        SELECT COUNT(*)::int AS c
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        WHERE e.kickoff_utc >= %s
          AND e.kickoff_utc < %s
          AND l.is_active = true
          AND lower(coalesce(e.status, '')) NOT IN (
              'cancelled', 'canceled', 'postponed', 'abandoned', 'awarded'
          )
        """,
        (day_start_utc, day_end_utc),
    )
    row = cur.fetchone()
    if isinstance(row, Mapping):
        return int(row.get("c") or 0)
    return int(row[0] or 0) if row else 0


def _list_event_ids_for_replay_day(
    cur: Any,
    day_start_utc: datetime,
    day_end_utc: datetime,
    *,
    limit: int,
) -> list[int]:
    cur.execute(
        """
        SELECT e.id
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        WHERE e.kickoff_utc >= %s
          AND e.kickoff_utc < %s
          AND l.is_active = true
          AND lower(coalesce(e.status, '')) NOT IN (
              'cancelled', 'canceled', 'postponed', 'abandoned', 'awarded'
          )
        ORDER BY
            CASE l.tier WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 ELSE 4 END ASC,
            e.kickoff_utc ASC
        LIMIT %s
        """,
        (day_start_utc, day_end_utc, limit),
    )
    return [int(r["id"]) if isinstance(r, Mapping) else int(r[0]) for r in cur.fetchall()]


def _resolve_pick_tuple_from_dsr_or_fallback(
    *,
    event_id: int,
    ds_out: Optional[tuple[str, str, str, str, Optional[float]]],
    agg,
    league_name: str,
    home_team: str,
    away_team: str,
) -> tuple[str, str, str, str, Optional[float]]:
    if ds_out and ds_out[2] and ds_out[2] != "UNKNOWN" and ds_out[3] and ds_out[3] != "unknown_side":
        return ds_out
    fb = suggest_sql_stat_fallback_from_consensus(
        event_id,
        agg.consensus,
        agg.market_coverage,
        home_team,
        away_team,
        league_name,
    )
    return fb[0], fb[1], fb[2], fb[3], None


def _deepseek_enabled() -> bool:
    return (
        str(getattr(bt2_settings, "bt2_dsr_provider", "") or "").lower().strip() == "deepseek"
        and bool(getattr(bt2_settings, "bt2_dsr_enabled", True))
        and bool((getattr(bt2_settings, "deepseek_api_key", "") or "").strip())
    )


def replay_single_operating_day(
    cur: Any,
    *,
    operating_day_key: str,
    odds_cutoff_utc: datetime,
    max_events: int,
    min_decimal: float = MIN_ODDS_DECIMAL_DEFAULT,
) -> dict[str, Any]:
    """
    Un día operativo: pool → ds_input (corte cuotas) → DSR ciego → evaluación vs CDM.
    """
    day_start_utc, day_end_utc = bogota_operating_day_utc_window(operating_day_key)
    candidate_events = _count_candidate_events(cur, day_start_utc, day_end_utc)
    event_ids = _list_event_ids_for_replay_day(
        cur, day_start_utc, day_end_utc, limit=max(1, int(max_events) * 3)
    )

    prepared: list[dict[str, Any]] = []
    eligible = 0
    useful_input = 0

    for eid in event_ids:
        if len(prepared) >= max_events:
            break
        er = _load_event_row_for_replay(cur, eid)
        if not er:
            continue
        agg, _fm = aggregated_odds_for_event_psycopg(
            cur,
            eid,
            min_decimal=min_decimal,
            odds_cutoff_utc=odds_cutoff_utc,
            skip_sfs_fusion=True,
        )
        if not event_passes_value_pool(agg, min_decimal=min_decimal):
            continue
        eligible += 1
        dcs = data_completeness_score(agg)
        if dcs >= USEFUL_INPUT_MIN_SCORE:
            useful_input += 1

        kickoff_utc = er.get("kickoff_utc")
        item = build_ds_input_item(
            event_id=eid,
            selection_tier="A",
            kickoff_utc=kickoff_utc,
            event_status=str(er.get("status") or ""),
            league_name=str(er.get("league_name") or ""),
            country=er.get("league_country"),
            league_tier=str(er.get("league_tier") or "") or None,
            home_team=str(er.get("home_team_name") or ""),
            away_team=str(er.get("away_team_name") or ""),
            agg=agg,
            sfs_fusion_applied=False,
            sfs_fusion_synthetic_rows=0,
        )
        apply_postgres_context_to_ds_item(
            cur,
            item,
            event_id=eid,
            home_team_id=int(er["home_team_id"]) if er.get("home_team_id") is not None else None,
            away_team_id=int(er["away_team_id"]) if er.get("away_team_id") is not None else None,
            sportmonks_fixture_id=int(er["sportmonks_fixture_id"])
            if er.get("sportmonks_fixture_id") is not None
            else None,
            kickoff_utc=kickoff_utc if isinstance(kickoff_utc, datetime) else None,
        )
        blind = blind_ds_input_item(item)
        tier = str(er.get("league_tier") or "") or None
        prepared.append(
            {
                "event_id": eid,
                "item": item,
                "blind": blind,
                "agg": agg,
                "tier": tier,
                "league_name": str(er.get("league_name") or ""),
                "home_team": str(er.get("home_team_name") or ""),
                "away_team": str(er.get("away_team_name") or ""),
                "kickoff_utc": kickoff_utc,
                "truth": {
                    "result_home": er.get("result_home"),
                    "result_away": er.get("result_away"),
                    "status": er.get("status"),
                },
                "input_coverage_score": dcs,
            }
        )

    ds_map: dict[int, Optional[tuple[str, str, str, str, Optional[float]]]] = {}
    if prepared and _deepseek_enabled():
        blinds = [p["blind"] for p in prepared]
        batch_size = max(1, int(getattr(bt2_settings, "bt2_dsr_batch_size", 15) or 15))
        for i in range(0, len(blinds), batch_size):
            chunk = blinds[i : i + batch_size]
            part = deepseek_suggest_batch(
                chunk,
                operating_day_key=BLIND_LOT_OPERATING_DAY_KEY,
                api_key=str(bt2_settings.deepseek_api_key),
                base_url=str(bt2_settings.bt2_dsr_deepseek_base_url),
                model=str(bt2_settings.bt2_dsr_deepseek_model),
                timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
                max_retries=int(bt2_settings.bt2_dsr_max_retries),
            )
            ds_map.update(part)
    elif prepared:
        for p in prepared:
            eid = int(p["event_id"])
            ds_map[eid] = None

    rows_out: list[dict[str, Any]] = []
    daily_hits = 0
    daily_misses = 0
    daily_pending = 0
    daily_void = 0
    daily_ne = 0
    by_market: dict[str, int] = {}
    by_tier: dict[str, int] = {}

    for p in prepared:
        eid = int(p["event_id"])
        agg = p["agg"]
        item = p["item"]
        ctx = item["event_context"]
        league_label = p["league_name"]
        home_team = p["home_team"]
        away_team = p["away_team"]
        tier = p["tier"]

        raw = ds_map.get(eid)
        narr, conf, mmc, msc, mod_o = _resolve_pick_tuple_from_dsr_or_fallback(
            event_id=eid,
            ds_out=raw,
            agg=agg,
            league_name=league_label,
            home_team=home_team,
            away_team=away_team,
        )
        ppc = postprocess_dsr_pick(
            narrative_es=narr,
            confidence_label=conf,
            market_canonical=mmc,
            selection_canonical=msc,
            model_declared_odds=mod_o,
            consensus=agg.consensus,
            market_coverage=agg.market_coverage,
            event_id=eid,
            home_team=home_team,
            away_team=away_team,
        )
        if not ppc:
            continue
        _n2, _c2, mmc_f, msc_f = ppc
        res = resolve_official_evaluation_from_cdm_truth(
            market_canonical=mmc_f,
            selection_canonical=msc_f,
            result_home=p["truth"]["result_home"],
            result_away=p["truth"]["result_away"],
            event_status=str(p["truth"]["status"] or ""),
        )
        st = res.evaluation_status
        outcome = evaluation_status_to_outcome_ui(st)

        rh, ra = p["truth"]["result_home"], p["truth"]["result_away"]
        if rh is not None and ra is not None:
            score_text = f"{int(rh)}-{int(ra)}"
        else:
            score_text = "—"

        if outcome == "si":
            daily_hits += 1
        elif outcome == "no":
            daily_misses += 1
        elif outcome == "pendiente":
            daily_pending += 1
        elif outcome == "void":
            daily_void += 1
        elif outcome == "ne":
            daily_ne += 1

        mk_label = market_canonical_label_es(mmc_f)
        by_market[mk_label] = int(by_market.get(mk_label, 0)) + 1
        prem = premium_tier_eligible(agg, tier)
        ak = "premium" if prem else "free"
        by_tier[ak] = int(by_tier.get(ak, 0)) + 1

        sel_es = selection_canonical_summary_es(
            mmc_f,
            msc_f,
            home_team=home_team,
            away_team=away_team,
        ) or msc_f

        real_kick = kickoff_day_key_bogota(
            p["kickoff_utc"] if isinstance(p["kickoff_utc"], datetime) else None
        )
        rows_out.append(
            {
                "operating_day_key": operating_day_key,
                "real_kickoff_day_key": real_kick,
                "daily_pick_id": eid,
                "event_id": eid,
                "event_label": f"{home_team} vs {away_team}",
                "league_label": league_label or None,
                "market_label_es": mk_label,
                "selection_summary_es": sel_es,
                "action_tier": ak,
                "outcome": outcome,
                "score_text": score_text,
                "input_coverage_score": int(p["input_coverage_score"]),
            }
        )

    scored = daily_hits + daily_misses
    hit_rate = round(100.0 * daily_hits / scored, 2) if scored else None

    return {
        "operating_day_key": operating_day_key,
        "candidate_events": int(candidate_events),
        "eligible_events": int(eligible),
        "useful_input_events": int(useful_input),
        "total_picks": len(rows_out),
        "hits": daily_hits,
        "misses": daily_misses,
        "pending": daily_pending,
        "void_count": daily_void,
        "no_evaluable": daily_ne,
        "evaluated_scored": scored,
        "hit_rate_pct": hit_rate,
        "scored_picks": scored,
        "by_market": by_market,
        "by_action_tier": by_tier,
        "rows": rows_out,
    }


def build_backtest_replay_payload(
    cur: Any,
    *,
    operating_day_key_from: str,
    operating_day_key_to: str,
    max_events_per_day: int,
    max_span_days: int,
) -> dict[str, Any]:
    d0 = date.fromisoformat(operating_day_key_from)
    d1 = date.fromisoformat(operating_day_key_to)
    if d0 > d1:
        raise ValueError("operating_day_key_from > operating_day_key_to")
    span = (d1 - d0).days + 1
    if span > max_span_days:
        raise ValueError(f"Rango máximo backtest: {max_span_days} días")

    tz_label = "America/Bogota"
    daily_series: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []

    tot = dict(
        hits=0,
        misses=0,
        pending=0,
        void_count=0,
        no_evaluable=0,
        picks=0,
        candidate_events=0,
        eligible_events=0,
        useful_input_events=0,
        generated_days=0,
    )

    d = d0
    while d <= d1:
        odk = d.isoformat()
        _ds, day_end_utc = bogota_operating_day_utc_window(odk)
        day_payload = replay_single_operating_day(
            cur,
            operating_day_key=odk,
            odds_cutoff_utc=day_end_utc,
            max_events=max_events_per_day,
        )
        daily_series.append(
            {
                "operating_day_key": day_payload["operating_day_key"],
                "total_picks": day_payload["total_picks"],
                "hits": day_payload["hits"],
                "misses": day_payload["misses"],
                "pending": day_payload["pending"],
                "void_count": day_payload["void_count"],
                "no_evaluable": day_payload["no_evaluable"],
                "evaluated_scored": day_payload["evaluated_scored"],
                "hit_rate_pct": day_payload["hit_rate_pct"],
                "candidate_events": day_payload["candidate_events"],
                "eligible_events": day_payload["eligible_events"],
                "useful_input_events": day_payload["useful_input_events"],
                "scored_picks": day_payload["scored_picks"],
                "by_market": day_payload["by_market"],
                "by_action_tier": day_payload["by_action_tier"],
            }
        )

        tot["hits"] += day_payload["hits"]
        tot["misses"] += day_payload["misses"]
        tot["pending"] += day_payload["pending"]
        tot["void_count"] += day_payload["void_count"]
        tot["no_evaluable"] += day_payload["no_evaluable"]
        tot["picks"] += day_payload["total_picks"]
        tot["candidate_events"] += day_payload["candidate_events"]
        tot["eligible_events"] += day_payload["eligible_events"]
        tot["useful_input_events"] += day_payload["useful_input_events"]
        if day_payload["total_picks"] > 0:
            tot["generated_days"] += 1

        for r in day_payload["rows"]:
            all_rows.append(r)

        d += timedelta(days=1)

    scored_total = tot["hits"] + tot["misses"]
    summary_hit_rate = round(100.0 * tot["hits"] / scored_total, 2) if scored_total else None

    agg_mkt: dict[str, dict[str, int]] = {}
    for r in all_rows:
        mk = str(r.get("market_label_es") or "—")
        agg_mkt.setdefault(mk, {"picks": 0, "hits": 0, "misses": 0})
        agg_mkt[mk]["picks"] += 1
        o = str(r.get("outcome") or "")
        if o == "si":
            agg_mkt[mk]["hits"] += 1
        elif o == "no":
            agg_mkt[mk]["misses"] += 1

    distribution_market = [
        {
            "market": mk,
            "picks": int(v["picks"]),
            "hits": int(v["hits"]),
            "misses": int(v["misses"]),
        }
        for mk, v in sorted(agg_mkt.items())
    ]

    agg_tier: dict[str, dict[str, int]] = {}
    for r in all_rows:
        tk = str(r.get("action_tier") or "free")
        agg_tier.setdefault(tk, {"picks": 0, "hits": 0, "misses": 0})
        agg_tier[tk]["picks"] += 1
        o = str(r.get("outcome") or "")
        if o == "si":
            agg_tier[tk]["hits"] += 1
        elif o == "no":
            agg_tier[tk]["misses"] += 1

    distribution_tier = [
        {
            "action_tier": tk,
            "picks": int(v["picks"]),
            "hits": int(v["hits"]),
            "misses": int(v["misses"]),
        }
        for tk, v in sorted(agg_tier.items())
    ]

    summary_human_es = (
        f"Replay ciego sobre Postgres: cuotas hasta fin de día ({tz_label}) por fecha operativa; "
        f"DSR sin fecha real ni marcador. Picks={tot['picks']}, scored hit+miss={scored_total}, "
        f"tasa hit/(hit+miss)={summary_hit_rate if summary_hit_rate is not None else 'n/a'} %."
    )

    return {
        "timezone_label": tz_label,
        "summary_human_es": summary_human_es,
        "range": {
            "from": operating_day_key_from,
            "to": operating_day_key_to,
            "preset": "range",
        },
        "summary": {
            "total_picks": int(tot["picks"]),
            "hits": int(tot["hits"]),
            "misses": int(tot["misses"]),
            "pending": int(tot["pending"]),
            "void_count": int(tot["void_count"]),
            "no_evaluable": int(tot["no_evaluable"]),
            "evaluated_scored": int(scored_total),
            "hit_rate_pct": summary_hit_rate,
            "candidate_events": int(tot["candidate_events"]),
            "eligible_events": int(tot["eligible_events"]),
            "useful_input_events": int(tot["useful_input_events"]),
            "generated_days": int(tot["generated_days"]),
        },
        "daily": daily_series,
        "distribution": {
            "by_market": distribution_market,
            "by_action_tier": distribution_tier,
        },
        "rows": all_rows,
        "replay_meta": {
            "replay_mode": "bounded_backtest",
            "live_parity": False,
            "candidate_events_semantics_es": (
                "Conteo de partidos con kickoff en el día operativo America/Bogota, liga activa, "
                "excluyendo solo estados terminalizados listados en SQL (no es el pool live de bóveda, "
                "que filtra además por scheduled y otros límites)."
            ),
            "eligible_events_semantics_es": (
                "Cantidad de eventos que entran al lote preparado para DSR en este replay: como máximo "
                f"{int(max_events_per_day)} por día operativo, tras barrer como máximo "
                f"max(1, {int(max_events_per_day)}×3) IDs en orden tier+kickoff, con cuotas sujetas al "
                "corte temporal y pasando event_passes_value_pool. No significa 'todos los elegibles del día'."
            ),
            "scan_limit_formula_es": (
                f"Por día: se consideran solo los primeros max(1, max_events_per_day×3) = "
                f"max(1, {int(max_events_per_day)}×3) event_ids en orden SQL del replay."
            ),
            "blind_operating_day_key": BLIND_LOT_OPERATING_DAY_KEY,
            "odds_cutoff_rule_es": (
                "Para cada día D, solo se consideran filas de bt2_odds_snapshot con fetched_at "
                "≤ fin del día calendario America/Bogota (convertido a UTC)."
            ),
            "useful_input_definition_es": (
                f"Evento elegible del pool de valor con data_completeness_score ≥ {USEFUL_INPUT_MIN_SCORE} "
                "(mercados canónicos cubiertos en el consensus)."
            ),
            "deepseek_used": _deepseek_enabled(),
            "max_events_per_day_applied": int(max_events_per_day),
            "max_span_days": int(max_span_days),
        },
    }

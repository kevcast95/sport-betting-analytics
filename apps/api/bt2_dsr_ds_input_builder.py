"""
US-BE-032 — Builder `ds_input` rico desde Postgres (whitelist T-171).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Optional

from apps.api.bt2_fixture_prob_coherence import prob_coherence_dict_for_ds_input
from apps.api.bt2_dsr_context_queries import (
    extract_lineups_summary_from_raw_payload,
    fetch_h2h_aggregate,
    fetch_h2h_aggregate_fixed_orientation,
    fetch_odds_ingest_meta,
    fetch_rest_days_before_kickoff,
    fetch_scored_conceded_last_matches,
    fetch_team_form_string,
    fetch_team_form_string_designated_role,
    fetch_team_form_string_same_league,
    streaks_from_form,
)
from apps.api.bt2_dsr_contract import validate_ds_input_item_dict
from apps.api.bt2_dsr_ds_input_sm_fixture_blocks import merge_sm_optional_fixture_blocks
from apps.api.bt2_dsr_sm_statistics import (
    merge_sm_statistics_into_processed_statistics,
    sm_fixture_statistics_block,
)
from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds, aggregate_odds_for_event
from apps.api.bt2_settings import bt2_settings
from apps.api.bt2_sfs_odds_bridge import synthetic_odds_tuples_for_bt2_event_psycopg

SelectionTier = Literal["A", "B"]


def _match_state_from_event_status(status: Optional[str]) -> str:
    s = (status or "").lower().strip()
    if s == "scheduled":
        return "scheduled"
    if s in ("postponed", "postponed "):
        return "postponed"
    if s in ("cancelled", "canceled"):
        return "cancelled"
    if s in ("live", "inplay", "in_play"):
        return "live"
    return "unknown"


def build_ds_input_item(
    *,
    event_id: int,
    selection_tier: SelectionTier,
    kickoff_utc: Optional[datetime],
    event_status: Optional[str],
    league_name: str,
    country: Optional[str],
    league_tier: Optional[str],
    home_team: str,
    away_team: str,
    agg: AggregatedOdds,
    sfs_fusion_applied: Optional[bool] = None,
    sfs_fusion_synthetic_rows: Optional[int] = None,
) -> dict[str, Any]:
    utc_iso = ""
    if kickoff_utc is not None:
        ko = kickoff_utc
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        utc_iso = ko.isoformat().replace("+00:00", "Z")

    start_unix: Optional[int] = None
    if kickoff_utc is not None:
        ko = kickoff_utc
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        start_unix = int(ko.timestamp())

    item: dict[str, Any] = {
        "event_id": int(event_id),
        "sport": "football",
        "selection_tier": selection_tier,
        "schedule_display": {
            "utc_iso": utc_iso or datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "timezone_reference": "UTC",
        },
        "event_context": {
            "league_name": league_name or "unknown",
            "home_team": home_team or "unknown",
            "away_team": away_team or "unknown",
            "match_state": _match_state_from_event_status(event_status),
        },
        "processed": {
            "odds_featured": {
                "consensus": agg.consensus,
                **({"by_bookmaker": agg.by_bookmaker} if agg.by_bookmaker else {}),
            },
            "lineups": {"available": False},
            "h2h": {"available": False},
            "statistics": {"available": False},
            "team_streaks": {"available": False},
            "team_season_stats": {"available": False},
            "fixture_conditions": {"available": False},
            "match_officials": {"available": False},
            "squad_availability": {"available": False},
            "tactical_shape": {"available": False},
            "prediction_signals": {"available": False},
            "broadcast_notes": {"available": False},
            "fixture_advanced_sm": {"available": False},
        },
        "diagnostics": {
            "market_coverage": agg.market_coverage,
            "lineups_ok": False,
            "h2h_ok": False,
            "statistics_ok": False,
            "fetch_errors": [],
            "raw_fixture_missing": False,
            "team_season_stats_reason": None,
            "prob_coherence": prob_coherence_dict_for_ds_input(agg.consensus),
        },
    }
    if sfs_fusion_applied is not None:
        item["diagnostics"]["sfs_fusion_applied"] = sfs_fusion_applied
    if sfs_fusion_synthetic_rows is not None:
        item["diagnostics"]["sfs_fusion_synthetic_rows"] = sfs_fusion_synthetic_rows
    if country is not None:
        item["event_context"]["country"] = country
    if league_tier is not None:
        item["event_context"]["league_tier"] = league_tier
    if start_unix is not None:
        item["event_context"]["start_timestamp_unix"] = start_unix
    if agg.markets_available:
        item["diagnostics"]["markets_available"] = agg.markets_available

    validate_ds_input_item_dict(item)
    return item


def apply_postgres_context_to_ds_item(
    cur,
    item: dict[str, Any],
    *,
    event_id: int,
    home_team_id: Optional[int],
    away_team_id: Optional[int],
    sportmonks_fixture_id: Optional[int],
    kickoff_utc: Optional[datetime],
) -> None:
    """
    D-06-028 — enriquece `processed` y `diagnostics` desde tablas CDM existentes.
    """
    diag = item["diagnostics"]
    fe: list[str] = list(diag.get("fetch_errors") or [])
    before = kickoff_utc
    if before is None:
        before = datetime.now(tz=timezone.utc)
    elif before.tzinfo is None:
        before = before.replace(tzinfo=timezone.utc)

    meta = fetch_odds_ingest_meta(cur, event_id)
    if meta:
        item["processed"]["odds_featured"]["ingest_meta"] = meta

    league_id: Optional[int] = None
    season_label: Optional[str] = None
    cur.execute(
        "SELECT league_id, season FROM bt2_events WHERE id = %s",
        (event_id,),
    )
    ev_meta = cur.fetchone()
    if ev_meta:
        if isinstance(ev_meta, Mapping):
            league_id = ev_meta.get("league_id")
            season_label = ev_meta.get("season")
        else:
            league_id, season_label = ev_meta[0], ev_meta[1]

    hf: Optional[str] = None
    af: Optional[str] = None
    if home_team_id is None or away_team_id is None:
        fe.append("context:missing_team_ids_skip_h2h_form")
    else:
        h2h = fetch_h2h_aggregate(
            cur,
            current_home_team_id=int(home_team_id),
            current_away_team_id=int(away_team_id),
            before_kickoff=before,
        )
        if h2h:
            item["processed"]["h2h"] = h2h
            diag["h2h_ok"] = True
        else:
            fe.append("h2h:no_finished_rows_for_pair")

        h2h_oriented = fetch_h2h_aggregate_fixed_orientation(
            cur,
            host_team_id=int(home_team_id),
            guest_team_id=int(away_team_id),
            before_kickoff=before,
        )
        if h2h_oriented:
            ph = item["processed"]["h2h"]
            if not isinstance(ph, dict):
                ph = {}
            if h2h:
                item["processed"]["h2h"] = {
                    **h2h,
                    "same_fixture_orientation_history": h2h_oriented,
                }
            else:
                item["processed"]["h2h"] = {
                    "available": True,
                    "meetings_in_sample": 0,
                    "current_home_wins": 0,
                    "draws": 0,
                    "current_away_wins": 0,
                    "note": "aggregate_h2h_empty_only_fixed_orientation_in_bt2_events",
                    "same_fixture_orientation_history": h2h_oriented,
                }
            diag["h2h_ok"] = True

        hf = fetch_team_form_string(cur, team_id=int(home_team_id), before_kickoff=before)
        af = fetch_team_form_string(cur, team_id=int(away_team_id), before_kickoff=before)
        if hf or af:
            stats_block: dict[str, Any] = {"available": True}
            if hf:
                stats_block["home_form_last5"] = hf
            if af:
                stats_block["away_form_last5"] = af
            item["processed"]["statistics"] = stats_block
            diag["statistics_ok"] = True
        else:
            fe.append("statistics:no_recent_finished_for_teams")

        if hf or af:
            hs = streaks_from_form(hf or "")
            aws = streaks_from_form(af or "")
            ts: dict[str, Any] = {"available": True}
            if hf:
                ts["home_unbeaten_run"] = hs["unbeaten_run"]
                ts["home_winless_run"] = hs["winless_run"]
                ts["home_winning_run"] = hs["winning_run"]
            if af:
                ts["away_unbeaten_run"] = aws["unbeaten_run"]
                ts["away_winless_run"] = aws["winless_run"]
                ts["away_winning_run"] = aws["winning_run"]
            item["processed"]["team_streaks"] = ts

        # D-06-028+ — contexto CDM explícito (ventanas fijas; reduce ambigüedad vs SM en vivo).
        home_side: dict[str, Any] = {}
        away_side: dict[str, Any] = {}
        lid = int(league_id) if league_id is not None else None
        if lid is not None:
            slh = fetch_team_form_string_same_league(
                cur,
                team_id=int(home_team_id),
                league_id=lid,
                before_kickoff=before,
            )
            sla = fetch_team_form_string_same_league(
                cur,
                team_id=int(away_team_id),
                league_id=lid,
                before_kickoff=before,
            )
            if slh:
                home_side["form_last5_same_league_window"] = slh
            if sla:
                away_side["form_last5_same_league_window"] = sla
        fh_role = fetch_team_form_string_designated_role(
            cur,
            team_id=int(home_team_id),
            before_kickoff=before,
            only_as_home=True,
            only_as_away=False,
        )
        fa_role = fetch_team_form_string_designated_role(
            cur,
            team_id=int(away_team_id),
            before_kickoff=before,
            only_as_home=False,
            only_as_away=True,
        )
        if fh_role:
            home_side["form_last5_only_when_team_was_home_in_bt2"] = fh_role
        if fa_role:
            away_side["form_last5_only_when_team_was_away_in_bt2"] = fa_role

        rd_h = fetch_rest_days_before_kickoff(
            cur, team_id=int(home_team_id), before_kickoff=before
        )
        rd_a = fetch_rest_days_before_kickoff(
            cur, team_id=int(away_team_id), before_kickoff=before
        )
        if rd_h is not None:
            home_side["rest_days_before_this_kickoff"] = rd_h
        if rd_a is not None:
            away_side["rest_days_before_this_kickoff"] = rd_a

        for label, tid, bucket in (
            ("home", int(home_team_id), home_side),
            ("away", int(away_team_id), away_side),
        ):
            agg = fetch_scored_conceded_last_matches(
                cur,
                team_id=tid,
                before_kickoff=before,
                max_matches=5,
                league_id=lid,
                only_as_home=False,
                only_as_away=False,
            )
            if agg:
                used, sc, cc = agg
                bucket["lastN_finished_matches_used_for_sums"] = used
                bucket["aggregate_scored_lastN_same_window_as_form"] = sc
                bucket["aggregate_conceded_lastN_same_window_as_form"] = cc
            if lid is not None:
                agg_ha = fetch_scored_conceded_last_matches(
                    cur,
                    team_id=tid,
                    before_kickoff=before,
                    max_matches=5,
                    league_id=lid,
                    only_as_home=(label == "home"),
                    only_as_away=(label == "away"),
                )
                if agg_ha:
                    used, sc, cc = agg_ha
                    if label == "home":
                        bucket["lastN_as_host_in_league_scored_sum"] = sc
                        bucket["lastN_as_host_in_league_conceded_sum"] = cc
                        bucket["lastN_as_host_in_league_matches_used"] = used
                    else:
                        bucket["lastN_as_guest_in_league_scored_sum"] = sc
                        bucket["lastN_as_guest_in_league_conceded_sum"] = cc
                        bucket["lastN_as_guest_in_league_matches_used"] = used

        if home_side or away_side:
            st_prev = item["processed"]["statistics"]
            if not isinstance(st_prev, dict):
                st_prev = {"available": False}
            if not st_prev.get("available"):
                st_prev["available"] = True
            st_prev["cdm_from_bt2_events"] = {
                "available": True,
                "definitions": {
                    "window_N": 5,
                    "scope": "solo_partidos_finished_en_bt2_events_previos_al_kickoff_de_este_evento",
                    "same_league_filter": bool(lid is not None),
                    "season_field_on_row": season_label,
                    "sums_note": "goles_a_favor_en_contra_sumados_en_la_ventana_N_no_promedio",
                    "orientation_subblock_h2h": "historial_solo_cuando_el_equipo_que_hoy_es_local_fue_local_en_bt2_y_el_visitante_fue_visitante",
                },
                "home_side_context": home_side,
                "away_side_context": away_side,
            }
            item["processed"]["statistics"] = st_prev
            diag["statistics_ok"] = True

    item["processed"]["team_season_stats"] = {"available": False}
    fe.append("team_season_stats:no_aggregate_table_bt2_s6_1r1_dx_gap")
    diag["team_season_stats_reason"] = "no_bt2_team_season_aggregate_table"

    sm_payload: Optional[dict] = None
    if sportmonks_fixture_id is not None:
        cur.execute(
            "SELECT payload FROM raw_sportmonks_fixtures WHERE fixture_id = %s LIMIT 1",
            (int(sportmonks_fixture_id),),
        )
        raw_row = cur.fetchone()
        payload_col = None
        if raw_row:
            payload_col = (
                raw_row["payload"]
                if isinstance(raw_row, Mapping)
                else raw_row[0]
            )
        if raw_row and payload_col is not None:
            sm_payload = payload_col if isinstance(payload_col, dict) else None
            if sm_payload is None:
                fe.append("lineups:raw_payload_not_object")
                diag["raw_fixture_missing"] = True
            else:
                lu = extract_lineups_summary_from_raw_payload(sm_payload)
                if lu:
                    item["processed"]["lineups"] = lu
                    diag["lineups_ok"] = True
                else:
                    fe.append(
                        "lineups:no_lineups_array_or_empty_in_raw_payload"
                    )

                sm_stats = sm_fixture_statistics_block(sm_payload)
                if sm_stats:
                    st = item["processed"]["statistics"]
                    if not st.get("available"):
                        st = {"available": True}
                        item["processed"]["statistics"] = st
                    merge_sm_statistics_into_processed_statistics(st, sm_stats)
        else:
            diag["raw_fixture_missing"] = True
            fe.append("lineups:no_raw_sportmonks_row")
    else:
        diag["raw_fixture_missing"] = True
        fe.append("lineups:no_sportmonks_fixture_id")

    if isinstance(sm_payload, dict):
        merge_sm_optional_fixture_blocks(item["processed"], sm_payload)

    st_final = item["processed"]["statistics"]
    sm_sub = st_final.get("from_sm_fixture") if isinstance(st_final, dict) else None
    has_sm_metrics = bool(
        isinstance(sm_sub, dict) and any(k != "available" for k in sm_sub)
    )
    cdm_ctx = st_final.get("cdm_from_bt2_events") if isinstance(st_final, dict) else None
    has_cdm_context = bool(
        isinstance(cdm_ctx, dict)
        and (
            bool(cdm_ctx.get("home_side_context"))
            or bool(cdm_ctx.get("away_side_context"))
        )
    )
    diag["statistics_ok"] = bool(
        (
            isinstance(st_final, dict)
            and (st_final.get("home_form_last5") or st_final.get("away_form_last5"))
        )
        or has_sm_metrics
        or has_cdm_context
    )

    diag["fetch_errors"] = fe
    validate_ds_input_item_dict(item)


def fetch_event_odds_rows_for_aggregation(cur, event_id: int) -> list[tuple[Any, ...]]:
    cur.execute(
        """
        SELECT bookmaker, market, selection, odds, fetched_at
        FROM bt2_odds_snapshot
        WHERE event_id = %s
        ORDER BY fetched_at DESC
        """,
        (event_id,),
    )
    return list(cur.fetchall())


def aggregated_odds_for_event_psycopg(
    cur,
    event_id: int,
    *,
    min_decimal: float = 1.30,
) -> tuple[AggregatedOdds, dict[str, Any]]:
    """
    Misma agregación que `build_ds_input_item_from_db` (incl. fusión SFS si está activa).
    Reutilizable para GET bóveda y otras rutas que necesiten `consensus` alineado al DSR.
    """
    odds_rows = fetch_event_odds_rows_for_aggregation(cur, event_id)
    rows_for_agg: list[tuple[Any, ...]] = [(b, m, s, o, f) for b, m, s, o, f in odds_rows]
    fusion_meta: dict[str, Any] = {"applied": False, "synthetic_rows": 0}
    if getattr(bt2_settings, "bt2_sfs_markets_fusion_enabled", False):
        extras, fm = synthetic_odds_tuples_for_bt2_event_psycopg(
            cur,
            event_id,
            provider=str(getattr(bt2_settings, "bt2_sfs_odds_provider_slug", "") or "sofascore_experimental"),
        )
        if extras:
            rows_for_agg = rows_for_agg + extras
            fusion_meta["applied"] = bool(fm.get("applied"))
            fusion_meta["synthetic_rows"] = int(fm.get("synthetic_rows") or len(extras))
    agg = aggregate_odds_for_event(rows_for_agg, min_decimal=min_decimal)
    return agg, fusion_meta


def build_ds_input_item_from_db(
    cur,
    event_id: int,
    *,
    selection_tier: SelectionTier,
    min_decimal: float = 1.30,
) -> Optional[tuple[dict[str, Any], AggregatedOdds]]:
    """
    Carga evento + odds; None si no hay fila evento.
    """
    cur.execute(
        """
        SELECT
            e.id,
            e.kickoff_utc,
            e.status,
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
    if not row:
        return None
    if isinstance(row, Mapping):
        r = dict(row)
        kickoff_utc = r["kickoff_utc"]
        ev_status = r["status"]
        league_name = r["league_name"]
        country = r["league_country"]
        league_tier = r["league_tier"]
        home_team = r["home_team_name"]
        away_team = r["away_team_name"]
        home_team_id = r["home_team_id"]
        away_team_id = r["away_team_id"]
        sportmonks_fixture_id = r["sportmonks_fixture_id"]
    else:
        (
            _eid,
            kickoff_utc,
            ev_status,
            league_name,
            country,
            league_tier,
            home_team,
            away_team,
            home_team_id,
            away_team_id,
            sportmonks_fixture_id,
        ) = row
    agg, fusion_meta = aggregated_odds_for_event_psycopg(cur, event_id, min_decimal=min_decimal)
    fusion_applied = False
    fusion_n = 0
    if getattr(bt2_settings, "bt2_sfs_markets_fusion_enabled", False):
        fusion_applied = bool(fusion_meta.get("applied"))
        fusion_n = int(fusion_meta.get("synthetic_rows") or 0)

    item = build_ds_input_item(
        event_id=event_id,
        selection_tier=selection_tier,
        kickoff_utc=kickoff_utc,
        event_status=ev_status,
        league_name=league_name,
        country=country,
        league_tier=league_tier,
        home_team=home_team,
        away_team=away_team,
        agg=agg,
        sfs_fusion_applied=fusion_applied if getattr(bt2_settings, "bt2_sfs_markets_fusion_enabled", False) else None,
        sfs_fusion_synthetic_rows=fusion_n if getattr(bt2_settings, "bt2_sfs_markets_fusion_enabled", False) else None,
    )
    apply_postgres_context_to_ds_item(
        cur,
        item,
        event_id=event_id,
        home_team_id=int(home_team_id) if home_team_id is not None else None,
        away_team_id=int(away_team_id) if away_team_id is not None else None,
        sportmonks_fixture_id=int(sportmonks_fixture_id) if sportmonks_fixture_id is not None else None,
        kickoff_utc=kickoff_utc,
    )
    return item, agg

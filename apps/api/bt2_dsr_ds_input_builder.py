"""
US-BE-032 — Builder `ds_input` rico desde Postgres (whitelist T-171).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from apps.api.bt2_dsr_context_queries import (
    extract_lineups_summary_from_raw_payload,
    fetch_h2h_aggregate,
    fetch_odds_ingest_meta,
    fetch_team_form_string,
    streaks_from_form,
)
from apps.api.bt2_dsr_contract import validate_ds_input_item_dict
from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds, aggregate_odds_for_event

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
        },
        "diagnostics": {
            "market_coverage": agg.market_coverage,
            "lineups_ok": False,
            "h2h_ok": False,
            "statistics_ok": False,
            "fetch_errors": [],
        },
    }
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

    item["processed"]["team_season_stats"] = {"available": False}
    fe.append("team_season_stats:no_aggregate_table_bt2_s6_1r1_dx_gap")

    if sportmonks_fixture_id is not None:
        cur.execute(
            "SELECT payload FROM raw_sportmonks_fixtures WHERE fixture_id = %s LIMIT 1",
            (int(sportmonks_fixture_id),),
        )
        raw_row = cur.fetchone()
        if raw_row and raw_row[0] is not None:
            lu = extract_lineups_summary_from_raw_payload(raw_row[0])
            if lu:
                item["processed"]["lineups"] = lu
                diag["lineups_ok"] = True
            else:
                fe.append(
                    "lineups:gap_no_v1_lineup_summary_in_raw_payload_see_AUDITORIA_RAW_SPORTMONKS_2026-04-09_sec4"
                )
        else:
            fe.append("lineups:no_raw_sportmonks_row")
    else:
        fe.append("lineups:no_sportmonks_fixture_id")

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
            COALESCE(l.name, ''),
            l.country,
            l.tier,
            COALESCE(th.name, ''),
            COALESCE(ta.name, ''),
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
    odds_rows = fetch_event_odds_rows_for_aggregation(cur, event_id)
    agg = aggregate_odds_for_event(
        [(b, m, s, o, f) for b, m, s, o, f in odds_rows],
        min_decimal=min_decimal,
    )
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

"""
Enriquecimiento de `ds_input` para el carril **shadow-native** (experimento; no productivo).

Problema resuelto: el replay native solo llamaba `apply_postgres_context_to_ds_item` cuando
`bt2_events.home_team_id` y `away_team_id` estaban ambos presentes. Si faltaba uno, se saltaba
todo el enriquecimiento CDM+SM, aunque existiera `raw_sportmonks_fixtures` y mapeo a `bt2_teams`.

Principio: la puerta sigue siendo shadow-native (TOA + value pool); esto solo **rellena** contexto
cuando hay datos auxiliares seguros (CDM, raw SM).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping, Optional

from apps.api.bt2_dsr_context_queries import (
    extract_lineups_summary_from_raw_payload,
    sm_participant_sportmonks_team_ids,
)
from apps.api.bt2_dsr_contract import validate_ds_input_item_dict
from apps.api.bt2_dsr_ds_input_builder import apply_postgres_context_to_ds_item
from apps.api.bt2_dsr_ds_input_sm_fixture_blocks import merge_sm_optional_fixture_blocks
from apps.api.bt2_dsr_sm_statistics import (
    merge_sm_statistics_into_processed_statistics,
    sm_fixture_statistics_block,
)


def fetch_sportmonks_payload(cur, sportmonks_fixture_id: int) -> Optional[dict[str, Any]]:
    cur.execute(
        "SELECT payload FROM raw_sportmonks_fixtures WHERE fixture_id = %s LIMIT 1",
        (int(sportmonks_fixture_id),),
    )
    raw_row = cur.fetchone()
    if not raw_row:
        return None
    payload_col = (
        raw_row["payload"] if isinstance(raw_row, Mapping) else raw_row[0]
    )
    if payload_col is None:
        return None
    if isinstance(payload_col, dict):
        return payload_col
    if isinstance(payload_col, str):
        try:
            d = json.loads(payload_col)
            return d if isinstance(d, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def bt2_team_id_for_sportmonks_team(cur, sportmonks_team_id: int) -> Optional[int]:
    cur.execute(
        "SELECT id FROM bt2_teams WHERE sportmonks_id = %s LIMIT 1",
        (int(sportmonks_team_id),),
    )
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, Mapping):
        v = row.get("id")
    else:
        v = row[0]
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def resolve_home_away_bt2_team_ids_for_shadow_native(
    cur,
    *,
    home_team_id: Optional[int],
    away_team_id: Optional[int],
    sportmonks_fixture_id: Optional[int],
) -> tuple[Optional[int], Optional[int], list[str]]:
    """
    Completa IDs CDM local desde participantes SportMonks cuando el evento CDM tiene huecos.
    """
    notes: list[str] = []
    hid: Optional[int] = int(home_team_id) if home_team_id is not None else None
    aid: Optional[int] = int(away_team_id) if away_team_id is not None else None
    if hid is not None and aid is not None:
        return hid, aid, notes

    if sportmonks_fixture_id is None:
        notes.append("enrichment:no_sm_fixture_for_team_resolution")
        return hid, aid, notes

    payload = fetch_sportmonks_payload(cur, int(sportmonks_fixture_id))
    if not payload:
        notes.append("enrichment:sm_payload_missing_for_team_resolution")
        return hid, aid, notes

    sm_h, sm_a = sm_participant_sportmonks_team_ids(payload)
    if hid is None and sm_h is not None:
        mapped = bt2_team_id_for_sportmonks_team(cur, int(sm_h))
        if mapped is not None:
            hid = mapped
            notes.append("enrichment:home_bt2_team_id_from_sm_participant")
        else:
            notes.append("enrichment:home_sm_team_not_mapped_to_bt2_teams")
    if aid is None and sm_a is not None:
        mapped = bt2_team_id_for_sportmonks_team(cur, int(sm_a))
        if mapped is not None:
            aid = mapped
            notes.append("enrichment:away_bt2_team_id_from_sm_participant")
        else:
            notes.append("enrichment:away_sm_team_not_mapped_to_bt2_teams")

    return hid, aid, notes


def apply_sm_fixture_blocks_without_bt2_event(
    cur,
    item: dict[str, Any],
    sportmonks_fixture_id: int,
) -> list[str]:
    """
    Cuando no hay fila `bt2_events` enlazada: al menos lineups agregados + stats SM + bloques opcionales.
    """
    notes: list[str] = []
    diag = item["diagnostics"]
    fe: list[str] = list(diag.get("fetch_errors") or [])

    payload = fetch_sportmonks_payload(cur, int(sportmonks_fixture_id))
    sm_payload: Optional[dict[str, Any]] = None
    if payload is None:
        diag["raw_fixture_missing"] = True
        fe.append("lineups:no_raw_sportmonks_row")
    else:
        sm_payload = payload
        lu = extract_lineups_summary_from_raw_payload(sm_payload)
        if lu:
            item["processed"]["lineups"] = lu
            diag["lineups_ok"] = True
            notes.append("enrichment_sm:lineups_summary")
        else:
            fe.append("lineups:no_lineups_array_or_empty_in_raw_payload")

        sm_stats = sm_fixture_statistics_block(sm_payload)
        if sm_stats:
            st = item["processed"]["statistics"]
            if not isinstance(st, dict):
                st = {"available": False}
                item["processed"]["statistics"] = st
            if not st.get("available"):
                st["available"] = True
            merge_sm_statistics_into_processed_statistics(st, sm_stats)
            notes.append("enrichment_sm:fixture_statistics")

    if isinstance(sm_payload, dict):
        merge_sm_optional_fixture_blocks(item["processed"], sm_payload)
        notes.append("enrichment_sm:optional_fixture_blocks_if_present")

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
    return notes


def apply_shadow_native_enriched_context(
    cur,
    item: dict[str, Any],
    *,
    bt2_event_id: Optional[int],
    sportmonks_fixture_id: Optional[int],
    kickoff_utc: Optional[datetime],
) -> dict[str, Any]:
    """
    Punto único para el carril shadow-native.

    - Con `bt2_event_id`: delega en `apply_postgres_context_to_ds_item`, pero **antes** intenta
      completar `home_team_id`/`away_team_id` desde participantes SM si el CDM tiene NULL.
    - Sin `bt2_event_id` pero con `sportmonks_fixture_id`: fusiona bloques desde raw SM (sin gate legacy odds).
    """
    meta: dict[str, Any] = {"path": None, "notes": [], "resolved_home_team_id": None, "resolved_away_team_id": None}

    if bt2_event_id is not None:
        cur.execute(
            """
            SELECT home_team_id, away_team_id, sportmonks_fixture_id
            FROM bt2_events WHERE id = %s
            """,
            (int(bt2_event_id),),
        )
        er = cur.fetchone()
        if not er:
            meta["notes"].append("enrichment:bt2_event_row_not_found")
            if sportmonks_fixture_id is not None:
                n = apply_sm_fixture_blocks_without_bt2_event(
                    cur, item, int(sportmonks_fixture_id)
                )
                meta["notes"].extend(n)
                meta["path"] = "sportmonks_only_after_missing_bt2_event"
            else:
                meta["path"] = "none"
            return meta

        if isinstance(er, Mapping):
            ev_home = er.get("home_team_id")
            ev_away = er.get("away_team_id")
            ev_sm = er.get("sportmonks_fixture_id")
        else:
            ev_home, ev_away, ev_sm = er[0], er[1], er[2]

        sm_fix: Optional[int]
        if sportmonks_fixture_id is not None:
            sm_fix = int(sportmonks_fixture_id)
        elif ev_sm is not None:
            sm_fix = int(ev_sm)
        else:
            sm_fix = None

        hid, aid, notes = resolve_home_away_bt2_team_ids_for_shadow_native(
            cur,
            home_team_id=ev_home,
            away_team_id=ev_away,
            sportmonks_fixture_id=sm_fix,
        )
        meta["notes"].extend(notes)
        meta["resolved_home_team_id"] = hid
        meta["resolved_away_team_id"] = aid

        apply_postgres_context_to_ds_item(
            cur,
            item,
            event_id=int(bt2_event_id),
            home_team_id=hid,
            away_team_id=aid,
            sportmonks_fixture_id=sm_fix,
            kickoff_utc=kickoff_utc,
        )
        meta["path"] = "apply_postgres_context_resolved_teams"
        return meta

    if sportmonks_fixture_id is not None:
        n = apply_sm_fixture_blocks_without_bt2_event(cur, item, int(sportmonks_fixture_id))
        meta["notes"].extend(n)
        meta["path"] = "sportmonks_fixture_only"
        return meta

    meta["notes"].append("enrichment:no_bt2_event_and_no_sm_fixture")
    meta["path"] = "none"
    return meta

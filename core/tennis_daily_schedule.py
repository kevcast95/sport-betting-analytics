"""
Descubrimiento diario de event_ids de tenis (SofaScore), alineado con P0 del roadmap.

1) sport/tennis/scheduled-tournaments/{date}/page/{n}  (paginación)
2) unique-tournament/{id}/scheduled-events/{date}      (fan-out)

Si no hay IDs o la API falla, se hace fallback a:
  sport/tennis/scheduled-events/{date}  (mismo que fútbol pero slug tennis).

Filtro MVP (roadmap): singles + pro; excluye virtual/simulated en category.
Desactivar con ALTEA_TENNIS_MVP_FILTER=0.
"""

from __future__ import annotations

import os
from typing import Any, List, Optional, Set

from core.sofascore_http import sofascore_get_json
from core.sofascore_payload_extract import extract_event_ids_from_scheduled_payload

BASE = "https://www.sofascore.com/api/v1"


def _mvp_filter_enabled() -> bool:
    return os.environ.get("ALTEA_TENNIS_MVP_FILTER", "1").lower() not in (
        "0",
        "false",
        "no",
    )

def _force_legacy_enabled() -> bool:
    return os.environ.get("ALTEA_TENNIS_FORCE_LEGACY", "0").lower() in (
        "1",
        "true",
        "yes",
    )

def _event_is_finished(ev: dict) -> bool:
    st = ev.get("status") if isinstance(ev.get("status"), dict) else {}
    t = str(st.get("type") or "").lower()
    code = st.get("code")
    desc = str(st.get("description") or "").lower()
    if t == "finished" or code == 100:
        return True
    if "finished" in desc or "full time" in desc or "ended" in desc:
        return True
    return False

def _extract_non_finished_event_ids_from_legacy_payload(
    payload: Any, *, apply_mvp: bool
) -> List[int]:
    """
    scheduled-events -> events[] contiene status y eventFilters.
    Filtra finished para que el job (modo operativo) no termine con 0 persisted.
    """
    events = None
    if isinstance(payload, dict):
        events = payload.get("events") or payload.get("scheduledEvents") or payload.get(
            "scheduled_events"
        )
    if events is None:
        return []
    if not isinstance(events, list):
        return []

    out: List[int] = []
    seen: Set[int] = set()
    for it in events:
        if not isinstance(it, dict):
            continue
        if apply_mvp and not _event_passes_mvp_filters(it):
            continue
        if _event_is_finished(it):
            continue
        eid = it.get("id")
        if eid is None:
            continue
        try:
            eid_i = int(eid)
        except (TypeError, ValueError):
            continue
        if eid_i not in seen:
            seen.add(eid_i)
            out.append(eid_i)
    return out


def _event_passes_mvp_filters(ev: dict) -> bool:
    if not _mvp_filter_enabled():
        return True
    ef = ev.get("eventFilters")
    if not isinstance(ef, dict):
        return True
    cat = str(ef.get("category") or "").lower()
    lvl = str(ef.get("level") or "").lower()
    if "singles" not in cat:
        return False
    if "pro" not in lvl:
        return False
    for bad in ("virtual", "simulated"):
        if bad in cat:
            return False
    return True


def _extract_unique_tournament_ids_from_page(data: Any) -> List[int]:
    if not isinstance(data, dict):
        return []
    ids: List[int] = []
    seen: Set[int] = set()
    groups = data.get("groups")
    if not isinstance(groups, list):
        return []
    for g in groups:
        if not isinstance(g, dict):
            continue
        uts = g.get("uniqueTournaments") or g.get("tournaments")
        if not isinstance(uts, list):
            continue
        for row in uts:
            if not isinstance(row, dict):
                continue
            ut = row.get("uniqueTournament")
            if not isinstance(ut, dict):
                ut = row.get("tournament")
            if not isinstance(ut, dict):
                ut = row
            if not isinstance(ut, dict) or ut.get("id") is None:
                continue
            try:
                uid = int(ut["id"])
            except (TypeError, ValueError):
                continue
            if uid not in seen:
                seen.add(uid)
                ids.append(uid)
    return ids


def _unwrap_event_dict(item: Any) -> Optional[dict]:
    if not isinstance(item, dict):
        return None
    ev = item.get("event")
    if isinstance(ev, dict) and ev.get("id") is not None:
        return ev
    if item.get("id") is not None:
        return item
    return None


def _event_ids_from_unique_tournament_day(
    ut_id: int, date: str, *, apply_mvp: bool
) -> List[int]:
    url = f"{BASE}/unique-tournament/{ut_id}/scheduled-events/{date}"
    data = sofascore_get_json(url)
    if not isinstance(data, dict) or data.get("error"):
        return []
    events = data.get("events") or data.get("scheduledEvents") or []
    if not isinstance(events, list):
        return []
    out: List[int] = []
    seen: Set[int] = set()
    for item in events:
        ev = _unwrap_event_dict(item)
        if ev is None:
            continue
        if apply_mvp and not _event_passes_mvp_filters(ev):
            continue
        try:
            eid = int(ev["id"])
        except (TypeError, ValueError):
            continue
        if eid not in seen:
            seen.add(eid)
            out.append(eid)
    return out


def _collect_via_tournament_fanout(
    date: str,
    *,
    max_pages: int,
    apply_mvp: bool,
) -> List[int]:
    ordered: List[int] = []
    seen: Set[int] = set()
    for page in range(max(1, max_pages)):
        url = f"{BASE}/sport/tennis/scheduled-tournaments/{date}/page/{page}"
        data = sofascore_get_json(url)
        if not isinstance(data, dict) or data.get("error"):
            break
        ut_ids = _extract_unique_tournament_ids_from_page(data)
        if not ut_ids and page == 0:
            break
        for ut_id in ut_ids:
            for eid in _event_ids_from_unique_tournament_day(
                ut_id, date, apply_mvp=apply_mvp
            ):
                if eid not in seen:
                    seen.add(eid)
                    ordered.append(eid)
        if data.get("hasNextPage") is False:
            break
        if not ut_ids:
            break
    return ordered


def fetch_legacy_tennis_scheduled_events(date: str) -> Any:
    url = f"{BASE}/sport/tennis/scheduled-events/{date}"
    return sofascore_get_json(url)


def tennis_event_ids_for_date(
    date: str,
    *,
    limit: Optional[int] = None,
    max_tournament_pages: int = 30,
) -> List[int]:
    """
    Orden estable, sin duplicados. Fan-out P0 primero; si vacío, legacy scheduled-events.
    """
    apply_mvp = _mvp_filter_enabled()
    ids: List[int] = []

    if _force_legacy_enabled():
        legacy = fetch_legacy_tennis_scheduled_events(date)
        ids = _extract_non_finished_event_ids_from_legacy_payload(
            legacy, apply_mvp=apply_mvp
        )
    else:
        # P0: scheduled-tournaments -> unique-tournament -> scheduled-events
        try:
            ids = _collect_via_tournament_fanout(
                date, max_pages=max_tournament_pages, apply_mvp=apply_mvp
            )
        except Exception:
            ids = []

        # Fallback legacy: scheduled-events, filtrando finished.
        if not ids:
            try:
                legacy = fetch_legacy_tennis_scheduled_events(date)
                ids = _extract_non_finished_event_ids_from_legacy_payload(
                    legacy, apply_mvp=apply_mvp
                )
            except Exception:
                ids = []
    if limit is not None:
        ids = ids[: int(limit)]
    return ids

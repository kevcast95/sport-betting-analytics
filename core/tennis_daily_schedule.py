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


def _top_tournament_ids_whitelist() -> Optional[Set[int]]:
    """
    Lista opcional de uniqueTournament.id permitidos.
    Env: ALTEA_TENNIS_TOP_UNIQUE_TOURNAMENT_IDS="2430,678,9012"
    """
    raw = (os.environ.get("ALTEA_TENNIS_TOP_UNIQUE_TOURNAMENT_IDS") or "").strip()
    if not raw:
        return None
    out: Set[int] = set()
    for token in raw.split(","):
        part = token.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except (TypeError, ValueError):
            continue
    return out or None


def _max_unique_tournaments_per_day() -> Optional[int]:
    """
    Tope opcional de torneos únicos a consultar por día.
    Env: ALTEA_TENNIS_MAX_UNIQUE_TOURNAMENTS_PER_DAY=3
    """
    raw = (os.environ.get("ALTEA_TENNIS_MAX_UNIQUE_TOURNAMENTS_PER_DAY") or "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return n


def _auto_top_unique_tournaments_per_day() -> Optional[int]:
    """
    Top-N automático de torneos por día cuando no hay whitelist manual.
    Default: 3 (mantener operación simple y con bajo ruido).
    Desactivar con 0.
    """
    raw = (os.environ.get("ALTEA_TENNIS_AUTO_TOP_UNIQUE_TOURNAMENTS_PER_DAY") or "3").strip()
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 3
    if n <= 0:
        return None
    return n

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


def _is_low_priority_tournament_name(name: str) -> bool:
    n = (name or "").strip().lower()
    if not n:
        return False
    bad_tokens = (
        "itf",
        "utr",
        "juniors",
        "junior",
        "wheelchair",
        "exhibition",
        "simulated",
        "virtual",
    )
    return any(tok in n for tok in bad_tokens)


def _tournament_priority_score(name: str) -> int:
    """
    Heurística simple para priorizar torneos top por nombre.
    """
    n = (name or "").strip().lower()
    if not n:
        return 0
    if any(tok in n for tok in ("wimbledon", "roland", "australian open", "us open", "grand slam")):
        return 100
    if "masters" in n or "atp 1000" in n or "wta 1000" in n:
        return 80
    if "atp" in n or "wta" in n:
        return 60
    if "challenger" in n:
        return 40
    return 20


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
) -> tuple[List[int], List[int], int, int, str]:
    url = f"{BASE}/unique-tournament/{ut_id}/scheduled-events/{date}"
    data = sofascore_get_json(url)
    if not isinstance(data, dict) or data.get("error"):
        return ([], [], 0, 0, "")
    events = data.get("events") or data.get("scheduledEvents") or []
    if not isinstance(events, list):
        return ([], [], 0, 0, "")
    out: List[int] = []
    out_not_started: List[int] = []
    seen: Set[int] = set()
    total = 0
    not_started = 0
    tournament_name = ""
    for item in events:
        ev = _unwrap_event_dict(item)
        if ev is None:
            continue
        if apply_mvp and not _event_passes_mvp_filters(ev):
            continue
        if not tournament_name:
            t = ev.get("tournament")
            if isinstance(t, dict):
                tournament_name = str(t.get("name") or "")
        total += 1
        is_not_started = str(ev.get("match_state") or "").strip().lower() == "not started"
        if is_not_started:
            not_started += 1
        try:
            eid = int(ev["id"])
        except (TypeError, ValueError):
            continue
        if eid not in seen:
            seen.add(eid)
            out.append(eid)
            if is_not_started:
                out_not_started.append(eid)
    return (out, out_not_started, not_started, total, tournament_name)


def _collect_via_tournament_fanout(
    date: str,
    *,
    max_pages: int,
    apply_mvp: bool,
) -> List[int]:
    ordered: List[int] = []
    seen: Set[int] = set()
    tournament_rows: List[tuple[int, str, List[int], List[int], int, int]] = []
    seen_tournaments: Set[int] = set()
    tournament_allowlist = _top_tournament_ids_whitelist()
    max_tournaments = _max_unique_tournaments_per_day()
    auto_top_tournaments = _auto_top_unique_tournaments_per_day()
    for page in range(max(1, max_pages)):
        url = f"{BASE}/sport/tennis/scheduled-tournaments/{date}/page/{page}"
        data = sofascore_get_json(url)
        if not isinstance(data, dict) or data.get("error"):
            break
        ut_ids = _extract_unique_tournament_ids_from_page(data)
        if tournament_allowlist is not None:
            ut_ids = [ut for ut in ut_ids if ut in tournament_allowlist]
        if not ut_ids and page == 0:
            break
        for ut_id in ut_ids:
            if ut_id in seen_tournaments:
                continue
            seen_tournaments.add(ut_id)
            ids, ids_not_started, not_started, total, tournament_name = _event_ids_from_unique_tournament_day(
                ut_id, date, apply_mvp=apply_mvp
            )
            if not ids:
                continue
            tournament_rows.append((ut_id, tournament_name, ids, ids_not_started, not_started, total))
        if data.get("hasNextPage") is False:
            break
        if not ut_ids:
            break

    # Límite final de torneos:
    # 1) manual explícito (max_tournaments)
    # 2) automático top-N por señales del día (no whitelist)
    limit = max_tournaments
    if limit is None and tournament_allowlist is None:
        limit = auto_top_tournaments

    if limit is not None:
        # Upcoming tab: solo torneos con al menos 1 evento no iniciado
        tournament_rows = [r for r in tournament_rows if r[4] > 0]
        # Quita circuitos de baja prioridad (ITF/UTR/etc.) para quedarse con torneos top
        tournament_rows = [r for r in tournament_rows if not _is_low_priority_tournament_name(r[1])]
        tournament_rows.sort(key=lambda r: (-_tournament_priority_score(r[1]), -r[4], -r[5], r[0]))
        tournament_rows = tournament_rows[:limit]

    for _, _, ids, ids_not_started, _, _ in tournament_rows:
        # Si auto-top está activo sin whitelist manual, alinea con "Upcoming"
        source_ids = ids_not_started if (tournament_allowlist is None and auto_top_tournaments is not None) else ids
        for eid in source_ids:
            if eid not in seen:
                seen.add(eid)
                ordered.append(eid)
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

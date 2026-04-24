"""Resolución BT2 event → SofaScore event id (D-06-067)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.bt2_models import Bt2Event, Bt2SfsEventOverride, Bt2SfsJoinAudit, Bt2Team
from apps.api.bt2.providers.sofascore.client import SfsHttpClient


@dataclass
class JoinResult:
    sofascore_event_id: Optional[int]
    layer: Optional[int]  # 1, 2, 3
    status: str  # matched | failed | no_scheduled_payload | ambiguous
    detail: dict[str, Any]


def _norm_name(s: str | None) -> str:
    return " ".join(str(s or "").lower().split())


def load_seed_mapping(path: str | None) -> dict[int, int]:
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    out: dict[int, int] = {}
    for k, v in data.items():
        try:
            sm_id = int(k)
            sfs_id = int(v)
            out[sm_id] = sfs_id
        except (TypeError, ValueError):
            continue
    return out


def resolve_join_layer1(
    session: Session,
    ev: Bt2Event,
    *,
    seed_by_sm_fixture: dict[int, int],
) -> JoinResult:
    if ev.sofascore_event_id:
        return JoinResult(int(ev.sofascore_event_id), 1, "matched", {"via": "bt2_events.sofascore_event_id"})
    ovr = session.execute(
        select(Bt2SfsEventOverride).where(Bt2SfsEventOverride.bt2_event_id == ev.id)
    ).scalar_one_or_none()
    if ovr is not None:
        return JoinResult(int(ovr.sofascore_event_id), 3, "matched", {"via": "override_table"})
    sid = seed_by_sm_fixture.get(int(ev.sportmonks_fixture_id))
    if sid is not None:
        return JoinResult(int(sid), 1, "matched", {"via": "seed_json_sm_fixture"})
    return JoinResult(None, None, "failed", {"via": "layer1_exhausted"})


def _event_team_names(session: Session, ev: Bt2Event) -> tuple[str, str]:
    ht = at = ""
    if ev.home_team_id:
        t = session.get(Bt2Team, ev.home_team_id)
        if t:
            ht = t.name or ""
    if ev.away_team_id:
        t = session.get(Bt2Team, ev.away_team_id)
        if t:
            at = t.name or ""
    return ht, at


def resolve_join_layer2_scheduled(
    ev: Bt2Event,
    session: Session,
    client: SfsHttpClient,
    *,
    sport: str = "football",
) -> JoinResult:
    if not ev.kickoff_utc:
        return JoinResult(None, None, "failed", {"reason": "missing_kickoff_utc"})
    k = ev.kickoff_utc
    if k.tzinfo is None:
        k = k.replace(tzinfo=timezone.utc)
    day = k.astimezone(timezone.utc).date().isoformat()
    payload = client.fetch_scheduled_football_day(day) if sport == "football" else {}
    if payload.get("_error"):
        return JoinResult(None, None, "no_scheduled_payload", {"payload_meta": list(payload.keys())[:8]})
    events = payload.get("events") or []
    if not isinstance(events, list):
        return JoinResult(None, None, "no_scheduled_payload", {"reason": "events_not_list"})

    h_bt2, a_bt2 = _event_team_names(session, ev)
    nh, na = _norm_name(h_bt2), _norm_name(a_bt2)
    if not nh or not na:
        return JoinResult(None, None, "failed", {"reason": "missing_team_names"})

    matches: list[tuple[int, dict[str, Any]]] = []
    for item in events:
        if not isinstance(item, dict):
            continue
        eid = item.get("id")
        try:
            eid_i = int(eid)
        except (TypeError, ValueError):
            continue
        home = item.get("homeTeam") or {}
        away = item.get("awayTeam") or {}
        hname = _norm_name(str(home.get("name") or home.get("shortName") or ""))
        aname = _norm_name(str(away.get("name") or away.get("shortName") or ""))
        if not hname or not aname:
            continue
        ts = item.get("startTimestamp")
        try:
            ts_i = int(ts)
        except (TypeError, ValueError):
            ts_i = 0
        ev_ts = int(k.timestamp())
        if abs(ts_i - ev_ts) > 4 * 3600:
            continue
        if (nh == hname and na == aname) or (nh == aname and na == hname):
            matches.append((eid_i, item))

    if len(matches) == 1:
        return JoinResult(matches[0][0], 2, "matched", {"via": "scheduled_day_teams_kickoff"})
    if len(matches) == 0:
        return JoinResult(None, 2, "failed", {"reason": "no_match_on_day", "day": day})
    return JoinResult(None, 2, "ambiguous", {"candidates": [m[0] for m in matches[:10]]})


def resolve_sfs_event_id(
    session: Session,
    ev: Bt2Event,
    client: SfsHttpClient,
    *,
    seed_by_sm_fixture: dict[int, int],
    try_layer2: bool = True,
) -> JoinResult:
    r1 = resolve_join_layer1(session, ev, seed_by_sm_fixture=seed_by_sm_fixture)
    if r1.sofascore_event_id is not None:
        return r1
    if not try_layer2:
        return r1
    return resolve_join_layer2_scheduled(ev, session, client)


def persist_join_audit(
    session: Session,
    *,
    run_id: str,
    bt2_event_id: int,
    result: JoinResult,
) -> None:
    """Inserta/actualiza fila en bt2_sfs_join_audit (idempotente por run+event)."""
    row = session.execute(
        select(Bt2SfsJoinAudit).where(
            Bt2SfsJoinAudit.run_id == run_id,
            Bt2SfsJoinAudit.bt2_event_id == bt2_event_id,
        )
    ).scalar_one_or_none()
    if row is None:
        session.add(
            Bt2SfsJoinAudit(
                run_id=run_id,
                bt2_event_id=bt2_event_id,
                sofascore_event_id=result.sofascore_event_id,
                match_layer=result.layer,
                match_status=result.status,
                detail_json=result.detail,
            )
        )
    else:
        row.sofascore_event_id = result.sofascore_event_id
        row.match_layer = result.layer
        row.match_status = result.status
        row.detail_json = result.detail

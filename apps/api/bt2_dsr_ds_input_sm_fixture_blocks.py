"""
Bloques opcionales de `processed` a partir del JSON SportMonks (fixture include).

Cada extractor es defensivo: si falta el array/objeto en el payload, devuelve
`{"available": false}`. No lanza por tipos inesperados. Salida acotada (tokens)
y sin claves prohibidas D-06-002 (solo nombres seguros).
"""

from __future__ import annotations

from typing import Any, Optional


def _s(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, str):
        t = v.strip()
        return t or None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v)
    return None


def _clip(s: str, max_len: int) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def extract_fixture_conditions(payload: dict[str, Any]) -> dict[str, Any]:
    venue = payload.get("venue")
    state = payload.get("state")
    wr = payload.get("weatherReport")
    out: dict[str, Any] = {"available": False}
    block: dict[str, Any] = {}
    if isinstance(venue, dict):
        vn = _s(venue.get("name"))
        if vn:
            block["venue_name"] = _clip(vn, 120)
        vc = _s(venue.get("city_name") or venue.get("city"))
        if vc:
            block["venue_city"] = _clip(vc, 80)
        cap = venue.get("capacity")
        if isinstance(cap, (int, float)) and int(cap) > 0:
            block["venue_capacity"] = int(cap)
        surf = _s(venue.get("surface"))
        if surf:
            block["venue_surface"] = _clip(surf, 40)
    if isinstance(state, dict):
        sn = _s(state.get("name") or state.get("short_name"))
        if sn:
            block["fixture_state_label"] = _clip(sn, 64)
        sid = state.get("id")
        if isinstance(sid, (int, float)):
            block["fixture_state_id"] = int(sid)
    if isinstance(wr, dict):
        for key, out_key in (
            ("temperature", "weather_temp"),
            ("humidity", "weather_humidity"),
            ("wind_speed", "weather_wind_speed"),
            ("description", "weather_description"),
            ("type", "weather_type"),
        ):
            val = wr.get(key)
            if val is None:
                continue
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                block[out_key] = float(val) if isinstance(val, float) else int(val)
            else:
                sv = _s(val)
                if sv:
                    block[out_key] = _clip(sv, 120)
    if block:
        block["available"] = True
        return block
    return out


def extract_match_officials(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"available": False}
    refs: list[dict[str, Any]] = []
    raw_refs = payload.get("referees")
    if isinstance(raw_refs, list):
        for r in raw_refs[:6]:
            if not isinstance(r, dict):
                continue
            ref = r.get("referee")
            name = None
            rid = None
            if isinstance(ref, dict):
                name = _s(ref.get("display_name") or ref.get("name"))
                rid = ref.get("id")
            if name is None:
                name = _s(r.get("referee_name"))
            row: dict[str, Any] = {}
            if isinstance(rid, (int, float)):
                row["referee_id"] = int(rid)
            if name:
                row["name"] = _clip(name, 120)
            if row:
                refs.append(row)
    coaches_out: list[dict[str, Any]] = []
    raw_coaches = payload.get("coaches")
    if isinstance(raw_coaches, list):
        for c in raw_coaches[:6]:
            if not isinstance(c, dict):
                continue
            coach = c.get("coach")
            name = None
            cid = None
            if isinstance(coach, dict):
                name = _s(coach.get("display_name") or coach.get("name"))
                cid = coach.get("id")
            pid = c.get("participant_id")
            row = {}
            if isinstance(cid, (int, float)):
                row["coach_id"] = int(cid)
            if isinstance(pid, (int, float)):
                row["participant_id"] = int(pid)
            if name:
                row["name"] = _clip(name, 120)
            if row:
                coaches_out.append(row)
    if not refs and not coaches_out:
        return out
    block: dict[str, Any] = {"available": True}
    if refs:
        block["referees"] = refs
    if coaches_out:
        block["coaches"] = coaches_out
    return block


def extract_squad_availability(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("sidelined")
    if not isinstance(raw, list) or not raw:
        return {"available": False}
    by_team: dict[str, int] = {}
    by_type: dict[str, int] = {}
    samples: list[dict[str, Any]] = []
    for row in raw[:40]:
        if not isinstance(row, dict):
            continue
        tid = row.get("team_id") or row.get("participant_id")
        if isinstance(tid, (int, float)):
            k = str(int(tid))
            by_team[k] = by_team.get(k, 0) + 1
        typ = row.get("type_id")
        if isinstance(typ, (int, float)):
            tk = str(int(typ))
            by_type[tk] = by_type.get(tk, 0) + 1
        if len(samples) < 10:
            pl = row.get("player")
            pname = None
            if isinstance(pl, dict):
                pname = _s(pl.get("display_name") or pl.get("name") or pl.get("common_name"))
            tid_s: Optional[int] = int(typ) if isinstance(typ, (int, float)) else None
            if pname:
                samples.append({"player": _clip(pname, 80), "type_id": tid_s})
    block: dict[str, Any] = {
        "available": True,
        "sidelined_rows": min(len(raw), 200),
        "by_team_id_count": by_team,
        "by_type_id_count": by_type,
    }
    if samples:
        block["sample_out"] = samples
    return block


def extract_tactical_shape(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"available": False}
    forms = payload.get("formations")
    exp = payload.get("expectedLineups")
    block: dict[str, Any] = {}
    if isinstance(forms, list) and forms:
        rows: list[dict[str, Any]] = []
        for f in forms[:4]:
            if not isinstance(f, dict):
                continue
            pid = f.get("participant_id")
            loc = _s(f.get("location"))
            formation = _s(f.get("formation"))
            r: dict[str, Any] = {}
            if isinstance(pid, (int, float)):
                r["participant_id"] = int(pid)
            if loc:
                r["location"] = loc[:16]
            if formation:
                r["formation"] = _clip(formation, 32)
            if r:
                rows.append(r)
        if rows:
            block["formations"] = rows
    if isinstance(exp, list) and exp:
        block["expected_lineup_rows"] = min(len(exp), 200)
    if block:
        block["available"] = True
        return block
    return out


def extract_prediction_signals(payload: dict[str, Any]) -> dict[str, Any]:
    preds = payload.get("predictions")
    if not isinstance(preds, list) or not preds:
        return {"available": False}
    slim: list[dict[str, Any]] = []
    for p in preds[:8]:
        if not isinstance(p, dict):
            continue
        row: dict[str, Any] = {}
        for k in ("type_id", "fixture_id"):
            v = p.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                row[k] = int(v)
        for k in ("advice", "label", "description"):
            sv = _s(p.get(k))
            if sv:
                row[k] = _clip(sv, 96)
        if row:
            slim.append(row)
    if not slim:
        return {"available": False}
    return {"available": True, "items": slim}


def extract_broadcast_notes(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"available": False}
    block: dict[str, Any] = {}
    tv = payload.get("tvStations")
    if isinstance(tv, list) and tv:
        names: list[str] = []
        for t in tv[:12]:
            if not isinstance(t, dict):
                continue
            n = _s(t.get("name"))
            if not n:
                nested = t.get("tvstation")
                if isinstance(nested, dict):
                    n = _s(nested.get("name"))
            if n:
                names.append(_clip(n, 80))
        if names:
            block["tv_station_names"] = names
    meta = payload.get("metadata")
    if isinstance(meta, dict) and meta:
        # solo claves cortas y valores escalares
        extra: dict[str, Any] = {}
        for k, v in list(meta.items())[:12]:
            sk = _s(k)
            if not sk or len(sk) > 40:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                extra[sk[:40]] = v
            else:
                sv = _s(v)
                if sv:
                    extra[sk[:40]] = _clip(sv, 160)
        if extra:
            block["metadata_subset"] = extra
    if block:
        block["available"] = True
        return block
    return out


def extract_fixture_advanced_sm(payload: dict[str, Any]) -> dict[str, Any]:
    """xG / pressure / hechos / resúmenes IA: solo presencia y extractos muy cortos."""
    out: dict[str, Any] = {"available": False}
    block: dict[str, Any] = {}
    if payload.get("xGFixture") is not None:
        block["has_xg_fixture_object"] = True
    if payload.get("pressure") is not None:
        block["has_pressure_object"] = True
    mf = payload.get("matchfacts")
    if isinstance(mf, (dict, list)):
        block["has_matchfacts"] = True
    ai = payload.get("AIOverviews")
    if isinstance(ai, dict):
        for key in ("text", "overview", "content", "description"):
            t = ai.get(key)
            if isinstance(t, str) and t.strip():
                block["ai_overview_excerpt"] = _clip(t, 400)
                break
    elif isinstance(ai, list) and ai:
        first = ai[0]
        if isinstance(first, dict):
            for key in ("text", "overview", "content"):
                t = first.get(key)
                if isinstance(t, str) and t.strip():
                    block["ai_overview_excerpt"] = _clip(t, 400)
                    break
    if block:
        block["available"] = True
        return block
    return out


def merge_sm_optional_fixture_blocks(
    processed: dict[str, Any], payload: dict[str, Any]
) -> None:
    """Actualiza sub-bloques de `processed` desde el payload SM (idempotente)."""
    processed["fixture_conditions"] = extract_fixture_conditions(payload)
    processed["match_officials"] = extract_match_officials(payload)
    processed["squad_availability"] = extract_squad_availability(payload)
    processed["tactical_shape"] = extract_tactical_shape(payload)
    processed["prediction_signals"] = extract_prediction_signals(payload)
    processed["broadcast_notes"] = extract_broadcast_notes(payload)
    processed["fixture_advanced_sm"] = extract_fixture_advanced_sm(payload)

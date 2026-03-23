"""
Normaliza el payload de GET /event/{eventId}/team-streaks (SofaScore).
No usa el sub-endpoint betting-odds; si el JSON incluye claves de cuotas, se omiten del output.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _sanitize_streak_row(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    # Campos habituales: name, value, team (obj), etc.
    out: Dict[str, Any] = {}
    for k in ("name", "value", "description", "type", "text"):
        if k in row and row[k] is not None:
            out[k] = row[k]
    team = row.get("team")
    if isinstance(team, dict):
        out["team"] = {
            "id": team.get("id"),
            "name": team.get("name"),
            "short_name": team.get("shortName"),
        }
    # Explícitamente no propagamos bettingOdds ni estructuras de cuotas.
    return out


def process_team_streaks(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {"ok": False, "reason": "not_a_dict"}

    if raw.get("_error"):
        return {"ok": False, "reason": "fetch_error"}

    general = raw.get("general")
    head2head = raw.get("head2head")
    g_list: List[Dict[str, Any]] = []
    h_list: List[Dict[str, Any]] = []

    if isinstance(general, list):
        for item in general:
            cleaned = _sanitize_streak_row(item)
            if cleaned:
                g_list.append(cleaned)

    if isinstance(head2head, list):
        for item in head2head:
            cleaned = _sanitize_streak_row(item)
            if cleaned:
                h_list.append(cleaned)

    if not g_list and not h_list:
        return {"ok": False, "reason": "empty_streaks"}

    return {
        "ok": True,
        "general": g_list,
        "head2head": h_list,
    }

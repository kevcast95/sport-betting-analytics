"""
Resumen de GET /event/{id}/statistics para tenis (estructura distinta a fútbol).
No reemplaza process_statistics del fútbol; añade vista paralela en processed.tennis_statistics.
"""

from __future__ import annotations

from typing import Any, Dict, List


def process_tennis_event_statistics(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("_error"):
        return {"ok": False, "note": "fetch_error_or_empty"}
    stats = raw.get("statistics")
    if not isinstance(stats, list):
        stats = []
    groups_out: List[Dict[str, Any]] = []
    for period in stats[:3]:
        if not isinstance(period, dict):
            continue
        groups = period.get("groups") or []
        if not isinstance(groups, list):
            continue
        for g in groups[:12]:
            if not isinstance(g, dict):
                continue
            gname = str(g.get("groupName") or g.get("name") or "")
            items = g.get("statisticsItems") or g.get("items") or []
            row: Dict[str, Any] = {"group": gname, "stats": []}
            if isinstance(items, list):
                for it in items[:8]:
                    if not isinstance(it, dict):
                        continue
                    nm = str(it.get("name") or it.get("statisticName") or "")
                    home = it.get("home") or it.get("homeValue")
                    away = it.get("away") or it.get("awayValue")
                    if nm:
                        row["stats"].append(
                            {"name": nm, "home": home, "away": away}
                        )
            if row["stats"] or gname:
                groups_out.append(row)
    return {
        "ok": len(groups_out) > 0,
        "periods_seen": len(stats),
        "groups": groups_out,
    }

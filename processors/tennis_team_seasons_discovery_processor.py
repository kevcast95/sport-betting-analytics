"""GET /team/{id}/team-statistics/seasons — descubrimiento utid/season para stats overall."""

from __future__ import annotations

from typing import Any, Dict, List


def process_team_statistics_seasons(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("_error"):
        return {"ok": False, "note": "fetch_error_or_empty"}
    # Formas habituales: uniqueTournaments + seasons, o typesMap
    uts = raw.get("uniqueTournaments") or raw.get("uniqueTournamentSeasons") or []
    if not isinstance(uts, list):
        uts = []
    types_map = raw.get("typesMap") or raw.get("types")
    summary: List[Dict[str, Any]] = []
    for block in uts[:15]:
        if not isinstance(block, dict):
            continue
        ut = block.get("uniqueTournament") if isinstance(block.get("uniqueTournament"), dict) else block
        utid = ut.get("id") if isinstance(ut, dict) else None
        seasons = block.get("seasons") or block.get("season") or []
        if not isinstance(seasons, list):
            seasons = []
        sids: List[int] = []
        for s in seasons[:5]:
            if isinstance(s, dict) and s.get("id") is not None:
                try:
                    sids.append(int(s["id"]))
                except (TypeError, ValueError):
                    pass
        if utid is not None or sids:
            summary.append(
                {
                    "unique_tournament_id": int(utid) if utid is not None else None,
                    "season_ids_sample": sids,
                }
            )
    return {
        "ok": len(uts) > 0 or (isinstance(types_map, dict) and len(types_map) > 0),
        "blocks": len(uts),
        "types_map_keys": list(types_map.keys())[:20] if isinstance(types_map, dict) else [],
        "summary": summary,
    }

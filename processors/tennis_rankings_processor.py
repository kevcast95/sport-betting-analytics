"""
Normaliza GET /team/{playerId}/rankings (SofaScore) para confianza / DeepSeek.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _best_ranking_entry(rankings: List[Any]) -> Optional[Dict[str, Any]]:
    """
    Prioriza ranking 'team' (ATP/WTA oficial) si existe; si no, primer bloque con rank numérico.
    """
    best: Optional[Dict[str, Any]] = None
    best_rank: Optional[int] = None
    for block in rankings:
        if not isinstance(block, dict):
            continue
        rows = block.get("rankings") or block.get("rankingRows") or []
        if not isinstance(rows, list):
            continue
        rclass = str(block.get("rankingClass") or block.get("type") or "")
        for row in rows:
            if not isinstance(row, dict):
                continue
            pos = row.get("position") or row.get("rank") or row.get("ranking")
            try:
                rnk = int(pos) if pos is not None else None
            except (TypeError, ValueError):
                rnk = None
            if rnk is None:
                continue
            if rclass.lower() == "team" or "atp" in rclass.lower() or "wta" in rclass.lower():
                return {
                    "rank": rnk,
                    "ranking_class": rclass or "team",
                    "name": row.get("name") or row.get("rowName"),
                }
            if best is None or (best_rank is not None and rnk < best_rank):
                best = {
                    "rank": rnk,
                    "ranking_class": rclass or "unknown",
                    "name": row.get("name") or row.get("rowName"),
                }
                best_rank = rnk
    return best


def process_team_rankings(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("_error"):
        return {"ok": False, "note": "fetch_error_or_empty"}
    rankings = raw.get("rankings")
    if not isinstance(rankings, list):
        rankings = []
    best = _best_ranking_entry(rankings)
    # Variante API: filas sueltas en la raíz
    if best is None and isinstance(raw.get("rankingRows"), list):
        best = _best_ranking_entry(
            [{"rankingRows": raw["rankingRows"], "rankingClass": "team"}]
        )
    return {
        "ok": best is not None,
        "best": best,
        "blocks_count": len(rankings),
    }

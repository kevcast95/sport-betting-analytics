"""Resume catálogo global tenis (categories/all, default-unique-tournaments) para DS sin JSON enorme."""

from __future__ import annotations

from typing import Any, Dict, List


def summarize_tennis_categories(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("_error"):
        return {"ok": False, "note": "fetch_error_or_empty"}
    cats = raw.get("categories") or raw.get("groups") or []
    if not isinstance(cats, list):
        cats = []
    slugs: List[str] = []
    for c in cats[:80]:
        if not isinstance(c, dict):
            continue
        s = c.get("slug") or c.get("name")
        if s:
            slugs.append(str(s))
    return {
        "ok": len(cats) > 0,
        "category_count": len(cats),
        "sample_slugs": slugs[:25],
    }


def summarize_default_unique_tournaments(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("_error"):
        return {"ok": False, "note": "fetch_error_or_empty"}
    items = raw.get("uniqueTournaments") or raw.get("tournaments") or raw.get("groups") or []
    if not isinstance(items, list):
        items = []
    ids: List[int] = []
    for it in items[:50]:
        if not isinstance(it, dict):
            continue
        ut = it.get("uniqueTournament") if isinstance(it.get("uniqueTournament"), dict) else it
        if isinstance(ut, dict) and ut.get("id") is not None:
            try:
                ids.append(int(ut["id"]))
            except (TypeError, ValueError):
                pass
    return {
        "ok": len(items) > 0,
        "tournament_count": len(items),
        "unique_tournament_ids_sample": ids[:20],
    }

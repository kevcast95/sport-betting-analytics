"""Mapeo raw SFS → filas canónicas v0 (D-06-066). Reutiliza processors legacy solo como lógica pura."""

from __future__ import annotations

from typing import Any, Iterable

from processors.odds_all_processor import process_odds_all
from processors.odds_feature_processor import process_odds_feature

CANONICAL_VERSION_S65 = "s65-v0"

FAMILY_FT_1X2 = "FT_1X2"
FAMILY_OU_25 = "OU_GOALS_2_5"
FAMILY_BTTS = "BTTS"
FAMILY_DC = "DOUBLE_CHANCE"


def _row(
    family: str,
    selection: str,
    price: float | None,
    *,
    source_scope: str,
) -> dict[str, Any]:
    return {
        "family": family,
        "selection": selection,
        "price": price,
        "source_scope": source_scope,
    }


def map_featured_raw_to_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """featured → FT_1X2 (y hándicap asiático no entra en v0 canónico salvo OU si existiera)."""
    out: list[dict[str, Any]] = []
    proc = process_odds_feature(raw if isinstance(raw, dict) else {})
    snap = proc.get("market_snapshot") or {}
    if not isinstance(snap, dict):
        return out
    ft = snap.get("full_time_1x2") or {}
    if isinstance(ft, dict):
        for sel, out_sel in (("home", "1"), ("draw", "X"), ("away", "2")):
            node = ft.get(sel)
            p = None
            if isinstance(node, dict):
                p = node.get("current")
            elif node is not None:
                p = node
            if p is not None:
                try:
                    pr = round(float(p), 4)
                except (TypeError, ValueError):
                    pr = None
                if pr is not None:
                    out.append(_row(FAMILY_FT_1X2, out_sel, pr, source_scope="featured"))
    return out


def map_all_raw_to_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """all → OU 2.5, BTTS, Double chance (v0)."""
    out: list[dict[str, Any]] = []
    proc = process_odds_all(raw if isinstance(raw, dict) else {})
    em = proc.get("extended_markets") or {}
    if not isinstance(em, dict):
        return out
    goals = em.get("goals_depth") or {}
    safety = em.get("safety") or {}
    if isinstance(goals, dict):
        ou = goals.get("over_under_2.5") or {}
        if isinstance(ou, dict):
            for sel in ("over", "under"):
                p = ou.get(sel)
                if p is not None:
                    try:
                        pr = round(float(p), 4)
                    except (TypeError, ValueError):
                        pr = None
                    if pr is not None:
                        out.append(_row(FAMILY_OU_25, sel.upper(), pr, source_scope="all"))
        btts = goals.get("btts") or {}
        if isinstance(btts, dict):
            for sel in ("yes", "no"):
                p = btts.get(sel)
                if p is not None:
                    try:
                        pr = round(float(p), 4)
                    except (TypeError, ValueError):
                        pr = None
                    if pr is not None:
                        out.append(_row(FAMILY_BTTS, sel.upper(), pr, source_scope="all"))
    if isinstance(safety, dict):
        dc = safety.get("double_chance") or {}
        if isinstance(dc, dict):
            for sel in ("1X", "X2", "12"):
                p = dc.get(sel)
                if p is not None:
                    try:
                        pr = round(float(p), 4)
                    except (TypeError, ValueError):
                        pr = None
                    if pr is not None:
                        out.append(_row(FAMILY_DC, sel, pr, source_scope="all"))
    return out


def merge_canonical_rows(
    featured_rows: Iterable[dict[str, Any]],
    all_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Unifica post-mapeo; dedup por (family, selection) priorizando `all` para familias no 1X2."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for r in featured_rows:
        k = (str(r.get("family")), str(r.get("selection")))
        by_key[k] = dict(r)
    for r in all_rows:
        k = (str(r.get("family")), str(r.get("selection")))
        fam = k[0]
        if fam == FAMILY_FT_1X2:
            if k not in by_key:
                by_key[k] = dict(r)
            continue
        by_key[k] = dict(r)
    merged = list(by_key.values())
    merged.sort(key=lambda x: (x.get("family", ""), x.get("selection", "")))
    return merged


def is_ft_1x2_complete(rows: Iterable[dict[str, Any]]) -> bool:
    need = {"1", "X", "2"}
    got: set[str] = set()
    for r in rows:
        if r.get("family") != FAMILY_FT_1X2:
            continue
        if r.get("price") is None:
            continue
        sel = str(r.get("selection") or "")
        if sel in need:
            got.add(sel)
    return got == need


def count_core_additional_complete(rows: Iterable[dict[str, Any]]) -> int:
    """Cuenta familias core adicionales (OU, BTTS, DC) con al menos una selección con precio."""
    fams: set[str] = set()
    for r in rows:
        fam = str(r.get("family") or "")
        if fam not in (FAMILY_OU_25, FAMILY_BTTS, FAMILY_DC):
            continue
        if r.get("price") is None:
            continue
        fams.add(fam)
    return len(fams)


def is_event_useful_s65(rows: Iterable[dict[str, Any]]) -> bool:
    """D-06-066: FT_1X2 completo y ≥1 familia core adicional con dato."""
    rlist = list(rows)
    if not is_ft_1x2_complete(rlist):
        return False
    return count_core_additional_complete(rlist) >= 1

"""Convierte filas `bt2_odds_snapshot` (SM agregado) a filas estilo S65 para métricas."""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.bt2_market_canonical import normalized_pick_to_canonical
from apps.api.bt2_models import Bt2OddsSnapshot
from apps.api.bt2.providers.sofascore.canonical_map import (
    FAMILY_BTTS,
    FAMILY_DC,
    FAMILY_FT_1X2,
    FAMILY_OU_25,
)


def _ft_sel_to_1x2(sel: str) -> str:
    s = (sel or "").lower()
    if s in ("home", "1"):
        return "1"
    if s in ("draw", "x"):
        return "X"
    if s in ("away", "2"):
        return "2"
    return ""


def _dc_family_to_row(mc: str, price: float) -> dict[str, Any] | None:
    if mc == "DOUBLE_CHANCE_1X":
        return {"family": FAMILY_DC, "selection": "1X", "price": price, "source_scope": "sm_bt2_odds"}
    if mc == "DOUBLE_CHANCE_X2":
        return {"family": FAMILY_DC, "selection": "X2", "price": price, "source_scope": "sm_bt2_odds"}
    if mc == "DOUBLE_CHANCE_12":
        return {"family": FAMILY_DC, "selection": "12", "price": price, "source_scope": "sm_bt2_odds"}
    return None


def sm_odds_snapshot_rows_for_event(session: Session, event_id: int) -> list[dict[str, Any]]:
    rows = session.execute(select(Bt2OddsSnapshot).where(Bt2OddsSnapshot.event_id == event_id)).scalars().all()
    out: list[dict[str, Any]] = []
    for r in rows:
        try:
            price = float(r.odds)
        except (TypeError, ValueError):
            continue
        mc, sc = normalized_pick_to_canonical(str(r.market or ""), str(r.selection or ""))
        if mc == "FT_1X2":
            sel = _ft_sel_to_1x2(sc)
            if sel:
                out.append(
                    {
                        "family": FAMILY_FT_1X2,
                        "selection": sel,
                        "price": price,
                        "source_scope": "sm_bt2_odds",
                    }
                )
        elif mc == "OU_GOALS_2_5":
            if "over" in (sc or "").lower():
                out.append({"family": FAMILY_OU_25, "selection": "OVER", "price": price, "source_scope": "sm_bt2_odds"})
            elif "under" in (sc or "").lower():
                out.append({"family": FAMILY_OU_25, "selection": "UNDER", "price": price, "source_scope": "sm_bt2_odds"})
        elif mc == "BTTS":
            if sc == "yes":
                out.append({"family": FAMILY_BTTS, "selection": "YES", "price": price, "source_scope": "sm_bt2_odds"})
            elif sc == "no":
                out.append({"family": FAMILY_BTTS, "selection": "NO", "price": price, "source_scope": "sm_bt2_odds"})
        else:
            dr = _dc_family_to_row(mc, price)
            if dr:
                out.append(dr)
    return out

"""
Agregación de bt2_odds_snapshot → consensus + market_coverage (US-BE-032/033, whitelist DX §3.4).

Medianas por (mercado canónico, selección) entre casas; mercado completo = todas las piernas
presentes y cada cuota ≥ umbral configurado (D-06-024).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Iterable, Optional

# Piernas requeridas por mercado (códigos alineados a whitelist / bt2_market_canonical).
_REQUIRED_LEGS: dict[str, tuple[str, ...]] = {
    "FT_1X2": ("home", "draw", "away"),
    "OU_GOALS_2_5": ("over_2_5", "under_2_5"),
    "BTTS": ("yes", "no"),
    "OU_GOALS_1_5": ("over_1_5", "under_1_5"),
    "OU_GOALS_3_5": ("over_3_5", "under_3_5"),
    "DOUBLE_CHANCE_1X": ("yes",),
    "DOUBLE_CHANCE_X2": ("yes",),
    "DOUBLE_CHANCE_12": ("yes",),
}


def _median(vals: list[float]) -> float:
    if not vals:
        return 0.0
    return float(statistics.median(vals))


def classify_snapshot_row(market: str, selection: str) -> Optional[tuple[str, str]]:
    """
    Mapea fila CDM cruda → (market_canonical, selection_canonical).
    None si no reconocido (se ignora para consensus).
    """
    m_raw, s_raw = market or "", selection or ""
    m = m_raw.lower().strip()
    s = s_raw.strip()
    sl = s.lower()

    # Corners / cards totals (heurística)
    if "corner" in m and ("over" in m or "under" in m or "total" in m):
        line = "9_5" if "9.5" in m or "9,5" in m else "8_5" if "8.5" in m else "10_5" if "10.5" in m else None
        if line:
            mc = f"OU_CORNERS_{line}"
            if "over" in sl and "under" not in sl:
                return (mc, f"over_{line}")
            if "under" in sl:
                return (mc, f"under_{line}")
        return None

    if ("card" in m or "booking" in m) and ("over" in m or "under" in m):
        line = "4_5" if "4.5" in m else "5_5" if "5.5" in m else None
        if line:
            mc = f"OU_CARDS_{line}"
            if "over" in sl:
                return (mc, f"over_{line}")
            if "under" in sl:
                return (mc, f"under_{line}")
        return None

    # Double chance
    if "double chance" in m or "doble oportunidad" in m:
        if "1x" in sl or "1 or x" in sl or "home or draw" in sl:
            return ("DOUBLE_CHANCE_1X", "yes")
        if "x2" in sl or "draw or away" in sl:
            return ("DOUBLE_CHANCE_X2", "yes")
        if "12" in sl or "home or away" in sl:
            return ("DOUBLE_CHANCE_12", "yes")
        return None

    # BTTS
    if "both teams" in m or "btts" in m or ("team" in m and "score" in m):
        if "yes" in sl or "si" == sl or sl == "sí":
            return ("BTTS", "yes")
        if "no" in sl:
            return ("BTTS", "no")
        return None

    # Goals O/U — líneas
    if any(
        k in m
        for k in (
            "goals over/under",
            "total goals",
            "over/under",
            "goals ou",
            "goal line",
        )
    ) or ("goal" in m and ("over" in m or "under" in m)):
        if "1.5" in m or "1,5" in m:
            mk = "OU_GOALS_1_5"
            if "over" in sl:
                return (mk, "over_1_5")
            if "under" in sl:
                return (mk, "under_1_5")
        if "3.5" in m or "3,5" in m:
            mk = "OU_GOALS_3_5"
            if "over" in sl:
                return (mk, "over_3_5")
            if "under" in sl:
                return (mk, "under_3_5")
        if "2.5" in m or "2,5" in m or ("over" in m and "under" in m and "2" in m):
            if "over" in sl and "under" not in sl:
                return ("OU_GOALS_2_5", "over_2_5")
            if "under" in sl:
                return ("OU_GOALS_2_5", "under_2_5")
        return None

    # 1X2
    if any(
        k in m
        for k in (
            "1x2",
            "match winner",
            "full time result",
            "fulltime result",
            "winner",
        )
    ):
        if s in ("1", "Home") or sl == "home" or sl.startswith("home"):
            return ("FT_1X2", "home")
        if s in ("X", "Draw", "x") or sl == "draw":
            return ("FT_1X2", "draw")
        if s in ("2", "Away") or sl == "away" or sl.startswith("away"):
            return ("FT_1X2", "away")
        return None

    return None


@dataclass(frozen=True)
class AggregatedOdds:
    consensus: dict[str, dict[str, float]]
    market_coverage: dict[str, bool]
    markets_available: list[str]
    by_bookmaker: list[dict[str, Any]]


def aggregate_odds_for_event(
    snapshot_rows: Iterable[tuple[Any, str, str, str, float, Any]],
    *,
    min_decimal: float = 1.30,
) -> AggregatedOdds:
    """
    snapshot_rows: iterables de (bookmaker, market, selection, fetched_at unused, odds decimal, ...)
    Acepta tuplas de DB: (bookmaker, market, selection, odds, fetched_at) — normalizar en caller.
    """
    buckets: dict[tuple[str, str], list[float]] = {}
    raw_keys: set[tuple[str, str]] = set()
    by_book: list[dict[str, Any]] = []

    for row in snapshot_rows:
        if len(row) >= 5:
            book, mk, sel, odds_val, fetched = (row[0], row[1], row[2], row[3], row[4])
        else:
            continue
        try:
            dec = float(odds_val)
        except (TypeError, ValueError):
            continue
        if dec < min_decimal:
            continue
        cl = classify_snapshot_row(str(mk), str(sel))
        if not cl:
            raw_keys.add((str(mk).strip(), str(sel).strip()))
            continue
        mc, sc = cl
        buckets.setdefault((mc, sc), []).append(dec)
        fa = fetched.isoformat() if hasattr(fetched, "isoformat") else str(fetched)
        by_book.append(
            {
                "bookmaker": str(book),
                "market_canonical": mc,
                "selection_canonical": sc,
                "decimal": dec,
                "fetched_at": fa,
            }
        )

    consensus: dict[str, dict[str, float]] = {}
    for (mc, sc), vals in buckets.items():
        consensus.setdefault(mc, {})[sc] = _median(vals)

    market_coverage: dict[str, bool] = {}
    for mc, legs in _REQUIRED_LEGS.items():
        sub = consensus.get(mc) or {}
        market_coverage[mc] = all(
            leg in sub and sub[leg] >= min_decimal for leg in legs
        )

    for mc, sel_dict in consensus.items():
        if mc in market_coverage:
            continue
        if mc.startswith("OU_CORNERS_") or mc.startswith("OU_CARDS_") or mc.startswith("OU_GOALS_"):
            keys = list(sel_dict.keys())
            if len(keys) >= 2:
                market_coverage[mc] = all(
                    sel_dict[k] >= min_decimal for k in keys if k in sel_dict
                )
            else:
                market_coverage[mc] = False
        elif mc.startswith("DOUBLE_CHANCE_"):
            market_coverage[mc] = bool(sel_dict.get("yes", 0) >= min_decimal)
        elif mc == "BTTS":
            market_coverage[mc] = (
                sel_dict.get("yes", 0) >= min_decimal and sel_dict.get("no", 0) >= min_decimal
            )

    # Mercados con al menos una pierna (aunque incompleto)
    markets_available = sorted({mc for mc, _ in buckets.keys()})

    return AggregatedOdds(
        consensus=consensus,
        market_coverage=market_coverage,
        markets_available=markets_available,
        by_bookmaker=by_book[:80],
    )


def event_passes_value_pool(
    agg: AggregatedOdds,
    *,
    min_decimal: float = 1.30,
) -> bool:
    """Al menos un mercado canónico completo con todas las piernas ≥ min_decimal."""
    for mc, ok in agg.market_coverage.items():
        if not ok:
            continue
        legs = _REQUIRED_LEGS.get(mc, ())
        sub = agg.consensus.get(mc) or {}
        if all(sub.get(leg, 0) >= min_decimal for leg in legs):
            return True
    return False


def count_distinct_bookmakers_ft_1x2(by_bookmaker: list[dict[str, Any]]) -> int:
    books: set[str] = set()
    for r in by_bookmaker:
        if r.get("market_canonical") != "FT_1X2":
            continue
        b = str(r.get("bookmaker") or "")
        if b:
            books.add(b)
    return len(books)


def ft_1x2_book_spread_ratio(consensus: dict[str, dict[str, float]]) -> Optional[float]:
    """max/min de las tres implícitas 1X2 en consensus; None si incompleto."""
    sub = consensus.get("FT_1X2") or {}
    need = ("home", "draw", "away")
    vals = [sub.get(k) for k in need]
    if not all(v and v > 1.0 for v in vals):
        return None
    implied = [1.0 / v for v in vals if v]
    return max(implied) / min(implied) if implied and min(implied) > 0 else None


def premium_tier_eligible(
    agg: AggregatedOdds,
    league_tier: Optional[str],
    *,
    min_books_ft_1x2: int = 2,
    max_implied_spread: float = 1.12,
) -> bool:
    """
    D-06-024 § premium: más estricto que standard (ligas S/A, 1X2 completo, varias casas, consenso ajustado).
    """
    tier = (league_tier or "").upper()
    if tier not in ("S", "A"):
        return False
    if not agg.market_coverage.get("FT_1X2"):
        return False
    if count_distinct_bookmakers_ft_1x2(agg.by_bookmaker) < min_books_ft_1x2:
        return False
    spread = ft_1x2_book_spread_ratio(agg.consensus)
    if spread is None or spread > max_implied_spread:
        return False
    return True


def data_completeness_score(agg: AggregatedOdds) -> int:
    """Heurística 0–100 para admin T-183 (no es probabilidad de acierto)."""
    if not agg.market_coverage:
        return 0
    ok = sum(1 for v in agg.market_coverage.values() if v)
    tot = len(agg.market_coverage)
    base = int(round(100.0 * ok / max(tot, 1)))
    return min(100, max(0, base))

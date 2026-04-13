"""
US-BE-033 / T-177 — pool valor: ligas prioritarias opcionales, cuota mín 1.30, mercado canónico completo.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, List, Optional, Tuple

from apps.api.bt2_dsr_odds_aggregation import (
    AggregatedOdds,
    aggregate_odds_for_event,
    event_passes_value_pool,
    premium_tier_eligible,
)

MIN_ODDS_DECIMAL_DEFAULT: float = 1.30


def parse_priority_league_ids(env_csv: str) -> Optional[set[int]]:
    """`BT2_PRIORITY_LEAGUE_IDS` = lista opcional de `bt2_leagues.id` separados por coma."""
    s = (env_csv or "").strip()
    if not s:
        return None
    out: set[int] = set()
    for part in s.split(","):
        p = part.strip()
        if p.isdigit():
            out.add(int(p))
    return out if out else None


def _tier_rank(tier: Optional[str]) -> int:
    t = (tier or "").upper()
    return {"S": 1, "A": 2, "B": 3}.get(t, 4)


def _house_margin_proxy(agg: AggregatedOdds) -> float:
    sub = agg.consensus.get("FT_1X2") or {}
    impl: list[float] = []
    for k in ("home", "draw", "away"):
        v = sub.get(k)
        if v and v > 1.0:
            impl.append(1.0 / float(v))
    if impl:
        return float(sum(impl) - 1.0)
    # sin 1X2: menor cuota entre selecciones cubiertas
    best = 999.0
    for mc, ok in agg.market_coverage.items():
        if not ok:
            continue
        for _sc, od in (agg.consensus.get(mc) or {}).items():
            if od and od >= MIN_ODDS_DECIMAL_DEFAULT:
                best = min(best, float(od))
    return best


def count_future_events_window(cur, day_start_utc: datetime, day_end_utc: datetime) -> int:
    cur.execute(
        """
        SELECT COUNT(*)::int
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        WHERE e.kickoff_utc >= %s
          AND e.kickoff_utc < %s
          AND e.status = 'scheduled'
          AND l.is_active = true
        """,
        (day_start_utc, day_end_utc),
    )
    row = cur.fetchone()
    return int(row[0] or 0) if row else 0


def _sql_prefilter_event_rows(
    cur,
    day_start_utc: datetime,
    day_end_utc: datetime,
    league_filter: Optional[set[int]],
) -> list[tuple[Any, ...]]:
    q = """
        SELECT e.id, e.kickoff_utc, l.tier, e.league_id
        FROM bt2_events e
        JOIN bt2_leagues l ON l.id = e.league_id
        WHERE e.kickoff_utc >= %s
          AND e.kickoff_utc < %s
          AND e.status = 'scheduled'
          AND l.is_active = true
    """
    params: list[Any] = [day_start_utc, day_end_utc]
    if league_filter:
        q += " AND e.league_id = ANY(%s)"
        params.append(list(league_filter))
    q += """
        ORDER BY
            CASE l.tier WHEN 'S' THEN 1 WHEN 'A' THEN 2 WHEN 'B' THEN 3 ELSE 4 END ASC,
            e.kickoff_utc ASC
        LIMIT 220
    """
    cur.execute(q, tuple(params))
    return list(cur.fetchall())


def _fetch_odds_grouped(cur, event_ids: list[int]) -> dict[int, list[tuple[Any, ...]]]:
    if not event_ids:
        return {}
    cur.execute(
        """
        SELECT event_id, bookmaker, market, selection, odds, fetched_at
        FROM bt2_odds_snapshot
        WHERE event_id = ANY(%s)
        """,
        (event_ids,),
    )
    by_eid: dict[int, list[tuple[Any, ...]]] = defaultdict(list)
    for r in cur.fetchall():
        by_eid[int(r[0])].append((r[1], r[2], r[3], r[4], r[5]))
    return by_eid


def build_value_pool_for_snapshot(
    cur,
    day_start_utc: datetime,
    day_end_utc: datetime,
    *,
    league_filter: Optional[set[int]] = None,
    min_decimal: float = MIN_ODDS_DECIMAL_DEFAULT,
) -> Tuple[
    List[Tuple[int, Any, float, AggregatedOdds, Optional[str]]],
    int,
]:
    """
    Devuelve:
      eligible_rows: (event_id, kickoff_utc, house_margin_proxy, agg, league_tier) orden calidad,
      raw_prefilter_count (eventos considerados antes de filtro canónico).
    """
    pre = _sql_prefilter_event_rows(cur, day_start_utc, day_end_utc, league_filter)
    eids = [int(r[0]) for r in pre]
    odds_by_eid = _fetch_odds_grouped(cur, eids)
    eligible: list[tuple[int, Any, float, AggregatedOdds, Optional[str]]] = []
    for r in pre:
        eid = int(r[0])
        ko = r[1]
        tier = r[2]
        rows = odds_by_eid.get(eid, [])
        agg = aggregate_odds_for_event(rows, min_decimal=min_decimal)
        if not event_passes_value_pool(agg, min_decimal=min_decimal):
            continue
        hm = _house_margin_proxy(agg)
        eligible.append((eid, ko, hm, agg, tier if tier is not None else None))
    eligible.sort(key=lambda x: (_tier_rank(x[4]), x[2]))
    return eligible, len(pre)


def premium_eligible_ids_from_pool(
    pool: List[Tuple[int, Any, float, AggregatedOdds, Optional[str]]],
) -> set[int]:
    out: set[int] = set()
    for eid, _ko, _hm, agg, tier in pool:
        if premium_tier_eligible(agg, tier):
            out.add(eid)
    return out

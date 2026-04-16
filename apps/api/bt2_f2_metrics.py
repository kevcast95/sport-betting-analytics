"""
T-263 / T-264 — Métricas F2: KPI oficial vs relajado, desgloses §6 DECISIONES_CIERRE_F2_S6_3_FINAL.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Mapping, Optional, Protocol, runtime_checkable

from apps.api.bt2_f2_league_constants import resolve_f2_official_league_bt2_ids
from apps.api.bt2_pool_eligibility_v1 import (
    POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63,
    evaluate_pool_eligibility_v1_from_db,
)


@runtime_checkable
class _DbCursor(Protocol):
    def execute(self, query: str, params: Any = None) -> None: ...
    def fetchall(self) -> list[Any]: ...
    def fetchone(self) -> Any: ...


def _parse_day(s: str) -> date:
    y, m, d = (int(x) for x in s.split("-")[:3])
    return date(y, m, d)


def _day_key(d: date) -> str:
    return d.isoformat()


def fetch_f2_event_ids_in_window(
    cur: _DbCursor,
    *,
    league_bt2_ids: list[int],
    from_day_key: str,
    to_day_key: str,
) -> list[int]:
    if not league_bt2_ids:
        return []
    cur.execute(
        """
        SELECT DISTINCT dp.event_id
        FROM bt2_daily_picks dp
        INNER JOIN bt2_events e ON e.id = dp.event_id
        WHERE e.league_id = ANY(%s::int[])
          AND dp.operating_day_key >= %s
          AND dp.operating_day_key <= %s
        ORDER BY 1
        """,
        (league_bt2_ids, from_day_key, to_day_key),
    )
    rows = cur.fetchall()
    out: list[int] = []
    for r in rows:
        if isinstance(r, Mapping):
            out.append(int(r["event_id"]))
        else:
            out.append(int(r[0]))
    return out


def _rollup_discard(disc: dict[str, int], reason: Optional[str]) -> None:
    k = reason or "(sin código)"
    disc[k] = disc.get(k, 0) + 1


def compute_f2_live_metrics_for_events(
    cur: _DbCursor,
    event_ids: list[int],
) -> dict[str, Any]:
    """
    Re-evalúa en vivo (sin confiar solo en auditoría persistida) con min_fam=2 vs 1.
    """
    official_ok = 0
    relaxed_ok = 0
    discard_official: dict[str, int] = {}
    core_cov = {"ft_1x2_complete": 0, "second_core_family": 0, "raw_present": 0, "lineups_ok": 0}
    n = 0
    for eid in event_ids:
        ro = evaluate_pool_eligibility_v1_from_db(
            cur, eid, min_distinct_market_families=POOL_ELIGIBILITY_MIN_FAMILIES_OFFICIAL_S63
        )
        rr = evaluate_pool_eligibility_v1_from_db(cur, eid, min_distinct_market_families=1)
        if ro is None:
            continue
        n += 1
        if ro.is_eligible:
            official_ok += 1
        else:
            _rollup_discard(discard_official, ro.primary_discard_reason)
        if rr is not None and rr.is_eligible:
            relaxed_ok += 1
        det = (ro.detail or {}) if ro else {}
        fc = det.get("families_covered") or []
        if "FT_1X2" in fc:
            core_cov["ft_1x2_complete"] += 1
        if any(x in fc for x in ("OU_GOALS", "BTTS", "DOUBLE_CHANCE")):
            core_cov["second_core_family"] += 1
        # proxies desde detail si existieran en futuras versiones
        if det.get("pool_tier") == "A":
            pass

    def _pct(num: int, den: int) -> Optional[float]:
        if den <= 0:
            return None
        return round(100.0 * num / den, 2)

    return {
        "candidate_events_count": n,
        "eligible_official_count": official_ok,
        "eligible_relaxed_count": relaxed_ok,
        "pool_eligibility_rate_official_pct": _pct(official_ok, n),
        "pool_eligibility_rate_relaxed_pct": _pct(relaxed_ok, n),
        "primary_discard_breakdown_official": discard_official,
        "core_family_coverage_counts": core_cov,
    }


def build_f2_pool_eligibility_metrics(
    cur: _DbCursor,
    *,
    operating_day_key: Optional[str] = None,
    days: int = 30,
) -> dict[str, Any]:
    """
    T-263 — Ventana: un día (`operating_day_key`) o últimos `days` días calendario
    respecto al máximo `operating_day_key` presente en `bt2_daily_picks`, restringido a 5 ligas F2.
    """
    league_ids = resolve_f2_official_league_bt2_ids(cur)
    if not league_ids:
        return {
            "league_bt2_ids_resolved": [],
            "sportmonks_reference": "ver bt2_f2_league_constants.F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS",
            "window_from": None,
            "window_to": None,
            "operating_day_key_filter": operating_day_key,
            "metrics_global": {},
            "thresholds": {
                "target_global_official_pct": 60.0,
                "target_per_league_official_pct": 40.0,
                "pass_global_60": None,
                "pass_all_leagues_40": None,
            },
            "insufficient_market_families_dominant": None,
            "note_es": "No se resolvieron ligas F2 en bt2_leagues (¿migración/seed?).",
        }

    if operating_day_key:
        w_from = w_to = operating_day_key
    else:
        cur.execute(
            """
            SELECT MAX(operating_day_key)::text AS mx FROM bt2_daily_picks
            """
        )
        row = cur.fetchone()
        mx = None
        if row:
            if isinstance(row, Mapping):
                mx = row.get("mx")
            else:
                mx = row[0]
        if not mx:
            return {
                "league_bt2_ids_resolved": league_ids,
                "window_from": None,
                "window_to": None,
                "operating_day_key_filter": None,
                "metrics_global": {},
                "thresholds": {},
                "note_es": "Sin operating_day_key en bt2_daily_picks.",
            }
        end = _parse_day(str(mx))
        start = end - timedelta(days=max(1, int(days)) - 1)
        w_from = _day_key(start)
        w_to = _day_key(end)

    ev_ids = fetch_f2_event_ids_in_window(
        cur,
        league_bt2_ids=league_ids,
        from_day_key=w_from,
        to_day_key=w_to,
    )
    glob = compute_f2_live_metrics_for_events(cur, ev_ids)
    po = glob.get("pool_eligibility_rate_official_pct")
    pass_g = po is not None and po >= 60.0
    br = glob.get("primary_discard_breakdown_official") or {}
    ins_count = int(br.get("INSUFFICIENT_MARKET_FAMILIES") or 0)
    n_cand = int(glob.get("candidate_events_count") or 0)
    dominant_ins = n_cand > 0 and ins_count >= max(1, int(0.5 * n_cand))

    # Por liga
    per_league: list[dict[str, Any]] = []
    pass_all = True
    if league_ids:
        cur.execute(
            """
            SELECT id, name FROM bt2_leagues WHERE id = ANY(%s::int[]) ORDER BY name
            """,
            (league_ids,),
        )
        for lr in cur.fetchall():
            lid = int(lr["id"] if isinstance(lr, Mapping) else lr[0])
            lname = str(lr["name"] if isinstance(lr, Mapping) else lr[1])
            cur.execute(
                """
                SELECT DISTINCT dp.event_id
                FROM bt2_daily_picks dp
                INNER JOIN bt2_events e ON e.id = dp.event_id
                WHERE e.league_id = %s
                  AND dp.operating_day_key >= %s
                  AND dp.operating_day_key <= %s
                """,
                (lid, w_from, w_to),
            )
            eids = [int(r["event_id"] if isinstance(r, Mapping) else r[0]) for r in cur.fetchall()]
            m = compute_f2_live_metrics_for_events(cur, eids)
            pct = m.get("pool_eligibility_rate_official_pct")
            pl_ok = pct is not None and pct >= 40.0
            if not pl_ok and eids:
                pass_all = False
            per_league.append(
                {
                    "league_id": lid,
                    "league_name": lname,
                    "candidate_events_count": m.get("candidate_events_count"),
                    "pool_eligibility_rate_official_pct": pct,
                    "pass_league_40": pl_ok if eids else None,
                }
            )

    if not ev_ids:
        pass_g = None
        pass_all = None

    return {
        "league_bt2_ids_resolved": league_ids,
        "window_from": w_from,
        "window_to": w_to,
        "operating_day_key_filter": operating_day_key,
        "metrics_global": glob,
        "metrics_by_league": per_league,
        "thresholds": {
            "target_global_official_pct": 60.0,
            "target_per_league_official_pct": 40.0,
            "pass_global_60": pass_g,
            "pass_all_leagues_40": pass_all if league_ids else None,
        },
        "insufficient_market_families_dominant": dominant_ins,
        "note_es": (
            "KPI oficial = re-evaluación en vivo con min_fam=2 (norma F2). "
            "Relajado = min_fam=1 (observabilidad §5)."
        ),
    }


def f2_closure_report_markdown(payload: dict[str, Any]) -> str:
    """T-264 — salida pegable en EJECUCION.md."""
    lines = [
        "## Reporte cierre F2 (T-264)",
        "",
        f"- Ventana: `{payload.get('window_from')}` … `{payload.get('window_to')}`",
        f"- Ligas BT2 resueltas: `{payload.get('league_bt2_ids_resolved')}`",
        "",
    ]
    mg = payload.get("metrics_global") or {}
    lines.append(
        f"- **pool_eligibility_rate_official:** {mg.get('pool_eligibility_rate_official_pct')}% "
        f"({mg.get('eligible_official_count')}/{mg.get('candidate_events_count')})"
    )
    lines.append(
        f"- **pool_eligibility_rate_relaxed:** {mg.get('pool_eligibility_rate_relaxed_pct')}% "
        f"({mg.get('eligible_relaxed_count')}/{mg.get('candidate_events_count')})"
    )
    th = payload.get("thresholds") or {}
    lines.append(f"- **Pasa umbral global 60%:** {th.get('pass_global_60')}")
    lines.append(f"- **Pasa 40% todas las ligas:** {th.get('pass_all_leagues_40')}")
    lines.append(
        f"- **INSUFFICIENT_MARKET_FAMILIES dominante:** {payload.get('insufficient_market_families_dominant')}"
    )
    lines.append("")
    lines.append("### Por liga")
    for row in payload.get("metrics_by_league") or []:
        lines.append(
            f"- {row.get('league_name')} (id={row.get('league_id')}): "
            f"{row.get('pool_eligibility_rate_official_pct')}% "
            f"candidatos={row.get('candidate_events_count')} "
            f"pasa40={row.get('pass_league_40')}"
        )
    return "\n".join(lines) + "\n"

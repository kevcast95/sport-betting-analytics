#!/usr/bin/env python3
"""
Fase 3C — read-only: comparar cutoffs candidatos para future historical_sm_lbu_replay.

Candidatos fijados en código (máx 3):
  C1: T-60
  C2: T-180
  C3: 09:00 America/Bogota en la fecha calendario local (Bogotá) del partido, capado
      a no superar (kickoff_utc - 60s) (evita ex-post; sin leakage post-KO en líneas tardías)
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # py<3.9
    ZoneInfo = None  # type: ignore[misc, assignment]

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

import psycopg2.extras

from apps.api.bt2_admin_backtest_replay import kickoff_day_key_bogota
from apps.api.bt2_dsr_odds_aggregation import (
    AggregatedOdds,
    aggregate_odds_for_event,
    data_completeness_score,
    event_passes_value_pool,
    ft_1x2_book_spread_ratio,
)
from apps.api.bt2_settings import bt2_settings

MARKET_1X2 = 1
MARKET_OU_25 = 80
MIN_DEC = 1.30

# Nombres estables para JSON / contrato
CUTOFF_SPECS: list[tuple[str, str]] = [
    (
        "T60",
        "kickoff_utc - 60 minutos; última señal SM admitida: latest_bookmaker_update <= cutoff (UTC alineada al kick almacenado en bt2_events)",
    ),
    (
        "T180",
        "kickoff_utc - 180 minutos; mismo criterio de línea que T60, ventana de cierre ~3h antes de KO",
    ),
    (
        "Bog09_same_day",
        "09:00:00 (reloj) America/Bogotá en la misma fecha calendario local (Bogotá) que el partido, "
        "y min(ese instante, kickoff_utc - 60s) — si el partido es por la mañana antes de las 09, "
        "el corte se acerca a pre-KO, no a la mañana siguiente",
    ),
]


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def _parse_ts(val: Any) -> Optional[datetime]:
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        t = val
    else:
        txt = str(val).strip()[:19]
        try:
            t = datetime.strptime(txt, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                from dateutil import parser as dateparser

                t = dateparser.parse(str(val).strip())
            except Exception:
                return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


def _cut_t60(ko: datetime) -> datetime:
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    return ko - timedelta(hours=1)


def _cut_t180(ko: datetime) -> datetime:
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    return ko - timedelta(hours=3)


def _cut_bog09_same_local_day_capped(ko: datetime) -> datetime:
    """9am Bogotá en el día calendario local del KO; nunca post-KO (mín. con kick-60s)."""
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    if ZoneInfo is None:
        return _cut_t60(ko)
    z = ZoneInfo("America/Bogota")
    dkey = kickoff_day_key_bogota(ko)
    if not dkey:
        return ko - timedelta(hours=1)
    d = date.fromisoformat(dkey)
    t09 = datetime(d.year, d.month, d.day, 9, 0, 0, tzinfo=z)
    t09_utc = t09.astimezone(timezone.utc)
    pre_ko = ko - timedelta(seconds=60)
    return min(t09_utc, pre_ko)


CUTOFF_FNS: dict[str, Callable[[datetime], datetime]] = {
    "T60": _cut_t60,
    "T180": _cut_t180,
    "Bog09_same_day": _cut_bog09_same_local_day_capped,
}


def extract_cdm_rows(payload: dict[str, Any]) -> list[tuple[str, str, str, float, Optional[datetime]]]:
    odds_raw = payload.get("odds") or []
    if not isinstance(odds_raw, list):
        return []
    out: list = []
    for o in odds_raw:
        if not isinstance(o, dict):
            continue
        mid = o.get("market_id")
        if mid not in (MARKET_1X2, MARKET_OU_25):
            continue
        if mid == MARKET_OU_25 and str(o.get("total") or "") != "2.5":
            continue
        try:
            val = float(o.get("value") or 0)
        except (TypeError, ValueError):
            continue
        if val <= 1.0:
            continue
        label = str(o.get("label") or o.get("name") or "").strip()
        if not label:
            continue
        mdesc = o.get("market_description") or (
            "1X2" if mid == MARKET_1X2 else "Over/Under 2.5"
        )
        key_m = str(mdesc)[:100]
        book = str(o.get("bookmaker_id") or "0")
        lbu = _parse_ts(o.get("latest_bookmaker_update")) or _parse_ts(o.get("created_at"))
        out.append((book, key_m, label[:100], val, lbu))
    return out


def to_agg_tuples(
    rows: list[tuple[str, str, str, float, Optional[datetime]]],
) -> list[tuple[str, str, str, float, datetime]]:
    syn = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return [(a, b, c, d, e or syn) for a, b, c, d, e in rows]


def stats_agg(agg: AggregatedOdds) -> tuple[bool, int, Optional[float], bool, Optional[float]]:
    sub = agg.consensus.get("FT_1X2") or {}
    f1x2 = all(k in sub and sub[k] and float(sub[k]) > MIN_DEC for k in ("home", "draw", "away"))
    return (
        event_passes_value_pool(agg, min_decimal=MIN_DEC),
        data_completeness_score(agg),
        ft_1x2_book_spread_ratio(agg.consensus),
        f1x2,
        (float(sub["home"]) if sub.get("home") is not None else None),
    )


@dataclass
class PerFixture:
    fixture_id: int
    kickoff_utc: str
    league_tier: Optional[str]
    n_lines_s1: int
    n_lbu_missing: int
    n_pass: dict[str, int]
    vp: dict[str, bool]
    dcs: dict[str, int]
    f1x2: dict[str, bool]
    home: dict[str, Optional[float]]
    abs_dhome_vs_s1: dict[str, Optional[float]]  # T60, T180, Bog09 (vs baseline S1)


def main() -> None:
    year = 2025
    n_per_month = 10
    conn = psycopg2.connect(_dsn())
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    picked: list[dict[str, Any]] = []
    for m in range(1, 13):
        cur.execute(
            """
            WITH pool AS (
              SELECT r.fixture_id, r.payload
              FROM raw_sportmonks_fixtures r
              INNER JOIN bt2_events e ON e.sportmonks_fixture_id = r.fixture_id
                AND e.kickoff_utc IS NOT NULL
              WHERE r.fixture_date >= %s::date AND r.fixture_date < %s::date
                AND EXTRACT(MONTH FROM r.fixture_date) = %s
                AND jsonb_typeof(r.payload->'odds') = 'array'
                AND jsonb_array_length(r.payload->'odds') > 2
            )
            SELECT fixture_id, payload
            FROM pool
            ORDER BY random()
            LIMIT %s
            """,
            (f"{year}-01-01", f"{year + 1}-01-01", m, n_per_month),
        )
        picked.extend([dict(x) for x in cur.fetchall()])

    rows_out: list[PerFixture] = []
    for r in picked:
        fid = int(r["fixture_id"])
        pl = r["payload"]
        if isinstance(pl, str):
            pl = json.loads(pl)
        cur.execute(
            """
            SELECT e.kickoff_utc, l.tier
            FROM bt2_events e
            LEFT JOIN bt2_leagues l ON l.id = e.league_id
            WHERE e.sportmonks_fixture_id = %s
            """,
            (fid,),
        )
        er = cur.fetchone()
        if not er or not er.get("kickoff_utc"):
            continue
        ko: datetime = er["kickoff_utc"]
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)

        raw = extract_cdm_rows(pl)
        n_miss = sum(1 for t in raw if t[4] is None)
        t_s1 = to_agg_tuples(raw)
        a_s1 = aggregate_odds_for_event(t_s1, min_decimal=MIN_DEC)
        vp1, d1, _, f1_s1, h1 = stats_agg(a_s1)

        n_pass: dict[str, int] = {}
        vp: dict[str, bool] = {"S1": bool(vp1)}
        dcs: dict[str, int] = {"S1": d1}
        f1: dict[str, bool] = {"S1": bool(f1_s1)}
        home: dict[str, Optional[float]] = {"S1": h1}
        abs_d: dict[str, Optional[float]] = {}

        for k, fn in CUTOFF_FNS.items():
            c = fn(ko)
            sub = [t for t in raw if t[4] is not None and t[4] <= c]
            n_pass[k] = len(sub)
            a = aggregate_odds_for_event(to_agg_tuples(sub), min_decimal=MIN_DEC)
            vpk, dck, _, f1k, hk = stats_agg(a)
            vp[k] = bool(vpk)
            dcs[k] = dck
            f1[k] = bool(f1k)
            home[k] = hk
            if h1 and hk and h1 > 0:
                abs_d[k] = abs(float(hk) - float(h1))
            else:
                abs_d[k] = None

        rows_out.append(
            PerFixture(
                fixture_id=fid,
                kickoff_utc=ko.isoformat(),
                league_tier=(str(er["tier"]) if er.get("tier") else None),
                n_lines_s1=len(raw),
                n_lbu_missing=n_miss,
                n_pass=n_pass,
                vp=vp,
                dcs=dcs,
                f1x2=f1,
                home=home,
                abs_dhome_vs_s1=abs_d,
            )
        )
    cur.close()
    conn.close()

    n = len(rows_out)
    if n == 0:
        print(json.dumps({"error": "no fixtures"}, indent=2))
        return

    by_key: dict[str, Any] = {
        "contract_cutoffs_frozen": [{"id": a[0], "description_es": a[1]} for a in CUTOFF_SPECS],
        "n_fixtures": n,
        "muestra": f"12 meses x {n_per_month} max; raw + INNER JOIN bt2_events.kickoff; 1X2+O/2,5; min_dec={MIN_DEC}",
    }

    for k in CUTOFF_FNS:
        n_ok_vp = sum(1 for r in rows_out if r.vp.get(k, False))
        s1ok = sum(1 for r in rows_out if r.vp.get("S1", False))
        br = sum(1 for r in rows_out if r.vp.get("S1") and not r.vp.get(k))
        line_surv = [r.n_pass.get(k, 0) / r.n_lines_s1 for r in rows_out if r.n_lines_s1 > 0]
        t_surv = round(sum(line_surv) / max(len(line_surv), 1), 4)
        dhome_big = [r for r in rows_out if (r.abs_dhome_vs_s1.get(k) or 0) > 0.15]
        f1x_ok = sum(1 for r in rows_out if r.f1x2.get(k, False))
        f1s1 = sum(1 for r in rows_out if r.f1x2.get("S1", False))
        by_key[k] = {
            "n_value_pool": n_ok_vp,
            "n_value_pool_S1": s1ok,
            "fixtures_que_perdieron_vp_teniendolo_en_S1": br,
            "tasa_sobrevivencia_lineas_media": t_surv,
            "ft1x2_completo": f1x_ok,
            "ft1x2_completo_S1": f1s1,
            "abs_delta_home_>_0.15 (vs S1)": len(dhome_big),
            "ratio_abs_delta_>_0.15": round(len(dhome_big) / n, 4) if n else 0,
        }

    by_key["tabla"] = [asdict(x) for x in rows_out]
    print(json.dumps(by_key, indent=2, default=str))


if __name__ == "__main__":
    main()

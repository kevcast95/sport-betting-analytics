#!/usr/bin/env python3
"""
Prototipo mínimo read-only: agregado de cuotas 2025 desde raw SportMonks con corte T-60
(latest_bookmaker_update o created_at), sin bt2_odds_snapshot.fetched_at.

No modifica datos. No es parity con replay live. exploratory_only.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

import psycopg2.extras

from apps.api.bt2_dsr_odds_aggregation import (
    aggregate_odds_for_event,
    data_completeness_score,
    event_passes_value_pool,
)
from apps.api.bt2_settings import bt2_settings

MARKET_1X2 = 1
MARKET_OU_25 = 80
MIN_DEC = 1.30
MODE = "historical_sm_lbu"
CUTOFF_MODE = "T60"


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


def cutoff_t60(ko: datetime) -> datetime:
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    return ko - timedelta(hours=1)


def extract_cdm_rows(
    payload: dict[str, Any],
) -> list[tuple[str, str, str, float, Optional[datetime]]]:
    """Mismos market_id / filtros que normalize_fixtures (1X2 + O/U 2.5)."""
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
        lbu = _parse_ts(o.get("latest_bookmaker_update")) or _parse_ts(
            o.get("created_at")
        )
        out.append((book, key_m, label[:100], val, lbu))
    return out


def to_agg_tuples(
    rows: list[tuple[str, str, str, float, Optional[datetime]]],
) -> list[tuple[str, str, str, float, datetime]]:
    syn = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return [(a, b, c, d, e or syn) for a, b, c, d, e in rows]


@dataclass
class FixtureRow:
    fixture_id: int
    event_id: int
    kickoff_utc: str
    n_lines_before_filter: int
    n_lines_t60: int
    n_lines_lbu_null: int
    value_pool: bool
    data_completeness_score: int
    ft1x2_home_consensus: Optional[float]
    ft1x2_draw: Optional[float]
    ft1x2_away: Optional[float]
    market_coverage_keys: list[str]
    kickoff_month: str
    kickoff_week: str


def run(
    *,
    day_from: date,
    day_to_inclusive: date,
    max_fixtures: int,
) -> dict[str, Any]:
    start = datetime.combine(day_from, time.min, tzinfo=timezone.utc)
    end = datetime.combine(
        day_to_inclusive + timedelta(days=1), time.min, tzinfo=timezone.utc
    )
    conn = psycopg2.connect(_dsn())
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT
          e.id AS event_id,
          e.sportmonks_fixture_id AS fixture_id,
          e.kickoff_utc,
          r.payload
        FROM bt2_events e
        INNER JOIN raw_sportmonks_fixtures r ON r.fixture_id = e.sportmonks_fixture_id
        WHERE e.kickoff_utc IS NOT NULL
          AND e.kickoff_utc >= %s
          AND e.kickoff_utc < %s
        ORDER BY e.kickoff_utc
        LIMIT %s
        """,
        (start, end, max_fixtures),
    )
    raw_rows = cur.fetchall()
    cur.close()
    conn.close()

    items: list[dict[str, Any]] = []
    n_vp = 0
    n_lines_b = 0
    n_lines_a = 0
    month_counts: dict[str, int] = {}
    week_counts: dict[str, int] = {}
    market_cov_counts: dict[str, int] = {}
    dcs_values: list[int] = []
    n_not_usable = 0
    for row in raw_rows:
        pl = row["payload"]
        if isinstance(pl, str):
            pl = json.loads(pl)
        ko: datetime = row["kickoff_utc"]
        if ko.tzinfo is None:
            ko = ko.replace(tzinfo=timezone.utc)
        t_cut = cutoff_t60(ko)
        before = extract_cdm_rows(pl)
        n_lbu_n = sum(1 for t in before if t[4] is None)
        t60 = [t for t in before if t[4] is not None and t[4] <= t_cut]
        n_lines_b += len(before)
        n_lines_a += len(t60)
        agg = aggregate_odds_for_event(to_agg_tuples(t60), min_decimal=MIN_DEC)
        vp = event_passes_value_pool(agg, min_decimal=MIN_DEC)
        if vp:
            n_vp += 1
        else:
            n_not_usable += 1
        dcs = data_completeness_score(agg)
        dcs_values.append(int(dcs))
        ft = agg.consensus.get("FT_1X2") or {}
        mkeys = [k for k, v in (agg.market_coverage or {}).items() if v]
        for mk in mkeys:
            market_cov_counts[mk] = market_cov_counts.get(mk, 0) + 1
        ko_utc = ko.astimezone(timezone.utc)
        mkey = ko_utc.strftime("%Y-%m")
        isoy = ko_utc.isocalendar()
        wkey = f"{isoy.year}-W{isoy.week:02d}"
        month_counts[mkey] = month_counts.get(mkey, 0) + 1
        week_counts[wkey] = week_counts.get(wkey, 0) + 1
        fr = FixtureRow(
            fixture_id=int(row["fixture_id"]),
            event_id=int(row["event_id"]),
            kickoff_utc=ko.isoformat(),
            n_lines_before_filter=len(before),
            n_lines_t60=len(t60),
            n_lines_lbu_null=n_lbu_n,
            value_pool=bool(vp),
            data_completeness_score=dcs,
            ft1x2_home_consensus=_f(ft.get("home")),
            ft1x2_draw=_f(ft.get("draw")),
            ft1x2_away=_f(ft.get("away")),
            market_coverage_keys=sorted(mkeys)[:20],
            kickoff_month=mkey,
            kickoff_week=wkey,
        )
        items.append(asdict(fr))
    n = len(items)
    dcs_dist: dict[str, int] = {}
    for v in dcs_values:
        k = str(int(v))
        dcs_dist[k] = dcs_dist.get(k, 0) + 1
    top_market_cov = [
        {"market": k, "fixtures_with_market_coverage": int(v)}
        for k, v in sorted(market_cov_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    return {
        "mode": MODE,
        "cutoff_mode": CUTOFF_MODE,
        "cutoff_instant": "line_ts <= kickoff_utc (bt2_events) - 1 hour; line_ts = latest_bookmaker_update or created_at",
        "live_parity": False,
        "exploratory_only": True,
        "temporal_truth": "raw_sportmonks line timestamps only; NOT bt2_odds_snapshot.fetched_at",
        "min_decimal": MIN_DEC,
        "markets_scope": "same 1X2+O/2.5 as normalize_fixtures (market_id 1, 80 total 2.5)",
        "window_utc": {"from": start.isoformat(), "to": end.isoformat(), "day_from": str(day_from), "day_to": str(day_to_inclusive)},
        "max_fixtures": max_fixtures,
        "summary": {
            "n_fixtures": n,
            "n_value_pool": n_vp,
            "n_not_usable": n_not_usable,
            "n_lines_total_before": n_lines_b,
            "n_lines_total_after_t60": n_lines_a,
            "tasa_sobrevivencia_lineas": round(n_lines_a / n_lines_b, 4) if n_lines_b else None,
            "lineas_before_por_fixture_p50": round(statistics.median([x["n_lines_before_filter"] for x in items]), 2) if items else None,
            "lineas_t60_por_fixture_p50": round(statistics.median([x["n_lines_t60"] for x in items]), 2) if items else None,
        },
        "distribution": {
            "by_month": [{"month": k, "n_fixtures": v} for k, v in sorted(month_counts.items())],
            "by_week": [{"week": k, "n_fixtures": v} for k, v in sorted(week_counts.items())],
            "data_completeness_score": [{"score": int(k), "n_fixtures": v} for k, v in sorted(dcs_dist.items(), key=lambda x: int(x[0]))],
            "market_coverage_top": top_market_cov,
        },
        "fixtures": items,
    }


def _f(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--day-from",
        default="2025-01-10",
        help="Fecha inicio (UTC) ventana de kickoff YYYY-MM-DD",
    )
    p.add_argument(
        "--day-to",
        default="2025-01-12",
        help="Fecha fin inclusive YYYY-MM-DD (misma ventana que from)",
    )
    p.add_argument(
        "--max-fixtures",
        type=int,
        default=20,
        help="Tope de fixtures a procesar en la ventana (default 20)",
    )
    p.add_argument(
        "-o",
        "--out",
        default="",
        help="Si se pasa, escribe JSON a esta ruta",
    )
    p.add_argument(
        "--summary-out",
        default="",
        help="Ruta de summary JSON compacto (sin fixtures[])",
    )
    p.add_argument(
        "--fixtures-csv",
        default="",
        help="Ruta CSV por fixture con columnas clave",
    )
    p.add_argument(
        "--fixtures-ndjson",
        default="",
        help="Ruta NDJSON por fixture (1 línea JSON por fixture)",
    )
    p.add_argument(
        "--summary-only",
        action="store_true",
        help="No imprimir ni guardar fixtures[] en el JSON principal",
    )
    args = p.parse_args()
    d0 = date.fromisoformat(str(args.day_from).strip())
    d1 = date.fromisoformat(str(args.day_to).strip())
    if d0 > d1:
        print("day-from > day-to", file=sys.stderr)
        sys.exit(1)
    out = run(day_from=d0, day_to_inclusive=d1, max_fixtures=int(args.max_fixtures))
    fixture_rows = out.get("fixtures") or []
    compact = {k: v for k, v in out.items() if k != "fixtures"}
    if args.fixtures_csv and fixture_rows:
        _write_fixtures_csv(Path(str(args.fixtures_csv)), fixture_rows)
    if args.fixtures_ndjson and fixture_rows:
        _write_fixtures_ndjson(Path(str(args.fixtures_ndjson)), fixture_rows)
    if args.summary_out:
        pth = Path(str(args.summary_out))
        pth.parent.mkdir(parents=True, exist_ok=True)
        pth.write_text(json.dumps(compact, indent=2, default=str), encoding="utf-8")
    payload = compact if args.summary_only else out
    s = json.dumps(payload, indent=2, default=str)
    if args.out:
        Path(str(args.out)).parent.mkdir(parents=True, exist_ok=True)
        Path(str(args.out)).write_text(s, encoding="utf-8")
    print(s)


def _write_fixtures_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "fixture_id",
        "event_id",
        "kickoff_utc",
        "kickoff_month",
        "kickoff_week",
        "n_lines_before_filter",
        "n_lines_t60",
        "n_lines_lbu_null",
        "value_pool",
        "data_completeness_score",
        "ft1x2_home_consensus",
        "ft1x2_draw",
        "ft1x2_away",
        "market_coverage_keys",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            rr = dict(r)
            rr["market_coverage_keys"] = "|".join(rr.get("market_coverage_keys") or [])
            w.writerow({k: rr.get(k) for k in fieldnames})


def _write_fixtures_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
report_effectiveness.py

Reporte de efectividad para picks persistidos/validados:
- Win rate y ROI unitario
- Desglose por fecha (run_date), mercado y franja (slot inferido)
- Desglose por confianza del modelo (odds_reference.confianza) y por mercado+confianza
- Salidas JSON + CSV para análisis semanal

Convenciones:
- settled = outcome in {'win','loss'}
- win_rate = wins / settled
- roi_unit = profit_unit / settled
- profit_unit:
    win  -> (picked_value - 1)
    loss -> -1
    pending/void -> 0 (fuera de settled)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo


def _parse_iso_utc(s: str) -> datetime:
    # created_at_utc viene en ISO; tolera "Z" si aparece.
    t = s.replace("Z", "+00:00")
    return datetime.fromisoformat(t)


def _slot_from_created_at(created_at_utc: str, tz_name: str) -> str:
    dt = _parse_iso_utc(created_at_utc).astimezone(ZoneInfo(tz_name))
    h = dt.hour
    # Heurística operativa del proyecto:
    # picks de la mañana ~ ejecuciones 08:00..15:59, tarde ~ 16:00..23:59.
    # Si cae en madrugada, lo clasificamos morning (suele venir de pruebas manuales).
    if h >= 16:
        return "exec_16h"
    return "exec_08h"


@dataclass
class Agg:
    issued: int = 0
    settled: int = 0
    wins: int = 0
    losses: int = 0
    pending: int = 0
    profit_unit: float = 0.0

    def add(self, outcome: Optional[str], picked_value: Optional[float]) -> None:
        self.issued += 1
        o = (outcome or "pending").lower()
        if o == "win":
            self.settled += 1
            self.wins += 1
            self.profit_unit += (picked_value or 0.0) - 1.0
        elif o == "loss":
            self.settled += 1
            self.losses += 1
            self.profit_unit += -1.0
        else:
            self.pending += 1

    def to_metrics(self) -> Dict[str, Any]:
        win_rate = (self.wins / self.settled) if self.settled else None
        roi_unit = (self.profit_unit / self.settled) if self.settled else None
        out = asdict(self)
        out["win_rate"] = win_rate
        out["roi_unit"] = roi_unit
        return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reporte de efectividad (JSON+CSV) por periodo.")
    p.add_argument("--db", default=None, help="Ruta SQLite (default DB_PATH o ./db/sport-tracker.sqlite3)")
    p.add_argument("--timezone", default=os.environ.get("COPA_FOXKIDS_TZ", "America/Bogota"))
    p.add_argument("--days", type=int, default=7, help="Ventana rolling en días (default 7)")
    p.add_argument("--end-date", default=None, help="YYYY-MM-DD local (default: hoy en timezone)")
    p.add_argument("--output-dir", default="out/reports")
    p.add_argument("--prefix", default="effectiveness")
    return p.parse_args()


def _db_path(arg_db: Optional[str]) -> str:
    if arg_db:
        return os.path.abspath(arg_db)
    env_db = os.environ.get("DB_PATH")
    if env_db:
        return os.path.abspath(env_db)
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(repo, "db", "sport-tracker.sqlite3")


def _date_range(end_date: str, days: int) -> tuple[str, str]:
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    start_dt = end_dt - timedelta(days=max(1, days) - 1)
    return start_dt.isoformat(), end_dt.isoformat()


def _confidence_bucket(odds_reference_raw: Any) -> str:
    """Etiqueta de confianza del modelo (odds_reference.confianza), o sin_confianza."""
    if odds_reference_raw is None:
        return "sin_confianza"
    ref: Any
    if isinstance(odds_reference_raw, dict):
        ref = odds_reference_raw
    elif isinstance(odds_reference_raw, str):
        try:
            ref = json.loads(odds_reference_raw)
        except json.JSONDecodeError:
            return "sin_confianza"
    else:
        return "sin_confianza"
    if not isinstance(ref, dict):
        return "sin_confianza"
    c = ref.get("confianza")
    if c is None:
        return "sin_confianza"
    s = str(c).strip()
    if not s:
        return "sin_confianza"
    sl = s.lower().replace(" ", "").replace("_", "-")
    if sl == "alta":
        return "Alta"
    if sl in ("media-alta", "mediaalta"):
        return "Media-Alta"
    if sl == "media":
        return "Media"
    if sl == "baja":
        return "Baja"
    return s


def _confidence_sort_key(bucket: str) -> tuple[int, str]:
    order = {
        "Alta": 0,
        "Media-Alta": 1,
        "Media": 2,
        "Baja": 3,
        "sin_confianza": 9,
    }
    return (order.get(bucket, 5), bucket)


def _fetch_rows(conn: sqlite3.Connection, start_date: str, end_date: str) -> Iterable[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT
            dr.run_date,
            p.market,
            p.picked_value,
            p.created_at_utc,
            p.odds_reference,
            pr.outcome
        FROM picks p
        JOIN daily_runs dr ON dr.daily_run_id = p.daily_run_id
        LEFT JOIN pick_results pr ON pr.pick_id = p.pick_id
        WHERE dr.run_date >= ? AND dr.run_date <= ?
        ORDER BY dr.run_date ASC, p.created_at_utc ASC
        """,
        (start_date, end_date),
    )
    return cur.fetchall()


def _agg_to_row(scope: str, key: str, agg: Agg) -> Dict[str, Any]:
    m = agg.to_metrics()
    return {
        "scope": scope,
        "key": key,
        "issued": m["issued"],
        "settled": m["settled"],
        "wins": m["wins"],
        "losses": m["losses"],
        "pending": m["pending"],
        "profit_unit": round(float(m["profit_unit"]), 4),
        "win_rate": None if m["win_rate"] is None else round(float(m["win_rate"]), 4),
        "roi_unit": None if m["roi_unit"] is None else round(float(m["roi_unit"]), 4),
    }


def main() -> None:
    args = parse_args()
    tz = ZoneInfo(args.timezone)
    end_date = args.end_date or datetime.now(tz).strftime("%Y-%m-%d")
    start_date, end_date = _date_range(end_date, args.days)
    db = _db_path(args.db)

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = list(_fetch_rows(conn, start_date, end_date))
    conn.close()

    total = Agg()
    by_day: Dict[str, Agg] = {}
    by_market: Dict[str, Agg] = {}
    by_slot: Dict[str, Agg] = {}
    by_day_market: Dict[str, Agg] = {}
    by_day_slot: Dict[str, Agg] = {}
    by_confidence: Dict[str, Agg] = {}
    by_market_confidence: Dict[str, Agg] = {}

    for r in rows:
        run_date = str(r["run_date"])
        market = str(r["market"])
        created = str(r["created_at_utc"])
        slot = _slot_from_created_at(created, args.timezone)
        outcome = r["outcome"]
        picked_value = float(r["picked_value"]) if r["picked_value"] is not None else None
        conf = _confidence_bucket(r["odds_reference"])

        total.add(outcome, picked_value)

        by_day.setdefault(run_date, Agg()).add(outcome, picked_value)
        by_market.setdefault(market, Agg()).add(outcome, picked_value)
        by_slot.setdefault(slot, Agg()).add(outcome, picked_value)
        by_day_market.setdefault(f"{run_date}|{market}", Agg()).add(outcome, picked_value)
        by_day_slot.setdefault(f"{run_date}|{slot}", Agg()).add(outcome, picked_value)
        by_confidence.setdefault(conf, Agg()).add(outcome, picked_value)
        by_market_confidence.setdefault(f"{market}|{conf}", Agg()).add(outcome, picked_value)

    by_conf_sorted = sorted(by_confidence.items(), key=lambda kv: _confidence_sort_key(kv[0]))
    by_mc_sorted = sorted(by_market_confidence.items())

    report: Dict[str, Any] = {
        "job": "report_effectiveness",
        "generated_at_utc": datetime.utcnow().isoformat() + "Z",
        "timezone": args.timezone,
        "range_start": start_date,
        "range_end": end_date,
        "days": args.days,
        "totals": _agg_to_row("totals", "all", total),
        "by_day": {k: _agg_to_row("day", k, v) for k, v in sorted(by_day.items())},
        "by_market": {k: _agg_to_row("market", k, v) for k, v in sorted(by_market.items())},
        "by_slot": {k: _agg_to_row("slot", k, v) for k, v in sorted(by_slot.items())},
        "by_day_market": {k: _agg_to_row("day_market", k, v) for k, v in sorted(by_day_market.items())},
        "by_day_slot": {k: _agg_to_row("day_slot", k, v) for k, v in sorted(by_day_slot.items())},
        "by_confidence": {
            k: _agg_to_row("confidence", k, v) for k, v in by_conf_sorted
        },
        "by_market_confidence": {
            k: _agg_to_row("market_confidence", k, v) for k, v in by_mc_sorted
        },
    }

    os.makedirs(args.output_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, f"{args.prefix}_{start_date}_to_{end_date}.json")
    csv_path = os.path.join(args.output_dir, f"{args.prefix}_{start_date}_to_{end_date}.csv")
    latest_json = os.path.join(args.output_dir, f"{args.prefix}_latest.json")
    latest_csv = os.path.join(args.output_dir, f"{args.prefix}_latest.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    rows_csv: List[Dict[str, Any]] = []
    rows_csv.append(report["totals"])
    rows_csv.extend(report["by_day"].values())
    rows_csv.extend(report["by_market"].values())
    rows_csv.extend(report["by_slot"].values())
    rows_csv.extend(report["by_day_market"].values())
    rows_csv.extend(report["by_day_slot"].values())
    rows_csv.extend(report["by_confidence"].values())
    rows_csv.extend(report["by_market_confidence"].values())

    fieldnames = ["scope", "key", "issued", "settled", "wins", "losses", "pending", "profit_unit", "win_rate", "roi_unit"]
    for out in (csv_path, latest_csv):
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows_csv)

    t = report["totals"]
    print("=== REPORT_EFFECTIVENESS ===")
    print(
        json.dumps(
            {
                "range": f"{start_date}..{end_date}",
                "issued": t["issued"],
                "settled": t["settled"],
                "wins": t["wins"],
                "losses": t["losses"],
                "pending": t["pending"],
                "win_rate": t["win_rate"],
                "roi_unit": t["roi_unit"],
                "json": json_path,
                "csv": csv_path,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("=== OK ===")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Fase 3C — otra malla read-only: un summary compacto por mes 2025 + consolidado.
Reutiliza run() de bt2_historical_sm_lbu_replay_prototype (mismo T-60, sin cambiar agregador).
"""

from __future__ import annotations

import calendar
import csv
import importlib.util
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

_proto_path = _repo / "scripts" / "bt2_historical_sm_lbu_replay_prototype.py"
_spec = importlib.util.spec_from_file_location("bt2_historical_sm_lbu_replay_prototype", _proto_path)
_proto = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["bt2_historical_sm_lbu_replay_prototype"] = _proto
_spec.loader.exec_module(_proto)
run = _proto.run

# Sin límite artificial por mes: tope defensivo alto
MAX_FX = 1_000_000

OUT_DIR = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_replay_2025" / "blocks_2025_monthly"
OUT_DIR_CONSOL = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_replay_2025"


@dataclass
class BlockRow:
    month: str
    day_from: str
    day_to: str
    elapsed_sec: float
    n_fixtures: int
    n_value_pool: int
    n_not_usable: int
    tasa_sobrevivencia_lineas: str
    p50_lineas_before: str
    p50_lineas_t60: str
    dcs_0: str
    dcs_12: str
    market_top_1: str
    market_top_1_n: str


def _month_window(y: int, m: int) -> tuple[date, date]:
    last = date(y, m, calendar.monthrange(y, m)[1])
    return date(y, m, 1), last


def _dcs_buck(compact: dict[str, Any], score: int) -> int:
    d = compact.get("distribution", {}).get("data_completeness_score", [])
    for e in d:
        if int(e.get("score", -1)) == score:
            return int(e.get("n_fixtures", 0))
    return 0


def main() -> None:
    year = 2025
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    blocks: list[dict[str, Any]] = []
    rows: list[BlockRow] = []

    t_all_0 = time.perf_counter()
    for m in range(1, 13):
        d0, d1 = _month_window(year, m)
        t0 = time.perf_counter()
        full = run(day_from=d0, day_to_inclusive=d1, max_fixtures=MAX_FX)
        elapsed = time.perf_counter() - t0
        key = f"{year}-{m:02d}"
        compact = {k: v for k, v in full.items() if k != "fixtures"}
        compact["elapsed_sec"] = round(elapsed, 3)
        p = OUT_DIR / f"summary_{key}.json"
        p.write_text(json.dumps(compact, indent=2, default=str), encoding="utf-8")

        s = full.get("summary", {})
        top = (full.get("distribution", {}) or {}).get("market_coverage_top", [])
        t1 = (top[0] if top else {}) or {}
        mkt = str(t1.get("market", ""))
        mkt_n = str(t1.get("fixtures_with_market_coverage", ""))
        rows.append(
            BlockRow(
                month=key,
                day_from=str(d0),
                day_to=str(d1),
                elapsed_sec=round(elapsed, 3),
                n_fixtures=int(s.get("n_fixtures", 0) or 0),
                n_value_pool=int(s.get("n_value_pool", 0) or 0),
                n_not_usable=int(s.get("n_not_usable", 0) or 0),
                tasa_sobrevivencia_lineas="" if s.get("tasa_sobrevivencia_lineas") is None else f"{s['tasa_sobrevivencia_lineas']:.4f}",
                p50_lineas_before="" if s.get("lineas_before_por_fixture_p50") is None else f"{s['lineas_before_por_fixture_p50']:.2f}",
                p50_lineas_t60="" if s.get("lineas_t60_por_fixture_p50") is None else f"{s['lineas_t60_por_fixture_p50']:.2f}",
                dcs_0=str(_dcs_buck(compact, 0)),
                dcs_12=str(_dcs_buck(compact, 12)),
                market_top_1=mkt,
                market_top_1_n=mkt_n,
            )
        )
        blocks.append(
            {
                "month": key,
                "elapsed_sec": round(elapsed, 3),
                "summary_path": str(p.relative_to(_repo)),
                "compact": compact,
            }
        )
    t_all = time.perf_counter() - t_all_0

    cons = {
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "historical_sm_lbu",
        "cutoff_mode": "T60",
        "year": year,
        "max_fixtures_per_block": MAX_FX,
        "total_elapsed_sec": round(t_all, 2),
        "blocks": [b["month"] for b in blocks],
        "rows": [asdict(r) for r in rows],
    }
    rows_nonzero = [x for x in rows if x.n_fixtures > 0]
    tasa = [float(x.tasa_sobrevivencia_lineas) for x in rows_nonzero if x.tasa_sobrevivencia_lineas]
    vp_rate = [x.n_value_pool / x.n_fixtures for x in rows_nonzero if x.n_fixtures > 0]
    cons["monthly_data_gaps"] = {
        "n_months_con_cero_fixtures": sum(1 for x in rows if x.n_fixtures == 0),
        "meses": [x.month for x in rows if x.n_fixtures == 0],
        "explicación": "0 fixtures implica: no hay (evento con kick en ventana) JOIN raw_sportmonks con odds en BT2. No es inestabilidad T-60; es hueco/ingesta en el CDM para ese mes en esta instancia de BD.",
    }
    if tasa and vp_rate and rows_nonzero:
        cons["stability_diagnostics_solo_meses_con_datos"] = {
            "n_meses": len(tasa),
            "tasa_sobrevivencia_lineas": {
                "min": round(min(tasa), 4),
                "max": round(max(tasa), 4),
                "mean": round(sum(tasa) / len(tasa), 4),
                "range": round(max(tasa) - min(tasa), 4),
            },
            "tasa_value_pool_sobre_n_fixtures": {
                "min": round(min(vp_rate), 4),
                "max": round(max(vp_rate), 4),
                "mean": round(sum(vp_rate) / len(vp_rate), 4),
            },
        }
    (OUT_DIR_CONSOL / "consolidated_2025_monthly.json").write_text(
        json.dumps(cons, indent=2, default=str), encoding="utf-8"
    )

    csvp = OUT_DIR_CONSOL / "consolidated_2025_monthly.csv"
    if rows:
        fn = list(asdict(rows[0]).keys())
        with csvp.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            for r in rows:
                w.writerow(asdict(r))
    else:
        csvp.write_text("month,error\n,empty\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "total_elapsed_sec": round(t_all, 2),
                "n_months": len(blocks),
                "OUT_DIR": str(OUT_DIR.relative_to(_repo)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

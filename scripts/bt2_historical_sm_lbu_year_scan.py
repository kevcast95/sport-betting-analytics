#!/usr/bin/env python3
"""
Fase 3C — barrido read-only 2023–2025: inventario mensual + métricas historical_sm_lbu (T-60).

1) SQL liviano por mes: join bt2_events + raw, odds JSON presente, muestra LBU en odds[0].
2) run() del prototipo (mismo agregador / T-60) por mes para métricas completas.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import importlib.util
import json
import sys
import time as time_mod
from dataclasses import asdict, dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2.extras

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from apps.api.bt2_settings import bt2_settings

_proto_path = _repo / "scripts" / "bt2_historical_sm_lbu_replay_prototype.py"
_spec = importlib.util.spec_from_file_location("bt2_historical_sm_lbu_replay_prototype", _proto_path)
_proto = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["bt2_historical_sm_lbu_replay_prototype"] = _proto
_spec.loader.exec_module(_proto)
run = _proto.run

MAX_FX = 1_000_000
YEARS = (2023, 2024, 2025)
OUT_ROOT = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_year_scan"
OUT_BLOCKS = OUT_ROOT / "blocks"


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def _month_window(y: int, m: int) -> tuple[date, date]:
    last = date(y, m, calendar.monthrange(y, m)[1])
    return date(y, m, 1), last


def _utc_bounds(d0: date, d1: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d0, dt_time.min, tzinfo=timezone.utc)
    end = datetime.combine(d1 + timedelta(days=1), dt_time.min, tzinfo=timezone.utc)
    return start, end


def sql_inventory(start: datetime, end: datetime) -> dict[str, int]:
    conn = psycopg2.connect(_dsn())
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT
          COUNT(*)::int AS n_join,
          COUNT(*) FILTER (
            WHERE jsonb_typeof(r.payload->'odds') = 'array'
              AND jsonb_array_length(COALESCE(r.payload->'odds', '[]'::jsonb)) > 2
          )::int AS n_odds_array_nonempty,
          COUNT(*) FILTER (
            WHERE (r.payload#>>'{odds,0,latest_bookmaker_update}') IS NOT NULL
          )::int AS n_sample_lbu0,
          COUNT(*) FILTER (
            WHERE (r.payload#>>'{odds,0,created_at}') IS NOT NULL
          )::int AS n_sample_created0
        FROM bt2_events e
        INNER JOIN raw_sportmonks_fixtures r ON r.fixture_id = e.sportmonks_fixture_id
        WHERE e.kickoff_utc IS NOT NULL
          AND e.kickoff_utc >= %s
          AND e.kickoff_utc < %s
        """,
        (start, end),
    )
    row = dict(cur.fetchone() or {})
    cur.close()
    conn.close()
    return {
        "sql_n_join": int(row.get("n_join") or 0),
        "sql_n_odds_array_nonempty": int(row.get("n_odds_array_nonempty") or 0),
        "sql_n_sample_lbu0": int(row.get("n_sample_lbu0") or 0),
        "sql_n_sample_created0": int(row.get("n_sample_created0") or 0),
    }


@dataclass
class ScanRow:
    ym: str
    year: int
    month: int
    day_from: str
    day_to: str
    elapsed_sql_sec: float
    elapsed_run_sec: float
    sql_n_join: int
    sql_n_odds_array_nonempty: int
    sql_n_sample_lbu0: int
    sql_n_sample_created0: int
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


def _dcs_buck(compact: dict[str, Any], score: int) -> int:
    d = compact.get("distribution", {}).get("data_completeness_score", [])
    for e in d:
        if int(e.get("score", -1)) == score:
            return int(e.get("n_fixtures", 0))
    return 0


def _scan_row_from_compact(
    *,
    ym: str,
    y: int,
    m: int,
    d0: date,
    d1: date,
    compact: dict[str, Any],
) -> ScanRow:
    inv = compact.get("sql_inventory") or {}
    s = compact.get("summary") or {}
    top = (compact.get("distribution") or {}).get("market_coverage_top", [])
    t1 = (top[0] if top else {}) or {}
    return ScanRow(
        ym=ym,
        year=y,
        month=m,
        day_from=str(d0),
        day_to=str(d1),
        elapsed_sql_sec=float(compact.get("elapsed_sql_sec") or 0),
        elapsed_run_sec=float(compact.get("elapsed_run_sec") or 0),
        sql_n_join=int(inv.get("sql_n_join") or 0),
        sql_n_odds_array_nonempty=int(inv.get("sql_n_odds_array_nonempty") or 0),
        sql_n_sample_lbu0=int(inv.get("sql_n_sample_lbu0") or 0),
        sql_n_sample_created0=int(inv.get("sql_n_sample_created0") or 0),
        n_fixtures=int(s.get("n_fixtures", 0) or 0),
        n_value_pool=int(s.get("n_value_pool", 0) or 0),
        n_not_usable=int(s.get("n_not_usable", 0) or 0),
        tasa_sobrevivencia_lineas=""
        if s.get("tasa_sobrevivencia_lineas") is None
        else f"{float(s['tasa_sobrevivencia_lineas']):.4f}",
        p50_lineas_before=""
        if s.get("lineas_before_por_fixture_p50") is None
        else f"{float(s['lineas_before_por_fixture_p50']):.2f}",
        p50_lineas_t60=""
        if s.get("lineas_t60_por_fixture_p50") is None
        else f"{float(s['lineas_t60_por_fixture_p50']):.2f}",
        dcs_0=str(_dcs_buck(compact, 0)),
        dcs_12=str(_dcs_buck(compact, 12)),
        market_top_1=str(t1.get("market", "")),
        market_top_1_n=str(t1.get("fixtures_with_market_coverage", "")),
    )


def _year_verdict(agg: dict[str, Any]) -> dict[str, Any]:
    """Clasificación operativa por cobertura + estabilidad (sin tocar T-60)."""
    tot_f = int(agg.get("total_n_fixtures") or 0)
    n_m = int(agg.get("n_months_con_fixtures") or 0)
    n_gap = int(agg.get("n_months_hueco") or 0)
    ts = agg.get("tasa_sobrevivencia_lineas_meses_con_datos") or {}
    tr = float(ts.get("range") or 0) if ts else 0.0
    tvp = agg.get("tasa_value_pool_sobre_fixtures")
    rationale: list[str] = []
    if tot_f == 0:
        return {
            "clase": "no utilizable en esta instancia",
            "rationale": ["Sin fixtures con join en ningún mes del año."],
        }
    if n_m <= 2:
        return {
            "clase": "no utilizable en esta instancia",
            "rationale": [f"Solo {n_m} mes(es) con datos; universo demasiado fragmentado."],
        }
    caveats: list[str] = []
    if n_gap >= 6:
        caveats.append(f"{n_gap}/12 meses sin fixtures (huecos de cobertura/join).")
    if n_gap >= 1 and n_m >= 1:
        caveats.append("Comparación año-a-año: meses en cero no son comparables con meses con datos.")
    if tr > 0.12:
        caveats.append(
            f"Rango amplio de tasa_sobrevivencia_lineas entre meses con datos (range={tr:.4f})."
        )
    if caveats:
        rationale = caveats
        clase = "utilizable con caveats"
    else:
        clase = "utilizable ya"
        rationale = [
            f"Cobertura mensual razonable ({n_m}/12 con fixtures).",
            "Sin señales fuertes de inestabilidad intermensual en supervivencia de líneas.",
        ]
    out = {"clase": clase, "rationale": rationale}
    if tvp is not None:
        out["tasa_value_pool_sobre_fixtures_anual"] = tvp
    return out


def _recomendacion_expansion(per_year: dict[str, Any], verdicts: dict[str, Any]) -> dict[str, Any]:
    usable = [y for y, v in verdicts.items() if v.get("clase") == "utilizable ya"]
    cave = [y for y, v in verdicts.items() if v.get("clase") == "utilizable con caveats"]
    bad = [y for y, v in verdicts.items() if v.get("clase") == "no utilizable en esta instancia"]
    lines: list[str] = []
    if usable:
        lines.append(
            f"Extender `historical_sm_lbu` con prioridad a: {', '.join(usable)} (cobertura estable)."
        )
    if cave:
        lines.append(
            f"Años con caveats ({', '.join(cave)}): útiles para exploración acotada a meses con fixtures; "
            "resolver huecos de BD/CDM antes de asumir parity histórica."
        )
    if bad:
        lines.append(f"No extender a {', '.join(bad)} hasta recuperar join/raw en esos periodos.")
    by_cov: list[str] = []
    # Heurística explícita cuando ningún año alcanza "utilizable ya"
    if not usable and cave:
        by_cov = sorted(
            cave,
            key=lambda yy: (
                -int(per_year[yy].get("n_months_con_fixtures") or 0),
                -int(per_year[yy].get("total_n_fixtures") or 0),
            ),
        )
        lines.append(
            "Por cobertura de calendario (meses con join), orden de conveniencia tentativo: "
            + " > ".join(by_cov)
            + ". No implica comparabilidad de régimen entre años."
        )
    next_step = (
        "Siguiente paso: backfill o refresh de `raw_sportmonks_fixtures` + `bt2_events` "
        "para meses en cero (sobre todo 2025-06+ si el negocio los necesita); "
        "re-ejecutar este scan con `--resume` tras el backfill."
    )
    return {
        "extender_prioridad": usable,
        "caveats": cave,
        "no_extender": bad,
        "orden_tentativo_por_cobertura_calendario": by_cov,
        "texto": lines,
        "siguiente_paso": next_step,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--resume",
        action="store_true",
        help="Si existe blocks/summary_YYYY-MM.json, reutilizarlo (no reconsulta BD para ese mes).",
    )
    ap.add_argument(
        "--consolidate-only",
        action="store_true",
        help="Solo leer summaries existentes y escribir consolidados/README (sin BD).",
    )
    args = ap.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_BLOCKS.mkdir(parents=True, exist_ok=True)
    rows: list[ScanRow] = []
    t0_all = time_mod.perf_counter()
    for y in YEARS:
        for m in range(1, 13):
            d0, d1 = _month_window(y, m)
            ym = f"{y}-{m:02d}"
            block_path = OUT_BLOCKS / f"summary_{ym}.json"
            if args.consolidate_only:
                if not block_path.is_file():
                    print(f"missing {block_path.name}", file=sys.stderr)
                    sys.exit(2)
                compact = json.loads(block_path.read_text(encoding="utf-8"))
                rows.append(
                    _scan_row_from_compact(
                        ym=ym, y=y, m=m, d0=d0, d1=d1, compact=compact
                    )
                )
                continue
            if args.resume and block_path.is_file():
                compact = json.loads(block_path.read_text(encoding="utf-8"))
                rows.append(
                    _scan_row_from_compact(
                        ym=ym, y=y, m=m, d0=d0, d1=d1, compact=compact
                    )
                )
                continue
            start, end = _utc_bounds(d0, d1)
            t_sql = time_mod.perf_counter()
            inv = sql_inventory(start, end)
            elapsed_sql = time_mod.perf_counter() - t_sql
            t_run = time_mod.perf_counter()
            full = run(day_from=d0, day_to_inclusive=d1, max_fixtures=MAX_FX)
            elapsed_run = time_mod.perf_counter() - t_run
            compact = {k: v for k, v in full.items() if k != "fixtures"}
            compact["elapsed_sql_sec"] = round(elapsed_sql, 4)
            compact["elapsed_run_sec"] = round(elapsed_run, 3)
            compact["sql_inventory"] = inv
            block_path.write_text(
                json.dumps(compact, indent=2, default=str), encoding="utf-8"
            )
            rows.append(_scan_row_from_compact(ym=ym, y=y, m=m, d0=d0, d1=d1, compact=compact))

    def _agg_year(y: int) -> dict[str, Any]:
        ys = [r for r in rows if r.year == y]
        nz = [r for r in ys if r.n_fixtures > 0]
        tot_f = sum(r.n_fixtures for r in ys)
        tot_vp = sum(r.n_value_pool for r in ys)
        gap_months = [r.ym for r in ys if r.n_fixtures == 0]
        tasas = [float(r.tasa_sobrevivencia_lineas) for r in nz if r.tasa_sobrevivencia_lineas]
        vp_rates = [r.n_value_pool / r.n_fixtures for r in nz if r.n_fixtures > 0]
        out: dict[str, Any] = {
            "year": y,
            "n_months": 12,
            "n_months_con_fixtures": len(nz),
            "n_months_hueco": len(gap_months),
            "total_n_fixtures": tot_f,
            "total_n_value_pool": tot_vp,
            "tasa_value_pool_sobre_fixtures": round(tot_vp / tot_f, 4) if tot_f else None,
            "meses_hueco": gap_months,
        }
        if tasas:
            out["tasa_sobrevivencia_lineas_meses_con_datos"] = {
                "min": round(min(tasas), 4),
                "max": round(max(tasas), 4),
                "mean": round(sum(tasas) / len(tasas), 4),
                "range": round(max(tasas) - min(tasas), 4),
            }
        if vp_rates:
            out["tasa_vp_sobre_n_meses_con_datos"] = {
                "min": round(min(vp_rates), 4),
                "max": round(max(vp_rates), 4),
                "mean": round(sum(vp_rates) / len(vp_rates), 4),
            }
        return out

    per_year = {str(y): _agg_year(y) for y in YEARS}
    total_elapsed = time_mod.perf_counter() - t0_all
    verdicts = {str(y): _year_verdict(per_year[str(y)]) for y in YEARS}

    cons: dict[str, Any] = {
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "historical_sm_lbu",
        "cutoff_mode": "T60",
        "live_parity": False,
        "exploratory_only": True,
        "years": list(YEARS),
        "total_elapsed_sec": round(total_elapsed, 2),
        "per_year": per_year,
        "verdict_por_ano": verdicts,
        "recomendacion_expansion": _recomendacion_expansion(per_year, verdicts),
        "rows": [asdict(r) for r in rows],
    }
    (OUT_ROOT / "year_scan_consolidated.json").write_text(
        json.dumps(cons, indent=2, default=str), encoding="utf-8"
    )
    csvp = OUT_ROOT / "year_scan_consolidated.csv"
    fn = list(asdict(rows[0]).keys()) if rows else []
    with csvp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for r in rows:
            w.writerow(asdict(r))

    readme = OUT_ROOT / "README.md"
    readme.write_text(
        """# BT2 — barrido `historical_sm_lbu` (2023–2025)

Read-only. Mismo contrato **T-60** que `bt2_historical_sm_lbu_replay_prototype.py`.

## Regenerar

Barrido completo (36 meses):

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_historical_sm_lbu_year_scan.py
```

Reanudar tras corte (reusa `blocks/summary_*.json` existentes):

```bash
python3 scripts/bt2_historical_sm_lbu_year_scan.py --resume
```

Solo reescribir consolidado desde bloques ya guardados (sin BD):

```bash
python3 scripts/bt2_historical_sm_lbu_year_scan.py --consolidate-only
```

## Salidas

- `blocks/summary_YYYY-MM.json` — resumen por mes (+ inventario SQL liviano).
- `year_scan_consolidated.json` / `year_scan_consolidated.csv` — 36 filas (12×3 años) + agregados por año + `verdict_por_ano`.

**Nota:** `sql_n_join` y `n_fixtures` de `run()` deben coincidir; si no, revisar join o ventana.
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "total_elapsed_sec": round(total_elapsed, 2),
                "out": str(OUT_ROOT.relative_to(_repo)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

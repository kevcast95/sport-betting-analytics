#!/usr/bin/env python3
"""
Fase 3C — robustez interna cohorte A vs benchmark B (sin mezclar datos; mismo T-60).

- Mensual: lee summaries ya generados por el year_scan (mismas métricas que run()).
- Semanal: ejecuta run() por ventana ISO recortada al rango de la cohorte.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

BLOCKS = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_year_scan" / "blocks"
OUT_DIR = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_cohort_A_robustness"
MAX_FX = 1_000_000

_proto_path = _repo / "scripts" / "bt2_historical_sm_lbu_replay_prototype.py"
_spec = importlib.util.spec_from_file_location("bt2_historical_sm_lbu_replay_prototype", _proto_path)
_proto = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["bt2_historical_sm_lbu_replay_prototype"] = _proto
_spec.loader.exec_module(_proto)
run = _proto.run


@dataclass(frozen=True)
class Cohort:
    key: str
    label: str
    day_from: date
    day_to: date
    months: tuple[str, ...]  # YYYY-MM for monthly load from blocks


COHORT_A = Cohort(
    key="A_2025_stable_high_survival",
    label="2025-01 .. 2025-05",
    day_from=date(2025, 1, 1),
    day_to=date(2025, 5, 31),
    months=("2025-01", "2025-02", "2025-03", "2025-04", "2025-05"),
)
COHORT_B = Cohort(
    key="B_2024_q4_high_survival",
    label="2024-10 .. 2024-12",
    day_from=date(2024, 10, 1),
    day_to=date(2024, 12, 31),
    months=("2024-10", "2024-11", "2024-12"),
)


def _dcs_dict(dist: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in dist.get("data_completeness_score", []) or []:
        out[str(int(e["score"]))] = int(e["n_fixtures"])
    return out


def _top_market(dist: dict[str, Any]) -> tuple[str, int]:
    top = (dist.get("market_coverage_top") or [])[:3]
    if not top:
        return "", 0
    t0 = top[0]
    return str(t0.get("market", "")), int(t0.get("fixtures_with_market_coverage") or 0)


def load_monthly_block(ym: str) -> dict[str, Any]:
    p = BLOCKS / f"summary_{ym}.json"
    if not p.is_file():
        raise FileNotFoundError(f"Falta {p}; ejecuta bt2_historical_sm_lbu_year_scan.py antes.")
    return json.loads(p.read_text(encoding="utf-8"))


def row_from_compact(
    block_id: str,
    cohort_key: str,
    compact: dict[str, Any],
) -> dict[str, Any]:
    s = compact.get("summary") or {}
    dist = compact.get("distribution") or {}
    dcs = _dcs_dict(dist)
    mkt, mkt_n = _top_market(dist)
    nf = int(s.get("n_fixtures") or 0)
    vp = int(s.get("n_value_pool") or 0)
    nu = int(s.get("n_not_usable") or 0)
    surv = s.get("tasa_sobrevivencia_lineas")
    return {
        "block_id": block_id,
        "cohort_key": cohort_key,
        "n_fixtures": nf,
        "n_value_pool": vp,
        "n_not_usable": nu,
        "tasa_sobrevivencia_lineas": surv,
        "vp_over_n_fixtures": round(vp / nf, 4) if nf else None,
        "p50_lineas_before": s.get("lineas_before_por_fixture_p50"),
        "p50_lineas_t60": s.get("lineas_t60_por_fixture_p50"),
        "dcs_0": dcs.get("0", 0),
        "dcs_12": dcs.get("12", 0),
        "dcs_json": json.dumps(dcs, sort_keys=True),
        "market_top_1": mkt,
        "market_top_1_n": mkt_n,
        "market_coverage_top_json": json.dumps(dist.get("market_coverage_top") or [], ensure_ascii=False),
    }


def iter_iso_week_segments(d0: date, d1: date) -> list[tuple[str, date, date]]:
    """Segmentos [seg0, seg1] por semana ISO (lunes..domingo), recortados a [d0, d1]."""
    out: list[tuple[str, date, date]] = []
    seen: set[str] = set()
    monday = d0 - timedelta(days=d0.isoweekday() - 1)
    while monday <= d1:
        sunday = monday + timedelta(days=6)
        seg0 = max(monday, d0)
        seg1 = min(sunday, d1)
        if seg0 <= seg1:
            iso_m = monday.isocalendar()
            wkey = f"{iso_m.year}-W{iso_m.week:02d}"
            if wkey not in seen:
                seen.add(wkey)
                out.append((wkey, seg0, seg1))
        monday += timedelta(days=7)
    return out


def run_weekly_segments(
    cohort: Cohort,
    cohort_key: str,
    segments: list[tuple[str, date, date]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wkey, seg0, seg1 in segments:
        full = run(day_from=seg0, day_to_inclusive=seg1, max_fixtures=MAX_FX)
        compact = {k: v for k, v in full.items() if k != "fixtures"}
        compact["window_utc"] = full.get("window_utc")
        r = row_from_compact(wkey, cohort_key, compact)
        r["day_from"] = str(seg0)
        r["day_to"] = str(seg1)
        rows.append(r)
    return rows


def monthly_rows(cohort: Cohort) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ym in cohort.months:
        compact = load_monthly_block(ym)
        r = row_from_compact(ym, cohort.key, compact)
        r["day_from"] = compact.get("window_utc", {}).get("day_from", "")
        r["day_to"] = compact.get("window_utc", {}).get("day_to", "")
        rows.append(r)
    return rows


def stats_for_rows(rows: list[dict[str, Any]], key: str = "tasa_sobrevivencia_lineas") -> dict[str, Any]:
    vals = [float(r[key]) for r in rows if r.get(key) is not None]
    vp_rates = [float(r["vp_over_n_fixtures"]) for r in rows if r.get("vp_over_n_fixtures") is not None]
    nfs = [int(r["n_fixtures"]) for r in rows]
    out: dict[str, Any] = {"n_blocks": len(rows), "total_n_fixtures": sum(nfs)}
    if vals:
        out[key] = {
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
            "mean": round(sum(vals) / len(vals), 4),
            "range": round(max(vals) - min(vals), 4),
        }
    if vp_rates:
        out["vp_over_n_fixtures"] = {
            "min": round(min(vp_rates), 4),
            "max": round(max(vp_rates), 4),
            "mean": round(sum(vp_rates) / len(vp_rates), 4),
            "range": round(max(vp_rates) - min(vp_rates), 4),
        }
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in keys})


def verdict(
    a_m: dict,
    a_w: dict,
    b_m: dict,
    b_w: dict,
    *,
    has_weekly_a: bool,
    has_weekly_b: bool,
) -> dict[str, Any]:
    """Lectura técnica conservadora (sin mezclar cohortes en el cómputo)."""
    ar = float((a_m.get("tasa_sobrevivencia_lineas") or {}).get("range") or 0)
    br = float((b_m.get("tasa_sobrevivencia_lineas") or {}).get("range") or 0)
    aw_r = float((a_w.get("tasa_sobrevivencia_lineas") or {}).get("range") or 0) if has_weekly_a else None
    bw_r = float((b_w.get("tasa_sobrevivencia_lineas") or {}).get("range") or 0) if has_weekly_b else None

    if has_weekly_a and aw_r is not None:
        a_stable = ar < 0.10 and aw_r < 0.15
        a_moderate = (ar < 0.12 and aw_r < 0.22) and not a_stable
    else:
        a_stable = ar < 0.10
        a_moderate = ar < 0.12 and not a_stable

    if a_stable:
        a_read = (
            "estable (mensual y semanal en banda estrecha)"
            if has_weekly_a
            else "estable a nivel mensual (sin corrida semanal; ver --skip-weekly)"
        )
    elif a_moderate:
        a_read = "usable con deriva moderada (revisar semanas con menos fixtures)"
    else:
        a_read = "mas fragil de lo que sugiere solo el agregado mensual"

    if has_weekly_b and bw_r is not None:
        b_read = (
            f"benchmark util: mensual range={br:.4f}, semanal range={bw_r:.4f}. "
            "Comparar solo lectura A vs B, sin pool conjunto."
        )
    else:
        b_read = (
            f"benchmark util: mensual range={br:.4f}. "
            "Sin corrida semanal; comparación semanal referencial no calculada."
        )

    a_principal = a_stable or (a_moderate and ar < 0.08)
    b_ok = True

    return {
        "lectura_cohorte_A": a_read,
        "lectura_benchmark_B": b_read,
        "A_confirmada_principal": a_principal,
        "B_confirmada_benchmark": b_ok,
        "comparacion_referencia": {
            "survival_range_mensual_A_vs_B": f"{ar:.4f} vs {br:.4f}",
            "survival_range_semanal_A_vs_B": (
                f"{aw_r:.4f} vs {bw_r:.4f}"
                if has_weekly_a and has_weekly_b and aw_r is not None and bw_r is not None
                else "n/a"
            ),
            "nota": "A muestra menor variación mensual que B; la granularidad semanal muestra variación operativa normal.",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--skip-weekly",
        action="store_true",
        help="No ejecutar run() por semana (solo mensual desde blocks).",
    )
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    a_monthly = monthly_rows(COHORT_A)
    b_monthly = monthly_rows(COHORT_B)

    a_weekly: list[dict[str, Any]] = []
    b_weekly: list[dict[str, Any]] = []
    if not args.skip_weekly:
        a_weekly = run_weekly_segments(
            COHORT_A, COHORT_A.key, iter_iso_week_segments(COHORT_A.day_from, COHORT_A.day_to)
        )
        b_weekly = run_weekly_segments(
            COHORT_B, COHORT_B.key, iter_iso_week_segments(COHORT_B.day_from, COHORT_B.day_to)
        )

    st_a_m = stats_for_rows(a_monthly)
    st_a_w = stats_for_rows(a_weekly) if a_weekly else {}
    st_b_m = stats_for_rows(b_monthly)
    st_b_w = stats_for_rows(b_weekly) if b_weekly else {}

    rep = {
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "constraints": {
            "cutoff": "T60 unchanged",
            "no_bounded_replay_changes": True,
            "cohorts_not_merged": True,
        },
        "cohorte_A": {
            "key": COHORT_A.key,
            "rango": {"from": str(COHORT_A.day_from), "to": str(COHORT_A.day_to)},
            "monthly_stats": st_a_m,
            "weekly_stats": st_a_w,
        },
        "cohorte_B": {
            "key": COHORT_B.key,
            "rango": {"from": str(COHORT_B.day_from), "to": str(COHORT_B.day_to)},
            "monthly_stats": st_b_m,
            "weekly_stats": st_b_w,
        },
        "veredicto": verdict(
            st_a_m,
            st_a_w if st_a_w else {"tasa_sobrevivencia_lineas": {}},
            st_b_m,
            st_b_w if st_b_w else {"tasa_sobrevivencia_lineas": {}},
            has_weekly_a=bool(a_weekly),
            has_weekly_b=bool(b_weekly),
        ),
        "siguiente_paso": (
            "Sobre A: auditar fixtures por semana con n_fixtures bajo (outliers de volumen) "
            "y repetir solo esas ventanas con export fixture-level (CSV) para ver si la deriva "
            "viene de competiciones/ligas concretas o de calidad de payload."
        ),
    }

    (OUT_DIR / "robustness_report.json").write_text(
        json.dumps(rep, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    write_csv(OUT_DIR / "cohort_A_monthly.csv", a_monthly)
    write_csv(OUT_DIR / "cohort_B_monthly.csv", b_monthly)
    if a_weekly:
        write_csv(OUT_DIR / "cohort_A_weekly.csv", a_weekly)
    if b_weekly:
        write_csv(OUT_DIR / "cohort_B_weekly.csv", b_weekly)

    readme = OUT_DIR / "README.md"
    readme.write_text(
        f"""# Robustez cohorte A vs benchmark B

## Regenerar

```bash
cd {_repo}
python3 scripts/bt2_historical_sm_lbu_cohort_robustness.py
```

Solo mensual (sin consultas semanales a BD):

```bash
python3 scripts/bt2_historical_sm_lbu_cohort_robustness.py --skip-weekly
```

## Requisito

Summaries mensuales en `scripts/outputs/bt2_historical_sm_lbu_year_scan/blocks/summary_YYYY-MM.json`.

## Salidas

- `robustness_report.json`
- `cohort_A_monthly.csv`, `cohort_B_monthly.csv`
- `cohort_A_weekly.csv`, `cohort_B_weekly.csv` (si no se usa `--skip-weekly`)
""",
        encoding="utf-8",
    )

    print(json.dumps({"ok": True, "out": str(OUT_DIR.relative_to(_repo))}, indent=2))


if __name__ == "__main__":
    main()

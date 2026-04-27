#!/usr/bin/env python3
"""
Fase 3C: particion metodologica de cohortes historical_sm_lbu (2023-2025).

No modifica T-60 ni bounded replay. Solo consume el consolidado mensual ya generado.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "scripts" / "outputs" / "bt2_historical_sm_lbu_year_scan" / "year_scan_consolidated.json"
OUT_DIR = REPO / "scripts" / "outputs" / "bt2_historical_sm_lbu_cohorts"
OUT_JSON = OUT_DIR / "cohort_plan.json"
OUT_CSV = OUT_DIR / "cohort_summary.csv"
OUT_README = OUT_DIR / "README.md"


@dataclass(frozen=True)
class CohortDef:
    key: str
    label: str
    ym_from: str
    ym_to: str
    objetivo: str


COHORTS = [
    CohortDef(
        key="A_2025_stable_high_survival",
        label="A — 2025 Ene-May (estable alta supervivencia)",
        ym_from="2025-01",
        ym_to="2025-05",
        objetivo="cohorte_principal",
    ),
    CohortDef(
        key="B_2024_q4_high_survival",
        label="B — 2024 Oct-Dic (post-cambio regimen, alta supervivencia)",
        ym_from="2024-10",
        ym_to="2024-12",
        objetivo="secundaria_contraste_metodologico",
    ),
    CohortDef(
        key="C_2024_q1_q3_low_mid_survival",
        label="C — 2024 Ene-Sep (pre-cambio regimen, baja-media supervivencia)",
        ym_from="2024-01",
        ym_to="2024-09",
        objetivo="secundaria_contraste_regimen",
    ),
    CohortDef(
        key="D_2023_aug_dec_low_survival_partial",
        label="D — 2023 Ago-Dic (parcial, banda baja supervivencia)",
        ym_from="2023-08",
        ym_to="2023-12",
        objetivo="referencia_secundaria",
    ),
]


def ym_in_range(ym: str, ym_from: str, ym_to: str) -> bool:
    return ym_from <= ym <= ym_to


def to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows_sorted = sorted(rows, key=lambda r: r["ym"])
    n_months = len(rows_sorted)
    n_months_with_data = sum(1 for r in rows_sorted if int(r.get("n_fixtures") or 0) > 0)
    n_months_gap = n_months - n_months_with_data

    n_fixtures = sum(int(r.get("n_fixtures") or 0) for r in rows_sorted)
    n_value_pool = sum(int(r.get("n_value_pool") or 0) for r in rows_sorted)
    n_not_usable = sum(int(r.get("n_not_usable") or 0) for r in rows_sorted)
    n_dcs12 = sum(int(r.get("dcs_12") or 0) for r in rows_sorted)
    n_market_top_1 = sum(int(r.get("market_top_1_n") or 0) for r in rows_sorted)
    n_odds_usable_raw = sum(int(r.get("sql_n_odds_array_nonempty") or 0) for r in rows_sorted)
    n_join = sum(int(r.get("sql_n_join") or 0) for r in rows_sorted)

    surv = [to_float(r.get("tasa_sobrevivencia_lineas")) for r in rows_sorted]
    surv = [x for x in surv if x is not None]

    gaps = [r["ym"] for r in rows_sorted if int(r.get("n_fixtures") or 0) == 0]

    return {
        "meses": [r["ym"] for r in rows_sorted],
        "n_months": n_months,
        "n_months_with_data": n_months_with_data,
        "n_months_gap": n_months_gap,
        "gap_ratio": round(n_months_gap / n_months, 4) if n_months else None,
        "n_fixtures": n_fixtures,
        "n_value_pool": n_value_pool,
        "n_not_usable": n_not_usable,
        "vp_over_fixtures": round(n_value_pool / n_fixtures, 4) if n_fixtures else None,
        "dcs12_over_fixtures": round(n_dcs12 / n_fixtures, 4) if n_fixtures else None,
        "market_top1_over_fixtures": round(n_market_top_1 / n_fixtures, 4) if n_fixtures else None,
        "odds_usable_raw_over_join": round(n_odds_usable_raw / n_join, 4) if n_join else None,
        "survival_mean": round(sum(surv) / len(surv), 4) if surv else None,
        "survival_min": round(min(surv), 4) if surv else None,
        "survival_max": round(max(surv), 4) if surv else None,
        "survival_range": round(max(surv) - min(surv), 4) if len(surv) >= 2 else 0.0,
        "meses_gap": gaps,
        "continuidad_temporal": "continua" if n_months_gap == 0 else "fragmentada",
    }


def main() -> None:
    src = json.loads(SRC.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = src.get("rows") or []
    if not rows:
        raise RuntimeError("No hay rows en year_scan_consolidated.json")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cohorts_out: list[dict[str, Any]] = []
    for c in COHORTS:
        c_rows = [r for r in rows if ym_in_range(str(r["ym"]), c.ym_from, c.ym_to)]
        metrics = agg(c_rows)

        if c.key.startswith("A_"):
            uso = "exploracion_historica_seria"
            calidad = "alta"
            caveats = ["Cobertura parcial anual (solo ene-may 2025)."]
        elif c.key.startswith("B_"):
            uso = "contraste_metodologico"
            calidad = "media_alta"
            caveats = ["Ventana corta (3 meses).", "No extrapolar automaticamente a 2024 completo."]
        elif c.key.startswith("C_"):
            uso = "contraste_metodologico"
            calidad = "media"
            caveats = [
                "Banda de supervivencia significativamente menor que A/B.",
                "No mezclar con 2024 Q4 ni con 2025 ene-may para inferencia unica.",
            ]
        else:
            uso = "solo_referencia_secundaria"
            calidad = "media_baja"
            caveats = [
                "Año parcial (ago-dic) y con huecos fuertes en 2023 ene-jul.",
                "Régimen distinto de supervivencia frente a 2025 ene-may.",
            ]

        cohorts_out.append(
            {
                "cohort_key": c.key,
                "cohort_label": c.label,
                "rango": {"from": c.ym_from, "to": c.ym_to},
                "objetivo": c.objetivo,
                "metrics": metrics,
                "calidad_esperada": calidad,
                "uso_recomendado": uso,
                "caveats": caveats,
            }
        )

    no_usable = [
        {
            "cohort_key": "X_2023_jan_jul_gap",
            "rango": {"from": "2023-01", "to": "2023-07"},
            "uso_recomendado": "no_usar_por_ahora",
            "motivo": "0 fixtures en todos los meses (hueco de datos/join).",
        },
        {
            "cohort_key": "Y_2025_jun_dec_gap",
            "rango": {"from": "2025-06", "to": "2025-12"},
            "uso_recomendado": "no_usar_por_ahora",
            "motivo": "0 fixtures en todos los meses (hueco de datos/join).",
        },
    ]

    no_mix = [
        {
            "pair": ["A_2025_stable_high_survival", "C_2024_q1_q3_low_mid_survival"],
            "motivo": "Banda de supervivencia y mediana de lineas T-60 en regimen distinto.",
        },
        {
            "pair": ["B_2024_q4_high_survival", "C_2024_q1_q3_low_mid_survival"],
            "motivo": "Cambio de regimen intranual 2024 (salto fuerte desde oct-2024).",
        },
        {
            "pair": ["A_2025_stable_high_survival", "D_2023_aug_dec_low_survival_partial"],
            "motivo": "Diferencias de cobertura/supervivencia y continuidad temporal.",
        },
    ]

    plan = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": str(SRC.relative_to(REPO)),
        "constraints": {
            "mode": "historical_sm_lbu",
            "cutoff_mode": "T60",
            "no_bounded_replay_changes": True,
            "no_phase4": True,
        },
        "cohortes_propuestas": cohorts_out,
        "cohortes_no_usar_por_ahora": no_usable,
        "cohortes_no_mezclar": no_mix,
        "cohorte_principal_recomendada": {
            "cohort_key": "A_2025_stable_high_survival",
            "motivo": "Mayor estabilidad interna y mejor VP/fixtures en meses con datos.",
            "scope_real": "2025-01..2025-05",
        },
    }

    OUT_JSON.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

    fieldnames = [
        "cohort_key",
        "cohort_label",
        "from",
        "to",
        "n_months",
        "n_months_with_data",
        "n_months_gap",
        "n_fixtures",
        "n_value_pool",
        "n_not_usable",
        "vp_over_fixtures",
        "survival_mean",
        "survival_min",
        "survival_max",
        "survival_range",
        "dcs12_over_fixtures",
        "market_top1_over_fixtures",
        "odds_usable_raw_over_join",
        "continuidad_temporal",
        "calidad_esperada",
        "uso_recomendado",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for c in cohorts_out:
            m = c["metrics"]
            w.writerow(
                {
                    "cohort_key": c["cohort_key"],
                    "cohort_label": c["cohort_label"],
                    "from": c["rango"]["from"],
                    "to": c["rango"]["to"],
                    "n_months": m["n_months"],
                    "n_months_with_data": m["n_months_with_data"],
                    "n_months_gap": m["n_months_gap"],
                    "n_fixtures": m["n_fixtures"],
                    "n_value_pool": m["n_value_pool"],
                    "n_not_usable": m["n_not_usable"],
                    "vp_over_fixtures": m["vp_over_fixtures"],
                    "survival_mean": m["survival_mean"],
                    "survival_min": m["survival_min"],
                    "survival_max": m["survival_max"],
                    "survival_range": m["survival_range"],
                    "dcs12_over_fixtures": m["dcs12_over_fixtures"],
                    "market_top1_over_fixtures": m["market_top1_over_fixtures"],
                    "odds_usable_raw_over_join": m["odds_usable_raw_over_join"],
                    "continuidad_temporal": m["continuidad_temporal"],
                    "calidad_esperada": c["calidad_esperada"],
                    "uso_recomendado": c["uso_recomendado"],
                }
            )

    OUT_README.write_text(
        """# BT2 historical_sm_lbu cohort plan

## Regenerar

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_historical_sm_lbu_cohort_plan.py
```

## Salidas

- `cohort_plan.json`
- `cohort_summary.csv`
""",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "ok": True,
                "out_json": str(OUT_JSON.relative_to(REPO)),
                "out_csv": str(OUT_CSV.relative_to(REPO)),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()

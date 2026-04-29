#!/usr/bin/env python3
"""
Fase 4B — Ejecución según preregistro congelado (solo lectura DB shadow).

Artefactos fuente: phase4b_holdout_plan.json, phase4b_allowed_segments.csv,
preregister_phase4b_final.md (no modificar).
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
PHASE4A_OUT = ROOT / "scripts" / "outputs" / "bt2_phase4a_shadow_signal_diagnosis"
OUT = ROOT / "scripts" / "outputs" / "bt2_phase4b_execution"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_diag():
    p = ROOT / "scripts" / "bt2_phase4a_shadow_signal_diagnosis.py"
    spec = importlib.util.spec_from_file_location("diag4a", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _tier(scored: int) -> str:
    if scored < 20:
        return "A_inadequate"
    if scored < 50:
        return "B_weak_exploratory"
    return "C_adequate_descriptive"


def _agg_partition(rows: list[dict[str, Any]], run_keys: frozenset) -> dict[str, Any]:
    m = {
        "picks_total": 0,
        "scored": 0,
        "hit": 0,
        "miss": 0,
        "roi_flat_stake_units": 0.0,
    }
    for r in rows:
        if str(r.get("run_key") or "") not in run_keys:
            continue
        m["picks_total"] += 1
        st = str(r.get("eval_status") or "")
        roi = float(r.get("roi_flat_stake_units") or 0.0)
        if st in ("hit", "miss"):
            m["scored"] += 1
            if st == "hit":
                m["hit"] += 1
            elif st == "miss":
                m["miss"] += 1
        m["roi_flat_stake_units"] += roi
    scored = m["scored"]
    hit = m["hit"]
    roi = m["roi_flat_stake_units"]
    return {
        "picks_total": m["picks_total"],
        "scored": scored,
        "hit": hit,
        "hit_rate_on_scored": round(hit / scored, 6) if scored else 0.0,
        "roi_flat_stake_units": round(roi, 4),
        "roi_flat_stake_pct": round((roi / scored) * 100.0, 6) if scored else 0.0,
        "interpretation_tier": _tier(scored),
    }


def _segment_row_value(row: dict[str, Any], dimension: str) -> str:
    if dimension == "source_path":
        return str(row.get("source_path") or "")
    if dimension == "league":
        return str(row.get("league_name") or "Unknown")
    if dimension == "odds_band":
        return str(row.get("odds_band") or "")
    if dimension == "selection_side":
        return str(row.get("selection_side") or "")
    raise ValueError(dimension)


def _load_allowed_segments() -> list[dict[str, str]]:
    path = PHASE4A_OUT / "phase4b_allowed_segments.csv"
    out = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            dim = (r.get("dimension") or "").strip()
            if dim not in ("source_path", "league", "odds_band", "selection_side"):
                continue
            out.append(
                {
                    "dimension": dim,
                    "segment_id": (r.get("segment_id") or "").strip(),
                    "primary_analysis_4b": (r.get("primary_analysis_4b") or "").strip(),
                }
            )
    return out


def _primary_allowed_for_promising(
    dimension: str,
    segment_id: str,
    primary_flag: str,
    sd: int,
    sv: int,
) -> tuple[bool, str]:
    pf = primary_flag.upper()
    if pf == "YES":
        return True, "primary_yes"
    if pf == "NO":
        return False, "primary_no_csv"
    if pf == "BY_CASE":
        if dimension == "league" and segment_id == "Unknown":
            return False, "league_unknown_by_case"
        if dimension == "selection_side" and segment_id == "draw":
            if sd >= 20 and sv >= 20:
                return True, "draw_by_case_scored_ge_20_both"
            return False, "draw_by_case_scored_lt_20"
        return False, "by_case_default_no"
    return False, "primary_flag_unknown"


def _classify_final(
    *,
    dimension: str,
    segment_id: str,
    primary_allowed: bool,
    primary_reason: str,
    sd: int,
    sv: int,
    tier_d: str,
    tier_v: str,
    roi_du: float,
    roi_vu: float,
    roi_dpct: float,
    roi_vpct: float,
) -> tuple[str, str]:
    # 1) Excluidos explícitos de carril prometedor (no interpretar como candidato primario)
    if not primary_allowed:
        return (
            "no_interpretar",
            f"excluded_primary:{primary_reason}",
        )

    # 2) Tier A en cualquier partición
    if tier_d == "A_inadequate" or tier_v == "A_inadequate":
        return (
            "no_interpretar",
            "tier_A_inadequate_in_discovery_or_validation",
        )

    # 3) Tier B en cualquier partición → no prometedor (ruido metodológico)
    if tier_d == "B_weak_exploratory" or tier_v == "B_weak_exploratory":
        return (
            "ruido",
            "tier_B_weak_exploratory_precludes_promising_per_preregister",
        )

    # 4) Ambos C: compuertas cuantitativas congeladas
    assert tier_d == "C_adequate_descriptive" and tier_v == "C_adequate_descriptive"

    # Sign flip rule (|ROI|>=1 en ambas particiones)
    if abs(roi_du) >= 1.0 and abs(roi_vu) >= 1.0:
        if (roi_du > 0) != (roi_vu > 0):
            return ("ruido", "opposite_sign_roi_units_rule_|roi|>=1_both_partitions")

    if roi_vpct <= -4.0:
        return ("ruido", f"validation_roi_pct_{roi_vpct:.4f}_not_above_-4pp_gate")

    if roi_vpct < roi_dpct - 3.0:
        return (
            "ruido",
            f"stability_fail:roi_val {roi_vpct:.4f} < roi_disco {roi_dpct:.4f} - 3pp",
        )

    return ("prometedor", "all_preregister_gates_passed_C_C_roi_gt_-4_stability_sign")


def main() -> None:
    diag = _load_diag()
    plan_path = PHASE4A_OUT / "phase4b_holdout_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    disco = frozenset(plan["discovery"]["run_keys"])
    val = frozenset(plan["validation"]["run_keys"])
    gates = plan["quantitative_gates_for_promising_candidate"]

    run_keys = list(disco | val)
    conn = psycopg2.connect(diag._dsn(), connect_timeout=15)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        rows = diag.fetch_rows(cur, run_keys)
    finally:
        cur.close()
        conn.close()

    allowed = _load_allowed_segments()
    seg_defs = {(a["dimension"], a["segment_id"]): a["primary_analysis_4b"] for a in allowed}

    results: list[dict[str, Any]] = []
    for dimension, segment_id in sorted(seg_defs.keys()):
        pf = seg_defs[(dimension, segment_id)]
        matching = [r for r in rows if _segment_row_value(r, dimension) == segment_id]
        rd = [r for r in matching if str(r.get("run_key") or "") in disco]
        rv = [r for r in matching if str(r.get("run_key") or "") in val]
        ad = _agg_partition(matching, disco)
        av = _agg_partition(matching, val)

        sd, sv = ad["scored"], av["scored"]
        tier_d, tier_v = ad["interpretation_tier"], av["interpretation_tier"]

        primary_ok, primary_reason = _primary_allowed_for_promising(
            dimension, segment_id, pf, sd, sv
        )

        fc, reason = _classify_final(
            dimension=dimension,
            segment_id=segment_id,
            primary_allowed=primary_ok,
            primary_reason=primary_reason,
            sd=sd,
            sv=sv,
            tier_d=tier_d,
            tier_v=tier_v,
            roi_du=float(ad["roi_flat_stake_units"]),
            roi_vu=float(av["roi_flat_stake_units"]),
            roi_dpct=float(ad["roi_flat_stake_pct"]),
            roi_vpct=float(av["roi_flat_stake_pct"]),
        )

        interpretation_combined = f"{tier_d}|{tier_v}"

        results.append(
            {
                "dimension": dimension,
                "segment_id": segment_id,
                "picks_total": len(matching),
                "scored_discovery": sd,
                "scored_validation": sv,
                "hit_rate_discovery": ad["hit_rate_on_scored"],
                "hit_rate_validation": av["hit_rate_on_scored"],
                "roi_discovery_units": ad["roi_flat_stake_units"],
                "roi_validation_units": av["roi_flat_stake_units"],
                "roi_discovery_pct": ad["roi_flat_stake_pct"],
                "roi_validation_pct": av["roi_flat_stake_pct"],
                "interpretation_tier_discovery": tier_d,
                "interpretation_tier_validation": tier_v,
                "interpretation_tier": interpretation_combined,
                "final_classification": fc,
                "classification_reason": reason,
                "primary_analysis_csv": pf,
            }
        )

    promising = [r for r in results if r["final_classification"] == "prometedor"]
    noise = [r for r in results if r["final_classification"] == "ruido"]
    nointerp = [r for r in results if r["final_classification"] == "no_interpretar"]

    OUT.mkdir(parents=True, exist_ok=True)
    summary = {
        "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "phase": "4B_execution",
        "frozen_sources": {
            "holdout_plan": str(PHASE4A_OUT / "phase4b_holdout_plan.json"),
            "allowed_segments": str(PHASE4A_OUT / "phase4b_allowed_segments.csv"),
            "preregister": str(PHASE4A_OUT / "preregister_phase4b_final.md"),
        },
        "universe": {
            "run_keys_discovery": sorted(disco),
            "run_keys_validation": sorted(val),
            "picks_total_all_partitions": len(rows),
            "gates_applied": gates,
        },
        "counts": {
            "segments_evaluated": len(results),
            "prometedor": len(promising),
            "ruido": len(noise),
            "no_interpretar": len(nointerp),
        },
        "verdict_one_liner": (
            "Hay candidatos prometedores según reglas congeladas."
            if promising
            else "Ningún segmento univariado cumplió todas las compuertas de prometedor."
        ),
        "structural_notes_4b": [
            "El segmento source_path=sportmonks_between_subset5_fallback solo existe en runs 2026-01..03 (discovery); en validation queda scored_validation=0 por definición de carril.",
            "Muchos estratos tienen scored_validation<50 (a menudo tier A en validation) porque abril+daily concentra menos masa por liga/banda que Q1+Q4 discovery-only splits.",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    fn = list(results[0].keys()) if results else []
    for name, subset in [
        ("by_segment_discovery_validation.csv", results),
        ("promising_candidates.csv", promising),
        ("noise_segments.csv", noise),
        ("do_not_interpret_segments.csv", nointerp),
    ]:
        with (OUT / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fn, extrasaction="ignore")
            w.writeheader()
            for row in subset:
                w.writerow(row)

    readme = """# Fase 4B — Ejecución (preregistro congelado)

Generado por `scripts/bt2_phase4b_execute.py`.

## Fuentes

- Umbrales y partición: `phase4b_holdout_plan.json` (sin modificación).
- Partición discovery/validation por `run_key`.

## Archivos

- `summary.json` — conteos, notas estructurales y veredicto.
- `by_segment_discovery_validation.csv` — todos los segmentos evaluados.
- `promising_candidates.csv` — estratos `prometedor` (puede estar vacío).
- `noise_segments.csv` / `do_not_interpret_segments.csv` — partición de resultados.

**No producción.** Solo lectura DB shadow.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps(summary["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

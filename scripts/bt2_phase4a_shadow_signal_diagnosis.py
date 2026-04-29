#!/usr/bin/env python3
"""
Fase 4A / 4A.1 — Diagnóstico descriptivo de señal sobre el stack shadow validado.

Solo lectura sobre DB shadow. No tuning, no producción.
Universo = mismo consolidado pre-Fase 4 (runs base + shadow-daily-*).
4A.1: manifiesto pick_inputs para home/away; capas de N; preregistro 4B en artifacts.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_phase4a_shadow_signal_diagnosis"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SM_FALLBACK_RUN_KEYS = frozenset(
    {
        "shadow-subset5-backfill-2026-01",
        "shadow-subset5-backfill-2026-02",
        "shadow-subset5-backfill-2026-03",
    }
)

BASE_RUNS = [
    "shadow-subset5-backfill-2025-01-05",
    "shadow-subset5-recovery-2025-07-12",
    "shadow-subset5-backfill-2026-01",
    "shadow-subset5-backfill-2026-02",
    "shadow-subset5-backfill-2026-03",
    "shadow-subset5-backfill-2026-04",
]

# Capas de scored (Fase 4A.1): <20 inadecuado para cualquier lectura direccional;
# 20–49 exploratorio; ≥50 descriptivo estable a nivel de estrato (sigue sin probar edge).
N_SCORED_TIER_INADEQUATE = 20
N_SCORED_TIER_ADEQUATE = 50
# Retrocompat: alerta si scored < 20
SMALL_SCORED_WARN = N_SCORED_TIER_INADEQUATE


def _interpretation_tier(scored: int) -> str:
    if scored < N_SCORED_TIER_INADEQUATE:
        return "A_inadequate"
    if scored < N_SCORED_TIER_ADEQUATE:
        return "B_weak_exploratory"
    return "C_adequate_descriptive"


def _treat_stratum_as_signal_banned(scored: int) -> bool:
    """Fase 4A.1: no calificar de 'señal' a estratos con N debil."""
    return scored < N_SCORED_TIER_ADEQUATE


def _dsn() -> str:
    from apps.api.bt2_settings import bt2_settings

    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def classify_source_path(run_key: str) -> str:
    if run_key.startswith("shadow-daily-"):
        return "daily_shadow_sm_toa"
    if run_key in SM_FALLBACK_RUN_KEYS:
        return "sportmonks_between_subset5_fallback"
    return "cdm_shadow"


def classify_time_window(run_key: str) -> str:
    if run_key.startswith("shadow-daily-"):
        return "daily_shadow"
    if run_key == "shadow-subset5-backfill-2025-01-05":
        return "2025_Jan_subset5_window"
    if run_key == "shadow-subset5-recovery-2025-07-12":
        return "2025_Jul_subset5_recovery"
    m = re.match(r"shadow-subset5-backfill-2026-(\d{2})$", run_key)
    if m:
        return f"2026_month_{m.group(1)}"
    return "other"


def classify_run_group(run_key: str) -> str:
    if run_key.startswith("shadow-daily-"):
        return "daily_shadow"
    if "2025-01" in run_key or "2025-07" in run_key:
        return "subset5_2025_backfill_or_recovery"
    return "subset5_2026_monthly"


def _norm_team(s: str | None) -> str:
    if not s:
        return ""
    t = unicodedata.normalize("NFKD", (s or "").strip().lower())
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = re.sub(r"[\.\'`´]", "", t)
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for tok in (" fc", " cf", " sc", " afc", " fk", " ac"):
        if t.endswith(tok):
            t = t[: -len(tok)].strip()
    return t


def _canon_team(s: str) -> str:
    aliases = {
        "afc bournemouth": "bournemouth",
        "bayer 04 leverkusen": "bayer leverkusen",
        "losc lille": "lille",
        "celta de vigo": "celta vigo",
        "deportivo alaves": "alaves",
    }
    n = _norm_team(s)
    return aliases.get(n, n)


def classify_selection_side(
    selection: str | None,
    home_name: str | None,
    away_name: str | None,
) -> str:
    s_raw = (selection or "").strip()
    if not s_raw:
        return "unknown"
    s = _canon_team(s_raw)
    if s in {"draw", "empate", "x"}:
        return "draw"
    home = _canon_team(home_name or "")
    away = _canon_team(away_name or "")
    if home and (s == home or home in s or s in home):
        return "home"
    if away and (s == away or away in s or s in away):
        return "away"
    if home or away:
        return "unknown_resolved_teams"
    return "unknown"


def classify_odds_band(dec: Any) -> str:
    try:
        d = float(dec) if dec is not None else None
    except (TypeError, ValueError):
        d = None
    if d is None or d <= 0:
        return "unknown_odds"
    if d < 2.0:
        return "dec_lt_2"
    if d < 2.5:
        return "dec_2_to_2_5"
    if d < 3.0:
        return "dec_2_5_to_3"
    if d < 4.0:
        return "dec_3_to_4"
    if d < 6.0:
        return "dec_4_to_6"
    return "dec_ge_6"


def _empty_metrics() -> dict[str, Any]:
    return {
        "picks_total": 0,
        "scored": 0,
        "hit": 0,
        "miss": 0,
        "void": 0,
        "pending_result": 0,
        "no_evaluable": 0,
        "roi_flat_stake_units": 0.0,
    }


def _add(m: dict[str, Any], st: str, roi: float) -> None:
    m["picks_total"] += 1
    if st in ("hit", "miss"):
        m["scored"] += 1
    if st == "hit":
        m["hit"] += 1
    elif st == "miss":
        m["miss"] += 1
    elif st == "void":
        m["void"] += 1
    elif st == "pending_result":
        m["pending_result"] += 1
    elif st == "no_evaluable":
        m["no_evaluable"] += 1
    m["roi_flat_stake_units"] += float(roi or 0.0)


def _finalize(m: dict[str, Any]) -> dict[str, Any]:
    scored = int(m["scored"])
    hit = int(m["hit"])
    roi = float(m["roi_flat_stake_units"])
    out = dict(m)
    out["hit_rate_on_scored"] = round(hit / scored, 6) if scored else 0.0
    out["roi_flat_stake_units"] = round(roi, 4)
    out["roi_flat_stake_pct"] = round((roi / scored) * 100.0, 6) if scored else 0.0
    out["small_sample_warning"] = scored > 0 and scored < SMALL_SCORED_WARN
    out["interpretation_tier"] = _interpretation_tier(scored)
    out["signal_reading_banned_4a1"] = _treat_stratum_as_signal_banned(scored)
    return out


def _sort_key_rows(rows: list[dict[str, Any]], key: str = "picks_total") -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: (-int(r.get(key) or 0), str(r.get(list(r.keys())[0], ""))))


def aggregate_by(
    rows: list[dict[str, Any]],
    key_fn: Callable[[dict[str, Any]], str],
    label: str,
) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(_empty_metrics)
    for r in rows:
        k = key_fn(r)
        _add(buckets[k], str(r.get("eval_status") or ""), float(r.get("roi_flat_stake_units") or 0.0))
    out = []
    for k, m in sorted(buckets.items()):
        row = _finalize(m)
        row[label] = k
        out.append(row)
    return _sort_key_rows(out, "picks_total")


def fetch_rows(cur: Any, run_keys: list[str]) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            r.run_key,
            dp.operating_day_key,
            dp.selection,
            dp.decimal_odds AS pick_decimal_odds,
            pe.eval_status,
            pe.roi_flat_stake_units,
            COALESCE(l.sportmonks_id, -1) AS sm_league_id,
            COALESCE(l.name, 'Unknown') AS league_name,
            COALESCE(
                NULLIF(BTRIM(ht.name), ''),
                NULLIF(BTRIM(rsf.home_team), ''),
                NULLIF(BTRIM(man.manifest_home_sm), '')
            ) AS home_team_name,
            COALESCE(
                NULLIF(BTRIM(at.name), ''),
                NULLIF(BTRIM(rsf.away_team), ''),
                NULLIF(BTRIM(man.manifest_away_sm), '')
            ) AS away_team_name,
            NULLIF(BTRIM(COALESCE(ht.name, rsf.home_team)), '') AS home_team_legacy,
            NULLIF(BTRIM(COALESCE(at.name, rsf.away_team)), '') AS away_team_legacy
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs r ON r.id = dp.run_id
        LEFT JOIN bt2_shadow_pick_eval pe ON pe.shadow_daily_pick_id = dp.id
        LEFT JOIN bt2_leagues l ON l.id = dp.league_id
        LEFT JOIN bt2_events e ON e.id = dp.bt2_event_id
        LEFT JOIN bt2_teams ht ON ht.id = e.home_team_id
        LEFT JOIN bt2_teams at ON at.id = e.away_team_id
        LEFT JOIN raw_sportmonks_fixtures rsf ON rsf.fixture_id = dp.sm_fixture_id
        LEFT JOIN LATERAL (
            SELECT
                pi.payload_json->'manifest_row'->>'home_team_sm' AS manifest_home_sm,
                pi.payload_json->'manifest_row'->>'away_team_sm' AS manifest_away_sm
            FROM bt2_shadow_pick_inputs pi
            WHERE pi.shadow_daily_pick_id = dp.id
            ORDER BY pi.id ASC
            LIMIT 1
        ) man ON true
        WHERE r.run_key = ANY(%s)
        """,
        (run_keys,),
    )
    raw = cur.fetchall() or []
    enriched: list[dict[str, Any]] = []
    for x in raw:
        d = dict(x)
        d["source_path"] = classify_source_path(str(d.get("run_key") or ""))
        d["time_window"] = classify_time_window(str(d.get("run_key") or ""))
        d["run_group"] = classify_run_group(str(d.get("run_key") or ""))
        d["selection_side"] = classify_selection_side(
            d.get("selection"),
            d.get("home_team_name"),
            d.get("away_team_name"),
        )
        d["selection_side_before_manifest_4a1"] = classify_selection_side(
            d.get("selection"),
            d.get("home_team_legacy"),
            d.get("away_team_legacy"),
        )
        d["odds_band"] = classify_odds_band(d.get("pick_decimal_odds"))
        enriched.append(d)
    return enriched


def _write_preregister_4b(out_dir: Path, side_audit: dict[str, Any]) -> None:
    text = f"""# Preregistro metodológico — Fase 4B (selective release *disciplinado*, no ejecutado)

Documento generado en Fase 4A.1. **No abre 4B**; fija reglas antes de cualquier ejecución.

## Alcance permitido (cuando se abra 4B)

- **Stack:** mismo shadow validado (subset5, h2h, us, T-60); sin nuevos proveedores.
- **Segmentos elegibles para *screening* (no para concluir edge):**
  - `source_path` ∈ {{`cdm_shadow`, `sportmonks_between_subset5_fallback`}} con **scored ≥ 50** en el estrato.
  - `by_league` con **scored ≥ 50** por liga (subset5 → normalmente una liga a la vez alcanza umbral).
  - `by_odds_band` con bandas fijas (mismas que 4A) y **scored ≥ 50** por banda.
- **Ventana temporal:** holdout: último mes o último run mensual *no* usado en el ajuste de reglas; definir en el arranque de 4B (pre-registro adicional con fecha de corte).

## Segmentos **no** permitidos para decisiones 4B sin ampliar N

- `daily_shadow_sm_toa` con **picks_total < 50** (muestra actual insuficiente).
- Cualquier estrato con **scored < 50** → solo descriptivo; **prohibido** rotular como “señal” o “regla de release”.
- Estratos con **scored < 20** → **no interpretar** direccionalidad de ROI.

## Reglas fijas reutilizables

- **Bandas de cuota (decimal):** `dec_lt_2`, `dec_2_to_2_5`, `dec_2_5_to_3`, `dec_3_to_4`, `dec_4_to_6`, `dec_ge_6`, `unknown_odds`.
- **Mínimos de N (scored):** ver `summary.json` → `methodology.n_thresholds_scored_4a1` (A/B/C). Criterio 4B: **C_adequate_descriptive** (≥{N_SCORED_TIER_ADEQUATE}) para plantear *candidato* a regla; **B** solo genera hipótesis.
- **Split temporal:** proponer “entrenamiento descriptivo” = consolidado pre-Fase 4 hasta corte T; “validación” = sombra posterior o mes siguiente. Detallar en el PR de 4B.

## Criterio “prometedor” vs “ruido”

- **Prometedor (candidato):** ROI% y hit_rate en estrato C con consistencia con narrativa 4A (p. ej. no contradice agregado sin explicación); **sigue siendo** candidato, no producto.
- **Ruido:** tier A o B, o contradicción fuerte con otras capas (path/liga) sin replicación.

## Criterio “no interpretar”

- `interpretation_tier` = `A_inadequate`, o `signal_reading_banned_4a1` = true bajo reglas 4A.1.

## `selection_side` (post 4A.1)

- Distribución al generar: {json.dumps(side_audit.get("distribution", {}), ensure_ascii=True)}

---

*Fase 4A.1: solo diagnóstico; 4B requiere aprobar explícitamente este preregistro o enmendarlo con versión fechada.*
"""
    (out_dir / "preregister_phase4b.md").write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in fieldnames})


def main() -> None:
    conn = psycopg2.connect(_dsn(), connect_timeout=15)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT run_key FROM bt2_shadow_runs
            WHERE run_key LIKE 'shadow-daily-%' ORDER BY created_at ASC
            """
        )
        daily = [str(r["run_key"]) for r in (cur.fetchall() or [])]
        run_keys = BASE_RUNS + daily
        rows = fetch_rows(cur, run_keys)
    finally:
        cur.close()
        conn.close()

    # Auditoría selection_side (4A.1)
    _side_dist: dict[str, int] = defaultdict(int)
    for r in rows:
        _side_dist[str(r.get("selection_side") or "unknown")] += 1
    unk_new = sum(1 for r in rows if (r.get("selection_side") or "") == "unknown")
    unk_old = sum(1 for r in rows if (r.get("selection_side_before_manifest_4a1") or "") == "unknown")
    side_audit = {
        "distribution": dict(sorted(_side_dist.items(), key=lambda x: -x[1])),
        "unknown_count_with_manifest_4a1": unk_new,
        "unknown_count_legacy_join_only": unk_old,
        "unknown_reduced_by": unk_old - unk_new,
        "note": "COALESCE con manifest_row (pick_inputs) tras bt2_teams y raw_sportmonks columnas.",
    }

    total = _empty_metrics()
    for r in rows:
        _add(total, str(r.get("eval_status") or ""), float(r.get("roi_flat_stake_units") or 0.0))
    total_f = _finalize(total)

    # --- breakdowns ---
    dim_fields = [
        "picks_total",
        "scored",
        "hit",
        "miss",
        "void",
        "pending_result",
        "no_evaluable",
        "hit_rate_on_scored",
        "roi_flat_stake_units",
        "roi_flat_stake_pct",
        "interpretation_tier",
        "signal_reading_banned_4a1",
        "small_sample_warning",
    ]

    by_sp = aggregate_by(rows, lambda r: r["source_path"], "source_path")

    lg_buckets: dict[tuple[int, str], dict[str, Any]] = defaultdict(_empty_metrics)
    for r in rows:
        lg_id = int(r.get("sm_league_id") or -1)
        lg_nm = str(r.get("league_name") or "Unknown")
        _add(lg_buckets[(lg_id, lg_nm)], str(r.get("eval_status") or ""), float(r.get("roi_flat_stake_units") or 0.0))
    by_lg = []
    for (lg_id, lg_nm), m in sorted(lg_buckets.items(), key=lambda x: (-x[1]["picks_total"], x[0][1])):
        row = _finalize(m)
        row["sm_league_id"] = lg_id
        row["league_name"] = lg_nm
        by_lg.append(row)

    by_ob = aggregate_by(rows, lambda r: str(r.get("odds_band")), "odds_band")
    by_side = aggregate_by(rows, lambda r: str(r.get("selection_side")), "selection_side")
    by_tw = aggregate_by(rows, lambda r: str(r.get("time_window")), "time_window")
    by_rk = aggregate_by(rows, lambda r: str(r.get("run_key")), "run_key")
    by_rg = aggregate_by(rows, lambda r: str(r.get("run_group")), "run_group")

    # ROI contribution (scored picks only sum to total roi in our data — same as roi sum on all rows)
    scored_roi_by_path: dict[str, float] = defaultdict(float)
    for r in rows:
        st = str(r.get("eval_status") or "")
        if st not in ("hit", "miss"):
            continue
        sp = r["source_path"]
        scored_roi_by_path[sp] += float(r.get("roi_flat_stake_units") or 0.0)
    total_roi_scored = sum(scored_roi_by_path.values())
    roi_contrib = []
    for sp, val in sorted(scored_roi_by_path.items(), key=lambda x: x[1]):
        roi_contrib.append(
            {
                "source_path": sp,
                "roi_flat_stake_units_on_scored": round(val, 4),
                "pct_of_total_scored_roi": round((val / total_roi_scored) * 100.0, 4) if total_roi_scored else 0.0,
            }
        )

    # Top league damage (negative ROI)
    lg_roi = defaultdict(float)
    for r in rows:
        if str(r.get("eval_status") or "") not in ("hit", "miss"):
            continue
        lg_roi[str(r.get("league_name") or "Unknown")] += float(r.get("roi_flat_stake_units") or 0.0)
    leagues_by_roi = sorted(lg_roi.items(), key=lambda x: x[1])

    worst_path = min(roi_contrib, key=lambda z: z["roi_flat_stake_units_on_scored"]) if roi_contrib else None
    best_candidate_lgs = [
        {"league_name": nm, "roi_flat_stake_units": round(v, 4), "scored_approx_note": "ver by_league"}
        for nm, v in leagues_by_roi[-3:]
        if v > 0
    ]

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "4A.1",
        "universe": {
            "constraint_lane": "shadow_only",
            "subset": "subset5",
            "market": "h2h",
            "region": "us",
            "snapshot_policy": "T-60",
            "runs_included": run_keys,
            "picks_total": total_f["picks_total"],
            "scored": total_f["scored"],
            "metrics_on_scored": {
                "hit_rate_on_scored": total_f["hit_rate_on_scored"],
                "roi_flat_stake_pct": total_f["roi_flat_stake_pct"],
                "roi_flat_stake_units": total_f["roi_flat_stake_units"],
            },
            "pending_result": total_f["pending_result"],
            "no_evaluable": total_f["no_evaluable"],
        },
        "methodology": {
            "mode": "descriptive_only",
            "no_production_touch": True,
            "no_tuning": True,
            "scored_definition": "eval_status in (hit, miss); ROI from bt2_shadow_pick_eval.roi_flat_stake_units",
            "stratifications": [
                "source_path",
                "run_key",
                "run_group",
                "league_name",
                "selection_side",
                "odds_band_decimal",
                "time_window",
            ],
            "n_thresholds_scored_4a1": {
                "A_inadequate": f"scored < {N_SCORED_TIER_INADEQUATE}",
                "B_weak_exploratory": f"{N_SCORED_TIER_INADEQUATE} <= scored < {N_SCORED_TIER_ADEQUATE}",
                "C_adequate_descriptive": f"scored >= {N_SCORED_TIER_ADEQUATE}",
                "justification": (
                    "<20: varianza muestral binomial extrema para proporciones. "
                    "20–49: heurística de exploración (cercano a regla informal n≥30 para CLT aproximado de p̂). "
                    "≥50: estrato con masa suficiente para descriptivos agregados; no implica edge."
                ),
                "signal_reading_banned_4a1": f"true si scored < {N_SCORED_TIER_ADEQUATE} (no formular 'señal' por estrato).",
            },
            "odds_bands_decimal": [
                "unknown_odds",
                "dec_lt_2",
                "dec_2_to_2_5",
                "dec_2_5_to_3",
                "dec_3_to_4",
                "dec_4_to_6",
                "dec_ge_6",
            ],
            "selection_side_rules_4a1": (
                "Orden de fuente de equipos: bt2_teams (vía bt2_events), columnas home_team/away de "
                "raw_sportmonks_fixtures, luego pick_inputs.payload_json.manifest_row (home_team_sm, away_team_sm) — "
                "misma ventana de matching que el backfill. Misma canon/alias que h2h backfill. "
                "Draw si draw/empate/x. unknown si no hay selection o el nombre no mapea."
            ),
            "what_this_does_not_prove": [
                "No es test estadístico de edge ni CI.",
                "Estratos tier B aún bajo signal_reading_ban para lenguaje de 'señal'.",
                "Múltiples comparaciones sin corrección — exploratorio.",
                "Caveats baseline pre-Fase 4 siguen vigentes (mezcla source_path, VP, pendientes).",
            ],
        },
        "selection_side_audit_4a1": side_audit,
        "caveat_selection_side_residual": (
            "Puede quedar unknown si no hay fila pick_inputs, selection vacía, o rótulo de equipo aún no alineable."
        ),
        "diagnosis_notes": {
            "roi_contribution_by_source_path_scored_picks": roi_contrib,
            "leagues_sorted_by_roi_units": [
                {"league_name": name, "roi_flat_stake_units": round(v, 4)} for name, v in leagues_by_roi
            ],
        },
        "verdict": {
            "primary_negative_driver_source_path": worst_path,
            "leagues_positive_roi_units_on_scored_sample": best_candidate_lgs,
            "phase_4b_selective_release": (
                "No recomendado solo con este diagnóstico; requiere reglas pre-registradas "
                "y validación temporal adicional."
            ),
        },
        "artifacts_4a1": {
            "preregister_phase4b": "preregister_phase4b.md",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_preregister_4b(OUT_DIR, side_audit)

    def pack(dim: str, rows_dim: list[dict[str, Any]]) -> None:
        fn = [dim] + dim_fields
        write_csv(OUT_DIR / f"by_{dim}.csv", rows_dim, fn)

    pack("source_path", by_sp)
    fn_lg = ["sm_league_id", "league_name"] + dim_fields
    write_csv(OUT_DIR / "by_league.csv", _sort_key_rows(by_lg, "picks_total"), fn_lg)
    pack("odds_band", by_ob)
    pack("selection_side", by_side)
    pack("time_window", by_tw)
    pack("run_key", by_rk)
    pack("run_group", by_rg)

    readme = _readme_text(
        total_f, by_sp, leagues_by_roi, side_audit, N_SCORED_TIER_INADEQUATE, N_SCORED_TIER_ADEQUATE
    )
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps({"ok": True, "out": str(OUT_DIR.relative_to(ROOT)), "total": total_f}, ensure_ascii=False, indent=2))


def _readme_text(
    total_f: dict[str, Any],
    by_sp: list[dict[str, Any]],
    leagues_by_roi: list[tuple[str, float]],
    side_audit: dict[str, Any],
    n_tier_inad: int,
    n_tier_adequate: int,
) -> str:
    dist = side_audit.get("distribution") or {}
    dist_s = ", ".join(f"{k}={v}" for k, v in sorted(dist.items(), key=lambda x: -x[1]))
    lines = [
        "# Fase 4A.1 — Diagnóstico de señal (shadow) + preregistro 4B",
        "",
        "Generado por `scripts/bt2_phase4a_shadow_signal_diagnosis.py`.",
        "**Solo lectura descriptiva.** No implica edge ni apertura de Fase 4B productiva.",
        "",
        "## Universo",
        "",
        f"- Picks: **{total_f['picks_total']}**, scored: **{total_f['scored']}**, ROI unidades (suma evals): **{total_f['roi_flat_stake_units']}**.",
        f"- Pendientes / no evaluable: **{total_f['pending_result']}** / **{total_f['no_evaluable']}**.",
        "",
        "## 4A.1 — N y lectura de estratos",
        "",
        f"- **Tier A (inadecuado):** scored < **{n_tier_inad}** — no interpretar dirección de ROI en el estrato.",
        f"- **Tier B (débil):** {n_tier_inad} ≤ scored < **{n_tier_adequate}** — solo exploratorio; `signal_reading_banned_4a1` = true.",
        f"- **Tier C (descriptivo):** scored ≥ **{n_tier_adequate}** — descriptivo agregado permitido; sigue sin probar edge.",
        "- Columnas en CSV: `interpretation_tier`, `signal_reading_banned_4a1`.",
        "",
        "## `selection_side` (post manifiesto)",
        "",
        f"- Distribución: {dist_s}",
        "- Fuente: `bt2_events`+equipos → `raw_sportmonks_fixtures` → **manifest_row** en `bt2_shadow_pick_inputs`.",
        "",
        "## Archivos",
        "",
        "- `summary.json` — universo, N-thresholds, auditoría de sides, notas de diagnóstico.",
        "- `preregister_phase4b.md` — reglas *propuestas* para una futura 4B (no activa).",
        "- `by_*.csv` — cortes con columnas de interpretación por estrato.",
        "",
        "## Hallazgos (source_path, scored)",
        "",
    ]
    for r in by_sp:
        lines.append(
            f"- **{r['source_path']}**: scored={r['scored']}, tier={r.get('interpretation_tier')}, "
            f"hit%={r['hit_rate_on_scored']:.4f}, roi%={r['roi_flat_stake_pct']:.2f}"
        )
    lines.extend(
        [
            "",
            "### Ligas (ROI unidades, hit+miss)",
            "",
        ]
    )
    for name, v in leagues_by_roi[:8]:
        lines.append(f"- {name}: **{v:.2f}**")
    lines.extend(
        [
            "",
            "## Veredicto 4A.1",
            "",
            "- Composición de agregado: sigue alineada con 4A (volumen fallback + aportes a ROI; ver `summary.json`).",
            "- Próximo salto: **Fase 4B** solo tras aprobar/ajustar `preregister_phase4b.md` y ejecutar con holdout; no se abre en esta iteración.",
            "",
            "## Caveats baseline (vigentes)",
            "",
            "- Carriles mezclados, VP no comparable entre paths, 14 `pending_result`.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fase 4 — discovery vs validation (read-only, metodología congelada en código + JSON).

No modifica bt2_phase4_selective_release_edge_audit.py: script hermano.

Split temporal: días con picks scored y reference_decimal_odds > 1, ordenados;
  discovery = primeros ceil(K/2) días calendario;
  validation = días restantes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import psycopg2
import psycopg2.extras

from apps.api.bt2_settings import bt2_settings

# --- Metodología congelada (Fase 4 discovery/validation) ---
# Segmentos base (sin tunear cruces a posteriori).
# Nombres alineados a columnas dp; prefijo en CSV como Fase 4 (market:, league_tier:, …).
SEGMENT_DIMS = ("confidence_band", "league_tier", "odds_band", "market")
# market_x_odds: solo se evalúa veredicto "prometedor" si N_discovery >= MIN_N_MARKET_X_ODDS
MIN_N_MARKET_X_ODDS = 35
# Mínimos para considerar un segmento en veredicto serio
MIN_N_DISCOVERY = 20
MIN_N_VALIDATION = 12
# Mejora material vs global discovery
MIN_HR_DELTA_VS_GLOBAL = 0.05
MIN_ROI_DELTA_VS_GLOBAL = 0.025
# Estabilidad: no colapsar en validation
MAX_HR_DROP_DISC_TO_VAL = 0.12
MAX_ROI_DROP_DISC_TO_VAL = 0.15
# Frágil si cae más que umbrales
FRAGILE_HR_DROP = 0.12
FRAGILE_ROI_DROP = 0.20
# Qué NO se hace (documentación)
ANTI_TUNING_ES = (
    "No se redefinen cortes de odds_band (mismos umbres que edge audit Fase 4). "
    "No se añaden dimensiones nuevas post-hoc. No se promueve segmento con N_discovery < "
    f"{MIN_N_DISCOVERY} ni N_validation < {MIN_N_VALIDATION}. market_x_odds solo entra en "
    f"veredicto prometedor si N_discovery >= {MIN_N_MARKET_X_ODDS}."
)


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def odds_band(odds: Optional[float]) -> str:
    if odds is None or odds <= 1.0:
        return "unknown_or_invalid_odds"
    o = float(odds)
    if o < 1.85:
        return "dec_1.00_1.85"
    if o < 2.2:
        return "dec_1.85_2.20"
    if o < 2.8:
        return "dec_2.20_2.80"
    return "dec_2.80_plus"


def conf_band(c: Optional[str]) -> str:
    s = (c or "").strip().lower()
    if s in ("high", "medium", "low"):
        return f"conf_{s}"
    return "conf_other_or_empty"


@dataclass
class Agg:
    n: int = 0
    hits: int = 0
    misses: int = 0
    sum_odds: float = 0.0
    n_odds: int = 0
    sum_be: float = 0.0
    n_be: int = 0
    sum_profit: float = 0.0
    n_profit: int = 0

    def add(self, hit: bool, odds: Optional[float]) -> None:
        self.n += 1
        if hit:
            self.hits += 1
        else:
            self.misses += 1
        if odds is not None and odds > 1.0:
            fo = float(odds)
            self.sum_odds += fo
            self.n_odds += 1
            self.sum_be += 1.0 / fo
            p = (fo - 1.0) if hit else -1.0
            self.sum_profit += p
            self.n_profit += 1

    def metrics(self) -> dict[str, Any]:
        scored = self.hits + self.misses
        hr = self.hits / scored if scored else None
        avg_o = self.sum_odds / self.n_odds if self.n_odds else None
        avg_be = self.sum_be / self.n_odds if self.n_odds else None
        roi = self.sum_profit / self.n_profit if self.n_profit else None
        return {
            "n": self.n,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hr, 4) if hr is not None else None,
            "avg_decimal_odds": round(avg_o, 4) if avg_o is not None else None,
            "avg_implied_break_even_rate": round(avg_be, 4) if avg_be is not None else None,
            "roi_flat_stake_1u": round(roi, 4) if roi is not None else None,
        }


def _day_filter_clause(day_from: Optional[str], day_to: Optional[str]) -> tuple[str, list[Any]]:
    """Filtro opcional por operating_day_key (inclusive). No altera metodología ni umbrales."""
    parts: list[str] = []
    params: list[Any] = []
    if day_from:
        parts.append("dp.operating_day_key >= %s::date")
        params.append(day_from)
    if day_to:
        parts.append("dp.operating_day_key <= %s::date")
        params.append(day_to)
    if not parts:
        return "", []
    return " AND " + " AND ".join(parts), params


def fetch_rows(cur: Any, day_from: Optional[str], day_to: Optional[str]) -> list[dict[str, Any]]:
    extra, params = _day_filter_clause(day_from, day_to)
    cur.execute(
        f"""
        SELECT
            dp.operating_day_key::text AS operating_day_key,
            (e.evaluation_status = 'evaluated_hit') AS is_hit,
            dp.reference_decimal_odds::float AS reference_decimal_odds,
            COALESCE(NULLIF(TRIM(dp.model_market_canonical), ''), '(vacío)') AS market_canonical,
            COALESCE(NULLIF(TRIM(UPPER(l.tier)), ''), 'UNK') AS league_tier,
            COALESCE(NULLIF(TRIM(dp.dsr_confidence_label), ''), '') AS dsr_confidence_label
        FROM bt2_daily_picks dp
        INNER JOIN bt2_pick_official_evaluation e ON e.daily_pick_id = dp.id
        INNER JOIN bt2_events ev ON ev.id = dp.event_id
        LEFT JOIN bt2_leagues l ON l.id = ev.league_id
        WHERE e.evaluation_status IN ('evaluated_hit', 'evaluated_miss')
          AND dp.reference_decimal_odds IS NOT NULL
          AND dp.reference_decimal_odds::float > 1
          {extra}
        ORDER BY dp.operating_day_key, dp.id
        """,
        params,
    )
    return [dict(r) for r in cur.fetchall()]


def fetch_bd_universe_scan(cur: Any) -> dict[str, Any]:
    """Solo evidencia operativa (read-only); no entra en veredictos."""
    cur.execute(
        """
        SELECT
          COUNT(*) FILTER (WHERE e.evaluation_status IN ('evaluated_hit','evaluated_miss')
            AND dp.reference_decimal_odds IS NOT NULL AND dp.reference_decimal_odds::float > 1) AS n_scored_with_usable_odds,
          COUNT(*) FILTER (WHERE e.evaluation_status IN ('evaluated_hit','evaluated_miss')) AS n_scored_any,
          COUNT(*) FILTER (WHERE e.evaluation_status IN ('evaluated_hit','evaluated_miss')
            AND dp.reference_decimal_odds IS NULL) AS n_scored_null_odds,
          COUNT(*) FILTER (WHERE e.evaluation_status IN ('evaluated_hit','evaluated_miss')
            AND dp.reference_decimal_odds IS NOT NULL AND dp.reference_decimal_odds::float <= 1) AS n_scored_bad_odds,
          MIN(dp.operating_day_key) FILTER (WHERE e.evaluation_status IN ('evaluated_hit','evaluated_miss')
            AND dp.reference_decimal_odds IS NOT NULL AND dp.reference_decimal_odds::float > 1) AS day_min_usable,
          MAX(dp.operating_day_key) FILTER (WHERE e.evaluation_status IN ('evaluated_hit','evaluated_miss')
            AND dp.reference_decimal_odds IS NOT NULL AND dp.reference_decimal_odds::float > 1) AS day_max_usable
        FROM bt2_daily_picks dp
        INNER JOIN bt2_pick_official_evaluation e ON e.daily_pick_id = dp.id
        """
    )
    row = dict(cur.fetchone() or {})
    for k in ("day_min_usable", "day_max_usable"):
        if row.get(k) is not None:
            row[k] = str(row[k])
    cur.execute(
        """
        SELECT COUNT(*)::int AS n_daily_picks,
               MIN(operating_day_key)::text AS day_min_dp,
               MAX(operating_day_key)::text AS day_max_dp
        FROM bt2_daily_picks
        """
    )
    row.update({k: v for k, v in dict(cur.fetchone() or {}).items()})
    cur.execute(
        """
        SELECT e.evaluation_status, COUNT(*)::int AS n
        FROM bt2_pick_official_evaluation e
        GROUP BY 1 ORDER BY n DESC
        """
    )
    row["official_evaluation_by_status"] = [dict(r) for r in cur.fetchall()]
    return row


def segment_keys(r: dict[str, Any]) -> dict[str, str]:
    odds = r.get("reference_decimal_odds")
    mk = str(r.get("market_canonical") or "(vacío)")
    return {
        "confidence_band": conf_band(r.get("dsr_confidence_label")),
        "league_tier": f"{r.get('league_tier') or 'UNK'}",
        "odds_band": odds_band(odds),
        "market": mk,
        "market_x_odds": f"{mk}|{odds_band(odds)}",
    }


def verdict(
    *,
    g_hr_d: float,
    g_roi_d: float,
    g_hr_v: float,
    g_roi_v: float,
    md: dict[str, Any],
    mv: dict[str, Any],
    dim_name: str,
    dim_key: str,
) -> tuple[str, str]:
    nd, nv = int(md["n"]), int(mv["n"])
    if "unknown_or_invalid_odds" in dim_key:
        return "neutro", "odds_invalid_dimension"
    if nd < MIN_N_DISCOVERY or nv < MIN_N_VALIDATION:
        return "fragil", f"n_insuficiente_d{nd}_v{nv}"
    hrd, roid = md.get("hit_rate"), md.get("roi_flat_stake_1u")
    hrv, roiv = mv.get("hit_rate"), mv.get("roi_flat_stake_1u")
    if hrd is None or roid is None or hrv is None or roiv is None:
        return "neutro", "metricas_incompletas"

    if dim_name == "market_x_odds" and nd < MIN_N_MARKET_X_ODDS:
        return "neutro", f"market_x_odds_n_disc_{nd}_lt_{MIN_N_MARKET_X_ODDS}"

    prom_hr = hrd >= g_hr_d + MIN_HR_DELTA_VS_GLOBAL
    prom_roi = roid >= g_roi_d + MIN_ROI_DELTA_VS_GLOBAL
    if not (prom_hr or prom_roi):
        return "neutro", "sin_mejora_material_vs_global_discovery"

    if hrv < hrd - FRAGILE_HR_DROP or roiv < roid - FRAGILE_ROI_DROP:
        return "fragil", "caida_fuerte_discovery_a_validation"

    if hrv < g_hr_v - 0.03 and hrd > g_hr_d + 0.05:
        return "fragil", "validation_por_debajo_global_validation"

    if hrv >= hrd - MAX_HR_DROP_DISC_TO_VAL and roiv >= roid - MAX_ROI_DROP_DISC_TO_VAL:
        return "prometedor", "mejora_discovery_estable_en_validation"

    return "neutro", "estabilidad_limite"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out-dir",
        default=str(_REPO / "scripts/outputs/bt2_phase4_discovery_validation"),
    )
    ap.add_argument(
        "--day-from",
        default=None,
        metavar="YYYY-MM-DD",
        help="Opcional: límite inferior operating_day_key (inclusive). Por defecto, todo el histórico disponible.",
    )
    ap.add_argument(
        "--day-to",
        default=None,
        metavar="YYYY-MM-DD",
        help="Opcional: límite superior operating_day_key (inclusive). Por defecto, todo el histórico disponible.",
    )
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    conn = psycopg2.connect(_dsn())
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    scan = fetch_bd_universe_scan(cur)
    (out / "bd_universe_scan.json").write_text(
        json.dumps(scan, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    rows = fetch_rows(cur, args.day_from, args.day_to)
    cur.close()
    conn.close()

    if not rows:
        print("Sin filas scored con odds; abortar.", file=sys.stderr)
        return 2

    days_sorted = sorted({r["operating_day_key"] for r in rows})
    k = len(days_sorted)
    split_n = (k + 1) // 2
    disc_days = set(days_sorted[:split_n])
    val_days = set(days_sorted[split_n:])

    def subset(day_set: set[str]) -> list[dict[str, Any]]:
        return [r for r in rows if r["operating_day_key"] in day_set]

    r_disc = subset(disc_days)
    r_val = subset(val_days)

    def global_metrics(rs: list[dict[str, Any]]) -> dict[str, Any]:
        a = Agg()
        for r in rs:
            a.add(bool(r["is_hit"]), r.get("reference_decimal_odds"))
        return a.metrics()

    g_d = global_metrics(r_disc)
    g_v = global_metrics(r_val)

    day_window: dict[str, Any] = {}
    if args.day_from or args.day_to:
        day_window = {"day_from": args.day_from, "day_to": args.day_to}

    methodology = {
        "version": "phase4_discovery_validation_v1",
        "optional_day_filter": day_window or None,
        "segment_dims": list(SEGMENT_DIMS),
        "market_x_odds_min_n_discovery": MIN_N_MARKET_X_ODDS,
        "min_n_discovery": MIN_N_DISCOVERY,
        "min_n_validation": MIN_N_VALIDATION,
        "min_hr_delta_vs_global_discovery": MIN_HR_DELTA_VS_GLOBAL,
        "min_roi_delta_vs_global_discovery": MIN_ROI_DELTA_VS_GLOBAL,
        "max_hr_drop_disc_to_val_stable": MAX_HR_DROP_DISC_TO_VAL,
        "max_roi_drop_disc_to_val_stable": MAX_ROI_DROP_DISC_TO_VAL,
        "fragile_hr_drop": FRAGILE_HR_DROP,
        "fragile_roi_drop": FRAGILE_ROI_DROP,
        "split_rule_es": (
            f"Días únicos con datos (K={k}): orden ASC; discovery = primeros ceil(K/2)={split_n} días "
            f"{sorted(disc_days)}; validation = resto {sorted(val_days)}."
        ),
        "anti_tuning_es": ANTI_TUNING_ES,
        "universe_note_es": (
            "Universo = picks con evaluated_hit/miss y reference_decimal_odds > 1. "
            "Amplía con backfill fuera de este script si hace falta más historia."
        ),
    }
    (out / "methodology.json").write_text(
        json.dumps(methodology, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    g_hr_d = float(g_d["hit_rate"] or 0)
    g_roi_d = float(g_d["roi_flat_stake_1u"] or 0)
    g_hr_v = float(g_v["hit_rate"] or 0)
    g_roi_v = float(g_v["roi_flat_stake_1u"] or 0)

    # agregar por dimensión:valor
    from collections import defaultdict as dd

    buckets_d: dict[str, dict[str, Agg]] = dd(lambda: dd(Agg))
    buckets_v: dict[str, dict[str, Agg]] = dd(lambda: dd(Agg))

    for r in r_disc:
        sks = segment_keys(r)
        for dim in list(SEGMENT_DIMS) + ["market_x_odds"]:
            buckets_d[dim][sks[dim]].add(bool(r["is_hit"]), r.get("reference_decimal_odds"))
    for r in r_val:
        sks = segment_keys(r)
        for dim in list(SEGMENT_DIMS) + ["market_x_odds"]:
            buckets_v[dim][sks[dim]].add(bool(r["is_hit"]), r.get("reference_decimal_odds"))

    verdict_rows: list[dict[str, Any]] = []
    for dim in list(SEGMENT_DIMS) + ["market_x_odds"]:
        keys = set(buckets_d[dim].keys()) | set(buckets_v[dim].keys())
        for key in sorted(keys):
            md = buckets_d[dim][key].metrics()
            mv = buckets_v[dim][key].metrics()
            seg = f"{dim}:{key}"
            v, reason = verdict(
                g_hr_d=g_hr_d,
                g_roi_d=g_roi_d,
                g_hr_v=g_hr_v,
                g_roi_v=g_roi_v,
                md=md,
                mv=mv,
                dim_name=dim,
                dim_key=key,
            )
            verdict_rows.append(
                {
                    "segment": seg,
                    "verdict": v,
                    "reason": reason,
                    "discovery": md,
                    "validation": mv,
                }
            )

    summary = {
        "total_rows_scored_with_odds": len(rows),
        "unique_days": days_sorted,
        "discovery_days": sorted(disc_days),
        "validation_days": sorted(val_days),
        "global_discovery": g_d,
        "global_validation": g_v,
        "verdict_counts": {
            "prometedor": sum(1 for x in verdict_rows if x["verdict"] == "prometedor"),
            "neutro": sum(1 for x in verdict_rows if x["verdict"] == "neutro"),
            "fragil": sum(1 for x in verdict_rows if x["verdict"] == "fragil"),
        },
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    flat: list[dict[str, Any]] = []
    for x in verdict_rows:
        flat.append(
            {
                "segment": x["segment"],
                "verdict": x["verdict"],
                "reason": x["reason"],
                "n_disc": x["discovery"]["n"],
                "hit_rate_disc": x["discovery"]["hit_rate"],
                "roi_disc": x["discovery"]["roi_flat_stake_1u"],
                "n_val": x["validation"]["n"],
                "hit_rate_val": x["validation"]["hit_rate"],
                "roi_val": x["validation"]["roi_flat_stake_1u"],
            }
        )
    with (out / "segments_verdict.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(flat[0].keys()))
        w.writeheader()
        w.writerows(flat)

    readme = f"""# Discovery / validation — Fase 4

## Metodología

Ver `methodology.json` (parámetros congelados en código del script).

## Universo de esta corrida

- Filas: **{len(rows)}** (scored + `reference_decimal_odds` > 1)
- Días: **{days_sorted}**
- Discovery días: {sorted(disc_days)}
- Validation días: {sorted(val_days)}

## Evidencia BD (read-only)

Ver `bd_universe_scan.json`: totales scored / odds en toda la BD vs esta corrida.

## Cómo regenerar

```bash
cd {_REPO}
PYTHONPATH=. python3 scripts/bt2_phase4_discovery_validation_audit.py \\
  --out-dir scripts/outputs/bt2_phase4_discovery_validation_expanded
```
"""
    (out / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Fase 4 — primer corte: selective release / edge audit (read-only).

- Une bt2_daily_picks + bt2_pick_official_evaluation + tier de liga.
- Solo picks con evaluación oficial scored (hit/miss), sin leakage ex-post
  (no usa resultado ni etiquetas posteriores al pick salvo lo ya persistido en dp/eval).
- Métricas: hit rate, odds promedio (reference_decimal_odds ex-ante), break-even implícito
  medio (1/odds), ROI proxy stake=1 unidad por pick scored con odds conocidas.
- Estabilidad: dos bloques por operating_day_key (split configurable).

Salida por defecto:
  scripts/outputs/bt2_phase4_edge_audit/summary.json
  scripts/outputs/bt2_phase4_edge_audit/segments.csv
  scripts/outputs/bt2_phase4_edge_audit/README.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Any, Optional

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import psycopg2
import psycopg2.extras

from apps.api.bt2_settings import bt2_settings


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


def completeness_band(dcs: Optional[int]) -> str:
    if dcs is None:
        return "dcs_unknown"
    if dcs < 50:
        return "dcs_lt_50"
    if dcs < 75:
        return "dcs_50_74"
    return "dcs_ge_75"


def conf_band(c: Optional[str]) -> str:
    s = (c or "").strip().lower()
    if s in ("high", "medium", "low"):
        return f"conf_{s}"
    return "conf_other_or_empty"


def profit_flat_stake(hit: bool, odds: Optional[float]) -> Optional[float]:
    if odds is None or odds <= 1.0:
        return None
    return float(odds) - 1.0 if hit else -1.0


def break_even_rate(odds: Optional[float]) -> Optional[float]:
    if odds is None or odds <= 1.0:
        return None
    return 1.0 / float(odds)


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
            self.n_be += 1
            p = profit_flat_stake(hit, fo)
            if p is not None:
                self.sum_profit += p
                self.n_profit += 1

    def metrics(self) -> dict[str, Any]:
        scored = self.hits + self.misses
        hr = self.hits / scored if scored else None
        avg_o = self.sum_odds / self.n_odds if self.n_odds else None
        avg_be = self.sum_be / self.n_be if self.n_be else None
        roi = self.sum_profit / self.n_profit if self.n_profit else None
        return {
            "n": self.n,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hr, 4) if hr is not None else None,
            "avg_decimal_odds": round(avg_o, 4) if avg_o is not None else None,
            "avg_implied_break_even_rate": round(avg_be, 4) if avg_be is not None else None,
            "roi_flat_stake_1u": round(roi, 4) if roi is not None else None,
            "n_with_odds_for_roi": self.n_profit,
        }


def fetch_rows(cur, date_from: str, date_to: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            dp.id AS daily_pick_id,
            dp.operating_day_key::text AS operating_day_key,
            COALESCE(NULLIF(TRIM(dp.model_market_canonical), ''), '(vacío)') AS market_canonical,
            dp.reference_decimal_odds::float AS reference_decimal_odds,
            dp.data_completeness_score::int AS data_completeness_score,
            COALESCE(NULLIF(TRIM(dp.dsr_confidence_label), ''), '') AS dsr_confidence_label,
            dp.slate_rank::int AS slate_rank,
            e.evaluation_status::text AS evaluation_status,
            COALESCE(NULLIF(TRIM(UPPER(l.tier)), ''), 'UNK') AS league_tier
        FROM bt2_daily_picks dp
        INNER JOIN bt2_pick_official_evaluation e ON e.daily_pick_id = dp.id
        INNER JOIN bt2_events ev ON ev.id = dp.event_id
        LEFT JOIN bt2_leagues l ON l.id = ev.league_id
        WHERE dp.operating_day_key >= %s
          AND dp.operating_day_key <= %s
          AND e.evaluation_status IN ('evaluated_hit', 'evaluated_miss')
        ORDER BY dp.operating_day_key, dp.id
        """,
        (date_from, date_to),
    )
    return [dict(r) for r in cur.fetchall()]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date-from", default="2026-04-13")
    p.add_argument("--date-to", default="2026-04-20")
    p.add_argument(
        "--split-day",
        default="2026-04-19",
        help="Días < split → bloque A; días >= split → bloque B (estabilidad).",
    )
    p.add_argument("--min-segment-n", type=int, default=5)
    p.add_argument("--small-sample-n", type=int, default=10)
    p.add_argument(
        "--out-dir",
        default=str(_REPO / "scripts/outputs/bt2_phase4_edge_audit"),
    )
    args = p.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = psycopg2.connect(_dsn())
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    rows = fetch_rows(cur, args.date_from, args.date_to)
    cur.close()
    conn.close()

    split_day = args.split_day

    def block_key(odk: str) -> str:
        return "A" if odk < split_day else "B"

    global_a = Agg()
    global_b = Agg()
    global_all = Agg()

    # segment -> block -> Agg
    seg_block: dict[str, dict[str, Agg]] = defaultdict(lambda: defaultdict(Agg))

    def seg_keys(r: dict[str, Any]) -> dict[str, str]:
        hit = r["evaluation_status"] == "evaluated_hit"
        odds = r.get("reference_decimal_odds")
        return {
            "market": str(r.get("market_canonical") or "(vacío)"),
            "odds_band": odds_band(odds),
            "league_tier": str(r.get("league_tier") or "UNK"),
            "completeness_band": completeness_band(r.get("data_completeness_score")),
            "confidence_band": conf_band(r.get("dsr_confidence_label")),
            "market_x_odds": f"{r.get('market_canonical') or '(vacío)'}|{odds_band(odds)}",
        }

    for r in rows:
        hit = r["evaluation_status"] == "evaluated_hit"
        odds = r.get("reference_decimal_odds")
        odk = str(r["operating_day_key"])
        bk = block_key(odk)
        global_all.add(hit, odds)
        (global_a if bk == "A" else global_b).add(hit, odds)
        for dim, sk in seg_keys(r).items():
            seg_block[f"{dim}:{sk}"][bk].add(hit, odds)

    g = global_all.metrics()
    ga = global_a.metrics()
    gb = global_b.metrics()
    n_missing_odds = sum(
        1
        for r in rows
        if r.get("reference_decimal_odds") is None or float(r["reference_decimal_odds"]) <= 1.0
    )

    def stability_note() -> str:
        if ga["n"] < 8 or gb["n"] < 8:
            return "bloques_A_B_muestra_pequeña"
        hra, hrb = ga.get("hit_rate"), gb.get("hit_rate")
        if hra is None or hrb is None:
            return "sin_hit_rate"
        d = abs(hra - hrb)
        if d >= 0.20:
            return f"fragil_delta_hit_rate_{round(d,3)}"
        return "delta_hit_rate_moderado"

    segment_rows: list[dict[str, Any]] = []
    for seg_name, blocks in sorted(seg_block.items()):
        a = blocks["A"]
        b = blocks["B"]
        t = Agg()
        for x in (a, b):
            t.n += x.n
            t.hits += x.hits
            t.misses += x.misses
            t.sum_odds += x.sum_odds
            t.n_odds += x.n_odds
            t.sum_be += x.sum_be
            t.n_be += x.n_be
            t.sum_profit += x.sum_profit
            t.n_profit += x.n_profit
        m = t.metrics()
        ma, mb = a.metrics(), b.metrics()
        small = t.n < int(args.small_sample_n)
        below_min = t.n < int(args.min_segment_n)
        hra, hrb = ma.get("hit_rate"), mb.get("hit_rate")
        delta = (
            abs((hra or 0) - (hrb or 0)) if hra is not None and hrb is not None and ma["n"] and mb["n"] else None
        )
        segment_rows.append(
            {
                "segment": seg_name,
                "n": m["n"],
                "hit_rate": m["hit_rate"],
                "avg_decimal_odds": m["avg_decimal_odds"],
                "avg_implied_break_even_rate": m["avg_implied_break_even_rate"],
                "roi_flat_stake_1u": m["roi_flat_stake_1u"],
                "hit_rate_block_A": ma.get("hit_rate"),
                "n_block_A": ma["n"],
                "hit_rate_block_B": mb.get("hit_rate"),
                "n_block_B": mb["n"],
                "hit_rate_delta_AB": round(delta, 4) if delta is not None else None,
                "flag_small_sample": small,
                "flag_below_min_segment_n": below_min,
            }
        )

    segment_rows.sort(key=lambda x: (-(x["n"] or 0), x["segment"]))

    summary = {
        "window": {"date_from": args.date_from, "date_to": args.date_to},
        "split_day": split_day,
        "methodology_es": (
            "Solo evaluated_hit / evaluated_miss. Hit rate = hits/(hits+misses). "
            "Odds = reference_decimal_odds en pick (ex-ante). Break-even implícito por pick = 1/odds "
            "(tasa mínima de acierto para EV=0 con stake 1 y pago decimal). "
            "ROI proxy = media de (odds-1) si hit, -1 si miss, solo filas con odds>1. "
            f"Bloque A: operating_day_key < {split_day}; B: >= {split_day}. "
            "No se usan features del resultado del partido ni columnas posteriores al pick salvo evaluación ya materializada."
        ),
        "caution_flags": [
            f"N global scored = {g['n']} — inferencia segmentada limitada.",
            f"Picks scored sin reference_decimal_odds usable: {n_missing_odds}/{g['n']} — ROI/odds medios solo sobre subconjunto con cuota.",
            "estimated_hit_probability / evidence_quality son ex-ante pero pueden estar calibrados débilmente; no usados en este primer corte salvo confianza explícita.",
        ],
        "global": {
            **g,
            "n_missing_reference_odds": n_missing_odds,
            "stability_note": stability_note(),
            "block_A": ga,
            "block_B": gb,
        },
        "best_candidates": [],
        "small_or_fragile": [],
    }

    # Heurística simple: entre segmentos con n>=min_segment_n y no small_sample, buscar hit_rate y roi por encima del global
    g_hr = g.get("hit_rate") or 0.0
    g_roi = g.get("roi_flat_stake_1u")
    for r in segment_rows:
        if r["flag_below_min_segment_n"]:
            summary["small_or_fragile"].append(
                {"segment": r["segment"], "reason": "n_lt_min_segment", "n": r["n"]}
            )
            continue
        if r["flag_small_sample"]:
            summary["small_or_fragile"].append(
                {"segment": r["segment"], "reason": "n_lt_small_sample_threshold", "n": r["n"]}
            )
        hr, roi = r.get("hit_rate"), r.get("roi_flat_stake_1u")
        if "unknown_or_invalid_odds" in r["segment"]:
            continue
        better_hr = hr is not None and hr > g_hr + 0.05
        better_roi = (
            roi is not None
            and g_roi is not None
            and roi > g_roi + 0.05
            or (roi is not None and g_roi is None and roi > 0)
        )
        fragile = (r.get("hit_rate_delta_AB") or 0) >= 0.25
        if (better_hr or better_roi) and not fragile:
            summary["best_candidates"].append(
                {
                    "segment": r["segment"],
                    "n": r["n"],
                    "hit_rate": hr,
                    "roi_flat_stake_1u": roi,
                    "rationale": "mejor_hit_o_roi_vs_global_sin_delta_AB_extremo",
                }
            )
        elif fragile and r["n"] >= args.min_segment_n:
            summary["small_or_fragile"].append(
                {"segment": r["segment"], "reason": "delta_hit_rate_AB_alto", "detail": r}
            )

    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    with (out_dir / "segments.csv").open("w", newline="", encoding="utf-8") as f:
        if segment_rows:
            w = csv.DictWriter(f, fieldnames=list(segment_rows[0].keys()))
            w.writeheader()
            w.writerows(segment_rows)

    readme = f"""# BT2 Fase 4 — edge audit (primer corte)

Ventana: **{args.date_from}** → **{args.date_to}** (evaluación oficial scored).

Archivos:
- `summary.json` — global, bloques A/B, candidatos “mejor que global” heurísticos.
- `segments.csv` — una fila por dimensión:valor de segmento.

Regenerar:

```bash
cd {_REPO}
PYTHONPATH=. python3 scripts/bt2_phase4_selective_release_edge_audit.py \\
  --date-from {args.date_from} --date-to {args.date_to} --split-day {split_day}
```

N global scored (esta corrida): **{g["n"]}**.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps({"output_dir": str(out_dir), "global": g, "stability": stability_note()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

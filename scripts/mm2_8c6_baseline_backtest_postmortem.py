#!/usr/bin/env python3
"""
MM-2.8C.6 — Baseline backtest post-mortem + failure segmentation (artifact-only).

Reads MM-2.8C.5 outputs under scripts/outputs. No APIs, no DSR, no DB writes.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "scripts" / "outputs"
AUD = ROOT / "docs" / "bettracker2" / "audits"
PREFIX = "mm2_8c5"
OUT6 = "mm2_8c6"

# Minimum exploratory sample for rescuable segment
MIN_RESCUE_PICKS = 8
CONFIDENCE_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def build_stage1_index(stage1: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in stage1.get("parsed_outputs", []):
        eid = str(rec.get("event_id") or "")
        parsed = rec.get("parsed") or {}
        for mo in (parsed.get("market_outputs") or []):
            mk = str(mo.get("market_canonical") or "")
            out[(eid, mk)] = mo
    return out


def outcome_relation_label(bucket: str, bench_rel: str) -> str:
    b = bucket or ""
    if b == "both_win":
        return "both_win"
    if b == "both_lose":
        return "both_lose"
    if b == "dsr_wins_benchmark_loses":
        return "DSR_wins_while_benchmark_loses"
    if b == "dsr_loses_benchmark_wins":
        return "DSR_loses_while_benchmark_wins"
    return b or "unknown"


def follow_oppose_label(bench_rel: str) -> str:
    if bench_rel == "matches_benchmark":
        return "DSR_follows_benchmark"
    if bench_rel == "opposes_benchmark":
        return "DSR_opposes_benchmark"
    return "DSR_no_benchmark_relation"


def odds_band_norm(d: float) -> str:
    if d < 1.50:
        return "1.30-1.49"
    if d < 1.80:
        return "1.50-1.79"
    if d < 2.20:
        return "1.80-2.19"
    return "2.20+"


def confidence_meets_medium(cc: str | None) -> bool:
    return CONFIDENCE_ORDER.get(str(cc or "none").lower(), 0) >= CONFIDENCE_ORDER["medium"]


def slice_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {
            "picks_kept": 0,
            "wins": 0,
            "losses": 0,
            "hit_rate": None,
            "profit": 0.0,
            "ROI": None,
            "benchmark_profit": 0.0,
            "benchmark_ROI": None,
            "delta_profit_dsr_minus_benchmark": 0.0,
            "delta_ROI": None,
        }
    wins = sum(1 for r in rows if str(r.get("dsr_settlement_status") or r.get("settlement_status")) == "win")
    losses = n - wins
    def pick_profit(x: dict[str, Any]) -> float:
        v = x.get("dsr_profit")
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return safe_float(x.get("profit"))
        return safe_float(v)

    d_profit = sum(pick_profit(x) for x in rows)
    b_profit = sum(safe_float(x.get("benchmark_profit")) for x in rows)
    hr = wins / n
    roi = d_profit / n
    broi = b_profit / n
    return {
        "picks_kept": n,
        "wins": wins,
        "losses": losses,
        "hit_rate": round(hr, 6),
        "profit": round(d_profit, 6),
        "ROI": round(roi, 6),
        "benchmark_profit": round(b_profit, 6),
        "benchmark_ROI": round(broi, 6),
        "delta_profit_dsr_minus_benchmark": round(d_profit - b_profit, 6),
        "delta_ROI": round(roi - broi, 6),
    }


def attribute_failure(row: dict[str, Any], league_roi: dict[str, float], band_roi: dict[str, float]) -> str:
    won = str(row.get("dsr_settlement_status") or row.get("dsr_result") or row.get("settlement_status")) == "win"
    if won:
        return "n_a_pick_won"
    bucket = str(row.get("comparison_bucket") or "")
    rel = str(row.get("benchmark_relation") or "")
    mr = str(row.get("market_relation") or "")
    po = safe_float(row.get("dsr_pick_odds"), safe_float(row.get("pick_odds")))
    league = str(row.get("league") or "")
    mkt = str(row.get("market_canonical") or "")
    pub = str(row.get("publishability_status") or "")
    nmc = row.get("non_market_signal_count")
    try:
        nmc_i = int(nmc) if nmc is not None and str(nmc).strip() != "" else -1
    except (TypeError, ValueError):
        nmc_i = -1

    if bucket == "dsr_loses_benchmark_wins" and rel == "opposes_benchmark":
        return "opposed_good_benchmark"
    if bucket == "both_lose" and rel == "matches_benchmark":
        return "followed_bad_benchmark"
    if po > 0 and po < 1.50:
        return "low_odds_no_value"
    if mr in ("context_opposes_market", "strong_tension"):
        return "overtrusted_context"
    if 0 <= nmc_i < 2:
        return "weak_signal_accepted"
    if mr in ("market_only", "weak_tension"):
        return "market_only_or_near_market_only"
    if mkt == "OU_GOALS_2_5":
        return "ou25_line_noise"
    if league and league_roi.get(league, 0) < -0.15:
        return "league_specific_failure"
    band = str(row.get("odds_band_normalized") or row.get("odds_band") or "")
    broi = band_roi.get(band)
    if broi is None and band == "2.20+":
        broi = band_roi.get(">2.20")
    if band and broi is not None and broi < -0.15:
        return "odds_band_failure"
    if pub == "candidate_publishable_shadow" and mr == "context_reinforces_market" and po > 0 and po < 1.60:
        return "normalizer_too_permissive"
    return "unclear"


def main() -> None:
    req = [
        OUT / f"{PREFIX}_summary.json",
        OUT / f"{PREFIX}_behavior_summary.json",
        OUT / f"{PREFIX}_normalized_final_outputs.json",
        OUT / f"{PREFIX}_pick_level_rows.csv",
        OUT / f"{PREFIX}_settlement_summary.json",
        OUT / f"{PREFIX}_settlement_pick_rows.csv",
        OUT / f"{PREFIX}_performance_by_market.csv",
        OUT / f"{PREFIX}_performance_by_league.csv",
        OUT / f"{PREFIX}_performance_by_odds_band.csv",
        OUT / f"{PREFIX}_benchmark_comparison.csv",
        OUT / f"{PREFIX}_stage1_dsr_parsed_outputs.json",
        OUT / f"{PREFIX}_stage2_dsr_parsed_outputs.json",
        OUT / f"{PREFIX}_schema_validation.json",
        OUT / f"{PREFIX}_latency_rows.csv",
    ]
    missing = [str(p) for p in req if not p.exists()]
    if missing:
        print(json.dumps({"error": "missing_mm2_8c5_artifacts", "missing": missing}, indent=2))
        sys.exit(1)

    s5 = read_json(OUT / f"{PREFIX}_summary.json")
    behavior = read_json(OUT / f"{PREFIX}_behavior_summary.json")
    settlement_sum = read_json(OUT / f"{PREFIX}_settlement_summary.json")
    schema_val = read_json(OUT / f"{PREFIX}_schema_validation.json")
    stage1 = read_json(OUT / f"{PREFIX}_stage1_dsr_parsed_outputs.json")
    s1_index = build_stage1_index(stage1)

    bc_rows = read_csv_rows(OUT / f"{PREFIX}_benchmark_comparison.csv")
    sp_rows = read_csv_rows(OUT / f"{PREFIX}_settlement_pick_rows.csv")
    sp_by_key = {(str(r["event_id"]), str(r["market_canonical"])): r for r in sp_rows}

    perf_league = read_csv_rows(OUT / f"{PREFIX}_performance_by_league.csv")
    league_roi = {str(r["league"]): safe_float(r.get("ROI")) for r in perf_league}
    perf_band = read_csv_rows(OUT / f"{PREFIX}_performance_by_odds_band.csv")
    band_roi: dict[str, float] = {}
    for r in perf_band:
        b = str(r.get("odds_band") or r.get("band") or "")
        band_roi[b] = safe_float(r.get("ROI"))
    if ">2.20" in band_roi and "2.20+" not in band_roi:
        band_roi["2.20+"] = band_roi[">2.20"]

    # Enriched pick rows (one row per pick) — primary spine: benchmark_comparison + settlement join
    pick_rows: list[dict[str, Any]] = []
    for b in bc_rows:
        eid = str(b["event_id"])
        mkt = str(b["market_canonical"])
        sp = sp_by_key.get((eid, mkt), {})
        s1m = s1_index.get((eid, mkt), {})
        nmc = s1m.get("non_market_signal_count")
        sigs = s1m.get("signal_summary") or []
        supported_n = len(sigs) if isinstance(sigs, list) else 0
        po = safe_float(b.get("dsr_pick_odds"))
        row: dict[str, Any] = {
            **b,
            "league": sp.get("league", ""),
            "kickoff_utc": sp.get("kickoff_utc", ""),
            "context_confidence": sp.get("context_confidence", ""),
            "rationale_short_es": sp.get("rationale_short_es", ""),
            "non_market_signal_count": nmc if nmc is not None else "",
            "supported_signal_count": supported_n,
            "rationale_char_len": len(str(sp.get("rationale_short_es") or "")),
            "dsr_pick": b.get("dsr_selection", ""),
            "benchmark_pick": b.get("benchmark_selection", ""),
            "dsr_result": b.get("dsr_settlement_status", ""),
            "benchmark_result": b.get("benchmark_settlement_status", ""),
            "dsr_profit": b.get("dsr_profit", ""),
            "benchmark_profit": b.get("benchmark_profit", ""),
            "delta_profit": b.get("profit_delta_dsr_minus_benchmark", ""),
            "relation_outcome": outcome_relation_label(str(b.get("comparison_bucket") or ""), str(b.get("benchmark_relation") or "")),
            "relation_follow_oppose": follow_oppose_label(str(b.get("benchmark_relation") or "")),
            "odds_band_normalized": odds_band_norm(po) if po else str(b.get("odds_band") or ""),
        }
        dp = safe_float(row.get("delta_profit"))
        row["model_helped"] = dp > 0
        row["model_hurt"] = dp < 0
        row["model_same_as_benchmark"] = str(b.get("benchmark_relation")) == "matches_benchmark"
        row["model_opposed_benchmark"] = str(b.get("benchmark_relation")) == "opposes_benchmark"
        row["relation_label"] = f"{row['relation_follow_oppose']}|{row['relation_outcome']}"
        pick_rows.append(row)

    for r in pick_rows:
        r["primary_failure_attribution"] = attribute_failure(
            {**r, "pick_odds": r.get("dsr_pick_odds"), "settlement_status": r.get("dsr_result")},
            league_roi,
            band_roi,
        )

    pv_fields = [
        "event_id",
        "market_canonical",
        "league",
        "odds_band",
        "odds_band_normalized",
        "dsr_pick",
        "benchmark_pick",
        "dsr_result",
        "benchmark_result",
        "dsr_profit",
        "benchmark_profit",
        "delta_profit",
        "model_helped",
        "model_hurt",
        "model_same_as_benchmark",
        "model_opposed_benchmark",
        "relation_label",
        "relation_follow_oppose",
        "relation_outcome",
        "publishability_status",
        "market_relation",
        "context_confidence",
        "non_market_signal_count",
        "supported_signal_count",
        "rationale_char_len",
        "comparison_bucket",
        "benchmark_relation",
        "primary_failure_attribution",
    ]
    write_csv(OUT / f"{OUT6}_pick_vs_benchmark_rows.csv", pick_rows, pv_fields)

    fa_fields = [
        "event_id",
        "market_canonical",
        "league",
        "dsr_settlement_status",
        "benchmark_settlement_status",
        "comparison_bucket",
        "benchmark_relation",
        "market_relation",
        "publishability_status",
        "dsr_pick_odds",
        "odds_band",
        "non_market_signal_count",
        "supported_signal_count",
        "context_confidence",
        "primary_failure_attribution",
        "delta_profit",
    ]
    write_csv(OUT / f"{OUT6}_failure_attribution_rows.csv", pick_rows, fa_fields)

    # --- Gate simulation ---
    base = pick_rows

    def as_row_for_slice(r: dict[str, Any]) -> dict[str, Any]:
        return {
            **r,
            "profit": r.get("dsr_profit"),
            "settlement_status": r.get("dsr_settlement_status"),
        }

    gates: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
        ("only_OU_GOALS_2_5", lambda r: r["market_canonical"] == "OU_GOALS_2_5"),
        ("only_FT_1X2", lambda r: r["market_canonical"] == "FT_1X2"),
        ("exclude_odds_lt_1_50", lambda r: safe_float(r.get("dsr_pick_odds")) >= 1.50),
        ("exclude_odds_lt_1_60", lambda r: safe_float(r.get("dsr_pick_odds")) >= 1.60),
        ("exclude_weak_tension", lambda r: str(r.get("market_relation")) != "weak_tension"),
        ("exclude_candidate_publishable_shadow_tier", lambda r: str(r.get("publishability_status")) != "candidate_publishable_shadow"),
        ("only_context_opposes_market", lambda r: str(r.get("market_relation")) == "context_opposes_market"),
        ("only_DSR_opposes_benchmark", lambda r: str(r.get("benchmark_relation")) == "opposes_benchmark"),
        ("only_DSR_follows_benchmark", lambda r: str(r.get("benchmark_relation")) == "matches_benchmark"),
        ("non_market_signal_count_ge_2", lambda r: isinstance(r.get("non_market_signal_count"), int) and r["non_market_signal_count"] >= 2
        or (str(r.get("non_market_signal_count")).isdigit() and int(r["non_market_signal_count"]) >= 2)),
        ("confidence_ge_medium", lambda r: confidence_meets_medium(str(r.get("context_confidence")))),
    ]

    positive_leagues = {lg for lg, roi in league_roi.items() if roi > 0}
    positive_markets = {
        str(r["market_canonical"])
        for r in read_csv_rows(OUT / f"{PREFIX}_performance_by_market.csv")
        if safe_float(r.get("ROI")) > 0
    }

    gates.append(
        (
            "only_leagues_positive_ROI_in_sample",
            lambda r, pl=positive_leagues: str(r.get("league")) in pl,
        )
    )
    gates.append(
        (
            "only_markets_positive_ROI_in_sample",
            lambda r, pm=positive_markets: str(r.get("market_canonical")) in pm,
        )
    )

    gate_rows: list[dict[str, Any]] = []
    for name, pred in gates:
        fil = [r for r in base if pred(r)]
        m = slice_metrics(fil)
        warn = ""
        if name.startswith("only_leagues") or name.startswith("only_markets"):
            warn = "in_sample_selection_bias_risk"
        if m["picks_kept"] < MIN_RESCUE_PICKS:
            warn = (warn + "; " if warn else "") + "small_sample"
        gate_rows.append(
            {
                "gate_name": name,
                "sample_size_warning": warn.strip("; ") or "none",
                **m,
            }
        )

    # Combined gates (examples)
    combo = [
        (
            "OU_only_and_odds_ge_1_60",
            lambda r: r["market_canonical"] == "OU_GOALS_2_5" and safe_float(r.get("dsr_pick_odds")) >= 1.60,
        ),
        (
            "FT_only_and_exclude_weak_tension",
            lambda r: r["market_canonical"] == "FT_1X2" and str(r.get("market_relation")) != "weak_tension",
        ),
        (
            "opposes_benchmark_and_conf_ge_medium",
            lambda r: str(r.get("benchmark_relation")) == "opposes_benchmark" and confidence_meets_medium(str(r.get("context_confidence"))),
        ),
    ]
    for name, pred in combo:
        fil = [r for r in base if pred(r)]
        m = slice_metrics(fil)
        warn = "small_sample" if m["picks_kept"] < MIN_RESCUE_PICKS else "none"
        gate_rows.append({"gate_name": name, "sample_size_warning": warn, **m})

    write_csv(
        OUT / f"{OUT6}_gate_simulation_rows.csv",
        gate_rows,
        [
            "gate_name",
            "picks_kept",
            "wins",
            "losses",
            "hit_rate",
            "profit",
            "ROI",
            "benchmark_profit",
            "benchmark_ROI",
            "delta_profit_dsr_minus_benchmark",
            "delta_ROI",
            "sample_size_warning",
        ],
    )

    # --- Rescuable segments ---
    def segment_key_dimensions(r: dict[str, Any]) -> dict[str, str]:
        return {
            "market": str(r.get("market_canonical")),
            "league": str(r.get("league")),
            "odds_band": str(r.get("odds_band_normalized") or r.get("odds_band")),
            "publishability": str(r.get("publishability_status")),
            "market_relation": str(r.get("market_relation")),
            "follow_oppose": str(r.get("relation_follow_oppose")),
        }

    segments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in pick_rows:
        sk = segment_key_dimensions(r)
        for k, v in sk.items():
            segments[f"{k}:{v}"].append(r)
        segments[f"market|league:{sk['market']}|{sk['league']}"].append(r)

    rescuable: list[dict[str, Any]] = []
    for seg_name, rows in segments.items():
        if len(rows) < MIN_RESCUE_PICKS:
            continue
        m = slice_metrics(rows)
        if m["ROI"] is None:
            continue
        broi = m["benchmark_ROI"] or 0
        droi = m["ROI"] or 0
        delta_roi = (m["delta_ROI"] or 0) if m.get("delta_ROI") is not None else droi - broi
        hindsight = "in_sample_slice_only"
        meets = (
            len(rows) >= MIN_RESCUE_PICKS
            and (droi > 0)
            and (delta_roi > 0 or m["delta_profit_dsr_minus_benchmark"] > 0)
        )
        operational = (
            f"Segment `{seg_name}` shows positive ROI and beats benchmark on this historical slice; "
            "requires held-out validation before any routing."
        )
        rescuable.append(
            {
                "segment": seg_name,
                "picks": len(rows),
                "DSR_ROI": m["ROI"],
                "benchmark_ROI": m["benchmark_ROI"],
                "delta_ROI": m["delta_ROI"],
                "delta_profit": m["delta_profit_dsr_minus_benchmark"],
                "candidate_for_validation": meets,
                "hindsight_note": hindsight,
                "operational_explanation": operational if meets else "Does not meet thresholds.",
            }
        )

    rescuable_sorted = sorted(rescuable, key=lambda x: (-int(x["candidate_for_validation"]), -(x.get("delta_ROI") or 0)))

    write_csv(
        OUT / f"{OUT6}_rescuable_segments.csv",
        rescuable_sorted,
        [
            "segment",
            "picks",
            "DSR_ROI",
            "benchmark_ROI",
            "delta_ROI",
            "delta_profit",
            "candidate_for_validation",
            "hindsight_note",
            "operational_explanation",
        ],
    )

    validated_segments = [x for x in rescuable_sorted if x["candidate_for_validation"]]
    rescuable_count = len(validated_segments)

    g_roi = safe_float(s5.get("ROI"))
    gb_roi = safe_float(s5.get("benchmark_ROI"))
    global_beats = g_roi > gb_roi if g_roi is not None and gb_roi is not None else False

    best_seg = None
    worst_seg = None
    big_segs = [x for x in rescuable_sorted if x["picks"] >= MIN_RESCUE_PICKS]
    cand_valid = [x for x in big_segs if x["candidate_for_validation"]]
    if cand_valid:
        best_seg = max(cand_valid, key=lambda x: ((x.get("delta_ROI") or 0), x["picks"]))
    if big_segs:
        worst_seg = min(big_segs, key=lambda x: (x.get("DSR_ROI") if x.get("DSR_ROI") is not None else 0.0, x["picks"]))

    # Decision rules
    continue_reason = []
    if g_roi is not None and g_roi < 0:
        continue_reason.append("global_DSR_ROI_negative")
    if g_roi is not None and gb_roi is not None and g_roi < gb_roi:
        continue_reason.append("DSR_ROI_below_benchmark")
    if rescuable_count == 0:
        continue_reason.append("no_segment_beats_benchmark_with_sufficient_n")

    if rescuable_count >= 1:
        baseline_continue = "conditional"
        pause_note = "Small positive in-sample segments require validation split; do not expand DSR spend."
    elif not global_beats and g_roi is not None and g_roi < 0:
        baseline_continue = "false"
        pause_note = "Pause baseline DSR spend; no robust rescuable slice."
    else:
        baseline_continue = "false"
        pause_note = "No qualifying segment; global underperformance vs benchmark."

    if rescuable_count >= 1 and all(x["picks"] >= 15 for x in validated_segments) and global_beats:
        baseline_continue = "true"

    decision = {
        "generated_at_utc": utc_now(),
        "baseline_dsr_should_continue": baseline_continue == "true",
        "baseline_dsr_should_continue_label": baseline_continue,
        "baseline_dsr_should_continue_conditional": baseline_continue == "conditional",
        "baseline_dsr_should_be_paused": baseline_continue in ("false", "conditional"),
        "reason": "; ".join(continue_reason) if continue_reason else "see_segments",
        "best_segment_if_any": best_seg["segment"] if best_seg else None,
        "worst_segment": worst_seg["segment"] if worst_seg else None,
        "benchmark_beats_dsr": bool(g_roi is not None and gb_roi is not None and gb_roi > g_roi),
        "rescuable_validated_segment_count": rescuable_count,
        "recommended_next_step": pause_note,
    }
    write_json(OUT / f"{OUT6}_baseline_decision.json", decision)

    summary = {
        "generated_at_utc": utc_now(),
        "MM2_8c6_postmortem_completed": True,
        "global_DSR_ROI": s5.get("ROI"),
        "global_benchmark_ROI": s5.get("benchmark_ROI"),
        "DSR_minus_benchmark_profit": s5.get("DSR_minus_benchmark_profit"),
        "best_segment": best_seg["segment"] if best_seg else None,
        "worst_segment": worst_seg["segment"] if worst_seg else None,
        "rescuable_segment_count": rescuable_count,
        "baseline_dsr_should_continue": baseline_continue == "true",
        "baseline_dsr_should_continue_label": baseline_continue,
        "recommended_next_step": pause_note,
        "inputs_prefix": PREFIX,
        "pick_rows_analyzed": len(pick_rows),
    }
    loss_tags = Counter(
        str(r["primary_failure_attribution"])
        for r in pick_rows
        if str(r.get("dsr_settlement_status")) != "win"
    )
    summary["failure_attribution_loss_counts"] = dict(loss_tags.most_common())

    write_json(OUT / f"{OUT6}_summary.json", summary)

    # --- Audit markdown ---
    perf_mkt = read_csv_rows(OUT / f"{PREFIX}_performance_by_market.csv")
    perf_ob = read_csv_rows(OUT / f"{PREFIX}_performance_by_odds_band.csv")
    lat_n = len(read_csv_rows(OUT / f"{PREFIX}_latency_rows.csv"))

    fa_blob = json.dumps(dict(loss_tags.most_common()), indent=2)
    md = f"""# MM-2.8C.6 — Baseline Backtest Post-Mortem

## 1. Executive summary

Post-mortem artifact-only sobre MM-2.8C.5. Objetivo: explicar por qué el baseline DSR perdió frente al benchmark same-slice y detectar segmentos **exploratorios** que merezcan validación fuera de muestra.

**Lectura principal:** la pérdida global viene sobre todo de **OU 2.5** (ROI negativo fuerte frente a FT) y de ligas con cohorte débil, especialmente **Serie A** en esta ventana. El DSR **no añadió edge agregado**: ROI global por debajo del benchmark same-slice. Los picks que **oponen** al benchmark (`diagnostic_only`, relación *opposes*) concentraron parte del delta negativo frente al benchmark de referencia.

- **Picks analizados**: {len(pick_rows)}
- **ROI global DSR / benchmark**: {s5.get("ROI")} / {s5.get("benchmark_ROI")}
- **Profit delta (DSR − benchmark)**: {s5.get("DSR_minus_benchmark_profit")}
- **Segmentos marcados `candidate_for_validation` (reglas MM-2.8C.6)**: {rescuable_count}
- **Mejor segmento exploratorio (in-sample)**: `{best_seg["segment"] if best_seg else "none"}`
- **Peor segmento (n≥{MIN_RESCUE_PICKS})**: `{worst_seg["segment"] if worst_seg else "none"}`
- **Decisión baseline**: `{baseline_continue}` — pausa recomendada: **{decision["baseline_dsr_should_be_paused"]}**

**Atribución heurística (solo pérdidas, conteos):**

```json
{fa_blob}
```

## 2. Scope and restrictions

Solo artefactos bajo `scripts/outputs/mm2_8c5_*`. Sin DSR, sin APIs externas, sin escrituras DB, sin producción, sin nuevos picks ni nuevo settlement (métricas derivadas de salidas MM-2.8C.5).

## 3. MM-2.8C.5 recap

{json.dumps({k: s5.get(k) for k in ("selected_events_count", "normalized_pick_count", "settled_pick_count", "leakage_failure_count", "schema_reliability_pct")}, indent=2)}

## 4. Global performance

Settlement MM-2.8C.5: {json.dumps(settlement_sum, indent=2)}

## 5. Benchmark comparison

El benchmark same-slice replica stake unitario en el lado benchmark por mercado/evento. Delta por pick en `mm2_8c6_pick_vs_benchmark_rows.csv`.

## 6. Market-level analysis

{json.dumps(perf_mkt, indent=2)}

## 7. League-level analysis

{json.dumps(perf_league, indent=2)}

## 8. Odds-band analysis

{json.dumps(perf_ob, indent=2)}

## 9. Publishability analysis

Distribución Stage 2 / picks (behavior summary): `candidate_publishable_shadow` vs `diagnostic_only` en artefacto MM-2.8C.5 — ver `mm2_8c5_behavior_summary.json`.

## 10. Benchmark-relation analysis

Relación matches_benchmark vs opposes_benchmark y buckets `comparison_bucket` documentados en filas pick-level.

## 11. Failure attribution

Heurística priorizada por pick en `mm2_8c6_failure_attribution_rows.csv` (pérdidas y desalineación vs benchmark). Atribución **no es causal**; sirve para lectura operativa y diseño de gates.

## 12. Gate simulation

Filtros simulados sobre los **mismos** picks ya emitidos: `mm2_8c6_gate_simulation_rows.csv`. Advertencias `in_sample_selection_bias_risk` / `small_sample` cuando aplica.

## 13. Rescuable segments

`mm2_8c6_rescuable_segments.csv`. Un segmento `candidate_for_validation` requiere n≥{MIN_RESCUE_PICKS}, ROI>0 y delta vs benchmark>0 en esta cohorte (validación posterior obligatoria).

## 14. Decision on baseline DSR

Ver `mm2_8c6_baseline_decision.json`:

```json
{json.dumps(decision, indent=2)}
```

## 15. What this proves

Dónde se concentró la pérdida (p.ej. OU vs FT, ligas con ROI negativo), y qué filtros **habrían reducido** exposición en muestra — útil para hipótesis, no para producción.

## 16. What this does not prove

Edge fuera de muestra, estabilidad temporal, ni idoneidad para publicar picks o aumentar spend en DeepSeek.

## 17. Recommended next step

{pause_note}

---

Schema reliability (MM-2.8C.5): {schema_val.get("overall_schema_ok_rate")}. Latency rows counted: {lat_n}.
"""
    AUD.mkdir(parents=True, exist_ok=True)
    (AUD / "MM2_8C6_BASELINE_BACKTEST_POSTMORTEM_AUDIT.md").write_text(md, encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

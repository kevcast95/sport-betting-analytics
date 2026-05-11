#!/usr/bin/env python3
"""
MM-2.8C.5 — Baseline DSR backtest on MM-2.8C.4 repaired TOA market board (2025 cohort).

Consumes scripts/outputs/mm2_8c4_expanded_market_board.json (no TOA/SM API calls).
DSR only with --allow-dsr + DeepSeek API key. Settlement uses historical results from DB (read-only).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "scripts" / "outputs"
AUDITS = ROOT / "docs" / "bettracker2" / "audits"
PREFIX = "mm2_8c5"
BOARD_8C4 = OUT / "mm2_8c4_expanded_market_board.json"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


M = load_module("mm2_8c_mm", ROOT / "scripts" / "mm2_8c_baseline_multimarket_backtest_rebuild.py")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def league_month_key(kickoff_iso: str | None, tz_name: str) -> str:
    ko = M.parse_dt(kickoff_iso or "")
    if not ko:
        return "unknown"
    loc = ko.astimezone(ZoneInfo(tz_name))
    return f"{loc.year}-{loc.month:02d}"


def league_display(name: str | None) -> str:
    if name == "LaLiga":
        return "La Liga"
    return str(name or "")


def select_balanced_league_month(
    eligible: list[dict[str, Any]], max_n: int, tz_name: str
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        lg = league_display(row.get("league"))
        key = (lg, league_month_key(row.get("kickoff_utc"), tz_name))
        buckets[key].append(row)
    for k in buckets:
        buckets[k].sort(key=lambda r: str(r.get("kickoff_utc") or ""))
    keys_sorted = sorted(buckets.keys())
    selected: list[dict[str, Any]] = []
    while len(selected) < max_n:
        progressed = False
        for k in keys_sorted:
            if buckets[k] and len(selected) < max_n:
                selected.append(buckets[k].pop(0))
                progressed = True
        if not progressed:
            break
    return selected


def board_index_from_board(board: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(ev.get("event_context", {}).get("event_id")): ev
        for ev in board.get("events", [])
        if ev.get("event_context")
    }


def board_index_from_path(path: Path) -> dict[str, dict[str, Any]]:
    return board_index_from_board(M.read_json(path, {"events": []}))


def select_eligible_market_ready(
    candidates: list[dict[str, Any]],
    board_by: dict[str, dict[str, Any]],
    min_odds: float,
) -> list[dict[str, Any]]:
    out = []
    for row in candidates:
        eid = str(row["event_id"])
        ev = board_by.get(eid)
        if ev and M.market_ready(ev, min_odds):
            out.append(row)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="MM-2.8C.5 baseline DSR on repaired 2025 market board")
    ap.add_argument("--date-from", default="2025-01-01")
    ap.add_argument("--date-to", default="2025-05-31")
    ap.add_argument("--timezone", default="America/Bogota")
    ap.add_argument("--target-events", type=int, default=75)
    ap.add_argument("--min-decimal-odds", type=float, default=1.30)
    ap.add_argument("--allow-dsr", action="store_true")
    ap.add_argument("--timeout-sec", type=int, default=120)
    ap.add_argument("--model", default="deepseek-v4-pro")
    args = ap.parse_args()

    if not BOARD_8C4.exists():
        raise SystemExit(f"Missing {BOARD_8C4}; run MM-2.8C.4 first.")

    M.MM18_BOARD = BOARD_8C4

    candidates = M.fetch_candidate_universe(args.date_from, args.date_to, args.timezone)
    board_by = board_index_from_path(BOARD_8C4)
    eligible = select_eligible_market_ready(candidates, board_by, args.min_decimal_odds)
    selected = select_balanced_league_month(eligible, args.target_events, args.timezone)

    expected_dsr = len(selected) * 2
    preflight_initial = {
        "generated_at_utc": utc_now(),
        "mode": "mm2_8c5_preflight",
        "selected_events_count": len(selected),
        "eligible_market_ready_count": len(eligible),
        "candidate_universe_count": len(candidates),
        "expected_dsr_calls": expected_dsr if args.allow_dsr else 0,
        "selected_events_count_ge_60": len(selected) >= 60,
        "expected_dsr_calls_le_150": expected_dsr <= 150,
        "market_board_source": str(BOARD_8C4.relative_to(ROOT)),
        "model_requested": args.model,
        "deepseek_external_authorization_note": "Prompts leave the machine only when --allow-dsr and bt2_settings.deepseek_api_key are set.",
        "restrictions": M.safety(False, args.allow_dsr)
        | {
            "no_enriched_context": True,
            "no_toa_api": True,
            "no_sportmonks_api": True,
            "no_db_writes": True,
            "no_production": True,
        },
        "preflight_counts_pass": len(selected) >= 60 and expected_dsr <= 150,
    }
    write_json(OUT / f"{PREFIX}_preflight.json", preflight_initial)

    M.write_csv(OUT / f"{PREFIX}_selected_backtest_events.csv", selected)
    if not preflight_initial["preflight_counts_pass"]:
        print(
            json.dumps(
                {
                    "error": "preflight_counts_failed",
                    "selected_events_count": len(selected),
                    "expected_dsr_calls": expected_dsr,
                },
                indent=2,
            )
        )
        sys.exit(2)

    packages: list[dict[str, Any]] = []
    blocks: dict[str, Any] = {}
    context_rows: list[dict[str, Any]] = []
    if selected:
        targets, history = M.fetch_targets_and_history([int(r["event_id"]) for r in selected])
        packages, blocks, context_rows = M.build_packages(
            selected, board_by, targets, history, args.min_decimal_odds
        )
        for p in packages:
            src = p.setdefault("run_context", {})
            src["run_key"] = "mm2_8c5_baseline_dsr_backtest_repaired_market_board"
            src["source_artifacts"] = [str(BOARD_8C4.relative_to(ROOT))]

    rendered_stage1, rendered_stage2, stage2_packages = M.render_prompts(packages)
    leak_rows = M.leakage_audit(rendered_stage1, rendered_stage2)
    leak_failures = [r for r in leak_rows if r["leakage_status"] != "PASS"]

    preflight_initial["leakage_failure_count"] = len(leak_failures)
    preflight_initial["preflight_passed_for_dsr"] = len(leak_failures) == 0 and args.allow_dsr
    write_json(OUT / f"{PREFIX}_preflight.json", preflight_initial)

    write_json(OUT / f"{PREFIX}_base_context_blocks.json", blocks)
    M.write_csv(OUT / f"{PREFIX}_base_context_rows.csv", context_rows)
    write_json(
        OUT / f"{PREFIX}_market_board_snapshot.json",
        {"generated_at_utc": utc_now(), "source": str(BOARD_8C4.relative_to(ROOT)), "packages_built": len(packages)},
    )
    write_json(OUT / f"{PREFIX}_stage1_packages.json", {"packages": packages})
    write_json(OUT / f"{PREFIX}_stage1_rendered_prompts.json", {"rendered_prompts": rendered_stage1})
    write_json(OUT / f"{PREFIX}_stage2_packages.json", {"stage2_packages": stage2_packages})
    write_json(OUT / f"{PREFIX}_stage2_rendered_prompts.json", {"rendered_prompts": rendered_stage2})
    M.write_csv(OUT / f"{PREFIX}_leakage_audit.csv", leak_rows)

    allow_run_dsr = args.allow_dsr and len(leak_failures) == 0

    class Args:
        pass

    dargs = Args()
    dargs.allow_dsr = allow_run_dsr
    dargs.allow_toa_api = False
    dargs.timeout_sec = args.timeout_sec
    dargs.model = args.model

    stage1_raw: list[dict[str, Any]] = []
    stage1_parsed: list[dict[str, Any]] = []
    stage2_raw: list[dict[str, Any]] = []
    stage2_parsed: list[dict[str, Any]] = []
    latency_rows: list[dict[str, Any]] = []

    dsr_error: str | None = None
    if allow_run_dsr:
        try:
            stage1_raw, stage1_parsed, stage2_raw, stage2_parsed, latency_rows = M.run_dsr_if_allowed(
                packages, rendered_stage1, dargs
            )
        except RuntimeError as ex:
            dsr_error = str(ex)
            print(json.dumps({"error": "dsr_failed", "detail": dsr_error}, indent=2))
    elif args.allow_dsr and leak_failures:
        print(json.dumps({"warning": "DSR skipped due to leakage_audit failures", "count": len(leak_failures)}, indent=2))

    s1_by = {str(r.get("event_id")): r for r in stage1_parsed}
    s2_by = {str(r.get("event_id")): r for r in stage2_parsed}
    MM20 = M.MM20
    normalized, norm_event_rows, market_rows, pick_rows = (
        MM20.normalize_outputs(packages, s1_by, s2_by, {}, 2) if allow_run_dsr and stage1_parsed else ({"events": []}, [], [], [])
    )
    n_s1 = len(stage1_parsed)
    n_s2 = len(stage2_parsed)
    slots = max(1, len(selected) * 2)
    s1_ok = sum(1 for r in stage1_parsed if MM20.stage1_schema_ok(r))
    s2_ok = sum(1 for r in stage2_parsed if MM20.stage2_schema_ok(r))
    schema_validation = {
        "generated_at_utc": utc_now(),
        "events_selected": len(selected),
        "stage1_parsed_count": n_s1,
        "stage2_parsed_count": n_s2,
        "stage1_schema_ok_count": s1_ok,
        "stage2_schema_ok_count": s2_ok,
        "stage1_schema_ok_rate": round(s1_ok / max(n_s1, 1), 4),
        "stage2_schema_ok_rate": round(s2_ok / max(n_s2, 1), 4),
        "overall_schema_ok_rate": round((s1_ok + s2_ok) / slots, 4),
    }

    write_json(OUT / f"{PREFIX}_schema_validation.json", schema_validation)
    write_json(OUT / f"{PREFIX}_stage1_dsr_raw_outputs.json", {"raw_outputs": stage1_raw})
    write_json(OUT / f"{PREFIX}_stage1_dsr_parsed_outputs.json", {"parsed_outputs": stage1_parsed})
    write_json(OUT / f"{PREFIX}_stage2_dsr_raw_outputs.json", {"raw_outputs": stage2_raw})
    write_json(OUT / f"{PREFIX}_stage2_dsr_parsed_outputs.json", {"parsed_outputs": stage2_parsed})
    write_json(OUT / f"{PREFIX}_normalized_final_outputs.json", normalized)
    M.write_csv(OUT / f"{PREFIX}_pick_level_rows.csv", pick_rows)
    behavior = (
        M.behavior_summary(stage1_parsed, stage2_parsed, pick_rows)
        if allow_run_dsr
        else {"DSR_executed": False, "normalized_pick_count": 0}
    )
    write_json(OUT / f"{PREFIX}_behavior_summary.json", behavior)
    M.write_csv(OUT / f"{PREFIX}_latency_rows.csv", latency_rows)

    settlement, settled_rows, by_market, by_league, by_odds, bench_rows = M.settlement_from_picks(pick_rows)
    bench = M.benchmark_summary(bench_rows)

    write_json(OUT / f"{PREFIX}_settlement_summary.json", settlement)
    M.write_csv(OUT / f"{PREFIX}_settlement_pick_rows.csv", settled_rows)
    M.write_csv(OUT / f"{PREFIX}_performance_by_market.csv", by_market)
    M.write_csv(OUT / f"{PREFIX}_performance_by_league.csv", by_league)
    M.write_csv(OUT / f"{PREFIX}_performance_by_odds_band.csv", by_odds)
    M.write_csv(OUT / f"{PREFIX}_benchmark_comparison.csv", bench_rows)

    normalized_pick_count = len(pick_rows)
    settled_pick_count = int(settlement.get("settled_picks") or 0)
    benchmark_roi = (bench.get("benchmark") or {}).get("ROI")
    schema_pct = float(schema_validation["overall_schema_ok_rate"]) * 100
    behavior_interp = schema_pct >= 90 and normalized_pick_count >= M.MIN_INTERPRETABLE_PICK_COUNT
    perf_interp = settled_pick_count >= M.MIN_INTERPRETABLE_PICK_COUNT and benchmark_roi is not None

    summary = {
        "generated_at_utc": utc_now(),
        "mode": "mm2_8c5_baseline_dsr_backtest_repaired_market_board",
        "MM2_8c5_baseline_dsr_backtest_completed": bool(
            selected
            and packages
            and len(leak_failures) == 0
            and (
                not args.allow_dsr
                or (bool(stage1_raw) and not dsr_error)
            )
        ),
        "MM2_8c5_behavior_interpretable": behavior_interp,
        "MM2_8c5_performance_interpretable": perf_interp,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "timezone": args.timezone,
        "selected_events_count": len(selected),
        "DSR_executed": allow_run_dsr,
        "normalized_pick_count": normalized_pick_count,
        "settled_pick_count": settled_pick_count,
        "hit_rate": settlement.get("hit_rate"),
        "ROI": settlement.get("ROI"),
        "benchmark_ROI": benchmark_roi,
        "DSR_minus_benchmark_profit": bench.get("delta_profit"),
        "FT_1X2_ROI": M.extract_roi(by_market, "FT_1X2"),
        "OU_GOALS_2_5_ROI": M.extract_roi(by_market, "OU_GOALS_2_5"),
        "leakage_failure_count": len(leak_failures),
        "schema_reliability_pct": round(schema_pct, 2),
        "safety": M.safety(False, allow_run_dsr),
        "benchmark_same_slice_note": "Flat benchmark stake vs model picks in settlement artifact rows.",
    }
    if dsr_error:
        summary["dsr_execution_error"] = dsr_error
    write_json(OUT / f"{PREFIX}_summary.json", summary)

    AUDITS.mkdir(parents=True, exist_ok=True)
    audit_body = f"""# MM-2.8C.5 — Baseline DSR Backtest on Repaired Market Board

## 1. Executive summary

MM-2.8C.5 ejecuta DSR baseline de dos etapas sobre el tablero TOA reparado **mm2_8c4_expanded_market_board.json** (cohorte 2025). Modo artefacto; sin TOA/SportMonks en esta corrida.

- **MM2_8c5_baseline_dsr_backtest_completed**: {summary["MM2_8c5_baseline_dsr_backtest_completed"]}
- **Eventos seleccionados**: {len(selected)}
- **DSR ejecutado**: {allow_run_dsr}
- **Picks normalizados / settled**: {normalized_pick_count} / {settled_pick_count}
- **ROI / benchmark ROI**: {summary.get("ROI")} / {benchmark_roi}

## 2. Scope and restrictions

Sin enriched context; sin odds TOA en vivo; sin escrituras DB de negocio; sin producción; sin picks publicados.

## 3. Why MM-2.8C.5 was unlocked

MM-2.8C.4 alcanzó volumen y readiness tras corregir **soccer_france_ligue_one**.

## 4. Inputs used

- `scripts/outputs/mm2_8c4_expanded_market_board.json`
- Universo `bt2_events` vía `fetch_candidate_universe` (ventana CLI)
- Templates Stage 1/2 MM-2.8C en `mm2_8c_baseline_multimarket_backtest_rebuild`

## 5. Universe and market board

Selección: candidatos finished/scored en 5 ligas con **market_ready** en el tablero 8c4; balance **liga/mes**.

## 6. Leakage audit

Filas en `mm2_8c5_leakage_audit.csv`; fallos: **{len(leak_failures)}**.

## 7. DSR execution summary

Salidas raw/parsed Stage 1 y 2 en `scripts/outputs/mm2_8c5_*`.

## 8. Schema reliability

Ver `mm2_8c5_schema_validation.json` — tasa global **{schema_pct:.2f}%**.

## 9. Normalized picks

`mm2_8c5_normalized_final_outputs.json`, `mm2_8c5_pick_level_rows.csv`.

## 10. Settlement results

`mm2_8c5_settlement_summary.json`, `mm2_8c5_settlement_pick_rows.csv`.

## 11–13. Performance by market / league / odds band

CSV `performance_by_*`.

## 14. Benchmark same-slice comparison

`mm2_8c5_benchmark_comparison.csv`.

## 15. Latency / cost

`mm2_8c5_latency_rows.csv` (tiempo por llamada DeepSeek; sin coste monetario en artefacto).

## 16. What this proves

Comportamiento pipeline baseline sobre cohorte 2025 con tablero reparado; settle histórico reproducible.

## 17. What this does not prove

Edge productivo, lift futuro o idoneidad para publicar picks.

## 18. Recommended next step

Revisión humana de segmentos y decisión sobre forward test operativo (fuera de alcance MM-2.8C.5).
"""
    (AUDITS / "MM2_8C5_BASELINE_DSR_BACKTEST_REPAIRED_MARKET_BOARD_AUDIT.md").write_text(audit_body, encoding="utf-8")

    print(json.dumps({k: summary[k] for k in summary if k != "safety"}, indent=2))


if __name__ == "__main__":
    main()

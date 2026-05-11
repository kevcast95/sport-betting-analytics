#!/usr/bin/env python3
"""
MM-2.8C.7 — Evaluate manual model outputs against mm2_8c7 answer key (artifact-only).

Reads blind bundle for consensus odds; no DB, no APIs.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mm2_1_settlement_performance_evaluation import odds_band, profit_for, settle_selection

OUT = ROOT / "scripts" / "outputs"
PREFIX = "mm2_8c7"

EXPECTED_FIELDS = ("model_name", "run_id", "picks")
PICK_FIELDS = ("blind_event_id", "decision", "market", "selection", "confidence", "rationale")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    flat: list[dict[str, Any]] = []
    for row in rows:
        fr: dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                fr[k] = json.dumps(v, ensure_ascii=False)
            else:
                fr[k] = v
        flat.append(fr)
    fields: list[str] = []
    for row in flat:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(flat)


def load_bundle_index(path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(path)
    return {e["blind_event_id"]: e for e in data.get("events", [])}


def load_answer_index(path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(path)
    return {e["blind_event_id"]: e for e in data.get("events", [])}


def consensus_price(bundle_ev: dict[str, Any], market: str, selection: str) -> float | None:
    mb = bundle_ev.get("market_board") or {}
    if market == "FT_1X2":
        block = mb.get("FT_1X2") or {}
        side = block.get(selection) or {}
        return side.get("consensus_decimal")
    if market == "OU_GOALS_2_5":
        block = mb.get("OU_GOALS_2_5") or {}
        side = block.get(selection) or {}
        return side.get("consensus_decimal")
    return None


def validate_model_doc(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for f in EXPECTED_FIELDS:
        if f not in doc:
            errs.append(f"missing_top_level:{f}")
    picks = doc.get("picks")
    if not isinstance(picks, list):
        errs.append("picks_not_list")
        return errs
    for i, p in enumerate(picks):
        if not isinstance(p, dict):
            errs.append(f"pick_{i}_not_object")
            continue
        for f in PICK_FIELDS:
            if f not in p:
                errs.append(f"pick_{i}_missing_{f}")
        dec = p.get("decision")
        if dec == "pick":
            if p.get("market") not in ("FT_1X2", "OU_GOALS_2_5"):
                errs.append(f"pick_{i}_invalid_market_for_pick")
            sel = p.get("selection")
            if p.get("market") == "FT_1X2" and sel not in ("home", "draw", "away"):
                errs.append(f"pick_{i}_invalid_ft_selection")
            if p.get("market") == "OU_GOALS_2_5" and sel not in ("over_2_5", "under_2_5"):
                errs.append(f"pick_{i}_invalid_ou_selection")
        elif dec == "abstain":
            if p.get("market") not in (None, "") or p.get("selection") not in (None, ""):
                errs.append(f"pick_{i}_abstain_should_null_market_selection")
        else:
            errs.append(f"pick_{i}_bad_decision")
    return errs


def evaluate_model(
    model_path: Path,
    bundle_by: dict[str, dict[str, Any]],
    ans_by: dict[str, dict[str, Any]],
    expected_ids: list[str],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    doc = read_json(model_path)
    schema_errs = validate_model_doc(doc)
    picks_by_id = {p["blind_event_id"]: p for p in doc.get("picks", []) if isinstance(p, dict)}
    missing = [i for i in expected_ids if i not in picks_by_id]
    extra = [k for k in picks_by_id if k not in expected_ids]
    id_errs = []
    if missing:
        id_errs.append(f"missing_blind_ids:{','.join(missing)}")
    if extra:
        id_errs.append(f"extra_blind_ids:{','.join(extra)}")

    rows: list[dict[str, Any]] = []
    for bid in expected_ids:
        p = picks_by_id.get(bid)
        ans = ans_by[bid]
        bev = bundle_by[bid]
        rh = ans.get("result_home")
        ra = ans.get("result_away")
        base_row: dict[str, Any] = {
            "model_name": doc.get("model_name"),
            "run_id": doc.get("run_id"),
            "blind_event_id": bid,
            "original_event_id": ans.get("original_event_id"),
            "league": ans.get("league"),
            "decision": p.get("decision") if p else None,
            "market": p.get("market") if p else None,
            "selection": p.get("selection") if p else None,
            "confidence": p.get("confidence") if p else None,
        }
        if not p:
            base_row.update(
                {
                    "settlement_status": "missing_pick_row",
                    "pick_odds": None,
                    "stake": 0.0,
                    "profit": 0.0,
                    "odds_band": None,
                    "validation_note": "missing_blind_event_in_model_output",
                }
            )
            rows.append(base_row)
            continue
        if p.get("decision") != "pick":
            base_row.update(
                {
                    "settlement_status": "abstain",
                    "pick_odds": None,
                    "stake": 0.0,
                    "profit": 0.0,
                    "odds_band": None,
                    "validation_note": "abstain",
                }
            )
            rows.append(base_row)
            continue

        market = str(p.get("market") or "")
        sel = str(p.get("selection") or "")
        supported = bev.get("supported_markets") or []
        if market not in supported:
            base_row.update(
                {
                    "settlement_status": "invalid_market_not_supported",
                    "pick_odds": None,
                    "stake": 0.0,
                    "profit": 0.0,
                    "odds_band": None,
                    "validation_note": "market_not_in_supported_markets",
                }
            )
            rows.append(base_row)
            continue

        price = consensus_price(bev, market, sel)
        if price is None:
            base_row.update(
                {
                    "settlement_status": "no_price",
                    "pick_odds": None,
                    "stake": 0.0,
                    "profit": 0.0,
                    "odds_band": None,
                    "validation_note": "missing_consensus_decimal",
                }
            )
            rows.append(base_row)
            continue

        status, _, _reason = settle_selection(market, sel, rh, ra)
        prof = profit_for(status, float(price))
        ob = odds_band(float(price))
        base_row.update(
            {
                "settlement_status": status,
                "pick_odds": float(price),
                "stake": 1.0 if status in ("win", "loss") else 0.0,
                "profit": prof,
                "odds_band": ob,
                "validation_note": "",
            }
        )
        rows.append(base_row)

    summary_counts = Counter(str(r.get("settlement_status")) for r in rows)
    settled = [r for r in rows if r.get("settlement_status") in ("win", "loss")]
    stake_sum = sum(float(r.get("stake") or 0) for r in rows)
    profit_sum = sum(float(r.get("profit") or 0) for r in rows)
    wins = sum(1 for r in settled if r.get("settlement_status") == "win")
    losses = sum(1 for r in settled if r.get("settlement_status") == "loss")

    summary = {
        "model_name": doc.get("model_name"),
        "run_id": doc.get("run_id"),
        "schema_errors": schema_errs + id_errs,
        "picks_count": len([r for r in rows if r.get("decision") == "pick"]),
        "abstain_count": len([r for r in rows if r.get("decision") == "abstain"]),
        "missing_pick_rows": len([r for r in rows if r.get("settlement_status") == "missing_pick_row"]),
        "settled_picks": len(settled),
        "wins": wins,
        "losses": losses,
        "voids_invalid": int(summary_counts.get("invalid_market_not_supported", 0) + summary_counts.get("no_price", 0)),
        "hit_rate": round(wins / len(settled), 6) if settled else None,
        "total_staked": round(stake_sum, 6),
        "total_profit": round(profit_sum, 6),
        "ROI_flat_stake": round(profit_sum / stake_sum, 6) if stake_sum else None,
    }
    return summary, rows, schema_errs + id_errs


def group_roi(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r.get("settlement_status") not in ("win", "loss"):
            continue
        groups[str(r.get(key) or "unknown")].append(r)
    out = []
    for gk, grp in sorted(groups.items()):
        stake = sum(float(x.get("stake") or 0) for x in grp)
        prof = sum(float(x.get("profit") or 0) for x in grp)
        out.append(
            {
                key: gk,
                "n_settled": len(grp),
                "profit": round(prof, 6),
                "staked": round(stake, 6),
                "ROI": round(prof / stake, 6) if stake else None,
            }
        )
    return out


def benchmark_slice_for_pick(ans: dict[str, Any], market: str) -> dict[str, Any] | None:
    bbm = ans.get("benchmark_by_market") or {}
    block = bbm.get(market)
    if not block:
        return None
    return {
        "benchmark_selection": block.get("benchmark_selection"),
        "benchmark_odds": block.get("benchmark_odds"),
        "benchmark_profit": block.get("benchmark_profit"),
    }


def dsr_slice_same_events(ans_by: dict[str, dict[str, Any]], blind_ids: list[str]) -> dict[str, Any]:
    total = 0.0
    n_picks = 0
    for bid in blind_ids:
        v = float(ans_by[bid].get("dsr_event_net_profit") or 0)
        total += v
        n_picks += len(ans_by[bid].get("dsr_mm2_8c5_picks") or [])
    stake_events = sum(
        1 for bid in blind_ids if (ans_by[bid].get("dsr_mm2_8c5_picks") or [])
    )
    return {
        "dsr_event_net_profit_sum_over_sample": round(total, 6),
        "dsr_pick_rows_in_sample": n_picks,
        "events_with_any_dsr_pick": stake_events,
        "note": "Net profit sums MM-2.8C.5 settlement rows for sampled events (may be 2 picks per event).",
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate MM-2.8C.7 manual model bake-off outputs")
    ap.add_argument("--blind-bundle", type=Path, default=OUT / f"{PREFIX}_blind_bundle.json")
    ap.add_argument("--answer-key", type=Path, default=OUT / f"{PREFIX}_answer_key.json")
    ap.add_argument(
        "--model-outputs",
        nargs="*",
        default=[
            OUT / f"{PREFIX}_manual_outputs" / "opus_4_6_output.json",
            OUT / f"{PREFIX}_manual_outputs" / "gpt_5_5_output.json",
        ],
    )
    args = ap.parse_args()

    bundle_by = load_bundle_index(args.blind_bundle)
    ans_by = load_answer_index(args.answer_key)
    expected_ids = sorted(bundle_by.keys(), key=lambda x: x)

    summaries: list[dict[str, Any]] = []
    all_pick_rows: list[dict[str, Any]] = []
    vs_bench: list[dict[str, Any]] = []
    vs_dsr: list[dict[str, Any]] = []

    dsr_ref = dsr_slice_same_events(ans_by, expected_ids)

    for mpath in args.model_outputs:
        if not mpath.exists():
            summaries.append(
                {
                    "model_name": mpath.stem,
                    "run_id": None,
                    "schema_errors": [f"missing_file:{mpath}"],
                    "ROI_flat_stake": None,
                }
            )
            continue
        summary, rows, errs = evaluate_model(mpath, bundle_by, ans_by, expected_ids)
        summary["schema_errors"] = errs
        summaries.append(summary)
        for r in rows:
            all_pick_rows.append(dict(r, source_file=str(mpath.name)))

        # vs benchmark (same market row when model picked)
        doc = read_json(mpath)
        picks_by_id = {p["blind_event_id"]: p for p in doc.get("picks", []) if isinstance(p, dict)}
        for bid in expected_ids:
            p = picks_by_id.get(bid)
            ans = ans_by[bid]
            if not p or p.get("decision") != "pick":
                vs_bench.append(
                    {
                        "model_name": doc.get("model_name"),
                        "blind_event_id": bid,
                        "comparison": "model_abstain_or_missing",
                        "benchmark_profit_same_market_row": None,
                    }
                )
                continue
            mkt = str(p.get("market") or "")
            bench = benchmark_slice_for_pick(ans, mkt)
            vs_bench.append(
                {
                    "model_name": doc.get("model_name"),
                    "blind_event_id": bid,
                    "model_market": mkt,
                    "benchmark_profit_same_market_row": bench.get("benchmark_profit") if bench else None,
                    "benchmark_selection": bench.get("benchmark_selection") if bench else None,
                    "comparison": "model_pick_vs_benchmark_row",
                }
            )

        vs_dsr.append(
            {
                "model_name": summary.get("model_name"),
                "run_id": summary.get("run_id"),
                "model_total_profit_sample": summary.get("total_profit"),
                "model_ROI": summary.get("ROI_flat_stake"),
                **dsr_ref,
            }
        )

        # grouped ROI for this model
        g_market = group_roi(rows, "market")
        g_league = group_roi(rows, "league")
        g_band = group_roi(rows, "odds_band")
        summary["ROI_by_market"] = g_market
        summary["ROI_by_league"] = g_league
        summary["ROI_by_odds_band"] = g_band

        bench_sum = 0.0
        bench_n = 0
        for bid in expected_ids:
            p = picks_by_id.get(bid)
            if not p or p.get("decision") != "pick":
                continue
            b = benchmark_slice_for_pick(ans_by[bid], str(p.get("market") or ""))
            if b and b.get("benchmark_profit") is not None:
                bench_sum += float(b["benchmark_profit"])
                bench_n += 1
        summary["benchmark_flat_stake_profit_sum_on_picked_markets"] = round(bench_sum, 6)
        summary["benchmark_ROI_on_picked_market_rows"] = round(bench_sum / bench_n, 6) if bench_n else None

    ranking = sorted(
        [s for s in summaries if s.get("ROI_flat_stake") is not None],
        key=lambda s: (s.get("ROI_flat_stake") is not None, s.get("ROI_flat_stake") or -999),
        reverse=True,
    )

    out_summary = {
        "generated_at_utc": utc_now(),
        "mode": "mm2_8c7_model_bakeoff_evaluation",
        "blind_event_count": len(expected_ids),
        "models": summaries,
        "ranking_by_ROI": [{"model_name": r.get("model_name"), "ROI_flat_stake": r.get("ROI_flat_stake")} for r in ranking],
        "dsr_reference_slice": dsr_ref,
    }
    write_json(OUT / f"{PREFIX}_model_bakeoff_summary.json", out_summary)
    write_csv(OUT / f"{PREFIX}_model_bakeoff_pick_rows.csv", all_pick_rows)
    write_csv(OUT / f"{PREFIX}_model_bakeoff_by_model.csv", summaries)
    write_csv(OUT / f"{PREFIX}_model_bakeoff_vs_benchmark.csv", vs_bench)
    write_csv(OUT / f"{PREFIX}_model_bakeoff_vs_dsr.csv", vs_dsr)

    print(json.dumps({"written": True, "models_evaluated": len(summaries)}, indent=2))


if __name__ == "__main__":
    main()

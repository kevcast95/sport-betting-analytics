#!/usr/bin/env python3
"""
MM-1.4 Final output normalizer / pick assembler (artifact-only).

Reads MM-1.3 Stage 2 parses + MM-1.1 packages; builds normalized picks from
market_outputs only (ignores model final_event_output.picks for acceptance).

No DSR, no external calls, no DB.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_OUT = ROOT / "scripts" / "outputs"
_S2_PARSED = _OUT / "mm1_3_stage2_compact_parsed_outputs.json"
_S1_REC = _OUT / "mm1_3_stage1_recovery_parsed_outputs.json"
_PP = _OUT / "mm1_3_postprocess_market_scoped.json"
_SUM_MM13 = _OUT / "mm1_3_e2e_reliability_summary.json"
_ROWS_MM13 = _OUT / "mm1_3_e2e_reliability_rows.csv"
_PACKAGES = _OUT / "mm1_1_safe_context_enriched_input_packages.json"
_CONTRACT = _OUT / "mm1_two_stage_shadow_postprocess_contract.json"

_SPEC_MM1 = importlib.util.spec_from_file_location(
    "mm1_dsr_shadow_signal_test",
    ROOT / "scripts" / "mm1_dsr_shadow_signal_test.py",
)
assert _SPEC_MM1 and _SPEC_MM1.loader
_MM1 = importlib.util.module_from_spec(_SPEC_MM1)
_SPEC_MM1.loader.exec_module(_MM1)

_SPEC_M13 = importlib.util.spec_from_file_location(
    "mm1_3_e2e_reliability_patch",
    ROOT / "scripts" / "mm1_3_e2e_reliability_patch.py",
)
assert _SPEC_M13 and _SPEC_M13.loader
_M13 = importlib.util.module_from_spec(_SPEC_M13)
_SPEC_M13.loader.exec_module(_M13)

ACTIVE_MARKETS = _MM1.ACTIVE_MARKETS
STAGE2_SELECTIONS = _MM1.STAGE2_SELECTIONS
package_markets = _MM1.package_markets
context_contains_word = _MM1.context_contains_word
ou_line_inventory_ok = _M13.ou_line_inventory_ok


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
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def scan_market_level_and_event_flags(
    parsed: dict[str, Any],
    package: dict[str, Any],
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    """Mirror MM-1.3 market scan: event_rejects, market_rejects, downgrades."""
    event_rejects: list[str] = []
    market_rejects: dict[str, list[str]] = defaultdict(list)
    downgrades: list[str] = []

    if package.get("leakage_flags", {}).get("HIGH_RISK_LEAKAGE"):
        event_rejects.append("high_risk_leakage")

    text = json.dumps(parsed, ensure_ascii=False).lower()
    if "combinada" in text:
        event_rejects.append("event_level_combinada")

    markets = package_markets(package)
    ou_inv = markets.get("OU_GOALS_2_5", {})
    ou_ok = ou_line_inventory_ok(ou_inv)

    for out in parsed.get("market_outputs", []) or []:
        if not isinstance(out, dict):
            continue
        market = out.get("market_canonical")
        if market not in ACTIVE_MARKETS:
            event_rejects.append("unsupported_market")
            continue
        if market == "BTTS":
            event_rejects.append("active_btts")
        if market == "DOUBLE_CHANCE":
            event_rejects.append("synthetic_double_chance")

        if market == "OU_GOALS_2_5":
            if not ou_ok:
                market_rejects["OU_GOALS_2_5"].append("ou25_missing_point_2_5")
                if out.get("selection_canonical") not in {"over_2_5", "under_2_5", None}:
                    market_rejects["OU_GOALS_2_5"].append("ou25_missing_over_or_under")
                if out.get("final_decision") == "pick":
                    event_rejects.append("ou_market_output_pick_without_supported_line")
            else:
                if out.get("selection_canonical") not in {"over_2_5", "under_2_5", None}:
                    market_rejects["OU_GOALS_2_5"].append("ou25_missing_over_or_under")

        if market == "FT_1X2" and out.get("selection_canonical") not in {"home", "draw", "away", None}:
            market_rejects["FT_1X2"].append("ft_1x2_missing_home_draw_away")

        inv_m = markets.get(market, {})
        if inv_m.get("pre_kickoff_market_validated") is False:
            market_rejects[str(market)].append("post_kickoff_odds")

        if inv_m.get("settlement_supported") is False and out.get("final_decision") == "pick":
            market_rejects[str(market)].append("missing_settlement_support")

        if out.get("market_relation") == "market_only":
            downgrades.append("market_only_not_publishable")
        if out.get("context_lean") == "unknown":
            downgrades.append("context_unknown")

        rationale = str(out.get("rationale_short_es") or "").lower()
        if any(x in rationale for x in ["lesion", "lesión", "alineacion", "alineación", "racha"]) and not context_contains_word(
            package, rationale
        ):
            event_rejects.append("invented_context")

    mr = {k: sorted(set(v)) for k, v in market_rejects.items() if v}
    return sorted(set(event_rejects)), mr, sorted(set(downgrades))


def stage1_non_market_signal_count(stage1_by_market: dict[str, Any], market: str) -> int | None:
    mo = stage1_by_market.get(market)
    if not isinstance(mo, dict):
        return None
    v = mo.get("non_market_signal_count")
    return int(v) if isinstance(v, int) else None


def build_stage1_by_market(stage1_parsed: dict[str, Any] | None) -> dict[str, Any]:
    if not stage1_parsed:
        return {}
    out: dict[str, Any] = {}
    for item in stage1_parsed.get("market_outputs", []) or []:
        if isinstance(item, dict) and item.get("market_canonical"):
            out[str(item["market_canonical"])] = item
    return out


def publishability_for_row(market_relation: str | None) -> str:
    if market_relation == "context_reinforces_market":
        return "candidate_publishable_shadow"
    if market_relation in ("weak_tension", "strong_tension"):
        return "diagnostic_only"
    return "diagnostic_only"


def assembly_gate_reasons(
    out: dict[str, Any],
    package: dict[str, Any],
    market_scan_rejects: dict[str, list[str]],
) -> list[str]:
    reasons: list[str] = []
    market = out.get("market_canonical")
    markets = package_markets(package)
    inv = markets.get(market, {})

    if out.get("final_decision") != "pick":
        reasons.append("not_pick_decision")

    if market not in ("FT_1X2", "OU_GOALS_2_5"):
        reasons.append("market_not_ft_or_ou")

    if inv.get("supported_for_mm1") is False:
        reasons.append("supported_for_mm1_false")

    if market_scan_rejects.get(str(market)):
        reasons.append("market_has_hard_rejects")

    sel = out.get("selection_canonical")
    allowed = STAGE2_SELECTIONS.get(market, set())
    if sel not in allowed or sel is None:
        reasons.append("invalid_selection_canonical")

    try:
        po = float(out.get("pick_odds"))
        if po <= 0:
            reasons.append("pick_odds_not_positive")
    except (TypeError, ValueError):
        reasons.append("pick_odds_invalid")

    if out.get("market_relation") == "market_only":
        reasons.append("market_relation_market_only")

    if out.get("context_lean") in (None, "", "unknown"):
        reasons.append("context_lean_unknown_or_missing")

    if out.get("context_confidence") not in {"none", "low", "medium", "high"}:
        reasons.append("context_confidence_invalid_or_missing")

    if not (isinstance(out.get("rationale_short_es"), str) and out.get("rationale_short_es", "").strip()):
        reasons.append("rationale_short_es_missing")

    if package.get("leakage_flags", {}).get("HIGH_RISK_LEAKAGE"):
        reasons.append("high_risk_leakage")

    if inv.get("pre_kickoff_market_validated") is not True:
        reasons.append("pre_kickoff_not_validated")

    return reasons


def try_assemble_pick(
    *,
    event_id: str,
    out: dict[str, Any],
    package: dict[str, Any],
    market_scan_rejects: dict[str, list[str]],
    s1bm: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    market = out.get("market_canonical")
    reasons = assembly_gate_reasons(out, package, market_scan_rejects)
    nmc = stage1_non_market_signal_count(s1bm, str(market))
    if nmc is not None and nmc < 1:
        reasons.append("non_market_signal_count_below_1")

    if reasons:
        return None, reasons

    markets = package_markets(package)
    inv = markets.get(market, {})
    bench_side = out.get("benchmark_side")
    if bench_side is None:
        bench_side = inv.get("benchmark_side")
    bench_odds = out.get("benchmark_odds")
    if bench_odds is None:
        bench_odds = inv.get("benchmark_odds")

    pub = publishability_for_row(out.get("market_relation"))

    if bench_side is None:
        return None, reasons + ["benchmark_side_missing"]
    try:
        bo = float(bench_odds) if bench_odds is not None else float("nan")
        if bo <= 0 or bo != bo:
            return None, reasons + ["benchmark_odds_invalid"]
    except (TypeError, ValueError):
        return None, reasons + ["benchmark_odds_invalid"]

    pick = {
        "event_id": event_id,
        "market_canonical": market,
        "selection_canonical": out.get("selection_canonical"),
        "pick_odds": float(out.get("pick_odds")),
        "market_relation": out.get("market_relation"),
        "context_lean": out.get("context_lean"),
        "context_confidence": out.get("context_confidence"),
        "benchmark_side": bench_side,
        "benchmark_odds": float(bench_odds),
        "publishability_status": pub,
        "rationale_short_es": str(out.get("rationale_short_es") or "").strip(),
    }
    return pick, []


def forbidden_activation(parsed: dict[str, Any] | None) -> list[str]:
    bad: list[str] = []
    if not parsed:
        return bad
    for out in parsed.get("market_outputs", []) or []:
        if not isinstance(out, dict):
            continue
        m = out.get("market_canonical")
        if m == "BTTS":
            bad.append("btts_active_output")
        if m == "DOUBLE_CHANCE":
            bad.append("double_chance_active_output")
    return bad


def mm13_before_missing_pick_count(pp_records: list[dict[str, Any]]) -> int:
    return sum(
        1
        for p in pp_records
        if "final_pick_missing_required_fields" in (p.get("event_level_hard_rejects") or [])
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="MM-1.4 final output normalizer")
    ap.add_argument("--max-picks-per-event", type=int, default=2)
    args = ap.parse_args()

    s2_root = read_json(_S2_PARSED)
    parsed_list = s2_root.get("parsed_outputs") or []

    packages_root = read_json(_PACKAGES)
    packages_by_id = {
        str(p["event_context"]["event_id"]): p
        for p in packages_root.get("packages", [])
        if p.get("mm1_signal_test_readiness") == "ready_for_dsr_signal_test"
    }

    mm13_summary = read_json(_SUM_MM13) if _SUM_MM13.is_file() else {}
    merged_s1_list = mm13_summary.get("stage1_merged_parsed_outputs") or []
    s1_by_event = {str(x.get("event_id")): x for x in merged_s1_list if x.get("event_id")}

    pp_root = read_json(_PP)
    pp_by_id = {str(x.get("event_id")): x for x in (pp_root.get("postprocess") or []) if x.get("event_id")}

    contract = read_json(_CONTRACT) if _CONTRACT.is_file() else {}

    mm13_accepted = int(mm13_summary.get("metrics", {}).get("event_level_accepted_count", 0))

    events_out: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    market_rows: list[dict[str, Any]] = []

    events_processed = 0
    stage2_parse_ok_count = 0
    normalized_accepted = 0
    normalized_rejected = 0
    accepted_shadow_no_pick = 0
    normalized_pick_total = 0
    cand_pub = 0
    mo_diag_mo = 0
    ml_reasons: Counter[str] = Counter()
    el_reasons: Counter[str] = Counter()
    bench_matches: Counter[str] = Counter()
    abstain_by_mkt: Counter[str] = Counter()
    mkt_total: Counter[str] = Counter()
    mo_only_by_mkt: Counter[str] = Counter()
    pick_mkt: Counter[str] = Counter()
    pick_sel: Counter[str] = Counter()
    mo_pub_violations = 0

    final_missing_after = 0

    market_order = {"FT_1X2": 0, "OU_GOALS_2_5": 1}

    for rec in parsed_list:
        event_id = str(rec.get("event_id") or "")
        events_processed += 1
        pkg = packages_by_id.get(event_id)
        if not pkg:
            normalized_rejected += 1
            el_reasons["missing_package"] += 1
            events_out.append({"event_id": event_id, "error": "missing_package"})
            continue

        parse_ok = rec.get("parse_status") == "ok"
        parsed = rec.get("parsed") if parse_ok else None
        if parse_ok:
            stage2_parse_ok_count += 1

        if not parse_ok or not isinstance(parsed, dict):
            normalized_rejected += 1
            el_reasons["stage2_parse_not_ok"] += 1
            rows.append(
                {
                    "event_id": event_id,
                    "stage2_parse_ok": False,
                    "normalized_event_accepted": False,
                    "accepted_shadow_no_pick": False,
                    "normalized_pick_count": 0,
                    "event_level_hard_rejects": "stage2_parse_not_ok",
                    "market_level_hard_rejects_json": "{}",
                    "model_final_picks_ignored": True,
                }
            )
            continue

        forbidden = forbidden_activation(parsed)
        if forbidden:
            normalized_rejected += 1
            for f in forbidden:
                el_reasons[f] += 1
            rows.append(
                {
                    "event_id": event_id,
                    "stage2_parse_ok": True,
                    "normalized_event_accepted": False,
                    "accepted_shadow_no_pick": False,
                    "normalized_pick_count": 0,
                    "event_level_hard_rejects": "|".join(forbidden),
                    "market_level_hard_rejects_json": "{}",
                    "model_final_picks_ignored": True,
                }
            )
            continue

        scan_ev, scan_mr, scan_dg = scan_market_level_and_event_flags(parsed, pkg)
        for mk, rs in scan_mr.items():
            for r in rs:
                ml_reasons[r] += 1

        s1rec = s1_by_event.get(event_id, {})
        s1parsed = {k: v for k, v in s1rec.items() if k != "stage1_source"}
        s1bm = build_stage1_by_market(s1parsed)

        candidate_picks: list[tuple[int, dict[str, Any]]] = []
        invalid_pick_attempt = False

        for out in parsed.get("market_outputs", []) or []:
            if not isinstance(out, dict):
                continue
            m = str(out.get("market_canonical") or "")
            mkt_total[m] += 1
            if out.get("final_decision") == "abstain" or out.get("market_relation") == "abstain":
                abstain_by_mkt[m] += 1
            if out.get("market_relation") == "market_only":
                mo_only_by_mkt[m] += 1
                mo_diag_mo += 1

            gate_fail: list[str] = []
            assembled, fail_reasons = try_assemble_pick(
                event_id=event_id,
                out=out,
                package=pkg,
                market_scan_rejects=scan_mr,
                s1bm=s1bm,
            )

            if out.get("final_decision") == "pick":
                if assembled is None:
                    invalid_pick_attempt = True
                    gate_fail = fail_reasons
                else:
                    candidate_picks.append((market_order.get(m, 9), assembled))

            market_rows.append(
                {
                    "event_id": event_id,
                    "market_canonical": m,
                    "model_final_decision": out.get("final_decision"),
                    "model_market_relation": out.get("market_relation"),
                    "assembled_normalized_pick": assembled is not None,
                    "assembly_gate_fail_reasons": "|".join(fail_reasons) if out.get("final_decision") == "pick" else "",
                    "market_level_hard_rejects": "|".join(scan_mr.get(m, [])),
                }
            )

        candidate_picks.sort(key=lambda x: x[0])
        picks_norm = [p for _, p in candidate_picks[: int(args.max_picks_per_event)]]

        event_level = list(scan_ev)
        if invalid_pick_attempt:
            event_level.append("invalid_market_output_pick_failed_normalizer_gates")

        for pub_stat in picks_norm:
            if pub_stat.get("market_relation") == "market_only" and pub_stat.get("publishability_status") == "candidate_publishable_shadow":
                event_level.append("market_only_as_candidate_publishable_shadow")

        event_level = sorted(set(event_level))
        for r in event_level:
            el_reasons[r] += 1

        accepted = not event_level
        picks_emitted = list(picks_norm) if accepted else []

        if accepted:
            normalized_accepted += 1
            normalized_pick_total += len(picks_emitted)
            if len(picks_emitted) == 0:
                accepted_shadow_no_pick += 1
                bench_matches["no_pick"] += 1
            else:
                bench_matches["events_with_normalized_picks"] += 1
            for pk in picks_emitted:
                if pk.get("publishability_status") == "candidate_publishable_shadow":
                    cand_pub += 1
                    if pk.get("market_relation") == "market_only":
                        mo_pub_violations += 1
                pick_mkt[str(pk.get("market_canonical"))] += 1
                pick_sel[f'{pk.get("market_canonical")}:{pk.get("selection_canonical")}'] += 1
                sel = pk.get("selection_canonical")
                bside = pk.get("benchmark_side")
                if sel and bside:
                    if sel == bside:
                        bench_matches["matches_benchmark"] += 1
                    else:
                        bench_matches["opposes_benchmark"] += 1
            for pk in picks_emitted:
                req = (
                    pk.get("event_id"),
                    pk.get("market_canonical"),
                    pk.get("selection_canonical"),
                    pk.get("pick_odds"),
                    pk.get("market_relation"),
                    pk.get("context_lean"),
                    pk.get("context_confidence"),
                    pk.get("benchmark_side"),
                    pk.get("benchmark_odds"),
                    pk.get("publishability_status"),
                    pk.get("rationale_short_es"),
                )
                if any(x is None for x in req):
                    final_missing_after += 1
                elif float(pk.get("pick_odds") or 0) <= 0 or float(pk.get("benchmark_odds") or 0) <= 0:
                    final_missing_after += 1
        else:
            normalized_rejected += 1

        norm_final = {
            "event_id": event_id,
            "picks": picks_emitted,
            "assembled_from": "market_outputs_mm1_4_v1",
            "model_final_event_output_ignored_for_acceptance": True,
            "postprocess_status": "accepted_shadow_no_pick"
            if accepted and not picks_emitted
            else ("accepted_shadow" if accepted else "rejected"),
            "event_no_pick_reason": None
            if picks_emitted
            else ("no_eligible_market_output_pick" if accepted else None),
            "assembly_candidates_pre_gate": picks_norm if (not accepted and picks_norm) else [],
        }

        events_out.append(
            {
                "event_id": event_id,
                "parse_status": rec.get("parse_status"),
                "normalized_final_event_output": norm_final,
                "normalized_postprocess": {
                    "accepted": accepted,
                    "event_level_hard_rejects": event_level,
                    "market_level_hard_rejects": scan_mr,
                    "diagnostic_downgrades": scan_dg,
                },
                "model_final_event_output_snapshot": (parsed.get("final_event_output") or {}),
            }
        )

        rows.append(
            {
                "event_id": event_id,
                "stage2_parse_ok": True,
                "normalized_event_accepted": accepted,
                "accepted_shadow_no_pick": accepted and len(picks_emitted) == 0,
                "normalized_pick_count": len(picks_emitted),
                "assembly_candidates_count_if_rejected": len(picks_norm) if not accepted else 0,
                "event_level_hard_rejects": "|".join(event_level),
                "market_level_hard_rejects_json": json.dumps(scan_mr, ensure_ascii=False),
                "invalid_pick_attempt_on_market_output": invalid_pick_attempt,
                "model_final_picks_ignored": True,
            }
        )

    before_missing = mm13_before_missing_pick_count(list(pp_by_id.values()))

    abstain_rate_by_market = {
        m: round(abstain_by_mkt[m] / mkt_total[m], 6) if mkt_total[m] else None for m in sorted(mkt_total)
    }
    mo_rate_by_market = {
        m: round(mo_only_by_mkt[m] / mkt_total[m], 6) if mkt_total[m] else None for m in sorted(mkt_total)
    }

    mm14_passed = (
        final_missing_after == 0
        and mo_pub_violations == 0
        and not any("btts" in x or "double_chance" in x for x in el_reasons)
        and normalized_accepted >= mm13_accepted
        and mo_pub_violations == 0
    )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "mm1_4_final_output_normalizer",
        "MM1_4_final_output_normalizer_passed": mm14_passed,
        "inputs": {
            "mm1_3_stage2_compact_parsed": str(_S2_PARSED),
            "mm1_3_stage1_recovery_parsed": str(_S1_REC),
            "mm1_3_postprocess": str(_PP),
            "mm1_3_e2e_summary": str(_SUM_MM13),
            "mm1_3_e2e_rows": str(_ROWS_MM13),
            "mm1_1_packages": str(_PACKAGES),
            "postprocess_contract": str(_CONTRACT),
            "contract_loaded": bool(contract),
            "stage1_signal_counts_source": "mm1_3_e2e_reliability_summary.stage1_merged_parsed_outputs",
        },
        "metrics": {
            "events_processed": events_processed,
            "stage2_parse_ok_count": stage2_parse_ok_count,
            "normalized_event_accepted_count": normalized_accepted,
            "normalized_event_rejected_count": normalized_rejected,
            "accepted_shadow_no_pick_count": accepted_shadow_no_pick,
            "normalized_pick_count": normalized_pick_total,
            "candidate_publishable_shadow_count": cand_pub,
            "market_only_diagnostic_count": mo_diag_mo,
            "market_level_rejects_by_reason": dict(ml_reasons),
            "event_level_rejects_by_reason": dict(el_reasons),
            "final_pick_missing_required_fields_before": before_missing,
            "final_pick_missing_required_fields_after": final_missing_after,
            "pick_distribution_by_market": dict(pick_mkt),
            "pick_distribution_by_selection": dict(pick_sel),
            "normalized_pick_vs_benchmark": dict(bench_matches),
            "abstain_rate_by_market": abstain_rate_by_market,
            "market_only_rate_by_market": mo_rate_by_market,
            "mm1_3_event_level_accepted_baseline": mm13_accepted,
        },
        "safety": {
            "dsr_calls": False,
            "external_calls": False,
            "db_writes": False,
            "production_writes": False,
        },
        "interpretation_guardrails": [
            "No edge/ROI from normalization.",
            "Picks are deterministic assemblies from market_outputs + package gates.",
        ],
    }

    write_json(
        _OUT / "mm1_4_normalized_final_outputs.json",
        {"summary": summary, "events": events_out},
    )
    write_json(_OUT / "mm1_4_final_output_normalizer_summary.json", summary)
    write_csv(_OUT / "mm1_4_final_output_normalizer_rows.csv", rows)
    write_csv(_OUT / "mm1_4_market_level_decisions.csv", market_rows)

    print(json.dumps({"MM1_4_final_output_normalizer_passed": mm14_passed, "metrics": summary["metrics"]}, indent=2))


if __name__ == "__main__":
    main()

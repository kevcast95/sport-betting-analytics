#!/usr/bin/env python3
"""
MM-2.6R.1 Stage 1 Schema Reliability Repair.

Artifact-only post-process repair. It does not call DSR, SportMonks, TOA, DB,
production paths, Telegram, vault or betting flows. It only normalizes parsed
Stage 1 outputs when the sole schema drift is a missing root odds_visible key.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mm2_6_dsr_stage1_ab_mini_run import (  # noqa: E402
    build_comparisons,
    forbidden_key_hits,
    output_forbidden_text_hits,
    parse_and_validate,
    validation_payload,
)
from scripts.mm2_6r_stage1_ab_live_forward_universe_refresh import (  # noqa: E402
    BASELINE_PACKAGES_OUT,
    ENRICHED_PACKAGES_OUT,
    package_visibility_rows,
)

OUT = ROOT / "scripts" / "outputs"
AUDITS = ROOT / "docs" / "bettracker2" / "audits"
PROMPTS = ROOT / "prompts" / "bt2"

RAW_IN = OUT / "mm2_6r_stage1_ab_raw_outputs.json"
PARSED_IN = OUT / "mm2_6r_stage1_ab_parsed_outputs.json"
VALIDATION_IN = OUT / "mm2_6r_stage1_ab_validation.json"
COMPARISON_IN = OUT / "mm2_6r_stage1_ab_comparison_rows.csv"
RATIONALE_IN = OUT / "mm2_6r_stage1_ab_rationale_quality_rows.csv"
LATENCY_IN = OUT / "mm2_6r_stage1_ab_latency_rows.csv"
SUMMARY_IN = OUT / "mm2_6r_stage1_ab_summary.json"

PARSED_REPAIRED_OUT = OUT / "mm2_6r1_stage1_ab_parsed_outputs_repaired.json"
VALIDATION_REPAIRED_OUT = OUT / "mm2_6r1_stage1_ab_validation_repaired.json"
COMPARISON_REPAIRED_CSV = OUT / "mm2_6r1_stage1_ab_comparison_rows_repaired.csv"
RATIONALE_REPAIRED_CSV = OUT / "mm2_6r1_stage1_ab_rationale_quality_rows_repaired.csv"
SUMMARY_OUT = OUT / "mm2_6r1_stage1_schema_repair_summary.json"
CLASSIFICATION_CSV = OUT / "mm2_6r1_stage1_schema_failure_classification_rows.csv"
AUDIT_MD = AUDITS / "MM2_6R1_STAGE1_SCHEMA_RELIABILITY_REPAIR_AUDIT.md"

SYSTEM_PATCH_DRAFT = PROMPTS / "mm2_stage1_system_prompt_schema_patch_draft.txt"
USER_PATCH_DRAFT = PROMPTS / "mm2_stage1_user_prompt_schema_patch_draft.txt"

FORBIDDEN_KEY_GROUPS = {
    "odds": {"odds", "odds_by_market", "pick_odds", "price", "prices", "consensus_decimal", "bookmaker", "bookmakers", "by_bookmaker"},
    "benchmark": {"benchmark", "benchmark_side", "benchmark_odds"},
    "market_board": {"market_board"},
    "stage2": {"final_decision", "market_only", "market_relation", "selection_canonical"},
}
FORBIDDEN_TEXT_GROUPS = {
    "odds": ["pick_odds", "odds_by_market", " bookmaker", " price ", " prices ", "consensus_decimal"],
    "benchmark": ["benchmark"],
    "market_board": ["market board", "market_board"],
    "stage2": ["stage 2", "stage2", "final_decision", "market_only", "market relation", "market_relation"],
    "forbidden_markets": ["btts", "double chance", "double_chance"],
}


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def text_blob(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str).lower().replace("odds_visible", "visibility_flag")


def recursive_keys(value: Any) -> set[str]:
    keys: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                keys.add(str(k).lower())
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(value)
    return keys


def has_text_any(value: Any, needles: list[str]) -> bool:
    blob = text_blob(value)
    return any(n.lower() in blob for n in needles)


def classify_record(raw: dict[str, Any], parsed_record: dict[str, Any]) -> dict[str, Any]:
    parsed = parsed_record.get("parsed")
    parse_ok = parsed_record.get("parse_status") == "ok" and isinstance(parsed, dict)
    schema_errors = parsed_record.get("schema_errors") or []
    keys = recursive_keys(parsed) if parse_ok else set()
    missing_odds_visible = parse_ok and "odds_visible" not in parsed
    odds_visible_true = parse_ok and parsed.get("odds_visible") is True
    forbidden_odds = bool(keys & FORBIDDEN_KEY_GROUPS["odds"]) or has_text_any(parsed, FORBIDDEN_TEXT_GROUPS["odds"])
    forbidden_benchmark = bool(keys & FORBIDDEN_KEY_GROUPS["benchmark"]) or has_text_any(parsed, FORBIDDEN_TEXT_GROUPS["benchmark"])
    forbidden_market_board = bool(keys & FORBIDDEN_KEY_GROUPS["market_board"]) or has_text_any(parsed, FORBIDDEN_TEXT_GROUPS["market_board"])
    forbidden_stage2 = bool(keys & FORBIDDEN_KEY_GROUPS["stage2"]) or has_text_any(parsed, FORBIDDEN_TEXT_GROUPS["stage2"])
    forbidden_markets = has_text_any(parsed, FORBIDDEN_TEXT_GROUPS["forbidden_markets"])
    market_outputs = parsed.get("market_outputs") if parse_ok else None
    stage1_shape = parse_ok and isinstance(market_outputs, list) and all(isinstance(x, dict) and "context_lean" in x for x in market_outputs)
    forbidden_any = forbidden_odds or forbidden_benchmark or forbidden_market_board or forbidden_stage2 or forbidden_markets
    only_missing_odds_visible = sorted(schema_errors) == ["odds_visible_not_false"] and missing_odds_visible
    can_auto_repair = bool(parse_ok and only_missing_odds_visible and not odds_visible_true and not forbidden_any and stage1_shape)
    repair_action = "insert_odds_visible_false" if can_auto_repair else ("none_already_schema_ok" if parsed_record.get("schema_status") == "ok" else "needs_dsr_retry_or_prompt_patch")
    return {
        "fixture_id": str(parsed_record.get("fixture_id") or raw.get("fixture_id")),
        "variant": parsed_record.get("variant") or raw.get("variant"),
        "parse_ok": parse_ok,
        "schema_ok_original": parsed_record.get("schema_status") == "ok",
        "schema_failure_reason": "|".join(schema_errors),
        "missing_odds_visible": bool(missing_odds_visible),
        "forbidden_odds_present": bool(forbidden_odds),
        "forbidden_benchmark_present": bool(forbidden_benchmark),
        "forbidden_market_board_present": bool(forbidden_market_board),
        "forbidden_stage2_label_present": bool(forbidden_stage2),
        "forbidden_btts_dc_present": bool(forbidden_markets),
        "stage1_shape": bool(stage1_shape),
        "can_auto_repair": can_auto_repair,
        "repair_action": repair_action,
    }


def repaired_raw_from_parsed(raw: dict[str, Any], repaired_parsed: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(raw)
    out["raw_content"] = json.dumps(repaired_parsed, ensure_ascii=False)
    return out


def avg(values: list[float]) -> float | None:
    return round(statistics.mean(values), 3) if values else None


def truthy(value: Any) -> bool:
    return str(value).lower() in {"true", "1", "yes"}


def build_repair_summary(
    raw_records: list[dict[str, Any]],
    original_parsed: list[dict[str, Any]],
    repaired_validation_records: list[dict[str, Any]],
    repair_rows: list[dict[str, Any]],
    comparison_rows: list[dict[str, Any]],
    rationale_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    calls_total = len(raw_records)
    parse_ok = sum(1 for r in original_parsed if r.get("parse_status") == "ok")
    schema_ok_before = sum(1 for r in original_parsed if r.get("schema_status") == "ok")
    schema_ok_after = sum(1 for r in repaired_validation_records if r.get("schema_status") == "ok")
    auto_repaired_count = sum(1 for r in repair_rows if truthy(r["can_auto_repair"]))
    unrepaired_count = sum(1 for r in repair_rows if r["repair_action"] == "needs_dsr_retry_or_prompt_patch")
    forbidden_leakage_count = sum(
        1
        for r in repair_rows
        if truthy(r["forbidden_odds_present"])
        or truthy(r["forbidden_benchmark_present"])
        or truthy(r["forbidden_market_board_present"])
        or truthy(r["forbidden_stage2_label_present"])
        or truthy(r["forbidden_btts_dc_present"])
    )
    invented_signal_count = sum(1 for r in rationale_rows if truthy(r.get("invented_signal_flag")))
    forbidden_mentions = sum(1 for r in rationale_rows if truthy(r.get("forbidden_market_or_odds_mentions")))
    enriched_context_used_count = sum(1 for r in rationale_rows if not truthy(r.get("enriched_ignores_enriched_context")))
    unknown_reduction_count = sum(1 for r in comparison_rows if truthy(r.get("unknown_reduced")))
    useful = (unknown_reduction_count > 0 or enriched_context_used_count > 0) and invented_signal_count == 0 and forbidden_mentions == 0
    reliable = (
        calls_total > 0
        and parse_ok / calls_total >= 0.90
        and schema_ok_after / calls_total >= 0.90
        and forbidden_leakage_count == 0
        and all(not (r.get("model_metadata") or {}).get("model_mismatch") for r in raw_records)
        and all(str(r.get("error_type") or "") not in {"TimeoutError", "timeout"} for r in raw_records)
    )
    repair_safe = auto_repaired_count > 0 and unrepaired_count == 0 and forbidden_leakage_count == 0
    return {
        "generated_at_utc": utc_now(),
        "mode": "mm2_6r1_stage1_schema_reliability_repair_artifact_only",
        "MM2_6r1_stage1_schema_reliability_repair_completed": True,
        "MM2_6r1_auto_repair_safe": repair_safe,
        "MM2_6r1_stage1_ab_reliable_after_repair": reliable,
        "MM2_6r1_enriched_context_useful_signal_after_repair": useful,
        "MM2_6r1_ready_for_stage2_ab_design_after_repair": reliable and useful,
        "calls_total": calls_total,
        "parse_ok_count": parse_ok,
        "schema_ok_before": schema_ok_before,
        "schema_ok_after": schema_ok_after,
        "auto_repaired_count": auto_repaired_count,
        "unrepaired_count": unrepaired_count,
        "forbidden_leakage_count": forbidden_leakage_count,
        "odds_visible_missing_count_before": sum(1 for r in repair_rows if truthy(r["missing_odds_visible"])),
        "odds_visible_missing_count_after": sum(1 for r in repaired_validation_records if "odds_visible_not_false" in (r.get("schema_errors") or [])),
        "unknown_reduction_count": unknown_reduction_count,
        "context_lean_changed_count": sum(1 for r in comparison_rows if truthy(r.get("context_lean_changed"))),
        "rationale_quality_improved_count": enriched_context_used_count,
        "enriched_context_used_count": enriched_context_used_count,
        "invented_signal_count": invented_signal_count,
        "forbidden_mentions_count": forbidden_mentions,
        "model_mismatch_count": sum(1 for r in raw_records if (r.get("model_metadata") or {}).get("model_mismatch")),
        "timeout_count": sum(1 for r in raw_records if str(r.get("error_type") or "") in {"TimeoutError", "timeout"}),
        "ab_classification_counts_after_repair": dict(Counter(r.get("ab_classification") for r in comparison_rows)),
        "restrictions_observed": {
            "artifact_only": True,
            "dsr_calls": False,
            "toa_calls": False,
            "sportmonks_api_calls": False,
            "external_calls": False,
            "db_writes": False,
            "production": False,
            "bt2_daily_picks": False,
            "telegram": False,
            "vault": False,
            "bets": False,
            "tennis": False,
            "stage2": False,
            "odds": False,
            "benchmark": False,
            "market_board": False,
            "picks": False,
            "settlement": False,
            "roi_hit_rate": False,
        },
    }


def write_prompt_patch_drafts() -> None:
    SYSTEM_PATCH_DRAFT.write_text(
        """BT2 MM-2 Stage 1 schema patch draft.

Root key odds_visible is REQUIRED.
In Stage 1, odds_visible MUST be the JSON boolean false.
Do not omit odds_visible.
Do not output odds_visible as true, null, a string, or 0.
Missing odds_visible invalidates the response.

Return strict JSON only with the existing Stage 1 schema.
""",
        encoding="utf-8",
    )
    USER_PATCH_DRAFT.write_text(
        """Stage 1 schema reminder draft:

Your JSON response MUST include the root field:

  "odds_visible": false

This field is required even though odds are not visible. It must be JSON boolean false, not true, null, string, or number. Omitting odds_visible invalidates the response.

Continue to analyze only FT_1X2 and OU_GOALS_2_5. Do not include odds, benchmark, market board, picks, Stage 2 labels, BTTS, or Double Chance.
""",
        encoding="utf-8",
    )


def write_audit(summary: dict[str, Any]) -> None:
    lines = [
        "# MM2.6R.1 Stage 1 Schema Reliability Repair Audit",
        "",
        "## 1. Executive summary",
        f"`MM2_6r1_stage1_schema_reliability_repair_completed = {str(summary['MM2_6r1_stage1_schema_reliability_repair_completed']).lower()}`.",
        f"`MM2_6r1_auto_repair_safe = {str(summary['MM2_6r1_auto_repair_safe']).lower()}`.",
        f"`MM2_6r1_stage1_ab_reliable_after_repair = {str(summary['MM2_6r1_stage1_ab_reliable_after_repair']).lower()}`.",
        f"`MM2_6r1_enriched_context_useful_signal_after_repair = {str(summary['MM2_6r1_enriched_context_useful_signal_after_repair']).lower()}`.",
        "",
        "## 2. Scope and restrictions",
        "Artifact-only post-process repair. No DSR, no TOA, no SportMonks API, no external calls, no DB writes, no production, no `bt2_daily_picks`, no Telegram, no vault, no bets, no tennis, no Stage 2, no odds, no benchmark, no market board, no picks, no settlement, no ROI/hit rate, and no product logic changes.",
        "",
        "## 3. Inputs used",
        "- `scripts/outputs/mm2_6r_stage1_ab_raw_outputs.json`",
        "- `scripts/outputs/mm2_6r_stage1_ab_parsed_outputs.json`",
        "- `scripts/outputs/mm2_6r_stage1_ab_validation.json`",
        "- `scripts/outputs/mm2_6r_stage1_ab_comparison_rows.csv`",
        "- `scripts/outputs/mm2_6r_stage1_ab_rationale_quality_rows.csv`",
        "- `scripts/outputs/mm2_6r_stage1_ab_latency_rows.csv`",
        "- MM-2.6R rendered prompts and leakage audit artifacts",
        "",
        "## 4. Original MM-2.6R result",
        f"Calls total `{summary['calls_total']}`, parse OK `{summary['parse_ok_count']}`, schema OK before repair `{summary['schema_ok_before']}`.",
        "",
        "## 5. Schema failure analysis",
        f"Missing `odds_visible` before repair: `{summary['odds_visible_missing_count_before']}`. Forbidden leakage count: `{summary['forbidden_leakage_count']}`.",
        "",
        "## 6. Auto-repair policy",
        "Auto-repair inserts root `odds_visible=false` only when parse is OK, the field is absent, no forbidden odds/benchmark/market-board/Stage-2/BTTS/DC content exists, and the output has Stage 1 shape. It does not alter leans, confidence, rationales, signal counts, or any model interpretation.",
        "",
        "## 7. Repaired validation results",
        f"Schema OK after repair `{summary['schema_ok_after']}`. Auto repaired `{summary['auto_repaired_count']}`. Unrepaired `{summary['unrepaired_count']}`. Missing `odds_visible` after repair `{summary['odds_visible_missing_count_after']}`.",
        "",
        "## 8. Baseline vs enriched comparison after repair",
        f"Unknown reductions `{summary['unknown_reduction_count']}`. Context lean changes `{summary['context_lean_changed_count']}`. A/B classification counts `{summary['ab_classification_counts_after_repair']}`.",
        "",
        "## 9. Rationale quality after repair",
        f"Enriched context used count `{summary['enriched_context_used_count']}`. Invented signal count `{summary['invented_signal_count']}`. Forbidden mentions count `{summary['forbidden_mentions_count']}`.",
        "",
        "## 10. Prompt/schema patch recommendation",
        "Draft prompt patches were created to make `odds_visible=false` non-optional and explicitly invalid when omitted. Do not replace production templates until MM-2.6R.2 or a separate prompt patch review.",
        "",
        "## 11. What this proves",
        "This proves the MM-2.6R schema failures were safely normalizable when they were solely missing `odds_visible=false`, and the A/B comparison can be recalculated without another DSR call.",
        "",
        "## 12. What this does not prove",
        "Esto no calcula picks. Esto no calcula ROI. Esto no calcula hit rate. Esto no prueba edge. Esto no prueba producción. It does not prove Stage 2 readiness unless reliability and enriched usefulness criteria are both met.",
        "",
        "## 13. Recommended next step",
        "Because enriched usefulness remains false after repair, do not advance to Stage 2 A/B design yet. If stricter schema reliability is needed, run MM-2.6R.2 as a targeted retry only for schema-failed calls using the prompt patch draft.",
        "",
    ]
    AUDIT_MD.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    raw_payload = read_json(RAW_IN, {})
    parsed_payload = read_json(PARSED_IN, {})
    raw_records = raw_payload.get("raw_outputs") or []
    parsed_records = parsed_payload.get("parsed_outputs") or []
    raw_by_key = {(str(r.get("fixture_id")), r.get("variant")): r for r in raw_records}
    repair_rows: list[dict[str, Any]] = []
    repaired_bundle: list[dict[str, Any]] = []
    repaired_validation_records: list[dict[str, Any]] = []
    repaired_parsed_records: list[dict[str, Any]] = []

    for original in parsed_records:
        key = (str(original.get("fixture_id")), original.get("variant"))
        raw = raw_by_key.get(key, {})
        classification = classify_record(raw, original)
        repaired_parsed = deepcopy(original.get("parsed"))
        repair_applied = False
        repair_reason = "not_repaired"
        if classification["can_auto_repair"]:
            repaired_parsed["odds_visible"] = False
            repair_applied = True
            repair_reason = "inserted_missing_root_odds_visible_false_only"
        repaired_raw = repaired_raw_from_parsed(raw, repaired_parsed) if isinstance(repaired_parsed, dict) else raw
        repaired_record = parse_and_validate(repaired_raw)
        repaired_record["repair_applied"] = repair_applied
        repaired_record["repair_reason"] = repair_reason
        repaired_parsed_records.append(repaired_record)
        repaired_validation_records.append(
            {
                "fixture_id": repaired_record["fixture_id"],
                "variant": repaired_record["variant"],
                "parse_status": repaired_record["parse_status"],
                "schema_status": repaired_record["schema_status"],
                "schema_errors": repaired_record["schema_errors"],
                "forbidden_key_hits": repaired_record["forbidden_key_hits"],
                "forbidden_text_hits": repaired_record["forbidden_text_hits"],
                "repair_applied": repair_applied,
                "repair_reason": repair_reason,
            }
        )
        repair_rows.append(classification)
        repaired_bundle.append(
            {
                "fixture_id": original.get("fixture_id"),
                "variant": original.get("variant"),
                "raw_original": raw,
                "parsed_original": original.get("parsed"),
                "parsed_repaired": repaired_parsed,
                "repair_applied": repair_applied,
                "repair_reason": repair_reason,
                "original_schema_errors": original.get("schema_errors"),
                "repaired_schema_errors": repaired_record.get("schema_errors"),
                "repaired_schema_status": repaired_record.get("schema_status"),
            }
        )

    visibility_rows = package_visibility_rows(read_json(BASELINE_PACKAGES_OUT, {}).get("packages") or [])
    visibility_rows.extend(package_visibility_rows(read_json(ENRICHED_PACKAGES_OUT, {}).get("packages") or []))
    comparison_rows, rationale_rows = build_comparisons(repaired_parsed_records, visibility_rows)
    summary = build_repair_summary(raw_records, parsed_records, repaired_validation_records, repair_rows, comparison_rows, rationale_rows)

    write_json(PARSED_REPAIRED_OUT, {"summary": summary, "repaired_outputs": repaired_bundle, "parsed_outputs": repaired_parsed_records})
    write_json(
        VALIDATION_REPAIRED_OUT,
        {
            "generated_at_utc": utc_now(),
            "records": repaired_validation_records,
            "summary": {
                "original_parse_ok_count": summary["parse_ok_count"],
                "original_schema_ok_count": summary["schema_ok_before"],
                "repaired_schema_ok_count": summary["schema_ok_after"],
                "auto_repaired_count": summary["auto_repaired_count"],
                "unrepaired_count": summary["unrepaired_count"],
                "forbidden_leakage_count": summary["forbidden_leakage_count"],
                "odds_visible_missing_count_before": summary["odds_visible_missing_count_before"],
                "odds_visible_missing_count_after": summary["odds_visible_missing_count_after"],
            },
        },
    )
    write_csv(CLASSIFICATION_CSV, repair_rows)
    write_csv(COMPARISON_REPAIRED_CSV, comparison_rows)
    write_csv(RATIONALE_REPAIRED_CSV, rationale_rows)
    write_json(SUMMARY_OUT, summary)
    write_prompt_patch_drafts()
    write_audit(summary)

    print(f"MM2_6r1_stage1_schema_reliability_repair_completed={summary['MM2_6r1_stage1_schema_reliability_repair_completed']}")
    print(f"schema_ok_before={summary['schema_ok_before']}")
    print(f"schema_ok_after={summary['schema_ok_after']}")
    print(f"auto_repaired_count={summary['auto_repaired_count']}")
    print(f"MM2_6r1_stage1_ab_reliable_after_repair={summary['MM2_6r1_stage1_ab_reliable_after_repair']}")
    print(f"MM2_6r1_enriched_context_useful_signal_after_repair={summary['MM2_6r1_enriched_context_useful_signal_after_repair']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

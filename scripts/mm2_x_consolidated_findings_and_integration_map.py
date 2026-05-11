#!/usr/bin/env python3
"""
MM2_X Consolidated Findings + Integration Map.

Artifact-only consolidation of MM-0 through MM-2.5/2.5b findings. No DSR,
external API calls, DB access, DB writes, production writes, picks, settlement,
ROI recomputation, or betting actions.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "scripts" / "outputs"
AUDITS = ROOT / "docs" / "bettracker2" / "audits"


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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def exists(*paths: str) -> str:
    return "; ".join(p for p in paths if (ROOT / p).exists())


def phase_inventory() -> list[dict[str, Any]]:
    return [
        {"phase_id": "MM-0", "title": "Multi-market inventory", "purpose": "Audit market taxonomy and active candidates.", "status": "completed", "main_finding": "FT_1X2 confirmed; BTTS/DC discovery-only.", "artifacts_generated": exists("docs/bettracker2/audits/MM0_MULTI_MARKET_INVENTORY_AUDIT.md", "scripts/outputs/mm0_multi_market_inventory_audit.json"), "scripts_generated": exists("scripts/mm0_1_ou25_line_provenance_audit.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "partial", "production_migration_candidate": "later", "blockers": "Validation sample still limited.", "next_dependency": "Market board and line preservation."},
        {"phase_id": "MM-0.1", "title": "OU2.5 line/provenance", "purpose": "Confirm OU_GOALS_2_5 point semantics.", "status": "completed", "main_finding": "OU2.5 must preserve point=2.5, not generic totals.", "artifacts_generated": exists("docs/bettracker2/audits/MM0_1_OU25_LINE_PROVENANCE_AUDIT.md", "scripts/outputs/mm0_1_ou25_line_provenance_audit.json"), "scripts_generated": exists("scripts/mm0_1_ou25_line_provenance_audit.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "yes", "blockers": "Need provider adapter hardening.", "next_dependency": "TOA totals backfill."},
        {"phase_id": "MM-0.2", "title": "TOA totals backfill", "purpose": "Backfill market-board totals evidence.", "status": "completed", "main_finding": "TOA totals can support OU_GOALS_2_5 with point=2.5.", "artifacts_generated": exists("docs/bettracker2/audits/MM0_2_TOA_TOTALS_BACKFILL_AUDIT.md", "scripts/outputs/mm0_2_toa_totals_backfill_summary.json"), "scripts_generated": exists("scripts/mm0_2_toa_totals_backfill_audit.py"), "external_api_calls": "yes", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "later", "blockers": "Quota/timing and vendor reliability.", "next_dependency": "Line preservation scaffold."},
        {"phase_id": "MM-0.3", "title": "Line preservation scaffold", "purpose": "Prevent line collapse for totals.", "status": "completed", "main_finding": "Line/point preservation is required for OU2.5 correctness.", "artifacts_generated": exists("docs/bettracker2/audits/MM0_3_LINE_PRESERVATION_SCAFFOLD_AUDIT.md", "scripts/outputs/mm0_3_line_preservation_scaffold_audit.json"), "scripts_generated": exists("scripts/mm0_3_line_preservation_scaffold_audit.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "yes", "blockers": "Needs production adapter tests.", "next_dependency": "Market board builder."},
        {"phase_id": "MM-1", "title": "Two-stage design and prompt spec", "purpose": "Separate context-only Stage 1 from market-aware Stage 2.", "status": "completed", "main_finding": "Two-stage contract prevents odds leakage into context evaluation.", "artifacts_generated": exists("docs/bettracker2/design/MM1_TWO_STAGE_SHADOW_DESIGN.md", "docs/bettracker2/design/MM1_DSR_PROMPT_SPEC.md"), "scripts_generated": exists("scripts/mm1_prompt_harness_dry_run.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "later", "blockers": "Prompt size and latency.", "next_dependency": "Prompt harness."},
        {"phase_id": "MM-1.0", "title": "Market board completion", "purpose": "Build DSR-ready market board packages.", "status": "completed", "main_finding": "FT_1X2 and OU2.5 market board support became available for shadow.", "artifacts_generated": exists("docs/bettracker2/audits/MM1_0_MARKET_BOARD_PACKAGE_COMPLETION_AUDIT.md", "scripts/outputs/mm1_0_market_board_input_packages.json"), "scripts_generated": exists("scripts/mm1_market_board_package_completion.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "later", "blockers": "No production persistence contract yet.", "next_dependency": "Safe context enrichment."},
        {"phase_id": "MM-1.1", "title": "Safe context enrichment", "purpose": "Add h2h/team form/rest/season context safely.", "status": "completed", "main_finding": "Historical base_context could be constructed without target leakage.", "artifacts_generated": exists("docs/bettracker2/audits/MM1_1_SAFE_CONTEXT_ENRICHMENT_AUDIT.md", "scripts/outputs/mm1_1_safe_context_enriched_input_packages.json"), "scripts_generated": exists("scripts/mm1_safe_context_enrichment_package.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "yes", "blockers": "Needs robust mapping for future fixture targets.", "next_dependency": "DSR signal test."},
        {"phase_id": "MM-1.2", "title": "Stage 2 compact reliability repair", "purpose": "Repair compact Stage 2 parsing/reliability.", "status": "completed", "main_finding": "Compact Stage 2 can be parsed reliably.", "artifacts_generated": exists("docs/bettracker2/audits/MM1_2_STAGE2_COMPACT_RELIABILITY_REPAIR_AUDIT.md", "scripts/outputs/mm1_2_stage2_compact_summary.json"), "scripts_generated": "", "external_api_calls": "yes", "DSR_calls": "yes", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "later", "blockers": "Still experimental prompt harness.", "next_dependency": "E2E reliability."},
        {"phase_id": "MM-1.3", "title": "E2E reliability patch", "purpose": "Stabilize Stage 1/Stage 2 parsing and postprocess.", "status": "completed", "main_finding": "E2E reliability became adequate for expanded shadow.", "artifacts_generated": exists("docs/bettracker2/audits/MM1_3_E2E_RELIABILITY_PATCH_AUDIT.md", "scripts/outputs/mm1_3_e2e_reliability_summary.json"), "scripts_generated": exists("scripts/mm1_3_e2e_reliability_patch.py"), "external_api_calls": "yes", "DSR_calls": "yes", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "later", "blockers": "No production gating.", "next_dependency": "Normalizer."},
        {"phase_id": "MM-1.4", "title": "Final output normalizer", "purpose": "Deterministically normalize DSR outputs.", "status": "completed", "main_finding": "Normalizer prevents market_only from becoming a pick.", "artifacts_generated": exists("docs/bettracker2/audits/MM1_4_FINAL_OUTPUT_NORMALIZER_AUDIT.md", "scripts/outputs/mm1_4_normalized_final_outputs.json"), "scripts_generated": exists("scripts/mm1_4_final_output_normalizer.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "yes", "blockers": "Needs production contract tests.", "next_dependency": "Behavior analysis."},
        {"phase_id": "MM-1.5", "title": "Behavior analysis", "purpose": "Audit DSR output behavior and rationale language.", "status": "completed", "main_finding": "Market-only remained diagnostic; rationale language needed guardrails.", "artifacts_generated": exists("docs/bettracker2/audits/MM1_5_BEHAVIOR_ANALYSIS_AUDIT.md", "scripts/outputs/mm1_5_behavior_analysis_summary.json"), "scripts_generated": exists("scripts/mm1_5_behavior_analysis.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "later", "blockers": "No proof of edge.", "next_dependency": "Expanded cohort."},
        {"phase_id": "MM-1.6/1.7", "title": "Expanded cohort and candidate universe", "purpose": "Prepare Medium50 candidate set.", "status": "completed", "main_finding": "A wider candidate universe was available for MM-2.0.", "artifacts_generated": exists("docs/bettracker2/audits/MM1_6_EXPANDED_SHADOW_COHORT_PLAN.md", "docs/bettracker2/audits/MM1_7_CANDIDATE_UNIVERSE_BUILDER_AUDIT.md"), "scripts_generated": exists("scripts/mm1_6_expanded_shadow_cohort_plan.py", "scripts/mm1_7_candidate_universe_builder.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "later", "blockers": "Cohort still shadow/diagnostic.", "next_dependency": "TOA backfill."},
        {"phase_id": "MM-1.8/1.9", "title": "TOA historical backfill and expanded prompt package", "purpose": "Build full packages for expanded shadow DSR.", "status": "completed", "main_finding": "Stage 1 saw h2h/team_form/rest_days/season_aggregates; Stage 2 saw compact market board.", "artifacts_generated": exists("docs/bettracker2/audits/MM1_8_TOA_HISTORICAL_BACKFILL_CONTROLLED_AUDIT.md", "docs/bettracker2/audits/MM1_9_EXPANDED_PROMPT_PACKAGE_BUILD_AUDIT.md"), "scripts_generated": exists("scripts/mm1_8_toa_historical_backfill_controlled.py", "scripts/mm1_9_expanded_prompt_package_build.py"), "external_api_calls": "yes", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "yes", "production_migration_candidate": "later", "blockers": "Long prompts around 10k chars.", "next_dependency": "MM-2.0 DSR run."},
        {"phase_id": "MM-2.0", "title": "Expanded DSR Shadow Run", "purpose": "Run 42-event two-stage DSR shadow.", "status": "completed", "main_finding": "42/42 Stage 1 and 42/42 Stage 2 parsed OK; 15 normalized picks; no timeout/model mismatch.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_0_EXPANDED_DSR_SHADOW_RUN_AUDIT.md", "scripts/outputs/mm2_0_run_lot_summary.json"), "scripts_generated": exists("scripts/mm2_0_expanded_dsr_shadow_run.py"), "external_api_calls": "yes", "DSR_calls": "yes", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "shadow_executed", "production_migration_candidate": "no", "blockers": "No SportMonks enriched context; high latency/cost.", "next_dependency": "Settlement/performance and latency audit."},
        {"phase_id": "MM-2.1", "title": "Settlement/performance evaluation", "purpose": "Evaluate MM-2.0 shadow picks historically.", "status": "completed", "main_finding": "15 settled picks: 6-9, ROI -20.13%; benchmark ROI -36.80%; no edge proof.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_1_SETTLEMENT_PERFORMANCE_EVALUATION_AUDIT.md", "scripts/outputs/mm2_1_settlement_summary.json"), "scripts_generated": exists("scripts/mm2_1_settlement_performance_evaluation.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "settlement_tested", "production_migration_candidate": "no", "blockers": "Small n; FT_1X2 weak; candidate_publishable worse than diagnostic_only.", "next_dependency": "Method audit and signal enrichment."},
        {"phase_id": "MM-2.0 latency", "title": "Latency diagnostics", "purpose": "Diagnose run latency/cost.", "status": "completed", "main_finding": "84 sequential DSR calls; no retries/timeouts; prompt size/token load is high.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_0_LATENCY_DIAGNOSTICS_AUDIT.md", "scripts/outputs/mm2_0_latency_diagnostics_summary.json"), "scripts_generated": exists("scripts/mm2_0_latency_diagnostics.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "artifact_only", "production_migration_candidate": "later", "blockers": "Need timestamps, checkpoint/resume, concurrency 2, compact prompts.", "next_dependency": "Compaction."},
        {"phase_id": "MM-2.2", "title": "ds_input visibility audit", "purpose": "See what DSR actually received.", "status": "completed", "main_finding": "DSR saw base_context but not lineups/injuries/formations; compaction could reduce Stage 1 by ~47.7%.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_2_DS_INPUT_VISIBILITY_AUDIT.md", "scripts/outputs/mm2_2_compaction_estimate.json"), "scripts_generated": exists("scripts/mm2_2_ds_input_visibility_audit.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "artifact_only", "production_migration_candidate": "later", "blockers": "Compact prompt not E2E tested.", "next_dependency": "SportMonks signal lineage."},
        {"phase_id": "MM-2.3", "title": "SportMonks includes signal lineage", "purpose": "Find raw signals missing from ds_input.", "status": "completed", "main_finding": "Raw SportMonks has rich lineups/sidelined/formations/weather not reaching DSR.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_3_SPORTMONKS_INCLUDES_SIGNAL_LINEAGE_AUDIT.md", "scripts/outputs/mm2_3_sm_signal_lineage_matrix.csv"), "scripts_generated": exists("scripts/mm2_3_sportmonks_includes_signal_lineage_audit.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "doc_only", "production_migration_candidate": "later", "blockers": "Need entitlement-safe include set.", "next_dependency": "Controlled probes."},
        {"phase_id": "MM-2.3b/2.3c", "title": "SportMonks controlled/reduced probes", "purpose": "Validate include entitlement and degradation.", "status": "experimental", "main_finding": "2.3b aggressive include failed; 2.3c reduced set confirmed basic enrichment.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_3B_SPORTMONKS_CONTROLLED_FIXTURE_PROBE_AUDIT.md", "docs/bettracker2/audits/MM2_3C_SPORTMONKS_REDUCED_ENTITLEMENT_PROBE_AUDIT.md"), "scripts_generated": exists("scripts/mm2_3b_sportmonks_controlled_fixture_probe.py", "scripts/mm2_3c_sportmonks_reduced_entitlement_probe.py"), "external_api_calls": "yes", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "artifact_only", "production_migration_candidate": "later", "blockers": "Need timestamp-safe pre-kickoff use.", "next_dependency": "Pre-kickoff probe."},
        {"phase_id": "MM-2.3d", "title": "Pre-kickoff enriched probe", "purpose": "Test future fixtures and timestamp safety.", "status": "experimental", "main_finding": "Pre-kickoff enriched payloads were safe and rich; lineups are listed/probable, not confirmed.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_3D_SPORTMONKS_PREKICKOFF_ENRICHED_PROBE_AUDIT.md", "scripts/outputs/mm2_3d_sm_prekickoff_probe_raw.json"), "scripts_generated": exists("scripts/mm2_3d_sportmonks_prekickoff_enriched_probe.py"), "external_api_calls": "yes", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "artifact_only", "production_migration_candidate": "later", "blockers": "Need adapter and prompt integration.", "next_dependency": "Timestamp-gated adapter."},
        {"phase_id": "MM-2.4", "title": "Timestamp-gated enriched adapter", "purpose": "Convert SportMonks payload to compact safe Stage 1 blocks.", "status": "completed", "main_finding": "10/10 safe; lineups/formations/sidelined/weather available; confirmed_flag false for all.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_4_TIMESTAMP_GATED_ENRICHED_CONTEXT_ADAPTER_AUDIT.md", "scripts/outputs/mm2_4_enriched_stage1_blocks.json"), "scripts_generated": exists("scripts/mm2_4_timestamp_gated_enriched_context_adapter.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "artifact_only", "production_migration_candidate": "yes", "blockers": "Needs integration into DSR runner and refresh timing.", "next_dependency": "Prompt A/B packages."},
        {"phase_id": "MM-2.5", "title": "Enriched Prompt A/B Package Build", "purpose": "Build baseline vs enriched Stage 1 dry-run packages.", "status": "partial", "main_finding": "Enriched prompts passed leakage, but base_context join failed: baseline was event-only.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_5_ENRICHED_PROMPT_AB_PACKAGE_BUILD_AUDIT.md", "scripts/outputs/mm2_5_enriched_prompt_ab_summary.json"), "scripts_generated": exists("scripts/mm2_5_enriched_prompt_ab_package_build.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "artifact_only", "production_migration_candidate": "no", "blockers": "base_context_available_count=0 due sandboxed local DB SELECT.", "next_dependency": "MM-2.5b join repair."},
        {"phase_id": "MM-2.5b", "title": "Base Context Join Repair", "purpose": "Repair baseline v2 and enriched v2 full Stage 1 context.", "status": "completed", "main_finding": "10/10 base_context available; 10/10 enriched context; leakage 0; ready for MM-2.6 artifact-only mini-run.", "artifacts_generated": exists("docs/bettracker2/audits/MM2_5B_BASE_CONTEXT_JOIN_REPAIR_AUDIT.md", "scripts/outputs/mm2_5b_summary.json"), "scripts_generated": exists("scripts/mm2_5b_base_context_join_repair.py"), "external_api_calls": "no", "DSR_calls": "no", "DB_writes": "no", "production_safe": "no", "shadow_integrated": "shadow_runner_ready", "production_migration_candidate": "later", "blockers": "Not yet used in real DSR; production writes disabled.", "next_dependency": "MM-2.6 Stage 1 A/B mini-run."},
    ]


def integration_matrix() -> list[dict[str, Any]]:
    rows = [
        ("FT_1X2 TOA h2h", "MM-0/MM-1", "mm1_9_expanded_prompt_package_build.py", "mm1_9_expanded_input_packages.json", "yes", "yes", "yes", "later", "shadow_executed", "Used in MM-2.0 base context."),
        ("OU_GOALS_2_5 TOA totals point=2.5", "MM-0.1/MM-0.2", "mm1_8_toa_historical_backfill_controlled.py", "mm1_8_toa_backfill_market_board.json", "yes", "yes", "yes", "later", "shadow_executed", "Line preserved at 2.5."),
        ("BTTS discovery-only", "MM-0", "mm0_multi_market_inventory", "mm0_multi_market_inventory_rows.csv", "no", "no", "no", "no", "doc_only", "Not active."),
        ("Double Chance discovery-only", "MM-0", "mm0_multi_market_inventory", "mm0_multi_market_inventory_rows.csv", "no", "no", "no", "no", "doc_only", "Not active; no synthetic DC."),
        ("line/point preservation", "MM-0.3", "mm0_3_line_preservation_scaffold_audit.py", "mm0_3_line_preservation_scaffold_rows.csv", "yes", "yes", "yes", "yes", "production_candidate", "Needs tests in provider adapter."),
        ("market board", "MM-1.0/MM-1.8", "mm1_market_board_package_completion.py", "mm1_8_toa_backfill_market_board.json", "yes", "yes", "no_stage1", "later", "shadow_executed", "Stage 2 only; no Stage 1 odds."),
        ("Stage 1 baseline prompt", "MM-1", "mm1_9_expanded_prompt_package_build.py", "mm1_9_expanded_stage1_rendered_prompts.json", "yes", "yes", "yes", "later", "shadow_executed", "Base context only in MM-2.0."),
        ("Stage 2 compact prompt", "MM-1.2", "mm2_0_expanded_dsr_shadow_run.py", "mm2_0_stage2_compact_prompts.json", "yes", "yes", "not_in_stage1", "later", "shadow_executed", "Market board and odds only in Stage 2."),
        ("two-stage DSR harness", "MM-1/MM-2.0", "mm2_0_expanded_dsr_shadow_run.py", "mm2_0_run_lot_summary.json", "yes", "yes", "not_yet", "later", "shadow_executed", "84 serial calls."),
        ("market_only discipline", "MM-1.4/MM-2.0", "mm1_4_final_output_normalizer.py", "mm2_0_run_lot_summary.json", "yes", "yes", "yes", "yes", "shadow_executed", "market_only converted to 0 picks."),
        ("deterministic normalizer", "MM-1.4", "mm1_4_final_output_normalizer.py", "mm1_4_normalized_final_outputs.json", "yes", "yes", "yes", "yes", "production_candidate", "Good candidate with tests."),
        ("settlement evaluator", "MM-2.1", "mm2_1_settlement_performance_evaluation.py", "mm2_1_settlement_summary.json", "yes", "not_runtime", "not_runtime", "later", "settlement_tested", "Eval/backtest job only."),
        ("benchmark same-slice comparison", "MM-2.1", "mm2_1_settlement_performance_evaluation.py", "mm2_1_benchmark_comparison_summary.json", "artifact", "no", "no", "no", "artifact_only", "Diagnostic only."),
        ("latency diagnostics", "MM-2.0 latency", "mm2_0_latency_diagnostics.py", "mm2_0_latency_diagnostics_summary.json", "artifact", "no", "no", "later", "artifact_only", "Informs harness redesign."),
        ("ds_input compact proposal", "MM-2.2", "mm2_2_ds_input_visibility_audit.py", "mm2_2_compaction_proposal.json", "artifact", "no", "partially", "later", "artifact_only", "Not E2E tested."),
        ("SportMonks reduced include set", "MM-2.3c", "mm2_3c_sportmonks_reduced_entitlement_probe.py", "mm2_3c_sm_reduced_probe_summary.json", "artifact", "no", "yes", "later", "artifact_only", "Needs refresh job."),
        ("SportMonks lineups", "MM-2.4", "mm2_4_timestamp_gated_enriched_context_adapter.py", "mm2_4_lineups_context_rows.csv", "artifact", "no", "yes", "later", "shadow_runner_ready", "Listed/probable only."),
        ("SportMonks sidelined/injuries", "MM-2.4", "mm2_4_timestamp_gated_enriched_context_adapter.py", "mm2_4_availability_context_rows.csv", "artifact", "no", "yes", "later", "shadow_runner_ready", "No key_absence model."),
        ("SportMonks formations", "MM-2.4", "mm2_4_timestamp_gated_enriched_context_adapter.py", "mm2_4_formation_context_rows.csv", "artifact", "no", "yes", "later", "shadow_runner_ready", "Descriptive, not automatic pick."),
        ("SportMonks venue/weather", "MM-2.4", "mm2_4_timestamp_gated_enriched_context_adapter.py", "mm2_4_venue_weather_context_rows.csv", "artifact", "no", "yes", "later", "shadow_runner_ready", "Extreme weather none in sample."),
        ("timestamp gate", "MM-2.4", "mm2_4_timestamp_gated_enriched_context_adapter.py", "mm2_4_enriched_context_summary.json", "artifact", "no", "yes", "yes", "production_candidate", "Must remain hard gate."),
        ("enriched Stage 1 block", "MM-2.4", "mm2_4_timestamp_gated_enriched_context_adapter.py", "mm2_4_enriched_stage1_blocks.json", "artifact", "no", "yes", "later", "shadow_runner_ready", "No DSR run yet."),
        ("enriched prompt A/B packages", "MM-2.5b", "mm2_5b_base_context_join_repair.py", "mm2_5b_enriched_stage1_packages.json", "artifact", "no", "yes", "later", "shadow_runner_ready", "Ready for MM-2.6."),
        ("base context join", "MM-2.5b", "mm2_5b_base_context_join_repair.py", "mm2_5b_base_context_blocks.json", "artifact", "no", "yes", "later", "shadow_runner_ready", "Repaired via artifact targets."),
        ("production publication", "not_started", "", "", "no", "no", "no", "no", "production_blocked", "No production readiness."),
        ("Telegram/vault", "out_of_scope", "", "", "no", "no", "no", "no", "production_blocked", "Explicitly disabled."),
        ("bt2_daily_picks writes", "out_of_scope", "", "", "no", "no", "no", "no", "production_blocked", "Explicitly disabled."),
    ]
    return [
        {
            "component": r[0],
            "discovered_in": r[1],
            "implemented_in_script": r[2],
            "artifact_outputs": r[3],
            "integrated_into_shadow_flow": r[4],
            "used_by_current_DSR_flow": r[5],
            "used_by_enriched_prompt_flow": r[6],
            "production_ready": r[7],
            "integration_level": r[8],
            "notes": r[9],
        }
        for r in rows
    ]


def blockers() -> list[dict[str, Any]]:
    items = [
        ("Integrate enriched_sm_context into real DSR runner", "high", "MM-2.6", "Use mm2_5b packages in Stage 1 A/B; no Stage 2 yet."),
        ("Compact prompt E2E validation", "medium", "MM-2.6/MM-2.7", "Measure UNKNOWN/rationale quality before Stage 2."),
        ("Checkpoint/resume/concurrency", "medium", "harness", "Add timestamps, resume checkpoints, concurrency=2."),
        ("Refresh timing for lineups/sidelined/formations", "high", "SportMonks adapter", "Define pre-kickoff windows and stale-data policy."),
        ("Player importance model", "medium", "availability", "Do not populate key_absences until model exists."),
        ("TOA odds provider separation", "high", "market board", "Keep odds out of Stage 1; TOA remains odds source."),
        ("No target fixture statistics/events", "high", "adapter", "Maintain hard block."),
        ("Performance sample size", "high", "evaluation", "Expand before edge/ROI claims."),
        ("Discovery vs validation split", "high", "methodology", "Do not use discovery cohorts as validation proof."),
        ("Production publishing disabled", "high", "release", "No Telegram/vault/bt2_daily_picks until validated."),
    ]
    return [{"blocker": b, "severity": s, "owner_or_area": o, "next_dependency": n} for b, s, o, n in items]


def production_candidates() -> list[dict[str, Any]]:
    rows = [
        ("TOA market board builder", "Build market board with line preservation", "later", "Add retry/quota policy, tests, observability", "medium", "integration owner"),
        ("line preservation/canonicalizer", "Preserve OU point and canonical selections", "yes", "Unit tests and provider adapter wiring", "low", "data engineer"),
        ("timestamp-gated enriched context adapter", "Safe SM context compaction", "yes", "Refresh timing, hard excludes, schema tests", "medium", "data engineer"),
        ("compact prompt builders", "Reduce Stage 1/Stage 2 payloads", "later", "E2E A/B validation", "medium", "prompt engineer"),
        ("deterministic normalizer", "Normalize DSR outputs", "yes", "Contract tests, production schema", "low", "integration owner"),
        ("settlement evaluator", "Backtest/eval job", "later", "Separate from runtime; larger sample", "medium", "PM/data"),
        ("checkpoint/resume/concurrency harness", "Operational reliability", "later", "Implement before expanded DSR", "medium", "integration owner"),
        ("auditors/probes/dry-run builders", "Forensic artifact generation", "no", "Keep as research tools", "low", "PM"),
    ]
    return [{"script_or_artifact": r[0], "purpose": r[1], "production_candidate": r[2], "required_changes": r[3], "risk": r[4], "owner_next_task": r[5]} for r in rows]


def flow_readiness() -> list[dict[str, Any]]:
    rows = [
        ("current_tested_shadow_MM2_0", "candidate universe -> TOA market board -> Stage 1 base_context -> Stage 2 compact market board -> DSR -> normalizer -> behavior -> settlement", "shadow_executed", "No SportMonks enriched context."),
        ("MM2_5_initial_enriched_prompt_flow", "event_context -> enriched_sm_context prompt packages", "artifact_only_partial", "base_context join failed; not valid full A/B."),
        ("MM2_5b_full_stage1_context_flow", "artifact target -> base_context repair -> enriched_sm_context merge -> baseline/enriched v2 prompts", "shadow_runner_ready", "No DSR call yet."),
        ("target_MM2_6", "baseline v2 vs enriched v2 Stage 1 DSR mini-run", "ready_next", "Artifact-only, no Stage 2/odds."),
        ("production_flow", "refresh -> adapter -> DSR -> normalizer -> publication", "production_blocked", "No performance validation, no production writes."),
    ]
    return [{"flow": r[0], "description": r[1], "readiness": r[2], "notes": r[3]} for r in rows]


def script_inventory(phases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scripts = sorted((ROOT / "scripts").glob("mm*.py"))
    out = []
    for s in scripts:
        name = s.name
        out.append({
            "script": str(s.relative_to(ROOT)),
            "phase_hint": name.split("_")[0].upper().replace("MM", "MM-"),
            "exists": True,
            "role": "auditor_or_builder_or_runner",
            "production_candidate": "later" if name in {"mm1_4_final_output_normalizer.py", "mm2_4_timestamp_gated_enriched_context_adapter.py", "mm2_5b_base_context_join_repair.py"} else "no",
        })
    return out


def markdown(summary: dict[str, Any], phases: list[dict[str, Any]], matrix: list[dict[str, Any]]) -> str:
    mm25b = read_json(OUT / "mm2_5b_summary.json", {})
    return "\n".join([
        "# MM2_X Consolidated Findings and Integration Map",
        "",
        "## 1. Executive summary",
        "MM-0 through MM-2.5 established a reliable artifact/shadow research stack, but not production readiness. MM-2.0/MM-2.1 is the only fully executed DSR+settlement shadow flow. It used historical base_context and TOA market boards; it did not include SportMonks enriched context. MM-2.5 initially proved enriched prompt shape but exposed a base_context join gap. MM-2.5b repaired that gap artifact-only.",
        "",
        "## 2. Why this consolidation was needed",
        "The project is auditing methodology, not just data. A green dry-run is insufficient if the flow is incomplete; MM-2.5 was green but baseline lacked historical base_context.",
        "",
        "## 3. Scope and restrictions",
        "This consolidation is artifact-only: no DSR, no TOA, no SportMonks API, no DB writes, no production, no picks, no new settlement, no ROI recomputation, no Telegram/vault/bt2_daily_picks.",
        "",
        "## 4. Phase-by-phase inventory MM-0 to MM-2.5",
        "\n".join(f"- `{p['phase_id']}` {p['title']}: {p['status']}. {p['main_finding']} Blocker: {p['blockers']}" for p in phases),
        "",
        "## 5. Key discoveries",
        "- Multi-market: FT_1X2 confirmed; OU_GOALS_2_5 confirmed from TOA totals point=2.5; BTTS/DC remain discovery-only and inactive.",
        "- Performance: MM-2.0 generated 15 picks, all settled; global 6-9, ROI -20.13%; benchmark ROI -36.80%; DSR was less bad than benchmark but still negative; no edge proof.",
        "- Behavior: 42/42 Stage 1 OK, 42/42 Stage 2 OK, no timeouts, no model mismatch, market_only did not become pick.",
        "- Latency/cost: 84 sequential DSR calls, long prompts around 10k chars, high token load; need timestamps/checkpoint/resume/concurrency/compaction.",
        "- ds_input: MM-2.0 saw h2h/team_form/rest_days/season_aggregates but not lineups/injuries/formations; MM-2.2 proposed compaction.",
        "- SportMonks: raw signals existed but were absent from ds_input; reduced include set works; pre-kickoff safety works; MM-2.4 built safe enriched_sm_context.",
        "- MM-2.5: enriched prompts passed leakage but base_context join failed; MM-2.5b repaired it.",
        "",
        "## 6. Current tested shadow flow",
        "The actually tested MM-2.0/MM-2.1 flow is: candidate universe -> TOA market board -> Stage 1 baseline historical context -> Stage 2 compact market board -> DSR -> deterministic normalizer -> behavior analysis -> settlement. This flow did not include SportMonks enriched context.",
        "",
        "## 7. Enriched context discovery and integration status",
        "SportMonks lineups, sidelined/injuries, formations, venue/weather, and timestamp gates are adapter-ready and prompt-package-ready. They have not yet been used in a real DSR call.",
        "",
        "## 8. ds_input and prompt compaction status",
        "MM-2.2 showed redundancy and proposed compact Stage 1/Stage 2 payloads. MM-2.5b enriched prompts average about "
        f"`{mm25b.get('enriched_prompt_avg_chars')}` chars, below the reasonable dry-run threshold, but compact prompt E2E behavior is not yet validated.",
        "",
        "## 9. Market board status",
        "TOA market board supports FT_1X2 and OU2.5 with line preservation. It belongs in Stage 2, not Stage 1.",
        "",
        "## 10. DSR harness status",
        "The two-stage DSR harness executed reliably in MM-2.0 but is sequential and not yet wired to enriched_sm_context.",
        "",
        "## 11. Settlement/performance status",
        "Settlement is diagnostic only. n=15 does not prove edge, ROI, CLV, or production readiness.",
        "",
        "## 12. Latency/cost status",
        "Primary bottleneck is sequential external model calls; local artifact I/O is unlikely to dominate.",
        "",
        "## 13. Integration matrix",
        "\n".join(f"- `{r['component']}`: `{r['integration_level']}`; current DSR `{r['used_by_current_DSR_flow']}`; enriched flow `{r['used_by_enriched_prompt_flow']}`. {r['notes']}" for r in matrix),
        "",
        "## 14. What is already integrated",
        "FT_1X2/OU2.5 market board, line preservation, base_context Stage 1, compact Stage 2, two-stage DSR harness, deterministic normalizer, behavior analysis, and settlement evaluation are integrated in the tested shadow flow.",
        "",
        "## 15. What is not yet integrated",
        "SportMonks enriched context has not been used in a real DSR call; compact enriched prompt final has not been E2E tested; production writes/publication are disabled.",
        "",
        "## 16. Open blockers",
        "See `mm2_x_open_blockers.csv`. The top blockers are enriched DSR runner integration, refresh timing, checkpoint/resume/concurrency, player importance, larger validation sample, and production gating.",
        "",
        "## 17. Production migration candidates",
        "Candidates are line preservation, timestamp gate adapter, deterministic normalizer, compact prompt builders after A/B validation, settlement evaluator as backtest job, and checkpoint/resume/concurrency harness.",
        "",
        "## 18. Recommended next actions",
        "Run MM-2.6 Stage 1 A/B mini-run using MM-2.5b packages: baseline v2 historical base_context vs enriched v2 historical base_context + enriched_sm_context; no Stage 2, no odds, artifact-only. Measure UNKNOWN reduction and rationale quality only.",
        "",
        "## 19. What this proves",
        "The methodology now distinguishes discovered signals, artifact-ready components, shadow-executed components, settlement-tested components, and production-blocked components. MM-2.5b proves a real full Stage 1 A/B package is ready for a controlled mini-run.",
        "",
        "## 20. What this does not prove",
        "It does not prove edge, ROI, CLV, hit rate, production readiness, or that enriched context improves DSR decisions. That still requires controlled DSR A/B and later out-of-sample evaluation.",
        "",
    ])


def main() -> None:
    phases = phase_inventory()
    matrix = integration_matrix()
    blockers_rows = blockers()
    candidates = production_candidates()
    flow = flow_readiness()
    scripts = script_inventory(phases)
    mm25b = read_json(OUT / "mm2_5b_summary.json", {})
    summary = {
        "MM2_X_consolidated_findings_completed": True,
        "MM2_X_full_shadow_flow_integrated": False,
        "phase_rows": len(phases),
        "integration_components": len(matrix),
        "open_blockers": len(blockers_rows),
        "production_migration_candidates": sum(1 for r in candidates if r["production_candidate"] in {"yes", "later"}),
        "current_tested_shadow_flow": "MM-2.0/MM-2.1 base_context + TOA market board two-stage DSR; no SportMonks enriched context",
        "next_flow_ready": bool(mm25b.get("MM2_5b_ready_for_MM2_6")),
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
            "new_settlement": False,
            "new_roi_hit_rate": False,
        },
        "recommended_next_step": "MM-2.6 Stage 1 A/B mini-run using MM-2.5b baseline/enriched v2 packages; no Stage 2, no odds, artifact-only.",
    }
    write_json(OUT / "mm2_x_consolidated_findings_summary.json", summary)
    write_csv(OUT / "mm2_x_integration_matrix.csv", matrix)
    write_csv(OUT / "mm2_x_script_inventory.csv", scripts)
    write_csv(OUT / "mm2_x_flow_readiness_matrix.csv", flow)
    write_csv(OUT / "mm2_x_open_blockers.csv", blockers_rows)
    write_csv(OUT / "mm2_x_production_migration_candidates.csv", candidates)
    (AUDITS / "MM2_X_CONSOLIDATED_FINDINGS_AND_INTEGRATION_MAP.md").write_text(
        markdown(summary, phases, matrix),
        encoding="utf-8",
    )
    print("MM2_X_consolidated_findings_completed=", summary["MM2_X_consolidated_findings_completed"])
    print("MM2_X_full_shadow_flow_integrated=", summary["MM2_X_full_shadow_flow_integrated"])
    print("next_flow_ready=", summary["next_flow_ready"])


if __name__ == "__main__":
    main()

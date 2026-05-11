#!/usr/bin/env python3
"""
MM-2.6R.2 Enriched Signal Failure Analysis + Guardrail Repair.

Artifact-only auditor. It reads repaired MM-2.6R.1 outputs and MM-2.6R
prompt/package artifacts, classifies enriched-context failures, and writes
guardrail proposals. It does not call DSR, TOA, SportMonks, databases, vault,
production paths, Telegram, betting flows, Stage 2, or settlement code.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "scripts" / "outputs"
PROMPTS = ROOT / "prompts" / "bt2"
AUDITS = ROOT / "docs" / "bettracker2" / "audits"

SUMMARY_IN = OUT / "mm2_6r1_stage1_schema_repair_summary.json"
PARSED_IN = OUT / "mm2_6r1_stage1_ab_parsed_outputs_repaired.json"
VALIDATION_IN = OUT / "mm2_6r1_stage1_ab_validation_repaired.json"
COMPARISON_IN = OUT / "mm2_6r1_stage1_ab_comparison_rows_repaired.csv"
RATIONALE_IN = OUT / "mm2_6r1_stage1_ab_rationale_quality_rows_repaired.csv"
BASELINE_PROMPTS_IN = OUT / "mm2_6r_baseline_stage1_rendered_prompts.json"
ENRICHED_PROMPTS_IN = OUT / "mm2_6r_enriched_stage1_rendered_prompts.json"
BASELINE_PACKAGES_IN = OUT / "mm2_6r_baseline_stage1_packages.json"
ENRICHED_PACKAGES_IN = OUT / "mm2_6r_enriched_stage1_packages.json"
ENRICHED_CONTEXT_BLOCKS_IN = OUT / "mm2_6r_enriched_context_blocks.json"
LEAKAGE_IN = OUT / "mm2_6r_stage1_leakage_audit.csv"
ENRICHED_TEMPLATE_IN = PROMPTS / "mm2_stage1_enriched_user_prompt_template.txt"
SYSTEM_TEMPLATE_IN = PROMPTS / "mm1_stage1_system_prompt.txt"

INVENTED_ROWS_OUT = OUT / "mm2_6r2_invented_signal_rows.csv"
USAGE_ROWS_OUT = OUT / "mm2_6r2_enriched_usage_rows.csv"
UNKNOWN_ROWS_OUT = OUT / "mm2_6r2_unknown_persistence_rows.csv"
PROMPT_FINDINGS_OUT = OUT / "mm2_6r2_prompt_guardrail_findings.json"
ADAPTER_POLICY_OUT = OUT / "mm2_6r2_enriched_adapter_policy_v2.json"
VALIDATOR_RULES_OUT = OUT / "mm2_6r2_validator_v2_rules.json"
SUMMARY_OUT = OUT / "mm2_6r2_enriched_signal_failure_summary.json"
USER_PROMPT_DRAFT_OUT = PROMPTS / "mm2_stage1_enriched_user_prompt_template_guardrail_v2_draft.txt"
SYSTEM_PROMPT_DRAFT_OUT = PROMPTS / "mm2_stage1_system_prompt_guardrail_v2_draft.txt"
AUDIT_OUT = AUDITS / "MM2_6R2_ENRICHED_SIGNAL_FAILURE_ANALYSIS_AUDIT.md"

MARKETS = ("FT_1X2", "OU_GOALS_2_5")


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, default=str)
        fh.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


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


def truthy(value: Any) -> bool:
    return str(value).lower() in {"true", "1", "yes"}


def as_text(value: Any) -> str:
    if isinstance(value, list):
        return " | ".join(str(x) for x in value)
    return "" if value is None else str(value)


def norm(value: Any) -> str:
    return as_text(value).lower()


def package_index(path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(path)
    return {str(pkg["event_context"]["fixture_id"]): pkg for pkg in data.get("packages", [])}


def prompt_index(path: Path) -> dict[str, dict[str, Any]]:
    data = read_json(path)
    rows = data.get("rendered_prompts") or data.get("prompts") or data.get("records") or data
    if isinstance(rows, dict):
        rows = rows.get("prompts", [])
    return {str(row.get("fixture_id")): row for row in rows}


def parsed_index(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    data = read_json(path)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in data.get("repaired_outputs", []):
        out[(str(row.get("fixture_id")), str(row.get("variant")))] = row
    return out


def market_output(parsed_record: dict[str, Any], market: str) -> dict[str, Any]:
    parsed = parsed_record.get("parsed_repaired") or {}
    for item in parsed.get("market_outputs", []):
        if item.get("market_canonical") == market:
            return item
    return {}


def reasoning_text(parsed_record: dict[str, Any]) -> str:
    try:
        return parsed_record["raw_original"]["raw_response"]["choices"][0]["message"].get("reasoning_content", "")
    except (KeyError, IndexError, TypeError):
        return ""


def get_enriched_context(pkg: dict[str, Any]) -> dict[str, Any]:
    return pkg.get("enriched_sm_context") or {}


def visible_enriched_fields(ctx: dict[str, Any]) -> dict[str, Any]:
    lineups = ctx.get("lineups_context") or {}
    availability = ctx.get("availability_context") or {}
    formation = ctx.get("formation_context") or {}
    weather = ctx.get("venue_weather_context") or {}
    return {
        "lineups": {
            "available": lineups.get("available"),
            "confirmed_status": lineups.get("confirmed_status"),
            "home_listed_lineup_count": (lineups.get("home") or {}).get("listed_lineup_count"),
            "away_listed_lineup_count": (lineups.get("away") or {}).get("listed_lineup_count"),
            "signal_strength": lineups.get("signal_strength"),
            "signal_direction_by_market": lineups.get("signal_direction_by_market"),
        },
        "sidelined": {
            "available": availability.get("available"),
            "home_sidelined_count": (availability.get("home") or {}).get("sidelined_count"),
            "away_sidelined_count": (availability.get("away") or {}).get("sidelined_count"),
            "key_absences_home": availability.get("key_absences_home"),
            "key_absences_away": availability.get("key_absences_away"),
            "severe_absence_imbalance": availability.get("severe_absence_imbalance"),
            "signal_strength": availability.get("signal_strength"),
            "signal_direction_by_market": availability.get("signal_direction_by_market"),
        },
        "formations": {
            "formation_available": formation.get("formation_available"),
            "home_formation": formation.get("home_formation"),
            "away_formation": formation.get("away_formation"),
            "signal_strength": formation.get("signal_strength"),
            "signal_direction_by_market": formation.get("signal_direction_by_market"),
        },
        "weather": {
            "available": weather.get("available"),
            "weather_description": weather.get("weather_description"),
            "rain_or_snow_flag": weather.get("rain_or_snow_flag"),
            "extreme_weather_flag": weather.get("extreme_weather_flag"),
            "signal_strength": weather.get("signal_strength"),
            "signal_direction_by_market": weather.get("signal_direction_by_market"),
        },
    }


def fields_available(ctx: dict[str, Any]) -> dict[str, bool]:
    lineups = ctx.get("lineups_context") or {}
    availability = ctx.get("availability_context") or {}
    formation = ctx.get("formation_context") or {}
    weather = ctx.get("venue_weather_context") or {}
    return {
        "lineups": bool(lineups.get("available")),
        "sidelined": bool(availability.get("available")),
        "formations": bool(formation.get("formation_available")),
        "weather": bool(weather.get("available")),
    }


def field_signal(ctx: dict[str, Any], field: str, market: str) -> tuple[str, str]:
    mapping = {
        "lineups": "lineups_context",
        "sidelined": "availability_context",
        "formations": "formation_context",
        "weather": "venue_weather_context",
    }
    block = ctx.get(mapping[field]) or {}
    direction = (block.get("signal_direction_by_market") or {}).get(market, "unknown")
    strength = block.get("signal_strength") or "none"
    return str(direction), str(strength)


def used_fields_from_comparison(row: dict[str, str]) -> list[str]:
    fields = []
    if truthy(row.get("enriched_mentions_lineups")):
        fields.append("lineups")
    if truthy(row.get("enriched_mentions_sidelined")):
        fields.append("sidelined")
    if truthy(row.get("enriched_mentions_formations")):
        fields.append("formations")
    if truthy(row.get("enriched_mentions_weather")):
        fields.append("weather")
    return fields


def field_use_valid(ctx: dict[str, Any], field: str, market: str, signal_summary: str, missing_reason: str) -> bool:
    direction, strength = field_signal(ctx, field, market)
    if direction not in {"unknown", "neutral", "", None} and strength != "none":
        return True
    text = f"{signal_summary} {missing_reason}".lower()
    if field == "lineups":
        confirmed = (ctx.get("lineups_context") or {}).get("confirmed_status") == "confirmed"
        return confirmed and "confirmed" in text
    if field == "weather":
        extreme = bool((ctx.get("venue_weather_context") or {}).get("extreme_weather_flag"))
        return extreme and ("extreme" in text or "under" in text)
    if field == "sidelined":
        avail = ctx.get("availability_context") or {}
        return bool(avail.get("key_absences_home") or avail.get("key_absences_away"))
    return False


def classify_invented_claim(ctx: dict[str, Any], row: dict[str, str], market_output_row: dict[str, Any]) -> tuple[str, str, str, str]:
    summary = as_text(market_output_row.get("signal_summary"))
    reason = as_text(market_output_row.get("missing_signal_reason"))
    text = f"{summary} {reason}".lower()
    visible = visible_enriched_fields(ctx)
    if "key player" in text or "key absence" in text:
        return (
            "unsupported_player_importance",
            "key player/key absence impact",
            "key_absences_home/key_absences_away are null and no player importance model is present.",
            "player_importance_model plus key_absences_home/key_absences_away",
        )
    if "confirmed lineup" in text or ("confirmed" in text and "probable" not in text):
        return (
            "unsupported_player_importance",
            "confirmed lineup claim",
            f"confirmed_status is {visible['lineups'].get('confirmed_status')}, not confirmed.",
            "confirmed_status=confirmed",
        )
    if "tactical edge" in text or "tactical advantage" in text or "formation advantage" in text:
        formation = ctx.get("formation_context") or {}
        if not formation.get("formation_available") or formation.get("signal_strength") == "none":
            return (
                "unsupported_tactical_edge",
                "formation/tactical edge claim",
                "formation_context is unavailable or signal_strength=none; no tactical rule was supplied.",
                "formation_available=true plus explicit signal_direction_by_market and non-none signal_strength",
            )
    if "weather favors" in text or "rain favors" in text or "conditions favor" in text:
        weather = ctx.get("venue_weather_context") or {}
        if weather.get("available") and not weather.get("extreme_weather_flag") and weather.get("signal_strength") == "none":
            return (
                "unsupported_weather_edge",
                "weather edge claim",
                "weather is descriptive and extreme_weather_flag=false; weather_signal_strength=none.",
                "extreme_weather_flag=true plus conservative weather signal rule",
            )
    if "injury crisis" in text or "absence crisis" in text or "depleted" in text or "key absence" in text:
        avail = ctx.get("availability_context") or {}
        if not (avail.get("key_absences_home") or avail.get("key_absences_away")):
            return (
                "unsupported_absence_edge",
                "availability/absence context used without directional support",
                "absence counts are descriptive, key_absences are null, and availability signal_strength=none.",
                "player_importance_model or severe_absence_imbalance rule emitting explicit signal_direction_by_market",
            )
    if "all blocks unavailable" in text:
        return (
            "other",
            "all blocks unavailable/neutral claim",
            "Several enriched blocks are available but explicitly non-directional; availability is not the same as usable signal.",
            "adapter-provided is_directional flags per block",
        )
    return (
        "minor_overinterpretation",
        "descriptive enriched context included in signal narrative",
        "The output used descriptive/non-directional enriched facts in signal_summary or missing_signal_reason even though lineups/formations/weather had no admissible directional signal.",
        "explicit block-level directional signal fields, confirmed_status=confirmed for lineup use, or extreme_weather_flag=true for weather use",
    )


def unknown_reason(ctx: dict[str, Any], row: dict[str, str]) -> str:
    market = row["market_canonical"]
    used = used_fields_from_comparison(row)
    if used and truthy(row.get("enriched_invented_signal_flag")):
        return "model_ignored_context"
    field_avail = fields_available(ctx)
    signals = [field_signal(ctx, f, market) for f in field_avail if field_avail[f]]
    if signals and all(direction in {"unknown", "neutral", ""} or strength == "none" for direction, strength in signals):
        if market == "OU_GOALS_2_5" and field_avail.get("weather") and not (ctx.get("venue_weather_context") or {}).get("extreme_weather_flag"):
            return "weather_not_extreme"
        if field_avail.get("lineups") and (ctx.get("lineups_context") or {}).get("confirmed_status") != "confirmed":
            return "no_confirmed_lineups"
        if field_avail.get("sidelined") and not ((ctx.get("availability_context") or {}).get("key_absences_home") or (ctx.get("availability_context") or {}).get("key_absences_away")):
            return "no_player_importance_model"
        return "enriched_non_directional"
    if field_avail.get("formations"):
        return "formations_descriptive_only"
    return "other"


def prompt_guardrail_findings(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    prompt = f"{system_prompt}\n\n{user_prompt}"
    checks = [
        (
            "formation_direction_without_rule",
            ["Formation and weather hints are descriptive context, not automatic picks."],
            "Present, but could be stronger: require explicit signal_direction_by_market and non-none signal_strength before any formation mention can enter signal_summary.",
        ),
        (
            "key_absence_without_player_importance",
            ["key_absences_home and key_absences_away are null unless a player importance model is present", "Do not infer key-player impact"],
            "Present, but validator should reject key-player language when key_absences are null.",
        ),
        (
            "probable_as_confirmed",
            ["Treat listed players as unconfirmed unless confirmed_status is \"confirmed\""],
            "Present and clear; add output-facing rule: do not cite lineups as a signal unless confirmed_status=confirmed and adapter emits direction.",
        ),
        (
            "non_extreme_weather_as_signal",
            ["Extreme weather may be noted only when the payload explicitly flags it"],
            "Present but permissive; add explicit no weather-favors-under language unless extreme_weather_flag=true.",
        ),
        (
            "availability_counts_as_direction",
            ["Absence counts are descriptive counts only"],
            "Present; missing severe_absence_imbalance threshold and adapter-emitted boolean gate.",
        ),
        (
            "unconfirmed_lineups_overvalued",
            ["listed/probable starters", "unconfirmed"],
            "Present; add no player names in enriched prompt and no XI quality inference without player importance model.",
        ),
        (
            "descriptive_context_in_signal_summary",
            ["If the context does not provide enough independent non-market signal"],
            "Residual risk: prompt does not forbid adding non-directional enriched facts to signal_summary. This enabled invalid 'used context' rows without true signal.",
        ),
    ]
    findings = []
    for key, needles, note in checks:
        present = all(n in prompt for n in needles)
        findings.append(
            {
                "finding_id": key,
                "guardrail_present": present,
                "risk_level": "medium" if present else "high",
                "evidence_or_gap": note,
                "recommended_patch": "Make enriched blocks admissible only when adapter emits explicit directional gate fields; otherwise allow them only in missing_signal_reason as non-directional blockers.",
            }
        )
    return {
        "generated_at_utc": utc_now(),
        "input_prompts": [str(SYSTEM_TEMPLATE_IN.relative_to(ROOT)), str(ENRICHED_TEMPLATE_IN.relative_to(ROOT))],
        "overall_assessment": "The current prompt contains many correct guardrails, but it leaves a soft gap: descriptive enriched facts can still be narrated as if they were evaluative signal.",
        "findings": findings,
    }


def adapter_policy_v2() -> dict[str, Any]:
    return {
        "generated_at_utc": utc_now(),
        "policy_id": "mm2_6r2_enriched_adapter_policy_v2",
        "artifact_only_proposal": True,
        "global_policy": {
            "emit_player_names": False,
            "emit_raw_player_payload": False,
            "each_block_must_emit": ["available", "descriptive_only", "is_directional", "signal_strength", "signal_direction_by_market", "allowed_markets"],
            "default_when_no_rule": {"is_directional": False, "signal_strength": "none", "signal_direction_by_market": {m: "unknown" for m in MARKETS}},
        },
        "lineups_context": {
            "policy": [
                "Listed/probable starters are descriptive.",
                "No directional signal if confirmed_status != confirmed.",
                "No player names in prompt.",
                "No XI quality inference without player importance model.",
            ],
            "directional_gate": "confirmed_status=confirmed AND explicit adapter rule emits is_directional=true",
        },
        "availability_sidelined": {
            "policy": [
                "Counts are descriptive.",
                "No key_absences without player importance model.",
                "Weak signal only if a severe imbalance rule is met.",
            ],
            "proposed_threshold": {
                "severe_absence_imbalance_min": 3,
                "same_position_severe_absence_imbalance_min": 2,
                "requires_player_importance_model_for_key_absence_language": True,
                "without_player_importance_max_signal_strength": "weak",
            },
        },
        "formations": {
            "policy": [
                "Descriptive only by default.",
                "No directional FT_1X2 signal without explicit future rule.",
                "Formation context may affect OU_GOALS_2_5 only if a conservative adapter rule emits signal_direction_by_market.",
            ],
        },
        "weather": {
            "policy": [
                "No signal if weather is not extreme.",
                "Extreme weather may emit weak under_2_5 only when extreme_weather_flag=true.",
            ],
            "proposed_threshold": {
                "extreme_weather_flag_required": True,
                "max_signal_strength": "weak",
                "allowed_direction": {"OU_GOALS_2_5": "under_2_5"},
            },
        },
    }


def validator_rules_v2() -> dict[str, Any]:
    return {
        "generated_at_utc": utc_now(),
        "ruleset_id": "mm2_6r2_validator_v2_rules",
        "mode": "reject_or_flag_stage1_outputs_artifact_only_proposal",
        "rules": [
            {"id": "no_key_player_missing_without_key_absences", "severity": "reject", "pattern": r"key player|key .*missing|important .*missing", "condition": "key_absences_home is null and key_absences_away is null"},
            {"id": "no_confirmed_lineup_when_unconfirmed", "severity": "reject", "pattern": r"confirmed lineup|confirmed starters|confirmed XI", "condition": "confirmed_status != confirmed"},
            {"id": "no_strong_tactical_advantage_without_signal", "severity": "reject", "pattern": r"strong tactical advantage|tactical edge|formation advantage", "condition": "formation_context.signal_strength == none"},
            {"id": "no_weather_favors_under_without_extreme_flag", "severity": "reject", "pattern": r"weather .*under|rain .*under|conditions .*under", "condition": "extreme_weather_flag == false"},
            {"id": "no_injury_crisis_without_severe_imbalance", "severity": "reject", "pattern": r"injury crisis|absence crisis|depleted", "condition": "severe_absence_imbalance rule not met"},
            {"id": "no_player_names_not_present_in_prompt", "severity": "reject", "pattern": "named_entity_player", "condition": "player name absent from rendered prompt OR adapter policy disallows player names"},
            {"id": "no_stage1_market_or_odds_mentions", "severity": "reject", "pattern": r"odds|bookmaker|price|benchmark|edge|value|favorite|market board|stage 2|pick|stake", "condition": "always in Stage 1"},
            {"id": "no_non_directional_enriched_facts_in_signal_summary", "severity": "flag", "pattern": r"lineups|formations|weather|availability|sidelined|injur", "condition": "referenced enriched block has is_directional=false or signal_strength=none"},
        ],
    }


def user_prompt_draft() -> str:
    return """Evaluate this football event in BT2 MM-2 Stage 1 enriched mode.

Use only the JSON payload below. The payload must not contain market quote data, bookmaker data, benchmark fields, fixture results, scores, live data, events, statistics, predictions, xG, pressure, or timeline fields.

Core Stage 1 rule:
- If the context does not provide enough independent non-market signal for a market, return unknown for that market.
- Do not infer with data that is absent.
- Do not create rationale from facts not present in the input.
- Do not invent missing h2h, team form, rest days, season aggregates, player importance, odds, prices, favorites, value, edge, tactical advantage, weather effect, or key absence impact.

Enriched context admissibility rule:
- An enriched block may affect context_lean, context_confidence, non_market_signal_count, or signal_summary only when that block explicitly has signal_strength != "none" and signal_direction_by_market for the evaluated market is not "unknown" or "neutral".
- If enriched context is descriptive or non-directional, keep context_lean unknown or rely only on base_context signals.
- Non-directional enriched facts may be used only to explain missing_signal_reason, and only as non-directional blockers.

Lineups/probable starters rule:
- SportMonks type.code = "lineup" means listed/probable starters.
- Listed/probable starters are not confirmed starters unless confirmed_status is "confirmed".
- Do not infer player quality, XI quality, team strength, tactical edge, or key-player effect from listed/probable lineups.
- Do not cite lineups as a directional signal unless confirmed_status is "confirmed" and the adapter provides an explicit directional signal for the market.

Availability/sidelined rule:
- Absence counts are descriptive counts only.
- key_absences_home and key_absences_away are null unless a player importance model is present.
- Do not infer key absences, injury crisis, depleted squad, or player importance from names, positions, or counts.
- Absence counts do not imply edge unless severe_absence_imbalance=true and the adapter emits explicit signal_direction_by_market.

Formation/weather rule:
- Formations are descriptive unless explicit signal_direction_by_market is provided for the evaluated market.
- Do not infer FT_1X2 tactical advantage from formations.
- Weather is descriptive unless extreme_weather_flag=true.
- Do not say weather favors under unless extreme_weather_flag=true and the adapter emits an OU_GOALS_2_5 under_2_5 signal.

Analyze only:
- FT_1X2
- OU_GOALS_2_5

Do not activate BTTS or DOUBLE_CHANCE. Do not synthesize Double Chance. Do not propose bets, staking, parlays, Telegram copy, production actions, or picks.

INPUT:
{
  "event_context": {{event_context_json}},
  "base_context_available": {{base_context_available_json}},
  "base_context_join": {{base_context_join_json}},
  "base_context": {{base_context_json}},
  "enriched_sm_context": {{enriched_sm_context_json}},
  "supported_markets": {{supported_markets_json}},
  "leakage_flags": {{leakage_flags_json}}
}

Return strict JSON only in the Stage 1 schema:
{
  "event_id": "string",
  "odds_visible": false,
  "market_outputs": [
    {
      "market_canonical": "FT_1X2",
      "context_lean": "home|draw|away|unknown",
      "context_confidence": "none|low|medium|high",
      "non_market_signal_count": 0,
      "signal_summary": ["string"],
      "missing_signal_reason": "string|null",
      "context_unknown": true
    },
    {
      "market_canonical": "OU_GOALS_2_5",
      "context_lean": "over_2_5|under_2_5|unknown",
      "context_confidence": "none|low|medium|high",
      "non_market_signal_count": 0,
      "signal_summary": ["string"],
      "missing_signal_reason": "string|null",
      "context_unknown": true
    }
  ]
}
"""


def system_prompt_draft() -> str:
    return """You are BT2 MM-2 Stage 1 Guardrail v2, a disciplined pre-match football evaluator.

You are evaluating safe pre-match context only. You do not see odds, bookmaker prices, consensus prices, market benchmarks, market favorites, picks, stakes, or production decisions.

Your task is not to choose by price. Your task is to decide whether the provided non-market context creates an independent lean for each supported market.

Supported active markets:
- FT_1X2 with allowed context_lean values: home, draw, away, unknown.
- OU_GOALS_2_5 with allowed context_lean values: over_2_5, under_2_5, unknown.

Excluded markets:
- BTTS is discovery-only and must not be evaluated, selected, inferred, or mentioned as active.
- DOUBLE_CHANCE is discovery-only and must not be evaluated, selected, synthesized from FT_1X2, or mentioned as active.

Rules:
- Use only data present in the user payload.
- Do not use external knowledge, memory, news, standings, injuries, lineups, form, statistics, or assumptions unless explicitly present in the payload and marked safe.
- Do not infer odds, benchmarks, probabilities, favorites, value, or edge.
- Do not infer player quality or key absences unless the payload explicitly provides key_absences or player importance fields.
- Probable/listed lineups are not confirmed lineups.
- Formations are descriptive unless explicit signal_direction_by_market is provided for the evaluated market.
- Weather is descriptive unless extreme_weather_flag=true and a conservative adapter signal is present.
- Absence counts do not imply edge unless severe_absence_imbalance=true and the adapter emits explicit signal_direction_by_market.
- Do not put descriptive-only enriched facts in signal_summary as if they were signal.
- If enriched context is non-directional, keep context_lean unknown or rely only on base_context.
- If the safe context is weak, incomplete, unavailable, or ambiguous, return context_lean: unknown.
- unknown is valid and preferred over inventing signal.
- Evaluate FT_1X2 and OU_GOALS_2_5 separately.
- A lean requires explicit non-market signal in the payload.
- If leakage flags indicate HIGH_RISK_LEAKAGE, mark every market unknown with context_confidence: none.
- Do not propose picks, parlays, combinadas, staking, bets, Telegram copy, or production actions.
- Return strict JSON only. No markdown, no prose outside JSON, no comments.

Required JSON shape:
{
  "event_id": "string",
  "odds_visible": false,
  "market_outputs": [
    {
      "market_canonical": "FT_1X2",
      "context_lean": "home|draw|away|unknown",
      "context_confidence": "none|low|medium|high",
      "non_market_signal_count": 0,
      "signal_summary": ["string"],
      "missing_signal_reason": "string|null",
      "context_unknown": true
    },
    {
      "market_canonical": "OU_GOALS_2_5",
      "context_lean": "over_2_5|under_2_5|unknown",
      "context_confidence": "none|low|medium|high",
      "non_market_signal_count": 0,
      "signal_summary": ["string"],
      "missing_signal_reason": "string|null",
      "context_unknown": true
    }
  ]
}
"""


def build_audit_md(summary: dict[str, Any], invented_rows: list[dict[str, Any]], usage_rows: list[dict[str, Any]], unknown_rows: list[dict[str, Any]], prompt_findings: dict[str, Any], policy: dict[str, Any], validator: dict[str, Any]) -> str:
    sev_counts = Counter(row["severity"] for row in invented_rows)
    usage_valid = sum(1 for row in usage_rows if truthy(row["use_was_valid"]))
    unknown_counts = Counter(row["reason_unknown_remained"] for row in unknown_rows)
    root_causes = "\n".join(f"- {cause}" for cause in summary["root_causes"])
    invented_lines = "\n".join(
        f"- {r['fixture_id']} {r['market_canonical']}: {r['severity']} - {r['invented_claim']}"
        for r in invented_rows
    ) or "- No invented signal rows."
    retry_note = (
        "A stricter patch can plausibly remove invented signals and at least one valid enriched usage exists."
        if summary["enriched_should_be_retried"]
        else "Do not retry DSR yet: no valid enriched usage was observed, so the retry criteria are not met even though a stricter patch can plausibly reduce invented narratives."
    )
    return f"""# MM-2.6R.2 Enriched Signal Failure Analysis Audit

## 1. Executive summary

MM-2.6R.2 completed an artifact-only failure analysis over the repaired MM-2.6R.1 Stage 1 A/B outputs. The harness is schema-reliable after repair, but enriched_sm_context did not reduce UNKNOWN and every detected enriched-context usage was invalid or non-useful.

Final answer: the failure is primarily a prompt/adapter boundary problem over descriptive enriched data, not proof that enriched_sm_context has no future value. The current adapter exposed mostly non-directional context, and the prompt allowed DSR to narrate that descriptive context as if it were useful signal.

## 2. Scope and restrictions

- Artifact-only.
- No DSR, TOA, SportMonks API, external calls, DB writes, production, bt2_daily_picks, Telegram, vault, bets, tennis, Stage 2, picks, settlement, ROI, or hit-rate analysis.
- No productive logic was modified.

## 3. Inputs used

- `scripts/outputs/mm2_6r1_stage1_schema_repair_summary.json`
- `scripts/outputs/mm2_6r1_stage1_ab_parsed_outputs_repaired.json`
- `scripts/outputs/mm2_6r1_stage1_ab_validation_repaired.json`
- `scripts/outputs/mm2_6r1_stage1_ab_comparison_rows_repaired.csv`
- `scripts/outputs/mm2_6r1_stage1_ab_rationale_quality_rows_repaired.csv`
- `scripts/outputs/mm2_6r_baseline_stage1_rendered_prompts.json`
- `scripts/outputs/mm2_6r_enriched_stage1_rendered_prompts.json`
- `scripts/outputs/mm2_6r_baseline_stage1_packages.json`
- `scripts/outputs/mm2_6r_enriched_stage1_packages.json`
- `scripts/outputs/mm2_6r_enriched_context_blocks.json`
- `scripts/outputs/mm2_6r_stage1_leakage_audit.csv`
- `prompts/bt2/mm2_stage1_enriched_user_prompt_template.txt`
- `prompts/bt2/mm1_stage1_system_prompt.txt`

## 4. MM-2.6R.1 recap

- schema_ok_before: {summary['mm2_6r1_recap']['schema_ok_before']}/20
- schema_ok_after: {summary['mm2_6r1_recap']['schema_ok_after']}/20
- auto_repaired_count: {summary['mm2_6r1_recap']['auto_repaired_count']}
- forbidden_leakage_count: {summary['mm2_6r1_recap']['forbidden_leakage_count']}
- unknown_reduction_count: {summary['mm2_6r1_recap']['unknown_reduction_count']}
- enriched_context_used_count: {summary['mm2_6r1_recap']['enriched_context_used_count']}
- invented_signal_count: {summary['mm2_6r1_recap']['invented_signal_count']}

## 5. Invented signal analysis

Invented rows: {len(invented_rows)}. Severity counts: {dict(sev_counts)}.

{invented_lines}

## 6. Valid enriched usage analysis

Enriched usage rows: {len(usage_rows)}. Valid usage rows: {usage_valid}. The detected usage did not change context_lean, did not change confidence, did not reduce UNKNOWN, and did not improve rationale quality.

## 7. Why UNKNOWN did not reduce

UNKNOWN persistence was driven by non-directional enriched data and missing gates. Reason counts: {dict(unknown_counts)}.

## 8. Prompt guardrail findings

{prompt_findings['overall_assessment']} The residual prompt gap is that descriptive context was not explicitly barred from `signal_summary`.

## 9. Adapter policy v2

The proposed adapter policy requires block-level directional gates, hides player names, treats probable lineups as descriptive, forbids key-absence language without player importance, treats formations as descriptive, and allows weather as weak OU2.5 input only under `extreme_weather_flag=true`.

## 10. Validator v2 rules

Validator v2 proposes reject/flag rules for unsupported key-player language, confirmed-lineup claims, tactical edge, weather-under claims, injury-crisis language, player names, odds/market/benchmark references, and descriptive enriched facts in `signal_summary`.

## 11. Recommendation

Do not move to Stage 2. Patch adapter/prompt/validator first. `enriched_should_be_retried={summary['enriched_should_be_retried']}`. {retry_note}

## 12. What this proves

- MM-2.6R.1 repaired schema reliability enough for interpretation.
- The observed enriched usage did not provide valid incremental Stage 1 signal.
- Descriptive enriched blocks can trigger rationale overuse unless gated.

## 13. What this does not prove

- It does not prove enriched_sm_context can never be useful.
- It does not prove any betting edge.
- It does not validate Stage 2, picks, settlement, ROI, hit rate, production readiness, or market performance.

## 14. Next step

Implement guardrail v2 in adapter/prompt/validator drafts only, inspect rendered prompts/packages, and only then decide whether a new Stage 1 artifact-only A/B is justified.

## Root causes

{root_causes}

## Output artifacts

- `scripts/outputs/mm2_6r2_invented_signal_rows.csv`
- `scripts/outputs/mm2_6r2_enriched_usage_rows.csv`
- `scripts/outputs/mm2_6r2_unknown_persistence_rows.csv`
- `scripts/outputs/mm2_6r2_prompt_guardrail_findings.json`
- `scripts/outputs/mm2_6r2_enriched_adapter_policy_v2.json`
- `scripts/outputs/mm2_6r2_validator_v2_rules.json`
- `scripts/outputs/mm2_6r2_enriched_signal_failure_summary.json`
- `prompts/bt2/mm2_stage1_enriched_user_prompt_template_guardrail_v2_draft.txt`
- `prompts/bt2/mm2_stage1_system_prompt_guardrail_v2_draft.txt`
"""


def main() -> None:
    summary_in = read_json(SUMMARY_IN)
    _validation = read_json(VALIDATION_IN)
    _baseline_prompts = prompt_index(BASELINE_PROMPTS_IN)
    _enriched_prompts = prompt_index(ENRICHED_PROMPTS_IN)
    _baseline_packages = package_index(BASELINE_PACKAGES_IN)
    enriched_packages = package_index(ENRICHED_PACKAGES_IN)
    _enriched_context_blocks = read_json(ENRICHED_CONTEXT_BLOCKS_IN)
    _leakage_rows = read_csv(LEAKAGE_IN)
    comparison_rows = read_csv(COMPARISON_IN)
    _rationale_rows = read_csv(RATIONALE_IN)
    parsed = parsed_index(PARSED_IN)
    system_prompt = read_text(SYSTEM_TEMPLATE_IN)
    enriched_prompt = read_text(ENRICHED_TEMPLATE_IN)

    invented_rows: list[dict[str, Any]] = []
    usage_rows: list[dict[str, Any]] = []
    unknown_rows: list[dict[str, Any]] = []

    for row in comparison_rows:
        fid = str(row["fixture_id"])
        market = row["market_canonical"]
        pkg = enriched_packages[fid]
        ctx = get_enriched_context(pkg)
        parsed_record = parsed.get((fid, "enriched_v2"), {})
        output = market_output(parsed_record, market)
        signal_summary = as_text(output.get("signal_summary"))
        rationale = as_text(output.get("missing_signal_reason"))
        reasoning = reasoning_text(parsed_record)

        if truthy(row.get("enriched_invented_signal_flag")):
            severity, claim, unsupported, needed = classify_invented_claim(ctx, row, output)
            invented_rows.append(
                {
                    "fixture_id": fid,
                    "market_canonical": market,
                    "variant": "enriched_v2",
                    "enriched_fields_visible": json.dumps(visible_enriched_fields(ctx), ensure_ascii=False, default=str),
                    "DSR_signal_summary": signal_summary,
                    "DSR_rationale": rationale,
                    "DSR_reasoning_excerpt": re.sub(r"\s+", " ", reasoning).strip()[:900],
                    "invented_claim": claim,
                    "why_unsupported": unsupported,
                    "source_fields_that_would_be_needed": needed,
                    "severity": severity,
                }
            )

        if truthy(row.get("enriched_used_any_context")):
            used_fields = used_fields_from_comparison(row)
            valid_by_field = {
                field: field_use_valid(ctx, field, market, signal_summary, rationale) for field in used_fields
            }
            use_valid = bool(valid_by_field) and all(valid_by_field.values())
            quality = "invalid" if truthy(row.get("enriched_invented_signal_flag")) else (
                "improved" if row.get("ab_classification") == "enriched_improved" else (
                    "worsened" if row.get("ab_classification") in {"enriched_invalid", "enriched_confused"} else "neutral"
                )
            )
            usage_rows.append(
                {
                    "fixture_id": fid,
                    "market": market,
                    "enriched_field_used": "|".join(used_fields),
                    "use_was_valid": use_valid,
                    "changed_context_lean": truthy(row.get("context_lean_changed")),
                    "changed_confidence": truthy(row.get("confidence_changed")),
                    "reduced_unknown": truthy(row.get("unknown_reduced")),
                    "rationale_quality_impact": quality,
                    "field_validity": json.dumps(valid_by_field, ensure_ascii=False),
                    "visible_field_availability": json.dumps(fields_available(ctx), ensure_ascii=False),
                }
            )

        added_data_available = any(fields_available(ctx).values())
        unknown_rows.append(
            {
                "fixture_id": fid,
                "market": market,
                "baseline_unknown": row.get("baseline_context_unknown"),
                "enriched_unknown": row.get("enriched_context_unknown"),
                "enriched_added_data_available": added_data_available,
                "reason_unknown_remained": unknown_reason(ctx, row) if truthy(row.get("enriched_context_unknown")) else "other",
                "reason_unknown_remained_detail": "Rows with enriched_unknown=false are retained for full fixture/market coverage; reason=other means UNKNOWN did not persist for this market.",
                "base_signal_summary": row.get("baseline_signal_summary"),
                "enriched_signal_summary": row.get("enriched_signal_summary"),
            }
        )

    prompt_findings = prompt_guardrail_findings(system_prompt, enriched_prompt)
    policy = adapter_policy_v2()
    validator = validator_rules_v2()

    invented_count = len(invented_rows)
    usage_valid_count = sum(1 for row in usage_rows if truthy(row["use_was_valid"]))
    usage_any_count = len(usage_rows)
    unknown_reduction_count = sum(1 for row in comparison_rows if truthy(row.get("unknown_reduced")))

    root_causes = [
        "Adapter exposed mostly descriptive enriched blocks with signal_strength=none and signal_direction_by_market=unknown.",
        "Prompt correctly warned against many inferential errors, but did not hard-gate descriptive enriched facts out of signal_summary.",
        "No player importance model was present, so sidelined counts could not support key-absence claims.",
        "Lineups were probable_or_unconfirmed, so they could not support confirmed-XI or player-quality inference.",
        "Weather was non-extreme in the observed invented rows, so it could not support an OU2.5 weather lean.",
        "Formation context was unavailable or descriptive-only, so it could not support tactical edge.",
    ]
    patch_can_plausibly_remove_invented = bool(invented_count > 0 and len(prompt_findings["findings"]) > 0)
    cost_is_acceptable = True
    enriched_has_some_valid_usage = usage_valid_count > 0
    enriched_should_be_retried = bool(
        patch_can_plausibly_remove_invented
        and enriched_has_some_valid_usage
        and cost_is_acceptable
    )
    enriched_should_remain_artifact_only = bool(invented_count > 0 and usage_valid_count == 0)
    summary = {
        "generated_at_utc": utc_now(),
        "mode": "mm2_6r2_enriched_signal_failure_analysis_artifact_only",
        "MM2_6r2_enriched_signal_failure_analysis_completed": True,
        "inputs_used": [
            str(p.relative_to(ROOT))
            for p in [
                SUMMARY_IN,
                PARSED_IN,
                VALIDATION_IN,
                COMPARISON_IN,
                RATIONALE_IN,
                BASELINE_PROMPTS_IN,
                ENRICHED_PROMPTS_IN,
                BASELINE_PACKAGES_IN,
                ENRICHED_PACKAGES_IN,
                ENRICHED_CONTEXT_BLOCKS_IN,
                LEAKAGE_IN,
                ENRICHED_TEMPLATE_IN,
                SYSTEM_TEMPLATE_IN,
            ]
        ],
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
            "picks": False,
            "settlement": False,
            "roi_hit_rate": False,
        },
        "mm2_6r1_recap": {
            "schema_ok_before": summary_in.get("schema_ok_before"),
            "schema_ok_after": summary_in.get("schema_ok_after"),
            "auto_repaired_count": summary_in.get("auto_repaired_count"),
            "unrepaired_count": summary_in.get("unrepaired_count"),
            "forbidden_leakage_count": summary_in.get("forbidden_leakage_count"),
            "unknown_reduction_count": summary_in.get("unknown_reduction_count"),
            "enriched_context_used_count": summary_in.get("enriched_context_used_count"),
            "invented_signal_count": summary_in.get("invented_signal_count"),
            "MM2_6r1_stage1_ab_reliable_after_repair": summary_in.get("MM2_6r1_stage1_ab_reliable_after_repair"),
            "MM2_6r1_enriched_context_useful_signal_after_repair": summary_in.get("MM2_6r1_enriched_context_useful_signal_after_repair"),
            "MM2_6r1_ready_for_stage2_ab_design_after_repair": summary_in.get("MM2_6r1_ready_for_stage2_ab_design_after_repair"),
        },
        "derived_counts": {
            "invented_signal_rows": invented_count,
            "enriched_usage_rows": usage_any_count,
            "valid_enriched_usage_rows": usage_valid_count,
            "unknown_reduction_count": unknown_reduction_count,
            "prompt_guardrail_findings": len(prompt_findings["findings"]),
        },
        "retry_criteria": {
            "prompt_adapter_patch_can_plausibly_remove_invented_signals": patch_can_plausibly_remove_invented,
            "enriched_context_has_at_least_some_valid_usage": enriched_has_some_valid_usage,
            "cost_is_acceptable": cost_is_acceptable,
            "criteria_met_for_retry": enriched_should_be_retried,
        },
        "root_causes": root_causes,
        "central_question_answer": "The problem was primarily that the prompt/adapter allowed DSR to overinterpret descriptive enriched data. The available enriched_sm_context in this run was mostly non-directional, so it also had insufficient direct signal, but that is not enough to conclude enriched_sm_context is structurally useless.",
        "enriched_should_be_retried": enriched_should_be_retried,
        "enriched_should_move_to_stage2": False,
        "enriched_should_remain_artifact_only": enriched_should_remain_artifact_only,
        "recommended_next_step": "Do not retry DSR yet. First apply guardrail v2 drafts to adapter/prompt/validator in artifact-only mode and inspect rendered prompts/packages. Retry a small Stage 1 A/B only after the adapter can expose at least one valid directional enriched gate without descriptive overuse.",
    }

    write_csv(INVENTED_ROWS_OUT, invented_rows)
    write_csv(USAGE_ROWS_OUT, usage_rows)
    write_csv(UNKNOWN_ROWS_OUT, unknown_rows)
    write_json(PROMPT_FINDINGS_OUT, prompt_findings)
    write_json(ADAPTER_POLICY_OUT, policy)
    write_json(VALIDATOR_RULES_OUT, validator)
    write_text(USER_PROMPT_DRAFT_OUT, user_prompt_draft())
    write_text(SYSTEM_PROMPT_DRAFT_OUT, system_prompt_draft())
    write_json(SUMMARY_OUT, summary)
    write_text(AUDIT_OUT, build_audit_md(summary, invented_rows, usage_rows, unknown_rows, prompt_findings, policy, validator))

    print(json.dumps({
        "completed": True,
        "invented_signal_rows": invented_count,
        "enriched_usage_rows": usage_any_count,
        "valid_enriched_usage_rows": usage_valid_count,
        "summary": str(SUMMARY_OUT.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()

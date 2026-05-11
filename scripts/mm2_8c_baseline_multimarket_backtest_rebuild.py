#!/usr/bin/env python3
"""
MM-2.8C Baseline Multi-Market Backtest Rebuild.

Artifact-only by default. No DB writes, no production writes, no Telegram,
no vault, no bets. The default run builds the universe, leakage-safe
base_context, TOA market board packages, Stage 1/Stage 2 prompts, leakage
audit, empty DSR/settlement placeholders and summary. DSR is called only with
--allow-dsr. TOA API is not called unless --allow-toa-api is present; this
runner first consumes existing historical TOA artifacts.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, time as dtime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg2
import psycopg2.extras

from apps.api.bt2_settings import bt2_settings

OUT = ROOT / "scripts" / "outputs"
AUDITS = ROOT / "docs" / "bettracker2" / "audits"
PROMPTS = ROOT / "prompts" / "bt2"

OFFICIAL_LEAGUES = ["Premier League", "La Liga", "Serie A", "Bundesliga", "Ligue 1"]
ACTIVE_MARKETS = ["FT_1X2", "OU_GOALS_2_5"]
EXCLUDED_MARKETS = [
    {"market_canonical": "BTTS", "status": "excluded_not_requested", "active": False},
    {"market_canonical": "DOUBLE_CHANCE", "status": "excluded_not_requested", "active": False},
]
MIN_INTERPRETABLE_PICK_COUNT = 20

MM18_BOARD = OUT / "mm1_8_toa_backfill_market_board.json"
MM18_RAW = OUT / "mm1_8_toa_backfill_raw.json"
MM18_COST = OUT / "mm1_8_toa_backfill_quota_cost.json"
STAGE1_SYSTEM = PROMPTS / "mm1_stage1_system_prompt.txt"
STAGE1_TEMPLATE = PROMPTS / "mm1_stage1_user_prompt_template.txt"
STAGE2_SYSTEM = PROMPTS / "mm1_stage2_system_prompt.txt"
STAGE2_TEMPLATE_COMPACT = PROMPTS / "mm1_stage2_user_prompt_template_compact.txt"

PREFIX = "mm2_8c"
MM28C_STAGE1_SYSTEM = """You are BT2 MM-2.8C Stage 1, a disciplined pre-match football context evaluator.

Use only the supplied safe historical base_context. Do not use prices, market favorites, external knowledge, target match outcomes, target match detail feeds, unavailable team-news data, unavailable environment data, staking, bets, Telegram copy, vault actions, or production actions.

Return strict JSON only. Supported markets are FT_1X2 and OU_GOALS_2_5. Unknown is valid and preferred when the safe context is weak or ambiguous.
"""
MM28C_STAGE1_USER = """Evaluate this football event in BT2 MM-2.8C Stage 1.

Use only safe pre-match historical base_context. Analyze only FT_1X2 and OU_GOALS_2_5. Do not activate BTTS, Double Chance, synthetic markets or combinadas.

INPUT:
{
  "event_context": {{event_context_json}},
  "context_only_stage_input": {{context_only_stage_input_json}},
  "context_block_availability": {{context_block_availability_json}},
  "supported_markets": {{supported_markets_json}},
  "leakage_flags": {{leakage_flags_json}},
  "provider_support_summary_without_prices": {{provider_support_summary_without_odds_json}},
  "excluded_markets": {{excluded_markets_json}}
}

Return this strict JSON shape:
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


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


MM19 = load_module("mm1_9_expanded_prompt_package_build", ROOT / "scripts" / "mm1_9_expanded_prompt_package_build.py")
MM20 = load_module("mm2_0_expanded_dsr_shadow_run", ROOT / "scripts" / "mm2_0_expanded_dsr_shadow_run.py")
MM21 = load_module("mm2_1_settlement_performance_evaluation", ROOT / "scripts" / "mm2_1_settlement_performance_evaluation.py")


def dsn() -> str:
    return bt2_settings.bt2_database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def local_window(date_from: str, date_to: str, tz_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    start = datetime.combine(datetime.fromisoformat(date_from).date(), dtime.min, tzinfo=tz)
    end = datetime.combine(datetime.fromisoformat(date_to).date(), dtime.max, tzinfo=tz)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def fetch_candidate_universe(date_from: str, date_to: str, tz_name: str) -> list[dict[str, Any]]:
    start_utc, end_utc = local_window(date_from, date_to, tz_name)
    conn = psycopg2.connect(dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT e.id AS event_id, e.sportmonks_fixture_id, e.league_id, l.name AS league,
               e.home_team_id, e.away_team_id, ht.name AS home_team, at.name AS away_team,
               e.kickoff_utc, e.status, e.result_home, e.result_away, e.season
        FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams ht ON ht.id = e.home_team_id
        LEFT JOIN bt2_teams at ON at.id = e.away_team_id
        WHERE l.name = ANY(%s)
          AND e.kickoff_utc >= %s
          AND e.kickoff_utc <= %s
          AND e.status IN ('finished', 'scored')
          AND e.result_home IS NOT NULL
          AND e.result_away IS NOT NULL
          AND e.status NOT IN ('void', 'cancelled', 'canceled', 'postponed')
        ORDER BY e.kickoff_utc ASC, e.id ASC
        """,
        (OFFICIAL_LEAGUES, start_utc, end_utc),
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    for row in rows:
        ko = parse_dt(row.get("kickoff_utc"))
        local = ko.astimezone(ZoneInfo(tz_name)) if ko else None
        row["event_id"] = str(row["event_id"])
        row["kickoff_utc"] = ko.isoformat() if ko else None
        row["operating_day"] = local.date().isoformat() if local else None
        row["score_complete"] = row.get("result_home") is not None and row.get("result_away") is not None
        row["context_reconstructable_select_only"] = True
        row["void_cancelled_postponed"] = False
    return rows


def market_board_index() -> dict[str, dict[str, Any]]:
    board = read_json(MM18_BOARD, {"events": []})
    return {str(ev.get("event_context", {}).get("event_id")): ev for ev in board.get("events", [])}


def validate_ft1x2(market: dict[str, Any]) -> bool:
    selections = market.get("selections") or {}
    return (
        market.get("market_canonical") == "FT_1X2"
        and market.get("pre_kickoff_market_validated") is True
        and all((selections.get(k) or {}).get("consensus_decimal") is not None for k in ["home", "draw", "away"])
    )


def validate_ou25(market: dict[str, Any]) -> bool:
    selections = market.get("selections") or {}
    return (
        market.get("market_canonical") == "OU_GOALS_2_5"
        and float(market.get("line") or 0) == 2.5
        and market.get("pre_kickoff_market_validated") is True
        and all((selections.get(k) or {}).get("consensus_decimal") is not None for k in ["over_2_5", "under_2_5"])
    )


def market_ready(ev: dict[str, Any], min_decimal_odds: float) -> bool:
    for market in ev.get("market_inventory", []):
        if market.get("market_canonical") == "FT_1X2" and validate_ft1x2(market) and float(market.get("benchmark_odds") or 0) >= min_decimal_odds:
            return True
        if market.get("market_canonical") == "OU_GOALS_2_5" and validate_ou25(market) and float(market.get("benchmark_odds") or 0) >= min_decimal_odds:
            return True
    return False


def select_events(candidates: list[dict[str, Any]], board_by_event: dict[str, dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    eligible = []
    for row in candidates:
        eid = str(row["event_id"])
        ev = board_by_event.get(eid)
        row["market_board_artifact_available"] = bool(ev)
        row["market_board_ready"] = bool(ev and market_ready(ev, args.min_decimal_odds))
        row["market_board_readiness"] = ev.get("market_board_readiness") if ev else "missing"
        if row["market_board_ready"]:
            eligible.append(row)

    if args.sample_mode != "balanced_by_league":
        return eligible[: args.max_events]

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        buckets[str(row["league"])].append(row)
    selected: list[dict[str, Any]] = []
    while len(selected) < args.max_events:
        changed = False
        for league in OFFICIAL_LEAGUES:
            if buckets.get(league):
                selected.append(buckets[league].pop(0))
                changed = True
                if len(selected) >= args.max_events:
                    break
        if not changed:
            break
    return selected


def fetch_targets_and_history(event_ids: list[int]) -> tuple[dict[int, dict[str, Any]], list[Any]]:
    return MM19.fetch_targets_and_history(event_ids)


def compact_market(market: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "market_canonical",
        "provider",
        "provider_market",
        "available",
        "supported_for_mm1",
        "pre_kickoff_market_validated",
        "benchmark_side",
        "benchmark_odds",
        "selections",
        "line",
        "line_preserved",
        "other_lines_observed",
        "point_values_observed",
        "rejection_reasons",
        "provenance",
    }
    return {k: v for k, v in market.items() if k in allowed}


def scrub_prompt_strings(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: scrub_prompt_strings(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub_prompt_strings(v) for v in value]
    if isinstance(value, str):
        return value.replace("scored sample", "completed-match sample").replace("scored", "completed")
    return value


def ready_markets(board_event: dict[str, Any], min_decimal_odds: float) -> list[dict[str, Any]]:
    markets = []
    for market in board_event.get("market_inventory", []):
        if market.get("market_canonical") == "FT_1X2" and validate_ft1x2(market):
            if float(market.get("benchmark_odds") or 0) >= min_decimal_odds:
                markets.append(compact_market(market))
        elif market.get("market_canonical") == "OU_GOALS_2_5" and validate_ou25(market):
            if float(market.get("benchmark_odds") or 0) >= min_decimal_odds:
                markets.append(compact_market(market))
    return markets


def classify_board(markets: list[dict[str, Any]]) -> str:
    ft = any(m["market_canonical"] == "FT_1X2" for m in markets)
    ou = any(m["market_canonical"] == "OU_GOALS_2_5" for m in markets)
    if ft and ou:
        return "both_markets_ready"
    if ft:
        return "ft_1x2_only_ready"
    if ou:
        return "ou25_only_ready"
    return "no_supported_market_ready"


def odds_by_market(markets: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for market in markets:
        if market["market_canonical"] == "FT_1X2":
            out["FT_1X2"] = {
                "provider_market": "h2h",
                "benchmark_side": market.get("benchmark_side"),
                "benchmark_odds": market.get("benchmark_odds"),
                "selections": market.get("selections"),
            }
        elif market["market_canonical"] == "OU_GOALS_2_5":
            out["OU_GOALS_2_5"] = {
                "provider_market": "totals",
                "line": 2.5,
                "benchmark_side": market.get("benchmark_side"),
                "benchmark_odds": market.get("benchmark_odds"),
                "selections": market.get("selections"),
            }
    return out


def leakage_flags(leakage: dict[str, Any]) -> dict[str, Any]:
    return {
        "HIGH_RISK_LEAKAGE": bool(leakage.get("HIGH_RISK_LEAKAGE")),
        "leakage_reasons": leakage.get("leakage_reasons") or [],
        "temporal_cutoff_rule": "source_kickoff_before_target_kickoff",
        "target_fixture_details_visible": False,
        "external_enrichment_visible": False,
    }


def context_only_input(blocks: dict[str, Any]) -> dict[str, Any]:
    return {
        "odds_visible": False,
        "price_reference_visible": False,
        "allowed_markets_without_odds": ACTIVE_MARKETS,
        "pre_match_context": {
            name: {"available": b.get("available"), "safe_status": b.get("safe_status"), "summary": b}
            for name, b in blocks.items()
        },
    }


def context_availability(blocks: dict[str, Any]) -> dict[str, str]:
    return {name: block.get("safe_status") for name, block in blocks.items()}


def provider_support(markets: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for market in markets:
        out[market["market_canonical"]] = {
            "provider": "the_odds_api",
            "provider_market": market.get("provider_market"),
            "supported_for_mm2_8c": True,
            "pre_kickoff_market_validated": market.get("pre_kickoff_market_validated") is True,
            "line": market.get("line"),
            "evidence_status": "confirmed_from_existing_toa_artifact",
        }
    return out


def build_packages(
    selected: list[dict[str, Any]],
    board_by_event: dict[str, dict[str, Any]],
    targets: dict[int, dict[str, Any]],
    history: list[Any],
    min_decimal_odds: float,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    packages = []
    blocks_out = {}
    context_rows = []
    for row in selected:
        eid = str(row["event_id"])
        target = targets[int(eid)]
        blocks, leak, source_rows = MM19.build_context_for_event(target, history)
        blocks = scrub_prompt_strings(blocks)
        markets = ready_markets(board_by_event[eid], min_decimal_odds)
        readiness = classify_board(markets)
        supported = [m["market_canonical"] for m in markets]
        ev_ctx = {
            "event_id": eid,
            "sport": "football",
            "league": row.get("league"),
            "home_team": row.get("home_team"),
            "away_team": row.get("away_team"),
            "kickoff_utc": row.get("kickoff_utc"),
            "operating_day": row.get("operating_day"),
            "match_state": "historical_baseline_backtest_pre_kickoff_artifact",
        }
        package = {
            "run_context": {
                "run_key": "mm2_8c_baseline_multimarket_backtest_rebuild",
                "mode": "artifact_only_baseline",
                "source_artifacts": [str(MM18_BOARD.relative_to(ROOT))],
                "safety": safety(False, False),
            },
            "event_context": ev_ctx,
            "context_only_stage_input": context_only_input(blocks),
            "context_block_availability": context_availability(blocks),
            "context_signal_blocks": blocks,
            "base_context": blocks,
            "supported_markets": supported,
            "market_inventory": markets,
            "market_board_readiness": readiness,
            "odds_by_market": odds_by_market(markets),
            "timestamp_provenance": {
                "kickoff_utc": row.get("kickoff_utc"),
                "source_artifacts": [str(MM18_BOARD.relative_to(ROOT))],
                "pre_kickoff_market_validated": bool(markets),
            },
            "leakage_flags": leakage_flags(leak),
            "provider_support_evidence": provider_support(markets),
            "excluded_discovery_markets": EXCLUDED_MARKETS,
            "methodological_policy": {
                "min_decimal_odds": min_decimal_odds,
                "artifact_only": True,
                "no_edge_claim": True,
                "no_enriched_context": True,
            },
            "rationale_language_policy": MM19.RATIONALE_LANGUAGE_POLICY,
            "safe_context_readiness": MM19.classify_context(blocks, leak),
            "mm2_8c_readiness": "ready_for_dsr_if_allowed" if markets and not leak.get("HIGH_RISK_LEAKAGE") else "not_ready",
        }
        packages.append(package)
        blocks_out[eid] = {"event_context": ev_ctx, "base_context": blocks, "leakage": leak}
        for src in source_rows:
            context_rows.append(src)
    return packages, blocks_out, context_rows


def render(template: str, values: dict[str, Any]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{{" + key + "}}", json.dumps(value, ensure_ascii=False, indent=2, default=str))
    return rendered


def stage1_payload(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_context": package["event_context"],
        "context_only_stage_input": package["context_only_stage_input"],
        "context_block_availability": package["context_block_availability"],
        "supported_markets": package["supported_markets"],
        "leakage_flags": package["leakage_flags"],
        "provider_support_summary_without_odds": package["provider_support_evidence"],
        "excluded_markets": package["excluded_discovery_markets"],
    }


def stage1_placeholder(package: dict[str, Any]) -> dict[str, Any]:
    outputs = []
    for market in ACTIVE_MARKETS:
        outputs.append(
            {
                "market_canonical": market,
                "context_lean": "unknown",
                "context_confidence": "none",
                "non_market_signal_count": 0,
                "signal_summary": [],
                "missing_signal_reason": "DSR_not_called_in_artifact_build",
                "context_unknown": True,
            }
        )
    return {"event_id": package["event_context"]["event_id"], "odds_visible": False, "market_outputs": outputs}


def compact_stage2_input(package: dict[str, Any], stage1_outputs: dict[str, Any]) -> dict[str, Any]:
    markets = package["market_inventory"]
    return {
        "event_context": package["event_context"],
        "stage_1_context_outputs": stage1_outputs,
        "market_inventory": markets,
        "odds_by_market": package["odds_by_market"],
        "benchmark_side": {m["market_canonical"]: m.get("benchmark_side") for m in markets},
        "benchmark_odds": {m["market_canonical"]: m.get("benchmark_odds") for m in markets},
        "market_board_readiness": package["market_board_readiness"],
        "timestamp_provenance": package["timestamp_provenance"],
        "leakage_flags": package["leakage_flags"],
        "provider_support_evidence": package["provider_support_evidence"],
        "excluded_discovery_markets": package["excluded_discovery_markets"],
        "methodological_policy": package["methodological_policy"],
        "rationale_language_policy": package["rationale_language_policy"],
    }


def render_prompts(packages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    s1_system = MM28C_STAGE1_SYSTEM
    s1_template = MM28C_STAGE1_USER
    s2_system = STAGE2_SYSTEM.read_text(encoding="utf-8")
    s2_template = STAGE2_TEMPLATE_COMPACT.read_text(encoding="utf-8")
    stage1 = []
    stage2 = []
    stage2_packages = []
    for package in packages:
        eid = package["event_context"]["event_id"]
        s1p = stage1_payload(package)
        s1_user = render(
            s1_template,
            {
                "event_context_json": s1p["event_context"],
                "context_only_stage_input_json": s1p["context_only_stage_input"],
                "context_block_availability_json": s1p["context_block_availability"],
                "supported_markets_json": s1p["supported_markets"],
                "leakage_flags_json": s1p["leakage_flags"],
                "provider_support_summary_without_odds_json": s1p["provider_support_summary_without_odds"],
                "excluded_markets_json": s1p["excluded_markets"],
            },
        )
        stage1.append(
            {
                "event_id": eid,
                "system_prompt": s1_system,
                "user_prompt": s1_user,
                "input_package_used": s1p,
                "validation_result": validate_stage1(s1p, s1_user),
                "rendered_prompt_chars": len(s1_system) + len(s1_user),
            }
        )
        s2p = compact_stage2_input(package, stage1_placeholder(package))
        s2_user = render(s2_template, {"compact_stage2_input_json": s2p})
        stage2_packages.append({"event_id": eid, "compact_stage2_input": s2p})
        stage2.append(
            {
                "event_id": eid,
                "system_prompt": s2_system,
                "user_prompt": s2_user,
                "compact_stage2_input_used": s2p,
                "validation_result": validate_stage2(s2p, s2_user),
                "rendered_prompt_chars": len(s2_system) + len(s2_user),
            }
        )
    return stage1, stage2, stage2_packages


def forbidden_key_errors(value: Any, forbidden: set[str]) -> list[str]:
    errors = []

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            for k, child in v.items():
                if str(k) in forbidden:
                    errors.append(str(k))
                walk(child)
        elif isinstance(v, list):
            for child in v:
                walk(child)

    walk(value)
    return sorted(set(errors))


def validate_stage1(payload: dict[str, Any], user_prompt: str) -> dict[str, Any]:
    forbidden = {
        "odds_by_market",
        "benchmark_side",
        "benchmark_odds",
        "bookmaker_count",
        "consensus_decimal",
        "price",
        "by_bookmaker",
        "result_home",
        "result_away",
        "score",
        "statistics",
        "events",
        "timeline",
        "periods",
        "enriched_sm_context",
        "lineups",
        "sidelined",
        "formations",
        "weather",
    }
    errors = forbidden_key_errors(payload, forbidden)
    prompt_lower = user_prompt.lower()
    for token in ["consensus_decimal", "benchmark_side", "benchmark_odds", "bookmaker_count", "result_home", "result_away", "enriched_sm_context"]:
        if token in prompt_lower:
            errors.append(f"stage1_prompt_contains_{token}")
    if any(m in {"BTTS", "DOUBLE_CHANCE"} for m in payload.get("supported_markets", [])):
        errors.append("forbidden_market_active")
    return {"valid": not errors, "errors": sorted(set(errors))}


def validate_stage2(payload: dict[str, Any], user_prompt: str) -> dict[str, Any]:
    errors = forbidden_key_errors(payload, {"result_home", "result_away", "score", "settlement", "future_knowledge", "enriched_sm_context"})
    active_market_names = {m.get("market_canonical") for m in payload.get("market_inventory", [])}
    if "BTTS" in active_market_names or "DOUBLE_CHANCE" in active_market_names:
        errors.append("forbidden_market_active")
    for market in payload.get("market_inventory", []):
        if market.get("market_canonical") == "OU_GOALS_2_5" and float(market.get("line") or 0) != 2.5:
            errors.append("ou25_line_not_2_5")
    if "result_home" in user_prompt.lower() or "result_away" in user_prompt.lower() or "enriched_sm_context" in user_prompt.lower():
        errors.append("stage2_prompt_contains_forbidden_token")
    return {"valid": not errors, "errors": sorted(set(errors))}


def leakage_audit(stage1: list[dict[str, Any]], stage2: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for stage_name, records, allowed_odds in [("stage1", stage1, False), ("stage2", stage2, True)]:
        for rec in records:
            payload = rec.get("input_package_used") or rec.get("compact_stage2_input_used") or {}
            text = json.dumps(payload, ensure_ascii=False, default=str).lower()
            hits = []
            if not allowed_odds:
                for token in ["odds_by_market", "benchmark_side", "benchmark_odds", "consensus_decimal", "bookmaker_count", "market_inventory"]:
                    if token in text:
                        hits.append(token)
            for token in ["result_home", "result_away", "score", "settlement", "enriched_sm_context", "lineups", "sidelined", "formations", "weather", "timeline", "periods"]:
                if token in text:
                    hits.append(token)
            validation = rec.get("validation_result") or {}
            hits.extend(validation.get("errors") or [])
            rows.append(
                {
                    "event_id": rec.get("event_id"),
                    "stage": stage_name,
                    "leakage_status": "FAIL" if hits else "PASS",
                    "leakage_hits": "|".join(sorted(set(hits))),
                    "odds_allowed": allowed_odds,
                }
            )
    return rows


def build_market_rows(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for package in packages:
        ev = package["event_context"]
        for market in package.get("market_inventory", []):
            selections = market.get("selections") or {}
            rows.append(
                {
                    "event_id": ev["event_id"],
                    "league": ev.get("league"),
                    "home_team": ev.get("home_team"),
                    "away_team": ev.get("away_team"),
                    "kickoff_utc": ev.get("kickoff_utc"),
                    "market_canonical": market.get("market_canonical"),
                    "provider_market": market.get("provider_market"),
                    "line": market.get("line"),
                    "benchmark_side": market.get("benchmark_side"),
                    "benchmark_odds": market.get("benchmark_odds"),
                    "bookmaker_count_min": min([int(v.get("bookmaker_count") or 0) for v in selections.values()] or [0]),
                    "consensus_decimal_json": json.dumps(selections, ensure_ascii=False),
                    "pre_kickoff_market_validated": market.get("pre_kickoff_market_validated"),
                }
            )
    return rows


def safety(allow_toa_api: bool, allow_dsr: bool) -> dict[str, bool]:
    return {
        "artifact_only": True,
        "db_writes": False,
        "production_writes": False,
        "bt2_daily_picks": False,
        "telegram": False,
        "vault": False,
        "bets": False,
        "tennis": False,
        "sportmonks_api_calls": False,
        "toa_api_calls": bool(allow_toa_api),
        "dsr_calls": bool(allow_dsr),
        "enriched_sm_context": False,
        "btts": False,
        "double_chance": False,
        "synthetic_markets": False,
    }


def run_dsr_if_allowed(
    packages: list[dict[str, Any]],
    rendered_stage1: list[dict[str, Any]],
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not args.allow_dsr:
        return [], [], [], [], []
    api_key = str(bt2_settings.deepseek_api_key or "").strip()
    if not api_key:
        raise RuntimeError("Missing deepseek_api_key; --allow-dsr cannot run.")
    base_url = str(bt2_settings.bt2_dsr_deepseek_base_url or "https://api.deepseek.com")
    configured_model = str(bt2_settings.bt2_dsr_deepseek_model or "")
    s1_by_id = {str(r["event_id"]): r for r in rendered_stage1}
    stage1_raw: list[dict[str, Any]] = []
    stage1_parsed: list[dict[str, Any]] = []
    stage2_raw: list[dict[str, Any]] = []
    stage2_parsed: list[dict[str, Any]] = []
    latency_rows: list[dict[str, Any]] = []
    for idx, package in enumerate(packages, start=1):
        eid = str(package["event_context"]["event_id"])
        prompt = s1_by_id[eid]
        started = time.monotonic()
        raw = MM20.call_deepseek(
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            api_key=api_key,
            base_url=base_url,
            model=args.model,
            timeout_sec=args.timeout_sec,
            max_retries=0,
            stage="stage1",
            event_id=eid,
        )
        raw = MM20.enrich_model_metadata(raw, configured_model, args.model)
        elapsed = round(time.monotonic() - started, 3)
        parsed = MM20.parse_stage1(raw)
        parsed["schema_status"] = "ok" if MM20.stage1_schema_ok(parsed) else "failed"
        stage1_raw.append(raw)
        stage1_parsed.append(parsed)
        latency_rows.append({"event_id": eid, "stage": "stage1", "seconds": elapsed, "sequence": idx})
        if not MM20.stage1_schema_ok(parsed):
            continue
        s2_prompt = MM20.render_stage2_compact(package, parsed["parsed"])
        started = time.monotonic()
        raw2 = MM20.call_deepseek(
            system_prompt=s2_prompt["system_prompt"],
            user_prompt=s2_prompt["user_prompt"],
            api_key=api_key,
            base_url=base_url,
            model=args.model,
            timeout_sec=args.timeout_sec,
            max_retries=0,
            stage="stage2",
            event_id=eid,
        )
        raw2 = MM20.enrich_model_metadata(raw2, configured_model, args.model)
        elapsed = round(time.monotonic() - started, 3)
        parsed2 = MM20.parse_stage2(raw2)
        parsed2["schema_status"] = "ok" if MM20.stage2_schema_ok(parsed2) else "failed"
        stage2_raw.append(raw2)
        stage2_parsed.append(parsed2)
        latency_rows.append({"event_id": eid, "stage": "stage2", "seconds": elapsed, "sequence": idx})
    return stage1_raw, stage1_parsed, stage2_raw, stage2_parsed, latency_rows


def settlement_from_picks(pick_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if not pick_rows:
        empty = MM21.summarize_rows([])
        return empty, [], [], [], [], []
    event_ids = sorted({int(p["event_id"]) for p in pick_rows})
    results = MM21.fetch_results(event_ids)
    settled_rows, bench_rows = MM21.build_settlement_rows(pick_rows, results)
    return (
        MM21.summarize_rows(settled_rows),
        settled_rows,
        MM21.group_performance(settled_rows, "market_canonical"),
        MM21.group_performance(settled_rows, "league"),
        MM21.group_performance(settled_rows, "odds_band"),
        bench_rows,
    )


def benchmark_summary(bench_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not bench_rows:
        return MM21.benchmark_summary([])
    return MM21.benchmark_summary(bench_rows)


def behavior_summary(stage1_parsed: list[dict[str, Any]], stage2_parsed: list[dict[str, Any]], pick_rows: list[dict[str, Any]]) -> dict[str, Any]:
    s1_leans: Counter[str] = Counter()
    s2_rel: Counter[str] = Counter()
    s2_decisions: Counter[str] = Counter()
    for rec in stage1_parsed:
        for out in ((rec.get("parsed") or {}).get("market_outputs") or []):
            s1_leans[f"{out.get('market_canonical')}:{out.get('context_lean')}"] += 1
    for rec in stage2_parsed:
        for out in ((rec.get("parsed") or {}).get("market_outputs") or []):
            s2_rel[f"{out.get('market_canonical')}:{out.get('market_relation')}"] += 1
            s2_decisions[f"{out.get('market_canonical')}:{out.get('final_decision')}"] += 1
    return {
        "stage1_context_lean_distribution": dict(s1_leans),
        "stage2_market_relation_distribution": dict(s2_rel),
        "stage2_final_decision_distribution": dict(s2_decisions),
        "normalized_pick_count": len(pick_rows),
        "pick_market_distribution": dict(Counter(p.get("market_canonical") for p in pick_rows)),
        "pick_benchmark_relation_distribution": dict(Counter("matches_benchmark" if p.get("selection_canonical") == p.get("benchmark_side") else "opposes_benchmark" for p in pick_rows)),
    }


def write_audit(summary: dict[str, Any]) -> None:
    s = summary
    lines = [
        "# MM2.8C Baseline Multi-Market Backtest Rebuild Audit",
        "",
        "## 1. Executive summary",
        "",
        f"`MM2_8c_baseline_multimarket_backtest_completed = {str(s['MM2_8c_baseline_multimarket_backtest_completed']).lower()}`.",
        f"`DSR_executed = {str(s['DSR_executed']).lower()}`. Normalized picks: `{s['normalized_pick_count']}`; settled picks: `{s['settled_pick_count']}`.",
        "",
        "## 2. Scope and restrictions",
        "",
        "Artifact-only baseline rebuild. No DB writes, production writes, bt2_daily_picks, Telegram, vault, bets, tennis, BTTS, Double Chance, synthetic markets, or production readiness claim.",
        "",
        "## 3. Why baseline backtest now",
        "",
        "MM-2.7 found no valid enriched directional gate in the evaluated universe. The project should measure the tested baseline instead of waiting on enriched context.",
        "",
        "## 4. Why enriched is excluded",
        "",
        "`enriched_sm_context`, lineups, sidelined, formations and weather are excluded from Stage 1/Stage 2 inputs because no valid directional gate is active.",
        "",
        "## 5. Universe selection",
        "",
        f"Window `{s['date_from']}` to `{s['date_to']}` in `{s['timezone']}` over the five official BT2 leagues. Universe count: `{s['universe_count']}`; selected events: `{s['selected_events_count']}`.",
        "",
        "## 6. Base context reconstruction",
        "",
        "Base context was reconstructed from local read-only historical events using only source matches with kickoff before target kickoff: h2h, team_form, rest_days and season_aggregates.",
        "",
        "## 7. TOA market board reconstruction",
        "",
        f"Existing TOA historical artifacts were used first. Market-board ready events: `{s['market_board_ready_count']}`. TOA API calls executed: `{s['toa_api_calls_executed']}`.",
        "",
        "## 8. Stage 1/Stage 2 packages",
        "",
        f"Stage 1 ready: `{s['stage1_ready_count']}`; Stage 2 ready: `{s['stage2_ready_count']}`. Active markets only: FT_1X2 and OU_GOALS_2_5.",
        "",
        "## 9. Leakage audit",
        "",
        f"Leakage failures: `{s['leakage_failure_count']}`. Stage 1 forbids odds, benchmarks, market board, scores/results, target statistics/events and enriched context; Stage 2 permits market board but not outcomes or settlement.",
        "",
        "## 10. DSR execution status",
        "",
        f"DSR executed: `{s['DSR_executed']}`. Default dry-run does not call DSR.",
        "",
        "## 11. Normalized picks",
        "",
        f"Normalized pick count: `{s['normalized_pick_count']}`.",
        "",
        "## 12. Settlement/performance",
        "",
        f"Settled picks: `{s['settled_pick_count']}`; hit rate: `{s['hit_rate']}`; ROI: `{s['ROI']}`.",
        "",
        "## 13. Benchmark comparison",
        "",
        f"Benchmark ROI: `{s['benchmark_ROI']}`; DSR minus benchmark profit: `{s['DSR_minus_benchmark_profit']}`.",
        "",
        "## 14. Segment analysis",
        "",
        f"FT_1X2 ROI: `{s['FT_1X2_ROI']}`. OU_GOALS_2_5 ROI: `{s['OU_GOALS_2_5_ROI']}`.",
        "",
        "## 15. What this proves",
        "",
        "The baseline harness can rebuild a leakage-audited artifact universe, base context, market board and DSR-ready prompt packages without enriched context.",
        "",
        "## 16. What this does not prove",
        "",
        "This does not prove edge, future ROI, CLV, production readiness, or that picks should be published.",
        "",
        "## 17. Recommended next step",
        "",
        s["recommended_next_step"],
    ]
    AUDITS.mkdir(parents=True, exist_ok=True)
    (AUDITS / "MM2_8C_BASELINE_MULTIMARKET_BACKTEST_REBUILD_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def preflight(args: argparse.Namespace, candidates: list[dict[str, Any]], selected: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "generated_at_utc": utc_now(),
        "date_from": args.date_from,
        "date_to": args.date_to,
        "timezone": args.timezone,
        "leagues": OFFICIAL_LEAGUES,
        "sample_mode": args.sample_mode,
        "max_events": args.max_events,
        "min_decimal_odds": args.min_decimal_odds,
        "allow_toa_api": args.allow_toa_api,
        "allow_dsr": args.allow_dsr,
        "expected_toa_calls": 0 if selected else ("controlled_backfill_needed_but_not_executed_without_allow_toa_api" if not args.allow_toa_api else "to_be_computed_by_backfill"),
        "expected_dsr_calls": len(selected) * 2 if args.allow_dsr else 0,
        "candidate_universe_count": len(candidates),
        "selected_events_count": len(selected),
        "restrictions_observed": safety(args.allow_toa_api, args.allow_dsr) | {
            "no_enriched_sm_context_in_dsr": True,
            "no_target_statistics_events": True,
            "no_scores_in_prompts": True,
            "no_leakage": True,
        },
    }


def extract_roi(rows: list[dict[str, Any]], market: str) -> float | None:
    for row in rows:
        if row.get("market_canonical") == market:
            return row.get("ROI")
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="MM-2.8C baseline multi-market backtest rebuild")
    ap.add_argument("--date-from", default="2026-04-01")
    ap.add_argument("--date-to", default="2026-04-30")
    ap.add_argument("--timezone", default="America/Bogota")
    ap.add_argument("--max-events", type=int, default=50)
    ap.add_argument("--sample-mode", default="balanced_by_league")
    ap.add_argument("--min-decimal-odds", type=float, default=1.30)
    ap.add_argument("--allow-toa-api", action="store_true")
    ap.add_argument("--allow-dsr", action="store_true")
    ap.add_argument("--timeout-sec", type=int, default=120)
    ap.add_argument("--model", default="deepseek-v4-pro")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    candidates = fetch_candidate_universe(args.date_from, args.date_to, args.timezone)
    board_by_event = market_board_index()
    selected = select_events(candidates, board_by_event, args)
    write_json(OUT / f"{PREFIX}_preflight.json", preflight(args, candidates, selected))
    write_csv(OUT / f"{PREFIX}_candidate_universe_rows.csv", candidates)
    write_csv(OUT / f"{PREFIX}_selected_events.csv", selected)

    packages: list[dict[str, Any]] = []
    blocks: dict[str, Any] = {}
    context_rows: list[dict[str, Any]] = []
    if selected:
        targets, history = fetch_targets_and_history([int(r["event_id"]) for r in selected])
        packages, blocks, context_rows = build_packages(selected, board_by_event, targets, history, args.min_decimal_odds)

    rendered_stage1, rendered_stage2, stage2_packages = render_prompts(packages)
    leak_rows = leakage_audit(rendered_stage1, rendered_stage2)
    leak_failures = [r for r in leak_rows if r["leakage_status"] != "PASS"]

    write_json(OUT / f"{PREFIX}_base_context_blocks.json", blocks)
    write_csv(OUT / f"{PREFIX}_base_context_rows.csv", context_rows)
    write_json(OUT / f"{PREFIX}_market_board.json", {"generated_at_utc": utc_now(), "source": str(MM18_BOARD.relative_to(ROOT)), "events": packages})
    write_csv(OUT / f"{PREFIX}_market_board_rows.csv", build_market_rows(packages))
    write_json(OUT / f"{PREFIX}_toa_backfill_raw.json", read_json(MM18_RAW, {"responses": [], "note": "no TOA API call executed by MM-2.8C"}))
    write_json(OUT / f"{PREFIX}_toa_cost.json", {"allow_toa_api": args.allow_toa_api, "toa_api_calls_executed": 0, "source_cost_artifact": str(MM18_COST.relative_to(ROOT)) if MM18_COST.exists() else None})
    write_json(OUT / f"{PREFIX}_stage1_packages.json", {"packages": packages})
    write_json(OUT / f"{PREFIX}_stage1_rendered_prompts.json", {"rendered_prompts": rendered_stage1})
    write_json(OUT / f"{PREFIX}_stage2_packages.json", {"stage2_packages": stage2_packages})
    write_json(OUT / f"{PREFIX}_stage2_rendered_prompts.json", {"rendered_prompts": rendered_stage2})
    write_csv(OUT / f"{PREFIX}_leakage_audit.csv", leak_rows)

    stage1_raw, stage1_parsed, stage2_raw, stage2_parsed, latency_rows = run_dsr_if_allowed(packages, rendered_stage1, args)
    s1_by = {str(r.get("event_id")): r for r in stage1_parsed}
    s2_by = {str(r.get("event_id")): r for r in stage2_parsed}
    normalized, norm_event_rows, market_rows, pick_rows = MM20.normalize_outputs(packages, s1_by, s2_by, {}, 2) if args.allow_dsr else ({"events": []}, [], [], [])
    behavior = behavior_summary(stage1_parsed, stage2_parsed, pick_rows) if args.allow_dsr else {"DSR_executed": False, "normalized_pick_count": 0}

    write_json(OUT / f"{PREFIX}_stage1_dsr_raw_outputs.json", {"raw_outputs": stage1_raw})
    write_json(OUT / f"{PREFIX}_stage1_dsr_parsed_outputs.json", {"parsed_outputs": stage1_parsed})
    write_json(OUT / f"{PREFIX}_stage2_dsr_raw_outputs.json", {"raw_outputs": stage2_raw})
    write_json(OUT / f"{PREFIX}_stage2_dsr_parsed_outputs.json", {"parsed_outputs": stage2_parsed})
    write_json(OUT / f"{PREFIX}_normalized_final_outputs.json", normalized)
    write_csv(OUT / f"{PREFIX}_pick_level_rows.csv", pick_rows)
    write_json(OUT / f"{PREFIX}_behavior_summary.json", behavior)
    write_csv(OUT / f"{PREFIX}_latency_rows.csv", latency_rows)

    settlement, settled_rows, by_market, by_league, by_odds, bench_rows = settlement_from_picks(pick_rows)
    bench = benchmark_summary(bench_rows)
    write_json(OUT / f"{PREFIX}_settlement_summary.json", settlement)
    write_csv(OUT / f"{PREFIX}_settlement_pick_rows.csv", settled_rows)
    write_csv(OUT / f"{PREFIX}_performance_by_market.csv", by_market)
    write_csv(OUT / f"{PREFIX}_performance_by_league.csv", by_league)
    write_csv(OUT / f"{PREFIX}_performance_by_odds_band.csv", by_odds)
    write_csv(OUT / f"{PREFIX}_benchmark_comparison.csv", bench_rows)

    normalized_pick_count = len(pick_rows)
    settled_pick_count = int(settlement.get("settled_picks") or 0)
    benchmark_roi = (bench.get("benchmark") or {}).get("ROI")
    dsr_minus_benchmark_profit = bench.get("delta_profit")
    schema_reliability_ok = (not args.allow_dsr) or (
        stage1_parsed
        and all(MM20.stage1_schema_ok(r) for r in stage1_parsed)
        and (not stage2_parsed or all(MM20.stage2_schema_ok(r) for r in stage2_parsed))
    )
    performance_interpretable = settled_pick_count >= MIN_INTERPRETABLE_PICK_COUNT and benchmark_roi is not None
    completed = bool(candidates) and bool(blocks) and bool(packages) and bool(rendered_stage1) and bool(rendered_stage2) and bool(leak_rows)
    if args.allow_dsr:
        completed = completed and bool(stage1_raw) and bool(stage1_parsed) and bool(normalized)
    recommended = (
        "DSR+settlement sample reaches interpretability threshold; review leakage-free segment tables before any forward-test proposal."
        if performance_interpretable
        else "Run the same MM-2.8C harness with --allow-dsr on enough selected events to reach at least 20 settled normalized picks; do not publish or claim edge."
    )
    summary = {
        "generated_at_utc": utc_now(),
        "mode": "mm2_8c_baseline_multimarket_backtest_rebuild_artifact_only",
        "MM2_8c_baseline_multimarket_backtest_completed": completed,
        "MM2_8c_behavior_interpretable": bool(schema_reliability_ok and len(leak_failures) == 0 and normalized_pick_count >= MIN_INTERPRETABLE_PICK_COUNT),
        "MM2_8c_performance_interpretable": performance_interpretable,
        "date_from": args.date_from,
        "date_to": args.date_to,
        "timezone": args.timezone,
        "universe_count": len(candidates),
        "selected_events_count": len(selected),
        "market_board_ready_count": len(packages),
        "stage1_ready_count": sum(1 for r in rendered_stage1 if (r.get("validation_result") or {}).get("valid")),
        "stage2_ready_count": sum(1 for r in rendered_stage2 if (r.get("validation_result") or {}).get("valid")),
        "DSR_executed": args.allow_dsr,
        "normalized_pick_count": normalized_pick_count,
        "settled_pick_count": settled_pick_count,
        "hit_rate": settlement.get("hit_rate"),
        "ROI": settlement.get("ROI"),
        "benchmark_ROI": benchmark_roi,
        "DSR_minus_benchmark_profit": dsr_minus_benchmark_profit,
        "FT_1X2_ROI": extract_roi(by_market, "FT_1X2"),
        "OU_GOALS_2_5_ROI": extract_roi(by_market, "OU_GOALS_2_5"),
        "leakage_failure_count": len(leak_failures),
        "schema_reliability_ok": schema_reliability_ok,
        "toa_api_calls_executed": 0,
        "safety": safety(args.allow_toa_api, args.allow_dsr),
        "recommended_next_step": recommended,
        "interpretation_guardrails": [
            "No production readiness claim.",
            "No edge claim.",
            "No pick publication.",
            "enriched_sm_context excluded.",
            "Dry-run without --allow-dsr cannot answer performance.",
        ],
    }
    write_json(OUT / f"{PREFIX}_summary.json", summary)
    write_audit(summary)
    print(json.dumps({k: summary[k] for k in ["MM2_8c_baseline_multimarket_backtest_completed", "universe_count", "selected_events_count", "DSR_executed", "normalized_pick_count", "settled_pick_count", "ROI"]}, indent=2))


if __name__ == "__main__":
    main()

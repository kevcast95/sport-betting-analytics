#!/usr/bin/env python3
"""
MM-0.3 Line Preservation Scaffold audit.

Artifact-only transformation from MM-0.2 raw TOA totals into a canonical
OU_GOALS_2_5 inventory. No DB writes, no DSR, no external calls.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "scripts" / "outputs"
DOC_PATH = ROOT / "docs" / "bettracker2" / "audits" / "MM0_3_LINE_PRESERVATION_SCAFFOLD_AUDIT.md"
AUDIT_PATH = OUT_DIR / "mm0_3_line_preservation_scaffold_audit.json"
ROWS_PATH = OUT_DIR / "mm0_3_line_preservation_scaffold_rows.csv"
CONTRACT_PATH = OUT_DIR / "mm0_3_line_market_contract_example.json"

MM02_RAW = OUT_DIR / "mm0_2_toa_totals_backfill_raw.json"
MM02_AUDIT = OUT_DIR / "mm0_2_toa_totals_backfill_audit.json"
MM02_ROWS = OUT_DIR / "mm0_2_toa_totals_backfill_rows.csv"
MM02_DOC = ROOT / "docs" / "bettracker2" / "audits" / "MM0_2_TOA_TOTALS_BACKFILL_AUDIT.md"


def _parse_dt(raw: Any) -> datetime | None:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _jsonable(v: Any) -> Any:
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def _norm(s: Any) -> str:
    x = unicodedata.normalize("NFKD", str(s or "").strip())
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9]+", " ", x).strip().lower())


def _point_value(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _is_point_25(raw: Any) -> bool:
    p = _point_value(raw)
    return p is not None and abs(p - 2.5) < 0.000001


def _canonicalize_total(name: Any, point: Any) -> tuple[str, str | None, str | None]:
    point_float = _point_value(point)
    n = _norm(name)
    if point_float is None:
        return "OU_GOALS_UNKNOWN_LINE", None, "line_unknown"
    if not _is_point_25(point):
        return "OU_GOALS_OTHER_LINE", None, "non_2_5_line"
    if n == "over":
        return "OU_GOALS_2_5", "over_2_5", None
    if n == "under":
        return "OU_GOALS_2_5", "under_2_5", None
    return "OU_GOALS_2_5", None, "unknown_over_under_selection"


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _event_odds_responses(raw: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in raw.get("responses", []) if r.get("phase") == "historical_event_odds"]


def _source_paths() -> dict[str, str]:
    return {
        "mm0_2_doc": str(MM02_DOC.relative_to(ROOT)),
        "mm0_2_raw": str(MM02_RAW.relative_to(ROOT)),
        "mm0_2_audit": str(MM02_AUDIT.relative_to(ROOT)),
        "mm0_2_rows": str(MM02_ROWS.relative_to(ROOT)),
    }


def _extract_rows(mm02_raw: dict[str, Any], mm02_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    row_by_event = {int(r["bt2_event_id"]): r for r in mm02_rows if r.get("bt2_event_id")}
    preserved_rows: list[dict[str, Any]] = []
    h2h_by_event: dict[int, bool] = defaultdict(bool)
    totals_by_event: dict[int, bool] = defaultdict(bool)

    for resp in _event_odds_responses(mm02_raw):
        request = resp.get("request") or {}
        bt2_event_id = int(request["bt2_event_id"])
        source_event = row_by_event.get(bt2_event_id, {})
        body = resp.get("raw_response") if isinstance(resp.get("raw_response"), dict) else {}
        data = body.get("data") if isinstance(body.get("data"), dict) else {}
        provider_snapshot_time = body.get("timestamp") or body.get("previous_timestamp") or source_event.get("provider_snapshot_time_utc")
        kickoff = _parse_dt(source_event.get("kickoff_utc"))
        snapshot_dt = _parse_dt(provider_snapshot_time)
        minutes_before = (kickoff - snapshot_dt).total_seconds() / 60 if kickoff and snapshot_dt else None
        is_pre = bool(minutes_before is not None and minutes_before > 0)

        for bm in data.get("bookmakers") or []:
            if not isinstance(bm, dict):
                continue
            bookmaker_key = bm.get("key")
            bookmaker_title = bm.get("title")
            bookmaker_last_update = bm.get("last_update")
            for market in bm.get("markets") or []:
                if not isinstance(market, dict):
                    continue
                market_key = str(market.get("key") or "").lower()
                market_last_update = market.get("last_update") or bookmaker_last_update
                if market_key == "h2h":
                    h2h_by_event[bt2_event_id] = True
                    continue
                if market_key != "totals":
                    continue
                totals_by_event[bt2_event_id] = True
                for outcome in market.get("outcomes") or []:
                    if not isinstance(outcome, dict):
                        continue
                    point = outcome.get("point")
                    market_canonical, selection_canonical, rejection_reason = _canonicalize_total(outcome.get("name"), point)
                    point_float = _point_value(point)
                    preserved_rows.append(
                        {
                            "bt2_event_id": bt2_event_id,
                            "sportmonks_fixture_id": source_event.get("sportmonks_fixture_id") or None,
                            "league": source_event.get("league") or None,
                            "home_team": source_event.get("home_team") or data.get("home_team"),
                            "away_team": source_event.get("away_team") or data.get("away_team"),
                            "kickoff_utc": source_event.get("kickoff_utc") or data.get("commence_time"),
                            "toa_event_id": data.get("id") or request.get("toa_event_id"),
                            "toa_home_team": data.get("home_team"),
                            "toa_away_team": data.get("away_team"),
                            "provider": "the_odds_api",
                            "sport_key": data.get("sport_key") or request.get("sport_key"),
                            "bookmaker_key": bookmaker_key,
                            "bookmaker_title": bookmaker_title,
                            "provider_market": market_key,
                            "market_last_update": market_last_update,
                            "outcome_name": outcome.get("name"),
                            "price": float(outcome["price"]) if outcome.get("price") is not None else None,
                            "point_raw": point,
                            "line": point_float,
                            "market_canonical": market_canonical,
                            "selection_canonical": selection_canonical,
                            "canonical_rejection_reason": rejection_reason,
                            "provider_snapshot_time": provider_snapshot_time,
                            "commence_time": data.get("commence_time"),
                            "minutes_before_kickoff": round(minutes_before, 2) if minutes_before is not None else None,
                            "is_pre_kickoff_market": is_pre,
                            "source_raw_artifact": str(MM02_RAW.relative_to(ROOT)),
                            "settlement_supported": market_canonical == "OU_GOALS_2_5",
                        }
                    )
    event_presence: dict[int, dict[str, Any]] = {}
    for event_id, source_event in row_by_event.items():
        event_presence[event_id] = {
            "has_h2h": bool(source_event.get("h2h_available") == "True" or h2h_by_event.get(event_id)),
            "has_totals": bool(source_event.get("totals_available") == "True" or totals_by_event.get(event_id)),
            "is_matched": bool(source_event.get("toa_event_id")),
        }
    return preserved_rows, event_presence


def _build_inventory(mm02_rows: list[dict[str, str]], preserved_rows: list[dict[str, Any]], event_presence: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    by_event: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in preserved_rows:
        by_event[int(row["bt2_event_id"])].append(row)

    inventory = []
    for src in mm02_rows:
        event_id = int(src["bt2_event_id"])
        rows = by_event.get(event_id, [])
        ou25 = [r for r in rows if r["market_canonical"] == "OU_GOALS_2_5"]
        over = [r for r in ou25 if r["selection_canonical"] == "over_2_5" and r["price"] is not None]
        under = [r for r in ou25 if r["selection_canonical"] == "under_2_5" and r["price"] is not None]
        other_lines = [r for r in rows if r["market_canonical"] == "OU_GOALS_OTHER_LINE"]
        missing_point = [r for r in rows if r["market_canonical"] == "OU_GOALS_UNKNOWN_LINE"]
        provider_snapshot = rows[0]["provider_snapshot_time"] if rows else src.get("provider_snapshot_time_utc") or None
        minutes_before = rows[0]["minutes_before_kickoff"] if rows else (float(src["minutes_before_kickoff"]) if src.get("minutes_before_kickoff") else None)
        is_pre = bool(rows[0]["is_pre_kickoff_market"]) if rows else src.get("is_pre_kickoff_market") == "True"
        over_min = min([r["price"] for r in over], default=None)
        under_min = min([r["price"] for r in under], default=None)
        benchmark_side = None
        benchmark_odds = None
        if over_min is not None and under_min is not None:
            benchmark_side, benchmark_odds = ("over_2_5", over_min) if over_min <= under_min else ("under_2_5", under_min)

        has_ou = bool(over and under and is_pre)
        if not src.get("toa_event_id"):
            rejection = "unmatched_event"
        elif not event_presence.get(event_id, {}).get("has_totals") and not rows:
            rejection = "no_totals_market"
        elif not ou25 and other_lines:
            rejection = "totals_without_2_5"
        elif missing_point:
            rejection = "line_unknown"
        elif ou25 and not over:
            rejection = "missing_over_2_5"
        elif ou25 and not under:
            rejection = "missing_under_2_5"
        elif ou25 and not is_pre:
            rejection = "post_kickoff"
        else:
            rejection = None

        inventory.append(
            {
                "bt2_event_id": event_id,
                "sportmonks_fixture_id": src.get("sportmonks_fixture_id") or None,
                "league": src.get("league"),
                "home_team": src.get("home_team"),
                "away_team": src.get("away_team"),
                "kickoff_utc": src.get("kickoff_utc"),
                "toa_event_id": src.get("toa_event_id") or None,
                "has_h2h": bool(event_presence.get(event_id, {}).get("has_h2h")),
                "has_totals": bool(event_presence.get(event_id, {}).get("has_totals") or rows),
                "has_ou_2_5": has_ou,
                "over_2_5_bookmaker_count": len({r["bookmaker_key"] for r in over}),
                "under_2_5_bookmaker_count": len({r["bookmaker_key"] for r in under}),
                "ou_2_5_complete_bookmaker_count": len({r["bookmaker_key"] for r in over} & {r["bookmaker_key"] for r in under}),
                "other_lines_observed": sorted({r["line"] for r in other_lines if r["line"] is not None}),
                "missing_point_outcome_count": len(missing_point),
                "benchmark_side": benchmark_side,
                "benchmark_odds": benchmark_odds,
                "provider_snapshot_time": provider_snapshot,
                "minutes_before_kickoff": minutes_before,
                "is_pre_kickoff_market": is_pre,
                "rejection_reason": rejection,
                "settlement_supported": has_ou,
                "source_raw_artifact": str(MM02_RAW.relative_to(ROOT)),
            }
        )
    return inventory


def _contract_example() -> dict[str, Any]:
    return {
        "event_id": "bt2_event_id",
        "provider": "the_odds_api",
        "provider_event_id": "toa_event_id",
        "provider_market": "totals",
        "market_canonical": "OU_GOALS_2_5",
        "line": 2.5,
        "selection_canonical": "over_2_5",
        "odds": 1.91,
        "bookmaker": {
            "key": "example_bookmaker",
            "title": "Example Bookmaker",
        },
        "provider_snapshot_time": "2026-04-19T14:25:37Z",
        "market_last_update": "2026-04-19T14:24:47Z",
        "kickoff_utc": "2026-04-22T19:00:00Z",
        "minutes_before_kickoff": 4594.38,
        "is_pre_kickoff_market": True,
        "source_raw_artifact": "scripts/outputs/mm0_2_toa_totals_backfill_raw.json",
        "settlement_supported": True,
        "canonicalization_rule": "TOA totals outcome with point exactly 2.5 and outcome name Over/Under",
    }


def _build_audit() -> dict[str, Any]:
    mm02_raw = json.loads(MM02_RAW.read_text(encoding="utf-8"))
    mm02_audit = json.loads(MM02_AUDIT.read_text(encoding="utf-8"))
    mm02_rows = _load_csv_rows(MM02_ROWS)
    preserved_rows, event_presence = _extract_rows(mm02_raw, mm02_rows)
    inventory = _build_inventory(mm02_rows, preserved_rows, event_presence)
    valid = [x for x in inventory if x["has_ou_2_5"] and x["benchmark_side"] and x["is_pre_kickoff_market"]]
    unmatched = [x for x in inventory if x["rejection_reason"] == "unmatched_event"]
    other_only = [x for x in inventory if x["rejection_reason"] == "totals_without_2_5"]
    missing_point = [x for x in inventory if x["missing_point_outcome_count"]]
    scaffold_passed = bool(valid)
    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "safety": {
            "artifact_only": True,
            "external_api_calls": False,
            "db_writes": False,
            "dsr_calls": False,
            "telegram": False,
            "vault": False,
            "bets": False,
            "bt2_daily_picks_writes": False,
            "football_only": True,
        },
        "inputs": _source_paths(),
        "mm0_2_summary": {
            "OU_GOALS_2_5_TOA_totals_confirmed": mm02_audit.get("status_flags", {}).get("OU_GOALS_2_5_TOA_totals_confirmed"),
            "matched_events_with_totals": mm02_audit.get("ou_goals_2_5_summary", {}).get("matched_events_with_totals"),
            "matched_events_with_point_2_5": mm02_audit.get("ou_goals_2_5_summary", {}).get("matched_events_with_point_2_5"),
        },
        "canonicalization_rules": [
            "point == 2.5 and outcome name Over -> OU_GOALS_2_5 / over_2_5",
            "point == 2.5 and outcome name Under -> OU_GOALS_2_5 / under_2_5",
            "point != 2.5 -> OU_GOALS_OTHER_LINE",
            "missing point -> OU_GOALS_UNKNOWN_LINE / line_unknown",
            "do not infer line from text",
            "do not collapse totals without line",
        ],
        "raw_totals_structure": {
            "provider": "the_odds_api",
            "event_path": "raw_response.data",
            "bookmakers_path": "raw_response.data.bookmakers[]",
            "market_path": "bookmakers[].markets[] where key == totals",
            "outcome_fields_preserved": [
                "bookmaker key/title",
                "market key",
                "outcome name",
                "price",
                "point",
                "market last_update",
                "provider snapshot timestamp",
                "commence_time",
                "bt2_event_id",
                "toa_event_id",
            ],
        },
        "readiness": {
            "OU_GOALS_2_5_line_preservation_scaffold_passed": scaffold_passed,
            "MM1_readiness": "candidate_pending_two_stage_shadow_design" if scaffold_passed else "blocked_line_preservation_scaffold",
            "events_total": len(inventory),
            "events_with_valid_ou25": len(valid),
            "events_missing_ou25": len([x for x in inventory if not x["has_ou_2_5"]]),
            "events_with_other_lines_only": len(other_only),
            "events_with_missing_point": len(missing_point),
            "events_unmatched": len(unmatched),
            "pre_kickoff_validated_count": len([x for x in inventory if x["is_pre_kickoff_market"]]),
        },
        "row_counts": {
            "preserved_total_outcomes": len(preserved_rows),
            "ou_goals_2_5_outcomes": sum(1 for r in preserved_rows if r["market_canonical"] == "OU_GOALS_2_5"),
            "other_line_outcomes": sum(1 for r in preserved_rows if r["market_canonical"] == "OU_GOALS_OTHER_LINE"),
            "unknown_line_outcomes": sum(1 for r in preserved_rows if r["market_canonical"] == "OU_GOALS_UNKNOWN_LINE"),
            "canonical_rejection_reasons": dict(Counter(r["canonical_rejection_reason"] or "canonical_ou25" for r in preserved_rows)),
        },
        "inventory": inventory,
        "preserved_rows_sample": preserved_rows[:100],
        "contract_example_path": str(CONTRACT_PATH.relative_to(ROOT)),
        "rows_artifact_path": str(ROWS_PATH.relative_to(ROOT)),
    }
    return audit, preserved_rows, inventory


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_rows(rows: list[dict[str, Any]]) -> None:
    ROWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)
    with ROWS_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _render_md(audit: dict[str, Any]) -> str:
    ready = audit["readiness"]
    counts = audit["row_counts"]
    inv = audit["inventory"]
    valid = [x for x in inv if x["has_ou_2_5"]]
    rejected = [x for x in inv if x["rejection_reason"]]
    coverage = [
        "|event|league|match|has totals|has OU2.5|over books|under books|benchmark|minutes before|rejection|",
        "|---|---|---|---|---|---:|---:|---|---:|---|",
    ]
    for row in inv:
        bench = f"{row['benchmark_side']} @ {row['benchmark_odds']}" if row["benchmark_side"] else ""
        coverage.append(
            f"|{row['bt2_event_id']}|{row['league']}|{bool(row['toa_event_id'])}|{row['has_totals']}|{row['has_ou_2_5']}|"
            f"{row['over_2_5_bookmaker_count']}|{row['under_2_5_bookmaker_count']}|{bench}|"
            f"{row['minutes_before_kickoff']}|{row['rejection_reason'] or ''}|"
        )
    rejection_counts = Counter(x["rejection_reason"] or "accepted_ou25" for x in inv)
    rejection_lines = [f"- `{k}`: `{v}`" for k, v in rejection_counts.items()]
    return "\n".join(
        [
            "# MM0.3 Line Preservation Scaffold Audit",
            "",
            "## 1. Executive summary",
            "",
            "MM-0.3 transformed the MM-0.2 raw TOA `totals` payload into an artifact-only canonical line-market inventory. It preserved bookmaker, market, outcome, price, explicit `point`, market update timestamp, provider snapshot timestamp, kickoff, benchmark and raw provenance.",
            "",
            f"Result: `OU_GOALS_2_5_line_preservation_scaffold_passed={ready['OU_GOALS_2_5_line_preservation_scaffold_passed']}` and `MM1_readiness={ready['MM1_readiness']}`.",
            "",
            "No DSR was called and no production path was modified.",
            "",
            "## 2. Scope and restrictions",
            "",
            "- Artifact-only transformation from MM-0.2 outputs.",
            "- No external APIs, no DB writes, no migrations, no product logic changes.",
            "- No DSR, Telegram, vault, bets, or `bt2_daily_picks`.",
            "- Football only.",
            "",
            "## 3. Inputs from MM-0.2",
            "",
            f"- `{audit['inputs']['mm0_2_doc']}`",
            f"- `{audit['inputs']['mm0_2_raw']}`",
            f"- `{audit['inputs']['mm0_2_audit']}`",
            f"- `{audit['inputs']['mm0_2_rows']}`",
            "",
            "## 4. Raw TOA totals structure",
            "",
            "The relevant raw path is `raw_response.data.bookmakers[].markets[]` where `market.key == totals`. Each outcome preserves `name`, `price`, and `point`; market/bookmaker timestamps are preserved from `last_update`; provider snapshot timestamp is taken from the TOA historical response `timestamp`.",
            "",
            "## 5. Canonicalization rules",
            "",
            "- `point == 2.5` and `name == Over` -> `OU_GOALS_2_5 / over_2_5`.",
            "- `point == 2.5` and `name == Under` -> `OU_GOALS_2_5 / under_2_5`.",
            "- `point != 2.5` -> `OU_GOALS_OTHER_LINE`.",
            "- missing `point` -> `OU_GOALS_UNKNOWN_LINE` / `line_unknown`.",
            "- No line is inferred from text.",
            "- Totals are never collapsed without an explicit line.",
            "",
            "## 6. OU_GOALS_2_5 preserved inventory",
            "",
            f"Events with valid OU2.5: `{ready['events_with_valid_ou25']}`.",
            f"Preserved OU2.5 outcome rows: `{counts['ou_goals_2_5_outcomes']}`.",
            f"Valid event examples: `{[x['bt2_event_id'] for x in valid]}`.",
            "",
            *coverage,
            "",
            "## 7. Rejected/other-line totals",
            "",
            *rejection_lines,
            "",
            f"Other-line outcome rows: `{counts['other_line_outcomes']}`. Unknown-line outcome rows: `{counts['unknown_line_outcomes']}`.",
            "",
            "## 8. Timestamp safety",
            "",
            f"Pre-kickoff validated events: `{ready['pre_kickoff_validated_count']}`.",
            "The scaffold uses TOA historical response `timestamp` as provider snapshot time. External execution time is not treated as market availability time.",
            "",
            "## 9. Benchmark construction",
            "",
            "For each valid event, benchmark is the shortest decimal price among preserved `over_2_5` and `under_2_5` selections. This is a market baseline only, not a model claim.",
            "",
            "## 10. Line preservation scaffold readiness",
            "",
            f"`OU_GOALS_2_5_line_preservation_scaffold_passed = {ready['OU_GOALS_2_5_line_preservation_scaffold_passed']}`.",
            f"`MM1_readiness = {ready['MM1_readiness']}`.",
            "",
            "This means the next design step can target an MM-1 two-stage shadow experiment contract, but DSR is still not enabled by this audit.",
            "",
            "## 11. What this proves",
            "",
            "- TOA raw `totals` can be transformed into a canonical OU2.5 artifact without losing line.",
            "- The scaffold can preserve bookmaker, line, selection, odds, timestamps, benchmark and provenance.",
            "- Events with non-2.5 totals are rejected cleanly instead of being mislabeled.",
            "",
            "## 12. What this does not prove",
            "",
            "- It does not prove edge, ROI, model performance, or production readiness.",
            "- It does not write a DB schema or migrate product tables.",
            "- It does not call DSR or generate picks.",
            "- It does not activate BTTS or Double Chance.",
            "",
            "## 13. Recommended next step",
            "",
            "Design MM-1 two-stage shadow for `FT_1X2 + OU_GOALS_2_5`: context-first, then market reveal, using this line-preserved inventory contract. Before running DSR, keep the run artifact-only and define parser/postprocess gates for unsupported lines and `market_only` outputs.",
            "",
        ]
    )


def main() -> int:
    audit, preserved_rows, _inventory = _build_audit()
    _write_json(AUDIT_PATH, audit)
    _write_rows(preserved_rows)
    _write_json(CONTRACT_PATH, _contract_example())
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_render_md(audit), encoding="utf-8")
    print(json.dumps({
        "OU_GOALS_2_5_line_preservation_scaffold_passed": audit["readiness"]["OU_GOALS_2_5_line_preservation_scaffold_passed"],
        "MM1_readiness": audit["readiness"]["MM1_readiness"],
        "events_with_valid_ou25": audit["readiness"]["events_with_valid_ou25"],
        "artifacts": [
            str(DOC_PATH.relative_to(ROOT)),
            str(AUDIT_PATH.relative_to(ROOT)),
            str(ROWS_PATH.relative_to(ROOT)),
            str(CONTRACT_PATH.relative_to(ROOT)),
        ],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

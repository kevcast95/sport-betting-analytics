#!/usr/bin/env python3
"""
MM-2.4 Timestamp-gated enriched SportMonks context adapter.

Artifact-only. Reads MM-2.3d raw responses and builds compact Stage 1 preview
blocks. No external calls, DB writes, DSR, TOA, production actions, picks, odds,
or performance metrics.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mm2_3b_sportmonks_controlled_fixture_probe import parse_dt, write_json  # noqa: E402

OUT = ROOT / "scripts" / "outputs"
AUDITS = ROOT / "docs" / "bettracker2" / "audits"
RAW_PATH = OUT / "mm2_3d_sm_prekickoff_probe_raw.json"

POSITION_BUCKETS = {
    "goalkeeper": {"goalkeeper", "keeper"},
    "defender": {"defender", "centre-back", "left-back", "right-back", "defence"},
    "midfielder": {"midfielder", "midfield", "defensive midfielder", "attacking midfielder"},
    "attacker": {"attacker", "forward", "striker", "winger", "centre-forward"},
}
SEVERE_TOKENS = {
    "rupture",
    "fracture",
    "surgery",
    "cruciate",
    "acl",
    "achilles",
    "broken",
    "meniscus",
    "suspension",
    "suspended",
    "red-card",
}
SUSPENSION_TOKENS = {"suspension", "suspended", "red-card", "yellow-cards"}
NATIONAL_TEAM_TOKENS = {"national-team", "called-up"}
INJURY_HINTS = {"injury", "rupture", "strain", "fracture", "illness", "knock", "muscle", "hamstring", "ankle", "knee", "achilles"}


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def data_node(entry: dict[str, Any]) -> dict[str, Any]:
    raw = entry.get("raw_json")
    if isinstance(raw, dict) and isinstance(raw.get("data"), dict):
        return raw["data"]
    return raw if isinstance(raw, dict) else {}


def fixture_kickoff(fixture: dict[str, Any]) -> datetime | None:
    return parse_dt(fixture.get("starting_at")) or parse_dt(fixture.get("starting_at_timestamp"))


def truthy_payload(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (list, dict, str)):
        return bool(value)
    return True


def has_recursive_key(node: Any, keys: set[str]) -> bool:
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if str(k).lower() in keys and truthy_payload(v):
                    return True
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(x for x in cur if isinstance(x, (dict, list)))
    return False


def state_not_started(fixture: dict[str, Any]) -> bool:
    state = fixture.get("state")
    if not isinstance(state, dict):
        return False
    text = " ".join(str(state.get(k, "")) for k in ("state", "name", "short_name", "developer_name")).lower()
    return "not started" in text or " ns" in f" {text} " or text.strip() == "ns"


def timestamp_gate(entry: dict[str, Any], fixture: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    fetched = parse_dt(entry.get("requested_at_utc"))
    kickoff = fixture_kickoff(fixture)
    result_info = fixture.get("result_info")
    score_present = truthy_payload(fixture.get("scores")) or has_recursive_key(fixture.get("scores"), {"score", "goals"})
    live_present = any(truthy_payload(fixture.get(k)) for k in ("periods", "events", "statistics", "timeline"))
    live_present = live_present or has_recursive_key({k: fixture.get(k) for k in ("periods", "events", "timeline")}, {"minute", "time", "period"})
    odds_present = truthy_payload(fixture.get("odds")) or truthy_payload(fixture.get("inplayOdds")) or truthy_payload(fixture.get("premiumOdds"))
    gate = {
        "fetched_before_kickoff": bool(fetched and kickoff and fetched < kickoff),
        "state_not_started": state_not_started(fixture),
        "result_info_null": result_info is None,
        "score_fields_absent": not score_present,
        "periods_absent": not truthy_payload(fixture.get("periods")),
        "live_minute_absent": not live_present,
        "events_absent": not truthy_payload(fixture.get("events")) and not truthy_payload(fixture.get("timeline")),
        "statistics_absent": not truthy_payload(fixture.get("statistics")),
        "odds_absent": not odds_present,
    }
    reasons = [k for k, ok in gate.items() if not ok]
    gate["no_score_result_live_fields"] = all(
        gate[k]
        for k in (
            "result_info_null",
            "score_fields_absent",
            "periods_absent",
            "live_minute_absent",
            "events_absent",
            "statistics_absent",
            "odds_absent",
        )
    )
    gate["safe_for_stage1"] = bool(gate["fetched_before_kickoff"] and gate["state_not_started"] and gate["no_score_result_live_fields"])
    return gate, reasons


def participant_locations(fixture: dict[str, Any]) -> dict[str, int | None]:
    out = {"home": None, "away": None}
    for p in fixture.get("participants") or []:
        if not isinstance(p, dict):
            continue
        loc = str((p.get("meta") or {}).get("location") or p.get("location") or "").lower()
        if loc in out and p.get("id") is not None:
            out[loc] = int(p["id"])
    return out


def normalize_position(value: Any) -> str:
    if not isinstance(value, dict):
        return "unknown"
    try:
        position_id = int(value.get("position_id"))
    except (TypeError, ValueError):
        position_id = None
    if position_id == 24:
        return "goalkeeper"
    if position_id == 25:
        return "defender"
    if position_id == 26:
        return "midfielder"
    if position_id == 27:
        return "attacker"
    text = " ".join(str(value.get(k, "")) for k in ("code", "name", "developer_name")).lower()
    for bucket, tokens in POSITION_BUCKETS.items():
        if any(t in text for t in tokens):
            return bucket
    return "unknown"


def side_for_team(team_id: int | None, locs: dict[str, int | None]) -> str:
    if team_id is not None and locs.get("home") == team_id:
        return "home"
    if team_id is not None and locs.get("away") == team_id:
        return "away"
    return "unknown"


def metadata_confirmed(fixture: dict[str, Any]) -> bool | None:
    for row in fixture.get("metadata") or []:
        if not isinstance(row, dict):
            continue
        vals = row.get("values")
        if isinstance(vals, dict) and "confirmed" in vals:
            return bool(vals.get("confirmed"))
    return None


def formation_from_metadata(fixture: dict[str, Any], side: str) -> str | None:
    for row in fixture.get("metadata") or []:
        vals = row.get("values") if isinstance(row, dict) else None
        if isinstance(vals, dict) and isinstance(vals.get(side), str):
            return vals[side]
    return None


def formation_from_formations(fixture: dict[str, Any], side: str) -> str | None:
    for row in fixture.get("formations") or []:
        if isinstance(row, dict) and str(row.get("location") or "").lower() == side:
            return row.get("formation")
    return None


def lineups_context(fixture: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    locs = participant_locations(fixture)
    rows = [r for r in fixture.get("lineups") or [] if isinstance(r, dict)]
    confirmed = metadata_confirmed(fixture)
    confirmed_status = "confirmed" if confirmed is True else ("probable_or_unconfirmed" if confirmed is False else "unknown")
    by_side: dict[str, dict[str, Any]] = {
        "home": Counter(),
        "away": Counter(),
        "unknown": Counter(),
    }
    lineup_type_counts: Counter[str] = Counter()
    for row in rows:
        side = side_for_team(row.get("team_id"), locs)
        type_code = str(((row.get("type") or {}).get("code") or "")).lower()
        pos = normalize_position(row.get("position") or row.get("player", {}))
        lineup_type_counts[type_code or "unknown"] += 1
        if type_code == "lineup":
            by_side[side]["listed_lineup_count"] += 1
            by_side[side][f"{pos}_count"] += 1
        elif type_code in {"bench", "substitute", "substitutes"}:
            by_side[side]["bench_count"] += 1
        else:
            by_side[side]["other_lineup_rows"] += 1
    for side in ("home", "away"):
        for key in ("listed_lineup_count", "bench_count", "goalkeeper_count", "defender_count", "midfielder_count", "attacker_count", "unknown_count"):
            by_side[side].setdefault(key, 0)
    ff_home = formation_from_formations(fixture, "home")
    ff_away = formation_from_formations(fixture, "away")
    fm_home = formation_from_metadata(fixture, "home")
    fm_away = formation_from_metadata(fixture, "away")
    context = {
        "available": bool(rows),
        "lineup_rows_count": len(rows),
        "confirmed_flag_from_metadata": confirmed,
        "confirmed_status": confirmed_status,
        "counting_note": "SportMonks type.code='lineup' is counted as listed/probable starter; not confirmed when metadata confirmed=false.",
        "home": {
            **dict(by_side["home"]),
            "formation_from_lineups": None,
            "formation_from_formations": ff_home,
            "formation_from_metadata": fm_home,
        },
        "away": {
            **dict(by_side["away"]),
            "formation_from_lineups": None,
            "formation_from_formations": ff_away,
            "formation_from_metadata": fm_away,
        },
        "starters_count_by_type_lineup": int(lineup_type_counts.get("lineup", 0)),
        "bench_count_by_type_bench": int(lineup_type_counts.get("bench", 0) + lineup_type_counts.get("substitute", 0) + lineup_type_counts.get("substitutes", 0)),
        "formation_match_consistency": (ff_home == fm_home if ff_home and fm_home else None, ff_away == fm_away if ff_away and fm_away else None),
        "signal_direction_by_market": {"FT_1X2": "unknown", "OU_GOALS_2_5": "unknown"},
        "signal_strength": "none",
        "notes": [],
    }
    row = {
        "fixture_id": fixture.get("id"),
        "lineup_available": bool(rows),
        "lineup_rows_count": len(rows),
        "confirmed_flag_from_metadata": confirmed,
        "confirmed_status": confirmed_status,
        "home_listed_lineup_count": by_side["home"]["listed_lineup_count"],
        "away_listed_lineup_count": by_side["away"]["listed_lineup_count"],
        "home_goalkeeper_count": by_side["home"]["goalkeeper_count"],
        "away_goalkeeper_count": by_side["away"]["goalkeeper_count"],
        "home_defender_count": by_side["home"]["defender_count"],
        "away_defender_count": by_side["away"]["defender_count"],
        "home_midfielder_count": by_side["home"]["midfielder_count"],
        "away_midfielder_count": by_side["away"]["midfielder_count"],
        "home_attacker_count": by_side["home"]["attacker_count"],
        "away_attacker_count": by_side["away"]["attacker_count"],
        "home_formation_from_formations": ff_home,
        "away_formation_from_formations": ff_away,
        "home_formation_from_metadata": fm_home,
        "away_formation_from_metadata": fm_away,
        "formation_match_consistency_home": ff_home == fm_home if ff_home and fm_home else "",
        "formation_match_consistency_away": ff_away == fm_away if ff_away and fm_away else "",
    }
    return context, row


def absence_type_bucket(type_obj: Any) -> str:
    text = ""
    if isinstance(type_obj, dict):
        text = " ".join(str(type_obj.get(k, "")) for k in ("code", "name", "developer_name")).lower()
    if any(t in text for t in NATIONAL_TEAM_TOKENS):
        return "national_team_callup"
    if any(t in text for t in SUSPENSION_TOKENS):
        return "suspension"
    if any(t in text for t in INJURY_HINTS):
        return "injury"
    return "unknown"


def is_severe_absence(type_obj: Any) -> bool:
    text = ""
    if isinstance(type_obj, dict):
        text = " ".join(str(type_obj.get(k, "")) for k in ("code", "name", "developer_name")).lower()
    return any(t in text for t in SEVERE_TOKENS)


def availability_context(fixture: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    locs = participant_locations(fixture)
    rows = [r for r in fixture.get("sidelined") or [] if isinstance(r, dict)]
    by_side: dict[str, Counter[str]] = {"home": Counter(), "away": Counter(), "unknown": Counter()}
    type_summary: Counter[str] = Counter()
    severe_by_pos_side: dict[str, Counter[str]] = {"home": Counter(), "away": Counter(), "unknown": Counter()}
    for row in rows:
        side = side_for_team(row.get("participant_id"), locs)
        bucket = absence_type_bucket(row.get("type"))
        pos = normalize_position((row.get("player") or {}))
        by_side[side]["sidelined_count"] += 1
        by_side[side][f"{bucket}_count"] += 1
        by_side[side][f"{pos}_absence_count"] += 1
        if is_severe_absence(row.get("type")):
            by_side[side]["severe_absence_count"] += 1
            severe_by_pos_side[side][pos] += 1
        type_code = str(((row.get("type") or {}).get("code") or (row.get("type") or {}).get("name") or "unknown")).lower()
        type_summary[type_code] += 1
    for side in ("home", "away"):
        for key in (
            "sidelined_count",
            "injury_count",
            "suspension_count",
            "national_team_callup_count",
            "unknown_count",
            "goalkeeper_absence_count",
            "defender_absence_count",
            "midfielder_absence_count",
            "attacker_absence_count",
            "severe_absence_count",
        ):
            by_side[side].setdefault(key, 0)
    severe_imbalance = abs(by_side["home"]["severe_absence_count"] - by_side["away"]["severe_absence_count"])
    same_pos_imbalance = 0
    for pos in ("goalkeeper", "defender", "midfielder", "attacker"):
        same_pos_imbalance = max(same_pos_imbalance, abs(severe_by_pos_side["home"][pos] - severe_by_pos_side["away"][pos]))
    signal_strength = "weak" if same_pos_imbalance >= 3 else "none"
    notes = []
    if signal_strength == "weak":
        notes.append("severe_absence_imbalance >= 3 in same position group; descriptive only")
    context = {
        "available": bool(rows),
        "home": dict(by_side["home"]),
        "away": dict(by_side["away"]),
        "absences_by_position": {
            "home": {k.replace("_absence_count", ""): by_side["home"][k] for k in ("goalkeeper_absence_count", "defender_absence_count", "midfielder_absence_count", "attacker_absence_count")},
            "away": {k.replace("_absence_count", ""): by_side["away"][k] for k in ("goalkeeper_absence_count", "defender_absence_count", "midfielder_absence_count", "attacker_absence_count")},
        },
        "absence_types_summary": dict(type_summary),
        "severe_absence_imbalance": severe_imbalance,
        "same_position_severe_absence_imbalance": same_pos_imbalance,
        "key_absences_home": None,
        "key_absences_away": None,
        "signal_direction_by_market": {"FT_1X2": "unknown", "OU_GOALS_2_5": "unknown"},
        "signal_strength": signal_strength,
        "notes": notes or ["key absence model not implemented; no player-name-based inference"],
    }
    flat = {
        "fixture_id": fixture.get("id"),
        "sidelined_available": bool(rows),
        "sidelined_count_home": by_side["home"]["sidelined_count"],
        "sidelined_count_away": by_side["away"]["sidelined_count"],
        "injuries_count_home": by_side["home"]["injury_count"],
        "injuries_count_away": by_side["away"]["injury_count"],
        "suspensions_count_home": by_side["home"]["suspension_count"],
        "suspensions_count_away": by_side["away"]["suspension_count"],
        "national_team_callups_count_home": by_side["home"]["national_team_callup_count"],
        "national_team_callups_count_away": by_side["away"]["national_team_callup_count"],
        "unknown_absence_count_home": by_side["home"]["unknown_count"],
        "unknown_absence_count_away": by_side["away"]["unknown_count"],
        "severe_absence_count_home": by_side["home"]["severe_absence_count"],
        "severe_absence_count_away": by_side["away"]["severe_absence_count"],
        "same_position_severe_absence_imbalance": same_pos_imbalance,
        "absence_types_summary": json.dumps(dict(type_summary), ensure_ascii=False),
        "signal_strength": signal_strength,
    }
    return context, flat, {"severe_absence_imbalance": int(same_pos_imbalance >= 3)}


def formation_family(formation: str | None) -> str:
    if not formation:
        return "unknown"
    try:
        first = int(str(formation).split("-", 1)[0])
    except (ValueError, TypeError):
        return "unknown"
    if first == 3:
        return "back_three"
    if first == 4:
        return "back_four"
    if first >= 5:
        return "back_five"
    return "unknown"


def attacking_shape_hint(formation: str | None) -> str:
    if not formation:
        return "unknown"
    f = str(formation)
    fam = formation_family(f)
    if fam == "back_five":
        return "conservative"
    if f in {"3-5-2", "3-4-3", "4-3-3", "4-2-3-1"}:
        return "attacking" if f in {"3-4-3", "4-3-3", "4-2-3-1"} else "balanced"
    return "balanced" if fam in {"back_three", "back_four"} else "unknown"


def formation_context(fixture: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    home = formation_from_formations(fixture, "home")
    away = formation_from_formations(fixture, "away")
    context = {
        "formation_available": bool(home or away),
        "home_formation": home,
        "away_formation": away,
        "formation_family_home": formation_family(home),
        "formation_family_away": formation_family(away),
        "attacking_shape_hint_home": attacking_shape_hint(home),
        "attacking_shape_hint_away": attacking_shape_hint(away),
        "signal_direction_by_market": {"FT_1X2": "unknown", "OU_GOALS_2_5": "unknown"},
        "signal_strength": "none",
        "notes": ["shape hints are descriptive only"],
    }
    return context, {"fixture_id": fixture.get("id"), **{k: v for k, v in context.items() if not isinstance(v, (dict, list))}}


def weather_node(fixture: dict[str, Any]) -> dict[str, Any]:
    w = fixture.get("weatherReport")
    if not isinstance(w, dict):
        w = fixture.get("weatherreport")
    return w if isinstance(w, dict) else {}


def first_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict):
        for key in ("day", "morning", "evening", "night", "speed"):
            if isinstance(value.get(key), (int, float)):
                return float(value[key])
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def venue_weather_context(fixture: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], int]:
    venue = fixture.get("venue") if isinstance(fixture.get("venue"), dict) else {}
    weather = weather_node(fixture)
    desc = str(weather.get("description") or "").lower()
    temp = first_number(weather.get("temperature"))
    wind = first_number(weather.get("wind"))
    humidity = first_number(weather.get("humidity"))
    rain_snow = any(x in desc for x in ("rain", "snow", "storm", "sleet"))
    extreme_desc = any(x in desc for x in ("heavy rain", "snow", "storm", "sleet", "thunder"))
    extreme = bool(extreme_desc or (wind is not None and wind >= 35) or (temp is not None and (temp <= 0 or temp >= 35)))
    signal_strength = "weak" if extreme else "none"
    direction = {"FT_1X2": "unknown", "OU_GOALS_2_5": "under_2_5_weak" if extreme else "unknown"}
    context = {
        "available": bool(venue or weather),
        "venue_name": venue.get("name"),
        "surface": venue.get("surface"),
        "weather_description": weather.get("description"),
        "temperature": temp,
        "wind_speed": wind,
        "humidity": humidity,
        "rain_or_snow_flag": rain_snow,
        "extreme_weather_flag": extreme,
        "signal_direction_by_market": direction,
        "signal_strength": signal_strength,
        "notes": ["weather direction only weak when extreme_weather_flag=true"] if extreme else ["venue/weather descriptive only"],
    }
    return context, {"fixture_id": fixture.get("id"), **{k: v for k, v in context.items() if not isinstance(v, (dict, list))}}, int(extreme)


def compact_base_context(fixture: dict[str, Any]) -> dict[str, Any]:
    parts = fixture.get("participants") or []
    home = away = None
    for p in parts:
        if not isinstance(p, dict):
            continue
        loc = str((p.get("meta") or {}).get("location") or "").lower()
        if loc == "home":
            home = p.get("name")
        elif loc == "away":
            away = p.get("name")
    return {
        "event_context": {
            "sportmonks_fixture_id": fixture.get("id"),
            "league_id": fixture.get("league_id"),
            "home_team": home,
            "away_team": away,
            "kickoff_utc": fixture_kickoff(fixture).isoformat() if fixture_kickoff(fixture) else None,
        },
        "supported_markets": ["FT_1X2", "OU_GOALS_2_5"],
        "base_context": {
            "h2h": {"available": False, "reason": "not joined in MM-2.4 artifact preview"},
            "team_form": {"available": False, "reason": "not joined in MM-2.4 artifact preview"},
            "rest_days": {"available": False, "reason": "not joined in MM-2.4 artifact preview"},
            "season_aggregates": {"available": False, "reason": "not joined in MM-2.4 artifact preview"},
        },
    }


def avg(rows: list[dict[str, Any]], key: str) -> float | None:
    vals = [float(r[key]) for r in rows if r.get(key) not in (None, "")]
    return round(mean(vals), 3) if vals else None


def main() -> int:
    raw = read_json(RAW_PATH, {}) or {}
    entries = raw.get("responses") or []
    enriched_blocks: list[dict[str, Any]] = []
    ds_previews: list[dict[str, Any]] = []
    context_rows: list[dict[str, Any]] = []
    line_rows: list[dict[str, Any]] = []
    avail_rows: list[dict[str, Any]] = []
    form_rows: list[dict[str, Any]] = []
    vw_rows: list[dict[str, Any]] = []
    blocked_rows: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    severe_imbalance_count = 0
    extreme_weather_count = 0

    for entry in entries:
        fixture = data_node(entry)
        if not fixture:
            continue
        gate, blocked_reasons = timestamp_gate(entry, fixture)
        fixture_id = fixture.get("id")
        decision_rows.append(
            {
                "fixture_id": fixture_id,
                "decision": "accept_enriched_context" if gate["safe_for_stage1"] else "block_enriched_context",
                "reasons": "|".join(blocked_reasons),
                "fetched_at_utc": entry.get("requested_at_utc"),
                "kickoff_utc": fixture_kickoff(fixture).isoformat() if fixture_kickoff(fixture) else "",
            }
        )
        if not gate["safe_for_stage1"]:
            blocked_rows.append({"fixture_id": fixture_id, "blocked_reason": "|".join(blocked_reasons), "gate": json.dumps(gate)})
            continue

        lc, lr = lineups_context(fixture)
        ac, ar, am = availability_context(fixture)
        fc, fr = formation_context(fixture)
        vc, vr, extreme = venue_weather_context(fixture)
        severe_imbalance_count += am["severe_absence_imbalance"]
        extreme_weather_count += extreme
        fetched_at = entry.get("requested_at_utc")
        kickoff = fixture_kickoff(fixture).isoformat() if fixture_kickoff(fixture) else None
        block = {
            "fixture_id": fixture_id,
            "enriched_sm_context": {
                "source": "sportmonks",
                "fetched_at_utc": fetched_at,
                "kickoff_utc": kickoff,
                "timestamp_gate": gate,
                "lineups_context": lc,
                "availability_context": ac,
                "formation_context": fc,
                "venue_weather_context": vc,
                "blocked_blocks": {
                    "state": "artifact_only",
                    "metadata": "artifact_only",
                    "statistics": "excluded",
                    "events": "excluded",
                    "odds": "excluded",
                    "predictions": "excluded",
                    "xGFixture": "excluded",
                    "pressure": "excluded",
                },
            },
        }
        enriched_blocks.append(block)
        preview = compact_base_context(fixture)
        preview["enriched_sm_context"] = block["enriched_sm_context"]
        ds_previews.append(preview)
        context_rows.append(
            {
                "fixture_id": fixture_id,
                "safe_for_stage1": gate["safe_for_stage1"],
                "lineups_available": lc["available"],
                "formations_available": fc["formation_available"],
                "sidelined_available": ac["available"],
                "venue_weather_available": vc["available"],
                "lineup_rows_count": lc["lineup_rows_count"],
                "listed_lineup_count_home": lc["home"]["listed_lineup_count"],
                "listed_lineup_count_away": lc["away"]["listed_lineup_count"],
                "sidelined_count_home": ac["home"]["sidelined_count"],
                "sidelined_count_away": ac["away"]["sidelined_count"],
                "lineups_signal_strength": lc["signal_strength"],
                "availability_signal_strength": ac["signal_strength"],
                "formation_signal_strength": fc["signal_strength"],
                "weather_signal_strength": vc["signal_strength"],
            }
        )
        line_rows.append(lr)
        avail_rows.append(ar)
        form_rows.append(fr)
        vw_rows.append(vr)

    strength_counter: Counter[str] = Counter()
    direction_counter: Counter[str] = Counter()
    for block in enriched_blocks:
        ctx = block["enriched_sm_context"]
        for section in ("lineups_context", "availability_context", "formation_context", "venue_weather_context"):
            sec = ctx[section]
            strength_counter[str(sec.get("signal_strength", "none"))] += 1
            for market, direction in (sec.get("signal_direction_by_market") or {}).items():
                direction_counter[f"{market}:{direction}"] += 1

    fixtures_total = len(entries)
    fixtures_safe = len(enriched_blocks)
    confirmed_true = sum(1 for r in line_rows if str(r.get("confirmed_flag_from_metadata")) == "True")
    confirmed_false = sum(1 for r in line_rows if str(r.get("confirmed_flag_from_metadata")) == "False")
    enriched_ready = (
        fixtures_safe >= 8
        and sum(1 for r in context_rows if r["lineups_available"] and r["formations_available"] and r["sidelined_available"]) >= 8
        and not blocked_rows
        and all(len(json.dumps(p, ensure_ascii=False)) < 25000 for p in ds_previews)
    )
    prompt_ready = enriched_ready
    summary = {
        "generated_at_utc": utc_now(),
        "MM2_4_timestamp_gated_enriched_context_adapter_completed": fixtures_total >= 10 and bool(enriched_blocks),
        "MM2_4_enriched_stage1_block_ready": enriched_ready,
        "MM2_4_ready_for_prompt_ab_test": prompt_ready,
        "restrictions_observed": {
            "external_calls": False,
            "db_writes": False,
            "dsr": False,
            "toa": False,
            "production": False,
            "bt2_daily_picks": False,
            "telegram": False,
            "vault": False,
            "bets": False,
        },
        "fixtures_total": fixtures_total,
        "fixtures_safe_for_stage1": fixtures_safe,
        "lineups_available_count": sum(1 for r in context_rows if r["lineups_available"]),
        "formations_available_count": sum(1 for r in context_rows if r["formations_available"]),
        "sidelined_available_count": sum(1 for r in context_rows if r["sidelined_available"]),
        "venue_weather_available_count": sum(1 for r in context_rows if r["venue_weather_available"]),
        "confirmed_flag_true_count": confirmed_true,
        "confirmed_flag_false_count": confirmed_false,
        "lineup_rows_avg": avg(context_rows, "lineup_rows_count"),
        "listed_lineup_count_home_avg": avg(context_rows, "listed_lineup_count_home"),
        "listed_lineup_count_away_avg": avg(context_rows, "listed_lineup_count_away"),
        "sidelined_home_avg": avg(context_rows, "sidelined_count_home"),
        "sidelined_away_avg": avg(context_rows, "sidelined_count_away"),
        "severe_absence_imbalance_count": severe_imbalance_count,
        "extreme_weather_count": extreme_weather_count,
        "enriched_signal_strength_distribution": dict(strength_counter),
        "enriched_signal_direction_distribution": dict(direction_counter),
        "blocked_due_to_leakage_count": sum(1 for r in blocked_rows if "score" in r["blocked_reason"] or "live" in r["blocked_reason"]),
        "blocked_due_to_timestamp_count": sum(1 for r in blocked_rows if "fetched_before_kickoff" in r["blocked_reason"]),
        "confirmed_starters_count_zero_explanation": "MM-2.3d preview counted type text containing 'start'. MM-2.4 counts SportMonks type.code='lineup' as listed/probable starter, while metadata confirmed=false prevents labeling as confirmed starters.",
    }

    write_json(OUT / "mm2_4_enriched_context_summary.json", summary)
    write_json(OUT / "mm2_4_enriched_stage1_blocks.json", enriched_blocks)
    write_json(OUT / "mm2_4_enriched_stage1_ds_input_preview.json", ds_previews)
    write_csv(OUT / "mm2_4_enriched_context_rows.csv", context_rows, ["fixture_id", "safe_for_stage1", "lineups_available", "formations_available", "sidelined_available", "venue_weather_available", "lineup_rows_count", "listed_lineup_count_home", "listed_lineup_count_away", "sidelined_count_home", "sidelined_count_away", "lineups_signal_strength", "availability_signal_strength", "formation_signal_strength", "weather_signal_strength"])
    write_csv(OUT / "mm2_4_lineups_context_rows.csv", line_rows, ["fixture_id", "lineup_available", "lineup_rows_count", "confirmed_flag_from_metadata", "confirmed_status", "home_listed_lineup_count", "away_listed_lineup_count", "home_goalkeeper_count", "away_goalkeeper_count", "home_defender_count", "away_defender_count", "home_midfielder_count", "away_midfielder_count", "home_attacker_count", "away_attacker_count", "home_formation_from_formations", "away_formation_from_formations", "home_formation_from_metadata", "away_formation_from_metadata", "formation_match_consistency_home", "formation_match_consistency_away"])
    write_csv(OUT / "mm2_4_availability_context_rows.csv", avail_rows, ["fixture_id", "sidelined_available", "sidelined_count_home", "sidelined_count_away", "injuries_count_home", "injuries_count_away", "suspensions_count_home", "suspensions_count_away", "national_team_callups_count_home", "national_team_callups_count_away", "unknown_absence_count_home", "unknown_absence_count_away", "severe_absence_count_home", "severe_absence_count_away", "same_position_severe_absence_imbalance", "absence_types_summary", "signal_strength"])
    write_csv(OUT / "mm2_4_formation_context_rows.csv", form_rows, ["fixture_id", "formation_available", "home_formation", "away_formation", "formation_family_home", "formation_family_away", "attacking_shape_hint_home", "attacking_shape_hint_away", "signal_strength"])
    write_csv(OUT / "mm2_4_venue_weather_context_rows.csv", vw_rows, ["fixture_id", "available", "venue_name", "surface", "weather_description", "temperature", "wind_speed", "humidity", "rain_or_snow_flag", "extreme_weather_flag", "signal_strength"])
    write_csv(OUT / "mm2_4_blocked_leakage_rows.csv", blocked_rows, ["fixture_id", "blocked_reason", "gate"])
    write_csv(OUT / "mm2_4_adapter_decision_log.csv", decision_rows, ["fixture_id", "decision", "reasons", "fetched_at_utc", "kickoff_utc"])

    write_audit(summary)
    print(json.dumps({"ok": True, "summary": summary}, ensure_ascii=False, indent=2))
    return 0


def write_audit(summary: dict[str, Any]) -> None:
    md = f"""# MM-2.4 Timestamp-Gated Enriched Context Adapter Audit

## 1. Executive summary

- `MM2_4_timestamp_gated_enriched_context_adapter_completed`: `{summary['MM2_4_timestamp_gated_enriched_context_adapter_completed']}`
- `MM2_4_enriched_stage1_block_ready`: `{summary['MM2_4_enriched_stage1_block_ready']}`
- `MM2_4_ready_for_prompt_ab_test`: `{summary['MM2_4_ready_for_prompt_ab_test']}`
- Fixtures processed: `{summary['fixtures_total']}`
- Fixtures safe for Stage 1: `{summary['fixtures_safe_for_stage1']}`

## 2. Scope and restrictions

Artifact-only. No external calls, no DSR, no TOA, no DB writes, no production, no `bt2_daily_picks`, no Telegram, no vault, no bets, no tennis, no odds, no fixture-target events/statistics, and no performance claims.

## 3. Inputs used

MM-2.3d pre-kickoff raw responses, signal presence, timestamp safety, adapter preview, MM-1.9 package artifact, and MM-2.2 compaction artifacts.

## 4. Timestamp gate

The adapter accepts only fixtures fetched before kickoff, state `NS / Not Started`, null `result_info`, and absent scores, periods, live minute/timeline, events, statistics, and odds.

## 5. Lineups adapter

SportMonks `type.code='lineup'` is counted as listed/probable starter. Because metadata `confirmed=false` in this sample, the adapter does not label those rows as confirmed starters. This explains the MM-2.3d preview count of 0: it searched for `start`, while the provider uses `lineup`.

## 6. Availability/sidelined adapter

Sidelined rows are counted by side, absence type, position bucket, and severe-rule tokens. `key_absences_home/away` remain null because there is no player importance model.

## 7. Formation adapter

Formations are extracted from `formations` and cross-checked against metadata when present. Formation family and shape hints are descriptive only.

## 8. Venue/weather adapter

Venue/weather is compacted into venue name, surface, weather description, temperature, wind, humidity, rain/snow, and extreme-weather flags.

## 9. Blocked fields and leakage controls

`state` and `metadata` are artifact-only. `statistics`, `events`, `odds`, `predictions`, `xGFixture`, and `pressure` are excluded. Blocked leakage rows: `{summary['blocked_due_to_leakage_count']}`.

## 10. Signal direction policy

Default signal direction remains unknown and signal strength remains none. Weak signals are allowed only for explicit rule cases: severe same-position absence imbalance or extreme weather.

## 11. Enriched Stage 1 preview

Generated `mm2_4_enriched_stage1_ds_input_preview.json` with base context placeholders plus compact `enriched_sm_context`. No raw player payload lists are included in the prompt preview.

## 12. Metrics

```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

## 13. Risks and limitations

Timestamp safety is based on fetch time and fixture state, not internal block timestamps. Key absence scoring and player importance are not implemented. Formation/weather hints are descriptive, not picks.

## 14. What this proves

SportMonks pre-kickoff lineups, sidelined, formations, and venue/weather can be transformed into compact, gated, auditable Stage 1 context without result/live leakage and without invented edge.

## 15. What this does not prove

It does not prove predictive value, ROI, hit rate, or final prompt behavior under DSR. It also does not prove every future fixture will publish the same blocks at all timing windows.

## 16. Recommended next step

Proceed to MM-2.5 Enriched Prompt Dry Run / A-B Package Build: baseline vs enriched Stage 1 package, no DSR yet, measuring prompt size and visible signal coverage.
"""
    AUDITS.mkdir(parents=True, exist_ok=True)
    (AUDITS / "MM2_4_TIMESTAMP_GATED_ENRICHED_CONTEXT_ADAPTER_AUDIT.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

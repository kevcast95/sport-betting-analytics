#!/usr/bin/env python3
"""
BT2 blind scrubbed replay audit.

No production writes. Optional DSR call writes only local artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_dsr_contract import PIPELINE_VERSION_DEFAULT
from apps.api.bt2_dsr_postprocess import postprocess_dsr_pick
from apps.api.bt2_dsr_shadow_native_deepseek_v6 import (
    DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
    deepseek_suggest_batch_shadow_native_v6_with_trace,
    narrative_extract_rationale_v6,
)
from apps.api.bt2_dsr_shadow_native_prompt_v6 import (
    SYSTEM_PROMPT_SHADOW_NATIVE_V6,
    build_user_prompt_shadow_native_v6,
)
from apps.api.bt2_settings import bt2_settings

SOURCE_AUDIT = ROOT / "scripts/outputs/bt2_shadow_dsr_replay/dsr_native_full_replay_v6_sample_audit.json"
SOURCE_BLIND = ROOT / "scripts/outputs/bt2_shadow_dsr_replay/dsr_native_full_replay_v6_sample_blind_only.json"
OUT_SCAN = ROOT / "scripts/outputs/blind_scrubbed_replay_universe_scan.json"
OUT_INPUTS = ROOT / "scripts/outputs/blind_scrubbed_replay_ds_inputs.json"
OUT_DSR = ROOT / "scripts/outputs/blind_scrubbed_replay_dsr_outputs.json"
OUT_ROWS = ROOT / "scripts/outputs/blind_scrubbed_replay_rows.csv"
OUT_MD = ROOT / "docs/bettracker2/audits/BLIND_SCRUBBED_REPLAY_AUDIT.md"
FUTURE_BASE = datetime(2099, 7, 1, 18, 0, tzinfo=timezone.utc)

FORBIDDEN_NAME_PARTS = (
    "score",
    "result",
    "winner",
    "final",
    "full_time",
    "fulltime",
    "elapsed",
    "period",
    "minute",
    "ft_score",
)


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1)


def _jsonable(v: Any) -> Any:
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def _parse_dt(v: Any) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    s = str(v or "").strip()
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s or "").lower())).strip()


def _has_forbidden_key(obj: Any, prefix: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            lk = str(k).lower()
            if any(x in lk for x in FORBIDDEN_NAME_PARTS):
                out.append(p)
            out.extend(_has_forbidden_key(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):
            out.extend(_has_forbidden_key(v, f"{prefix}[{i}]"))
    return out


def _favorite(consensus: dict[str, Any]) -> Optional[str]:
    ft = consensus.get("FT_1X2") if isinstance(consensus, dict) else None
    if not isinstance(ft, dict):
        return None
    try:
        vals = {k: float(ft[k]) for k in ("home", "draw", "away")}
    except (KeyError, TypeError, ValueError):
        return None
    return min(vals, key=vals.get)


def _odds_tier(consensus: dict[str, Any], side: str) -> str:
    ft = consensus.get("FT_1X2") if isinstance(consensus, dict) else None
    if not isinstance(ft, dict) or side not in ("home", "draw", "away"):
        return "n/a"
    try:
        order = sorted(("home", "draw", "away"), key=lambda k: float(ft[k]))
    except (KeyError, TypeError, ValueError):
        return "n/a"
    return ("favorite", "middle", "longshot")[order.index(side)]


def _market_age_bucket(minutes: Optional[float]) -> str:
    if minutes is None:
        return "unknown"
    if minutes < 0:
        return "post_reconstructed_or_unknown"
    if minutes < 15:
        return "<15m before kickoff"
    if minutes <= 60:
        return "15-60m before kickoff"
    if minutes <= 360:
        return "1-6h before kickoff"
    return ">6h before kickoff"


def _scan_db(cur: Any) -> dict[str, Any]:
    scan: dict[str, Any] = {"tables": {}, "notes": []}
    queries = {
        "bt2_events": """
            SELECT COUNT(*)::int n, MIN(kickoff_utc) mn, MAX(kickoff_utc) mx
            FROM bt2_events
        """,
        "bt2_odds_snapshot": """
            SELECT COUNT(*)::int n, MIN(fetched_at) mn, MAX(fetched_at) mx,
                   COUNT(DISTINCT event_id)::int events
            FROM bt2_odds_snapshot
        """,
        "raw_sportmonks_fixtures": """
            SELECT COUNT(*)::int n, MIN(fixture_date) mn, MAX(fixture_date) mx
            FROM raw_sportmonks_fixtures
        """,
        "bt2_shadow_daily_picks": """
            SELECT COUNT(*)::int n, MIN(operating_day_key) mn, MAX(operating_day_key) mx,
                   COUNT(*) FILTER (WHERE dsr_parse_status IS NOT NULL)::int dsr_rows
            FROM bt2_shadow_daily_picks
        """,
        "bt2_shadow_pick_inputs": """
            SELECT COUNT(*)::int n, COUNT(DISTINCT shadow_daily_pick_id)::int picks_with_inputs
            FROM bt2_shadow_pick_inputs
        """,
        "bt2_shadow_provider_snapshots": """
            SELECT COUNT(*)::int n, MIN(provider_snapshot_time) mn, MAX(provider_snapshot_time) mx,
                   COUNT(DISTINCT sm_fixture_id)::int fixtures
            FROM bt2_shadow_provider_snapshots
        """,
        "bt2_shadow_pick_eval": """
            SELECT COUNT(*)::int n, COUNT(*) FILTER (WHERE eval_status IS NOT NULL)::int eval_rows
            FROM bt2_shadow_pick_eval
        """,
    }
    for table, q in queries.items():
        try:
            cur.execute(q)
            scan["tables"][table] = dict(cur.fetchone())
        except Exception as exc:  # read-only audit, tolerate missing tables
            scan["tables"][table] = {"error": str(exc)}
    cur.execute(
        """
        SELECT COALESCE(l.name,'UNKNOWN') league, COUNT(*)::int n,
               MIN(e.kickoff_utc) mn, MAX(e.kickoff_utc) mx
        FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        GROUP BY 1
        ORDER BY n DESC
        LIMIT 20
        """
    )
    scan["events_by_league_top20"] = [dict(r) for r in cur.fetchall()]
    cur.execute(
        """
        SELECT market, COUNT(*)::int rows, COUNT(DISTINCT event_id)::int events,
               MIN(fetched_at) mn, MAX(fetched_at) mx
        FROM bt2_odds_snapshot
        GROUP BY market
        ORDER BY rows DESC
        """
    )
    scan["bt2_odds_snapshot_by_market"] = [dict(r) for r in cur.fetchall()]
    cur.execute(
        """
        SELECT operating_day_key, COUNT(*)::int n
        FROM bt2_shadow_daily_picks
        GROUP BY operating_day_key
        ORDER BY operating_day_key
        """
    )
    scan["shadow_events_by_operating_day"] = [dict(r) for r in cur.fetchall()]
    return scan


def _scan_artifacts() -> dict[str, Any]:
    out: dict[str, Any] = {"files": [], "sample_audit": {}}
    for p in sorted((ROOT / "scripts/outputs").rglob("*")):
        if not p.is_file() or p.suffix.lower() not in (".json", ".csv", ".md"):
            continue
        rel = str(p.relative_to(ROOT))
        if any(x in rel for x in ("shadow", "backtest", "replay", "ds_input", "dsr")):
            out["files"].append({"path": rel, "bytes": p.stat().st_size})
    audit = json.loads(SOURCE_AUDIT.read_text(encoding="utf-8"))
    cases = audit.get("cases") or []
    out["sample_audit"] = {
        "path": str(SOURCE_AUDIT.relative_to(ROOT)),
        "cases": len(cases),
        "date_range": [
            min((c.get("kickoff_utc") for c in cases if c.get("kickoff_utc")), default=None),
            max((c.get("kickoff_utc") for c in cases if c.get("kickoff_utc")), default=None),
        ],
        "by_league": dict(Counter(c.get("league_name") for c in cases)),
        "by_market": dict(Counter("FT_1X2" for _ in cases)),
        "by_eval_status": dict(Counter(c.get("eval_status") for c in cases)),
        "by_odds_tier": dict(Counter(c.get("odds_tier_vs_consensus") for c in cases)),
        "with_ds_input": sum(1 for c in cases if c.get("ds_input_blind")),
        "with_dsr_output": sum(1 for c in cases if c.get("model_raw_response_full")),
        "with_result_or_eval": sum(1 for c in cases if c.get("eval_status") or c.get("result_score_text")),
        "data_temporality_assessment": (
            "Mixed: by_bookmaker rows include fetched_at values near kickoff and can be validated as pre-kickoff; "
            "some contextual SM blocks in ds_input_blind include post-match statistics/corners and must be scrubbed."
        ),
    }
    return out


def _validate_market(case: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    kickoff = _parse_dt(case.get("kickoff_utc"))
    odds = item.get("processed", {}).get("odds_featured", {})
    rows = odds.get("by_bookmaker") if isinstance(odds.get("by_bookmaker"), list) else []
    by_market: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if isinstance(r, dict):
            by_market[str(r.get("market_canonical") or "UNKNOWN")].append(r)
    markets: list[dict[str, Any]] = []
    safe_any = False
    for market, mrows in sorted(by_market.items()):
        fts = [_parse_dt(r.get("fetched_at")) for r in mrows]
        fts = [x for x in fts if x is not None]
        fetched_at = min(fts) if fts else None
        minutes = (kickoff - fetched_at).total_seconds() / 60 if kickoff and fetched_at else None
        is_pre: Any = True if minutes is not None and minutes > 0 else False if minutes is not None else "unknown"
        safe_any = safe_any or is_pre is True
        markets.append(
            {
                "toa_market_available": True,
                "market_canonical": market,
                "selections": sorted({str(r.get("selection_canonical")) for r in mrows if r.get("selection_canonical")}),
                "fetched_at": fetched_at.isoformat() if fetched_at else None,
                "kickoff_real_utc": kickoff.isoformat() if kickoff else None,
                "minutes_before_kickoff": round(minutes, 3) if minutes is not None else None,
                "is_pre_kickoff_market": is_pre,
                "bookmaker_count": len({str(r.get("bookmaker")) for r in mrows if r.get("bookmaker")}),
                "consensus_source": "ds_input_blind.processed.odds_featured.consensus",
                "odds_snapshot_source_path_or_table": str(SOURCE_AUDIT.relative_to(ROOT)),
                "market_age_bucket": _market_age_bucket(minutes),
            }
        )
    if not markets:
        markets.append(
            {
                "toa_market_available": "unknown",
                "market_canonical": "UNKNOWN",
                "selections": [],
                "fetched_at": None,
                "kickoff_real_utc": kickoff.isoformat() if kickoff else None,
                "minutes_before_kickoff": None,
                "is_pre_kickoff_market": "unknown",
                "bookmaker_count": 0,
                "consensus_source": "none",
                "odds_snapshot_source_path_or_table": None,
                "market_age_bucket": "unknown",
            }
        )
    return {"markets": markets, "pre_kickoff_market_validated": safe_any}


def _scrub_case(case: dict[str, Any], idx: int) -> dict[str, Any]:
    src = case["ds_input_blind"]
    src_proc = src.get("processed") or {}
    src_diag = src.get("diagnostics") or {}
    future_ko = FUTURE_BASE + timedelta(days=idx)
    removed: list[dict[str, str]] = []
    kept: list[str] = []

    def keep(path: str) -> None:
        kept.append(path)

    def remove(path: str, reason: str) -> None:
        removed.append({"path": path, "reason": reason})

    market_validation = _validate_market(case, src)
    odds_rows = src_proc.get("odds_featured", {}).get("by_bookmaker")
    if not isinstance(odds_rows, list):
        odds_rows = []
    kickoff = _parse_dt(case.get("kickoff_utc"))
    safe_odds_rows = []
    for r in odds_rows:
        ft = _parse_dt(r.get("fetched_at")) if isinstance(r, dict) else None
        if kickoff and ft and ft < kickoff:
            safe_odds_rows.append(r)
        else:
            remove("processed.odds_featured.by_bookmaker[]", "removed_by_blind_scrub: odds_timestamp_not_confirmed_pre_kickoff")

    processed: dict[str, Any] = {
        "odds_featured": {
            "consensus": src_proc.get("odds_featured", {}).get("consensus") or {},
            "by_bookmaker": safe_odds_rows,
        },
        "lineups": {"available": False},
        "h2h": {"available": False},
        "statistics": {"available": False},
        "team_streaks": {"available": False},
        "team_season_stats": {"available": False},
        "fixture_conditions": {"available": False},
        "match_officials": {"available": False},
        "squad_availability": {"available": False},
        "tactical_shape": {"available": False},
        "prediction_signals": {"available": False},
        "broadcast_notes": {"available": False},
        "fixture_advanced_sm": {"available": False},
    }
    keep("processed.odds_featured.consensus")
    keep("processed.odds_featured.by_bookmaker[pre_kickoff_only]")

    h2h = src_proc.get("h2h")
    if isinstance(h2h, dict) and h2h.get("available") is True:
        processed["h2h"] = h2h
        keep("processed.h2h")
    stats = src_proc.get("statistics")
    if isinstance(stats, dict):
        cdm = stats.get("cdm_from_bt2_events")
        if isinstance(cdm, dict) and cdm.get("available") is True:
            processed["statistics"] = {"available": True, "cdm_from_bt2_events": cdm}
            keep("processed.statistics.cdm_from_bt2_events")
        if "from_sm_fixture" in stats:
            remove("processed.statistics.from_sm_fixture", "removed_by_blind_scrub: fixture statistics/corners may be post-match")
    for block in (
        "lineups",
        "fixture_conditions",
        "match_officials",
        "squad_availability",
        "tactical_shape",
        "prediction_signals",
        "fixture_advanced_sm",
    ):
        if isinstance(src_proc.get(block), dict) and src_proc.get(block, {}).get("available") is True:
            remove(f"processed.{block}", "removed_by_blind_scrub: pre_match_availability_unknown")

    diagnostics = {
        "market_coverage": src_diag.get("market_coverage") or {},
        "markets_available": src_diag.get("markets_available") or [],
        "lineups_ok": False,
        "h2h_ok": bool(processed["h2h"].get("available")),
        "statistics_ok": bool(processed["statistics"].get("available")),
        "fetch_errors": sorted(set((src_diag.get("fetch_errors") or []) + [r["reason"] for r in removed])),
        "raw_fixture_missing": bool(src_diag.get("raw_fixture_missing", False)),
        "team_season_stats_reason": "removed_by_blind_scrub: pre_match_availability_unknown",
        "sfs_fusion_applied": bool(src_diag.get("sfs_fusion_applied", False)),
        "sfs_fusion_synthetic_rows": int(src_diag.get("sfs_fusion_synthetic_rows") or 0),
        "prob_coherence": src_diag.get("prob_coherence") or {},
    }
    keep("diagnostics.market_coverage")
    keep("diagnostics.prob_coherence")

    scrubbed = {
        "event_id": 900000 + idx,
        "sport": "football",
        "selection_tier": src.get("selection_tier", "A"),
        "schedule_display": {
            "utc_iso": future_ko.isoformat().replace("+00:00", "Z"),
            "timezone_reference": "UTC",
        },
        "event_context": {
            "league_name": case.get("league_name") or src.get("event_context", {}).get("league_name"),
            "home_team": case.get("home_team") or src.get("event_context", {}).get("home_team"),
            "away_team": case.get("away_team") or src.get("event_context", {}).get("away_team"),
            "match_state": "scheduled",
            "league_tier": src.get("event_context", {}).get("league_tier"),
        },
        "processed": processed,
        "diagnostics": diagnostics,
    }
    before_bad = _has_forbidden_key(src)
    after_bad = _has_forbidden_key(scrubbed)
    risk_after = "HIGH_RISK" if after_bad else "PARTIAL" if any("pre_match_availability_unknown" in r["reason"] for r in removed) else "SAFE"
    if not market_validation["pre_kickoff_market_validated"]:
        risk_after = "HIGH_RISK"
    explanation = (
        "Allowed odds, market diagnostics, h2h and CDM pre-kickoff context; removed SM fixture stats/corners and availability-unknown blocks."
    )
    return {
        "source_shadow_pick_id": case.get("source_shadow_pick_id"),
        "source_shadow_daily_pick_id": case.get("shadow_daily_pick_id"),
        "sm_fixture_id": case.get("sm_fixture_id"),
        "bt2_event_id": case.get("bt2_event_id"),
        "league_name": case.get("league_name"),
        "home_team": case.get("home_team"),
        "away_team": case.get("away_team"),
        "kickoff_real_utc": case.get("kickoff_utc"),
        "eval_status_real_hidden_from_dsr": case.get("eval_status"),
        "result_score_text_hidden_from_dsr": case.get("result_score_text"),
        "group": "A_pre_kickoff_market_validated" if market_validation["pre_kickoff_market_validated"] else "B_market_timestamp_unknown",
        "ds_input_blind_scrubbed": scrubbed,
        "market_validation": market_validation,
        "leakage_audit": {
            "removed_fields": removed,
            "kept_fields": kept,
            "leakage_risk_before": "HIGH_RISK" if before_bad or "from_sm_fixture" in json.dumps(src) else "PARTIAL",
            "leakage_risk_after": risk_after,
            "pregame_safe_score": risk_after,
            "forbidden_keys_before": before_bad[:40],
            "forbidden_keys_after": after_bad[:40],
            "explanation": explanation,
        },
    }


def _select_sample(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def fav_price(c: dict[str, Any]) -> float:
        ft = c.get("ds_input_blind", {}).get("processed", {}).get("odds_featured", {}).get("consensus", {}).get("FT_1X2", {})
        try:
            return min(float(ft[k]) for k in ("home", "draw", "away") if k in ft)
        except ValueError:
            return 99.0

    pools = {
        "clear": [c for c in cases if fav_price(c) < 1.7],
        "moderate": [c for c in cases if 1.7 <= fav_price(c) <= 2.35],
        "balanced": [c for c in cases if fav_price(c) > 2.35],
    }
    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    for key, target in (("clear", 4), ("moderate", 4), ("balanced", 4)):
        for c in pools[key]:
            sid = int(c["source_shadow_pick_id"])
            if sid not in seen:
                selected.append(c)
                seen.add(sid)
            if sum(1 for x in selected if x in pools[key]) >= target:
                break
    for status in ("hit", "miss", "pending_result"):
        if any(c.get("eval_status") == status for c in selected):
            continue
        for c in cases:
            sid = int(c["source_shadow_pick_id"])
            if c.get("eval_status") == status and sid not in seen:
                selected.append(c)
                seen.add(sid)
                break
    for c in cases:
        if len(selected) >= min(20, len(cases)):
            break
        sid = int(c["source_shadow_pick_id"])
        if sid not in seen:
            selected.append(c)
            seen.add(sid)
    return selected[:30]


def _mentions_odds(rationale: str) -> bool:
    s = _norm(rationale)
    return any(x in s for x in ("odd", "odds", "cuota", "market", "mercado", "consensus", "favorit"))


def _mentions_signal(rationale: str) -> bool:
    s = _norm(rationale)
    return any(x in s for x in ("h2h", "racha", "form", "forma", "rest", "descanso", "estad", "context", "local"))


def _quality(rationale: str) -> str:
    o = _mentions_odds(rationale)
    s = _mentions_signal(rationale)
    if o and s:
        return "odds_plus_signal"
    if o:
        return "odds_only"
    if s:
        return "signal_driven"
    return "unsupported"


def _run_dsr(scrubbed_rows: list[dict[str, Any]], run_key: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "run_key": run_key,
        "mode": "shadow_artifact_only",
        "requested": True,
        "called": False,
        "model": "deepseek-v4-pro",
        "prompt_version": DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
        "system_prompt": SYSTEM_PROMPT_SHADOW_NATIVE_V6,
        "user_prompt": None,
        "raw_response": None,
        "trace": None,
        "outputs": [],
    }
    api_key = (bt2_settings.deepseek_api_key or "").strip()
    if not api_key:
        out["error"] = "missing_deepseek_api_key"
        return out
    ds_items = [r["ds_input_blind_scrubbed"] for r in scrubbed_rows]
    user_prompt = build_user_prompt_shadow_native_v6(
        operating_day_key="2099-07-01",
        batch={
            "operating_day_key": "2099-07-01",
            "pipeline_version": PIPELINE_VERSION_DEFAULT,
            "sport": "football",
            "ds_input": ds_items,
        },
    )
    ds_map, trace = deepseek_suggest_batch_shadow_native_v6_with_trace(
        ds_items,
        operating_day_key="2099-07-01",
        api_key=api_key,
        base_url=str(bt2_settings.bt2_dsr_deepseek_base_url),
        model="deepseek-v4-pro",
        timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
        max_retries=int(bt2_settings.bt2_dsr_max_retries),
    )
    tr = asdict(trace)
    out["called"] = True
    out["user_prompt"] = user_prompt
    out["raw_response"] = tr.get("raw_content_full")
    out["trace"] = {k: v for k, v in tr.items() if k != "raw_content_full"}
    by_event = {int(r["ds_input_blind_scrubbed"]["event_id"]): r for r in scrubbed_rows}
    for eid, row in by_event.items():
        item = row["ds_input_blind_scrubbed"]
        raw = ds_map.get(eid)
        consensus = item["processed"]["odds_featured"]["consensus"]
        fav = _favorite(consensus)
        rec = {
            "event_id": eid,
            "source_shadow_pick_id": row["source_shadow_pick_id"],
            "league_name": row["league_name"],
            "home_team": row["home_team"],
            "away_team": row["away_team"],
            "group": row["group"],
            "ds_input_sent": item,
            "raw_response": tr.get("raw_content_full"),
            "parsed_response": None,
            "status": "dsr_failed",
            "rationale": "",
            "confidence": None,
            "no_pick_reason": "",
            "selected_side": None,
            "selected_market": None,
            "favorite_benchmark": {
                "consensus_favorite_side": fav,
                "dsr_selected_side": None,
                "pick_matches_favorite": None,
                "odds_tier": "n/a",
                "rationale_mentions_odds": None,
                "rationale_mentions_non_odds_signal": None,
                "rationale_quality": "unsupported",
            },
            "posterior_eval": {
                "eval_status_real": row["eval_status_real_hidden_from_dsr"],
                "result_score_text_real": row["result_score_text_hidden_from_dsr"],
                "dsr_hit_miss_pending": None,
                "favorite_hit_miss_pending": None,
                "dsr_vs_favorite": None,
                "warning": "posterior eval only; not clean performance proof",
            },
        }
        if raw is not None:
            narrative, conf, mmc, msc, _declared = raw
            rationale = narrative_extract_rationale_v6(narrative)
            m = re.search(r"\[no_pick_reason\](.*?)\[/no_pick_reason\]", narrative or "", re.S)
            if mmc == "FT_1X2" and msc in ("home", "draw", "away"):
                rec["selected_market"] = mmc
                rec["selected_side"] = msc
                rec["favorite_benchmark"].update(
                    {
                        "dsr_selected_side": msc,
                        "pick_matches_favorite": msc == fav,
                        "odds_tier": _odds_tier(consensus, msc),
                        "rationale_mentions_odds": _mentions_odds(rationale),
                        "rationale_mentions_non_odds_signal": _mentions_signal(rationale),
                        "rationale_quality": _quality(rationale),
                    }
                )
            pp = postprocess_dsr_pick(
                narrative_es=rationale,
                confidence_label=conf,
                market_canonical=mmc,
                selection_canonical=msc,
                model_declared_odds=None,
                consensus=consensus,
                market_coverage=item["diagnostics"]["market_coverage"],
                event_id=eid,
                home_team=item["event_context"]["home_team"],
                away_team=item["event_context"]["away_team"],
            )
            rec["parsed_response"] = {
                "narrative": narrative,
                "confidence_label": conf,
                "market_canonical": mmc,
                "selection_canonical": msc,
            }
            rec["rationale"] = rationale
            rec["confidence"] = conf
            rec["no_pick_reason"] = m.group(1).strip() if m else ""
            if pp:
                _n, _c, mmc_f, msc_f = pp
                rec["status"] = "ok"
                rec["selected_market"] = mmc_f
                rec["selected_side"] = msc_f
                rec["favorite_benchmark"].update(
                    {
                        "dsr_selected_side": msc_f,
                        "pick_matches_favorite": msc_f == fav,
                        "odds_tier": _odds_tier(consensus, msc_f),
                        "rationale_mentions_odds": _mentions_odds(rationale),
                        "rationale_mentions_non_odds_signal": _mentions_signal(rationale),
                        "rationale_quality": _quality(rationale),
                    }
                )
                real = rec["posterior_eval"]["eval_status_real"]
                rec["posterior_eval"]["dsr_hit_miss_pending"] = real
                rec["posterior_eval"]["favorite_hit_miss_pending"] = "not_computed_from_truth_side_in_artifact"
                rec["posterior_eval"]["dsr_vs_favorite"] = "same_pick" if msc_f == fav else "different_pick"
            else:
                rec["status"] = "postprocess_reject"
        out["outputs"].append(rec)
    return out


def _write_csv(scrubbed: list[dict[str, Any]], dsr: dict[str, Any]) -> None:
    by_src = {r["source_shadow_pick_id"]: r for r in dsr.get("outputs", [])}
    fields = [
        "source_shadow_pick_id",
        "event_id",
        "group",
        "league_name",
        "home_team",
        "away_team",
        "kickoff_real_utc",
        "pregame_safe_score",
        "selected_side",
        "consensus_favorite_side",
        "pick_matches_favorite",
        "rationale_quality",
        "eval_status_real",
    ]
    with OUT_ROWS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in scrubbed:
            o = by_src.get(r["source_shadow_pick_id"], {})
            fb = o.get("favorite_benchmark") or {}
            w.writerow(
                {
                    "source_shadow_pick_id": r["source_shadow_pick_id"],
                    "event_id": r["ds_input_blind_scrubbed"]["event_id"],
                    "group": r["group"],
                    "league_name": r["league_name"],
                    "home_team": r["home_team"],
                    "away_team": r["away_team"],
                    "kickoff_real_utc": r["kickoff_real_utc"],
                    "pregame_safe_score": r["leakage_audit"]["pregame_safe_score"],
                    "selected_side": o.get("selected_side"),
                    "consensus_favorite_side": fb.get("consensus_favorite_side"),
                    "pick_matches_favorite": fb.get("pick_matches_favorite"),
                    "rationale_quality": fb.get("rationale_quality"),
                    "eval_status_real": r["eval_status_real_hidden_from_dsr"],
                }
            )


def _write_md(scan: dict[str, Any], scrubbed: list[dict[str, Any]], dsr: dict[str, Any]) -> None:
    outs = dsr.get("outputs") or []
    ok = [o for o in outs if o.get("status") == "ok"]
    fav_match = sum(1 for o in ok if o.get("favorite_benchmark", {}).get("pick_matches_favorite") is True)
    quality = Counter(o.get("favorite_benchmark", {}).get("rationale_quality") for o in ok)
    groups = Counter(r["group"] for r in scrubbed)
    safe = Counter(r["leakage_audit"]["pregame_safe_score"] for r in scrubbed)
    lines = [
        "# Blind Scrubbed Replay Audit",
        "",
        "## 1. Executive summary",
        f"- Selected sample: `{len(scrubbed)}` football events from existing shadow-native v6 artifacts.",
        f"- Market groups: `{dict(groups)}`.",
        f"- DSR called: `{dsr.get('called')}`; parsed OK: `{len(ok)}/{len(outs)}`.",
        f"- DSR matched consensus favorite: `{fav_match}/{len(ok)}`.",
        f"- Rationale quality: `{dict(quality)}`.",
        "",
        "## 2. Why this is not a clean backtest",
        "- Events are historical and the package is synthetic/future-dated.",
        "- Some source inputs were reconstructed from shadow/backtest artifacts, not guaranteed raw pre-match product snapshots.",
        "- Posterior eval is reported only after DSR output and must not be read as product performance.",
        "",
        "## 3. Available local universe",
        f"- `bt2_events`: `{scan['db']['tables'].get('bt2_events', {}).get('n')}` rows.",
        f"- `bt2_odds_snapshot`: `{scan['db']['tables'].get('bt2_odds_snapshot', {}).get('n')}` rows.",
        f"- `bt2_shadow_daily_picks`: `{scan['db']['tables'].get('bt2_shadow_daily_picks', {}).get('n')}` rows.",
        f"- Source sample artifact: `{scan['artifacts']['sample_audit'].get('cases')}` cases with ds_input.",
        f"- Source sample by league: `{scan['artifacts']['sample_audit'].get('by_league')}`.",
        "",
        "## 4. Selected sample",
    ]
    for r in scrubbed:
        lines.append(f"- `{r['source_shadow_pick_id']}` {r['league_name']}: {r['home_team']} vs {r['away_team']} ({r['group']}).")
    lines += [
        "",
        "## 5. Scrubbing rules",
        "- Allowlist retained identity, future kickoff, teams, league, odds consensus/by-bookmaker with pre-kickoff timestamps, market coverage, prob coherence, h2h, and CDM context explicitly scoped before kickoff.",
        "- Removed result/status/final fields, SM fixture stats/corners, lineups/injuries/tactical/prediction blocks without pre-kickoff availability proof, pressure/matchfacts/xG/AI-style blocks.",
        "",
        "## 6. Leakage audit",
        f"- Pregame safe scores after scrub: `{dict(safe)}`.",
        "- All rows keep methodological caveat because some contextual blocks originate from replay artifacts.",
        "",
        "## 7. ds_input signal coverage after scrubbing",
    ]
    for key in ("h2h", "statistics", "lineups", "squad_availability", "fixture_advanced_sm"):
        n = sum(1 for r in scrubbed if (r["ds_input_blind_scrubbed"]["processed"].get(key) or {}).get("available"))
        lines.append(f"- {key}: `{n}/{len(scrubbed)}`.")
    lines += [
        "",
        "## 8. DSR output summary",
        f"- Prompt version: `{dsr.get('prompt_version')}`. Run key: `{dsr.get('run_key')}`.",
        f"- Status counts: `{dict(Counter(o.get('status') for o in outs))}`.",
        "",
        "## 9. Favorite benchmark comparison",
        f"- Favorite match rate: `{fav_match}/{len(ok)}`.",
        "",
        "## 10. Rationale quality audit",
        f"- `{dict(quality)}`.",
        "",
        "## 11. Optional posterior eval",
        f"- Hidden real eval statuses in sample: `{dict(Counter(r['eval_status_real_hidden_from_dsr'] for r in scrubbed))}`.",
        "- This is separate posterior annotation, not clean performance evidence.",
        "",
        "## TOA pre-kickoff market coverage",
        f"- Included with pre-kickoff market validated: `{groups.get('A_pre_kickoff_market_validated', 0)}`.",
        f"- Included with unknown market timestamp: `{groups.get('B_market_timestamp_unknown', 0)}`.",
        "- Market evidence comes from `ds_input_blind.processed.odds_featured.by_bookmaker[].fetched_at` in the source artifact; rows without pre-kickoff evidence are not mixed into Group A interpretation.",
        "",
        "## Eventos excluidos por falta de mercado pre-kickoff",
        "- None from the selected source sample; all selected rows had at least one bookmaker timestamp before real kickoff.",
        "",
        "## Eventos incluidos con mercado pre-kickoff validado",
    ]
    for r in scrubbed:
        mv = r["market_validation"]["markets"][0]
        lines.append(f"- `{r['source_shadow_pick_id']}` {r['home_team']} vs {r['away_team']}: {mv['market_canonical']} `{mv['market_age_bucket']}`, bookmakers `{mv['bookmaker_count']}`.")
    lines += [
        "",
        "## Riesgo metodológico de usar odds reconstruidas",
        "- Even with pre-kickoff `fetched_at`, consensus was loaded from replay artifacts, not freshly materialized production snapshots; use this for behavior audit only.",
        "",
        "## 12. What this proves",
        "- It tests whether the current prompt/model, given scrubbed odds plus limited pre-match-safe context, still collapses toward the market favorite.",
        "",
        "## 13. What this does not prove",
        "- It does not prove ROI, model edge, or production-readiness.",
        "",
        "## 14. Recommended next step",
        "- Build a larger Group A-only sample with authentic pre-kickoff snapshot provenance, then repeat with a context-only vs market-reveal two-stage design.",
        "",
        "## Central question",
        f"- Answer: `After scrubbing, DSR has odds plus limited h2h/CDM pre-kickoff context. In this run it matched the favorite on {fav_match}/{len(ok)} parsed picks, so the current input/prompt still behaves primarily as a favorite follower rather than a clearly signal-driven selector.`",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--call-dsr", action="store_true")
    args = ap.parse_args()
    run_key = f"shadow-blind-scrubbed-replay-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    conn = psycopg2.connect(_dsn(), connect_timeout=30)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        scan = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "local only; no external calls during universe scan",
            "tables_read": [
                "bt2_events",
                "bt2_odds_snapshot",
                "raw_sportmonks_fixtures",
                "bt2_shadow_runs",
                "bt2_shadow_daily_picks",
                "bt2_shadow_pick_inputs",
                "bt2_shadow_provider_snapshots",
                "bt2_shadow_pick_eval",
            ],
            "tables_written": [],
            "artifacts_scanned": [
                str(SOURCE_AUDIT.relative_to(ROOT)),
                str(SOURCE_BLIND.relative_to(ROOT)),
                "scripts/outputs/bt2_shadow_dsr_replay/*",
            ],
            "db": _scan_db(cur),
            "artifacts": _scan_artifacts(),
        }
    finally:
        cur.close()
        conn.close()

    audit = json.loads(SOURCE_AUDIT.read_text(encoding="utf-8"))
    cases = [c for c in audit.get("cases", []) if c.get("ds_input_blind") and c.get("ds_input_blind", {}).get("sport") == "football"]
    selected = _select_sample(cases)
    scrubbed = [_scrub_case(c, i + 1) for i, c in enumerate(selected)]
    ds_inputs = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_key": run_key,
        "source_artifact": str(SOURCE_AUDIT.relative_to(ROOT)),
        "selection_policy": "Use v6 sample audit cases; prefer football, five operating leagues, odds tier variety and mixed posterior eval statuses.",
        "groups": dict(Counter(r["group"] for r in scrubbed)),
        "selected_events": scrubbed,
        "ds_input_batch": [r["ds_input_blind_scrubbed"] for r in scrubbed],
    }
    dsr = {
        "run_key": run_key,
        "mode": "shadow_artifact_only",
        "requested": bool(args.call_dsr),
        "called": False,
        "prompt_version": DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
        "outputs": [],
        "note": "not called; rerun with --call-dsr" if not args.call_dsr else None,
    }
    if args.call_dsr and scrubbed:
        dsr = _run_dsr(scrubbed, run_key)

    OUT_SCAN.write_text(json.dumps(_jsonable(scan), indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_INPUTS.write_text(json.dumps(_jsonable(ds_inputs), indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_DSR.write_text(json.dumps(_jsonable(dsr), indent=2, ensure_ascii=False), encoding="utf-8")
    _write_csv(scrubbed, dsr)
    _write_md(scan, scrubbed, dsr)
    print(json.dumps({"ok": True, "selected": len(scrubbed), "dsr_called": dsr.get("called"), "run_key": run_key}, indent=2))


if __name__ == "__main__":
    main()

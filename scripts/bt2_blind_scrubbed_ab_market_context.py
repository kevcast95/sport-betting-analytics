#!/usr/bin/env python3
"""
BT2 blind scrubbed A/B/C market-vs-context audit.

Shadow-artifact only:
- reads scripts/outputs/blind_scrubbed_replay_ds_inputs.json
- performs local contract simulation/classification only
- no DB writes, no production writes, no external calls
"""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
SRC_INPUTS = ROOT / "scripts/outputs/blind_scrubbed_replay_ds_inputs.json"
OUT_A = ROOT / "scripts/outputs/blind_scrubbed_ab_market_only_outputs.json"
OUT_B = ROOT / "scripts/outputs/blind_scrubbed_ab_context_only_outputs.json"
OUT_C = ROOT / "scripts/outputs/blind_scrubbed_ab_two_stage_outputs.json"
OUT_CSV = ROOT / "scripts/outputs/blind_scrubbed_ab_market_context_comparison.csv"
OUT_MD = ROOT / "docs/bettracker2/audits/BLIND_SCRUBBED_REPLAY_AB_MARKET_CONTEXT_AUDIT.md"


def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s or "").lower())).strip()


def _favorite(consensus: dict[str, Any]) -> tuple[Optional[str], dict[str, float]]:
    ft = consensus.get("FT_1X2") if isinstance(consensus, dict) else None
    vals: dict[str, float] = {}
    if not isinstance(ft, dict):
        return None, vals
    for k in ("home", "draw", "away"):
        try:
            vals[k] = float(ft[k])
        except (KeyError, TypeError, ValueError):
            return None, {}
    return min(vals, key=vals.get), vals


def _odds_tier(consensus: dict[str, Any], side: Optional[str]) -> str:
    fav, vals = _favorite(consensus)
    if not vals or side not in vals:
        return "n/a"
    order = sorted(("home", "draw", "away"), key=lambda k: vals[k])
    return ("favorite", "middle", "longshot")[order.index(str(side))]


def _market_strength(vals: dict[str, float]) -> tuple[str, float]:
    if not vals:
        return "unknown", 0.0
    order = sorted(vals, key=lambda k: vals[k])
    best = vals[order[0]]
    second = vals[order[1]]
    ratio = second / best if best else 0.0
    if best <= 1.7 or ratio >= 1.75:
        return "clear_favorite", ratio
    if best <= 2.35 or ratio >= 1.25:
        return "moderate_favorite", ratio
    return "balanced", ratio


def _consensus_to_probs(vals: dict[str, float]) -> dict[str, float]:
    if not vals:
        return {}
    inv = {k: 1.0 / v for k, v in vals.items() if v and v > 1.0}
    total = sum(inv.values())
    return {k: round(v / total, 6) for k, v in inv.items()} if total else {}


def _context_lean(item: dict[str, Any]) -> dict[str, Any]:
    proc = item.get("processed") or {}
    ctx = item.get("event_context") or {}
    score = {"home": 0.0, "draw": 0.0, "away": 0.0}
    signals: list[str] = []
    missing: list[str] = []

    h2h = proc.get("h2h") if isinstance(proc.get("h2h"), dict) else {}
    if h2h.get("available"):
        try:
            hw = float(h2h.get("current_home_wins") or 0)
            aw = float(h2h.get("current_away_wins") or 0)
            dr = float(h2h.get("draws") or 0)
            meetings = float(h2h.get("meetings_in_sample") or 0)
        except (TypeError, ValueError):
            meetings = 0
            hw = aw = dr = 0
        if meetings > 0:
            score["home"] += hw / meetings
            score["away"] += aw / meetings
            score["draw"] += 0.6 * dr / meetings
            signals.append(f"h2h {int(hw)}H/{int(dr)}D/{int(aw)}A over {int(meetings)}")
        else:
            missing.append("h2h_available_but_zero_meetings")
    else:
        missing.append("h2h_missing")

    stats = proc.get("statistics") if isinstance(proc.get("statistics"), dict) else {}
    cdm = stats.get("cdm_from_bt2_events") if isinstance(stats.get("cdm_from_bt2_events"), dict) else {}
    if stats.get("available") and cdm.get("available"):
        home_ctx = cdm.get("home_side_context") if isinstance(cdm.get("home_side_context"), dict) else {}
        away_ctx = cdm.get("away_side_context") if isinstance(cdm.get("away_side_context"), dict) else {}
        hr = home_ctx.get("rest_days_before_this_kickoff")
        ar = away_ctx.get("rest_days_before_this_kickoff")
        if isinstance(hr, (int, float)) and isinstance(ar, (int, float)):
            diff = float(hr) - float(ar)
            if abs(diff) >= 2:
                side = "home" if diff > 0 else "away"
                score[side] += min(abs(diff) / 10.0, 0.5)
                signals.append(f"rest_days_edge_{side}:{diff:+.0f}")
            else:
                signals.append("rest_days_neutral")
        else:
            missing.append("rest_days_missing")
        if cdm.get("definitions"):
            signals.append("cdm_context_pre_kickoff_scope_declared")
    else:
        missing.append("cdm_statistics_missing")

    if not signals or max(score.values()) < 0.25:
        return {
            "lean_side": "unknown",
            "lean_confidence": "low",
            "signal_summary": signals,
            "missing_signal_reason": ";".join(missing) or "insufficient_context_signal",
            "scorecard": score,
        }
    order = sorted(score, key=lambda k: score[k], reverse=True)
    margin = score[order[0]] - score[order[1]]
    conf = "high" if margin >= 0.75 else "medium" if margin >= 0.35 else "low"
    if margin < 0.15:
        return {
            "lean_side": "unknown",
            "lean_confidence": "low",
            "signal_summary": signals,
            "missing_signal_reason": "context_signal_too_weak_or_tied",
            "scorecard": score,
        }
    return {
        "lean_side": order[0],
        "lean_confidence": conf,
        "signal_summary": signals,
        "missing_signal_reason": "",
        "scorecard": score,
    }


def _quality(text: str, has_odds: bool, has_signal: bool) -> str:
    if has_odds and has_signal:
        return "odds_plus_signal"
    if has_odds:
        return "odds_only"
    if has_signal:
        return "signal_driven"
    return "unsupported"


def _market_only(rows: list[dict[str, Any]]) -> dict[str, Any]:
    outputs = []
    for row in rows:
        item = row["ds_input_blind_scrubbed"]
        consensus = item["processed"]["odds_featured"]["consensus"]
        fav, vals = _favorite(consensus)
        strength, ratio = _market_strength(vals)
        conf = "high" if strength == "clear_favorite" else "medium" if strength == "moderate_favorite" else "low"
        outputs.append(
            {
                "event_id": item["event_id"],
                "source_shadow_pick_id": row["source_shadow_pick_id"],
                "variant": "A_market_only",
                "selected_side": fav,
                "selected_market": "FT_1X2" if fav else "UNKNOWN",
                "confidence": conf,
                "consensus_favorite_side": fav,
                "matches_favorite": fav is not None,
                "odds_tier": "favorite" if fav else "n/a",
                "market_strength": strength,
                "favorite_to_second_odds_ratio": round(ratio, 6),
                "consensus_probabilities": _consensus_to_probs(vals),
                "rationale_quality": "odds_only",
                "rationale": (
                    f"Market-only baseline selects {fav}; {strength} from FT_1X2 consensus."
                    if fav
                    else "No complete FT_1X2 consensus."
                ),
            }
        )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow_artifact_only_no_external_calls",
        "execution_type": "local_contract_simulation_not_dsr_api",
        "outputs": outputs,
        "summary": {
            "events": len(outputs),
            "matches_favorite": sum(1 for o in outputs if o["matches_favorite"]),
            "confidence": dict(Counter(o["confidence"] for o in outputs)),
            "market_strength": dict(Counter(o["market_strength"] for o in outputs)),
        },
    }


def _context_only(rows: list[dict[str, Any]]) -> dict[str, Any]:
    outputs = []
    for row in rows:
        item = row["ds_input_blind_scrubbed"]
        lean = _context_lean(item)
        side = lean["lean_side"]
        outputs.append(
            {
                "event_id": item["event_id"],
                "source_shadow_pick_id": row["source_shadow_pick_id"],
                "variant": "B_context_only",
                "selected_side": None if side == "unknown" else side,
                "selected_market": "UNKNOWN" if side == "unknown" else "FT_1X2",
                "unknown": side == "unknown",
                "confidence": lean["lean_confidence"],
                "rationale_quality": _quality("", has_odds=False, has_signal=side != "unknown"),
                "signal_summary": lean["signal_summary"],
                "missing_signal_reason": lean["missing_signal_reason"],
                "scorecard": lean["scorecard"],
                "rationale": (
                    "Context-only lean from pre-match-safe h2h/CDM/rest context."
                    if side != "unknown"
                    else f"UNKNOWN: {lean['missing_signal_reason']}"
                ),
            }
        )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow_artifact_only_no_external_calls",
        "execution_type": "local_context_signal_classifier_not_dsr_api",
        "outputs": outputs,
        "summary": {
            "events": len(outputs),
            "unknown_rate": round(sum(1 for o in outputs if o["unknown"]) / len(outputs), 6) if outputs else None,
            "selected_side": dict(Counter(o["selected_side"] or "UNKNOWN" for o in outputs)),
            "confidence": dict(Counter(o["confidence"] for o in outputs)),
            "rationale_quality": dict(Counter(o["rationale_quality"] for o in outputs)),
        },
    }


def _two_stage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    outputs = []
    for row in rows:
        item = row["ds_input_blind_scrubbed"]
        consensus = item["processed"]["odds_featured"]["consensus"]
        fav, vals = _favorite(consensus)
        strength, ratio = _market_strength(vals)
        lean = _context_lean(item)
        lean_side = lean["lean_side"]
        if lean_side == "unknown":
            relation = "market_only"
            final = fav
        elif lean_side == fav:
            relation = "reinforce_favorite"
            final = fav
        else:
            relation = "strong_tension" if lean["lean_confidence"] in ("medium", "high") else "weak_tension"
            final = "abstain" if relation == "strong_tension" and strength != "clear_favorite" else fav
        if final == "abstain" or fav is None:
            selected_side = None
            selected_market = "UNKNOWN"
        else:
            selected_side = final
            selected_market = "FT_1X2"
        outputs.append(
            {
                "event_id": item["event_id"],
                "source_shadow_pick_id": row["source_shadow_pick_id"],
                "variant": "C_two_stage",
                "stage_1_context": lean,
                "stage_2_market": {
                    "consensus_favorite_side": fav,
                    "market_strength": strength,
                    "favorite_to_second_odds_ratio": round(ratio, 6),
                    "consensus_probabilities": _consensus_to_probs(vals),
                },
                "classification": relation if selected_side is not None else "abstain",
                "selected_side": selected_side,
                "selected_market": selected_market,
                "final_pick_matches_favorite": selected_side == fav if selected_side else None,
                "context_lean_matches_favorite": lean_side == fav if lean_side != "unknown" and fav else None,
                "rationale_quality": _quality("", has_odds=True, has_signal=lean_side != "unknown"),
                "rationale": f"context={lean_side}; favorite={fav}; classification={relation}; final={selected_side or 'abstain'}",
            }
        )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "shadow_artifact_only_no_external_calls",
        "execution_type": "local_two_stage_classifier_not_dsr_api",
        "outputs": outputs,
        "summary": {
            "events": len(outputs),
            "classification": dict(Counter(o["classification"] for o in outputs)),
            "context_lean_vs_favorite": dict(Counter(str(o["context_lean_matches_favorite"]) for o in outputs)),
            "final_pick_vs_favorite": dict(Counter(str(o["final_pick_matches_favorite"]) for o in outputs)),
            "rationale_quality": dict(Counter(o["rationale_quality"] for o in outputs)),
        },
    }


def _write_csv(rows: list[dict[str, Any]], a: dict[str, Any], b: dict[str, Any], c: dict[str, Any]) -> None:
    by_a = {o["source_shadow_pick_id"]: o for o in a["outputs"]}
    by_b = {o["source_shadow_pick_id"]: o for o in b["outputs"]}
    by_c = {o["source_shadow_pick_id"]: o for o in c["outputs"]}
    fields = [
        "source_shadow_pick_id",
        "league_name",
        "home_team",
        "away_team",
        "market_favorite",
        "market_only_side",
        "context_only_side",
        "context_unknown",
        "two_stage_context_lean",
        "two_stage_classification",
        "two_stage_final_side",
        "two_stage_final_matches_favorite",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            sid = r["source_shadow_pick_id"]
            ao = by_a[sid]
            bo = by_b[sid]
            co = by_c[sid]
            w.writerow(
                {
                    "source_shadow_pick_id": sid,
                    "league_name": r["league_name"],
                    "home_team": r["home_team"],
                    "away_team": r["away_team"],
                    "market_favorite": ao["consensus_favorite_side"],
                    "market_only_side": ao["selected_side"],
                    "context_only_side": bo["selected_side"] or "UNKNOWN",
                    "context_unknown": bo["unknown"],
                    "two_stage_context_lean": co["stage_1_context"]["lean_side"],
                    "two_stage_classification": co["classification"],
                    "two_stage_final_side": co["selected_side"] or "ABSTAIN",
                    "two_stage_final_matches_favorite": co["final_pick_matches_favorite"],
                }
            )


def _write_md(rows: list[dict[str, Any]], a: dict[str, Any], b: dict[str, Any], c: dict[str, Any]) -> None:
    a_sum = a["summary"]
    b_sum = b["summary"]
    c_sum = c["summary"]
    market_follow = a_sum["matches_favorite"]
    unknown_n = sum(1 for o in b["outputs"] if o["unknown"])
    tension_n = sum(1 for o in c["outputs"] if "tension" in o["classification"])
    market_only_n = sum(1 for o in c["outputs"] if o["classification"] == "market_only")
    reinforce_n = sum(1 for o in c["outputs"] if o["classification"] == "reinforce_favorite")
    lines = [
        "# Blind Scrubbed Replay A/B Market Context Audit",
        "",
        "## 1. Executive summary",
        f"- Sample: `{len(rows)}` Group A events from `blind_scrubbed_replay_ds_inputs.json`.",
        "- Execution: local shadow-artifact simulation/classification only; no external DSR/API calls.",
        f"- Market-only follows favorite by construction: `{market_follow}/{len(rows)}`.",
        f"- Context-only UNKNOWN rate: `{unknown_n}/{len(rows)}`.",
        f"- Two-stage classifications: `{c_sum['classification']}`.",
        "",
        "## 2. Why this experiment was needed",
        "- The prior blind scrubbed replay showed DSR matching the favorite on 9/10 model-parsed outputs.",
        "- This A/B/C separates market information from the limited safe context left after leakage scrubbing.",
        "",
        "## 3. Sample used",
    ]
    for r in rows:
        lines.append(f"- `{r['source_shadow_pick_id']}` {r['league_name']}: {r['home_team']} vs {r['away_team']} ({r['group']}).")
    lines += [
        "",
        "## 4. Market-only results",
        f"- Confidence distribution: `{a_sum['confidence']}`.",
        f"- Market strength: `{a_sum['market_strength']}`.",
        "- Diagnosis: with only odds, the only defensible deterministic behavior is favorite-following.",
        "",
        "## 5. Context-only results",
        f"- Selected sides: `{b_sum['selected_side']}`.",
        f"- Confidence: `{b_sum['confidence']}`.",
        f"- Rationale quality: `{b_sum['rationale_quality']}`.",
        f"- UNKNOWN rate: `{b_sum['unknown_rate']}`.",
        "",
        "## 6. Two-stage results",
        f"- Classification counts: `{c_sum['classification']}`.",
        f"- Context lean vs favorite: `{c_sum['context_lean_vs_favorite']}`.",
        f"- Final pick vs favorite: `{c_sum['final_pick_vs_favorite']}`.",
        f"- Market-only cases: `{market_only_n}`; reinforce favorite: `{reinforce_n}`; tension cases: `{tension_n}`.",
        "",
        "## 7. Favorite-following comparison",
        f"- Previous DSR run: `9/10` model-parsed selections matched favorite.",
        f"- Market-only: `{market_follow}/{len(rows)}`.",
        f"- Two-stage final favorite matches: `{c_sum['final_pick_vs_favorite']}`.",
        "",
        "## 8. Signal sufficiency diagnosis",
        "- Context-only retained mostly h2h and CDM/rest-days context. It produced low/medium local leans, but these are weak and often aligned with or too close to market priors.",
        "- The current safe context lacks richer pre-match signals such as lineups, injuries, tactical shape, availability, team-season aggregates, or independently validated model features.",
        "",
        "## 9. Prompt/product implications",
        "- The current prompt receives a strong market prior and weak context. It can sound signal-aware while still mostly selecting the favorite.",
        "- Product framing should avoid implying independent edge until context-only leans can be shown to carry stable information before odds reveal.",
        "",
        "## 10. Recommendation for BT2 Phase 4A/4B",
        "- Phase 4A: adopt two-stage evaluation as the default audit harness: context lean first, market reveal second.",
        "- Phase 4B: gate release claims on Group A-only samples with authentic pre-kickoff snapshots and non-market signal coverage above a declared threshold.",
        "- Add prompt output fields for `context_lean`, `market_relation`, and `market_only_reason` before permitting a final pick.",
        "",
        "## Central question",
        "- Answer: `DSR appears to follow the favorite primarily because the market is the dominant high-confidence signal in the current input. The scrubbed context is not empty, but it is too thin and weakly discriminative to justify an independent decision reliably.`",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    data = json.loads(SRC_INPUTS.read_text(encoding="utf-8"))
    rows = data.get("selected_events") or []
    if not rows:
        raise SystemExit("No selected_events found. Run bt2_blind_scrubbed_replay.py first.")
    a = _market_only(rows)
    b = _context_only(rows)
    c = _two_stage(rows)
    OUT_A.write_text(json.dumps(a, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_B.write_text(json.dumps(b, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_C.write_text(json.dumps(c, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_csv(rows, a, b, c)
    _write_md(rows, a, b, c)
    print(
        json.dumps(
            {
                "ok": True,
                "events": len(rows),
                "market_only_matches_favorite": a["summary"]["matches_favorite"],
                "context_unknown_rate": b["summary"]["unknown_rate"],
                "two_stage_classification": c["summary"]["classification"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

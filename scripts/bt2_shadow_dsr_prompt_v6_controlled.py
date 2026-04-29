#!/usr/bin/env python3
"""
Prueba controlada DSR prompt v6 (shadow-native) — muestra fija 32, sin replay masivo.

- No escribe en bt2_shadow_*.
- Genera artefactos bajo scripts/outputs/bt2_shadow_dsr_replay/.

Uso:
  PYTHONPATH=. python3 scripts/bt2_shadow_dsr_prompt_v6_controlled.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_admin_backtest_replay import BLIND_LOT_OPERATING_DAY_KEY, blind_ds_input_item  # noqa: E402
from apps.api.bt2_dsr_shadow_native_enrichment import apply_shadow_native_enriched_context  # noqa: E402
from apps.api.bt2_dsr_postprocess import postprocess_dsr_pick  # noqa: E402
from apps.api.bt2_dsr_shadow_native_adapter import build_ds_input_shadow_native  # noqa: E402
from apps.api.bt2_dsr_shadow_native_deepseek_v6 import (  # noqa: E402
    DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
    deepseek_suggest_batch_shadow_native_v6_with_trace,
    narrative_extract_rationale_v6,
)
from apps.api.bt2_settings import bt2_settings  # noqa: E402

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
FIXED_SAMPLE = OUT_DIR / "dsr_pilot_sample.csv"
MODEL = "deepseek-v4-pro"

_ST_MARK = re.compile(r"\[no_pick_reason\](.*?)\[/no_pick_reason\]", re.DOTALL)

_SPEC = importlib.util.spec_from_file_location(
    "_sn_pilot", ROOT / "scripts" / "bt2_shadow_native_dsr_pilot.py"
)
_SN = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(_SN)


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _extract_no_pick(narrative: str) -> str:
    m = _ST_MARK.search(narrative or "")
    return (m.group(1) if m else "").strip()


def _consensus_favorite_side(consensus: dict[str, Any]) -> Optional[str]:
    sub = consensus.get("FT_1X2") or {}
    triple: dict[str, float] = {}
    for k in ("home", "draw", "away"):
        v = sub.get(k)
        if v is None:
            return None
        try:
            triple[k] = float(v)
        except (TypeError, ValueError):
            return None
    return min(triple.keys(), key=lambda x: triple[x])


def _pick_odds_tier(consensus: dict[str, Any], selection_canonical: str) -> str:
    sub = consensus.get("FT_1X2") or {}
    triple: dict[str, float] = {}
    for k in ("home", "draw", "away"):
        v = sub.get(k)
        if v is None:
            return "n/a"
        try:
            triple[k] = float(v)
        except (TypeError, ValueError):
            return "n/a"
    order = sorted(triple.keys(), key=lambda x: triple[x])
    try:
        i = order.index(selection_canonical)
    except ValueError:
        return "n/a"
    return ("favorite", "middle", "longshot")[i]


def main() -> None:
    dkey = (bt2_settings.deepseek_api_key or "").strip()
    if not dkey:
        raise SystemExit("Falta deepseek_api_key para la prueba v6.")

    if not FIXED_SAMPLE.is_file():
        raise SystemExit(f"Falta muestra fija: {FIXED_SAMPLE}")

    sample_ids: list[int] = []
    with FIXED_SAMPLE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("shadow_pick_id") or row.get("source_shadow_pick_id")
            if pid and str(pid).isdigit():
                sample_ids.append(int(pid))

    conn = psycopg2.connect(_dsn(), connect_timeout=30)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        universe = _SN._fetch_universe(cur)
        by_id = {int(r["shadow_pick_id"]): r for r in universe}
        rows_ready: list[dict[str, Any]] = []
        prepared_blinds: list[dict[str, Any]] = []
        meta_order: list[dict[str, Any]] = []

        for spid in sample_ids:
            r = by_id.get(spid)
            if not r:
                meta_order.append({"shadow_pick_id": spid, "skip": "not_in_universe"})
                continue
            pj = _SN._load_pick_inputs(cur, spid)
            sn_ex, agg, meta = _SN._shadow_native_exclusion(cur, r, pj)
            if sn_ex != "eligible_shadow_native" or agg is None:
                meta_order.append(
                    {
                        "shadow_pick_id": spid,
                        "skip": sn_ex,
                    }
                )
                continue
            league, home, away, ko, status = _SN._resolve_context(cur, r, meta)
            item = build_ds_input_shadow_native(
                synthetic_event_id=spid,
                league_name=league,
                country=r.get("league_country"),
                league_tier=str(r.get("league_tier") or "") or None,
                home_team=home or "unknown",
                away_team=away or "unknown",
                kickoff_utc=ko,
                event_status=status,
                agg=agg,
            )
            eid_opt = r.get("bt2_event_id")
            sm_fid = int(r["sm_fixture_id"]) if r.get("sm_fixture_id") else None
            apply_shadow_native_enriched_context(
                cur,
                item,
                bt2_event_id=int(eid_opt) if eid_opt is not None else None,
                sportmonks_fixture_id=sm_fid,
                kickoff_utc=ko,
            )
            prepared_blinds.append(blind_ds_input_item(item))
            rows_ready.append({"row": r, "item": item, "agg": agg})
            meta_order.append({"shadow_pick_id": spid, "skip": None})

        if not prepared_blinds:
            raise SystemExit("Ninguna fila de la muestra elegible shadow-native; no se llama al API.")

        ds_map, trace = deepseek_suggest_batch_shadow_native_v6_with_trace(
            prepared_blinds,
            operating_day_key=BLIND_LOT_OPERATING_DAY_KEY,
            api_key=dkey,
            base_url=str(bt2_settings.bt2_dsr_deepseek_base_url),
            model=MODEL,
            timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
            max_retries=int(bt2_settings.bt2_dsr_max_retries),
        )

        parse_status_counts: Counter[str] = Counter()
        tier_counts: Counter[str] = Counter()
        details: list[dict[str, Any]] = []
        fav_csv_rows: list[dict[str, Any]] = []

        for pack in rows_ready:
            r0 = pack["row"]
            item = pack["item"]
            agg = pack["agg"]
            spid = int(r0["shadow_pick_id"])
            raw = ds_map.get(spid)
            ec = item.get("event_context") if isinstance(item.get("event_context"), dict) else {}
            diag = item.get("diagnostics") if isinstance(item.get("diagnostics"), dict) else {}
            pc = diag.get("prob_coherence")

            parse_status = ""
            failure_reason = ""
            mmc_f = ""
            msc_f = ""
            rationale_txt = ""
            conf_lab = ""

            if raw is None:
                parse_status = "dsr_failed"
                failure_reason = trace.last_error or "deepseek_batch_degraded"
            else:
                narrative, confidence_label, mmc, msc, _declared = raw
                rationale_txt = narrative_extract_rationale_v6(narrative)
                conf_lab = confidence_label
                no_pick_reason = _extract_no_pick(narrative)
                rationale_only = rationale_txt or narrative

                if mmc in ("", "UNKNOWN") or msc in ("", "unknown_side"):
                    parse_status = "dsr_empty_signal"
                    failure_reason = no_pick_reason or "no_canonical_pick"
                else:
                    ppc = postprocess_dsr_pick(
                        narrative_es=rationale_only,
                        confidence_label=confidence_label,
                        market_canonical=mmc,
                        selection_canonical=msc,
                        model_declared_odds=None,
                        consensus=agg.consensus,
                        market_coverage=agg.market_coverage,
                        event_id=spid,
                        home_team=str(ec.get("home_team") or ""),
                        away_team=str(ec.get("away_team") or ""),
                    )
                    if not ppc:
                        parse_status = "dsr_postprocess_reject"
                        failure_reason = "postprocess_dsr_pick_returned_none"
                    else:
                        _n2, _c2, mmc_f, msc_f = ppc
                        if mmc_f != "FT_1X2":
                            parse_status = "dsr_non_h2h_canonical"
                            failure_reason = f"market={mmc_f}"
                        else:
                            parse_status = "ok"
                            tier = _pick_odds_tier(agg.consensus, msc_f)
                            tier_counts[tier] += 1

            parse_status_counts[parse_status] += 1
            fav_side = _consensus_favorite_side(agg.consensus)
            tier_label = (
                _pick_odds_tier(agg.consensus, msc_f)
                if parse_status == "ok" and msc_f
                else "n/a"
            )
            fav_csv_rows.append(
                {
                    "shadow_pick_id": spid,
                    "parse_status": parse_status,
                    "selection_canonical_ok": msc_f if parse_status == "ok" else "",
                    "consensus_favorite_side": fav_side or "",
                    "pick_vs_favorite": (
                        "same_as_favorite"
                        if parse_status == "ok" and msc_f and fav_side and msc_f == fav_side
                        else (
                            "not_favorite"
                            if parse_status == "ok" and fav_side
                            else ""
                        )
                    ),
                    "odds_tier_vs_consensus": tier_label,
                    "confidence_label": conf_lab,
                    "rationale_short_es_excerpt": (rationale_txt[:160] + "…") if len(rationale_txt) > 160 else rationale_txt,
                    "prob_coherence": json.dumps(pc, ensure_ascii=False) if pc is not None else "",
                }
            )

            details.append(
                {
                    "shadow_pick_id": spid,
                    "league_name": str(r0.get("league_name") or ""),
                    "operating_day_key": str(r0.get("operating_day_key") or ""),
                    "parse_status": parse_status,
                    "failure_reason": failure_reason,
                    "market_canonical": mmc_f,
                    "selection_canonical": msc_f,
                    "confidence_label": conf_lab,
                    "rationale_short_es": rationale_txt,
                    "prob_coherence": pc,
                    "consensus_favorite_side": fav_side,
                    "odds_tier_when_ok": tier_label if parse_status == "ok" else None,
                    "trace_response_id": trace.response_id,
                    "trace_last_error": trace.last_error if raw is None else "",
                }
            )

        processed_eligible = {int(p["row"]["shadow_pick_id"]) for p in rows_ready}
        for sid in sample_ids:
            if sid in processed_eligible:
                continue
            if sid not in by_id:
                details.append(
                    {
                        "shadow_pick_id": sid,
                        "parse_status": "sample_not_in_universe",
                        "failure_reason": "shadow_pick_id no aparece en taxonomía subset5/frozen",
                    }
                )
                continue
            pj = _SN._load_pick_inputs(cur, sid)
            sn_ex, _, _ = _SN._shadow_native_exclusion(cur, by_id[sid], pj)
            details.append(
                {
                    "shadow_pick_id": sid,
                    "parse_status": "sample_not_eligible_shadow_native",
                    "failure_reason": sn_ex,
                }
            )

        details.sort(key=lambda d: sample_ids.index(d["shadow_pick_id"]) if d["shadow_pick_id"] in sample_ids else 999)

        ok_total = int(parse_status_counts.get("ok", 0))
        summary = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "dsr_prompt_version": DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
            "model": MODEL,
            "fixed_sample_csv": str(FIXED_SAMPLE.relative_to(ROOT)),
            "sample_ids_requested": sample_ids,
            "batch_event_count": len(prepared_blinds),
            "skipped_ids": [m for m in meta_order if m.get("skip")],
            "metrics": {
                "ok_total": ok_total,
                "dsr_failed": int(parse_status_counts.get("dsr_failed", 0)),
                "dsr_empty_signal": int(parse_status_counts.get("dsr_empty_signal", 0)),
                "dsr_postprocess_reject": int(parse_status_counts.get("dsr_postprocess_reject", 0)),
                "dsr_non_h2h_canonical": int(parse_status_counts.get("dsr_non_h2h_canonical", 0)),
                "parse_status_counts": dict(parse_status_counts),
                "picks_odds_tier_when_ok": dict(tier_counts),
                "favorite_alignment_when_ok": {
                    "same_as_consensus_favorite": sum(
                        1
                        for row in fav_csv_rows
                        if row["pick_vs_favorite"] == "same_as_favorite"
                    ),
                    "not_favorite": sum(
                        1 for row in fav_csv_rows if row["pick_vs_favorite"] == "not_favorite"
                    ),
                },
            },
            "deepseek_trace": asdict(trace),
        }

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "dsr_prompt_v6_sample_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (OUT_DIR / "dsr_prompt_v6_sample_details.json").write_text(
            json.dumps(details, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        with (OUT_DIR / "dsr_prompt_v6_favorite_bias_check.csv").open("w", encoding="utf-8", newline="") as f:
            if fav_csv_rows:
                w = csv.DictWriter(f, fieldnames=list(fav_csv_rows[0].keys()))
                w.writeheader()
                w.writerows(fav_csv_rows)

        print(json.dumps({"ok": True, "summary": summary["metrics"]}, indent=2, ensure_ascii=False))
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()

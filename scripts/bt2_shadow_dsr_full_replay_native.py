#!/usr/bin/env python3
"""
Replay DSR completo — puerta shadow-native únicamente (sin gating legacy).

- run_family: shadow_dsr_replay_native
- selection_source: dsr_api_only
- Cuotas/agregación: TOA persistido (adapter shadow-native), event_id sintético = source_shadow_pick_id
- No productivo; nuevo INSERT en bt2_shadow_runs / picks / eval.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
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
from apps.api.bt2_dsr_contract import CONTRACT_VERSION_PUBLIC  # noqa: E402
from apps.api.bt2_dsr_shadow_native_deepseek_v6 import (  # noqa: E402
    DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
    deepseek_suggest_batch_shadow_native_v6_with_trace,
    narrative_extract_rationale_v6,
)
from apps.api.bt2_dsr_shadow_native_enrichment import apply_shadow_native_enriched_context  # noqa: E402
from apps.api.bt2_dsr_odds_aggregation import consensus_decimal_for_canonical_pick  # noqa: E402
from apps.api.bt2_dsr_postprocess import postprocess_dsr_pick  # noqa: E402
from apps.api.bt2_dsr_shadow_native_adapter import build_ds_input_shadow_native  # noqa: E402
from apps.api.bt2_settings import bt2_settings  # noqa: E402

# Reutiliza gate shadow-native del piloto (misma definición de elegibilidad).
_SPEC = importlib.util.spec_from_file_location(
    "_sn_pilot", ROOT / "scripts" / "bt2_shadow_native_dsr_pilot.py"
)
_SN = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(_SN)

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
SELECTION_SOURCE = "dsr_api_only"
RUN_FAMILY = "shadow_dsr_replay_native"
MODEL = "deepseek-v4-pro"
SUBSET5_SPORTMONKS = {8, 82, 301, 384, 564}
FROZEN_RUN_KEYS: tuple[str, ...] = (
    "shadow-subset5-backfill-2025-01-05",
    "shadow-subset5-recovery-2025-07-12",
    "shadow-subset5-backfill-2026-01",
    "shadow-subset5-backfill-2026-02",
    "shadow-subset5-backfill-2026-03",
    "shadow-subset5-backfill-2026-04",
)

_ST_MARK = re.compile(r"\[no_pick_reason\](.*?)\[/no_pick_reason\]", re.DOTALL)


def _norm_sm(s: str) -> str:
    x = unicodedata.normalize("NFKD", (s or "").strip())
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = re.sub(r"[^a-zA-Z0-9]+", " ", x).strip().lower()
    return re.sub(r"\s+", " ", x)


def _parse_sm_truth_payload(payload: dict[str, Any]) -> tuple[str, Optional[int], Optional[int], str, str, bool]:
    """Copia lógica de scripts/bt2_shadow_evaluate_performance._parse_sm_truth."""
    state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    event_status = str(state.get("state") or state.get("name") or state.get("short_name") or "")
    participants = payload.get("participants") if isinstance(payload.get("participants"), list) else []
    p_home: int | None = None
    p_away: int | None = None
    home_name = ""
    away_name = ""
    for p in participants:
        if not isinstance(p, dict):
            continue
        loc = str((p.get("meta") or {}).get("location") or "").lower()
        if loc == "home":
            p_home = int(p.get("id") or 0) or None
            home_name = str(p.get("name") or "")
        elif loc == "away":
            p_away = int(p.get("id") or 0) or None
            away_name = str(p.get("name") or "")
    scores = payload.get("scores") if isinstance(payload.get("scores"), list) else []
    best_rank = -1
    out_home: int | None = None
    out_away: int | None = None
    for s in scores:
        if not isinstance(s, dict):
            continue
        desc = _norm_sm(str(s.get("description") or s.get("type") or ""))
        rank = 3 if desc in {"current", "fulltime", "ft"} else 2 if "2nd" in desc else 1 if "1st" in desc else 0
        pid = int(s.get("participant_id") or 0) or None
        score_node = s.get("score")
        val = None
        if isinstance(score_node, dict):
            raw = score_node.get("goals") if score_node.get("goals") is not None else score_node.get("participant")
            if raw is None:
                raw = score_node.get("score")
            try:
                val = int(raw) if raw is not None else None
            except (TypeError, ValueError):
                val = None
        if val is None:
            try:
                val = int(s.get("score")) if s.get("score") is not None else None
            except (TypeError, ValueError):
                val = None
        if val is None:
            continue
        if pid == p_home and rank >= best_rank:
            out_home = val
            best_rank = rank
        elif pid == p_away and rank >= best_rank:
            out_away = val
            best_rank = rank
    has_score = out_home is not None and out_away is not None
    return event_status or "", out_home, out_away, home_name, away_name, has_score


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _load_event_row_cdm(cur: Any, event_id: int) -> Optional[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            e.id,
            e.kickoff_utc,
            e.status,
            e.result_home,
            e.result_away,
            COALESCE(l.name, '') AS league_name,
            l.country AS league_country,
            l.tier AS league_tier,
            COALESCE(th.name, '') AS home_team_name,
            COALESCE(ta.name, '') AS away_team_name,
            e.home_team_id,
            e.away_team_id,
            e.sportmonks_fixture_id
        FROM bt2_events e
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE e.id = %s
        """,
        (event_id,),
    )
    r = cur.fetchone()
    return dict(r) if r else None


def _eval_event_for_row(
    cur: Any,
    r: dict[str, Any],
    meta: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    """
    Fila estilo _event del replay legacy para métricas + baseline.
    Retorna (event_dict, truth_source_label).
    """
    eid = r.get("bt2_event_id")
    if eid:
        er = _load_event_row_cdm(cur, int(eid))
        if er:
            return er, "bt2_events_cdm_v1"
    fid = r.get("sm_fixture_id")
    if fid:
        cur.execute(
            "SELECT payload FROM raw_sportmonks_fixtures WHERE fixture_id = %s LIMIT 1",
            (int(fid),),
        )
        row = cur.fetchone()
        pl = row.get("payload") if isinstance(row, dict) else (row[0] if row else None)
        if isinstance(pl, str):
            try:
                pl = json.loads(pl)
            except json.JSONDecodeError:
                pl = None
        if isinstance(pl, dict):
            st, rh, ra, hn, an, ok = _parse_sm_truth_payload(pl)
            if not hn:
                hn = str(meta.get("toa_home_team") or "")
            if not an:
                an = str(meta.get("toa_away_team") or "")
            return (
                {
                    "id": None,
                    "kickoff_utc": None,
                    "status": st or "unknown",
                    "result_home": rh if ok else None,
                    "result_away": ra if ok else None,
                    "league_name": str(r.get("league_name") or ""),
                    "league_country": r.get("league_country"),
                    "league_tier": r.get("league_tier"),
                    "home_team_name": hn,
                    "away_team_name": an,
                    "home_team_id": None,
                    "away_team_id": None,
                    "sportmonks_fixture_id": int(fid),
                },
                "raw_sportmonks_fixture_payload_v1",
            )
    # Fallback mínimo: solo TOA
    return (
        {
            "id": None,
            "kickoff_utc": None,
            "status": "scheduled",
            "result_home": None,
            "result_away": None,
            "league_name": str(r.get("league_name") or ""),
            "home_team_name": str(meta.get("toa_home_team") or ""),
            "away_team_name": str(meta.get("toa_away_team") or ""),
            "home_team_id": None,
            "away_team_id": None,
            "sportmonks_fixture_id": int(r["sm_fixture_id"]) if r.get("sm_fixture_id") else None,
        },
        "toa_payload_only_v1",
    )


def _is_void_status(status: str) -> bool:
    s = (status or "").strip().lower()
    return s in {
        "abandoned",
        "cancelled",
        "canceled",
        "postponed",
        "suspended",
        "interrupted",
        "deleted",
        "walkover",
    }


def _selection_side(selection: str, home: str, away: str) -> str | None:
    s = (selection or "").strip().lower()
    if not s:
        return None
    if s in {"draw", "empate", "x"}:
        return "draw"
    if s in {"home", "local", "1", (home or "").strip().lower()}:
        return "home"
    if s in {"away", "visitante", "2", (away or "").strip().lower()}:
        return "away"
    return None


def _evaluate_prediction(
    *,
    selection: str,
    home_name: str,
    away_name: str,
    event_status: str,
    result_home: Optional[int],
    result_away: Optional[int],
    decimal_odds: Optional[float],
) -> tuple[str, Optional[float]]:
    if _is_void_status(event_status):
        return ("void", None)
    if result_home is None or result_away is None:
        return ("pending_result", None)
    side = _selection_side(selection, home_name, away_name)
    if side is None:
        return ("no_evaluable", None)
    home_win = result_home > result_away
    away_win = result_away > result_home
    draw = result_home == result_away
    hit = (side == "home" and home_win) or (side == "away" and away_win) or (side == "draw" and draw)
    if hit:
        return ("hit", ((float(decimal_odds) - 1.0) if decimal_odds is not None else None))
    return ("miss", -1.0)


def _extract_no_pick(narrative: str) -> str:
    m = _ST_MARK.search(narrative or "")
    return (m.group(1) if m else "").strip()


def _processed_flags(item: dict[str, Any]) -> dict[str, Optional[bool]]:
    proc = item.get("processed") or {}
    out: dict[str, Optional[bool]] = {}
    for k, v in proc.items():
        if not isinstance(v, dict):
            out[k] = None
            continue
        if k == "odds_featured":
            out[k] = bool(v.get("consensus"))
            continue
        out[k] = bool(v.get("available"))
    return out


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


def _odds_tier(consensus: dict[str, Any], selection_canonical: str) -> str:
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


def _v6_raw_pick_row(raw_text: str, event_id: int) -> Optional[dict[str, Any]]:
    if not (raw_text or "").strip():
        return None
    try:
        obj = json.loads(raw_text.strip())
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    for row in obj.get("picks_by_event") or []:
        if not isinstance(row, dict):
            continue
        try:
            if int(row.get("event_id")) == int(event_id):
                return dict(row)
        except (TypeError, ValueError):
            continue
    return None


def _select_stratified_audit_sample(rows: list[dict[str, Any]], n: int = 10) -> tuple[list[dict[str, Any]], str]:
    """Muestra variada: tiers de cuota, contexto lineups, hit/miss, fallos parse."""
    ok = [r for r in rows if r.get("pipeline_parse_status") == "ok"]
    by_tier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in ok:
        by_tier[str(r.get("odds_tier_vs_consensus") or "n/a")].append(r)
    picked: set[int] = set()
    out: list[dict[str, Any]] = []

    for tier in ("favorite", "middle", "longshot"):
        for r in by_tier.get(tier, [])[:4]:
            if len(out) >= n:
                break
            pid = int(r["source_shadow_pick_id"])
            if pid not in picked:
                out.append(r)
                picked.add(pid)
        if len(out) >= n:
            break

    for r in rows:
        if len(out) >= n:
            break
        if r.get("processed_flags", {}).get("lineups") and int(r["source_shadow_pick_id"]) not in picked:
            out.append(r)
            picked.add(int(r["source_shadow_pick_id"]))

    for es in ("hit", "miss"):
        if len(out) >= n:
            break
        for r in rows:
            if r.get("eval_status") == es and int(r["source_shadow_pick_id"]) not in picked:
                out.append(r)
                picked.add(int(r["source_shadow_pick_id"]))
                break

    for r in rows:
        if len(out) >= n:
            break
        if r.get("pipeline_parse_status") != "ok" and int(r["source_shadow_pick_id"]) not in picked:
            out.append(r)
            picked.add(int(r["source_shadow_pick_id"]))

    for r in rows:
        if len(out) >= n:
            break
        pid = int(r["source_shadow_pick_id"])
        if pid not in picked:
            out.append(r)
            picked.add(pid)

    crit = (
        "Orden: hasta 4 por tier (favorite/middle/longshot) entre picks OK; "
        "luego filas con lineups disponible; luego un hit y un miss si existen; "
        "luego un fallo de parse si cabe; relleno por orden de ejecución."
    )
    return out[:n], crit


def _create_shadow_run_v2(
    cur: Any, *, run_key: str, eligible: list[dict[str, Any]]
) -> int:
    days = sorted({str(r.get("operating_day_key") or "") for r in eligible if r.get("operating_day_key")})
    d_from = days[0] if days else datetime.now(timezone.utc).date().isoformat()
    d_to = days[-1] if days else d_from
    cur.execute(
        """
        INSERT INTO bt2_shadow_runs (
            run_key, operating_day_key_from, operating_day_key_to, mode,
            provider_stack, is_shadow, run_family, selection_source, notes
        )
        VALUES (%s,%s,%s,'shadow',%s,true,%s,%s,%s)
        RETURNING id
        """,
        (
            run_key,
            d_from,
            d_to,
            "shadow_native_full_replay_deepseek_v4_pro_prompt_v6",
            RUN_FAMILY,
            SELECTION_SOURCE,
            "shadow_native_gate_only_no_fallback",
        ),
    )
    return int(cur.fetchone()["id"])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dkey = (bt2_settings.deepseek_api_key or "").strip()
    if not dkey:
        raise SystemExit("Falta deepseek_api_key para replay DSR completo.")

    run_key = f"shadow-dsr-native-full-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    summary: dict[str, Any] = {
        "run_key": run_key,
        "selection_source": SELECTION_SOURCE,
        "run_family": RUN_FAMILY,
        "model": MODEL,
        "contract_version": CONTRACT_VERSION_PUBLIC,
        "dsr_prompt_version": DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
        "gate": "shadow_native_only",
        "frozen_run_keys": list(FROZEN_RUN_KEYS),
        "subset5_sportmonks_ids": sorted(SUBSET5_SPORTMONKS),
        "batch_size_config": max(1, int(getattr(bt2_settings, "bt2_dsr_batch_size", 15) or 15)),
        "batching_note": "Mismo bt2_dsr_batch_size que DSR admin; lotes para límites de tokens/timeout DeepSeek.",
    }

    conn = psycopg2.connect(_dsn(), connect_timeout=30)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        universe = _SN._fetch_universe(cur)
        for u in universe:
            u["source_shadow_pick_id"] = int(u.pop("shadow_pick_id"))

        excluded_vp = 0
        excluded_other = 0
        eligible: list[dict[str, Any]] = []
        for r in universe:
            spid = int(r["source_shadow_pick_id"])
            pj = _SN._load_pick_inputs(cur, spid)
            sn_ex, agg, meta = _SN._shadow_native_exclusion(cur, r, pj)
            if sn_ex != "eligible_shadow_native" or agg is None:
                if sn_ex == "shadow_native_value_pool_failed":
                    excluded_vp += 1
                else:
                    excluded_other += 1
                continue
            er, truth_src = _eval_event_for_row(cur, r, meta)
            eligible.append(
                {
                    **r,
                    "_event": er,
                    "_agg": agg,
                    "_meta": meta,
                    "_truth_source": truth_src,
                }
            )

        summary["universe_rows_matched_taxonomy"] = len(universe)
        summary["eligible_shadow_native"] = len(eligible)
        summary["excluded_shadow_native_value_pool_failed"] = excluded_vp
        summary["excluded_shadow_native_other"] = excluded_other
        summary["universe_executed_with_dsr"] = len(eligible)
        summary["execution_shortfall"] = {
            "eligible_minus_executed": max(0, len(eligible) - summary["universe_executed_with_dsr"]),
            "cause": None,
        }

        run_id = _create_shadow_run_v2(cur, run_key=run_key, eligible=eligible)
        summary["shadow_run_id"] = run_id

        bs = max(1, int(getattr(bt2_settings, "bt2_dsr_batch_size", 15) or 15))
        total_prompt_tokens = 0
        total_completion_tokens = 0
        parse_status_counts: dict[str, int] = defaultdict(int)
        trace_samples: list[dict[str, Any]] = []
        dsr_rows: list[dict[str, Any]] = []
        audit_trail: list[dict[str, Any]] = []

        prepared_chunks: list[list[dict[str, Any]]] = []
        chunk_meta: list[list[dict[str, Any]]] = []

        block: list[dict[str, Any]] = []
        for r in eligible:
            agg = r["_agg"]
            meta = r["_meta"]
            league, home, away, ko, status = _SN._resolve_context(cur, r, meta)
            spid = int(r["source_shadow_pick_id"])
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
            row_pack = {
                "row": r,
                "blind": blind_ds_input_item(item),
                "item": item,
                "agg": agg,
                "kickoff_utc": ko,
            }
            block.append(row_pack)
            if len(block) >= bs:
                prepared_chunks.append([x["blind"] for x in block])
                chunk_meta.append(block)
                block = []
        if block:
            prepared_chunks.append([x["blind"] for x in block])
            chunk_meta.append(block)

        chunk_idx = 0
        for chunk_blinds, meta_blk in zip(prepared_chunks, chunk_meta):
            ds_map, trace = deepseek_suggest_batch_shadow_native_v6_with_trace(
                chunk_blinds,
                operating_day_key=BLIND_LOT_OPERATING_DAY_KEY,
                api_key=dkey,
                base_url=str(bt2_settings.bt2_dsr_deepseek_base_url),
                model=MODEL,
                timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
                max_retries=int(bt2_settings.bt2_dsr_max_retries),
            )
            usage = trace.usage or {}
            total_prompt_tokens += int(usage.get("prompt_tokens") or 0)
            total_completion_tokens += int(usage.get("completion_tokens") or 0)
            tr_d = asdict(trace)
            if tr_d.get("raw_content_full"):
                tr_d["raw_content_length_chars"] = len(tr_d["raw_content_full"])
                tr_d.pop("raw_content_full", None)
            trace_samples.append(tr_d)

            for pack in meta_blk:
                r0 = pack["row"]
                item = pack["item"]
                agg = pack["agg"]
                ko_pack = pack.get("kickoff_utc")
                er = r0["_event"]
                spid = int(r0["source_shadow_pick_id"])
                raw = ds_map.get(spid)
                tier = ""
                parse_status = ""
                failure_reason = ""
                market_canonical = ""
                selection_canonical = ""
                narrative = ""
                confidence_label = ""
                declared_odds: Optional[float] = None
                no_pick_reason = ""

                if raw is None:
                    parse_status = "dsr_failed"
                    failure_reason = trace.last_error or "deepseek_batch_degraded"
                else:
                    narrative, confidence_label, mmc, msc, declared_odds = raw
                    no_pick_reason = _extract_no_pick(narrative)
                    rationale_only = narrative_extract_rationale_v6(narrative) or narrative
                    if mmc in ("", "UNKNOWN") or msc in ("", "unknown_side"):
                        parse_status = "dsr_empty_signal"
                        failure_reason = no_pick_reason or "no_canonical_pick"
                    else:
                        ec = item.get("event_context") if isinstance(item.get("event_context"), dict) else {}
                        ppc = postprocess_dsr_pick(
                            narrative_es=rationale_only,
                            confidence_label=confidence_label,
                            market_canonical=mmc,
                            selection_canonical=msc,
                            model_declared_odds=declared_odds,
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
                                market_canonical = mmc_f
                                selection_canonical = msc_f

                parse_status_counts[parse_status or "unknown"] += 1
                selection = None
                selected_side = None
                dec = None
                if parse_status == "ok":
                    if selection_canonical == "home":
                        selection = str(er.get("home_team_name") or "")
                        selected_side = "home"
                    elif selection_canonical == "away":
                        selection = str(er.get("away_team_name") or "")
                        selected_side = "away"
                    elif selection_canonical == "draw":
                        selection = "Draw"
                        selected_side = "draw"
                    dec = consensus_decimal_for_canonical_pick(
                        agg.consensus,
                        market_canonical,
                        selection_canonical,
                    )

                cur.execute(
                    """
                    INSERT INTO bt2_shadow_daily_picks (
                        run_id, operating_day_key, bt2_event_id, sm_fixture_id, league_id,
                        market, selection, status_shadow, classification_taxonomy, decimal_odds, dsr_source,
                        dsr_parse_status, dsr_failure_reason, dsr_model, dsr_prompt_version, dsr_response_id,
                        dsr_usage_json, dsr_raw_summary_json, selected_side_canonical, provider_snapshot_id
                    )
                    VALUES (%s,%s,%s,%s,%s,'h2h',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING id
                    """,
                    (
                        run_id,
                        r0["operating_day_key"],
                        int(r0["bt2_event_id"]) if r0.get("bt2_event_id") is not None else None,
                        int(r0["sm_fixture_id"]) if r0.get("sm_fixture_id") is not None else None,
                        int(r0["league_id"]) if r0.get("league_id") is not None else None,
                        selection,
                        ("ready_for_shadow_pick" if parse_status == "ok" else "needs_review"),
                        ("matched_with_odds_t60" if parse_status == "ok" else parse_status),
                        dec,
                        SELECTION_SOURCE,
                        parse_status,
                        failure_reason or None,
                        MODEL,
                        DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
                        trace.response_id,
                        psycopg2.extras.Json(trace.usage or {}),
                        psycopg2.extras.Json(
                            {
                                "market_canonical": market_canonical,
                                "selection_canonical": selection_canonical,
                                "confidence_label": confidence_label,
                                "no_pick_reason": no_pick_reason,
                                "rationale_short_es": narrative_extract_rationale_v6(narrative),
                                "narrative_excerpt": (narrative or "")[:500],
                                "truth_source_eval": r0.get("_truth_source"),
                                "synthetic_event_id": spid,
                            }
                        ),
                        selected_side,
                        int(r0["provider_snapshot_id"]) if r0.get("provider_snapshot_id") is not None else None,
                    ),
                )
                new_pick_id = int(cur.fetchone()["id"])

                eval_status = "no_evaluable"
                roi_units = None
                if parse_status == "ok":
                    eval_status, roi_units = _evaluate_prediction(
                        selection=selection or "",
                        home_name=str(er.get("home_team_name") or ""),
                        away_name=str(er.get("away_team_name") or ""),
                        event_status=str(er.get("status") or ""),
                        result_home=(int(er["result_home"]) if er.get("result_home") is not None else None),
                        result_away=(int(er["result_away"]) if er.get("result_away") is not None else None),
                        decimal_odds=dec,
                    )
                cur.execute(
                    """
                    INSERT INTO bt2_shadow_pick_eval (
                        shadow_daily_pick_id, eval_status, classification_taxonomy, eval_notes,
                        evaluation_reason, evaluated_at, truth_source, result_home, result_away,
                        event_status, decimal_odds, roi_flat_stake_units
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (shadow_daily_pick_id) DO NOTHING
                    """,
                    (
                        new_pick_id,
                        eval_status,
                        ("matched_with_odds_t60" if parse_status == "ok" else parse_status),
                        f"run_key={run_key} run_family={RUN_FAMILY}",
                        f"dsr_parse_status={parse_status}",
                        datetime.now(timezone.utc),
                        str(r0.get("_truth_source") or "unknown"),
                        (int(er["result_home"]) if er.get("result_home") is not None else None),
                        (int(er["result_away"]) if er.get("result_away") is not None else None),
                        str(er.get("status") or ""),
                        dec,
                        roi_units,
                    ),
                )
                dsr_rows.append(
                    {
                        "run_key": run_key,
                        "league_name": str(r0.get("league_name") or ""),
                        "source_run_key": str(r0.get("source_run_key") or ""),
                        "source_shadow_pick_id": spid,
                        "shadow_daily_pick_id": new_pick_id,
                        "operating_day_key": str(r0.get("operating_day_key") or ""),
                        "bt2_event_id": int(r0["bt2_event_id"]) if r0.get("bt2_event_id") else "",
                        "parse_status": parse_status,
                        "eval_status": eval_status,
                        "roi_flat_stake_units": roi_units,
                        "decimal_odds": dec,
                    }
                )

                ko_disp = ""
                if ko_pack is not None:
                    ko_disp = ko_pack.isoformat() if hasattr(ko_pack, "isoformat") else str(ko_pack)
                elif er.get("kickoff_utc") is not None:
                    kx = er.get("kickoff_utc")
                    ko_disp = kx.isoformat() if hasattr(kx, "isoformat") else str(kx)

                fav_s = _consensus_favorite_side(agg.consensus)
                tier = _odds_tier(agg.consensus, selection_canonical) if parse_status == "ok" and selection_canonical else ""
                match_fav = (
                    bool(fav_s and selection_canonical and fav_s == selection_canonical)
                    if parse_status == "ok"
                    else None
                )
                of = item.get("processed", {}).get("odds_featured", {}) if isinstance(item.get("processed"), dict) else {}
                audit_trail.append(
                    {
                        "run_key": run_key,
                        "batch_chunk_index": chunk_idx,
                        "source_shadow_pick_id": spid,
                        "shadow_daily_pick_id": new_pick_id,
                        "sm_fixture_id": r0.get("sm_fixture_id"),
                        "bt2_event_id": r0.get("bt2_event_id"),
                        "league_name": str(r0.get("league_name") or ""),
                        "kickoff_utc": ko_disp,
                        "home_team": str(er.get("home_team_name") or ""),
                        "away_team": str(er.get("away_team_name") or ""),
                        "ds_input_blind": pack["blind"],
                        "odds_snapshot_summary": {
                            "consensus_FT_1X2": (agg.consensus or {}).get("FT_1X2"),
                            "ingest_meta": of.get("ingest_meta") if isinstance(of, dict) else None,
                        },
                        "prob_coherence": (item.get("diagnostics") or {}).get("prob_coherence"),
                        "processed_flags": _processed_flags(item),
                        "dsr_response_id": trace.response_id,
                        "model_raw_response_full": getattr(trace, "raw_content_full", "") or "",
                        "model_parsed_row_v6_api": _v6_raw_pick_row(
                            getattr(trace, "raw_content_full", "") or "", spid
                        ),
                        "pipeline_parse_status": parse_status,
                        "selection_canonical_final": selection_canonical,
                        "selected_team_final": selection,
                        "confidence_label": confidence_label,
                        "rationale_short_es": narrative_extract_rationale_v6(narrative),
                        "no_pick_reason": no_pick_reason,
                        "eval_status": eval_status,
                        "result_score_text": (
                            f"{er.get('result_home')}-{er.get('result_away')}"
                            if er.get("result_home") is not None and er.get("result_away") is not None
                            else ""
                        ),
                        "odds_tier_vs_consensus": tier,
                        "consensus_favorite_side": fav_s,
                        "pick_matches_consensus_favorite": match_fav,
                    }
                )

            chunk_idx += 1

        conn.commit()

        ok_total = int(parse_status_counts.get("ok", 0))
        scored = sum(1 for r in dsr_rows if r["eval_status"] in {"hit", "miss"})
        hit = sum(1 for r in dsr_rows if r["eval_status"] == "hit")
        miss = sum(1 for r in dsr_rows if r["eval_status"] == "miss")
        void = sum(1 for r in dsr_rows if r["eval_status"] == "void")
        pending_result = sum(1 for r in dsr_rows if r["eval_status"] == "pending_result")
        no_evaluable = sum(1 for r in dsr_rows if r["eval_status"] == "no_evaluable")
        roi_u = float(sum(float(r["roi_flat_stake_units"] or 0.0) for r in dsr_rows if r["eval_status"] in {"hit", "miss"}))
        hit_rate = (hit / scored) if scored else 0.0
        roi_pct = ((roi_u / scored) * 100.0) if scored else 0.0

        baseline_rows = []
        for r in eligible:
            er = r["_event"]
            cur.execute(
                """
                SELECT selection, decimal_odds
                FROM bt2_shadow_daily_picks
                WHERE id = %s
                """,
                (int(r["source_shadow_pick_id"]),),
            )
            br = cur.fetchone() or {}
            eval_status_b, roi_b = _evaluate_prediction(
                selection=str(br.get("selection") or ""),
                home_name=str(er.get("home_team_name") or ""),
                away_name=str(er.get("away_team_name") or ""),
                event_status=str(er.get("status") or ""),
                result_home=(int(er["result_home"]) if er.get("result_home") is not None else None),
                result_away=(int(er["result_away"]) if er.get("result_away") is not None else None),
                decimal_odds=(float(br["decimal_odds"]) if br.get("decimal_odds") is not None else None),
            )
            baseline_rows.append(
                {
                    "source_shadow_pick_id": int(r["source_shadow_pick_id"]),
                    "eval_status": eval_status_b,
                    "roi_flat_stake_units": roi_b,
                }
            )

        b_scored = sum(1 for r in baseline_rows if r["eval_status"] in {"hit", "miss"})
        b_hit = sum(1 for r in baseline_rows if r["eval_status"] == "hit")
        b_miss = sum(1 for r in baseline_rows if r["eval_status"] == "miss")
        b_void = sum(1 for r in baseline_rows if r["eval_status"] == "void")
        b_pending = sum(1 for r in baseline_rows if r["eval_status"] == "pending_result")
        b_no_eval = sum(1 for r in baseline_rows if r["eval_status"] == "no_evaluable")
        b_roi_units = float(sum(float(r["roi_flat_stake_units"] or 0.0) for r in baseline_rows if r["eval_status"] in {"hit", "miss"}))
        b_hit_rate = (b_hit / b_scored) if b_scored else 0.0
        b_roi_pct = ((b_roi_units / b_scored) * 100.0) if b_scored else 0.0

        comparable_note = (
            "Misma verdad de resultado para DSR y baseline: prioridad CDM `bt2_events`, "
            "si no hay evento, `raw_sportmonks_fixtures.payload` (FT); si no hay marcador, pending/no_evaluable."
        )

        summary["metrics"] = {
            "prompts_built": len(eligible),
            "dsr_failed": int(parse_status_counts.get("dsr_failed", 0)),
            "ok_total": ok_total,
            "evaluable": ok_total,
            "parse_status_counts": dict(parse_status_counts),
            "usage_prompt_tokens_sum": total_prompt_tokens,
            "usage_completion_tokens_sum": total_completion_tokens,
            "estimated_cost_usd": None,
            "picks_total": len(dsr_rows),
            "scored": scored,
            "hit": hit,
            "miss": miss,
            "void": void,
            "pending_result": pending_result,
            "no_evaluable": no_evaluable,
            "hit_rate_on_scored": round(hit_rate, 6),
            "roi_flat_stake_units": round(roi_u, 6),
            "roi_flat_stake_pct": round(roi_pct, 6),
            "baseline_non_dsr_same_native_slice": {
                "description": "Picks shadow fuente (no DSR) por source_shadow_pick_id; misma función de verdad que DSR.",
                "picks_total": len(baseline_rows),
                "scored": b_scored,
                "hit": b_hit,
                "miss": b_miss,
                "void": b_void,
                "pending_result": b_pending,
                "no_evaluable": b_no_eval,
                "hit_rate_on_scored": round(b_hit_rate, 6),
                "roi_flat_stake_units": round(b_roi_units, 6),
                "roi_flat_stake_pct": round(b_roi_pct, 6),
            },
            "comparison_slice_note": comparable_note,
        }

        ok_audit = [a for a in audit_trail if a.get("pipeline_parse_status") == "ok"]
        tier_c = Counter(str(a.get("odds_tier_vs_consensus") or "") for a in ok_audit)
        fav_same = sum(1 for a in ok_audit if a.get("pick_matches_consensus_favorite") is True)
        fav_not = sum(1 for a in ok_audit if a.get("pick_matches_consensus_favorite") is False)
        summary["metrics"]["odds_tier_distribution_ok"] = dict(tier_c)
        summary["metrics"]["favorite_bias_ok_same_as_consensus"] = fav_same
        summary["metrics"]["favorite_bias_ok_not_favorite"] = fav_not

        summary["batch_traces_sample"] = trace_samples[:15]

        sample_cases, sample_crit = _select_stratified_audit_sample(audit_trail, 10)
        sample_payload = {
            "run_key": run_key,
            "dsr_prompt_version": DSR_PROMPT_VERSION_SHADOW_NATIVE_V6,
            "enrichment": "apply_shadow_native_enriched_context",
            "selection_criterion": sample_crit,
            "cases": sample_cases,
        }

        summary["observability"] = {
            "audit_trail_row_count": len(audit_trail),
            "human_audit_sample_size": len(sample_cases),
        }
        summary["operational_snapshot"] = {
            "parse_status_counts": dict(parse_status_counts),
            "ok_total": ok_total,
            "dsr_failed": int(parse_status_counts.get("dsr_failed", 0)),
            "dsr_empty_signal": int(parse_status_counts.get("dsr_empty_signal", 0)),
            "scored": scored,
            "pending_result": pending_result,
            "no_evaluable": no_evaluable,
            "hit": hit,
            "miss": miss,
            "odds_tier_distribution_ok": dict(tier_c),
            "favorite_bias_among_ok_picks": {
                "same_as_consensus_favorite": fav_same,
                "not_favorite": fav_not,
            },
        }

        (OUT_DIR / "dsr_native_full_replay_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (OUT_DIR / "dsr_native_full_replay_v6_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (OUT_DIR / "dsr_native_full_replay_v6_sample_audit.json").write_text(
            json.dumps(sample_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        with (OUT_DIR / "dsr_native_full_replay_v6_sample_audit.csv").open("w", encoding="utf-8", newline="") as f:
            fn = [
                "run_key",
                "shadow_daily_pick_id",
                "source_shadow_pick_id",
                "sm_fixture_id",
                "bt2_event_id",
                "league_name",
                "kickoff_utc",
                "home_team",
                "away_team",
                "pipeline_parse_status",
                "selection_canonical_final",
                "selected_team_final",
                "confidence_label",
                "rationale_short_es",
                "no_pick_reason",
                "eval_status",
                "result_score_text",
                "odds_tier_vs_consensus",
                "pick_matches_consensus_favorite",
                "model_raw_response_chars",
                "ds_input_blind_json_chars",
            ]
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            for c in sample_cases:
                raw_t = c.get("model_raw_response_full") or ""
                blind = c.get("ds_input_blind") or {}
                w.writerow(
                    {
                        "run_key": str(c.get("run_key") or run_key),
                        "shadow_daily_pick_id": c.get("shadow_daily_pick_id"),
                        "source_shadow_pick_id": c.get("source_shadow_pick_id"),
                        "sm_fixture_id": c.get("sm_fixture_id"),
                        "bt2_event_id": c.get("bt2_event_id"),
                        "league_name": c.get("league_name"),
                        "kickoff_utc": c.get("kickoff_utc"),
                        "home_team": c.get("home_team"),
                        "away_team": c.get("away_team"),
                        "pipeline_parse_status": c.get("pipeline_parse_status"),
                        "selection_canonical_final": c.get("selection_canonical_final"),
                        "selected_team_final": c.get("selected_team_final"),
                        "confidence_label": c.get("confidence_label"),
                        "rationale_short_es": (str(c.get("rationale_short_es") or ""))[:800],
                        "no_pick_reason": c.get("no_pick_reason"),
                        "eval_status": c.get("eval_status"),
                        "result_score_text": c.get("result_score_text"),
                        "odds_tier_vs_consensus": c.get("odds_tier_vs_consensus"),
                        "pick_matches_consensus_favorite": c.get("pick_matches_consensus_favorite"),
                        "model_raw_response_chars": len(raw_t),
                        "ds_input_blind_json_chars": len(json.dumps(blind, ensure_ascii=False)),
                    }
                )

        with (OUT_DIR / "dsr_native_full_replay_by_run.csv").open("w", encoding="utf-8", newline="") as f:
            fn = [
                "run_key",
                "run_family",
                "selection_source",
                "model",
                "contract_version",
                "universe_rows_matched_taxonomy",
                "eligible_shadow_native",
                "excluded_shadow_native_value_pool_failed",
                "universe_executed_with_dsr",
                "prompts_built",
                "dsr_failed",
                "ok_total",
                "evaluable",
                "usage_prompt_tokens_sum",
                "usage_completion_tokens_sum",
                "picks_total",
                "scored",
                "hit",
                "miss",
                "void",
                "pending_result",
                "no_evaluable",
                "hit_rate_on_scored",
                "roi_flat_stake_units",
                "roi_flat_stake_pct",
            ]
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            m = summary["metrics"]
            w.writerow(
                {
                    "run_key": run_key,
                    "run_family": RUN_FAMILY,
                    "selection_source": SELECTION_SOURCE,
                    "model": MODEL,
                    "contract_version": CONTRACT_VERSION_PUBLIC,
                    "universe_rows_matched_taxonomy": summary["universe_rows_matched_taxonomy"],
                    "eligible_shadow_native": summary["eligible_shadow_native"],
                    "excluded_shadow_native_value_pool_failed": summary["excluded_shadow_native_value_pool_failed"],
                    "universe_executed_with_dsr": summary["universe_executed_with_dsr"],
                    "prompts_built": m["prompts_built"],
                    "dsr_failed": m["dsr_failed"],
                    "ok_total": m["ok_total"],
                    "evaluable": m["evaluable"],
                    "usage_prompt_tokens_sum": m["usage_prompt_tokens_sum"],
                    "usage_completion_tokens_sum": m["usage_completion_tokens_sum"],
                    "picks_total": m["picks_total"],
                    "scored": m["scored"],
                    "hit": m["hit"],
                    "miss": m["miss"],
                    "void": m["void"],
                    "pending_result": m["pending_result"],
                    "no_evaluable": m["no_evaluable"],
                    "hit_rate_on_scored": m["hit_rate_on_scored"],
                    "roi_flat_stake_units": m["roi_flat_stake_units"],
                    "roi_flat_stake_pct": m["roi_flat_stake_pct"],
                }
            )

        by_league: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "picks_total": 0,
                "scored": 0,
                "hit": 0,
                "miss": 0,
                "void": 0,
                "pending_result": 0,
                "no_evaluable": 0,
                "roi_flat_stake_units": 0.0,
            }
        )
        for r in dsr_rows:
            lg = r["league_name"] or "unknown"
            acc = by_league[lg]
            acc["picks_total"] += 1
            es = r["eval_status"]
            if es in {"hit", "miss"}:
                acc["scored"] += 1
            acc[es] = acc.get(es, 0) + 1
            if es in {"hit", "miss"} and r["roi_flat_stake_units"] is not None:
                acc["roi_flat_stake_units"] += float(r["roi_flat_stake_units"])

        with (OUT_DIR / "dsr_native_full_replay_by_league.csv").open("w", encoding="utf-8", newline="") as f:
            fn = [
                "league_name",
                "picks_total",
                "scored",
                "hit",
                "miss",
                "void",
                "pending_result",
                "no_evaluable",
                "hit_rate_on_scored",
                "roi_flat_stake_units",
                "roi_flat_stake_pct",
            ]
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            for lg, acc in sorted(by_league.items(), key=lambda x: x[0]):
                scored_l = int(acc["scored"])
                hit_l = int(acc["hit"])
                roi_lv = float(acc["roi_flat_stake_units"])
                w.writerow(
                    {
                        "league_name": lg,
                        "picks_total": acc["picks_total"],
                        "scored": scored_l,
                        "hit": hit_l,
                        "miss": acc["miss"],
                        "void": acc["void"],
                        "pending_result": acc["pending_result"],
                        "no_evaluable": acc["no_evaluable"],
                        "hit_rate_on_scored": round(hit_l / scored_l, 6) if scored_l else 0.0,
                        "roi_flat_stake_units": round(roi_lv, 6),
                        "roi_flat_stake_pct": round((roi_lv / scored_l) * 100.0, 6) if scored_l else 0.0,
                }
            )

        shutil.copy(
            OUT_DIR / "dsr_native_full_replay_by_run.csv",
            OUT_DIR / "dsr_native_full_replay_v6_by_run.csv",
        )
        shutil.copy(
            OUT_DIR / "dsr_native_full_replay_by_league.csv",
            OUT_DIR / "dsr_native_full_replay_v6_by_league.csv",
        )

        with (OUT_DIR / "dsr_native_vs_non_dsr_same_slice.csv").open("w", encoding="utf-8", newline="") as f:
            fn = [
                "slice",
                "variant",
                "picks_total",
                "scored",
                "hit",
                "miss",
                "void",
                "pending_result",
                "no_evaluable",
                "hit_rate_on_scored",
                "roi_flat_stake_units",
                "roi_flat_stake_pct",
            ]
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            w.writerow(
                {
                    "slice": "same_shadow_native_eligible",
                    "variant": "dsr_replay_native",
                    "picks_total": len(dsr_rows),
                    "scored": scored,
                    "hit": hit,
                    "miss": miss,
                    "void": void,
                    "pending_result": pending_result,
                    "no_evaluable": no_evaluable,
                    "hit_rate_on_scored": round(hit_rate, 6),
                    "roi_flat_stake_units": round(roi_u, 6),
                    "roi_flat_stake_pct": round(roi_pct, 6),
                }
            )
            w.writerow(
                {
                    "slice": "same_shadow_native_eligible",
                    "variant": "baseline_non_dsr_source_picks",
                    "picks_total": len(baseline_rows),
                    "scored": b_scored,
                    "hit": b_hit,
                    "miss": b_miss,
                    "void": b_void,
                    "pending_result": b_pending,
                    "no_evaluable": b_no_eval,
                    "hit_rate_on_scored": round(b_hit_rate, 6),
                    "roi_flat_stake_units": round(b_roi_units, 6),
                    "roi_flat_stake_pct": round(b_roi_pct, 6),
                }
            )

    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    print(
        json.dumps(
            {
                "ok": True,
                "run_key": run_key,
                "summary_path": "scripts/outputs/bt2_shadow_dsr_replay/dsr_native_full_replay_summary.json",
                "v6_summary_path": "scripts/outputs/bt2_shadow_dsr_replay/dsr_native_full_replay_v6_summary.json",
                "v6_sample_audit_json": "scripts/outputs/bt2_shadow_dsr_replay/dsr_native_full_replay_v6_sample_audit.json",
                "v6_sample_audit_csv": "scripts/outputs/bt2_shadow_dsr_replay/dsr_native_full_replay_v6_sample_audit.csv",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

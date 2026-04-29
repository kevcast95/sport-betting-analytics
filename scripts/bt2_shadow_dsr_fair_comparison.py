#!/usr/bin/env python3
"""
Comparación justa DSR native (liquidado) vs baseline no-DSR sobre el mismo slice.

- DSR: métricas desde bt2_shadow_pick_eval del run_key native (post bt2_shadow_evaluate_performance).
- No-DSR: mismos source_shadow_pick_id, misma lógica que scripts/bt2_shadow_evaluate_performance.py
  (EvalRow + merge SM + _evaluate_one). No escribe DB.

Salidas: scripts/outputs/bt2_shadow_dsr_replay/dsr_vs_non_dsr_fair_* + segmentos DSR.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import importlib.util
import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_settings import bt2_settings

_SPEC = importlib.util.spec_from_file_location(
    "bt2_shadow_evaluate_performance",
    ROOT / "scripts" / "bt2_shadow_evaluate_performance.py",
)
assert _SPEC and _SPEC.loader
_EVM = importlib.util.module_from_spec(_SPEC)
sys.modules["bt2_shadow_evaluate_performance"] = _EVM
_SPEC.loader.exec_module(_EVM)
EvalRow = _EVM.EvalRow
_evaluate_one = _EVM._evaluate_one
_fetch_sm_truth_map = _EVM._fetch_sm_truth_map
_selection_side = _EVM._selection_side

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
DSR_RUN_KEY = "shadow-dsr-native-full-20260428-214014"


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _agg_empty() -> dict[str, Any]:
    return {
        "picks_total": 0,
        "scored": 0,
        "hit": 0,
        "miss": 0,
        "void": 0,
        "pending_result": 0,
        "no_evaluable": 0,
        "roi_flat_stake_units": 0.0,
    }


def _finalize(acc: dict[str, Any]) -> dict[str, Any]:
    sc = int(acc["scored"])
    hit = int(acc["hit"])
    roi = float(acc["roi_flat_stake_units"])
    out = dict(acc)
    out["hit_rate_on_scored"] = round(hit / sc, 6) if sc else 0.0
    out["roi_flat_stake_pct"] = round((roi / sc) * 100.0, 6) if sc else 0.0
    out["roi_flat_stake_units"] = round(roi, 6)
    return out


def _odds_band(dec: Any) -> str:
    if dec is None:
        return "unknown"
    try:
        x = float(dec)
    except (TypeError, ValueError):
        return "unknown"
    if x < 1.5:
        return "<1.5"
    if x < 2.0:
        return "[1.5,2.0)"
    if x < 2.5:
        return "[2.0,2.5)"
    if x < 3.0:
        return "[2.5,3.0)"
    return ">=3.0"


def _rollup(rows: list[dict[str, Any]], keyfn: Any) -> dict[str, dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = defaultdict(_agg_empty)
    for r in rows:
        k = keyfn(r)
        b = buckets[k]
        b["picks_total"] += 1
        es = str(r.get("eval_status") or "")
        if es in b:
            b[es] += 1
        if es in ("hit", "miss"):
            b["scored"] += 1
            ru = r.get("roi_flat_stake_units")
            if ru is not None:
                b["roi_flat_stake_units"] += float(ru)
    return {k: _finalize(v) for k, v in sorted(buckets.items(), key=lambda x: x[0])}


def main() -> None:
    conn = psycopg2.connect(_dsn(), connect_timeout=20)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        """
        SELECT
          dp.id AS dsr_pick_id,
          (dp.dsr_raw_summary_json->>'synthetic_event_id')::bigint AS source_shadow_pick_id,
          dp.selection,
          dp.decimal_odds,
          dp.selected_side_canonical,
          dp.operating_day_key,
          COALESCE(lg.name, '(unknown_league)') AS league_name,
          sr.run_key AS source_run_key,
          COALESCE(ht.name, '') AS ev_home_name,
          COALESCE(at.name, '') AS ev_away_name,
          e.eval_status,
          e.roi_flat_stake_units,
          e.evaluation_reason,
          e.truth_source
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs dr ON dr.id = dp.run_id
        INNER JOIN bt2_shadow_pick_eval e ON e.shadow_daily_pick_id = dp.id
        LEFT JOIN bt2_events ev ON ev.id = dp.bt2_event_id
        LEFT JOIN bt2_leagues lg ON lg.id = COALESCE(dp.league_id, ev.league_id)
        LEFT JOIN bt2_teams ht ON ht.id = ev.home_team_id
        LEFT JOIN bt2_teams at ON at.id = ev.away_team_id
        LEFT JOIN bt2_shadow_daily_picks sp ON sp.id = (dp.dsr_raw_summary_json->>'synthetic_event_id')::bigint
        LEFT JOIN bt2_shadow_runs sr ON sr.id = sp.run_id
        WHERE dr.run_key = %s
        ORDER BY dp.id
        """,
        (DSR_RUN_KEY,),
    )
    dsr_rows = list(cur.fetchall() or [])

    source_ids = [int(r["source_shadow_pick_id"]) for r in dsr_rows if r.get("source_shadow_pick_id")]
    if len(source_ids) != len(dsr_rows):
        raise RuntimeError("source_shadow_pick_id faltante en alguna fila DSR")

    cur.execute(
        """
        SELECT
          dp.id AS shadow_daily_pick_id,
          sr.run_key,
          COALESCE(dp.selection,'') AS selection,
          dp.decimal_odds,
          COALESCE(ht.name,'') AS home_name,
          COALESCE(at.name,'') AS away_name,
          ev.status AS event_status,
          ev.result_home,
          ev.result_away,
          dp.sm_fixture_id,
          COALESCE(dp.classification_taxonomy,'') AS classification_taxonomy
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs sr ON sr.id = dp.run_id
        LEFT JOIN bt2_events ev ON ev.id = dp.bt2_event_id
        LEFT JOIN bt2_teams ht ON ht.id = ev.home_team_id
        LEFT JOIN bt2_teams at ON at.id = ev.away_team_id
        WHERE dp.id = ANY(%s)
        ORDER BY dp.id
        """,
        (source_ids,),
    )
    raw_src = list(cur.fetchall() or [])
    cur.close()
    conn.close()

    by_id = {int(r["shadow_daily_pick_id"]): r for r in raw_src}
    for sid in source_ids:
        if sid not in by_id:
            raise RuntimeError(f"source pick {sid} no encontrado")

    sm_truth_map = _fetch_sm_truth_map(
        {
            int(rr["sm_fixture_id"])
            for rr in raw_src
            if rr.get("sm_fixture_id") is not None
            and (rr.get("result_home") is None or rr.get("result_away") is None)
        }
    )

    non_dsr_evaluated: list[dict[str, Any]] = []
    for rr in raw_src:
        sm_fixture_id = int(rr["sm_fixture_id"]) if rr.get("sm_fixture_id") is not None else None
        fallback = sm_truth_map.get(sm_fixture_id or -1)
        event_status = str(rr.get("event_status") or "")
        result_home = int(rr["result_home"]) if rr.get("result_home") is not None else None
        result_away = int(rr["result_away"]) if rr.get("result_away") is not None else None
        home_name = str(rr.get("home_name") or "")
        away_name = str(rr.get("away_name") or "")
        truth_source = "bt2_events_cdm_v1"
        if fallback and (result_home is None or result_away is None):
            result_home = int(fallback["result_home"]) if fallback.get("result_home") is not None else result_home
            result_away = int(fallback["result_away"]) if fallback.get("result_away") is not None else result_away
            if fallback.get("event_status"):
                event_status = str(fallback.get("event_status") or event_status)
            if fallback.get("home_name"):
                home_name = str(fallback["home_name"])
            if fallback.get("away_name"):
                away_name = str(fallback["away_name"])
            truth_source = "sportmonks_fixture_api_v1"

        er = EvalRow(
            shadow_daily_pick_id=int(rr["shadow_daily_pick_id"]),
            run_key=str(rr["run_key"]),
            selection=str(rr.get("selection") or ""),
            decimal_odds=float(rr["decimal_odds"]) if rr.get("decimal_odds") is not None else None,
            home_name=home_name,
            away_name=away_name,
            event_status=event_status,
            result_home=result_home,
            result_away=result_away,
            sm_fixture_id=sm_fixture_id,
        )
        ev = _evaluate_one(er)
        ev["truth_source"] = truth_source
        roi = ev.get("roi_flat_stake_units")
        non_dsr_evaluated.append(
            {
                "shadow_daily_pick_id": er.shadow_daily_pick_id,
                "source_run_key": er.run_key,
                "eval_status": ev["eval_status"],
                "evaluation_reason": ev.get("evaluation_reason"),
                "truth_source": ev["truth_source"],
                "roi_flat_stake_units": float(roi) if roi is not None else None,
                "decimal_odds": float(er.decimal_odds) if er.decimal_odds is not None else None,
                "selection": er.selection,
                "merged_home_name": home_name,
                "merged_away_name": away_name,
            }
        )

    # --- Métricas DSR desde DB ---
    dsr_detail: list[dict[str, Any]] = []
    for r in dsr_rows:
        es = str(r["eval_status"])
        roi = r.get("roi_flat_stake_units")
        roi_f = float(roi) if roi is not None else None
        side = r.get("selected_side_canonical") or ""
        if not side:
            side = _selection_side(
                str(r.get("selection") or ""),
                str(r.get("ev_home_name") or ""),
                str(r.get("ev_away_name") or ""),
            ) or "unknown"
        dsr_detail.append(
            {
                "dsr_pick_id": int(r["dsr_pick_id"]),
                "source_shadow_pick_id": int(r["source_shadow_pick_id"]),
                "eval_status": es,
                "roi_flat_stake_units": roi_f,
                "decimal_odds": float(r["decimal_odds"]) if r.get("decimal_odds") is not None else None,
                "league_name": r.get("league_name"),
                "operating_day_key": r.get("operating_day_key"),
                "month_key": str(r.get("operating_day_key") or "")[:7],
                "source_run_key": r.get("source_run_key") or "",
                "selection_side": side,
                "odds_band": _odds_band(r.get("decimal_odds")),
            }
        )

    def _metrics_from_detail(rows: list[dict[str, Any]], status_key: str = "eval_status") -> dict[str, Any]:
        acc = _agg_empty()
        for x in rows:
            acc["picks_total"] += 1
            es = str(x.get(status_key) or "")
            if es in acc:
                acc[es] += 1
            if es in ("hit", "miss"):
                acc["scored"] += 1
                ru = x.get("roi_flat_stake_units")
                if ru is not None:
                    acc["roi_flat_stake_units"] += float(ru)
        return _finalize(acc)

    by_src = {int(x["shadow_daily_pick_id"]): x for x in non_dsr_evaluated}
    non_dsr_for_compare: list[dict[str, Any]] = []
    for r in dsr_rows:
        spid = int(r["source_shadow_pick_id"])
        nd = by_src[spid]
        league_name = r.get("league_name") or "(unknown_league)"
        non_dsr_for_compare.append(
            {
                "eval_status": nd["eval_status"],
                "roi_flat_stake_units": nd["roi_flat_stake_units"],
                "decimal_odds": nd["decimal_odds"],
                "league_name": league_name,
                "operating_day_key": r.get("operating_day_key"),
                "month_key": str(r.get("operating_day_key") or "")[:7],
                "source_run_key": nd["source_run_key"],
                "selection_side": _selection_side(
                    nd["selection"] or "",
                    nd["merged_home_name"] or "",
                    nd["merged_away_name"] or "",
                )
                or "unknown",
                "odds_band": _odds_band(nd["decimal_odds"]),
            }
        )

    m_dsr = _metrics_from_detail(dsr_detail)
    m_nd = _metrics_from_detail(non_dsr_for_compare)

    leagues_sorted = sorted({str(r.get("league_name") or "unknown") for r in dsr_detail})
    league_compare: list[dict[str, Any]] = []
    for lg in leagues_sorted:
        d_part = [r for r in dsr_detail if str(r.get("league_name")) == lg]
        n_part = [r for r in non_dsr_for_compare if str(r.get("league_name")) == lg]
        md = _metrics_from_detail(d_part)
        mn = _metrics_from_detail(n_part)
        league_compare.append(
            {
                "league_name": lg,
                "picks_total": md["picks_total"],
                "dsr_hit_rate_on_scored": md["hit_rate_on_scored"],
                "non_dsr_hit_rate_on_scored": mn["hit_rate_on_scored"],
                "hit_rate_diff": round(md["hit_rate_on_scored"] - mn["hit_rate_on_scored"], 6),
                "dsr_roi_flat_stake_pct": md["roi_flat_stake_pct"],
                "non_dsr_roi_flat_stake_pct": mn["roi_flat_stake_pct"],
                "roi_flat_stake_pct_diff": round(md["roi_flat_stake_pct"] - mn["roi_flat_stake_pct"], 6),
            }
        )

    generated = datetime.now(timezone.utc).isoformat()

    summary: dict[str, Any] = {
        "generated_at_utc": generated,
        "dsr_run_key": DSR_RUN_KEY,
        "comparison_rules": {
            "dsr_metrics_source": "bt2_shadow_pick_eval (tras evaluación shadow H2H estándar)",
            "non_dsr_metrics_source": "recompute con EvalRow + _evaluate_one + _fetch_sm_truth_map (idéntico a bt2_shadow_evaluate_performance.py)",
            "same_truth": "bt2_events con fallback SportMonks si falta marcador local",
            "same_selection_mapping": "_selection_side importado del evaluador shadow",
            "selection_semantics": "DSR re-read usa selected_side_canonical del pick; no-DSR usa _selection_side(selection, merged home/away)",
            "what_is_being_compared": "Mismos 259 eventos (via source_shadow_pick_id); selección y cuota difieren entre DSR y pick shadow fuente. Métricas comparan dos estrategias de pick sobre la misma verdad final.",
        },
        "dsr_native_liquidated": m_dsr,
        "baseline_non_dsr_same_slice": m_nd,
        "delta": {
            "hit_rate_on_scored_diff": round(m_dsr["hit_rate_on_scored"] - m_nd["hit_rate_on_scored"], 6),
            "roi_flat_stake_pct_diff": round(m_dsr["roi_flat_stake_pct"] - m_nd["roi_flat_stake_pct"], 6),
        },
        "by_league_compare": league_compare,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "dsr_vs_non_dsr_fair_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (OUT_DIR / "dsr_vs_non_dsr_fair_comparison.csv").open("w", encoding="utf-8", newline="") as f:
        fn = [
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
        w.writerow({"variant": "dsr_native_liquidated", **{k: m_dsr[k] for k in fn if k != "variant"}})
        w.writerow({"variant": "baseline_non_dsr_same_slice", **{k: m_nd[k] for k in fn if k != "variant"}})

    # Segmentación DSR
    seg_league = _rollup(
        dsr_detail,
        lambda r: str(r.get("league_name") or "unknown"),
    )
    with (OUT_DIR / "dsr_native_re_read_by_league.csv").open("w", encoding="utf-8", newline="") as f:
        fn = ["league_name"] + [k for k in next(iter(seg_league.values())).keys() if k != "league_name"]
        fn = ["league_name", "picks_total", "scored", "hit", "miss", "void", "pending_result", "no_evaluable", "hit_rate_on_scored", "roi_flat_stake_units", "roi_flat_stake_pct"]
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for lg, row in seg_league.items():
            w.writerow({"league_name": lg, **{k: row[k] for k in fn if k != "league_name"}})

    seg_run = _rollup(dsr_detail, lambda r: str(r.get("source_run_key") or "unknown"))
    with (OUT_DIR / "dsr_native_re_read_by_run.csv").open("w", encoding="utf-8", newline="") as f:
        fn = ["source_run_key", "picks_total", "scored", "hit", "miss", "void", "pending_result", "no_evaluable", "hit_rate_on_scored", "roi_flat_stake_units", "roi_flat_stake_pct"]
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for k, row in seg_run.items():
            w.writerow({"source_run_key": k, **{x: row[x] for x in fn if x != "source_run_key"}})

    seg_side = _rollup(dsr_detail, lambda r: str(r.get("selection_side") or "unknown"))
    with (OUT_DIR / "dsr_native_re_read_by_selection_side.csv").open("w", encoding="utf-8", newline="") as f:
        fn = ["selection_side", "picks_total", "scored", "hit", "miss", "void", "pending_result", "no_evaluable", "hit_rate_on_scored", "roi_flat_stake_units", "roi_flat_stake_pct"]
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for k, row in seg_side.items():
            w.writerow({"selection_side": k, **{x: row[x] for x in fn if x != "selection_side"}})

    seg_band = _rollup(dsr_detail, lambda r: str(r.get("odds_band") or "unknown"))
    with (OUT_DIR / "dsr_native_re_read_by_odds_band.csv").open("w", encoding="utf-8", newline="") as f:
        fn = ["odds_band", "picks_total", "scored", "hit", "miss", "void", "pending_result", "no_evaluable", "hit_rate_on_scored", "roi_flat_stake_units", "roi_flat_stake_pct"]
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for k, row in seg_band.items():
            w.writerow({"odds_band": k, **{x: row[x] for x in fn if x != "odds_band"}})

    # Opcional: mismo slice por mes (ventana)
    seg_month = _rollup(dsr_detail, lambda r: str(r.get("month_key") or "unknown"))
    with (OUT_DIR / "dsr_native_re_read_by_month.csv").open("w", encoding="utf-8", newline="") as f:
        fn = ["month_key", "picks_total", "scored", "hit", "miss", "void", "pending_result", "no_evaluable", "hit_rate_on_scored", "roi_flat_stake_units", "roi_flat_stake_pct"]
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for k, row in seg_month.items():
            w.writerow({"month_key": k, **{x: row[x] for x in fn if x != "month_key"}})

    with (OUT_DIR / "dsr_vs_non_dsr_fair_by_league.csv").open("w", encoding="utf-8", newline="") as f:
        fn = list(league_compare[0].keys()) if league_compare else []
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for row in league_compare:
            w.writerow(row)

    print(json.dumps({"ok": True, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

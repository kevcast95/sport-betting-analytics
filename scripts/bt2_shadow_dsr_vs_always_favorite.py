#!/usr/bin/env python3
"""
Benchmark trivial «always favorite» (FT_1X2: pierna de menor decimal en consensus agregado TOA)
vs DSR native liquidado y vs baseline no-DSR (misma verdad y mismo EvalRow/_evaluate_one).

- Consensus: misma agregación que shadow-native (`aggregated_odds_from_toa_shadow_payload` + fallback pick_inputs).
- Empates en el mínimo decimal: desempate fijo orden home → draw → away (primera pierna igualada al mínimo gana).

Salidas:
  scripts/outputs/bt2_shadow_dsr_replay/dsr_vs_always_favorite_summary.json
  scripts/outputs/bt2_shadow_dsr_replay/dsr_vs_always_favorite_sample32.csv
  scripts/outputs/bt2_shadow_dsr_replay/dsr_vs_always_favorite_full_run.csv

Uso:
  PYTHONPATH=. python3 scripts/bt2_shadow_dsr_vs_always_favorite.py
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds  # noqa: E402
from apps.api.bt2_dsr_shadow_native_adapter import (  # noqa: E402
    aggregated_odds_from_toa_shadow_payload,
    merge_pick_inputs_odds_blob,
)
from apps.api.bt2_settings import bt2_settings  # noqa: E402

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
SAMPLE_CSV = OUT_DIR / "dsr_pilot_sample.csv"
DSR_RUN_KEY = "shadow-dsr-native-full-20260429-033425"

OUT_SUMMARY = OUT_DIR / "dsr_vs_always_favorite_summary.json"
OUT_SAMPLE32 = OUT_DIR / "dsr_vs_always_favorite_sample32.csv"
OUT_FULL = OUT_DIR / "dsr_vs_always_favorite_full_run.csv"


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


def _metrics_from_rows(rows: list[dict[str, Any]], status_key: str = "eval_status") -> dict[str, Any]:
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


def _load_pick_inputs(cur: Any, shadow_pick_id: int) -> Optional[dict[str, Any]]:
    cur.execute(
        """
        SELECT payload_json FROM bt2_shadow_pick_inputs
        WHERE shadow_daily_pick_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (shadow_pick_id,),
    )
    row = cur.fetchone()
    if not row:
        return None
    pj = row.get("payload_json") if isinstance(row, dict) else row[0]
    return pj if isinstance(pj, dict) else None


def _load_snapshot(cur: Any, snapshot_id: int) -> Optional[dict[str, Any]]:
    cur.execute(
        """
        SELECT id, raw_payload, provider_snapshot_time
        FROM bt2_shadow_provider_snapshots
        WHERE id = %s
        """,
        (snapshot_id,),
    )
    r = cur.fetchone()
    return dict(r) if r else None


def _aggregate_shadow_native_like(
    cur: Any,
    *,
    source_shadow_pick_id: int,
    provider_snapshot_id: Optional[int],
    payload_json: Optional[dict[str, Any]],
) -> tuple[Optional[AggregatedOdds], str]:
    """Misma fuente TOA que carril shadow-native (snapshot + fallback pick_inputs)."""
    if not provider_snapshot_id:
        return None, "missing_provider_snapshot_id"
    sn = _load_snapshot(cur, int(provider_snapshot_id))
    if not sn:
        return None, "provider_snapshot_not_found"
    raw_pl = sn.get("raw_payload")
    pst = sn.get("provider_snapshot_time")
    if isinstance(pst, datetime):
        ps_time = pst if pst.tzinfo else pst.replace(tzinfo=timezone.utc)
    else:
        ps_time = None
    agg, meta = aggregated_odds_from_toa_shadow_payload(raw_pl, provider_snapshot_time=ps_time)
    if int(meta.get("bookmaker_rows_normalized") or 0) == 0:
        alt = merge_pick_inputs_odds_blob(payload_json or {})
        if alt:
            agg2, meta2 = aggregated_odds_from_toa_shadow_payload(alt, provider_snapshot_time=ps_time)
            if int(meta2.get("bookmaker_rows_normalized") or 0) > 0:
                agg, meta = agg2, meta2
    if int(meta.get("bookmaker_rows_normalized") or 0) == 0:
        return None, "missing_toa_h2h_bookmakers"
    return agg, "ok"


def _favorite_side_ft_1x2(sub: dict[str, Any]) -> tuple[Optional[str], Optional[float], str]:
    """
    Pierna con menor decimal en consensus FT_1X2.
    Empate exacto: desempate fijo en orden home → draw → away (primera que alcance el mínimo).
    """
    try:
        h = float(sub["home"])
        d = float(sub["draw"])
        a = float(sub["away"])
    except (KeyError, TypeError, ValueError):
        return None, None, "incomplete_triple"
    for x in (h, d, a):
        if x <= 1.0:
            return None, None, "non_positive_decimal"
    m = min(h, d, a)
    order = ("home", "draw", "away")
    vals = {"home": h, "draw": d, "away": a}
    tied = [s for s in order if abs(vals[s] - m) < 1e-9]
    chosen = tied[0]
    note = "unique_min" if len(tied) == 1 else f"tiebreak_fixed_order_home_draw_away_among_{tied}"
    return chosen, vals[chosen], note


def _truth_merge_for_source(
    rr: dict[str, Any],
    sm_truth_map: dict[int, dict[str, Any]],
) -> tuple[str, Optional[int], Optional[int], str, str]:
    sm_fixture_id = int(rr["sm_fixture_id"]) if rr.get("sm_fixture_id") is not None else None
    fallback = sm_truth_map.get(sm_fixture_id or -1)
    event_status = str(rr.get("event_status") or "")
    result_home = int(rr["result_home"]) if rr.get("result_home") is not None else None
    result_away = int(rr["result_away"]) if rr.get("result_away") is not None else None
    home_name = str(rr.get("home_name") or "")
    away_name = str(rr.get("away_name") or "")
    if fallback and (result_home is None or result_away is None):
        result_home = int(fallback["result_home"]) if fallback.get("result_home") is not None else result_home
        result_away = int(fallback["result_away"]) if fallback.get("result_away") is not None else result_away
        if fallback.get("event_status"):
            event_status = str(fallback.get("event_status") or event_status)
        if fallback.get("home_name"):
            home_name = str(fallback["home_name"])
        if fallback.get("away_name"):
            away_name = str(fallback["away_name"])
    return event_status, result_home, result_away, home_name, away_name


def main() -> None:
    sample_ids: list[int] = []
    if SAMPLE_CSV.is_file():
        with SAMPLE_CSV.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pid = row.get("shadow_pick_id") or row.get("source_shadow_pick_id")
                if pid and str(pid).isdigit():
                    sample_ids.append(int(pid))
    sample_set = set(sample_ids)

    conn = psycopg2.connect(_dsn(), connect_timeout=30)
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
          e.eval_status AS dsr_eval_status_db,
          e.roi_flat_stake_units AS dsr_roi_flat_stake_units_db
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs dr ON dr.id = dp.run_id
        LEFT JOIN bt2_shadow_pick_eval e ON e.shadow_daily_pick_id = dp.id
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
    if not dsr_rows:
        cur.close()
        conn.close()
        raise SystemExit(f"Sin filas DSR para run_key={DSR_RUN_KEY!r}. ¿Evaluación aplicada?")

    cur.execute(
        """
        SELECT
          dp.id AS shadow_daily_pick_id,
          dp.bt2_event_id,
          sr.run_key,
          COALESCE(dp.selection,'') AS selection,
          dp.decimal_odds,
          COALESCE(ht.name,'') AS home_name,
          COALESCE(at.name,'') AS away_name,
          ev.status AS event_status,
          ev.result_home,
          ev.result_away,
          dp.sm_fixture_id,
          dp.provider_snapshot_id,
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

    by_id = {int(r["shadow_daily_pick_id"]): r for r in raw_src}
    for sid in source_ids:
        if sid not in by_id:
            cur.close()
            conn.close()
            raise RuntimeError(f"source pick {sid} no encontrado")

    sm_truth_map = _fetch_sm_truth_map(
        {
            int(rr["sm_fixture_id"])
            for rr in raw_src
            if rr.get("sm_fixture_id") is not None
            and (rr.get("result_home") is None or rr.get("result_away") is None)
        }
    )

    detail_rows: list[dict[str, Any]] = []

    for dsr_r in dsr_rows:
        spid = int(dsr_r["source_shadow_pick_id"])
        rr = by_id[spid]
        event_status, result_home, result_away, home_name, away_name = _truth_merge_for_source(rr, sm_truth_map)
        sm_fixture_id = int(rr["sm_fixture_id"]) if rr.get("sm_fixture_id") is not None else None

        pj = _load_pick_inputs(cur, spid)
        agg, agg_reason = _aggregate_shadow_native_like(
            cur,
            source_shadow_pick_id=spid,
            provider_snapshot_id=int(rr["provider_snapshot_id"]) if rr.get("provider_snapshot_id") else None,
            payload_json=pj,
        )

        consensus_ft: dict[str, Any] = {}
        fav_side: Optional[str] = None
        fav_decimal: Optional[float] = None
        fav_tie_note = ""
        fav_agg_note = agg_reason
        if agg is not None:
            consensus_ft = dict((agg.consensus or {}).get("FT_1X2") or {})
            fav_side, fav_decimal, fav_tie_note = _favorite_side_ft_1x2(consensus_ft)

        sel_fav = ""
        if fav_side == "home":
            sel_fav = home_name
        elif fav_side == "away":
            sel_fav = away_name
        elif fav_side == "draw":
            sel_fav = "Draw"

        er_base = EvalRow(
            shadow_daily_pick_id=spid,
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
        ev_base = _evaluate_one(er_base)

        er_dsr = EvalRow(
            shadow_daily_pick_id=int(dsr_r["dsr_pick_id"]),
            run_key=str(dsr_r.get("source_run_key") or rr["run_key"]),
            selection=str(dsr_r.get("selection") or ""),
            decimal_odds=float(dsr_r["decimal_odds"]) if dsr_r.get("decimal_odds") is not None else None,
            home_name=home_name,
            away_name=away_name,
            event_status=event_status,
            result_home=result_home,
            result_away=result_away,
            sm_fixture_id=sm_fixture_id,
        )
        ev_dsr = _evaluate_one(er_dsr)

        er_fav = EvalRow(
            shadow_daily_pick_id=spid,
            run_key=str(rr["run_key"]),
            selection=sel_fav,
            decimal_odds=float(fav_decimal) if fav_decimal is not None else None,
            home_name=home_name,
            away_name=away_name,
            event_status=event_status,
            result_home=result_home,
            result_away=result_away,
            sm_fixture_id=sm_fixture_id,
        )
        if fav_side is None or fav_decimal is None:
            ev_fav = {
                "eval_status": "no_evaluable",
                "evaluation_reason": f"favorite_benchmark_skipped:{fav_tie_note or agg_reason}",
                "roi_flat_stake_units": None,
            }
        else:
            ev_fav = _evaluate_one(er_fav)

        dsr_side = str(dsr_r.get("selected_side_canonical") or "").strip()
        if not dsr_side:
            dsr_side = (
                _selection_side(
                    str(dsr_r.get("selection") or ""),
                    str(dsr_r.get("ev_home_name") or ""),
                    str(dsr_r.get("ev_away_name") or ""),
                )
                or "unknown"
            )

        same_pick = "yes" if (dsr_side == fav_side and fav_side is not None) else "no"
        if fav_side is None:
            same_pick = "n/a"

        detail_rows.append(
            {
                "source_shadow_pick_id": spid,
                "bt2_event_id": rr.get("bt2_event_id") if "bt2_event_id" in rr else None,
                "league_name": dsr_r.get("league_name"),
                "home_team": home_name,
                "away_team": away_name,
                "consensus_FT_1X2_json": json.dumps(consensus_ft, ensure_ascii=False) if consensus_ft else "",
                "favorite_side_by_market": fav_side or "",
                "favorite_tiebreak_note": fav_tie_note,
                "aggregate_note": fav_agg_note,
                "dsr_selection_side_canonical": dsr_side,
                "favorite_benchmark_selection": fav_side or "",
                "same_pick_yes_no": same_pick,
                "evaluation_status_dsr": str(ev_dsr.get("eval_status") or ""),
                "evaluation_status_dsr_db": str(dsr_r.get("dsr_eval_status_db") or ""),
                "evaluation_status_baseline_non_dsr": str(ev_base.get("eval_status") or ""),
                "evaluation_status_favorite": str(ev_fav.get("eval_status") or ""),
                "roi_dsr": float(ev_dsr["roi_flat_stake_units"])
                if ev_dsr.get("roi_flat_stake_units") is not None
                else None,
                "roi_baseline_non_dsr": float(ev_base["roi_flat_stake_units"])
                if ev_base.get("roi_flat_stake_units") is not None
                else None,
                "roi_favorite": float(ev_fav["roi_flat_stake_units"])
                if ev_fav.get("roi_flat_stake_units") is not None
                else None,
                "decimal_odds_favorite_consensus": fav_decimal,
                "in_sample_32": spid in sample_set if sample_set else False,
            }
        )

    cur.close()
    conn.close()

    def row_as_metric_dsr(d: dict[str, Any]) -> dict[str, Any]:
        return {
            "eval_status": d["evaluation_status_dsr"],
            "roi_flat_stake_units": d["roi_dsr"],
        }

    def row_as_metric(d: dict[str, Any], status_key: str, roi_key: str) -> dict[str, Any]:
        return {
            "eval_status": d[status_key],
            "roi_flat_stake_units": d[roi_key],
        }

    full_dsr = _metrics_from_rows([row_as_metric_dsr(x) for x in detail_rows])
    full_base = _metrics_from_rows(
        [row_as_metric(x, "evaluation_status_baseline_non_dsr", "roi_baseline_non_dsr") for x in detail_rows]
    )
    full_fav = _metrics_from_rows(
        [row_as_metric(x, "evaluation_status_favorite", "roi_favorite") for x in detail_rows]
    )

    s32 = [x for x in detail_rows if x.get("in_sample_32")]
    s32_dsr = _metrics_from_rows([row_as_metric_dsr(x) for x in s32])
    s32_base = _metrics_from_rows(
        [row_as_metric(x, "evaluation_status_baseline_non_dsr", "roi_baseline_non_dsr") for x in s32]
    )
    s32_fav = _metrics_from_rows(
        [row_as_metric(x, "evaluation_status_favorite", "roi_favorite") for x in s32]
    )

    same_ct = sum(1 for x in detail_rows if x.get("same_pick_yes_no") == "yes")
    same_total = sum(1 for x in detail_rows if x.get("same_pick_yes_no") in ("yes", "no"))
    s32_same_ct = sum(1 for x in s32 if x.get("same_pick_yes_no") == "yes")
    s32_same_tot = sum(1 for x in s32 if x.get("same_pick_yes_no") in ("yes", "no"))

    summary: dict[str, Any] = {
        "dsr_run_key": DSR_RUN_KEY,
        "benchmark_rules": {
            "name": "always_favorite_ft_1x2",
            "consensus_source": "aggregated_odds_from_toa_shadow_payload (mismo snapshot TOA / fallback pick_inputs que shadow-native)",
            "choice": "pierna con menor decimal en consensus.FT_1X2 (home, draw, away)",
            "tiebreak": "si dos o tres piernas empatan al mínimo, elegir en orden fijo home → draw → away",
            "evaluation": (
                "EvalRow + _evaluate_one (scripts/bt2_shadow_evaluate_performance.py), misma fusión de verdad "
                "(bt2_events + fallback SportMonks) para DSR, baseline no-DSR y always_favorite. "
                "Métricas DSR recalculadas aquí (no solo fila histórica en bt2_shadow_pick_eval)."
            ),
        },
        "full_native_run_n": len(detail_rows),
        "sample_32_n": len(s32),
        "sample_32_source_csv": str(SAMPLE_CSV),
        "alignment_dsr_vs_favorite": {
            "full_run_same_pick_count": same_ct,
            "full_run_comparable_pair_count": same_total,
            "full_run_same_pick_rate": round(same_ct / same_total, 6) if same_total else None,
            "sample32_same_pick_count": s32_same_ct,
            "sample32_comparable_pair_count": s32_same_tot,
            "sample32_same_pick_rate": round(s32_same_ct / s32_same_tot, 6) if s32_same_tot else None,
        },
        "metrics_full_run": {
            "dsr_native": full_dsr,
            "always_favorite": full_fav,
            "baseline_non_dsr_same_slice": full_base,
        },
        "metrics_sample_32": {
            "dsr_native": s32_dsr,
            "always_favorite": s32_fav,
            "baseline_non_dsr_same_slice": s32_base,
        },
        "delta_hit_rate_on_scored": {
            "dsr_minus_favorite_full": round(
                float(full_dsr["hit_rate_on_scored"]) - float(full_fav["hit_rate_on_scored"]),
                6,
            ),
            "dsr_minus_favorite_sample32": round(
                float(s32_dsr["hit_rate_on_scored"]) - float(s32_fav["hit_rate_on_scored"]),
                6,
            ),
            "dsr_minus_favorite_roi_pct_full": round(
                float(full_dsr["roi_flat_stake_pct"]) - float(full_fav["roi_flat_stake_pct"]),
                6,
            ),
            "dsr_minus_favorite_roi_pct_sample32": round(
                float(s32_dsr["roi_flat_stake_pct"]) - float(s32_fav["roi_flat_stake_pct"]),
                6,
            ),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_cols = [
        "source_shadow_pick_id",
        "home_team",
        "away_team",
        "consensus_FT_1X2_json",
        "favorite_side_by_market",
        "dsr_selection_side_canonical",
        "favorite_benchmark_selection",
        "same_pick_yes_no",
        "evaluation_status_dsr",
        "evaluation_status_baseline_non_dsr",
        "evaluation_status_favorite",
        "roi_dsr",
        "roi_baseline_non_dsr",
        "roi_favorite",
    ]

    def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=csv_cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in csv_cols})

    _write_csv(OUT_FULL, detail_rows)
    _write_csv(OUT_SAMPLE32, s32)

    print(json.dumps({"ok": True, "wrote": str(OUT_SUMMARY), "n_full": len(detail_rows), "n_sample32": len(s32)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Exportación fila-a-fila de picks de un shadow run (ej. replay native completo).

Solo lectura + escritura de artefactos en scripts/outputs/.
No modifica replay ni producción.

Uso:
  PYTHONPATH=. python3 scripts/export_bt2_shadow_native_full_replay_picks.py \\
    --run-key shadow-dsr-native-full-20260428-214014
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_dsr_shadow_native_adapter import aggregated_odds_from_toa_shadow_payload  # noqa: E402
from apps.api.bt2_settings import bt2_settings  # noqa: E402

OUT_CSV = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay" / "dsr_native_full_replay_picks_detailed.csv"
OUT_JSON = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay" / "dsr_native_full_replay_picks_detailed.json"
OUT_SUMMARY = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay" / "dsr_native_full_replay_picks_detailed_summary.json"


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _ft12_consensus(agg: Any) -> tuple[Optional[float], Optional[float], Optional[float]]:
    if agg is None:
        return None, None, None
    c = getattr(agg, "consensus", None) or {}
    if not isinstance(c, dict):
        return None, None, None
    ft = c.get("FT_1X2") if isinstance(c.get("FT_1X2"), dict) else {}
    if not isinstance(ft, dict):
        return None, None, None
    return _f(ft.get("home")), _f(ft.get("draw")), _f(ft.get("away"))


def _odds_rank_label(
    sel_side: Optional[str],
    h: Optional[float],
    d: Optional[float],
    a: Optional[float],
) -> str:
    """favorite | mid | longest según cuota decimal (menor = más favorito)."""
    if not sel_side or sel_side not in {"home", "draw", "away"}:
        return ""
    triple = [
        ("home", h),
        ("draw", d),
        ("away", a),
    ]
    valid = [(s, o) for s, o in triple if o is not None and o > 0]
    if len(valid) < 2:
        return ""
    sorted_legs = sorted(valid, key=lambda x: x[1])
    order_map = {s: i for i, (s, _) in enumerate(sorted_legs)}
    idx = order_map.get(sel_side)
    if idx is None:
        return ""
    n = len(sorted_legs)
    if n == 3:
        return ("favorite", "mid", "longest")[idx]
    if n == 2:
        return "favorite" if idx == 0 else "longest"
    return "favorite"


def _odds_band(dec: Optional[float]) -> str:
    if dec is None or dec <= 0:
        return "sin_cuota"
    if dec < 1.5:
        return "<1.5"
    if dec < 2.0:
        return "1.5-2"
    if dec < 3.0:
        return "2-3"
    if dec < 5.0:
        return "3-5"
    return "5+"


def _truth_hit(eval_status: Optional[str]) -> Optional[bool]:
    if eval_status == "hit":
        return True
    if eval_status == "miss":
        return False
    return None


def _excerpt(raw_summary: Any, max_len: int = 280) -> str:
    if not isinstance(raw_summary, dict):
        return ""
    ne = raw_summary.get("narrative_excerpt") or ""
    s = str(ne).replace("\n", " ").strip()
    return s[:max_len] if len(s) > max_len else s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-key", required=True, help="bt2_shadow_runs.run_key")
    ap.add_argument("--out-csv", type=Path, default=OUT_CSV)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-summary", type=Path, default=OUT_SUMMARY)
    args = ap.parse_args()

    conn = psycopg2.connect(_dsn(), connect_timeout=30)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT id FROM bt2_shadow_runs WHERE run_key = %s LIMIT 1
            """,
            (args.run_key,),
        )
        rr = cur.fetchone()
        if not rr:
            raise SystemExit(f"No existe run_key: {args.run_key}")
        run_pk = int(rr["id"])

        cur.execute(
            """
            SELECT
                sr.run_key,
                dp.id AS shadow_daily_pick_id,
                dp.sm_fixture_id,
                dp.bt2_event_id,
                e.kickoff_utc,
                COALESCE(l.name, '') AS league_name,
                COALESCE(th.name, '') AS home_team,
                COALESCE(ta.name, '') AS away_team,
                dp.market AS market_raw,
                dp.selection AS selected_team,
                dp.decimal_odds AS selected_decimal_odds,
                dp.dsr_model,
                dp.dsr_prompt_version,
                dp.dsr_parse_status AS parse_status,
                dp.dsr_raw_summary_json,
                dp.selected_side_canonical,
                dp.provider_snapshot_id,
                pe.eval_status AS evaluation_status,
                pe.result_home,
                pe.result_away
            FROM bt2_shadow_daily_picks dp
            INNER JOIN bt2_shadow_runs sr ON sr.id = dp.run_id
            LEFT JOIN bt2_events e ON e.id = dp.bt2_event_id
            LEFT JOIN bt2_leagues l ON l.id = dp.league_id
            LEFT JOIN bt2_teams th ON th.id = e.home_team_id
            LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
            LEFT JOIN bt2_shadow_pick_eval pe ON pe.shadow_daily_pick_id = dp.id
            WHERE dp.run_id = %s
            ORDER BY dp.id ASC
            """,
            (run_pk,),
        )
        rows_in = cur.fetchall() or []
    finally:
        cur.close()
        conn.close()

    rows_out: list[dict[str, Any]] = []
    snap_cache: dict[int, tuple[Any, Any]] = {}

    conn = psycopg2.connect(_dsn(), connect_timeout=30)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        for r in rows_in:
            r = dict(r)
            raw_summary = r.get("dsr_raw_summary_json")
            if isinstance(raw_summary, str):
                try:
                    raw_summary = json.loads(raw_summary)
                except json.JSONDecodeError:
                    raw_summary = {}
            market_canonical = ""
            selection_canonical = ""
            no_pick_reason = ""
            if isinstance(raw_summary, dict):
                market_canonical = str(raw_summary.get("market_canonical") or "")
                selection_canonical = str(raw_summary.get("selection_canonical") or "")
                no_pick_reason = str(raw_summary.get("no_pick_reason") or "")

            psid = r.get("provider_snapshot_id")
            h_odds = d_odds = a_odds = None
            if psid is not None:
                pid = int(psid)
                if pid not in snap_cache:
                    cur.execute(
                        """
                        SELECT raw_payload, provider_snapshot_time
                        FROM bt2_shadow_provider_snapshots
                        WHERE id = %s
                        """,
                        (pid,),
                    )
                    sr = cur.fetchone()
                    snap_cache[pid] = (
                        (sr or {}).get("raw_payload"),
                        (sr or {}).get("provider_snapshot_time"),
                    )
                raw_pl, pst = snap_cache[pid]
                agg, _meta = aggregated_odds_from_toa_shadow_payload(
                    raw_pl, provider_snapshot_time=pst
                )
                h_odds, d_odds, a_odds = _ft12_consensus(agg)

            sel_dec = _f(r.get("selected_decimal_odds"))
            implied = (1.0 / sel_dec) if sel_dec and sel_dec > 0 else None

            side = r.get("selected_side_canonical")
            side_s = str(side).strip().lower() if side else ""
            if side_s not in {"home", "draw", "away"}:
                side_s = ""
            rank_lbl = _odds_rank_label(side_s or None, h_odds, d_odds, a_odds)

            rh, ra = r.get("result_home"), r.get("result_away")
            if rh is not None and ra is not None:
                result_score_text = f"{int(rh)}-{int(ra)}"
            else:
                result_score_text = ""

            evs = r.get("evaluation_status")
            row_flat = {
                "run_key": r.get("run_key"),
                "shadow_daily_pick_id": r.get("shadow_daily_pick_id"),
                "sm_fixture_id": r.get("sm_fixture_id"),
                "bt2_event_id": r.get("bt2_event_id"),
                "kickoff_utc": r.get("kickoff_utc").isoformat() if r.get("kickoff_utc") else "",
                "league_name": r.get("league_name"),
                "home_team": r.get("home_team"),
                "away_team": r.get("away_team"),
                "market_canonical": market_canonical,
                "selection_canonical": selection_canonical,
                "selected_team": r.get("selected_team"),
                "selected_decimal_odds": sel_dec,
                "implied_probability": round(implied, 6) if implied is not None else "",
                "home_odds": h_odds,
                "draw_odds": d_odds,
                "away_odds": a_odds,
                "odds_rank_of_selection": rank_lbl,
                "dsr_model": r.get("dsr_model"),
                "dsr_prompt_version": r.get("dsr_prompt_version"),
                "parse_status": r.get("parse_status"),
                "no_pick_reason": no_pick_reason,
                "response_excerpt": _excerpt(raw_summary if isinstance(raw_summary, dict) else {}),
                "evaluation_status": evs,
                "result_score_text": result_score_text,
                "truth_hit": _truth_hit(str(evs) if evs else ""),
            }
            rows_out.append(row_flat)
    finally:
        cur.close()
        conn.close()

    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows_out[0].keys()) if rows_out else []
    if rows_out:
        with args.out_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows_out)
        with args.out_json.open("w", encoding="utf-8") as f:
            json.dump(rows_out, f, ensure_ascii=False, indent=2)

    # Resumen derivado (solo filas con pick OK y rank conocido / bandas)
    rank_counts = Counter()
    band_counts = Counter()
    for row in rows_out:
        rk = row.get("odds_rank_of_selection") or ""
        if rk:
            rank_counts[rk] += 1
        band_counts[_odds_band(_f(row.get("selected_decimal_odds")))] += 1

    summary = {
        "run_key": args.run_key,
        "total_rows": len(rows_out),
        "odds_rank_counts": dict(rank_counts),
        "notes": {
            "favorite": rank_counts.get("favorite", 0),
            "mid": rank_counts.get("mid", 0),
            "longest": rank_counts.get("longest", 0),
        },
        "odds_band_distribution": dict(band_counts),
    }
    with args.out_summary.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

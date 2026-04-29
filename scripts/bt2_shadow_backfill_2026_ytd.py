#!/usr/bin/env python3
"""
Backfill shadow subset5 por mes (2026 YTD): subtramos controlados, un run_key por mes.

No toca tablas productivas; persiste solo en bt2_shadow_*.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_backfill_2026_ytd"


def _import_backfill() -> Any:
    p = ROOT / "scripts" / "bt2_shadow_backfill_subset5.py"
    name = "bt2_shadow_backfill_subset5_ytd"
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run_one_month(
    bf: Any,
    *,
    year: int,
    month: int,
    cap: int,
    run_key: str,
) -> dict[str, Any]:
    """Misma lógica que `_run_window`, pero si CDM no trae fixtures del mes, usa SM Starter between (subset5)."""
    import os

    import psycopg2
    import psycopg2.extras

    from apps.api.bt2_settings import bt2_settings

    conn = psycopg2.connect(bf._dsn(), connect_timeout=12)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        rows = bf._build_rows_for_window(
            cur, year=year, month_from=month, month_to=month, per_league_cap=cap
        )
    finally:
        cur.close()
        conn.close()

    row_source = "bt2_events_cdm"
    if not rows:
        sm_api = (os.environ.get("SPORTMONKS_API_KEY") or bt2_settings.sportmonks_api_key or "").strip()
        if sm_api:
            rows = bf._sm_fetch_between_subset5(
                year=year,
                month_from=month,
                month_to=month,
                sm_api_key=sm_api,
                per_league_cap=cap,
            )
            row_source = "sportmonks_between_subset5"

    paid = bf._import_paid_lab()
    api_toa = (os.environ.get("THEODDSAPI_KEY") or bt2_settings.theoddsapi_key or "").strip()
    if not api_toa:
        raise SystemExit("Falta THEODDSAPI_KEY / theoddsapi_key para backfill shadow.")

    matching_rows, odds_rows, credits = (
        paid.run_toa_phase(rows, api_toa)
        if rows
        else ([], [], {"estimated_total_cost_from_headers_sum": 0.0, "calls": []})
    )
    vp_map = (
        bf._compute_value_pool_pass([r for r in rows if int(r.get("bt2_event_id") or 0) > 0])
        if rows
        else {}
    )
    for r in rows:
        vp_map.setdefault(str(r.get("sm_fixture_id") or ""), "")

    conn2 = psycopg2.connect(bf._dsn(), connect_timeout=12)
    cur2 = conn2.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        persist_counts = bf._persist_run(
            cur2,
            run_key=run_key,
            rows=rows,
            matching_rows=matching_rows,
            odds_rows=odds_rows,
            credit_summary=credits,
            vp_map=vp_map,
        )
        conn2.commit()
    except Exception:
        conn2.rollback()
        raise
    finally:
        cur2.close()
        conn2.close()

    out = bf._summary_from_results(
        run_key=run_key,
        year=year,
        month_from=month,
        month_to=month,
        rows=rows,
        matching_rows=matching_rows,
        odds_rows=odds_rows,
        credits=credits,
        vp_map=vp_map,
        persist_counts=persist_counts,
    )
    out["row_source"] = row_source
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill shadow 2026 YTD por mes (subset5)")
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument(
        "--months",
        type=str,
        default="1,2,3,4",
        help="Meses a ejecutar (coma-separados), ej. 1,2,3,4",
    )
    ap.add_argument("--per-league-cap", type=int, default=12)
    ap.add_argument(
        "--skip-if-exists",
        action="store_true",
        default=True,
        help="Si el run_key ya existe en bt2_shadow_runs, no re-ejecuta (evita pisar corridas).",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Ignora skip-if-exists (peligro de duplicado por UNIQUE en run_key).",
    )
    args = ap.parse_args()

    bf = _import_backfill()
    cap = max(1, args.per_league_cap)
    months = [int(x.strip()) for x in args.months.split(",") if x.strip()]
    summaries: list[dict[str, Any]] = []

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    import psycopg2
    import psycopg2.extras

    for m in months:
        if m < 1 or m > 12:
            raise SystemExit(f"Mes inválido: {m}")
        run_key = f"shadow-subset5-backfill-{args.year}-{m:02d}"
        if args.skip_if_exists and not args.force:
            conn_chk = psycopg2.connect(bf._dsn(), connect_timeout=12)
            cur_chk = conn_chk.cursor()
            try:
                cur_chk.execute(
                    "SELECT 1 FROM bt2_shadow_runs WHERE run_key = %s LIMIT 1",
                    (run_key,),
                )
                if cur_chk.fetchone():
                    prev = OUT_DIR / f"backfill_summary_{args.year}_{m:02d}.json"
                    if prev.is_file():
                        loaded = json.loads(prev.read_text(encoding="utf-8"))
                        loaded["skipped_existing_run"] = True
                        summaries.append(loaded)
                    else:
                        summaries.append(
                            {
                                "run_key": run_key,
                                "skipped_existing_run": True,
                                "note": "run ya en bt2_shadow_runs; falta JSON local",
                            }
                        )
                    continue
            finally:
                cur_chk.close()
                conn_chk.close()

        s = _run_one_month(bf, year=args.year, month=m, cap=cap, run_key=run_key)
        summaries.append(s)
        out_json = OUT_DIR / f"backfill_summary_{args.year}_{m:02d}.json"
        out_json.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")

    fn = [
        "run_key",
        "window",
        "fixtures_seen",
        "fixtures_matched",
        "match_rate",
        "fixtures_with_h2h_t60",
        "matched_with_odds_t60",
        "matched_without_odds_t60",
        "unmatched_event",
        "credits_used",
        "shadow_picks_generated",
        "value_pool_pass_rate",
        "distinct_leagues",
        "rows_persisted_bt2_shadow_runs",
        "rows_persisted_snapshots",
        "rows_persisted_daily_picks",
        "rows_persisted_inputs",
        "rows_persisted_evals",
    ]
    ov = OUT_DIR / "backfill_2026_ytd_overview.csv"
    with ov.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn)
        w.writeheader()
        for s in summaries:
            rp = s.get("rows_persisted") or {}
            w.writerow(
                {
                    "run_key": s.get("run_key"),
                    "window": s.get("window"),
                    "fixtures_seen": s.get("fixtures_seen"),
                    "fixtures_matched": s.get("fixtures_matched"),
                    "match_rate": s.get("match_rate"),
                    "fixtures_with_h2h_t60": s.get("fixtures_with_h2h_t60"),
                    "matched_with_odds_t60": s.get("matched_with_odds_t60"),
                    "matched_without_odds_t60": s.get("matched_without_odds_t60"),
                    "unmatched_event": s.get("unmatched_event"),
                    "credits_used": s.get("credits_used"),
                    "shadow_picks_generated": s.get("shadow_picks_generated"),
                    "value_pool_pass_rate": s.get("value_pool_pass_rate"),
                    "distinct_leagues": s.get("distinct_leagues"),
                    "rows_persisted_bt2_shadow_runs": rp.get("bt2_shadow_runs"),
                    "rows_persisted_snapshots": rp.get("bt2_shadow_provider_snapshots"),
                    "rows_persisted_daily_picks": rp.get("bt2_shadow_daily_picks"),
                    "rows_persisted_inputs": rp.get("bt2_shadow_pick_inputs"),
                    "rows_persisted_evals": rp.get("bt2_shadow_pick_eval"),
                }
            )

    readme = f"""# BT2 Shadow backfill 2026 YTD (subset5)

Subtramos mensuales controlados; un `run_key` por mes. No productivo.

## Run keys

- `shadow-subset5-backfill-{args.year}-01` … `shadow-subset5-backfill-{args.year}-04` (según `--months`)

## Artefactos

- `backfill_summary_{args.year}_01.json` … (por mes ejecutado)
- `backfill_2026_ytd_overview.csv`

## Restricciones

- subset5, h2h, us, T-60, carril shadow.

## Fuente de filas por mes

- Si `bt2_events` no tiene fixtures del mes para subset5, se usa **SportMonks** `fixtures/between` (subset5) y el resumen JSON incluye `row_source=sportmonks_between_subset5`.
- Si hay datos en CDM, `row_source=bt2_events_cdm`.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    print(
        json.dumps(
            {"ok": True, "out_dir": str(OUT_DIR.relative_to(ROOT)), "summaries": summaries},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

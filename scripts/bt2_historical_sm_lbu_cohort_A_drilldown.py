#!/usr/bin/env python3
"""
Fase 3C — drill-down cohorte A (2025-01..2025-05): semanas más débiles + fixture/league/tiempo.

Criterio de selección reproducible (min-max sobre las 22 semanas ISO de A).
No modifica T-60 ni bounded replay.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2.extras

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from apps.api.bt2_settings import bt2_settings

WEEKLY_CSV = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_cohort_A_robustness" / "cohort_A_weekly.csv"
OUT_DIR = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_cohort_A_drilldown"
TOP_N_WEEKS = 5
MAX_FX = 2_000_000

# Pesos documentados para weakness_score (mayor = semana más débil dentro de A)
W_NU = 0.35
W_SURV = 0.35
W_VP = 0.30

_proto_path = _repo / "scripts" / "bt2_historical_sm_lbu_replay_prototype.py"
_spec = importlib.util.spec_from_file_location("bt2_historical_sm_lbu_replay_prototype", _proto_path)
_proto = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules["bt2_historical_sm_lbu_replay_prototype"] = _proto
_spec.loader.exec_module(_proto)
extract_cdm_rows = _proto.extract_cdm_rows
cutoff_t60 = _proto.cutoff_t60
to_agg_tuples = _proto.to_agg_tuples
aggregate_odds_for_event = _proto.aggregate_odds_for_event
data_completeness_score = _proto.data_completeness_score
event_passes_value_pool = _proto.event_passes_value_pool
MIN_DEC = _proto.MIN_DEC
_f = _proto._f


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def _minmax(vals: list[float]) -> list[float]:
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return [0.0 for _ in vals]
    return [(v - lo) / (hi - lo) for v in vals]


def load_weekly_rows() -> list[dict[str, Any]]:
    if not WEEKLY_CSV.is_file():
        raise FileNotFoundError(
            f"Falta {WEEKLY_CSV}; ejecuta antes scripts/bt2_historical_sm_lbu_cohort_robustness.py"
        )
    rows: list[dict[str, Any]] = []
    with WEEKLY_CSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def rank_weeks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nfs = [int(r["n_fixtures"]) for r in rows]
    nu = [int(r["n_not_usable"]) for r in rows]
    nu_rate = [nu[i] / nfs[i] if nfs[i] else 0.0 for i in range(len(rows))]
    surv = [float(r["tasa_sobrevivencia_lineas"]) for r in rows]
    vp = [float(r["vp_over_n_fixtures"]) for r in rows]
    inv_s = [1.0 - s for s in surv]
    inv_vp = [1.0 - v for v in vp]

    mm_nu = _minmax(nu_rate)
    mm_inv_s = _minmax(inv_s)
    mm_inv_vp = _minmax(inv_vp)

    scored: list[dict[str, Any]] = []
    for i, r in enumerate(rows):
        w = W_NU * mm_nu[i] + W_SURV * mm_inv_s[i] + W_VP * mm_inv_vp[i]
        scored.append(
            {
                "block_id": r["block_id"],
                "day_from": r["day_from"],
                "day_to": r["day_to"],
                "n_fixtures": nfs[i],
                "n_not_usable": nu[i],
                "not_usable_rate": round(nu_rate[i], 6),
                "tasa_sobrevivencia_lineas": surv[i],
                "vp_over_n_fixtures": vp[i],
                "weakness_score": round(w, 6),
            }
        )
    scored.sort(
        key=lambda x: (
            -x["weakness_score"],
            -x["not_usable_rate"],
            x["vp_over_n_fixtures"],
            -x["n_not_usable"],
        )
    )
    return scored


def observable_reason(
    *,
    n_before: int,
    n_t60: int,
    n_lbu_null: int,
    value_pool: bool,
    dcs: int,
    mkeys: list[str],
) -> str:
    if n_before == 0:
        return "sin_lineas_canonicas_pre_t60"
    if n_t60 == 0:
        if n_lbu_null >= n_before:
            return "todas_lineas_sin_ts_o_ts_post_t60"
        return "lineas_canonicas_filtradas_t60_cero_restantes"
    if not value_pool:
        if dcs == 0:
            return "vp_false_dcs0_agregado_sin_consenso_util"
        if "FT_1X2" not in mkeys:
            return "vp_false_sin_ft1x2_en_cobertura_mercados"
        return "vp_false_con_ft1x2_revisa_umbral_min_decimal_o_balance_mercados"
    return "value_pool_true"


def hour_bucket(h: int) -> str:
    if h < 6:
        return "00-05"
    if h < 12:
        return "06-11"
    if h < 18:
        return "12-17"
    return "18-23"


def fetch_fixtures_window(d0: date, d1: date) -> list[dict[str, Any]]:
    start = datetime.combine(d0, time.min, tzinfo=timezone.utc)
    end = datetime.combine(d1 + timedelta(days=1), time.min, tzinfo=timezone.utc)
    conn = psycopg2.connect(_dsn())
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT
          e.id AS event_id,
          e.sportmonks_fixture_id AS fixture_id,
          e.kickoff_utc,
          e.league_id,
          l.name AS league_name,
          l.tier AS league_tier,
          l.country AS league_country,
          r.payload
        FROM bt2_events e
        INNER JOIN raw_sportmonks_fixtures r ON r.fixture_id = e.sportmonks_fixture_id
        LEFT JOIN bt2_leagues l ON l.id = e.league_id
        WHERE e.kickoff_utc IS NOT NULL
          AND e.kickoff_utc >= %s
          AND e.kickoff_utc < %s
        ORDER BY e.kickoff_utc
        LIMIT %s
        """,
        (start, end, MAX_FX),
    )
    out = [dict(x) for x in cur.fetchall()]
    cur.close()
    conn.close()
    return out


def process_fixture_row(row: dict[str, Any], target_week: str) -> dict[str, Any]:
    pl = row["payload"]
    if isinstance(pl, str):
        pl = json.loads(pl)
    ko: datetime = row["kickoff_utc"]
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    t_cut = cutoff_t60(ko)
    before = extract_cdm_rows(pl)
    n_lbu_n = sum(1 for t in before if t[4] is None)
    t60 = [t for t in before if t[4] is not None and t[4] <= t_cut]
    agg = aggregate_odds_for_event(to_agg_tuples(t60), min_decimal=MIN_DEC)
    vp = event_passes_value_pool(agg, min_decimal=MIN_DEC)
    dcs = data_completeness_score(agg)
    ft = agg.consensus.get("FT_1X2") or {}
    mkeys = [k for k, v in (agg.market_coverage or {}).items() if v]
    mkeys_s = sorted(mkeys)[:20]
    ko_utc = ko.astimezone(timezone.utc)
    day = ko_utc.strftime("%Y-%m-%d")
    hr = ko_utc.hour
    reason = observable_reason(
        n_before=len(before),
        n_t60=len(t60),
        n_lbu_null=n_lbu_n,
        value_pool=bool(vp),
        dcs=int(dcs),
        mkeys=mkeys_s,
    )
    isoy = ko_utc.isocalendar()
    wkey = f"{isoy.year}-W{isoy.week:02d}"
    return {
        "target_week": target_week,
        "fixture_id": int(row["fixture_id"]),
        "event_id": int(row["event_id"]),
        "kickoff_utc": ko.isoformat(),
        "kickoff_day_utc": day,
        "kickoff_hour_utc": hr,
        "hour_bucket_utc": hour_bucket(hr),
        "iso_week_fixture": wkey,
        "league_id": row.get("league_id"),
        "league_name": row.get("league_name") or "",
        "league_tier": row.get("league_tier") or "",
        "league_country": row.get("league_country") or "",
        "n_lines_before_filter": len(before),
        "n_lines_t60": len(t60),
        "n_lines_lbu_null": n_lbu_n,
        "value_pool": bool(vp),
        "data_completeness_score": int(dcs),
        "ft1x2_home_consensus": _f(ft.get("home")),
        "ft1x2_draw": _f(ft.get("draw")),
        "ft1x2_away": _f(ft.get("away")),
        "market_coverage_keys": "|".join(mkeys_s),
        "observable_reason": reason,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    weekly = load_weekly_rows()
    ranked = rank_weeks(weekly)
    selected = ranked[:TOP_N_WEEKS]

    # Map block_id -> day range from original CSV
    by_id = {r["block_id"]: r for r in weekly}

    all_fixtures: list[dict[str, Any]] = []
    for s in selected:
        bid = s["block_id"]
        r0 = by_id[bid]
        d0 = date.fromisoformat(str(r0["day_from"]))
        d1 = date.fromisoformat(str(r0["day_to"]))
        raw = fetch_fixtures_window(d0, d1)
        for row in raw:
            all_fixtures.append(process_fixture_row(row, target_week=bid))

    # Agregados
    agg_lt: dict[tuple[str, Any, str, str], dict[str, Any]] = {}
    agg_day: dict[tuple[str, str], dict[str, Any]] = {}
    agg_hr: dict[tuple[str, str], dict[str, Any]] = {}

    def bump(
        store: dict[tuple, dict[str, Any]],
        key: tuple,
        fr: dict[str, Any],
    ) -> None:
        if key not in store:
            store[key] = {
                "n_fixtures": 0,
                "n_not_usable": 0,
                "n_lines_before": 0,
                "n_lines_t60": 0,
                "n_vp_true": 0,
                "n_before_zero": 0,
            }
        e = store[key]
        e["n_fixtures"] += 1
        if not fr["value_pool"]:
            e["n_not_usable"] += 1
        else:
            e["n_vp_true"] += 1
        e["n_lines_before"] += int(fr["n_lines_before_filter"])
        e["n_lines_t60"] += int(fr["n_lines_t60"])
        if int(fr["n_lines_before_filter"]) == 0:
            e["n_before_zero"] += 1

    for fr in all_fixtures:
        tw = fr["target_week"]
        lid = fr["league_id"]
        lname = fr["league_name"] or "(sin_liga)"
        ltier = fr["league_tier"] or "unknown"
        bump(agg_lt, (tw, lid, lname, ltier), fr)
        bump(agg_day, (tw, fr["kickoff_day_utc"]), fr)
        bump(agg_hr, (tw, fr["hour_bucket_utc"]), fr)

    reason_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for fr in all_fixtures:
        if not fr["value_pool"]:
            reason_counts[fr["target_week"]][fr["observable_reason"]] += 1

    # Pooled por liga (todas las semanas objetivo)
    pool_league: dict[tuple[Any, str, str], dict[str, Any]] = {}
    for fr in all_fixtures:
        key = (fr["league_id"], fr["league_name"] or "(sin_liga)", fr["league_tier"] or "unknown")
        bump(pool_league, key, fr)

    pool_rows = []
    for (lid, lname, ltier), e in pool_league.items():
        nf = e["n_fixtures"]
        pool_rows.append(
            {
                "league_id": lid,
                "league_name": lname,
                "league_tier": ltier,
                "n_fixtures": nf,
                "n_not_usable": e["n_not_usable"],
                "not_usable_share": round(e["n_not_usable"] / nf, 4) if nf else 0,
                "lines_survival_proxy": round(e["n_lines_t60"] / e["n_lines_before"], 4)
                if e["n_lines_before"]
                else None,
            }
        )
    pool_rows.sort(key=lambda x: (-x["n_not_usable"], -x["n_fixtures"]))

    summary = {
        "cohorte": "A_2025_stable_high_survival",
        "rango_kickoff_utc": {"from": "2025-01-01", "to": "2025-05-31"},
        "selection": {
            "source_weekly_csv": str(WEEKLY_CSV.relative_to(_repo)),
            "formula": (
                f"weakness_score = {W_NU}*minmax(not_usable_rate) + "
                f"{W_SURV}*minmax(1 - tasa_sobrevivencia_lineas) + "
                f"{W_VP}*minmax(1 - vp_over_n_fixtures); "
                "minmax sobre las 22 filas semanales de A; mayor = más débil."
            ),
            "tie_break": [
                "mayor weakness_score",
                "mayor not_usable_rate",
                "menor vp_over_n_fixtures",
                "mayor n_not_usable absoluto",
            ],
        },
        "ranking_top10": ranked[:10],
        "weeks_selected": selected,
        "not_usable_reason_by_week": {k: dict(v) for k, v in reason_counts.items()},
        "top_leagues_by_n_not_usable_pooled": pool_rows[:15],
        "counts": {
            "fixtures_exported": len(all_fixtures),
            "weeks_drilled": len(selected),
        },
    }

    (OUT_DIR / "drilldown_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    if all_fixtures:
        fn = list(all_fixtures[0].keys())
        with (OUT_DIR / "fixtures_selected_weeks.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            for row in all_fixtures:
                w.writerow(row)

    def write_agg(path: Path, rows_out: list[dict[str, Any]], fieldnames: list[str]) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows_out:
                w.writerow(r)

    lt_rows = []
    for (tw, lid, lname, ltier), e in sorted(agg_lt.items()):
        nf = e["n_fixtures"]
        lt_rows.append(
            {
                "target_week": tw,
                "league_id": lid,
                "league_name": lname,
                "league_tier": ltier,
                "n_fixtures": nf,
                "n_not_usable": e["n_not_usable"],
                "not_usable_share": round(e["n_not_usable"] / nf, 4) if nf else 0,
                "n_vp_true": e["n_vp_true"],
                "n_lines_before_sum": e["n_lines_before"],
                "n_lines_t60_sum": e["n_lines_t60"],
                "lines_survival_proxy": round(e["n_lines_t60"] / e["n_lines_before"], 4)
                if e["n_lines_before"]
                else None,
                "fixtures_sin_lineas_canonicas": e["n_before_zero"],
            }
        )
    lt_rows.sort(key=lambda x: (-x["n_not_usable"], -x["n_fixtures"]))
    if lt_rows:
        write_agg(OUT_DIR / "aggregates_by_league_tier_week.csv", lt_rows, list(lt_rows[0].keys()))

    day_rows = []
    for (tw, day), e in sorted(agg_day.items()):
        nf = e["n_fixtures"]
        day_rows.append(
            {
                "target_week": tw,
                "kickoff_day_utc": day,
                "n_fixtures": nf,
                "n_not_usable": e["n_not_usable"],
                "not_usable_share": round(e["n_not_usable"] / nf, 4) if nf else 0,
                "lines_survival_proxy": round(e["n_lines_t60"] / e["n_lines_before"], 4)
                if e["n_lines_before"]
                else None,
            }
        )
    if day_rows:
        write_agg(OUT_DIR / "aggregates_by_day_week.csv", day_rows, list(day_rows[0].keys()))

    hr_rows = []
    for (tw, hb), e in sorted(agg_hr.items()):
        nf = e["n_fixtures"]
        hr_rows.append(
            {
                "target_week": tw,
                "hour_bucket_utc": hb,
                "n_fixtures": nf,
                "n_not_usable": e["n_not_usable"],
                "not_usable_share": round(e["n_not_usable"] / nf, 4) if nf else 0,
                "lines_survival_proxy": round(e["n_lines_t60"] / e["n_lines_before"], 4)
                if e["n_lines_before"]
                else None,
            }
        )
    if hr_rows:
        write_agg(OUT_DIR / "aggregates_by_hour_bucket_week.csv", hr_rows, list(hr_rows[0].keys()))

    if pool_rows:
        with (OUT_DIR / "aggregates_by_league_pooled.csv").open("w", encoding="utf-8", newline="") as f:
            cols = list(pool_rows[0].keys())
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in pool_rows:
                w.writerow(r)

    readme = OUT_DIR / "README.md"
    readme.write_text(
        f"""# Drill-down cohorte A (semanas débiles)

## Regenerar

Requiere `cohort_A_weekly.csv` del paso de robustez:

```bash
cd {_repo}
python3 scripts/bt2_historical_sm_lbu_cohort_robustness.py
python3 scripts/bt2_historical_sm_lbu_cohort_A_drilldown.py
```

## Salidas

- `drilldown_summary.json` — criterio de selección, ranking, semanas elegidas, razones `observable_reason` entre no-VP.
- `fixtures_selected_weeks.csv` — nivel fixture.
- `aggregates_by_league_tier_week.csv`, `aggregates_by_day_week.csv`, `aggregates_by_hour_bucket_week.csv`
- `aggregates_by_league_pooled.csv` — ligas en las semanas objetivo (pooled).

**T-60** y agregador: mismos que `bt2_historical_sm_lbu_replay_prototype.py`.
""",
        encoding="utf-8",
    )

    print(json.dumps({"ok": True, "out": str(OUT_DIR.relative_to(_repo)), "weeks": [s["block_id"] for s in selected]}, indent=2))


if __name__ == "__main__":
    main()

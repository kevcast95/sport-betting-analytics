#!/usr/bin/env python3
"""
Panel por liga — cohorte A completa (kickoff 2025-01..2025-05), historical_sm_lbu / T-60.

Umbral mínimo documentado en summary.json. Paraleliza el cómputo por chunks tras una lectura BD.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import calendar
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2.extras

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from apps.api.bt2_settings import bt2_settings

OUT_DIR = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_cohort_A_league_outliers"
DAY0 = date(2025, 1, 1)
DAY1 = date(2025, 5, 31)
MAX_FX = 2_000_000
MIN_FIXTURES_THRESHOLD = 30

LeagueKey = tuple[Any, str, str, str]

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


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


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


def fetch_month(y: int, m: int) -> list[dict[str, Any]]:
    d0 = date(y, m, 1)
    last = date(y, m, calendar.monthrange(y, m)[1])
    start = datetime.combine(d0, time.min, tzinfo=timezone.utc)
    end = datetime.combine(last + timedelta(days=1), time.min, tzinfo=timezone.utc)
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


def process_one(row: dict[str, Any]) -> dict[str, Any]:
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
    mkeys = [k for k, v in (agg.market_coverage or {}).items() if v]
    mkeys_s = sorted(mkeys)[:20]
    reason = observable_reason(
        n_before=len(before),
        n_t60=len(t60),
        n_lbu_null=n_lbu_n,
        value_pool=bool(vp),
        dcs=int(dcs),
        mkeys=mkeys_s,
    )
    lid = row.get("league_id")
    return {
        "league_id": lid if lid is not None else -1,
        "league_name": (row.get("league_name") or "").strip() or "(sin_liga)",
        "league_tier": (row.get("league_tier") or "").strip() or "unknown",
        "league_country": (row.get("league_country") or "").strip(),
        "reason": reason,
        "value_pool": bool(vp),
        "n_lines_before": len(before),
        "n_lines_t60": len(t60),
    }


def _empty_league_bucket() -> dict[str, Any]:
    return {
        "n_fixtures": 0,
        "n_value_pool": 0,
        "n_not_usable": 0,
        "n_vp_false_dcs0": 0,
        "n_sin_lineas_pre": 0,
        "n_t60_zero": 0,
        "n_todas_sin_ts": 0,
        "n_vp_false_sin_ft1x2": 0,
        "n_vp_false_ft1x2_other": 0,
        "n_lines_before": 0,
        "n_lines_t60": 0,
    }


def process_chunk(rows: list[dict[str, Any]]) -> dict[LeagueKey, dict[str, Any]]:
    local: dict[LeagueKey, dict[str, Any]] = {}

    def get(k: LeagueKey) -> dict[str, Any]:
        if k not in local:
            local[k] = _empty_league_bucket()
        return local[k]

    for row in rows:
        fr = process_one(row)
        k: LeagueKey = (
            fr["league_id"],
            fr["league_name"],
            fr["league_tier"],
            fr["league_country"],
        )
        e = get(k)
        e["n_fixtures"] += 1
        if fr["value_pool"]:
            e["n_value_pool"] += 1
        else:
            e["n_not_usable"] += 1
            r = fr["reason"]
            if r == "vp_false_dcs0_agregado_sin_consenso_util":
                e["n_vp_false_dcs0"] += 1
            elif r == "sin_lineas_canonicas_pre_t60":
                e["n_sin_lineas_pre"] += 1
            elif r == "lineas_canonicas_filtradas_t60_cero_restantes":
                e["n_t60_zero"] += 1
            elif r == "todas_lineas_sin_ts_o_ts_post_t60":
                e["n_todas_sin_ts"] += 1
            elif r == "vp_false_sin_ft1x2_en_cobertura_mercados":
                e["n_vp_false_sin_ft1x2"] += 1
            elif r.startswith("vp_false_con_ft1x2"):
                e["n_vp_false_ft1x2_other"] += 1
        e["n_lines_before"] += fr["n_lines_before"]
        e["n_lines_t60"] += fr["n_lines_t60"]
    return local


def merge_league_maps(
    parts: list[dict[LeagueKey, dict[str, Any]]],
) -> dict[LeagueKey, dict[str, Any]]:
    out: dict[LeagueKey, dict[str, Any]] = {}
    for p in parts:
        for k, e in p.items():
            if k not in out:
                out[k] = _empty_league_bucket()
            o = out[k]
            for fld in e:
                o[fld] += e[fld]
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parts: list[dict[LeagueKey, dict[str, Any]]] = []
    for m in range(1, 6):
        month_rows = fetch_month(2025, m)
        parts.append(process_chunk(month_rows))
    agg = merge_league_maps(parts)

    total_nu = sum(e["n_not_usable"] for e in agg.values())
    total_fx = sum(e["n_fixtures"] for e in agg.values())
    total_vp = sum(e["n_value_pool"] for e in agg.values())
    totals_reason = {
        "n_vp_false_dcs0": sum(e["n_vp_false_dcs0"] for e in agg.values()),
        "n_sin_lineas_canonicas_pre_t60": sum(e["n_sin_lineas_pre"] for e in agg.values()),
        "n_lineas_filtradas_t60_solo": sum(e["n_t60_zero"] for e in agg.values()),
        "n_todas_lineas_sin_ts_o_post_t60": sum(e["n_todas_sin_ts"] for e in agg.values()),
        "n_vp_false_sin_ft1x2": sum(e["n_vp_false_sin_ft1x2"] for e in agg.values()),
        "n_vp_false_ft1x2_otros": sum(e["n_vp_false_ft1x2_other"] for e in agg.values()),
    }
    tr = totals_reason
    totals_reason["checksum_not_usable_sum"] = (
        tr["n_vp_false_dcs0"]
        + tr["n_sin_lineas_canonicas_pre_t60"]
        + tr["n_lineas_filtradas_t60_solo"]
        + tr["n_todas_lineas_sin_ts_o_post_t60"]
        + tr["n_vp_false_sin_ft1x2"]
        + tr["n_vp_false_ft1x2_otros"]
    )
    totals_reason["share_of_not_usable_vp_false_dcs0"] = (
        round(tr["n_vp_false_dcs0"] / total_nu, 6) if total_nu else 0.0
    )
    totals_reason["share_of_not_usable_sin_lineas_pre"] = (
        round(tr["n_sin_lineas_canonicas_pre_t60"] / total_nu, 6) if total_nu else 0.0
    )

    rows_out: list[dict[str, Any]] = []
    below_nu = 0
    below_fx = 0
    eligible_nu = 0
    eligible_fx = 0

    for k, e in agg.items():
        lid, lname, ltier, lcountry = k
        nf = e["n_fixtures"]
        nu = e["n_not_usable"]
        if nf < MIN_FIXTURES_THRESHOLD:
            below_fx += nf
            below_nu += nu
            continue
        eligible_fx += nf
        eligible_nu += nu
        lb = e["n_lines_before"]
        lt = e["n_lines_t60"]
        rows_out.append(
            {
                "league_id": lid,
                "league_name": lname,
                "league_tier": ltier,
                "league_country": lcountry,
                "n_fixtures": nf,
                "n_value_pool": e["n_value_pool"],
                "n_not_usable": nu,
                "not_usable_rate": round(nu / nf, 6) if nf else 0.0,
                "vp_over_n_fixtures": round(e["n_value_pool"] / nf, 6) if nf else 0.0,
                "n_vp_false_dcs0": e["n_vp_false_dcs0"],
                "n_sin_lineas_canonicas_pre_t60": e["n_sin_lineas_pre"],
                "n_lineas_canonicas_filtradas_t60_cero": e["n_t60_zero"] + e["n_todas_sin_ts"],
                "n_todas_lineas_sin_ts_o_post_t60": e["n_todas_sin_ts"],
                "n_lineas_filtradas_t60_solo": e["n_t60_zero"],
                "n_vp_false_sin_ft1x2": e["n_vp_false_sin_ft1x2"],
                "n_vp_false_ft1x2_otros": e["n_vp_false_ft1x2_other"],
                "lines_survival_proxy": round(lt / lb, 6) if lb else None,
                "n_lines_before_sum": lb,
                "n_lines_t60_sum": lt,
            }
        )

    rows_out.sort(key=lambda x: (-x["n_not_usable"], -x["n_fixtures"]))

    def cum_share_top_k(k: int) -> float:
        s = sum(r["n_not_usable"] for r in rows_out[:k])
        return round(s / total_nu, 6) if total_nu else 0.0

    shares = [r["n_not_usable"] / total_nu for r in rows_out if total_nu]
    hhi = round(sum(s * s for s in shares), 6) if shares else 0.0

    top1_share = cum_share_top_k(1)
    top3_share = cum_share_top_k(3)
    top5_share = cum_share_top_k(5)
    top10_share = cum_share_top_k(10)

    nu_below_share = round(below_nu / total_nu, 6) if total_nu else 0.0

    concentration_label = (
        "concentrada_en_pocos_outliers"
        if top3_share >= 0.35 or top1_share >= 0.15
        else "distribuida_mas_homogeneamente"
    )

    summary = {
        "cohorte": "A_2025_stable_high_survival",
        "kickoff_utc_range": {"from": str(DAY0), "to": str(DAY1)},
        "processing": {"strategy": "by_calendar_month_2025_01_to_05", "n_month_queries": 5},
        "min_fixtures_threshold": MIN_FIXTURES_THRESHOLD,
        "min_fixtures_rationale": (
            "Excluir ligas con menos fixtures reduce ruido estadístico en tasas; "
            f"{MIN_FIXTURES_THRESHOLD} es ~orden de magnitud de una semana concurrida o fracción pequeña del total mensual en A."
        ),
        "totals_all_leagues": {
            "n_fixtures": total_fx,
            "n_value_pool": total_vp,
            "n_not_usable": total_nu,
            "not_usable_rate": round(total_nu / total_fx, 6) if total_fx else 0,
        },
        "totals_not_usable_by_observable_reason": totals_reason,
        "below_threshold_mass": {
            "n_leagues_bucket": sum(1 for k, e in agg.items() if e["n_fixtures"] < MIN_FIXTURES_THRESHOLD),
            "n_fixtures": below_fx,
            "n_not_usable": below_nu,
            "share_of_total_not_usable": nu_below_share,
        },
        "eligible_leagues_count": len(rows_out),
        "concentration_of_not_usable_among_eligible": {
            "top1_cumulative_share": top1_share,
            "top3_cumulative_share": top3_share,
            "top5_cumulative_share": top5_share,
            "top10_cumulative_share": top10_share,
            "herfindahl_on_not_usable_shares_eligible": hhi,
            "label": concentration_label,
        },
        "top_outliers_by_n_not_usable": rows_out[:12],
    }

    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    if rows_out:
        fn = list(rows_out[0].keys())
        with (OUT_DIR / "league_outliers_A.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            for r in rows_out:
                w.writerow(r)

    (OUT_DIR / "README.md").write_text(
        f"""# Panel por liga — cohorte A

## Regenerar

```bash
cd {_repo}
python3 scripts/bt2_historical_sm_lbu_cohort_A_league_panel.py
```

## Umbral

Solo ligas con `n_fixtures >= {MIN_FIXTURES_THRESHOLD}` en `league_outliers_A.csv`. El resto en `summary.json` → `below_threshold_mass`.

## Contrato

Mismo `historical_sm_lbu` + T-60 que `bt2_historical_sm_lbu_replay_prototype.py`.
""",
        encoding="utf-8",
    )

    print(json.dumps({"ok": True, "out": str(OUT_DIR.relative_to(_repo))}, indent=2))


if __name__ == "__main__":
    main()

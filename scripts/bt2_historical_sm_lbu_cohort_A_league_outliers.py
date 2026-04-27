#!/usr/bin/env python3
"""
Fase 3C — panel por liga en toda la cohorte A (2025-01..2025-05).

Misma agregación T-60 y mismos `observable_reason` que
`bt2_historical_sm_lbu_cohort_A_drilldown.py` / prototipo.
Solo lectura; no modifica T-60 ni bounded replay.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2.extras

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from apps.api.bt2_settings import bt2_settings

DAY_FROM = date(2025, 1, 1)
DAY_TO = date(2025, 5, 31)
DEFAULT_MIN_FIXTURES = 100
MAX_FX = 2_000_000
OUT_DIR = _repo / "scripts" / "outputs" / "bt2_historical_sm_lbu_cohort_A_league_outliers"

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


def fetch_fixtures_cohort_a() -> list[dict[str, Any]]:
    start = datetime.combine(DAY_FROM, time.min, tzinfo=timezone.utc)
    end = datetime.combine(DAY_TO + timedelta(days=1), time.min, tzinfo=timezone.utc)
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


def process_fixture(row: dict[str, Any]) -> dict[str, Any]:
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
    reason = observable_reason(
        n_before=len(before),
        n_t60=len(t60),
        n_lbu_null=n_lbu_n,
        value_pool=bool(vp),
        dcs=int(dcs),
        mkeys=mkeys_s,
    )
    return {
        "fixture_id": int(row["fixture_id"]),
        "event_id": int(row["event_id"]),
        "kickoff_utc": ko.isoformat(),
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


LeagueKey = tuple[Any, str, str, str]


def league_key(fr: dict[str, Any]) -> LeagueKey:
    return (
        fr["league_id"],
        fr["league_name"] or "(sin_nombre_liga)",
        fr["league_tier"] or "unknown",
        fr["league_country"] or "",
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--min-fixtures",
        type=int,
        default=DEFAULT_MIN_FIXTURES,
        help=f"Mínimo n_fixtures por liga para incluir en panel y concentración (default {DEFAULT_MIN_FIXTURES})",
    )
    p.add_argument(
        "--out-dir",
        type=str,
        default=str(OUT_DIR),
        help="Directorio de salida",
    )
    args = p.parse_args()
    min_f = max(1, int(args.min_fixtures))
    out_dir = Path(str(args.out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_rows = fetch_fixtures_cohort_a()
    fixtures: list[dict[str, Any]] = []
    for row in raw_rows:
        fixtures.append(process_fixture(row))

    # Por liga: contadores
    by_league: dict[LeagueKey, dict[str, Any]] = {}
    for fr in fixtures:
        k = league_key(fr)
        if k not in by_league:
            by_league[k] = {
                "league_id": k[0],
                "league_name": k[1],
                "league_tier": k[2],
                "league_country": k[3],
                "n_fixtures": 0,
                "n_value_pool": 0,
                "n_not_usable": 0,
                "n_lines_before": 0,
                "n_lines_t60": 0,
                "vp_false_dcs0": 0,
                "sin_lineas_canonicas_pre_t60": 0,
                "lineas_canonicas_filtradas_t60_cero_restantes": 0,
                "todas_lineas_sin_ts_o_ts_post_t60": 0,
                "vp_false_sin_ft1x2": 0,
                "vp_false_otros": 0,
                "value_pool_true": 0,
            }
        e = by_league[k]
        e["n_fixtures"] += 1
        if fr["value_pool"]:
            e["n_value_pool"] += 1
            if fr["observable_reason"] == "value_pool_true":
                e["value_pool_true"] += 1
        else:
            e["n_not_usable"] += 1
            r = fr["observable_reason"]
            if r == "vp_false_dcs0_agregado_sin_consenso_util":
                e["vp_false_dcs0"] += 1
            elif r == "sin_lineas_canonicas_pre_t60":
                e["sin_lineas_canonicas_pre_t60"] += 1
            elif r == "lineas_canonicas_filtradas_t60_cero_restantes":
                e["lineas_canonicas_filtradas_t60_cero_restantes"] += 1
            elif r == "todas_lineas_sin_ts_o_ts_post_t60":
                e["todas_lineas_sin_ts_o_ts_post_t60"] += 1
            elif r == "vp_false_sin_ft1x2_en_cobertura_mercados":
                e["vp_false_sin_ft1x2"] += 1
            else:
                e["vp_false_otros"] += 1
        e["n_lines_before"] += int(fr["n_lines_before_filter"])
        e["n_lines_t60"] += int(fr["n_lines_t60"])

    rows_out: list[dict[str, Any]] = []
    for e in by_league.values():
        nf = int(e["n_fixtures"])
        nu = int(e["n_not_usable"])
        nb = int(e["n_lines_before"])
        nt = int(e["n_lines_t60"])
        rows_out.append(
            {
                **e,
                "not_usable_rate": round(nu / nf, 6) if nf else 0.0,
                "lines_survival_proxy": round(nt / nb, 6) if nb else None,
                "meets_min_volume": nf >= min_f,
            }
        )

    rows_out.sort(key=lambda x: (-x["n_not_usable"], -x["n_fixtures"]))

    filtered = [r for r in rows_out if r["meets_min_volume"]]
    total_nu = sum(int(r["n_not_usable"]) for r in filtered)
    total_fx = sum(int(r["n_fixtures"]) for r in filtered)

    def cum_share_top_k(k: int) -> Optional[float]:
        if total_nu <= 0:
            return None
        top = sorted(filtered, key=lambda x: -int(x["n_not_usable"]))[:k]
        s = sum(int(x["n_not_usable"]) for x in top)
        return round(s / total_nu, 6)

    # Herfindahl sobre participación en not_usable (ligas filtradas)
    hhi: Optional[float] = None
    if total_nu > 0 and filtered:
        shares = [int(r["n_not_usable"]) / total_nu for r in filtered]
        hhi = round(sum(s * s for s in shares), 6)

    # Veredicto heurístico documentado
    c5 = cum_share_top_k(5) or 0.0
    c10 = cum_share_top_k(10) or 0.0
    if total_nu == 0:
        concentration_verdict = "sin_no_usable_en_panel_filtrado"
    elif c5 >= 0.45:
        concentration_verdict = "concentrada_top5_explica_mayor_parte"
    elif c10 >= 0.65:
        concentration_verdict = "moderada_top10_dominante_resto_disperso"
    else:
        concentration_verdict = "distribuida_muchas_ligas_contribuyen"

    summary = {
        "cohort_key": "A_2025_stable_high_survival",
        "kickoff_window_utc": {"from": str(DAY_FROM), "to": str(DAY_TO)},
        "mode": _proto.MODE,
        "cutoff_mode": _proto.CUTOFF_MODE,
        "min_decimal": MIN_DEC,
        "min_fixtures_per_league_for_panel": min_f,
        "rationale_min_volume": (
            "Excluye ligas con pocas observaciones donde la tasa not_usable es ruidosa; "
            f"umbral por defecto {DEFAULT_MIN_FIXTURES} fixtures en la ventana."
        ),
        "counts": {
            "n_fixtures_processed": len(fixtures),
            "n_leagues_all": len(rows_out),
            "n_leagues_meeting_min_volume": len(filtered),
            "n_not_usable_total_cohort": sum(int(r["n_not_usable"]) for r in rows_out),
            "n_not_usable_in_filtered_leagues": total_nu,
            "n_fixtures_in_filtered_leagues": total_fx,
        },
        "concentration_among_filtered_leagues": {
            "cum_share_not_usable_top1": cum_share_top_k(1),
            "cum_share_not_usable_top3": cum_share_top_k(3),
            "cum_share_not_usable_top5": cum_share_top_k(5),
            "cum_share_not_usable_top10": cum_share_top_k(10),
            "herfindahl_not_usable_shares": hhi,
            "verdict": concentration_verdict,
            "rule_of_thumb": (
                "Si cum_share_top5 >= 0.45 -> concentrada; "
                "si no pero top10 >= 0.65 -> moderada; si no -> más distribuida."
            ),
        },
        "top_leagues_by_n_not_usable_filtered": filtered[:15],
    }

    csv_path = out_dir / "league_outliers_A.csv"
    fieldnames = [
        "league_id",
        "league_name",
        "league_tier",
        "league_country",
        "n_fixtures",
        "n_value_pool",
        "n_not_usable",
        "not_usable_rate",
        "vp_false_dcs0",
        "sin_lineas_canonicas_pre_t60",
        "lineas_canonicas_filtradas_t60_cero_restantes",
        "todas_lineas_sin_ts_o_ts_post_t60",
        "vp_false_sin_ft1x2",
        "vp_false_otros",
        "n_lines_before",
        "n_lines_t60",
        "lines_survival_proxy",
        "meets_min_volume",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows_out:
            row = {k: r.get(k) for k in fieldnames}
            w.writerow(row)

    json_path = out_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    readme = out_dir / "README.md"
    readme.write_text(
        f"""# Liga outliers — cohorte A (3C)

Ventana kickoff UTC: `{DAY_FROM}` .. `{DAY_TO}` (misma cohorte A que robustez/drill-down).

## Regenerar

```bash
cd {_repo}
python3 scripts/bt2_historical_sm_lbu_cohort_A_league_outliers.py
# umbral explícito:
python3 scripts/bt2_historical_sm_lbu_cohort_A_league_outliers.py --min-fixtures 100
```

## Salidas

- `league_outliers_A.csv` — todas las ligas; columna `meets_min_volume` según `--min-fixtures` (default {DEFAULT_MIN_FIXTURES}).
- `summary.json` — concentración de `n_not_usable` entre ligas que pasan el umbral.

T-60 y agregación: mismas que `bt2_historical_sm_lbu_replay_prototype.py`.
""",
        encoding="utf-8",
    )

    print(json.dumps(summary["counts"], indent=2))
    print("concentration:", summary["concentration_among_filtered_leagues"]["verdict"])
    print("wrote", csv_path)
    print("wrote", json_path)


if __name__ == "__main__":
    main()

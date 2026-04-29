#!/usr/bin/env python3
"""
Puerta DSR-ready shadow-native vs embudo legacy (bt2_odds_snapshot T-60).

- No escribe en tablas shadow salvo --persist-shadow-run (opcional, desactivado por defecto).
- Genera artefactos en scripts/outputs/bt2_shadow_dsr_replay/.
- Prueba controlada: muestra fija 32 (dsr_pilot_sample.csv) + comparación universo.

Uso:
  PYTHONPATH=. python3 scripts/bt2_shadow_native_dsr_pilot.py
  PYTHONPATH=. python3 scripts/bt2_shadow_native_dsr_pilot.py --call-deepseek
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_admin_backtest_replay import BLIND_LOT_OPERATING_DAY_KEY, blind_ds_input_item  # noqa: E402
from apps.api.bt2_dsr_deepseek import deepseek_suggest_batch_with_trace  # noqa: E402
from apps.api.bt2_dsr_ds_input_builder import (  # noqa: E402
    aggregated_odds_for_event_psycopg,
    fetch_event_odds_rows_for_aggregation,
)
from apps.api.bt2_dsr_shadow_native_enrichment import apply_shadow_native_enriched_context  # noqa: E402
from apps.api.bt2_dsr_odds_aggregation import AggregatedOdds, event_passes_value_pool  # noqa: E402
from apps.api.bt2_dsr_postprocess import postprocess_dsr_pick  # noqa: E402
from apps.api.bt2_dsr_shadow_native_adapter import (  # noqa: E402
    aggregated_odds_from_toa_shadow_payload,
    build_ds_input_shadow_native,
    extract_toa_data_from_shadow_raw_payload,
    merge_pick_inputs_odds_blob,
    shadow_native_passes_value_pool,
    toa_bookmakers_to_aggregate_rows,
)
from apps.api.bt2_dsr_contract import CONTRACT_VERSION_PUBLIC  # noqa: E402
from apps.api.bt2_settings import bt2_settings  # noqa: E402
from apps.api.bt2_value_pool import MIN_ODDS_DECIMAL_DEFAULT  # noqa: E402

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
SUBSET5_SPORTMONKS = {8, 82, 301, 384, 564}
FROZEN_RUN_KEYS: tuple[str, ...] = (
    "shadow-subset5-backfill-2025-01-05",
    "shadow-subset5-recovery-2025-07-12",
    "shadow-subset5-backfill-2026-01",
    "shadow-subset5-backfill-2026-02",
    "shadow-subset5-backfill-2026-03",
    "shadow-subset5-backfill-2026-04",
)
FIXED_SAMPLE = OUT_DIR / "dsr_pilot_sample.csv"
MODEL = "deepseek-v4-pro"


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _fetch_universe(cur: Any) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            dp.id AS shadow_pick_id,
            sr.run_key AS source_run_key,
            dp.operating_day_key,
            dp.bt2_event_id,
            dp.sm_fixture_id,
            dp.league_id,
            dp.provider_snapshot_id,
            COALESCE(l.sportmonks_id, 0) AS sm_league_id,
            COALESCE(l.name, '') AS league_name,
            l.country AS league_country,
            l.tier AS league_tier
        FROM bt2_shadow_daily_picks dp
        INNER JOIN bt2_shadow_runs sr ON sr.id = dp.run_id
        LEFT JOIN bt2_leagues l ON l.id = dp.league_id
        WHERE (
            sr.run_key = ANY(%s)
            OR sr.run_key LIKE 'shadow-daily-%%'
        )
          AND dp.classification_taxonomy = 'matched_with_odds_t60'
          AND COALESCE(l.sportmonks_id, 0) = ANY(%s)
        ORDER BY dp.operating_day_key ASC, dp.id ASC
        """,
        (list(FROZEN_RUN_KEYS), list(SUBSET5_SPORTMONKS)),
    )
    return [dict(r) for r in (cur.fetchall() or [])]


def _load_event_row(cur: Any, event_id: int) -> Optional[dict[str, Any]]:
    cur.execute(
        """
        SELECT
            e.id,
            e.kickoff_utc,
            e.status,
            COALESCE(th.name, '') AS home_team_name,
            COALESCE(ta.name, '') AS away_team_name,
            e.home_team_id,
            e.away_team_id,
            e.sportmonks_fixture_id
        FROM bt2_events e
        LEFT JOIN bt2_teams th ON th.id = e.home_team_id
        LEFT JOIN bt2_teams ta ON ta.id = e.away_team_id
        WHERE e.id = %s
        """,
        (event_id,),
    )
    r = cur.fetchone()
    return dict(r) if r else None


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
        SELECT id, raw_payload, provider_snapshot_time, market, region, provider_source
        FROM bt2_shadow_provider_snapshots
        WHERE id = %s
        """,
        (snapshot_id,),
    )
    r = cur.fetchone()
    return dict(r) if r else None


def _legacy_exclusion(
    cur: Any,
    r: dict[str, Any],
) -> tuple[str, Optional[datetime]]:
    """Misma lógica que bt2_shadow_dsr_gap_radiography (embudo local CDM)."""
    eid = r.get("bt2_event_id")
    if not eid:
        return "missing_bt2_event_id", None
    ev = _load_event_row(cur, int(eid))
    if not ev:
        return "event_not_found_in_cdm", None
    ko = ev.get("kickoff_utc")
    if not isinstance(ko, datetime):
        return "missing_kickoff_utc", None
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    cutoff = ko - timedelta(minutes=60)
    agg, _ = aggregated_odds_for_event_psycopg(
        cur,
        int(eid),
        min_decimal=MIN_ODDS_DECIMAL_DEFAULT,
        odds_cutoff_utc=cutoff,
        skip_sfs_fusion=True,
    )

    raw_rows = fetch_event_odds_rows_for_aggregation(cur, int(eid), max_fetched_at=cutoff)
    if len(raw_rows) == 0:
        return "no_local_snapshot_before_t60", ko
    markets_available = sorted(list(agg.markets_available or []))
    if len(markets_available) == 0:
        return "canonicalization_yielded_no_market", ko
    if not event_passes_value_pool(agg, min_decimal=MIN_ODDS_DECIMAL_DEFAULT):
        return "value_pool_failed_no_complete_market_family", ko
    return "eligible_legacy_local", ko


def _shadow_native_exclusion(
    cur: Any,
    r: dict[str, Any],
    payload_json: Optional[dict[str, Any]],
) -> tuple[str, Optional[AggregatedOdds], dict[str, Any]]:
    if not r.get("sm_fixture_id"):
        return "missing_sm_fixture_id", None, {}
    if not r.get("provider_snapshot_id"):
        return "missing_provider_snapshot_id", None, {}
    sn = _load_snapshot(cur, int(r["provider_snapshot_id"]))
    if not sn:
        return "provider_snapshot_not_found", None, {}

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
        return "missing_toa_h2h_bookmakers_in_snapshot", None, meta

    if not shadow_native_passes_value_pool(agg, min_decimal=MIN_ODDS_DECIMAL_DEFAULT):
        return "shadow_native_value_pool_failed", agg, meta

    return "eligible_shadow_native", agg, meta


def _resolve_context(
    cur: Any,
    r: dict[str, Any],
    meta: dict[str, Any],
) -> tuple[str, str, str, Optional[datetime], str]:
    """Equipos, liga, kickoff: TOA primero; refuerzo CDM si hay bt2_event_id."""
    league = str(r.get("league_name") or "unknown")
    country = r.get("league_country")
    tier = str(r.get("league_tier") or "") or None
    home = str(meta.get("toa_home_team") or "").strip()
    away = str(meta.get("toa_away_team") or "").strip()
    ko: Optional[datetime] = None
    ct = meta.get("toa_commence_time")
    if isinstance(ct, str) and ct.strip():
        try:
            s = ct.strip().replace("Z", "+00:00")
            ko = datetime.fromisoformat(s)
            if ko.tzinfo is None:
                ko = ko.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            ko = None
    status = "scheduled"
    eid = r.get("bt2_event_id")
    if eid:
        ev = _load_event_row(cur, int(eid))
        if ev:
            if not home:
                home = str(ev.get("home_team_name") or "")
            if not away:
                away = str(ev.get("away_team_name") or "")
            if ko is None and isinstance(ev.get("kickoff_utc"), datetime):
                ko = ev["kickoff_utc"]
                if ko.tzinfo is None:
                    ko = ko.replace(tzinfo=timezone.utc)
            status = str(ev.get("status") or "scheduled")
    return league, home, away, ko, status


def _write_contract_md(path: Path) -> None:
    body = """# DSR-ready shadow-native — contrato operativo

## Qué cuenta como elegible (DSR-ready shadow-native)

Una fila `bt2_shadow_daily_picks` entra si **simultáneamente**:

1. **Taxonomía shadow auditada**: `classification_taxonomy = matched_with_odds_t60` (mismo universo que el pipeline shadow actual).
2. **Fixture SM**: `sm_fixture_id` no nulo (partido identificado en SportMonks).
3. **Cadena TOA persistida**: `provider_snapshot_id` apunta a `bt2_shadow_provider_snapshots` con mercado `h2h` y región `us` (sin cambiar subset ni proveedor).
4. **Cuotas TOA parseables**: desde `raw_payload` (típicamente `payload_summary` con JSON tipo API TOA histórica) se extraen `data.bookmakers[*].markets[h2h].outcomes`.
5. **Agregación + pool valor**: las filas normalizadas `(bookmaker, match winner, selección, decimal, fetched_at)` pasan por `aggregate_odds_for_event` y `event_passes_value_pool` con el mismo `MIN_ODDS_DECIMAL_DEFAULT` que el DSR CDM (≥ 1.30 y familia canónica completa).

## Qué **no** es requisito (dejó de gobernar la puerta)

- `bt2_event_id` CDM (puede ser NULL en datos shadow).
- Filas en `bt2_odds_snapshot` locales antes de T-60.
- `aggregated_odds_for_event_psycopg` sobre CDM.

## Qué entra y qué no (defendible)

| Situación | Entra a DSR-ready shadow-native |
|-----------|----------------------------------|
| Taxonomía distinta de `matched_with_odds_t60` | No — fuera del universo shadow acordado |
| Sin `sm_fixture_id` | No |
| Sin snapshot TOA ligado | No |
| Snapshot sin bookmakers h2h parseables (ni fallback en `pick_inputs.odds_row.payload_summary`) | No |
| TOA agregado no cumple value pool canónico | No (`shadow_native_value_pool_failed`) |
| Cumple 1–5 | **Sí** |

## T-60

El corte temporal operativo del stack auditado es el **timestamp del snapshot TOA** ya seleccionado para la ventana T-60 en el carril shadow (no se redefine minutos). La agregación usa ese payload como universo de cuotas coherente con el experimento, no la tabla local `bt2_odds_snapshot`.

## Orientación 1X2 (TOA)

Los outcomes h2h de The Odds API usan **nombre del club**, no las etiquetas literales Home/Away. Antes de agregar, se proyectan a las piernas canónicas comparando contra `data.home_team` / `data.away_team` del payload (misma convención que el picker tras blindaje de calendario).

## Identidad en el lote DSR

`event_id` en `ds_input` = `shadow_daily_pick.id` (correlación estable sin depender del CDM).
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_adapter_md(path: Path) -> None:
    body = """# Adapter shadow → DSR input (`bt2_dsr_shadow_native_adapter`)

## Usa

- `bt2_shadow_provider_snapshots.raw_payload`: JSON TOA (directo o dentro de `payload_summary`).
- `bt2_shadow_pick_inputs.payload_json` (opcional): `odds_row.payload_summary` si el snapshot no trae el árbol de bookmakers.
- `bt2_leagues` vía la fila pick (`league_id`) para nombre/tier/país.
- Equipos y `commence_time` preferentes desde el payload TOA (`data.home_team`, `data.away_team`, `data.commence_time`).
- Refuerzo opcional desde `bt2_events` **solo si** existe `bt2_event_id` (equipos/kickoff/status cuando faltan en TOA).

## No usa (para existir el input mínimo)

- `bt2_odds_snapshot` / `aggregated_odds_for_event_psycopg` como fuente de cuotas.
- `apply_postgres_context_to_ds_item` **no es obligatorio**: el piloto construye `ds_input` con odds TOA agregadas; el enriquecimiento CDM/SM profundo es opcional si hay evento.

## Funciones

- `extract_toa_data_from_shadow_raw_payload`
- `toa_bookmakers_to_aggregate_rows` (orientación equipo local/visitante vs payload TOA)
- `aggregated_odds_from_toa_shadow_payload` → `AggregatedOdds`
- `build_ds_input_shadow_native` → dict compatible con `build_ds_input_item` / contrato DSR

## Enriquecimiento opcional

Si hay `bt2_event_id`, el piloto puede llamar `apply_postgres_context_to_ds_item` para stats/H2H CDM; **no** condiciona la elegibilidad shadow-native.
"""
    path.write_text(body, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--call-deepseek", action="store_true", help="Un lote DSR sobre la muestra elegible shadow-native")
    ap.add_argument(
        "--fixed-sample-csv",
        type=str,
        default=str(FIXED_SAMPLE),
        help="CSV de 32 filas (columna shadow_pick_id)",
    )
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fixed_path = Path(args.fixed_sample_csv)
    if not fixed_path.is_file():
        raise SystemExit(f"No existe muestra fija: {fixed_path}")

    _write_contract_md(OUT_DIR / "shadow_native_dsr_ready_contract.md")
    _write_adapter_md(OUT_DIR / "shadow_native_dsr_input_adapter.md")

    conn = psycopg2.connect(_dsn(), connect_timeout=25)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        universe = _fetch_universe(cur)
        rows_csv: list[dict[str, Any]] = []
        leg_c = Counter()
        sn_c = Counter()

        for r in universe:
            spid = int(r["shadow_pick_id"])
            pj = _load_pick_inputs(cur, spid)
            leg, _ko = _legacy_exclusion(cur, r)
            sn_ex, _agg_sn, _meta = _shadow_native_exclusion(cur, r, pj)
            leg_c[leg] += 1
            sn_c[sn_ex] += 1
            rows_csv.append(
                {
                    "shadow_pick_id": spid,
                    "source_run_key": str(r.get("source_run_key") or ""),
                    "operating_day_key": str(r.get("operating_day_key") or ""),
                    "bt2_event_id": int(r["bt2_event_id"]) if r.get("bt2_event_id") else "",
                    "sm_fixture_id": int(r["sm_fixture_id"]) if r.get("sm_fixture_id") else "",
                    "sm_league_id": int(r["sm_league_id"]) if r.get("sm_league_id") is not None else "",
                    "league_name": str(r.get("league_name") or ""),
                    "legacy_exclusion": leg,
                    "shadow_native_exclusion": sn_ex,
                    "legacy_eligible": leg == "eligible_legacy_local",
                    "shadow_native_eligible": sn_ex == "eligible_shadow_native",
                }
            )

        gap_path = OUT_DIR / "shadow_native_dsr_ready_gap_comparison.csv"
        with gap_path.open("w", encoding="utf-8", newline="") as f:
            fn = list(rows_csv[0].keys()) if rows_csv else []
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            for row in rows_csv:
                w.writerow(row)

        # Pilot sample
        sample_ids: list[int] = []
        with fixed_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("shadow_pick_id") or row.get("source_shadow_pick_id")
                if pid and str(pid).isdigit():
                    sample_ids.append(int(pid))

        sample_rows = [r for r in universe if int(r["shadow_pick_id"]) in sample_ids]
        pilot_legacy_eligible = 0
        pilot_sn_eligible = 0
        pilot_sn_missing_payload = 0
        for r in sample_rows:
            pj = _load_pick_inputs(cur, int(r["shadow_pick_id"]))
            leg, _ = _legacy_exclusion(cur, r)
            sn_ex, _, _ = _shadow_native_exclusion(cur, r, pj)
            if leg == "eligible_legacy_local":
                pilot_legacy_eligible += 1
            if sn_ex == "eligible_shadow_native":
                pilot_sn_eligible += 1
            if sn_ex == "missing_toa_h2h_bookmakers_in_snapshot":
                pilot_sn_missing_payload += 1

        deepseek_ok = 0
        deepseek_any = 0

        if args.call_deepseek:
            dkey = (bt2_settings.deepseek_api_key or "").strip()
            if not dkey:
                raise SystemExit("Falta DEEPSEEK_API_KEY / deepseek_api_key para --call-deepseek")
            prepared_blinds: list[dict[str, Any]] = []
            items_by_id: dict[int, dict[str, Any]] = {}
            for r in sample_rows:
                pj = _load_pick_inputs(cur, int(r["shadow_pick_id"]))
                sn_ex, agg, meta = _shadow_native_exclusion(cur, r, pj)
                if sn_ex != "eligible_shadow_native" or agg is None:
                    continue
                league, home, away, ko, status = _resolve_context(cur, r, meta)
                spid = int(r["shadow_pick_id"])
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
                items_by_id[spid] = item

            if prepared_blinds:
                ds_map, _trace = deepseek_suggest_batch_with_trace(
                    prepared_blinds,
                    operating_day_key=BLIND_LOT_OPERATING_DAY_KEY,
                    api_key=dkey,
                    base_url=str(bt2_settings.bt2_dsr_deepseek_base_url),
                    model=MODEL,
                    timeout_sec=int(bt2_settings.bt2_dsr_timeout_sec),
                    max_retries=int(bt2_settings.bt2_dsr_max_retries),
                )
                deepseek_any = len(prepared_blinds)
                for sid, item in items_by_id.items():
                    raw = ds_map.get(sid)
                    if raw is None:
                        continue
                    narrative, conf, mmc, msc, _dec = raw
                    if mmc in ("", "UNKNOWN") or msc in ("", "unknown_side"):
                        continue
                    r0 = next(x for x in sample_rows if int(x["shadow_pick_id"]) == sid)
                    pj = _load_pick_inputs(cur, sid)
                    _, agg, _ = _shadow_native_exclusion(cur, r0, pj)
                    if agg is None:
                        continue
                    ec = item.get("event_context") if isinstance(item.get("event_context"), dict) else {}
                    ppc = postprocess_dsr_pick(
                        narrative_es=narrative,
                        confidence_label=conf,
                        market_canonical=mmc,
                        selection_canonical=msc,
                        model_declared_odds=None,
                        consensus=agg.consensus,
                        market_coverage=agg.market_coverage,
                        event_id=sid,
                        home_team=str(ec.get("home_team") or ""),
                        away_team=str(ec.get("away_team") or ""),
                    )
                    if ppc and ppc[2] == "FT_1X2":
                        deepseek_ok += 1

        summary = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "universe_rows_matched_taxonomy": len(universe),
            "legacy_eligible_count": int(leg_c.get("eligible_legacy_local", 0)),
            "shadow_native_eligible_count": int(sn_c.get("eligible_shadow_native", 0)),
            "frozen_run_keys": list(FROZEN_RUN_KEYS),
            "subset5_sportmonks_ids": sorted(SUBSET5_SPORTMONKS),
            "legacy_by_exclusion": [{"cause": k, "count": v} for k, v in sorted(leg_c.items(), key=lambda x: -x[1])],
            "shadow_native_by_exclusion": [{"cause": k, "count": v} for k, v in sorted(sn_c.items(), key=lambda x: -x[1])],
            "pilot_sample": {
                "fixed_sample_csv": str(fixed_path.relative_to(ROOT))
                if str(fixed_path).startswith(str(ROOT))
                else str(fixed_path),
                "sample_pick_ids": sample_ids,
                "sample_rows_found": len(sample_rows),
                "legacy_eligible_in_sample": pilot_legacy_eligible,
                "shadow_native_eligible_in_sample": pilot_sn_eligible,
                "sample_missing_toa_payload_rows": pilot_sn_missing_payload,
            },
            "deepseek_probe": {
                "called": bool(args.call_deepseek),
                "batch_event_count": deepseek_any,
                "ft_1x2_postprocess_ok": deepseek_ok,
                "model": MODEL if args.call_deepseek else None,
                "contract_version": CONTRACT_VERSION_PUBLIC if args.call_deepseek else None,
            },
            "artifacts": {
                "gap_comparison_csv": str(gap_path.relative_to(ROOT)),
                "contract_md": "scripts/outputs/bt2_shadow_dsr_replay/shadow_native_dsr_ready_contract.md",
                "adapter_md": "scripts/outputs/bt2_shadow_dsr_replay/shadow_native_dsr_input_adapter.md",
            },
        }
        (OUT_DIR / "shadow_native_pilot_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    finally:
        cur.close()
        conn.close()

    print(json.dumps({"ok": True, "out": str(OUT_DIR)}, indent=2))


if __name__ == "__main__":
    main()

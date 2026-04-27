#!/usr/bin/env python3
"""
Preparación día 1 — piloto The Odds API (subset 5 ligas), sin llamadas HTTP.

- Base: vendor_validation_sample.csv (priority_pilot_now, subset5, h2h, us, T-60 del sample 3D).
- Complemento: si faltan ligas del subset5 en el sample, añade hasta 2 fixtures/liga
  desde bt2_events en cohorte A, mismo mapeo 3D + T-60 (lectura DB, sin HTTP).
Genera artefactos bajo scripts/outputs/bt2_vendor_pilot_prep/ con --generate.
Valida integridad y créditos estimados (modo por defecto). BT2_PILOT_TOPUP_OFFLINE=1 desactiva top-up.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

_repo = Path(__file__).resolve().parents[1]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))

from apps.api.bt2_settings import bt2_settings

VENDOR_SAMPLE = _repo / "scripts" / "outputs" / "bt2_vendor_readiness" / "vendor_validation_sample.csv"
PILOT_LEAGUE_MANIFEST = _repo / "scripts" / "outputs" / "bt2_vendor_readiness" / "pilot_league_manifest.json"
OUT_DIR = _repo / "scripts" / "outputs" / "bt2_vendor_pilot_prep"

SUBSET5_SM_LEAGUE_IDS: frozenset[int] = frozenset({8, 564, 82, 384, 301})
SUBSET5_NAMES: dict[int, str] = {
    8: "Premier League",
    564: "La Liga",
    82: "Bundesliga",
    384: "Serie A",
    301: "Ligue 1",
}

REGION_FROZEN = "us"
MARKET_FROZEN = "h2h"
BT2_MARKET = "FT_1X2"

# Alineado a laboratorio 3D / doc TOA v4 event odds histórico (h2h × 1 región).
CREDITS_PASO_A_PER_REQUEST_EST = 1
CREDITS_PASO_B_PER_FIXTURE_EST = 10
# Mínimo representativo extra si el vendor_validation_sample no trae liga 82/384 (u otra del subset5).
DB_TOPUP_FIXTURES_PER_LEAGUE = 2

PASO_A_ENDPOINT_TEMPLATE = (
    "GET https://api.the-odds-api.com/v4/historical/sports/{sport_key}/events"
    "?date={snapshot_time_iso_url_encoded}"
)
PASO_B_ENDPOINT_TEMPLATE = (
    "GET https://api.the-odds-api.com/v4/historical/sports/{sport_key}/events/"
    "{the_odds_api_event_id}/odds?markets=h2h&regions=us&date={snapshot_time_iso_url_encoded}"
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _iter_vendor_subset5_pilot_now() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with VENDOR_SAMPLE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("pilot_tier") != "priority_pilot_now":
                continue
            lid = int(row["sm_league_id"])
            if lid not in SUBSET5_SM_LEAGUE_IDS:
                continue
            if (row.get("the_odds_api_market") or "").strip().lower() != MARKET_FROZEN:
                continue
            if (row.get("the_odds_api_region") or "").strip().lower() != REGION_FROZEN:
                continue
            rows.append(row)
    return rows


def _validate_pilot_manifest_json() -> list[str]:
    warnings: list[str] = []
    data = _load_json(PILOT_LEAGUE_MANIFEST)
    operative = {int(x["sm_league_id"]) for x in data.get("leagues_operative_pilot_in", [])}
    for lid in sorted(SUBSET5_SM_LEAGUE_IDS):
        if lid not in operative:
            warnings.append(f"pilot_league_manifest: sm_league_id {lid} no listado en leagues_operative_pilot_in")
    return warnings


def _import_vendor_readiness_phase3d() -> Any:
    p = _repo / "scripts" / "bt2_vendor_readiness_phase3d.py"
    spec = importlib.util.spec_from_file_location("bt2_vr3d", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _import_hist_proto() -> Any:
    p = _repo / "scripts" / "bt2_historical_sm_lbu_replay_prototype.py"
    spec = importlib.util.spec_from_file_location("bt2_hist_proto", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules["bt2_hist_proto"] = mod
    spec.loader.exec_module(mod)
    return mod


def _db_dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith(
        "postgresql+asyncpg://"
    ) else u


def _db_topup_laboratorio_rows(
    base_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    """
    Completa representatividad: cohorte A (mismas fechas que 3D), T-60 = cutoff_t60(kickoff),
    solo priority_pilot_now + the_odds_api_sport_key_expected con mapping_status mapped_expected.
    """
    notes: list[str] = []
    err: list[str] = []
    if os.environ.get("BT2_PILOT_TOPUP_OFFLINE", "").strip().lower() in ("1", "true", "yes"):
        notes.append("topup: omitido (BT2_PILOT_TOPUP_OFFLINE=1)")
        return [], notes, err

    present: set[int] = set()
    seen_fixtures: set[str] = {str(r.get("fixture_id", "")) for r in base_rows}
    for r in base_rows:
        try:
            present.add(int(r["sm_league_id"]))
        except (TypeError, ValueError):
            continue

    missing: list[int] = [lid for lid in sorted(SUBSET5_SM_LEAGUE_IDS) if lid not in present]
    if not missing:
        return [], ["topup: no requerido (5 ligas ya en vendor sample)"], err

    vr3d = _import_vendor_readiness_phase3d()
    hist = _import_hist_proto()
    cutoff = hist.cutoff_t60
    start = datetime.combine(vr3d.COHORT_A0, time.min, tzinfo=timezone.utc)
    end = datetime.combine(vr3d.COHORT_A1 + timedelta(days=1), time.min, tzinfo=timezone.utc)

    try:
        conn = psycopg2.connect(_db_dsn(), connect_timeout=12)
    except Exception as e:
        return [], [f"topup: conexion BT2 fallo ({e!r}); reintentar con BT2_DATABASE_URL"], [str(e)]

    out: list[dict[str, str]] = []
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        for lid in missing:
            n_need = DB_TOPUP_FIXTURES_PER_LEAGUE
            n_added = 0
            cur.execute(
                """
                SELECT e.id AS event_id, e.sportmonks_fixture_id AS fixture_id, e.kickoff_utc,
                       l.sportmonks_id AS sm_league_id, l.name AS league_name, l.tier AS league_tier,
                       l.country AS league_country
                FROM bt2_events e
                INNER JOIN bt2_leagues l ON l.id = e.league_id
                WHERE l.sportmonks_id = %s
                  AND e.kickoff_utc >= %s AND e.kickoff_utc < %s
                ORDER BY e.kickoff_utc
                """,
                (lid, start, end),
            )
            scanned = 0
            for row in cur:
                if n_added >= n_need:
                    break
                scanned += 1
                if str(int(row["fixture_id"])) in seen_fixtures:
                    continue
                ko: Optional[datetime] = row["kickoff_utc"]
                if ko and ko.tzinfo is None:
                    ko = ko.replace(tzinfo=timezone.utc)
                t_cut: Optional[datetime] = cutoff(ko) if ko else None
                t60 = t_cut.isoformat() if t_cut else ""
                lm = vr3d.resolve_league_mapping(
                    int(row["sm_league_id"]) if row.get("sm_league_id") is not None else None,
                    str(row.get("league_name") or ""),
                    str(row.get("league_country") or ""),
                    str(row.get("league_tier") or ""),
                )
                if lm.get("pilot_tier") != "priority_pilot_now":
                    continue
                if lm.get("mapping_status") != "mapped_expected":
                    continue
                sk = (lm.get("the_odds_api_sport_key_expected") or "").strip()
                if not sk:
                    continue
                n_added += 1
                fid = str(int(row["fixture_id"]))
                eid = str(int(row["event_id"]))
                seen_fixtures.add(fid)
                out.append(
                    {
                        "fixture_id": fid,
                        "event_id": eid,
                        "sm_league_id": str(lid),
                        "league_name": str(row.get("league_name") or ""),
                        "kickoff_utc": ko.isoformat() if ko else "",
                        "the_odds_api_sport_key_expected": sk,
                        "historical_query_timestamp_utc": t60,
                    }
                )
            if n_added < n_need:
                err.append(
                    f"sm_league_id {lid} ({SUBSET5_NAMES.get(lid, '?')}): solo {n_added}/{n_need} "
                    f"fixtures top-up mapeables priority_pilot_now+mapped_expected en cohorte A "
                    f"(filas inspeccionadas: {scanned or '0'})"
                )
            else:
                notes.append(
                    f"topup: {n_added} fixtures sm_league_id {lid} desde BT2 cohorte {vr3d.COHORT_A0}..{vr3d.COHORT_A1}"
                )
        cur.close()
    finally:
        conn.close()
    return out, notes, err


def generate_artifacts() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_warnings = _validate_pilot_manifest_json()
    base_rows = _iter_vendor_subset5_pilot_now()
    if not base_rows:
        raise SystemExit(
            "No hay filas que cumplan subset5 + priority_pilot_now + h2h + us en vendor_validation_sample.csv"
        )

    topup_rows, topup_notes, topup_errors = _db_topup_laboratorio_rows(base_rows)
    all_rows: list[dict[str, str]] = list(base_rows) + list(topup_rows)
    n_vendor = len(base_rows)
    n_topup = len(topup_rows)

    manifest_fn = OUT_DIR / "pilot_fixture_manifest.csv"
    fieldnames = [
        "sm_fixture_id",
        "bt2_event_id",
        "sm_league_id",
        "league_name",
        "kickoff_utc",
        "the_odds_api_sport_key_expected",
        "bt2_market",
        "market",
        "region",
        "snapshot_time_t60",
        "pilot_inclusion_reason",
    ]
    league_counts: dict[int, int] = defaultdict(int)
    usable_sk = 0
    out_rows: list[dict[str, str]] = []
    topup_fixture_ids = {str(r.get("fixture_id", "")) for r in topup_rows}
    for row in all_rows:
        lid = int(row["sm_league_id"])
        league_counts[lid] += 1
        sk = (row.get("the_odds_api_sport_key_expected") or "").strip()
        if sk:
            usable_sk += 1
        is_top = str(row.get("fixture_id", "")) in topup_fixture_ids
        if is_top:
            reason = (
                "db_topup_cohort_A_priority_pilot_now_mapped_expected_subset5_t60; "
                "h2h/us fijos; vendor_validation_sample 3D no aporta fixtures para esta liga (sample estratificado 180 max)"
            )
        else:
            reason = "frozen_vendor_validation_sample_cohort_A_priority_pilot_now_subset5_h2h_us_t60"
        out_rows.append(
            {
                "sm_fixture_id": row["fixture_id"],
                "bt2_event_id": row["event_id"],
                "sm_league_id": str(lid),
                "league_name": row.get("league_name") or "",
                "kickoff_utc": row.get("kickoff_utc") or "",
                "the_odds_api_sport_key_expected": sk,
                "bt2_market": BT2_MARKET,
                "market": MARKET_FROZEN,
                "region": REGION_FROZEN,
                "snapshot_time_t60": row.get("historical_query_timestamp_utc") or "",
                "pilot_inclusion_reason": reason,
            }
        )
    with manifest_fn.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

    # Paso A: una fila por (sport_key, snapshot_time_t60) único (misma ventana T-60 que el laboratorio).
    paso_a_keys: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in all_rows:
        sk = (row.get("the_odds_api_sport_key_expected") or "").strip()
        t60 = (row.get("historical_query_timestamp_utc") or "").strip()
        paso_a_keys[(sk, t60)].append(row["fixture_id"])

    plan_rows: list[dict[str, Any]] = []
    for (sk, t60), fids in sorted(paso_a_keys.items(), key=lambda x: (x[0][0], x[0][1])):
        rep = fids[0]
        plan_rows.append(
            {
                "sport_key": sk,
                "request_type": "paso_a_event_discovery",
                "endpoint_expected": PASO_A_ENDPOINT_TEMPLATE.format(
                    sport_key=sk,
                    snapshot_time_iso_url_encoded="{snapshot_time_iso}",
                ),
                "snapshot_time": t60,
                "fixture_event_reference_local": rep,
                "market": MARKET_FROZEN,
                "region": REGION_FROZEN,
                "estimated_credit_cost": CREDITS_PASO_A_PER_REQUEST_EST,
                "purpose": (
                    "Listar eventos históricos TOA para matchear SM fixture→TOA event_id "
                    f"(agrupa {len(fids)} fixtures con mismo sport_key y T-60; ver manifest)."
                ),
            }
        )

    for row in all_rows:
        sk = (row.get("the_odds_api_sport_key_expected") or "").strip()
        t60 = (row.get("historical_query_timestamp_utc") or "").strip()
        plan_rows.append(
            {
                "sport_key": sk,
                "request_type": "paso_b_event_odds_h2h_t60",
                "endpoint_expected": PASO_B_ENDPOINT_TEMPLATE.format(
                    sport_key=sk,
                    the_odds_api_event_id="{the_odds_api_event_id}",
                    snapshot_time_iso_url_encoded="{snapshot_time_iso}",
                ),
                "snapshot_time": t60,
                "fixture_event_reference_local": f"sm_fixture_id={row['fixture_id']};bt2_event_id={row['event_id']}",
                "market": MARKET_FROZEN,
                "region": REGION_FROZEN,
                "estimated_credit_cost": CREDITS_PASO_B_PER_FIXTURE_EST,
                "purpose": (
                    "Tras match en paso A: odds h2h (FT_1X2 laboratorio) en snapshot T-60 para el event_id TOA."
                ),
            }
        )

    plan_fn = OUT_DIR / "pilot_request_plan.csv"
    plan_fields = [
        "sport_key",
        "request_type",
        "endpoint_expected",
        "snapshot_time",
        "fixture_event_reference_local",
        "market",
        "region",
        "estimated_credit_cost",
        "purpose",
    ]
    with plan_fn.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=plan_fields)
        w.writeheader()
        for pr in plan_rows:
            w.writerow(pr)

    n_paso_a = sum(1 for r in plan_rows if r["request_type"] == "paso_a_event_discovery")
    n_paso_b = sum(1 for r in plan_rows if r["request_type"] == "paso_b_event_odds_h2h_t60")
    credits_a = n_paso_a * CREDITS_PASO_A_PER_REQUEST_EST
    credits_b = n_paso_b * CREDITS_PASO_B_PER_FIXTURE_EST
    total_requests = len(plan_rows)
    total_credits_est = credits_a + credits_b

    leagues_present = sorted(league_counts.keys())
    missing_leagues = sorted(SUBSET5_SM_LEAGUE_IDS - set(leagues_present))
    coverage_subset5_complete = len(missing_leagues) == 0

    execution_ready = usable_sk == len(all_rows) and len(all_rows) > 0
    all_warnings = list(manifest_warnings) + [f"topup: {e}" for e in topup_errors]

    summary = {
        "phase": "3e_the_odds_api_pilot_prep_subset5",
        "generated_at_note": "Regenerar con scripts/bt2_theoddsapi_pilot_day1_dryrun.py --generate",
        "diagnostico_ausencia_82_384_en_sample_3d": {
            "causa_principal": (
                "Ninguna fila de `vendor_validation_sample.csv` con sm_league_id 82 o 384: el builder 3D "
                "estratifica ~40-180 filas entre semanas/VP; no garantiza al menos un fixture por cada liga subset5."
            ),
            "no_es": [
                "Mapeo TOA roto para 82/384 (están en mapa sm_league_id; pilot_tier pilot_now en manifiesto de ligas).",
            ],
        },
        "complemento_db_topup": {
            "activo": bool(topup_rows),
            "notas": topup_notes,
            "errores_o_corto": topup_errors,
        },
        "constraints": {
            "no_the_odds_api_http": True,
            "no_sm_odds": True,
            "no_phase_4": True,
            "no_bounded_replay_changes": True,
            "no_productive_integration": True,
            "no_mass_backfill": True,
        },
        "frozen_universe": {
            "subset5_sm_league_ids": sorted(SUBSET5_SM_LEAGUE_IDS),
            "market": MARKET_FROZEN,
            "bt2_market": BT2_MARKET,
            "region": REGION_FROZEN,
            "snapshot_policy": (
                "T-60: cutoff_t60(kickoff) (igual 3C/3D). Vendor sample: historical_query_timestamp_utc. "
                "Top-up: mismo cálculo desde eventos en cohorte A (BT2)."
            ),
            "sources": [
                str(VENDOR_SAMPLE.relative_to(_repo)),
                str(PILOT_LEAGUE_MANIFEST.relative_to(_repo)),
                "bt2_events + bt2_leagues (top-up mínimo lectura, sin HTTP)",
            ],
        },
        "counts": {
            "fixtures_in_manifest": len(all_rows),
            "fixtures_from_vendor_sample_only": n_vendor,
            "fixtures_from_db_topup": n_topup,
            "distinct_leagues_in_manifest": len(leagues_present),
            "rows_with_usable_sport_key": usable_sk,
            "fixtures_per_sm_league_id": {str(k): league_counts[k] for k in sorted(league_counts)},
            "subset5_leagues_without_fixtures_in_manifest": [str(x) for x in missing_leagues],
            "coverage_subset5_all_five_leagues": coverage_subset5_complete,
        },
        "request_plan_estimates": {
            "paso_a_requests": n_paso_a,
            "paso_b_requests": n_paso_b,
            "total_requests": total_requests,
            "credits_paso_a_est": credits_a,
            "credits_paso_b_est": credits_b,
            "total_credits_est": total_credits_est,
            "credit_assumptions": (
                "Paso A: 1 crédito/request (listado histórico por deporte/fecha snapshot según práctica 3D). "
                "Paso B: 10 créditos/fixture para odds histórico por evento (h2h × us), alineado a readiness_summary day_one."
            ),
        },
        "pilot_ready_after_payment": execution_ready and coverage_subset5_complete,
        "pilot_ready_reason": (
            "Manifiesto y plan listos; cobertura 5 ligas; top-up no alcanzó n mínimo en alguna liga (ver complemento_db_topup)."
            if (topup_errors and coverage_subset5_complete)
            else (
                "Manifiesto y plan listos; 5 ligas con al menos 1 fixture; T-60 + h2h + us; listo para laboratorio pago."
                if (execution_ready and coverage_subset5_complete)
                else "Revisar fixtures/cobertura: ver subset5_leagues_without_fixtures_in_manifest o complemento_db_topup."
            )
        ),
        "pilot_representative_subset5_verdict": (
            "representativo_5_ligas"
            if (coverage_subset5_complete and not topup_errors)
            else (
                "representativo_5_ligas_con_asterisco" if (coverage_subset5_complete and topup_errors) else "no_representativo"
            )
        ),
        "manifest_generation_warnings": all_warnings,
    }

    (OUT_DIR / "pilot_prep_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    readme = f"""# BT2 — Preparación piloto The Odds API (subset 5)

- **Base:** `vendor_validation_sample.csv` + `pilot_league_manifest.json` — `priority_pilot_now`, subset5, `h2h`, `us`, T-60 (sample 3D).
- **Complemento (representatividad 5 ligas):** si el sample no trae alguna liga del subset5, se añaden fixtures desde `bt2_events` (cohorte A, mismo criterio mapeo/T-60 que 3D). Sin top-up: `BT2_PILOT_TOPUP_OFFLINE=1`.

## Regenerar

```bash
cd {_repo}
python3 scripts/bt2_theoddsapi_pilot_day1_dryrun.py --generate
python3 scripts/bt2_theoddsapi_pilot_day1_dryrun.py
```

## Artefactos

- `pilot_fixture_manifest.csv`
- `pilot_request_plan.csv`
- `pilot_persistence_contract.md`
- `pilot_result_taxonomy.md`
- `pilot_prep_summary.json`

Ver `pilot_prep_summary.json` para conteos, `pilot_representative_subset5_verdict` y créditos estimados.
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    return summary


def _write_static_docs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "pilot_persistence_contract.md").write_text(
        """# Contrato de persistencia — laboratorio piloto The Odds API (no productivo)

Definición de campos para cuando se persistan resultados del piloto (tabla laboratorio o CSV). **No implementa pipeline productivo.**

## Timestamps

| Campo | Significado |
|-------|-------------|
| `provider_snapshot_time` | Instantánea declarada por el proveedor TOA en la respuesta (tiempo de mercado/snapshot del payload histórico). |
| `provider_last_update` | Última actualización del book dentro del mercado/outcome TOA (`last_update` por bookmaker/outcome cuando aplique). |
| `ingested_at` | Cuando nuestro proceso escribió la fila en almacenamiento local. **No es tiempo de mercado.** |
| `backfilled_at` | Si un job reprocesó o backfiltró la fila. **No es tiempo de mercado.** |
| `kickoff_utc` | Inicio del partido (`bt2_events.kickoff_utc` / fixture master SportMonks). |

**Regla:** nunca usar `ingested_at` ni `backfilled_at` como sustituto del tiempo real del mercado o de la cuota.

## Identificación mercado / evento

| Campo | Significado |
|-------|-------------|
| `sport_key` | Clave TOA del deporte/liga (`the_odds_api_sport_key_expected`). |
| `market` | Mercado TOA (`h2h` para piloto FT_1X2). |
| `region` | Región de bookmakers (`us` en piloto inicial). |
| `bookmaker` | Identificador/nombre bookmaker en respuesta TOA. |
| `outcome_name` | Etiqueta outcome (ej. equipo / Draw) tal cual TOA. |
| `decimal_price` | Probabilidad implícita como decimal desde outcome TOA (normalizado para análisis). |

## Matching y estado laboratorio

| Campo | Significado |
|-------|-------------|
| `sm_fixture_id` | ID fixture SportMonks (referencia BT2). |
| `bt2_event_id` | ID interno BT2. |
| `the_odds_api_event_id` | ID evento devuelto por TOA tras paso A. |
| `fixture_matching_status` | Ver `pilot_result_taxonomy.md` (matched / unmatched / gap). |
| `laboratory_classification_status` | Clasificación del resultado del experimento (taxonomía piloto). |

--- 

*Piloto subset 5, mercado único h2h, región us, snapshots T-60.*
""",
        encoding="utf-8",
    )

    (OUT_DIR / "pilot_result_taxonomy.md").write_text(
        """# Taxonomía de resultados — laboratorio piloto The Odds API

Estados mínimos para clasificar cada intento cuando existan llamadas reales.

| Estado | Cuándo usar |
|--------|-------------|
| `matched_with_odds_t60` | Evento TOA matcheado y respuesta odds h2h en snapshot T-60 con outcomes utilizables. |
| `matched_without_odds_t60` | Evento matcheado pero sin mercado h2h o sin precios en ventana T-60. |
| `unmatched_event` | No se encontró evento TOA coherente con SM/BT2 para el sport_key y fecha/snapshot. |
| `league_not_supported` | `sport_key` o liga no disponible en TOA para el piloto. |
| `market_not_supported` | Deporte/liga ok pero mercado `h2h` no devuelto o vacío. |
| `bookmaker_gap` | Mercado existe pero ningún bookmaker en región `us` (o lista vacía). |
| `timestamp_gap` | Odds existen pero `provider_snapshot_time` / alineación T-60 es inválida o fuera de ventana. |
| `normalization_gap` | No se pudo mapear outcome a lado BT2 / decimal / nombre equipo tras normalizar. |

Los campos `fixture_matching_status` y `laboratory_classification_status` en persistencia deben referenciar estos valores o refinamientos documentados en el mismo experimento.
""",
        encoding="utf-8",
    )


def validate_artifacts() -> dict[str, Any]:
    manifest_path = OUT_DIR / "pilot_fixture_manifest.csv"
    plan_path = OUT_DIR / "pilot_request_plan.csv"
    summary_path = OUT_DIR / "pilot_prep_summary.json"
    errors: list[str] = []
    warnings: list[str] = []

    if not manifest_path.is_file():
        errors.append(f"Falta {manifest_path.name}; ejecuta --generate")
        return {"ok": False, "errors": errors, "warnings": warnings}

    rows: list[dict[str, str]] = []
    with manifest_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    league_ids = set()
    for row in rows:
        lid = int(row["sm_league_id"])
        league_ids.add(lid)
        if lid not in SUBSET5_SM_LEAGUE_IDS:
            errors.append(f"Liga fuera subset5: sm_league_id={lid}")
        sk = (row.get("the_odds_api_sport_key_expected") or "").strip()
        if not sk:
            errors.append(f"sport_key vacío: sm_fixture_id={row.get('sm_fixture_id')}")
        if (row.get("market") or "").lower() != MARKET_FROZEN:
            errors.append(f"market distinto de {MARKET_FROZEN}: {row.get('sm_fixture_id')}")
        if (row.get("region") or "").lower() != REGION_FROZEN:
            errors.append(f"region distinta de {REGION_FROZEN}: {row.get('sm_fixture_id')}")

    missing = SUBSET5_SM_LEAGUE_IDS - league_ids
    if missing:
        warnings.append(
            "Muestra sin fixtures para ligas subset5: " + ", ".join(str(m) for m in sorted(missing))
        )

    if plan_path.is_file():
        plan_rows = list(csv.DictReader(plan_path.open(encoding="utf-8")))
        total_credits = sum(int(r.get("estimated_credit_cost") or 0) for r in plan_rows)
    else:
        warnings.append("Falta pilot_request_plan.csv")
        total_credits = 0

    summary_ok = summary_path.is_file()
    if not summary_path.is_file():
        warnings.append("Falta pilot_prep_summary.json; ejecuta --generate")

    ok = not errors
    out: dict[str, Any] = {
        "ok": ok,
        "fixtures_validated": len(rows),
        "distinct_leagues": len(league_ids),
        "errors": errors,
        "warnings": warnings,
        "estimated_total_credits_from_plan": total_credits,
        "summary_present": summary_ok,
    }
    if summary_ok:
        out["pilot_ready_flag"] = json.loads(summary_path.read_text(encoding="utf-8")).get(
            "pilot_ready_after_payment"
        )

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run piloto TOA día 1 (sin HTTP)")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Regenera manifiesto, plan, summary y README desde vendor_validation_sample + manifest 3D",
    )
    args = parser.parse_args()

    if args.generate:
        _write_static_docs()
        summary = generate_artifacts()
        print(json.dumps({"ok": True, "mode": "generate", "summary": summary}, indent=2, ensure_ascii=False))
    else:
        _write_static_docs()
        val = validate_artifacts()
        print(json.dumps(val, indent=2, ensure_ascii=False))
        if not val.get("ok"):
            sys.exit(1)


if __name__ == "__main__":
    main()

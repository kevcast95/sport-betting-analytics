#!/usr/bin/env python3
"""
Auditoría ds_input shadow-native + muestra enriquecida (experimento).

Genera:
- ds_input_shadow_native_current_audit.md
- ds_input_shadow_native_vs_original_gap.md
- ds_input_shadow_native_enrichment_design.md
- ds_input_shadow_native_enriched_sample.json

Uso: PYTHONPATH=. python3 scripts/bt2_shadow_native_ds_input_audit.py
"""

from __future__ import annotations

import copy
import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Optional

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.bt2_admin_backtest_replay import blind_ds_input_item  # noqa: E402
from apps.api.bt2_dsr_ds_input_builder import apply_postgres_context_to_ds_item  # noqa: E402
from apps.api.bt2_dsr_shadow_native_adapter import build_ds_input_shadow_native  # noqa: E402
from apps.api.bt2_dsr_shadow_native_enrichment import apply_shadow_native_enriched_context  # noqa: E402
from apps.api.bt2_settings import bt2_settings  # noqa: E402

OUT_DIR = ROOT / "scripts" / "outputs" / "bt2_shadow_dsr_replay"
FIXED_SAMPLE = OUT_DIR / "dsr_pilot_sample.csv"

_SPEC = importlib.util.spec_from_file_location("_sn", ROOT / "scripts" / "bt2_shadow_native_dsr_pilot.py")
_SN = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader
_SPEC.loader.exec_module(_SN)


def _dsn() -> str:
    u = bt2_settings.bt2_database_url
    return u.replace("postgresql+asyncpg://", "postgresql://", 1) if u.startswith("postgresql+asyncpg://") else u


def _availability(item: dict[str, Any]) -> dict[str, Optional[bool]]:
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


def _diag_snapshot(item: dict[str, Any]) -> dict[str, Any]:
    d = item.get("diagnostics") or {}
    return {
        "lineups_ok": d.get("lineups_ok"),
        "h2h_ok": d.get("h2h_ok"),
        "statistics_ok": d.get("statistics_ok"),
        "prob_coherence": (d.get("prob_coherence") or {}).get("flag"),
        "fetch_errors_count": len(d.get("fetch_errors") or []),
    }


def _strip_heavy(item: dict[str, Any]) -> dict[str, Any]:
    """Reduce odds_featured.by_bookmaker para JSON legible."""
    x = copy.deepcopy(item)
    po = x.get("processed") if isinstance(x.get("processed"), dict) else {}
    of = po.get("odds_featured") if isinstance(po.get("odds_featured"), dict) else {}
    if isinstance(of, dict) and of.get("by_bookmaker"):
        rows = of["by_bookmaker"]
        if isinstance(rows, list):
            of["by_bookmaker"] = {
                "_truncated": True,
                "rows_total": len(rows),
                "sample_first_3": rows[:3],
            }
    return x


def _simulate_legacy_strict_gate(
    cur: Any,
    item: dict[str, Any],
    *,
    bt2_event_id: Optional[int],
    kickoff_utc: Any,
) -> None:
    """Comportamiento anterior: solo apply_postgres si ambos team ids en bt2_events."""
    if not bt2_event_id:
        return
    ev = _SN._load_event_row(cur, int(bt2_event_id))
    if ev and ev.get("home_team_id") and ev.get("away_team_id"):
        apply_postgres_context_to_ds_item(
            cur,
            item,
            event_id=int(bt2_event_id),
            home_team_id=int(ev["home_team_id"]),
            away_team_id=int(ev["away_team_id"]),
            sportmonks_fixture_id=int(ev["sportmonks_fixture_id"])
            if ev.get("sportmonks_fixture_id")
            else None,
            kickoff_utc=kickoff_utc,
        )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sample_ids: list[int] = []
    with open(FIXED_SAMPLE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row.get("shadow_pick_id")
            if pid and str(pid).isdigit():
                sample_ids.append(int(pid))

    audit_ids = sample_ids[:15]

    conn = psycopg2.connect(_dsn(), connect_timeout=35)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    rows_audit: list[dict[str, Any]] = []
    enriched_records: list[dict[str, Any]] = []
    counts_legacy_true = {k: 0 for k in [
        "odds_featured", "lineups", "h2h", "statistics", "team_streaks",
        "team_season_stats", "fixture_conditions", "match_officials",
        "squad_availability", "tactical_shape", "prediction_signals",
        "broadcast_notes", "fixture_advanced_sm",
    ]}
    counts_new_true = copy.deepcopy(counts_legacy_true)
    flip_counts = {k: 0 for k in counts_legacy_true}

    universe = _SN._fetch_universe(cur)
    by_id = {int(r["shadow_pick_id"]): r for r in universe}

    for spid in sample_ids:
        r = by_id.get(spid)
        if not r:
            continue
        pj = _SN._load_pick_inputs(cur, spid)
        sn_ex, agg, meta = _SN._shadow_native_exclusion(cur, r, pj)
        if sn_ex != "eligible_shadow_native" or agg is None:
            continue

        league, home, away, ko, status = _SN._resolve_context(cur, r, meta)
        base = build_ds_input_shadow_native(
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

        legacy_item = copy.deepcopy(base)
        _simulate_legacy_strict_gate(
            cur,
            legacy_item,
            bt2_event_id=int(r["bt2_event_id"]) if r.get("bt2_event_id") else None,
            kickoff_utc=ko,
        )

        enriched_item = copy.deepcopy(base)
        sm_fid = int(r["sm_fixture_id"]) if r.get("sm_fixture_id") else None
        meta_enr = apply_shadow_native_enriched_context(
            cur,
            enriched_item,
            bt2_event_id=int(r["bt2_event_id"]) if r.get("bt2_event_id") else None,
            sportmonks_fixture_id=sm_fid,
            kickoff_utc=ko,
        )

        a_leg = _availability(legacy_item)
        a_new = _availability(enriched_item)
        for k in counts_legacy_true:
            if a_leg.get(k):
                counts_legacy_true[k] += 1
            if a_new.get(k):
                counts_new_true[k] += 1
            if (not a_leg.get(k)) and a_new.get(k):
                flip_counts[k] += 1

        if spid in audit_ids:
            rows_audit.append(
                {
                    "shadow_pick_id": spid,
                    "bt2_event_id": r.get("bt2_event_id"),
                    "sm_fixture_id": r.get("sm_fixture_id"),
                    "legacy_processed_available": a_leg,
                    "enriched_processed_available": a_new,
                    "legacy_diagnostics": _diag_snapshot(legacy_item),
                    "enriched_diagnostics": _diag_snapshot(enriched_item),
                    "enrichment_meta": meta_enr,
                }
            )

        enriched_records.append(
            {
                "shadow_pick_id": spid,
                "enrichment_path": meta_enr.get("path"),
                "enrichment_notes": meta_enr.get("notes"),
                "ds_input_blind_summary": {
                    "processed_available": _availability(enriched_item),
                    "diagnostics": _diag_snapshot(enriched_item),
                },
                "ds_input_blind_excerpt": blind_ds_input_item(_strip_heavy(enriched_item)),
            }
        )

    cur.close()
    conn.close()

    eligible_n = len(enriched_records)

    audit_md = f"""# Auditoría `ds_input` shadow-native (muestra fija)

- Generado por `scripts/bt2_shadow_native_ds_input_audit.py`
- Universo: picks elegibles shadow-native intersectados con `dsr_pilot_sample.csv`
- Filas elegibles en muestra: **{eligible_n}** (de {len(sample_ids)} ids en CSV)
- `odds_featured`: se cuenta como “presente” si hay `consensus` (no usa clave `available`).
- **Nota:** en esta muestra, el gate legacy simulado y el enrichment coinciden en flags (`Δ false→true` = 0) porque los eventos tienen `home_team_id`/`away_team_id` en CDM; la capa nueva **sigue siendo necesaria** para filas con NULL o sin `bt2_event_id`.

## Resumen: bloques `processed.*` con `available=true`

Conteos sobre las filas elegibles de la muestra (no sobre todo el replay masivo).

| Bloque | Legacy (gate estricto previo) | Tras `apply_shadow_native_enriched_context` | Δ false→true |
|--------|-------------------------------|-----------------------------------------------|--------------|
"""
    for k in counts_legacy_true:
        audit_md += f"| `{k}` | {counts_legacy_true[k]} | {counts_new_true[k]} | {flip_counts[k]} |\n"

    audit_md += """
## Detalle (primeros 15 ids del CSV elegibles)

"""
    for row in rows_audit:
        audit_md += f"### shadow_pick_id={row['shadow_pick_id']} (bt2_event_id={row.get('bt2_event_id')})\n\n"
        audit_md += f"- **Legacy** processed flags: `{row['legacy_processed_available']}`\n"
        audit_md += f"- **Enriched** processed flags: `{row['enriched_processed_available']}`\n"
        audit_md += f"- Enrichment path: `{row.get('enrichment_meta', {}).get('path')}` — notes: `{row.get('enrichment_meta', {}).get('notes')}`\n\n"

    (OUT_DIR / "ds_input_shadow_native_current_audit.md").write_text(audit_md, encoding="utf-8")

    gap_md = """# Brecha: builder original vs carril shadow-native (antes del enrichment)

## Builder “rico” (`build_ds_input_item` + `apply_postgres_context_to_ds_item`)

- Base: `processed.odds_featured.consensus` + `by_bookmaker`, `diagnostics.market_coverage`, `prob_coherence`.
- Enriquecimiento CDM: forma (últimos partidos), H2H, rachas, descanso, subbloques por rol/localía, sums goles en ventana, contexto `cdm_from_bt2_events`.
- SportMonks raw (`raw_sportmonks_fixtures`): `lineups` agregados, estadísticas fixture SM, `merge_sm_optional_fixture_blocks`.
- Meta ingesta: `ingest_meta` desde `bt2_odds_snapshot` **solo si hay** `bt2_events.id` (evento CDM).

## Qué hace shadow-native base (`build_ds_input_shadow_native`)

- Reutiliza **el mismo** `build_ds_input_item` para odds/contexto mínimo.
- Las cuotas vienen del adapter TOA (no `bt2_odds_snapshot` como gate).

## Qué se perdía en la práctica (bug de integración)

El script de replay native llamaba `apply_postgres_context_to_ds_item` **solo si**
`bt2_events.home_team_id` **y** `away_team_id` estaban ambos presentes.

Si cualquiera era NULL, **no se ejecutaba ningún enriquecimiento**, incluida la fusión SM (lineups/stats) que en el builder original sí ocurre más abajo con `sportmonks_fixture_id`.

## Qué corrige `apply_shadow_native_enriched_context`

1. Resolución auxiliar de `home_team_id`/`away_team_id` desde `participants` SM → `bt2_teams.sportmonks_id`.
2. Llamada a `apply_postgres_context_to_ds_item` con IDs resueltos (cuando existe `bt2_event_id`).
3. Sin `bt2_event_id` pero con `sm_fixture_id`: bloques SM (lineups/stats/opcionales) sin depender del CDM.

No se usa la puerta legacy T-60 ni `bt2_odds_snapshot` como requisito de elegibilidad.
"""
    (OUT_DIR / "ds_input_shadow_native_vs_original_gap.md").write_text(gap_md, encoding="utf-8")

    design_md = """# Diseño: capa de enriquecimiento shadow-native

## Módulo

`apps/api/bt2_dsr_shadow_native_enrichment.py`

## API

`apply_shadow_native_enriched_context(cur, item, *, bt2_event_id, sportmonks_fixture_id, kickoff_utc) -> meta`

## Fuentes

| Fuente | Uso |
|--------|-----|
| `bt2_events` | IDs equipo, `sportmonks_fixture_id`, liga/temporada para `apply_postgres_context_to_ds_item` |
| `raw_sportmonks_fixtures` | Participantes (IDs SM), lineups agregados, stats fixture, bloques opcionales |
| `bt2_teams` | Mapeo `sportmonks_id` → `bt2_teams.id` para forma/H2H cuando el CDM tiene NULL |

## Qué no recupera (por ahora)

- Temporada agregada custom (`team_season_stats`) sigue vacío por gap de tabla DX documentado.
- Si no hay fila raw SM o participantes no mapean a `bt2_teams`, parte del contexto sigue ausente.

## Principios

- La **puerta** sigue siendo shadow-native (TOA + value pool); esto es solo **relleno** posterior al `build_ds_input_shadow_native`.
- No sustituye `bt2_odds_snapshot`; las odds del lote siguen siendo TOA agregadas del adapter.
"""
    (OUT_DIR / "ds_input_shadow_native_enrichment_design.md").write_text(design_md, encoding="utf-8")

    (OUT_DIR / "ds_input_shadow_native_enriched_sample.json").write_text(
        json.dumps(
            {
                "sample_csv": str(FIXED_SAMPLE.relative_to(ROOT)),
                "eligible_rows": eligible_n,
                "processed_available_counts_legacy_strict_simulation": counts_legacy_true,
                "processed_available_counts_after_enrichment": counts_new_true,
                "false_to_true_flips": flip_counts,
                "records": enriched_records,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(json.dumps({"ok": True, "eligible_in_sample": eligible_n, "out": str(OUT_DIR)}, indent=2))


if __name__ == "__main__":
    main()

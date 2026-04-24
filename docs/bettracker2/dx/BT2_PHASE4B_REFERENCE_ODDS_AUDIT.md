# Fase 4B — `reference_decimal_odds`: circuito, auditoría y backfill

## Dónde vive

- Tabla: **`bt2_daily_picks`**
- Columna: **`reference_decimal_odds`** (`Numeric(10,4)`, nullable) — migración `k1a2b3c4d5e6_bt2_daily_picks_reference_decimal_odds.py`

## Origen previsto (write path productivo)

- Archivo: `apps/api/bt2_router.py` → `_materialize_daily_picks_snapshot`
- Tras armar `row_payloads`, por pick:
  - `ref_odds = consensus_decimal_for_canonical_pick(agg.consensus, mmc, msc)`
  - `agg` es el de la **materialización** del mismo día (pool valor + `build_ds_input_item_from_db`)
- INSERT en `bt2_daily_picks` incluye `p.get("ref_odds")` → puede quedar **NULL** si `consensus_decimal_for_canonical_pick` devuelve `None` (mercado/selección ausente en `consensus`, o cuota ≤ 1).

Función de resolución: `apps/api/bt2_dsr_odds_aggregation.py` → `consensus_decimal_for_canonical_pick`.

## Reconstrucción histórica (backfill)

- Script existente: `scripts/bt2_cdm/backfill_daily_pick_reference_odds.py`
- Lee `model_market_canonical` / `model_selection_canonical` del pick, agrega con **`aggregated_odds_for_event_psycopg` sin corte de tiempo** (consenso “actual” CDM) y actualiza solo filas con `reference_decimal_odds IS NULL`.
- **Caveat:** la cuota backfilleara no es necesariamente la del instante `suggested_at`; sirve para cobertura analítica y segmentación, no para un audit legal de línea exacta sin snapshot temporal.

## Lecturas

- `apps/api/bt2_monitor_resultados.py` (lista / detalle)
- `scripts/bt2_phase4_selective_release_edge_audit.py` (si está en la rama que use edge audit)

## Auditoría ventana 2026-04-13 → 2026-04-20 (scored official)

| Métrica | Antes | Después (backfill 53 filas) |
|--------|-------|-------------------------------|
| Scored total | 79 | 79 |
| Con `reference_decimal_odds` > 1 | 26 | **79** |
| Sin cuota usable | 53 | **0** |

Patrón **antes**: días `2026-04-13` … `2026-04-18` → **0** picks scored con cuota; `2026-04-19` y `2026-04-20` → **100%** con cuota. Eso apunta a **deuda histórica** (filas creadas con `NULL` en ese período) más que a un fallo aleatorio por mercado; el dry-run del backfill encontró **53** filas `NULL` actualizables con consenso actual — todas las faltantes de la ventana.

## Ejecución realizada

```bash
python3 scripts/bt2_cdm/backfill_daily_pick_reference_odds.py \
  --operating-day-from 2026-04-13 --operating-day-to 2026-04-20 --limit 5000
```

(`--dry-run` previo: 53 examinadas, 53 actualizables.)

## Validación métricas globales (misma ventana, stake 1u)

| | Antes (Fase 4) | Después |
|--|----------------|---------|
| `n_with_odds` / ROI | 26 picks con odds | **79** |
| ROI proxy medio | ≈ −0,40 | ≈ **−0,19** |
| `avg_decimal_odds` | ≈ 2,10 (sesgado a bloque B) | ≈ **1,99** |
| Hit rate global | 0,4557 | **0,4557** (sin cambio; solo relleno de cuota) |

## Próximo paso Fase 4

Volver a correr el edge audit completo en la rama que incluya `scripts/bt2_phase4_selective_release_edge_audit.py` y commitear `summary.json` / `segments.csv` actualizados si se desea trazabilidad en repo.

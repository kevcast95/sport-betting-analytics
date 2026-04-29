# DSR-ready shadow-native — contrato operativo

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

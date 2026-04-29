# BT2 Shadow Monitoring Contract (Subset5)

## Alcance actual (iteración 1)
- UI reutiliza `monitor-resultados` con selector `Prod | Shadow`.
- `Prod` mantiene endpoint y tablas actuales (`bt2_daily_picks`, `bt2_pick_official_evaluation`).
- `Shadow` usa endpoint separado `GET /bt2/admin/analytics/monitor-resultados-shadow`.
- Fuente inicial del endpoint shadow: artefactos de laboratorio en `scripts/outputs/bt2_vendor_lab_day1/`.

## KPIs shadow mínimos (ya soportados)
- `fixtures_seen`
- `fixtures_matched`
- `match_rate`
- `fixtures_with_h2h_t60`
- `value_pool_pass_rate`
- `shadow_picks_generated`
- `matched_with_odds_t60`
- `matched_without_odds_t60`
- `unmatched_event`
- `credits_used`
- `avg_credits_per_fixture`

## Row contract shadow (ya soportado en API/UI)
- `operating_day_key`
- `fixture_event_label`
- `league_name`
- `market`
- `selection`
- `status_shadow`
- `classification_taxonomy`
- `decimal_odds`
- `provider_source`
- `provider_snapshot_time`
- `provider_last_update`
- `ingested_at`
- `dsr_source`
- `match_notes` / `raw_payload_summary`

## Persistencia shadow dedicada (iteración 1, DDL listo)
Tablas nuevas (sin tocar picks productivos):
- `bt2_shadow_runs`
- `bt2_shadow_provider_snapshots`
- `bt2_shadow_daily_picks`
- `bt2_shadow_pick_inputs`
- `bt2_shadow_pick_eval`

Campos clave cubiertos:
- `mode`, `provider_stack`, `is_shadow`
- `provider_snapshot_time`, `provider_last_update`, `ingested_at`
- `classification_taxonomy`
- `credits_used`

## Regla de tiempo de mercado
- `ingested_at` es tiempo de ingestión técnica.
- Tiempo de mercado debe leerse desde `provider_snapshot_time` y/o `provider_last_update`.
- Nunca usar `ingested_at` como tiempo real del mercado.

## Próxima iteración (sin romper contrato UI/API)
1. Poblar `bt2_shadow_*` desde corridas diarias/backfill controlado.
2. Mover endpoint shadow de artefactos CSV a lectura SQL (`bt2_shadow_daily_picks` + joins).
3. Exponer cortes duales en UI:
   - flujo diario shadow
   - histórico ciego subset5

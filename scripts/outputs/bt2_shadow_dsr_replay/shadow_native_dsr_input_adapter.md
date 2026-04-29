# Adapter shadow → DSR input (`bt2_dsr_shadow_native_adapter`)

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

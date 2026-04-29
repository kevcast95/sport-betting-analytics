# Brecha: builder original vs carril shadow-native (antes del enrichment)

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

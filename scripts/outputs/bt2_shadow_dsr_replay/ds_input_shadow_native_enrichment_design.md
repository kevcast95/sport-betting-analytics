# Diseño: capa de enriquecimiento shadow-native

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

# Auditoría `ds_input` shadow-native (muestra fija)

- Generado por `scripts/bt2_shadow_native_ds_input_audit.py`
- Universo: picks elegibles shadow-native intersectados con `dsr_pilot_sample.csv`
- Filas elegibles en muestra: **32** (de 32 ids en CSV)
- `odds_featured`: se cuenta como “presente” si hay `consensus` (no usa clave `available`).
- **Nota:** en esta muestra, el gate legacy simulado y el enrichment coinciden en flags (`Δ false→true` = 0) porque los eventos tienen `home_team_id`/`away_team_id` en CDM; la capa nueva **sigue siendo necesaria** para filas con NULL o sin `bt2_event_id`.

## Resumen: bloques `processed.*` con `available=true`

Conteos sobre las filas elegibles de la muestra (no sobre todo el replay masivo).

| Bloque | Legacy (gate estricto previo) | Tras `apply_shadow_native_enriched_context` | Δ false→true |
|--------|-------------------------------|-----------------------------------------------|--------------|
| `odds_featured` | 32 | 32 | 0 |
| `lineups` | 17 | 17 | 0 |
| `h2h` | 26 | 26 | 0 |
| `statistics` | 32 | 32 | 0 |
| `team_streaks` | 0 | 0 | 0 |
| `team_season_stats` | 0 | 0 | 0 |
| `fixture_conditions` | 19 | 19 | 0 |
| `match_officials` | 0 | 0 | 0 |
| `squad_availability` | 18 | 18 | 0 |
| `tactical_shape` | 19 | 19 | 0 |
| `prediction_signals` | 19 | 19 | 0 |
| `broadcast_notes` | 0 | 0 | 0 |
| `fixture_advanced_sm` | 19 | 19 | 0 |

## Detalle (primeros 15 ids del CSV elegibles)

### shadow_pick_id=244 (bt2_event_id=102355)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=214 (bt2_event_id=102352)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=203 (bt2_event_id=102606)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': False, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': False, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=235 (bt2_event_id=102342)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=243 (bt2_event_id=102354)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=193 (bt2_event_id=102628)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=262 (bt2_event_id=102336)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=239 (bt2_event_id=102611)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=242 (bt2_event_id=102353)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': False, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': False, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=213 (bt2_event_id=102351)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': False, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': False, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=259 (bt2_event_id=102333)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=233 (bt2_event_id=102340)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=251 (bt2_event_id=102543)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=212 (bt2_event_id=102350)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': True, 'h2h': True, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': True, 'match_officials': False, 'squad_availability': True, 'tactical_shape': True, 'prediction_signals': True, 'broadcast_notes': False, 'fixture_advanced_sm': True}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`

### shadow_pick_id=256 (bt2_event_id=102330)

- **Legacy** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': False, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- **Enriched** processed flags: `{'odds_featured': True, 'lineups': False, 'h2h': False, 'statistics': True, 'team_streaks': False, 'team_season_stats': False, 'fixture_conditions': False, 'match_officials': False, 'squad_availability': False, 'tactical_shape': False, 'prediction_signals': False, 'broadcast_notes': False, 'fixture_advanced_sm': False}`
- Enrichment path: `apply_postgres_context_resolved_teams` — notes: `[]`


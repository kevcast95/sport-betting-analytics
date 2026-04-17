# BT2 provider — SofaScore (S6.5 Validate SFS)

**No** es el scraper legacy V1. **No** usa SQLite como destino del experimento.

## Obligatorio de cierre S6.5

- `GET /api/v1/event/{id}/odds/1/featured`
- `GET /api/v1/event/{id}/odds/1/all`

## Límites (ver `EJECUCION.md` / runbook)

- `BT2_SFS_EXPERIMENT_MAX_EVENTS_PER_RUN` (default 500)
- `BT2_SFS_HTTP_MAX_RPS` (default 4)
- `BT2_SFS_EXPERIMENT_ENABLED` kill switch

## Join (D-06-067)

1. `bt2_events.sofascore_event_id`, seed JSON, override tabla `bt2_sfs_event_override`
2. Determinista: scheduled día UTC + equipos + kickoff
3. Overrides manuales

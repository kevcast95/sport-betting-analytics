# CDM Normalize — Reporte

**Fecha:** 2026-04-06 16:30
**Modo:** DRY-RUN

## Resultados

| Métrica | Valor |
|---------|-------|
| Fixtures leídos | 54,802 |
| Ligas upserted | 0 |
| Equipos upserted | 0 |
| Eventos upserted | 43,091 |
| Odds insertados | 0 |
| Excluidos (liga) | 11,711 |
| Excluidos (sin equipos) | 0 |
| Errores | 0 |

## Errores (primeros 20)
  Ninguno

## Verificación SQL
```sql
SELECT COUNT(*) FROM bt2_events;
SELECT COUNT(*) FROM bt2_odds_snapshot;
SELECT tier, COUNT(*) FROM bt2_leagues GROUP BY tier ORDER BY tier;
SELECT status, COUNT(*) FROM bt2_events GROUP BY status ORDER BY status;
```

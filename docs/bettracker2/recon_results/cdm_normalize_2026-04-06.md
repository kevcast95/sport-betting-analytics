# CDM Normalize — Reporte

**Fecha:** 2026-04-06 20:35
**Modo:** PRODUCCIÓN

## Resultados

| Métrica | Valor |
|---------|-------|
| Fixtures leídos | 55,222 |
| Ligas upserted | 43,497 |
| Equipos upserted | 86,994 |
| Eventos upserted | 43,497 |
| Odds insertados | 449,689 |
| Excluidos (liga) | 11,725 |
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

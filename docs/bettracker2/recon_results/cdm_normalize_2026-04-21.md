# CDM Normalize — Reporte

**Fecha:** 2026-04-21 23:51
**Modo:** PRODUCCIÓN

## Resultados

| Métrica | Valor |
|---------|-------|
| Fixtures leídos | 55,541 |
| Ligas upserted | 43,816 |
| Equipos upserted | 87,632 |
| Eventos upserted | 43,816 |
| Odds insertados | 452,943 |
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
